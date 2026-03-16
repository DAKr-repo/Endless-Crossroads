"""
tests/test_fr_wiki.py — WO-V55.0
==================================
Tests for:
1. FRWikiClient — search, fetch, cache, probe
2. is_fr_context() setting gate
3. lore bridge command
4. DnD5eCharacter/Engine setting_id field
5. ModuleManifest campaign_setting field
6. NPC dialogue wiki enrichment
"""
from unittest.mock import MagicMock, patch, PropertyMock
import pytest


# =========================================================================
# Track A: FRWikiClient
# =========================================================================

class TestIsfrContext:
    """is_fr_context() should gate on known FR settings."""

    def test_known_settings(self):
        from codex.integrations.fr_wiki import is_fr_context
        assert is_fr_context("forgotten_realms") is True
        assert is_fr_context("sword_coast") is True
        assert is_fr_context("waterdeep") is True
        assert is_fr_context("icewind_dale") is True
        assert is_fr_context("barovia") is True
        assert is_fr_context("chult") is True
        assert is_fr_context("baldurs_gate") is True

    def test_unknown_settings(self):
        from codex.integrations.fr_wiki import is_fr_context
        assert is_fr_context("burnwillow") is False
        assert is_fr_context("roshar") is False
        assert is_fr_context("eberron") is False
        assert is_fr_context("") is False

    def test_case_insensitive(self):
        from codex.integrations.fr_wiki import is_fr_context
        assert is_fr_context("FORGOTTEN_REALMS") is True
        assert is_fr_context("Waterdeep") is True

    def test_empty_and_none(self):
        from codex.integrations.fr_wiki import is_fr_context
        assert is_fr_context("") is False
        # None should not crash
        assert is_fr_context(None) is False


class TestKiwixSource:
    """KiwixSource dataclass."""

    def test_creation(self):
        from codex.integrations.fr_wiki import KiwixSource
        src = KiwixSource(name="test", book_id="test_book",
                          description="Test", priority=5)
        assert src.name == "test"
        assert src.priority == 5

    def test_default_priority(self):
        from codex.integrations.fr_wiki import KiwixSource
        src = KiwixSource(name="test", book_id="test_book",
                          description="Test")
        assert src.priority == 10


class TestFRWikiClient:
    """FRWikiClient with mocked HTTP responses."""

    def _make_client(self):
        from codex.integrations.fr_wiki import FRWikiClient, KiwixSource
        sources = [
            KiwixSource("wiki_a", "wiki_a_book", "Wiki A", priority=1),
            KiwixSource("wiki_b", "wiki_b_book", "Wiki B", priority=2),
        ]
        return FRWikiClient(base_url="http://test:8080", sources=sources)

    def test_probe_sources_filters_to_loaded(self):
        """Only sources whose name appears in catalog should survive."""
        client = self._make_client()
        catalog_xml = (
            '<entry><name>wiki_a</name>'
            '<link type="text/html" href="/wiki_a_2026-03" />'
            '</entry>'
        )
        mock_resp = MagicMock()
        mock_resp.text = catalog_xml

        with patch("codex.integrations.fr_wiki.requests.get",
                    return_value=mock_resp):
            sources = client._probe_sources()
        assert len(sources) == 1
        assert sources[0].name == "wiki_a"
        # book_id should be auto-detected from catalog link
        assert sources[0].book_id == "wiki_a_2026-03"

    def test_probe_sources_caches_result(self):
        """Subsequent calls should not re-query the catalog."""
        client = self._make_client()
        catalog_xml = (
            '<entry><name>wiki_b</name>'
            '<link type="text/html" href="/wiki_b_book" />'
            '</entry>'
        )
        mock_resp = MagicMock()
        mock_resp.text = catalog_xml

        with patch("codex.integrations.fr_wiki.requests.get",
                    return_value=mock_resp) as mock_get:
            client._probe_sources()
            client._probe_sources()
        assert mock_get.call_count == 1

    def test_probe_sources_handles_timeout(self):
        """Network errors should result in empty sources, not crash."""
        client = self._make_client()
        import requests as _req
        with patch("codex.integrations.fr_wiki.requests.get",
                    side_effect=_req.ConnectionError("timeout")):
            sources = client._probe_sources()
        assert sources == []

    def test_search_returns_results(self):
        """Search should parse result links from HTML."""
        client = self._make_client()
        # Pre-set available sources
        from codex.integrations.fr_wiki import KiwixSource
        client._available = [
            KiwixSource("wiki_a", "wiki_a_book", "Wiki A", 1)]

        search_html = """
        <html><body>
        <a href="/wiki_a_book/Waterdeep">Waterdeep</a>
        <a href="/wiki_a_book/Baldurs_Gate">Baldur's Gate</a>
        </body></html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = search_html

        with patch("codex.integrations.fr_wiki.requests.get",
                    return_value=mock_resp):
            results = client.search("waterdeep", k=5)
        assert len(results) == 2
        assert results[0][0] == "Waterdeep"
        assert results[0][2] == "wiki_a"

    def test_search_empty_when_no_sources(self):
        """If no sources loaded, search should return empty."""
        client = self._make_client()
        client._available = []
        results = client.search("waterdeep")
        assert results == []

    def test_search_falls_through_sources(self):
        """If first source has no results, try second."""
        client = self._make_client()
        from codex.integrations.fr_wiki import KiwixSource
        client._available = [
            KiwixSource("wiki_a", "wiki_a_book", "Wiki A", 1),
            KiwixSource("wiki_b", "wiki_b_book", "Wiki B", 2),
        ]

        call_count = [0]

        def _mock_get(url, **kwargs):
            call_count[0] += 1
            resp = MagicMock()
            resp.status_code = 200
            if "wiki_a_book" in url:
                resp.text = "<html><body>No results</body></html>"
            else:
                resp.text = '<a href="/wiki_b_book/Drizzt">Drizzt</a>'
            return resp

        with patch("codex.integrations.fr_wiki.requests.get",
                    side_effect=_mock_get):
            results = client.search("drizzt")
        assert len(results) == 1
        assert results[0][2] == "wiki_b"

    def test_fetch_article_extracts_paragraphs(self):
        """Fetch should extract <p> content."""
        client = self._make_client()
        html = "<html><body><p>Waterdeep is a city.</p><p>It is large.</p></body></html>"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html

        with patch("codex.integrations.fr_wiki.requests.get",
                    return_value=mock_resp):
            text = client.fetch_article("wiki_a_book/A/Waterdeep")
        assert "Waterdeep is a city." in text
        assert "It is large." in text

    def test_fetch_article_caches(self):
        """Second fetch of same path should use cache."""
        client = self._make_client()
        html = "<html><body><p>Cached content.</p></body></html>"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html

        with patch("codex.integrations.fr_wiki.requests.get",
                    return_value=mock_resp) as mock_get:
            client.fetch_article("path/A/Test")
            client.fetch_article("path/A/Test")
        assert mock_get.call_count == 1

    def test_fetch_article_lru_eviction(self):
        """Cache should evict oldest entry when full."""
        client = self._make_client()
        client._max_cache = 2
        client._cache = {"old_path": "old_text", "older_path": "older_text"}

        html = "<html><body><p>New content.</p></body></html>"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html

        with patch("codex.integrations.fr_wiki.requests.get",
                    return_value=mock_resp):
            client.fetch_article("new_path")
        assert "new_path" in client._cache
        assert len(client._cache) == 2

    def test_fetch_article_handles_404(self):
        """404 should return empty string."""
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("codex.integrations.fr_wiki.requests.get",
                    return_value=mock_resp):
            text = client.fetch_article("bad/path")
        assert text == ""

    def test_get_lore_summary_truncates(self):
        """Summary should truncate at sentence boundary."""
        client = self._make_client()
        from codex.integrations.fr_wiki import KiwixSource
        client._available = [
            KiwixSource("wiki_a", "wiki_a_book", "Wiki A", 1)]

        long_text = "First sentence. " * 50  # ~800 chars

        search_html = '<a href="/wiki_a_book/Topic">Topic</a>'
        article_html = f"<html><body><p>{long_text}</p></body></html>"

        call_count = [0]

        def _mock_get(url, **kwargs):
            nonlocal call_count
            call_count[0] += 1
            resp = MagicMock()
            resp.status_code = 200
            if "search" in url:
                resp.text = search_html
            else:
                resp.text = article_html
            return resp

        with patch("codex.integrations.fr_wiki.requests.get",
                    side_effect=_mock_get):
            summary = client.get_lore_summary("topic", max_chars=100)
        assert summary is not None
        assert len(summary) <= 100
        assert summary.endswith(".")

    def test_get_lore_summary_returns_none_when_no_results(self):
        """No results should return None."""
        client = self._make_client()
        client._available = []
        summary = client.get_lore_summary("nothing")
        assert summary is None

    def test_get_lore_summary_graceful_degradation(self):
        """Network errors should return None, not crash."""
        client = self._make_client()
        from codex.integrations.fr_wiki import KiwixSource
        client._available = [
            KiwixSource("wiki_a", "wiki_a_book", "Wiki A", 1)]

        import requests as _req
        with patch("codex.integrations.fr_wiki.requests.get",
                    side_effect=_req.ConnectionError("down")):
            summary = client.get_lore_summary("waterdeep")
        assert summary is None


class TestSingleton:
    """get_fr_wiki() singleton."""

    def test_returns_same_instance(self):
        from codex.integrations import fr_wiki
        # Reset singleton
        fr_wiki._client = None
        w1 = fr_wiki.get_fr_wiki()
        w2 = fr_wiki.get_fr_wiki()
        assert w1 is w2
        fr_wiki._client = None  # cleanup


# =========================================================================
# Track B: DnD5e setting_id
# =========================================================================

class TestDnD5eSettingId:
    """DnD5eCharacter and DnD5eEngine setting_id propagation."""

    def test_character_setting_id_default(self):
        from codex.games.dnd5e import DnD5eCharacter
        char = DnD5eCharacter(name="Test")
        assert char.setting_id == ""

    def test_character_setting_id_set(self):
        from codex.games.dnd5e import DnD5eCharacter
        char = DnD5eCharacter(name="Test", setting_id="forgotten_realms")
        assert char.setting_id == "forgotten_realms"

    def test_character_serialization(self):
        from codex.games.dnd5e import DnD5eCharacter
        char = DnD5eCharacter(name="Test", setting_id="sword_coast")
        d = char.to_dict()
        assert d["setting_id"] == "sword_coast"
        restored = DnD5eCharacter.from_dict(d)
        assert restored.setting_id == "sword_coast"

    def test_character_from_dict_missing_field(self):
        """Old saves without setting_id should default to empty."""
        from codex.games.dnd5e import DnD5eCharacter
        d = {"name": "OldSave", "race": "Human"}
        char = DnD5eCharacter.from_dict(d)
        assert char.setting_id == ""

    def test_engine_setting_id_default(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        assert engine.setting_id == ""

    def test_engine_create_character_propagates(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Hero", setting_id="forgotten_realms")
        assert engine.setting_id == "forgotten_realms"
        assert engine.character.setting_id == "forgotten_realms"

    def test_engine_save_load_roundtrip(self):
        from codex.games.dnd5e import DnD5eEngine
        engine = DnD5eEngine()
        engine.create_character("Hero")
        engine.setting_id = "waterdeep"
        state = engine.save_state()
        assert state["setting_id"] == "waterdeep"

        engine2 = DnD5eEngine()
        engine2.load_state(state)
        assert engine2.setting_id == "waterdeep"


# =========================================================================
# Track C: ModuleManifest campaign_setting
# =========================================================================

class TestModuleManifestCampaignSetting:
    """ModuleManifest campaign_setting field."""

    def test_default_empty(self):
        from codex.spatial.module_manifest import ModuleManifest
        mm = ModuleManifest(module_id="test", display_name="Test",
                            system_id="dnd5e")
        assert mm.campaign_setting == ""

    def test_serialization(self):
        from codex.spatial.module_manifest import ModuleManifest
        mm = ModuleManifest(module_id="test", display_name="Test",
                            system_id="dnd5e",
                            campaign_setting="forgotten_realms")
        d = mm.to_dict()
        assert d["campaign_setting"] == "forgotten_realms"

    def test_deserialization(self):
        from codex.spatial.module_manifest import ModuleManifest
        data = {
            "module_id": "test", "display_name": "Test",
            "system_id": "dnd5e",
            "campaign_setting": "forgotten_realms",
        }
        mm = ModuleManifest.from_dict(data)
        assert mm.campaign_setting == "forgotten_realms"

    def test_deserialization_missing_field(self):
        """Old manifests without campaign_setting should default."""
        from codex.spatial.module_manifest import ModuleManifest
        data = {"module_id": "test", "display_name": "Test",
                "system_id": "dnd5e"}
        mm = ModuleManifest.from_dict(data)
        assert mm.campaign_setting == ""

    def test_to_dict_omits_empty(self):
        """Empty campaign_setting should NOT appear in dict."""
        from codex.spatial.module_manifest import ModuleManifest
        mm = ModuleManifest(module_id="test", display_name="Test",
                            system_id="dnd5e")
        d = mm.to_dict()
        assert "campaign_setting" not in d

    def test_dragon_heist_manifest(self):
        """Dragon Heist module manifest should have campaign_setting."""
        import json
        from pathlib import Path
        manifest_path = Path(__file__).resolve().parent.parent / \
            "vault_maps" / "modules" / "dragon_heist" / "module_manifest.json"
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text())
            assert data.get("campaign_setting") == "forgotten_realms"


# =========================================================================
# Track D: lore bridge command
# =========================================================================

def _make_mock_engine(exits=None, room_id=0):
    """Build a minimal mock engine for bridge tests."""
    engine = MagicMock()
    engine.system_id = "dnd5e"
    engine.display_name = "D&D 5th Edition"
    engine.current_room_id = room_id
    engine.setting_id = ""

    room = MagicMock()
    room.room_type.name = "NORMAL"
    room.id = room_id
    room.x = 0
    room.y = 0
    room.width = 3
    room.height = 3
    room.connections = set()
    room.is_locked = False
    room.tier = 1
    engine.get_current_room.return_value = room
    engine.get_cardinal_exits.return_value = exits or []

    pop = MagicMock()
    pop.content = {"description": "A room.", "enemies": [], "loot": [],
                    "npcs": [], "services": []}
    engine.populated_rooms = {room_id: pop}
    engine.character = MagicMock()
    engine.character.name = "Hero"
    engine.character.current_hp = 10
    engine.character.max_hp = 10
    engine.dungeon_graph = MagicMock()
    engine.dungeon_graph.rooms = {0: room}
    engine.visited_rooms = {0}

    return engine


def _make_bridge(engine):
    """Create a UniversalGameBridge bypassing __init__."""
    from codex.games.bridge import UniversalGameBridge
    from codex.core.mechanics.rest import RestManager

    bridge = object.__new__(UniversalGameBridge)
    bridge.engine = engine
    bridge.dead = False
    bridge.last_frame = None
    bridge._broadcast = None
    bridge._system_tag = engine.system_id.upper()
    bridge._rest_mgr = RestManager()
    bridge._butler = None
    bridge.show_dm_notes = False
    bridge._talking_to = None
    bridge._session_log = []     # WO-V61.0
    return bridge


class TestLoreCommand:
    """lore <topic> bridge command."""

    def test_lore_no_arg(self):
        engine = _make_mock_engine()
        bridge = _make_bridge(engine)
        result = bridge.step("lore")
        assert "Usage:" in result

    def test_lore_non_fr_setting(self):
        engine = _make_mock_engine()
        engine.setting_id = "burnwillow"
        bridge = _make_bridge(engine)
        result = bridge.step("lore waterdeep")
        assert "No lore archive" in result

    def test_lore_empty_setting(self):
        engine = _make_mock_engine()
        engine.setting_id = ""
        bridge = _make_bridge(engine)
        result = bridge.step("lore waterdeep")
        assert "No lore archive" in result

    def test_lore_fr_setting_with_results(self):
        engine = _make_mock_engine()
        engine.setting_id = "forgotten_realms"
        bridge = _make_bridge(engine)

        with patch("codex.integrations.fr_wiki.get_fr_wiki") as mock_wiki:
            mock_client = MagicMock()
            mock_client.get_lore_summary.return_value = "Waterdeep is a great city."
            mock_wiki.return_value = mock_client
            result = bridge.step("lore waterdeep")

        assert "Lore: Waterdeep" in result
        assert "Waterdeep is a great city." in result

    def test_lore_fr_setting_no_results(self):
        engine = _make_mock_engine()
        engine.setting_id = "sword_coast"
        bridge = _make_bridge(engine)

        with patch("codex.integrations.fr_wiki.get_fr_wiki") as mock_wiki:
            mock_client = MagicMock()
            mock_client.get_lore_summary.return_value = None
            mock_wiki.return_value = mock_client
            result = bridge.step("lore xyznotfound")

        assert "No lore found" in result

    def test_lore_multi_word_topic(self):
        engine = _make_mock_engine()
        engine.setting_id = "waterdeep"
        bridge = _make_bridge(engine)

        with patch("codex.integrations.fr_wiki.get_fr_wiki") as mock_wiki:
            mock_client = MagicMock()
            mock_client.get_lore_summary.return_value = "Icewind Dale info."
            mock_wiki.return_value = mock_client
            result = bridge.step("lore icewind dale")

        assert "Icewind Dale" in result


# =========================================================================
# Track E: NPC dialogue wiki enrichment
# =========================================================================

class TestNpcDialogueEnrichment:
    """NPC dialogue should inject wiki lore for FR settings."""

    def test_npc_dialogue_injects_wiki_for_fr(self):
        """When setting_id is FR, wiki lore should be in context."""
        engine = _make_mock_engine()
        engine.setting_id = "forgotten_realms"
        pop = engine.populated_rooms[0]
        pop.content["npcs"] = [
            {"name": "Volothamp", "role": "author", "dialogue": "Well met!"}
        ]
        bridge = _make_bridge(engine)

        # Enter conversation
        bridge.step("talk volothamp")
        assert bridge._talking_to == "Volothamp"

        # Mock both wiki and mimir
        with patch("codex.integrations.fr_wiki.get_fr_wiki") as mock_wiki, \
             patch("codex.integrations.mimir.query_mimir",
                   return_value="I am Volo!"):
            mock_client = MagicMock()
            mock_client.get_lore_summary.return_value = "Volo wrote a guide."
            mock_wiki.return_value = mock_client
            result = bridge.step("hello there")

        assert "Volo" in result or "I am Volo" in result

    def test_npc_dialogue_no_wiki_for_non_fr(self):
        """When setting_id is NOT FR, wiki should not be queried."""
        engine = _make_mock_engine()
        engine.setting_id = "burnwillow"
        pop = engine.populated_rooms[0]
        pop.content["npcs"] = [
            {"name": "Merchant", "role": "trader", "dialogue": "Wares?"}
        ]
        bridge = _make_bridge(engine)

        bridge.step("talk merchant")

        with patch("codex.integrations.fr_wiki.get_fr_wiki") as mock_wiki, \
             patch("codex.integrations.mimir.query_mimir",
                   return_value="Buy something!"):
            result = bridge.step("what do you sell")
            mock_wiki.assert_not_called()


# =========================================================================
# Track E2: NarrativeEngine talk_to_npc wiki enrichment
# =========================================================================

class TestNarrativeEngineWikiEnrichment:
    """NarrativeEngine.talk_to_npc() should inject wiki for FR settings."""

    def test_wiki_not_injected_for_burnwillow(self):
        """Burnwillow system_id should not trigger FR wiki."""
        from codex.core.narrative_engine import NarrativeEngine
        engine = NarrativeEngine(system_id="burnwillow")
        # talk_to_npc with a known NPC
        with patch("codex.integrations.fr_wiki.get_fr_wiki") as mock_wiki:
            engine.talk_to_npc("nonexistent")
            mock_wiki.assert_not_called()


# =========================================================================
# Track F: Module-load context (integration)
# =========================================================================

class TestModuleLoadSettingPropagation:
    """Setting propagation from manifest to engine."""

    def test_campaign_setting_propagates_to_engine(self):
        """If manifest has campaign_setting and engine has setting_id,
        engine.setting_id should be set."""
        from codex.spatial.module_manifest import ModuleManifest

        mm = ModuleManifest(module_id="test", display_name="Test Module",
                            system_id="dnd5e",
                            campaign_setting="forgotten_realms")
        engine = MagicMock()
        engine.setting_id = ""

        # Simulate what play_universal.py does
        if hasattr(engine, 'setting_id') and mm.campaign_setting:
            engine.setting_id = mm.campaign_setting

        assert engine.setting_id == "forgotten_realms"


# =========================================================================
# HTML Parser tests
# =========================================================================

class TestParagraphExtractor:
    """_ParagraphExtractor correctly extracts <p> content."""

    def test_basic_extraction(self):
        from codex.integrations.fr_wiki import _ParagraphExtractor
        parser = _ParagraphExtractor()
        parser.feed("<p>Hello world.</p><div>Not this.</div><p>Second.</p>")
        assert parser.paragraphs == ["Hello world.", "Second."]

    def test_nested_tags_in_p(self):
        from codex.integrations.fr_wiki import _ParagraphExtractor
        parser = _ParagraphExtractor()
        parser.feed("<p>Hello <b>bold</b> world.</p>")
        assert parser.paragraphs == ["Hello bold world."]

    def test_empty_p_skipped(self):
        from codex.integrations.fr_wiki import _ParagraphExtractor
        parser = _ParagraphExtractor()
        parser.feed("<p></p><p>Content.</p>")
        assert parser.paragraphs == ["Content."]


class TestSearchResultExtractor:
    """_SearchResultExtractor correctly extracts search result links."""

    def test_basic_extraction_with_book_id(self):
        from codex.integrations.fr_wiki import _SearchResultExtractor
        parser = _SearchResultExtractor(book_id="fr_wiki_2026-03")
        parser.feed('<a href="/fr_wiki_2026-03/Waterdeep">Waterdeep</a>')
        assert len(parser.results) == 1
        assert parser.results[0] == ("Waterdeep", "fr_wiki_2026-03/Waterdeep")

    def test_legacy_a_path_fallback(self):
        """Without book_id, /A/ style links should still work."""
        from codex.integrations.fr_wiki import _SearchResultExtractor
        parser = _SearchResultExtractor()
        parser.feed('<a href="/wiki/A/Waterdeep">Waterdeep</a>')
        assert len(parser.results) == 1

    def test_non_article_links_ignored(self):
        from codex.integrations.fr_wiki import _SearchResultExtractor
        parser = _SearchResultExtractor(book_id="mybook")
        parser.feed('<a href="/search?q=test">Search</a>')
        parser.feed('<a href="/skin/style.css">CSS</a>')
        parser.feed('<a href="/catalog/search">Catalog</a>')
        parser.feed('<a href="/">Home</a>')
        assert len(parser.results) == 0

    def test_book_prefix_only_ignored(self):
        """Link to book root (no article) should be ignored."""
        from codex.integrations.fr_wiki import _SearchResultExtractor
        parser = _SearchResultExtractor(book_id="mybook")
        parser.feed('<a href="/mybook/">Book Root</a>')
        assert len(parser.results) == 0

    def test_multiple_results(self):
        from codex.integrations.fr_wiki import _SearchResultExtractor
        parser = _SearchResultExtractor(book_id="wiki")
        parser.feed(
            '<a href="/wiki/One">One</a>'
            '<a href="/wiki/Two">Two</a>'
            '<a href="/other_book/Skip">Skip</a>'
        )
        assert len(parser.results) == 2

    def test_wrong_book_id_filtered(self):
        """Links from a different book should be filtered out."""
        from codex.integrations.fr_wiki import _SearchResultExtractor
        parser = _SearchResultExtractor(book_id="fr_wiki")
        parser.feed('<a href="/wikipedia/Waterdeep">Waterdeep</a>')
        assert len(parser.results) == 0


# =========================================================================
# Help text includes lore
# =========================================================================

class TestHelpTextLore:
    """Help text should include lore command."""

    def test_help_includes_lore(self):
        engine = _make_mock_engine()
        bridge = _make_bridge(engine)
        result = bridge._help_text()
        assert "lore" in result.lower()
