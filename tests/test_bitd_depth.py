"""
tests/test_bitd_depth.py — WO-P2 BitD Depth tests
===================================================
Covers:
  - ClaimsMap: graph construction, claim/lose mechanics, persistence
  - BitDEngine: fortune/resist/gather_info commands, spend_coin, claim_territory,
    use_ability, save/load with claims state
"""

import pytest
from codex.games.bitd.claims import Claim, ClaimsMap, DEFAULT_CLAIMS
from codex.games.bitd import BitDEngine, BitDCharacter


# ===========================================================================
# ClaimsMap tests
# ===========================================================================


class TestClaimsMapConstruction:
    """ClaimsMap builds correctly from defaults."""

    def test_default_has_15_claims(self):
        m = ClaimsMap()
        assert len(m.claims) == 15

    def test_default_matches_default_claims_list(self):
        m = ClaimsMap()
        expected_names = {c["name"] for c in DEFAULT_CLAIMS}
        assert set(m.claims.keys()) == expected_names

    def test_lair_is_controlled_by_default(self):
        m = ClaimsMap()
        assert m.claims["Lair"].controlled is True

    def test_all_others_uncontrolled_by_default(self):
        m = ClaimsMap()
        uncontrolled = [name for name, c in m.claims.items() if name != "Lair" and c.controlled]
        assert uncontrolled == []

    def test_controlled_count_starts_at_1(self):
        m = ClaimsMap()
        assert m.controlled_count() == 1

    def test_adjacency_populated(self):
        m = ClaimsMap()
        # Lair is adjacent to Turf, Vice Den, and Fixer
        assert "Turf" in m.claims["Lair"].adjacent
        assert "Vice Den" in m.claims["Lair"].adjacent
        assert "Fixer" in m.claims["Lair"].adjacent


class TestClaimsMapClaim:
    """ClaimsMap.claim() adjacency and state logic."""

    def test_can_claim_adjacent_to_lair(self):
        m = ClaimsMap()
        result = m.claim("Turf")
        assert result["success"] is True
        assert result["name"] == "Turf"
        assert "benefit" in result

    def test_claim_sets_controlled_flag(self):
        m = ClaimsMap()
        m.claim("Turf")
        assert m.claims["Turf"].controlled is True

    def test_claim_increments_controlled_count(self):
        m = ClaimsMap()
        m.claim("Turf")
        assert m.controlled_count() == 2

    def test_cannot_claim_non_adjacent(self):
        # Covert Drops requires Warehouse, which requires many intermediate claims
        m = ClaimsMap()
        result = m.claim("Covert Drops")
        assert result["success"] is False
        assert "not adjacent" in result["error"]

    def test_cannot_re_claim_already_controlled(self):
        m = ClaimsMap()
        m.claim("Turf")
        result = m.claim("Turf")
        assert result["success"] is False
        assert "already controlled" in result["error"]

    def test_unknown_claim_name_returns_error(self):
        m = ClaimsMap()
        result = m.claim("Dragon's Lair")
        assert result["success"] is False
        assert "Unknown claim" in result["error"]

    def test_chain_claim_two_hops(self):
        """Claim Turf, then Hagfish Farm (adjacent to Turf)."""
        m = ClaimsMap()
        m.claim("Turf")
        result = m.claim("Hagfish Farm")
        assert result["success"] is True
        assert m.claims["Hagfish Farm"].controlled is True

    def test_cannot_skip_intermediary(self):
        """Hagfish Farm cannot be reached before Turf is controlled."""
        m = ClaimsMap()
        # Hagfish Farm is adjacent to Turf and Cover Operation — neither controlled yet
        result = m.claim("Hagfish Farm")
        assert result["success"] is False


class TestClaimsMapLose:
    """ClaimsMap.lose_claim() mechanics."""

    def test_lose_controlled_claim(self):
        m = ClaimsMap()
        m.claim("Turf")
        result = m.lose_claim("Turf")
        assert result["success"] is True
        assert m.claims["Turf"].controlled is False

    def test_lose_decrements_controlled_count(self):
        m = ClaimsMap()
        m.claim("Turf")
        m.lose_claim("Turf")
        assert m.controlled_count() == 1   # back to just Lair

    def test_cannot_lose_lair(self):
        m = ClaimsMap()
        result = m.lose_claim("Lair")
        assert result["success"] is False
        assert "Cannot lose the Lair" in result["error"]

    def test_cannot_lose_uncontrolled_claim(self):
        m = ClaimsMap()
        result = m.lose_claim("Turf")   # not yet claimed
        assert result["success"] is False
        assert "not controlled" in result["error"]

    def test_cannot_lose_unknown_claim(self):
        m = ClaimsMap()
        result = m.lose_claim("Phantom Node")
        assert result["success"] is False
        assert "Unknown claim" in result["error"]


class TestClaimsMapGetAvailable:
    """ClaimsMap.get_available() returns correct expandable nodes."""

    def test_available_from_lair_only(self):
        m = ClaimsMap()
        available = m.get_available()
        # Lair is adjacent to Turf, Vice Den, Fixer — all should be available
        assert "Turf" in available
        assert "Vice Den" in available
        assert "Fixer" in available

    def test_controlled_not_in_available(self):
        m = ClaimsMap()
        available = m.get_available()
        assert "Lair" not in available

    def test_available_expands_after_claim(self):
        m = ClaimsMap()
        m.claim("Turf")
        available = m.get_available()
        # Turf is adjacent to Hagfish Farm and Cover Operation
        assert "Hagfish Farm" in available
        assert "Cover Operation" in available

    def test_claimed_node_not_in_available(self):
        m = ClaimsMap()
        m.claim("Turf")
        available = m.get_available()
        assert "Turf" not in available


class TestClaimsMapDisplay:
    """ClaimsMap.display() output format."""

    def test_display_contains_all_claim_names(self):
        m = ClaimsMap()
        output = m.display()
        for name in m.claims:
            assert name in output

    def test_display_shows_controlled_marker(self):
        m = ClaimsMap()
        output = m.display()
        assert "[X]" in output   # Lair is controlled

    def test_display_shows_uncontrolled_marker(self):
        m = ClaimsMap()
        output = m.display()
        assert "[ ]" in output

    def test_display_shows_controlled_count(self):
        m = ClaimsMap()
        output = m.display()
        assert "Controlled: 1/15" in output

    def test_display_shows_available_section(self):
        m = ClaimsMap()
        output = m.display()
        assert "Available:" in output

    def test_display_after_claim(self):
        m = ClaimsMap()
        m.claim("Turf")
        output = m.display()
        assert "Controlled: 2/15" in output


class TestClaimsMapPersistence:
    """ClaimsMap.to_dict() / from_dict() round-trip."""

    def test_round_trip_preserves_controlled_flags(self):
        m = ClaimsMap()
        m.claim("Turf")
        m.claim("Vice Den")
        data = m.to_dict()
        m2 = ClaimsMap.from_dict(data)
        assert m2.claims["Turf"].controlled is True
        assert m2.claims["Vice Den"].controlled is True
        assert m2.claims["Fixer"].controlled is False

    def test_round_trip_lair_stays_controlled(self):
        m = ClaimsMap()
        data = m.to_dict()
        m2 = ClaimsMap.from_dict(data)
        assert m2.claims["Lair"].controlled is True

    def test_round_trip_controlled_count(self):
        m = ClaimsMap()
        m.claim("Turf")
        data = m.to_dict()
        m2 = ClaimsMap.from_dict(data)
        assert m2.controlled_count() == 2

    def test_round_trip_adjacency_intact(self):
        m = ClaimsMap()
        data = m.to_dict()
        m2 = ClaimsMap.from_dict(data)
        # After round-trip, Turf should still be claimable
        result = m2.claim("Turf")
        assert result["success"] is True

    def test_from_dict_empty_gives_fresh_map(self):
        m = ClaimsMap.from_dict({})
        assert len(m.claims) == 15
        assert m.claims["Lair"].controlled is True

    def test_to_dict_structure(self):
        m = ClaimsMap()
        data = m.to_dict()
        assert "claims" in data
        assert "Lair" in data["claims"]
        assert data["claims"]["Lair"]["controlled"] is True


# ===========================================================================
# BitDEngine command tests
# ===========================================================================


def _make_engine_with_char(playbook: str = "Cutter") -> BitDEngine:
    """Helper: fresh BitDEngine with a character registered."""
    eng = BitDEngine()
    eng.create_character("Silas", playbook=playbook, hunt=2, survey=1, consort=1)
    return eng


class TestBitDFortune:
    """fortune command via handle_command."""

    def test_fortune_returns_string(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("fortune", dice_count=2)
        assert isinstance(result, str)

    def test_fortune_contains_outcome(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("fortune", dice_count=2)
        assert any(word in result.upper() for word in ("BAD", "MIXED", "GOOD", "CRIT"))

    def test_fortune_zero_dice(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("fortune", dice_count=0)
        assert isinstance(result, str)
        assert "Fortune:" in result

    def test_fortune_default_dice(self):
        """No dice_count kwarg should default to 1 die."""
        eng = _make_engine_with_char()
        result = eng.handle_command("fortune")
        assert isinstance(result, str)


class TestBitDResist:
    """resist command via handle_command."""

    def test_resist_returns_string(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("resist", attribute="hunt")
        assert isinstance(result, str)

    def test_resist_contains_stress_cost(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("resist", attribute="hunt")
        assert "stress" in result.lower()

    def test_resist_no_character_returns_error(self):
        eng = BitDEngine()
        result = eng.handle_command("resist", attribute="hunt")
        assert "No active character" in result

    def test_resist_no_attribute_returns_error(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("resist")
        assert "Specify attribute" in result

    def test_resist_unknown_attribute_uses_zero_dice(self):
        """Unknown attribute resolves gracefully as 0-dice disadvantage roll."""
        eng = _make_engine_with_char()
        result = eng.handle_command("resist", attribute="nonexistent_action")
        assert isinstance(result, str)
        assert "stress" in result.lower()


class TestBitDGatherInfo:
    """gather_info command via handle_command."""

    def test_gather_info_returns_string(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("gather_info", action="survey", question="What guards are posted?")
        assert isinstance(result, str)

    def test_gather_info_contains_quality(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("gather_info", action="survey", question="Where is the vault?")
        assert "Quality:" in result

    def test_gather_info_includes_question(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("gather_info", action="survey", question="Where is the vault?")
        assert "Where is the vault?" in result

    def test_gather_info_default_action(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("gather_info", question="Who is the target?")
        assert isinstance(result, str)


class TestBitDSpendCoin:
    """spend_coin command."""

    def test_spend_coin_deducts_correctly(self):
        eng = _make_engine_with_char()
        eng.coin = 5
        eng.handle_command("spend_coin", amount=3, purpose="bribing the guard")
        assert eng.coin == 2

    def test_spend_coin_returns_remaining(self):
        eng = _make_engine_with_char()
        eng.coin = 5
        result = eng.handle_command("spend_coin", amount=2, purpose="bribing the guard")
        assert "Remaining: 3" in result

    def test_spend_coin_rejects_overspend(self):
        eng = _make_engine_with_char()
        eng.coin = 2
        result = eng.handle_command("spend_coin", amount=5, purpose="too much")
        assert "Insufficient coin" in result
        assert eng.coin == 2   # unchanged

    def test_spend_coin_rejects_zero(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("spend_coin", amount=0, purpose="nothing")
        assert "positive" in result.lower()

    def test_spend_coin_rejects_negative(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("spend_coin", amount=-1, purpose="nothing")
        assert "positive" in result.lower()

    def test_spend_coin_exact_amount(self):
        eng = _make_engine_with_char()
        eng.coin = 3
        result = eng.handle_command("spend_coin", amount=3, purpose="all-in")
        assert eng.coin == 0
        assert "Remaining: 0" in result


class TestBitDClaimTerritory:
    """claim_territory command."""

    def test_claim_territory_increments_turf(self):
        eng = _make_engine_with_char()
        eng.handle_command("claim_territory", name="Turf")
        assert eng.turf == 1

    def test_claim_territory_success_message(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("claim_territory", name="Turf")
        assert "Territory claimed: Turf" in result
        assert "Turf: 1" in result

    def test_claim_territory_non_adjacent_fails(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("claim_territory", name="Covert Drops")
        assert "not adjacent" in result
        assert eng.turf == 0

    def test_claim_territory_no_name_returns_usage(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("claim_territory")
        assert "claim_territory name=" in result

    def test_claim_territory_unknown_name_returns_error(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("claim_territory", name="Phantom Node")
        assert "Unknown claim" in result

    def test_claim_territory_already_controlled_fails(self):
        eng = _make_engine_with_char()
        eng.handle_command("claim_territory", name="Turf")
        result = eng.handle_command("claim_territory", name="Turf")
        assert "already controlled" in result
        assert eng.turf == 1   # only incremented once

    def test_claims_map_alias(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("claims_map")
        assert "Claims Map:" in result

    def test_claims_alias(self):
        eng = _make_engine_with_char()
        result = eng.handle_command("claims")
        assert "Claims Map:" in result


class TestBitDUseAbility:
    """use_ability command."""

    def test_use_ability_cutter_battleborn(self):
        eng = _make_engine_with_char("Cutter")
        result = eng.handle_command("use_ability", name="Battleborn")
        assert "Battleborn" in result
        assert "Silas" in result

    def test_use_ability_case_insensitive(self):
        eng = _make_engine_with_char("Cutter")
        result = eng.handle_command("use_ability", name="battleborn")
        assert "Battleborn" in result

    def test_use_ability_unknown_returns_error(self):
        eng = _make_engine_with_char("Cutter")
        result = eng.handle_command("use_ability", name="Shadow Walk")
        assert "Unknown ability" in result

    def test_use_ability_lists_available_on_failure(self):
        eng = _make_engine_with_char("Cutter")
        result = eng.handle_command("use_ability", name="Totally Fake Ability")
        assert "Available:" in result

    def test_use_ability_no_name_returns_usage(self):
        eng = _make_engine_with_char("Cutter")
        result = eng.handle_command("use_ability")
        assert "use_ability name=" in result

    def test_use_ability_no_character_returns_error(self):
        eng = BitDEngine()
        result = eng.handle_command("use_ability", name="Battleborn")
        assert "No active character" in result

    def test_use_ability_hound_sharpshooter(self):
        eng = _make_engine_with_char("Hound")
        result = eng.handle_command("use_ability", name="Sharpshooter")
        assert "Sharpshooter" in result


class TestBitDSaveLoadWithClaims:
    """save_state / load_state preserves claims map."""

    def test_save_without_claims_is_none(self):
        eng = _make_engine_with_char()
        state = eng.save_state()
        assert state["claims_map"] is None

    def test_save_after_claim_preserves_controlled(self):
        eng = _make_engine_with_char()
        eng.handle_command("claim_territory", name="Turf")
        state = eng.save_state()
        assert state["claims_map"] is not None
        assert state["claims_map"]["claims"]["Turf"]["controlled"] is True

    def test_load_restores_claims_state(self):
        eng = _make_engine_with_char()
        eng.handle_command("claim_territory", name="Turf")
        eng.handle_command("claim_territory", name="Vice Den")
        state = eng.save_state()

        eng2 = BitDEngine()
        eng2.load_state(state)
        claims = eng2._get_claims_map()
        assert claims.claims["Turf"].controlled is True
        assert claims.claims["Vice Den"].controlled is True
        assert claims.claims["Fixer"].controlled is False

    def test_load_no_claims_data_leaves_claims_none(self):
        eng = _make_engine_with_char()
        state = eng.save_state()
        assert state.get("claims_map") is None

        eng2 = BitDEngine()
        eng2.load_state(state)
        assert eng2._claims_map is None

    def test_load_preserves_lair_controlled(self):
        eng = _make_engine_with_char()
        eng.handle_command("claim_territory", name="Turf")
        state = eng.save_state()

        eng2 = BitDEngine()
        eng2.load_state(state)
        assert eng2._get_claims_map().claims["Lair"].controlled is True

    def test_round_trip_available_claims(self):
        eng = _make_engine_with_char()
        eng.handle_command("claim_territory", name="Turf")
        state = eng.save_state()

        eng2 = BitDEngine()
        eng2.load_state(state)
        available = eng2._get_claims_map().get_available()
        # After restoring Turf, Hagfish Farm and Cover Operation should be available
        assert "Hagfish Farm" in available
        assert "Cover Operation" in available
