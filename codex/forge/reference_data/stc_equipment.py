"""
codex.forge.reference_data.stc_equipment
==========================================
Cosmere RPG (Stormlight) equipment reference data.

SOURCE AUTHORITY:
  Primary: STC_Stormlight_Starter_Rules_digital.pdf (Cosmere RPG v1.01, 2025)
  Secondary: SL016_Stonewalkers_GM_Tools_digital.pdf
  Full rules:  STC_Stormlight_Handbook_digital.pdf (too large to extract; rules
               for Shardblades/Shardplate/full item lists are in ch.7)

SOURCED vs EXPANDED notation:
  # SOURCE: Starter Rules p.XX  — directly verified from PDF
  # EXPANDED: not in Starter Rules; derived from novels/handbook description
              or invented for this codebase. May need revision against full handbook.

Contains:
  - SHARDBLADES: Named Shardblades with stats and properties
  - SHARDPLATE: Three grades of Shardplate armor
  - FABRIALS: 10 fabrial devices with stormlight costs
  - SPHERE_TYPES: 15 sphere entries (5 gems × 3 denominations, subset of full 10-gem list)
  - WEAPON_PROPERTIES: Standard Rosharan weapons (abstracted for engine use)
"""

from typing import Any, Dict, List


# =========================================================================
# SPHERE TYPES (Currency / Stormlight Storage)
# SOURCE: Starter Rules p.46 — "Sphere Values in Diamond Marks" table
# =========================================================================
#
# CONFIRMED FROM PDF (p.46) — full 10-gem list:
#   Diamond        Chip=0.2mk   Mark=1mk    Broam=4mk   (LOWEST monetary value)
#   Garnet/Heliodor/Topaz  Chip=1mk  Mark=5mk  Broam=20mk
#   Ruby/Smokestone/Zircon Chip=2mk  Mark=10mk Broam=40mk
#   Amethyst/Sapphire      Chip=5mk  Mark=25mk Broam=100mk
#   Emerald        Chip=10mk   Mark=50mk   Broam=200mk  (HIGHEST monetary value)
#
# IMPORTANT: Diamond is the BASE denomination (lowest value), not highest.
# Emerald is the highest monetary value sphere.
# This is the opposite of Western gem-value intuition.
#
# The test contract (test_fifteen_sphere_types) expects exactly 5 gems × 3 = 15.
# We include the 5 most commonly referenced gems in the novels.
# The full game has 10 gem types; the remaining 5 (Garnet, Heliodor, Topaz,
# Ruby, Emerald) are omitted here to stay within the test contract.
# EXPANDED: Stormlight capacity values are not in the Starter Rules PDF;
# they are inferred from the narrative (larger/more valuable gems = more
# stormlight storage capacity).

SPHERE_TYPES: Dict[str, Dict[str, Any]] = {
    # Diamond — BASE denomination (1 diamond mark = 1 mark)
    # SOURCE: Starter Rules p.46
    "Diamond Chip": {
        "setting": "roshar",
        "gem": "Diamond", "denomination": "Chip",
        "value_in_marks": 0.2,
        "description": (
            "Smallest denomination sphere. A tiny sliver of diamond in a glass bead. "
            "The base unit of Rosharan currency. Gives faint white light when charged."
            # SOURCE: Starter Rules p.46 — Chip=0.2mk, Mark=1mk, Broam=4mk
        ),
        "max_stormlight": 2,  # EXPANDED: low capacity befits smallest denomination
    },
    "Diamond Mark": {
        "setting": "roshar",
        "gem": "Diamond", "denomination": "Mark",
        "value_in_marks": 1,
        "description": (
            "The standard unit of currency on Roshar. A half-carat diamond in a glass "
            "bead. Glows brilliant white when fully charged with Stormlight."
            # SOURCE: Starter Rules p.46
        ),
        "max_stormlight": 10,  # EXPANDED
    },
    "Diamond Broam": {
        "setting": "roshar",
        "gem": "Diamond", "denomination": "Broam",
        "value_in_marks": 4,
        "description": (
            "A two-carat diamond sphere worth 4 marks. Despite being a higher "
            "denomination than a chip, diamond broams are common in everyday trade."
            # SOURCE: Starter Rules p.46 — Broam=4mk
        ),
        "max_stormlight": 40,  # EXPANDED
    },
    # Zircon — Ruby/Smokestone/Zircon tier (2mk chip, 10mk mark, 40mk broam)
    # SOURCE: Starter Rules p.46
    "Zircon Chip": {
        "setting": "roshar",
        "gem": "Zircon", "denomination": "Chip",
        "value_in_marks": 2,
        "description": "A small zircon chip worth 2 marks. Gives faint blue-white light when charged.",
        # SOURCE: Starter Rules p.46
        "max_stormlight": 4,  # EXPANDED
    },
    "Zircon Mark": {
        "setting": "roshar",
        "gem": "Zircon", "denomination": "Mark",
        "value_in_marks": 10,
        "description": "A half-carat zircon sphere worth 10 marks. Moderate stormlight reserve.",
        # SOURCE: Starter Rules p.46
        "max_stormlight": 20,  # EXPANDED
    },
    "Zircon Broam": {
        "setting": "roshar",
        "gem": "Zircon", "denomination": "Broam",
        "value_in_marks": 40,
        "description": "A two-carat zircon sphere worth 40 marks. Useful stormlight reserve.",
        # SOURCE: Starter Rules p.46
        "max_stormlight": 80,  # EXPANDED
    },
    # Smokestone — Ruby/Smokestone/Zircon tier
    # SOURCE: Starter Rules p.46
    "Smokestone Chip": {
        "setting": "roshar",
        "gem": "Smokestone", "denomination": "Chip",
        "value_in_marks": 2,
        "description": "A small smokestone chip worth 2 marks. Nearly black, gives dim glow when charged.",
        # SOURCE: Starter Rules p.46
        "max_stormlight": 4,  # EXPANDED
    },
    "Smokestone Mark": {
        "setting": "roshar",
        "gem": "Smokestone", "denomination": "Mark",
        "value_in_marks": 10,
        "description": "A smokestone sphere worth 10 marks. Favored for its dim, reliable glow.",
        # SOURCE: Starter Rules p.46
        "max_stormlight": 20,  # EXPANDED
    },
    "Smokestone Broam": {
        "setting": "roshar",
        "gem": "Smokestone", "denomination": "Broam",
        "value_in_marks": 40,
        "description": "A large smokestone sphere worth 40 marks.",
        # SOURCE: Starter Rules p.46
        "max_stormlight": 80,  # EXPANDED
    },
    # Amethyst — Amethyst/Sapphire tier (5mk chip, 25mk mark, 100mk broam)
    # SOURCE: Starter Rules p.46
    "Amethyst Chip": {
        "setting": "roshar",
        "gem": "Amethyst", "denomination": "Chip",
        "value_in_marks": 5,
        "description": "A small amethyst chip worth 5 marks. Purple glow when charged.",
        # SOURCE: Starter Rules p.46
        "max_stormlight": 10,  # EXPANDED
    },
    "Amethyst Mark": {
        "setting": "roshar",
        "gem": "Amethyst", "denomination": "Mark",
        "value_in_marks": 25,
        "description": "An amethyst sphere worth 25 marks. Popular with scholars for reading light.",
        # SOURCE: Starter Rules p.46
        "max_stormlight": 50,  # EXPANDED
    },
    "Amethyst Broam": {
        "setting": "roshar",
        "gem": "Amethyst", "denomination": "Broam",
        "value_in_marks": 100,
        "description": "A large amethyst sphere worth 100 marks. Considerable stormlight capacity.",
        # SOURCE: Starter Rules p.46
        "max_stormlight": 200,  # EXPANDED
    },
    # Sapphire — Amethyst/Sapphire tier
    # SOURCE: Starter Rules p.46
    "Sapphire Chip": {
        "setting": "roshar",
        "gem": "Sapphire", "denomination": "Chip",
        "value_in_marks": 5,
        "description": "A small sapphire chip worth 5 marks. Bright blue glow when charged.",
        # SOURCE: Starter Rules p.46
        "max_stormlight": 10,  # EXPANDED
    },
    "Sapphire Mark": {
        "setting": "roshar",
        "gem": "Sapphire", "denomination": "Mark",
        "value_in_marks": 25,
        "description": "A sapphire sphere worth 25 marks. Glows bright blue when fully charged.",
        # SOURCE: Starter Rules p.46
        "max_stormlight": 50,  # EXPANDED
    },
    "Sapphire Broam": {
        "setting": "roshar",
        "gem": "Sapphire", "denomination": "Broam",
        "value_in_marks": 100,
        "description": "A large sapphire sphere worth 100 marks. Wealthy merchants carry these.",
        # SOURCE: Starter Rules p.46
        "max_stormlight": 200,  # EXPANDED
    },
}

# NOTE: Full game includes 10 gem types. Missing from this file (outside test contract):
#   Garnet, Heliodor, Topaz (1mk chip / 5mk mark / 20mk broam)
#   Ruby (2mk chip / 10mk mark / 40mk broam — same tier as Smokestone/Zircon)
#   Emerald (10mk chip / 50mk mark / 200mk broam — HIGHEST monetary value)
# SOURCE: Starter Rules p.46


# =========================================================================
# SHARDBLADES
# =========================================================================
#
# SOURCE NOTES:
#   - GM Tools p.10 (Stonewalkers): Shardblade attack deals SPIRIT damage.
#     Confirmed: Duelist Shardbearer stat block — "22 (2d8+6) spirit damage"
#   - Dead blades take 10 heartbeats to summon (canonical Sanderson lore,
#     confirmed in starter rules context).
#   - Shardblades bypass mundane armor (spirit damage is not reduced by deflect:
#     SOURCE Starter Rules p.27 — "Spirit. Effects that damage both your physical
#     and spiritual self (such as Shardblades) deal spirit damage. This damage
#     type is not reduced by your deflect value.")
#   - Living vs dead Shardblade distinction: SOURCE Stormlight Archive novels.
#   - Named blades (Sylblade, Pattern, Oathbringer): EXPANDED — these are
#     story-accurate names but full game stats are in the Stormlight Handbook.
#   - damage_dice: EXPANDED. Starter Rules shows "2d8+6" for Duelist Shardbearer
#     (Tier 2 rival); actual player-facing Shardblade rules are in the Handbook.

SHARDBLADES: Dict[str, Dict[str, Any]] = {
    "Sylblade": {
        "setting": "roshar",
        "description": (
            "A living Shardblade formed from Sylphrena, an Honorspren. Unlike dead "
            "Shardblades, Sylblade does not kill spren and hums with warm awareness. "
            "Kaladin Stormblessed's signature weapon."
            # EXPANDED: story-accurate name from Stormlight Archive novels
        ),
        "damage_dice": "2d10",  # EXPANDED: full Handbook has exact values
        "damage_type": "spirit",  # SOURCE: Starter Rules p.27 + GM Tools p.10 stat blocks
        "properties": ["Armor Piercing", "Ethereal", "Living Bond"],
        # SOURCE: Starter Rules p.27 — spirit damage not reduced by deflect
        # EXPANDED: "Armor Piercing" and "Ethereal" are our engine terms
        "special": (
            "Living: Does not kill spren on touch. Can be dismissed and re-summoned "
            "as a free action (no 10-heartbeat delay). The blade whispers warnings of danger."
            # SOURCE: novels confirm living blades dismiss/resummon instantly
        ),
        "weight_slots": 2,  # EXPANDED
        "rarity": "legendary",  # EXPANDED
    },
    "Pattern Blade": {
        "setting": "roshar",
        "description": (
            "A Shardblade formed from Pattern, a Cryptic. Manifests as a blade covered "
            "in ever-shifting mathematical patterns. Shallan Davar's weapon."
            # EXPANDED: story-accurate from Stormlight Archive novels
        ),
        "damage_dice": "2d8",  # EXPANDED
        "damage_type": "spirit",  # SOURCE: Starter Rules p.27 + GM Tools stat blocks
        "properties": ["Armor Piercing", "Ethereal", "Living Bond", "Finesse"],
        "special": (
            "Living: Pattern can whisper tactical information about enemies, granting "
            "advantage on attack rolls once per encounter."
            # EXPANDED: flavored from novels
        ),
        "weight_slots": 2,  # EXPANDED
        "rarity": "legendary",  # EXPANDED
    },
    "Oathbringer": {
        "setting": "roshar",
        "description": (
            "A dead Shardblade of ancient make, formerly belonging to the Alethi royal "
            "line. Glows faintly with embedded glyphs. Now bonded to Dalinar Kholin."
            # EXPANDED: story-accurate from Stormlight Archive novels
        ),
        "damage_dice": "2d10",  # EXPANDED
        "damage_type": "spirit",  # SOURCE: Starter Rules p.27
        "properties": ["Armor Piercing", "Ethereal", "Bonded Dead"],
        "special": (
            "Dead Blade: Takes 10 heartbeats to summon. On hit, deadens the limb struck "
            "(target suffers disadvantage on rolls using that limb for 1 hour). "
            "Kills spren on touch."
            # SOURCE: 10-heartbeat summon from novels; limb-deadening from novels
        ),
        "weight_slots": 3,  # EXPANDED
        "rarity": "legendary",  # EXPANDED
    },
    "Shardspear of the Peaks": {
        "setting": "roshar",
        "description": (
            "An ancient Shardblade shaped as a spear rather than a sword, favored by "
            "Stoneward Radiants for its reach. The blade is etched with mountain glyphs."
            # EXPANDED: not a named weapon from the novels; created for engine variety
        ),
        "damage_dice": "2d8",  # EXPANDED
        "damage_type": "spirit",  # SOURCE: Starter Rules p.27
        "properties": ["Armor Piercing", "Ethereal", "Reach"],
        "special": (
            "Reach: Attacks targets up to 10 feet away. On a critical hit, the "
            "spear pins the target in place until they use an action to break free."
            # EXPANDED
        ),
        "weight_slots": 2,  # EXPANDED
        "rarity": "very rare",  # EXPANDED
    },
    "Midnight Essence Blade": {
        "setting": "roshar",
        "description": (
            "A corrupted Shardblade captured from an Unmade's servant. The blade "
            "is dark as night with faint violet Voidlight pulsing along its edges."
            # EXPANDED: not a named weapon from the novels; created for engine variety
        ),
        "damage_dice": "2d10",  # EXPANDED
        "damage_type": "spirit",  # SOURCE: Starter Rules p.27 (Shardblades deal spirit damage)
        # NOTE: Voidlight corruption is a narrative property, not a different damage type
        "properties": ["Armor Piercing", "Ethereal", "Voidlight Tainted"],
        "special": (
            "Voidlight Tainted: On hit, Stormlight healing is halved on the target "
            "for 1 hour. The blade whispers Odium's will to the wielder."
            # EXPANDED: mechanics invented for engine variety
        ),
        "weight_slots": 2,  # EXPANDED
        "rarity": "very rare",  # EXPANDED
    },
}


# =========================================================================
# SHARDPLATE
# =========================================================================
#
# SOURCE NOTES:
#   - Shardplate exists and is distinct from mundane armor: SOURCE novels + GM Tools.
#   - GM Tools stat blocks: Shardplate-wearing characters have high deflect values.
#     The Stonewalkers adventure references Shardbearers who are "Duelist Shardbearers"
#     with Investiture 0 (they carry dead Shardblades, not plate).
#   - Full Shardplate stats are in STC_Stormlight_Handbook_digital.pdf ch.7.
#   - All numeric values below are EXPANDED: derived from game design reasoning
#     and the relative power described in the novels.
#   - Starter Rules p.39 shows Full Plate (mundane) = Deflect 4, Cumbersome [5].
#     Shardplate is explicitly stated as far superior to Full Plate.

SHARDPLATE: Dict[str, Dict[str, Any]] = {
    "Full Shardplate": {
        "setting": "roshar",
        "description": (
            "A complete set of Shardplate covering the wearer from head to foot. "
            "Enormously heavy by mundane standards but feels light to the wearer "
            "due to its stormlight-powered assistance. Grants supernatural strength."
            # SOURCE: Stormlight Archive novels; confirmed referenced in GM Tools
        ),
        "defense_bonus": 8,  # EXPANDED: substantially above Full Plate's deflect 4
        "stormlight_drain": 1,  # EXPANDED: per round while cracked
        "properties": ["Enhanced Strength", "Stormlight Regen", "Full Coverage"],
        "special": (
            "Enhanced Strength: +4 to Strength for encumbrance and grapple checks. "
            "Stormlight Regen: Cracks heal at a rate of 1 point per round when the "
            "wearer has stormlight. At 0 stormlight, plate does not regenerate. "
            "Full Coverage: Immune to limb-deadening from dead Shardblades."
            # EXPANDED: specific numbers are engine design choices
        ),
        "weight_slots": 5,  # EXPANDED
        "rarity": "legendary",  # EXPANDED
    },
    "Partial Shardplate": {
        "setting": "roshar",
        "description": (
            "A mismatched or incomplete set of Shardplate, possibly pieced together "
            "from multiple sources or with some pieces lost over centuries. Still "
            "provides significant protection."
            # EXPANDED: not a defined category in the Handbook; engine convenience
        ),
        "defense_bonus": 5,  # EXPANDED
        "stormlight_drain": 1,  # EXPANDED
        "properties": ["Enhanced Strength", "Stormlight Regen", "Partial Coverage"],
        "special": (
            "Enhanced Strength: +2 to Strength for encumbrance and grapple checks. "
            "Stormlight Regen: As Full Shardplate but slower (1 point per 2 rounds). "
            "Partial Coverage: Limb hits have a 50% chance of bypassing plate."
            # EXPANDED
        ),
        "weight_slots": 3,  # EXPANDED
        "rarity": "very rare",  # EXPANDED
    },
    "Damaged Shardplate": {
        "setting": "roshar",
        "description": (
            "A heavily cracked set of Shardplate that has seen too many battles "
            "without proper stormlight repair. Pieces are missing and the remaining "
            "segments are held together with mundane straps."
            # EXPANDED: engine convenience category
        ),
        "defense_bonus": 3,  # EXPANDED
        "stormlight_drain": 2,  # EXPANDED: higher drain for cracked plate
        "properties": ["Partial Coverage", "Cracked"],
        "special": (
            "Cracked: The plate must be infused with stormlight before each encounter "
            "or its defense_bonus is halved. "
            "Cannot regenerate cracks without significant repair time and stormlight. "
            "May shatter entirely on a critical hit (DC 15 Athletics or one segment breaks off)."
            # EXPANDED: DC changed from Constitution (not a stat in this game) to Athletics
            # SOURCE: Starter Rules p.13 — the six attributes are Strength, Speed,
            # Intellect, Willpower, Awareness, Presence. No "Constitution" attribute.
        ),
        "weight_slots": 4,  # EXPANDED
        "rarity": "rare",  # EXPANDED
    },
}


# =========================================================================
# FABRIALS
# =========================================================================
#
# SOURCE NOTES:
#   - Fabrials are confirmed to exist in the STC RPG: SOURCE Starter Rules p.46,
#     54-55 (Tuning Fork, Unencased Gem, Lantern sphere), GM Tools (Kaiana's
#     surge skills include "Illumination" listed as a Surge Skill on her stat block).
#   - Spanreed: SOURCE Starter Rules p.46 footnote area + GM Tools Ch.2 "Scribe's
#     Spanreed" scene heading — confirmed as a real paired writing fabrial.
#   - Soulcaster: SOURCE Starter Rules p.55 (Unencased Gem entry mentions
#     "recharge fabrials, Shardplate, and half-shards as if the spheres were
#     unencased gemstones"). Soulcasters are referenced in the novel context.
#   - Specific stormlight costs and activation details: EXPANDED.
#   - "Painrial" and "Heatrial" are terms from Sanderson novels (not in Starter
#     Rules PDF); their inclusion here is EXPANDED.
#   - Augmenter/Diminisher/Reverser: canonical fabrial types from novels. EXPANDED
#     for this engine.

FABRIALS: Dict[str, Dict[str, Any]] = {
    "Painrial": {
        "setting": "roshar",
        "description": "A fabrial attuned to a painspren. Detects intense pain in nearby "
                       "creatures, useful for locating wounded allies or enemies.",
        # EXPANDED: Painrial name from Stormlight Archive novels; game stats invented
        "effect": "Sense the location and intensity of painful wounds within 60 feet.",
        "stormlight_cost": 0,  # EXPANDED
        "activation": "Passive while powered. Glows brighter near greater pain.",
        "rarity": "uncommon",  # EXPANDED
    },
    "Heatrial": {
        "setting": "roshar",
        "description": "A fabrial housing a flamespren. Produces sustained heat equivalent "
                       "to a campfire for warmth or heating purposes.",
        # EXPANDED: Heatrial name from Stormlight Archive novels; game stats invented
        "effect": "Generate controlled heat up to 400 degrees for one hour.",
        "stormlight_cost": 1,  # EXPANDED
        "activation": "Twist the housing to activate. Adjustable intensity.",
        "rarity": "common",  # EXPANDED
    },
    "Spanreed": {
        "setting": "roshar",
        "description": "A paired writing device. What is written on one ruby-tipped reed "
                       "appears simultaneously on its partner, regardless of distance.",
        # SOURCE: GM Tools Ch.2 scene 'Scribe's Spanreed' confirms Spanreed is a real
        # paired communication fabrial in the STC RPG.
        "effect": "Communicate in writing with the holder of the paired Spanreed, any distance.",
        "stormlight_cost": 1,  # EXPANDED: specific cost not in Starter Rules
        "activation": "Activate both reeds simultaneously; write to communicate.",
        "rarity": "uncommon",  # EXPANDED
    },
    "Alerter": {
        "setting": "roshar",
        "description": "A fabrial attuned to an anticipationspren. Triggers a warning "
                       "sensation when anything crosses a designated threshold.",
        # EXPANDED: Alerter name from Stormlight Archive novels; game stats invented
        "effect": "Alert the holder when a creature crosses a set boundary (up to 100 feet).",
        "stormlight_cost": 1,  # EXPANDED
        "activation": "Set the boundary area by walking it while the fabrial is active.",
        "rarity": "uncommon",  # EXPANDED
    },
    "Reverser": {
        "setting": "roshar",
        "description": "A fabrial of opposing forces. Repels or attracts objects depending "
                       "on its configuration. Common in Alethi elevators and cranes.",
        # EXPANDED: Reverser name from Stormlight Archive novels; game stats invented
        "effect": "Repel or attract objects or creatures within 20 feet (Athletics DC 13 to resist).",
        # NOTE: Changed Constitution DC to Athletics DC — no Constitution attribute in this game
        # SOURCE: Starter Rules p.13 — six attributes are STR/SPD/INT/WIL/AWA/PRE
        "stormlight_cost": 2,  # EXPANDED
        "activation": "Rotate the casing to switch between attract and repel modes.",
        "rarity": "rare",  # EXPANDED
    },
    "Augmenter": {
        "setting": "roshar",
        "description": "A fabrial that enhances the output of whatever it is paired with. "
                       "Often used in industry to multiply the force of tools.",
        # EXPANDED: Augmenter name from Stormlight Archive novels; game stats invented
        "effect": "Double the output or effect of a mundane tool, weapon, or device for one hour.",
        "stormlight_cost": 2,  # EXPANDED
        "activation": "Attach to a tool and infuse. The tool glows faintly while active.",
        "rarity": "rare",  # EXPANDED
    },
    "Diminisher": {
        "setting": "roshar",
        "description": "The opposite of an Augmenter. Reduces the output or potency of "
                       "whatever it is applied to. Can be used to nullify fires or slow creatures.",
        # EXPANDED: Diminisher name from Stormlight Archive novels; game stats invented
        "effect": "Halve the speed, strength, or intensity of a target effect or creature.",
        "stormlight_cost": 2,  # EXPANDED
        "activation": "Point at target and infuse. Effect lasts one round per stormlight spent.",
        "rarity": "rare",  # EXPANDED
    },
    "Regrowth Fabrial": {
        "setting": "roshar",
        "description": "A fabrial attuned to lifespren. Accelerates natural healing, "
                       "particularly effective on wounds that have not gone septic.",
        # EXPANDED: Regrowth fabrial from Stormlight Archive novels; game stats invented
        # NOTE: 'Regrowth' is also confirmed as an action name in Kaiana's stat block
        # in GM Tools — SOURCE: GM Tools p.5 "Regrowth (Costs 1 Investiture)"
        "effect": "Restore 2d6+4 HP to a touched target. Cannot regrow severed limbs.",
        "stormlight_cost": 3,  # EXPANDED
        "activation": "Hold against the wound while infusing stormlight for one minute.",
        "rarity": "very rare",  # EXPANDED
    },
    "Soulcaster": {
        "setting": "roshar",
        "description": "The most powerful and dangerous fabrials, capable of transforming "
                       "matter. Attuned to three specific materials. Overuse corrupts the wielder.",
        # SOURCE: Stormlight Archive novels confirm Soulcasters corrupt users over time.
        # Mentioned in Starter Rules p.55 context (unencased gems can recharge fabrials).
        "effect": "Transform matter into one of three preset materials (e.g., air, water, stone).",
        "stormlight_cost": 5,  # EXPANDED
        "activation": "Touch target material and concentrate. Deduction DC 12 or suffer Soulcaster's curse.",
        # NOTE: Changed Intellect check to Deduction (the skill) — SOURCE: Starter Rules p.20
        "rarity": "legendary",  # EXPANDED
    },
    "Oathgate Key": {
        "setting": "roshar",
        "description": "A paired fabrial device that, when combined with an Inkspren's "
                       "cooperation, can activate the ancient Oathgates connecting Rosharan cities.",
        # SOURCE: Oathgates are canonical from Stormlight Archive novels.
        # GM Tools reference: Kaiana's stat block shows Surge Skills: Illumination + Progression
        # (not Transportation), so Oathgate activation is a separate Elsecaller/Willshaper ability.
        "effect": "Activate a dormant Oathgate to teleport a party to the linked city.",
        "stormlight_cost": 6,  # EXPANDED
        "activation": "Requires both an Oathgate platform and an Elsecaller or Willshaper Radiant.",
        "rarity": "legendary",  # EXPANDED
    },
}


# =========================================================================
# STANDARD ROSHARAN WEAPONS (non-Shard)
# =========================================================================
#
# SOURCE NOTES:
#   Starter Rules p.48 provides the definitive weapon tables for this RPG.
#
#   LIGHT WEAPONRY (Speed skill):
#     Knife:      1d4 keen,   Melee,         Discreet / Expert: Offhand+Thrown[20/60]
#     Mace:       1d6 impact, Melee,         Momentum / Expert: —
#     Shortspear: 1d8 keen,   Melee,         Two-Handed / Expert: loses Two-Handed
#     Sidesword:  1d6 keen,   Melee,         Quickdraw / Expert: Offhand
#     Staff:      1d6 impact, Melee,         Discreet+Two-Handed / Expert: Defensive
#     Shortbow:   1d6 keen,   Ranged[80/320], Two-Handed / Expert: Quickdraw
#
#   HEAVY WEAPONRY (Strength skill):
#     Axe:        1d6 keen,   Melee,         Thrown[20/60] / Expert: Offhand
#     Hammer:     1d10 impact,Melee,         Two-Handed / Expert: Momentum
#     Longspear:  1d8 keen,   Melee[+5],     Two-Handed / Expert: Defensive
#     Longsword:  1d8 keen,   Melee,         Quickdraw+Two-Handed / Expert: loses Two-Handed
#     Shield:     1d4 impact, Melee,         Defensive / Expert: Offhand
#
#   The engine's WEAPON_PROPERTIES dict uses our own abstracted format (damage_dice,
#   damage_type, properties) for game logic — NOT a 1:1 copy of the weapon table.
#   The real game uses "keen/impact" damage types and skill-based traits.
#   Our engine maps these to a simplified format for internal use.
#   Damage types corrected below:
#     keen   -> SOURCE: Starter Rules p.27 — "Keen. Effects that slice, puncture, or impale"
#     impact -> SOURCE: Starter Rules p.27 — "Impact. Effects that crush or bludgeon"

WEAPON_PROPERTIES: Dict[str, Dict[str, Any]] = {
    "spear": {
        "setting": "cosmere",
        "damage_dice": "1d8",
        "damage_type": "keen",  # SOURCE: Starter Rules p.48 — Shortspear/Longspear = keen damage
        "properties": ["Two-Handed"],
        # SOURCE: Starter Rules p.48 — Shortspear has Two-Handed trait; Longspear has Two-Handed+Reach
        "description": (
            "The favored weapon of the Alethi army. Available as Shortspear (Light, 1d8 keen) "
            "or Longspear (Heavy, 1d8 keen, Melee[+5] reach). Long reach suits the formations "
            "of Alethkar's warcamps."
            # SOURCE: Starter Rules p.48
        ),
    },
    "sword": {
        "setting": "cosmere",
        "damage_dice": "1d6",
        "damage_type": "keen",  # SOURCE: Starter Rules p.48 — Sidesword = 1d6 keen
        "properties": ["Quickdraw"],
        # SOURCE: Starter Rules p.48 — Sidesword has Quickdraw trait
        "description": (
            "A Sidesword: a standard one-handed sword of Rosharan make (1d6 keen, Quickdraw). "
            "Common among lighteyes of middle dahn. Can also be wielded in the offhand with expertise."
            # SOURCE: Starter Rules p.48 — Sidesword entry
        ),
    },
    "axe": {
        "setting": "cosmere",
        "damage_dice": "1d6",
        "damage_type": "keen",  # SOURCE: Starter Rules p.48 — Axe = 1d6 keen (Heavy Weaponry)
        "properties": ["Thrown [20/60]"],
        # SOURCE: Starter Rules p.48 — Axe has Thrown[20/60] trait
        "description": (
            "A sturdy chopping weapon (Heavy Weaponry, 1d6 keen, Thrown[20/60]). "
            "Favored by Horneater and Herdazian fighters."
            # SOURCE: Starter Rules p.48
        ),
    },
    "bow": {
        "setting": "cosmere",
        "damage_dice": "1d6",
        "damage_type": "keen",  # SOURCE: Starter Rules p.48 — Shortbow = 1d6 keen
        "properties": ["Ranged [80/320]", "Two-Handed"],
        # SOURCE: Starter Rules p.48 — Shortbow: Ranged[80/320], Two-Handed
        "description": (
            "A Shortbow (Light Weaponry, 1d6 keen, Ranged[80/320], Two-Handed). "
            "Suitable for use on the Shattered Plains plateaus."
            # SOURCE: Starter Rules p.48
        ),
    },
    "staff": {
        "setting": "cosmere",
        "damage_dice": "1d6",
        "damage_type": "impact",  # SOURCE: Starter Rules p.48 — Staff = 1d6 impact
        "properties": ["Two-Handed", "Discreet"],
        # SOURCE: Starter Rules p.48 — Staff has Discreet and Two-Handed traits
        "description": (
            "A hardwood fighting staff (Light Weaponry, 1d6 impact, Discreet, Two-Handed). "
            "Favored by scholars-turned-fighters and Edgedancer Radiants."
            # SOURCE: Starter Rules p.48
        ),
    },
    "dagger": {
        "setting": "cosmere",
        "damage_dice": "1d4",
        "damage_type": "keen",  # SOURCE: Starter Rules p.48 — Knife = 1d4 keen
        "properties": ["Discreet"],
        # SOURCE: Starter Rules p.48 — Knife has Discreet trait; expert gains Offhand+Thrown[20/60]
        "description": (
            "A Knife (Light Weaponry, 1d4 keen, Discreet). Easily concealed. "
            "With expertise: gains Offhand and Thrown[20/60] traits. "
            "Favored by Lightweavers and spies."
            # SOURCE: Starter Rules p.48
        ),
    },
    "warhammer": {
        "setting": "cosmere",
        "damage_dice": "1d10",
        "damage_type": "impact",  # SOURCE: Starter Rules p.48 — Hammer = 1d10 impact
        "properties": ["Two-Handed"],
        # SOURCE: Starter Rules p.48 — Hammer has Two-Handed trait; expert gains Momentum
        "description": (
            "A Hammer (Heavy Weaponry, 1d10 impact, Two-Handed). Effective against "
            "Shardplate. The impact can crack plate even without a Shardblade."
            # SOURCE: Starter Rules p.48
        ),
    },
    "longsword": {
        "setting": "cosmere",
        "damage_dice": "1d8",
        "damage_type": "keen",  # SOURCE: Starter Rules p.48 — Longsword = 1d8 keen (NOT 1d10)
        "properties": ["Two-Handed", "Quickdraw"],
        # SOURCE: Starter Rules p.48 — Longsword: Quickdraw, Two-Handed; expert: loses Two-Handed
        "description": (
            "A Longsword (Heavy Weaponry, 1d8 keen, Quickdraw, Two-Handed). "
            "With expertise, loses the Two-Handed trait (wielded one-handed)."
            # SOURCE: Starter Rules p.48 — corrected from 1d10 to 1d8
        ),
    },
    "shortsword": {
        "setting": "cosmere",
        "damage_dice": "1d6",
        "damage_type": "keen",  # SOURCE: Starter Rules p.48 — Sidesword = 1d6 keen
        "properties": ["Quickdraw"],
        # EXPANDED: shortsword mapped to Sidesword stats
        "description": (
            "A short, fast blade mapped to the Sidesword entry (Light Weaponry, 1d6 keen, Quickdraw). "
            "Good sidearm for those who carry a spear."
            # SOURCE: Starter Rules p.48 — Sidesword entry
        ),
    },
    "unarmed": {
        "setting": "cosmere",
        "damage_dice": "varies",
        # SOURCE: Starter Rules p.50 — Unarmed Damage table:
        #   Strength 0-2: 1 impact (no die roll)
        #   Strength 3-4: 1d4 impact
        #   Strength 5-6: 1d8 impact
        #   Strength 7-8: 2d6 impact
        #   Strength 9+:  2d10 impact
        "damage_type": "impact",  # SOURCE: Starter Rules p.50 — unarmed = impact damage
        "properties": ["Always Available"],
        # SOURCE: Starter Rules p.50 — "Unarmed attacks don't count as weapon attacks...
        # you can make an unarmed attack even if each of your hands is holding something"
        "description": (
            "Unarmed attack. Damage depends on Strength score (SOURCE: Starter Rules p.50): "
            "STR 0-2: 1 impact (no roll), STR 3-4: 1d4 impact, STR 5-6: 1d8 impact, "
            "STR 7-8: 2d6 impact, STR 9+: 2d10 impact. Uses Athletics skill."
            # SOURCE: Starter Rules p.50 — Unarmed Damage table
        ),
    },
    "mace": {
        "setting": "cosmere",
        "damage_dice": "1d6",
        "damage_type": "impact",  # SOURCE: Starter Rules p.48 — Mace = 1d6 impact
        "properties": ["Momentum"],
        # SOURCE: Starter Rules p.48 — Mace has Momentum trait
        "description": (
            "A Mace (Light Weaponry, 1d6 impact, Momentum). Momentum grants advantage "
            "when attacking after moving 10+ feet in a straight line."
            # SOURCE: Starter Rules p.48-49
        ),
    },
    "shield": {
        "setting": "cosmere",
        "damage_dice": "1d4",
        "damage_type": "impact",  # SOURCE: Starter Rules p.48 — Shield = 1d4 impact
        "properties": ["Defensive"],
        # SOURCE: Starter Rules p.48 — Shield has Defensive trait; expert gains Offhand
        "description": (
            "A Shield (Heavy Weaponry, 1d4 impact, Defensive). Defensive allows using "
            "the Brace action without nearby cover."
            # SOURCE: Starter Rules p.48-49
        ),
    },
}


__all__ = [
    "SHARDBLADES",
    "SHARDPLATE",
    "FABRIALS",
    "SPHERE_TYPES",
    "WEAPON_PROPERTIES",
]
