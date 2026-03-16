"""
codex.core.world.grapes_engine -- Structured G.R.A.P.E.S. World Generator
==========================================================================

Generates rich, multi-entry world profiles using structured templates with
combinatorial name generation, seeded RNG, and faction clock integration.

Replaces the flat single-string-per-category approach in genesis_data.json
with 2-4 structured entries per category drawn from grapes_templates.json.
"""

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Dataclasses -- one per G.R.A.P.E.S. category
# ---------------------------------------------------------------------------

@dataclass
class Landmark:
    """Geography entry."""
    name: str
    terrain: str
    feature: str

    def to_dict(self) -> dict:
        return {"name": self.name, "terrain": self.terrain, "feature": self.feature}

    @classmethod
    def from_dict(cls, data: dict) -> "Landmark":
        return cls(name=data["name"], terrain=data["terrain"], feature=data["feature"])


@dataclass
class Tenet:
    """Religion entry."""
    doctrine: str
    ritual: str
    heresy: str

    def to_dict(self) -> dict:
        return {"doctrine": self.doctrine, "ritual": self.ritual, "heresy": self.heresy}

    @classmethod
    def from_dict(cls, data: dict) -> "Tenet":
        return cls(doctrine=data["doctrine"], ritual=data["ritual"], heresy=data["heresy"])


@dataclass
class Aesthetic:
    """Arts entry (replaces 'Achievements')."""
    style: str
    art_form: str
    cultural_mark: str

    def to_dict(self) -> dict:
        return {"style": self.style, "art_form": self.art_form, "cultural_mark": self.cultural_mark}

    @classmethod
    def from_dict(cls, data: dict) -> "Aesthetic":
        return cls(style=data["style"], art_form=data["art_form"], cultural_mark=data["cultural_mark"])


@dataclass
class PoliticalFaction:
    """Politics entry."""
    name: str
    agenda: str
    clock_name: str
    clock_segments: int

    def to_dict(self) -> dict:
        return {
            "name": self.name, "agenda": self.agenda,
            "clock_name": self.clock_name, "clock_segments": self.clock_segments,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PoliticalFaction":
        return cls(
            name=data["name"], agenda=data["agenda"],
            clock_name=data["clock_name"], clock_segments=data["clock_segments"],
        )


@dataclass
class ScarcityEntry:
    """Economics entry."""
    resource: str
    abundance: str
    trade_note: str

    def to_dict(self) -> dict:
        return {"resource": self.resource, "abundance": self.abundance, "trade_note": self.trade_note}

    @classmethod
    def from_dict(cls, data: dict) -> "ScarcityEntry":
        return cls(resource=data["resource"], abundance=data["abundance"], trade_note=data["trade_note"])


@dataclass
class Taboo:
    """Social entry."""
    prohibition: str
    punishment: str
    origin: str

    def to_dict(self) -> dict:
        return {"prohibition": self.prohibition, "punishment": self.punishment, "origin": self.origin}

    @classmethod
    def from_dict(cls, data: dict) -> "Taboo":
        return cls(prohibition=data["prohibition"], punishment=data["punishment"], origin=data["origin"])


@dataclass
class LanguageProfile:
    """Language entry -- phoneme-based procedural name generation."""
    name: str
    phoneme_type: str
    vowels: List[str] = field(default_factory=list)
    consonants: List[str] = field(default_factory=list)
    syllable_patterns: List[str] = field(default_factory=list)
    naming_rules: str = ""
    suffixes: List[str] = field(default_factory=list)
    titles: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "phoneme_type": self.phoneme_type,
            "vowels": self.vowels, "consonants": self.consonants,
            "syllable_patterns": self.syllable_patterns,
            "naming_rules": self.naming_rules,
            "suffixes": self.suffixes, "titles": self.titles,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LanguageProfile":
        return cls(
            name=data.get("name", ""),
            phoneme_type=data.get("phoneme_type", ""),
            vowels=data.get("vowels", []),
            consonants=data.get("consonants", []),
            syllable_patterns=data.get("syllable_patterns", []),
            naming_rules=data.get("naming_rules", ""),
            suffixes=data.get("suffixes", []),
            titles=data.get("titles", []),
        )


@dataclass
class CulturalValue:
    """Culture entry -- positive value systems that drive NPC motivation."""
    tenet: str
    expression: str
    consequence: str

    def to_dict(self) -> dict:
        return {"tenet": self.tenet, "expression": self.expression, "consequence": self.consequence}

    @classmethod
    def from_dict(cls, data: dict) -> "CulturalValue":
        return cls(tenet=data["tenet"], expression=data["expression"], consequence=data["consequence"])


@dataclass
class AestheticProfile:
    """Architecture & Clothing entry -- procedural visual identity."""
    building_style: str = ""
    material: str = ""
    motif: str = ""
    clothing_style: str = ""
    textile: str = ""
    accessory: str = ""

    def to_dict(self) -> dict:
        return {
            "building_style": self.building_style, "material": self.material,
            "motif": self.motif, "clothing_style": self.clothing_style,
            "textile": self.textile, "accessory": self.accessory,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AestheticProfile":
        return cls(
            building_style=data.get("building_style", ""),
            material=data.get("material", ""),
            motif=data.get("motif", ""),
            clothing_style=data.get("clothing_style", ""),
            textile=data.get("textile", ""),
            accessory=data.get("accessory", ""),
        )


# ---------------------------------------------------------------------------
# Name generation from LanguageProfile
# ---------------------------------------------------------------------------

def generate_name(
    profile: LanguageProfile,
    rng: random.Random,
    syllable_count: int = 0,
) -> str:
    """Generate a single name from a LanguageProfile.

    Builds syllables from ``syllable_patterns`` (C=consonant, V=vowel).
    30% chance to append a suffix from the profile.
    Returns a capitalized, pronounceable name.
    """
    if not profile.vowels or not profile.consonants or not profile.syllable_patterns:
        return ""

    if syllable_count <= 0:
        syllable_count = rng.randint(2, 3)

    parts: List[str] = []
    for _ in range(syllable_count):
        pattern = rng.choice(profile.syllable_patterns)
        syllable = ""
        for ch in pattern.upper():
            if ch == "C":
                syllable += rng.choice(profile.consonants)
            elif ch == "V":
                syllable += rng.choice(profile.vowels)
            else:
                syllable += ch
        parts.append(syllable)

    name = "".join(parts)

    # 30% chance to append a suffix
    if profile.suffixes and rng.random() < 0.30:
        name += rng.choice(profile.suffixes)

    return name.capitalize()


def generate_full_name(
    profile: LanguageProfile,
    rng: random.Random,
    include_title: bool = False,
) -> str:
    """Generate a two-part name, optionally with a title prefix.

    Returns ``"Given Family"`` or ``"Title Given Family"``.
    """
    given = generate_name(profile, rng, syllable_count=rng.randint(2, 3))
    family = generate_name(profile, rng, syllable_count=rng.randint(2, 4))

    if not given or not family:
        return given or family or ""

    if include_title and profile.titles:
        title = rng.choice(profile.titles)
        return f"{title} {given} {family}"
    return f"{given} {family}"


# ---------------------------------------------------------------------------
# GrapesProfile -- container for a full world profile
# ---------------------------------------------------------------------------

@dataclass
class GrapesProfile:
    """Container for a complete G.R.A.P.E.S. world profile."""
    geography: List[Landmark] = field(default_factory=list)
    religion: List[Tenet] = field(default_factory=list)
    arts: List[Aesthetic] = field(default_factory=list)
    politics: List[PoliticalFaction] = field(default_factory=list)
    economics: List[ScarcityEntry] = field(default_factory=list)
    social: List[Taboo] = field(default_factory=list)
    language: List[LanguageProfile] = field(default_factory=list)
    culture: List[CulturalValue] = field(default_factory=list)
    architecture: List[AestheticProfile] = field(default_factory=list)
    seed: Optional[int] = None
    universe_id: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "geography": [e.to_dict() for e in self.geography],
            "religion": [e.to_dict() for e in self.religion],
            "arts": [e.to_dict() for e in self.arts],
            "politics": [e.to_dict() for e in self.politics],
            "economics": [e.to_dict() for e in self.economics],
            "social": [e.to_dict() for e in self.social],
            "seed": self.seed,
            "universe_id": self.universe_id,
        }
        # Only emit new keys when populated (backward-compat)
        if self.language:
            d["language"] = [e.to_dict() for e in self.language]
        if self.culture:
            d["culture"] = [e.to_dict() for e in self.culture]
        if self.architecture:
            d["architecture"] = [e.to_dict() for e in self.architecture]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "GrapesProfile":
        return cls(
            geography=[Landmark.from_dict(d) for d in data.get("geography", [])],
            religion=[Tenet.from_dict(d) for d in data.get("religion", [])],
            arts=[Aesthetic.from_dict(d) for d in data.get("arts", [])],
            politics=[PoliticalFaction.from_dict(d) for d in data.get("politics", [])],
            economics=[ScarcityEntry.from_dict(d) for d in data.get("economics", [])],
            social=[Taboo.from_dict(d) for d in data.get("social", [])],
            language=[LanguageProfile.from_dict(d) for d in data.get("language", [])],
            culture=[CulturalValue.from_dict(d) for d in data.get("culture", [])],
            architecture=[AestheticProfile.from_dict(d) for d in data.get("architecture", [])],
            seed=data.get("seed"),
            universe_id=data.get("universe_id"),
        )

    def to_narrative_summary(self) -> str:
        """Produce a concise ~200 token summary for LLM injection."""
        parts = []
        if self.geography:
            terrains = ", ".join(lm.terrain for lm in self.geography[:3])
            parts.append(f"Terrain: {terrains}.")
            parts.append(f"Landmark: {self.geography[0].name} -- {self.geography[0].feature}.")
        if self.religion:
            t = self.religion[0]
            parts.append(f"Faith: {t.doctrine}. Ritual: {t.ritual}. Heresy: {t.heresy}.")
        if self.arts:
            a = self.arts[0]
            parts.append(f"Art: {a.style} ({a.art_form}). Mark: {a.cultural_mark}.")
        if self.politics:
            factions = "; ".join(f"{f.name}: {f.agenda}" for f in self.politics[:2])
            parts.append(f"Factions: {factions}.")
        if self.economics:
            resources = ", ".join(
                f"{e.resource} ({e.abundance})" for e in self.economics[:2]
            )
            parts.append(f"Economy: {resources}.")
        if self.social:
            t = self.social[0]
            parts.append(f"Taboo: {t.prohibition} (punishment: {t.punishment}).")
        if self.language:
            lang = self.language[0]
            parts.append(f"Language: {lang.name} ({lang.phoneme_type}).")
        if self.culture:
            cv = self.culture[0]
            parts.append(f"Cultural Value: {cv.tenet} -- {cv.expression}.")
        if self.architecture:
            ap = self.architecture[0]
            parts.append(
                f"Architecture: {ap.building_style} in {ap.material}, marked by {ap.motif}. "
                f"Fashion: {ap.clothing_style} of {ap.textile}."
            )
        return " ".join(parts)

    def create_faction_clocks(self) -> list:
        """Create UniversalClock instances for each political faction.

        Returns a list of FactionClock instances. Import is guarded so the
        module can be used standalone.
        """
        try:
            from codex.core.mechanics.clock import FactionClock
        except ImportError:
            return []
        clocks = []
        for faction in self.politics:
            clocks.append(FactionClock(
                name=faction.clock_name,
                segments=faction.clock_segments,
            ))
        return clocks

    def to_world_map_locations(self, seed: int, bounds: tuple = (100, 100)) -> list:
        """Convert Geography landmarks to LocationNode dicts for world map creation.

        Each Landmark becomes a location node:
        - location_type inferred from terrain (coastal->city, mountain->ruins, forest->village, etc.)
        - Positions assigned via seeded scatter within bounds
        - First landmark is the starting location

        Returns list of dicts compatible with LocationNode.from_dict().
        """
        if not self.geography:
            return []

        import math
        rng = random.Random(seed)

        # Terrain -> default location type mapping
        TERRAIN_TYPE_MAP = {
            "coastal": "city",
            "forest": "village",
            "mountain": "ruins",
            "plains": "town",
            "desert": "ruins",
            "swamp": "wilderness_poi",
            "urban": "city",
            "tundra": "camp",
            "volcanic": "dungeon_entrance",
            "river": "town",
            "island": "village",
            "underground": "dungeon_entrance",
            "canyon": "wilderness_poi",
            "jungle": "village",
            "savanna": "camp",
        }

        # Location type -> icon mapping
        TERRAIN_ICON = {
            "city": "C", "town": "T", "village": "v", "ruins": "R",
            "dungeon_entrance": "D", "wilderness_poi": "*", "camp": "c",
        }

        locations = []
        positions = []

        for i, landmark in enumerate(self.geography):
            loc_type = TERRAIN_TYPE_MAP.get(landmark.terrain, "wilderness_poi")

            # Scatter positions within bounds with minimum spacing
            attempts = 0
            while attempts < 50:
                x = rng.randint(5, bounds[0] - 5)
                y = rng.randint(5, bounds[1] - 5)
                # Check minimum distance from existing positions
                too_close = False
                for px, py in positions:
                    dist = math.sqrt((x - px) ** 2 + (y - py) ** 2)
                    if dist < bounds[0] // (len(self.geography) + 1):
                        too_close = True
                        break
                if not too_close:
                    break
                attempts += 1

            positions.append((x, y))

            loc_id = landmark.name.lower().replace(" ", "_").replace("'", "")
            locations.append({
                "id": loc_id,
                "display_name": landmark.name,
                "x": x,
                "y": y,
                "location_type": loc_type,
                "terrain": landmark.terrain,
                "feature": landmark.feature,
                "zones": [],
                "connections": [],  # filled below
                "icon": TERRAIN_ICON.get(loc_type, "?"),
                "tier": min(4, 1 + i // 2),  # escalating difficulty
                "is_starting_location": i == 0,
                "services": ["tavern", "market"] if loc_type in ("city", "town") else [],
                "grapes_landmark_index": i,
            })

        # Build connections via nearest-neighbor (1-3 connections per node)
        for i, loc in enumerate(locations):
            if not positions:
                break
            px, py = positions[i]
            # Calculate distances to all other locations
            dists = []
            for j, (ox, oy) in enumerate(positions):
                if i == j:
                    continue
                dist = math.sqrt((px - ox) ** 2 + (py - oy) ** 2)
                dists.append((dist, j))
            dists.sort()

            # Connect to 1-3 nearest neighbors
            num_connections = min(rng.randint(1, 3), len(dists))
            for _, j in dists[:num_connections]:
                other_id = locations[j]["id"]
                if other_id not in loc["connections"]:
                    loc["connections"].append(other_id)
                # Bidirectional
                if loc["id"] not in locations[j]["connections"]:
                    locations[j]["connections"].append(loc["id"])

        return locations


# ---------------------------------------------------------------------------
# GrapesGenerator -- template-driven world generation
# ---------------------------------------------------------------------------

_TEMPLATE_PATH = Path(__file__).parent / "grapes_templates.json"


class GrapesGenerator:
    """Generates GrapesProfile instances from structured templates."""

    def __init__(self, data_path: Optional[Path] = None):
        path = data_path or _TEMPLATE_PATH
        with open(path, "r", encoding="utf-8") as f:
            self._templates = json.load(f)

    # -- public API ---------------------------------------------------------

    def generate(
        self,
        seed: Optional[int] = None,
        universe_id: Optional[str] = None,
    ) -> GrapesProfile:
        """Generate a full GrapesProfile using seeded RNG.

        Picks 2-4 entries per category via combinatorial name generation.
        """
        rng = random.Random(seed)
        count = lambda: rng.randint(2, 4)  # noqa: E731

        profile = GrapesProfile(
            geography=self._roll_geography(rng, count()),
            religion=self._roll_religion(rng, count()),
            arts=self._roll_arts(rng, count()),
            politics=self._roll_politics(rng, count()),
            economics=self._roll_economics(rng, count()),
            social=self._roll_social(rng, count()),
            language=self._roll_language(rng, rng.randint(1, 2)),
            culture=self._roll_culture(rng, count()),
            architecture=self._roll_architecture(rng, count()),
            seed=seed,
            universe_id=universe_id,
        )
        return profile

    def reroll_category(
        self,
        profile: GrapesProfile,
        category: str,
    ) -> GrapesProfile:
        """Re-roll a single category within an existing profile."""
        rng = random.Random()
        n = rng.randint(2, 4)
        rollers = {
            "geography": lambda: self._roll_geography(rng, n),
            "religion": lambda: self._roll_religion(rng, n),
            "arts": lambda: self._roll_arts(rng, n),
            "politics": lambda: self._roll_politics(rng, n),
            "economics": lambda: self._roll_economics(rng, n),
            "social": lambda: self._roll_social(rng, n),
            "language": lambda: self._roll_language(rng, rng.randint(1, 2)),
            "culture": lambda: self._roll_culture(rng, n),
            "architecture": lambda: self._roll_architecture(rng, n),
        }
        roller = rollers.get(category)
        if roller:
            setattr(profile, category, roller())
        return profile

    # -- private rollers ----------------------------------------------------

    def _join_name(self, parts: List[str], rng: random.Random) -> str:
        """Join name_parts list into a single string."""
        return " ".join(parts)

    def _roll_geography(self, rng: random.Random, n: int) -> List[Landmark]:
        pool = self._templates.get("geography", {}).get("landmarks", [])
        if not pool:
            return []
        picks = rng.sample(pool, min(n, len(pool)))
        return [
            Landmark(
                name=self._join_name(p["name_parts"], rng),
                terrain=p["terrain"],
                feature=p["feature"],
            )
            for p in picks
        ]

    def _roll_religion(self, rng: random.Random, n: int) -> List[Tenet]:
        pool = self._templates.get("religion", {}).get("tenets", [])
        if not pool:
            return []
        picks = rng.sample(pool, min(n, len(pool)))
        return [
            Tenet(doctrine=p["doctrine"], ritual=p["ritual"], heresy=p["heresy"])
            for p in picks
        ]

    def _roll_arts(self, rng: random.Random, n: int) -> List[Aesthetic]:
        pool = self._templates.get("arts", {}).get("aesthetics", [])
        if not pool:
            return []
        picks = rng.sample(pool, min(n, len(pool)))
        return [
            Aesthetic(style=p["style"], art_form=p["art_form"], cultural_mark=p["cultural_mark"])
            for p in picks
        ]

    def _roll_politics(self, rng: random.Random, n: int) -> List[PoliticalFaction]:
        pool = self._templates.get("politics", {}).get("factions", [])
        if not pool:
            return []
        picks = rng.sample(pool, min(n, len(pool)))
        return [
            PoliticalFaction(
                name=self._join_name(p["name_parts"], rng),
                agenda=p["agenda"],
                clock_name=self._join_name(p["name_parts"], rng),
                clock_segments=p["clock_segments"],
            )
            for p in picks
        ]

    def _roll_economics(self, rng: random.Random, n: int) -> List[ScarcityEntry]:
        pool = self._templates.get("economics", {}).get("resources", [])
        if not pool:
            return []
        picks = rng.sample(pool, min(n, len(pool)))
        return [
            ScarcityEntry(
                resource=p["resource"],
                abundance=rng.choice(p["abundance_pool"]),
                trade_note=rng.choice(p["trade_note_pool"]),
            )
            for p in picks
        ]

    def _roll_social(self, rng: random.Random, n: int) -> List[Taboo]:
        pool = self._templates.get("social", {}).get("taboos", [])
        if not pool:
            return []
        picks = rng.sample(pool, min(n, len(pool)))
        return [
            Taboo(prohibition=p["prohibition"], punishment=p["punishment"], origin=p["origin"])
            for p in picks
        ]

    def _roll_language(self, rng: random.Random, n: int) -> List[LanguageProfile]:
        pool = self._templates.get("language", {}).get("profiles", [])
        if not pool:
            return []
        picks = rng.sample(pool, min(n, len(pool)))
        return [
            LanguageProfile(
                name=self._join_name(p.get("name_parts", [p.get("name", "?")]), rng),
                phoneme_type=p.get("phoneme_type", ""),
                vowels=p.get("vowels", []),
                consonants=p.get("consonants", []),
                syllable_patterns=p.get("syllable_patterns", []),
                naming_rules=p.get("naming_rules", ""),
                suffixes=p.get("suffixes", []),
                titles=p.get("titles", []),
            )
            for p in picks
        ]

    def _roll_culture(self, rng: random.Random, n: int) -> List[CulturalValue]:
        pool = self._templates.get("culture", {}).get("values", [])
        if not pool:
            return []
        picks = rng.sample(pool, min(n, len(pool)))
        return [
            CulturalValue(tenet=p["tenet"], expression=p["expression"], consequence=p["consequence"])
            for p in picks
        ]

    def _roll_architecture(self, rng: random.Random, n: int) -> List[AestheticProfile]:
        pool = self._templates.get("architecture", {}).get("styles", [])
        if not pool:
            return []
        picks = rng.sample(pool, min(n, len(pool)))
        return [
            AestheticProfile(
                building_style=p.get("building_style", ""),
                material=p.get("material", ""),
                motif=p.get("motif", ""),
                clothing_style=p.get("clothing_style", ""),
                textile=p.get("textile", ""),
                accessory=p.get("accessory", ""),
            )
            for p in picks
        ]
