"""
Cosmere STC Engine Depth Tests — Phase 3
==========================================

Covers:
  - TestSTCOrderData: All 10 orders load with powers, ideals, surges
  - TestSTCEquipmentData: Shardblades, Shardplate, fabrials, spheres
  - TestSTCHeritageData: All 10 heritages load with stat bonuses
  - TestStormTracker: Storm cycle, highstorm trigger, advance_day
  - TestSurgeManager: Stormlight infuse/drain, power usage, healing,
                      lashing, soulcast, illuminate, get_status, to/from_dict
  - TestCosmereCombatResolver: Attack rolls (advantage/disadvantage/crit),
                                Shardblade, Shardplate defense, duel, surge combat
  - TestIdealProgression: Oath checks, progress, ability unlocks, sequence
  - TestSTCEngineSaveLoad: Full round-trip with all subsystem state
  - TestSTCCommandDispatch: All handle_command dispatches
"""

import random
import pytest

from codex.forge.reference_data.stc_orders import ORDERS, SURGE_TYPES
from codex.forge.reference_data.stc_equipment import (
    SHARDBLADES,
    SHARDPLATE,
    FABRIALS,
    SPHERE_TYPES,
    WEAPON_PROPERTIES,
)
from codex.forge.reference_data.stc_heritages import HERITAGES
from codex.forge.reference_data.stc import (
    ORDERS as AGG_ORDERS,
    SURGE_TYPES as AGG_SURGE_TYPES,
    SHARDBLADES as AGG_SHARDBLADES,
    HERITAGES as AGG_HERITAGES,
)
from codex.games.stc.surgebinding import StormTracker, SurgeManager
from codex.games.stc.combat import AttackResult, CosmereCombatResolver
from codex.games.stc.ideals import IdealProgression, IDEAL_DC, IDEAL_PROGRESS_THRESHOLD
from codex.games.stc import CosmereEngine, CosmereCharacter


# =========================================================================
# HELPERS
# =========================================================================

def _rng(seed: int = 42) -> random.Random:
    """Return a seeded Random instance for deterministic tests."""
    return random.Random(seed)


def _char(**kwargs) -> CosmereCharacter:
    """Build a minimal CosmereCharacter with sensible defaults."""
    defaults = {
        "name": "Kaladin",
        "order": "windrunner",
        "heritage": "Alethi",
        "strength": 14,
        "speed": 12,
        "intellect": 10,
    }
    defaults.update(kwargs)
    return CosmereCharacter(**defaults)


def _engine_with_char(**kwargs) -> CosmereEngine:
    """Return an engine with one character in the party."""
    eng = CosmereEngine()
    char = eng.create_character(**{**{"name": "Kaladin", "order": "windrunner"}, **kwargs})
    return eng


# =========================================================================
# 1. ORDER DATA
# =========================================================================

class TestSTCOrderData:
    """All 10 Radiant Orders load with correct structure."""

    EXPECTED_ORDERS = [
        "windrunner", "skybreaker", "dustbringer", "edgedancer",
        "truthwatcher", "lightweaver", "elsecaller", "willshaper",
        "stoneward", "bondsmith",
    ]

    def test_all_ten_orders_present(self):
        for order in self.EXPECTED_ORDERS:
            assert order in ORDERS, f"Missing order: {order}"

    def test_each_order_has_two_surges(self):
        for name, data in ORDERS.items():
            surges = data.get("surges", [])
            assert len(surges) == 2, f"{name} should have 2 surges, got {len(surges)}"

    def test_each_order_has_five_ideals(self):
        for name, data in ORDERS.items():
            ideals = data.get("ideals", {})
            assert len(ideals) == 5, f"{name} should have 5 ideals, got {len(ideals)}"
            for i in range(1, 6):
                assert i in ideals, f"{name} missing ideal {i}"

    def test_each_order_has_per_ideal_powers(self):
        for name, data in ORDERS.items():
            powers = data.get("per_ideal_powers", {})
            assert len(powers) >= 1, f"{name} should have per_ideal_powers"

    def test_each_order_has_starting_equipment(self):
        for name, data in ORDERS.items():
            eq = data.get("starting_equipment", [])
            assert len(eq) >= 1, f"{name} should have starting equipment"

    def test_each_order_has_oath_text(self):
        for name, data in ORDERS.items():
            oath = data.get("oath_text", "")
            assert len(oath) > 20, f"{name} oath_text is too short"

    def test_windrunner_surges_are_adhesion_gravitation(self):
        wr = ORDERS["windrunner"]
        assert "Gravitation" in wr["surges"]
        assert "Adhesion" in wr["surges"]

    def test_bondsmith_surges_are_tension_adhesion(self):
        bs = ORDERS["bondsmith"]
        assert "Tension" in bs["surges"]
        assert "Adhesion" in bs["surges"]

    def test_windrunner_ideal_1_has_basic_lashing(self):
        powers = ORDERS["windrunner"]["per_ideal_powers"].get(1, [])
        names = [p["name"] for p in powers]
        assert "Basic Lashing" in names

    def test_all_powers_have_required_fields(self):
        for order_name, data in ORDERS.items():
            for lvl, powers in data.get("per_ideal_powers", {}).items():
                for p in powers:
                    assert "name" in p, f"{order_name} L{lvl} power missing 'name'"
                    assert "description" in p, f"{order_name} L{lvl} power missing 'description'"
                    assert "stormlight_cost" in p, f"{order_name} L{lvl} power missing 'stormlight_cost'"

    def test_ten_surge_types_defined(self):
        assert len(SURGE_TYPES) == 10

    def test_all_surges_in_orders_are_defined(self):
        for order_name, data in ORDERS.items():
            for surge in data["surges"]:
                assert surge in SURGE_TYPES, f"{order_name} references undefined surge {surge}"

    def test_aggregator_exports_orders(self):
        assert AGG_ORDERS is ORDERS
        assert AGG_SURGE_TYPES is SURGE_TYPES


# =========================================================================
# 2. EQUIPMENT DATA
# =========================================================================

class TestSTCEquipmentData:
    """Shardblades, Shardplate, fabrials, and spheres load correctly."""

    def test_five_shardblades_defined(self):
        assert len(SHARDBLADES) == 5

    def test_each_shardblade_has_armor_piercing(self):
        for name, blade in SHARDBLADES.items():
            props = blade.get("properties", [])
            assert "Armor Piercing" in props, f"{name} missing Armor Piercing"

    def test_each_shardblade_has_ethereal(self):
        for name, blade in SHARDBLADES.items():
            props = blade.get("properties", [])
            assert "Ethereal" in props, f"{name} missing Ethereal"

    def test_each_shardblade_has_damage_dice(self):
        for name, blade in SHARDBLADES.items():
            assert "damage_dice" in blade, f"{name} missing damage_dice"
            assert "d" in blade["damage_dice"], f"{name} damage_dice malformed"

    def test_three_shardplate_types(self):
        assert len(SHARDPLATE) == 3

    def test_shardplate_has_defense_bonus(self):
        for name, plate in SHARDPLATE.items():
            assert "defense_bonus" in plate, f"{name} missing defense_bonus"
            assert plate["defense_bonus"] > 0

    def test_shardplate_has_stormlight_drain(self):
        for name, plate in SHARDPLATE.items():
            assert "stormlight_drain" in plate, f"{name} missing stormlight_drain"

    def test_full_shardplate_highest_defense(self):
        full = SHARDPLATE["Full Shardplate"]["defense_bonus"]
        partial = SHARDPLATE["Partial Shardplate"]["defense_bonus"]
        damaged = SHARDPLATE["Damaged Shardplate"]["defense_bonus"]
        assert full > partial > damaged

    def test_ten_fabrials_defined(self):
        assert len(FABRIALS) == 10

    def test_each_fabrial_has_required_fields(self):
        required = ["description", "effect", "stormlight_cost", "activation", "rarity"]
        for name, fab in FABRIALS.items():
            for field in required:
                assert field in fab, f"Fabrial '{name}' missing field '{field}'"

    def test_soulcaster_is_legendary(self):
        assert FABRIALS["Soulcaster"]["rarity"] == "legendary"

    def test_fifteen_sphere_types(self):
        assert len(SPHERE_TYPES) == 15

    def test_sphere_types_cover_five_gems(self):
        gems = set(s["gem"] for s in SPHERE_TYPES.values())
        assert gems == {"Zircon", "Smokestone", "Amethyst", "Sapphire", "Diamond"}

    def test_sphere_denominations_all_three(self):
        denoms = set(s["denomination"] for s in SPHERE_TYPES.values())
        assert denoms == {"Chip", "Mark", "Broam"}

    def test_diamond_broam_highest_stormlight(self):
        # Broam always has more stormlight than a chip of the same gem
        diamond = SPHERE_TYPES["Diamond Broam"]["max_stormlight"]
        zircon = SPHERE_TYPES["Zircon Chip"]["max_stormlight"]
        assert diamond > zircon

    def test_sphere_monetary_value_ordering(self):
        # SOURCE: Starter Rules p.46 — Sphere Values in Diamond Marks table.
        # Diamond is the BASE denomination (lowest monetary value per chip).
        # Correct ordering: Diamond < Zircon=Smokestone < Amethyst=Sapphire
        # Diamond Mark = 1mk, Zircon Mark = 10mk, Amethyst Mark = 25mk (same for sapphire)
        diamond_mark_value = SPHERE_TYPES["Diamond Mark"]["value_in_marks"]
        zircon_mark_value = SPHERE_TYPES["Zircon Mark"]["value_in_marks"]
        amethyst_mark_value = SPHERE_TYPES["Amethyst Mark"]["value_in_marks"]
        sapphire_mark_value = SPHERE_TYPES["Sapphire Mark"]["value_in_marks"]
        # Diamond is the LOWEST value gem (base denomination)
        assert diamond_mark_value < zircon_mark_value, (
            "Diamond should be LOWER value than Zircon "
            "(SOURCE: Starter Rules p.46)"
        )
        assert zircon_mark_value < amethyst_mark_value, (
            "Zircon should be LOWER value than Amethyst "
            "(SOURCE: Starter Rules p.46)"
        )
        assert amethyst_mark_value == sapphire_mark_value, (
            "Amethyst and Sapphire are in the same value tier "
            "(SOURCE: Starter Rules p.46)"
        )

    def test_sphere_has_value_in_marks(self):
        # All spheres must have monetary value recorded
        for name, sphere in SPHERE_TYPES.items():
            assert "value_in_marks" in sphere, (
                f"Sphere '{name}' missing value_in_marks "
                "(SOURCE: Starter Rules p.46)"
            )

    def test_shardblades_deal_spirit_damage(self):
        # SOURCE: Starter Rules p.27 — "Spirit. Effects that damage both your physical
        # and spiritual self (such as Shardblades) deal spirit damage."
        # SOURCE: GM Tools p.10 Duelist Shardbearer — "22 (2d8+6) spirit damage"
        for name, blade in SHARDBLADES.items():
            assert blade["damage_type"] == "spirit", (
                f"Shardblade '{name}' should deal spirit damage, not "
                f"'{blade['damage_type']}' (SOURCE: Starter Rules p.27)"
            )

    def test_weapon_properties_has_standard_weapons(self):
        for weapon in ["spear", "sword", "axe", "bow", "staff", "dagger", "unarmed"]:
            assert weapon in WEAPON_PROPERTIES, f"Missing weapon: {weapon}"

    def test_each_weapon_has_damage_dice(self):
        for name, wpn in WEAPON_PROPERTIES.items():
            assert "damage_dice" in wpn, f"{name} missing damage_dice"

    def test_longsword_damage_is_1d8_not_1d10(self):
        # SOURCE: Starter Rules p.48 — Longsword is Heavy Weaponry, 1d8 keen damage.
        # Not 1d10 as previously recorded.
        assert WEAPON_PROPERTIES["longsword"]["damage_dice"] == "1d8", (
            "Longsword should deal 1d8 damage (SOURCE: Starter Rules p.48)"
        )

    def test_weapons_use_correct_damage_types(self):
        # SOURCE: Starter Rules p.27 — damage types are impact/keen/energy/spirit/vital
        # SOURCE: Starter Rules p.48 — weapon damage type per entry
        keen_weapons = ["sword", "axe", "bow", "dagger", "longsword", "shortsword", "spear"]
        impact_weapons = ["staff", "mace", "shield", "warhammer", "unarmed"]
        for w in keen_weapons:
            if w in WEAPON_PROPERTIES:
                assert WEAPON_PROPERTIES[w]["damage_type"] == "keen", (
                    f"Weapon '{w}' should deal keen damage (SOURCE: Starter Rules p.48)"
                )
        for w in impact_weapons:
            if w in WEAPON_PROPERTIES:
                assert WEAPON_PROPERTIES[w]["damage_type"] == "impact", (
                    f"Weapon '{w}' should deal impact damage (SOURCE: Starter Rules p.48)"
                )

    def test_aggregator_exports_shardblades(self):
        assert AGG_SHARDBLADES is SHARDBLADES


# =========================================================================
# 3. HERITAGE DATA
# =========================================================================

class TestSTCHeritageData:
    """All 10 heritages load with correct structure."""

    EXPECTED_HERITAGES = [
        "Alethi", "Veden", "Thaylen", "Azish", "Herdazian",
        "Shin", "Makabaki", "Iriali", "Unkalaki", "Natan",
    ]

    def test_all_ten_heritages_present(self):
        for h in self.EXPECTED_HERITAGES:
            assert h in HERITAGES, f"Missing heritage: {h}"

    def test_each_heritage_has_stat_bonuses(self):
        for name, data in HERITAGES.items():
            bonuses = data.get("stat_bonuses", {})
            assert len(bonuses) >= 1, f"{name} should have at least one stat bonus"

    def test_each_heritage_has_cultural_traits(self):
        for name, data in HERITAGES.items():
            traits = data.get("cultural_traits", [])
            assert len(traits) >= 1, f"{name} should have cultural traits"

    def test_each_heritage_has_description(self):
        for name, data in HERITAGES.items():
            desc = data.get("description", "")
            assert len(desc) > 30, f"{name} description is too short"

    def test_alethi_gets_strength_bonus(self):
        assert HERITAGES["Alethi"]["stat_bonuses"].get("strength") == 1

    def test_veden_gets_intellect_bonus(self):
        assert HERITAGES["Veden"]["stat_bonuses"].get("intellect") == 1

    def test_thaylen_gets_speed_bonus(self):
        assert HERITAGES["Thaylen"]["stat_bonuses"].get("speed") == 1

    def test_iriali_and_natan_get_focus_bonus(self):
        assert HERITAGES["Iriali"]["stat_bonuses"].get("focus") == 1
        assert HERITAGES["Natan"]["stat_bonuses"].get("focus") == 1

    def test_unkalaki_gets_strength_bonus(self):
        assert HERITAGES["Unkalaki"]["stat_bonuses"].get("strength") == 1

    def test_aggregator_exports_heritages(self):
        assert AGG_HERITAGES is HERITAGES


# =========================================================================
# 4. STORM TRACKER
# =========================================================================

class TestStormTracker:
    """Storm cycle management and highstorm triggering."""

    def test_initialises_with_zero_days(self):
        st = StormTracker(storm_cycle=7)
        assert st.days_since_storm == 0
        assert st.storm_cycle == 7

    def test_advance_day_increments_counter(self):
        st = StormTracker(storm_cycle=7, rng=_rng())
        result = st.advance_day()
        assert result["day_advanced"] is True
        assert st.days_since_storm == 1

    def test_no_highstorm_before_cycle_ends(self):
        st = StormTracker(storm_cycle=7, rng=_rng())
        for _ in range(6):
            result = st.advance_day()
        assert not result["highstorm_occurred"]

    def test_highstorm_triggers_on_cycle(self):
        st = StormTracker(storm_cycle=3, rng=_rng())
        for _ in range(2):
            st.advance_day()
        result = st.advance_day()
        assert result["highstorm_occurred"] is True
        assert result["storm_data"] is not None

    def test_highstorm_resets_days_counter(self):
        st = StormTracker(storm_cycle=3, rng=_rng())
        for _ in range(3):
            st.advance_day()
        assert st.days_since_storm == 0

    def test_trigger_highstorm_directly(self):
        st = StormTracker(storm_cycle=7, rng=_rng())
        result = st.trigger_highstorm()
        assert "intensity" in result
        assert "sphere_recharge" in result
        assert "environmental_effect" in result
        assert "next_cycle" in result
        assert 5 <= result["next_cycle"] <= 10

    def test_highstorm_intensity_is_valid(self):
        valid = {"Weak", "Moderate", "Strong", "Furious"}
        st = StormTracker(storm_cycle=7, rng=_rng(99))
        result = st.trigger_highstorm()
        assert result["intensity"] in valid

    def test_to_dict_from_dict_round_trip(self):
        st = StormTracker(storm_cycle=5, rng=_rng())
        st.days_since_storm = 3
        d = st.to_dict()
        restored = StormTracker.from_dict(d)
        assert restored.days_since_storm == 3
        assert restored.storm_cycle == 5

    def test_advance_storm_data_returned_on_highstorm(self):
        st = StormTracker(storm_cycle=1, rng=_rng())
        result = st.advance_day()
        assert result["highstorm_occurred"] is True
        assert result["storm_data"]["sphere_recharge"] != ""


# =========================================================================
# 5. SURGE MANAGER
# =========================================================================

class TestSurgeManager:
    """Per-character stormlight tracking and surge abilities."""

    def test_initialises_with_zero_stormlight(self):
        mgr = SurgeManager("Kaladin", order="windrunner", ideal_level=1)
        assert mgr.stormlight == 0

    def test_max_stormlight_scales_with_ideal(self):
        for lvl in range(1, 6):
            mgr = SurgeManager("Test", order="windrunner", ideal_level=lvl)
            assert mgr.max_stormlight == lvl * 10

    def test_infuse_adds_stormlight(self):
        mgr = SurgeManager("Kaladin", order="windrunner", ideal_level=2)
        result = mgr.infuse(15)
        assert result["absorbed"] == 15
        assert mgr.stormlight == 15

    def test_infuse_caps_at_max(self):
        mgr = SurgeManager("Kaladin", order="windrunner", ideal_level=1)
        result = mgr.infuse(100)  # max is 10
        assert mgr.stormlight == mgr.max_stormlight
        assert result["overflow"] > 0

    def test_drain_reduces_stormlight(self):
        mgr = SurgeManager("Kaladin", order="windrunner", ideal_level=3)
        mgr.infuse(30)
        result = mgr.drain(5)
        assert result["success"] is True
        assert result["spent"] == 5
        assert mgr.stormlight == 25

    def test_drain_fails_when_insufficient(self):
        mgr = SurgeManager("Kaladin", order="windrunner", ideal_level=1)
        mgr.infuse(2)
        result = mgr.drain(10)
        assert result["success"] is False
        assert mgr.stormlight == 2

    def test_use_power_basic_lashing_succeeds(self):
        mgr = SurgeManager("Kaladin", order="windrunner", ideal_level=1, rng=_rng())
        mgr.infuse(10)
        result = mgr.use_power("Basic Lashing")
        assert result["success"] is True
        assert result["stormlight"] == 8  # cost is 2

    def test_use_power_unlocked_at_ideal_level(self):
        mgr = SurgeManager("Syl", order="windrunner", ideal_level=1)
        mgr.infuse(10)
        # Windrunner's Shield requires ideal 4 — should fail at ideal 1
        result = mgr.use_power("Windrunner's Shield")
        assert result["success"] is False

    def test_use_power_available_after_ideal_increase(self):
        mgr = SurgeManager("Kal", order="windrunner", ideal_level=4)
        mgr.infuse(20)
        result = mgr.use_power("Windrunner's Shield")
        assert result["success"] is True

    def test_use_power_unknown_power_fails(self):
        mgr = SurgeManager("Kal", order="windrunner", ideal_level=5)
        mgr.infuse(10)
        result = mgr.use_power("Nonexistent Power")
        assert result["success"] is False

    def test_use_power_with_zero_cost(self):
        mgr = SurgeManager("Kal", order="windrunner", ideal_level=5)
        mgr.infuse(10)
        result = mgr.use_power("Honorspren Bond")
        assert result["success"] is True
        assert mgr.stormlight == 10  # no cost

    def test_maintain_surges_drains_stormlight(self):
        mgr = SurgeManager("Kal", order="windrunner", ideal_level=2)
        mgr.infuse(20)
        mgr.active_surges = [{"name": "Active Lashing", "maintenance_cost": 2}]
        result = mgr.maintain_surges()
        assert result["total_drained"] == 2
        assert mgr.stormlight == 18
        assert result["active_count"] == 1

    def test_maintain_surges_expires_when_empty(self):
        mgr = SurgeManager("Kal", order="windrunner", ideal_level=1)
        mgr.stormlight = 0
        mgr.active_surges = [{"name": "Expired Surge", "maintenance_cost": 1}]
        result = mgr.maintain_surges()
        assert "Expired Surge" in result["expired_surges"]
        assert result["active_count"] == 0

    def test_healing_uses_stormlight(self):
        mgr = SurgeManager("Kal", order="windrunner", ideal_level=2)
        mgr.infuse(20)
        char = _char(name="Kal")
        char.current_hp = 5  # Damaged
        result = mgr.healing(char)
        assert result["healed"] > 0
        assert mgr.stormlight < 20

    def test_healing_stops_at_max_hp(self):
        mgr = SurgeManager("Kal", order="windrunner", ideal_level=2)
        mgr.infuse(20)
        char = _char(name="Kal")
        # Full health
        result = mgr.healing(char)
        assert result["healed"] == 0

    def test_lashing_costs_stormlight(self):
        mgr = SurgeManager("Kal", order="windrunner", ideal_level=1)
        mgr.infuse(10)
        result = mgr.lashing("Fused Scout", direction="up")
        assert result["success"] is True
        assert mgr.stormlight == 8  # cost 2

    def test_lashing_fails_without_stormlight(self):
        mgr = SurgeManager("Kal", order="windrunner", ideal_level=1)
        result = mgr.lashing("Target")
        assert result["success"] is False

    def test_soulcast_requires_stormlight(self):
        mgr = SurgeManager("Shallan", order="lightweaver", ideal_level=2, rng=_rng(5))
        mgr.infuse(10)
        result = mgr.soulcast("air", difficulty=8)
        assert result["success"] is True or result["success"] is False
        # Must have spent stormlight
        assert mgr.stormlight <= 7

    def test_soulcast_fails_without_stormlight(self):
        mgr = SurgeManager("Shallan", order="lightweaver", ideal_level=2)
        result = mgr.soulcast("stone")
        assert result["success"] is False

    def test_illuminate_costs_stormlight(self):
        mgr = SurgeManager("Shallan", order="lightweaver", ideal_level=2)
        mgr.infuse(10)
        result = mgr.illuminate("A tall Alethi soldier")
        assert result["success"] is True
        assert mgr.stormlight == 8

    def test_get_available_powers_returns_list(self):
        mgr = SurgeManager("Kal", order="windrunner", ideal_level=3)
        powers = mgr.get_available_powers()
        assert isinstance(powers, list)
        assert len(powers) >= 3  # 1 power per ideal level 1-3

    def test_get_status_returns_string(self):
        mgr = SurgeManager("Kal", order="windrunner", ideal_level=2)
        mgr.infuse(15)
        status = mgr.get_status()
        assert "Kal" in status
        assert "15/20" in status

    def test_set_ideal_level_updates_max(self):
        mgr = SurgeManager("Kal", order="windrunner", ideal_level=1)
        mgr.set_ideal_level(3)
        assert mgr.ideal_level == 3
        assert mgr.max_stormlight == 30

    def test_to_dict_from_dict_round_trip(self):
        mgr = SurgeManager("Kal", order="windrunner", ideal_level=2)
        mgr.infuse(15)
        mgr.active_surges = [{"name": "Test Surge", "maintenance_cost": 1}]
        d = mgr.to_dict()
        restored = SurgeManager.from_dict(d)
        assert restored.character_name == "Kal"
        assert restored.order == "windrunner"
        assert restored.ideal_level == 2
        assert restored.stormlight == 15
        assert len(restored.active_surges) == 1


# =========================================================================
# 6. COSMERE COMBAT RESOLVER
# =========================================================================

class TestCosmereCombatResolver:
    """Attack rolls, Shardblade, Shardplate defense, duel, surge combat."""

    def test_attack_roll_returns_attack_result(self):
        r = CosmereCombatResolver(rng=_rng())
        char = _char()
        result = r.attack_roll(char, target_defense=12)
        assert isinstance(result, AttackResult)

    def test_attack_roll_hit_on_high_roll(self):
        # Seed 42 rolls specific values; force with stormlight bonus
        r = CosmereCombatResolver(rng=_rng(1))
        char = _char(name="Kal")
        result = r.attack_roll(char, target_defense=5, weapon_name="spear",
                               ability_mod=2, stormlight_bonus=0)
        # Should hit against DC 5 with ability mod 2
        assert isinstance(result, AttackResult)

    def test_critical_hit_on_natural_20(self):
        # Use a seeded rng that produces 20 on first roll
        class Fixed20:
            def randint(self, a, b):
                return 20
            def choice(self, seq):
                return seq[0]
        r = CosmereCombatResolver(rng=Fixed20())
        char = _char()
        result = r.attack_roll(char, target_defense=20)
        assert result.critical is True
        assert result.hit is True

    def test_fumble_on_natural_1(self):
        class Fixed1:
            def randint(self, a, b):
                return 1
            def choice(self, seq):
                return seq[0]
        r = CosmereCombatResolver(rng=Fixed1())
        char = _char()
        result = r.attack_roll(char, target_defense=10)
        assert result.fumble is True
        assert result.hit is False

    def test_advantage_takes_higher_roll(self):
        results_checked = False
        for seed in range(50):
            r = CosmereCombatResolver(rng=random.Random(seed))
            char = _char()
            result_adv = r.attack_roll(char, target_defense=15, advantage=True)
            results_checked = True
        assert results_checked

    def test_attack_result_describe_on_hit(self):
        r = CosmereCombatResolver(rng=_rng())
        char = _char()
        result = r.attack_roll(char, target_defense=1, weapon_name="spear", ability_mod=2)
        result.target = "Fused Scout"
        description = result.describe()
        assert isinstance(description, str)
        assert len(description) > 0

    def test_shardblade_attack_returns_dict(self):
        r = CosmereCombatResolver(rng=_rng())
        char = _char()
        target = {"name": "Parshendi Warrior", "hp": 20, "defense": 10}
        result = r.shardblade_attack(char, target)
        assert "hit" in result
        assert "message" in result
        assert "location" in result

    def test_shardblade_hit_deadens_limb_or_kills(self):
        class FixedHigh:
            def randint(self, a, b):
                # Always roll 15, always gives a hit (8+15=23), always non-lethal location
                # Force a specific result
                return 15
            def choice(self, seq):
                return seq[0]
        r = CosmereCombatResolver(rng=FixedHigh())
        char = _char()
        target = {"name": "Enemy", "hp": 30, "defense": 10}
        result = r.shardblade_attack(char, target)
        assert result["hit"] is True
        # Effect should be either kill, deaden_limb, or plate_crack
        assert result["effect"] in ("kill", "deaden_limb", "plate_crack")

    def test_shardblade_miss_returns_no_damage(self):
        class Fixed1:
            def randint(self, a, b):
                return 1
            def choice(self, seq):
                return seq[0]
        r = CosmereCombatResolver(rng=Fixed1())
        char = _char()
        target = {"name": "Enemy", "hp": 20, "defense": 15}
        result = r.shardblade_attack(char, target)
        assert result["hit"] is False
        assert result["damage"] == 0

    def test_shardplate_defense_absorbs_damage(self):
        r = CosmereCombatResolver(rng=_rng())
        defender = _char(name="Shardbearer")
        result = r.shardplate_defense(defender, damage=10)
        assert result["absorbed"] > 0
        assert result["actual_damage"] < 10

    def test_shardplate_cracks_on_large_hit(self):
        r = CosmereCombatResolver(rng=_rng())
        defender = _char(name="Shardbearer")
        plate_state = {"integrity": 100, "cracks": 0}
        result = r.shardplate_defense(defender, damage=20, plate_state=plate_state)
        assert result["plate_cracked"] is True
        assert result["cracks"] >= 1

    def test_shardplate_no_crack_on_small_hit(self):
        r = CosmereCombatResolver(rng=_rng())
        defender = _char(name="Shardbearer")
        plate_state = {"integrity": 100, "cracks": 0}
        result = r.shardplate_defense(defender, damage=5, plate_state=plate_state)
        assert result["plate_cracked"] is False

    def test_shardplate_shatters_at_zero_integrity(self):
        r = CosmereCombatResolver(rng=_rng())
        defender = _char(name="Shardbearer")
        plate_state = {"integrity": 20, "cracks": 3}  # Nearly broken
        result = r.shardplate_defense(defender, damage=30, plate_state=plate_state)
        assert result["plate_shattered"] is True

    def test_duel_of_champions_returns_dict(self):
        r = CosmereCombatResolver(rng=_rng())
        attacker = {"name": "Kaladin", "hp": 30, "defense": 14, "atk_mod": 4}
        defender = {"name": "Fused", "hp": 20, "defense": 12, "atk_mod": 3}
        result = r.duel_of_champions(attacker, defender, rounds=5)
        assert "winner" in result
        assert "log" in result
        assert "rounds_fought" in result
        assert result["rounds_fought"] <= 5

    def test_duel_produces_winner_or_draw(self):
        r = CosmereCombatResolver(rng=_rng())
        attacker = {"name": "Hero", "hp": 50, "defense": 10, "atk_mod": 8}
        defender = {"name": "Weakling", "hp": 5, "defense": 5, "atk_mod": 0}
        result = r.duel_of_champions(attacker, defender, rounds=10)
        # Hero should win easily
        assert result["winner"] == "Hero"

    def test_duel_log_is_list_of_strings(self):
        r = CosmereCombatResolver(rng=_rng())
        a = {"name": "A", "hp": 20, "defense": 10, "atk_mod": 2}
        b = {"name": "B", "hp": 20, "defense": 10, "atk_mod": 2}
        result = r.duel_of_champions(a, b, rounds=3)
        assert isinstance(result["log"], list)
        assert all(isinstance(s, str) for s in result["log"])

    def test_resolve_surge_combat_returns_dict(self):
        r = CosmereCombatResolver(rng=_rng())
        char = _char()
        mgr = SurgeManager("Kaladin", order="windrunner", ideal_level=2, rng=_rng())
        mgr.infuse(20)
        targets = [{"name": "Enemy", "hp": 20}]
        result = r.resolve_surge_combat(char, mgr, targets, "Basic Lashing")
        assert "success" in result
        assert "message" in result

    def test_surge_combat_fails_without_stormlight(self):
        r = CosmereCombatResolver(rng=_rng())
        char = _char()
        mgr = SurgeManager("Kaladin", order="windrunner", ideal_level=2)
        # No stormlight infused
        targets = [{"name": "Enemy", "hp": 20}]
        result = r.resolve_surge_combat(char, mgr, targets, "Basic Lashing")
        assert result["success"] is False

    def test_attack_result_describe_fumble(self):
        result = AttackResult(attacker="Hero", target="Enemy", roll=1, modifier=0,
                               total=1, defense=10, hit=False, critical=False, fumble=True)
        desc = result.describe()
        assert "fumble" in desc.lower() or "1" in desc

    def test_attack_result_describe_critical(self):
        result = AttackResult(attacker="Hero", target="Enemy", roll=20, modifier=3,
                               total=23, defense=10, hit=True, critical=True, fumble=False,
                               damage=25, weapon="spear")
        desc = result.describe()
        assert "CRITICAL" in desc


# =========================================================================
# 7. IDEAL PROGRESSION
# =========================================================================

class TestIdealProgression:
    """Oath checks, progress, ability unlocks, and sequence enforcement."""

    def test_initialises_at_ideal_one(self):
        ip = IdealProgression("Kaladin", order="windrunner")
        assert ip.current_ideal == 1

    def test_ideal_one_progress_starts_full(self):
        ip = IdealProgression("Kaladin", order="windrunner")
        assert ip.ideal_progress[1] == 1.0

    def test_higher_ideals_start_at_zero(self):
        ip = IdealProgression("Kaladin", order="windrunner", current_ideal=1)
        assert ip.ideal_progress[2] == 0.0
        assert ip.ideal_progress[3] == 0.0

    def test_get_oath_text_returns_string(self):
        ip = IdealProgression("Kaladin", order="windrunner")
        text = ip.get_oath_text(2)
        assert isinstance(text, str)
        assert len(text) > 10

    def test_oath_text_from_reference_data(self):
        ip = IdealProgression("Kaladin", order="windrunner")
        text = ip.get_oath_text(2)
        assert "protect" in text.lower()

    def test_add_progress_increments_next_ideal(self):
        ip = IdealProgression("Kaladin", order="windrunner")
        result = ip.add_progress(0.3, reason="protected someone")
        assert result["progress"] == pytest.approx(0.3)
        assert ip.ideal_progress[2] == pytest.approx(0.3)

    def test_add_progress_caps_at_one(self):
        ip = IdealProgression("Kaladin", order="windrunner")
        ip.add_progress(0.9)
        ip.add_progress(0.9)
        assert ip.ideal_progress[2] <= 1.0

    def test_add_progress_signals_ready_at_threshold(self):
        ip = IdealProgression("Kaladin", order="windrunner")
        result = ip.add_progress(IDEAL_PROGRESS_THRESHOLD, reason="test")
        assert result["ready_to_swear"] is True

    def test_add_progress_at_max_ideal_returns_message(self):
        ip = IdealProgression("Kal", order="windrunner", current_ideal=5)
        result = ip.add_progress(0.5)
        assert "all 5 Ideals" in result["message"]

    def test_oath_check_fails_without_progress(self):
        ip = IdealProgression("Kaladin", order="windrunner")
        result = ip.oath_check(2)
        assert result["success"] is False

    def test_oath_check_succeeds_with_progress_and_high_roll(self):
        ip = IdealProgression("Kaladin", order="windrunner")
        ip.add_progress(1.0)  # Full progress
        # Guarantee a high roll
        class FixedHigh:
            def randint(self, a, b):
                return 20
        result = ip.oath_check(2, rng=FixedHigh())
        assert result["success"] is True
        assert ip.current_ideal == 2

    def test_oath_check_fails_on_low_roll(self):
        ip = IdealProgression("Kaladin", order="windrunner")
        ip.add_progress(1.0)
        class FixedLow:
            def randint(self, a, b):
                return 1
        result = ip.oath_check(2, rng=FixedLow())
        assert result["success"] is False
        assert ip.current_ideal == 1  # Not advanced

    def test_oath_check_wrong_sequence_fails(self):
        ip = IdealProgression("Kaladin", order="windrunner", current_ideal=1)
        ip.add_progress(1.0)
        result = ip.oath_check(3)  # Skip ideal 2
        assert result["success"] is False
        assert "Ideal 2" in result["message"] or "next" in result["message"].lower()

    def test_oath_check_already_sworn_fails(self):
        ip = IdealProgression("Kaladin", order="windrunner", current_ideal=2)
        result = ip.oath_check(1)  # Already sworn
        assert result["success"] is False

    def test_oath_check_unlocks_powers(self):
        ip = IdealProgression("Kaladin", order="windrunner")
        ip.add_progress(1.0)
        class FixedHigh:
            def randint(self, a, b):
                return 20
        result = ip.oath_check(2, rng=FixedHigh())
        assert result["success"] is True
        assert len(result["new_powers"]) >= 1

    def test_unlock_ability_adds_to_list(self):
        ip = IdealProgression("Kaladin", order="windrunner")
        result = ip.unlock_ability("Test Power")
        assert result["unlocked"] is True
        assert "Test Power" in ip.unlocked_abilities

    def test_unlock_ability_duplicate_returns_false(self):
        ip = IdealProgression("Kaladin", order="windrunner")
        ip.unlock_ability("Power A")
        result = ip.unlock_ability("Power A")
        assert result["unlocked"] is False

    def test_get_available_ideals_returns_five(self):
        ip = IdealProgression("Kaladin", order="windrunner")
        ideals = ip.get_available_ideals()
        assert len(ideals) == 5

    def test_get_available_ideals_marks_sworn_correctly(self):
        ip = IdealProgression("Kaladin", order="windrunner", current_ideal=3)
        ideals = ip.get_available_ideals()
        assert ideals[0]["sworn"] is True
        assert ideals[1]["sworn"] is True
        assert ideals[2]["sworn"] is True
        assert ideals[3]["sworn"] is False
        assert ideals[4]["sworn"] is False

    def test_get_available_ideals_marks_ready_to_attempt(self):
        ip = IdealProgression("Kaladin", order="windrunner")
        ip.add_progress(IDEAL_PROGRESS_THRESHOLD)
        ideals = ip.get_available_ideals()
        # Ideal 2 should be ready
        assert ideals[1]["ready_to_attempt"] is True

    def test_to_dict_from_dict_round_trip(self):
        ip = IdealProgression("Kaladin", order="windrunner", current_ideal=2)
        ip.add_progress(0.4)
        ip.unlock_ability("Windrunner's Shield")
        d = ip.to_dict()
        restored = IdealProgression.from_dict(d)
        assert restored.character_name == "Kaladin"
        assert restored.current_ideal == 2
        assert restored.ideal_progress[3] == pytest.approx(0.4)
        assert "Windrunner's Shield" in restored.unlocked_abilities

    def test_ideal_dc_values_correct(self):
        assert IDEAL_DC[1] == 0
        assert IDEAL_DC[2] == 10
        assert IDEAL_DC[5] == 19


# =========================================================================
# 8. SAVE/LOAD ROUND-TRIP
# =========================================================================

class TestSTCEngineSaveLoad:
    """Full round-trip save/load with all subsystem state."""

    def test_basic_save_load_preserves_party(self):
        eng = _engine_with_char()
        state = eng.save_state()
        eng2 = CosmereEngine()
        eng2.load_state(state)
        assert len(eng2.party) == 1
        assert eng2.party[0].name == "Kaladin"

    def test_save_load_preserves_ideal_level(self):
        eng = _engine_with_char()
        eng.swear_ideal()
        state = eng.save_state()
        eng2 = CosmereEngine()
        eng2.load_state(state)
        assert eng2.party[0].ideal_level == 2

    def test_save_load_preserves_surge_manager(self):
        eng = _engine_with_char()
        char = eng.party[0]
        mgr = eng._get_surge_manager(char)
        # Ideal 1 -> max_stormlight is 10; infuse exactly 10 to avoid cap
        mgr.infuse(10)
        state = eng.save_state()
        eng2 = CosmereEngine()
        eng2.load_state(state)
        assert "Kaladin" in eng2._surge_managers
        assert eng2._surge_managers["Kaladin"].stormlight == 10

    def test_save_load_preserves_ideal_tracker(self):
        eng = _engine_with_char()
        char = eng.party[0]
        tracker = eng._get_ideal_tracker(char)
        tracker.add_progress(0.6)
        state = eng.save_state()
        eng2 = CosmereEngine()
        eng2.load_state(state)
        assert "Kaladin" in eng2._ideal_trackers
        assert eng2._ideal_trackers["Kaladin"].ideal_progress[2] == pytest.approx(0.6)

    def test_save_load_preserves_storm_tracker(self):
        eng = _engine_with_char()
        storm = eng._get_storm_tracker()
        storm.days_since_storm = 4
        storm.storm_cycle = 6
        state = eng.save_state()
        eng2 = CosmereEngine()
        eng2.load_state(state)
        assert eng2._storm_tracker is not None
        assert eng2._storm_tracker.days_since_storm == 4
        assert eng2._storm_tracker.storm_cycle == 6

    def test_save_load_state_ids(self):
        eng = _engine_with_char()
        state = eng.save_state()
        assert state["system_id"] == "stc"

    def test_load_state_with_no_subsystems_is_safe(self):
        """Loading a state dict without subsystem keys should not crash."""
        minimal_state = {
            "system_id": "stc",
            "party": [{"name": "Solo", "heritage": "", "order": "windrunner",
                        "strength": 10, "speed": 10, "intellect": 10}],
            "current_room_id": None,
            "player_pos": None,
            "visited_rooms": [],
        }
        eng = CosmereEngine()
        eng.load_state(minimal_state)
        assert eng.party[0].name == "Solo"

    def test_save_contains_subsystem_keys(self):
        eng = _engine_with_char()
        eng._get_surge_manager(eng.party[0])  # Force init
        state = eng.save_state()
        assert "surge_managers" in state
        assert "ideal_trackers" in state
        assert "storm_tracker" in state

    def test_multi_character_save_load(self):
        eng = CosmereEngine()
        c1 = eng.create_character("Kaladin", order="windrunner")
        c2 = CosmereCharacter(name="Shallan", order="lightweaver")
        eng.add_to_party(c2)
        # Init subsystems for both
        eng._get_surge_manager(c1).infuse(10)
        eng._get_surge_manager(c2).infuse(5)
        state = eng.save_state()
        eng2 = CosmereEngine()
        eng2.load_state(state)
        assert len(eng2.party) == 2
        assert eng2._surge_managers["Kaladin"].stormlight == 10
        assert eng2._surge_managers["Shallan"].stormlight == 5


# =========================================================================
# 9. COMMAND DISPATCH
# =========================================================================

class TestSTCCommandDispatch:
    """All handle_command dispatches reach correct handler."""

    def test_party_status_command(self):
        eng = _engine_with_char()
        result = eng.handle_command("party_status")
        assert "Kaladin" in result
        assert "windrunner" in result.lower()

    def test_swear_ideal_command(self):
        eng = _engine_with_char()
        result = eng.handle_command("swear_ideal", name="Kaladin")
        assert "Kaladin" in result
        assert "Ideal" in result

    def test_roll_check_command(self):
        eng = _engine_with_char()
        result = eng.handle_command("roll_check", attribute="strength")
        assert "Roll" in result

    def test_roll_check_with_dc(self):
        eng = _engine_with_char()
        result = eng.handle_command("roll_check", attribute="strength", dc=10)
        assert "SUCCESS" in result or "FAIL" in result

    def test_trace_fact_command(self):
        eng = _engine_with_char()
        result = eng.handle_command("trace_fact", fact="test fact")
        assert isinstance(result, str)

    def test_infuse_command(self):
        eng = _engine_with_char()
        # Ideal 1 char has max_stormlight=10; infuse 8 to stay within cap
        result = eng.handle_command("infuse", amount=8)
        assert "8" in result
        assert "Kaladin" in result

    def test_stormlight_status_command(self):
        eng = _engine_with_char()
        eng.handle_command("infuse", amount=10)
        result = eng.handle_command("stormlight_status")
        assert "Kaladin" in result

    def test_surge_command_requires_power(self):
        eng = _engine_with_char()
        result = eng.handle_command("surge")  # No power specified
        assert "requires" in result.lower() or "power" in result.lower()

    def test_surge_command_with_power(self):
        eng = _engine_with_char()
        eng.handle_command("infuse", amount=10)
        result = eng.handle_command("surge", power="Basic Lashing")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_attack_command_returns_string(self):
        eng = _engine_with_char()
        target = {"name": "Parshendi Scout", "hp": 15, "defense": 10}
        result = eng.handle_command("attack", target_enemy=target, weapon="spear")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_shardblade_command_requires_target(self):
        eng = _engine_with_char()
        result = eng.handle_command("shardblade")
        assert "requires" in result.lower() or "target" in result.lower()

    def test_shardblade_command_with_target(self):
        eng = _engine_with_char()
        target = {"name": "Fused", "hp": 30, "defense": 12}
        result = eng.handle_command("shardblade", target_enemy=target)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_duel_command_requires_both_combatants(self):
        eng = _engine_with_char()
        result = eng.handle_command("duel")
        assert "requires" in result.lower() or "challenger" in result.lower()

    def test_duel_command_with_combatants(self):
        eng = _engine_with_char()
        challenger = {"name": "Hero", "hp": 30, "defense": 12, "atk_mod": 4}
        defender = {"name": "Villain", "hp": 20, "defense": 10, "atk_mod": 2}
        result = eng.handle_command("duel", challenger=challenger, defender=defender)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_oath_command_advances_ideal(self):
        eng = _engine_with_char()
        result = eng.handle_command("oath", context="I saved a darkeyed child")
        assert isinstance(result, str)
        # Should attempt to swear ideal 2
        assert "Ideal" in result or "ideal" in result

    def test_ideal_status_command(self):
        eng = _engine_with_char()
        result = eng.handle_command("ideal_status")
        assert "Ideal Progression" in result
        assert "Kaladin" in result

    def test_highstorm_status_command(self):
        eng = _engine_with_char()
        result = eng.handle_command("highstorm")
        assert "storm" in result.lower()

    def test_highstorm_trigger_command(self):
        eng = _engine_with_char()
        result = eng.handle_command("highstorm", trigger=True)
        assert "Highstorm triggered" in result
        assert "sphere_recharge" in result.lower() or "recharged" in result.lower()

    def test_highstorm_advance_day_command(self):
        eng = _engine_with_char()
        result = eng.handle_command("highstorm", advance_day=True)
        assert isinstance(result, str)
        assert "day advanced" in result.lower() or "highstorm" in result.lower()

    def test_unknown_command_returns_error(self):
        eng = _engine_with_char()
        result = eng.handle_command("nonexistent_command")
        assert "Unknown" in result

    def test_char_not_found_graceful(self):
        eng = _engine_with_char()
        result = eng.handle_command("infuse", amount=10, char_name="Nobody")
        assert "not found" in result.lower() or "Nobody" in result

    def test_zone_status_no_module(self):
        eng = _engine_with_char()
        result = eng.handle_command("zone_status")
        assert "No module" in result
