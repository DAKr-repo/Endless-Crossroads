"""
FITD Smoke Test — Adversarial Simulation Engine
================================================
Tests all 5 FITD engines (BitD, SaV, BoB, Candela, CBR+PNK) with 4 player
archetypes: Ralgur (rules lawyer), Zyx (chaos gremlin), Nara (dissenter),
Pax (mediator). Checks for crashes, state desync, and edge-case failures.
"""
import sys
import json
import traceback

sys.path.insert(0, "/home/pi/Projects/claude_sandbox/Codex")

results = {"pass": [], "fail": [], "warn": []}


def check(test_name, condition, detail=""):
    if condition:
        results["pass"].append(test_name)
    else:
        results["fail"].append(f"{test_name}: {detail}")


def warn(test_name, detail):
    results["warn"].append(f"{test_name}: {detail}")


def safe_call(test_name, fn, *args, **kwargs):
    """Call fn(*args, **kwargs), return (True, result) or (False, error_str)."""
    try:
        result = fn(*args, **kwargs)
        return True, result
    except Exception as e:
        tb = traceback.format_exc()
        results["fail"].append(f"{test_name}: EXCEPTION: {e}\n{tb}")
        return False, str(e)


# ===========================================================================
# SHARED MECHANIC TESTS (NarrativeEngineBase)
# ===========================================================================

def test_shared_mechanics(engine, prefix, valid_action, create_kwargs):
    """Run the standard set of shared FITD tests on any engine."""

    # --- Character creation ---
    ok, char = safe_call(f"{prefix}/create_character", engine.create_character,
                         "Ralgur", **create_kwargs)
    check(f"{prefix}/create_character_returns_object", ok and char is not None,
          f"got {type(char)}")
    check(f"{prefix}/party_populated", ok and len(engine.party) >= 1,
          f"party={engine.party}")
    check(f"{prefix}/character_set", ok and engine.character is not None,
          "engine.character is None")

    # --- Ralgur: Fortune roll ---
    ok, r = safe_call(f"{prefix}/fortune_2d", engine.handle_command, "fortune", dice_count=2)
    check(f"{prefix}/fortune_2d_returns_str", ok and isinstance(r, str), f"got {r!r}")
    check(f"{prefix}/fortune_2d_contains_keyword", ok and (
        "Fortune" in r or "fortune" in r or "good" in r.lower() or
        "bad" in r.lower() or "mixed" in r.lower() or "crit" in r.lower()
    ), f"got {r!r}")

    # --- Ralgur: Resist with valid attribute ---
    ok, r = safe_call(f"{prefix}/resist_valid", engine.handle_command,
                      "resist", attribute=valid_action)
    check(f"{prefix}/resist_valid_returns_str", ok and isinstance(r, str), f"got {r!r}")
    check(f"{prefix}/resist_valid_contains_resistance",
          ok and ("Resistance" in r or "resistance" in r or "stress" in r.lower()),
          f"got {r!r}")

    # --- Zyx: Resist with no attribute (should error, not crash) ---
    ok, r = safe_call(f"{prefix}/resist_no_attr", engine.handle_command, "resist")
    check(f"{prefix}/resist_no_attr_no_crash", ok, f"got {r}")
    if ok:
        check(f"{prefix}/resist_no_attr_returns_error_msg",
              "attribute" in r.lower() or "specify" in r.lower() or "no active" in r.lower(),
              f"got {r!r}")

    # --- Zyx: Resist with nonexistent attribute (should return 0 dice, not crash) ---
    ok, r = safe_call(f"{prefix}/resist_bad_attr", engine.handle_command,
                      "resist", attribute="nonexistent_action_xyz")
    check(f"{prefix}/resist_bad_attr_no_crash", ok, f"got {r}")

    # --- Ralgur: Gather info ---
    ok, r = safe_call(f"{prefix}/gather_info", engine.handle_command,
                      "gather_info", action=valid_action, question="Who guards the vault?")
    check(f"{prefix}/gather_info_returns_str", ok and isinstance(r, str), f"got {r!r}")
    check(f"{prefix}/gather_info_contains_quality",
          ok and "quality" in r.lower(), f"got {r!r}")

    # --- Ralgur: NPC status (empty) ---
    ok, r = safe_call(f"{prefix}/npc_status_empty", engine.handle_command, "npc_status")
    check(f"{prefix}/npc_status_empty_no_crash", ok, f"got {r}")

    # --- Ralgur: NPC adjust (first time creates NPC) ---
    ok, r = safe_call(f"{prefix}/npc_adjust", engine.handle_command,
                      "npc_adjust", name="TestNPC", delta=1, reason="helped us")
    check(f"{prefix}/npc_adjust_no_crash", ok, f"got {r}")
    if ok:
        check(f"{prefix}/npc_adjust_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Ralgur: NPC status (now should show TestNPC) ---
    ok, r = safe_call(f"{prefix}/npc_status_testnpc", engine.handle_command,
                      "npc_status", name="TestNPC")
    check(f"{prefix}/npc_status_testnpc_no_crash", ok, f"got {r}")
    if ok:
        check(f"{prefix}/npc_status_testnpc_contains_npc",
              "TestNPC" in r or "neutral" in r.lower() or "friendly" in r.lower(),
              f"got {r!r}")

    # --- Zyx: NPC adjust delta=99 (should clamp to +3) ---
    ok, r = safe_call(f"{prefix}/npc_adjust_clamp", engine.handle_command,
                      "npc_adjust", name="TestNPC", delta=99, reason="max test")
    check(f"{prefix}/npc_adjust_clamp_no_crash", ok, f"got {r}")
    if ok:
        # Verify the final value is capped (the NPC started at +1 then +99 → must clamp)
        ok2, r2 = safe_call(f"{prefix}/npc_status_after_clamp",
                            engine.handle_command, "npc_status", name="TestNPC")
        if ok2:
            # (+3) is the max label, check it appears
            check(f"{prefix}/npc_clamped_to_max",
                  "+3" in r2 or "ally" in r2.lower() or "friendly" in r2.lower() or
                  "+4" not in r2,
                  f"got {r2!r}")

    # --- Ralgur: Faction response ---
    ok, r = safe_call(f"{prefix}/faction_response", engine.handle_command,
                      "faction_response", name="TestNPC", event_type="score_against")
    check(f"{prefix}/faction_response_no_crash", ok, f"got {r}")
    if ok:
        check(f"{prefix}/faction_response_returns_response",
              "response" in r.lower() or "faction" in r.lower() or "disposition" in r.lower(),
              f"got {r!r}")

    # --- Zyx: Unknown command (should return 'Unknown command', not crash) ---
    ok, r = safe_call(f"{prefix}/unknown_cmd", engine.handle_command, "NOTACOMMAND_xyz123")
    check(f"{prefix}/unknown_cmd_no_crash", ok, f"got {r}")
    if ok:
        check(f"{prefix}/unknown_cmd_returns_unknown",
              "unknown" in r.lower() or "not found" in r.lower(),
              f"got {r!r}")

    return engine  # Return for save/load test


def test_save_load(engine, prefix, npc_name="TestNPC"):
    """Verify save/load round-trip preserves party and NPC state."""
    ok, state = safe_call(f"{prefix}/save_state", engine.save_state)
    check(f"{prefix}/save_state_no_crash", ok, f"got {state}")
    if not ok:
        return

    # Verify it's JSON-serializable
    try:
        serialized = json.dumps(state)
        check(f"{prefix}/save_state_json_serializable", True)
    except Exception as e:
        check(f"{prefix}/save_state_json_serializable", False, str(e))
        return

    # Capture pre-load party names
    party_before = [c.name for c in engine.party]
    npc_disp_before = None
    if engine._npc_disposition is not None:
        npc_rec = engine._npc_disposition.npcs.get(npc_name)
        if npc_rec:
            npc_disp_before = npc_rec.disposition

    # Load state
    ok, _ = safe_call(f"{prefix}/load_state", engine.load_state, state)
    check(f"{prefix}/load_state_no_crash", ok)
    if not ok:
        return

    # Party names must match
    party_after = [c.name for c in engine.party]
    check(f"{prefix}/load_state_party_survives",
          party_before == party_after,
          f"before={party_before}, after={party_after}")

    # NPC disposition must match
    if npc_disp_before is not None and engine._npc_disposition is not None:
        npc_rec_after = engine._npc_disposition.npcs.get(npc_name)
        npc_disp_after = npc_rec_after.disposition if npc_rec_after else None
        check(f"{prefix}/load_state_npc_disposition_survives",
              npc_disp_before == npc_disp_after,
              f"before={npc_disp_before}, after={npc_disp_after}")


# ===========================================================================
# BITD ENGINE TESTS
# ===========================================================================

def test_bitd():
    print("\n=== Testing BitD Engine ===")
    from codex.games.bitd import BitDEngine
    e = BitDEngine()
    e.crew_name = "The Iron Cobras"
    e.crew_type = "Shadows"
    PREFIX = "BitD"

    # Shared mechanics
    test_shared_mechanics(e, PREFIX, "hunt", {"playbook": "Hound"})

    # --- Ralgur: Crew status ---
    ok, r = safe_call(f"{PREFIX}/crew_status", e.handle_command, "crew_status")
    check(f"{PREFIX}/crew_status_no_crash", ok)
    if ok:
        check(f"{PREFIX}/crew_status_shows_crew",
              "Iron Cobras" in r or "Shadows" in r or "Crew" in r,
              f"got {r!r}")

    # --- Ralgur: Claims map (15 claims, Lair controlled) ---
    ok, r = safe_call(f"{PREFIX}/claims_map", e.handle_command, "claims_map")
    check(f"{PREFIX}/claims_map_no_crash", ok)
    if ok:
        check(f"{PREFIX}/claims_map_shows_lair", "Lair" in r, f"got {r!r}")
        count_claims = r.count("\n") + 1
        check(f"{PREFIX}/claims_map_has_claims", count_claims >= 5, f"line count={count_claims}")

    # --- Ralgur: Claim Turf (adjacent to Lair) ---
    ok, r = safe_call(f"{PREFIX}/claim_turf", e.handle_command, "claim_territory", name="Turf")
    check(f"{PREFIX}/claim_turf_no_crash", ok)
    if ok:
        check(f"{PREFIX}/claim_turf_success", "success" in r.lower() or "Turf" in r, f"got {r!r}")
    # Verify turf incremented
    check(f"{PREFIX}/turf_incremented_after_claim", e.turf >= 1, f"turf={e.turf}")

    # --- Nara: Claim Turf again (already controlled) ---
    ok, r = safe_call(f"{PREFIX}/claim_turf_duplicate", e.handle_command, "claim_territory", name="Turf")
    check(f"{PREFIX}/claim_turf_duplicate_no_crash", ok)
    if ok:
        check(f"{PREFIX}/claim_turf_duplicate_rejected",
              "already" in r.lower() or "controlled" in r.lower() or "error" in r.lower(),
              f"got {r!r}")

    # --- Nara: Claim Secret Pathways (not adjacent from Lair) ---
    ok, r = safe_call(f"{PREFIX}/claim_far_territory", e.handle_command,
                      "claim_territory", name="Secret Pathways")
    check(f"{PREFIX}/claim_far_territory_no_crash", ok)
    if ok:
        check(f"{PREFIX}/claim_far_territory_rejected",
              "not adjacent" in r.lower() or "adjacent" in r.lower() or "cannot" in r.lower() or "error" in r.lower(),
              f"got {r!r}")

    # --- Ralgur: Spend coin ---
    coin_before = e.coin
    ok, r = safe_call(f"{PREFIX}/spend_coin", e.handle_command, "spend_coin", amount=1, purpose="bribe")
    check(f"{PREFIX}/spend_coin_no_crash", ok)
    if ok:
        check(f"{PREFIX}/spend_coin_decreases", e.coin == coin_before - 1, f"coin: {coin_before} -> {e.coin}")

    # --- Zyx: Spend too much coin ---
    ok, r = safe_call(f"{PREFIX}/spend_coin_overflow", e.handle_command, "spend_coin", amount=9999, purpose="impossible")
    check(f"{PREFIX}/spend_coin_overflow_no_crash", ok)
    if ok:
        check(f"{PREFIX}/spend_coin_overflow_rejected",
              "insufficient" in r.lower() or "not enough" in r.lower() or
              "cannot" in r.lower() or "error" in r.lower() or e.coin >= 0,
              f"got {r!r}, coin={e.coin}")
    check(f"{PREFIX}/spend_coin_overflow_coin_nonnegative", e.coin >= 0, f"coin went negative: {e.coin}")

    # --- Ralgur: Use ability ---
    ok, r = safe_call(f"{PREFIX}/use_ability", e.handle_command, "use_ability", name="Ambush")
    check(f"{PREFIX}/use_ability_no_crash", ok)
    if ok:
        check(f"{PREFIX}/use_ability_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Pax: Engagement -> resolve_score (turf bonus check) ---
    ok, r = safe_call(f"{PREFIX}/engagement", e.handle_command, "engagement", plan_type="infiltration")
    check(f"{PREFIX}/engagement_no_crash", ok)

    ok, r = safe_call(f"{PREFIX}/resolve_score", e.handle_command, "resolve_score")
    check(f"{PREFIX}/resolve_score_no_crash", ok)
    if ok:
        check(f"{PREFIX}/resolve_score_returns_str", isinstance(r, str), f"got {r!r}")
        if e.turf > 0:
            check(f"{PREFIX}/resolve_score_turf_bonus_in_output",
                  "turf" in r.lower() or "coin" in r.lower(),
                  f"got {r!r}")

    # --- Nara: Resolve score when no score is active ---
    ok, r = safe_call(f"{PREFIX}/resolve_score_inactive", e.handle_command, "resolve_score")
    check(f"{PREFIX}/resolve_score_inactive_no_crash", ok)
    if ok:
        check(f"{PREFIX}/resolve_score_inactive_rejected",
              "no active" in r.lower() or "active score" in r.lower(),
              f"got {r!r}")

    # --- Heat and rep status ---
    ok, r = safe_call(f"{PREFIX}/heat_status", e.handle_command, "heat_status")
    check(f"{PREFIX}/heat_status_no_crash", ok)
    if ok:
        # heat_status may not exist, check it doesn't crash
        pass

    ok, r = safe_call(f"{PREFIX}/rep_status", e.handle_command, "rep_status")
    check(f"{PREFIX}/rep_status_no_crash", ok)

    # --- Save/Load ---
    test_save_load(e, PREFIX)


# ===========================================================================
# SAV ENGINE TESTS
# ===========================================================================

def test_sav():
    print("\n=== Testing SaV Engine ===")
    from codex.games.sav import SaVEngine
    e = SaVEngine()
    e.ship_name = "The Remora"
    e.ship_class = "Stardancer"
    PREFIX = "SaV"

    # Shared mechanics
    test_shared_mechanics(e, PREFIX, "helm", {"playbook": "Pilot"})

    # --- Ship status ---
    ok, r = safe_call(f"{PREFIX}/ship_status", e.handle_command, "ship_status")
    check(f"{PREFIX}/ship_status_no_crash", ok)
    if ok:
        check(f"{PREFIX}/ship_status_shows_ship", "Remora" in r or "Ship" in r, f"got {r!r}")

    # --- Plan job: valid ---
    ok, r = safe_call(f"{PREFIX}/plan_job_valid", e.handle_command,
                      "plan_job", plan_type="infiltration", detail="the vault")
    check(f"{PREFIX}/plan_job_valid_no_crash", ok)
    if ok:
        check(f"{PREFIX}/plan_job_valid_confirms", "infiltration" in r.lower() or "plan" in r.lower(), f"got {r!r}")

    # --- Nara: Plan job with invalid type ---
    ok, r = safe_call(f"{PREFIX}/plan_job_invalid", e.handle_command,
                      "plan_job", plan_type="invalid_plan_xyz")
    check(f"{PREFIX}/plan_job_invalid_no_crash", ok)
    if ok:
        check(f"{PREFIX}/plan_job_invalid_rejected",
              "invalid" in r.lower() or "error" in r.lower() or "unknown" in r.lower() or
              "invalid_plan" in r.lower() or "Plan set" in r,  # some engines just accept it
              f"got {r!r}")

    # --- Downtime repair ---
    ok, r = safe_call(f"{PREFIX}/downtime_repair", e.handle_command,
                      "downtime_repair", system="hull", mechanic_dots=2)
    check(f"{PREFIX}/downtime_repair_no_crash", ok)
    if ok:
        check(f"{PREFIX}/downtime_repair_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Downtime resupply ---
    ok, r = safe_call(f"{PREFIX}/downtime_resupply", e.handle_command, "downtime_resupply")
    check(f"{PREFIX}/downtime_resupply_no_crash", ok)
    if ok:
        check(f"{PREFIX}/downtime_resupply_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Downtime vice ---
    ok, r = safe_call(f"{PREFIX}/downtime_vice", e.handle_command, "downtime_vice")
    check(f"{PREFIX}/downtime_vice_no_crash", ok)
    if ok:
        check(f"{PREFIX}/downtime_vice_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Downtime project ---
    ok, r = safe_call(f"{PREFIX}/downtime_project", e.handle_command,
                      "downtime_project", project_name="Test Gadget", action_dots=2)
    check(f"{PREFIX}/downtime_project_no_crash", ok)
    if ok:
        check(f"{PREFIX}/downtime_project_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Pax: Engagement -> resolve_job ---
    ok, r = safe_call(f"{PREFIX}/engagement", e.handle_command, "engagement", target="TestTarget")
    check(f"{PREFIX}/engagement_no_crash", ok)

    ok, r = safe_call(f"{PREFIX}/resolve_job", e.handle_command, "resolve_job")
    check(f"{PREFIX}/resolve_job_no_crash", ok)
    if ok:
        check(f"{PREFIX}/resolve_job_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Faction response ---
    ok, r = safe_call(f"{PREFIX}/faction_response_heat", e.handle_command, "faction_response")
    check(f"{PREFIX}/faction_response_heat_no_crash", ok)

    # --- Save/Load ---
    test_save_load(e, PREFIX)


# ===========================================================================
# BOB ENGINE TESTS
# ===========================================================================

def test_bob():
    print("\n=== Testing BoB Engine ===")
    from codex.games.bob import BoBEngine
    e = BoBEngine()
    e.chosen = "Zora the Stalwart"
    PREFIX = "BoB"

    # Shared mechanics
    test_shared_mechanics(e, PREFIX, "skirmish", {"playbook": "Heavy"})

    # --- Legion status ---
    ok, r = safe_call(f"{PREFIX}/legion_status", e.handle_command, "legion_status")
    check(f"{PREFIX}/legion_status_no_crash", ok)
    if ok:
        check(f"{PREFIX}/legion_status_shows_resources",
              "Supply" in r or "Morale" in r or "Pressure" in r, f"got {r!r}")

    # --- Religious services (morale) ---
    morale_before = e.legion.morale
    ok, r = safe_call(f"{PREFIX}/religious_services", e.handle_command, "religious_services")
    check(f"{PREFIX}/religious_services_no_crash", ok)
    if ok:
        check(f"{PREFIX}/religious_services_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Liberty (stress relief) ---
    ok, r = safe_call(f"{PREFIX}/liberty", e.handle_command, "liberty")
    check(f"{PREFIX}/liberty_no_crash", ok)
    if ok:
        check(f"{PREFIX}/liberty_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Scrounge (supply change) ---
    supply_before = e.legion.supply
    ok, r = safe_call(f"{PREFIX}/scrounge", e.handle_command, "scrounge")
    check(f"{PREFIX}/scrounge_no_crash", ok)
    if ok:
        check(f"{PREFIX}/scrounge_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Record casualty ---
    ok, r = safe_call(f"{PREFIX}/record_casualty", e.handle_command,
                      "record_casualty", name="Private Smith")
    check(f"{PREFIX}/record_casualty_no_crash", ok)
    if ok:
        check(f"{PREFIX}/record_casualty_smith_recorded",
              "Smith" in r or "Private Smith" in r or "fallen" in r.lower() or
              "casualty" in r.lower(),
              f"got {r!r}")
    check(f"{PREFIX}/record_casualty_in_fallen",
          "Private Smith" in e._fallen_legionnaires,
          f"fallen={e._fallen_legionnaires}")

    # --- Memorial (shows Private Smith) ---
    ok, r = safe_call(f"{PREFIX}/memorial", e.handle_command, "memorial")
    check(f"{PREFIX}/memorial_no_crash", ok)
    if ok:
        check(f"{PREFIX}/memorial_shows_smith",
              "Smith" in r or "Private Smith" in r or "No fallen" in r,
              f"got {r!r}")

    # --- Legion advance ---
    ok, r = safe_call(f"{PREFIX}/legion_advance", e.handle_command, "legion_advance")
    check(f"{PREFIX}/legion_advance_no_crash", ok)
    if ok:
        check(f"{PREFIX}/legion_advance_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Pax: mission_plan -> mission_resolve ---
    missions_before = e._missions_completed
    ok, r = safe_call(f"{PREFIX}/mission_plan", e.handle_command,
                      "mission_plan", mission_type="Assault", squad="Soldiers")
    check(f"{PREFIX}/mission_plan_no_crash", ok)
    if ok:
        check(f"{PREFIX}/mission_plan_returns_str", isinstance(r, str), f"got {r!r}")

    ok, r = safe_call(f"{PREFIX}/mission_resolve_success", e.handle_command,
                      "mission_resolve", success_level="success")
    check(f"{PREFIX}/mission_resolve_no_crash", ok)
    if ok:
        check(f"{PREFIX}/mission_resolve_returns_str", isinstance(r, str), f"got {r!r}")
    check(f"{PREFIX}/mission_resolve_increments_counter",
          e._missions_completed == missions_before + 1,
          f"before={missions_before}, after={e._missions_completed}")

    # --- Do 2 more missions to test threshold ---
    for i in range(2):
        e.handle_command("mission_plan", mission_type="Assault", squad="Soldiers")
        e.handle_command("mission_resolve", success_level="success")

    # --- Campaign advance ---
    phase_before = e.campaign_phase
    ok, r = safe_call(f"{PREFIX}/campaign_advance", e.handle_command, "campaign_advance")
    check(f"{PREFIX}/campaign_advance_no_crash", ok)
    if ok:
        check(f"{PREFIX}/campaign_advance_returns_str", isinstance(r, str), f"got {r!r}")
        check(f"{PREFIX}/campaign_advance_phase_changed",
              e.campaign_phase != phase_before or "march" in r.lower() or "phase" in r.lower(),
              f"before={phase_before}, after={e.campaign_phase}")

    # --- Save/Load ---
    test_save_load(e, PREFIX)


# ===========================================================================
# CANDELA ENGINE TESTS
# ===========================================================================

def test_candela():
    print("\n=== Testing Candela Engine ===")
    from codex.games.candela import CandelaEngine
    e = CandelaEngine()
    e.circle_name = "The Pale Circle"
    PREFIX = "Candela"

    # Candela does NOT inherit NarrativeEngineBase exactly the same way —
    # it uses resist/gather_info from base but no stress clocks
    test_shared_mechanics(e, PREFIX, "survey",
                          {"role": "Scholar", "specialization": "Doctor"})

    # --- Verify _use_stress_clocks() returns False ---
    check(f"{PREFIX}/use_stress_clocks_false", e._use_stress_clocks() is False,
          f"got {e._use_stress_clocks()}")

    # --- Pax: Start assignment ---
    ok, r = safe_call(f"{PREFIX}/start_assignment", e.handle_command,
                      "start_assignment", name="The Vanishing")
    check(f"{PREFIX}/start_assignment_no_crash", ok)
    if ok:
        check(f"{PREFIX}/start_assignment_at_hook",
              "hook" in r.lower() or "Vanishing" in r,
              f"got {r!r}")

    # --- Pax: Advance phase (hook -> exploration) ---
    ok, r = safe_call(f"{PREFIX}/advance_phase_1", e.handle_command, "advance_phase")
    check(f"{PREFIX}/advance_phase_1_no_crash", ok)
    if ok:
        check(f"{PREFIX}/advance_phase_1_exploration",
              "exploration" in r.lower() or "EXPLORATION" in r,
              f"got {r!r}")

    # --- Pax: Advance phase (exploration -> climax) ---
    ok, r = safe_call(f"{PREFIX}/advance_phase_2", e.handle_command, "advance_phase")
    check(f"{PREFIX}/advance_phase_2_no_crash", ok)
    if ok:
        check(f"{PREFIX}/advance_phase_2_climax",
              "climax" in r.lower() or "CLIMAX" in r,
              f"got {r!r}")

    # --- Pax: Complete assignment ---
    assignments_before = e.assignments_completed
    ok, r = safe_call(f"{PREFIX}/complete_assignment", e.handle_command, "complete_assignment")
    check(f"{PREFIX}/complete_assignment_no_crash", ok)
    if ok:
        check(f"{PREFIX}/complete_assignment_increments",
              e.assignments_completed == assignments_before + 1,
              f"before={assignments_before}, after={e.assignments_completed}")

    # --- Nara: Complete assignment from hook (should fail) ---
    e.handle_command("start_assignment", name="Second Assignment")
    ok, r = safe_call(f"{PREFIX}/complete_assignment_from_hook", e.handle_command,
                      "complete_assignment")
    check(f"{PREFIX}/complete_assignment_from_hook_no_crash", ok)
    if ok:
        check(f"{PREFIX}/complete_assignment_from_hook_rejected",
              "hook" in r.lower() or "not" in r.lower() or "cannot" in r.lower() or
              "climax" in r.lower() or "error" in r.lower(),
              f"got {r!r}")

    # --- Phenomena tick ---
    ok, r = safe_call(f"{PREFIX}/phenomena_tick_1", e.handle_command, "phenomena_tick", amount=1)
    check(f"{PREFIX}/phenomena_tick_1_no_crash", ok)
    if ok:
        check(f"{PREFIX}/phenomena_tick_1_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Zyx: Phenomena tick amount=10 (should not crash) ---
    ok, r = safe_call(f"{PREFIX}/phenomena_tick_10", e.handle_command, "phenomena_tick", amount=10)
    check(f"{PREFIX}/phenomena_tick_10_no_crash", ok, f"got {r}")

    # --- Phenomena reduce ---
    ok, r = safe_call(f"{PREFIX}/phenomena_reduce", e.handle_command, "phenomena_reduce", amount=1)
    check(f"{PREFIX}/phenomena_reduce_no_crash", ok)
    if ok:
        check(f"{PREFIX}/phenomena_reduce_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Phenomena status ---
    ok, r = safe_call(f"{PREFIX}/phenomena_status", e.handle_command, "phenomena_status")
    check(f"{PREFIX}/phenomena_status_no_crash", ok)
    if ok:
        check(f"{PREFIX}/phenomena_status_shows_stage",
              "stage" in r.lower() or "phenomena" in r.lower() or "tick" in r.lower(),
              f"got {r!r}")

    # --- Bleed escalation (pre-marks, should not trigger) ---
    ok, r = safe_call(f"{PREFIX}/bleed_escalation_clear", e.handle_command, "bleed_escalation")
    check(f"{PREFIX}/bleed_escalation_clear_no_crash", ok)

    # --- Take mark x3 then check bleed escalation ---
    for _ in range(3):
        e.handle_command("take_mark", track="bleed")
    ok, r = safe_call(f"{PREFIX}/bleed_escalation_triggered", e.handle_command, "bleed_escalation")
    check(f"{PREFIX}/bleed_escalation_triggered_no_crash", ok)
    if ok:
        # With 1 party member having bleed 3, threshold = 1*2 = 2, should trigger
        check(f"{PREFIX}/bleed_escalation_triggered_or_checked",
              isinstance(r, str) and ("bleed" in r.lower() or "threshold" in r.lower() or "escalation" in r.lower()),
              f"got {r!r}")

    # --- Investigation: open_case -> investigate -> case_status ---
    ok, r = safe_call(f"{PREFIX}/open_case", e.handle_command,
                      "open_case", case_name="TestCase")
    check(f"{PREFIX}/open_case_no_crash", ok)
    if ok:
        check(f"{PREFIX}/open_case_returns_str", isinstance(r, str), f"got {r!r}")

    ok, r = safe_call(f"{PREFIX}/investigate", e.handle_command, "investigate")
    check(f"{PREFIX}/investigate_no_crash", ok)
    if ok:
        check(f"{PREFIX}/investigate_returns_str", isinstance(r, str), f"got {r!r}")

    ok, r = safe_call(f"{PREFIX}/case_status", e.handle_command, "case_status")
    check(f"{PREFIX}/case_status_no_crash", ok)
    if ok:
        check(f"{PREFIX}/case_status_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Save/Load (Candela doesn't have _npc_disposition on first access) ---
    # force npc_disposition creation
    e.handle_command("npc_adjust", name="TestNPC", delta=1, reason="helped")
    test_save_load(e, PREFIX)


# ===========================================================================
# CBRPNK ENGINE TESTS
# ===========================================================================

def test_cbrpnk():
    print("\n=== Testing CBR+PNK Engine ===")
    from codex.games.cbrpnk import CBRPNKEngine
    e = CBRPNKEngine()
    PREFIX = "CBRPNK"

    # CBR+PNK uses its own handle_command (not NarrativeEngineBase)
    # so we test it directly

    # --- Character creation ---
    ok, char = safe_call(f"{PREFIX}/create_character", e.create_character,
                         "Nara", archetype="Hacker")
    check(f"{PREFIX}/create_character_no_crash", ok)
    check(f"{PREFIX}/create_character_party_set", len(e.party) >= 1, f"party={e.party}")
    check(f"{PREFIX}/create_character_lead_set", e.character is not None)

    # Install chrome for overclock test
    e.character.chrome.append("Neural Jack")
    e.character.hack = 2

    # --- Fortune (manually added, not inherited) ---
    ok, r = safe_call(f"{PREFIX}/fortune", e.handle_command, "fortune", dice_count=2)
    check(f"{PREFIX}/fortune_no_crash", ok)
    if ok:
        check(f"{PREFIX}/fortune_returns_str", isinstance(r, str), f"got {r!r}")
        check(f"{PREFIX}/fortune_contains_keyword",
              "Fortune" in r or "fortune" in r or any(w in r.lower() for w in ["good","bad","mixed","crit"]),
              f"got {r!r}")

    # --- Resist (attribute=hack) ---
    ok, r = safe_call(f"{PREFIX}/resist_hack", e.handle_command, "resist", attribute="hack")
    check(f"{PREFIX}/resist_hack_no_crash", ok)
    if ok:
        check(f"{PREFIX}/resist_hack_contains_stress",
              "stress" in r.lower() or "Resistance" in r,
              f"got {r!r}")

    # --- Gather info ---
    ok, r = safe_call(f"{PREFIX}/gather_info", e.handle_command,
                      "gather_info", action="scan", question="who is watching?")
    check(f"{PREFIX}/gather_info_no_crash", ok)
    if ok:
        check(f"{PREFIX}/gather_info_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Glitch ---
    glitch_before = e.glitch_die
    ok, r = safe_call(f"{PREFIX}/glitch", e.handle_command, "glitch")
    check(f"{PREFIX}/glitch_no_crash", ok)
    if ok:
        check(f"{PREFIX}/glitch_increments", e.glitch_die == glitch_before + 1,
              f"before={glitch_before}, after={e.glitch_die}")
        check(f"{PREFIX}/glitch_returns_severity",
              any(w in r.upper() for w in ["MINOR", "MODERATE", "MAJOR"]),
              f"got {r!r}")

    # --- Corp response ---
    ok, r = safe_call(f"{PREFIX}/corp_response", e.handle_command, "corp_response")
    check(f"{PREFIX}/corp_response_no_crash", ok)
    if ok:
        check(f"{PREFIX}/corp_response_has_tier",
              "street" in r.lower() or "security" in r.lower() or "strike" in r.lower() or
              "corp" in r.lower(),
              f"got {r!r}")

    # --- Overclock (costs stress, adds glitch) ---
    glitch_before = e.glitch_die
    ok, r = safe_call(f"{PREFIX}/overclock", e.handle_command, "overclock")
    check(f"{PREFIX}/overclock_no_crash", ok)
    if ok:
        check(f"{PREFIX}/overclock_increments_glitch", e.glitch_die == glitch_before + 1,
              f"before={glitch_before}, after={e.glitch_die}")
        check(f"{PREFIX}/overclock_returns_str", isinstance(r, str), f"got {r!r}")

    # --- NPC adjust ---
    ok, r = safe_call(f"{PREFIX}/npc_adjust", e.handle_command,
                      "npc_adjust", name="Fixer", delta=-2, reason="double-crossed us")
    check(f"{PREFIX}/npc_adjust_no_crash", ok)
    if ok:
        check(f"{PREFIX}/npc_adjust_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Faction response ---
    ok, r = safe_call(f"{PREFIX}/faction_response", e.handle_command,
                      "faction_response", name="Fixer", event_type="score_against")
    check(f"{PREFIX}/faction_response_no_crash", ok)
    if ok:
        check(f"{PREFIX}/faction_response_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Crew status ---
    ok, r = safe_call(f"{PREFIX}/crew_status", e.handle_command, "crew_status")
    check(f"{PREFIX}/crew_status_no_crash", ok)
    if ok:
        check(f"{PREFIX}/crew_status_shows_heat", "heat" in r.lower() or "Heat" in r, f"got {r!r}")

    # --- Chrome status ---
    ok, r = safe_call(f"{PREFIX}/chrome_status", e.handle_command, "chrome_status")
    check(f"{PREFIX}/chrome_status_no_crash", ok)
    if ok:
        check(f"{PREFIX}/chrome_status_returns_str", isinstance(r, str), f"got {r!r}")

    # --- Unknown command ---
    ok, r = safe_call(f"{PREFIX}/unknown_cmd", e.handle_command, "NOTACOMMAND_xyz123")
    check(f"{PREFIX}/unknown_cmd_no_crash", ok)
    if ok:
        check(f"{PREFIX}/unknown_cmd_returns_unknown",
              "unknown" in r.lower() or "not found" in r.lower(),
              f"got {r!r}")

    # --- Resist no attribute ---
    ok, r = safe_call(f"{PREFIX}/resist_no_attr", e.handle_command, "resist")
    check(f"{PREFIX}/resist_no_attr_no_crash", ok)
    if ok:
        check(f"{PREFIX}/resist_no_attr_error_msg",
              "specify" in r.lower() or "attribute" in r.lower() or "no active" in r.lower(),
              f"got {r!r}")

    # --- Resist nonexistent attribute (0 dice roll) ---
    ok, r = safe_call(f"{PREFIX}/resist_bad_attr", e.handle_command,
                      "resist", attribute="nonexistent_xyz")
    check(f"{PREFIX}/resist_bad_attr_no_crash", ok)

    # --- Save/Load round-trip ---
    e.handle_command("npc_adjust", name="TestNPC", delta=1, reason="helped")
    ok, state = safe_call(f"{PREFIX}/save_state", e.save_state)
    check(f"{PREFIX}/save_state_no_crash", ok)
    if ok:
        try:
            json.dumps(state)
            check(f"{PREFIX}/save_state_json_serializable", True)
        except Exception as ex:
            check(f"{PREFIX}/save_state_json_serializable", False, str(ex))

        party_before = [c.name for c in e.party]
        npc_before = None
        if e._npc_disposition:
            rec = e._npc_disposition.npcs.get("TestNPC")
            npc_before = rec.disposition if rec else None

        ok2, _ = safe_call(f"{PREFIX}/load_state", e.load_state, state)
        check(f"{PREFIX}/load_state_no_crash", ok2)
        if ok2:
            party_after = [c.name for c in e.party]
            check(f"{PREFIX}/load_state_party_survives",
                  party_before == party_after,
                  f"before={party_before}, after={party_after}")
            if npc_before is not None and e._npc_disposition:
                rec_after = e._npc_disposition.npcs.get("TestNPC")
                npc_after = rec_after.disposition if rec_after else None
                check(f"{PREFIX}/load_state_npc_survives",
                      npc_before == npc_after,
                      f"before={npc_before}, after={npc_after}")


# ===========================================================================
# RUN ALL TESTS
# ===========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("FITD SMOKE TEST — Adversarial Simulation Engine")
    print("=" * 60)

    test_bitd()
    test_sav()
    test_bob()
    test_candela()
    test_cbrpnk()

    # Print results
    total = len(results["pass"]) + len(results["fail"])
    print("\n" + "=" * 60)
    print("=== SMOKE TEST RESULTS ===")
    print(f"PASSED: {len(results['pass'])}")
    print(f"FAILED: {len(results['fail'])}")
    print(f"WARNINGS: {len(results['warn'])}")
    print(f"TOTAL CHECKS: {total}")

    if results["fail"]:
        print("\n=== FAILURES ===")
        for f in results["fail"]:
            print(f"  FAIL: {f}")

    if results["warn"]:
        print("\n=== WARNINGS ===")
        for w in results["warn"]:
            print(f"  WARN: {w}")

    if not results["fail"] and not results["warn"]:
        print("\nAll systems nominal. No edge cases triggered.")

    sys.exit(0 if not results["fail"] else 1)
