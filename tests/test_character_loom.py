"""Tests for codex.core.services.character_loom — Unified Character Loom."""

import pytest
from codex.core.services.character_loom import CharacterLoom, _DEFAULTS


class TestLoomCreation:
    """Test Loom construction from various sources."""

    def test_empty_loom(self):
        loom = CharacterLoom.empty()
        assert loom.name == "Traveler"
        assert loom.background == "unknown origins"
        assert not loom.has_data()

    def test_from_dict_basic(self):
        loom = CharacterLoom.from_dict({"name": "Kael", "background": "Soldier"})
        assert loom.name == "Kael"
        assert loom.background == "Soldier"
        assert loom.has_data()

    def test_from_dict_with_lists(self):
        loom = CharacterLoom.from_dict({
            "name": "Sera",
            "personality_traits": ["Brave and reckless", "Quick to laugh"],
            "ideals": ["Freedom above all"],
            "bonds": ["My sister's safety is everything"],
            "flaws": ["I trust too easily"],
        })
        assert loom.personality == "Brave and reckless"
        assert loom.ideal == "Freedom above all"
        assert loom.bond == "My sister's safety is everything"
        assert loom.flaw == "I trust too easily"

    def test_from_sheet(self):
        """Test creation from a CharacterSheet-like object."""
        from dataclasses import dataclass, field
        from typing import List, Dict, Any

        @dataclass
        class MockSheet:
            system_id: str = "dnd5e"
            name: str = "Durnan"
            background: str = "Soldier"
            alignment: str = "Lawful Neutral"
            personality_traits: List[str] = field(default_factory=lambda: ["Gruff but fair"])
            ideals: List[str] = field(default_factory=lambda: ["Duty"])
            bonds: List[str] = field(default_factory=lambda: ["My tavern is my kingdom"])
            flaws: List[str] = field(default_factory=lambda: ["I never forgive a slight"])
            friend: str = "Mirt"
            rival: str = "Xanathar"
            choices: Dict[str, Any] = field(default_factory=lambda: {"class": "Fighter", "race": "Human"})
            pronouns: str = "he/him"
            background_story: str = ""
            catalyst: str = ""
            look: str = ""
            alias: str = ""
            style: str = ""
            purpose: str = ""
            obstacle: str = ""

        sheet = MockSheet()
        loom = CharacterLoom.from_sheet(sheet)
        assert loom.name == "Durnan"
        assert loom.background == "Soldier"
        assert loom.ideal == "Duty"
        assert loom.bond == "My tavern is my kingdom"
        assert loom.flaw == "I never forgive a slight"
        assert loom.friend == "Mirt"
        assert loom.rival == "Xanathar"
        assert loom._data.get("class") == "Fighter"

    def test_missing_fields_use_defaults(self):
        loom = CharacterLoom.from_dict({"name": "Kael"})
        assert loom.ideal == _DEFAULTS["ideal"]
        assert loom.bond == _DEFAULTS["bond"]
        assert loom.flaw == _DEFAULTS["flaw"]


class TestLoomResolve:
    """Test template variable resolution."""

    def test_resolve_basic(self):
        loom = CharacterLoom.from_dict({"name": "Kael", "background": "Soldier"})
        result = loom.resolve("Welcome, {loom.name}. I see you were a {loom.background}.")
        assert result == "Welcome, Kael. I see you were a Soldier."

    def test_resolve_no_variables(self):
        loom = CharacterLoom.from_dict({"name": "Kael"})
        text = "A plain string with no variables."
        assert loom.resolve(text) == text

    def test_resolve_missing_uses_default(self):
        loom = CharacterLoom.from_dict({"name": "Kael"})
        result = loom.resolve("Your bond to {loom.bond} calls you.")
        assert "someone they left behind" in result

    def test_resolve_multiple_variables(self):
        loom = CharacterLoom.from_dict({
            "name": "Sera",
            "ideal": "Freedom",
            "flaw": "recklessness",
        })
        result = loom.resolve(
            "{loom.name} believes in {loom.ideal}, but {loom.flaw} may be their undoing."
        )
        assert result == "Sera believes in Freedom, but recklessness may be their undoing."

    def test_resolve_unknown_variable_preserved(self):
        loom = CharacterLoom.from_dict({"name": "Kael"})
        result = loom.resolve("The {loom.nonexistent_field} beckons.")
        assert "{loom.nonexistent_field}" in result

    def test_resolve_with_overrides(self):
        loom = CharacterLoom.from_dict({"name": "Kael"})
        loom.set_override("authority", "The Garrison")
        result = loom.resolve("{loom.authority} demands your surrender, {loom.name}.")
        assert result == "The Garrison demands your surrender, Kael."

    def test_override_takes_precedence(self):
        loom = CharacterLoom.from_dict({"name": "Kael"})
        loom.set_override("name", "Commander Kael")
        assert loom.name == "Commander Kael"
        result = loom.resolve("Attention, {loom.name}!")
        assert result == "Attention, Commander Kael!"


class TestBackgroundHint:
    """Test the background_hint property for inline narration."""

    def test_hint_with_background(self):
        loom = CharacterLoom.from_dict({"background": "Soldier"})
        assert loom.background_hint == "a former Soldier"

    def test_hint_without_background(self):
        loom = CharacterLoom.empty()
        assert loom.background_hint == _DEFAULTS["background_hint"]


class TestBondPersonExtraction:
    """Test extraction of person references from bond text."""

    def test_my_sister(self):
        loom = CharacterLoom.from_dict({"bonds": ["my sister is everything to me"]})
        assert "sister" in loom.bond_person.lower()

    def test_the_temple(self):
        loom = CharacterLoom.from_dict({"bonds": ["the temple where I was raised"]})
        assert "temple" in loom.bond_person.lower()

    def test_short_bond_used_directly(self):
        loom = CharacterLoom.from_dict({"bonds": ["Captain Vane"]})
        assert loom.bond_person == "Captain Vane"

    def test_empty_bond_uses_default(self):
        loom = CharacterLoom.from_dict({})
        assert loom.bond_person == _DEFAULTS["bond_person"]


class TestContextBlock:
    """Test LLM context block generation."""

    def test_full_context(self):
        loom = CharacterLoom.from_dict({
            "name": "Sera",
            "background": "Criminal",
            "ideal": "Freedom",
            "bond": "my crew",
            "flaw": "I can't resist a dare",
        })
        block = loom.get_context_block()
        assert "Sera" in block
        assert "Criminal" in block
        assert "Freedom" in block
        assert "crew" in block
        assert "dare" in block

    def test_empty_context(self):
        loom = CharacterLoom.empty()
        block = loom.get_context_block()
        assert block == ""

    def test_context_respects_max_tokens(self):
        loom = CharacterLoom.from_dict({
            "name": "A" * 100,
            "background": "B" * 100,
            "ideal": "C" * 100,
        })
        block = loom.get_context_block(max_tokens=50)
        assert len(block) <= 55  # Slight overflow for "..." is acceptable


class TestSerialization:
    """Test save/load round-trip."""

    def test_round_trip(self):
        loom = CharacterLoom.from_dict({"name": "Kael", "ideal": "Justice"})
        loom.set_override("authority", "The Crown")
        saved = loom.to_dict()
        restored = CharacterLoom.restore(saved)
        assert restored.name == "Kael"
        assert restored.ideal == "Justice"
        assert restored.resolve("{loom.authority}") == "The Crown"

    def test_empty_round_trip(self):
        loom = CharacterLoom.empty()
        saved = loom.to_dict()
        restored = CharacterLoom.restore(saved)
        assert not restored.has_data()
        assert restored.name == _DEFAULTS["name"]


class TestMultipleCharacters:
    """Test that separate Loom instances don't interfere."""

    def test_two_looms_independent(self):
        loom_a = CharacterLoom.from_dict({"name": "Kael", "ideal": "Duty"})
        loom_b = CharacterLoom.from_dict({"name": "Sera", "ideal": "Freedom"})
        assert loom_a.resolve("{loom.name} believes in {loom.ideal}") == "Kael believes in Duty"
        assert loom_b.resolve("{loom.name} believes in {loom.ideal}") == "Sera believes in Freedom"

    def test_overrides_per_instance(self):
        loom_a = CharacterLoom.from_dict({"name": "Kael"})
        loom_b = CharacterLoom.from_dict({"name": "Sera"})
        loom_a.set_override("title", "The Enforcer")
        loom_b.set_override("title", "The Firebrand")
        assert loom_a.resolve("{loom.title}") == "The Enforcer"
        assert loom_b.resolve("{loom.title}") == "The Firebrand"
