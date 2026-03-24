#!/usr/bin/env python3
"""
CROWN & CREW ENGINE
-------------------
Variable-length narrative arcs. One choice to make.

A narrative decision engine for the C.O.D.E.X. system.
Implements the "Blind Allegiance" loop, Sway mechanics,
Political Gravity (weighted council voting), rest-based
progression, and quest archetype injection.

Supports dynamic world injection via WorldState dicts
from codex_world_engine.py.

Version: 4.0 (Rest Progression + Quest Archetypes)
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional

try:
    from codex.core.mechanics.clock import DayClock, TimeOfDay
    _DAY_CLOCK_AVAILABLE = True
except ImportError:
    _DAY_CLOCK_AVAILABLE = False

try:
    from codex.core.services.narrative_loom import (
        synthesize_narrative, SessionManifest, diagnostic_trace,
    )
    NARRATIVE_LOOM_AVAILABLE = True
except ImportError:
    NARRATIVE_LOOM_AVAILABLE = False

try:
    from codex.core.memory import MemoryShard, ShardType
    MEMORY_SHARDS_AVAILABLE = True
except ImportError:
    MEMORY_SHARDS_AVAILABLE = False

# =============================================================================
# HARDCODED DATA — EXPANDED POOLS
# =============================================================================

# Original (4) + Expansion (4) = 8 Patrons
PATRONS: tuple[str, ...] = (
    # Original Set
    "The High Inquisitor",
    "The Governor",
    "The Spymaster",
    "The Justiciar",
    # Variety Pack — Archetypes
    "The High Priestess",       # Religious Authority
    "The Merchant Prince",      # Financial Authority
    "The Iron Marshal",         # Military Authority
    "The Court Astrologer"      # Arcane Authority
)

# Original (4) + Expansion (4) = 8 Leaders
LEADERS: tuple[str, ...] = (
    # Original Set
    "Captain Vane",
    "The Defector",
    "The Mercenary",
    "The Mystic",
    # Variety Pack — Archetypes
    "Brother Ash",              # The Zealot
    "Lady Miren",               # The Fallen Noble
    "The Faceless",             # The Anarchist
    "Old Sergeant Kell"         # The Veteran
)

# Narrative DNA Tags
TAGS: list[str] = ["BLOOD", "GUILE", "HEARTH", "SILENCE", "DEFIANCE"]

# =============================================================================
# GOLDEN SET + VARIETY PACK — NARRATIVE ASSETS
# =============================================================================

# The Temptation of Safety (Original 5 + Expansion 5 = 10)
PROMPTS_CROWN: list[str] = [
    # --- Original Set ---
    "A bounty hunter hails the camp. He offers a clean slate to anyone who points out the Leader. His hand rests on his blade.",
    "You find a dead courier in the mud. His satchel holds blank pardons, signed and sealed. One name would set you free.",
    "The Patron's voice echoes in your skull: 'Bring me the Mystic's journal, and your sister walks free.' The book is in your hands.",
    "A checkpoint guards the river crossing. The sergeant remembers your face—but not your crimes. One lie could buy safe passage.",
    "The Spymaster's raven lands on your shoulder at dawn. The message: 'Light a fire at midnight. We will do the rest.'",
    # --- Variety Pack (Guilt & Future Promises) ---
    "A letter arrives from your mother. She's sick. The Patron offers medicine—enough for a year—in exchange for one name.",
    "The Patron's agent unfolds a deed. Forty acres. A farmhouse. A life. All you have to do is tell them where the Crew sleeps tonight.",
    "You pass a village you burned with the Crew last winter. A child recognizes your face. The Patron's men are watching. Do you wave?",
    "The Spymaster offers new documents: a new name, a new history, a new life. 'Walk away,' he says. 'No one has to die.'",
    "You dream of the guard you killed at the checkpoint. He had a locket with two faces inside. The Patron knows his widow."
]

# The Burden of Loyalty (Original 5 + Expansion 5 = 10)
PROMPTS_CREW: list[str] = [
    # --- Original Set ---
    "The youngest crewmate shivers through the fever. Your last dose of willow bark could save her—or keep you walking tomorrow.",
    "The Leader hands you a rusted blade. 'Bury this in the thornfield. Tell no one what it did.' The blood is still wet.",
    "A crewmate collapses in the gorge. Carrying them means missing the rendezvous. Leaving them means the crows eat well tonight.",
    "The Captain asks you to lie to the others about the food. 'They'll panic if they know.' There's enough for three. You are five.",
    "The Defector whispers: 'I know what you did before you joined us.' He wants your silence in exchange for his. Do you shake hands?",
    # --- Variety Pack (Internal Conflict & Morale) ---
    "The Leader wants to cross the frozen lake. You've seen ice like this before—it killed your brother. Do you challenge the order?",
    "Two crewmates are circling each other with knives drawn—one stole the other's rations. The Leader is asleep. Do you intervene?",
    "The Crew captures a Crown scout. He's young. Terrified. The Leader hands you the knife. 'No witnesses.' Do you obey?",
    "The oldest crewmate can't keep pace. He knows it too. He asks you for the mercy of a lie: 'Tell them I fell behind on purpose.'",
    "You find extra food hidden in the Leader's pack—enough for three days. The others are starving. Do you confront, steal, or stay silent?"
]

# The Hostile Wilds (Original 5 + Expansion 5 = 10)
PROMPTS_WORLD: list[str] = [
    # --- Original Set (Swamp/Forest/River) ---
    "The Blackmire stretches ahead—three miles of sucking mud and rotting reeds. Something large moved beneath the surface at dawn.",
    "Freezing rain turns the cliffside path to glass. One slip means the river takes you. The rope is frayed. Who goes first?",
    "The forest burns behind you. Smoke fills the valley. The only shelter is a collapsed mine that smells of old death.",
    "You wake to silence. The birds have stopped singing. The treeline watches. Something followed you from the last village.",
    "The river has swollen overnight. Your supplies are on the far bank. The current carries bodies from upstream.",
    # --- Variety Pack (New Biomes) ---
    "The Mountain Pass narrows to a blade's width. Wind screams through the gap. Below: a thousand feet of nothing. Above: a rockslide waiting.",
    "The Ruined City rises from the fog—towers broken, streets silent. They say plague killed everyone in a single night. Something moves in the bell tower.",
    "The Salt Flats stretch to every horizon. No shade. No water. The sun splits your lips. A skeleton points west.",
    "The Dead Forest surrounds you—every tree white and bare, killed by something in the soil. The silence is absolute. Nothing lives here.",
    "The Flooded Valley was farmland last month. Now brown water hides everything—fences, roads, the dead. You wade chest-deep, feeling for solid ground."
]

# The Echo (Original 5 + Expansion 5 = 10)
PROMPTS_CAMPFIRE: list[str] = [
    # --- Original Set ---
    "The fire dies low. Someone hums a hymn from the old country. Who taught you that song? Are they still alive?",
    "You catch a crewmate staring at the flames, lips moving without sound. What prayer do you think they're saying?",
    "The Leader shows a scar he's never explained. Tonight, he seems ready to talk. What question have you been afraid to ask?",
    "A shooting star crosses the smoke. In your village, that meant a soul was leaving. Whose face comes to mind?",
    "The Mystic deals cards no one asked for. Yours shows The Drowned King. 'Tell us about the water,' she says. 'Tell us why you fear it.'",
    # --- Variety Pack (Hopes & Fears) ---
    "The fire crackles low. Someone asks: 'When this is over—if we make it—what's the first thing you'll eat?' What do you answer?",
    "You realize you can't remember your father's voice anymore. Just his face, fading. Who else are you forgetting out here?",
    "A crewmate asks where you'll go if you survive. Not what you'll do—where. What place have you been dreaming of?",
    "You catch your reflection in a blade. The face looking back is harder than you remember. When did you start looking like them?",
    "Someone shares the last of their tobacco. The smoke tastes like your grandfather's study. What memory does it unlock?"
]

# Day 3 Special Event — The Breach
PROMPT_SECRET_WITNESS: str = (
    "A figure steps from the shadows at the edge of camp. They say nothing—but they hold something that belongs to you. "
    "Something you thought was buried. The crew is watching. The Patron's men are close. What do you do?"
)

# =============================================================================
# DAY 3 MIRROR BREAK — Sin Generation (WO-V99)
# =============================================================================
# The player's dominant DNA tag determines what sin they witness the
# Crew Leader committing. The player must choose: hide or expose.

MIRROR_SINS: dict[str, dict[str, str]] = {
    "BLOOD": {
        "sin": "Unnecessary Brutality",
        "witness": (
            "You couldn't sleep. You followed the sounds past the firelight.\n\n"
            "The {leader} stands over a kneeling figure — a prisoner, hands bound, "
            "no weapon, no threat. The first blow was enough. The second was punishment. "
            "The third was something else entirely. The prisoner stopped moving two blows ago.\n\n"
            "The {leader} hasn't seen you yet."
        ),
    },
    "GUILE": {
        "sin": "A Secret Deal",
        "witness": (
            "You couldn't sleep. You followed the whispers past the firelight.\n\n"
            "The {leader} is meeting someone — a Crown agent, if the cloak is any "
            "indication. Coin changes hands. A sealed letter. The {leader}'s smile "
            "is not the smile of someone being extorted. It is the smile of someone "
            "closing a deal.\n\n"
            "Neither of them has seen you yet."
        ),
    },
    "HEARTH": {
        "sin": "Hoarding and Neglect",
        "witness": (
            "You couldn't sleep. The hunger drove you past the firelight.\n\n"
            "The {leader} has a cache — hidden beneath a false bottom in their "
            "pack. Dried meat. Medicine. Clean bandages. Enough for three days, "
            "while the weakest members of the crew go hungry and the wounded "
            "wrap their cuts in rags.\n\n"
            "The {leader} hasn't seen you yet."
        ),
    },
    "SILENCE": {
        "sin": "Erasing History",
        "witness": (
            "You couldn't sleep. The smell of burning paper drew you past the firelight.\n\n"
            "The {leader} feeds documents into a small fire — letters, manifests, "
            "names. You catch fragments: dates, routes, a list of people who helped "
            "the crew. Evidence of the journey, being erased one page at a time. "
            "When this is done, there will be no record that any of you were here.\n\n"
            "The {leader} hasn't seen you yet."
        ),
    },
    "DEFIANCE": {
        "sin": "A False Flag",
        "witness": (
            "You couldn't sleep. The sound of a forged seal press drew you past the firelight.\n\n"
            "The {leader} is fabricating Crown orders — forged documents that will "
            "redirect patrols into a civilian settlement. The settlers will be "
            "interrogated, their homes searched, their livestock seized. The Crew "
            "buys a day. The village pays the price.\n\n"
            "The {leader} hasn't seen you yet."
        ),
    },
}

# =============================================================================
# SWAY TIER DEFINITIONS
# =============================================================================

SWAY_TIERS: dict[int, dict] = {
    -3: {
        "name": "Crown Agent",
        "power": "Royal Decree",
        "desc": "Your word carries the Crown's authority.",
        "effect": "Once per march: force a council dilemma to resolve Crown. Crew hostility rises.",
        "grants": "royal_decree",
    },
    -2: {
        "name": "Crown Sympathizer",
        "power": "Imperial Intelligence",
        "desc": "The Crown shares what it knows.",
        "effect": "Morning events reveal extra detail. Crown-only choice options unlock.",
        "grants": "imperial_intelligence",
    },
    -1: {
        "name": "Crown Leaning",
        "power": "Safe Passage",
        "desc": "The Crown's patrols wave you through.",
        "effect": "Can bypass one midday encounter. Campfire prompts are colder.",
        "grants": "safe_passage",
    },
    0: {
        "name": "Drifter",
        "power": "The Whirlpool",
        "desc": "No allies. No mercy. But you can talk to anyone.",
        "effect": "Double Draw penalty. Unique broker dialogue with both sides.",
        "grants": "whirlpool",
    },
    1: {
        "name": "Crew Leaning",
        "power": "Trusted Ear",
        "desc": "The Crew shares gossip.",
        "effect": "Morning events reveal NPC motives. Crown patrols more frequent.",
        "grants": "trusted_ear",
    },
    2: {
        "name": "Crew Trusted",
        "power": "The Inner Circle",
        "desc": "They trust you with secrets.",
        "effect": "Council dilemmas reveal a hidden third option from the Leader.",
        "grants": "inner_circle",
    },
    3: {
        "name": "Crew Loyal",
        "power": "The Leader's Confidence",
        "desc": "The Leader trusts you above all others.",
        "effect": "Once per march: the Leader reveals their secret agenda and betrayal trigger.",
        "grants": "leaders_confidence",
    },
}

# =============================================================================
# LEGACY TITLES — CAMPAIGN BRIDGE (Alignment + Dominant Tag)
# =============================================================================

LEGACY_TITLES: dict[tuple[str, str], dict[str, str]] = {
    # CREW Alignments
    ("CREW", "HEARTH"):    {"title": "The Shepherd",   "desc": "You carried them when they could not walk."},
    ("CREW", "DEFIANCE"):  {"title": "The Firebrand",  "desc": "You burned brighter than their fear."},
    ("CREW", "BLOOD"):     {"title": "The Enforcer",   "desc": "You did what had to be done."},
    ("CREW", "GUILE"):     {"title": "The Schemer",    "desc": "You played the long game for the Crew."},
    ("CREW", "SILENCE"):   {"title": "The Shadow",     "desc": "You kept their secrets safe."},

    # CROWN Alignments
    ("CROWN", "GUILE"):    {"title": "The Whisper",    "desc": "You traded in secrets and lies."},
    ("CROWN", "SILENCE"):  {"title": "The Witness",    "desc": "You saw everything and said nothing."},
    ("CROWN", "BLOOD"):    {"title": "The Headsman",   "desc": "You were the Crown's blade."},
    ("CROWN", "HEARTH"):   {"title": "The Turncloak",  "desc": "You betrayed those who fed you."},
    ("CROWN", "DEFIANCE"): {"title": "The Contrarian", "desc": "You defied even those you served."},

    # DRIFTER Alignments (all tags map to Survivor)
    ("DRIFTER", "BLOOD"):    {"title": "The Survivor", "desc": "You outlasted them all."},
    ("DRIFTER", "GUILE"):    {"title": "The Survivor", "desc": "You outlasted them all."},
    ("DRIFTER", "HEARTH"):   {"title": "The Survivor", "desc": "You outlasted them all."},
    ("DRIFTER", "SILENCE"):  {"title": "The Survivor", "desc": "You outlasted them all."},
    ("DRIFTER", "DEFIANCE"): {"title": "The Survivor", "desc": "You outlasted them all."},
}

# Auto-tag mappings for allegiance choices (fallback when Echo is skipped)
AUTO_TAGS: dict[str, list[str]] = {
    "crew": ["HEARTH", "DEFIANCE", "BLOOD"],
    "crown": ["GUILE", "SILENCE", "BLOOD"]
}

# =============================================================================
# THE ECHO — Response archetypes (WO-V108)
# =============================================================================
# Each response archetype works for ANY prompt. The player picks how their
# character reacts, which determines the DNA tag. These are universal —
# modules can override with prompt-specific responses.

ECHO_RESPONSES: dict[str, dict[str, str]] = {
    "BLOOD": {
        "label": "With force",
        "desc": "You solved this with violence, threat, or raw intimidation.",
    },
    "GUILE": {
        "label": "With cunning",
        "desc": "You lied, bargained, misdirected, or played both sides.",
    },
    "HEARTH": {
        "label": "With compassion",
        "desc": "You prioritized someone's safety, comfort, or dignity over advantage.",
    },
    "SILENCE": {
        "label": "With silence",
        "desc": "You kept the secret, bore the burden alone, or looked the other way.",
    },
    "DEFIANCE": {
        "label": "With defiance",
        "desc": "You challenged the order, broke the rule, or exposed the lie.",
    },
}

# Context-sensitive Echo prompts — keyed by allegiance side.
# Displayed after the prompt reveal to frame the player's response.
ECHO_FRAME: dict[str, str] = {
    "crown": "The weight of order presses down. How did you carry it?",
    "crew": "The fire of freedom burns bright. How did you feed it?",
}


# =============================================================================
# MORNING EVENTS — Interactive Road Encounters (WO-V14.0, V107.0)
# =============================================================================
# Each event now has a `choices` array. Each choice: text, tag, sway_effect.
# Events without choices fall back to auto-generated generic options.

MORNING_EVENTS: list[dict] = [
    {
        "text": "A Crown patrol passes within bowshot. Their captain scans your camp but moves on. You catch his eye — and he nods, once.",
        "bias": "crown", "tag": "GUILE",
        "choices": [
            {"text": "Nod back. A silent understanding between soldiers.", "tag": "GUILE", "sway_effect": -1},
            {"text": "Look away. Don't give him a face to remember.", "tag": "SILENCE", "sway_effect": 0},
            {"text": "Spit in the dirt where he can see. Let him know what you think of his mercy.", "tag": "DEFIANCE", "sway_effect": 1},
        ],
    },
    {
        "text": "You find a dead messenger on the road. His satchel holds sealed orders — troop movements, supply routes. The Crew could use this.",
        "bias": "crew", "tag": "DEFIANCE",
        "choices": [
            {"text": "Take the orders to the Crew. Intelligence wins wars.", "tag": "DEFIANCE", "sway_effect": 1},
            {"text": "Bury the satchel with the body. Some things aren't yours to use.", "tag": "HEARTH", "sway_effect": 0},
            {"text": "Read the orders, memorize them, burn the originals. Keep the advantage for yourself.", "tag": "GUILE", "sway_effect": 0},
        ],
    },
    {
        "text": "Smoke rises from a farmstead ahead. Crown soldiers are burning grain stores to deny them to rebels. A family watches from the road.",
        "bias": "neutral", "tag": "HEARTH",
        "choices": [
            {"text": "Intervene. Drive the soldiers off and help the family salvage what they can.", "tag": "BLOOD", "sway_effect": 1},
            {"text": "Offer the family a place in your column. You can't save the grain but you can save them.", "tag": "HEARTH", "sway_effect": 0},
            {"text": "Keep moving. You can't fight every injustice and survive.", "tag": "SILENCE", "sway_effect": -1},
        ],
    },
    {
        "text": "A deserter stumbles out of the treeline, Crown tabard torn. He begs to join you. His hands are steady and his eyes are clear.",
        "bias": "crew", "tag": "BLOOD",
        "choices": [
            {"text": "Take him in. Everyone deserves a second chance.", "tag": "HEARTH", "sway_effect": 1},
            {"text": "Interrogate him first. Steady hands and clear eyes could mean he's a plant.", "tag": "GUILE", "sway_effect": 0},
            {"text": "Turn him away. Every new mouth is a risk you can't afford.", "tag": "BLOOD", "sway_effect": -1},
        ],
    },
    {
        "text": "A Crown magistrate has posted your description at the crossroads. The likeness is poor — for now. Someone is asking questions.",
        "bias": "crown", "tag": "SILENCE",
        "choices": [
            {"text": "Tear the notice down and destroy it. Erase the evidence.", "tag": "DEFIANCE", "sway_effect": 1},
            {"text": "Leave it. Tearing it down proves you were here.", "tag": "SILENCE", "sway_effect": 0},
            {"text": "Alter the sketch — make it look like someone else. Redirect the hunt.", "tag": "GUILE", "sway_effect": -1},
        ],
    },
    {
        "text": "You wake to find fresh bread and dried meat left at the edge of camp. No footprints. No note. Someone knows you're here and wants you fed.",
        "bias": "neutral", "tag": "HEARTH",
        "choices": [
            {"text": "Accept the gift gratefully. Share it equally.", "tag": "HEARTH", "sway_effect": 0},
            {"text": "Check for poison. Generosity from strangers is rarely free.", "tag": "GUILE", "sway_effect": -1},
            {"text": "Follow the trail. Find out who's watching and why.", "tag": "BLOOD", "sway_effect": 1},
        ],
    },
    {
        "text": "A merchant caravan flies Crown colors but the drivers wink at your crew. 'Flags are cheap,' one mutters. 'Loyalty isn't.'",
        "bias": "crew", "tag": "GUILE",
        "choices": [
            {"text": "Trade with them. Supplies matter more than politics.", "tag": "GUILE", "sway_effect": 0},
            {"text": "Ask what they really carry under those Crown tarps.", "tag": "DEFIANCE", "sway_effect": 1},
            {"text": "Report them to the nearest Crown checkpoint. Play both sides.", "tag": "GUILE", "sway_effect": -1},
        ],
    },
    {
        "text": "You pass a gibbet at the crossroads. The body wears a Crew sash. A warning, or a message: the Crown's justice reaches everywhere.",
        "bias": "crown", "tag": "SILENCE",
        "choices": [
            {"text": "Cut the body down and bury it properly. Even the dead deserve dignity.", "tag": "HEARTH", "sway_effect": 1},
            {"text": "Study the body for information. How long? What method? Who ordered this?", "tag": "GUILE", "sway_effect": 0},
            {"text": "Walk past without looking. You can't afford to care.", "tag": "SILENCE", "sway_effect": -1},
        ],
    },
    {
        "text": "A half-drowned rider catches up to your party. She carries a letter from the Leader — new orders, or old debts calling due.",
        "bias": "crew", "tag": "DEFIANCE",
        "choices": [
            {"text": "Read the letter aloud to the group. No more secrets.", "tag": "DEFIANCE", "sway_effect": 1},
            {"text": "Read it privately first. Knowledge is leverage.", "tag": "GUILE", "sway_effect": 0},
            {"text": "Burn it unread. You follow your own orders now.", "tag": "BLOOD", "sway_effect": 0},
        ],
    },
    {
        "text": "The road forks. One path is smooth and patrolled — Crown territory. The other is overgrown and unmarked. Both lead to the border.",
        "bias": "neutral", "tag": "BLOOD",
        "choices": [
            {"text": "Take the Crown road. Speed matters more than secrecy.", "tag": "BLOOD", "sway_effect": -1},
            {"text": "Take the wild path. Harder ground, but no eyes on you.", "tag": "SILENCE", "sway_effect": 1},
            {"text": "Split the group. One draws attention, the other slips through.", "tag": "GUILE", "sway_effect": 0},
        ],
    },
]


# =============================================================================
# MIDDAY ENCOUNTERS — The March (WO-V109)
# =============================================================================
# Each encounter presents a physical/social test during the day's travel.
# Choices carry tag + sway effects. Safe Passage (sway -1) can bypass these.
# Trusted Ear (sway +1) adds NPC motive reveals.

MIDDAY_ENCOUNTERS: list[dict] = [
    {
        "text": "The trail narrows to a knife-edge ridge. Wind tears at your clothing. Below, the drop is absolute. Someone has to go first.",
        "choices": [
            {"text": "Go first yourself. Lead from the front.", "tag": "BLOOD", "sway_effect": 1},
            {"text": "Send the strongest. This isn't about bravery — it's about weight distribution.", "tag": "GUILE", "sway_effect": 0},
            {"text": "Rope everyone together. If one falls, everyone catches them — or everyone dies.", "tag": "HEARTH", "sway_effect": 0},
        ],
    },
    {
        "text": "A checkpoint blocks the road. Two guards, bored and cold. They haven't seen your description yet — but they will soon.",
        "choices": [
            {"text": "Bluff your way through. Papers can be faked with confidence.", "tag": "GUILE", "sway_effect": -1},
            {"text": "Go around. Add two hours, lose no blood.", "tag": "SILENCE", "sway_effect": 0},
            {"text": "Ambush them. They chose their post.", "tag": "BLOOD", "sway_effect": 1},
        ],
    },
    {
        "text": "A river crossing — waist-deep, fast-moving, ice-cold. The bridge is intact but patrolled. The ford is hidden but dangerous.",
        "choices": [
            {"text": "Take the bridge. Speed over stealth.", "tag": "BLOOD", "sway_effect": -1},
            {"text": "Ford the river. Cold won't kill you. Patrols will.", "tag": "DEFIANCE", "sway_effect": 1},
            {"text": "Wait for nightfall. Cross under darkness.", "tag": "SILENCE", "sway_effect": 0},
        ],
    },
    {
        "text": "A fellow traveler — wounded, limping, carrying too much. They're slowing down. The column can't afford to slow down with them.",
        "choices": [
            {"text": "Help carry their pack. We don't leave people behind.", "tag": "HEARTH", "sway_effect": 1},
            {"text": "Trade: your help for their information. Everyone pays their way.", "tag": "GUILE", "sway_effect": 0},
            {"text": "Walk past. You can't save everyone and survive.", "tag": "SILENCE", "sway_effect": -1},
        ],
    },
    {
        "text": "An abandoned camp — still warm coals, scattered rations, a sword driven into the earth. Someone left in a hurry. Or was taken.",
        "choices": [
            {"text": "Search the camp. Intelligence is worth the risk.", "tag": "GUILE", "sway_effect": 0},
            {"text": "Take what's useful and move on. The dead don't need supplies.", "tag": "BLOOD", "sway_effect": 0},
            {"text": "Follow the tracks. Someone might need help — or might lead you to danger.", "tag": "DEFIANCE", "sway_effect": 1},
        ],
    },
    {
        "text": "A Crown supply wagon sits overturned in a ditch, its guard detail scattered. Crates of rations, medicine, and ammunition spill across the road.",
        "choices": [
            {"text": "Take everything. This is war, and war has spoils.", "tag": "BLOOD", "sway_effect": 1},
            {"text": "Take only the medicine. Leave the rest for whoever else passes.", "tag": "HEARTH", "sway_effect": 0},
            {"text": "Mark the location and report it. Someone owes you a favor now.", "tag": "GUILE", "sway_effect": -1},
        ],
    },
    {
        "text": "The path enters dense forest. Branches close overhead like a cage. Your scouts report movement ahead — could be wildlife. Could be an ambush.",
        "choices": [
            {"text": "Push through. If it's an ambush, meet it head-on.", "tag": "BLOOD", "sway_effect": 0},
            {"text": "Send a decoy ahead. If something springs, it springs on a shadow.", "tag": "GUILE", "sway_effect": 0},
            {"text": "Go around. Add an hour, keep everyone alive.", "tag": "HEARTH", "sway_effect": 1},
        ],
    },
    {
        "text": "A local farmer blocks the trail with a loaded cart. 'Road tax,' she says flatly. 'Crown or Crew, everyone pays to cross my land.' She isn't afraid of you.",
        "choices": [
            {"text": "Pay the tax. Respect earns passage.", "tag": "HEARTH", "sway_effect": 0},
            {"text": "Negotiate. You have information worth more than coin.", "tag": "GUILE", "sway_effect": 0},
            {"text": "Move the cart yourself. She can complain to whoever she likes.", "tag": "DEFIANCE", "sway_effect": 1},
        ],
    },
    {
        "text": "Smoke on the horizon — a settlement burning. Not your fight. Not your people. But the screams carry across the valley.",
        "choices": [
            {"text": "Intervene. You didn't come this far to look away.", "tag": "DEFIANCE", "sway_effect": 1},
            {"text": "Skirt the edge. Help survivors you find on the road, not in the fire.", "tag": "HEARTH", "sway_effect": 0},
            {"text": "Use the distraction. While they burn, you move unseen.", "tag": "SILENCE", "sway_effect": -1},
        ],
    },
    {
        "text": "A narrow canyon offers a shortcut — two hours off the march. But the walls are too close. One rockslide, one ambush, one bad step and there's no way out.",
        "choices": [
            {"text": "Take the canyon. Fortune favors the bold — and the desperate.", "tag": "BLOOD", "sway_effect": 1},
            {"text": "Scout it first. Send two ahead, wait for their signal.", "tag": "GUILE", "sway_effect": 0},
            {"text": "Take the long way. Two extra hours beats a mass grave.", "tag": "SILENCE", "sway_effect": -1},
        ],
    },
]

# =============================================================================
# COUNCIL DILEMMAS — Consolidated (was duplicated across 3 files)
# =============================================================================

COUNCIL_DILEMMAS: list[dict] = [
    {
        "prompt": "A wounded Crown courier is found at the edge of camp. He carries sealed orders — troop positions, supply caches, names of informants. The Crew could use this intelligence. But the courier begs for mercy.",
        "crown": "Return the courier and his documents to the nearest Crown outpost.",
        "crew": "Take the intelligence and leave the courier to the road.",
        "consequences": {
            "crown": {"narrative": "The courier limps away. Tomorrow, the Crown will know you showed mercy.", "morning_bias": "crown", "tag": "HEARTH", "sway_modifier": -1},
            "crew": {"narrative": "The intelligence is good — patrol routes, supply lines. The Crew moves faster tomorrow.", "morning_bias": "crew", "tag": "DEFIANCE", "sway_modifier": 1},
        },
    },
    {
        "prompt": "A village elder offers sanctuary for the night — warm beds, hot food, safe walls. But she asks a price: hand over the youngest crewmate as a ward. 'Insurance,' she calls it. 'Against what you might do to my people.'",
        "crown": "Accept the deal. One life for one night of safety.",
        "crew": "Refuse and camp in the cold. The Crew stays whole.",
        "consequences": {
            "crown": {"narrative": "You sleep warm. But the young crewmate's face haunts the morning.", "morning_bias": "crown", "tag": "SILENCE", "sway_modifier": -1},
            "crew": {"narrative": "Cold camp, colder ground. But no one was traded. Loyalty deepens.", "morning_bias": "crew", "tag": "HEARTH", "sway_modifier": 1},
        },
    },
    {
        "prompt": "A Crown defector approaches under a white flag. He offers maps of every checkpoint between here and the border. His price: safe passage for his family, currently held in a Crew-controlled town.",
        "crown": "Take the maps and honor the deal — the Crown's intelligence network is worth the cost.",
        "crew": "Refuse. The Crew's grip on that town is leverage we can't afford to lose.",
        "consequences": {
            "crown": {"narrative": "The maps are genuine. Tomorrow's route avoids two patrols.", "morning_bias": "neutral", "tag": "GUILE", "sway_modifier": -1},
            "crew": {"narrative": "The town stays under Crew control. The defector disappears into the night.", "morning_bias": "crew", "tag": "BLOOD", "sway_modifier": 1},
        },
    },
    {
        "prompt": "The Crew's healer has been dosing the Leader with poppy milk — 'to manage the pain,' she says. But the Leader's judgment has been slipping. Confronting her means losing the only one who can treat wounds.",
        "crown": "Report the healer's actions and demand she stop. Order must be maintained.",
        "crew": "Say nothing. The healer keeps us alive. The Leader's pain is real.",
        "consequences": {
            "crown": {"narrative": "The healer stops. The Leader's clarity returns — along with the screaming pain.", "morning_bias": "crown", "tag": "DEFIANCE", "sway_modifier": -1},
            "crew": {"narrative": "The dosing continues. The Leader drifts further. But no one bleeds out tonight.", "morning_bias": "crew", "tag": "SILENCE", "sway_modifier": 0},
        },
    },
    {
        "prompt": "A bridge spans the gorge — the only crossing for fifty miles. Crown engineers have rigged it with blasting powder. A single torch would buy days of pursuit-free travel. But a merchant caravan is crossing now.",
        "crown": "Wait for the caravan to cross, then sabotage the bridge.",
        "crew": "Light the fuse now. Every hour counts. The merchants knew the risks.",
        "consequences": {
            "crown": {"narrative": "The caravan crosses safely. The delay costs a day, but no innocent blood was spilled.", "morning_bias": "crown", "tag": "HEARTH", "sway_modifier": -1},
            "crew": {"narrative": "The bridge goes up in fire and screaming. No one follows — but you carry the sound.", "morning_bias": "crew", "tag": "BLOOD", "sway_modifier": 1},
        },
    },
    {
        "prompt": "Two crewmates have been caught stealing from the communal supplies. The rations they took would have fed the weakest members for two days. The Leader wants them flogged. The Patron's code demands exile.",
        "crown": "Exile them. The law is clear, even out here.",
        "crew": "Flog them and move on. We need every hand we have.",
        "consequences": {
            "crown": {"narrative": "Two fewer mouths. Two fewer hands. The law was served, but the march is harder now.", "morning_bias": "crown", "tag": "SILENCE", "sway_modifier": -1},
            "crew": {"narrative": "The flogging is public and brief. No one steals again. But the thieves' eyes are dead.", "morning_bias": "crew", "tag": "BLOOD", "sway_modifier": 1},
        },
    },
    {
        "prompt": "A dying Crown soldier whispers the location of a hidden weapons cache — enough to arm the whole Crew. But it's in a chapel, and taking it means desecrating ground the locals hold sacred.",
        "crown": "Leave the weapons. Some lines shouldn't be crossed.",
        "crew": "Take everything. The dead don't need swords. The living do.",
        "consequences": {
            "crown": {"narrative": "The chapel stands. Tomorrow, the locals leave food at the road's edge.", "morning_bias": "neutral", "tag": "HEARTH", "sway_modifier": -1},
            "crew": {"narrative": "The Crew is armed. The locals bolt their doors as you pass.", "morning_bias": "crew", "tag": "DEFIANCE", "sway_modifier": 1},
        },
    },
    {
        "prompt": "The Patron has sent a raven with an offer: full amnesty for everyone except the Leader. Surrender one person, and the rest walk free. The Leader doesn't know about the message yet.",
        "crown": "Accept the offer. One life for many.",
        "crew": "Burn the message. We all make it, or none of us do.",
        "consequences": {
            "crown": {"narrative": "The deal is struck in whispers. The Leader suspects nothing — yet.", "morning_bias": "crown", "tag": "GUILE", "sway_modifier": -1},
            "crew": {"narrative": "The ashes of the message drift away. Tomorrow, the Patron sends hunters.", "morning_bias": "crew", "tag": "HEARTH", "sway_modifier": 1},
        },
    },
]


# =============================================================================
# VOTE POWER TABLE — POLITICAL GRAVITY
# =============================================================================
# Sway determines vote weight in council decisions.
# Deeper allegiance = heavier political influence.
VOTE_POWER: dict[int, int] = {
    0: 1,   # Drifter — one voice, easily ignored
    1: 2,   # Leaning — some credibility
    2: 4,   # Trusted — respected voice
    3: 8,   # Loyal — the heaviest vote
}


# =============================================================================
# PLAYER STATE (WO-V133 — Multiplayer)
# =============================================================================

_SOLO = "_solo"  # Sentinel name for single-player mode


@dataclass
class CrownPlayerState:
    """Per-player state in a Crown & Crew session.

    Each player tracks their own sway, DNA, history, mirror choice, and
    power usage independently. Shared state (day, patron, leader, prompts,
    factions, consequences) lives on the engine.
    """
    name: str = ""
    sway: int = 0
    dna: dict[str, int] = field(default_factory=lambda: {tag: 0 for tag in TAGS})
    history: list[dict] = field(default_factory=list)

    # Echo state
    _pending_allegiance: str | None = field(default=None, repr=False)
    _pending_echo: bool = field(default=False, repr=False)
    _pending_shift: int = field(default=0, repr=False)

    # Mirror Break
    _mirror_choice: str = field(default="", repr=False)
    _mirror_sin: str = field(default="", repr=False)

    # Power usage (once-per-march)
    _royal_decree_used: bool = field(default=False, repr=False)
    _leaders_confidence_used: bool = field(default=False, repr=False)
    _safe_passage_used: bool = field(default=False, repr=False)

    # Voting record
    dissent_count: int = field(default=0, repr=False)
    majority_count: int = field(default=0, repr=False)

    # Character Loom (WO-V124)
    _loom: object | None = field(default=None, repr=False)

    def get_dominant_tag(self) -> str:
        """Return the tag with the highest count."""
        if not any(self.dna.values()):
            return "SILENCE"
        return max(self.dna, key=lambda k: self.dna[k])

    def get_alignment(self) -> str:
        """Determine alignment from sway."""
        if self.sway > 0:
            return "CREW"
        elif self.sway < 0:
            return "CROWN"
        return "DRIFTER"

    def get_vote_power(self) -> int:
        """Get vote weight from sway magnitude."""
        return VOTE_POWER.get(abs(self.sway), 1)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "sway": self.sway,
            "dna": dict(self.dna),
            "history": list(self.history),
            "_pending_allegiance": self._pending_allegiance,
            "_pending_echo": self._pending_echo,
            "_pending_shift": self._pending_shift,
            "_mirror_choice": self._mirror_choice,
            "_mirror_sin": self._mirror_sin,
            "_royal_decree_used": self._royal_decree_used,
            "_leaders_confidence_used": self._leaders_confidence_used,
            "_safe_passage_used": self._safe_passage_used,
            "dissent_count": self.dissent_count,
            "majority_count": self.majority_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CrownPlayerState":
        ps = cls(name=data.get("name", ""))
        for key in ("sway", "dna", "history", "_pending_allegiance",
                     "_pending_echo", "_pending_shift", "_mirror_choice",
                     "_mirror_sin", "_royal_decree_used",
                     "_leaders_confidence_used", "_safe_passage_used",
                     "dissent_count", "majority_count"):
            if key in data:
                setattr(ps, key, data[key])
        return ps


# =============================================================================
# ENGINE CLASS
# =============================================================================

@dataclass
class CrownAndCrewEngine:
    """
    The Crown & Crew Narrative Engine.

    Tracks player allegiance through the Sway system (-3 to +3).
    Implements the Blind Allegiance loop where players commit before seeing prompts.
    Generates Legacy Reports for Campaign Bridge continuity.

    Supports dynamic world injection via world_state dict from WorldEngine.
    Supports Political Gravity (weighted council voting via resolve_vote).
    Supports variable-length arcs via arc_length and rest-based progression.

    WO-V133: Multiplayer support via player slots. Per-player state (sway, DNA,
    history, powers) tracked in ``players`` dict. Single-player mode uses the
    ``_solo`` sentinel. All per-player methods accept ``player_name`` param.
    """
    day: int = 1
    sway: int = 0       # Legacy single-player sway (synced from _solo player)
    patron: str = ""
    leader: str = ""
    history: list[dict] = field(default_factory=list)  # Legacy (synced from _solo)

    # Narrative DNA tracking (legacy — synced from _solo player)
    dna: dict[str, int] = field(default_factory=lambda: {tag: 0 for tag in TAGS})

    # WO-V133: Multiplayer player slots
    players: dict[str, CrownPlayerState] = field(default_factory=dict, repr=False)

    # Arc length + rest progression (v4.0)
    arc_length: int = 5
    rest_type: str = "long"
    rest_config: dict = field(default_factory=lambda: {
        "sway_decay_on_skip": 1,
        "short_rest_sway_cap": 1,
        "breach_day_fraction": 0.6,
    })

    # World injection — optional dict from codex_world_engine.WorldState.to_dict()
    world_state: dict | None = field(default=None, repr=False)

    # Dynamic terminology (populated in __post_init__)
    terms: dict[str, str] = field(default_factory=dict, repr=False)

    # Dynamic prompt pools (populated in __post_init__)
    _prompts_crown: list[str] = field(default_factory=list, repr=False)
    _prompts_crew: list[str] = field(default_factory=list, repr=False)
    _prompts_world: list[str] = field(default_factory=list, repr=False)
    _prompts_campfire: list[str] = field(default_factory=list, repr=False)
    _secret_witness: str = field(default="", repr=False)
    _legacy_titles: dict = field(default_factory=dict, repr=False)

    # Track used prompts to avoid repeats
    _used_crown: list[int] = field(default_factory=list, repr=False)
    _used_crew: list[int] = field(default_factory=list, repr=False)
    _used_world: list[int] = field(default_factory=list, repr=False)
    _used_campfire: list[int] = field(default_factory=list, repr=False)
    _used_morning: list[int] = field(default_factory=list, repr=False)
    _used_dilemmas: list[int] = field(default_factory=list, repr=False)

    # Council dilemma pool (populated in __post_init__)
    _council_dilemmas: list[dict] = field(default_factory=list, repr=False)

    # HIGH-05: Quest identity serialization
    quest_slug: str = field(default="", repr=False)
    quest_name: str = field(default="", repr=False)
    special_mechanics: dict = field(default_factory=dict, repr=False)

    # MED-01: Per-instance morning events (quest-injectable)
    _morning_events: list[dict] = field(default_factory=list, repr=False)

    # Internal state
    _pending_allegiance: str | None = field(default=None, repr=False)
    _drifter_tax_active: bool = field(default=False, repr=False)  # WO-V100: Double Draw pending
    _pending_echo: bool = field(default=False, repr=False)  # WO-V108: Awaiting Echo response
    _pending_shift: int = field(default=0, repr=False)  # WO-V108: Sway shift to record in history
    _royal_decree_used: bool = field(default=False, repr=False)  # WO-V104: Once-per-march power
    _leaders_confidence_used: bool = field(default=False, repr=False)  # WO-V104: Once-per-march power
    _active_consequences: list[dict] = field(default_factory=list, repr=False)  # WO-V110: Tracked council outcomes
    _midday_encounters: list[dict] = field(default_factory=list, repr=False)  # WO-V109: Midday encounter pool
    _used_midday: list[int] = field(default_factory=list, repr=False)  # WO-V109: Used midday indices
    _safe_passage_used: bool = field(default=False, repr=False)  # WO-V109: Safe Passage bypass (sway -1)
    _mirror_choice: str = field(default="", repr=False)  # WO-V99: "hide" or "expose"
    _mirror_sin: str = field(default="", repr=False)  # WO-V99: What sin was witnessed

    # MED-06: Short rest per-day counter
    _short_rests_today: int = field(default=0, repr=False)

    # Council vote log (for Political Gravity tracking)
    vote_log: list[dict] = field(default_factory=list, repr=False)

    # Campaign context injection (WO 080 — Prologue Bridge)
    campaign_context: dict | None = field(default=None, repr=False)
    threat: str = ""
    region: str = ""
    goal: str = ""
    endings: dict = field(default_factory=dict, repr=False)

    # WO 088 — Narrative Link: AI bridge
    mimir: object | None = field(default=None, repr=False)

    # WO 088-V2 — Entity State Tracking (deterministic fact GPS)
    entities: dict[str, dict[str, object]] = field(default_factory=dict, repr=False)

    # WO-V9.5 — Narrative Loom integration
    _memory_shards: list = field(default_factory=list, repr=False)
    _manifest: object | None = field(default=None, repr=False)

    # Phase 4 — Lazy-init subsystems (not serialized as dataclass fields)
    _politics_engine: Optional[Any] = field(default=None, init=False, repr=False)
    _event_generator: Optional[Any] = field(default=None, init=False, repr=False)

    # WO-V69.0 — Day clock for world-simulation time tracking (not a dataclass init arg)
    _day_clock: Optional[Any] = field(default=None, init=False, repr=False)

    # Scene progression runner — optional, set via set_scene_runner() (not a dataclass init arg)
    _scene_runner: Optional[Any] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        """Load world data or fall back to hardcoded defaults."""

        # --- Campaign Context Injection (WO 080) ---
        ctx = self.campaign_context
        if ctx and isinstance(ctx, dict):
            self.patron = ctx.get('villain', "The High Inquisitor")
            self.leader = ctx.get('mentor', "Captain Vane")
            self.threat = ctx.get('threat', "The Inquisition")
            self.region = ctx.get('region', "The Borderlands")
            self.goal = f"Reach {self.region} before the {self.threat} strikes."
            self.endings = {
                "loyal": f"{self.patron} rewards your loyalty.",
                "rebel": f"You defect to the {self.threat}.",
                "chaos": f"The mission to {self.region} ends in ruin.",
            }

        ws = self.world_state

        if ws and isinstance(ws, dict):
            # ── Injected world ──
            self.terms = ws.get("terms", {
                "crown": "The Crown", "crew": "The Crew",
                "neutral": "The Drifter", "campfire": "Campfire",
                "world": "The Wilds",
            })
            self._prompts_crown = ws.get("prompts_crown", []) or list(PROMPTS_CROWN)
            self._prompts_crew = ws.get("prompts_crew", []) or list(PROMPTS_CREW)
            self._prompts_world = ws.get("prompts_world", []) or list(PROMPTS_WORLD)
            self._prompts_campfire = ws.get("prompts_campfire", []) or list(PROMPTS_CAMPFIRE)
            self._secret_witness = ws.get("secret_witness", "") or PROMPT_SECRET_WITNESS
            self._legacy_titles = ws.get("legacy_titles", {}) or LEGACY_TITLES

            patron_pool = ws.get("patrons", []) or list(PATRONS)
            leader_pool = ws.get("leaders", []) or list(LEADERS)
        else:
            # ── Default hardcoded world ──
            self.terms = {
                "crown": "The Crown", "crew": "The Crew",
                "neutral": "The Drifter", "campfire": "Campfire",
                "world": "The Wilds",
            }
            self._prompts_crown = list(PROMPTS_CROWN)
            self._prompts_crew = list(PROMPTS_CREW)
            self._prompts_world = list(PROMPTS_WORLD)
            self._prompts_campfire = list(PROMPTS_CAMPFIRE)
            self._secret_witness = PROMPT_SECRET_WITNESS
            self._legacy_titles = LEGACY_TITLES

            patron_pool = list(PATRONS)
            leader_pool = list(LEADERS)

        # Set patron/leader if not already provided
        if not self.patron:
            self.patron = random.choice(patron_pool)
        if not self.leader:
            self.leader = random.choice(leader_pool)

        # Accept arc_length + rest_config from world_state (WO-V23.0)
        if ws and isinstance(ws, dict):
            if "arc_length" in ws:
                self.arc_length = ws["arc_length"]
            if "rest_config" in ws and isinstance(ws["rest_config"], dict):
                self.rest_config.update(ws["rest_config"])

        # Council dilemmas — from world_state or module-level default
        if not self._council_dilemmas:
            if ws and isinstance(ws, dict) and ws.get("council_dilemmas"):
                self._council_dilemmas = list(ws["council_dilemmas"])
            else:
                self._council_dilemmas = list(COUNCIL_DILEMMAS)

        # HIGH-05: Quest identity from world_state
        if ws and isinstance(ws, dict):
            if "quest_slug" in ws:
                self.quest_slug = ws["quest_slug"]
            if "quest_name" in ws:
                self.quest_name = ws["quest_name"]
            if "special_mechanics" in ws and isinstance(ws["special_mechanics"], dict):
                self.special_mechanics = dict(ws["special_mechanics"])

        # MED-01: Morning events — from world_state or module-level default
        if not self._morning_events:
            if ws and isinstance(ws, dict) and ws.get("morning_events"):
                self._morning_events = list(ws["morning_events"])
            else:
                self._morning_events = list(MORNING_EVENTS)

        # WO-V109: Midday encounters — from world_state or default pool
        if not self._midday_encounters:
            if ws and isinstance(ws, dict) and ws.get("midday_encounters"):
                self._midday_encounters = list(ws["midday_encounters"])
            else:
                self._midday_encounters = list(MIDDAY_ENCOUNTERS)

        # WO-V69.0: Initialize DayClock aligned to Crown's day counter
        if _DAY_CLOCK_AVAILABLE:
            self._day_clock = DayClock(phase=TimeOfDay.MORNING, day=self.day)
        else:
            self._day_clock = None

        # WO-V133: Initialize solo player if no players provided
        if not self.players:
            # Share references so engine.dna IS player.dna — zero-copy sync
            ps = CrownPlayerState(name=_SOLO)
            ps.sway = self.sway
            ps.dna = self.dna  # Shared reference
            ps.history = self.history  # Shared reference
            ps._pending_allegiance = self._pending_allegiance
            ps._pending_echo = self._pending_echo
            ps._pending_shift = self._pending_shift
            ps._mirror_choice = self._mirror_choice
            ps._mirror_sin = self._mirror_sin
            ps._royal_decree_used = self._royal_decree_used
            ps._leaders_confidence_used = self._leaders_confidence_used
            ps._safe_passage_used = self._safe_passage_used
            self.players[_SOLO] = ps

    # ─────────────────────────────────────────────────────────────────────
    # PLAYER ACCESS (WO-V133)
    # ─────────────────────────────────────────────────────────────────────

    def _get_player(self, player_name: str = _SOLO) -> CrownPlayerState:
        """Get or create a player state by name.

        In solo mode (default), returns the _solo player.
        In multiplayer, returns the named player or creates a new one.
        """
        if player_name not in self.players:
            self.players[player_name] = CrownPlayerState(name=player_name)
        return self.players[player_name]

    def add_player(self, name: str) -> CrownPlayerState:
        """Register a new player for multiplayer sessions."""
        if name in self.players:
            return self.players[name]
        ps = CrownPlayerState(name=name)
        self.players[name] = ps
        return ps

    def get_all_players(self) -> list[CrownPlayerState]:
        """Return all player states (excluding _solo in multiplayer)."""
        if len(self.players) == 1 and _SOLO in self.players:
            return [self.players[_SOLO]]
        return [ps for name, ps in self.players.items() if name != _SOLO]

    def is_multiplayer(self) -> bool:
        """True if more than one real player is registered."""
        real = [n for n in self.players if n != _SOLO]
        return len(real) > 1

    def _sync_solo_to_legacy(self) -> None:
        """Sync the _solo player's state back to legacy engine fields.

        dna and history are shared references (mutations auto-sync).
        Scalar fields (sway, booleans) need explicit sync.
        """
        if _SOLO in self.players:
            ps = self.players[_SOLO]
            self.sway = ps.sway
            # dna and history are shared references — no copy needed
            self._pending_allegiance = ps._pending_allegiance
            self._pending_echo = ps._pending_echo
            self._pending_shift = ps._pending_shift
            self._mirror_choice = ps._mirror_choice
            self._mirror_sin = ps._mirror_sin
            self._royal_decree_used = ps._royal_decree_used
            self._leaders_confidence_used = ps._leaders_confidence_used
            self._safe_passage_used = ps._safe_passage_used

    def _sync_legacy_to_solo(self) -> None:
        """Sync legacy scalar fields back to the _solo player.

        Called after methods that modify engine.sway directly.
        """
        if _SOLO in self.players:
            ps = self.players[_SOLO]
            ps.sway = self.sway
            ps._pending_allegiance = self._pending_allegiance
            ps._pending_echo = self._pending_echo
            ps._pending_shift = self._pending_shift
            ps._mirror_choice = self._mirror_choice
            ps._mirror_sin = self._mirror_sin
            ps._royal_decree_used = self._royal_decree_used
            ps._leaders_confidence_used = self._leaders_confidence_used
            ps._safe_passage_used = self._safe_passage_used

    # ─────────────────────────────────────────────────────────────────────
    # MEMORY SHARD HELPERS (WO-V10.0)
    # ─────────────────────────────────────────────────────────────────────

    def _add_shard(self, content: str, shard_type: str, source: str = "crown") -> None:
        """Create a MemoryShard and append to _memory_shards."""
        if not MEMORY_SHARDS_AVAILABLE:
            return
        shard = MemoryShard(
            shard_type=ShardType(shard_type),
            content=content,
            source=source,
        )
        self._memory_shards.append(shard)

    def setup(self) -> None:
        """Initialize the engine and seed narrative memory.

        Call after construction to populate the initial MASTER shard
        with campaign context.  Also creates the SessionManifest if one
        has not already been restored from a save.
        """
        world_summary = ""
        if self.world_state and isinstance(self.world_state, dict):
            world_summary = f"World: {self.world_state.get('terms', {}).get('world', 'Unknown')}"
        context = (
            f"Campaign: {self.patron} vs {self.leader}. "
            f"Region: {self.region or 'The Borderlands'}. "
            f"{world_summary}"
        ).strip()
        self._add_shard(context, "MASTER", "system")

        # WO-V68.0: Ensure a SessionManifest exists for narrative caching
        if NARRATIVE_LOOM_AVAILABLE and self._manifest is None:
            session_id = f"crown_{int(time.time() * 1000)}"
            self._manifest = SessionManifest(session_id=session_id)

    @staticmethod
    def _mimir_adapter(prompt: str, context: str) -> str:
        """Sync adapter for narrative loom's mimir_fn parameter."""
        try:
            from codex.integrations.mimir import query_mimir
            return query_mimir(prompt, context)
        except Exception:
            return ""

    async def _consult_mimir(self, prompt: str, fallback: str) -> str:
        """Ask Mimir to generate narrative text, falling back to static string.

        If self.mimir exists and has an invoke_model method (Architect),
        call it asynchronously. On any failure, return the fallback.
        """
        if self.mimir is None:
            return fallback

        # Use narrative loom for coherent context if available
        if NARRATIVE_LOOM_AVAILABLE and self._memory_shards:
            # Lazy-create manifest for caching
            if not self._manifest:
                session_id = f"crown_{id(self)}"
                self._manifest = SessionManifest(session_id=session_id)
            context = synthesize_narrative(
                prompt, self._memory_shards,
                mimir_fn=self._mimir_adapter, manifest=self._manifest,
            )
            if context:
                prompt = f"SYNTHESIZED CONTEXT:\n{context}\n\nQUERY: {prompt}"

        # WO-V33.0: RAG lore injection for grounded narrative
        try:
            from codex.core.services.rag_service import get_rag_service
            rag = get_rag_service()
            rag_result = rag.search(prompt[:200], "dnd5e", k=2, token_budget=300)
            if rag_result:
                rag_block = rag.format_context(rag_result, header="LORE:")
                prompt = f"{rag_block}\n\n{prompt}"
        except Exception:
            pass

        try:
            response = await self.mimir.invoke_model(
                prompt,
                system_prompt=(
                    "You are the NARRATOR. You are NOT a character. "
                    "Write in Third-Person Omniscient. "
                    "Never refer to 'Mimir' or 'I'. "
                    "Focus purely on describing the world and consequences. "
                    "Write vivid, concise prose (2-4 sentences). No meta-commentary."
                )
            )
            text = getattr(response, 'content', str(response)).strip()
            if text:
                # WO-V10.0: ECHO shard for Mimir response trace-back
                self._add_shard(text[:200], "ECHO", "mimir")
                return text
            return fallback
        except Exception:
            return fallback

    def _consult_mimir_sync(self, prompt: str, fallback: str) -> str:
        """Synchronous wrapper for _consult_mimir (used in non-async contexts)."""
        if self.mimir is None:
            return fallback
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context — can't block; return fallback
                return fallback
            return loop.run_until_complete(self._consult_mimir(prompt, fallback))
        except RuntimeError:
            return fallback

    def _get_unique_prompt(self, pool: list[str], used: list[int]) -> str:
        """Get a prompt that hasn't been used yet. Resets if all used."""
        if not pool:
            return "The road stretches ahead in silence."
        available = [i for i in range(len(pool)) if i not in used]
        if not available:
            used.clear()
            available = list(range(len(pool)))
        idx = random.choice(available)
        used.append(idx)
        return pool[idx]

    # ─────────────────────────────────────────────────────────────────────
    # STATUS & TIER
    def get_mood_context(self) -> dict:
        """Return current mechanical state as narrative mood modifiers (WO-V61.0)."""
        sway = getattr(self, 'sway', 0)
        day = getattr(self, 'day', 1)
        if abs(sway) >= 3:
            condition = "committed"
            words = ["fervent", "decisive", "zealous"]
        elif sway == 0 and day > 3:
            condition = "adrift"
            words = ["uncertain", "wary", "uncommitted"]
        else:
            condition = "healthy"
            words = []
        tension = min(1.0, day / 7)
        return {
            "tension": round(tension, 2),
            "tone_words": words,
            "party_condition": condition,
            "system_specific": {"sway": sway, "day": day},
        }

    # ─────────────────────────────────────────────────────────────────────

    def get_status(self) -> str:
        """Returns a formatted string describing the current Sway Tier."""
        tier = SWAY_TIERS.get(self.sway, SWAY_TIERS[0])
        return (
            f"Day {self.day}/{self.arc_length} | Sway: {self.sway:+d} | "
            f"Status: {tier['name']} | Power: {tier['power']}"
        )

    def get_tier(self) -> dict[str, str]:
        """Returns the current Sway Tier data."""
        return SWAY_TIERS.get(self.sway, SWAY_TIERS[0])

    def get_alignment(self) -> str:
        """Determine alignment based on final sway. Uses dynamic terms."""
        if self.sway > 0:
            return "CREW"
        elif self.sway < 0:
            return "CROWN"
        else:
            return "DRIFTER"

    def get_alignment_display(self) -> str:
        """Get the display name for current alignment using world terms."""
        alignment = self.get_alignment()
        if alignment == "CROWN":
            return self.terms.get("crown", "The Crown")
        elif alignment == "CREW":
            return self.terms.get("crew", "The Crew")
        else:
            return self.terms.get("neutral", "The Drifter")

    def get_sway_color(self) -> int:
        """
        Get hex color value based on current sway.
        For Discord embed sidebar coloring.
        """
        if self.sway < 0:
            return 0x00FFFF
        elif self.sway > 0:
            return 0xFF00FF
        else:
            return 0xFFD700

    def get_sway_visual(self) -> str:
        """
        Get a simple visual sway bar string.

        Returns:
            String like: 👑═══◆═══🏴
        """
        bar_chars = ['═'] * 7
        marker_idx = self.sway + 3
        marker_idx = max(0, min(6, marker_idx))
        bar_chars[marker_idx] = '◆'
        return f"👑{''.join(bar_chars)}🏴"

    def get_dominant_tag(self) -> str:
        """Get the tag with the highest DNA value."""
        if not any(self.dna.values()):
            return "SILENCE"
        return max(self.dna, key=lambda k: self.dna[k])

    # ─────────────────────────────────────────────────────────────────────
    # SWAY POWER SYSTEM (WO-V104)
    # ─────────────────────────────────────────────────────────────────────

    def has_power(self, power_id: str) -> bool:
        """Check if the player's current sway grants a specific power."""
        tier = self.get_tier()
        return tier.get("grants") == power_id

    def get_active_power(self) -> dict:
        """Return the player's current active power from their sway tier."""
        return self.get_tier()

    def get_available_powers(self) -> list[str]:
        """Return all power IDs the current sway level qualifies for.

        Crown powers stack downward: sway -3 also has -2 and -1 powers.
        Crew powers stack upward: sway +3 also has +2 and +1 powers.
        """
        powers = []
        for sway_val, tier in SWAY_TIERS.items():
            if sway_val < 0 and self.sway <= sway_val:
                powers.append(tier["grants"])
            elif sway_val > 0 and self.sway >= sway_val:
                powers.append(tier["grants"])
            elif sway_val == 0 and self.sway == 0:
                powers.append(tier["grants"])
        return powers

    def activate_royal_decree(self) -> str:
        """WO-V104: Crown Agent (-3) — Force council to Crown outcome. Once per march."""
        if not self.has_power("royal_decree"):
            return "You lack the authority. Royal Decree requires Crown Agent status (sway -3)."
        if getattr(self, '_royal_decree_used', False):
            return "Royal Decree has already been invoked this march."
        self._royal_decree_used = True
        self._add_shard("Invoked Royal Decree — forced council outcome to Crown", "ANCHOR")
        crown_term = self.terms.get("crown", "The Crown").upper()
        return (
            f"ROYAL DECREE INVOKED.\n"
            f"The {crown_term}'s will overrides all dissent. "
            f"The council bows — but the Crew will remember this."
        )

    def activate_leaders_confidence(self) -> str:
        """WO-V104: Crew Loyal (+3) — Leader reveals secret agenda. Once per march."""
        if not self.has_power("leaders_confidence"):
            return "The Leader doesn't trust you enough. Requires Crew Loyal status (sway +3)."
        if getattr(self, '_leaders_confidence_used', False):
            return "The Leader has already shared their secret this march."
        self._leaders_confidence_used = True

        leader = getattr(self, 'leader', None)
        if isinstance(leader, dict):
            agenda = leader.get("secret_agenda", "a hidden purpose they won't share with anyone else")
            betrayal = leader.get("betrayal_trigger", "something that could turn them against everything")
            name = leader.get("name", "The Leader")
        else:
            agenda = "a hidden purpose they won't share with anyone else"
            betrayal = "something that could turn them against everything"
            name = self.terms.get("crew", "The Leader")

        self._add_shard(f"The Leader revealed their secret agenda: {agenda[:60]}", "ANCHOR")
        return (
            f"THE LEADER'S CONFIDENCE\n"
            f"{name} draws you aside. In a low voice:\n\n"
            f'"My real purpose? {agenda}"\n\n'
            f"You sense a vulnerability — {betrayal}."
        )

    def get_gated_morning_choices(self, event: dict) -> list[dict]:
        """WO-V104: Return morning choices with sway-gated bonus options.

        At sway <= -2: adds a Crown-only choice (Imperial Intelligence).
        At sway >= +2: adds a Crew insider choice (Inner Circle).
        At sway == 0: adds a unique broker choice (Whirlpool).
        """
        choices = list(event.get("choices", []))

        if self.sway <= -2:
            choices.append({
                "text": "[Crown Intel] Your contacts share a detail others missed.",
                "tag": "GUILE", "sway_effect": -1, "gated": "imperial_intelligence",
            })

        if self.sway >= 2:
            choices.append({
                "text": "[Crew Insider] The Leader's people slip you a warning.",
                "tag": "HEARTH", "sway_effect": 1, "gated": "inner_circle",
            })

        if self.sway == 0:
            choices.append({
                "text": "[Broker] Play both sides — you're the only one who can.",
                "tag": "GUILE", "sway_effect": 0, "gated": "whirlpool",
            })

        return choices

    def get_gated_council_choices(self, dilemma: dict) -> list[dict]:
        """WO-V104: Return council choices with sway-gated bonus options.

        At sway >= +2: the Crew Leader whispers a hidden third option.
        At sway == -3: Royal Decree option available (if not yet used).
        """
        crown_text = dilemma.get("crown", "Side with the Crown.")
        crew_text = dilemma.get("crew", "Side with the Crew.")
        choices = [
            {"text": crown_text, "side": "crown"},
            {"text": crew_text, "side": "crew"},
        ]

        if self.sway >= 2:
            leader_name = "The Leader"
            if isinstance(getattr(self, 'leader', None), dict):
                leader_name = self.leader.get("name", "The Leader")
            choices.append({
                "text": f"[Inner Circle] {leader_name} whispers a third path...",
                "side": "crew", "tag_bonus": "GUILE", "gated": "inner_circle",
            })

        if self.sway == -3 and not getattr(self, '_royal_decree_used', False):
            choices.append({
                "text": "[Royal Decree] Invoke the Crown's absolute authority.",
                "side": "crown", "force_outcome": True, "gated": "royal_decree",
            })

        return choices

    def get_affinity_display(self) -> str:
        """Render Sway as a visual progress bar (WO 088-V2).

        Range: -3 (Crown) to +3 (Crew), mapped onto a 10-segment bar.
        """
        # Normalize sway (-3..+3) to bar position (0..10)
        normalized = max(-3, min(3, self.sway)) + 3  # 0 to 6
        # Scale to 10 segments: round(normalized * 10 / 6)
        filled = round(normalized * 10 / 6)
        bar = "█" * filled + "░" * (10 - filled)

        if self.sway < 0:
            status = f"👑 CROWN FAVOR ({self.sway})"
        elif self.sway > 0:
            status = f"🏴 CREW LOYALTY (+{self.sway})"
        else:
            status = "⚖️ BALANCED"

        return f"[{bar}] {status}"

    # ─────────────────────────────────────────────────────────────────────
    # ENTITY STATE TRACKING (WO 088-V2 — Deterministic Fact GPS)
    # ─────────────────────────────────────────────────────────────────────

    def update_entity(self, name: str, key: str, value: object):
        """Update a specific fact about an entity (e.g., Dragon -> Location)."""
        if name not in self.entities:
            self.entities[name] = {}
        self.entities[name][key] = value

    def get_entity_state(self, name: str) -> str:
        """Return a formatted string of known facts about an entity."""
        if name not in self.entities:
            return "Unknown."
        return ", ".join(f"{k}: {v}" for k, v in self.entities[name].items())

    # ─────────────────────────────────────────────────────────────────────
    # NARRATIVE LOOM — Diagnostic Trace (WO-V9.5)
    # ─────────────────────────────────────────────────────────────────────

    def trace_fact(self, fact: str) -> str:
        """Trace a stated fact back through narrative shard layers.

        Returns a formatted string showing which shards support or
        contradict the claim, ordered by authority.
        """
        if not NARRATIVE_LOOM_AVAILABLE:
            return "Narrative Loom not available."
        if not self._memory_shards:
            return "No memory shards loaded — trace unavailable."

        results = diagnostic_trace(fact, self._memory_shards)
        if not results:
            return f"No shards mention '{fact}'."

        lines = [f"Trace: \"{fact}\"", ""]
        for r in results:
            lines.append(
                f"  [{r['type']}] ({r['source']}) "
                f"relevance={r['relevance']}"
            )
            if r.get("excerpt"):
                lines.append(f"    {r['excerpt']}")
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────
    # PHASE 4 — LAZY SUBSYSTEM ACCESSORS
    # ─────────────────────────────────────────────────────────────────────

    def _get_politics_engine(self):
        """Lazily initialise and return the PoliticalGravityEngine."""
        if self._politics_engine is None:
            from codex.games.crown.politics import PoliticalGravityEngine
            self._politics_engine = PoliticalGravityEngine()
        return self._politics_engine

    def _get_event_generator(self):
        """Lazily initialise and return the EventGenerator."""
        if self._event_generator is None:
            from codex.games.crown.events import EventGenerator
            self._event_generator = EventGenerator()
        return self._event_generator

    # ─────────────────────────────────────────────────────────────────────
    # PHASE 4 — HANDLE COMMAND (Crown's first command dispatcher)
    # ─────────────────────────────────────────────────────────────────────

    def handle_command(self, cmd: str, **kwargs) -> str:
        """
        Command dispatcher for dashboard and bridge integration.

        Supported commands:
            trace_fact          — Trace a fact through narrative shards
            faction_status      — Show all faction influences
            shift_influence     — Modify a faction's influence
            form_alliance       — Form alliance between two factions
            break_alliance      — Break an alliance between two factions
            council_vote        — Simulate a weighted council vote
            power_balance       — Show current power balance
            generate_event      — Generate a weighted political event
            event_chain         — Advance or start an event chain
            political_landscape — Full political summary
            status              — Show current sway/day status

        Args:
            cmd: Command name string.
            **kwargs: Command-specific keyword arguments.

        Returns:
            Human-readable result string.
        """
        cmd = cmd.lower().replace("-", "_")
        if cmd == "trace_fact":
            return self.trace_fact(kwargs.get("fact", ""))

        handler = getattr(self, f"_cmd_{cmd}", None)
        if handler is not None:
            return handler(**kwargs)

        return f"Unknown Crown command: {cmd}"

    def _cmd_faction_status(self, **kwargs) -> str:
        """Show all faction influences, sorted by influence descending."""
        politics = self._get_politics_engine()
        statuses = politics.influence_tracker.get_all_statuses()
        lines = ["Faction Status:"]
        for s in statuses:
            territory = ", ".join(s.get("territory", [])[:2])
            suffix = f" (and {len(s.get('territory', [])) - 2} more)" if len(s.get("territory", [])) > 2 else ""
            lines.append(
                f"  {s['name']}: influence {s['influence']}/10  "
                f"territory: {territory}{suffix}"
            )
        dominant = politics.influence_tracker.get_dominant_faction()
        lines.append(f"\nDominant: {dominant}")
        return "\n".join(lines)

    def _cmd_shift_influence(self, faction: str = "", amount: int = 1, **kwargs) -> str:
        """Modify a faction's influence."""
        if not faction:
            return "shift_influence requires 'faction' kwarg"
        politics = self._get_politics_engine()
        result = politics.influence_tracker.shift_influence(faction, amount)
        if "error" in result:
            return result["error"]
        return (
            f"{faction}: influence {result['old_influence']} → {result['new_influence']} "
            f"(delta {result['delta']:+d})"
            + (" [capped]" if result["capped"] else "")
        )

    def _cmd_form_alliance(self, faction_a: str = "", faction_b: str = "", **kwargs) -> str:
        """Form an alliance between two factions."""
        if not faction_a or not faction_b:
            return "form_alliance requires 'faction_a' and 'faction_b' kwargs"
        politics = self._get_politics_engine()
        result = politics.alliance_system.form_alliance(faction_a, faction_b)
        return (
            f"Alliance formed: {faction_a} + {faction_b}  "
            f"(was: {result['old_status']})"
        )

    def _cmd_break_alliance(
        self, faction_a: str = "", faction_b: str = "", reason: str = "", **kwargs
    ) -> str:
        """Break an existing alliance."""
        if not faction_a or not faction_b:
            return "break_alliance requires 'faction_a' and 'faction_b' kwargs"
        politics = self._get_politics_engine()
        result = politics.alliance_system.break_alliance(faction_a, faction_b, reason)
        return (
            f"Alliance broken: {faction_a} vs {faction_b}  "
            f"(was: {result['old_status']}, now: {result['new_status']})"
        )

    def _cmd_council_vote(
        self, proposal: str = "", factions_voting: Optional[Dict[str, str]] = None, **kwargs
    ) -> str:
        """Simulate a weighted council vote."""
        if not proposal:
            proposal = "Unnamed council matter"
        if not factions_voting:
            return "council_vote requires 'factions_voting' dict (faction_name → 'crown'|'crew')"
        politics = self._get_politics_engine()
        result = politics.council_vote(
            proposal=proposal,
            factions_voting=factions_voting,
            sway_modifier=self.sway,
        )
        return (
            f"Council Vote: {proposal}\n"
            f"  Crown weight: {result['crown_weight']}  "
            f"Crew weight: {result['crew_weight']}\n"
            f"  Winner: {result['winner'].upper()}  (margin: {result['margin']})\n"
            f"  {result['flavor']}"
        )

    def _cmd_power_balance(self, **kwargs) -> str:
        """Show current political power balance."""
        politics = self._get_politics_engine()
        gravity = politics.calculate_gravity()
        balance = gravity["power_balance"]
        label = gravity["balance_label"]
        dominant = gravity["dominant_faction"]
        alliances = gravity["alliance_count"]
        rivalries = gravity["rivalry_count"]
        bar_filled = int((balance + 1.0) * 5)  # 0-10
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        return (
            f"Power Balance: [{bar}] {balance:+.2f} ({label})\n"
            f"  Dominant faction: {dominant}\n"
            f"  Active alliances: {alliances}  Active rivalries: {rivalries}"
        )

    def _cmd_generate_event(self, **kwargs) -> str:
        """Generate a weighted political event based on current sway and day."""
        gen = self._get_event_generator()
        event = gen.generate_event(sway=self.sway, day=self.day)
        tag = event.get("tag", "")
        bias = event.get("sway_bias", "neutral")
        return (
            f"[{bias.upper()} / {tag}]\n"
            f"{event['text']}"
        )

    def _cmd_event_chain(self, chain_id: str = "", **kwargs) -> str:
        """Trigger or advance an event chain."""
        if not chain_id:
            return "event_chain requires 'chain_id' kwarg"
        gen = self._get_event_generator()
        event = gen.generate_chain_event(chain_id)
        if event is None:
            if gen.is_chain_complete(chain_id):
                return f"Chain '{chain_id}' is complete."
            return f"Unknown chain: '{chain_id}'"
        tag = event.get("tag", "")
        bias = event.get("sway_bias", "neutral")
        return (
            f"Chain [{chain_id}] — [{bias.upper()} / {tag}]\n"
            f"{event['text']}"
        )

    def _cmd_political_landscape(self, **kwargs) -> str:
        """Full political landscape summary."""
        politics = self._get_politics_engine()
        gravity = politics.calculate_gravity()
        lines = [
            f"=== Political Landscape — Day {self.day}/{self.arc_length} ===",
            f"Power Balance: {gravity['power_balance']:+.2f} ({gravity['balance_label']})",
            f"Dominant Faction: {gravity['dominant_faction']}",
            f"Alliances: {gravity['alliance_count']}  Rivalries: {gravity['rivalry_count']}",
            "",
            "Faction Influence:",
        ]
        for summary in gravity["faction_summary"]:
            lines.append(
                f"  {summary['name']:25}  {summary['influence']:2}/10  "
                f"({summary['territory_count']} districts)"
            )
        return "\n".join(lines)

    def _cmd_status(self, **kwargs) -> str:
        """Show current day, sway, and alignment."""
        return self.get_status()

    # ─────────────────────────────────────────────────────────────────────
    # ALLEGIANCE & PROMPTS (dynamic pool routing)
    # ─────────────────────────────────────────────────────────────────────

    def declare_allegiance(self, side: Literal["crown", "crew"], tag: str | None = None) -> str:
        """
        Declare allegiance BEFORE seeing the prompt (Blind Allegiance).

        Phase 1 of the two-step allegiance flow:
          1. declare_allegiance() — shifts sway, records side
          2. resolve_echo() — player picks HOW they responded → assigns DNA tag

        If *tag* is provided, the Echo step is skipped and the tag is
        assigned immediately (backward compat / bot shortcut).
        If *tag* is None, sway shifts but no DNA tag is assigned yet —
        call get_echo_responses() + resolve_echo() to complete the flow.
        """
        side = side.lower()
        side_term = self.terms.get(side, side.upper())

        if side == "crown":
            self.sway -= 1
            shift = -1
        elif side == "crew":
            self.sway += 1
            shift = 1
        else:
            raise ValueError(f"Invalid side: {side}. Must be 'crown' or 'crew'.")

        self.sway = max(-3, min(3, self.sway))
        self._pending_allegiance = side

        if tag is not None:
            # Immediate tag assignment (backward compat / bot shortcut)
            tag = tag.upper()
            if tag not in TAGS:
                raise ValueError(f"Invalid tag: {tag}. Must be one of {TAGS}.")
            self.dna[tag] += 1
            self._pending_echo = False
            self.history.append({
                "day": self.day,
                "choice": side,
                "tag": tag,
                "sway_shift": shift,
                "sway_after": self.sway
            })
            self._add_shard(
                f"Day {self.day}: Declared allegiance to {side_term} [{tag}]. Sway: {self.sway:+d}",
                "ANCHOR",
            )
            tier = self.get_tier()
            return (
                f"Allegiance declared: {side_term.upper()} [{tag}]. "
                f"Sway shifts to {self.sway:+d} ({tier['name']})."
            )
        else:
            # Deferred tag — Echo step required
            self._pending_echo = True
            self._pending_shift = shift
            self._add_shard(
                f"Day {self.day}: Declared allegiance to {side_term}. Sway: {self.sway:+d}. Awaiting Echo.",
                "CHRONICLE",
            )
            tier = self.get_tier()
            return (
                f"Allegiance declared: {side_term.upper()}. "
                f"Sway shifts to {self.sway:+d} ({tier['name']}). "
                f"Now — how did you carry that choice?"
            )

    def get_echo_responses(self) -> list[dict]:
        """WO-V108: Return the 5 Echo response options for the current allegiance.

        Each response maps to a DNA tag. The player picks one to complete
        the allegiance flow. Returns a list of dicts with keys:
        tag, label, desc.
        """
        responses = []
        for tag_name in TAGS:
            echo = ECHO_RESPONSES.get(tag_name, {})
            responses.append({
                "tag": tag_name,
                "label": echo.get("label", tag_name),
                "desc": echo.get("desc", ""),
            })
        return responses

    def get_echo_frame(self) -> str:
        """WO-V108: Return the Echo framing text for the current allegiance."""
        side = self._pending_allegiance or "crew"
        return ECHO_FRAME.get(side, "How did you respond?")

    def resolve_echo(self, tag: str) -> str:
        """WO-V108: Complete the allegiance flow by assigning the player-chosen DNA tag.

        Args:
            tag: The DNA tag chosen by the player (BLOOD, GUILE, HEARTH, SILENCE, DEFIANCE).

        Returns:
            Narrative confirmation string.
        """
        tag = tag.upper()
        if tag not in TAGS:
            raise ValueError(f"Invalid tag: {tag}. Must be one of {TAGS}.")

        side = self._pending_allegiance or "crew"
        side_term = self.terms.get(side, side.upper())
        shift = getattr(self, '_pending_shift', 0)

        self.dna[tag] += 1
        self._pending_echo = False

        self.history.append({
            "day": self.day,
            "choice": side,
            "tag": tag,
            "sway_shift": shift,
            "sway_after": self.sway
        })

        echo_label = ECHO_RESPONSES.get(tag, {}).get("label", tag)
        echo_desc = ECHO_RESPONSES.get(tag, {}).get("desc", "")

        self._add_shard(
            f"Day {self.day}: Echo — responded to {side_term} with [{tag}] ({echo_label}). Sway: {self.sway:+d}",
            "ANCHOR",
        )

        return (
            f"[{tag}] {echo_label}. {echo_desc}\n"
            f"Your DNA shifts. {tag} marks this memory."
        )

    def get_prompt(self, side: Literal["crown", "crew"] | None = None) -> str:
        """Get a unique prompt for the declared side (from dynamic pool).

        If the Drifter's Tax is active (sway was 0 at sunset), returns
        a DOUBLE DRAW: both a Crown and a Crew prompt that must be
        justified simultaneously. The tax is consumed after drawing.
        """
        if side is None:
            side = self._pending_allegiance
        if side is None:
            return "ERROR: No allegiance declared. Call declare_allegiance() first."

        side = side.lower()

        # WO-V100: Drifter's Tax — Double Draw
        if self._drifter_tax_active:
            crown_prompt = self._get_unique_prompt(self._prompts_crown, self._used_crown)
            crew_prompt = self._get_unique_prompt(self._prompts_crew, self._used_crew)
            neutral_term = self.terms.get("neutral", "DRIFTER")
            self._drifter_tax_active = False  # Consumed
            return (
                f"═══ {neutral_term.upper()}'S TAX: DOUBLE DRAW ═══\n\n"
                f"You walk the line between worlds. Justify BOTH:\n\n"
                f"▸ {self.terms.get('crown', 'CROWN').upper()} PROMPT:\n"
                f"{crown_prompt}\n\n"
                f"▸ {self.terms.get('crew', 'CREW').upper()} PROMPT:\n"
                f"{crew_prompt}\n\n"
                f"Your answer must reconcile these opposing demands. "
                f"Both factions are watching. Neither trusts a neutral."
            )

        if side == "crown":
            return self._get_unique_prompt(self._prompts_crown, self._used_crown)
        elif side == "crew":
            return self._get_unique_prompt(self._prompts_crew, self._used_crew)
        else:
            return f"ERROR: Unknown side '{side}'."

    async def get_dilemma_ai(self, side: Literal["crown", "crew"] | None = None) -> str:
        """AI-enhanced dilemma. Falls back to static pool."""
        fallback = self.get_prompt(side)
        resolved_side = side or self._pending_allegiance or "crew"
        if resolved_side == "crown":
            prompt = (
                f"Generate a moral dilemma where {self.patron} (representing Order and authority) "
                f"tempts the player to betray {self.leader} and the Crew. "
                f"Day {self.day}/{self.arc_length}, sway is {self.sway:+d}. 2-4 sentences, second person."
            )
        else:
            prompt = (
                f"Generate a moral dilemma where {self.leader} (representing Freedom and loyalty) "
                f"asks the player to make a sacrifice for the Crew against {self.patron}'s authority. "
                f"Day {self.day}/{self.arc_length}, sway is {self.sway:+d}. 2-4 sentences, second person."
            )
        return await self._consult_mimir(prompt, fallback)

    def get_world_prompt(self) -> str:
        """Get a unique World/Environment prompt (from dynamic pool)."""
        return self._get_unique_prompt(self._prompts_world, self._used_world)

    async def get_world_prompt_ai(self) -> str:
        """AI-enhanced world prompt. Falls back to static pool."""
        fallback = self.get_world_prompt()
        region = self.region or "the borderlands"
        threat = self.threat or "an unnamed darkness"
        prompt = (
            f"Describe the specific terrain and weather of {region} on Day {self.day} of {self.arc_length}. "
            f"The threat is {threat}. The party is weary and desperate. "
            f"End by describing a specific obstacle the party must traverse. "
            f"2-4 sentences, dark-fantasy tone."
        )
        return await self._consult_mimir(prompt, fallback)

    def get_campfire_prompt(self) -> str:
        """Get a unique Campfire prompt (from dynamic pool). Unavailable on Breach day."""
        if self.is_breach_day():
            campfire_term = self.terms.get("campfire", "Campfire")
            return f"No {campfire_term.lower()} tonight. The Breach has broken the silence."
        return self._get_unique_prompt(self._prompts_campfire, self._used_campfire)

    def get_secret_witness(self) -> str:
        """Get the Day 3 Secret Witness event prompt.

        Legacy method — returns the static witness prompt.
        Prefer get_mirror_break() for the full sin mechanic.
        """
        return self._secret_witness

    def get_mirror_break(self) -> dict:
        """WO-V99: Generate the Day 3 Mirror Break scene.

        The player's dominant DNA tag determines what sin they witness
        the Crew Leader committing. Returns a dict with:
        - sin: the sin type name
        - witness: the narrative text (with Leader name substituted)
        - choices: hide vs expose options with tag/sway effects

        Only meaningful on breach day — call is_breach_day() first.
        """
        dominant = self.get_dominant_tag()
        sin_data = MIRROR_SINS.get(dominant, MIRROR_SINS["SILENCE"])

        leader_name = self.leader
        if isinstance(leader_name, dict):
            leader_name = leader_name.get("name", "The Leader")

        witness_text = sin_data["witness"].format(leader=leader_name)

        return {
            "sin": sin_data["sin"],
            "dominant_tag": dominant,
            "witness": witness_text,
            "choices": [
                {
                    "text": f"Stay silent. Hide what you saw. The {self.terms.get('crew', 'Crew')} must not fracture.",
                    "action": "hide",
                    "tag": "SILENCE",
                    "sway_effect": 1,
                    "narrative": (
                        f"You slip back to your bedroll. The secret coils inside you like a stone "
                        f"in your gut. {leader_name} meets your eyes in the morning. "
                        f"You wonder if they know."
                    ),
                },
                {
                    "text": f"Expose the sin. The {self.terms.get('crown', 'Crown')} and the {self.terms.get('crew', 'Crew')} both deserve the truth.",
                    "action": "expose",
                    "tag": "DEFIANCE",
                    "sway_effect": -1,
                    "narrative": (
                        f"You step into the firelight. {leader_name} turns. The camp goes silent.\n\n"
                        f"'I saw what you did,' you say. The words land like stones in still water. "
                        f"Nothing will be the same after this."
                    ),
                },
            ],
        }

    def resolve_mirror_choice(self, choice_index: int) -> str:
        """WO-V99: Resolve the Mirror Break hide/expose choice.

        Args:
            choice_index: 0 = hide (SILENCE, +1 crew), 1 = expose (DEFIANCE, -1 crown)

        Returns:
            Narrative result with tag and sway feedback.
        """
        mirror = self.get_mirror_break()
        choices = mirror["choices"]
        if choice_index < 0 or choice_index >= len(choices):
            choice_index = 0

        choice = choices[choice_index]
        tag = choice["tag"]
        sway_effect = choice["sway_effect"]
        action = choice["action"]

        # Apply tag
        self.dna[tag] += 1

        # Apply sway
        self.sway += sway_effect
        self.sway = max(-3, min(3, self.sway))

        # Track complicity
        self._mirror_choice = action
        self._mirror_sin = mirror["sin"]

        # ANCHOR shard — this is a defining moment
        self._add_shard(
            f"Day {self.day} THE MIRROR: Witnessed {mirror['sin']}. "
            f"Chose to {action}. [{tag}] Sway {sway_effect:+d}",
            "ANCHOR",
        )

        tier = self.get_tier()
        narrative = choice["narrative"]
        direction = "toward the Crown" if sway_effect < 0 else "toward the Crew"

        return (
            f"{narrative}\n\n"
            f"[{tag}] — {mirror['sin']}: {'Hidden' if action == 'hide' else 'Exposed'}.\n"
            f"Sway shifts {direction}. Now: {self.sway:+d} ({tier['name']})."
        )

    def get_morning_event(self) -> dict:
        """Get a sway-relevant morning road event (WO-V14.0, V107.0).

        Day 1 returns neutral events to set the scene.
        Days 2+ return biased events to sway the allegiance choice.
        Avoids repeats using the same pattern as _get_unique_prompt.
        Uses self._morning_events (quest-injectable, WO-V25.0).

        WO-V107: Events now include a ``choices`` array. If the source
        event lacks choices (legacy module data), generic choices are
        auto-generated from the event's bias and tag.

        Returns:
            dict with keys: text, bias, tag, choices (list of dicts
            with text, tag, sway_effect).
        """
        pool = self._morning_events
        # WO-V110: Check if last night's council consequence biases today's morning
        consequence_bias = self.get_consequence_morning_bias()

        if self.day == 1:
            # Day 1: only neutral events
            neutral = [i for i, e in enumerate(pool) if e["bias"] == "neutral"]
            available = [i for i in neutral if i not in self._used_morning]
            if not available:
                self._used_morning = [x for x in self._used_morning if x not in neutral]
                available = neutral
        elif consequence_bias and consequence_bias != "neutral":
            # Days 2+: prefer events matching last night's consequence bias
            biased = [i for i, e in enumerate(pool)
                      if e["bias"] == consequence_bias and i not in self._used_morning]
            if biased:
                available = biased
            else:
                available = [i for i in range(len(pool)) if i not in self._used_morning]
                if not available:
                    self._used_morning.clear()
                    available = list(range(len(pool)))
        else:
            # Days 2+: any event not yet used
            available = [i for i in range(len(pool)) if i not in self._used_morning]
            if not available:
                self._used_morning.clear()
                available = list(range(len(pool)))

        idx = random.choice(available)
        self._used_morning.append(idx)
        event = pool[idx]

        # WO-V107: Ensure choices exist — auto-generate for legacy events
        if "choices" not in event or not event["choices"]:
            event = dict(event)  # Don't mutate the pool
            event["choices"] = self._generate_morning_choices(event)

        return event

    @staticmethod
    def _generate_morning_choices(event: dict) -> list[dict]:
        """WO-V107: Auto-generate choices for a morning event without them.

        Produces 3 generic choices based on the event's bias:
        - One aligned with Crown (sway -1)
        - One aligned with Crew (sway +1)
        - One neutral/pragmatic (sway 0)
        """
        bias = event.get("bias", "neutral")
        tag = event.get("tag", "SILENCE")

        # Crown-aligned choice
        crown_tags = ["GUILE", "SILENCE"]
        crown_tag = tag if tag in crown_tags else "SILENCE"

        # Crew-aligned choice
        crew_tags = ["DEFIANCE", "HEARTH", "BLOOD"]
        crew_tag = tag if tag in crew_tags else "DEFIANCE"

        return [
            {"text": "Act in the Crown's interest — order and caution.", "tag": crown_tag, "sway_effect": -1},
            {"text": "Act in the Crew's interest — freedom and solidarity.", "tag": crew_tag, "sway_effect": 1},
            {"text": "Act for yourself — pragmatism above allegiance.", "tag": "GUILE", "sway_effect": 0},
        ]

    def resolve_morning_choice(self, choice_index: int, event: dict) -> str:
        """WO-V107: Resolve a morning event choice.

        Args:
            choice_index: Zero-based index into event['choices'].
            event: The morning event dict returned by get_morning_event().

        Returns:
            Narrative result string with tag and sway feedback.
        """
        choices = event.get("choices", [])
        if not choices:
            return "No choices available."
        if choice_index < 0 or choice_index >= len(choices):
            choice_index = 0

        choice = choices[choice_index]
        tag = choice.get("tag", "SILENCE").upper()
        sway_effect = choice.get("sway_effect", 0)

        # Apply sway shift
        self.sway += sway_effect
        self.sway = max(-3, min(3, self.sway))

        # Apply DNA tag
        if tag in TAGS:
            self.dna[tag] += 1

        # Record shard
        self._add_shard(
            f"Day {self.day} morning: {choice['text'][:60]} [{tag}] sway {sway_effect:+d}",
            "CHRONICLE",
        )

        tier = self.get_tier()
        parts = [f"[{tag}] {choice['text']}"]
        if sway_effect != 0:
            direction = "toward the Crown" if sway_effect < 0 else "toward the Crew"
            parts.append(f"Sway shifts {direction}. Now: {self.sway:+d} ({tier['name']}).")
        else:
            parts.append(f"Sway holds at {self.sway:+d} ({tier['name']}).")
        return "\n".join(parts)

    # ─────────────────────────────────────────────────────────────────────
    # MIDDAY ENCOUNTERS — The March (WO-V109)
    # ─────────────────────────────────────────────────────────────────────

    def get_midday_encounter(self) -> dict | None:
        """WO-V109: Get a midday encounter for the day's march.

        Returns an encounter dict with text + choices, or None if
        Safe Passage is used to bypass. Avoids repeats.
        """
        pool = self._midday_encounters
        if not pool:
            return None

        available = [i for i in range(len(pool)) if i not in self._used_midday]
        if not available:
            self._used_midday.clear()
            available = list(range(len(pool)))

        idx = random.choice(available)
        self._used_midday.append(idx)

        encounter = pool[idx]
        # Ensure choices exist
        if "choices" not in encounter or not encounter["choices"]:
            encounter = dict(encounter)
            encounter["choices"] = [
                {"text": "Press through with caution.", "tag": "SILENCE", "sway_effect": 0},
                {"text": "Push hard and fast.", "tag": "BLOOD", "sway_effect": 0},
                {"text": "Find another way around.", "tag": "GUILE", "sway_effect": 0},
            ]
        return encounter

    def can_bypass_midday(self) -> bool:
        """WO-V109: Check if Safe Passage (sway -1) can bypass the midday encounter."""
        if self._safe_passage_used:
            return False
        return "safe_passage" in self.get_available_powers()

    def use_safe_passage(self) -> str:
        """WO-V109: Bypass the midday encounter via Safe Passage power."""
        if not self.can_bypass_midday():
            if self._safe_passage_used:
                return "Safe Passage has already been used this march."
            return "You lack Safe Passage. Requires Crown Leaning status (sway -1 or lower)."
        self._safe_passage_used = True
        crown_term = self.terms.get("crown", "The Crown")
        self._add_shard(
            f"Day {self.day}: Used Safe Passage — bypassed midday encounter",
            "CHRONICLE",
        )
        return (
            f"A {crown_term} patrol recognizes something in your bearing. "
            f"A nod. A turned back. You pass through unchallenged.\n"
            f"[Safe Passage consumed — the Crew notices your privilege.]"
        )

    def get_gated_midday_choices(self, encounter: dict) -> list[dict]:
        """WO-V109: Return midday choices with sway-gated modifications.

        Trusted Ear (sway +1): adds NPC motive reveal to the encounter.
        """
        choices = list(encounter.get("choices", []))

        # Trusted Ear (sway >= 1): bonus insight choice
        if self.sway >= 1:
            choices.append({
                "text": "[Trusted Ear] The Crew's scouts whisper what they know about this place.",
                "tag": "GUILE", "sway_effect": 0, "gated": "trusted_ear",
            })

        return choices

    def resolve_midday_choice(self, choice_index: int, encounter: dict) -> str:
        """WO-V109: Resolve a midday encounter choice.

        Same pattern as resolve_morning_choice — applies tag + sway.
        """
        choices = encounter.get("choices", [])
        if not choices:
            return "The march continues without incident."
        if choice_index < 0 or choice_index >= len(choices):
            choice_index = 0

        choice = choices[choice_index]
        tag = choice.get("tag", "SILENCE").upper()
        sway_effect = choice.get("sway_effect", 0)

        self.sway += sway_effect
        self.sway = max(-3, min(3, self.sway))

        if tag in TAGS:
            self.dna[tag] += 1

        self._add_shard(
            f"Day {self.day} midday: {choice['text'][:60]} [{tag}] sway {sway_effect:+d}",
            "CHRONICLE",
        )

        tier = self.get_tier()
        parts = [f"[{tag}] {choice['text']}"]
        if sway_effect != 0:
            direction = "toward the Crown" if sway_effect < 0 else "toward the Crew"
            parts.append(f"Sway shifts {direction}. Now: {self.sway:+d} ({tier['name']}).")
        else:
            parts.append(f"Sway holds at {self.sway:+d} ({tier['name']}).")
        return "\n".join(parts)

    # ─────────────────────────────────────────────────────────────────────
    # COUNCIL DILEMMAS (v4.0 — consolidated)
    # ─────────────────────────────────────────────────────────────────────

    def get_council_dilemma(self) -> dict:
        """Get a council dilemma that hasn't been used yet. Resets if exhausted.

        Returns:
            dict with keys: prompt, crown, crew
        """
        pool = self._council_dilemmas
        if not pool:
            return {
                "prompt": "The group faces a choice with no clear answer.",
                "crown": "Side with authority.",
                "crew": "Side with the people.",
            }
        available = [i for i in range(len(pool)) if i not in self._used_dilemmas]
        if not available:
            self._used_dilemmas.clear()
            available = list(range(len(pool)))
        idx = random.choice(available)
        self._used_dilemmas.append(idx)
        return pool[idx]

    # ─────────────────────────────────────────────────────────────────────
    # REST MECHANICS (v4.0)
    # ─────────────────────────────────────────────────────────────────────

    def trigger_long_rest(self) -> str:
        """Full phase cycle: morning -> night -> campfire -> council -> sleep.
        Advances day."""
        self.rest_type = "long"
        return self.end_day()

    def trigger_short_rest(self) -> str:
        """Minor event only. Does NOT advance day. Optional sway micro-shift.
        Limited to max_short_rests_per_day (default 1) per day (MED-06)."""
        max_short = self.rest_config.get("max_short_rests_per_day", 1)
        if self._short_rests_today >= max_short:
            return "You've already taken a short rest today. Choose long rest or press on."
        self._short_rests_today += 1
        self.rest_type = "short"
        event = self.get_morning_event()
        cap = self.rest_config.get("short_rest_sway_cap", 1)
        if event["bias"] == "crown":
            self.sway = max(-3, self.sway - cap)
        elif event["bias"] == "crew":
            self.sway = min(3, self.sway + cap)
        return f"Short rest: {event['text']}"

    def skip_rest(self) -> str:
        """Skip rest entirely. Sway decays toward 0."""
        decay = self.rest_config.get("sway_decay_on_skip", 1)
        if self.sway > 0:
            self.sway = max(0, self.sway - decay)
        elif self.sway < 0:
            self.sway = min(0, self.sway + decay)
        return f"No rest taken. Conviction wavers. (Sway: {self.sway:+d})"

    # ─────────────────────────────────────────────────────────────────────
    # POLITICAL GRAVITY — WEIGHTED COUNCIL VOTING
    # ─────────────────────────────────────────────────────────────────────

    def get_vote_power(self) -> int:
        """
        Get the current player's vote weight based on sway magnitude.

        Political Gravity:
            |sway| 0 → 1 vote power  (Drifter: no one listens)
            |sway| 1 → 2 vote power  (Leaning: some weight)
            |sway| 2 → 4 vote power  (Trusted: respected)
            |sway| 3 → 8 vote power  (Loyal: the heaviest voice)
        """
        return VOTE_POWER.get(abs(self.sway), 1)

    def resolve_vote(self, votes: dict[str, int], dilemma: dict | None = None) -> dict:
        """
        Resolve a council vote using Political Gravity.

        Each vote is weighted by the voter's sway magnitude.
        The side with more total weight wins.

        Args:
            votes: {"crown": raw_count, "crew": raw_count}
                   In single-player, this is {chosen_side: 1}
                   The engine applies political weight automatically.

        Returns:
            {
                "winner": "crown" | "crew",
                "crown_power": int,
                "crew_power": int,
                "player_weight": int,
                "margin": int,
                "unanimous": bool,
                "flavor": str
            }
        """
        player_weight = self.get_vote_power()
        raw_crown = votes.get("crown", 0)
        raw_crew = votes.get("crew", 0)

        # Apply political gravity:
        # The player's vote carries weight based on sway.
        # NPC votes are weighted at 1 each.
        if self.sway < 0:
            # Player leans Crown — Crown votes are heavier
            crown_power = raw_crown * player_weight
            crew_power = raw_crew * 1
        elif self.sway > 0:
            # Player leans Crew — Crew votes are heavier
            crown_power = raw_crown * 1
            crew_power = raw_crew * player_weight
        else:
            # Drifter — all votes equal
            crown_power = raw_crown * 1
            crew_power = raw_crew * 1

        margin = abs(crown_power - crew_power)

        if crown_power > crew_power:
            winner = "crown"
        elif crew_power > crown_power:
            winner = "crew"
        else:
            # Tie-breaker: current allegiance wins; if drifter, random
            if self.sway < 0:
                winner = "crown"
            elif self.sway > 0:
                winner = "crew"
            else:
                winner = random.choice(["crown", "crew"])

        winner_term = self.terms.get(winner, winner.upper())
        unanimous = raw_crown == 0 or raw_crew == 0

        # Flavor text based on margin
        if margin >= 8:
            flavor = f"{winner_term} dominates. No voice dared oppose."
        elif margin >= 4:
            flavor = f"{winner_term} prevails with authority."
        elif margin >= 2:
            flavor = f"{winner_term} wins, but dissent lingers."
        else:
            flavor = f"{winner_term} wins by a hair. The council is divided."

        result = {
            "winner": winner,
            "crown_power": crown_power,
            "crew_power": crew_power,
            "player_weight": player_weight,
            "margin": margin,
            "unanimous": unanimous,
            "flavor": flavor,
        }

        # WO-V110: Apply consequences from current dilemma
        consequence = self._apply_vote_consequence(winner, dilemma)
        if consequence:
            result["consequence"] = consequence

        self.vote_log.append({
            "day": self.day,
            "votes": dict(votes),
            "result": result,
        })

        return result

    def _apply_vote_consequence(self, winner: str, dilemma: dict | None) -> dict | None:
        """WO-V110: Apply tracked consequences from a council vote.

        Consequences affect:
        - narrative: flavor text shown immediately
        - morning_bias: next morning event is biased toward this side
        - tag: DNA tag awarded for the group decision
        - sway_modifier: additional sway shift from the collective choice

        Returns the consequence dict or None if no consequences defined.
        """
        if not dilemma:
            return None
        consequences = dilemma.get("consequences", {})
        if not consequences:
            return None

        consequence = consequences.get(winner, {})
        if not consequence:
            return None

        # Apply DNA tag
        tag = consequence.get("tag", "")
        if tag and tag in TAGS:
            self.dna[tag] += 1

        # Apply sway modifier
        sway_mod = consequence.get("sway_modifier", 0)
        if sway_mod:
            self.sway += sway_mod
            self.sway = max(-3, min(3, self.sway))

        # Track the consequence for next-day effects
        self._active_consequences.append({
            "day": self.day,
            "winner": winner,
            "narrative": consequence.get("narrative", ""),
            "morning_bias": consequence.get("morning_bias", "neutral"),
            "tag": tag,
        })

        # Shard
        self._add_shard(
            f"Day {self.day} council consequence: {consequence.get('narrative', '')[:60]}",
            "CHRONICLE",
        )

        return consequence

    def get_pending_consequences(self) -> list[dict]:
        """WO-V110: Return consequences from previous day that affect the current morning."""
        return [c for c in self._active_consequences if c.get("day") == self.day - 1]

    def get_consequence_morning_bias(self) -> str | None:
        """WO-V110: Get morning event bias from last night's council consequence."""
        pending = self.get_pending_consequences()
        if pending:
            return pending[-1].get("morning_bias")
        return None

    # ─────────────────────────────────────────────────────────────────────
    # GAME FLOW — AUTO-WIRING (#102 Factions, #103 Events)
    # ─────────────────────────────────────────────────────────────────────

    def _advance_factions(self) -> str:
        """WO-V102: Auto-advance faction state at end of day.

        The most influential faction takes an autonomous action.
        Council vote outcomes shift the power balance.
        Returns a narrative message or empty string.
        """
        try:
            politics = self._get_politics_engine()
        except Exception:
            return ""

        # Determine which faction acts based on dominance
        dominant = politics.influence_tracker.get_dominant_faction()
        if not dominant:
            return ""

        # Pick action based on faction's current state
        actions = ["propaganda", "recruit", "negotiate"]
        # If there's a rivalry, consider sabotage
        alliances = politics.alliance_system
        rivals = [
            f for f in politics.influence_tracker.factions
            if f != dominant and alliances.get_relationship(dominant, f) == "rivalry"
        ]
        if rivals:
            actions.append("sabotage")

        action = random.choice(actions)
        target = random.choice(rivals) if rivals and action == "sabotage" else ""

        result = politics.faction_action(dominant, action, target=target)
        if result.get("success") and result.get("narrative"):
            # Shift power balance based on last council vote
            if self.vote_log:
                last_vote = self.vote_log[-1].get("result", {})
                winner = last_vote.get("winner", "")
                if winner == "crown":
                    politics.power_shift(-0.1, "Council favored the Crown")
                elif winner == "crew":
                    politics.power_shift(0.1, "Council favored the Crew")
            return f"[Faction] {result['narrative']}"
        return ""

    def _auto_event(self) -> str:
        """WO-V103: Auto-generate a political event for the day.

        Uses EventGenerator to produce a sway-biased event and
        records it as a narrative shard. Returns the event text
        or empty string.
        """
        try:
            event_gen = self._get_event_generator()
        except Exception:
            return ""

        event = event_gen.generate_event(sway=self.sway, day=self.day)
        if event and event.get("text"):
            tag = event.get("tag", "")
            if tag and tag in TAGS:
                self.dna[tag] += 1
            self._add_shard(
                f"Day {self.day} event: {event['text'][:80]}",
                "CHRONICLE",
            )
            return f"[Event] {event['text']}"
        return ""

    def get_enhanced_morning_event(self) -> dict:
        """WO-V103: Get a morning event that combines static + generated layers.

        Returns the static morning event dict with an optional
        'political_event' key containing an EventGenerator event.
        """
        base_event = self.get_morning_event()
        try:
            event_gen = self._get_event_generator()
            political = event_gen.generate_event(sway=self.sway, day=self.day)
            if political and political.get("text"):
                base_event = dict(base_event)  # Don't mutate the pool
                base_event["political_event"] = political
        except Exception:
            pass
        return base_event

    def check_drifter_tax(self) -> bool:
        """Check if the Drifter's Tax applies (Double Draw penalty).

        The Whirlpool: neutrality is unstable. At sway 0, the player
        must justify BOTH a Crown and a Crew prompt simultaneously,
        suffers a resource drain, and is targeted by both factions.
        """
        return self.sway == 0

    def is_breach_day(self) -> bool:
        """Check if today is the Breach day (scales with arc_length)."""
        fraction = self.rest_config.get("breach_day_fraction", 0.6)
        breach_day = max(1, round(self.arc_length * fraction))
        return self.day == breach_day

    def end_day(self) -> str:
        """End the current day and advance to the next."""
        messages = []

        if self.check_drifter_tax():
            neutral_term = self.terms.get("neutral", "DRIFTER")
            self._drifter_tax_active = True
            messages.append(
                f"⚠️  {neutral_term.upper()}'S TAX: The Whirlpool pulls at you. "
                f"Tomorrow you must justify BOTH Crown and Crew. "
                f"Rations halved. Both factions watch you closely."
            )
        else:
            self._drifter_tax_active = False

        if self.is_breach_day():
            messages.append("👁️  THE BREACH: A Secret Witness saw what you did. No campfire tonight.")

        # WO-V102: Auto-advance factions at end of day
        faction_msg = self._advance_factions()
        if faction_msg:
            messages.append(faction_msg)

        # WO-V103: Auto-generate a political event for the day
        event_msg = self._auto_event()
        if event_msg:
            messages.append(event_msg)

        # WO-V10.0: CHRONICLE shard for day summary
        alignment = self.get_alignment_display()
        last_choice = self.history[-1]["choice"] if self.history else "none"
        self._add_shard(
            f"Day {self.day} summary: Sided with {last_choice}. "
            f"Sway: {self.sway:+d} ({alignment}). Breach: {self.is_breach_day()}",
            "CHRONICLE",
        )

        self.day = min(self.day + 1, self.arc_length + 1)
        self._pending_allegiance = None
        self._short_rests_today = 0

        # WO-V69.0: Advance DayClock by 1 phase per scene/day transition
        if self._day_clock is not None:
            self._day_clock.day = self.day
            self._day_clock.advance(1)

        if self.day > self.arc_length:
            messages.append("🏁 THE BORDER: Your journey ends. Final reckoning awaits.")
        else:
            messages.append(f"☀️  Dawn breaks. Day {self.day} begins.")

        return "\n".join(messages)

    def reset_day_state(self):
        """Clear volatile per-day state. Called at start of each day iteration."""
        self._pending_allegiance = None
        # Note: _drifter_tax_active persists across reset — it's set at end_day
        # and consumed when get_prompt() is called the following day.

    async def resolve_day_ai(self, vote_winner: str = "") -> str:
        """AI-enhanced day resolution narration. Falls back to end_day()."""
        fallback = self.end_day()
        alignment_display = self.get_alignment_display()
        last_choice = self.history[-1]["choice"] if self.history else "none"
        prompt = (
            f"Narrate the outcome of Day {self.day - 1}'s events. "
            f"The player sided with {last_choice}. "
            f"{'The council voted for ' + vote_winner + '. ' if vote_winner else ''}"
            f"Current alignment: {alignment_display} (sway {self.sway:+d}). "
            f"Patron is {self.patron}, Leader is {self.leader}. "
            f"1-2 sentences bridging to {'the next dawn' if self.day <= self.arc_length else 'the final reckoning'}."
        )
        # Note: end_day() was already called for state advancement,
        # this only generates narrative color
        return await self._consult_mimir(prompt, fallback)

    # ─────────────────────────────────────────────────────────────────────
    # REPORTS
    # ─────────────────────────────────────────────────────────────────────

    def get_summary(self) -> str:
        """Returns a full journey summary with dynamic terminology."""
        crown_term = self.terms.get("crown", "CROWN")
        crew_term = self.terms.get("crew", "CREW")

        lines = [
            "=" * 60,
            f"{crown_term.upper()} & {crew_term.upper()} — JOURNEY LOG",
            "=" * 60,
            f"Patron: {self.patron}",
            f"Leader: {self.leader}",
            "-" * 60,
        ]

        for entry in self.history:
            tag_str = f" [{entry.get('tag', '?')}]" if 'tag' in entry else ""
            side_display = crown_term if entry['choice'] == 'crown' else crew_term
            lines.append(
                f"  Day {entry['day']}: Chose {side_display.upper()}{tag_str} "
                f"(Sway: {entry['sway_after']:+d})"
            )

        lines.append("-" * 60)
        tier = self.get_tier()
        lines.append(f"Final Status: {tier['name']}")
        lines.append(f"Final Power: {tier['power']} — \"{tier['desc']}\"")
        lines.append("=" * 60)

        return "\n".join(lines)

    def generate_legacy_report(self) -> str:
        """Generate the Campaign Bridge Character Receipt."""
        alignment = self.get_alignment()
        dominant_tag = self.get_dominant_tag()
        tier = self.get_tier()

        # Use dynamic legacy titles, fall back to global
        titles = self._legacy_titles if self._legacy_titles else LEGACY_TITLES
        legacy_key = (alignment, dominant_tag)
        legacy_data = titles.get(
            legacy_key,
            {"title": "The Unknown", "desc": "Your path defies classification."}
        )

        # Build DNA breakdown
        dna_lines = []
        for tag in TAGS:
            value = self.dna[tag]
            bar = "█" * value + "░" * (5 - value)
            marker = " ◄" if tag == dominant_tag else ""
            dna_lines.append(f"    {tag:10} [{bar}] {value}{marker}")

        alignment_display = self.get_alignment_display()

        lines = [
            "",
            "╔" + "═" * 58 + "╗",
            "║" + "📜 CAMPAIGN BRIDGE: CHARACTER RECEIPT".center(58) + "║",
            "╠" + "═" * 58 + "╣",
            "║" + f"  Archetype: {legacy_data['title']}".ljust(58) + "║",
            "║" + f"  \"{legacy_data['desc']}\"".ljust(58) + "║",
            "╠" + "═" * 58 + "╣",
            "║" + f"  Final Alignment: {alignment_display}".ljust(58) + "║",
            "║" + f"  Final Status: {tier['name']}".ljust(58) + "║",
            "║" + f"  Final Power: {tier['power']}".ljust(58) + "║",
            "║" + f"  Dominant Trait: {dominant_tag}".ljust(58) + "║",
            "╠" + "═" * 58 + "╣",
            "║" + "  NARRATIVE DNA:".ljust(58) + "║",
        ]

        for dna_line in dna_lines:
            lines.append("║" + dna_line.ljust(58) + "║")

        lines.extend([
            "╠" + "═" * 58 + "╣",
            "║" + "  JOURNEY SUMMARY:".ljust(58) + "║",
            "║" + f"    Patron: {self.patron}".ljust(58) + "║",
            "║" + f"    Leader: {self.leader}".ljust(58) + "║",
            "║" + f"    Days Survived: {min(self.day, self.arc_length)}".ljust(58) + "║",
            "║" + f"    Choices Made: {len(self.history)}".ljust(58) + "║",
            "╚" + "═" * 58 + "╝",
            ""
        ])

        return "\n".join(lines)


    # ─────────────────────────────────────────────────────────────────────
    # SCENE PROGRESSION (optional — backward compatible)
    # ─────────────────────────────────────────────────────────────────────

    def set_scene_runner(self, runner: Any) -> None:
        """Attach a CrownSceneRunner for campaign scene progression.

        Args:
            runner: A CrownSceneRunner instance.  Passing None clears it.
        """
        self._scene_runner = runner

    def get_scene_for_today(self) -> Any:
        """Get the next unresolved scene for the current day, if any.

        Returns:
            CrownScene instance, or None if no scene runner is attached
            or no scenes remain.
        """
        if self._scene_runner is None:
            return None
        return self._scene_runner.get_current_scene(self.day)

    def resolve_scene_choice(self, choice_index: int) -> dict:
        """Resolve a scene choice and apply its effects to engine state.

        Applies sway delta (clamped to ±3) and increments the matching
        DNA tag.  Advances the scene runner afterward.

        Args:
            choice_index: Zero-based index of the player's chosen option.

        Returns:
            The result dict from CrownScene.resolve() with keys
            ``sway_effect``, ``tag``, ``next_scene``, ``narrative``.
            Returns empty dict if there is no active scene.
        """
        if self._scene_runner is None:
            return {}
        from codex.games.crown.scenes import CrownScene  # local import avoids circular
        scene: Optional[CrownScene] = self._scene_runner.get_current_scene(self.day)
        if scene is None:
            return {}
        result = scene.resolve(choice_index)
        # Apply sway effect (clamp to [-3, +3])
        self.sway = max(-3, min(3, self.sway + result.get("sway_effect", 0)))
        # Apply DNA tag increment
        tag = result.get("tag", "")
        if tag and tag in self.dna:
            self.dna[tag] += 1
        # Advance the runner (may bump chapter index)
        self._scene_runner.advance()
        return result

    # ─────────────────────────────────────────────────────────────────────
    # SERIALIZATION (v4.0)
    # ─────────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize engine state for save/load."""
        data: dict = {
            "day": self.day,
            "sway": self.sway,
            "patron": self.patron,
            "leader": self.leader,
            "history": self.history,
            "dna": self.dna,
            "vote_log": self.vote_log,
            "arc_length": self.arc_length,
            "rest_type": self.rest_type,
            "rest_config": self.rest_config,
            "terms": self.terms,
            "entities": self.entities,
            "threat": self.threat,
            "region": self.region,
            "goal": self.goal,
            "_used_crown": self._used_crown,
            "_used_crew": self._used_crew,
            "_used_world": self._used_world,
            "_used_campfire": self._used_campfire,
            "_used_morning": self._used_morning,
            "_used_dilemmas": self._used_dilemmas,
            "_council_dilemmas": self._council_dilemmas,
            "quest_slug": self.quest_slug,
            "quest_name": self.quest_name,
            "special_mechanics": self.special_mechanics,
            "_morning_events": self._morning_events,
            "_short_rests_today": self._short_rests_today,
            "_drifter_tax_active": self._drifter_tax_active,
            "_royal_decree_used": self._royal_decree_used,
            "_leaders_confidence_used": self._leaders_confidence_used,
            "_active_consequences": self._active_consequences,
            "_used_midday": self._used_midday,
            "_safe_passage_used": self._safe_passage_used,
            "_mirror_choice": self._mirror_choice,
            "_mirror_sin": self._mirror_sin,
            "players": {name: ps.to_dict() for name, ps in self.players.items()},
        }
        # Phase 4 — Persist subsystem state if they have been initialised
        if self._politics_engine is not None:
            data["_politics_engine"] = self._politics_engine.to_dict()
        if self._event_generator is not None:
            data["_event_generator"] = self._event_generator.to_dict()
        # WO-V68.0: Persist SessionManifest for narrative caching
        if NARRATIVE_LOOM_AVAILABLE and self._manifest is not None:
            try:
                data["_manifest"] = self._manifest.to_dict()
            except Exception:
                pass
        # WO-V69.0: Persist DayClock
        if self._day_clock is not None:
            try:
                data["_day_clock"] = self._day_clock.to_dict()
            except Exception:
                pass
        # Scene progression runner
        if self._scene_runner is not None:
            try:
                data["_scene_runner"] = self._scene_runner.to_dict()
            except Exception:
                pass
        return data

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> "CrownAndCrewEngine":
        """Restore engine from saved state."""
        init_keys = (
            "day", "sway", "patron", "leader", "history", "dna",
            "vote_log", "arc_length", "rest_type", "rest_config",
            "terms", "entities", "threat", "region", "goal",
        )
        init_args = {k: data[k] for k in init_keys if k in data}
        engine = cls(world_state=kwargs.get("world_state"), **init_args)
        for key in (
            "_used_crown", "_used_crew", "_used_world",
            "_used_campfire", "_used_morning", "_used_dilemmas",
            "_council_dilemmas", "quest_slug", "quest_name",
            "special_mechanics", "_morning_events", "_short_rests_today",
            "_drifter_tax_active", "_royal_decree_used", "_leaders_confidence_used",
            "_active_consequences", "_used_midday", "_safe_passage_used",
            "_mirror_choice", "_mirror_sin",
        ):
            if key in data:
                setattr(engine, key, data[key])

        # WO-V133: Restore player slots
        if "players" in data and isinstance(data["players"], dict):
            engine.players = {
                name: CrownPlayerState.from_dict(ps_data)
                for name, ps_data in data["players"].items()
            }

        # Phase 4 — Restore subsystem state if present
        if "_politics_engine" in data:
            try:
                from codex.games.crown.politics import PoliticalGravityEngine
                engine._politics_engine = PoliticalGravityEngine.from_dict(
                    data["_politics_engine"]
                )
            except Exception:
                pass

        if "_event_generator" in data:
            try:
                from codex.games.crown.events import EventGenerator
                engine._event_generator = EventGenerator.from_dict(
                    data["_event_generator"]
                )
            except Exception:
                pass

        # WO-V68.0: Restore SessionManifest for narrative caching
        if "_manifest" in data and NARRATIVE_LOOM_AVAILABLE:
            try:
                engine._manifest = SessionManifest.from_dict(data["_manifest"])
            except Exception:
                pass

        # WO-V69.0: Restore DayClock
        if "_day_clock" in data and _DAY_CLOCK_AVAILABLE:
            try:
                engine._day_clock = DayClock.from_dict(data["_day_clock"])
            except Exception:
                engine._day_clock = DayClock(phase=TimeOfDay.MORNING, day=engine.day)
        elif _DAY_CLOCK_AVAILABLE:
            engine._day_clock = DayClock(phase=TimeOfDay.MORNING, day=engine.day)

        # Scene progression runner
        if "_scene_runner" in data:
            try:
                from codex.games.crown.scenes import CrownSceneRunner
                engine._scene_runner = CrownSceneRunner.from_dict(data["_scene_runner"])
            except Exception:
                pass

        return engine


# =============================================================================
# INTEGRATION TEST — FULL 5-DAY RUN + WORLD INJECTION + POLITICAL GRAVITY
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("CROWN & CREW ENGINE v4.0 — REST + QUESTS + POLITICAL GRAVITY TEST")
    print("=" * 70)
    print()

    # ── Test 1: Default world (backward compatibility) ──
    print(">>> TEST 1: Default hardcoded world")
    engine = CrownAndCrewEngine()
    assert engine.terms["crown"] == "The Crown"
    assert len(engine._prompts_crown) == 10
    assert engine.arc_length == 5
    assert engine.rest_type == "long"
    print(f"  Patron: {engine.patron}")
    print(f"  Terms: {engine.terms['crown']} vs {engine.terms['crew']}")
    print(f"  Arc length: {engine.arc_length}")
    print(f"  Council dilemmas: {len(engine._council_dilemmas)}")
    print("  ✅ Default world OK")
    print()

    # ── Test 2: Injected world ──
    print(">>> TEST 2: Injected custom world")
    custom_world = {
        "terms": {
            "crown": "The Church",
            "crew": "The Coven",
            "neutral": "The Wanderer",
            "campfire": "The Seance",
            "world": "The Moors",
        },
        "prompts_crown": [
            "A bishop offers absolution. The price is a name.",
            "Cathedral bells ring. They know you're here.",
        ],
        "prompts_crew": [
            "The eldest witch asks for blood. Not much. Just enough.",
            "The ritual circle is drawn. Someone must stand in the center.",
        ],
        "prompts_world": [
            "Fog rolls across the barrows. Something old is awake.",
        ],
        "prompts_campfire": [
            "A candle gutters. Someone whispers a name you thought forgotten.",
        ],
        "secret_witness": "A child with no shadow stands at the gate, holding your mother's ring.",
        "patrons": ["The Bishop", "The Magistrate", "The Inquisitor General"],
        "leaders": ["Mother Nyx", "The Branded Man", "Sister Thorn"],
    }

    injected = CrownAndCrewEngine(world_state=custom_world)
    assert injected.terms["crown"] == "The Church"
    assert injected.terms["crew"] == "The Coven"
    assert len(injected._prompts_crown) == 2
    assert injected.patron in custom_world["patrons"]
    print(f"  Terms: {injected.terms['crown']} vs {injected.terms['crew']}")
    print(f"  Crown prompts: {len(injected._prompts_crown)}")
    print(f"  Patron: {injected.patron}")
    witness_len = len(injected.get_secret_witness())
    print(f"  Witness: <redacted, {witness_len} chars>")
    print("  ✅ World injection OK")
    print()

    # ── Test 3: Political Gravity ──
    print(">>> TEST 3: Political Gravity (Weighted Voting)")

    # Sway 0: weight 1
    engine = CrownAndCrewEngine()
    assert engine.get_vote_power() == 1
    result = engine.resolve_vote({"crown": 1, "crew": 0})
    print(f"  Sway  0, Crown=1 Crew=0 → winner={result['winner']} "
          f"(power: {result['crown_power']} vs {result['crew_power']})")

    # Sway -2: weight 4 (Crown leaning)
    engine.sway = -2
    assert engine.get_vote_power() == 4
    result = engine.resolve_vote({"crown": 1, "crew": 2})
    print(f"  Sway -2, Crown=1 Crew=2 → winner={result['winner']} "
          f"(power: {result['crown_power']} vs {result['crew_power']}) "
          f"[{result['flavor']}]")

    # Sway +3: weight 8 (Crew loyal)
    engine.sway = 3
    assert engine.get_vote_power() == 8
    result = engine.resolve_vote({"crown": 3, "crew": 1})
    print(f"  Sway +3, Crown=3 Crew=1 → winner={result['winner']} "
          f"(power: {result['crown_power']} vs {result['crew_power']}) "
          f"[{result['flavor']}]")
    print("  ✅ Political Gravity OK")
    print()

    # ── Test 4: Full 5-day run ──
    print(">>> TEST 4: Full 5-day campaign run")
    engine = CrownAndCrewEngine()
    choices = [
        ("crew", "HEARTH"),
        ("crew", "DEFIANCE"),
        ("crown", "GUILE"),
        ("crew", "BLOOD"),
        ("crew", None),
    ]

    for day in range(1, 6):
        side, tag = choices[day - 1]
        engine.declare_allegiance(side, tag)
        engine.get_prompt()
        engine.get_world_prompt()
        if not engine.is_breach_day():
            engine.get_campfire_prompt()
        engine.end_day()

    print(engine.generate_legacy_report())
    print(engine.get_summary())

    alignment = engine.get_alignment()
    dom_tag = engine.get_dominant_tag()
    print(f"  Alignment Display: {engine.get_alignment_display()}")
    print(f"  Legacy Title: {LEGACY_TITLES.get((alignment, dom_tag), {}).get('title', '?')}")
    print("  ✅ Full campaign OK")
    print()

    # ── Test 5: Rest mechanics ──
    print(">>> TEST 5: Rest Mechanics")
    engine = CrownAndCrewEngine()
    engine.sway = 2
    msg = engine.skip_rest()
    assert engine.sway == 1, f"Expected sway 1 after skip, got {engine.sway}"
    print(f"  Skip rest (sway 2→{engine.sway}): {msg}")

    engine.sway = 0
    msg = engine.trigger_short_rest()
    print(f"  Short rest: {msg}")
    print(f"  Day after short rest: {engine.day} (should be 1)")
    assert engine.day == 1

    msg = engine.trigger_long_rest()
    print(f"  Long rest: Day advanced to {engine.day}")
    assert engine.day == 2
    print("  ✅ Rest mechanics OK")
    print()

    # ── Test 6: Council dilemmas ──
    print(">>> TEST 6: Council Dilemmas")
    engine = CrownAndCrewEngine()
    dilemma = engine.get_council_dilemma()
    assert "prompt" in dilemma
    assert "crown" in dilemma
    assert "crew" in dilemma
    print(f"  Dilemma: {dilemma['prompt'][:60]}...")
    print("  ✅ Council dilemmas OK")
    print()

    # ── Test 7: Serialization roundtrip ──
    print(">>> TEST 7: Serialization")
    engine = CrownAndCrewEngine(arc_length=7)
    engine.declare_allegiance("crew", "HEARTH")
    engine.end_day()
    data = engine.to_dict()
    restored = CrownAndCrewEngine.from_dict(data)
    assert restored.day == engine.day
    assert restored.sway == engine.sway
    assert restored.arc_length == 7
    print(f"  Roundtrip: day={restored.day}, sway={restored.sway}, arc={restored.arc_length}")
    print("  ✅ Serialization OK")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED")
    print("=" * 70)


# =============================================================================
# CROWN_COMMANDS / CROWN_CATEGORIES — Dashboard / Bridge Integration
# =============================================================================

CROWN_COMMANDS: dict = {
    "status": "Show current sway, day, and alignment",
    "faction_status": "List all faction influences and territory",
    "shift_influence": "Modify a faction's influence (faction=, amount=)",
    "form_alliance": "Form a faction alliance (faction_a=, faction_b=)",
    "break_alliance": "Break a faction alliance (faction_a=, faction_b=, reason=)",
    "council_vote": "Simulate a council vote (proposal=, factions_voting={...})",
    "power_balance": "Show current political power balance",
    "generate_event": "Generate a weighted political event",
    "event_chain": "Advance an event chain (chain_id=)",
    "political_landscape": "Full political landscape summary",
    "trace_fact": "Trace a fact through narrative shards (fact=)",
}

CROWN_CATEGORIES: dict = {
    "Political Status": ["status", "power_balance", "political_landscape"],
    "Faction Management": [
        "faction_status", "shift_influence",
        "form_alliance", "break_alliance",
    ],
    "Council & Events": ["council_vote", "generate_event", "event_chain"],
    "Narrative": ["trace_fact"],
}


# Engine registration
try:
    from codex.core.engine_protocol import register_engine
    register_engine("crown", CrownAndCrewEngine)
except ImportError:
    pass
