"""
codex.forge.reference_data.cbrpnk_mechanics
============================================
Core mechanical rules reference data for CBR+PNK.

SOURCE: cbrpnk_03_framework.pdf (Core Rules)
SOURCE: cbrpnk_01_gm-guide.pdf (GM Guide)

Covers:
  - Action roll results
  - Harm levels (4 levels)
  - Consequence types (5 types)
  - Adversary skill ratings
  - Run structure (3 phases)
  - Glitch Dice rules
  - Angle Roll results (epilogue)
  - Progress track sizes
  - Long Shot campaign rules
  - Downtime activities
"""

from typing import Any, Dict, List


# =========================================================================
# ACTION ROLL RESULTS
# SOURCE: cbrpnk_03_framework.pdf
# =========================================================================

ACTION_RESULTS: Dict[str, Dict[str, Any]] = {
    "Critical": {
        "trigger": "Roll two or more 6s",
        "dice_values": "6, 6",
        "description": (
            "You succeed remarkably. The outcome exceeds expectations — "
            "better position, bonus effect, or additional advantage."
        ),
        "effect": "Full success with exceptional outcome",
        "consequence": False,
    },
    "Success": {
        "trigger": "Highest die is a 6",
        "dice_values": "6",
        "description": (
            "You do it. Clean result with no complications."
        ),
        "effect": "Full success",
        "consequence": False,
    },
    "Partial Success": {
        "trigger": "Highest die is 4 or 5",
        "dice_values": "4 or 5",
        "description": (
            "You do it, but not cleanly. You achieve the goal but face "
            "a consequence: reduced effect, harm, complication, threat escalation, "
            "or lost opportunity."
        ),
        "effect": "Success with consequence",
        "consequence": True,
    },
    "Failure": {
        "trigger": "Highest die is 1, 2, or 3",
        "dice_values": "1-3",
        "description": (
            "You fail and face a consequence. "
            "Things get worse — and the GM gets to decide how."
        ),
        "effect": "Failure with consequence",
        "consequence": True,
    },
}


# =========================================================================
# THREAT & EFFECT LEVELS
# SOURCE: cbrpnk_03_framework.pdf
# =========================================================================

THREAT_LEVELS: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "Low",
        "description": "Minimal danger; routine for experienced Runners.",
        "default": False,
    },
    2: {
        "name": "Standard",
        "description": (
            "Default threat level. Normal operations in the SPRAWL — "
            "dangerous but manageable."
        ),
        "default": True,
    },
    3: {
        "name": "High",
        "description": (
            "Serious danger. Failing rolls at this level escalates fast. "
            "Hunter activation can occur here."
        ),
        "default": False,
        "hunter_trigger": True,
    },
    4: {
        "name": "Extreme",
        "description": (
            "Near-suicidal conditions. Military-grade opposition, "
            "zero margin for error."
        ),
        "default": False,
    },
}

EFFECT_LEVELS: Dict[int, Dict[str, str]] = {
    1: {
        "name": "Limited",
        "description": "Reduced impact — partial progress, glancing blow.",
    },
    2: {
        "name": "Standard",
        "description": "Default effect level. Full expected outcome.",
    },
    3: {
        "name": "Great",
        "description": "Enhanced impact — accelerated progress, decisive blow.",
    },
    4: {
        "name": "Extreme",
        "description": "Overwhelming impact — exceptional outcome, major advantage.",
    },
}


# =========================================================================
# CONSEQUENCE TYPES
# SOURCE: cbrpnk_03_framework.pdf
# =========================================================================

CONSEQUENCE_TYPES: Dict[str, Dict[str, Any]] = {
    "Reduced Effect": {
        "description": (
            "The action succeeds but with less impact than intended. "
            "Partial progress, smaller gain, weaker result."
        ),
        "severity": "Low",
        "examples": [
            "The door opens but the alarm still trips.",
            "You land the hit but only stagger the target.",
            "The hack succeeds but you only get partial data.",
        ],
    },
    "Harm": {
        "description": (
            "You or an ally sustain physical or psychological damage. "
            "Harm is recorded by level (1-4) and has mechanical effects "
            "on future actions."
        ),
        "severity": "Variable",
        "examples": [
            "Level 1: Battered — minor wound, dazed.",
            "Level 2: Deeply Cut — serious injury, action penalties.",
            "Level 3: Broken Bones — incapacitating, requires immediate aid.",
            "Level 4: Lethal — survival uncertain without immediate intervention.",
        ],
    },
    "Complication": {
        "description": (
            "A new obstacle or problem emerges from the action. "
            "Not direct harm, but a situation that will require addressing."
        ),
        "severity": "Variable",
        "examples": [
            "Witnesses saw you — heat increases.",
            "The target is now alerted to your presence.",
            "The data you extracted is encrypted.",
            "Your contact is now in danger.",
        ],
    },
    "Threat Escalation": {
        "description": (
            "The threat level increases. The opposition gets more dangerous, "
            "more organized, or brings in reinforcements."
        ),
        "severity": "Medium",
        "examples": [
            "Corp sec calls in a detachment.",
            "The grid alarm jumps to a higher level.",
            "The target corp puts a bounty on the crew.",
        ],
    },
    "Lost Opportunity": {
        "description": (
            "The chance to act is gone — the window closed, "
            "the target moved, the situation changed before you could act."
        ),
        "severity": "Low",
        "examples": [
            "The convoy already passed.",
            "The executive left the building.",
            "The data node was purged before extraction.",
        ],
    },
}


# =========================================================================
# HARM LEVELS
# SOURCE: cbrpnk_03_framework.pdf
# =========================================================================

HARM_LEVELS: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "Superficial",
        "description": (
            "Minor injury, easily shaken off. Penalizes some actions "
            "but doesn't take a Runner out of the fight."
        ),
        "examples": ["Dazed", "Bleeding", "Battered", "Confused", "Lagging"],
        "mechanical_effect": "Minor penalty on relevant actions.",
        "recovery": "Rest or minimal downtime.",
    },
    2: {
        "name": "Serious",
        "description": (
            "Significant injury requiring attention. Clear mechanical penalty; "
            "the Runner is compromised but still functional."
        ),
        "examples": [
            "Sensory Deprived",
            "Deeply Cut",
            "Drained",
            "Panicking",
            "Low Morale",
            "Concussed",
        ],
        "mechanical_effect": "Significant penalty; -1d or restricted actions.",
        "recovery": "Downtime activity: Recover.",
    },
    3: {
        "name": "Incapacitating",
        "description": (
            "The Runner is effectively out of the fight. "
            "Requires immediate assistance to avoid deteriorating further."
        ),
        "examples": ["Impaled", "Broken Bones", "Badly Burned", "Terrified"],
        "mechanical_effect": "Cannot act normally; requires assistance.",
        "recovery": "Extended downtime; medical intervention required.",
    },
    4: {
        "name": "Lethal / FATAL",
        "description": (
            "The Runner's life is in immediate danger. "
            "Without intervention, they die or suffer permanent consequences."
        ),
        "examples": [
            "Compromised Vital Organ",
            "Loss of a Limb",
            "Lore Wiped",
            "Electrocuted",
            "Drowned",
        ],
        "mechanical_effect": "Survival requires immediate extraordinary action.",
        "recovery": "Major downtime, surgery, or permanent consequence.",
    },
}


# =========================================================================
# ADVERSARY SKILL RATINGS
# SOURCE: cbrpnk_03_framework.pdf
# =========================================================================

ADVERSARY_SKILLS: Dict[str, Dict[str, Any]] = {
    "Regular": {
        "description": (
            "Standard opposition — corp sec grunts, gang members, "
            "basic patrol ICE. Dangerous in numbers but beatable by "
            "a competent Runner."
        ),
        "threat_modifier": 0,
        "examples": ["Burnt Pistons gang members", "Patrol guards", "Artemisia-I ICE"],
    },
    "Skilled": {
        "description": (
            "Trained professionals — detectives, veteran security, "
            "specialist hackers. Require specific approaches to handle "
            "and will exploit Runner weaknesses."
        ),
        "threat_modifier": 1,
        "examples": ["Corp sec detachments", "Poison (hacker)", "Defender ICE"],
    },
    "Elite": {
        "description": (
            "Top-tier opposition — paramilitary units, legendary operators, "
            "black-budget ICE. Engaging them head-on is usually suicide. "
            "Runners need a plan."
        ),
        "threat_modifier": 2,
        "examples": ["Taskforce (paramilitary)", "Dozer (bipedal drone)", "I.C.P. ICE"],
    },
}


# =========================================================================
# RUN STRUCTURE
# SOURCE: cbrpnk_01_gm-guide.pdf
# =========================================================================

RUN_STRUCTURE: Dict[str, Dict[str, Any]] = {
    "Phase 1: Coming in Hot": {
        "order": 1,
        "description": (
            "The setup. The crew approaches the objective. "
            "The engagement plan is declared. The opening situation is established — "
            "what does the scene look like when the Runners arrive?"
        ),
        "key_questions": [
            "What is the engagement plan?",
            "What is the opposition's initial disposition?",
            "What immediate complications exist?",
        ],
    },
    "Phase 2: Error 417: Expectation Failed": {
        "order": 2,
        "description": (
            "The complications phase. Something goes sideways — "
            "or everything does. The crew navigates the gap between "
            "their plan and reality. This is the meat of the run."
        ),
        "key_questions": [
            "What went wrong?",
            "Who adapts and how?",
            "What new information changes the situation?",
        ],
    },
    "Phase 3: Logoff": {
        "order": 3,
        "description": (
            "The exit. The crew gets out — or doesn't. "
            "Consequences land. Heat is assessed. The Angle Roll "
            "determines the epilogue for the run."
        ),
        "key_questions": [
            "Did the crew achieve their objective?",
            "What heat did they generate?",
            "What's the Angle Roll outcome?",
        ],
    },
}


# =========================================================================
# GLITCH DICE RULES
# SOURCE: cbrpnk_03_framework.pdf
# =========================================================================

GLITCH_DICE_RULES: Dict[str, Any] = {
    "description": (
        "When a factor is GLITCHED — a piece of chrome malfunctioning, "
        "a tool compromised, an environment interfering — that factor "
        "replaces one of the normal action dice with a Glitch die."
    ),
    "glitch_die_rule": (
        "Roll the Glitch die separately from the normal pool. "
        "If the Glitch die shows 1-3, it triggers a Level 2 Consequence "
        "in addition to whatever the normal pool result was."
    ),
    "glitch_trigger_range": "1-3",
    "consequence_on_glitch": "Level 2 Consequence (Serious Harm or equivalent)",
    "stacking": (
        "Each additional GLITCHED factor replaces another normal die "
        "with another Glitch die. Multiple Glitch dice = multiple "
        "independent 1-3 checks."
    ),
    "examples": [
        "Malfunctioning Neural Jack during a hack: one die in the hack pool becomes a Glitch die.",
        "Damaged Reflex Boosters in combat: one die in the skirmish pool becomes a Glitch die.",
    ],
}


# =========================================================================
# ANGLE ROLL RESULTS (Epilogue)
# SOURCE: cbrpnk_03_framework.pdf
# =========================================================================

ANGLE_ROLL_RESULTS: Dict[str, Dict[str, str]] = {
    "Critical": {
        "trigger": "Two or more 6s",
        "description": "Succeeded remarkably.",
        "narrative": (
            "The run paid off beyond expectations. The crew not only achieved "
            "the objective but gained something extra — reputation, unexpected "
            "intel, a new angle for the future."
        ),
    },
    "Success": {
        "trigger": "Highest die is 6",
        "description": "Got out mostly intact.",
        "narrative": (
            "The job's done. Not pretty, but done. The crew walks away "
            "with what they came for and nothing they didn't want."
        ),
    },
    "Partial": {
        "trigger": "Highest die is 4 or 5",
        "description": "Did it, but it won't last.",
        "narrative": (
            "Objective achieved, but there's a problem on the horizon. "
            "A loose end, a witness, heat building. The win is real "
            "but comes with a future complication."
        ),
    },
    "Failure": {
        "trigger": "Highest die is 1-3",
        "description": "Failed.",
        "narrative": (
            "The run didn't work out. Objectives missed, heat gained, "
            "and the crew has to live with the consequences and figure out "
            "what comes next."
        ),
    },
}


# =========================================================================
# PROGRESS TRACK SIZES
# SOURCE: cbrpnk_03_framework.pdf
# =========================================================================

PROGRESS_TRACK_SIZES: List[int] = [4, 6, 8]

PROGRESS_TRACK_GUIDANCE: Dict[int, str] = {
    4: "Short-term goal. A few decisive actions can close it.",
    6: "Standard challenge. Requires sustained effort or multiple rolls.",
    8: "Major obstacle. Long-term project or heavily defended target.",
}


# =========================================================================
# LONG SHOT CAMPAIGN RULES
# SOURCE: cbrpnk_01_gm-guide.pdf
# =========================================================================

LONG_SHOT_RULES: Dict[str, Any] = {
    "description": (
        "Long Shot is the campaign mode for CBR+PNK. "
        "A structured 4-8 session arc focused on bringing down an Oppressor."
    ),
    "session_range": "4-8 sessions",
    "structure": {
        "Oppressor": (
            "The power structure the crew is targeting. "
            "A megacorp, a government body, a criminal empire. "
            "Example: Omni Global Solutions."
        ),
        "Target": (
            "The specific objective within the Oppressor's operation "
            "that the crew is striking at."
        ),
        "Countermeasures": (
            "The active defenses and responses the Oppressor deploys "
            "as the crew escalates pressure."
        ),
    },
    "angles": {
        "Take Down": "Destroy or eliminate the Oppressor entirely.",
        "Resist": "Survive and resist the Oppressor's encroachment.",
        "Liberate": "Free people or communities from the Oppressor's control.",
    },
    "random_tables": [
        "Objectives",
        "Interior Locations",
        "Exterior Locations",
        "Environmental Issues",
        "Streets",
        "Status",
        "Condition",
        "Online",
        "Payload",
        "Target",
    ],
    "source": "cbrpnk_01_gm-guide.pdf",
}


# =========================================================================
# DOWNTIME ACTIVITIES
# SOURCE: cbrpnk_01_gm-guide.pdf
# =========================================================================

DOWNTIME_ACTIVITIES: Dict[str, Dict[str, str]] = {
    "Recover": {
        "description": (
            "Rest, seek medical attention, and heal from harm sustained "
            "during the run. Addresses physical and psychological damage."
        ),
        "mechanical_effect": "Clear one or more harm levels.",
        "time_cost": "One downtime activity slot.",
    },
    "Repair": {
        "description": (
            "Fix damaged chrome, equipment, and gear. "
            "Address GLITCHED factors before they cause problems on the next run."
        ),
        "mechanical_effect": "Clear glitch flags from chrome and equipment.",
        "time_cost": "One downtime activity slot.",
    },
    "Side Project": {
        "description": (
            "Pursue a personal goal, build a resource, work a contact, "
            "or advance a long-term plan outside of crew runs."
        ),
        "mechanical_effect": "Advance a personal or crew-level clock.",
        "time_cost": "One downtime activity slot.",
    },
}


# =========================================================================
# SETTING TERMINOLOGY
# SOURCE: cbrpnk_01_gm-guide.pdf
# =========================================================================

SETTING_TERMS: Dict[str, str] = {
    "Runners": "The player characters. The crew doing the run.",
    "Operator": "The Runners' fixer — the contact who brings them jobs.",
    "The SPRAWL": "The megacity. The physical urban environment.",
    "The GRID": "The digital network. The virtual space for hacking.",
}


__all__ = [
    "ACTION_RESULTS",
    "THREAT_LEVELS",
    "EFFECT_LEVELS",
    "CONSEQUENCE_TYPES",
    "HARM_LEVELS",
    "ADVERSARY_SKILLS",
    "RUN_STRUCTURE",
    "GLITCH_DICE_RULES",
    "ANGLE_ROLL_RESULTS",
    "PROGRESS_TRACK_SIZES",
    "PROGRESS_TRACK_GUIDANCE",
    "LONG_SHOT_RULES",
    "DOWNTIME_ACTIVITIES",
    "SETTING_TERMS",
]
