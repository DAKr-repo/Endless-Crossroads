"""
codex/core/enrichment_prompts.py — Prompt Templates for Module Enrichment
==========================================================================
System prompts and user-prompt templates for Tier 2/3 module enrichment.
Each pair (SYSTEM + TEMPLATE) drives one Codex invocation via Architect.

Templates use str.format() with named placeholders.
"""

# ---------------------------------------------------------------------------
# NPC Enrichment (Codex model — full context, used as fallback)
# ---------------------------------------------------------------------------

NPC_ENRICHMENT_SYSTEM = (
    "You are a TTRPG module writer. You write NPC dialogue lines that are "
    "concise, setting-grounded, and reveal personality through speech. "
    "Output ONLY the dialogue line — no stage directions, no labels, no "
    "quotation marks wrapping the whole output."
)

NPC_ENRICHMENT_TEMPLATE = (
    "MODULE: {module_name} ({system_id})\n"
    "{source_material}"
    "MODULE BRIEF: {module_brief}\n\n"
    "NPC: {npc_name} (Role: {npc_role})\n"
    "Current dialogue: \"{current_dialogue}\"\n\n"
    "Rewrite this NPC's dialogue to be grounded in the setting. Include:\n"
    "- A tone tag in brackets (e.g. [Wary], [Eager], [Hushed])\n"
    "- 2 sentences maximum\n"
    "- Reference to the local environment or current events\n"
    "- Personality that fits their role\n\n"
    "Output ONLY the new dialogue line, nothing else."
)

# ---------------------------------------------------------------------------
# NPC Enrichment — Mimir model (few-shot, fast, dialogue-only)
# ---------------------------------------------------------------------------
# Small models (<2B) pattern-match from examples better than they follow
# instructions.  Keep the system prompt short and front-load 3 examples
# that demonstrate the exact output format: [Tone] Sentence. Sentence.

MIMIR_NPC_SYSTEM = "Write NPC dialogue. Format: [Tone] 1-2 sentences."

MIMIR_NPC_TEMPLATE = (
    "EXAMPLES:\n"
    "informant | The Dusk Market | \"Knows things.\"\n"
    "-> [Wary] The Bluecoats doubled patrols after last night. Keep your voice down.\n\n"
    "fence | The Docks | \"Buys stolen goods.\"\n"
    "-> [Eager] Fresh haul? I can move electroplasm quick — the war's driven prices through the roof.\n\n"
    "lookout | Rooftop | \"Watches for trouble.\"\n"
    "-> [Hushed] Three shadows on Crows Foot bridge. Not ours.\n\n"
    "NOW WRITE:\n"
    "{npc_role} | {scene_name} | \"{current_dialogue}\"\n"
    "->"
)

# Regex pattern for validating Mimir dialogue output
MIMIR_NPC_VALIDATE_PATTERN = r"^\[[\w]+\] .+"

# ---------------------------------------------------------------------------
# Room Description Enrichment
# ---------------------------------------------------------------------------

ROOM_ENRICHMENT_SYSTEM = (
    "You are a TTRPG module writer. You write vivid, atmospheric room "
    "descriptions that use concrete sensory detail. Output ONLY the "
    "description text — no labels, no bullet points."
)

ROOM_ENRICHMENT_TEMPLATE = (
    "MODULE: {module_name} ({system_id})\n"
    "{source_material}"
    "SCENE: {scene_name} ({topology})\n"
    "TIER: {tier}\n\n"
    "Current description: \"{current_description}\"\n\n"
    "Expand this into a vivid 2-3 sentence description that includes:\n"
    "- One sensory detail (sound, smell, or texture)\n"
    "- One detail that hints at danger or opportunity\n"
    "- Tone appropriate for tier {tier}\n\n"
    "Output ONLY the description, nothing else."
)

# ---------------------------------------------------------------------------
# Event Trigger Enrichment
# ---------------------------------------------------------------------------

EVENT_ENRICHMENT_SYSTEM = (
    "You are a TTRPG module writer. You rewrite generic event triggers "
    "into dramatic narration. Output ONLY the rewritten trigger text."
)

EVENT_ENRICHMENT_TEMPLATE = (
    "MODULE: {module_name} ({system_id})\n"
    "MODULE BRIEF: {module_brief}\n"
    "SCENE: {scene_name}\n\n"
    "Current event triggers:\n{current_triggers}\n\n"
    "Rewrite each trigger into a 1-2 sentence dramatic narration that:\n"
    "- Sets the scene with urgency or tension\n"
    "- Hints at what the players must decide\n\n"
    "Output ONLY the rewritten triggers, one per line."
)

# ---------------------------------------------------------------------------
# Room Description — Mimir fallback (few-shot, fast)
# ---------------------------------------------------------------------------

MIMIR_ROOM_SYSTEM = "Write a vivid 2-sentence room description. Include one sensory detail."

MIMIR_ROOM_TEMPLATE = (
    "EXAMPLES:\n"
    "tavern | dungeon | \"A dark room.\"\n"
    "-> The low ceiling presses down like a held breath, slick with condensation that reeks of copper and old stone. A single lantern swings from a rusted chain, its light catching the wet edge of something scratched into the far wall.\n\n"
    "market | settlement | \"A busy square.\"\n"
    "-> Vendors hawk their wares beneath canvas canopies stained by coal smoke, the air thick with the competing scents of fried dough and cured leather. A pickpocket works the crowd near the fountain — you catch the glint of a blade.\n\n"
    "NOW WRITE:\n"
    "{room_type} | {topology} | \"{current_description}\"\n"
    "->"
)

# ---------------------------------------------------------------------------
# Event Trigger — Mimir fallback (few-shot, fast)
# ---------------------------------------------------------------------------

MIMIR_EVENT_SYSTEM = "Rewrite event triggers into dramatic 1-sentence narration."

MIMIR_EVENT_TEMPLATE = (
    "EXAMPLES:\n"
    "- A guard notices you.\n"
    "-> The sentry's lantern swings your way — one heartbeat before the shout goes up.\n\n"
    "- The ground shakes.\n"
    "-> The flagstones buck underfoot and dust cascades from the ceiling; something immense is moving below.\n\n"
    "NOW WRITE:\n"
    "- {current_trigger}\n"
    "->"
)

# ---------------------------------------------------------------------------
# Quest Arc Weave
# ---------------------------------------------------------------------------

QUEST_ARC_SYSTEM = (
    "You are a TTRPG module writer. You craft narrative hooks that connect "
    "scenes into a coherent adventure. Output ONLY the narrative hook."
)

QUEST_ARC_TEMPLATE = (
    "MODULE: {module_name} ({system_id})\n"
    "{source_material}"
    "SCENES IN ORDER:\n{scene_list}\n\n"
    "Generate a 2-3 sentence narrative hook that:\n"
    "- Establishes WHY the player is here\n"
    "- Names the central threat or mystery\n"
    "- Connects scene 1 to the final scene\n\n"
    "Output ONLY the narrative hook."
)
