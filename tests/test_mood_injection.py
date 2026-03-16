"""
tests/test_mood_injection.py — WO-V61.0 Track B: Narrative Mood Injection
==========================================================================

Verifies:
  1. Every registered engine returns a valid get_mood_context() dict.
  2. BurnwillowEngine tension scales correctly with HP and DoomClock state.
  3. FITD engines (BitD representative) scale with stress and trauma.
  4. Mood context appears in _build_affordance_context() output.
  5. play_burnwillow._MOOD_OVERLAYS is well-formed.
"""

from __future__ import annotations

import pytest


# =========================================================================
# TestEngineMoodContext
# =========================================================================

class TestEngineMoodContext:
    """Verify each engine returns a structurally valid get_mood_context() dict."""

    REQUIRED_KEYS = {"tension", "tone_words", "party_condition", "system_specific"}

    def _assert_valid_mood(self, mood: dict, engine_name: str) -> None:
        assert isinstance(mood, dict), f"{engine_name}: get_mood_context() must return dict"
        missing = self.REQUIRED_KEYS - mood.keys()
        assert not missing, f"{engine_name}: mood dict missing keys: {missing}"
        tension = mood["tension"]
        assert isinstance(tension, float), f"{engine_name}: tension must be float, got {type(tension)}"
        assert 0.0 <= tension <= 1.0, f"{engine_name}: tension {tension} out of [0, 1]"
        assert isinstance(mood["tone_words"], list), f"{engine_name}: tone_words must be list"
        assert isinstance(mood["party_condition"], str), (
            f"{engine_name}: party_condition must be str"
        )

    def test_burnwillow_engine(self):
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        engine.create_party(["Test"])
        engine.generate_dungeon(seed=42)
        mood = engine.get_mood_context()
        self._assert_valid_mood(mood, "BurnwillowEngine")

    def test_dnd5e_engine(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Test")
        mood = engine.get_mood_context()
        self._assert_valid_mood(mood, "DnD5eEngine")

    def test_cosmere_engine(self):
        from codex.games.stc import CosmereEngine
        engine = CosmereEngine()
        engine.create_character("Test")
        mood = engine.get_mood_context()
        self._assert_valid_mood(mood, "CosmereEngine")

    def test_bitd_engine(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Test")
        mood = engine.get_mood_context()
        self._assert_valid_mood(mood, "BitDEngine")

    def test_sav_engine(self):
        from codex.games.sav import SaVEngine
        engine = SaVEngine()
        engine.create_character("Test")
        mood = engine.get_mood_context()
        self._assert_valid_mood(mood, "SaVEngine")

    def test_bob_engine(self):
        from codex.games.bob import BoBEngine
        engine = BoBEngine()
        engine.create_character("Test")
        mood = engine.get_mood_context()
        self._assert_valid_mood(mood, "BoBEngine")

    def test_cbrpnk_engine(self):
        from codex.games.cbrpnk import CBRPNKEngine
        engine = CBRPNKEngine()
        engine.create_character("Test")
        mood = engine.get_mood_context()
        self._assert_valid_mood(mood, "CBRPNKEngine")

    def test_candela_engine(self):
        from codex.games.candela import CandelaEngine
        engine = CandelaEngine()
        engine.create_character("Test")
        mood = engine.get_mood_context()
        self._assert_valid_mood(mood, "CandelaEngine")

    def test_crown_engine(self):
        from codex.games.crown.engine import CrownAndCrewEngine
        engine = CrownAndCrewEngine()
        mood = engine.get_mood_context()
        self._assert_valid_mood(mood, "CrownAndCrewEngine")


# =========================================================================
# TestBurnwillowMoodScaling
# =========================================================================

class TestBurnwillowMoodScaling:
    """Test that BurnwillowEngine tension scales correctly with game state."""

    def test_healthy_party_low_doom(self):
        """Full HP + low doom = healthy condition, low tension."""
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        engine.create_party(["Hero"])
        engine.generate_dungeon(seed=42)
        mood = engine.get_mood_context()
        assert mood["party_condition"] == "healthy", (
            f"Expected 'healthy', got '{mood['party_condition']}'"
        )
        assert mood["tension"] < 0.5, (
            f"Expected tension < 0.5 for fresh party, got {mood['tension']}"
        )

    def test_low_hp_raises_tension(self):
        """Low HP pushes party_condition to battered or critical and tension above 0.5."""
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        engine.create_party(["Hero"])
        engine.generate_dungeon(seed=42)
        char = engine.party[0]
        char.current_hp = 1  # Nearly dead
        mood = engine.get_mood_context()
        assert mood["party_condition"] in ("battered", "critical"), (
            f"Expected 'battered' or 'critical' with 1 HP, got '{mood['party_condition']}'"
        )
        assert mood["tension"] > 0.5, (
            f"Expected tension > 0.5 with near-zero HP, got {mood['tension']}"
        )

    def test_critical_hp_condition(self):
        """HP below 25% max triggers 'critical' condition."""
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        engine.create_party(["Hero"])
        engine.generate_dungeon(seed=42)
        char = engine.party[0]
        # Force HP to below 25% of max
        char.current_hp = max(1, char.max_hp // 5)
        mood = engine.get_mood_context()
        assert mood["party_condition"] == "critical", (
            f"Expected 'critical' at <25% HP (hp={char.current_hp}/{char.max_hp}), "
            f"got '{mood['party_condition']}'"
        )

    def test_battered_hp_range(self):
        """HP between 25% and 50% of max triggers 'battered' condition."""
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        engine.create_party(["Hero"])
        engine.generate_dungeon(seed=42)
        char = engine.party[0]
        # Force HP to ~35% of max (battered range: 25%-50%)
        char.current_hp = max(1, int(char.max_hp * 0.35))
        mood = engine.get_mood_context()
        assert mood["party_condition"] == "battered", (
            f"Expected 'battered' at ~35% HP (hp={char.current_hp}/{char.max_hp}), "
            f"got '{mood['party_condition']}'"
        )

    def test_high_doom_desperate(self):
        """High doom (>75%) pushes tension above 0.7."""
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        engine.create_party(["Hero"])
        engine.generate_dungeon(seed=42)
        # Push doom to 80% (16/20)
        engine.doom_clock.filled = 16
        mood = engine.get_mood_context()
        assert mood["tension"] > 0.7, (
            f"Expected tension > 0.7 with doom at 80%, got {mood['tension']}"
        )

    def test_doom_desperate_condition_with_full_hp(self):
        """High doom + full HP => 'desperate' condition (doom path, not hp path)."""
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        engine.create_party(["Hero"])
        engine.generate_dungeon(seed=42)
        # Full HP, doom at 80%
        char = engine.party[0]
        char.current_hp = char.max_hp
        engine.doom_clock.filled = 16
        mood = engine.get_mood_context()
        assert mood["party_condition"] == "desperate", (
            f"Expected 'desperate' at full HP + high doom, got '{mood['party_condition']}'"
        )

    def test_tone_words_present_for_critical(self):
        """Critical HP condition includes tone words."""
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        engine.create_party(["Hero"])
        engine.generate_dungeon(seed=42)
        char = engine.party[0]
        char.current_hp = 1
        mood = engine.get_mood_context()
        assert len(mood["tone_words"]) > 0, "Expected tone_words for critical condition"

    def test_healthy_no_tone_words(self):
        """Healthy party with low doom has no tone words."""
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        engine.create_party(["Hero"])
        engine.generate_dungeon(seed=42)
        mood = engine.get_mood_context()
        assert mood["tone_words"] == [], (
            f"Expected empty tone_words for healthy party, got {mood['tone_words']}"
        )

    def test_system_specific_includes_doom(self):
        """system_specific dict includes doom and doom_pct keys."""
        from codex.games.burnwillow.engine import BurnwillowEngine
        engine = BurnwillowEngine()
        engine.create_party(["Hero"])
        engine.generate_dungeon(seed=42)
        engine.doom_clock.filled = 8
        mood = engine.get_mood_context()
        ss = mood["system_specific"]
        assert "doom" in ss, f"system_specific missing 'doom' key: {ss}"
        assert "doom_pct" in ss, f"system_specific missing 'doom_pct' key: {ss}"
        assert ss["doom"] == 8
        assert abs(ss["doom_pct"] - 0.4) < 0.01


# =========================================================================
# TestFITDMoodScaling
# =========================================================================

class TestFITDMoodScaling:
    """Test FITD engine (BitD) tension scales with stress and trauma."""

    def test_no_stress_healthy(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Scoundrel")
        mood = engine.get_mood_context()
        assert mood["party_condition"] == "healthy", (
            f"Expected 'healthy' with 0 stress, got '{mood['party_condition']}'"
        )
        assert mood["tension"] < 0.3, (
            f"Expected tension < 0.3 with 0 stress, got {mood['tension']}"
        )

    def test_high_stress_battered(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Scoundrel")
        clock = engine.stress_clocks[engine.character.name]
        clock.current_stress = 6  # 6/9 = 67%
        mood = engine.get_mood_context()
        assert mood["party_condition"] == "battered", (
            f"Expected 'battered' at 6/9 stress, got '{mood['party_condition']}'"
        )
        assert mood["tension"] > 0.5, (
            f"Expected tension > 0.5 at 6/9 stress, got {mood['tension']}"
        )

    def test_trauma_adds_tone_words(self):
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Scoundrel")
        clock = engine.stress_clocks[engine.character.name]
        clock.traumas = ["cold", "paranoid"]  # 2 traumas triggers haunted/fractured
        mood = engine.get_mood_context()
        assert len(mood["tone_words"]) > 0, (
            "Expected tone_words with 2+ traumas"
        )
        assert "haunted" in mood["tone_words"], (
            f"Expected 'haunted' in tone_words with 2 traumas, got {mood['tone_words']}"
        )

    def test_single_trauma_battered(self):
        """One trauma (any stress level) pushes condition to at least battered."""
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Scoundrel")
        clock = engine.stress_clocks[engine.character.name]
        clock.traumas = ["reckless"]
        mood = engine.get_mood_context()
        assert mood["party_condition"] in ("battered", "critical"), (
            f"Expected battered/critical with 1 trauma, got '{mood['party_condition']}'"
        )

    def test_critical_stress_condition(self):
        """Stress above 80% triggers critical condition."""
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Scoundrel")
        clock = engine.stress_clocks[engine.character.name]
        clock.current_stress = 8  # 8/9 ≈ 89%
        mood = engine.get_mood_context()
        assert mood["party_condition"] == "critical", (
            f"Expected 'critical' at 8/9 stress, got '{mood['party_condition']}'"
        )

    def test_three_traumas_critical(self):
        """Three or more traumas triggers critical condition regardless of stress."""
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Scoundrel")
        clock = engine.stress_clocks[engine.character.name]
        clock.traumas = ["cold", "paranoid", "haunted"]
        mood = engine.get_mood_context()
        assert mood["party_condition"] == "critical", (
            f"Expected 'critical' with 3 traumas, got '{mood['party_condition']}'"
        )

    def test_tension_bounded(self):
        """tension is always clamped to [0.0, 1.0] even with many traumas."""
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Scoundrel")
        clock = engine.stress_clocks[engine.character.name]
        clock.current_stress = 9
        clock.traumas = ["cold", "paranoid", "haunted", "reckless"]
        mood = engine.get_mood_context()
        assert 0.0 <= mood["tension"] <= 1.0, (
            f"tension out of bounds: {mood['tension']}"
        )

    def test_system_specific_contains_stress(self):
        """system_specific dict includes stress and trauma_count."""
        from codex.games.bitd import BitDEngine
        engine = BitDEngine()
        engine.create_character("Scoundrel")
        clock = engine.stress_clocks[engine.character.name]
        clock.current_stress = 3
        clock.traumas = ["paranoid"]
        mood = engine.get_mood_context()
        ss = mood["system_specific"]
        assert "stress" in ss, f"system_specific missing 'stress': {ss}"
        assert "trauma_count" in ss, f"system_specific missing 'trauma_count': {ss}"
        assert ss["stress"] == 3
        assert ss["trauma_count"] == 1


# =========================================================================
# TestMoodInAffordanceContext
# =========================================================================

class TestMoodInAffordanceContext:
    """Verify mood appears in narrative_frame._build_affordance_context() output."""

    def test_mood_injected_when_available(self):
        """When engine has mood context, it appears in affordance string."""
        from unittest.mock import MagicMock
        from codex.core.services.narrative_frame import _build_affordance_context

        engine = MagicMock()
        engine.get_current_room.return_value = {
            "tier": 1, "type": "hallway", "enemies": [], "loot": [],
        }
        engine.get_cardinal_exits.return_value = [{"direction": "N", "id": 1}]
        engine.get_mood_context.return_value = {
            "tension": 0.9,
            "tone_words": ["desperate", "bleeding"],
            "party_condition": "critical",
            "system_specific": {},
        }
        result = _build_affordance_context(engine)
        assert "desperate" in result, f"Expected 'desperate' in result: {result!r}"
        assert "critical" in result, f"Expected 'critical' in result: {result!r}"
        assert "urgent" in result.lower(), (
            f"Expected 'urgent' for tension=0.9 in result: {result!r}"
        )

    def test_no_mood_when_engine_lacks_method(self):
        """When engine has no get_mood_context, affordance still works."""
        from unittest.mock import MagicMock
        from codex.core.services.narrative_frame import _build_affordance_context

        # spec=[] means MagicMock has no attributes — hasattr() returns False
        engine = MagicMock(spec=[])
        engine.get_current_room = MagicMock(
            return_value={"tier": 1, "type": "room", "enemies": [], "loot": []}
        )
        engine.get_cardinal_exits = MagicMock(return_value=[])
        result = _build_affordance_context(engine)
        assert "Mood" not in result, (
            f"Expected no 'Mood' key without get_mood_context, got: {result!r}"
        )

    def test_low_tension_no_urgency(self):
        """Low tension does not add urgency hint."""
        from unittest.mock import MagicMock
        from codex.core.services.narrative_frame import _build_affordance_context

        engine = MagicMock()
        engine.get_current_room.return_value = {
            "tier": 1, "type": "room", "enemies": [], "loot": [],
        }
        engine.get_cardinal_exits.return_value = []
        engine.get_mood_context.return_value = {
            "tension": 0.3,
            "tone_words": [],
            "party_condition": "healthy",
            "system_specific": {},
        }
        result = _build_affordance_context(engine)
        assert "urgent" not in result.lower(), (
            f"Expected no 'urgent' for tension=0.3, got: {result!r}"
        )

    def test_empty_tone_words_no_mood_line(self):
        """Engine with empty tone_words does not produce a Mood: line."""
        from unittest.mock import MagicMock
        from codex.core.services.narrative_frame import _build_affordance_context

        engine = MagicMock()
        engine.get_current_room.return_value = {
            "tier": 2, "type": "chamber", "enemies": [], "loot": [],
        }
        engine.get_cardinal_exits.return_value = []
        engine.get_mood_context.return_value = {
            "tension": 0.2,
            "tone_words": [],
            "party_condition": "healthy",
            "system_specific": {},
        }
        result = _build_affordance_context(engine)
        assert "Mood:" not in result, (
            f"Expected no 'Mood:' line with empty tone_words, got: {result!r}"
        )

    def test_high_tension_without_tone_words_still_urgent(self):
        """High tension (>0.7) adds urgency hint even with empty tone_words."""
        from unittest.mock import MagicMock
        from codex.core.services.narrative_frame import _build_affordance_context

        engine = MagicMock()
        engine.get_current_room.return_value = {
            "tier": 4, "type": "boss", "enemies": [], "loot": [],
        }
        engine.get_cardinal_exits.return_value = []
        engine.get_mood_context.return_value = {
            "tension": 0.85,
            "tone_words": [],
            "party_condition": "critical",
            "system_specific": {},
        }
        result = _build_affordance_context(engine)
        assert "urgent" in result.lower(), (
            f"Expected 'urgent' for tension=0.85, got: {result!r}"
        )

    def test_affordance_still_returns_room_info_with_mood(self):
        """Mood injection doesn't clobber the base room state info."""
        from unittest.mock import MagicMock
        from codex.core.services.narrative_frame import _build_affordance_context

        room_data = {
            "tier": 3,
            "type": "vault",
            "enemies": [{"name": "Guardian"}],
            "loot": [{"name": "Gold"}],
        }
        engine = MagicMock()
        # _build_affordance_context prefers get_current_room_dict — configure both
        engine.get_current_room.return_value = room_data
        engine.get_current_room_dict.return_value = room_data
        engine.get_cardinal_exits.return_value = [{"direction": "S", "id": 2}]
        engine.get_mood_context.return_value = {
            "tension": 0.8,
            "tone_words": ["foreboding"],
            "party_condition": "battered",
            "system_specific": {},
        }
        result = _build_affordance_context(engine)
        assert "ROOM STATE" in result, "Expected ROOM STATE prefix"
        assert "Tier 3" in result, "Expected Tier 3 in result"
        assert "Guardian" in result, "Expected enemy name in result"
        assert "foreboding" in result, "Expected tone word in result"


# =========================================================================
# TestMoodOverlay
# =========================================================================

class TestMoodOverlay:
    """Verify play_burnwillow._MOOD_OVERLAYS is well-formed."""

    def test_mood_overlays_defined(self):
        """_MOOD_OVERLAYS has the expected condition keys."""
        from play_burnwillow import _MOOD_OVERLAYS
        assert "critical" in _MOOD_OVERLAYS, "Missing 'critical' key"
        assert "battered" in _MOOD_OVERLAYS, "Missing 'battered' key"
        assert "desperate" in _MOOD_OVERLAYS, "Missing 'desperate' key"

    def test_each_overlay_has_strings(self):
        """Every overlay list contains at least one non-empty string."""
        from play_burnwillow import _MOOD_OVERLAYS
        for key, overlays in _MOOD_OVERLAYS.items():
            assert len(overlays) >= 1, f"Overlay '{key}' is empty"
            for item in overlays:
                assert isinstance(item, str), (
                    f"Overlay '{key}' contains non-string item: {item!r}"
                )
                assert item.strip(), f"Overlay '{key}' contains blank string"

    def test_overlay_values_are_lists(self):
        """All overlay values are lists."""
        from play_burnwillow import _MOOD_OVERLAYS
        for key, value in _MOOD_OVERLAYS.items():
            assert isinstance(value, list), (
                f"_MOOD_OVERLAYS['{key}'] should be a list, got {type(value)}"
            )

    def test_no_duplicate_overlays_within_key(self):
        """Each overlay list has no duplicate entries."""
        from play_burnwillow import _MOOD_OVERLAYS
        for key, overlays in _MOOD_OVERLAYS.items():
            assert len(overlays) == len(set(overlays)), (
                f"_MOOD_OVERLAYS['{key}'] has duplicate entries"
            )
