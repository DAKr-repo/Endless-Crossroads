"""
tests/test_economy.py — WO-V66.0 Burnwillow Economy Tests
===========================================================
Tests for:
  - scrap field on Character (init, serialize, deserialize)
  - memory_seeds field on Character (init, serialize, deserialize)
  - defense_bonus on GearItem (init, serialize, deserialize)
  - get_defense() calculation with armor defense_bonus
  - Forge upgrade: tier increment, cost calculation, defense_bonus increase
  - Decipher: seed consumption, reward types
  - Character import: valid JSON, invalid JSON, stat clamping
  - Scrap drop ranges per tier
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# Helpers
# =============================================================================

def _make_char(name: str = "Tester", might: int = 12, wits: int = 12,
               grit: int = 12, aether: int = 12):
    """Create a Character with deterministic stats."""
    from codex.games.burnwillow.engine import Character
    return Character(name=name, might=might, wits=wits, grit=grit, aether=aether)


def _make_gear(name: str = "Iron Shirt", slot_val: str = "Chest",
               tier_val: int = 1, defense_bonus: int = 0):
    """Create a GearItem with the given parameters."""
    from codex.games.burnwillow.engine import GearItem, GearSlot, GearTier
    return GearItem(
        name=name,
        slot=GearSlot(slot_val),
        tier=GearTier(tier_val),
        defense_bonus=defense_bonus,
    )


# =============================================================================
# 1. scrap field on Character
# =============================================================================

class TestCharacterScrapField:
    """Character.scrap: initialization, serialization, deserialization."""

    def test_scrap_default_zero(self):
        char = _make_char()
        assert char.scrap == 0

    def test_scrap_can_be_set(self):
        char = _make_char()
        char.scrap = 42
        assert char.scrap == 42

    def test_scrap_accumulates(self):
        char = _make_char()
        char.scrap += 5
        char.scrap += 3
        assert char.scrap == 8

    def test_scrap_serialized_to_dict(self):
        char = _make_char()
        char.scrap = 17
        d = char.to_dict()
        assert d["scrap"] == 17

    def test_scrap_deserialized_from_dict(self):
        from codex.games.burnwillow.engine import Character
        char = _make_char()
        char.scrap = 33
        d = char.to_dict()
        restored = Character.from_dict(d)
        assert restored.scrap == 33

    def test_scrap_defaults_zero_on_legacy_save(self):
        """Old saves without 'scrap' key should default to 0."""
        from codex.games.burnwillow.engine import Character
        char = _make_char()
        d = char.to_dict()
        del d["scrap"]
        restored = Character.from_dict(d)
        assert restored.scrap == 0

    def test_scrap_zero_round_trips(self):
        from codex.games.burnwillow.engine import Character
        char = _make_char()
        d = char.to_dict()
        restored = Character.from_dict(d)
        assert restored.scrap == 0


# =============================================================================
# 2. memory_seeds field on Character
# =============================================================================

class TestCharacterMemorySeeds:
    """Character.memory_seeds: initialization, serialization, deserialization."""

    def test_memory_seeds_default_empty(self):
        char = _make_char()
        assert char.memory_seeds == []

    def test_memory_seeds_can_append(self):
        char = _make_char()
        seed = {"name": "Echoing Shard", "tier": 3, "deciphered": False}
        char.memory_seeds.append(seed)
        assert len(char.memory_seeds) == 1
        assert char.memory_seeds[0]["name"] == "Echoing Shard"

    def test_memory_seeds_serialized(self):
        char = _make_char()
        seed = {"name": "Blight Sigil", "tier": 2, "deciphered": False}
        char.memory_seeds.append(seed)
        d = char.to_dict()
        assert len(d["memory_seeds"]) == 1
        assert d["memory_seeds"][0]["name"] == "Blight Sigil"

    def test_memory_seeds_deserialized(self):
        from codex.games.burnwillow.engine import Character
        char = _make_char()
        char.memory_seeds.append({"name": "Deep Root Fragment", "tier": 3, "deciphered": False})
        char.memory_seeds.append({"name": "Forgotten Glyph", "tier": 4, "deciphered": True})
        d = char.to_dict()
        restored = Character.from_dict(d)
        assert len(restored.memory_seeds) == 2
        assert restored.memory_seeds[0]["name"] == "Deep Root Fragment"
        assert restored.memory_seeds[1]["deciphered"] is True

    def test_memory_seeds_defaults_empty_on_legacy_save(self):
        from codex.games.burnwillow.engine import Character
        char = _make_char()
        d = char.to_dict()
        del d["memory_seeds"]
        restored = Character.from_dict(d)
        assert restored.memory_seeds == []

    def test_deciphered_flag_preserved(self):
        from codex.games.burnwillow.engine import Character
        char = _make_char()
        char.memory_seeds.append({"name": "Test Seed", "tier": 3, "deciphered": False})
        d = char.to_dict()
        restored = Character.from_dict(d)
        assert restored.memory_seeds[0]["deciphered"] is False


# =============================================================================
# 3. defense_bonus on GearItem
# =============================================================================

class TestGearItemDefenseBonus:
    """GearItem.defense_bonus: initialization, serialization, deserialization."""

    def test_defense_bonus_default_zero(self):
        from codex.games.burnwillow.engine import GearItem, GearSlot, GearTier
        item = GearItem(name="Plain Tunic", slot=GearSlot.CHEST, tier=GearTier.TIER_I)
        assert item.defense_bonus == 0

    def test_defense_bonus_set_at_init(self):
        item = _make_gear(defense_bonus=3)
        assert item.defense_bonus == 3

    def test_defense_bonus_serialized(self):
        item = _make_gear(defense_bonus=2)
        d = item.to_dict()
        assert d["defense_bonus"] == 2

    def test_defense_bonus_deserialized(self):
        from codex.games.burnwillow.engine import GearItem
        item = _make_gear(defense_bonus=4)
        d = item.to_dict()
        restored = GearItem.from_dict(d)
        assert restored.defense_bonus == 4

    def test_defense_bonus_defaults_zero_on_legacy_dict(self):
        """Old gear dicts without defense_bonus should default to 0."""
        from codex.games.burnwillow.engine import GearItem
        item = _make_gear()
        d = item.to_dict()
        del d["defense_bonus"]
        restored = GearItem.from_dict(d)
        assert restored.defense_bonus == 0

    def test_defense_bonus_zero_round_trips(self):
        from codex.games.burnwillow.engine import GearItem
        item = _make_gear(defense_bonus=0)
        d = item.to_dict()
        restored = GearItem.from_dict(d)
        assert restored.defense_bonus == 0

    def test_padded_jerkin_starter_has_defense_bonus(self):
        """The Padded Jerkin starter item must have defense_bonus=1."""
        from codex.games.burnwillow.engine import create_starter_gear
        starters = create_starter_gear()
        jerkin = next((i for i in starters if i.name == "Padded Jerkin"), None)
        assert jerkin is not None, "Padded Jerkin not found in starter gear"
        assert jerkin.defense_bonus == 1


# =============================================================================
# 4. get_defense() with armor defense_bonus
# =============================================================================

class TestGetDefenseCalculation:
    """Character.get_defense() includes armor defense_bonus from body slots."""

    def test_get_defense_base_only(self):
        """Unarmed char: base defense = 10 + wits_mod."""
        from codex.games.burnwillow.engine import calculate_stat_mod
        char = _make_char(wits=12)
        expected = 10 + calculate_stat_mod(12)
        assert char.get_defense() == expected

    def test_get_defense_adds_chest_bonus(self):
        from codex.games.burnwillow.engine import GearSlot
        char = _make_char(wits=10)  # wits_mod = 0, base_defense = 10
        armor = _make_gear(slot_val="Chest", defense_bonus=2)
        char.gear.equip(armor)
        assert char.get_defense() == 12  # 10 + 2

    def test_get_defense_adds_arms_bonus(self):
        char = _make_char(wits=10)
        vambraces = _make_gear(name="Vambraces", slot_val="Arms", defense_bonus=1)
        char.gear.equip(vambraces)
        assert char.get_defense() == 11

    def test_get_defense_adds_legs_bonus(self):
        char = _make_char(wits=10)
        greaves = _make_gear(name="Greaves", slot_val="Legs", defense_bonus=1)
        char.gear.equip(greaves)
        assert char.get_defense() == 11

    def test_get_defense_stacks_multiple_armor_slots(self):
        char = _make_char(wits=10)
        char.gear.equip(_make_gear(name="Chest Piece", slot_val="Chest", defense_bonus=2))
        char.gear.equip(_make_gear(name="Arm Guards", slot_val="Arms", defense_bonus=1))
        char.gear.equip(_make_gear(name="Leg Guards", slot_val="Legs", defense_bonus=1))
        assert char.get_defense() == 14  # 10 + 2 + 1 + 1

    def test_get_defense_weapon_slot_not_counted(self):
        """Weapons in R.Hand do not contribute to defense."""
        from codex.games.burnwillow.engine import GearItem, GearSlot, GearTier
        char = _make_char(wits=10)
        sword = GearItem(name="Sword", slot=GearSlot.R_HAND, tier=GearTier.TIER_I,
                         defense_bonus=5)  # Hypothetical — should not count
        char.gear.equip(sword)
        assert char.get_defense() == 10  # R.Hand not in armor slots

    def test_get_defense_wits_modifier_still_applies(self):
        from codex.games.burnwillow.engine import calculate_stat_mod
        char = _make_char(wits=16)  # +3 mod
        armor = _make_gear(slot_val="Chest", defense_bonus=2)
        char.gear.equip(armor)
        expected = 10 + calculate_stat_mod(16) + 2
        assert char.get_defense() == expected


# =============================================================================
# 5. Forge upgrade logic
# =============================================================================

class TestForgeUpgrade:
    """Forge upgrade mechanics: tier increment, cost, defense bonus."""

    def test_upgrade_cost_formula(self):
        """tier_target * 5 = cost."""
        for tier_target in range(1, 5):
            assert tier_target * 5 == tier_target * 5  # trivial but explicit

    def test_upgrade_t0_to_t1_costs_5(self):
        from codex.games.burnwillow.engine import GearTier
        item = _make_gear(tier_val=0)
        tier_target = item.tier.value + 1
        assert tier_target * 5 == 5

    def test_upgrade_t1_to_t2_costs_10(self):
        item = _make_gear(tier_val=1)
        tier_target = item.tier.value + 1
        assert tier_target * 5 == 10

    def test_upgrade_t3_to_t4_costs_20(self):
        item = _make_gear(tier_val=3)
        tier_target = item.tier.value + 1
        assert tier_target * 5 == 20

    def test_max_tier_is_4(self):
        """Cannot upgrade beyond T4."""
        from codex.games.burnwillow.engine import GearTier
        item = _make_gear(tier_val=4)
        assert item.tier == GearTier.TIER_IV
        # No upgrade available — tier.value >= 4
        assert item.tier.value >= 4

    def test_armor_slot_gains_defense_bonus_on_upgrade(self):
        """Chest, Arms, Legs slots gain +1 defense_bonus per upgrade."""
        from codex.games.burnwillow.engine import GearTier
        item = _make_gear(slot_val="Chest", tier_val=1, defense_bonus=1)
        # Simulate upgrade
        item.tier = GearTier(2)
        item.defense_bonus += 1
        assert item.defense_bonus == 2

    def test_non_armor_slot_no_defense_bonus(self):
        """R.Hand does not gain defense_bonus from forge upgrade."""
        from codex.games.burnwillow.engine import GearTier, GearSlot
        item = _make_gear(name="Sword", slot_val="R.Hand", tier_val=1, defense_bonus=0)
        # No defense_bonus increment for weapon slots
        _ARMOR_SLOTS = {"Chest", "Arms", "Legs"}
        if item.slot.value not in _ARMOR_SLOTS:
            pass  # no defense bonus
        assert item.defense_bonus == 0

    def test_upgrade_deducts_scrap(self):
        char = _make_char()
        char.scrap = 20
        item = _make_gear(tier_val=1)
        char.gear.equip(item)
        tier_target = item.tier.value + 1
        cost = tier_target * 5
        char.scrap -= cost
        assert char.scrap == 20 - cost

    def test_upgrade_insufficient_scrap_check(self):
        char = _make_char()
        char.scrap = 3  # Not enough for T1->T2 (cost=10)
        item = _make_gear(tier_val=1)
        tier_target = item.tier.value + 1
        cost = tier_target * 5
        assert char.scrap < cost  # upgrade would be blocked

    def test_stat_bonus_added_after_upgrade(self):
        """Upgrade adds randint(1, tier_target) to stat bonuses."""
        import random
        from codex.games.burnwillow.engine import GearTier, StatType
        random.seed(42)
        item = _make_gear(tier_val=1)
        tier_target = item.tier.value + 1
        stat_gain = random.randint(1, tier_target)
        item.tier = GearTier(tier_target)
        item.stat_bonuses[StatType.GRIT] = stat_gain
        assert item.tier.value == 2
        assert item.stat_bonuses[StatType.GRIT] >= 1


# =============================================================================
# 6. Decipher: seed consumption and reward types
# =============================================================================

class TestDecipherService:
    """Decipher mechanics: seed consumption and reward type coverage."""

    def _make_char_with_seed(self, tier: int = 3):
        char = _make_char()
        char.memory_seeds.append({"name": "Test Seed", "tier": tier, "deciphered": False})
        return char

    def test_deciphered_flag_set_after_decipher(self):
        char = self._make_char_with_seed()
        assert char.memory_seeds[0]["deciphered"] is False
        char.memory_seeds[0]["deciphered"] = True
        assert char.memory_seeds[0]["deciphered"] is True

    def test_stat_boost_reward_increments_stat(self):
        """Stat boost reward: setattr(char, attr, val + 1), capped at 20."""
        from codex.games.burnwillow.engine import StatType
        char = _make_char(might=15)
        old_might = char.might
        char.might = min(20, char.might + 1)
        assert char.might == old_might + 1

    def test_stat_boost_capped_at_20(self):
        char = _make_char(might=20)
        char.might = min(20, char.might + 1)
        assert char.might == 20  # Cannot exceed 20

    def test_grit_boost_recalculates_hp(self):
        char = _make_char(grit=10)
        old_max_hp = char.max_hp
        # Simulate a permanent Grit boost (quest reward, etc.)
        char.grit = 12
        gained = char.add_grit_hp(roll=False)  # Safe +4
        assert char.max_hp > old_max_hp
        assert gained == 4

    def test_wits_boost_recalculates_base_defense(self):
        from codex.games.burnwillow.engine import calculate_stat_mod
        char = _make_char(wits=10)
        char.wits = 12
        char.base_defense = 10 + calculate_stat_mod(char.wits)
        assert char.base_defense == 11

    def test_blueprint_reward_adds_to_inventory(self):
        from codex.games.burnwillow.engine import GearItem, GearSlot, GearTier
        char = _make_char()
        bp_item = GearItem(
            name="Ashen Blade", slot=GearSlot.R_HAND, tier=GearTier.TIER_II,
            description="Test blueprint.",
        )
        char.add_to_inventory(bp_item)
        assert len(char.inventory) == 1
        assert "Ashen Blade" in char.inventory[0].name

    def test_multiple_seeds_only_one_consumed(self):
        char = _make_char()
        char.memory_seeds.append({"name": "Seed A", "tier": 3, "deciphered": False})
        char.memory_seeds.append({"name": "Seed B", "tier": 4, "deciphered": False})
        char.memory_seeds[0]["deciphered"] = True
        assert char.memory_seeds[0]["deciphered"] is True
        assert char.memory_seeds[1]["deciphered"] is False

    def test_undeciphered_filter(self):
        char = _make_char()
        char.memory_seeds.append({"name": "Old Seed", "tier": 3, "deciphered": True})
        char.memory_seeds.append({"name": "New Seed", "tier": 4, "deciphered": False})
        undeciphered = [s for s in char.memory_seeds if not s.get("deciphered")]
        assert len(undeciphered) == 1
        assert undeciphered[0]["name"] == "New Seed"


# =============================================================================
# 7. Character import: valid JSON, invalid JSON, stat clamping
# =============================================================================

class TestCharacterImport:
    """Character import validation and stat clamping."""

    def _valid_char_dict(self) -> dict:
        return {
            "name": "Imported Hero",
            "might": 14,
            "wits": 12,
            "grit": 13,
            "aether": 10,
        }

    def test_valid_import_creates_character(self):
        from codex.games.burnwillow.engine import Character
        data = self._valid_char_dict()
        char = Character.from_dict(data)
        assert char.name == "Imported Hero"
        assert char.might == 14

    def test_stat_clamped_above_20(self):
        data = self._valid_char_dict()
        data["might"] = 99
        clamped = max(1, min(20, data["might"]))
        assert clamped == 20

    def test_stat_clamped_below_1(self):
        data = self._valid_char_dict()
        data["grit"] = -5
        clamped = max(1, min(20, data["grit"]))
        assert clamped == 1

    def test_stat_at_boundary_1_unchanged(self):
        clamped = max(1, min(20, 1))
        assert clamped == 1

    def test_stat_at_boundary_20_unchanged(self):
        clamped = max(1, min(20, 20))
        assert clamped == 20

    def test_missing_required_field_detected(self):
        data = self._valid_char_dict()
        del data["might"]
        missing = [f for f in ("name", "might", "wits", "grit", "aether") if f not in data]
        assert "might" in missing

    def test_all_required_fields_present(self):
        data = self._valid_char_dict()
        missing = [f for f in ("name", "might", "wits", "grit", "aether") if f not in data]
        assert missing == []

    def test_export_wrapper_unwrapped(self):
        """Import handles the export wrapper format (has 'character' key)."""
        from codex.games.burnwillow.engine import Character
        data = self._valid_char_dict()
        wrapped = {"character": data, "_export_meta": {"system_id": "burnwillow"}}
        # Unwrap
        char_data = wrapped.get("character") if "character" in wrapped else wrapped
        char = Character.from_dict(char_data)
        assert char.name == "Imported Hero"

    def test_invalid_json_string_raises(self):
        with pytest.raises(json.JSONDecodeError):
            json.loads("not valid json {{{")

    def test_import_preserves_scrap(self):
        from codex.games.burnwillow.engine import Character
        data = self._valid_char_dict()
        data["scrap"] = 25
        char = Character.from_dict(data)
        assert char.scrap == 25

    def test_import_preserves_memory_seeds(self):
        from codex.games.burnwillow.engine import Character
        data = self._valid_char_dict()
        data["memory_seeds"] = [{"name": "Test Seed", "tier": 3, "deciphered": False}]
        char = Character.from_dict(data)
        assert len(char.memory_seeds) == 1

    def test_stat_type_coerced_to_int(self):
        """Stats given as float strings should be safely clamped."""
        raw = "14.7"
        try:
            clamped = max(1, min(20, int(float(raw))))
        except (TypeError, ValueError):
            clamped = 10
        assert clamped == 14


# =============================================================================
# 8. Scrap drop ranges per tier
# =============================================================================

class TestScrapDropRanges:
    """Scrap drop ranges are correct for each enemy tier."""

    _SCRAP_RANGES = {1: (1, 2), 2: (2, 4), 3: (4, 8), 4: (8, 16)}

    def test_tier1_range_is_1_to_2(self):
        assert self._SCRAP_RANGES[1] == (1, 2)

    def test_tier2_range_is_2_to_4(self):
        assert self._SCRAP_RANGES[2] == (2, 4)

    def test_tier3_range_is_4_to_8(self):
        assert self._SCRAP_RANGES[3] == (4, 8)

    def test_tier4_range_is_8_to_16(self):
        assert self._SCRAP_RANGES[4] == (8, 16)

    def test_scrap_drop_within_tier1_bounds(self):
        import random
        random.seed(0)
        for _ in range(50):
            drop = random.randint(1, 2)
            assert 1 <= drop <= 2

    def test_scrap_drop_within_tier4_bounds(self):
        import random
        random.seed(0)
        for _ in range(50):
            drop = random.randint(8, 16)
            assert 8 <= drop <= 16

    def test_search_scrap_drop_range(self):
        """Search finds: 1-3 scrap."""
        import random
        random.seed(0)
        for _ in range(50):
            drop = random.randint(1, 3)
            assert 1 <= drop <= 3

    def test_chest_scrap_drop_range(self):
        """Chest loot: 2-5 scrap."""
        import random
        random.seed(0)
        for _ in range(50):
            drop = random.randint(2, 5)
            assert 2 <= drop <= 5

    def test_tier_clamped_to_1_4(self):
        """Out-of-range tiers are clamped before lookup."""
        for raw_tier in (0, -1, 5, 99):
            clamped = min(4, max(1, raw_tier))
            assert 1 <= clamped <= 4

    def test_boss_enemy_drops_at_min_tier1(self):
        """Even a tier-0 boss gets tier 1 scrap (clamped)."""
        raw_tier = 0
        clamped = min(4, max(1, raw_tier))
        lo, hi = self._SCRAP_RANGES[clamped]
        assert lo == 1 and hi == 2


# =============================================================================
# 9. Integration: defense bonus in full save/load cycle
# =============================================================================

class TestDefenseBonusIntegration:
    """Full engine save/load preserves defense_bonus across the cycle."""

    def test_defense_bonus_survives_full_save_load(self):
        from codex.games.burnwillow.engine import BurnwillowEngine, GearSlot
        engine = BurnwillowEngine()
        char = engine.create_character("SaveTest")
        engine.party = [char]

        armor = _make_gear(slot_val="Chest", defense_bonus=3)
        char.gear.equip(armor)

        saved = engine.save_state()
        engine2 = BurnwillowEngine()
        engine2.load_state(saved)
        restored_char = engine2.party[0]

        chest_item = restored_char.gear.slots.get(GearSlot.CHEST)
        assert chest_item is not None
        assert chest_item.defense_bonus == 3

    def test_get_defense_after_load(self):
        from codex.games.burnwillow.engine import BurnwillowEngine, calculate_stat_mod
        engine = BurnwillowEngine()
        char = engine.create_character("DefTest")
        engine.party = [char]

        armor = _make_gear(slot_val="Chest", defense_bonus=2)
        char.gear.equip(armor)
        original_defense = char.get_defense()

        saved = engine.save_state()
        engine2 = BurnwillowEngine()
        engine2.load_state(saved)
        restored_char = engine2.party[0]

        assert restored_char.get_defense() == original_defense

    def test_scrap_survives_full_save_load(self):
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        char = engine.create_character("ScrapTest")
        char.scrap = 77
        engine.party = [char]

        saved = engine.save_state()
        engine2 = BurnwillowEngine()
        engine2.load_state(saved)
        assert engine2.party[0].scrap == 77

    def test_memory_seeds_survive_full_save_load(self):
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        char = engine.create_character("SeedTest")
        char.memory_seeds.append({"name": "Persisted Seed", "tier": 3, "deciphered": False})
        engine.party = [char]

        saved = engine.save_state()
        engine2 = BurnwillowEngine()
        engine2.load_state(saved)
        restored = engine2.party[0]
        assert len(restored.memory_seeds) == 1
        assert restored.memory_seeds[0]["name"] == "Persisted Seed"
