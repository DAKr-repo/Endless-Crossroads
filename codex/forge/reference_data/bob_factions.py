"""
codex.forge.reference_data.bob_factions
=========================================
Band of Blades faction data: Broken forces, undead types, and allied groups.

There are exactly THREE Broken generals serving the Cinder King:
  Blighter (p.187) — Flesh Blighter, body horror and toxic science
  Breaker  (p.195) — Stormbreaker, tension and psychological horror
  Render   (p.203) — Bonerender, depersonalization of war and totalitarianism

The GM picks TWO Broken for each campaign.

SOURCE: Band of Blades.pdf
  - The Broken overview: pp.184-185
  - Blighter:   pp.187-193
  - Breaker:    pp.195-201
  - Render:     pp.203-209
  - Undead overview: pp.182-183
"""

from typing import Dict, List, Any

# =========================================================================
# FACTIONS
# =========================================================================

FACTIONS: Dict[str, Dict[str, Any]] = {

    # =====================================================================
    # THE BROKEN — Enemy Generals (exactly 3)
    # SOURCE: Band of Blades.pdf, pp.184-209
    # =====================================================================

    "Blighter": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.187-193
        "faction_type": "broken",
        "tier": 5,  # SOURCE: p.190 — "Blighter herself is a threat 5 opponent"
        "description": (
            "Flesh Blighter, Broken servant of the Cinder King. Body horror and "
            "toxic science themes. Was once Elenessa, a high engineer-priestess of "
            "the Orite triumvirate of crafter gods. Former lover of Shreya. Now a "
            "pale, hooded, leather-clad figure with dark hair and green eyes, bearing "
            "alchemical seals and bandoliers of chemicals. Full title: Flesh Blighter, "
            "also called the Foul, Corruptor of Flesh, and Plaguebringer."
        ),
        "commander": "Blighter (Elenessa)",  # SOURCE: p.187
        "horror_themes": (
            "Body horror. Surgery and science gone wrong. Toxic gasses and the horrors "
            "of trench warfare. Troops oozing pus and disease. Bodies knitted together "
            "in disturbing ways. Limbs and organs where they shouldn't be."
        ),  # SOURCE: p.187
        "unit_types": [
            # SOURCE: Band of Blades.pdf, p.190 — Line Troops
            "Rotters (line troop, threat 1) — undead burning with hate, driven by alchemical fluid in veins",
            "Crows (line troop controller, threat 1) — wear plague masks, mark and organize the dead",
            # SOURCE: Band of Blades.pdf, p.191 — Elites
            "Horrors (elite, threat 2) — 8-to-14-foot amalgamations of stitched body parts",
            "Gut-Sacks (elite, threat 2) — failed Spitter attempts, explode in poison and acid when killed",
            "Spitters (elite, threat 2) — mouths sewn shut, projectile vomit flesh-melting acid",
        ],
        "special_abilities": [
            {
                "name": "Abominable Science",
                # SOURCE: Band of Blades.pdf, p.188 — Starting ability
                "description": (
                    "Blighter's chirurgeons learn to stitch writhing undead together. "
                    "Horrors can appear in any mission."
                ),
            },
            {
                "name": "Attrition Strategies",
                # SOURCE: Band of Blades.pdf, p.188 — Broken ability
                "description": (
                    "Blighter attacks and poisons supply lines. Supply mission "
                    "engagement rolls take -1d."
                ),
            },
            {
                "name": "Cruel Gluttony",
                # SOURCE: Band of Blades.pdf, p.188 — Broken ability
                "description": (
                    "Blighter crafts fluids that brew acid inside undead. Gut-Sacks "
                    "can appear in any mission."
                ),
            },
            {
                "name": "Toxic Bile",
                # SOURCE: Band of Blades.pdf, p.188 — Broken ability
                "description": (
                    "Gut-Sacks and Spitters cause corrupting wounds. At end of mission, "
                    "untreated corrupting wounds cause +1 corruption each."
                ),
            },
            {
                "name": "Modern Warfare",
                # SOURCE: Band of Blades.pdf, p.189 — Broken ability
                "description": (
                    "Blighter's troops carry appropriate fine arms and armor. Elevates "
                    "threat of troops that use arms and armor by 1 — all of Blighter's "
                    "troops except Elites."
                ),
            },
            {
                "name": "Scars of War",
                # SOURCE: Band of Blades.pdf, p.189 — Broken ability
                "description": (
                    "Blighter's troops can corrupt the land. Poison mists erupt and "
                    "plague the countryside. The GM may introduce these mists as "
                    "obstacles on any Blighter mission, or as consequences for failed "
                    "rolls. These mists are threat 1."
                ),
            },
            {
                "name": "Toxic Mutagen",
                # SOURCE: Band of Blades.pdf, p.189 — Broken ability
                "description": (
                    "Blighter's troops coat their weapons in alchemical oil, causing "
                    "+1 corruption when they wound someone."
                ),
            },
            {
                "name": "Violent Emulsion",
                # SOURCE: Band of Blades.pdf, p.189 — Broken ability
                "description": (
                    "Blighter crafts undead to overdrive bile production. Spitters "
                    "can appear in any mission."
                ),
            },
        ],
        "notable_npcs": [
            {
                "name": "Red Hook (infamous Horror)",
                # SOURCE: Band of Blades.pdf, p.192
                "role": "Infamous",
                "description": (
                    "This Horror lost a 'hand,' replaced by a hook on a chain. Uses it "
                    "to scale walls and drag soldiers while they scream to lure friends."
                ),
            },
            {
                "name": "The Doctor (infamous Crow)",
                # SOURCE: Band of Blades.pdf, p.192
                "role": "Infamous",
                "description": (
                    "A Crow that regained former intellect. Wearing a bone-white mask "
                    "with a bloody handprint, improvises modifications on Rotters and "
                    "Horrors using parts carved from still-dying Legionnaires."
                ),
            },
            {
                "name": "Wailer (infamous Horror)",
                # SOURCE: Band of Blades.pdf, p.192
                "role": "Infamous",
                "description": (
                    "Has nine heads embedded about its body, all crying in horrific "
                    "dissonance. Half a dozen spikes to carry back bodies for 'repairs'."
                ),
            },
            {
                "name": "Viktoria Karhowl, the Macabre Scientist",
                # SOURCE: Band of Blades.pdf, p.192
                "role": "Lieutenant",
                "description": (
                    "A corrupted engineer — not dead — who traded her humanity for a "
                    "seat at the Cinder King's table. Blighter uses her clever designs "
                    "for siege weapons and advanced clockworks."
                ),
            },
            {
                "name": "Black Rotting Gale, the Abomination",
                # SOURCE: Band of Blades.pdf, p.192
                "role": "Lieutenant (Horror)",
                "description": (
                    "A Horror that exchanged raw size for tubes and tanks of alchemicals. "
                    "As it walks, it vents a cloud toxic to all organic matter. Created "
                    "to pursue the deforestation of Aldermark."
                ),
            },
            {
                "name": "Lugos, the Clockwork Assassin",
                # SOURCE: Band of Blades.pdf, p.192
                "role": "Lieutenant (Crow)",
                "description": (
                    "A Crow with much of its body replaced with advanced clockworks, "
                    "enhancing strength and vision. Armor makes it immune to Black Shot "
                    "and most blades. It habitually winds itself."
                ),
            },
        ],
    },

    "Breaker": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.195-201
        "faction_type": "broken",
        "tier": 5,  # SOURCE: p.198 — "Breaker herself fights as a threat 5 opponent"
        "description": (
            "Stormbreaker, Broken servant of the Cinder King. Tension, uncertainty, "
            "and psychological horror themes. Was once Minika Arya, a priestess of "
            "the Bartan goddess Vazara. A gaunt, pale figure using illusion to disguise "
            "the marks of death. Full title: Stormbreaker, also called the Bringer of "
            "Thunder or the Weather Witch."
        ),
        "commander": "Breaker (Minika Arya)",  # SOURCE: p.195
        "horror_themes": (
            "Long blood rituals. Tension, uncertainty, and psychological horror. "
            "Perversion of natural order. Wind, thunder, lightning, and wailing. "
            "Monstrous transformations of beautiful things. Hexes that bind the bones, "
            "and make you doubt what you see."
        ),  # SOURCE: p.195
        "unit_types": [
            # SOURCE: Band of Blades.pdf, p.198 — Line Troops
            "Burned (line troop, threat 1) — impaled on lightning-blasted trees, animated by storms, still warm inside",
            "Hexed (line troop, threat 1) — living people with sigils carved into flesh, mind-dominated",
            # SOURCE: Band of Blades.pdf, p.199 — Elites
            "Shadow Witches (elite, threat 2) — living bodies infused with piece of Breaker, cast hexes",
            "Devourers (elite, threat 2) — corrupted sacred beasts of Vazara, large bat-like creatures with black feathers",
            "Transformed (elite, threat 2) — people warped by sigils into animal-part shock troops",
        ],
        "special_abilities": [
            {
                "name": "The Coven",
                # SOURCE: Band of Blades.pdf, p.196 — Starting ability
                "description": (
                    "Breaker imbues still-living bodies with pieces of herself to craft "
                    "acolytes. Shadow Witches can appear in any mission."
                ),
            },
            {
                "name": "The Changing Curse",
                # SOURCE: Band of Blades.pdf, p.196 — Broken ability
                "description": (
                    "Shadow Witches twist the living. Transformed can appear in any "
                    "mission."
                ),
            },
            {
                "name": "Pillar of Skulls",
                # SOURCE: Band of Blades.pdf, p.196 — Broken ability
                "description": (
                    "Breaker makes a pillar of wailing bodies to summon and corrupt "
                    "sacred beasts. Devourers can appear in any mission."
                ),
            },
            {
                "name": "Nature's Fury",
                # SOURCE: Band of Blades.pdf, p.196 — Broken ability
                "description": (
                    "Breaker and Shadow Witches can hex nature, covering troops with "
                    "fog and storms, and animating trees in combat. Animated trees are "
                    "threat 1."
                ),
            },
            {
                "name": "Storm Riding",
                # SOURCE: Band of Blades.pdf, p.197 — Broken ability
                "description": (
                    "Shadow Witches learn to use the lightning forces inside Burned to "
                    "jump from body to body. Killing a Shadow Witch displaces the Witch "
                    "to the body of a Burned instead of removing them as a threat."
                ),
            },
            {
                "name": "Wild Awakening",
                # SOURCE: Band of Blades.pdf, p.197 — Broken ability
                "description": (
                    "Shadow Witches and Breaker hex animals into spies and packs for "
                    "the Transformed to run with."
                ),
            },
            {
                "name": "Dark Visions",
                # SOURCE: Band of Blades.pdf, p.197 — Broken ability
                "description": (
                    "Breaker hexes the Legion with screaming nightmares. Liberty "
                    "restores 1 less stress."
                ),
            },
            {
                "name": "Defilement",
                # SOURCE: Band of Blades.pdf, p.197 — Broken ability
                "description": (
                    "Breaker's defilement of religious sites has diminished the holy "
                    "influences in this region. Religious mission engagement rolls "
                    "take -1d."
                ),
            },
        ],
        "notable_npcs": [
            {
                "name": "Chimera (infamous Transformed)",
                # SOURCE: Band of Blades.pdf, p.200
                "role": "Infamous",
                "description": (
                    "An early Changing Curse experiment that somehow survived. A mix of "
                    "several animal parts and the heads of a few most Transformed."
                ),
            },
            {
                "name": "Silver (infamous Devourer)",
                # SOURCE: Band of Blades.pdf, p.200
                "role": "Infamous",
                "description": (
                    "Breaker's personal steed named for his color. 14-foot wingspan, "
                    "potent strength. Known for riding storms and dropping soldiers on "
                    "their friends from vast heights."
                ),
            },
            {
                "name": "Elia, the Passing Curse (infamous Hexed)",
                # SOURCE: Band of Blades.pdf, p.200
                "role": "Infamous",
                "description": (
                    "A Hexed that carves her sigils on others and has learned to "
                    "transfer her essence. Elia works alone; many Legion squads "
                    "realized too late that one member was not who they seemed."
                ),
            },
            {
                "name": "Bhed, the Wolf (Transformed lieutenant)",
                # SOURCE: Band of Blades.pdf, p.200
                "role": "Lieutenant",
                "description": (
                    "A nine-foot-tall, wolf-headed beast-man who shrugs off most wounds. "
                    "A circle of five Shadow Witches ensures his mental bindings never "
                    "slip, lest his rage turn on Breaker."
                ),
            },
            {
                "name": "The Hag (Shadow Witch lieutenant)",
                # SOURCE: Band of Blades.pdf, p.200
                "role": "Lieutenant",
                "description": (
                    "Killed and devoured her coven, decorates herself with their skulls. "
                    "A far more powerful force capable of sustaining multiple hexes at "
                    "once. Looks for opportunities to devour more of Breaker's essence."
                ),
            },
            {
                "name": "Ogiyer, the Cinder Guard",
                # SOURCE: Band of Blades.pdf, p.200
                "role": "Lieutenant (Cinder King's oversight)",
                "description": (
                    "Clad in red armor, this decayed body is hollow and filled with "
                    "black flame. The Cinder King's oversight on Breaker — this potent "
                    "armored monstrosity is rarely far from Breaker's side."
                ),
            },
        ],
    },

    "Render": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, pp.203-209
        "faction_type": "broken",
        "tier": 5,  # SOURCE: p.206 — "Render himself fights as a threat 5 enemy and is potent in melee"
        "description": (
            "Bonerender, Broken servant of the Cinder King. Brutal simplicity, "
            "overwhelming force, depersonalization of war and totalitarianism themes. "
            "Was once Vlaisim — the Shining One — a Zemyati Chosen of the Living God. "
            "The Cinder King burned Vlaisim's face during Breaking and commanded him "
            "never to hide it. Seven feet tall, clad in solid black armor, wielding a "
            "massive metal sword. Also called the Hollow Knight or the Burned One."
        ),
        "commander": "Render (Vlaisim)",  # SOURCE: p.203
        "horror_themes": (
            "Brutal simplicity. Overwhelming force. Hunger for blood. The unstoppable "
            "tide of undead. Metal and smoke and fire and soot. The depersonalization "
            "of war. Totalitarianism and rigidity. Piles of dead bodies. Rivers running "
            "red with blood. War as hell."
        ),  # SOURCE: p.203
        "unit_types": [
            # SOURCE: Band of Blades.pdf, p.206 — Line Troops
            "Gaunt (line troop, threat 1) — humans drained of blood, armor bolted and fused to flesh, reanimated",
            "Hounds (line troop, threat 1) — people with eyes sewn shut, lips ripped off, teeth filed to points, chains in bones",
            # SOURCE: Band of Blades.pdf, p.207 — Elites
            "Knights of the Black Oak (elite, threat 2) — holy order sworn to Vlaisim, mix of pikemen and heavy cavalry, still alive",
            "Heartless (elite, threat 2) — former Knights pumped full of cinderblood, heart removed, oversized metal weapons",
            "Thorns (elite, threat 2) — fallen killed by Render's troops skewered with metal blades treated with cinderblood",
        ],
        "special_abilities": [
            {
                "name": "The Sworn",
                # SOURCE: Band of Blades.pdf, p.204 — Starting ability
                "description": (
                    "Some oaths transcend death. Knights of the Black Oak can appear "
                    "in any mission."
                ),
            },
            {
                "name": "The Forge",
                # SOURCE: Band of Blades.pdf, p.204 — Broken ability
                "description": (
                    "Render forges blades of the fallen and cinderblood into Elites. "
                    "Thorns can appear in any mission."
                ),
            },
            {
                "name": "Heartless",
                # SOURCE: Band of Blades.pdf, p.204 — Broken ability
                "description": (
                    "Render grants strength to those that carve out their own hearts. "
                    "Heartless can appear in any mission."
                ),
            },
            {
                "name": "Spearforge",
                # SOURCE: Band of Blades.pdf, p.204 — Broken ability
                "description": (
                    "Render smiths massive, bladed, corrupting, black-iron spears that "
                    "Heartless carry and Knights fire from ballistae. Causes corruption "
                    "on hit."
                ),
            },
            {
                "name": "Fury",
                # SOURCE: Band of Blades.pdf, p.205 — Broken ability
                "description": (
                    "Render learns to spread his hate to his line troops. Gaunt now "
                    "move swiftly and can act with cunning if their Elite dies (do not "
                    "revert to feral instincts)."
                ),
            },
            {
                "name": "Shredders",
                # SOURCE: Band of Blades.pdf, p.205 — Broken ability
                "description": (
                    "Remnants of Thorns — balls of blades and Render's blood that "
                    "explode when near troops. Often buried in the ground or thrown into "
                    "squads. Threat 2 and cause corruption."
                ),
            },
            {
                "name": "Forced March",
                # SOURCE: Band of Blades.pdf, p.205 — Broken ability
                "description": (
                    "Render's troops, fueled by rage, push forward. The Commander adds "
                    "three ticks to the 'Time' clock."
                ),
            },
            {
                "name": "Massacre",
                # SOURCE: Band of Blades.pdf, p.205 — Broken ability
                "description": (
                    "Render's savage tactics and defiling use of the dead instills fear "
                    "in all soldiers. Assault mission engagement rolls take -1d."
                ),
            },
        ],
        "notable_npcs": [
            {
                "name": "Ache (infamous Heartless)",
                # SOURCE: Band of Blades.pdf, p.208
                "role": "Infamous",
                "description": (
                    "Born with his heart on the right, Ache has two holes in his chest. "
                    "One stays empty; he places the head of his most recent conquest in "
                    "the other. This dessicated head tells him secrets only the dead know."
                ),
            },
            {
                "name": "Eater (infamous Hound)",
                # SOURCE: Band of Blades.pdf, p.208
                "role": "Infamous",
                "description": (
                    "This pale-skinned Hound feasts on the last breath of the dying, "
                    "stealing a touch of their essence. The voices of many dead echo "
                    "through its baying and cause physical pain or hallucinations."
                ),
            },
            {
                "name": "Shatter (infamous Thorn)",
                # SOURCE: Band of Blades.pdf, p.208
                "role": "Infamous",
                "description": (
                    "A Thorn forged by including blades of two dead Chosen. Its "
                    "movements are precise and its metal sounds exude malice. Said to "
                    "contain Chosen blood and to seek any remnant of more."
                ),
            },
            {
                "name": "Irag, the Flayed (Black Oak Knight lieutenant)",
                # SOURCE: Band of Blades.pdf, p.208
                "role": "Lieutenant",
                "description": (
                    "A Knight renowned as a Weaponmaster. Irag has removed all his "
                    "skin as a show of loyalty to Render. Arrows and bullets are lodged "
                    "in his flesh but he feels no pain. Render feeds him pure cinderblood."
                ),
            },
            {
                "name": "Mihkin, the Dark General (Black Oak Knight lieutenant)",
                # SOURCE: Band of Blades.pdf, p.208
                "role": "Lieutenant",
                "description": (
                    "Astride an armored steed, Mihkin bears a holy lance cut from his "
                    "family tree, now blackened and twisted. On his shoulders are skulls "
                    "of those who disagreed with his choice to keep the Knights loyal to "
                    "Render."
                ),
            },
            {
                "name": "Zenya, the Sable Arrow (Black Oak Knight lieutenant)",
                # SOURCE: Band of Blades.pdf, p.208
                "role": "Lieutenant",
                "description": (
                    "A raven-haired archer who is the primary scout for the Black Oak. "
                    "Her quiver is filled with arrows Render gifted her — each causing "
                    "corruption and disease that can burn a Legionnaire from inside."
                ),
            },
        ],
    },

    # =====================================================================
    # UNDEAD TYPES — Common Enemy Forces
    # SOURCE: Band of Blades.pdf, pp.182-183 (overview), pp.190-191, 198-199, 206-207
    # Organized by which Broken creates them, with threat ratings from PDF
    # =====================================================================

    "Rotters": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, p.190 — Blighter's line troops
        "faction_type": "undead",
        "tier": 1,
        "description": (
            "Undead burning with a hate for the living. These corpses continue to rot "
            "even as dark sorcery compels them into battle. An alchemical liquid forced "
            "through their veins reanimates them. Blighter is always tinkering with "
            "plagues and toxins that, if injected before death, can raise Rotters. "
            "Typically 6 to 12 per group, controlled by a Crow or Elite."
        ),
        "unit_types": ["Rotter (line troop, threat 1)"],
        "special_abilities": [
            {
                "name": "Feral Without Supervision",
                "description": (
                    "Without a Crow or Elite directing them, Rotters act on bestial "
                    "instinct — chewing apart enemies without discipline or tactics."
                ),
            },
        ],
        "notable_npcs": [],
    },

    "Crows": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, p.190 — Blighter's line troop controllers
        "faction_type": "undead",
        "tier": 1,
        "description": (
            "Striking undead that make no sound but wear plague masks and cloaks. "
            "Troops nicknamed them after watching them walk amongst the dead, marking "
            "corpses to be taken and raised. Their presence focuses and organizes "
            "the undead. Their bodies rapidly decay if killed."
        ),
        "unit_types": ["Crow (line troop controller, threat 1)"],
        "special_abilities": [
            {
                "name": "Organize the Undead",
                "description": (
                    "Crows direct Rotters, giving them coordination and tactics. "
                    "Killing Crows renders nearby Rotters feral."
                ),
            },
        ],
        "notable_npcs": [],
    },

    "Burned": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, p.198 — Breaker's line troops
        "faction_type": "undead",
        "tier": 1,
        "description": (
            "Made by taking freshly killed or still-living people and impaling them on "
            "specially prepared trees with sharpened branches. Near-perpetual summoned "
            "storms blast them with lightning, animating those impaled. Burned often "
            "give off sparks and minor shocks when struck, and unlike other undead, "
            "are still warm inside. Destroying the trees is a priority."
        ),
        "unit_types": ["Burned (line troop, threat 1)"],
        "special_abilities": [
            {
                "name": "Storm Riding (via Shadow Witch)",
                # SOURCE: p.197
                "description": (
                    "When a Shadow Witch is killed, it can displace into the body of a "
                    "nearby Burned instead of being destroyed."
                ),
            },
        ],
        "notable_npcs": [],
    },

    "Gaunt": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, p.206 — Render's line troops
        "faction_type": "undead",
        "tier": 1,
        "description": (
            "As humans, the Gaunt were drained over the course of months, their blood "
            "infused with cinderblood and reinjected into them. Armor and plates are "
            "bolted and fused directly onto their flesh. None survive the process, "
            "reanimating after they are so equipped. Slower than other undead but the "
            "armor makes landing shots particularly tricky at any range. "
            "6 to 12 per group, supporting a Heartless or in units of Knights of the Black Oak."
        ),
        "unit_types": ["Gaunt (line troop, threat 1)"],
        "special_abilities": [
            {
                "name": "Fury (with ability)",
                # SOURCE: p.205 — Render's Fury broken ability
                "description": (
                    "If Render has the Fury ability, Gaunt can act with cunning even "
                    "if their commanding Elite dies — they do not revert to feral."
                ),
            },
        ],
        "notable_npcs": [],
    },

    "Shadow Witches": {
        "setting": "eastern_kingdoms",
        # SOURCE: Band of Blades.pdf, p.199 — Breaker's Elite troops
        "faction_type": "undead",
        "tier": 2,
        "description": (
            "Infused with a piece of Breaker stitched into their bodies, these former "
            "people beg for forgiveness in combat but are controlled from within. No "
            "longer fully human, Shadow Witches use hexes to twist the world around "
            "them — binding limbs, corrupting animals, befouling supplies, and "
            "weakening troops before setting rank and file undead on them. Elite, "
            "threat 2 opponents."
        ),
        "unit_types": ["Shadow Witch (elite, threat 2)"],
        "special_abilities": [
            {
                "name": "Hexes",
                "description": "Bind limbs, corrupt animals, befoul supplies, weaken troops.",
            },
            {
                "name": "Storm Riding",
                # SOURCE: p.197
                "description": (
                    "When killed, can displace into a nearby Burned instead of dying, "
                    "if Burned are in line of sight."
                ),
            },
        ],
        "notable_npcs": [],
    },

    # =====================================================================
    # ALLIED GROUPS
    # SOURCE: Band of Blades.pdf — campaign chapter, world chapter
    # These are EXPANDED — not directly catalogued in the extracted pages.
    # =====================================================================

    "Aldermani Loyalists": {
        "setting": "eastern_kingdoms",
        # EXPANDED — not directly sourced from extracted PDF pages
        "faction_type": "allied",
        "tier": 2,
        "description": (
            "Soldiers and militia from the Aldermark provinces who remain loyal "
            "and resist the Cinder King's occupation. They are scattered, poorly "
            "equipped, and desperate — but they know the terrain."
        ),
        "unit_types": [
            "Aldermani militia (untrained but motivated)",
            "Provincial cavalry (light, fast, local knowledge)",
            "Civilian informants",
        ],
        "special_abilities": [
            {
                "name": "Local Knowledge",
                "description": (
                    "Aldermani guides provide +1d to Scout rolls in their home "
                    "territory."
                ),
            },
            {
                "name": "Civilian Infrastructure",
                "description": (
                    "Loyalist communities can provide food and shelter. When resting "
                    "in Loyalist territory, recover 1 additional Supply."
                ),
            },
        ],
        "notable_npcs": [
            {
                "name": "Commander Vesna",
                "role": "Loyalist leader",
                "description": (
                    "A former provincial garrison commander who kept her forces "
                    "intact through the initial Cinder King invasion."
                ),
            },
        ],
    },

    "Panyar Shamans": {
        "setting": "eastern_kingdoms",
        # EXPANDED — setting lore, not directly from extracted PDF pages
        "faction_type": "allied",
        "tier": 2,
        "description": (
            "The spiritual leaders of the Panyar people maintain ancient rituals "
            "connected to their shattered moon goddess Nyx. Their methods are alien "
            "to most Legion soldiers — but their results are undeniable. They mourn "
            "their Broken goddess alongside the Horned One."
        ),
        "unit_types": [
            "Panyar shaman (spiritual practitioner)",
            "Spirit warrior (Panyar fighter with ritual preparation)",
        ],
        "special_abilities": [
            {
                "name": "Ward the Land",
                "description": (
                    "Panyar shamans can consecrate an area against undead using "
                    "ancient rituals tied to their moon goddess."
                ),
            },
            {
                "name": "Spirit Sight",
                "description": (
                    "Shamans can sense Cinder King corruption and detect "
                    "the presence of divine influence."
                ),
            },
        ],
        "notable_npcs": [
            {
                "name": "Shaman Yira",
                "role": "Senior shaman",
                "description": (
                    "One of the most powerful surviving Panyar shamans, maintaining "
                    "contact with the forest spirits who oppose the Cinder King's "
                    "corruption."
                ),
            },
        ],
    },

    "Orite Engineers": {
        "setting": "eastern_kingdoms",
        # EXPANDED — setting lore, Orite heritage confirmed at p.358
        "faction_type": "allied",
        "tier": 2,
        "description": (
            "Technical specialists from the Orite cities — masters of engineering, "
            "alchemy, and craft. The Orite triumvirate of crafter-gods (Builder, "
            "Maker, Crafter) govern all aspects of Orite life. Note: Blighter was "
            "once an Orite high engineer-priestess."
        ),
        "unit_types": [
            "Combat engineer (fortification and demolitions)",
            "Artificer (equipment repair and modification)",
        ],
        "special_abilities": [
            {
                "name": "Rapid Fortification",
                "description": (
                    "Orite engineers can erect defensible positions quickly. "
                    "+2 to any Wreck-based construction roll during camp phase."
                ),
            },
            {
                "name": "Equipment Mastery",
                "description": (
                    "Orite artificers can repair or modify Legion equipment during "
                    "downtime."
                ),
            },
        ],
        "notable_npcs": [
            {
                "name": "Chief Engineer Dorik",
                "role": "Orite Engineering lead",
                "description": (
                    "A no-nonsense engineer who evacuated the Orite technical archives "
                    "before the Cinder King's forces arrived."
                ),
            },
        ],
    },
}
