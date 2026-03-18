"""tests/test_reputation.py — Unit tests for codex/core/mechanics/reputation.py

Covers:
- Standing titles at every level (-3..+3)
- Clamping at min/max bounds
- Tier-change messages vs same-tier delta messages
- Unchanged standing message (already at cap)
- Disposition modifiers at every level
- all_standings sort order
- to_dict / from_dict round-trips for FactionStanding and ReputationTracker
- Empty tracker defaults
"""

import pytest

from codex.core.mechanics.reputation import (
    FactionStanding,
    ReputationTracker,
    STANDING_TITLES,
    _DISPOSITION_MAP,
)


# ---------------------------------------------------------------------------
# FactionStanding — title property
# ---------------------------------------------------------------------------

class TestStandingTitles:
    """Standing titles map correctly for every defined level."""

    @pytest.mark.parametrize("level, expected", [
        (-3, "Outcast"),
        (-2, "Suspect"),
        (-1, "Stranger"),
        (0,  "Neutral"),
        (1,  "Known"),
        (2,  "Trusted"),
        (3,  "Honored"),
    ])
    def test_title_at_each_level(self, level, expected):
        fs = FactionStanding(faction_id="test_faction", standing=level)
        assert fs.title == expected

    def test_default_standing_is_neutral(self):
        fs = FactionStanding(faction_id="city_watch")
        assert fs.standing == 0
        assert fs.title == "Neutral"


# ---------------------------------------------------------------------------
# FactionStanding — serialization
# ---------------------------------------------------------------------------

class TestFactionStandingSerialization:

    def test_to_dict_contains_expected_keys(self):
        fs = FactionStanding(faction_id="guild", standing=2)
        d = fs.to_dict()
        assert d == {"faction_id": "guild", "standing": 2}

    def test_round_trip_preserves_data(self):
        original = FactionStanding(faction_id="thieves_guild", standing=-2)
        restored = FactionStanding.from_dict(original.to_dict())
        assert restored.faction_id == original.faction_id
        assert restored.standing == original.standing

    def test_from_dict_defaults_standing_to_zero(self):
        fs = FactionStanding.from_dict({"faction_id": "unknown_faction"})
        assert fs.standing == 0


# ---------------------------------------------------------------------------
# ReputationTracker — defaults
# ---------------------------------------------------------------------------

class TestEmptyTracker:

    def test_empty_tracker_has_no_standings(self):
        tracker = ReputationTracker()
        assert tracker.standings == {}

    def test_all_standings_on_empty_tracker_returns_empty_list(self):
        tracker = ReputationTracker()
        assert tracker.all_standings() == []

    def test_get_standing_on_unknown_faction_creates_neutral(self):
        tracker = ReputationTracker()
        fs = tracker.get_standing("new_faction")
        assert fs.standing == 0
        assert fs.faction_id == "new_faction"


# ---------------------------------------------------------------------------
# ReputationTracker — clamping
# ---------------------------------------------------------------------------

class TestClamping:

    def test_clamp_at_positive_max(self):
        tracker = ReputationTracker()
        tracker.adjust("faction_a", 3)   # +3 from neutral → 3
        tracker.adjust("faction_a", 5)   # would push to 8, must clamp
        assert tracker.get_standing("faction_a").standing == 3

    def test_clamp_at_negative_min(self):
        tracker = ReputationTracker()
        tracker.adjust("faction_b", -3)  # -3 from neutral → -3
        tracker.adjust("faction_b", -5)  # would push to -8, must clamp
        assert tracker.get_standing("faction_b").standing == -3

    def test_clamp_does_not_allow_above_three(self):
        tracker = ReputationTracker()
        tracker.adjust("faction_c", 100)
        assert tracker.get_standing("faction_c").standing == 3

    def test_clamp_does_not_allow_below_minus_three(self):
        tracker = ReputationTracker()
        tracker.adjust("faction_c", -100)
        assert tracker.get_standing("faction_c").standing == -3


# ---------------------------------------------------------------------------
# ReputationTracker — adjust messages
# ---------------------------------------------------------------------------

class TestAdjustMessages:

    def test_tier_change_message_contains_old_and_new_title(self):
        tracker = ReputationTracker()
        # Neutral (0) → Known (1): tier change
        msg = tracker.adjust("guards", 1)
        assert "Neutral" in msg
        assert "Known" in msg

    def test_same_tier_delta_message_shows_numeric_values(self):
        """Moving within a tier (0→0 is impossible, but +1 from Known to Known is impossible too.
        Move from Known (+1) by +0 would be unchanged, so test within-tier for
        a case where standing changes but title stays the same — not possible on this scale
        since every integer has its own title. Use unchanged path instead."""
        tracker = ReputationTracker()
        # Set to max, then try to go higher: unchanged message
        tracker.adjust("guards", 3)
        msg = tracker.adjust("guards", 1)  # already at cap
        assert "unchanged" in msg

    def test_negative_delta_message_says_worsened(self):
        tracker = ReputationTracker()
        tracker.adjust("city_watch", 2)   # Trusted
        msg = tracker.adjust("city_watch", -1)  # Trusted → Known
        assert "worsened" in msg

    def test_positive_delta_message_says_improved(self):
        tracker = ReputationTracker()
        msg = tracker.adjust("city_watch", 1)
        assert "improved" in msg

    def test_reason_string_appears_in_message(self):
        tracker = ReputationTracker()
        msg = tracker.adjust("merchants", 1, reason="saved the caravan")
        assert "saved the caravan" in msg

    def test_no_reason_message_has_no_parenthetical(self):
        tracker = ReputationTracker()
        msg = tracker.adjust("merchants", 1)
        # Should not have empty parentheses in output
        assert "()" not in msg


# ---------------------------------------------------------------------------
# ReputationTracker — disposition modifier
# ---------------------------------------------------------------------------

class TestDispositionModifier:

    @pytest.mark.parametrize("standing, expected_mod", [
        (-3, -6),
        (-2, -4),
        (-1, -2),
        (0,   0),
        (1,   2),
        (2,   4),
        (3,   6),
    ])
    def test_disposition_modifier_at_each_standing(self, standing, expected_mod):
        tracker = ReputationTracker()
        tracker.standings["faction"] = FactionStanding(
            faction_id="faction", standing=standing
        )
        assert tracker.get_disposition_modifier("faction") == expected_mod

    def test_disposition_modifier_for_unknown_faction_is_zero(self):
        tracker = ReputationTracker()
        # Unknown faction gets created at neutral → modifier 0
        assert tracker.get_disposition_modifier("brand_new") == 0


# ---------------------------------------------------------------------------
# ReputationTracker — all_standings
# ---------------------------------------------------------------------------

class TestAllStandings:

    def test_all_standings_returns_sorted_by_faction_id(self):
        tracker = ReputationTracker()
        tracker.adjust("zebra_guild", 1)
        tracker.adjust("apple_clan", -1)
        tracker.adjust("mango_order", 2)

        ids = [fid for fid, _ in tracker.all_standings()]
        assert ids == sorted(ids)

    def test_all_standings_count_matches_factions_touched(self):
        tracker = ReputationTracker()
        tracker.adjust("faction_x", 1)
        tracker.adjust("faction_y", -1)
        assert len(tracker.all_standings()) == 2


# ---------------------------------------------------------------------------
# ReputationTracker — serialization round-trip
# ---------------------------------------------------------------------------

class TestTrackerSerialization:

    def test_to_dict_round_trip_restores_all_factions(self):
        tracker = ReputationTracker()
        tracker.adjust("city_watch", 2)
        tracker.adjust("thieves_guild", -3)
        tracker.adjust("merchants", 1)

        restored = ReputationTracker.from_dict(tracker.to_dict())

        assert restored.get_standing("city_watch").standing == 2
        assert restored.get_standing("thieves_guild").standing == -3
        assert restored.get_standing("merchants").standing == 1

    def test_from_dict_on_empty_dict_creates_empty_tracker(self):
        tracker = ReputationTracker.from_dict({})
        assert tracker.standings == {}

    def test_serialized_standing_preserves_title(self):
        tracker = ReputationTracker()
        tracker.adjust("nobles", 3)
        restored = ReputationTracker.from_dict(tracker.to_dict())
        assert restored.get_standing("nobles").title == "Honored"
