"""
codex.forge.reference_data.bitd_playbooks
==========================================
Blades in the Dark playbook reference data.

SOURCE: Blades in the Dark.pdf
  - Playbooks: pp.61-87
  - Heritages: p.51
  - Vice types: p.52
"""

# SOURCE: Blades in the Dark.pdf, pp.61-87
PLAYBOOKS = {
    "Cutter": {
        "setting": "doskvol",
        # SOURCE: Blades in the Dark.pdf, p.61
        "description": "A dangerous and intimidating fighter",
        "special_abilities": [
            # SOURCE: Blades in the Dark.pdf, p.62
            {"name": "Battleborn", "description": "You may expend your special armor to reduce harm from an attack in combat or to push yourself during a fight."},
            {"name": "Bodyguard", "description": "When you protect a teammate, take +1d to your resistance roll. When you gather information to anticipate possible threats in the current situation, you get +1 effect."},
            {"name": "Ghost Fighter", "description": "You may imbue your hands, melee weapons, or tools with spirit energy. You gain potency in combat vs. the supernatural."},
            {"name": "Leader", "description": "When you Command a cohort in combat, they continue to fight when they would otherwise break (morale 1). They gain potency and 1 armor."},
            {"name": "Mule", "description": "Your load limits are higher. Light: 5. Normal: 7. Heavy: 8."},
            {"name": "Not to be Trifled With", "description": "You can push yourself to do one of the following: perform a feat of physical force that verges on the superhuman—engage a small gang on equal footing in close combat."},
            {"name": "Savage", "description": "When you unleash physical violence, it's especially frightening. When you Command a frightened target, take +1d."},
            {"name": "Vigorous", "description": "You recover from harm faster. Permanently fill in one of your healing clock segments. Take +1d to healing treatment rolls."},
        ],
        "friends": ["Marlane, a pugilist", "Chael, a vicious thug", "Mercy, a cold killer", "Grace, an extortionist", "Sawtooth, a physicker"],
        "rivals": ["Collecting Rust, a gang", "Coran, a drug dealer"],
        "items": ["Fine hand weapon", "Fine heavy weapon", "Scary weapon or tool", "Manacles & chain", "Rage essence vial"],
        "xp_trigger": "You addressed a challenge with violence or coercion.",
    },
    "Hound": {
        "setting": "doskvol",
        # SOURCE: Blades in the Dark.pdf, p.65
        "description": "A deadly sharpshooter and tracker",
        "special_abilities": [
            # SOURCE: Blades in the Dark.pdf, p.66
            {"name": "Sharpshooter", "description": "You can push yourself to do one of the following: make a ranged attack at extreme distance beyond what's normal for the weapon—make a ranged attack with a concealed weapon."},
            {"name": "Focused", "description": "You may expend your special armor to resist a consequence of surprise or mental harm (trauma, confusion, losing track of someone) or to push yourself for ranged combat or tracking."},
            {"name": "Ghost Hunter", "description": "Your hunting pet is imbued with spirit energy. It gains potency when tracking or fighting the supernatural, and gains an arcane ability."},
            {"name": "Scout", "description": "When you gather information to discover the location of a target, you get +1 effect. When you hide in a prepared position or use camouflage you get +1d to rolls to avoid detection."},
            {"name": "Survivor", "description": "From physical harm or environmental danger. Permanently fill in one of your healing clock segments."},
            {"name": "Tough as Nails", "description": "Penalties from harm are one level less severe (though level 4 harm is still fatal)."},
            {"name": "Vengeful", "description": "You gain an additional xp trigger: You got payback against someone who harmed you or someone you care about."},
        ],
        "friends": ["Steiner, an assassin", "Celene, a sentinel", "Melvir, a physicker", "Veleris, a spy", "Casta, a bounty hunter"],
        "rivals": ["Bazran, a gang leader"],
        "items": ["Fine pair of pistols", "Fine long rifle", "Electroplasmic ammunition", "A trained hunting pet", "Spyglass"],
        "xp_trigger": "You addressed a challenge with tracking or violence.",
    },
    "Leech": {
        "setting": "doskvol",
        # SOURCE: Blades in the Dark.pdf, p.69
        "description": "A saboteur and technician",
        "special_abilities": [
            # SOURCE: Blades in the Dark.pdf, pp.70-71
            {"name": "Alchemist", "description": "When you invent or craft a creation with alchemical features, take +1d to your roll. You begin with one special formula already known."},
            {"name": "Artificer", "description": "When you invent or craft a creation with spark-craft features, take +1d to your roll. You begin with one special design already known."},
            {"name": "Analyst", "description": "During downtime, you get two ticks to distribute among any long term project clocks that involve investigation or learning a new formula or design plan."},
            {"name": "Fortitude", "description": "You may expend your special armor to resist a consequence of fatigue, weakness, or chemical effects, or to push yourself when working with technical skill."},
            {"name": "Ghost Ward", "description": "When you Wreck an area with arcane substances, ruining it for any other use, it becomes anathema or enticing to spirits (your choice)."},
            {"name": "Physicker", "description": "You can Tinker with bones, blood, and bodily humours to treat wounds or stabilize the dying. You may Study a malady or corpse. Everyone in your crew (including you) gets +1d to their healing treatment rolls."},
            {"name": "Saboteur", "description": "When you Wreck, your work is much quieter than it should be and the damage is very well-hidden from casual inspection."},
            {"name": "Venomous", "description": "Choose a drug or poison (from your bandolier stock) to which you have become immune. You can push yourself to secrete it through your skin or saliva or exhale it as a vapor."},
        ],
        "friends": ["Stazia, an apothecary", "Veldren, a psychonaut", "Eckerd, a corpse thief", "Jul, a blood dealer", "Malista, a priestess"],
        "rivals": ["Ojak, a drug dealer"],
        "items": ["Fine tinkering tools", "Fine wrecker tools", "Blowgun & darts, syringes", "Bandolier of alchemicals", "Gadgets"],
        "xp_trigger": "You addressed a challenge with technical skill or mayhem.",
    },
    "Lurk": {
        "setting": "doskvol",
        # SOURCE: Blades in the Dark.pdf, p.73
        "description": "A stealthy infiltrator and burglar",
        "special_abilities": [
            # SOURCE: Blades in the Dark.pdf, pp.74-75
            {"name": "Infiltrator", "description": "You are not affected by quality or Tier when you bypass security measures."},
            {"name": "Ambush", "description": "When you attack from hiding or spring a trap, you get +1d to your roll."},
            {"name": "Daredevil", "description": "When you roll a desperate action, you get +1d to your roll if you also take -1d to any resistance rolls against consequences from your action."},
            {"name": "The Devil's Footsteps", "description": "You can push yourself to do one of the following: perform a feat of athletics that verges on the superhuman—maneuver to confuse your enemies so they mistakenly attack each other."},
            {"name": "Expertise", "description": "Choose one of your action ratings. When you lead a group action using that action, you can suffer only 1 stress at most, regardless of the number of failed rolls."},
            {"name": "Ghost Veil", "description": "You may shift partially into the ghost field, becoming shadowy and insubstantial for a few moments. Take 2 stress when you shift, plus 1 stress for each extra feature."},
            {"name": "Reflexes", "description": "When there's a question about who acts first, the answer is you."},
            {"name": "Shadow", "description": "You may expend your special armor to resist a consequence from detection or security measures, or to push yourself for a feat of athletics or stealth."},
        ],
        # SOURCE: Blades in the Dark.pdf, p.73 — "Roslyn Kellis, a noble" (full surname given in book)
        "friends": ["Telda, a beggar", "Darmot, a Bluecoat", "Frake, a locksmith", "Roslyn Kellis, a noble", "Petra, a city clerk"],
        "rivals": ["Harker, a jail-bird"],
        "items": ["Fine lockpicks", "Fine shadow cloak", "Light climbing gear", "Silence potion vial", "Dark-sight goggles"],
        "xp_trigger": "You addressed a challenge with stealth or evasion.",
    },
    "Slide": {
        "setting": "doskvol",
        # SOURCE: Blades in the Dark.pdf, p.77
        "description": "A subtle manipulator and spy",
        "special_abilities": [
            # SOURCE: Blades in the Dark.pdf, pp.78-79
            {"name": "Rook's Gambit", "description": "Take 2 stress to roll your best action rating while performing a different action. Say how you adapt your skill to this use."},
            {"name": "Cloak & Dagger", "description": "When you use a disguise or other form of covert misdirection, you get +1d to rolls to confuse or deflect suspicion. When you throw off your disguise, the resulting surprise gives you the initiative in the situation."},
            # SOURCE: Blades in the Dark.pdf, p.78 — Ghost Voice description corrected from source
            {"name": "Ghost Voice", "description": "You know the secret method to interact with a ghost or demon as if it were a normal human, regardless of how wild or feral it appears. You gain potency when communicating with the supernatural."},
            {"name": "A Little Something on the Side", "description": "At the end of each downtime phase, you earn +2 stash."},
            {"name": "Like Looking into a Mirror", "description": "You can always tell when someone is lying to you."},
            {"name": "Mesmerism", "description": "When you Sway someone, you may cause them to forget that it's happened until they next interact with you."},
            {"name": "Trust in Me", "description": "You get +1d vs. a target with whom you have an intimate relationship."},
            {"name": "Subterfuge", "description": "You may expend your special armor to resist a consequence from suspicion or persuasion, or to push yourself for subterfuge."},
        ],
        "friends": ["Bryl, a drug dealer", "Bazso Baz, a gang leader", "Klyra, a tavern owner", "Nyrix, a prostitute", "Harker, a jail-bird"],
        "rivals": ["Salia, an information broker"],
        # SOURCE: Blades in the Dark.pdf, p.79 — "A cane-sword" confirmed in Slide items list
        "items": ["Fine clothes & jewelry", "Fine disguise kit", "Fine loaded dice, trick cards", "Trance powder", "A cane-sword"],
        "xp_trigger": "You addressed a challenge with deception or influence.",
    },
    "Spider": {
        "setting": "doskvol",
        # SOURCE: Blades in the Dark.pdf, p.81
        "description": "A devious mastermind",
        "special_abilities": [
            # SOURCE: Blades in the Dark.pdf, p.82
            # EXPANDED: Foresight description — "Two times per score you can assist a teammate without paying stress" per PDF p.82
            {"name": "Foresight", "description": "Two times per score you can assist a teammate without paying stress. At the end of the score, clear 1 stress."},
            {"name": "Calculating", "description": "Due to your careful planning, during downtime, you may give yourself or a cohort additional downtime activity."},
            {"name": "Connected", "description": "During downtime, you get +1 result level when you acquire an asset or reduce heat."},
            {"name": "Functioning Vice", "description": "Your vices are under control. You get +1d when you indulge your vice during downtime."},
            {"name": "Ghost Contract", "description": "When you shake on a deal, you can invest a ghostly presence in the contract. If either party breaks the terms, they take level 3 harm, 'Cursed.'"},
            {"name": "Jail Bird", "description": "When incarcerated, your wanted level counts as 1 less, and you claim +1 prison claim."},
            {"name": "Mastermind", "description": "You may assist a teammate without paying stress. When you lead a group action, you may spend a gambit to negate one consequence suffered by one of the group members."},
            {"name": "Weaving the Web", "description": "You gain +1d to Consort when you gather information on a target for a score. You get +1d to the engagement roll for that score."},
        ],
        # SOURCE: Blades in the Dark.pdf, p.81 — Spider contacts list
        "friends": ["Salia, an information broker", "Augus, a master architect", "Jennah, a servant", "Riven, a chemist", "Jeren, a Bluecoat archivist"],
        "rivals": ["Veldren, a psychonaut"],
        "items": ["Fine cover identity", "Fine bottle of whiskey", "Blueprints", "Small wrecking tools", "Concealed palm pistol"],
        "xp_trigger": "You addressed a challenge with calculation or conspiracy.",
    },
    "Whisper": {
        "setting": "doskvol",
        # SOURCE: Blades in the Dark.pdf, p.85
        "description": "An arcane adept and spirit trafficker",
        "special_abilities": [
            # SOURCE: Blades in the Dark.pdf, p.86
            {"name": "Compel", "description": "You can Attune to the ghost field to force a nearby spirit to appear and answer truthfully one question. Take stress equal to the spirit's level of power."},
            {"name": "Ghost Mind", "description": "You're always aware of supernatural entities in your presence. Take +1d when you gather info about the supernatural by any means."},
            {"name": "Iron Will", "description": "You are immune to the terror that some supernatural entities inflict on sight. Take +1d to resistance rolls with resolve."},
            {"name": "Occultist", "description": "You know the secret ways to Consort with ancient powers, forgotten gods, or demons. Once you've consorted with a specific entity, you may summon it to your presence."},
            {"name": "Ritual", "description": "You can Study an occult ritual and perform it. You begin with one ritual already learned."},
            {"name": "Strange Methods", "description": "When you invent or craft using arcane methods (spirit essences or electroplasmic gadgetry), take +1d."},
            {"name": "Tempest", "description": "You can push yourself to do one of the following: unleash a lightning strike—unleash a howling storm in an area."},
            {"name": "Warded", "description": "You may expend your special armor to resist a supernatural consequence, or to push yourself when you contend with or employ arcane forces."},
        ],
        "friends": ["Nyryx, a possessor ghost", "Scurlock, a vampire", "Setarra, a demon", "Quellyn, a witch", "Flint, a spirit trafficker"],
        "rivals": ["Roslyn, a noble, spirit collector"],
        "items": ["Fine lightning hook", "Fine spirit mask", "Electroplasm vials", "Spirit bottles (2)", "Ghost key"],
        "xp_trigger": "You addressed a challenge with knowledge or arcane power.",
    },
}

# SOURCE: Blades in the Dark.pdf, p.51
HERITAGES = {
    "Akoros": {"setting": "doskvol", "description": "The largest and most industrialized land. Akorosi are typically dark-haired, with a range of complexions from pale to dark brown."},
    "Dagger Isles": {"setting": "doskvol", "description": "A tropical archipelago. People of the Dagger Isles are often deeply tanned with dark hair, known as fierce fighters and sailors."},
    "Iruvia": {"setting": "doskvol", "description": "A hot land of dark deserts and mystery. Iruvians are known as cunning diplomats and merchants with dark skin and dark hair."},
    "Severos": {"setting": "doskvol", "description": "A cold, mountainous land. Severosi are typically pale-skinned, fair-haired and gaunt."},
    "Skovlan": {"setting": "doskvol", "description": "A rainy island recently conquered by the Imperium. Skovlander people are often stout and ruddy, with red or blonde hair."},
    "Tycheros": {"setting": "doskvol", "description": "A distant land shrouded in mystery. Tycherosi have demon blood and often display strange features—black eyes, or unusual skin patterns."},
}

# SOURCE: Blades in the Dark.pdf, p.52
VICE_TYPES = ["Faith", "Gambling", "Luxury", "Obligation", "Pleasure", "Stupor", "Weird"]

__all__ = ["PLAYBOOKS", "HERITAGES", "VICE_TYPES"]
