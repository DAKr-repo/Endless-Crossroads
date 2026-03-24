"""
codex/core/services/character_loom.py — Unified Character Loom
================================================================
A queryable service that any game engine can call to get personalized
narrative strings from character data. Replaces static prompts with
dynamic, character-aware text.

The Loom accepts a CharacterSheet (or minimal dict) and resolves
``{loom.*}`` template variables at runtime. Engines that don't provide
character data get graceful fallbacks — every variable has a default.

Usage:
    loom = CharacterLoom(character_sheet)
    text = loom.resolve("A stranger recognizes {loom.name} as a former {loom.background}.")
    # → "A stranger recognizes Kael as a former Soldier."

    # Or query individual fields:
    loom.name        → "Kael"
    loom.background  → "Soldier"
    loom.bond        → "my sister's safety"
    loom.ideal       → "Justice"
    loom.flaw        → "I trust too easily"

WO-V122: Core service. Patient zero: Crown & Crew (#124).
Cross-system rollout: NarrativeBridge (#129), Combat (#130), NPC (#131), Mimir (#132).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Default fallbacks when character data is missing
_DEFAULTS = {
    "name": "Traveler",
    "background": "unknown origins",
    "background_story": "",
    "background_hint": "a past they don't discuss",
    "personality": "a guarded demeanor",
    "ideal": "survival",
    "bond": "someone they left behind",
    "bond_person": "someone from your past",
    "flaw": "a weakness they won't name",
    "friend": "an old ally",
    "rival": "an old enemy",
    "alignment": "unaligned",
    "class": "wanderer",
    "race": "stranger",
    "pronouns": "they/them",
    "catalyst": "an unnamed purpose",
    "look": "a weathered appearance",
}

# Pattern for {loom.variable_name} in template strings
_LOOM_PATTERN = re.compile(r"\{loom\.(\w+)\}")


@dataclass
class CharacterLoom:
    """Resolves character-aware narrative variables from a CharacterSheet or dict.

    Accepts either a CharacterSheet dataclass or a plain dict with the same
    field names. Missing fields fall back to atmospheric defaults rather
    than empty strings — "someone they left behind" instead of "".

    Attributes:
        _data: The resolved character data dict.
        _overrides: Optional per-session overrides (e.g., Crown terms).
    """
    _data: Dict[str, Any] = field(default_factory=dict)
    _overrides: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_sheet(cls, sheet: Any) -> "CharacterLoom":
        """Create a Loom from a CharacterSheet dataclass.

        Extracts narrative-relevant fields and normalizes them into
        the Loom's variable namespace.
        """
        data = _extract_from_sheet(sheet)
        return cls(_data=data)

    @classmethod
    def from_dict(cls, char_dict: Dict[str, Any]) -> "CharacterLoom":
        """Create a Loom from a plain character dict (e.g., from save data)."""
        data = _extract_from_dict(char_dict)
        return cls(_data=data)

    @classmethod
    def empty(cls) -> "CharacterLoom":
        """Create an empty Loom that returns defaults for everything."""
        return cls(_data={})

    def set_override(self, key: str, value: str) -> None:
        """Set a per-session override for a variable.

        Useful for Crown & Crew term substitution:
            loom.set_override("authority", "The Garrison")
        """
        self._overrides[key] = value

    # ── Property accessors (convenience) ─────────────────────────────

    @property
    def name(self) -> str:
        return self._get("name")

    @property
    def background(self) -> str:
        return self._get("background")

    @property
    def background_hint(self) -> str:
        """A short hint suitable for inline narration.

        Returns background if available, else the atmospheric default.
        """
        bg = self._get("background")
        if bg and bg != _DEFAULTS["background"]:
            return f"a former {bg}"
        return self._get("background_hint")

    @property
    def personality(self) -> str:
        return self._get("personality")

    @property
    def ideal(self) -> str:
        return self._get("ideal")

    @property
    def bond(self) -> str:
        return self._get("bond")

    @property
    def bond_person(self) -> str:
        return self._get("bond_person")

    @property
    def flaw(self) -> str:
        return self._get("flaw")

    @property
    def friend(self) -> str:
        return self._get("friend")

    @property
    def rival(self) -> str:
        return self._get("rival")

    @property
    def alignment(self) -> str:
        return self._get("alignment")

    @property
    def pronouns(self) -> str:
        return self._get("pronouns")

    @property
    def catalyst(self) -> str:
        return self._get("catalyst")

    # ── Core resolution ──────────────────────────────────────────────

    def resolve(self, template: str) -> str:
        """Resolve all ``{loom.*}`` variables in a template string.

        Variables not found in character data or overrides are replaced
        with their atmospheric defaults. Templates without any
        ``{loom.*}`` variables are returned unchanged.

        Args:
            template: A string potentially containing {loom.name},
                      {loom.background}, {loom.bond}, etc.

        Returns:
            The resolved string with all variables substituted.
        """
        if "{loom." not in template:
            return template

        def _replacer(match: re.Match) -> str:
            key = match.group(1)
            # Check overrides first
            if key in self._overrides:
                return self._overrides[key]
            # Then character data
            if key in self._data and self._data[key]:
                return str(self._data[key])
            # Then defaults
            return _DEFAULTS.get(key, match.group(0))

        return _LOOM_PATTERN.sub(_replacer, template)

    def get_context_block(self, max_tokens: int = 200) -> str:
        """Build a compact context block for LLM prompt injection.

        Returns a short paragraph summarizing the character's narrative
        identity, suitable for appending to Mimir prompts.

        Args:
            max_tokens: Approximate character limit for the block.
        """
        parts = []
        name = self._get("name")
        if name != _DEFAULTS["name"]:
            parts.append(f"The character is {name}")
        bg = self._get("background")
        if bg != _DEFAULTS["background"]:
            parts.append(f"a {bg}")
        ideal = self._get("ideal")
        if ideal != _DEFAULTS["ideal"]:
            parts.append(f"who believes in {ideal}")
        bond = self._get("bond")
        if bond != _DEFAULTS["bond"]:
            parts.append(f"and is bound to {bond}")
        flaw = self._get("flaw")
        if flaw != _DEFAULTS["flaw"]:
            parts.append(f"but struggles with {flaw}")

        if not parts:
            return ""

        block = ", ".join(parts) + "."
        if len(block) > max_tokens:
            block = block[:max_tokens].rsplit(" ", 1)[0] + "..."
        return block

    def has_data(self) -> bool:
        """Return True if the Loom has any character data beyond defaults."""
        return bool(self._data)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for save/load."""
        return {"data": dict(self._data), "overrides": dict(self._overrides)}

    @classmethod
    def restore(cls, saved: Dict[str, Any]) -> "CharacterLoom":
        """Restore from serialized dict."""
        return cls(
            _data=saved.get("data", {}),
            _overrides=saved.get("overrides", {}),
        )

    # ── Internal ─────────────────────────────────────────────────────

    def _get(self, key: str) -> str:
        """Get a value: overrides → character data → defaults."""
        if key in self._overrides:
            return self._overrides[key]
        val = self._data.get(key, "")
        if val:
            return str(val)
        return _DEFAULTS.get(key, "")


# =====================================================================
# Extraction helpers
# =====================================================================

def _extract_from_sheet(sheet: Any) -> Dict[str, Any]:
    """Extract narrative fields from a CharacterSheet dataclass."""
    data: Dict[str, Any] = {}

    # Direct field mappings
    for attr in ("name", "background", "background_story", "alignment",
                 "pronouns", "friend", "rival", "catalyst", "look",
                 "alias", "style", "purpose", "obstacle"):
        val = getattr(sheet, attr, "")
        if val:
            data[attr] = str(val)

    # Class/race from choices dict
    choices = getattr(sheet, "choices", {}) or {}
    if choices.get("class"):
        data["class"] = str(choices["class"])
    if choices.get("race"):
        data["race"] = str(choices["race"])

    # First element of list fields
    for attr, key in [
        ("personality_traits", "personality"),
        ("ideals", "ideal"),
        ("bonds", "bond"),
        ("flaws", "flaw"),
    ]:
        lst = getattr(sheet, attr, []) or []
        if lst:
            data[key] = str(lst[0])
            # Also store the full list under plural key
            data[f"{key}s"] = [str(x) for x in lst]

    # Bond person: try to extract a name from the bond text
    bond_text = data.get("bond", "")
    if bond_text:
        data["bond_person"] = _extract_person_from_bond(bond_text)

    # Background hint for inline narration
    bg = data.get("background", "")
    if bg:
        data["background_hint"] = f"a former {bg}"

    return data


def _extract_from_dict(char_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Extract narrative fields from a plain dict."""
    data: Dict[str, Any] = {}

    for key in ("name", "background", "background_story", "alignment",
                "pronouns", "friend", "rival", "catalyst", "look",
                "personality", "ideal", "bond", "flaw", "bond_person",
                "class", "race", "alias", "style", "purpose", "obstacle"):
        val = char_dict.get(key, "")
        if val:
            data[key] = str(val)

    # Handle list fields → take first element
    for list_key, single_key in [
        ("personality_traits", "personality"),
        ("ideals", "ideal"),
        ("bonds", "bond"),
        ("flaws", "flaw"),
    ]:
        if single_key not in data:
            lst = char_dict.get(list_key, [])
            if lst and isinstance(lst, list):
                data[single_key] = str(lst[0])

    # Bond person extraction
    if "bond" in data and "bond_person" not in data:
        data["bond_person"] = _extract_person_from_bond(data["bond"])

    # Background hint
    if "background" in data and "background_hint" not in data:
        data["background_hint"] = f"a former {data['background']}"

    return data


def _extract_person_from_bond(bond_text: str) -> str:
    """Best-effort extraction of a person reference from bond text.

    Looks for patterns like "my sister", "my mentor", "the temple",
    "Captain Vane". Returns the bond text itself if no clear person found.
    """
    if not bond_text:
        return _DEFAULTS["bond_person"]

    # Common patterns: "my X", "a X I once knew"
    import re as _re
    person_match = _re.search(
        r"\b(?:my|the)\s+([\w\s]+?)(?:\s+(?:who|that|in|from|at|is|was)\b|[.,;!?]|$)",
        bond_text, _re.IGNORECASE,
    )
    if person_match:
        person = person_match.group(1).strip()
        if len(person) > 3 and len(person) < 40:
            return person

    # If bond is short enough, use it directly
    if len(bond_text) < 50:
        return bond_text

    return _DEFAULTS["bond_person"]
