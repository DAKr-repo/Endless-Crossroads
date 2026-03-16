"""
codex.forge.reference_data.cbrpnk_chrome
=========================================
Cybernetic augmentation reference data for CBR+PNK.

NOTE: Core rules don't define specific chrome items beyond the CYBERWARE_TABLE
(d6 pairs from Mona_Rise_Megalopolis.pdf and cbrpnk_04_prdtr.pdf).
The CHROME dict below is expanded content for gameplay richness — these items
are not canonical to the CBR+PNK rules text but are consistent with the game's
tone and mechanics. The CYBERWARE_TABLE is the PDF-sourced canonical list.

CHROME dict: 20 augmentations (EXPANDED — not in source PDF)
CHROME_SLOTS: Valid slots with max capacity (EXPANDED)
GLITCH_EFFECTS: Glitch severity descriptors (EXPANDED)
CYBERWARE_TABLE: Canonical d6 cyberware pairs from PDF sources
"""

from typing import Any, Dict, List


# =========================================================================
# CHROME AUGMENTATIONS
# =========================================================================

CHROME: Dict[str, Dict[str, Any]] = {
    "Neural Jack": {
        "setting": "the_sprawl",
        "name": "Neural Jack",
        "slot": "neural",
        "description": (
            "A direct-interface port drilled into the base of the skull. "
            "Allows cable connection to the Grid, vehicles, or compatible hardware."
        ),
        "effect": "+1d on hack actions when cabled in; required for Grid access",
        "glitch_risk": 0.15,
        "humanity_cost": 1,
    },
    "Reflex Boosters": {
        "setting": "the_sprawl",
        "name": "Reflex Boosters",
        "slot": "neural",
        "description": (
            "Synthetic nerve sheathing that accelerates signal transmission. "
            "Your reactions are mechanically enhanced, not just trained."
        ),
        "effect": "+1d on scramble and shoot actions; you can never be ambushed",
        "glitch_risk": 0.20,
        "humanity_cost": 2,
    },
    "Cybereyes": {
        "setting": "the_sprawl",
        "name": "Cybereyes",
        "slot": "optical",
        "description": (
            "Full ocular replacement with integrated targeting reticle, low-light "
            "amplification, and optional zoom up to 10x magnification."
        ),
        "effect": "+1d on scan actions; ignores darkness penalties",
        "glitch_risk": 0.10,
        "humanity_cost": 1,
    },
    "Thermal Vision": {
        "setting": "the_sprawl",
        "name": "Thermal Vision",
        "slot": "optical",
        "description": (
            "Infrared overlay upgrade for cybereyes or a standalone thermal sensor "
            "array mounted at the temple. Detects heat signatures through thin walls."
        ),
        "effect": "Detect heat signatures through non-reinforced walls; +1d on scan vs. hidden targets",
        "glitch_risk": 0.10,
        "humanity_cost": 1,
    },
    "Mantis Blades": {
        "setting": "the_sprawl",
        "name": "Mantis Blades",
        "slot": "limb",
        "description": (
            "Retractable carbon-fiber blades housed in the forearms, deploying "
            "through splits in the wrist. Named for the insect they resemble at full extension."
        ),
        "effect": "+2 on melee damage; can be concealed with a skulk roll",
        "glitch_risk": 0.25,
        "humanity_cost": 2,
    },
    "Dermal Armor": {
        "setting": "the_sprawl",
        "name": "Dermal Armor",
        "slot": "subdermal",
        "description": (
            "Titanium mesh woven beneath the skin in overlapping plates. "
            "Visible as a faint geometric pattern. Extremely effective; extremely uncomfortable."
        ),
        "effect": "Reduce incoming physical harm by 1; -1d on sway actions (obviously augmented)",
        "glitch_risk": 0.05,
        "humanity_cost": 3,
    },
    "Adrenaline Pump": {
        "setting": "the_sprawl",
        "name": "Adrenaline Pump",
        "slot": "torso",
        "description": (
            "A synthetic gland implanted near the adrenal system, delivering "
            "calibrated hormone cocktails on demand. Crash is ugly."
        ),
        "effect": "Activate once per session: take +2d on any physical action this round, then take 2 stress",
        "glitch_risk": 0.20,
        "humanity_cost": 2,
    },
    "Smart Link": {
        "setting": "the_sprawl",
        "name": "Smart Link",
        "slot": "neural",
        "description": (
            "A wireless feedback loop between your nervous system and compatible "
            "smart weapons. The gun becomes an extension of your intent."
        ),
        "effect": "+1d on shoot actions with smart-linked weapons; no off-hand penalty",
        "glitch_risk": 0.10,
        "humanity_cost": 1,
    },
    "Ghost Module": {
        "setting": "the_sprawl",
        "name": "Ghost Module",
        "slot": "subdermal",
        "description": (
            "A subdermal EM suppressor and thermal diffuser that masks your electronic "
            "and thermal footprint. Expensive, military-grade, definitely illegal."
        ),
        "effect": "+2d on skulk actions vs. electronic surveillance; invisible to thermal sensors",
        "glitch_risk": 0.15,
        "humanity_cost": 1,
    },
    "EMP Hardening": {
        "setting": "the_sprawl",
        "name": "EMP Hardening",
        "slot": "subdermal",
        "description": (
            "Faraday shielding and surge protectors woven through all chrome, "
            "protecting augmentations from electromagnetic pulses."
        ),
        "effect": "Immune to EMP disabling effects; +1d on override actions vs. electronic systems",
        "glitch_risk": 0.05,
        "humanity_cost": 1,
    },
    "Memory Palace": {
        "setting": "the_sprawl",
        "name": "Memory Palace",
        "slot": "neural",
        "description": (
            "A co-processor that creates an eidetic memory buffer and runs "
            "background analytical routines. You remember everything. Everything."
        ),
        "effect": "+1d on study actions; retain perfect recall of any scene you've been in",
        "glitch_risk": 0.20,
        "humanity_cost": 2,
    },
    "Synth Muscle": {
        "setting": "the_sprawl",
        "name": "Synth Muscle",
        "slot": "limb",
        "description": (
            "Myomer bundles layered over natural muscle, multiplying output force. "
            "You can punch through a car door. Please don't punch through car doors."
        ),
        "effect": "+1d on scrap actions; lift/carry capacity multiplied by 3",
        "glitch_risk": 0.20,
        "humanity_cost": 2,
    },
    "Razor Nails": {
        "setting": "the_sprawl",
        "name": "Razor Nails",
        "slot": "limb",
        "description": (
            "Monofilament-edged fingertip blades, ceramic-coated to resist scanners. "
            "Subtle enough to pass a casual pat-down; lethal in close quarters."
        ),
        "effect": "+1 on unarmed melee damage; bypass soft armor; largely undetectable",
        "glitch_risk": 0.10,
        "humanity_cost": 1,
    },
    "Magnetic Grip": {
        "setting": "the_sprawl",
        "name": "Magnetic Grip",
        "slot": "limb",
        "description": (
            "Electromagnets embedded in the palms and soles, tunable from zero to "
            "adhesive. Lets you climb ferrous surfaces without gear."
        ),
        "effect": "Climb ferrous surfaces without a roll; +1d on scramble actions involving climbing",
        "glitch_risk": 0.10,
        "humanity_cost": 1,
    },
    "Voice Modulator": {
        "setting": "the_sprawl",
        "name": "Voice Modulator",
        "slot": "torso",
        "description": (
            "A synthetic larynx capable of perfect voice mimicry after a 30-second "
            "sample. Pitch, timbre, accent — indistinguishable from the original."
        ),
        "effect": "+1d on sway and consort actions when impersonating; mimic any recorded voice",
        "glitch_risk": 0.15,
        "humanity_cost": 1,
    },
    "Pain Editor": {
        "setting": "the_sprawl",
        "name": "Pain Editor",
        "slot": "neural",
        "description": (
            "A neural interrupt that selectively blocks pain signals. You still take "
            "damage; you just don't feel it. This is why people die doing things they shouldn't."
        ),
        "effect": "Ignore wound penalties for one scene per session; risk missing critical injury signals",
        "glitch_risk": 0.25,
        "humanity_cost": 3,
    },
    "Bone Lacing": {
        "setting": "the_sprawl",
        "name": "Bone Lacing",
        "slot": "subdermal",
        "description": (
            "Your skeleton has been reinforced with titanium-ceramic composite. "
            "Surviving an impact that would shatter normal bones is no longer impressive — "
            "it's expected."
        ),
        "effect": "Immune to bone-break consequences; reduce fall damage by half",
        "glitch_risk": 0.10,
        "humanity_cost": 3,
    },
    "Toxin Filter": {
        "setting": "the_sprawl",
        "name": "Toxin Filter",
        "slot": "torso",
        "description": (
            "Nano-filter arrays in the bloodstream that neutralize pathogens, toxins, "
            "and recreational drugs with uncomfortable efficiency. Your vice costs more."
        ),
        "effect": "Immune to poison and disease; +1d to resist chemical weapons; vice recovery costs doubled",
        "glitch_risk": 0.05,
        "humanity_cost": 1,
    },
    "Wired Reflexes": {
        "setting": "the_sprawl",
        "name": "Wired Reflexes",
        "slot": "neural",
        "description": (
            "The gold standard of combat augmentation: superconducting neural cables "
            "running a parallel fast-path from senses to muscles. Street samurai pay "
            "entire careers for these."
        ),
        "effect": "+2d on scrap and scramble actions; always act before unaugmented opponents",
        "glitch_risk": 0.30,
        "humanity_cost": 3,
    },
    "Data Spike": {
        "setting": "the_sprawl",
        "name": "Data Spike",
        "slot": "limb",
        "description": (
            "A retractable data probe in the fingertip that can physically jack into "
            "any port, or deliver a lethal voltage spike into electronics or biological targets."
        ),
        "effect": "+1d on hack when physically connected; deal 1 harm to touched electronics or people",
        "glitch_risk": 0.20,
        "humanity_cost": 2,
    },
}


# =========================================================================
# CHROME SLOTS
# =========================================================================

CHROME_SLOTS: Dict[str, Dict[str, Any]] = {
    "neural": {
        "description": "Brain, spine, and nervous system augmentations",
        "max_capacity": 3,
        "notes": "Exceeding capacity requires a humanity check",
    },
    "optical": {
        "description": "Eye and visual system replacements",
        "max_capacity": 2,
        "notes": "Full replacement (both eyes) counts as 2",
    },
    "limb": {
        "description": "Arms, hands, legs, and feet augmentations",
        "max_capacity": 4,
        "notes": "Each major limb section counts separately",
    },
    "torso": {
        "description": "Chest cavity and organ augmentations",
        "max_capacity": 2,
        "notes": "Major organs require full recovery time after installation",
    },
    "subdermal": {
        "description": "Under-skin and skeletal augmentations",
        "max_capacity": 3,
        "notes": "Bone lacing and dermal armor cannot be installed simultaneously",
    },
}


# =========================================================================
# GLITCH EFFECTS
# =========================================================================

GLITCH_EFFECTS: Dict[str, Dict[str, Any]] = {
    "minor": {
        "description": "Transient malfunction — glitchy output, flickering display",
        "examples": [
            "Neural Jack feeds static — +1 difficulty on hack this scene",
            "Cybereyes autofocus loop — penalized scan rolls until rebooted",
            "Smart Link targeting lag — one missed shot before recalibration",
            "Voice Modulator pitch shift — noticeable but not obviously synthetic",
            "Reflex Boosters stutter — one round of normal speed before full restore",
        ],
        "stress_cost": 0,
        "duration": "Scene",
    },
    "major": {
        "description": "Significant failure — chrome temporarily offline or actively harmful",
        "examples": [
            "Neural Jack broadcasts location — enemy trace gains 2 ticks",
            "Mantis Blades won't retract — visible, illegal, and a social liability",
            "Adrenaline Pump fires involuntarily — forced action, then take 2 stress",
            "Pain Editor blocks all sensation — cannot sense injuries this scene",
            "Wired Reflexes feedback loop — take 1 harm from the spike",
        ],
        "stress_cost": 1,
        "duration": "Session",
    },
    "critical": {
        "description": "Catastrophic failure — chrome destroyed or causes serious harm",
        "examples": [
            "Neural Jack short-circuits — unconscious for 1d6 rounds, lose jack until repaired",
            "Dermal Armor calcification — -2 to all physical actions, surgery required",
            "Memory Palace cascade — lose 1 session's worth of retained memories",
            "Bone Lacing micro-fractures — treat as broken bone consequence",
            "Wired Reflexes runaway — take 2 harm and roll Trauma immediately",
        ],
        "stress_cost": 2,
        "duration": "Campaign (requires downtime repair)",
    },
}


# =========================================================================
# CYBERWARE TABLE (Canonical d6 pairs)
# SOURCE: Mona_Rise_Megalopolis.pdf and cbrpnk_04_prdtr.pdf
# Roll 1d6: each result gives two cyberware options (player or GM choice)
# =========================================================================

CYBERWARE_TABLE: Dict[int, Dict[str, Any]] = {
    1: {
        "options": ["Drone Control", "Fireproof Skin"],
        "description": (
            "1: Drone Control — interface implant for piloting drone swarms. "
            "2: Fireproof Skin — subdermal thermal insulation layer."
        ),
    },
    2: {
        "options": ["Eye Scanner", "Artificial Legs"],
        "description": (
            "1: Eye Scanner — optical implant for biometric and environmental reading. "
            "2: Artificial Legs — full prosthetic lower limb replacement."
        ),
    },
    3: {
        "options": ["Adrenaline Rush", "Retractable Blade"],
        "description": (
            "1: Adrenaline Rush — synthetic adrenal pump, on-demand fight/flight surge. "
            "2: Retractable Blade — forearm or wrist-mounted concealed blade."
        ),
    },
    4: {
        "options": ["Blood Valve", "Titanium Bone"],
        "description": (
            "1: Blood Valve — circulatory regulator, controls bleeding and toxin spread. "
            "2: Titanium Bone — skeletal reinforcement, impact and fracture resistance."
        ),
    },
    5: {
        "options": ["Second Heart", "Advanced Nanochip"],
        "description": (
            "1: Second Heart — redundant cardiac pump, survive one fatal hit per session. "
            "2: Advanced Nanochip — neural co-processor for computation and memory."
        ),
    },
    6: {
        "options": ["Pain Inhibitor", "Mouth Laser Cannon"],
        "description": (
            "1: Pain Inhibitor — neural block, ignore wound penalties for one scene. "
            "2: Mouth Laser Cannon — concealed directed-energy weapon, extreme range."
        ),
    },
}


__all__ = ["CHROME", "CHROME_SLOTS", "GLITCH_EFFECTS", "CYBERWARE_TABLE"]
