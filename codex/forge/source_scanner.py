"""
codex_source_scanner.py - Vault Content Availability Scanner
=============================================================
Scans vault SOURCE directories for PDFs and returns a set of
available source keywords. Used by codex_char_wizard.py to filter
character creation options at runtime.

Author: Codex Team (WO 086-B)
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent  # -> Codex/

# Mapping: if a PDF filename contains the key, add the value as a keyword
_KEYWORD_MAP = {
    "Strahd": "Ravenloft",
    "Ravenloft": "Ravenloft",
    "Richten": "Ravenloft",
    "Eberron": "Eberron",
    "Sword Coast": "Sword Coast",
    "Xanathar": "Xanathar",
    "Tasha": "Tasha",
    "Player": "Core",
    "Dungeon Master": "Core",
}


def scan_content_availability(vault_path: str = None) -> set[str]:
    """Scan SOURCE directory (recursive) for PDF filenames.
    Returns set of available source keywords."""
    keywords = {"Core"}  # Core is always available
    if vault_path is None:
        vault_path = str(_ROOT / "vault" / "dnd5e" / "SOURCE")
    source_dir = Path(vault_path)
    if not source_dir.exists():
        return keywords
    for pdf in source_dir.rglob("*.pdf"):
        name = pdf.stem
        for fragment, keyword in _KEYWORD_MAP.items():
            if fragment in name:
                keywords.add(keyword)
    return keywords


def scan_vault_structure(vault_path: str = None) -> dict:
    """Scan vault directory structure and categorize by content type.

    Maps standard vault subdirectories:
      SOURCE/RULES, SOURCE/Rules -> rules
      SETTINGS, SOURCE/SETTINGS, SOURCE/Settings -> settings
      MODULES, MODULE -> modules

    Returns:
        {"rules": [...], "settings": [...], "modules": [...]}
    """
    result = {"rules": [], "settings": [], "modules": []}
    if vault_path is None:
        vault_path = str(_ROOT / "vault")
    base = Path(vault_path)
    if not base.exists():
        return result

    # Map directory names to category
    _DIR_MAP = {
        "RULES": "rules", "Rules": "rules",
        "SETTINGS": "settings", "Settings": "settings",
        "MODULES": "modules", "MODULE": "modules",
    }

    # Scan SOURCE subdirectories
    source_dir = base / "SOURCE"
    if source_dir.is_dir():
        for sub in source_dir.iterdir():
            if sub.is_dir() and sub.name in _DIR_MAP:
                category = _DIR_MAP[sub.name]
                for f in sorted(sub.iterdir()):
                    if f.is_file():
                        result[category].append(str(f))
            elif sub.is_file():
                # Files directly in SOURCE/ are treated as rules
                result["rules"].append(str(sub))

    # Scan top-level MODULES/MODULE directories
    for dirname in ("MODULES", "MODULE"):
        mod_dir = base / dirname
        if mod_dir.is_dir():
            for f in sorted(mod_dir.iterdir()):
                if f.is_file():
                    result["modules"].append(str(f))

    # Scan top-level SETTINGS directory
    for dirname in ("SETTINGS", "Settings"):
        set_dir = base / dirname
        if set_dir.is_dir():
            for f in sorted(set_dir.iterdir()):
                if f.is_file():
                    result["settings"].append(str(f))

    return result


def _infer_system_id(vault_path: str) -> str:
    """Infer system_id from a vault path.

    E.g. 'vault/FITD/bitd' -> 'bitd', 'vault/dnd5e' -> 'dnd5e',
    'vault/ILLUMINATED_WORLDS/Candela_Obscura' -> 'candela'.
    """
    name = Path(vault_path).name.lower()
    _ALIASES = {
        "cbr_pnk": "cbrpnk",
        "candela_obscura": "candela",
    }
    return _ALIASES.get(name, name)


def _scan_adventure_modules(system_id: str) -> list:
    """Scan vault_maps/modules/ for adventure modules matching system_id.

    Returns list of {"name": display_name, "path": manifest_path,
    "module_id": dir_name} dicts.
    """
    import json
    modules_dir = _ROOT / "vault_maps" / "modules"
    if not modules_dir.is_dir():
        return []
    results = []
    for entry in sorted(modules_dir.iterdir()):
        if not entry.is_dir():
            continue
        mf = entry / "module_manifest.json"
        if not mf.exists():
            continue
        try:
            data = json.loads(mf.read_text())
            if data.get("system_id") == system_id:
                results.append({
                    "name": data.get("display_name", entry.name),
                    "path": str(mf),
                    "module_id": data.get("module_id", entry.name),
                })
        except Exception:
            continue
    return results


def scan_system_content(vault_path: str, parent_path: str = None) -> dict:
    """Scan a specific system's vault directory for available content.

    Categorizes files found under SOURCE/, SETTINGS/, and MODULES/ into
    rules, settings, and modules. Also scans vault_maps/modules/ for
    adventure modules matching this system's ID.

    Args:
        vault_path: Path to a system's vault dir (e.g. vault/FITD/bitd/)
        parent_path: Optional parent vault dir for sub-settings. Parent
            modules/settings/rules not already in the child are merged in.

    Returns:
        {"rules": [{"name": ..., "path": ...}],
         "settings": [{"name": ..., "path": ...}],
         "modules": [{"name": ..., "path": ...}]}
    """
    result = _scan_system_content_single(vault_path)

    if parent_path:
        parent_result = _scan_system_content_single(parent_path)
        # Merge parent content not already in child (by name)
        for category in ("rules", "settings", "modules"):
            child_names = {m["name"] for m in result.get(category, [])}
            for item in parent_result.get(category, []):
                if item["name"] not in child_names:
                    result.setdefault(category, []).append(item)

    # Merge adventure modules from vault_maps/modules/
    system_id = _infer_system_id(vault_path)
    existing_names = {m["name"] for m in result.get("modules", [])}
    for mod in _scan_adventure_modules(system_id):
        if mod["name"] not in existing_names:
            existing_names.add(mod["name"])
            result["modules"].append(mod)

    # Also check the rules JSON for a "settings" key (for systems like Burnwillow
    # that define settings in the config rather than as vault files)
    if system_id:
        _config_base = Path(__file__).resolve().parent.parent.parent / "config" / "systems"
        _rules_path = _config_base / f"rules_{system_id.upper()}.json"
        if not _rules_path.exists():
            _rules_path = _config_base / f"rules_{system_id}.json"
        if _rules_path.exists():
            try:
                import json as _json
                _rules = _json.loads(_rules_path.read_text())
                _json_settings = _rules.get("settings", {})
                if isinstance(_json_settings, dict):
                    result.setdefault("settings", [])
                    existing_setting_names = {s["name"] for s in result["settings"]}
                    for _sid, _sdata in _json_settings.items():
                        _sname = _sdata.get("name", _sid)
                        if _sname not in existing_setting_names:
                            result["settings"].append({
                                "name": _sname,
                                "path": f"rules_{system_id}.json#{_sid}",
                                "description": _sdata.get("description", ""),
                                "status": _sdata.get("status", ""),
                            })
                            existing_setting_names.add(_sname)
            except Exception:
                pass

    return result


def _scan_system_content_single(vault_path: str) -> dict:
    """Scan a single vault directory (no parent merging)."""
    result = {"rules": [], "settings": [], "modules": []}
    base = Path(vault_path)
    if not base.exists():
        return result

    seen_paths = set()

    def _add(category: str, file_path: Path):
        s = str(file_path)
        if s not in seen_paths:
            seen_paths.add(s)
            result[category].append({"name": file_path.stem, "path": s})

    # SOURCE/ — files directly inside are rules; subdirs mapped by name
    source_dir = base / "SOURCE"
    if source_dir.is_dir():
        _subdir_map = {
            "Rules": "rules", "RULES": "rules",
            "Bestiary": "rules",
            "Settings": "settings", "SETTINGS": "settings",
        }
        for item in sorted(source_dir.iterdir()):
            if item.is_file():
                _add("rules", item)
            elif item.is_dir() and item.name in _subdir_map:
                cat = _subdir_map[item.name]
                for f in sorted(item.iterdir()):
                    if f.is_file():
                        _add(cat, f)

    # Top-level SETTINGS/ and SUPPLEMENTS/
    for dirname in ("SETTINGS", "Settings", "SUPPLEMENTS"):
        d = base / dirname
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if f.is_file():
                    _add("settings", f)

    # Top-level MODULES/ or MODULE/
    for dirname in ("MODULES", "MODULE"):
        d = base / dirname
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if f.is_file():
                    _add("modules", f)

    return result
