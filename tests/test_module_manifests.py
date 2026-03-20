"""
tests/test_module_manifests.py
================================
Auto-discovers all module_manifest.json files under vault_maps/modules/,
validates their structure, and verifies that blueprint paths referenced
in zone entries actually resolve to existing files on disk.

Test categories
---------------
1. JSON validity and required top-level keys
2. Chapter structure (chapter_id, display_name, order, zones)
3. Zone entry structure (zone_id, exit_trigger per zone)
4. Blueprint path resolution (relative to manifest directory)
5. Zone chain traversal produces a non-empty list
"""

import json
import os
from pathlib import Path
from typing import List, Tuple

import pytest

# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

_VAULT_MAPS_ROOT = Path(__file__).resolve().parent.parent / "vault_maps" / "modules"

_REQUIRED_TOP_LEVEL_KEYS = {"module_id", "display_name", "system_id", "chapters"}
_REQUIRED_CHAPTER_KEYS = {"chapter_id", "display_name", "order", "zones"}
_REQUIRED_ZONE_KEYS = {"zone_id", "exit_trigger"}

_VALID_EXIT_TRIGGERS = {
    # Core triggers supported by ZoneManager.check_exit_condition()
    "boss_defeated",
    "quest_complete",
    "player_choice",
    "timer",
    "all_rooms",
    # Module-specific extension triggers (fall through to logged warning in engine)
    "investigation_complete",
    "module_complete",
    "scene_complete",
    "door_unlocked",
    "exit_reached",
    "simulacrum_exited",
}


def _discover_manifests() -> List[Tuple[str, Path]]:
    """Return a list of (module_name, manifest_path) tuples for parametrize."""
    manifests = []
    if not _VAULT_MAPS_ROOT.is_dir():
        return manifests
    for module_dir in sorted(_VAULT_MAPS_ROOT.iterdir()):
        manifest_path = module_dir / "module_manifest.json"
        if manifest_path.is_file():
            manifests.append((module_dir.name, manifest_path))
    return manifests


_MANIFEST_PARAMS = _discover_manifests()


def _load_manifest(manifest_path: Path) -> dict:
    """Load raw JSON from a manifest file."""
    with open(manifest_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Parametrized fixture
# ---------------------------------------------------------------------------

@pytest.fixture(params=_MANIFEST_PARAMS, ids=[p[0] for p in _MANIFEST_PARAMS])
def manifest_pair(request):
    """Yield (module_name, manifest_path, raw_data) for each discovered manifest."""
    module_name, manifest_path = request.param
    raw = _load_manifest(manifest_path)
    return module_name, manifest_path, raw


# ---------------------------------------------------------------------------
# 1. JSON validity and required top-level keys
# ---------------------------------------------------------------------------

class TestManifestTopLevel:
    """Validate top-level keys in each module_manifest.json."""

    def test_manifest_is_valid_json(self, manifest_pair):
        """The manifest must be loadable as valid JSON."""
        module_name, manifest_path, raw = manifest_pair
        assert isinstance(raw, dict), (
            f"{module_name}: manifest JSON root must be a dict, got {type(raw)}"
        )

    def test_required_top_level_keys_present(self, manifest_pair):
        """module_id, display_name, system_id, chapters must all be present."""
        module_name, manifest_path, raw = manifest_pair
        missing = _REQUIRED_TOP_LEVEL_KEYS - set(raw.keys())
        assert not missing, (
            f"{module_name}: manifest is missing required keys: {missing}"
        )

    def test_module_id_is_nonempty_string(self, manifest_pair):
        """module_id must be a non-empty string."""
        module_name, manifest_path, raw = manifest_pair
        mid = raw.get("module_id", "")
        assert isinstance(mid, str) and mid.strip(), (
            f"{module_name}: module_id must be a non-empty string, got {mid!r}"
        )

    def test_display_name_is_nonempty_string(self, manifest_pair):
        """display_name must be a non-empty string."""
        module_name, manifest_path, raw = manifest_pair
        dn = raw.get("display_name", "")
        assert isinstance(dn, str) and dn.strip(), (
            f"{module_name}: display_name must be a non-empty string, got {dn!r}"
        )

    def test_system_id_is_nonempty_string(self, manifest_pair):
        """system_id must be a non-empty string."""
        module_name, manifest_path, raw = manifest_pair
        sid = raw.get("system_id", "")
        assert isinstance(sid, str) and sid.strip(), (
            f"{module_name}: system_id must be a non-empty string, got {sid!r}"
        )

    def test_chapters_is_a_list(self, manifest_pair):
        """chapters must be a list."""
        module_name, manifest_path, raw = manifest_pair
        assert isinstance(raw.get("chapters"), list), (
            f"{module_name}: 'chapters' must be a list"
        )

    def test_at_least_one_chapter(self, manifest_pair):
        """A module must have at least one chapter."""
        module_name, manifest_path, raw = manifest_pair
        chapters = raw.get("chapters", [])
        assert len(chapters) >= 1, (
            f"{module_name}: must have at least one chapter, got 0"
        )


# ---------------------------------------------------------------------------
# 2. Chapter structure
# ---------------------------------------------------------------------------

class TestChapterStructure:
    """Validate that each chapter has the required fields."""

    def test_chapters_have_required_keys(self, manifest_pair):
        """Each chapter must contain chapter_id, display_name, order, zones."""
        module_name, manifest_path, raw = manifest_pair
        for i, chapter in enumerate(raw.get("chapters", [])):
            missing = _REQUIRED_CHAPTER_KEYS - set(chapter.keys())
            assert not missing, (
                f"{module_name}: chapter[{i}] is missing keys: {missing}"
            )

    def test_chapter_ids_are_unique(self, manifest_pair):
        """chapter_id must be unique within a module."""
        module_name, manifest_path, raw = manifest_pair
        ids = [ch.get("chapter_id") for ch in raw.get("chapters", [])]
        assert len(ids) == len(set(ids)), (
            f"{module_name}: duplicate chapter_id values found: {ids}"
        )

    def test_chapter_order_is_integer(self, manifest_pair):
        """The order field must be a numeric value."""
        module_name, manifest_path, raw = manifest_pair
        for i, chapter in enumerate(raw.get("chapters", [])):
            order = chapter.get("order")
            assert isinstance(order, (int, float)), (
                f"{module_name}: chapter[{i}].order must be numeric, got {order!r}"
            )

    def test_chapter_zones_is_a_list(self, manifest_pair):
        """The zones field on each chapter must be a list."""
        module_name, manifest_path, raw = manifest_pair
        for i, chapter in enumerate(raw.get("chapters", [])):
            zones = chapter.get("zones")
            assert isinstance(zones, list), (
                f"{module_name}: chapter[{i}].zones must be a list"
            )

    def test_each_chapter_has_at_least_one_zone(self, manifest_pair):
        """Every chapter must contain at least one zone (Crown campaigns excluded)."""
        module_name, manifest_path, raw = manifest_pair
        # Crown campaign modules use scenarios instead of spatial zones
        if raw.get("system_id") == "crown":
            return
        for i, chapter in enumerate(raw.get("chapters", [])):
            zones = chapter.get("zones", [])
            assert len(zones) >= 1, (
                f"{module_name}: chapter[{i}] (id={chapter.get('chapter_id')!r}) "
                f"has no zones"
            )


# ---------------------------------------------------------------------------
# 3. Zone entry structure
# ---------------------------------------------------------------------------

class TestZoneEntryStructure:
    """Validate that each zone entry has zone_id and exit_trigger."""

    def test_zones_have_required_keys(self, manifest_pair):
        """Each zone must have zone_id and exit_trigger."""
        module_name, manifest_path, raw = manifest_pair
        for ch_i, chapter in enumerate(raw.get("chapters", [])):
            for z_i, zone in enumerate(chapter.get("zones", [])):
                missing = _REQUIRED_ZONE_KEYS - set(zone.keys())
                assert not missing, (
                    f"{module_name}: chapter[{ch_i}].zone[{z_i}] "
                    f"is missing keys: {missing}"
                )

    def test_zone_ids_are_unique_within_module(self, manifest_pair):
        """zone_id must be unique across all chapters in a module."""
        module_name, manifest_path, raw = manifest_pair
        all_ids = []
        for chapter in raw.get("chapters", []):
            for zone in chapter.get("zones", []):
                all_ids.append(zone.get("zone_id"))
        assert len(all_ids) == len(set(all_ids)), (
            f"{module_name}: duplicate zone_id values found: {all_ids}"
        )

    def test_exit_triggers_are_valid(self, manifest_pair):
        """exit_trigger values must be from the supported set."""
        module_name, manifest_path, raw = manifest_pair
        for ch_i, chapter in enumerate(raw.get("chapters", [])):
            for z_i, zone in enumerate(chapter.get("zones", [])):
                trigger = zone.get("exit_trigger", "")
                assert trigger in _VALID_EXIT_TRIGGERS, (
                    f"{module_name}: chapter[{ch_i}].zone[{z_i}] "
                    f"has unknown exit_trigger {trigger!r}. "
                    f"Valid: {_VALID_EXIT_TRIGGERS}"
                )

    def test_zone_id_is_nonempty_string(self, manifest_pair):
        """zone_id must be a non-empty string."""
        module_name, manifest_path, raw = manifest_pair
        for ch_i, chapter in enumerate(raw.get("chapters", [])):
            for z_i, zone in enumerate(chapter.get("zones", [])):
                zid = zone.get("zone_id", "")
                assert isinstance(zid, str) and zid.strip(), (
                    f"{module_name}: chapter[{ch_i}].zone[{z_i}] "
                    f"has invalid zone_id {zid!r}"
                )


# ---------------------------------------------------------------------------
# 4. Blueprint path resolution
# ---------------------------------------------------------------------------

class TestBlueprintPaths:
    """Verify that blueprint paths in zone entries resolve to existing files."""

    def test_blueprint_files_exist(self, manifest_pair):
        """If a zone references a blueprint, that file must exist on disk."""
        module_name, manifest_path, raw = manifest_pair
        manifest_dir = manifest_path.parent
        missing_files = []
        for chapter in raw.get("chapters", []):
            for zone in chapter.get("zones", []):
                bp = zone.get("blueprint")
                if bp is not None:
                    resolved = manifest_dir / bp
                    if not resolved.is_file():
                        missing_files.append(
                            f"zone={zone.get('zone_id')!r} -> {resolved}"
                        )
        assert not missing_files, (
            f"{module_name}: blueprint files not found:\n"
            + "\n".join(f"  {p}" for p in missing_files)
        )

    def test_freeform_blueprint_files_exist(self, manifest_pair):
        """Blueprints in freeform_zones must also resolve to existing files."""
        module_name, manifest_path, raw = manifest_pair
        manifest_dir = manifest_path.parent
        missing_files = []
        for zone in raw.get("freeform_zones", []):
            bp = zone.get("blueprint")
            if bp is not None:
                resolved = manifest_dir / bp
                if not resolved.is_file():
                    missing_files.append(
                        f"freeform_zone={zone.get('zone_id')!r} -> {resolved}"
                    )
        assert not missing_files, (
            f"{module_name}: freeform blueprint files not found:\n"
            + "\n".join(f"  {p}" for p in missing_files)
        )


# ---------------------------------------------------------------------------
# 5. Zone chain traversal
# ---------------------------------------------------------------------------

class TestZoneChainTraversal:
    """Verify that get_zone_chain() produces a non-empty ordered list."""

    def test_zone_chain_is_nonempty(self, manifest_pair):
        """Importing ModuleManifest and calling get_zone_chain must return >= 1 zone.

        Scenario-based modules (Crown, Ashburn) use campaign.json + scenarios
        instead of spatial zones — skip those.
        """
        from codex.spatial.module_manifest import ModuleManifest

        module_name, manifest_path, raw = manifest_pair
        # Skip modules that legitimately have no zones (scenario-based)
        total_zones = sum(
            len(ch.get("zones", []))
            for ch in raw.get("chapters", [])
        )
        if total_zones == 0:
            pytest.skip(f"{module_name}: scenario-based module with no spatial zones")
        manifest = ModuleManifest.load(str(manifest_path))
        chain = manifest.get_zone_chain()
        assert len(chain) >= 1, (
            f"{module_name}: get_zone_chain() returned empty list"
        )

    def test_zone_chain_zone_ids_match_manifest(self, manifest_pair):
        """zone_ids in the chain must match what is declared in the raw JSON."""
        from codex.spatial.module_manifest import ModuleManifest

        module_name, manifest_path, raw = manifest_pair
        manifest = ModuleManifest.load(str(manifest_path))
        chain = manifest.get_zone_chain()
        chain_ids = [ze.zone_id for ze in chain]

        # Collect raw zone ids in sorted-chapter order
        sorted_chapters = sorted(raw.get("chapters", []), key=lambda c: c.get("order", 0))
        raw_ids = []
        for chapter in sorted_chapters:
            for zone in chapter.get("zones", []):
                raw_ids.append(zone["zone_id"])

        assert chain_ids == raw_ids, (
            f"{module_name}: get_zone_chain() order mismatch.\n"
            f"Expected: {raw_ids}\nGot: {chain_ids}"
        )

    def test_zone_chain_count_matches_total_zones(self, manifest_pair):
        """Chain length must equal the total number of chapter zones."""
        from codex.spatial.module_manifest import ModuleManifest

        module_name, manifest_path, raw = manifest_pair
        manifest = ModuleManifest.load(str(manifest_path))
        chain = manifest.get_zone_chain()

        total_zones = sum(
            len(ch.get("zones", []))
            for ch in raw.get("chapters", [])
        )
        assert len(chain) == total_zones, (
            f"{module_name}: chain has {len(chain)} zones but "
            f"manifest declares {total_zones}"
        )

    def test_get_next_zone_from_start_returns_second_entry(self, manifest_pair):
        """get_next_zone(0, 0) must return the zone after the first one."""
        from codex.spatial.module_manifest import ModuleManifest

        module_name, manifest_path, raw = manifest_pair
        manifest = ModuleManifest.load(str(manifest_path))
        chain = manifest.get_zone_chain()
        if len(chain) < 2:
            pytest.skip(f"{module_name}: only one zone in chain, skip next-zone test")

        result = manifest.get_next_zone(0, 0)
        assert result is not None, (
            f"{module_name}: get_next_zone(0,0) returned None for a multi-zone module"
        )
        _new_ch, _new_z, next_entry = result
        assert next_entry.zone_id != chain[0].zone_id, (
            f"{module_name}: next zone returned same id as first zone"
        )

    def test_get_next_zone_past_end_returns_none(self, manifest_pair):
        """get_next_zone() past the last chapter/zone must return None."""
        from codex.spatial.module_manifest import ModuleManifest

        module_name, manifest_path, raw = manifest_pair
        manifest = ModuleManifest.load(str(manifest_path))
        sorted_chapters = sorted(manifest.chapters, key=lambda c: c.order)
        last_ch_idx = len(sorted_chapters) - 1
        last_zone_idx = len(sorted_chapters[last_ch_idx].zones) - 1

        result = manifest.get_next_zone(last_ch_idx, last_zone_idx)
        assert result is None, (
            f"{module_name}: expected None at module end, got {result}"
        )
