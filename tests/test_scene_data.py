"""
tests/test_scene_data.py — SceneData model tests.
====================================================

Covers SceneNPC, SceneEnemy, SceneLoot, and SceneData parsing and
serialization across all Dragon Heist JSON formats.

WO-V51.0: The Foundation Sprint — Phase B5
"""

import pytest

from codex.spatial.scene_data import SceneData, SceneNPC, SceneEnemy, SceneLoot


# =========================================================================
# SceneNPC
# =========================================================================

class TestSceneNPC:
    """SceneNPC serialization."""

    def test_to_dict_from_dict_roundtrip(self):
        npc = SceneNPC(name="Durnan", role="innkeeper",
                       dialogue="Welcome.", notes="Retired adventurer")
        d = npc.to_dict()
        npc2 = SceneNPC.from_dict(d)
        assert npc2.name == "Durnan"
        assert npc2.role == "innkeeper"
        assert npc2.dialogue == "Welcome."
        assert npc2.notes == "Retired adventurer"


# =========================================================================
# SceneEnemy
# =========================================================================

class TestSceneEnemy:
    """SceneEnemy serialization."""

    def test_to_dict_from_dict_roundtrip(self):
        enemy = SceneEnemy(name="Thug", hp=11, ac=11, attack=4,
                           damage="1d6+2", count=2, is_boss=False,
                           notes="Will surrender", special=["multiattack"])
        d = enemy.to_dict()
        e2 = SceneEnemy.from_dict(d)
        assert e2.name == "Thug"
        assert e2.hp == 11
        assert e2.count == 2
        assert e2.special == ["multiattack"]

    def test_boss_flag_serialization(self):
        boss = SceneEnemy(name="Dragon", hp=100, is_boss=True)
        d = boss.to_dict()
        assert d["is_boss"] is True
        e2 = SceneEnemy.from_dict(d)
        assert e2.is_boss is True

    def test_non_boss_omits_flag(self):
        normal = SceneEnemy(name="Goblin", hp=7)
        d = normal.to_dict()
        assert "is_boss" not in d


# =========================================================================
# SceneLoot
# =========================================================================

class TestSceneLoot:
    """SceneLoot serialization."""

    def test_to_dict_from_dict_roundtrip(self):
        loot = SceneLoot(name="Half-Burned Ledger", value=0,
                         description="Mentions payments to 'The Zhent'")
        d = loot.to_dict()
        l2 = SceneLoot.from_dict(d)
        assert l2.name == "Half-Burned Ledger"
        assert l2.value == 0
        assert "Zhent" in l2.description


# =========================================================================
# SceneData — Yawning Portal format (npcs, services)
# =========================================================================

class TestSceneDataYawningPortal:
    """from_content_hints with Yawning Portal format."""

    def test_parses_npcs_and_services(self):
        hints = {
            "description": "The main hall of the Yawning Portal.",
            "npcs": [
                {"name": "Durnan", "role": "innkeeper",
                 "dialogue": "Welcome.", "notes": "Retired adventurer"},
                {"name": "Volo", "role": "quest_giver",
                 "dialogue": "You there!"},
            ],
            "services": ["drink", "rest", "rumor", "quest"],
            "event_triggers": ["On entry: Volo approaches."],
        }
        scene = SceneData.from_content_hints(hints)
        assert len(scene.npcs) == 2
        assert scene.npcs[0].name == "Durnan"
        assert scene.npcs[1].role == "quest_giver"
        assert "drink" in scene.services
        assert len(scene.event_triggers) == 1
        assert scene.description.startswith("The main hall")


# =========================================================================
# SceneData — Zhentarim format (enemies, investigation_dc)
# =========================================================================

class TestSceneDataZhentarim:
    """from_content_hints with Zhentarim Hideout format."""

    def test_parses_enemies_and_dc(self):
        hints = {
            "description": "A cramped office.",
            "enemies": [
                {"name": "Zhentarim Spy", "hp": 12, "ac": 12,
                 "attack": 4, "damage": "1d6+2", "count": 1,
                 "notes": "Cunning Action"},
            ],
            "loot": [
                {"name": "Ledger", "value": 0,
                 "description": "Partially destroyed."},
            ],
            "investigation_dc": 12,
            "investigation_success": "A note reading 'Bring the boy.'",
        }
        scene = SceneData.from_content_hints(hints)
        assert len(scene.enemies) == 1
        assert scene.enemies[0].name == "Zhentarim Spy"
        assert scene.enemies[0].hp == 12
        assert scene.investigation_dc == 12
        assert "note" in scene.investigation_success.lower()
        assert len(scene.loot) == 1


# =========================================================================
# SceneData — Empty / missing keys
# =========================================================================

class TestSceneDataDefaults:
    """from_content_hints with empty/missing keys."""

    def test_empty_hints(self):
        scene = SceneData.from_content_hints({})
        assert scene.description == ""
        assert scene.npcs == []
        assert scene.enemies == []
        assert scene.loot == []
        assert scene.services == []
        assert scene.investigation_dc == 0

    def test_missing_optional_keys(self):
        hints = {"description": "A room."}
        scene = SceneData.from_content_hints(hints)
        assert scene.description == "A room."
        assert scene.npcs == []
        assert scene.enemies == []


# =========================================================================
# SceneData — Trollskull renovation_options
# =========================================================================

class TestSceneDataTrollskull:
    """from_content_hints with renovation_options format."""

    def test_parses_renovation_options(self):
        hints = {
            "description": "Trollskull Manor taproom.",
            "renovation_options": [
                {"name": "Basic Repairs", "cost": 250, "days": 5,
                 "effect": "Tavern becomes functional."},
                {"name": "Full Renovation", "cost": 1000, "days": 20,
                 "effect": "Tavern profitable."},
            ],
        }
        scene = SceneData.from_content_hints(hints)
        assert len(scene.renovation_options) == 2
        assert scene.renovation_options[0]["name"] == "Basic Repairs"
        assert scene.renovation_options[1]["cost"] == 1000


# =========================================================================
# SceneData — Full roundtrip
# =========================================================================

class TestSceneDataRoundtrip:
    """to_dict / from_dict roundtrips."""

    def test_full_roundtrip(self):
        scene = SceneData(
            description="A dark room.",
            read_aloud="You step into darkness.",
            npcs=[SceneNPC(name="Guard", role="guard")],
            enemies=[SceneEnemy(name="Goblin", hp=7, ac=13, attack=5)],
            loot=[SceneLoot(name="Gold Coins", value=50)],
            services=["rest"],
            event_triggers=["On entry: combat begins."],
            investigation_dc=15,
            investigation_success="You find a key.",
            perception_dc=10,
            perception_success="You notice a draft.",
            lock_dc=12,
        )
        d = scene.to_dict()
        scene2 = SceneData.from_dict(d)
        assert scene2.description == "A dark room."
        assert scene2.read_aloud == "You step into darkness."
        assert len(scene2.npcs) == 1
        assert len(scene2.enemies) == 1
        assert len(scene2.loot) == 1
        assert scene2.investigation_dc == 15
        assert scene2.perception_dc == 10
        assert scene2.lock_dc == 12

    def test_perception_dc_roundtrip(self):
        hints = {
            "description": "Entrance.",
            "perception_dc": 10,
            "perception_success": "Fresh bootprints.",
        }
        scene = SceneData.from_content_hints(hints)
        d = scene.to_dict()
        scene2 = SceneData.from_dict(d)
        assert scene2.perception_dc == 10
        assert "bootprints" in scene2.perception_success
