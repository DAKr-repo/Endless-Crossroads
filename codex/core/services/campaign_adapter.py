"""
codex/core/services/campaign_adapter.py — Crown & Crew Campaign Adapter
=========================================================================
Builds a world_state dict from target campaign data so Crown & Crew
adapts to any campaign world. The adapter reads NPC, location, and
enemy config from the target system and maps them into C&C's narrative
structures (patrons, leaders, terms, world prompts, morning events).

Three modes:
1. Authored — hand-written campaign.json (border_run, pirate_throne, etc.)
2. Auto-generated — adapter reads config, produces full world_state
3. Hybrid — authored C&C module with target system NPC/term swap

WO-V112: Adapter layer. WO-V113: NPC selection rules.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional


# NPC role classifications for Crown/Crew mapping
_PATRON_ROLES = {"faction_leader", "noble", "scholar", "innkeeper", "priest", "guard"}
_LEADER_ROLES = {"criminal", "mercenary", "ranger", "barbarian", "monk", "healer"}
_EXCLUDED_ROLES = {"demon_lord", "deity", "pet", "construct"}

# Default terms for system-specific Crown/Crew labeling
_SYSTEM_TERMS: Dict[str, Dict[str, str]] = {
    "dnd5e": {
        "crown": "The Lords",
        "crew": "The Company",
        "neutral": "Wanderer",
        "campfire": "Long Rest",
        "region": "The Sword Coast",
    },
    "bitd": {
        "crown": "The Inspectors",
        "crew": "The Crew",
        "neutral": "Drifter",
        "campfire": "Downtime",
        "region": "Doskvol",
    },
    "sav": {
        "crown": "The Hegemony",
        "crew": "The Ship",
        "neutral": "Void-walker",
        "campfire": "Shore Leave",
        "region": "The Procyon Sector",
    },
    "bob": {
        "crown": "The Command",
        "crew": "The Legion",
        "neutral": "Straggler",
        "campfire": "Bivouac",
        "region": "The Western Front",
    },
    "stc": {
        "crown": "The Lighteyes",
        "crew": "The Bridgemen",
        "neutral": "Darkeyes",
        "campfire": "The Lull",
        "region": "The Shattered Plains",
    },
    "candela": {
        "crown": "The Fairelands Council",
        "crew": "The Circle",
        "neutral": "Unaffiliated",
        "campfire": "The Séance",
        "region": "Newfaire",
    },
    "cbrpnk": {
        "crown": "The Corporations",
        "crew": "The Runners",
        "neutral": "Ghost",
        "campfire": "Downlink",
        "region": "The Sprawl",
    },
    "burnwillow": {
        "crown": "The Garrison",
        "crew": "The Deserters",
        "neutral": "Drifter",
        "campfire": "Campfire",
        "region": "The Borderlands",
    },
}


class CampaignAdapter:
    """Builds a world_state dict for CrownAndCrewEngine from target campaign data.

    Usage:
        adapter = CampaignAdapter("dnd5e", module_path="vault_maps/modules/dragon_heist")
        world_state = adapter.build_world_state()
        engine = CrownAndCrewEngine(world_state=world_state)
    """

    def __init__(
        self,
        system_id: str,
        module_path: Optional[str] = None,
        config_root: str = "config",
        vault_root: str = "vault_maps/modules",
    ):
        self.system_id = system_id.lower()
        self.module_path = Path(module_path) if module_path else None
        self.config_root = Path(config_root)
        self.vault_root = Path(vault_root)

        # Loaded data
        self._npcs: List[dict] = []
        self._locations: dict = {}
        self._boss_names: set[str] = set()

    def build_world_state(self) -> Dict[str, Any]:
        """Build a complete world_state dict for the Crown engine.

        Loads NPC, location, and enemy data from the target system.
        Returns a dict consumable by CrownAndCrewEngine.__init__.
        """
        self._load_npcs()
        self._load_locations()
        self._load_boss_names()

        patrons = self._select_patrons()
        leaders = self._select_leaders()
        terms = self._generate_terms()

        # Build prompt pools from location data
        world_prompts = self._generate_world_prompts()
        morning_events = self._generate_morning_events()

        ws: Dict[str, Any] = {
            "terms": terms,
            "patron_pool": [p["name"] for p in patrons],
            "leader_pool": [l["name"] for l in leaders],
            "patron_data": patrons,
            "leader_data": leaders,
            "world_prompts": world_prompts,
            "morning_events": morning_events,
            "system_id": self.system_id,
        }

        if self.module_path:
            ws["module"] = self.module_path.name

        return ws

    # ── Data Loading ─────────────────────────────────────────────────

    def _load_npcs(self) -> None:
        """Load named NPCs from config/npcs/{system}.json."""
        npc_path = self.config_root / "npcs" / f"{self.system_id}.json"
        if npc_path.exists():
            try:
                data = json.loads(npc_path.read_text())
                self._npcs = data.get("named_npcs", [])
            except (json.JSONDecodeError, KeyError):
                self._npcs = []

    def _load_locations(self) -> None:
        """Load locations from config/locations/{system}.json."""
        loc_path = self.config_root / "locations" / f"{self.system_id}.json"
        if loc_path.exists():
            try:
                self._locations = json.loads(loc_path.read_text())
            except json.JSONDecodeError:
                self._locations = {}

    def _load_boss_names(self) -> None:
        """Extract boss/enemy names from the target module's zone files.

        Any NPC who appears as a boss in the module is excluded from
        Crown/Crew selection. Crew ≠ villain faction.
        """
        self._boss_names = set()
        if not self.module_path or not self.module_path.exists():
            return

        for zone_file in self.module_path.glob("*.json"):
            if zone_file.name == "module_manifest.json":
                continue
            try:
                data = json.loads(zone_file.read_text())
            except json.JSONDecodeError:
                continue

            rooms = data.get("rooms", data.get("locations", {}))
            for room in rooms.values():
                ch = room.get("content_hints", {})
                for enemy in ch.get("enemies", []):
                    if isinstance(enemy, dict):
                        name = enemy.get("name", "")
                        if enemy.get("is_boss") and name:
                            self._boss_names.add(name.lower())
                        # Also exclude high-CR enemies as potential villains
                        cr = enemy.get("cr", 0)
                        if isinstance(cr, (int, float)) and cr >= 10 and name:
                            self._boss_names.add(name.lower())

    # ── NPC Selection (#113) ─────────────────────────────────────────

    def _select_patrons(self, count: int = 4) -> List[dict]:
        """Select Crown Patron candidates from authority NPCs.

        Rules:
        - Roles: faction_leader, noble, scholar, innkeeper, priest, guard
        - Exclude: names that appear as bosses in the target module
        - Exclude: roles in _EXCLUDED_ROLES (demon_lord, deity, pet)
        """
        candidates = []
        for npc in self._npcs:
            role = npc.get("role", "").lower()
            name = npc.get("name", "")
            if role in _EXCLUDED_ROLES:
                continue
            if name.lower() in self._boss_names:
                continue
            if role in _PATRON_ROLES:
                candidates.append(npc)

        if len(candidates) < count:
            # Fall back to any non-excluded, non-boss NPC
            fallback = [
                n for n in self._npcs
                if n.get("role", "").lower() not in _EXCLUDED_ROLES
                and n.get("name", "").lower() not in self._boss_names
                and n not in candidates
            ]
            candidates.extend(fallback[:count - len(candidates)])

        random.shuffle(candidates)
        return candidates[:count]

    def _select_leaders(self, count: int = 4) -> List[dict]:
        """Select Crew Leader candidates from underdog/sympathetic NPCs.

        Rules:
        - Roles: criminal, mercenary, ranger, barbarian, monk, healer
        - Exclude: names that appear as bosses in the target module
        - Exclude: roles in _EXCLUDED_ROLES
        - Crew ≠ villain faction — no BBEG as Crew Leader
        """
        candidates = []
        for npc in self._npcs:
            role = npc.get("role", "").lower()
            name = npc.get("name", "")
            if role in _EXCLUDED_ROLES:
                continue
            if name.lower() in self._boss_names:
                continue
            if role in _LEADER_ROLES:
                candidates.append(npc)

        if len(candidates) < count:
            fallback = [
                n for n in self._npcs
                if n.get("role", "").lower() not in _EXCLUDED_ROLES
                and n.get("name", "").lower() not in self._boss_names
                and n not in candidates
                and n.get("role", "").lower() not in _PATRON_ROLES
            ]
            candidates.extend(fallback[:count - len(candidates)])

        random.shuffle(candidates)
        return candidates[:count]

    # ── Content Generation ───────────────────────────────────────────

    def _generate_terms(self) -> Dict[str, str]:
        """Generate Crown/Crew terminology for the target system."""
        terms = _SYSTEM_TERMS.get(self.system_id, {
            "crown": "The Authority",
            "crew": "The Outcasts",
            "neutral": "Drifter",
            "campfire": "Campfire",
            "region": "The Borderlands",
        })
        return dict(terms)

    def _generate_world_prompts(self, count: int = 15) -> List[str]:
        """Generate world/terrain prompts from location descriptions."""
        prompts = []

        # Pull from dungeons, settlements, and other location types
        for key in ("dungeons", "settlements", "waterdeep_wards",
                     "regions", "wilderness", "locations"):
            locs = self._locations.get(key, [])
            if isinstance(locs, list):
                for loc in locs:
                    if isinstance(loc, dict):
                        desc = loc.get("description", "")
                        name = loc.get("name", "")
                        if desc and name:
                            prompts.append(
                                f"The road passes near {name}. {desc[:150]}"
                            )

        if not prompts:
            region = _SYSTEM_TERMS.get(self.system_id, {}).get("region", "unknown lands")
            prompts = [
                f"The column moves through {region}. The horizon is empty.",
                f"Dust and silence. {region} offers no comfort today.",
                f"The trail cuts through {region}. Something watches from the ridge.",
            ]

        random.shuffle(prompts)
        return prompts[:count]

    def _generate_morning_events(self, count: int = 10) -> List[dict]:
        """Generate morning events from NPC and location data.

        Each event references actual NPCs/locations from the target system
        and includes 3 choices with tag/sway effects.
        """
        events = []

        # NPC-based events
        patrons = self._select_patrons(2)
        leaders = self._select_leaders(2)

        for npc in patrons[:1]:
            name = npc.get("name", "A figure of authority")
            events.append({
                "text": f"A rider bearing {name}'s seal approaches the camp at dawn. They carry a message — sealed, urgent, not meant for all eyes.",
                "bias": "crown",
                "tag": "GUILE",
                "choices": [
                    {"text": f"Open it and share with the group. No secrets on the march.", "tag": "DEFIANCE", "sway_effect": 1},
                    {"text": f"Read it privately. Knowledge from {name} is worth protecting.", "tag": "GUILE", "sway_effect": -1},
                    {"text": f"Burn it unread. You don't serve {name}'s interests.", "tag": "BLOOD", "sway_effect": 0},
                ],
            })

        for npc in leaders[:1]:
            name = npc.get("name", "A shadowy figure")
            events.append({
                "text": f"{name}'s contact appears at the edge of camp. They've brought supplies — but they want information in return.",
                "bias": "crew",
                "tag": "HEARTH",
                "choices": [
                    {"text": f"Trade. Information for supplies is a fair exchange.", "tag": "GUILE", "sway_effect": 0},
                    {"text": f"Take the supplies, give nothing. Survival first.", "tag": "BLOOD", "sway_effect": 1},
                    {"text": f"Refuse both. You don't deal with {name}'s people.", "tag": "SILENCE", "sway_effect": -1},
                ],
            })

        # Location-based events
        for key in ("settlements", "dungeons", "waterdeep_wards"):
            locs = self._locations.get(key, [])
            if isinstance(locs, list):
                for loc in locs[:2]:
                    if isinstance(loc, dict):
                        name = loc.get("name", "a nearby settlement")
                        events.append({
                            "text": f"Smoke rises from the direction of {name}. Could be campfires. Could be worse.",
                            "bias": "neutral",
                            "tag": "SILENCE",
                            "choices": [
                                {"text": f"Investigate {name}. Someone might need help.", "tag": "HEARTH", "sway_effect": 1},
                                {"text": f"Avoid {name}. Too many unknowns.", "tag": "SILENCE", "sway_effect": 0},
                                {"text": f"Send a scout. Know before you commit.", "tag": "GUILE", "sway_effect": -1},
                            ],
                        })

        # Generic fallback events if we don't have enough
        while len(events) < count:
            events.append({
                "text": "The road stretches on. A figure appears on the horizon — ally or threat, you can't tell yet.",
                "bias": "neutral",
                "tag": "SILENCE",
                "choices": [
                    {"text": "Approach openly. Show no fear.", "tag": "BLOOD", "sway_effect": 0},
                    {"text": "Watch and wait. Let them come to you.", "tag": "SILENCE", "sway_effect": 0},
                    {"text": "Prepare an ambush. Better safe than sorry.", "tag": "GUILE", "sway_effect": 0},
                ],
            })

        return events[:count]

    # ── Hybrid Mode ──────────────────────────────────────────────────

    # ── Legacy Report Handoff (#114) ───────────────────────────────────

    def translate_legacy(self, legacy_json: Dict[str, Any]) -> Dict[str, Any]:
        """WO-V114+V115: Translate a C&C Legacy Report into target system terms.

        Takes the structured legacy JSON from CrownAndCrewEngine.generate_legacy_json()
        and produces a system-specific translation with:
        - Faction standings for the target system
        - Mechanical benefits/consequences from sway powers
        - NPC relationship mappings
        - DM advisory notes

        Args:
            legacy_json: The structured legacy dict from the engine.

        Returns:
            Translated dict with system-specific mechanical suggestions.
        """
        system = self.system_id
        sway = legacy_json.get("sway", 0)
        dominant = legacy_json.get("dominant_tag", "SILENCE")
        alignment = legacy_json.get("alignment", "DRIFTER")
        title = legacy_json.get("title", "The Unknown")
        mirror = legacy_json.get("mirror", {})
        powers = legacy_json.get("powers_used", [])
        ending = legacy_json.get("ending", "uncertain_crossing") if "ending" in legacy_json else legacy_json.get("ending_id", "")

        translation: Dict[str, Any] = {
            "system": system,
            "title": title,
            "alignment": alignment,
            "sway": sway,
        }

        # System-specific faction mapping
        translation["factions"] = self._translate_factions(sway, system)

        # System-specific mechanical benefits from DNA
        translation["mechanical_benefits"] = self._translate_dna(dominant, system)

        # NPC relationships → system contacts
        translation["contacts"] = self._translate_relationships(legacy_json, system)

        # DM advisory notes
        translation["dm_notes"] = self._generate_dm_notes(legacy_json)

        # Power consequences
        translation["power_consequences"] = self._translate_powers(powers, system)

        return translation

    @staticmethod
    def _translate_factions(sway: int, system: str) -> Dict[str, Any]:
        """Map sway to system-specific faction standings."""
        _FACTION_MAP = {
            "dnd5e": {
                -3: {"faction": "Lords' Alliance", "rank": 3, "note": "Trusted operative"},
                -2: {"faction": "Lords' Alliance", "rank": 2, "note": "Known ally"},
                -1: {"faction": "Lords' Alliance", "rank": 1, "note": "On their radar"},
                0: {"faction": "None", "rank": 0, "note": "Unaffiliated"},
                1: {"faction": "Harpers", "rank": 1, "note": "Sympathizer"},
                2: {"faction": "Zhentarim (Doom Raiders)", "rank": 2, "note": "Trusted contact"},
                3: {"faction": "Zhentarim (Doom Raiders)", "rank": 3, "note": "Inner circle"},
            },
            "bitd": {
                -3: {"faction": "Inspectors", "rep": 3, "note": "Badge of honor"},
                -2: {"faction": "Inspectors", "rep": 2, "note": "Known associate"},
                0: {"faction": "None", "rep": 0, "note": "Ghost"},
                2: {"faction": "Crew", "rep": 2, "note": "Made member"},
                3: {"faction": "Crew", "rep": 3, "note": "Crew legend"},
            },
            "stc": {
                -3: {"faction": "Alethi Military", "rank": "Tenner", "note": "Command respects you"},
                -2: {"faction": "Lighteyes", "rank": "Associate", "note": "Doors open"},
                0: {"faction": "Darkeyes", "rank": "None", "note": "Invisible"},
                2: {"faction": "Bridge Four", "rank": "Bridgeman", "note": "One of us"},
                3: {"faction": "Bridge Four", "rank": "Squadleader", "note": "Leader of men"},
            },
        }

        system_map = _FACTION_MAP.get(system, {})
        # Find closest matching sway
        closest = min(system_map.keys(), key=lambda k: abs(k - sway)) if system_map else 0
        return system_map.get(closest, {"faction": "Unknown", "note": "No standing"})

    @staticmethod
    def _translate_dna(dominant: str, system: str) -> Dict[str, str]:
        """Map dominant DNA tag to system-specific mechanical benefit."""
        _DNA_MECHANICS = {
            "dnd5e": {
                "BLOOD": "Proficiency in Intimidation (if not already). Advantage on first attack roll per session.",
                "GUILE": "Proficiency in Deception (if not already). Advantage on first Persuasion check per session.",
                "HEARTH": "Proficiency in Medicine (if not already). Once per long rest, stabilize at range.",
                "SILENCE": "Proficiency in Stealth (if not already). Advantage on first Perception check per session.",
                "DEFIANCE": "Proficiency in Insight (if not already). Advantage on saves vs. Frightened.",
            },
            "bitd": {
                "BLOOD": "+1d on Command when using threats.",
                "GUILE": "+1d on Sway when lying.",
                "HEARTH": "+1d on Consort with allies.",
                "SILENCE": "+1d on Prowl in shadows.",
                "DEFIANCE": "+1d on Attune when resisting.",
            },
            "stc": {
                "BLOOD": "Bonus to Might checks in first combat of session.",
                "GUILE": "Bonus to Cunning checks in social encounters.",
                "HEARTH": "Bonus to Presence when protecting allies.",
                "SILENCE": "Bonus to Awareness when observing.",
                "DEFIANCE": "Bonus to Resolve when defying authority.",
            },
        }

        system_map = _DNA_MECHANICS.get(system, {})
        return {"dominant_tag": dominant, "benefit": system_map.get(dominant, "No mechanical benefit defined.")}

    @staticmethod
    def _translate_relationships(legacy: dict, system: str) -> List[dict]:
        """Map patron/leader relationships to system contacts."""
        contacts = []
        patron = legacy.get("patron", "")
        patron_rel = legacy.get("patron_relationship", "")
        leader = legacy.get("leader", "")
        leader_rel = legacy.get("leader_relationship", "")

        if patron:
            attitude = "friendly" if "allied" in patron_rel else "hostile" if "hostile" in patron_rel else "neutral"
            contacts.append({"name": patron, "role": "Authority Figure", "attitude": attitude})
        if leader:
            attitude = "friendly" if "trust" in leader_rel else "hostile" if "fury" in leader_rel else "neutral"
            contacts.append({"name": leader, "role": "Underworld Contact", "attitude": attitude})

        return contacts

    @staticmethod
    def _generate_dm_notes(legacy: dict) -> List[str]:
        """Generate advisory DM notes from the legacy data."""
        notes = []

        mirror = legacy.get("mirror", {})
        if mirror.get("choice") == "hide":
            notes.append(
                f"SECRET: The player hid the Leader's {mirror.get('sin', 'transgression')}. "
                f"This is leverage — for the Leader, for enemies, or for dramatic revelation."
            )
        elif mirror.get("choice") == "expose":
            notes.append(
                f"FACTION RIFT: The player exposed the Leader's {mirror.get('sin', 'transgression')}. "
                f"The Crew may be fractured. Former allies could become enemies."
            )

        ending = legacy.get("ending", "")
        if ending == "captured":
            notes.append(
                "OPENING SCENE SUGGESTION: The campaign opens with the player in custody. "
                "The authorities offer a deal — a dangerous mission in exchange for freedom."
            )
        elif ending == "abandoned":
            notes.append(
                "OPENING SCENE SUGGESTION: The player starts alone, no faction ties. "
                "Their first challenge is earning trust from anyone willing to work with them."
            )
        elif ending == "martyrs_march":
            notes.append(
                "FACTION DYNAMICS: The player leads a splinter group. "
                "The original Leader is out there with the rest. Civil war is possible."
            )

        debts = legacy.get("debts_and_secrets", [])
        for d in debts[:3]:
            notes.append(f"HOOK: {d.get('text', '')}")

        return notes

    @staticmethod
    def _translate_powers(powers: list, system: str) -> List[dict]:
        """Map used C&C powers to campaign consequences."""
        consequences = []
        if "royal_decree" in powers:
            consequences.append({
                "power": "Royal Decree",
                "consequence": "The Crew faction remembers this act of authority. -1 to initial reputation with criminal/underworld NPCs.",
            })
        if "safe_passage" in powers:
            consequences.append({
                "power": "Safe Passage",
                "consequence": "A specific patrol/guard unit recognizes the player. They may demand return favors.",
            })
        if "leaders_confidence" in powers:
            consequences.append({
                "power": "Leader's Confidence",
                "consequence": "The player knows the Leader's secret agenda. This is a plot hook the DM can activate at any time.",
            })
        return consequences

    def overlay_on_module(self, campaign_json: Dict[str, Any]) -> Dict[str, Any]:
        """Hybrid mode: overlay target system NPCs/terms onto an authored module.

        Takes an existing C&C campaign.json and replaces patron/leader
        names and terms with target-system equivalents while keeping
        the hand-written prompts and dilemmas.

        Args:
            campaign_json: The authored campaign.json data.

        Returns:
            Modified campaign_json with system-specific overlays.
        """
        self._load_npcs()
        self._load_boss_names()

        result = dict(campaign_json)

        # Replace terms
        result["terms"] = self._generate_terms()

        # Replace patron/leader pools
        patrons = self._select_patrons(4)
        leaders = self._select_leaders(4)
        if patrons:
            result["patron_list"] = [p["name"] for p in patrons]
        if leaders:
            result["leader_list"] = [l["name"] for l in leaders]

        return result
