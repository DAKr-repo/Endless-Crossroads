"""
codex.games.dnd5e.feats
=========================
Feat prerequisite validation and effect application for D&D 5e characters.

Prerequisites are checked against the character's ability scores, class
proficiency flags, and whether the character has access to spellcasting.
Effects are applied directly to the character object's attributes where
possible; complex effects (e.g. bonus action attacks) are recorded as
notes and must be enforced by the combat resolver.
"""

from typing import Any, Dict, List, Optional


# =========================================================================
# FEAT PREREQUISITE CATALOGUE
# =========================================================================
# Keys match feat names exactly as written in the SRD.
# Values are dicts describing required ability scores, proficiencies, or
# a "spellcasting" capability flag.  An empty dict means no prerequisites.

FEAT_PREREQUISITES: Dict[str, Dict[str, Any]] = {
    # Strength-gated
    "Grappler":              {"ability": {"strength": 13}},
    "Heavy Armor Master":    {"proficiency": "heavy_armor"},
    "Heavily Armored":       {"proficiency": "medium_armor"},
    # Dexterity-gated
    "Defensive Duelist":     {"ability": {"dexterity": 13}},
    "Skulker":               {"ability": {"dexterity": 13}},
    # Intelligence/Wisdom OR gate
    "Ritual Caster":         {"ability_or": {"intelligence": 13, "wisdom": 13}},
    # Armor proficiency gates
    "Medium Armor Master":   {"proficiency": "medium_armor"},
    "Moderately Armored":    {"proficiency": "light_armor"},
    "Lightly Armored":       {},
    # Spellcasting requirement
    "Spell Sniper":          {"requirement": "spellcasting"},
    "War Caster":            {"requirement": "spellcasting"},
    "Elemental Adept":       {"requirement": "spellcasting"},
    # Charisma-gated
    "Inspiring Leader":      {"ability": {"charisma": 13}},
    "Actor":                 {},
    # No prerequisites
    "Alert":                 {},
    "Athlete":               {},
    "Charger":               {},
    "Crossbow Expert":       {},
    "Dual Wielder":          {},
    "Dungeon Delver":        {},
    "Durable":               {},
    "Great Weapon Master":   {},
    "Healer":                {},
    "Keen Mind":             {},
    "Linguist":              {},
    "Lucky":                 {},
    "Mage Slayer":           {},
    "Magic Initiate":        {},
    "Martial Adept":         {},
    "Mobile":                {},
    "Mounted Combatant":     {},
    "Observant":             {},
    "Polearm Master":        {},
    "Resilient":             {},
    "Savage Attacker":       {},
    "Sentinel":              {},
    "Sharpshooter":          {},
    "Shield Master":         {},
    "Skilled":               {},
    "Tavern Brawler":        {},
    "Tough":                 {},
    "Weapon Master":         {},
}


# =========================================================================
# FEAT EFFECT CATALOGUE
# =========================================================================
# Describes the mechanical effects of each feat.  These are applied by
# FeatManager.apply_feat().  Effects not listed here are flavour-only or
# require table-level enforcement.

FEAT_EFFECTS: Dict[str, Dict[str, Any]] = {
    "Tough": {
        "hp_bonus_per_level": 2,
    },
    "Alert": {
        "initiative_bonus": 5,
        "no_surprise": True,
    },
    "Observant": {
        "passive_bonus": 5,
    },
    "Athlete": {
        "asi_choice": ["strength", "dexterity"],
        "asi_amount": 1,
    },
    "Actor": {
        "asi": {"charisma": 1},
    },
    "Keen Mind": {
        "asi": {"intelligence": 1},
    },
    "Durable": {
        "asi": {"constitution": 1},
    },
    "Resilient": {
        "asi_choice": [
            "strength", "dexterity", "constitution",
            "intelligence", "wisdom", "charisma",
        ],
        "asi_amount": 1,
        "saving_throw_proficiency": True,
    },
    "Heavy Armor Master": {
        "asi": {"strength": 1},
        "dr_nonmagical": 3,
    },
    "Linguist": {
        "asi": {"intelligence": 1},
        "languages": 3,
    },
    "Lucky": {
        "lucky_points": 3,
    },
    "Sentinel": {
        "opportunity_attack_speed_0": True,
    },
    "Great Weapon Master": {
        "power_attack": True,
    },
    "Sharpshooter": {
        "power_shot": True,
    },
    "Polearm Master": {
        "bonus_attack_polearm": True,
    },
    "Crossbow Expert": {
        "ignore_loading": True,
        "no_disadvantage_melee_range": True,
    },
    "Mage Slayer": {
        "mage_slayer": True,
    },
    "Mobile": {
        "speed_bonus": 10,
    },
    "Shield Master": {
        "shield_shove": True,
    },
    "Savage Attacker": {
        "reroll_damage_once": True,
    },
    "Charger": {
        "charge_bonus_attack": True,
    },
    "Tavern Brawler": {
        "asi_choice": ["strength", "constitution"],
        "asi_amount": 1,
        "improvised_proficiency": True,
    },
    "Dual Wielder": {
        "initiative_bonus": 1,
        "dual_wield_upgrade": True,
    },
    "Dungeon Delver": {
        "advantage_secret_doors": True,
        "advantage_trap_saves": True,
    },
}


# =========================================================================
# FEAT MANAGER
# =========================================================================

class FeatManager:
    """
    Manages feat acquisition, prerequisite validation, and effect application
    for a single D&D 5e character.

    Usage::

        fm = FeatManager()
        msg = fm.apply_feat("Tough", character)
    """

    SPELLCASTING_CLASSES = frozenset({
        "bard", "cleric", "druid", "paladin", "ranger",
        "sorcerer", "warlock", "wizard", "artificer",
    })

    def __init__(self) -> None:
        self.granted_feats: List[str] = []

    # ─── Validation ────────────────────────────────────────────────────

    def validate_prerequisite(self, feat_name: str, character: Any) -> bool:
        """
        Check whether a character meets all prerequisites for a feat.

        Args:
            feat_name: Exact feat name from FEAT_PREREQUISITES.
            character: Character object with ability score attributes and
                       a `character_class` string attribute.

        Returns:
            True if all prerequisites are satisfied, False otherwise.
            Also returns False for unknown feat names.
        """
        prereqs = FEAT_PREREQUISITES.get(feat_name)
        if prereqs is None:
            return False  # Unrecognised feat
        if not prereqs:
            return True  # No prerequisites

        # ── Ability score prerequisites (all must be met) ───────────────
        if "ability" in prereqs:
            for ability, min_score in prereqs["ability"].items():
                if getattr(character, ability, 0) < min_score:
                    return False

        # ── Ability OR prerequisites (at least one must be met) ─────────
        if "ability_or" in prereqs:
            met = any(
                getattr(character, ability, 0) >= min_score
                for ability, min_score in prereqs["ability_or"].items()
            )
            if not met:
                return False

        # ── Spellcasting capability ─────────────────────────────────────
        if prereqs.get("requirement") == "spellcasting":
            char_class = getattr(character, "character_class", "").lower()
            if char_class not in self.SPELLCASTING_CLASSES:
                return False

        # ── Armor proficiency prerequisites ─────────────────────────────
        # If the character object has a `proficiencies` list we check it;
        # otherwise we fall back to class-based assumptions.
        if "proficiency" in prereqs:
            required_prof = prereqs["proficiency"]
            char_profs = getattr(character, "proficiencies", [])
            if char_profs:
                if required_prof not in char_profs:
                    return False
            else:
                # Heuristic: assume all martial classes have the required armor
                char_class = getattr(character, "character_class", "").lower()
                martial = {"fighter", "paladin", "cleric", "ranger", "barbarian", "artificer"}
                if char_class not in martial:
                    return False

        return True

    # ─── Eligibility ───────────────────────────────────────────────────

    def get_eligible_feats(self, character: Any) -> List[str]:
        """
        Return all feats the character qualifies for that have not yet been granted.

        Args:
            character: Character object.

        Returns:
            Sorted list of eligible feat names.
        """
        eligible = [
            feat_name
            for feat_name in FEAT_PREREQUISITES
            if feat_name not in self.granted_feats
            and self.validate_prerequisite(feat_name, character)
        ]
        return sorted(eligible)

    # ─── Application ───────────────────────────────────────────────────

    def apply_feat(self, feat_name: str, character: Any) -> str:
        """
        Apply a feat's mechanical effects to a character.

        Performs prerequisite validation before applying.  ASI effects are
        capped at 20. HP bonus (Tough) applies per level and is added to
        both max_hp and current_hp.

        Args:
            feat_name: Exact feat name.
            character: Mutable character object.

        Returns:
            Multi-line string describing what was applied.
        """
        if feat_name in self.granted_feats:
            return f"{feat_name} already granted."
        if not self.validate_prerequisite(feat_name, character):
            return f"Prerequisites not met for {feat_name}."

        effects = FEAT_EFFECTS.get(feat_name, {})
        messages: List[str] = [f"Gained feat: {feat_name}"]

        # ── Direct ASI ─────────────────────────────────────────────────
        if "asi" in effects:
            for ability, bonus in effects["asi"].items():
                current = getattr(character, ability, 10)
                new_val = min(20, current + bonus)
                setattr(character, ability, new_val)
                messages.append(f"  +{bonus} {ability.title()} ({new_val})")

        # ── HP bonus (Tough: +2 HP per level) ──────────────────────────
        if "hp_bonus_per_level" in effects:
            bonus = effects["hp_bonus_per_level"] * character.level
            character.max_hp += bonus
            character.current_hp += bonus
            messages.append(
                f"  +{bonus} HP ({effects['hp_bonus_per_level']} per level, "
                f"total max: {character.max_hp})"
            )

        # ── Initiative bonus (Alert, Dual Wielder) ─────────────────────
        if "initiative_bonus" in effects:
            messages.append(
                f"  +{effects['initiative_bonus']} Initiative (tracked by system)"
            )

        # ── Lucky points ───────────────────────────────────────────────
        if "lucky_points" in effects:
            messages.append(
                f"  {effects['lucky_points']} Lucky points per long rest"
            )

        # ── Movement speed bonus (Mobile) ──────────────────────────────
        if "speed_bonus" in effects:
            messages.append(
                f"  +{effects['speed_bonus']} ft movement speed"
            )

        # ── Boolean flags — record as features on the character ────────
        bool_flags = {
            "no_surprise", "power_attack", "power_shot", "bonus_attack_polearm",
            "ignore_loading", "no_disadvantage_melee_range", "mage_slayer",
            "shield_shove", "reroll_damage_once", "charge_bonus_attack",
            "improvised_proficiency", "dual_wield_upgrade",
            "advantage_secret_doors", "advantage_trap_saves",
            "opportunity_attack_speed_0", "saving_throw_proficiency",
        }
        applied_flags = [
            flag for flag in bool_flags if effects.get(flag) is True
        ]
        if applied_flags:
            features_list = getattr(character, "features", [])
            for flag in applied_flags:
                if flag not in features_list:
                    features_list.append(flag)
            try:
                character.features = features_list
            except AttributeError:
                pass  # Character object may be immutable; ignore
            messages.append(f"  Flags: {', '.join(applied_flags)}")

        # ── Non-magical DR (Heavy Armor Master) ────────────────────────
        if "dr_nonmagical" in effects:
            messages.append(
                f"  DR {effects['dr_nonmagical']} vs non-magical bludgeoning/piercing/slashing"
            )

        # ── Languages (Linguist) ───────────────────────────────────────
        if "languages" in effects:
            messages.append(f"  +{effects['languages']} languages learned")

        # ── ASI choice (note only — caller must apply) ─────────────────
        if "asi_choice" in effects:
            choice_list = ", ".join(effects["asi_choice"])
            messages.append(
                f"  +{effects.get('asi_amount', 1)} to one of: {choice_list} "
                f"(choose manually)"
            )

        self.granted_feats.append(feat_name)
        return "\n".join(messages)

    # ─── Serialisation ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialise manager state for save/load."""
        return {"granted_feats": list(self.granted_feats)}

    @classmethod
    def from_dict(cls, data: dict) -> "FeatManager":
        """Restore a FeatManager from a saved dict."""
        m = cls()
        m.granted_feats = data.get("granted_feats", [])
        return m

    def __repr__(self) -> str:  # pragma: no cover
        return f"FeatManager(feats={self.granted_feats!r})"
