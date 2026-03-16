"""
tests/test_chronologer.py -- WO-V11.2: The Chronologer
=======================================================

12 tests covering HistoricalEvent, WorldLedger chronology, and Mimir context.
"""

import json
import tempfile
import unittest
from pathlib import Path

from codex.core.world.world_ledger import (
    AuthorityLevel,
    EventType,
    HistoricalEvent,
    WorldLedger,
)
from codex.integrations.mimir import build_chronology_context


def _make_ledger(grapes=None, chronology=None):
    """Create a WorldLedger backed by a temp file."""
    d = tempfile.mkdtemp()
    p = Path(d) / "test_world.json"
    data = {"grapes": grapes or {"geography": [{"name": "X", "terrain": "y", "feature": "z"}]}}
    if chronology:
        data["chronology"] = chronology
    p.write_text(json.dumps(data))
    return WorldLedger(p, data["grapes"]), p


class TestHistoricalEventSerialization(unittest.TestCase):
    """T1: HistoricalEvent round-trip serialization."""

    def test_round_trip(self):
        event = HistoricalEvent(
            timestamp="2026-02-19T12:00:00",
            event_type=EventType.WAR,
            summary="The Battle of Ash Ridge",
            authority_level=AuthorityLevel.EYEWITNESS,
            category="geography",
            universe_id="u1",
            source="player",
        )
        d = event.to_dict()
        restored = HistoricalEvent.from_dict(d)
        self.assertEqual(restored.timestamp, event.timestamp)
        self.assertEqual(restored.event_type, event.event_type)
        self.assertEqual(restored.summary, event.summary)
        self.assertEqual(restored.authority_level, event.authority_level)
        self.assertEqual(restored.category, event.category)
        self.assertEqual(restored.universe_id, event.universe_id)
        self.assertEqual(restored.source, event.source)


class TestEnumValues(unittest.TestCase):
    """T2: EventType / AuthorityLevel enum values."""

    def test_event_types(self):
        expected = {"war", "discovery", "chronicle_ending", "mutation",
                    "political", "economic", "social", "civic", "faction"}
        actual = {e.value for e in EventType}
        self.assertEqual(actual, expected)

    def test_authority_levels(self):
        self.assertEqual(AuthorityLevel.EYEWITNESS.value, 1)
        self.assertEqual(AuthorityLevel.CHRONICLE.value, 2)
        self.assertEqual(AuthorityLevel.LEGEND.value, 3)


class TestMutateAutoRecord(unittest.TestCase):
    """T3: mutate() creates MUTATION chronology entry."""

    def test_mutate_records_event(self):
        grapes = {"geography": [{"name": "Peaks", "terrain": "alpine", "feature": "volcanoes"}]}
        ledger, _ = _make_ledger(grapes)
        ledger.mutate("geography", 0, "terrain", "glacial")
        events = ledger.get_chronology()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, EventType.MUTATION)
        self.assertIn("terrain", events[0].summary)


class TestClearLandmarkAutoRecord(unittest.TestCase):
    """T4: clear_landmark() creates DISCOVERY event."""

    def test_clear_landmark_records_event(self):
        grapes = {"geography": [{"name": "Peaks", "terrain": "alpine", "feature": "volcanoes"}]}
        ledger, _ = _make_ledger(grapes)
        ledger.clear_landmark("Peaks", "the party")
        events = ledger.get_chronology()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, EventType.DISCOVERY)
        self.assertIn("Peaks", events[0].summary)


class TestDepleteResourceAutoRecord(unittest.TestCase):
    """T5: deplete_resource() creates ECONOMIC event."""

    def test_deplete_records_event(self):
        grapes = {"economics": [{"resource": "Iron", "abundance": "plentiful"}]}
        ledger, _ = _make_ledger(grapes)
        ledger.deplete_resource("Iron")
        events = ledger.get_chronology()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, EventType.ECONOMIC)
        self.assertIn("Iron", events[0].summary)


class TestManualRecording(unittest.TestCase):
    """T6: record_historical_event() manual recording."""

    def test_manual_record(self):
        ledger, _ = _make_ledger()
        ledger.record_historical_event(
            EventType.WAR,
            "The Siege of Emberhome",
            authority_level=AuthorityLevel.LEGEND,
            source="lore_master",
        )
        events = ledger.get_chronology()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, EventType.WAR)
        self.assertEqual(events[0].authority_level, AuthorityLevel.LEGEND)
        self.assertEqual(events[0].source, "lore_master")


class TestChronologyOrdering(unittest.TestCase):
    """T7: get_chronology() returns most-recent-first."""

    def test_most_recent_first(self):
        ledger, _ = _make_ledger()
        ledger.record_historical_event(EventType.WAR, "First event")
        ledger.record_historical_event(EventType.DISCOVERY, "Second event")
        ledger.record_historical_event(EventType.POLITICAL, "Third event")
        events = ledger.get_chronology()
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].summary, "Third event")
        self.assertEqual(events[2].summary, "First event")


class TestChronologyFiltering(unittest.TestCase):
    """T8: get_chronology(event_type=X) filtering."""

    def test_filter_by_type(self):
        ledger, _ = _make_ledger()
        ledger.record_historical_event(EventType.WAR, "Battle 1")
        ledger.record_historical_event(EventType.DISCOVERY, "Ruin found")
        ledger.record_historical_event(EventType.WAR, "Battle 2")
        wars = ledger.get_chronology(event_type=EventType.WAR)
        self.assertEqual(len(wars), 2)
        for e in wars:
            self.assertEqual(e.event_type, EventType.WAR)


class TestSavePersistsChronology(unittest.TestCase):
    """T9: save() persists chronology to JSON."""

    def test_save_chronology(self):
        ledger, path = _make_ledger()
        ledger.record_historical_event(EventType.WAR, "The Battle of Ash Ridge")
        ledger.record_historical_event(EventType.DISCOVERY, "Ancient ruins uncovered")
        ledger.save()
        data = json.loads(path.read_text())
        self.assertIn("chronology", data)
        self.assertEqual(len(data["chronology"]), 2)
        self.assertEqual(data["chronology"][0]["event_type"], "war")


class TestLoadChronology(unittest.TestCase):
    """T10: _load_chronology() hydrates from JSON."""

    def test_survives_save_load_cycle(self):
        ledger, path = _make_ledger()
        ledger.record_historical_event(EventType.FACTION, "Guild formed")
        ledger.save()
        # Create a new ledger from the same file
        data = json.loads(path.read_text())
        ledger2 = WorldLedger(path, data["grapes"])
        events = ledger2.get_chronology()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, EventType.FACTION)
        self.assertEqual(events[0].summary, "Guild formed")


class TestIngestCivicEvent(unittest.TestCase):
    """T11: ingest_civic_event() bridges CivicPulse."""

    def test_civic_to_chronology(self):
        ledger, _ = _make_ledger()
        ledger.ingest_civic_event({
            "timestamp": "2026-02-19T10:00:00",
            "category": "trade",
            "event_tag": "SCRAP_MERCHANT",
        })
        events = ledger.get_chronology()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, EventType.ECONOMIC)
        self.assertEqual(events[0].summary, "SCRAP_MERCHANT")
        self.assertEqual(events[0].source, "civic_pulse")

    def test_unknown_category_defaults_civic(self):
        ledger, _ = _make_ledger()
        ledger.ingest_civic_event({
            "category": "unknown_category",
            "event_tag": "MYSTERY_EVENT",
        })
        events = ledger.get_chronology()
        self.assertEqual(events[0].event_type, EventType.CIVIC)


class TestBuildChronologyContext(unittest.TestCase):
    """T12: build_chronology_context() LLM formatting."""

    def test_dict_format(self):
        events = [
            {"timestamp": "2026-02-19T12:00:00", "event_type": "war",
             "summary": "Battle of Ash", "authority_level": 1},
            {"timestamp": "2026-02-19T13:00:00", "event_type": "discovery",
             "summary": "Ruins found", "authority_level": 2},
        ]
        ctx = build_chronology_context(events)
        self.assertIn("WORLD HISTORY", ctx)
        self.assertIn("Battle of Ash", ctx)
        self.assertIn("Ruins found", ctx)
        self.assertIn("EYEWITNESS", ctx)
        self.assertIn("CHRONICLE", ctx)

    def test_object_format(self):
        events = [
            HistoricalEvent(
                timestamp="2026-02-19T14:00:00",
                event_type=EventType.POLITICAL,
                summary="New king crowned",
                authority_level=AuthorityLevel.LEGEND,
            ),
        ]
        ctx = build_chronology_context(events)
        self.assertIn("WORLD HISTORY", ctx)
        self.assertIn("New king crowned", ctx)
        self.assertIn("LEGEND", ctx)

    def test_empty_returns_empty(self):
        self.assertEqual(build_chronology_context([]), "")
        self.assertEqual(build_chronology_context(None), "")


if __name__ == "__main__":
    unittest.main()
