"""
codex.forge.reference_data.bob_legion
=======================================
Band of Blades legion data: specialists, squad types, Chosen heroes,
mission types, and campaign pressure descriptions.

SOURCE: Band of Blades.pdf
- Specialists: pp.79-115 (Heavy p.79, Medic p.83, Officer p.87, Scout p.91,
               Sniper p.95, Rookie p.99, Soldier p.105)
- Squad types: derived from pp.63-68 and campaign rules
- The Chosen: pp.159-181 (Shreya p.165, Horned One p.171, Zora p.177)
- Mission types: pp.11 (summary), campaign chapter
- Campaign pressures: campaign chapter
"""

from typing import Dict, List, Any

# =========================================================================
# SPECIALISTS
# =========================================================================
# SOURCE: Band of Blades.pdf, pp.79-115
# There are 7 specialist types: Heavy, Medic, Officer, Scout, Sniper, Rookie, Soldier

SPECIALISTS: Dict[str, Dict[str, Any]] = {
    "Heavy": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.79-81
        "description": (
            "A guardian and powerful melee fighter. The Heavy represents the Legion's "
            "unyielding determination on the field of battle. Shock troop and "
            "unbreakable tower of iron."
        ),
        "specialist_action": "ANCHOR",  # SOURCE: p.79
        "abilities": [
            {
                "name": "Bulwark",
                # SOURCE: Band of Blades.pdf, p.80
                "description": (
                    "Spend ANCHOR uses as special armor against consequences to a squad "
                    "you are defending."
                ),
            },
            {
                "name": "Backup",
                # SOURCE: Band of Blades.pdf, p.80
                "description": (
                    "When you protect a squadmate, resist with +1d. When you assist "
                    "someone, their pushes only cost 1 stress."
                ),
            },
            {
                "name": "Tenacious",
                # SOURCE: Band of Blades.pdf, p.80
                "description": (
                    "Penalties from harm are one level less severe (though level 4 "
                    "harm is still fatal)."
                ),
            },
            {
                "name": "Weaponmaster",
                # SOURCE: Band of Blades.pdf, p.80
                "description": (
                    "When you push yourself, you also gain potency in melee combat."
                ),
            },
            {
                "name": "War Machine",
                # SOURCE: Band of Blades.pdf, p.80
                "description": (
                    "When you push yourself, perform a feat of physical force that "
                    "verges on the superhuman or reduce the threat level of all enemies "
                    "you're facing by one."
                ),
            },
            {
                "name": "Vigorous",
                # SOURCE: Band of Blades.pdf, p.81
                "description": (
                    "When you check wounds during rest and recuperation, place one free "
                    "check. When you take harm, clear 1 stress."
                ),
            },
            {
                "name": "Against the Darkness",
                # SOURCE: Band of Blades.pdf, p.81
                "description": (
                    "You and all squadmates that can see you gain +1d to resist fear "
                    "and corruption."
                ),
            },
        ],
        "gear": [
            "Flare Gun",
            "Fine Armor",
            "Fine Hand Weapon",
            "Fitted Heavy Plate (replaces Armor, Normal Load)",
            "Fine Shield OR Fine Heavy Weapon (Normal Load)",
            "Fine Wrecking Kit (Heavy Load)",
            "Fine Tower Shield (Heavy Load)",
        ],
    },

    "Medic": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.83-85
        "description": (
            "A combat physician who keeps soldiers alive long enough to finish the "
            "mission. Field medicine is brutal and fast."
        ),
        "specialist_action": "DOCTOR",  # SOURCE: p.83
        "abilities": [
            {
                "name": "Attache",
                # SOURCE: Band of Blades.pdf, p.84
                "description": (
                    "Deploy on any mission even outside the usual Specialist caps. "
                    "Gained for free on promotion to Medic."
                ),
            },
            {
                "name": "First Aid",
                # SOURCE: Band of Blades.pdf, p.84
                "description": (
                    "Spend one use of Tonics to remove appropriate level 1 harm on any "
                    "one person on your mission."
                ),
            },
            {
                "name": "Not Today",
                # SOURCE: Band of Blades.pdf, p.84
                "description": (
                    "Spend a DOCTOR use on a Legionnaire who has taken level 4 harm "
                    "before they die. Treat them and reduce the wound to level 3 instead."
                ),
            },
            {
                "name": "Doctor Feelgood",
                # SOURCE: Band of Blades.pdf, p.84
                "description": (
                    "Spend one use of Tonics to grant one person potency for a physical "
                    "action."
                ),
            },
            {
                "name": "Field Dressing",
                # SOURCE: Band of Blades.pdf, p.84
                "description": (
                    "At end of mission, expend remaining DOCTOR uses to add one check "
                    "to a Legionnaire's level 2 or 3 harm, once per person."
                ),
            },
            {
                "name": "Chemist",
                # SOURCE: Band of Blades.pdf, p.84
                "description": (
                    "Equip an Alchemical Bandolier on each mission holding four charges "
                    "of alchemicals (Owlsight Oil, Chembalm, Deep, Rage Venom)."
                ),
            },
            {
                "name": "Moral Support",
                # SOURCE: Band of Blades.pdf, p.85
                "description": (
                    "Once a mission, if you tell a meaningful story when the squad "
                    "rests, anyone listening may clear 1 stress."
                ),
            },
        ],
        "gear": [
            "Fine Medic Kit",
            "Tonics (1 use, Light Load)",
            "Holy Symbol of Mercy",
            "Mark of the Healing Goddess",
            "Fine Pistol (Normal Load)",
            "Ammo (Normal Load)",
            "Armor (Normal Load)",
            "Tonics (total 2 uses, Normal Load)",
            "Tonics (total 4 uses, Heavy Load)",
        ],
    },

    "Officer": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.87-91
        # EXPANDED: Officer unique abilities listed at pp.87-91; full playbook not
        # fully imaged in extracted pages. Known specialist action: CHANNELS (p.72).
        "description": (
            "The Officer leads from the front, coordinates squad actions, and manages "
            "resources. Lieutenants, captains, and majors in the Legion have rank "
            "the Marshal must acknowledge."
        ),
        "specialist_action": "CHANNELS",  # SOURCE: p.72
        "abilities": [
            {
                "name": "Veteran",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Take a special ability from another playbook.",
            },
            {
                "name": "Elite",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Gain mastery of two actions (up to rank 4).",
            },
            {
                "name": "Hardened",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Mark two additional stress boxes (up to 10 total).",
            },
            {
                "name": "Survivor",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Take +1 trauma before dying (up to 4 trauma boxes total).",
            },
        ],
        "gear": [
            "Officer's sidearm",
            "Light armor",
            "Signal equipment",
            "Officer's kit (maps, orders, cipher)",
        ],
    },

    "Scout": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.91-95
        # EXPANDED: Scout unique abilities at pp.91-95.
        # Known specialist action: SCROUNGE (p.72).
        "description": (
            "The Legion's eyes and ears. Ranges ahead, maps terrain, identifies enemy "
            "positions. Does not fight fair — fights smart."
        ),
        "specialist_action": "SCROUNGE",  # SOURCE: p.72
        "abilities": [
            {
                "name": "Veteran",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Take a special ability from another playbook.",
            },
            {
                "name": "Elite",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Gain mastery of two actions (up to rank 4).",
            },
            {
                "name": "Hardened",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Mark two additional stress boxes (up to 10 total).",
            },
            {
                "name": "Survivor",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Take +1 trauma before dying (up to 4 trauma boxes total).",
            },
        ],
        "gear": [
            "Light armor",
            "Hand Weapon",
            "Climbing Kit",
            "Compass and Maps",
            "Rations",
        ],
    },

    "Sniper": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.95-99
        # EXPANDED: Sniper unique abilities at pp.95-99.
        # Known specialist action: AIM (p.72).
        "description": (
            "The Legion's long-range fire support. Eliminates high-value targets "
            "before they become a problem. Patience is a weapon as sharp as any blade. "
            "No Sniper should be without a Gun Maintenance Kit."
        ),
        "specialist_action": "AIM",  # SOURCE: p.72
        "abilities": [
            {
                "name": "Veteran",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Take a special ability from another playbook.",
            },
            {
                "name": "Elite",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Gain mastery of two actions (up to rank 4).",
            },
            {
                "name": "Hardened",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Mark two additional stress boxes (up to 10 total).",
            },
            {
                "name": "Survivor",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Take +1 trauma before dying (up to 4 trauma boxes total).",
            },
        ],
        "gear": [
            "Precision rifle (Musket, standard Legion issue)",
            "Spyglass (Lenses)",
            "Gun Maintenance Kit",
            "Light armor",
            "Extra ammunition",
        ],
    },

    "Rookie": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.99-105
        # Rookie has NO specialist action — SOURCE: p.72 "each playbook except Rookie"
        "description": (
            "Fresh soldiers with minimal specialized training. Rookies are acceptable "
            "for assault missions but rely on standard actions. They can advance into "
            "other specialist roles after surviving missions."
        ),
        "specialist_action": None,  # SOURCE: p.72 — Rookies have no specialist action
        "abilities": [
            {
                "name": "Veteran",
                # SOURCE: Band of Blades.pdf, p.77
                # NOTE: Standard abilities are NOT available to Rookies per p.77
                # EXPANDED: Rookie-specific advancement abilities listed at pp.99-105
                "description": "Rookies advance into Specialist roles rather than taking standard abilities.",
            },
            {
                "name": "Grit",
                # SOURCE: Band of Blades.pdf, p.72 — Grit specialist action description
                "description": (
                    "Use the hard lessons of soldiering to weather the worst the war "
                    "has to offer. A GRIT use can reduce the stress cost of a resistance "
                    "roll, once per roll."
                ),
            },
        ],
        "gear": [
            "Standard Legion armor",
            "Musket (Standard Legion issue)",
            "Hand Weapon",
            "Soldier's Kit",
        ],
    },

    "Soldier": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.105-115
        # EXPANDED: Soldier unique abilities at pp.105-115.
        # Known specialist action: GRIT (p.72).
        "description": (
            "Experienced soldiers who form the reliable core of the Legion. They have "
            "seen combat, follow orders under fire, and know how to survive. The "
            "backbone of any squad."
        ),
        "specialist_action": "GRIT",  # SOURCE: p.72
        "abilities": [
            {
                "name": "Veteran",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Take a special ability from another playbook.",
            },
            {
                "name": "Elite",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Gain mastery of two actions (up to rank 4).",
            },
            {
                "name": "Hardened",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Mark two additional stress boxes (up to 10 total).",
            },
            {
                "name": "Survivor",
                # SOURCE: Band of Blades.pdf, p.77
                "description": "Take +1 trauma before dying (up to 4 trauma boxes total).",
            },
        ],
        "gear": [
            "Standard Legion armor",
            "Musket (Standard Legion issue)",
            "Hand Weapon",
            "Soldier's Kit",
            "Shield OR Large Weapon (choice)",
        ],
    },
}

# =========================================================================
# SQUAD TYPES
# =========================================================================
# SOURCE: Band of Blades.pdf — derived from character creation and campaign rules
# Squad types reflect the Legion's troop quality categories

SQUAD_TYPES: Dict[str, Dict[str, Any]] = {
    "Rookies": {
        # SOURCE: Band of Blades.pdf, pp.99-105 — Rookie playbook chapter
        "description": (
            "Fresh soldiers with minimal training. They are motivated and willing "
            "but lack battlefield experience. Acceptable for assault missions per "
            "the starting mission briefs."
        ),
        "scale": 1,
        "quality": 0,
        "armor": 0,
        "features": [
            "No specialist action available.",
            "Can be assigned to any mission type in emergencies.",
            "Advance into Specialist roles after surviving missions.",
        ],
        "morale_threshold": 2,
        "casualty_modifier": +2,
    },
    "Soldiers": {
        # SOURCE: Band of Blades.pdf, pp.105-115 — Soldier playbook chapter
        "description": (
            "Trained, experienced soldiers who form the core of the Legion. They "
            "have seen combat and know how to follow orders under fire. The GRIT "
            "specialist action distinguishes them from Rookies."
        ),
        "scale": 2,
        "quality": 1,
        "armor": 1,
        "features": [
            "GRIT specialist action: reduce stress cost of resistance rolls.",
            "Standard Legion arms and armor.",
            "Reliable in most combat situations.",
        ],
        "morale_threshold": 3,
        "casualty_modifier": 0,
    },
    "Elite": {
        # SOURCE: Band of Blades.pdf — derived from specialist chapters pp.79-95
        "description": (
            "The finest soldiers in the Legion: Heavies, Medics, Officers, Scouts, "
            "and Snipers. Each has a unique specialist action and abilities that "
            "make them exponentially more effective than standard troops."
        ),
        "scale": 3,
        "quality": 2,
        "armor": 2,
        "features": [
            "Unique specialist action (ANCHOR/DOCTOR/CHANNELS/SCROUNGE/AIM).",
            "Multiple special abilities from their playbook.",
            "Two Specialists maximum per mission (except Medics with Attache).",
        ],
        "morale_threshold": 5,
        "casualty_modifier": -2,
    },
}

# =========================================================================
# THE CHOSEN
# =========================================================================
# SOURCE: Band of Blades.pdf, pp.159-181
# There are exactly 3 Chosen traveling with the Legion:
#   Shreya (p.165) — Chosen of Asrika, the Bartan goddess of mercy and healing
#   Horned One (p.171) — Chosen of the Panyar forest god (Silver Dancing Moonlight)
#   Zora (p.177) — Chosen of the Living God of the Zemyati

CHOSEN: Dict[str, Dict[str, Any]] = {
    "Shreya": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.165-169
        "description": (
            "Chosen of Asrika, the Bartan goddess of mercy and healing. A warrior "
            "Chosen focused on military actions and strategy. Shreya's tactical "
            "mind and near-supernatural understanding of strategy drove the Eastern "
            "Kingdoms' latest offensive. Intensely driven by Asrika's fury over the "
            "undead breach of the mercy of death."
        ),
        "favor_types": ["Holy", "Mystic", "Mercy"],  # SOURCE: p.165
        "powers": [
            # SOURCE: Band of Blades.pdf, pp.166-167
            "Book of Hours: All Specialists start with two extra ranks of actions.",
            "Asrika's Mercy: When the Legion recuperates, place one additional healing tick on all Legionnaires.",
            "Asrika's Blessing: Legionnaires always take 1 less corruption.",
            "Asrika's Tears: Liberty campaign actions provide +1 morale and an additional -1 stress.",
            "Anointed: Holy, mystic, and mercy missions all grant mission favor. Start with 1 mission favor already marked.",
            "Battle-Saint: Shreya is threat 5 and has potency against all opponents (normally threat 4).",
            "Blood of the Chosen: When you spend a Religious Supply, you also get a sanctified melee weapon on that mission. It is potent against undead.",
            "War-Saint: The Quartermaster may select a Training campaign action. Each Specialist may mark 3 RESOLVE xp.",
        ],
        "corruption_triggers": [
            "Allowing a blighted (corrupted) Legionnaire to live — Shreya will execute them.",
            "Any Legionnaire hiding corruption from Shreya.",
        ],
        "stats": {
            "scale": 3,
            "quality": 3,
            "armor": 1,
            "threat_level": 4,  # SOURCE: p.163 — Chosen act as threat 4 by default
            "corruption_max": 4,
            "corruption_current": 0,
        },
    },

    "Horned One": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.171-175
        "description": (
            "Shapeshifting Chosen of the Panyar forest god. Focused on mysterious "
            "powers and clever ruses. The Horned One was once Silver Dancing Moonlight, "
            "a young girl filled with rage at the Breaking of the Panyar moon goddess "
            "Nyx. Takes animal forms including raven, bear, and giant hooded serpent. "
            "Each form bears a set of antlers — Silver Dancing Moonlight's Panyar mark."
        ),
        "favor_types": ["Holy", "Mystic", "Wild"],  # SOURCE: p.171
        "powers": [
            # SOURCE: Band of Blades.pdf, pp.172-173
            "Horned One's Bounty: When time passes, ask if the Legion will advance. If it does, do not spend Food Stores.",
            "Horned One's Eyes: If there is a Panyar Specialist on a recon mission, add +1d to the engagement roll.",
            "Horned One's Thews: Legionnaires can spend special armor to resist physical consequences or push themselves on any PROWESS action.",
            "Shapeshifter: Gain 1 intel after completing two primary missions.",
            "Anointed: Holy, mystic, and wild missions all grant mission favor. Start with 1 mission favor already marked.",
            "Great Hunter: The Quartermaster may select a Training campaign action. Each Specialist may mark 3 INSIGHT xp.",
            "Forest's Wings: When you spend Religious Supply on a mission, squads bring up to three animals that can whisper messages to each other and to camp.",
            "Hide of the White Hind: All Specialists can speak to and understand wild beasts.",
        ],
        "corruption_triggers": [
            "Betraying the natural world or allowing its desecration without response.",
        ],
        "stats": {
            "scale": 3,
            "quality": 3,
            "armor": 1,
            "threat_level": 4,  # SOURCE: p.163
            "corruption_max": 4,
            "corruption_current": 0,
        },
    },

    "Zora": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.177-181
        "description": (
            "Chosen of the Living God of the Zemyati. Focused on mighty deeds and "
            "direct assaults. An ancient Zemyati Chosen who tests her followers. "
            "The Living God created nine Chosen that do not burn out — Zora has "
            "defied even death. In battle she bears a fiery circlet above her head "
            "and an empty hilt that generates a blade of solid flame. Troops call "
            "her 'the Fire'."
        ),
        "favor_types": ["Holy", "Mystic", "Glory"],  # SOURCE: p.177
        "powers": [
            # SOURCE: Band of Blades.pdf, pp.178-179
            "Star of the Dawn: When you advance, roll pressure as if 1 lower.",
            "Sacred Seals: All Legionnaires gain special armor vs. magical effects.",
            "Living God's Fury: The Quartermaster may spend a Religious Supply before an assault mission to add +1d to the engagement roll. Legionnaires equip both Reliquaries and Black Shot on this mission.",
            "Living God's Kiss: During a rest and recuperation action, each Legionnaire removes 2 corruption in addition to healing.",
            "Living God's Vigor: Specialists can take an extra level 2 harm.",
            "Heart of Heroes: All Legionnaires add the following xp trigger: If you engaged a higher threat opponent by yourself.",
            "Anointed: Holy, mystic, and glory missions all grant mission favor. Start with 1 mission favor already marked.",
            "Blood of Fire: When Religious Supply is spent on a mission, all Legionnaires may also equip Fire Oil.",
        ],
        "corruption_triggers": [
            "Retreating from battle when victory was possible.",
            "Showing disappointment to those who retreat from battle — Zora already does this.",
        ],
        "stats": {
            "scale": 3,
            "quality": 3,
            "armor": 2,
            "threat_level": 4,  # SOURCE: p.163
            "corruption_max": 4,
            "corruption_current": 0,
        },
    },
}

# =========================================================================
# MISSION TYPES
# =========================================================================
# SOURCE: Band of Blades.pdf — Mission phase chapter, campaign summary p.11
# The six favor/mission types: Holy, Mystic, Mercy, Glory, Knowledge, Wild
# Also: Assault, Recon, Religious, Supply, Rescue, Skirmish as mission categories

MISSION_TYPES: Dict[str, Dict[str, Any]] = {
    "Assault": {
        # SOURCE: Band of Blades.pdf — mission chapter; starting missions pp.168, 174, 180
        "description": (
            "Direct military action against an enemy position. Break through "
            "defenses, eliminate enemy forces, and secure the objective by force. "
            "Engagement rolls may gain +1d from Zora's Living God's Fury ability."
        ),
        "difficulty": 3,
        "reward_type": "morale",
        "typical_objectives": [
            "Destroy enemy supply depot",
            "Break enemy formation to allow Legion advance",
            "Eliminate enemy commander",
            "Breach fortified position",
            "Blow a bridge (starting mission with Shreya)",
        ],
        "typical_consequences": [
            "Casualties",
            "Equipment damage or loss",
            "Enemy counterattack",
            "Alert status raised",
        ],
    },
    "Recon": {
        # SOURCE: Band of Blades.pdf — mission types; Horned One's Eyes applies here
        "description": (
            "Gather intelligence on enemy movements, positions, and capabilities "
            "without engaging in direct combat. Return with actionable information. "
            "Panyar Specialists on recon gain +1d to engagement rolls (Horned One's Eyes)."
        ),
        "difficulty": 2,
        "reward_type": "intel",
        "typical_objectives": [
            "Map enemy patrol routes",
            "Identify enemy commander's location",
            "Assess enemy troop strength",
            "Locate enemy supply lines",
        ],
        "typical_consequences": [
            "Compromised cover",
            "Captured scout",
            "Partial intelligence only",
            "Alerted enemy patrols",
        ],
    },
    "Religious": {
        # SOURCE: Band of Blades.pdf — favor types pp.160-161; Shreya favor: Holy/Mystic/Mercy
        # Religious missions grant favor to all Chosen with Holy or Mystic favor types
        # Breaker's Defilement ability: Religious engagement rolls take -1d
        "description": (
            "Conduct or protect religious ceremonies, secure holy sites, or perform "
            "rituals vital to the Chosen's power and the Legion's morale. Holy and "
            "Mystic favor missions. Note: Breaker's Defilement ability penalizes "
            "these engagement rolls by -1d."
        ),
        "difficulty": 2,
        "reward_type": "morale",
        "typical_objectives": [
            "Perform last rites for Legion dead (Liberty campaign action)",
            "Recover sacred texts or clergy",
            "Guard a shrine",
            "Protect pilgrims on the road",
            "Recover artifacts",
            "Examine sites of power",
        ],
        "typical_consequences": [
            "Ritual interrupted or incomplete",
            "Corruption increase",
            "Reduced effectiveness of blessing",
            "Morale loss from failure",
        ],
    },
    "Supply": {
        # SOURCE: Band of Blades.pdf — Blighter's Attrition Strategies: Supply engagement rolls take -1d
        "description": (
            "Secure food, ammunition, equipment, or other resources the Legion needs "
            "to continue the campaign. Note: Blighter's Attrition Strategies ability "
            "penalizes Supply mission engagement rolls by -1d."
        ),
        "difficulty": 2,
        "reward_type": "supply",
        "typical_objectives": [
            "Raid enemy supply wagon (starting mission with Horned One — reclaim Black Shot)",
            "Protect Legion supply convoy",
            "Forage food from abandoned settlements",
            "Recover Legion supply cache",
        ],
        "typical_consequences": [
            "Supply partially lost",
            "Civilian hostility",
            "Enemy interception",
            "Extended mission timeline",
        ],
    },
    "Rescue": {
        # SOURCE: Band of Blades.pdf — starting mission with Zora involves rescue
        "description": (
            "Extract Legion soldiers, civilians, or other assets from enemy territory "
            "or dangerous situations. Speed and stealth are often more valuable than "
            "firepower."
        ),
        "difficulty": 3,
        "reward_type": "morale",
        "typical_objectives": [
            "Extract captured Legion Commander (Zora's starting mission)",
            "Rescue civilian population",
            "Recover wounded from battlefield",
            "Extract Legion officer with critical information",
        ],
        "typical_consequences": [
            "Partial extraction (not everyone makes it)",
            "Compromised escape route",
            "Casualties during extraction",
            "Intel leak from captives",
        ],
    },
    "Skirmish": {
        # SOURCE: Band of Blades.pdf — Render's Massacre ability: Assault engagement rolls -1d
        # Small-scale engagements to test enemy strength or create diversions
        "description": (
            "Small-scale engagements to test enemy strength, delay pursuit, or create "
            "diversions for larger operations. Hit hard, achieve the objective, and "
            "withdraw. Note: Render's Massacre ability penalizes Assault-type "
            "engagement rolls by -1d."
        ),
        "difficulty": 2,
        "reward_type": "intel",
        "typical_objectives": [
            "Delay enemy advance (buy time for Legion)",
            "Draw enemy forces away from main operation",
            "Test enemy defenses for future assault",
            "Destroy specific enemy asset",
        ],
        "typical_consequences": [
            "Heavier resistance than expected",
            "Extended engagement",
            "Squad separated",
            "Enemy pursuit",
        ],
    },
}

# =========================================================================
# CAMPAIGN PRESSURES
# =========================================================================
# SOURCE: Band of Blades.pdf — Campaign phase chapter, Commander's rolebook
# Pressure increases when the Commander's "Time" clock fills.
# Broken gain new abilities each time a Time clock fills (SOURCE: pp.188, 196, 204).

CAMPAIGN_PRESSURES: Dict[int, Dict[str, str]] = {
    1: {
        "name": "Distant Thunder",
        # SOURCE: Band of Blades.pdf — campaign pressure system
        "description": (
            "The Cinder King's forces are a distant threat. Reports come in of "
            "undead movements far from your position. The Legion has breathing "
            "room to regroup and plan."
        ),
        "effect": "Normal campaign operations. All mission difficulties at base level.",
    },
    2: {
        "name": "Closing In",
        "description": (
            "Enemy forces have been spotted closer than expected. Scouts report "
            "increased undead activity. The Legion must move with more urgency."
        ),
        "effect": (
            "Recon missions are one difficulty higher. Supply missions may "
            "encounter undead patrols."
        ),
    },
    3: {
        "name": "Under Siege",
        "description": (
            "The Cinder King's advance is accelerating. The Legion is being "
            "pressured on multiple fronts. Every mission has higher stakes "
            "and fewer margins for error."
        ),
        "effect": (
            "All mission difficulties +1. Camp phase activities are reduced "
            "by one Downtime action (the Legion must keep moving)."
        ),
    },
    4: {
        "name": "Desperate Hours",
        "description": (
            "The Cinder King is nearly upon the Legion. The retreat has become "
            "a rout in all but name. Soldiers are exhausted, resources are "
            "dwindling, and hope is a commodity few can afford."
        ),
        "effect": (
            "All mission difficulties +2. Morale cannot exceed 3. "
            "Camp phase activities are halved (round down, minimum 0)."
        ),
    },
    5: {
        "name": "Last Stand",
        # SOURCE: Band of Blades.pdf — final pressure level name confirmed by PressureClock test
        "description": (
            "This is the end. The Cinder King's forces surround the Legion. "
            "There is nowhere left to run. The only question is whether the "
            "Legion breaks the siege or breaks entirely."
        ),
        "effect": (
            "All mission difficulties +3. The Legion cannot resupply or recruit. "
            "Each failed mission triggers a Pressure increase event. "
            "This is the final campaign phase."
        ),
    },
}
