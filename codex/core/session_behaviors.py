"""
codex.core.session_behaviors — Per-System Session Type Behaviors (WO-V62.0 Track D)
====================================================================================

Defines how each game system behaves under different session types:
one_shot, expedition, campaign, freeform.

FITD one-shots follow the CBR+PNK model: single score, no downtime, in media res.
Crown supports multi-arc campaigns and freeform court exploration.
Spatial systems get expedition timers with narrative supply pressure.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# =========================================================================
# Session Type Labels (system-aware menu text)
# =========================================================================

SESSION_TYPE_LABELS: Dict[str, Dict[str, Tuple[str, str]]] = {
    # system_id -> session_type -> (label, description)
    "burnwillow": {
        "one_shot": ("Quick Delve", "A single dungeon run. No strings attached."),
        "expedition": ("Expedition", "Explore, fight, return. Your progress matters."),
        "campaign": ("Campaign", "A continuing story across multiple sessions."),
        "freeform": ("Freeform", "The world responds to you. No fixed ending."),
    },
    "dnd5e": {
        "one_shot": ("One-Shot", "A single adventure module."),
        "expedition": ("Expedition", "Delve deep. Supplies are limited."),
        "campaign": ("Campaign", "Chapter by chapter, the story unfolds."),
        "freeform": ("Freeform", "The Realms are yours to explore."),
    },
    "stc": {
        "one_shot": ("One-Shot", "A single Cosmere encounter."),
        "expedition": ("Expedition", "Invest Stormlight wisely."),
        "campaign": ("Campaign", "Walk the path of Radiance."),
        "freeform": ("Freeform", "The Cosmere beckons."),
    },
    "bitd": {
        "one_shot": ("The Score", "One job. Get in. Get out."),
        "expedition": ("Score + Downtime", "The job and its aftermath."),
        "campaign": ("Crew Campaign", "Score after score. The faction map turns."),
        "freeform": ("Free Play", "Choose your scores. Shape the city."),
    },
    "sav": {
        "one_shot": ("The Job", "One job. One ship. One chance."),
        "expedition": ("Job + Downtime", "The job and repairs after."),
        "campaign": ("Crew Campaign", "Chart your course through the stars."),
        "freeform": ("Free Play", "The sector is yours."),
    },
    "bob": {
        "one_shot": ("The Mission", "One mission. One squad. No retreat."),
        "expedition": ("Mission + Camp", "The mission and its aftermath."),
        "campaign": ("Legion Campaign", "The war grinds on. Push the line."),
        "freeform": ("Free Play", "Command as you see fit."),
    },
    "cbrpnk": {
        "one_shot": ("The Run", "Hack in. Grab the data. Get out alive."),
        "expedition": ("Run + Cooldown", "The run and recovery after."),
        "campaign": ("Grid Campaign", "ICE escalates. The net remembers."),
        "freeform": ("Free Play", "The grid is your playground."),
    },
    "candela": {
        "one_shot": ("The Assignment", "One mystery. One circle. One night."),
        "expedition": ("Assignment + Study", "The case and research after."),
        "campaign": ("Circle Campaign", "The Bleed spreads. Assignments chain."),
        "freeform": ("Open Investigation", "Follow the Bleed where it leads."),
    },
    "crown": {
        "one_shot": ("The Arc", "Seven days. One choice. Crown or Crew."),
        "expedition": ("Extended Arc", "Take your time with the court."),
        "campaign": ("Multi-Arc", "The court remembers you between arcs."),
        "freeform": ("Open Court", "No deadline. The court is your stage."),
    },
}

# Default labels for unknown systems
_DEFAULT_LABELS: Dict[str, Tuple[str, str]] = {
    "one_shot": ("Quick Play", "A single self-contained session."),
    "expedition": ("Expedition", "Extended play with resource pressure."),
    "campaign": ("Campaign", "A continuing story across sessions."),
    "freeform": ("Freeform", "Open-ended exploration."),
}


def get_session_labels(system_id: str) -> Dict[str, Tuple[str, str]]:
    """Get session type labels for a system.

    Args:
        system_id: The game system identifier (e.g. "bitd", "burnwillow").

    Returns:
        Dict mapping session_type -> (label, description). Falls back to
        generic labels for unrecognised system IDs.
    """
    return SESSION_TYPE_LABELS.get(system_id, _DEFAULT_LABELS)


# =========================================================================
# FITD One-Shot Behaviors (CBR+PNK Model)
# =========================================================================

@dataclass
class FITDOneShot:
    """Configuration for FITD one-shot sessions.

    Follows the CBR+PNK model:
    1. Character generation (fast, template-driven)
    2. Briefing (one objective, clear stakes)
    3. The Run/Score (linear scenes, no downtime)
    4. Resolution (success or failure, story ends)

    Attributes:
        system_id: The FITD system this config applies to.
        skip_engagement_roll: If True, skip the pre-score engagement roll.
        skip_downtime: If True, omit the downtime phase entirely.
        skip_free_play: If True, omit free-play scene selection.
        start_in_media_res: If True, drop players into the action immediately.
        score_type: System-specific name for the primary action unit
                    (score, job, mission, run, assignment).
    """
    system_id: str
    skip_engagement_roll: bool = True
    skip_downtime: bool = True
    skip_free_play: bool = True
    start_in_media_res: bool = True
    score_type: str = ""

    @classmethod
    def for_system(cls, system_id: str) -> "FITDOneShot":
        """Create system-appropriate one-shot config.

        Args:
            system_id: The FITD system identifier.

        Returns:
            A fully-populated FITDOneShot for known systems, or a generic
            one with score_type="score" for unknown systems.
        """
        configs = {
            "bitd": cls(system_id="bitd", score_type="score"),
            "sav": cls(system_id="sav", score_type="job"),
            "bob": cls(system_id="bob", score_type="mission"),
            "cbrpnk": cls(system_id="cbrpnk", score_type="run"),
            "candela": cls(system_id="candela", score_type="assignment"),
        }
        return configs.get(system_id, cls(system_id=system_id, score_type="score"))


# System-specific briefing templates for one-shots.
# Placeholders: {target}, {payload}, {location}
FITD_BRIEFING_TEMPLATES: Dict[str, List[str]] = {
    "bitd": [
        "Word on the street: {target} is moving {payload} through {location} tonight. Your crew has one shot.",
        "The Bluecoats are distracted. {location} is unguarded for the next three bells. Make it count.",
        "A rival gang crossed you last week. Tonight, you hit {target}'s {location}. Send a message.",
    ],
    "sav": [
        "The job's simple: pick up {payload} from {location}. The catch? {target} wants it too.",
        "Your ship's fuel is running low. {location} has what you need — if you can get past {target}.",
        "A contact on {location} needs extraction. {target}'s blockade says otherwise.",
    ],
    "bob": [
        "Command says take {location}. Intel says {target} has it fortified. Your squad says nothing.",
        "The Broken are advancing on {location}. Hold the line until dawn. No reinforcements.",
        "Recon mission: confirm {target} presence at {location}. Do not engage. (You will engage.)",
    ],
    "cbrpnk": [
        "The data is on a server inside {location}. {target}'s ICE is legendary. Jack in. Grab it. Bounce.",
        "A corpo whistleblower needs their files extracted from {location} before {target} kills them.",
        "The net says {location} has a back door. {target}'s netrunners say otherwise. Prove them wrong.",
    ],
    "candela": [
        "A member of the Fourth Pharos was found dead in {location}. The Bleed marks on the walls suggest {target}.",
        "Strange phenomena at {location}. Witnesses describe {target}. Your circle draws the assignment.",
        "The Wick has gone dark in {location}. Last report mentioned {target}. Investigate. Survive.",
    ],
}


def generate_one_shot_briefing(system_id: str, seed: int = 0) -> str:
    """Generate a one-shot briefing for a FITD system.

    Uses a seeded RNG for deterministic output. Fills placeholders with
    generic targets/payloads/locations from internal word lists.

    Args:
        system_id: The FITD system identifier (e.g. "bitd", "cbrpnk").
        seed: RNG seed for reproducible output.

    Returns:
        A briefing string with all placeholders filled in.
    """
    import random
    rng = random.Random(seed)

    templates = FITD_BRIEFING_TEMPLATES.get(system_id, [])
    if not templates:
        return "Your mission is clear. Move fast. Trust no one."

    template = rng.choice(templates)

    targets = ["the Syndicate", "the Hive", "an unknown faction", "corporate security", "the Watch"]
    payloads = ["a sealed case", "stolen documents", "medical supplies", "a prototype", "the evidence"]
    locations = ["the docks", "the old district", "the upper ward", "the underground", "the tower"]

    return template.format(
        target=rng.choice(targets),
        payload=rng.choice(payloads),
        location=rng.choice(locations),
    )


# =========================================================================
# Crown Extended Modes
# =========================================================================

@dataclass
class CrownSessionConfig:
    """Configuration for Crown session types.

    Crown is a court-intrigue game built around a 7-day arc. This config
    governs how many days the arc runs, how days advance, and which NPC
    relationships persist between arcs (campaign mode).

    Attributes:
        session_type: One of "one_shot", "expedition", "campaign", "freeform".
        max_days: Day limit for the arc. None means no limit (freeform).
        day_advance_mode: "auto" advances days on narrative triggers;
                          "manual" requires explicit player input.
        arc_number: Campaign arc counter (starts at 1, increments per arc).
        persistent_npcs: Mapping of NPC name -> relationship score (-1.0..1.0)
                         that carries forward between campaign arcs.
    """
    session_type: str = "one_shot"
    max_days: Optional[int] = 7
    day_advance_mode: str = "auto"
    arc_number: int = 1
    persistent_npcs: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def for_session_type(cls, session_type: str,
                         save_data: Optional[dict] = None) -> "CrownSessionConfig":
        """Create Crown config for a session type.

        For campaign and freeform types, prior save_data is used to restore
        persistent NPC relationships and the arc counter.

        Args:
            session_type: One of "one_shot", "expedition", "campaign", "freeform".
            save_data: Optional dict from a prior arc's to_dict() to restore
                       cross-arc state.

        Returns:
            A fully-populated CrownSessionConfig.
        """
        save_data = save_data or {}
        if session_type == "one_shot":
            return cls(session_type="one_shot", max_days=7, day_advance_mode="auto")
        elif session_type == "expedition":
            return cls(session_type="expedition", max_days=10, day_advance_mode="auto")
        elif session_type == "campaign":
            return cls(
                session_type="campaign",
                max_days=7,
                day_advance_mode="auto",
                arc_number=save_data.get("arc_number", 1),
                persistent_npcs=save_data.get("persistent_npcs", {}),
            )
        elif session_type == "freeform":
            return cls(
                session_type="freeform",
                max_days=None,
                day_advance_mode="manual",
                persistent_npcs=save_data.get("persistent_npcs", {}),
            )
        # Unknown session type — sensible defaults
        return cls(session_type=session_type)

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict.

        Returns:
            Dict with all config fields, safe for JSON serialisation.
        """
        return {
            "session_type": self.session_type,
            "max_days": self.max_days,
            "day_advance_mode": self.day_advance_mode,
            "arc_number": self.arc_number,
            "persistent_npcs": dict(self.persistent_npcs),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CrownSessionConfig":
        """Deserialize from a dict (as produced by to_dict).

        Args:
            data: Dict previously returned by to_dict().

        Returns:
            Restored CrownSessionConfig instance.
        """
        return cls(
            session_type=data.get("session_type", "one_shot"),
            max_days=data.get("max_days", 7),
            day_advance_mode=data.get("day_advance_mode", "auto"),
            arc_number=data.get("arc_number", 1),
            persistent_npcs=data.get("persistent_npcs", {}),
        )


# =========================================================================
# Session Behavior Queries
# =========================================================================

# Session types that persist world state between sessions
PERSISTS_WORLD: frozenset = frozenset({"expedition", "campaign", "freeform"})

# Session types that advance CivicPulse at session end
ADVANCES_CIVIC: frozenset = frozenset({"expedition", "campaign", "freeform"})

# Number of CivicPulse ticks emitted per session type
CIVIC_TICKS: Dict[str, int] = {
    "expedition": 2,
    "campaign": 1,
    "freeform": 1,
}

# Session types that apply momentum decay at session end
DECAYS_MOMENTUM: frozenset = frozenset({"expedition", "campaign", "freeform"})

# Systems that use FITD (Forged in the Dark) mechanics
FITD_SYSTEMS: frozenset = frozenset({"bitd", "sav", "bob", "cbrpnk", "candela"})

# Systems that use spatial dungeon mechanics
SPATIAL_SYSTEMS: frozenset = frozenset({"burnwillow", "dnd5e", "stc"})

# Default expedition turn budgets per spatial system
EXPEDITION_BUDGETS: Dict[str, int] = {
    "burnwillow": 50,
    "dnd5e": 60,
    "stc": 55,
}


def should_persist_world(session_type: str) -> bool:
    """Check if this session type persists world state.

    Args:
        session_type: One of "one_shot", "expedition", "campaign", "freeform".

    Returns:
        True if the session type carries world state forward.
    """
    return session_type in PERSISTS_WORLD


def should_advance_civic(session_type: str) -> bool:
    """Check if this session type advances CivicPulse at session end.

    Args:
        session_type: One of "one_shot", "expedition", "campaign", "freeform".

    Returns:
        True if CivicPulse should tick at the end of this session type.
    """
    return session_type in ADVANCES_CIVIC


def get_civic_ticks(session_type: str) -> int:
    """Get the number of CivicPulse ticks for a session type.

    Args:
        session_type: One of "one_shot", "expedition", "campaign", "freeform".

    Returns:
        Number of ticks (0 for one_shot and unknown types).
    """
    return CIVIC_TICKS.get(session_type, 0)


def is_fitd_system(system_id: str) -> bool:
    """Check if a system uses FITD (Forged in the Dark) mechanics.

    Args:
        system_id: The game system identifier.

    Returns:
        True for bitd, sav, bob, cbrpnk, candela.
    """
    return system_id in FITD_SYSTEMS


def is_spatial_system(system_id: str) -> bool:
    """Check if a system uses spatial dungeon mechanics.

    Args:
        system_id: The game system identifier.

    Returns:
        True for burnwillow, dnd5e, stc.
    """
    return system_id in SPATIAL_SYSTEMS


def get_expedition_budget(system_id: str) -> int:
    """Get the default expedition turn budget for a spatial system.

    Args:
        system_id: The game system identifier.

    Returns:
        Turn budget integer. Returns 50 for unknown systems.
    """
    return EXPEDITION_BUDGETS.get(system_id, 50)


def should_offer_character_export(session_type: str) -> bool:
    """Check if this session type should offer character export at close.

    One-shot sessions offer export so players can carry their characters
    into a new one-shot or campaign.

    Args:
        session_type: One of "one_shot", "expedition", "campaign", "freeform".

    Returns:
        True only for one_shot sessions.
    """
    return session_type == "one_shot"
