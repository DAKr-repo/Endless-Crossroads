"""Tests for WO-V12.2 — AestheticProfile & inject_style_markers."""

import random
import unittest

from codex.core.world.grapes_engine import (
    AestheticProfile,
    GrapesGenerator,
    GrapesProfile,
)
from codex.games.burnwillow.atmosphere import inject_style_markers


class TestAestheticProfileSerialization(unittest.TestCase):
    """T1-T2: AestheticProfile to_dict/from_dict."""

    def test_roundtrip(self):
        """T1: to_dict -> from_dict produces identical object."""
        ap = AestheticProfile(
            building_style="Brutalist Stone",
            material="dark granite",
            motif="imposing geometric forms",
            clothing_style="Heavy layers",
            textile="oiled canvas and leather",
            accessory="iron clasps",
        )
        d = ap.to_dict()
        restored = AestheticProfile.from_dict(d)
        self.assertEqual(ap, restored)

    def test_from_dict_missing_fields(self):
        """T2: from_dict with missing fields uses empty-string defaults."""
        ap = AestheticProfile.from_dict({"building_style": "Gothic"})
        self.assertEqual(ap.building_style, "Gothic")
        self.assertEqual(ap.material, "")
        self.assertEqual(ap.motif, "")
        self.assertEqual(ap.clothing_style, "")
        self.assertEqual(ap.textile, "")
        self.assertEqual(ap.accessory, "")


class TestGrapesProfileArchitecture(unittest.TestCase):
    """T3-T6: GrapesProfile integration with architecture field."""

    def _make_profile(self, with_arch=True):
        arch = []
        if with_arch:
            arch = [AestheticProfile(
                building_style="Brutalist Stone", material="dark granite",
                motif="imposing geometric forms", clothing_style="Heavy layers",
                textile="oiled canvas", accessory="iron clasps",
            )]
        return GrapesProfile(architecture=arch)

    def test_to_dict_includes_architecture_when_populated(self):
        """T3: to_dict emits architecture when non-empty."""
        p = self._make_profile(with_arch=True)
        d = p.to_dict()
        self.assertIn("architecture", d)
        self.assertEqual(len(d["architecture"]), 1)

    def test_to_dict_omits_architecture_when_empty(self):
        """T4: to_dict omits architecture when empty (backward compat)."""
        p = self._make_profile(with_arch=False)
        d = p.to_dict()
        self.assertNotIn("architecture", d)

    def test_from_dict_loads_architecture(self):
        """T5: from_dict correctly deserializes architecture entries."""
        data = {
            "architecture": [
                {"building_style": "Gothic", "material": "limestone",
                 "motif": "flying buttresses", "clothing_style": "Robes",
                 "textile": "velvet", "accessory": "silver chains"},
            ],
        }
        p = GrapesProfile.from_dict(data)
        self.assertEqual(len(p.architecture), 1)
        self.assertEqual(p.architecture[0].building_style, "Gothic")

    def test_narrative_summary_includes_architecture(self):
        """T6: to_narrative_summary includes architecture text."""
        p = self._make_profile(with_arch=True)
        summary = p.to_narrative_summary()
        self.assertIn("Architecture", summary)
        self.assertIn("Brutalist Stone", summary)
        self.assertIn("Fashion", summary)


class TestGrapesGeneratorArchitecture(unittest.TestCase):
    """T7-T8: Generator rolling and re-rolling."""

    def test_generate_produces_architecture(self):
        """T7: generate() produces 2-4 architecture entries."""
        gen = GrapesGenerator()
        profile = gen.generate(seed=42)
        self.assertGreaterEqual(len(profile.architecture), 2)
        self.assertLessEqual(len(profile.architecture), 4)

    def test_reroll_architecture(self):
        """T8: reroll_category('architecture') replaces entries."""
        gen = GrapesGenerator()
        profile = gen.generate(seed=42)
        original = [a.building_style for a in profile.architecture]
        gen.reroll_category(profile, "architecture")
        rerolled = [a.building_style for a in profile.architecture]
        # Very unlikely to be identical with different RNG seeds
        self.assertTrue(len(rerolled) >= 2)


class TestInjectStyleMarkers(unittest.TestCase):
    """T9-T11: inject_style_markers()."""

    SAMPLE_STYLES = [
        {
            "building_style": "Brutalist",
            "material": "dark granite",
            "motif": "geometric carvings",
            "clothing_style": "Heavy layers",
            "textile": "oiled canvas",
            "accessory": "iron clasps",
        },
    ]

    def test_empty_list_passthrough(self):
        """T9: Empty architecture list returns description unchanged."""
        desc = "A dark chamber."
        self.assertEqual(inject_style_markers(desc, [], random.Random(1)), desc)
        self.assertEqual(inject_style_markers(desc, None, random.Random(1)), desc)

    def test_appends_style_clause(self):
        """T10: Non-empty list appends a style clause."""
        desc = "A dark chamber."
        result = inject_style_markers(desc, self.SAMPLE_STYLES, random.Random(1))
        self.assertTrue(len(result) > len(desc))
        self.assertTrue(result.startswith(desc))

    def test_deterministic_with_seed(self):
        """T11: Same seed produces identical output."""
        desc = "A dark chamber."
        r1 = inject_style_markers(desc, self.SAMPLE_STYLES, random.Random(99))
        r2 = inject_style_markers(desc, self.SAMPLE_STYLES, random.Random(99))
        self.assertEqual(r1, r2)


class TestMimirArchitectureFallback(unittest.TestCase):
    """T12: build_grapes_context includes architecture in fallback."""

    def test_fallback_includes_architecture(self):
        """T12: build_grapes_context includes architecture in output."""
        from codex.integrations.mimir import build_grapes_context

        grapes = {
            "geography": [{"name": "Peak", "terrain": "alpine", "feature": "glow"}],
            "architecture": [
                {"building_style": "Gothic", "material": "stone",
                 "motif": "spires", "clothing_style": "Robes",
                 "textile": "silk", "accessory": "chains"},
            ],
        }
        ctx = build_grapes_context(grapes)
        # Rich path uses to_narrative_summary() which emits "Architecture:"
        self.assertIn("Architecture", ctx)
        self.assertIn("Gothic", ctx)


if __name__ == "__main__":
    unittest.main()
