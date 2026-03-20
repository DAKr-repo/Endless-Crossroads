"""
tests/test_enrich_module.py — Tests for the Module Enrichment Pipeline
=======================================================================
Tests prompt formatting, module brief generation, dry-run mode, and
enriched content_hints field retention — no LLM calls required.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from codex.core.enrichment_prompts import (
    NPC_ENRICHMENT_SYSTEM,
    NPC_ENRICHMENT_TEMPLATE,
    ROOM_ENRICHMENT_SYSTEM,
    ROOM_ENRICHMENT_TEMPLATE,
    EVENT_ENRICHMENT_SYSTEM,
    EVENT_ENRICHMENT_TEMPLATE,
    QUEST_ARC_SYSTEM,
    QUEST_ARC_TEMPLATE,
)
from scripts.enrich_module import build_module_brief, enrich_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_test_module(tmp_dir: Path) -> Path:
    """Create a minimal module directory with manifest + 1 blueprint."""
    module_dir = tmp_dir / "test_system_heist_42"
    module_dir.mkdir()

    manifest = {
        "module_id": "test_system_heist_42",
        "display_name": "Test Heist Module",
        "system_id": "bitd",
        "starting_location": "scene_hub",
        "recommended_levels": {"min": 1, "max": 3},
        "chapters": [
            {
                "chapter_id": "act_1",
                "display_name": "Act I",
                "order": 1,
                "zones": [
                    {
                        "zone_id": "scene_hub",
                        "blueprint": "scene_hub.json",
                        "topology": "settlement",
                        "theme": "GOTHIC",
                    }
                ],
            }
        ],
        "freeform_zones": [],
    }
    (module_dir / "module_manifest.json").write_text(json.dumps(manifest, indent=2))

    blueprint = {
        "seed": 12345,
        "width": 80,
        "height": 80,
        "start_room_id": 0,
        "metadata": {
            "zone_id": "scene_hub",
            "theme": "GOTHIC",
            "topology": "settlement",
            "display_name": "The Dusk Market",
        },
        "rooms": {
            "0": {
                "id": 0,
                "x": 10, "y": 10, "width": 8, "height": 8,
                "room_type": "town_square",
                "connections": [1],
                "tier": 1,
                "is_locked": False,
                "is_secret": False,
                "content_hints": {
                    "description": "A dimly lit chamber.",
                    "read_aloud": "A dimly lit chamber.",
                    "npcs": [
                        {
                            "name": "Rook",
                            "role": "informant",
                            "dialogue": "A boisterous individual. Owes money.",
                            "notes": "",
                        }
                    ],
                    "event_triggers": ["A shadow moves in the corner."],
                    "services": ["drink", "rumor"],
                },
            },
            "1": {
                "id": 1,
                "x": 24, "y": 10, "width": 8, "height": 8,
                "room_type": "normal",
                "connections": [0],
                "tier": 1,
                "is_locked": False,
                "is_secret": False,
                "content_hints": {},
            },
        },
    }
    (module_dir / "scene_hub.json").write_text(json.dumps(blueprint, indent=2))

    return module_dir


# ---------------------------------------------------------------------------
# Tests: Module brief generation
# ---------------------------------------------------------------------------

class TestModuleBrief:
    def test_brief_contains_module_name(self):
        manifest = {
            "display_name": "Shadow Heist",
            "system_id": "bitd",
            "chapters": [],
        }
        brief = build_module_brief(manifest, {})
        assert "Shadow Heist" in brief
        assert "bitd" in brief

    def test_brief_lists_npcs(self):
        manifest = {
            "display_name": "Test Module",
            "system_id": "bitd",
            "chapters": [
                {
                    "display_name": "Act I",
                    "zones": [{"zone_id": "s1"}],
                }
            ],
        }
        blueprints = {
            "s1": {
                "metadata": {"topology": "settlement"},
                "rooms": {
                    "0": {
                        "content_hints": {
                            "npcs": [{"name": "Varis"}],
                        }
                    }
                },
            }
        }
        brief = build_module_brief(manifest, blueprints)
        assert "Varis" in brief

    def test_brief_lists_enemies(self):
        manifest = {
            "display_name": "Test",
            "system_id": "dnd5e",
            "chapters": [
                {
                    "display_name": "Act I",
                    "zones": [{"zone_id": "z1"}],
                }
            ],
        }
        blueprints = {
            "z1": {
                "metadata": {"topology": "dungeon"},
                "rooms": {
                    "0": {
                        "content_hints": {
                            "enemies": [{"name": "Goblin"}],
                        }
                    }
                },
            }
        }
        brief = build_module_brief(manifest, blueprints)
        assert "Goblin" in brief


# ---------------------------------------------------------------------------
# Tests: Prompt template formatting
# ---------------------------------------------------------------------------

class TestPromptTemplates:
    def test_npc_template_formats(self):
        result = NPC_ENRICHMENT_TEMPLATE.format(
            module_name="Test Heist",
            system_id="bitd",
            source_material="",
            module_brief="A heist module",
            npc_name="Rook",
            npc_role="informant",
            current_dialogue="A boisterous individual.",
        )
        assert "Rook" in result
        assert "informant" in result
        assert "A heist module" in result

    def test_room_template_formats(self):
        result = ROOM_ENRICHMENT_TEMPLATE.format(
            module_name="Test Module",
            system_id="dnd5e",
            source_material="",
            scene_name="The Vault",
            topology="dungeon",
            tier=2,
            current_description="A dark room.",
        )
        assert "The Vault" in result
        assert "dungeon" in result
        assert "tier 2" in result.lower()

    def test_event_template_formats(self):
        result = EVENT_ENRICHMENT_TEMPLATE.format(
            module_name="Test",
            system_id="sav",
            module_brief="A pirate module",
            scene_name="The Docks",
            current_triggers="- A shadow moves.",
        )
        assert "The Docks" in result
        assert "shadow" in result

    def test_quest_arc_template_formats(self):
        result = QUEST_ARC_TEMPLATE.format(
            module_name="Test Heist",
            system_id="bitd",
            source_material="SOURCE MATERIAL:\nBlades info\n\n",
            scene_list="- The Dusk Market: settlement, NPCs: Rook",
        )
        assert "Dusk Market" in result
        assert "SOURCE MATERIAL" in result

    def test_system_prompts_are_nonempty(self):
        for prompt in [NPC_ENRICHMENT_SYSTEM, ROOM_ENRICHMENT_SYSTEM,
                       EVENT_ENRICHMENT_SYSTEM, QUEST_ARC_SYSTEM]:
            assert len(prompt) > 20


# ---------------------------------------------------------------------------
# Tests: Dry-run mode
# ---------------------------------------------------------------------------

class TestDryRun:
    def test_dry_run_does_not_modify_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            module_dir = _make_test_module(Path(tmp))
            bp_path = module_dir / "scene_hub.json"
            original = bp_path.read_text()

            import asyncio
            stats = asyncio.run(enrich_module(str(module_dir), dry_run=True))

            assert bp_path.read_text() == original
            assert stats["npcs"] == 1
            assert stats["rooms"] == 1
            assert stats["events"] == 1

    def test_dry_run_reports_rag_flag(self, capsys):
        with tempfile.TemporaryDirectory() as tmp:
            module_dir = _make_test_module(Path(tmp))

            import asyncio
            asyncio.run(enrich_module(str(module_dir), use_rag=True, dry_run=True))

            captured = capsys.readouterr()
            assert "RAG enabled" in captured.out


# ---------------------------------------------------------------------------
# Tests: Enriched content retains required fields
# ---------------------------------------------------------------------------

class TestEnrichedContent:
    def test_enrichment_preserves_npc_fields(self):
        """After enrichment, NPCs still have name/role/dialogue/notes."""
        with tempfile.TemporaryDirectory() as tmp:
            module_dir = _make_test_module(Path(tmp))

            async def fake_codex(prompt, sys_prompt):
                return "[Wary] The docks are restless tonight. Watch your coin purse."

            async def fake_mimir(prompt, sys_prompt):
                return "[Wary] The docks are restless tonight. Watch your coin purse."

            import asyncio
            with patch("scripts.enrich_module._invoke_codex", new=fake_codex), \
                 patch("scripts.enrich_module._invoke_mimir", new=fake_mimir):
                asyncio.run(enrich_module(str(module_dir)))

            bp = json.loads((module_dir / "scene_hub.json").read_text())
            npc = bp["rooms"]["0"]["content_hints"]["npcs"][0]
            assert "name" in npc
            assert "role" in npc
            assert "dialogue" in npc
            assert npc["dialogue"].startswith("[Wary]")

    def test_enrichment_updates_room_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            module_dir = _make_test_module(Path(tmp))

            async def fake_invoke(prompt, sys_prompt):
                if "SCENE" in prompt:
                    return "Lanterns sway overhead, casting amber pools across wet cobblestones."
                if "event trigger" in sys_prompt.lower():
                    return "A blade scrapes stone in the darkness."
                if "narrative hook" in sys_prompt.lower():
                    return "A stolen relic draws you to the underbelly of Doskvol."
                return "Enriched content."

            async def fake_mimir(prompt, sys_prompt):
                return "[Eager] Fresh fish from the harbor!"

            import asyncio
            with patch("scripts.enrich_module._invoke_codex", new=fake_invoke), \
                 patch("scripts.enrich_module._invoke_mimir", new=fake_mimir):
                stats = asyncio.run(enrich_module(str(module_dir)))

            bp = json.loads((module_dir / "scene_hub.json").read_text())
            desc = bp["rooms"]["0"]["content_hints"]["description"]
            assert desc != "A dimly lit chamber."
            assert stats["rooms_enriched"] >= 1

    def test_enrichment_writes_quest_arc_to_read_aloud(self):
        with tempfile.TemporaryDirectory() as tmp:
            module_dir = _make_test_module(Path(tmp))

            async def fake_invoke(prompt, sys_prompt):
                if "narrative hook" in sys_prompt.lower():
                    return "The Hound has stolen the Twilight Chalice."
                return "Enriched."

            async def fake_mimir(prompt, sys_prompt):
                return "[Hushed] Enriched dialogue."

            import asyncio
            with patch("scripts.enrich_module._invoke_codex", new=fake_invoke), \
                 patch("scripts.enrich_module._invoke_mimir", new=fake_mimir):
                stats = asyncio.run(enrich_module(str(module_dir)))

            bp = json.loads((module_dir / "scene_hub.json").read_text())
            read_aloud = bp["rooms"]["0"]["content_hints"].get("read_aloud", "")
            assert "Twilight Chalice" in read_aloud
            assert stats["quest_arc"] is True

    def test_missing_manifest_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            import asyncio
            with pytest.raises(FileNotFoundError):
                asyncio.run(enrich_module(tmp))

    def test_enrichment_stats_count_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            module_dir = _make_test_module(Path(tmp))

            async def fake_invoke(prompt, sys_prompt):
                return "Enriched content."

            async def fake_mimir(prompt, sys_prompt):
                return "[Wary] Enriched dialogue from Mimir."

            import asyncio
            with patch("scripts.enrich_module._invoke_codex", new=fake_invoke), \
                 patch("scripts.enrich_module._invoke_mimir", new=fake_mimir):
                stats = asyncio.run(enrich_module(str(module_dir)))

            # 1 NPC via mimir + 1 room + 1 event + 1 quest arc via codex = 3+1
            assert stats["mimir_calls"] == 1
            assert stats["codex_calls"] == 3

    def test_mimir_failure_falls_back_to_codex(self):
        """When Mimir returns invalid output, Codex fallback fires."""
        with tempfile.TemporaryDirectory() as tmp:
            module_dir = _make_test_module(Path(tmp))

            async def fake_mimir(prompt, sys_prompt):
                return "bad output no tone tag"  # Fails validation

            async def fake_codex(prompt, sys_prompt):
                return "[Gruff] Codex fallback dialogue."

            import asyncio
            with patch("scripts.enrich_module._invoke_mimir", new=fake_mimir), \
                 patch("scripts.enrich_module._invoke_codex", new=fake_codex):
                asyncio.run(enrich_module(str(module_dir)))

            bp = json.loads((module_dir / "scene_hub.json").read_text())
            npc = bp["rooms"]["0"]["content_hints"]["npcs"][0]
            assert npc["dialogue"].startswith("[Gruff]")

    def test_mimir_validates_tone_tag_format(self):
        """Mimir output must match [Tone] sentence pattern."""
        from scripts.enrich_module import _validate_npc_dialogue
        assert _validate_npc_dialogue("[Wary] The streets are quiet.")
        assert _validate_npc_dialogue("[Eager] Come, let me show you!")
        assert not _validate_npc_dialogue("No tone tag here.")
        assert not _validate_npc_dialogue("")
        assert not _validate_npc_dialogue("[Broken]")
