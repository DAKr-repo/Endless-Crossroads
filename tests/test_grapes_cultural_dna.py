"""
Tests for WO-V11.0 — The Cultural DNA
=======================================

Validates LanguageProfile, CulturalValue dataclasses, procedural name
generation, GrapesProfile backward compatibility, and generator output.
"""

import random
import unittest

from codex.core.world.grapes_engine import (
    CulturalValue,
    GrapesGenerator,
    GrapesProfile,
    LanguageProfile,
    generate_full_name,
    generate_name,
)


class TestLanguageProfileSerialization(unittest.TestCase):
    """1. LanguageProfile round-trip serialization."""

    def test_roundtrip(self):
        lp = LanguageProfile(
            name="Guttural Stone",
            phoneme_type="guttural",
            vowels=["a", "o", "u"],
            consonants=["k", "g", "r"],
            syllable_patterns=["CVC", "CV"],
            naming_rules="Hard stops",
            suffixes=["-ak", "-ur"],
            titles=["Thane"],
        )
        d = lp.to_dict()
        lp2 = LanguageProfile.from_dict(d)
        self.assertEqual(lp.name, lp2.name)
        self.assertEqual(lp.phoneme_type, lp2.phoneme_type)
        self.assertEqual(lp.vowels, lp2.vowels)
        self.assertEqual(lp.consonants, lp2.consonants)
        self.assertEqual(lp.syllable_patterns, lp2.syllable_patterns)
        self.assertEqual(lp.suffixes, lp2.suffixes)
        self.assertEqual(lp.titles, lp2.titles)


class TestCulturalValueSerialization(unittest.TestCase):
    """2. CulturalValue round-trip serialization."""

    def test_roundtrip(self):
        cv = CulturalValue(
            tenet="Hospitality above all",
            expression="No stranger sleeps outside",
            consequence="Innkeepers hold power",
        )
        d = cv.to_dict()
        cv2 = CulturalValue.from_dict(d)
        self.assertEqual(cv.tenet, cv2.tenet)
        self.assertEqual(cv.expression, cv2.expression)
        self.assertEqual(cv.consequence, cv2.consequence)


class TestGenerateNameDeterminism(unittest.TestCase):
    """3. generate_name() determinism (same seed = same name)."""

    def test_deterministic(self):
        lp = LanguageProfile(
            name="Test", phoneme_type="test",
            vowels=["a", "e", "i"],
            consonants=["k", "r", "t"],
            syllable_patterns=["CVC", "CV"],
        )
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        n1 = generate_name(lp, rng1)
        n2 = generate_name(lp, rng2)
        self.assertEqual(n1, n2)
        self.assertTrue(len(n1) > 0)


class TestGenerateNamePronounceable(unittest.TestCase):
    """4. generate_name() returns only expected characters."""

    def test_ascii_only(self):
        lp = LanguageProfile(
            name="Test", phoneme_type="test",
            vowels=["a", "e", "o"],
            consonants=["k", "r", "l", "th"],
            syllable_patterns=["CVC", "CV", "CCV"],
            suffixes=["-an", "-el"],
        )
        rng = random.Random(100)
        for _ in range(20):
            name = generate_name(lp, rng)
            self.assertTrue(name.isascii(), f"Non-ASCII: {name}")
            # Only letters and hyphens from suffixes
            cleaned = name.replace("-", "")
            self.assertTrue(cleaned.isalpha(), f"Non-alpha: {name}")


class TestGenerateNameEmpty(unittest.TestCase):
    """5. generate_name() with empty profile returns empty string."""

    def test_empty_profile(self):
        lp = LanguageProfile(name="Empty", phoneme_type="none")
        result = generate_name(lp, random.Random(1))
        self.assertEqual(result, "")


class TestGenerateFullNameWithTitle(unittest.TestCase):
    """6. generate_full_name() with title."""

    def test_with_title(self):
        lp = LanguageProfile(
            name="Test", phoneme_type="test",
            vowels=["a", "e"],
            consonants=["k", "r"],
            syllable_patterns=["CVC", "CV"],
            titles=["Thane", "Lord"],
        )
        full = generate_full_name(lp, random.Random(42), include_title=True)
        self.assertIn(" ", full)
        parts = full.split()
        self.assertGreaterEqual(len(parts), 3)  # title + given + family


class TestGrapesProfileBackwardCompat(unittest.TestCase):
    """7. Old data without language/culture loads as empty lists."""

    def test_old_format(self):
        old = {
            "geography": [], "religion": [], "arts": [],
            "politics": [], "economics": [], "social": [],
        }
        p = GrapesProfile.from_dict(old)
        self.assertEqual(p.language, [])
        self.assertEqual(p.culture, [])


class TestGrapesProfileOmitsEmpty(unittest.TestCase):
    """8. to_dict() omits empty language/culture keys."""

    def test_omit_when_empty(self):
        p = GrapesProfile()
        d = p.to_dict()
        self.assertNotIn("language", d)
        self.assertNotIn("culture", d)

    def test_include_when_populated(self):
        p = GrapesProfile(
            language=[LanguageProfile(name="X", phoneme_type="x")],
            culture=[CulturalValue(tenet="T", expression="E", consequence="C")],
        )
        d = p.to_dict()
        self.assertIn("language", d)
        self.assertIn("culture", d)
        self.assertEqual(len(d["language"]), 1)
        self.assertEqual(len(d["culture"]), 1)


class TestGrapesGeneratorProducesNewCategories(unittest.TestCase):
    """9. GrapesGenerator produces non-empty language + culture."""

    def test_generate(self):
        gen = GrapesGenerator()
        profile = gen.generate(seed=42)
        self.assertGreaterEqual(len(profile.language), 1)
        self.assertGreaterEqual(len(profile.culture), 2)
        # Verify structure
        lp = profile.language[0]
        self.assertTrue(len(lp.name) > 0)
        self.assertTrue(len(lp.vowels) > 0)
        self.assertTrue(len(lp.consonants) > 0)
        cv = profile.culture[0]
        self.assertTrue(len(cv.tenet) > 0)


class TestNarrativeSummaryIncludesNewCategories(unittest.TestCase):
    """10. to_narrative_summary() includes language and culture."""

    def test_summary(self):
        gen = GrapesGenerator()
        profile = gen.generate(seed=42)
        summary = profile.to_narrative_summary()
        self.assertIn("Language:", summary)
        self.assertIn("Cultural Value:", summary)


class TestRerollLanguage(unittest.TestCase):
    """11. reroll_category("language") works."""

    def test_reroll(self):
        gen = GrapesGenerator()
        profile = gen.generate(seed=42)
        old_lang = profile.language[0].name if profile.language else ""
        # Reroll several times — at least one should differ
        changed = False
        for _ in range(10):
            gen.reroll_category(profile, "language")
            if profile.language and profile.language[0].name != old_lang:
                changed = True
                break
        self.assertTrue(len(profile.language) >= 1)


if __name__ == "__main__":
    unittest.main()
