"""
codex.games.crown.events
==========================
Event generation subsystem for Crown & Crew.

Provides weighted, sway-sensitive event generation with support for
multi-step event chains that unfold across multiple days.

Classes:
    EventGenerator — Weighted event selection with history, chains, and sway bias

Constants:
    WEIGHTED_EVENT_POOL — 30+ weighted events with sway_bias, tags, day_range
    EVENT_CHAINS        — 6 multi-event story chains
    NPC_EVENTS          — Leader/patron-specific events (keyed by NPC name)
"""

import random
from typing import Any, Dict, List, Optional


# =============================================================================
# WEIGHTED EVENT POOL
# =============================================================================
# Each event: text, sway_bias (crown/crew/neutral), tag, weight, day_range
#   sway_bias: Crown-leaning events score higher when sway < 0, and vice versa.
#   day_range: [min_day, max_day] — None means any day.
#   weight: Base probability weight (higher = more common).
#   chain_id: If present, this event can start a chain.
#   event_id: Unique identifier for chain targeting.

WEIGHTED_EVENT_POOL: List[Dict[str, Any]] = [
    # ─── CROWN-LEANING EVENTS (bias: "crown") ────────────────────────────
    {
        "event_id": "informant_offer",
        "text": (
            "A hooded figure slips a coin under your door. One side is stamped with "
            "the Crown seal. The message reads: 'Name three Crew safehouses. You'll "
            "never see a warrant again.'"
        ),
        "sway_bias": "crown", "tag": "GUILE",
        "weight": 4, "day_range": [2, None], "chain_id": "informant_trap",
    },
    {
        "event_id": "arrest_threat",
        "text": (
            "Crown soldiers are checking papers at the east gate. Someone has posted "
            "your general description. The sketch is poor — but your scar is accurate."
        ),
        "sway_bias": "crown", "tag": "SILENCE",
        "weight": 5, "day_range": [1, None],
    },
    {
        "event_id": "pardon_offer",
        "text": (
            "A Crown herald reads a public pardon in the square — conditional, "
            "narrow, but real. It includes language that might apply to someone "
            "with your record, if read carefully."
        ),
        "sway_bias": "crown", "tag": "GUILE",
        "weight": 3, "day_range": [3, None],
    },
    {
        "event_id": "patrol_warning",
        "text": (
            "A Crown patrol has doubled its rounds through the Outer Wards. "
            "Three Crew sympathizers have been questioned. None have talked yet. "
            "'Yet' is the operative word."
        ),
        "sway_bias": "crown", "tag": "SILENCE",
        "weight": 5, "day_range": [1, None],
    },
    {
        "event_id": "crown_aid_offer",
        "text": (
            "The Governor's secretary approaches you privately. Her employer wants "
            "one problem solved quietly, off the books. In exchange: resources, "
            "and three days of looking the other way."
        ),
        "sway_bias": "crown", "tag": "GUILE",
        "weight": 3, "day_range": [2, None], "chain_id": "governor_deal",
    },
    {
        "event_id": "spy_exposed",
        "text": (
            "A Crown spy has been watching the Crew's eastern safehouse for a week. "
            "The Defector found him this morning. The spy is unarmed. He's seventeen years old."
        ),
        "sway_bias": "crown", "tag": "BLOOD",
        "weight": 3, "day_range": [2, None],
    },
    {
        "event_id": "trial_rumor",
        "text": (
            "Word reaches you through back channels: the Justiciar is preparing "
            "charges. Not against you — against someone you care about. "
            "The evidence is circumstantial. It won't matter."
        ),
        "sway_bias": "crown", "tag": "BLOOD",
        "weight": 3, "day_range": [3, None], "chain_id": "succession_plot",
    },
    {
        "event_id": "marshal_advance",
        "text": (
            "The Iron Marshal has moved two regiments into the city. No explanation. "
            "The Merchant Guild has quietly begun moving inventory out of the "
            "Market Quarter."
        ),
        "sway_bias": "crown", "tag": "BLOOD",
        "weight": 4, "day_range": [2, None],
    },
    # ─── CREW-LEANING EVENTS (bias: "crew") ──────────────────────────────
    {
        "event_id": "crew_rescue",
        "text": (
            "Three Crew members were taken in last night's sweep. They're being held "
            "at the Watch Station in the Docklands — understaffed on Tuesdays. "
            "Kell has a plan. It's not a good plan."
        ),
        "sway_bias": "crew", "tag": "HEARTH",
        "weight": 5, "day_range": [1, None],
    },
    {
        "event_id": "deserter_joins",
        "text": (
            "A Crown soldier — young, clearly exhausted — has been sitting outside "
            "the safehouse door for three hours. She hasn't knocked. She's waiting "
            "to be noticed."
        ),
        "sway_bias": "crew", "tag": "HEARTH",
        "weight": 4, "day_range": [1, None],
    },
    {
        "event_id": "rally_point",
        "text": (
            "Word has spread through the Outer Wards. People are gathering at the "
            "old mill, uninvited. They've brought food, and questions, and a lot "
            "of quiet, desperate hope."
        ),
        "sway_bias": "crew", "tag": "DEFIANCE",
        "weight": 4, "day_range": [2, None],
    },
    {
        "event_id": "intelligence_windfall",
        "text": (
            "The Defector drops a sealed packet on your table. Crown supply routes, "
            "three weeks of patrol schedules, and a map of the High Inquisitor's "
            "private correspondence archive. No explanation of how he got it."
        ),
        "sway_bias": "crew", "tag": "GUILE",
        "weight": 3, "day_range": [2, None],
    },
    {
        "event_id": "union_action",
        "text": (
            "The dock workers have stopped unloading Crown shipments. "
            "No official strike call, no pamphlets — just two hundred people "
            "standing with their arms folded. The Faceless is smiling."
        ),
        "sway_bias": "crew", "tag": "DEFIANCE",
        "weight": 4, "day_range": [1, None], "chain_id": "merchant_crisis",
    },
    {
        "event_id": "temple_aid",
        "text": (
            "The High Priestess has left a supply cache at the edge of your "
            "known territory. Medical supplies, enough dried goods for a week. "
            "No note. No demand. But the Temple seal is on every box."
        ),
        "sway_bias": "crew", "tag": "HEARTH",
        "weight": 3, "day_range": [2, None],
    },
    {
        "event_id": "civilian_protection",
        "text": (
            "A family is sheltering in a building the Crown has marked for "
            "confiscation. They have three hours before the soldiers arrive. "
            "They have nowhere to go. They have a small child."
        ),
        "sway_bias": "crew", "tag": "HEARTH",
        "weight": 5, "day_range": [1, None],
    },
    {
        "event_id": "old_blood_deal",
        "text": (
            "Lady Miren has brokered a meeting with an Old Blood lord who controls "
            "a private road through the garrison district. The price is a favor "
            "to be named later. Miren says it's the best deal available."
        ),
        "sway_bias": "crew", "tag": "GUILE",
        "weight": 3, "day_range": [3, None],
    },
    {
        "event_id": "legend_grows",
        "text": (
            "Someone is telling stories about the Crew in the taverns — embellished, "
            "half-true, but vivid. Three young people have already asked where to find "
            "the Crew's meeting point. The Faceless is taking notes."
        ),
        "sway_bias": "crew", "tag": "DEFIANCE",
        "weight": 3, "day_range": [2, None],
    },
    {
        "event_id": "plague_first_case",
        "text": (
            "A healer in the Outer Wards has sent word: a fever is spreading through "
            "the tenements. She's overwhelmed. The Temple is sending help — "
            "but the Crown has sealed the district to 'contain the risk.'"
        ),
        "sway_bias": "crew", "tag": "HEARTH",
        "weight": 3, "day_range": [2, None], "chain_id": "plague",
    },
    # ─── NEUTRAL EVENTS (bias: "neutral") ────────────────────────────────
    {
        "event_id": "crossroads_choice",
        "text": (
            "The road forks at dawn. The northern path is faster but passes "
            "within sight of the garrison. The southern path is safe but costs "
            "half a day. The Crew is watching to see which way you turn."
        ),
        "sway_bias": "neutral", "tag": "SILENCE",
        "weight": 5, "day_range": [1, None],
    },
    {
        "event_id": "strange_traveler",
        "text": (
            "A traveler catches up to your party at dusk. They haven't asked "
            "who you are or where you're going. They've shared their food "
            "without being asked. They might be innocent. They might not."
        ),
        "sway_bias": "neutral", "tag": "GUILE",
        "weight": 4, "day_range": [1, None],
    },
    {
        "event_id": "weather_crisis",
        "text": (
            "A cold front has turned the roads to mud. Three wagons are stuck "
            "at the ford — one of them belongs to a Crown provisioner, one to "
            "a Crew sympathizer, one to an ordinary family. You can free one."
        ),
        "sway_bias": "neutral", "tag": "HEARTH",
        "weight": 4, "day_range": [1, None],
    },
    {
        "event_id": "old_scar",
        "text": (
            "Someone at the last camp recognized your face from before you "
            "joined the Crew. They haven't said what they remember. "
            "They're watching you sleep."
        ),
        "sway_bias": "neutral", "tag": "BLOOD",
        "weight": 3, "day_range": [2, None],
    },
    {
        "event_id": "astrologer_message",
        "text": (
            "A sealed letter with the Court Astrologer's personal mark arrives "
            "with no courier — left on a windowsill you locked this morning. "
            "The contents are in a cipher neither the Defector nor the Mystic "
            "immediately recognize."
        ),
        "sway_bias": "neutral", "tag": "SILENCE",
        "weight": 2, "day_range": [3, None],
    },
    {
        "event_id": "memory_surface",
        "text": (
            "A detail you filed away weeks ago suddenly matters. You can't explain "
            "why you remember it now, at this moment, walking past this corner. "
            "But you're certain: something here doesn't fit."
        ),
        "sway_bias": "neutral", "tag": "GUILE",
        "weight": 3, "day_range": [2, None],
    },
    {
        "event_id": "resource_find",
        "text": (
            "A hidden cache in the floorboards — left by whoever lived here before. "
            "Food, a little coin, a military-grade lockpick set, and a letter "
            "in code addressed to someone who is almost certainly dead."
        ),
        "sway_bias": "neutral", "tag": "SILENCE",
        "weight": 4, "day_range": [1, None],
    },
    {
        "event_id": "shadow_court_contact",
        "text": (
            "The Shadow Court's representative appears without appointment. "
            "They have information for sale — reliable information, they insist. "
            "The price isn't money. It's a future favor, unspecified."
        ),
        "sway_bias": "neutral", "tag": "GUILE",
        "weight": 3, "day_range": [2, None],
    },
    {
        "event_id": "press_report",
        "text": (
            "A pamphlet is circulating with an account of the Crew's last operation "
            "— accurate enough to be alarming. Someone was watching. "
            "The Reformist press is calling it 'the People's justice.'"
        ),
        "sway_bias": "neutral", "tag": "DEFIANCE",
        "weight": 3, "day_range": [2, None],
    },
    {
        "event_id": "prophecy_fragment",
        "text": (
            "The Mystic wakes the camp at midnight and says one word: 'Tomorrow.' "
            "She won't say anything else. She spends the rest of the night "
            "checking her maps."
        ),
        "sway_bias": "neutral", "tag": "SILENCE",
        "weight": 2, "day_range": [3, None],
    },
    {
        "event_id": "faction_clash",
        "text": (
            "Two factions are fighting in the street below. Not the Crown versus "
            "the Crew — two factions you thought were on the same side. "
            "It's been building for weeks. Someone finally threw a punch."
        ),
        "sway_bias": "neutral", "tag": "BLOOD",
        "weight": 3, "day_range": [2, None],
    },
    {
        "event_id": "dawn_messenger",
        "text": (
            "A breathless rider arrives at first light with a sealed dispatch. "
            "It's addressed to the Crew in general, not to anyone specifically. "
            "The rider is already gone."
        ),
        "sway_bias": "neutral", "tag": "DEFIANCE",
        "weight": 4, "day_range": [1, None],
    },
]


# =============================================================================
# EVENT CHAINS — Multi-Step Story Arcs
# =============================================================================
# Each chain is a list of events in sequence.
# Trigger an event with chain_id to start the chain.
# Call generate_chain_event(trigger_event_id) to advance it.

EVENT_CHAINS: Dict[str, List[Dict[str, Any]]] = {
    "merchant_crisis": [
        {
            "event_id": "merchant_crisis_1",
            "text": (
                "The dock strike has lasted three days. The Merchant Guild is "
                "furious. The Governor is threatening to arrest strike organizers. "
                "The Faceless wants the Crew to escort workers who might be targeted."
            ),
            "sway_bias": "crew", "tag": "DEFIANCE",
        },
        {
            "event_id": "merchant_crisis_2",
            "text": (
                "Crown soldiers have moved into the Docklands. Three arrests. "
                "The strike is cracking. The Merchant Prince has offered to meet "
                "with Crew representatives — privately, in the Harbor Exchange."
            ),
            "sway_bias": "neutral", "tag": "GUILE",
        },
        {
            "event_id": "merchant_crisis_3",
            "text": (
                "The smuggling ring is moving Crown goods through the Shadow Court "
                "while the dock strike holds. Someone is profiting from the chaos. "
                "The trail leads to the Merchant Prince's own warehouse."
            ),
            "sway_bias": "crew", "tag": "GUILE",
        },
        {
            "event_id": "merchant_crisis_4",
            "text": (
                "Resolution: The dock strike ends. The Merchant Prince has quietly "
                "agreed to recognize the guild in exchange for the Crew's silence "
                "about his smuggling operation. The Faceless calls it 'a compromise.' "
                "The way they say it is not a compliment."
            ),
            "sway_bias": "neutral", "tag": "DEFIANCE",
        },
    ],
    "succession_plot": [
        {
            "event_id": "succession_plot_1",
            "text": (
                "Rumors are spreading through the court: one of the King's "
                "advisors is corresponding with a foreign power. The Spymaster "
                "wants the Crew to intercept the next letter. Plausible deniability "
                "is the whole point."
            ),
            "sway_bias": "neutral", "tag": "GUILE",
        },
        {
            "event_id": "succession_plot_2",
            "text": (
                "The intercepted letter is in code, but the Defector has broken "
                "it. The contents are worse than expected: a succession timeline, "
                "a list of targets, and a name — someone inside the Crew's "
                "own network."
            ),
            "sway_bias": "crown", "tag": "SILENCE",
        },
        {
            "event_id": "succession_plot_3",
            "text": (
                "Confrontation. The named contact within the Crew is found. "
                "They claim they were feeding false information — a double agent. "
                "They have documentation. It's either brilliant or elaborately forged."
            ),
            "sway_bias": "crew", "tag": "BLOOD",
        },
        {
            "event_id": "succession_plot_4",
            "text": (
                "The coup attempt happens in the night. It fails — barely. "
                "The aftermath leaves three court positions vacant and the "
                "Spymaster asking the Crew for a very specific favor. "
                "He calls it 'repayment.'"
            ),
            "sway_bias": "neutral", "tag": "BLOOD",
        },
    ],
    "plague": [
        {
            "event_id": "plague_1",
            "text": (
                "The fever has spread to two more blocks. The Temple's healers are "
                "overwhelmed. Crown soldiers are preventing people from leaving "
                "the quarantine zone — but they're also preventing food from "
                "getting in."
            ),
            "sway_bias": "crew", "tag": "HEARTH",
        },
        {
            "event_id": "plague_2",
            "text": (
                "A healer claims to have found a treatment — herbal, uncertain, "
                "but promising. The ingredients are in the Temple's locked "
                "pharmacy, which is currently Crown-controlled as part of "
                "the quarantine."
            ),
            "sway_bias": "neutral", "tag": "BLOOD",
        },
        {
            "event_id": "plague_3",
            "text": (
                "The Crew has the treatment ingredients. Now someone has to "
                "go into the quarantine zone to administer them — and stay "
                "there until the job is done. The healer is asking for volunteers."
            ),
            "sway_bias": "crew", "tag": "HEARTH",
        },
        {
            "event_id": "plague_4",
            "text": (
                "Aftermath: The fever breaks. The quarantine zone is opened. "
                "The High Priestess credits the Temple publicly. The Crew's "
                "role is an open secret. Three people ask you how to contact "
                "the Crew. Word spreads."
            ),
            "sway_bias": "crew", "tag": "HEARTH",
        },
    ],
    "informant_trap": [
        {
            "event_id": "informant_trap_1",
            "text": (
                "The Crown's informant offer turns out to be a test. "
                "The 'agent' was a Crew loyalist checking for traitors. "
                "You've passed — but the fact that you were approached "
                "means someone gave the Crown your name."
            ),
            "sway_bias": "crew", "tag": "GUILE",
        },
        {
            "event_id": "informant_trap_2",
            "text": (
                "The leak has been traced to a crewmate. Not the person "
                "you suspected. The evidence is solid. They haven't "
                "been told you know yet."
            ),
            "sway_bias": "neutral", "tag": "SILENCE",
        },
        {
            "event_id": "informant_trap_3",
            "text": (
                "The crewmate confesses. They were being blackmailed — "
                "Crown holds their family. They passed only minor intelligence. "
                "They're asking for help, and the Crew is waiting to see "
                "what you think should happen."
            ),
            "sway_bias": "crew", "tag": "BLOOD",
        },
    ],
    "governor_deal": [
        {
            "event_id": "governor_deal_1",
            "text": (
                "The Governor's 'quiet problem' turns out to be a rival "
                "who knows about the reconstruction fund skimming. "
                "He wants the evidence destroyed. It would also exonerate "
                "three men currently imprisoned on related charges."
            ),
            "sway_bias": "neutral", "tag": "GUILE",
        },
        {
            "event_id": "governor_deal_2",
            "text": (
                "The evidence archive is in the Governor's own office — "
                "a place the Crew can only reach with official permission "
                "or extraordinary audacity. "
                "The Defector has a third option. He says it's cleaner."
            ),
            "sway_bias": "neutral", "tag": "SILENCE",
        },
        {
            "event_id": "governor_deal_3",
            "text": (
                "The deal is completed. The Governor provides the promised "
                "resources and three days of grace. He also mentions, casually, "
                "that he still has a copy of everything. "
                "'For mutual security,' he says."
            ),
            "sway_bias": "crown", "tag": "GUILE",
        },
    ],
    "temple_crisis": [
        {
            "event_id": "temple_crisis_1",
            "text": (
                "The High Inquisitor has moved to audit the Temple's finances — "
                "a transparent attempt to destabilize the High Priestess before "
                "the Concordat vote. She's asking the Crew to find "
                "the Inquisitor's own financial irregularities first."
            ),
            "sway_bias": "crew", "tag": "GUILE",
        },
        {
            "event_id": "temple_crisis_2",
            "text": (
                "The audit has uncovered genuine Temple irregularities — "
                "not corruption, but years of quietly feeding people "
                "off the official books. Technically illegal. "
                "The Inquisitor wants to make an example."
            ),
            "sway_bias": "neutral", "tag": "HEARTH",
        },
        {
            "event_id": "temple_crisis_3",
            "text": (
                "The Concordat vote happens under crisis conditions. "
                "The High Priestess needs the Crew's evidence against "
                "the Inquisitor delivered to the Justiciar before "
                "the morning session. The window is three hours."
            ),
            "sway_bias": "crew", "tag": "DEFIANCE",
        },
    ],
}


# =============================================================================
# NPC EVENTS — Events Specific to Named Leaders and Patrons
# =============================================================================

NPC_EVENTS: Dict[str, List[Dict[str, Any]]] = {
    "Captain Vane": [
        {
            "event_id": "vane_past",
            "text": (
                "Vane has gone quiet for the past two days. "
                "You find him staring at a naval chart with a location "
                "circled in red ink. The circle is around a graveyard."
            ),
            "sway_bias": "crew", "tag": "HEARTH",
            "weight": 3,
        },
    ],
    "The Mystic": [
        {
            "event_id": "mystic_vision",
            "text": (
                "The Mystic has been awake for three days, and she's "
                "been writing. Pages and pages of something. "
                "When you look over her shoulder, you recognize your name."
            ),
            "sway_bias": "crew", "tag": "SILENCE",
            "weight": 2,
        },
    ],
    "The High Inquisitor": [
        {
            "event_id": "inquisitor_ultimatum",
            "text": (
                "A public proclamation arrives with the Inquisitor's seal: "
                "surrender within seventy-two hours, or face collective "
                "punishment. He lists eight names. Yours is third."
            ),
            "sway_bias": "crown", "tag": "BLOOD",
            "weight": 3,
        },
    ],
    "The Spymaster": [
        {
            "event_id": "spymaster_gift",
            "text": (
                "A package arrives with no sender, containing exactly "
                "the documentation you needed for tomorrow's operation. "
                "Someone has been one step ahead of you for a long time."
            ),
            "sway_bias": "neutral", "tag": "GUILE",
            "weight": 2,
        },
    ],
}


# =============================================================================
# EVENT GENERATOR
# =============================================================================

class EventGenerator:
    """
    Weighted event selection engine with history tracking, sway bias,
    day-range filtering, and multi-step chain support.
    """

    def __init__(
        self,
        event_pool: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.event_pool: List[Dict[str, Any]] = (
            list(event_pool) if event_pool is not None else list(WEIGHTED_EVENT_POOL)
        )
        self.event_history: List[Dict[str, Any]] = []
        # Maps chain_id → current step index (0-based)
        self.chain_progress: Dict[str, int] = {}

    # ── Core Generation ────────────────────────────────────────────────────

    def get_weighted_pool(
        self, sway: int, tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter and weight events based on sway and optional tag filter.

        Sway bias multipliers:
            Matching sway bias:  weight * 2
            Neutral events:      weight * 1.5 (always relevant)
            Opposing sway bias:  weight * 0.5

        Args:
            sway: Current player sway (-3 to +3).
            tags: Optional list of DNA tags to filter by.

        Returns:
            List of (event, effective_weight) usable by random.choices().
        """
        pool = []
        for event in self.event_pool:
            bias = event.get("sway_bias", "neutral")
            base_weight = event.get("weight", 3)

            # Sway weighting
            if bias == "neutral":
                effective = base_weight * 1.5
            elif (bias == "crown" and sway < 0) or (bias == "crew" and sway > 0):
                effective = base_weight * 2  # Matches current political lean
            else:
                effective = base_weight * 0.5  # Opposes current lean

            # Tag filter (optional)
            if tags and event.get("tag") not in tags:
                continue

            pool.append((event, effective))

        return pool

    def generate_event(
        self,
        sway: int,
        day: int,
        faction_context: Optional[Dict[str, Any]] = None,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """
        Generate a weighted event appropriate for the current game state.

        Args:
            sway: Current player sway.
            day: Current in-game day.
            faction_context: Optional dict (unused in base implementation,
                             available for subclass extension).
            rng: Optional Random for deterministic testing.

        Returns:
            A copy of the selected event dict, with 'day' field added.
        """
        _rng = rng or random

        # Filter by day range
        day_pool = []
        for event in self.event_pool:
            day_range = event.get("day_range", [1, None])
            min_day = day_range[0] if day_range[0] is not None else 1
            max_day = day_range[1]
            if day < min_day:
                continue
            if max_day is not None and day > max_day:
                continue
            day_pool.append(event)

        if not day_pool:
            day_pool = list(self.event_pool)

        # Apply sway weights
        weighted = []
        weights = []
        for event in day_pool:
            bias = event.get("sway_bias", "neutral")
            base_weight = event.get("weight", 3)
            if bias == "neutral":
                w = base_weight * 1.5
            elif (bias == "crown" and sway < 0) or (bias == "crew" and sway > 0):
                w = base_weight * 2.0
            else:
                w = base_weight * 0.5
            weighted.append(event)
            weights.append(w)

        chosen = _rng.choices(weighted, weights=weights, k=1)[0]
        event_copy = dict(chosen)
        event_copy["day"] = day

        # Record in history
        self.event_history.append({
            "day": day,
            "event_id": event_copy.get("event_id", "unknown"),
            "bias": event_copy.get("sway_bias", "neutral"),
            "tag": event_copy.get("tag", ""),
        })

        return event_copy

    # ── Chain Events ───────────────────────────────────────────────────────

    def generate_chain_event(self, trigger_event_id: str) -> Optional[Dict[str, Any]]:
        """
        Return the next step in an event chain, if one exists.

        Args:
            trigger_event_id: The chain_id that was triggered.

        Returns:
            Next chain event dict, or None if chain is complete or unknown.
        """
        if trigger_event_id not in EVENT_CHAINS:
            return None

        chain = EVENT_CHAINS[trigger_event_id]
        step = self.chain_progress.get(trigger_event_id, 0)

        if step >= len(chain):
            return None

        event = dict(chain[step])
        self.chain_progress[trigger_event_id] = step + 1

        return event

    def is_chain_complete(self, chain_id: str) -> bool:
        """Return True if a chain has been fully consumed."""
        if chain_id not in EVENT_CHAINS:
            return True
        chain = EVENT_CHAINS[chain_id]
        step = self.chain_progress.get(chain_id, 0)
        return step >= len(chain)

    # ── Custom Events ──────────────────────────────────────────────────────

    def add_custom_event(self, event_data: Dict[str, Any]) -> None:
        """Add a custom event to the active pool."""
        self.event_pool.append(dict(event_data))

    # ── Serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_history": list(self.event_history),
            "chain_progress": dict(self.chain_progress),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventGenerator":
        gen = cls()
        gen.event_history = list(data.get("event_history", []))
        gen.chain_progress = dict(data.get("chain_progress", {}))
        return gen
