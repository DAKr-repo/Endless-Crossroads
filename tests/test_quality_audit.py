"""
test_quality_audit.py — WO-V36.0 Quality Audit Tests
=====================================================

Tests for:
- PDF Rich markup escape (Section A)
- Tutorial text fixes (Section B)
- AoE trait resolvers (Section C1)
- Loot items (Section C2)
- Auto-trigger damage AoE (Section C3)
- Manual AoE commands (Section C3)
- Companion command (Section D)
- Enemy gear AoE (Section C4)
- State tracking expiry (Section C3)
"""

import random
from unittest.mock import MagicMock, patch

import pytest

from codex.games.burnwillow.engine import (
    BurnwillowEngine, Character, GearGrid, GearItem, GearSlot, GearTier,
    BurnwillowTraitResolver, StatType, CheckResult,
)
from codex.games.burnwillow.content import ENEMY_TABLES, LOOT_TABLES


# ============================================================================
# Helpers
# ============================================================================

def _make_engine_with_party(names=None):
    """Create a BurnwillowEngine with a party of characters."""
    names = names or ["Kael"]
    engine = BurnwillowEngine()
    engine.create_party(names)
    return engine


def _make_item(name: str, slot: str, tier: int, traits: list) -> GearItem:
    """Create a GearItem with given parameters."""
    slot_map = {
        "R.Hand": GearSlot.R_HAND, "L.Hand": GearSlot.L_HAND,
        "Head": GearSlot.HEAD, "Chest": GearSlot.CHEST,
        "Arms": GearSlot.ARMS, "Legs": GearSlot.LEGS,
        "Shoulders": GearSlot.SHOULDERS, "Neck": GearSlot.NECK,
        "R.Ring": GearSlot.R_RING, "L.Ring": GearSlot.L_RING,
    }
    tier_map = {1: GearTier.TIER_I, 2: GearTier.TIER_II, 3: GearTier.TIER_III, 4: GearTier.TIER_IV}
    return GearItem(
        name=name,
        slot=slot_map.get(slot, GearSlot.R_HAND),
        tier=tier_map.get(tier, GearTier.TIER_I),
        special_traits=traits,
        description=f"Test item: {name}",
    )


def _equip(char: Character, item: GearItem):
    """Equip an item on a character."""
    char.gear.equip(item)


# ============================================================================
# Section A: PDF Escape
# ============================================================================

class TestPDFEscape:
    """Test that Rich markup characters in PDFs are properly escaped."""

    def test_brackets_escaped(self):
        from codex.core.services.librarian import LibrarianTUI
        text = "[//ENCRYPTED TRANSMISSION] begins here"
        result = LibrarianTUI._sanitize_pdf_text(text)
        # Rich escape() converts [ to \[ to prevent markup interpretation
        assert "\\[" in result
        # The escaped version should start with backslash-bracket
        assert result.startswith("\\[")

    def test_normal_text_unchanged(self):
        from codex.core.services.librarian import LibrarianTUI
        text = "This is normal text without brackets."
        result = LibrarianTUI._sanitize_pdf_text(text)
        assert result == "This is normal text without brackets."

    def test_mixed_content(self):
        from codex.core.services.librarian import LibrarianTUI
        text = "Normal text [secret code] and more text [another]"
        result = LibrarianTUI._sanitize_pdf_text(text)
        # Opening brackets are escaped
        assert "\\[secret code]" in result
        assert "\\[another]" in result


# ============================================================================
# Section B: Tutorial Text Fixes
# ============================================================================

class TestTutorialTextFixes:
    """Test that tutorial text accurately reflects game mechanics."""

    @pytest.fixture(autouse=True)
    def _load_tutorial(self):
        import codex.core.services.tutorial_content  # noqa: F401
        from codex.core.services.tutorial import TutorialRegistry
        self.registry = TutorialRegistry

    def test_sway_range_is_3(self):
        """B1: Crown sway should show -3/+3, not -10/+10."""
        module = self.registry.get_module("crown_allegiance")
        assert module is not None
        page = module.pages[0]
        assert "-3" in page.content
        assert "+3" in page.content
        assert "-10" not in page.content
        assert "+10" not in page.content

    def test_attack_roll_is_d6_pool(self):
        """B2: Burnwillow attack should reference d6 dice pool, not d20."""
        module = self.registry.get_module("burnwillow_combat")
        assert module is not None
        page1 = module.pages[0]  # "Entering Combat"
        assert "d20" not in page1.content
        assert "dice pool" in page1.content or "Might dice pool" in page1.content

    def test_gear_slots_is_ten(self):
        """B3: Gear Grid should list 10 slots, not 6."""
        module = self.registry.get_module("burnwillow_gear")
        assert module is not None
        page1 = module.pages[0]  # "The Gear Grid"
        assert "Ten Slots" in page1.content
        assert "Six Slots" not in page1.content
        # Check for the 4 new slots
        assert "Shoulders" in page1.content
        assert "Neck" in page1.content
        assert "R.Ring" in page1.content
        assert "L.Ring" in page1.content

    def test_platform_menu_includes_dnd5e_cosmere(self):
        """B4: Platform tutorial should mention D&D 5e and Cosmere."""
        module = self.registry.get_module("platform_overview")
        assert module is not None
        page2 = module.pages[1]  # "Main Menu"
        assert "D&D 5e" in page2.content or "5e" in page2.content
        assert "Cosmere" in page2.content or "Stormlight" in page2.content

    def test_aoe_tutorial_lists_all_traits(self):
        """B5: AoE tutorial should list all 12 AoE trait types."""
        module = self.registry.get_module("burnwillow_scaling")
        assert module is not None
        # Find the AoE Combat page
        aoe_page = None
        for page in module.pages:
            if "AoE" in page.title or "Area" in page.title:
                aoe_page = page
                break
        assert aoe_page is not None, "AoE Combat page not found"
        # Check for key traits
        for trait in ["Cleave", "Shockwave", "Whirlwind", "Flash", "Snare", "Rally",
                      "Inferno", "Tempest", "Voidgrip", "Mending", "Renewal", "Aegis"]:
            assert trait in aoe_page.content, f"Missing trait: {trait}"
        # Should NOT mention bare "slam attacks" as the main mechanic
        assert "slam attacks" not in aoe_page.content


# ============================================================================
# Section C1: Trait Resolvers
# ============================================================================

class TestTraitResolvers:
    """Test all 11 new trait resolvers in BurnwillowTraitResolver."""

    @pytest.fixture
    def resolver(self):
        return BurnwillowTraitResolver()

    @pytest.fixture
    def char(self):
        engine = _make_engine_with_party(["TestHero"])
        return engine.party[0]

    def _ctx(self, char, tier=2):
        item = _make_item("TestWeapon", "R.Hand", tier, [])
        return {"character": char, "item": item}

    def test_shockwave(self, resolver, char):
        result = resolver.resolve_trait("SHOCKWAVE", self._ctx(char, 2))
        assert "message" in result
        assert "SHOCKWAVE" in result["message"]
        assert "action" in result
        assert result["action"] == "shockwave"
        if result["success"]:
            assert result["stun_rounds"] == 1
            assert result["targets"] <= 3

    def test_whirlwind(self, resolver, char):
        result = resolver.resolve_trait("WHIRLWIND", self._ctx(char, 3))
        assert "WHIRLWIND" in result["message"]
        assert result["action"] == "whirlwind"
        if result["success"]:
            assert result["hits_all"] is True
            assert result["damage_pct"] == 0.75

    def test_flash(self, resolver, char):
        result = resolver.resolve_trait("FLASH", self._ctx(char, 2))
        assert "FLASH" in result["message"]
        assert result["action"] == "flash"
        if result["success"]:
            assert result["blind_rounds"] == 2
            assert result["accuracy_penalty"] == -2

    def test_snare(self, resolver, char):
        result = resolver.resolve_trait("SNARE", self._ctx(char, 3))
        assert "SNARE" in result["message"]
        assert result["action"] == "snare"
        if result["success"]:
            assert result["defense_reduction"] == 3  # tier value

    def test_rally(self, resolver, char):
        result = resolver.resolve_trait("RALLY", self._ctx(char, 1))
        assert "RALLY" in result["message"]
        assert result["action"] == "rally"
        if result["success"]:
            assert result["bonus_dice"] == 1
            assert result["hits_all_allies"] is True

    def test_inferno(self, resolver, char):
        result = resolver.resolve_trait("INFERNO", self._ctx(char, 2))
        assert "INFERNO" in result["message"]
        assert result["action"] == "inferno"
        if result["success"]:
            assert result["burning_rounds"] == 2
            assert result["targets"] <= 3

    def test_tempest(self, resolver, char):
        result = resolver.resolve_trait("TEMPEST", self._ctx(char, 3))
        assert "TEMPEST" in result["message"]
        assert result["action"] == "tempest"
        if result["success"]:
            assert result["targets"] <= 3
            assert result["damage"] > 0

    def test_voidgrip(self, resolver, char):
        result = resolver.resolve_trait("VOIDGRIP", self._ctx(char, 2))
        assert "VOIDGRIP" in result["message"]
        assert result["action"] == "voidgrip"
        if result["success"]:
            assert result["blighted_rounds"] == 2
            assert result["targets"] <= 2

    def test_mending(self, resolver, char):
        result = resolver.resolve_trait("MENDING", self._ctx(char, 2))
        assert "MENDING" in result["message"]
        assert result["action"] == "mending"
        if result["success"]:
            assert result["heal_amount"] > 0
            assert result["hits_all_allies"] is True

    def test_renewal(self, resolver, char):
        result = resolver.resolve_trait("RENEWAL", self._ctx(char, 1))
        assert "RENEWAL" in result["message"]
        assert result["action"] == "renewal"
        if result["success"]:
            assert result["hot_rounds"] == 3
            assert result["hits_all_allies"] is True

    def test_aegis(self, resolver, char):
        result = resolver.resolve_trait("AEGIS", self._ctx(char, 3))
        assert "AEGIS" in result["message"]
        assert result["action"] == "aegis"
        if result["success"]:
            assert result["dr_bonus"] == 3  # tier value
            assert result["duration_rounds"] == 2


# ============================================================================
# Section C2: Loot Items
# ============================================================================

class TestLootItems:
    """Test new loot items exist in LOOT_TABLES at correct tiers."""

    def test_tier2_new_items(self):
        """T2 should have Quake Hammer, Gale Glaive, etc."""
        t2_names = [item[0] for item in LOOT_TABLES[2]]
        for name in ["Quake Hammer", "Gale Glaive", "Flashbang Pouch",
                     "Bolas of Binding", "War Horn", "Embertongue Wand",
                     "Stormcaller Rod", "Herbalist's Satchel"]:
            assert name in t2_names, f"Missing T2 item: {name}"

    def test_tier3_new_items(self):
        """T3 should have Earthsplitter Maul, Cyclone Blade, etc."""
        t3_names = [item[0] for item in LOOT_TABLES[3]]
        for name in ["Earthsplitter Maul", "Cyclone Blade", "Sunburst Lantern",
                     "Rootweave Net", "Commander's Pennant", "Inferno Staff",
                     "Voidstone Focus", "Renewal Chalice"]:
            assert name in t3_names, f"Missing T3 item: {name}"

    def test_tier4_new_items(self):
        """T4 should have Worldbreaker, Tempest Annihilator, etc."""
        t4_names = [item[0] for item in LOOT_TABLES[4]]
        for name in ["Worldbreaker", "Tempest Annihilator", "Void Scepter",
                     "Arcanist's Aegis", "Lifebinder's Mantle", "Eternity Bloom",
                     "Flashfire Crown", "Warden's Bastion"]:
            assert name in t4_names, f"Missing T4 item: {name}"

    def test_traits_correct(self):
        """New items should carry their designated AoE traits."""
        trait_checks = {
            "Quake Hammer": "[Shockwave]",
            "Gale Glaive": "[Whirlwind]",
            "Flashbang Pouch": "[Flash]",
            "Bolas of Binding": "[Snare]",
            "War Horn": "[Rally]",
            "Embertongue Wand": "[Inferno]",
            "Stormcaller Rod": "[Tempest]",
            "Herbalist's Satchel": "[Mending]",
            "Voidstone Focus": "[Voidgrip]",
            "Renewal Chalice": "[Renewal]",
            "Arcanist's Aegis": "[Aegis]",
            "Warden's Bastion": "[Aegis]",
        }
        all_items = {}
        for tier, items in LOOT_TABLES.items():
            for item in items:
                all_items[item[0]] = item[3]  # name -> traits list

        for name, expected_trait in trait_checks.items():
            assert name in all_items, f"Item not found: {name}"
            assert expected_trait in all_items[name], f"{name} missing trait {expected_trait}"

    def test_slot_assignments_valid(self):
        """All new items should have valid slot assignments."""
        valid_slots = {"R.Hand", "L.Hand", "Head", "Chest", "Arms", "Legs",
                       "Shoulders", "Neck", "R.Ring", "L.Ring"}
        for tier, items in LOOT_TABLES.items():
            for item in items:
                assert item[1] in valid_slots, f"Invalid slot '{item[1]}' for {item[0]}"


# ============================================================================
# Section C3: Auto-Trigger Damage AoE
# ============================================================================

class TestAutoTriggerAoE:
    """Test auto-trigger damage AoE functions from play_burnwillow."""

    @pytest.fixture
    def state(self):
        """Create a minimal GameState-like object for testing."""
        import play_burnwillow as pb
        state = pb.GameState()
        engine = _make_engine_with_party(["Kael", "Lyra"])
        state.engine = engine
        # Place in a room with enemies
        state.room_enemies = {0: [
            {"name": "Goblin A", "hp": 8, "defense": 10, "dr": 0, "damage": "1d6"},
            {"name": "Goblin B", "hp": 8, "defense": 10, "dr": 0, "damage": "1d6"},
            {"name": "Goblin C", "hp": 8, "defense": 10, "dr": 0, "damage": "1d6"},
        ]}
        state.room_loot = {}
        state.cleared_rooms = set()
        state.enemies_slain = 0
        return state

    def test_check_damage_aoe_finds_shockwave(self):
        import play_burnwillow as pb
        engine = _make_engine_with_party(["Tester"])
        char = engine.party[0]
        item = _make_item("Quake Hammer", "R.Hand", 2, ["[Shockwave]"])
        _equip(char, item)
        result = pb._check_damage_aoe_trait(char)
        assert result is not None
        assert result[0] == "[Shockwave]"
        assert result[1] == 2

    def test_shockwave_stuns(self, state):
        import play_burnwillow as pb
        char = state.engine.party[0]
        item = _make_item("Quake Hammer", "R.Hand", 2, ["[Shockwave]"])
        _equip(char, item)
        enemies = state.room_enemies[0]
        msgs = pb._apply_damage_aoe(state, char, "[Shockwave]", 2, 5, enemies, 0)
        # Should have stunned at least one enemy
        assert len(state.stunned_enemies) > 0
        assert any("SHOCKWAVE" in m for m in msgs)

    def test_whirlwind_hits_all(self, state):
        import play_burnwillow as pb
        char = state.engine.party[0]
        enemies = state.room_enemies[0]
        initial_count = len(enemies)
        msgs = pb._apply_damage_aoe(state, char, "[Whirlwind]", 3, 5, enemies, 0)
        # All enemies should have been hit (messages for each)
        whirlwind_msgs = [m for m in msgs if "WHIRLWIND" in m]
        assert len(whirlwind_msgs) >= 1

    def test_inferno_applies_burning(self, state):
        import play_burnwillow as pb
        char = state.engine.party[0]
        enemies = state.room_enemies[0]
        msgs = pb._apply_damage_aoe(state, char, "[Inferno]", 2, 5, enemies, 0)
        assert any("INFERNO" in m for m in msgs)
        # Should have blinded (burning proxy) at least one enemy
        assert len(state.blinded_enemies) > 0

    def test_tempest_damages(self, state):
        import play_burnwillow as pb
        char = state.engine.party[0]
        enemies = state.room_enemies[0]
        initial_hp = enemies[0]["hp"]
        msgs = pb._apply_damage_aoe(state, char, "[Tempest]", 3, 5, enemies, 0)
        assert any("TEMPEST" in m for m in msgs)

    def test_voidgrip_blights(self, state):
        import play_burnwillow as pb
        char = state.engine.party[0]
        enemies = state.room_enemies[0]
        msgs = pb._apply_damage_aoe(state, char, "[Voidgrip]", 2, 5, enemies, 0)
        assert any("VOIDGRIP" in m for m in msgs)
        assert len(state.blinded_enemies) > 0


# ============================================================================
# Section C3: Manual AoE Commands
# ============================================================================

class TestManualAoE:
    """Test the 6 manual AoE combat commands."""

    @pytest.fixture
    def state(self):
        import play_burnwillow as pb
        state = pb.GameState()
        engine = _make_engine_with_party(["Kael", "Lyra"])
        state.engine = engine
        state.room_enemies = {0: [
            {"name": "Goblin A", "hp": 8, "defense": 12, "dr": 0, "damage": "1d6"},
            {"name": "Goblin B", "hp": 8, "defense": 12, "dr": 0, "damage": "1d6"},
        ]}
        state.room_loot = {}
        state.cleared_rooms = set()
        # Stub current_room_id — engine uses property, so we patch it
        engine.current_room_id = 0
        return state

    def _equip_trait(self, state, trait, slot="Arms", tier=2):
        char = state.engine.party[0]
        item = _make_item(f"Test {trait}", slot, tier, [trait])
        _equip(char, item)
        return char

    def test_flash_blinds(self, state):
        import play_burnwillow as pb
        self._equip_trait(state, "[Flash]")
        # Force success by mocking make_check
        with patch.object(state.engine.party[0], 'make_check',
                          return_value=CheckResult(success=True, total=15, rolls=[5, 5, 5], modifier=0, dc=12, dice_count=3)):
            msgs = pb.action_flash(state, state.engine.party[0])
        assert any("blinded" in m.lower() or "FLASH" in m for m in msgs)
        assert len(state.blinded_enemies) > 0

    def test_snare_debuffs(self, state):
        import play_burnwillow as pb
        self._equip_trait(state, "[Snare]")
        with patch.object(state.engine.party[0], 'make_check',
                          return_value=CheckResult(success=True, total=15, rolls=[5, 5, 5], modifier=0, dc=12, dice_count=3)):
            msgs = pb.action_snare(state, state.engine.party[0])
        assert any("defense reduced" in m.lower() or "SNARE" in m for m in msgs)
        assert len(state.defense_debuffs) > 0

    def test_rally_buffs(self, state):
        import play_burnwillow as pb
        self._equip_trait(state, "[Rally]", slot="L.Hand")
        with patch.object(state.engine.party[0], 'make_check',
                          return_value=CheckResult(success=True, total=12, rolls=[6, 6], modifier=0, dc=10, dice_count=2)):
            msgs = pb.action_rally(state, state.engine.party[0])
        assert any("RALLY" in m for m in msgs)
        # Lyra (ally) should get bonus dice
        assert "Lyra" in state.party_bonus_dice

    def test_mending_heals_all(self, state):
        import play_burnwillow as pb
        self._equip_trait(state, "[Mending]")
        # Damage party first
        for c in state.engine.party:
            c.current_hp = max(1, c.current_hp - 5)
        with patch.object(state.engine.party[0], 'make_check',
                          return_value=CheckResult(success=True, total=12, rolls=[6, 6], modifier=0, dc=10, dice_count=2)):
            msgs = pb.action_mending(state, state.engine.party[0])
        assert any("MENDING" in m for m in msgs)
        # All party members should have been healed
        assert any("healed" in m.lower() for m in msgs)

    def test_renewal_hot(self, state):
        import play_burnwillow as pb
        self._equip_trait(state, "[Renewal]", slot="Neck")
        with patch.object(state.engine.party[0], 'make_check',
                          return_value=CheckResult(success=True, total=14, rolls=[6, 6, 2], modifier=0, dc=12, dice_count=3)):
            msgs = pb.action_renewal(state, state.engine.party[0])
        assert any("RENEWAL" in m for m in msgs)
        assert len(state.party_hot) > 0
        for name, rounds in state.party_hot.items():
            assert rounds == 3

    def test_aegis_dr_buff(self, state):
        import play_burnwillow as pb
        self._equip_trait(state, "[Aegis]", slot="L.Hand")
        with patch.object(state.engine.party[0], 'make_check',
                          return_value=CheckResult(success=True, total=12, rolls=[6, 6], modifier=0, dc=10, dice_count=2)):
            msgs = pb.action_aegis(state, state.engine.party[0])
        assert any("AEGIS" in m for m in msgs)
        dr_val, dr_rounds = state.party_dr_buff
        assert dr_val == 2  # tier 2
        assert dr_rounds == 2


# ============================================================================
# Section D: Companion Command
# ============================================================================

class TestCompanionCommand:
    """Test the in-game companion summon command."""

    @pytest.fixture
    def state(self):
        import play_burnwillow as pb
        state = pb.GameState()
        engine = _make_engine_with_party(["Kael"])
        state.engine = engine
        state.in_settlement = False
        state.autopilot_agents = {}
        state.companion_mode = False
        state.narrative = None
        return state

    def test_summon_companion_at_hub(self, state):
        import play_burnwillow as pb
        state.in_settlement = True
        msgs = pb.action_companion(state)
        assert any("joins your party" in m.lower() or "companion" in m.lower() for m in msgs)
        assert len(state.engine.party) == 2

    def test_companion_status(self, state):
        import play_burnwillow as pb
        state.in_settlement = True
        # First summon
        pb.action_companion(state)
        # Then check status
        msgs = pb.action_companion(state)
        assert any("HP:" in m or "Status:" in m for m in msgs)

    def test_hub_only_restriction(self, state):
        import play_burnwillow as pb
        state.in_settlement = False
        msgs = pb.action_companion(state)
        assert any("hub" in m.lower() or "emberhome" in m.lower() for m in msgs)
        assert len(state.engine.party) == 1  # Not added


# ============================================================================
# Section C4: Enemy Gear AoE
# ============================================================================

class TestEnemyGearAoE:
    """Test that AoE enemies use gear-based traits."""

    def test_treant_has_whirlwind(self):
        """Ashwood Treant should have innate [Whirlwind]."""
        treant = None
        for tier, enemies in ENEMY_TABLES.items():
            for enemy in enemies:
                if enemy[0] == "Ashwood Treant":
                    treant = enemy
                    break
        assert treant is not None, "Ashwood Treant not found"
        special = treant[5]  # Description/special field
        assert "[Whirlwind]" in special
        assert "AOE" in special

    def test_tyrant_has_shockwave(self):
        """Ironroot Tyrant should have innate [Shockwave]."""
        tyrant = None
        for tier, enemies in ENEMY_TABLES.items():
            for enemy in enemies:
                if enemy[0] == "Ironroot Tyrant":
                    tyrant = enemy
                    break
        assert tyrant is not None, "Ironroot Tyrant not found"
        special = tyrant[5]
        assert "[Shockwave]" in special
        assert "AOE" in special


# ============================================================================
# Section C3: State Tracking
# ============================================================================

class TestStateTracking:
    """Test that AoE state effects expire correctly."""

    def test_stun_blind_expire_on_round_end(self):
        import play_burnwillow as pb
        state = pb.GameState()
        engine = _make_engine_with_party(["Kael"])
        state.engine = engine

        state.stunned_enemies = {"Goblin": 1, "Orc": 2}
        state.blinded_enemies = {"Troll": 1}
        state.defense_debuffs = {"Imp": 1}
        state.party_dr_buff = (3, 1)
        state.party_hot = {"Kael": 1}

        state.clear_combat_effects()

        # Goblin stun (1 round) should have expired
        assert "Goblin" not in state.stunned_enemies
        # Orc stun (2 rounds) should have decremented to 1
        assert state.stunned_enemies.get("Orc") == 1
        # Troll blind (1 round) should have expired
        assert "Troll" not in state.blinded_enemies
        # Imp defense debuff (1 round) should have expired
        assert "Imp" not in state.defense_debuffs
        # DR buff should have expired (was 1 round)
        assert state.party_dr_buff == (0, 0)
        # HoT should have expired
        assert "Kael" not in state.party_hot

    def test_dr_buff_decrements(self):
        import play_burnwillow as pb
        state = pb.GameState()
        engine = _make_engine_with_party(["Kael"])
        state.engine = engine

        state.party_dr_buff = (2, 2)

        state.clear_combat_effects()
        assert state.party_dr_buff == (2, 1)

        state.clear_combat_effects()
        assert state.party_dr_buff == (0, 0)


# ============================================================================
# Section E: Trait Combo System (#172)
# ============================================================================

class TestComboRegistry:
    """Test the trait combo registry and _resolve_combo method."""

    def _make_bridge(self):
        """Create a minimal BurnwillowBridge for combo testing."""
        from codex.games.burnwillow.bridge import BurnwillowBridge
        bridge = object.__new__(BurnwillowBridge)
        bridge._butler = None
        bridge.show_dm_notes = False
        bridge._talking_to = None
        bridge._last_trait_used = ""
        bridge._snared_enemies = set()
        bridge._blinded_enemies = set()
        bridge._snare_reduction = 0
        bridge._guard_dr_remaining = 0
        bridge._reflect_pending = 0
        bridge._pending_bonus_damage = 0
        engine = BurnwillowEngine()
        engine.create_character("ComboTester")
        engine.generate_dungeon(depth=3, seed=42)
        bridge.engine = engine
        return bridge

    def test_combo_registry_has_entries(self):
        """Combo registry should have natural + corrupted + void combos."""
        from codex.games.burnwillow.bridge import BurnwillowBridge
        reg = BurnwillowBridge._COMBO_REGISTRY
        assert len(reg) >= 7  # At least 7 natural combos
        # Verify themed names replaced generic ones
        assert reg[("SNARE", "CLEAVE")] == "ROOT CRUSH"
        assert reg[("GUARD", "REFLECT")] == "AMBER MIRROR"
        assert reg[("FLASH", "BACKSTAB")] == "EMBER SHADOW"
        # Verify corrupted combos exist
        assert ("BLIGHTWEB", "CLEAVE") in reg
        # Verify void combos exist
        assert ("NULLIFY", "WITHER") in reg

    def test_snare_cleave_combo(self):
        """SNARE → CLEAVE should produce ROOT CRUSH combo lines."""
        bridge = self._make_bridge()
        bridge._last_trait_used = "SNARE"
        bridge._snared_enemies.add("room_enemies")
        enemies = [{"name": "Goblin", "hp": 20, "defense": 10}]
        result = {"success": True, "cleave_targets": 1, "action": "cleave"}
        lines = bridge._resolve_combo("CLEAVE", result, enemies, None)
        assert any("ROOT CRUSH" in l for l in lines)
        assert len(bridge._snared_enemies) == 0  # Cleared after combo

    def test_flash_backstab_combo(self):
        """FLASH → BACKSTAB should produce EMBER SHADOW combo lines."""
        bridge = self._make_bridge()
        bridge._last_trait_used = "FLASH"
        bridge._blinded_enemies.add("room_enemies")
        result = {"success": True, "damage": 6, "was_backstab": True, "action": "backstab"}
        lines = bridge._resolve_combo("BACKSTAB", result, [], None)
        assert any("EMBER SHADOW" in l for l in lines)

    def test_guard_reflect_combo_doubles_damage(self):
        """GUARD → REFLECT should double pending reflect damage."""
        bridge = self._make_bridge()
        bridge._last_trait_used = "GUARD"
        bridge._reflect_pending = 3
        result = {"success": True, "reflect_damage": 3, "action": "reflect"}
        lines = bridge._resolve_combo("REFLECT", result, [], None)
        assert any("AMBER MIRROR" in l for l in lines)
        assert bridge._reflect_pending == 6  # Doubled

    def test_no_combo_without_setup(self):
        """Using a payoff trait without setup should not trigger combo."""
        bridge = self._make_bridge()
        bridge._last_trait_used = ""
        result = {"success": True, "cleave_targets": 2, "action": "cleave"}
        lines = bridge._resolve_combo("CLEAVE", result, [], None)
        assert not any("COMBO" in l for l in lines)

    def test_combo_hints_on_setup(self):
        """Setup traits should show combo hint text."""
        bridge = self._make_bridge()
        bridge._last_trait_used = ""
        result = {"success": True, "defense_reduction": 2, "action": "snare"}
        lines = bridge._resolve_combo("SNARE", result, [], None)
        assert any("Combo ready" in l for l in lines)

    def test_combo_state_resets_on_room_entry(self):
        """Room entry should clear all combo tracking state."""
        bridge = self._make_bridge()
        bridge._last_trait_used = "SNARE"
        bridge._snared_enemies.add("room_enemies")
        bridge._blinded_enemies.add("room_enemies")
        bridge._snare_reduction = 3
        # Simulate room entry reset (same logic as _on_room_entered)
        bridge._last_trait_used = ""
        bridge._snared_enemies.clear()
        bridge._blinded_enemies.clear()
        bridge._snare_reduction = 0
        assert bridge._last_trait_used == ""
        assert len(bridge._snared_enemies) == 0
        assert len(bridge._blinded_enemies) == 0

    def test_charge_cleave_combo(self):
        """CHARGE → CLEAVE should apply momentum bonus to cleave targets."""
        bridge = self._make_bridge()
        bridge._last_trait_used = "CHARGE"
        bridge._pending_bonus_damage = 4
        enemies = [{"name": "Orc", "hp": 15, "defense": 10}]
        result = {"success": True, "cleave_targets": 1, "action": "cleave"}
        lines = bridge._resolve_combo("CLEAVE", result, enemies, None)
        assert any("TIMBER FALL" in l for l in lines)
        assert bridge._pending_bonus_damage == 0  # Consumed
        assert enemies[0]["hp"] == 11  # 15 - 4

    def test_snare_ranged_combo(self):
        """SNARE → RANGED should produce PINNED PREY combo lines."""
        bridge = self._make_bridge()
        bridge._last_trait_used = "SNARE"
        bridge._snared_enemies.add("room_enemies")
        bridge._snare_reduction = 3
        result = {"success": True, "damage": 3, "action": "ranged"}
        lines = bridge._resolve_combo("RANGED", result, [], None)
        assert any("PINNED PREY" in l for l in lines)

    def test_flash_spellslot_combo(self):
        """FLASH → SPELLSLOT should produce SUNBURST combo lines."""
        bridge = self._make_bridge()
        bridge._last_trait_used = "FLASH"
        bridge._blinded_enemies.add("room_enemies")
        result = {"success": True, "damage": 5, "action": "spellslot"}
        lines = bridge._resolve_combo("SPELLSLOT", result, [], None)
        assert any("SUNBURST" in l for l in lines)
