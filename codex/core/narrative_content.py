"""
Narrative Content Pools for the Universal Narrative Engine
==========================================================
Pure data module. No class logic -- only dictionaries and lists of templates
used by the narrative engine to populate quests, NPCs, haven events,
settlement descriptions, canopy quests, and dungeon NPCs.

All content is keyed to the Burnwillow setting: a procedural dungeon-crawler
set inside a dying, mile-wide willow tree blighted from within.

Tiers map to depth:
  Tier 1 - The Rootwork (fungal warrens, vermin, rot)
  Tier 2 - The Clockwork (ancient mechanisms, constructs, oil)
  Tier 3 - The Heartwood (corrupted aetherial forest, twisted knights)
  Tier 4 - The Crown (canopy above, final blight source)
"""

from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# 1. QUEST TEMPLATES  --  keyed by chapter (1-4)
# ---------------------------------------------------------------------------

QUEST_TEMPLATES: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {
            "id": "main_01",
            "type": "main",
            "title": "The Root of the Problem",
            "description": (
                "The Rootwork festers beneath Emberhome. Something gnaws at "
                "the foundations -- the mycelial networks are swollen with "
                "blight-sap, and the lower passages groan under the weight "
                "of infected growth. Push deeper. Find the passage to the "
                "Clockwork below and learn what drives the corruption upward."
            ),
            "objective": "reach_tier_2",
            "trigger": "chapter_1_start",
            "reward": {
                "gold": 50,
                "item": "Rootwalker's Charm",
                "description": "A knotted talisman that hums faintly near hidden passages.",
            },
            "turn_in": "leader",
        },
        {
            "id": "side_infestation",
            "type": "side",
            "title": "Pest Control",
            "description": (
                "Blightrats and spore-crawlers have overrun the upper "
                "galleries. The settlers can hear them scratching behind "
                "the walls at night. Clear out at least five of the vermin "
                "before they chew through the last load-bearing root."
            ),
            "objective": "kill_count_tier1_5",
            "trigger": "chapter_1_start",
            "reward": {
                "gold": 20,
                "item": "Rat-Catcher's Belt",
                "description": "A leather belt strung with tiny skulls. Grants +1 to Grit checks against poison.",
            },
            "turn_in": "leader",
        },
        {
            "id": "side_missing",
            "type": "side",
            "title": "The Missing Delver",
            "description": (
                "A delver named Harsk went into the lower Rootwork three "
                "days ago and never came back. His partner, Maren, paces "
                "the tavern floor raw every night. Find Harsk's journal -- "
                "or what's left of him -- and bring it home so Maren can "
                "stop waiting."
            ),
            "objective": "find_item_delver_journal",
            "trigger": "chapter_1_start",
            "reward": {
                "gold": 30,
                "item": "Harsk's Compass",
                "description": "A brass compass whose needle always points toward the nearest exit.",
            },
            "turn_in": "informant",
        },
        {
            "id": "side_samples",
            "type": "side",
            "title": "Spore Samples",
            "description": (
                "The settlement's herbalist needs fresh blight-spore "
                "samples from three different Rootwork chambers. The "
                "spores lose potency within hours, so they must be "
                "harvested on-site and sealed in wax vials. Search "
                "carefully -- not every fungal growth carries the strain "
                "she needs."
            ),
            "objective": "search_count_tier1_3",
            "trigger": "chapter_1_start",
            "reward": {
                "gold": 15,
                "item": "Antitoxin Vial",
                "description": "A single-use vial that neutralises one poison effect.",
            },
            "turn_in": "healer",
        },
    ],
    2: [
        {
            "id": "main_02",
            "type": "main",
            "title": "The Clockwork Below",
            "description": (
                "Beneath the Rootwork lies something older than the tree "
                "itself -- a lattice of brass gears and crystal conduits "
                "built by hands long turned to dust. The mechanisms still "
                "turn, pumping something foul upward through the sapwood. "
                "Find the Overseer construct that governs this level and "
                "shut it down."
            ),
            "objective": "defeat_boss_tier_2",
            "trigger": "reach_tier_2",
            "reward": {
                "gold": 100,
                "item": "Gear-Forged Gauntlet",
                "description": "An articulated gauntlet of interlocking brass plates. Grants +1d6 to Might checks involving mechanisms.",
            },
            "turn_in": "smith",
        },
        {
            "id": "side_clockwork",
            "type": "side",
            "title": "Salvage Run",
            "description": (
                "The smith back in Emberhome says Clockwork-tier scrap is "
                "worth its weight in silver. Bring back three pieces of "
                "intact loot from the Clockwork -- gears, conduits, plating, "
                "anything that hasn't corroded past usefulness."
            ),
            "objective": "loot_count_tier2_3",
            "trigger": "reach_tier_2",
            "reward": {
                "gold": 60,
                "item": "Smith's Favour",
                "description": "A token redeemable for one free weapon or armour upgrade at the forge.",
            },
            "turn_in": "smith",
        },
        {
            "id": "side_map",
            "type": "side",
            "title": "Cartographer's Request",
            "description": (
                "Old Sable in the library has been mapping the Burnwillow "
                "for decades from second-hand accounts. She needs someone "
                "to walk every corridor of the Clockwork level and confirm "
                "her sketches. Visit every room on Tier 2 and report back."
            ),
            "objective": "visit_all_tier2",
            "trigger": "reach_tier_2",
            "reward": {
                "gold": 40,
                "item": "Sable's Annotated Map",
                "description": "A parchment that reveals hidden rooms on the current dungeon floor when studied.",
            },
            "turn_in": "informant",
        },
    ],
    3: [
        {
            "id": "main_03",
            "type": "main",
            "title": "The Heartwood Calls",
            "description": (
                "The corruption runs deeper than machinery. Beyond the "
                "Clockwork, the living heartwood of the Burnwillow pulses "
                "with a sickly amber light. The tree's own immune system "
                "has turned against it -- twisted wardens patrol corridors "
                "of petrified sap. Reach the Heartwood's guardian and learn "
                "what poisoned the tree's core."
            ),
            "objective": "reach_tier_3_boss",
            "trigger": "defeat_boss_tier_2",
            "reward": {
                "gold": 150,
                "item": "Heartwood Splinter",
                "description": "A shard of uncorrupted heartwood. Warm to the touch. Grants +1 Aether modifier while carried.",
            },
            "turn_in": "healer",
        },
        {
            "id": "side_corruption",
            "type": "side",
            "title": "Purge the Blight",
            "description": (
                "Blight-corrupted creatures roam the Heartwood in packs, "
                "spreading infection with every step. The healer begs you "
                "to cull at least three of the worst offenders before the "
                "rot reaches Emberhome's water supply."
            ),
            "objective": "kill_count_tier3_3",
            "trigger": "defeat_boss_tier_2",
            "reward": {
                "gold": 80,
                "item": "Purifier's Censer",
                "description": "A bronze censer that burns blight-ward incense. Enemies in the same room suffer -1 to attack rolls.",
            },
            "turn_in": "healer",
        },
    ],
    4: [
        {
            "id": "main_04",
            "type": "main",
            "title": "Burn the Blight",
            "description": (
                "The source of the corruption has a name, and it waits at "
                "the heart of the dying tree. Every step forward costs more "
                "than the last. The Doom Clock ticks toward midnight. There "
                "is no side quest now -- only the final chamber and whatever "
                "waits inside. End this, or the Burnwillow falls and takes "
                "Emberhome with it."
            ),
            "objective": "defeat_final_boss",
            "trigger": "reach_tier_3_boss",
            "reward": {
                "gold": 300,
                "item": "Ember Crown",
                "description": "A circlet forged from the last living ember of the Burnwillow. Its wearer carries the tree's gratitude -- or its curse.",
            },
            "turn_in": "leader",
        },
    ],
}


# ---------------------------------------------------------------------------
# 2. NPC TEMPLATES  --  Haven (Emberhome) NPCs, one per role
# ---------------------------------------------------------------------------

NPC_TEMPLATES: List[Dict[str, Any]] = [
    {
        "role": "leader",
        "location": "barracks",
        "names": ["Captain Dalla", "Warden Kael", "Marshal Thresh"],
        "descriptions": [
            (
                "A broad-shouldered woman whose chainmail is more patch than "
                "original link. A scar bisects her left eyebrow, pulling it "
                "into a permanent look of mild disbelief. She keeps a tally "
                "of the dead scratched into the pommel of her sword."
            ),
            (
                "A lean man with a soldier's posture and a politician's smile. "
                "His boots are always polished, even when the rest of him is "
                "covered in tunnel dust. He speaks in clipped sentences, each "
                "word measured like a ration."
            ),
        ],
        "greetings": [
            "You're still breathing. That puts you ahead of the last three delvers I sent down. Report.",
            "Another day, another body count. Tell me you brought something useful back.",
        ],
        "rumors": [
            "The Clockwork level's been grinding louder. Old Sable thinks something woke up down there -- something with a schedule.",
            "A patrol found blight-marks on the town gate this morning. The rot's climbing faster than we can cut it back.",
        ],
        "turn_ins": [
            "You did what needed doing. The settlement owes you -- and I always pay my debts. Take this.",
            "Hm. Better than I expected. You've earned a reprieve and a reward. Don't spend it all on ale.",
        ],
    },
    {
        "role": "merchant",
        "location": "market",
        "names": ["Finch", "Old Marrowbone", "Tally"],
        "descriptions": [
            (
                "A wiry halfling perched on a stool behind a counter made "
                "from a split log. Every pocket of his coat bulges with "
                "something -- nails, coins, dried mushrooms, or the odd "
                "stolen ring. He weighs everything by hand and is never wrong."
            ),
            (
                "A heavyset woman with ink-stained fingers and a laugh that "
                "carries across the market. Her stall is chaos -- trinkets "
                "piled on trinkets -- but she knows where every item sits "
                "and will tell you its provenance whether you asked or not."
            ),
        ],
        "greetings": [
            "Buying or selling? Either way, step up. I don't haggle and I don't extend credit.",
            "Fresh from the depths, are you? Let's see what you've dragged back. I'll give you a fair price -- my definition of fair.",
        ],
        "rumors": [
            "A delver tried to sell me a gear-shaft from the Clockwork last week. Thing was still warm. Still ticking. I told him to bury it.",
            "Word is the smith's been buying blight-iron off the black market. Can't blame her -- the forge eats metal faster than we can scavenge it.",
        ],
        "turn_ins": [
            "A deal's a deal. Here's your payment, counted twice. Pleasure doing business.",
            "You held up your end. I respect that more than you know. Take this and come back when you need supplies.",
        ],
    },
    {
        "role": "informant",
        "location": "library",
        "names": ["Old Sable", "Quill", "Archivist Ren"],
        "descriptions": [
            (
                "A gaunt woman surrounded by scrolls, maps, and the faint "
                "smell of lamp oil. Her eyes are milky with cataracts, but "
                "she reads by touch -- fingers tracing ink like old friends. "
                "She has not left this room in eleven years."
            ),
            (
                "A young man with spectacles held together by wire and hope. "
                "He speaks too fast, drops papers constantly, and knows more "
                "about the Burnwillow's history than anyone alive. He is "
                "terrified of the dark."
            ),
        ],
        "greetings": [
            "Ah, a visitor. Sit. Tell me what you saw down there -- every detail. The walls remember, but I need living witnesses.",
            "You're back. Good. I've been cross-referencing your last report with the old surveys. I have... questions.",
        ],
        "rumors": [
            "The tree's ring-patterns suggest it was planted -- not grown. Whatever built the Clockwork also seeded the Burnwillow. Think about that.",
            "I found a reference to something called the 'Rot Warden' in a fragment from the second age. A guardian that turns against its charge when the blight reaches critical mass.",
        ],
        "turn_ins": [
            "This is exactly what I needed. You've filled a gap in the record that's been haunting me for years. Here -- you've earned this.",
            "Remarkable. This confirms a theory I've held since before you were born. Take this as thanks, and know that your name will appear in my chronicle.",
        ],
    },
    {
        "role": "healer",
        "location": "temple",
        "names": ["Sister Vael", "Brother Moss", "The Quiet One"],
        "descriptions": [
            (
                "A soft-spoken woman whose hands are perpetually stained "
                "green from poultice work. She hums while she heals -- the "
                "same three notes, over and over -- and her patients swear "
                "the melody dulls the pain better than any tincture."
            ),
            (
                "A heavyset man with a shaved head and gentle eyes. He "
                "speaks in proverbs, most of which he invented himself. "
                "His temple is half-hospital, half-greenhouse, and the "
                "air tastes of mint and antiseptic."
            ),
        ],
        "greetings": [
            "Let me see your hands. ... You've been gripping your weapon too hard. Sit. I'll wrap those blisters before they turn septic.",
            "You carry the smell of the deep places. Blight-spore in your lungs, I'd wager. Breathe this -- slowly -- and tell me where it hurts.",
        ],
        "rumors": [
            "The blight isn't just killing the tree. It's changing it. I've seen wounds that heal wrong -- bark growing inward, sap running black. The tree is fighting itself.",
            "A wounded delver came in last night raving about light in the Heartwood. Not torchlight -- something alive. Something watching.",
        ],
        "turn_ins": [
            "You've done a kindness the tree won't forget, even if its people do. Take this -- I prepared it while you were gone, just in case you came back alive.",
            "The blight recedes a little more because of what you did today. That matters. Here, this is the least I can offer.",
        ],
    },
    {
        "role": "smith",
        "location": "forge",
        "names": ["Anvil Brenn", "Slag", "Ironwych Dara"],
        "descriptions": [
            (
                "A dwarf-built woman -- not a dwarf, just built like one -- "
                "with forearms like knotted rope and a voice like a bellows. "
                "Her forge is carved into a living root the size of a house, "
                "and the heat never dies because the root itself burns slow "
                "and eternal."
            ),
            (
                "A quiet man with burns up both arms and a mechanical left "
                "hand he built himself from Clockwork scrap. He lets his "
                "work speak for him. Every blade he makes is stamped with "
                "a tiny anvil, and he keeps a ledger of where each one ends "
                "up -- including the ones found next to corpses."
            ),
        ],
        "greetings": [
            "Blade's dull, armour's cracked, and you look like you crawled through a furnace. Standard Tuesday. Put it on the counter.",
            "Back again? Either you're hard on your gear or your gear's hard on you. Let's see the damage.",
        ],
        "rumors": [
            "I pulled a piece of blight-iron out of a construct's chest last week. It was fused with the mechanism -- grown into it, like a bone graft. The blight isn't just infecting flesh anymore.",
            "There's a metal down in the Clockwork I've never seen before. Lighter than steel, harder than iron, and it sings when you strike it. I'd kill for a proper sample.",
        ],
        "turn_ins": [
            "Good haul. I can work with this. Here's your cut -- and next time you're down there, keep an eye out for anything that shines.",
            "You've got an eye for salvage, I'll give you that. This is yours, fair and square. Now get out of my forge before you touch something hot.",
        ],
    },
]


# ---------------------------------------------------------------------------
# 3. HAVEN EVENTS  --  atmospheric flavor for Emberhome between delves
# ---------------------------------------------------------------------------

HAVEN_EVENTS: List[Dict[str, Any]] = [
    {
        "text": (
            "A child runs past carrying a jar of fireflies -- the only light "
            "source that doesn't attract blight-moths. She trips, and the jar "
            "shatters. For a moment, the square is full of tiny, desperate stars."
        ),
        "effect": None,
    },
    {
        "text": (
            "The town bell rings twice -- the signal for a returning patrol. "
            "Settlers gather at the gate, counting heads. The silence when the "
            "count comes up short says everything."
        ),
        "effect": {"type": "doom", "value": 1, "desc": "The grim news weighs on everyone. The Doom Clock advances by 1."},
    },
    {
        "text": (
            "A merchant argues with a delver over a cracked shield. 'It stopped "
            "a blade meant for my heart,' the delver says. 'Then it did its job,' "
            "the merchant replies. 'No refunds on heroism.'"
        ),
        "effect": {"type": "shop_discount", "value": 10, "desc": "The merchant offers you a deal on your next purchase."},
    },
    {
        "text": (
            "Smoke rises from the forge in thick, amber coils. The smith is "
            "burning blight-wood again -- the only fuel hot enough to work "
            "Clockwork steel. The smell is sweet and wrong, like caramelised rot."
        ),
        "effect": {"type": "forge_bonus", "value": 1, "desc": "The smith offers to sharpen your blade. Next forge upgrade is discounted."},
    },
    {
        "text": (
            "An old woman sits on the temple steps, knitting something from "
            "salvaged wire. 'Chainmail,' she says when asked. 'For my cat.' "
            "The cat in question is enormous, battle-scarred, and missing an ear."
        ),
        "effect": None,
    },
    {
        "text": (
            "Rain falls through the canopy gaps -- not water, but thin, amber "
            "sap. It coats everything in a sticky film that takes hours to scrub "
            "off. The children collect it in buckets. The healer says it has "
            "medicinal properties. The merchant says it sells."
        ),
        "effect": {"type": "heal", "value": 3, "desc": "The healer shares a sap-tincture. Party heals 3 HP."},
    },
    {
        "text": (
            "A group of delvers sit in a circle outside the tavern, passing a "
            "bottle and telling lies about the Heartwood. Each story is wilder "
            "than the last. None of them are smiling."
        ),
        "effect": None,
    },
    {
        "text": (
            "The library's single window glows late into the night. Old Sable "
            "is mapping again -- her fingers tracing paths on parchment that "
            "no living person has walked. She hums a tune that sounds older "
            "than the tree."
        ),
        "effect": None,
    },
    {
        "text": (
            "A scuffle breaks out near the market. A delver accuses another of "
            "hoarding Clockwork parts. The Captain arrives, separates them with "
            "a look, and confiscates the parts. 'Emberhome's needs come first.'"
        ),
        "effect": None,
    },
    {
        "text": (
            "The roots beneath the settlement groan -- a deep, wooden sound "
            "that vibrates through the floor and into your teeth. Everyone "
            "freezes. Then it stops, and life resumes as if nothing happened. "
            "No one mentions it."
        ),
        "effect": {"type": "doom", "value": 1, "desc": "An ill omen. The Doom Clock advances by 1."},
    },
    {
        "text": (
            "A pair of crows has built a nest in the barracks rafters. The "
            "Captain tolerates them because they eat the blight-beetles. She "
            "has named them 'Discipline' and 'Morale.'"
        ),
        "effect": None,
    },
    {
        "text": (
            "Tonight the canopy above Emberhome parts just enough to show "
            "a sliver of sky -- the first stars anyone has seen in weeks. "
            "The settlement goes quiet. Someone, somewhere, begins to weep."
        ),
        "effect": None,
    },
    {
        "text": (
            "The healer tends to wounded delvers returning from below. She "
            "notices your party and waves you over. 'Let me take a look at "
            "those cuts before they fester.'"
        ),
        "effect": {"type": "heal", "value": 5, "desc": "The healer patches your wounds. Party heals 5 HP."},
    },
    {
        "text": (
            "The doom bell tolls at midnight. Three deep, resonant notes "
            "that vibrate through the heartwood. The blight creeps closer. "
            "Even the crows go silent."
        ),
        "effect": {"type": "doom", "value": 2, "desc": "The blight surges. The Doom Clock advances by 2."},
    },
    {
        "text": (
            "A travelling tinker has set up shop near the gate, selling "
            "oddments salvaged from deeper tiers. Most of it is junk, but "
            "you spot something useful in the pile."
        ),
        "effect": {"type": "shop_discount", "value": 15, "desc": "The tinker offers you a bargain price."},
    },
    {
        "text": (
            "The forge fires burn unusually bright tonight. The smith hums "
            "as she works, coaxing impossible shapes from stubborn metal. "
            "'Good iron tonight,' she says. 'The tree is generous.'"
        ),
        "effect": {"type": "forge_bonus", "value": 2, "desc": "The smith's inspiration yields a bonus to your next forge visit."},
    },
    {
        "text": (
            "A delver staggers in from the deep, clutching a bundle of "
            "glowing moss. 'Burn it,' she gasps. 'Burn it before it spreads.' "
            "The healer takes it instead. By morning, two sick children are "
            "breathing easier."
        ),
        "effect": {"type": "heal", "value": 2, "desc": "The healer's new remedy eases your aches. Party heals 2 HP."},
    },
    {
        "text": (
            "A quiet funeral at the tree's edge. No names are spoken — just "
            "a count. The Captain scratches another mark into her sword's "
            "pommel and walks away without a word."
        ),
        "effect": None,
    },
    {
        "text": (
            "Someone has strung lanterns between the barracks and the tavern. "
            "For one night, Emberhome almost looks like a place where people "
            "live rather than survive. Almost."
        ),
        "effect": {"type": "heal", "value": 1, "desc": "A rare moment of peace restores the spirit. Party heals 1 HP."},
    },
    {
        "text": (
            "A crack echoes through the settlement as a section of root-wall "
            "collapses. Blight-spores billow into the air. The settlers scramble "
            "to patch the breach before nightfall."
        ),
        "effect": {"type": "doom", "value": 1, "desc": "The blight finds another way in. The Doom Clock advances by 1."},
    },
]


# ---------------------------------------------------------------------------
# 4. SETTLEMENT DESCRIPTIONS  --  keyed by building type
# ---------------------------------------------------------------------------

SETTLEMENT_DESCRIPTIONS: Dict[str, List[str]] = {
    "town_square": [
        (
            "The heart of Emberhome is a clearing where three massive roots "
            "converge, their surfaces worn smooth by generations of foot "
            "traffic. A well sits at the centre, its water tinged amber by "
            "the tree's sap. Notice boards cluster around the well-head, "
            "layered with requests, warnings, and the occasional memorial."
        ),
        (
            "Lanterns hang from hooks driven into living wood, casting pools "
            "of warm light across the packed-earth square. The air smells of "
            "cook-fires and damp bark. A faded banner stretches between two "
            "root-arches, reading: 'Emberhome Endures.' Someone has crossed "
            "out 'Endures' and written 'Persists' in charcoal."
        ),
    ],
    "tavern": [
        (
            "The Hollow Keg is carved into the base of a root as thick as a "
            "granary. Its floor is polished smooth by six centuries of "
            "shuffling feet, and the corner booth still bears the knife-carved "
            "initials of delvers long dead. The ale tastes of mushroom and "
            "regret, but it's warm and the ceiling doesn't drip -- much."
        ),
        (
            "Smoke curls between the low rafters, mingling with the murmur of "
            "a dozen quiet conversations. The barkeep -- a woman with hands "
            "like shovels -- pours without measuring and never overcharges the "
            "wounded. A lute hangs on the wall, unplayed since its owner went "
            "into the Rootwork and didn't come back."
        ),
    ],
    "forge": [
        (
            "Heat hits you three paces from the door. The forge is built "
            "around a living root that burns from within -- a slow, eternal "
            "combustion that the smith feeds with blight-wood and prayer. "
            "Hammers of six different sizes hang on the wall, each named "
            "and each older than anyone in the settlement."
        ),
        (
            "The clang of metal on metal echoes through the root-tunnels "
            "like a heartbeat. Sparks drift upward and die against the "
            "damp ceiling. The smith's workbench is a slab of Clockwork "
            "alloy, scavenged from the depths and too heavy to steal. "
            "Every surface is covered in half-finished projects and cooling "
            "ingots."
        ),
    ],
    "market": [
        (
            "Stalls crowd the widest tunnel in Emberhome, their awnings "
            "stitched from salvaged cloth and bark-leather. Everything has "
            "a price and everything is negotiable except water, medicine, "
            "and ammunition. The merchants shout over each other in a "
            "practised chaos that somehow functions."
        ),
        (
            "The market smells of tallow, dried fungus, and the faint "
            "metallic tang of Clockwork oil. Crates stamped with delver "
            "guild marks line the walls, their contents mysterious until "
            "coin changes hands. A board near the entrance lists today's "
            "prices in chalk -- they change with the Doom Clock."
        ),
    ],
    "barracks": [
        (
            "Rows of cots fill a long, low chamber reinforced with iron "
            "braces. Weapons racks line the walls -- half empty, the rest "
            "holding blades in various states of disrepair. A map of the "
            "known dungeon levels is pinned to the far wall, bristling with "
            "coloured pins that mark patrols, kills, and losses."
        ),
        (
            "The barracks smells of leather, sweat, and the harsh lye soap "
            "the Captain insists on. Boots stand in pairs beneath each cot, "
            "ready for the alarm that comes too often. A duty roster hangs "
            "by the door, names crossed out and rewritten so many times the "
            "parchment is wearing through."
        ),
    ],
    "temple": [
        (
            "The temple is a hollow carved into a root-knot the size of a "
            "chapel. Bioluminescent moss provides a soft green glow that "
            "the healer calls 'the tree's blessing.' Cots for the wounded "
            "line one wall; shelves of dried herbs and stoppered bottles "
            "line the other. The air is thick with mint and quiet grief."
        ),
        (
            "Candles burn in niches carved into the living wood, their wax "
            "pooling in patterns the faithful claim to read like auguries. "
            "A simple altar stands at the centre -- a flat stone draped with "
            "a cloth embroidered with the Burnwillow's silhouette. Beside it, "
            "a basin of clean water reflects the candlelight like a still eye."
        ),
    ],
    "library": [
        (
            "Scrolls and bound journals fill every surface in a chamber that "
            "was never meant to be a library. The shelves are root-growths, "
            "coaxed into shape over decades by a patient hand. A single desk "
            "dominates the centre, buried under maps, ink bottles, and a "
            "magnifying lens the size of a dinner plate."
        ),
        (
            "The library smells of old paper, lamp oil, and the particular "
            "mustiness of knowledge hoarded against extinction. String "
            "connects pins on a corkboard, mapping relationships between "
            "dungeon levels that only the archivist understands. A sign on "
            "the door reads: 'Silence. The walls are listening.'"
        ),
    ],
    "town_gate": [
        (
            "The gate is a wound in the settlement's outer wall -- a gap "
            "between two roots plugged with scrap iron, sharpened stakes, "
            "and stubborn engineering. Two guards stand watch at all hours, "
            "their eyes fixed on the tunnel beyond. The gate opens inward, "
            "because nothing good ever comes from outside."
        ),
        (
            "Claw marks score the outside of the gate -- deep grooves "
            "in iron that speak to the size of what tried to get in last "
            "night. The guards don't talk about it. A bell hangs above the "
            "gate, its rope frayed. When it rings, everyone in Emberhome "
            "knows what it means: something got through."
        ),
    ],
}


# ---------------------------------------------------------------------------
# 5. CANOPY QUEST TEMPLATES  --  alternate path (ascend the tree)
# ---------------------------------------------------------------------------

CANOPY_QUEST_TEMPLATES: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {
            "id": "canopy_main_01",
            "type": "main",
            "title": "The Dimming Flame",
            "path": "ascend",
            "description": (
                "The canopy above Emberhome is dying. Leaves the size of "
                "longboats curl inward, their edges blackened by blight. "
                "The settlement's light -- filtered through a mile of "
                "living wood -- grows dimmer each day. Climb to the first "
                "bough and find what's choking the tree's crown."
            ),
            "objective": "reach_canopy_tier_1",
            "trigger": "chapter_1_start",
            "reward": {
                "gold": 45,
                "item": "Canopy Climber's Harness",
                "description": "A leather harness with bark-grip hooks. Prevents falling in vertical rooms.",
            },
            "turn_in": "leader",
        },
        {
            "id": "canopy_side_nests",
            "type": "side",
            "title": "Clear the Nesting Grounds",
            "path": "ascend",
            "description": (
                "Blight-hawks have nested in the lower canopy, fouling the "
                "branch-roads with corrosive droppings and attacking anyone "
                "who climbs above the settlement line. Clear the nests so "
                "the scouts can resume their patrols."
            ),
            "objective": "destroy_nests_3",
            "trigger": "chapter_1_start",
            "reward": {
                "gold": 25,
                "item": "Hawk Feather Cloak",
                "description": "A cloak woven from blight-hawk plumage. Grants advantage on stealth checks in the canopy.",
            },
            "turn_in": "informant",
        },
    ],
    2: [
        {
            "id": "canopy_main_02",
            "type": "main",
            "title": "The Warden's Challenge",
            "path": "ascend",
            "description": (
                "The mid-canopy is guarded by a Warden -- one of the tree's "
                "ancient protectors, now half-mad with blight-fever. It "
                "attacks anything that moves through its territory, unable "
                "to distinguish friend from infection. Defeat or cure the "
                "Warden to open the path higher."
            ),
            "objective": "defeat_or_cure_warden",
            "trigger": "reach_canopy_tier_1",
            "reward": {
                "gold": 90,
                "item": "Warden's Bark Shield",
                "description": "A shield grown from living bark. Regenerates 1 DR per rest.",
            },
            "turn_in": "healer",
        },
    ],
    3: [
        {
            "id": "canopy_main_03",
            "type": "main",
            "title": "The Crown Harvest",
            "path": "ascend",
            "description": (
                "The upper canopy -- the Crown -- is where the Burnwillow's "
                "last uncorrupted fruit still grows. These golden seed-pods "
                "hold the key to purifying the tree, but they're guarded by "
                "aetherial constructs that consider all climbers to be "
                "parasites. Harvest the fruit before the blight reaches it."
            ),
            "objective": "harvest_crown_fruit",
            "trigger": "defeat_or_cure_warden",
            "reward": {
                "gold": 140,
                "item": "Seed of Renewal",
                "description": "A golden seed that pulses with warmth. Can purify one blight-corrupted item or creature.",
            },
            "turn_in": "healer",
        },
    ],
    4: [
        {
            "id": "canopy_main_04",
            "type": "main",
            "title": "Guardian of the Crown",
            "path": "ascend",
            "description": (
                "At the very top of the Burnwillow, where the last leaves "
                "touch open sky, the Crown Guardian waits. It is the tree's "
                "final defender -- ancient, immense, and utterly convinced "
                "that the only way to save the tree is to burn away "
                "everything that lives within it. Including Emberhome. "
                "Including you."
            ),
            "objective": "defeat_crown_guardian",
            "trigger": "harvest_crown_fruit",
            "reward": {
                "gold": 250,
                "item": "Mantle of the Living Crown",
                "description": "A cloak of living leaves that never wilt. The tree acknowledges its bearer as kin.",
            },
            "turn_in": "leader",
        },
    ],
}


# ---------------------------------------------------------------------------
# 6. DUNGEON NPC TEMPLATES  --  keyed by tier (1-4)
# ---------------------------------------------------------------------------

DUNGEON_NPC_TEMPLATES: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {
            "role": "delver",
            "disposition": "friendly",
            "names": ["Harsk the Unlucky", "Pip Candlewick", "Torva Half-Ear"],
            "descriptions": [
                (
                    "A stocky man in patched leather, his torch guttering in "
                    "the damp air. His pack bulges with salvage and his eyes "
                    "dart to every shadow. A fresh scratch runs down his cheek."
                ),
                (
                    "A young woman with a miner's helmet and a nervous grin. "
                    "She carries a crossbow held together with wire and "
                    "optimism. Her boots squelch with every step."
                ),
                (
                    "A grizzled veteran crouched behind a root-buttress, "
                    "eating something from a tin. He nods at you with the "
                    "weary familiarity of someone who's been down here too "
                    "long and knows it."
                ),
            ],
            "greeting_seeds": [
                "You are a delver who has been exploring the Rootwork for three days. You are tired, a little scared, and glad to see a friendly face. Share a useful tip about a nearby room.",
                "You are a delver who just survived an ambush. You are shaken but trying to be brave. Warn the player about what attacked you.",
            ],
            "greeting_fallbacks": [
                "Thank the roots -- a friendly face. Listen, the tunnel to the east? Don't go that way. I heard something big moving in there, and I'm not the curious type.",
                "You look better equipped than me. That's not saying much. Watch your step around the fungal patches -- some of them pop when you get close. Learned that the hard way.",
            ],
            "lore_seeds": [
                "Share a fragment of Rootwork history -- something carved into a wall, or a story another delver told you.",
                "Mention something strange you saw deeper in the tunnels that you can't explain.",
            ],
            "lore_fallbacks": [
                "There are carvings on the walls down near the water line. Old ones. Older than Emberhome. They show roots growing downward into something -- a city, maybe. Or a machine.",
                "I found a room where the blight doesn't grow. Clean stone, dry air. There was a symbol on the floor -- a gear inside a leaf. Never seen anything like it.",
            ],
            "trade_seeds": [
                "Offer to trade a minor item you found -- a key, a potion, or a piece of scrap -- for something the player might have.",
            ],
            "trade_fallbacks": [
                "I found this key on a dead rat-thing. Don't need it -- I'm heading up, not down. Trade you for a bandage or a ration?",
                "Got a vial of something the healer might want. Smells terrible, but it glows in the dark. Interested?",
            ],
            "quest_seeds": [
                "Ask the player to retrieve something you dropped when you fled from a creature -- a locket, a journal, or a tool.",
            ],
            "quest_fallbacks": [
                "I dropped my partner's compass two rooms back when the rats came. Brass thing, needle always points up. If you find it, I'd owe you. Maren gave it to me and she'll have my hide if I come back without it.",
                "There's a supply cache behind the waterfall in the north tunnel -- I stashed it yesterday, but something's moved in between here and there. If you clear the path, we can split the supplies.",
            ],
        },
        {
            "role": "merchant",
            "disposition": "neutral",
            "names": ["Grub the Peddler", "Silent Kessa", "Nix Rattlebag"],
            "descriptions": [
                (
                    "A hunched figure squatting beside a blanket covered in "
                    "scavenged goods. A lantern dangling from a staff throws "
                    "long shadows across a face that's all angles and "
                    "calculation. A rat perches on one shoulder, watching you."
                ),
                (
                    "A woman draped in a patchwork cloak, her wares arranged "
                    "in neat rows on a flat stone. She doesn't speak -- just "
                    "taps items and holds up fingers to indicate prices. Her "
                    "eyes miss nothing."
                ),
                (
                    "A scrawny man who jingles when he walks, every pocket "
                    "stuffed with trinkets and trade-goods. He grins too wide "
                    "and talks too fast, but his prices are almost reasonable."
                ),
            ],
            "greeting_seeds": [
                "You are a dungeon merchant who sets up shop in relatively safe rooms. You are pragmatic and profit-driven but not dishonest. Greet the player and hint at your wares.",
            ],
            "greeting_fallbacks": [
                "Ah, a customer. Don't get many down here, and the ones I get are usually in a hurry. Browse at your leisure -- but if something's chasing you, I'd appreciate a heads-up.",
                "Buying, selling, or just sheltering? All three cost something, but I'm flexible. Have a look.",
            ],
            "lore_seeds": [
                "Share a rumor you heard from another customer -- something about a hidden room or a dangerous creature.",
            ],
            "lore_fallbacks": [
                "A delver came through yesterday -- half-dead, raving about golden light in the walls. Paid me in Clockwork screws. Good ones, too. Whatever he saw, it wasn't a hallucination.",
                "I've been trading in these tunnels for six years. The blight's worse now than I've ever seen it. The tree's losing, friend. Buy what you need while I'm still here to sell it.",
            ],
            "trade_seeds": [
                "List 2-3 items you have for sale, with prices in gold or barter. Include one oddity that might have a hidden use.",
            ],
            "trade_fallbacks": [
                "I've got torches, rope, a healing salve that mostly works, and a key I pulled off a dead thing. Name your price.",
                "Today's specials: a vial of blight-ward oil, a slightly bent crowbar, and a map fragment that might -- might -- show a shortcut to Tier 2. Interested?",
            ],
            "quest_seeds": [
                "Ask the player to deal with something that's bad for business -- a creature blocking a trade route, or a rival merchant spreading lies.",
            ],
            "quest_fallbacks": [
                "There's a spore-crawler nesting in the corridor I use for supply runs. Kill it and I'll knock ten percent off everything. For a week.",
                "A rival set up shop two levels down and she's undercutting me on torches. I'm not asking you to hurt anyone -- just... let her know this territory's spoken for.",
            ],
        },
        {
            "role": "wounded",
            "disposition": "friendly",
            "names": ["Maren Split-Shield", "Cole the Quiet", "Burned Adra"],
            "descriptions": [
                (
                    "A woman propped against the wall, one arm bound in a "
                    "makeshift splint. Her shield lies beside her, split clean "
                    "down the middle. She breathes through clenched teeth and "
                    "watches the tunnel with the focus of someone who knows "
                    "what's coming."
                ),
                (
                    "A man lying in a hollow between two roots, his face pale "
                    "and his breathing shallow. A crude bandage darkens around "
                    "his midsection. He holds a knife in one hand -- not to "
                    "fight, but because he can't make his fingers let go."
                ),
                (
                    "A figure huddled beneath a cloak, shivering despite the "
                    "heat. Burns cover one side of their face -- not fire "
                    "burns, but chemical ones, the kind blight-acid leaves. "
                    "They flinch when you approach, then relax when they see "
                    "you're human."
                ),
            ],
            "greeting_seeds": [
                "You are a wounded delver who can barely move. You are in pain and frightened but trying to maintain dignity. Ask for help -- healing, an escort, or just someone to sit with.",
            ],
            "greeting_fallbacks": [
                "You real? Not a blight-phantom? ... Good. Listen, I can't walk. Something got my leg two rooms back. If you've got a bandage or a potion, I'd give you everything in my pack for it.",
                "Don't look at me like that -- I'm not dead yet. Just need a minute. Maybe an hour. Maybe someone to watch the door while I rest.",
            ],
            "lore_seeds": [
                "While delirious with pain, mention something you saw that doesn't make sense -- a door that wasn't there before, a sound from below, a figure in the dark.",
            ],
            "lore_fallbacks": [
                "I saw something before I went down. A door -- but not one made by hands. It grew. Bark and iron, woven together. It was breathing. I swear it was breathing.",
                "The rats aren't natural. I watched one stop, look at me -- really look -- and then walk away. Like it decided I wasn't worth the effort. Since when do rats make decisions?",
            ],
            "trade_seeds": [
                "Offer your remaining gear at a steep discount -- you can't use it anyway, and you need the player's help more than you need a shield.",
            ],
            "trade_fallbacks": [
                "Take the shield -- both halves. The smith might be able to reforge it. I won't be swinging it anytime soon. Just... help me get to the exit.",
                "I've got three keys and a scroll I can't read. All yours if you get me out of here alive.",
            ],
            "quest_seeds": [
                "Ask the player to deliver a message to someone in Emberhome -- a loved one, a debtor, or a rival -- in case you don't make it.",
            ],
            "quest_fallbacks": [
                "If I don't make it back, tell Captain Dalla that the east passage is compromised. She'll know what it means. And tell Finch at the market that I'm sorry about the money. He'll know what that means too.",
                "My partner went ahead to scout. Hasn't come back. If you find a woman with red hair and a crossbow two rooms east, tell her I'm alive. If you find her body... bring back her ring. Her mother should have it.",
            ],
        },
    ],
    2: [
        {
            "role": "scholar",
            "disposition": "neutral",
            "names": ["Cogwright Fen", "Lensmaker Drial", "The Indexer"],
            "descriptions": [
                (
                    "A thin man in a waxed coat, hunched over a brass mechanism "
                    "with a jeweler's loupe pressed to one eye. His fingers are "
                    "stained with oil and ink in equal measure. A satchel at "
                    "his side overflows with technical sketches."
                ),
                (
                    "A woman with close-cropped hair and wire-rimmed spectacles, "
                    "taking rubbings from the walls with paper and charcoal. She "
                    "moves with the focused intensity of someone who has "
                    "forgotten that danger exists."
                ),
                (
                    "A figure in a heavy apron, surrounded by disassembled "
                    "Clockwork components laid out in precise rows. They mutter "
                    "to themselves while comparing fragments, occasionally "
                    "scribbling notes in a shorthand only they can read."
                ),
            ],
            "greeting_seeds": [
                "You are a scholar studying the Clockwork mechanisms. You are fascinated, not frightened. Greet the player with academic excitement and ask if they've seen anything interesting.",
            ],
            "greeting_fallbacks": [
                "Remarkable -- another living person. I was beginning to think I'd imagined civilisation. Have you seen the conduit array in the east wing? The crystalline lattice structure suggests a purpose far beyond simple mechanical function.",
                "Careful where you step -- I've catalogued every gear in a three-room radius and I will not have my data contaminated by boot prints.",
            ],
            "lore_seeds": [
                "Explain a theory about who built the Clockwork and why. Include one detail that is probably wrong but dramatically interesting.",
                "Describe a mechanism you've been studying and what you think it does.",
            ],
            "lore_fallbacks": [
                "The Clockwork predates the tree. I'm certain of it. The alloy composition, the gear ratios -- this was built by a civilisation that understood mathematics we've forgotten. And then someone -- or something -- grew a mile-high willow on top of it.",
                "These conduits carry a fluid that isn't water, oil, or sap. It's warm, it pulses, and under magnification, it contains structures that look almost... cellular. I think the Clockwork is alive. Or was.",
            ],
            "trade_seeds": [
                "Offer a Clockwork component or a piece of technical knowledge in exchange for a sample, a tool, or safe passage to another area.",
            ],
            "trade_fallbacks": [
                "I've decoded a partial schematic for the level's lock system. I'll share it if you bring me a crystal conduit from the east chamber -- intact, mind you. Intact.",
                "Take this gear-key. It opens maintenance hatches -- three on this level that I know of. In return, I need you to record what you see in the rooms beyond. Accurate drawings, please. Not interpretations.",
            ],
            "quest_seeds": [
                "Ask the player to investigate a sealed chamber you can't access -- it may contain records, mechanisms, or something dangerous.",
            ],
            "quest_fallbacks": [
                "There's a sealed chamber to the north. Triple-locked, Clockwork-grade. My tools aren't strong enough. Whatever's inside is important enough to lock away with mechanisms that still function after all this time. I need to know what it is.",
                "I found references in the wall-script to something called the 'Overseer Core.' A central processing node for the entire Clockwork level. If I could study it -- even briefly -- I could understand what this place was built to do.",
            ],
        },
        {
            "role": "hermit",
            "disposition": "wary",
            "names": ["Rust", "The Tinker", "Old Gears"],
            "descriptions": [
                (
                    "A person of indeterminate age living inside a hollowed-out "
                    "construct, its chest cavity converted into a cramped but "
                    "functional shelter. Trinkets made from Clockwork scrap "
                    "hang from strings around the entrance like wind chimes."
                ),
                (
                    "A wild-eyed individual wearing armour cobbled together from "
                    "Clockwork plating. They move with jerky, mechanical "
                    "precision, as if they've been down here long enough to "
                    "start imitating the machines."
                ),
                (
                    "A gaunt figure crouching atop a dormant gear-assembly, "
                    "wrapped in a cloak of woven copper wire. They watch you "
                    "approach with the stillness of a predator -- or prey "
                    "that's learned to freeze."
                ),
            ],
            "greeting_seeds": [
                "You are a hermit who has lived in the Clockwork for years. You are suspicious of newcomers but starved for conversation. Test the player before trusting them.",
            ],
            "greeting_fallbacks": [
                "Stop. Don't move. ... Alright, you're not a construct. They don't hesitate. What do you want? And don't say 'help' -- everyone wants help. Be specific.",
                "Another surface-dweller. You all smell the same -- like wood and fear. State your business or keep walking. This section is mine.",
            ],
            "lore_seeds": [
                "Share a secret about the Clockwork that only someone who's lived here would know -- a safe route, a hidden cache, or a behavioral pattern of the constructs.",
            ],
            "lore_fallbacks": [
                "The constructs patrol on a schedule. Seventeen-minute cycles, three routes, one overlap zone. Miss the window and you're scrap. I've been timing them for four years.",
                "There's a maintenance shaft behind the third gear-column -- too small for constructs, just right for a person. It connects to a supply room the builders left stocked. Rations are dust, but the tools still work.",
            ],
            "trade_seeds": [
                "Offer a piece of Clockwork technology you've modified -- something jury-rigged but functional. Name a steep price.",
            ],
            "trade_fallbacks": [
                "I built this from salvage. It disrupts construct targeting for about six seconds. Enough to run. Cost me two years of scavenging. What's it worth to you?",
                "I know where the clean water filters through. I'll show you -- for a price. Fresh food from the surface. Real food. Not mushroom paste.",
            ],
            "quest_seeds": [
                "Ask the player to disable or destroy something that's been encroaching on your territory -- a new construct patrol, a blight growth, or another survivor who's been stealing from your caches.",
            ],
            "quest_fallbacks": [
                "Something new's been patrolling my corridor. Bigger than the standard units. I think the Overseer's adapting. I need it gone before it finds my shelter.",
                "The blight's reached the Clockwork. Saw it creeping through a ventilation shaft yesterday -- tendrils of it, feeling along the walls. If it reaches the main gear-line, this whole level seizes up. And then I'm trapped.",
            ],
        },
    ],
    3: [
        {
            "role": "knight",
            "disposition": "wary",
            "names": ["Ser Velan the Thorn-Bound", "Dame Ashwyn", "The Bark Knight"],
            "descriptions": [
                (
                    "A figure in armour that was once magnificent -- plate and "
                    "chain etched with leaf motifs, now tarnished and cracked. "
                    "Bark grows through the joints, as if the tree is trying "
                    "to reclaim the metal. The knight's visor is up, revealing "
                    "amber eyes that glow faintly in the dark."
                ),
                (
                    "A woman kneeling in a clearing of petrified sap, her "
                    "sword driven into the ground before her. Her armour is "
                    "fused with living wood -- thorns sprout from her "
                    "pauldrons, and moss carpets her greaves. She has not "
                    "moved in what looks like days."
                ),
                (
                    "A towering figure wrapped in bark-plate and silence. "
                    "They carry a halberd of Heartwood -- the blade still "
                    "sharp, the shaft still growing. When they speak, their "
                    "voice resonates like a struck bell, as if the tree "
                    "itself vibrates with their words."
                ),
            ],
            "greeting_seeds": [
                "You are a knight-warden of the Heartwood, half-corrupted by blight. You are torn between duty and despair. Challenge the player to prove they are not part of the infection.",
                "You are an ancient guardian who has been fighting the blight for years. You are exhausted but unbroken. Test the player's resolve before sharing what you know.",
            ],
            "greeting_fallbacks": [
                "Hold. You carry the smell of the upper world -- wood-smoke and clean air. That means you came from above, not below. Speak your purpose, and choose your words with care. The Heartwood listens.",
                "Another delver. The tree sends them and the blight takes them. Tell me -- are you here to save this place, or to loot its corpse? I've seen too many of the latter to assume the former.",
            ],
            "lore_seeds": [
                "Describe the Heartwood as it was before the blight -- a place of beauty and power. Then describe what it has become. Let the contrast carry the weight.",
                "Share what you know about the blight's source -- a fragment of truth wrapped in uncertainty and grief.",
            ],
            "lore_fallbacks": [
                "I was sworn to the tree when the Heartwood still sang. Every root carried a melody, every leaf caught the light like a prayer. Now it screams. The blight didn't invade -- it was invited. Something in the tree's core opened a door and let the rot in.",
                "The corruption radiates from below -- from the place where root meets stone, where the Clockwork joins the living wood. I've fought my way down twice. Both times, the tree itself pushed me back. It's protecting the source. Or the source is controlling it.",
            ],
            "trade_seeds": [
                "Offer a Heartwood weapon or piece of living armour -- powerful but with a cost. The tree's gifts always have conditions.",
            ],
            "trade_fallbacks": [
                "This blade was grown, not forged. The Heartwood shaped it for me in better days. It bites deep against the blight-touched, but it feeds on the wielder's strength. Take it if you're willing to pay that price.",
                "I can offer you the tree's blessing -- a ward against corruption. It won't last forever. Nothing does down here. But it will buy you time, and time is the only currency that matters in the Heartwood.",
            ],
            "quest_seeds": [
                "Ask the player to reach the Heartwood's central chamber and determine whether the tree can still be saved -- or whether mercy requires a different kind of courage.",
            ],
            "quest_fallbacks": [
                "The Heartwood's guardian has turned. I felt it happen -- a shift in the air, a change in the tree's pulse. It guards the path to the core now, killing everything that approaches. I cannot defeat it alone. I'm not sure I can defeat it at all. But someone must try.",
                "There is a chamber at the heart of this level where the sap runs pure -- the last clean wellspring in the tree. If the blight reaches it, the Burnwillow dies. I've been guarding the approach, but I'm one knight and the corruption is endless. Help me hold the line.",
            ],
        },
    ],
    4: [
        {
            "role": "shade",
            "disposition": "neutral",
            "names": ["The Echo of Vael", "Whisper", "The Last Gardener"],
            "descriptions": [
                (
                    "A translucent figure standing where the roots meet open "
                    "sky, their outline shifting like heat-haze. They wear "
                    "the ghost of robes that were once green, and their face "
                    "is a suggestion rather than a certainty. When they speak, "
                    "their voice comes from everywhere and nowhere."
                ),
                (
                    "A shimmer in the air, vaguely humanoid, standing beside "
                    "the last flowering branch of the Burnwillow. Petals "
                    "pass through their hand without moving. They turn to "
                    "face you, and for a moment you see a smile that has been "
                    "waiting centuries for someone to arrive."
                ),
                (
                    "A presence more felt than seen -- a pressure against "
                    "the skin, a scent of green things growing. Where it "
                    "stands, the blight pulls back like a tide retreating "
                    "from the shore. It regards you with the patience of "
                    "something that has watched civilisations rise and "
                    "compost."
                ),
            ],
            "greeting_seeds": [
                "You are the spirit of someone who tended the Burnwillow in its youth -- centuries or millennia ago. You are beyond fear, beyond anger, but not beyond hope. Greet the player with quiet wonder.",
                "You are an echo trapped in the tree's memory. You remember planting the seed. You remember the first leaf. You remember when the Clockwork was built beneath the roots. Share fragments, not certainties.",
            ],
            "greeting_fallbacks": [
                "You climbed all this way. Most turn back at the Heartwood -- the despair is too heavy. But you kept climbing. That tells me something. Sit. I have been waiting for someone worth talking to.",
                "I am what remains when a life is lived entirely in service to a single tree. Don't pity me -- I chose this. I'm only sorry I couldn't stop what came after.",
            ],
            "lore_seeds": [
                "Reveal the true history of the Burnwillow -- who planted it, what it was meant to be, and what went wrong. Speak in fragments, as if memory itself is decaying.",
                "Explain the relationship between the Clockwork and the tree. They were built together -- one to sustain the other. Something broke the balance.",
            ],
            "lore_fallbacks": [
                "The tree was planted to seal something beneath the earth. Not to imprison it -- to digest it. A slow, living furnace burning away a corruption older than the soil. The Clockwork was built to regulate the process. Root and gear, life and mechanism, working in concert. It worked for a thousand years. And then someone -- I think it was someone with kind intentions -- tried to make it work faster.",
                "I remember the seed. Small enough to hold in one palm. It was the last of its kind -- bred for this purpose, grown in a garden that no longer exists. We planted it at the convergence, where five rivers met, and we built the Clockwork to feed it. The tree grew. The corruption shrank. And for a while, the world was a little less broken.",
            ],
            "trade_seeds": [
                "Offer a final gift -- knowledge, a blessing, or a key to the last chamber. You have nothing material to give. What you offer is understanding.",
            ],
            "trade_fallbacks": [
                "I have no gold, no steel, no potions. I have a name -- the name of the thing at the bottom of the tree. The thing the Burnwillow was planted to consume. That name has power. Speak it in the final chamber and the blight will recognise you. Whether that helps or hinders... I cannot say.",
                "Take this memory. Not mine -- the tree's. It will show you the path to the heart, through walls the blight has sealed. The tree wants to be saved. It just forgot how to ask.",
            ],
            "quest_seeds": [
                "Ask the player to finish what you started -- not to kill the blight, but to complete the tree's original purpose. The Burnwillow was always meant to burn.",
            ],
            "quest_fallbacks": [
                "The tree must burn. Not in destruction -- in completion. The Burnwillow was always a furnace. It was planted to burn away the old corruption, and when its work was done, it was meant to release its ashes and let new growth begin. The blight is the tree refusing to let go. Help it remember what it was made to do.",
                "Find the core. Not the Clockwork core -- the living one, where root and gear and sap converge. There is a seed there, dormant, waiting. It is the next tree -- the one that grows from the Burnwillow's ashes. Plant it. Let the old tree finish burning. Let the cycle begin again.",
            ],
        },
    ],
}


# ---------------------------------------------------------------------------
# 7. DUNGEON NPC QUEST TEMPLATES  --  quests offered by dungeon NPCs
# ---------------------------------------------------------------------------

DUNGEON_NPC_QUEST_TEMPLATES: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {
            "id": "dnpc_escort_t1",
            "title": "Escort to Safety",
            "description": (
                "A frightened delver begs you to escort them back to the "
                "stairway. Keep them alive through the Rootwork's dangers."
            ),
            "objective": "reach_tier_1",
            "reward": {"gold": 25, "item": "Delver's Ration", "description": "A sealed packet of dried roots and mushroom jerky. Heals 3 HP when consumed."},
        },
        {
            "id": "dnpc_retrieve_t1",
            "title": "Lost Toolkit",
            "description": (
                "A stranded scholar dropped their toolkit somewhere in "
                "these corridors. Search two rooms to find the scattered pieces."
            ),
            "objective": "search_count_tier1_2",
            "reward": {"gold": 20, "item": "Makeshift Lockpick", "description": "A bent wire that grants +1 to lockpicking checks."},
        },
        {
            "id": "dnpc_pest_t1",
            "title": "Vermin Bounty",
            "description": (
                "A merchant trapped in the dungeon will pay for every "
                "blightrat you kill. Slay three to earn the bounty."
            ),
            "objective": "kill_count_tier1_3",
            "reward": {"gold": 15, "item": "Rat-Tooth Pendant", "description": "A necklace of rodent fangs. Crude, but the superstitious say it wards off vermin."},
        },
    ],
    2: [
        {
            "id": "dnpc_salvage_t2",
            "title": "Clockwork Salvage",
            "description": (
                "A tinkerer wants you to loot three pieces of Clockwork "
                "mechanism from this tier. Gears, springs, anything intact."
            ),
            "objective": "loot_count_tier2_3",
            "reward": {"gold": 45, "item": "Tinkerer's Wrench", "description": "A multi-jointed wrench that can disable simple traps."},
        },
        {
            "id": "dnpc_scan_t2",
            "title": "Map the Clockwork",
            "description": (
                "A cartographer needs you to search three rooms on this "
                "tier to verify her maps. Thoroughness is key."
            ),
            "objective": "search_count_tier2_3",
            "reward": {"gold": 35, "item": "Annotated Schematic", "description": "A folded parchment showing hidden passages. Reveals one secret room."},
        },
    ],
    3: [
        {
            "id": "dnpc_purge_t3",
            "title": "Blight Purge",
            "description": (
                "A desperate warden begs you to kill four blight-corrupted "
                "creatures before they overrun the upper levels."
            ),
            "objective": "kill_count_tier3_4",
            "reward": {"gold": 70, "item": "Warden's Signet", "description": "A ring bearing the Heartwood seal. Grants audience with the tree's defenders."},
        },
        {
            "id": "dnpc_harvest_t3",
            "title": "Heartwood Samples",
            "description": (
                "A scholar needs uncorrupted heartwood samples. Search "
                "three rooms in the Heartwood tier to find them."
            ),
            "objective": "search_count_tier3_3",
            "reward": {"gold": 60, "item": "Heartwood Vial", "description": "A glass vial of golden sap. Restores 5 HP when consumed."},
        },
    ],
    4: [
        {
            "id": "dnpc_final_t4",
            "title": "The Last Witness",
            "description": (
                "A dying guardian asks you to reach the Crown's apex and "
                "bear witness to what lies there. Knowledge is its own reward."
            ),
            "objective": "reach_tier_4",
            "reward": {"gold": 100, "item": "Crown Shard", "description": "A fragment of crystallised canopy. Pulses with fading warmth."},
        },
        {
            "id": "dnpc_hunt_t4",
            "title": "Crown Hunter",
            "description": (
                "An ancient protector tasks you with slaying three of the "
                "corrupted crown guardians that have turned against the tree."
            ),
            "objective": "kill_count_tier4_3",
            "reward": {"gold": 120, "item": "Guardian's Bark-Plate", "description": "Armour grown from living wood. Grants +1 DR."},
        },
    ],
}


# ---------------------------------------------------------------------------
# 8. ROOM FRAGMENTS — Hand-written narrative fragments keyed by (room_type, tier)
# ---------------------------------------------------------------------------
# The model's job becomes *connecting* fragments, not inventing from nothing.
# Each key is (room_type_str, tier_int) → list of 3 fragments.
# WO-V47.0: Narrative Intelligence Layer.

ROOM_FRAGMENTS: Dict[str, List[str]] = {
    # --- TIER 1: The Rootwork (fungal warrens, vermin, rot) ---
    ("normal", 1): [
        "Rust flakes drift like red snow from the ceiling.",
        "The walls weep dark sap that pools in the cracks between flagstones.",
        "Pale mycelium threads the mortar like veins beneath skin.",
    ],
    ("forge", 1): [
        "The anvil is split clean in two — something nests in the crack.",
        "Bellows hang from the wall like deflated lungs, still wheezing.",
        "Slag heaps glow faintly orange, too warm for a dead forge.",
    ],
    ("library", 1): [
        "Sodden pages carpet the floor like fallen leaves.",
        "Shelf-rot has turned the wood soft as bread. Books slump into each other.",
        "A reading desk stands untouched, its candle melted to a puddle of wax.",
    ],
    ("treasure", 1): [
        "Something glints behind a curtain of hanging rootlets.",
        "A chest sits in the corner, its lock furred with green mold.",
        "The room smells of copper and old blood — someone stashed value here.",
    ],
    ("boss", 1): [
        "The chamber ceiling arches high, lost in shadow. Something breathes up there.",
        "Bones crunch underfoot — not human, but close enough to worry.",
        "A throne of tangled roots dominates the far wall, seat polished smooth by use.",
    ],
    ("corridor", 1): [
        "The passage narrows to a squeeze. Your torch gutters in a draft.",
        "Water drips from above in a rhythm that sounds almost like speech.",
        "Root tendrils hang from the ceiling, brushing your face as you pass.",
    ],
    ("secret", 1): [
        "The wall here is hollow — you can feel the air change when you press.",
        "A narrow gap behind a collapsed shelf. Someone bricked this up on purpose.",
        "Scratch marks on the inside of a sealed door. Someone wanted out.",
    ],
    ("start", 1): [
        "Daylight fades behind you. Ahead, the dark is absolute.",
        "The entrance exhales damp air that tastes of mushrooms and regret.",
        "Rough-hewn steps descend into the root network. No guardrails.",
    ],
    # --- TIER 2: The Clockwork (ancient mechanisms, constructs, oil) ---
    ("normal", 2): [
        "Gears the size of cartwheels tick overhead, measuring nothing.",
        "The floor vibrates with the pulse of some deeper engine.",
        "Brass pipes run along the walls, hissing steam at irregular intervals.",
    ],
    ("forge", 2): [
        "The forge's heart still glows — not with fire, but with something older.",
        "Mechanical arms hang from tracks above, frozen mid-swing.",
        "A crucible of liquid brass sits cooling. The surface hasn't skinned over.",
    ],
    ("library", 2): [
        "Dust-choked shelves sag under crumbling tomes.",
        "A brass orrery clicks overhead, its planets long misaligned.",
        "Punch-card stacks line the walls — a language no one alive can read.",
    ],
    ("treasure", 2): [
        "Behind a cage of interlocking gears, something gleams.",
        "The lock on this vault is a puzzle — three rotating cylinders.",
        "Oil-stained velvet lines a display case. Most of the contents are gone.",
    ],
    ("boss", 2): [
        "The room hums at a frequency you feel in your teeth.",
        "A central mechanism dominates the space — half clock, half altar.",
        "Scorch marks radiate from the center like a frozen explosion.",
    ],
    ("corridor", 2): [
        "The corridor clicks with every step — pressure plates, or just old metal.",
        "Steam vents line the passage, their timing just irregular enough to worry.",
        "Copper conduits overhead spark and pop, casting stroboscopic shadows.",
    ],
    ("secret", 2): [
        "A panel slides aside with a hydraulic sigh.",
        "The mechanism that sealed this room required a key no one carries anymore.",
        "Behind the false wall: a maintenance crawlspace, tools still racked.",
    ],
    ("start", 2): [
        "The stairwell transitions from root to riveted metal. A threshold.",
        "Oil slicks the steps. Below, something ticks like a massive heartbeat.",
        "Warmth rises from below — furnace heat, mechanical and relentless.",
    ],
    # --- TIER 3: The Heartwood (corrupted aetherial forest, twisted knights) ---
    ("normal", 3): [
        "The wood here is alive — growing, but wrong. Bark spirals inward.",
        "Crystallized sap catches your torchlight and refracts it into rainbows.",
        "A sound like singing comes from deep within the walls.",
    ],
    ("forge", 3): [
        "The anvil is grown from living wood, its surface harder than iron.",
        "Aetherial fire burns cold and violet in the hearth.",
        "Half-finished weapons hang from branches — grown, not forged.",
    ],
    ("library", 3): [
        "The books grow from the shelves here. Pages are pressed leaves.",
        "Text writhes across a living scroll, rewriting itself as you watch.",
        "A tree has swallowed the reading nook. Its knotholes glow with knowledge.",
    ],
    ("treasure", 3): [
        "Amber encases something valuable — and something still moving.",
        "The treasure here pulses with aetherial light, warm to the touch.",
        "Crystalline growths jut from the walls, each containing a small object.",
    ],
    ("boss", 3): [
        "The chamber is a cathedral of living wood, vaulted and breathing.",
        "Corruption and beauty war here — half the room blooms, half rots.",
        "A knight stands at the center, perfectly still. Its armor is bark.",
    ],
    ("corridor", 3): [
        "The passage breathes — walls contracting slightly with each step.",
        "Bioluminescent fungi light the way in shifting blues and greens.",
        "Thorned vines have reclaimed this corridor. They twitch when touched.",
    ],
    ("secret", 3): [
        "A doorway of woven branches, visible only when the light shifts.",
        "The heartwood here is hollow — someone carved a sanctuary inside.",
        "Press the knothole and the wall unfolds like a flower.",
    ],
    ("start", 3): [
        "The transition is abrupt — metal gives way to living wood.",
        "The air changes. Charged, electric, like before a storm.",
        "Roots and gears interlock at the threshold, neither winning.",
    ],
    # --- TIER 4: The Crown (canopy above, final blight source) ---
    ("normal", 4): [
        "Sunlight filters through dead branches in pale, dusty shafts.",
        "The wood here is hollow. Everything echoes.",
        "Ash drifts like snow from the canopy above.",
    ],
    ("forge", 4): [
        "The forge is cold. Whatever powered it has been spent.",
        "Tools of a craft beyond mortal understanding hang unused.",
        "The hearth holds only ash and a single ember that refuses to die.",
    ],
    ("library", 4): [
        "Every book is blank. The words have been consumed.",
        "A single tome remains, chained to its pedestal, cover warm to the touch.",
        "The shelves are bare. Knowledge fled before the blight arrived.",
    ],
    ("treasure", 4): [
        "The vault is open. What remains glows with the last light of the tree.",
        "Crown-shards litter the floor like broken stained glass.",
        "A single object rests on a pedestal of dead wood. It radiates warmth.",
    ],
    ("boss", 4): [
        "The sky is visible through the shattered crown. Wind howls.",
        "This is where it ends — or where it began. Hard to tell the difference.",
        "The blight's heart beats here, visible, terrible, and almost beautiful.",
    ],
    ("corridor", 4): [
        "The walkway spans open air. Below, the tree drops away into darkness.",
        "Dead branches form a bridge. They creak but hold. For now.",
        "Wind carries ash and the smell of distant fire.",
    ],
    ("secret", 4): [
        "A chamber sealed by the tree itself — grown shut against the blight.",
        "The last clean room in the Crown. It smells of green and rain.",
        "Hidden behind a cascade of dead leaves: a door that was never meant to open.",
    ],
    ("start", 4): [
        "You emerge into light — blinding after the depths. The canopy stretches above.",
        "The final ascent. Wind replaces the underground stillness.",
        "From here, you can see how far the blight has spread. Too far.",
    ],
}


# ---------------------------------------------------------------------------
# 9. MODULAR QUEST MODULES — Faction-introducing story quests (#218-#221)
# ---------------------------------------------------------------------------
# These are narrative quest modules triggered by gameplay events (not chapter
# progression). Each represents a faction contact point with 3-5 conceptual
# rooms, social scenes, and faction reputation consequences.
#
# Trigger conditions: checked by quest_trigger.py / narrative_engine.py
# Objectives: matched by check_objective() triggers
# Prerequisites: gated by prior quest completion

MODULAR_QUEST_TEMPLATES: List[Dict[str, Any]] = [
    # ─── #218: THE HIVE'S DYING QUEEN ───────────────────────────────────
    # First faction contact. Introduces the Hive, the gift-cycle, and the
    # Leech Cascade tension. Trigger: Zone 1-2 NPC encounter.
    {
        "id": "mod_hive_queen",
        "type": "side",
        "title": "The Hive's Dying Queen",
        "description": (
            "A Hive scout — thorax scarred, antennae twitching — stumbles into "
            "your path. She is Stinger, last of the Queen Mother's honour guard. "
            "The breeding chambers are under siege: Rot-choked fungi have sealed "
            "the royal gallery, and the Queen's sap-song grows fainter by the hour. "
            "Stinger offers the Hive's oldest bargain — the gift-cycle. Help them, "
            "and honeydew flows. Refuse, and the Leech Cascade begins."
        ),
        "objective": "kill_count_tier1_3",
        "trigger": "zone_1",
        "tier_hint": 1,
        "reward": {
            "gold": 40,
            "item": "Honeydew Vial",
            "description": "A wax-sealed vial of Queen's honeydew. Heals 2d6+2 HP. The Hive remembers your aid.",
            "faction_rep": {"hive": 2},
        },
        "turn_in": "quest_giver",
        "quest_npcs": [
            {
                "name": "Stinger",
                "role": "quest_giver",
                "description": (
                    "A wasp-kin scout with compound eyes and a voice like "
                    "dry reeds. Half her wings are torn. She clicks when "
                    "she speaks, translating pheromone-language into words "
                    "that almost make sense."
                ),
                "faction": "hive",
                "disposition": "wary",
                "dialogue_greeting": (
                    "You. Soft-shell. The Queen dies. The wax cracks. The "
                    "Rot-things grow fat on our dead. I am Stinger. I ask — "
                    "not beg — for the gift-cycle. We give, you give. This "
                    "is the way of the Hive."
                ),
                "dialogue_quest": (
                    "Three Rot-bloated crawlers nest in the royal gallery. "
                    "Kill them. Burn the fungal seals. The Queen cannot "
                    "breathe. If you do this, the honeydew is yours. "
                    "If you walk away, the Leech Cascade begins — the Hive "
                    "takes what it needs from whoever passes."
                ),
                "dialogue_turn_in": (
                    "The gallery breathes again. The Queen's song strengthens. "
                    "You have earned the gift-cycle. Take this — honeydew, "
                    "the Hive's covenant. Return when the wax calls."
                ),
            },
        ],
        "rooms": [
            {
                "name": "Wax-Sealed Gallery",
                "description": "Hexagonal chambers of dried wax and amber resin. The walls hum with a subsonic vibration — the Queen's sap-song, growing weaker.",
                "enemies": ["Rot Crawler", "Rot Crawler", "Spore-Bloated Drone"],
                "tier": 1,
            },
            {
                "name": "Royal Antechamber",
                "description": "The air is thick with pheromones. Honeycombs line the walls, some still dripping golden liquid. A massive sealed door vibrates faintly.",
                "enemies": [],
                "loot": ["Wax Sealant", "Honeydew Vial"],
                "tier": 1,
            },
            {
                "name": "Queen's Audience Chamber",
                "description": "The Queen Mother fills the chamber — vast, translucent, her body a living map of the Hive's network. She cannot speak. Stinger translates the pheromone-clouds.",
                "social": True,
                "tier": 1,
            },
        ],
    },

    # ─── #219: OLD CAP'S SECRET ─────────────────────────────────────────
    # Mycelium lore quest. Introduces Root-Roads, An Cór Briste, and the
    # Rot/Blight distinction. Trigger: Zone 2+ Mycelium node.
    {
        "id": "mod_old_cap",
        "type": "side",
        "title": "Old Cap's Secret",
        "description": (
            "Deep in a bioluminescent chamber, a Mycelium elder named Old Cap "
            "grows from the wall itself — half-mushroom, half-memory. He knows "
            "why the Root-Roads were sealed, but the knowledge costs a Crown "
            "ingredient: Moth-Scale Powder, currency of the Canopy Court. "
            "Old Cap claims natural Rot and the Blight are not the same thing. "
            "He calls the true enemy by an older name: An Cór Briste — the "
            "Broken Choir."
        ),
        "objective": "find_item_moth_scale_powder",
        "trigger": "zone_2",
        "tier_hint": 2,
        "prerequisite": "",
        "reward": {
            "gold": 60,
            "item": "Root-Road Key",
            "description": "A living tendril that writhes toward Mycelium nodes. Unlocks fast-travel between visited network points.",
            "faction_rep": {"mycelium": 2},
        },
        "turn_in": "quest_giver",
        "quest_npcs": [
            {
                "name": "Old Cap",
                "role": "quest_giver",
                "description": (
                    "A shelf-mushroom the size of a table, growing from "
                    "a junction of three root-walls. A face has formed "
                    "in the cap — ancient, patient, slightly amused. "
                    "Bioluminescent spores drift from his gills when he speaks."
                ),
                "faction": "mycelium",
                "disposition": "friendly",
                "dialogue_greeting": (
                    "Ah. A walker. The network felt your footsteps three "
                    "rooms ago. Sit. Or stand. I have been here since "
                    "before your grandmother's grandmother learned to "
                    "tell mushrooms from stones."
                ),
                "dialogue_quest": (
                    "The Root-Roads were sealed for a reason. The Elders "
                    "call it safety. I call it cowardice. I can unseal "
                    "them — but I need something the Canopy Court hoards: "
                    "Moth-Scale Powder. The dust between dimensions. "
                    "Bring it, and I will tell you what An Cór Briste "
                    "truly means. The settlers call it the Rot. They are "
                    "wrong. The Rot is me. The Rot is natural. What is "
                    "killing this tree is something else entirely."
                ),
                "dialogue_turn_in": (
                    "The powder dissolves into the network. The Roads "
                    "breathe again. Now listen: the Blight is not decay. "
                    "It is a song gone wrong. The Choir changed the Root-Song "
                    "to fight something worse — and the side effects are "
                    "what your people call the Rot. An Cór Briste. The "
                    "Broken Choir. They are still singing, deep below."
                ),
            },
            {
                "name": "Maeth",
                "role": "informant",
                "description": (
                    "A young woman with soil-stained hands and hollow eyes. "
                    "She searches the Mycelium tunnels for her daughter, who "
                    "wandered into a Root-Road before the seals held. "
                    "Maeth does not believe the Roads are truly closed."
                ),
                "faction": "mycelium",
                "disposition": "neutral",
                "dialogue_greeting": (
                    "Have you seen a girl? Eight years old. Red hair. "
                    "She went into the network before they sealed it. "
                    "The mushrooms say she's alive. I can feel her, "
                    "through the spores. Please."
                ),
            },
        ],
        "rooms": [
            {
                "name": "Luminescent Junction",
                "description": "Three root-tunnels converge in a cathedral of fungal growth. Bioluminescent threads pulse in slow waves — the Mycelium's heartbeat.",
                "enemies": [],
                "social": True,
                "tier": 2,
            },
            {
                "name": "Sealed Root-Road",
                "description": "A tunnel mouth blocked by hardened amber resin. Behind the seal, you can hear something — a low vibration, like a distant choir.",
                "enemies": ["Blight Tendril", "Spore Guardian"],
                "tier": 2,
            },
            {
                "name": "The Spreading",
                "description": "A vast cavern where the natural Rot and the Blight visibly collide. White mycelia push against black corruption. The boundary shifts like a tide.",
                "enemies": ["Choir Sprout"],
                "loot": ["Mycelium Map Fragment"],
                "tier": 2,
            },
        ],
    },

    # ─── #220: THE CRACKED SEAL ─────────────────────────────────────────
    # Heartwood discovery. Introduces the Descendants, the Whisper, and
    # the first Heartwood entrance. Trigger: Zone 1 Ash Runner encounter
    # or Allied faction rep with any faction.
    {
        "id": "mod_cracked_seal",
        "type": "side",
        "title": "The Cracked Seal",
        "description": (
            "Sable — the settlement's cartographer — found something in the old "
            "maps: a vault that doesn't match any known Arborist construction. "
            "Its seal is cracking from the inside. Something within wants out. "
            "The Heartwood Elders sealed these passages generations ago and "
            "refuse to explain why. The vault bows when approached, as though "
            "recognising visitors. A figure called the Whisper speaks through "
            "the amber."
        ),
        "objective": "reach_tier_2",
        "trigger": "zone_1",
        "tier_hint": 1,
        "prerequisite": "",
        "reward": {
            "gold": 50,
            "item": "Amber Shard (Heartwood)",
            "description": "A warm shard of pure heartwood amber. Vibrates near concealed passages. Heartwood entrance discovered.",
            "faction_rep": {"heartwood_elders": 1},
            "unlocks": "heartwood_entrance",
        },
        "turn_in": "informant",
        "quest_npcs": [
            {
                "name": "The Whisper",
                "role": "quest_giver",
                "description": (
                    "Not a person — a voice. It speaks through vibrations "
                    "in the amber walls, through resonance in your equipment, "
                    "through the hum of your teeth. It claims to be a "
                    "Descendant — one who came after the Arborists and "
                    "inherited their silence."
                ),
                "faction": "heartwood_elders",
                "disposition": "neutral",
                "dialogue_greeting": (
                    "You hear us. Good. Most walk past and hear only "
                    "the wood creaking. We are the Descendants. We "
                    "inherited the Elders' vigil when they withdrew "
                    "into the Heartwood and fell silent."
                ),
                "dialogue_quest": (
                    "The seal was made to keep something in — or keep "
                    "something out. We can no longer tell. The Elders "
                    "forgot the reason generations ago. But the seal is "
                    "cracking. If you help us stabilise it, we will show "
                    "you the entrance. What you find inside... that is "
                    "between you and the tree."
                ),
                "dialogue_turn_in": (
                    "The seal holds. For now. As promised — the entrance "
                    "to the Heartwood. The Elders will not welcome you. "
                    "But the tree might. It remembers things its caretakers "
                    "have forgotten."
                ),
            },
        ],
        "rooms": [
            {
                "name": "The Bowing Vault",
                "description": "An Arborist vault unlike any other — the door curves inward as you approach, as if the wood is genuflecting. Amber light pulses within.",
                "enemies": [],
                "social": True,
                "tier": 1,
            },
            {
                "name": "Seal Chamber",
                "description": "Song-craft murals line every surface — painted songs frozen mid-phrase. The central seal is a disc of compressed amber the size of a cart wheel, and hairline fractures web across its face.",
                "enemies": ["Amber Echo", "Seal Guardian"],
                "tier": 2,
            },
            {
                "name": "The Threshold",
                "description": "Beyond the seal: a passage that breathes. The walls are living wood, warm to the touch. The grain patterns spell words in a language older than the settlement.",
                "enemies": [],
                "loot": ["Amber Shard (Heartwood)"],
                "tier": 2,
            },
        ],
    },

    # ─── #221: THE SONG BELOW ───────────────────────────────────────────
    # Undergrove introduction. First Chorus Walker and Section Leader
    # encounter. The Choir's song becomes audible. Endgame begins.
    # Trigger: Zone 4 or Heartwood reached.
    {
        "id": "mod_song_below",
        "type": "main",
        "title": "The Song Below",
        "description": (
            "The wood vibrates. Not from wind, not from movement — from sound. "
            "A song rises through the roots, audible only in the deepest chambers. "
            "It is beautiful, and it is wrong. Every seventh note lands flat, and "
            "when it does, the Blight pulses. Someone is singing the tree sick. "
            "The grey-amber vault ahead leads down — past the Heartwood, past "
            "the sealed corridors, into the Undergrove where the roots of all "
            "four groves converge. The Conductor waits at the convergence."
        ),
        "objective": "zone_7",
        "trigger": "zone_4",
        "tier_hint": 4,
        "prerequisite": "mod_cracked_seal",
        "reward": {
            "gold": 200,
            "item": "Resonance Dampener",
            "description": "A disc of counter-harmonics etched in heartwood. Reduces Choir Resonance buildup by half.",
            "unlocks": "undergrove_entrance",
        },
        "turn_in": "quest_giver",
        "quest_npcs": [
            {
                "name": "Section Leader Vrenn",
                "role": "quest_giver",
                "description": (
                    "Once an Arborist — now something between. Their body "
                    "is still humanoid but the skin is bark-grey, the eyes "
                    "amber-lit from within. They speak in two voices: their "
                    "own, and a harmonic that resonates from the walls. "
                    "They are not hostile. They are tired."
                ),
                "faction": "",
                "disposition": "wary",
                "dialogue_greeting": (
                    "You should not be here. The Song is stronger at this "
                    "depth. Can you hear it? Every seventh note — that is "
                    "the Blight. The Conductor cannot stop. We cannot stop. "
                    "The Song holds Autumn in place. Without it, Winter "
                    "comes. The Void comes."
                ),
                "dialogue_quest": (
                    "The Undergrove is where the roots converge. The Choir "
                    "sings from there — not by choice, not anymore. The "
                    "Conductor changed the Song to fight the Void, and it "
                    "worked. But the cost... the Blight is a side effect. "
                    "We are the side effect. Go down. See what we became. "
                    "Then decide: do you silence the Song and let Winter in, "
                    "or leave us singing and let the Blight spread?"
                ),
                "dialogue_turn_in": (
                    "You saw. You heard. The Song cannot be unsung. But "
                    "perhaps it can be... retuned. The original Root-Song "
                    "still echoes in the Heartwood. If someone could carry "
                    "it to the Conductor... but that is a quest for another "
                    "day. Take this. It will quiet the resonance. A little."
                ),
            },
        ],
        "rooms": [
            {
                "name": "The Grey-Amber Vault",
                "description": "The amber here is not golden — it is grey, drained, like a photograph left in the rain. Golems stand at broken attention, their song-cores dark.",
                "enemies": ["Hollow Walker", "Hollow Walker"],
                "tier": 4,
            },
            {
                "name": "Root Convergence",
                "description": "Four massive root-systems plunge into a single cavern. They are alive — pulsing, intertwined, fighting. The air tastes of ozone and old sap.",
                "enemies": ["Chorus Walker", "Choir Sprout"],
                "tier": 4,
            },
            {
                "name": "The Conductor's Balcony",
                "description": "A ledge overlooking a vast chasm. Far below, a figure stands at the intersection of all roots, arms raised, mouth open in an endless song. The sound is deafening and silent at the same time.",
                "enemies": [],
                "social": True,
                "tier": 4,
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# 10. QUEST MODULE NPC POOL — Unified access for quest injection
# ---------------------------------------------------------------------------

QUEST_MODULE_NPCS: Dict[str, dict] = {}
for _qmod in MODULAR_QUEST_TEMPLATES:
    for _npc in _qmod.get("quest_npcs", []):
        QUEST_MODULE_NPCS[_npc["name"]] = {
            "quest_id": _qmod["id"],
            "npc_type": _npc["role"],
            **_npc,
        }
