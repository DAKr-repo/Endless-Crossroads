"""
codex.forge.reference_data.sav_playbooks
=========================================
Scum and Villainy playbook reference data.

Contains 7 playbooks, heritage options, backgrounds, and vice types.

SOURCE POLICY:
  # SOURCE: Scum and Villainy.pdf, p.XX  — verified directly from PDF text
  # EXPANDED — content consistent with game fiction but not verbatim from PDF
    (used where PDF ability pages did not render extractable text)
"""

# =========================================================================
# PLAYBOOKS
# SOURCE: Scum and Villainy.pdf, p.112 (ship/playbook list), p.69-109
# Playbook names and page numbers confirmed from Table of Contents p.8
# Ability NAMES confirmed via cross-references in "Playing a..." sidebars
# Ability DESCRIPTIONS marked EXPANDED where verbatim text was unextractable
# =========================================================================

PLAYBOOKS: dict = {
    # SOURCE: Scum and Villainy.pdf, p.69 (playbook header)
    "Mechanic": {
        "setting": "procyon",
        "description": (
            "You keep the ship running. Engines, life support, weapons systems — "
            "if it has moving parts, you can fix it or break it. The Guilds would "
            "love to have someone like you working for them. Without you, the crew "
            "would be floating dead in the black."
        ),
        "special_abilities": [
            # SOURCE: Scum and Villainy.pdf, p.70 — starting ability, name confirmed
            # p.73 'Playing a Mechanic' cross-references "Tinker" as starting ability
            {
                "name": "Tinker",
                "description": (  # EXPANDED — PDF ability page text unextractable
                    "When you work on a clock with a Rig or Hack action, or when you "
                    "Attune to examine a mechanism, you may use a push to work on two "
                    "clocks at the same time. If one of the clocks is a device you "
                    "created, you may roll with potency."
                ),
            },
            {
                "name": "Ghost",  # EXPANDED — ability name from game community reference
                "description": (  # EXPANDED
                    "You can move through a small group of people without being noticed "
                    "as long as you keep moving. Others don't register your presence. "
                    "You may push yourself to sneak through any size group undetected."
                ),
            },
            {
                "name": "Mechanic's Heart",  # EXPANDED
                "description": (  # EXPANDED
                    "When you give yourself over to love for the ship, machines, and your "
                    "crew, you may use Rig instead of Doctor to tend to wounds. You may "
                    "also push yourself when repairing to remove an additional system "
                    "damage box."
                ),
            },
            {
                "name": "Overclock",  # EXPANDED
                "description": (  # EXPANDED
                    "When you push a ship system to extreme performance, you may treat its "
                    "quality as one higher for the scene. Afterward, the system takes "
                    "1 damage."
                ),
            },
            {
                "name": "Fixed",  # EXPANDED — referenced in Pilot 'Playing a Pilot' p.91
                "description": (  # EXPANDED
                    "Your ship's systems rarely fail catastrophically. Once per job, you "
                    "may declare that a ship system holds together when it would otherwise "
                    "take damage from a consequence."
                ),
            },
            {
                "name": "Bomb Maker",  # EXPANDED
                "description": (  # EXPANDED
                    "You can craft explosive devices from ship materials. They are "
                    "reliable and purpose-built. When you Rig a device to detonate, "
                    "treat your position as one step better."
                ),
            },
            {
                "name": "Dr. Strange",  # EXPANDED — referenced in Stitch 'Playing a Stitch' p.109
                "description": (  # EXPANDED
                    "You can push yourself to invent or jury-rig a device that produces "
                    "a specified effect. The GM will tell you what it costs in time, "
                    "materials, and downtime clocks."
                ),
            },
            {
                "name": "Veteran",  # EXPANDED — standard veteran ability pattern
                "description": (  # EXPANDED
                    "Choose one special ability from another playbook. You've picked up "
                    "enough experience to make it your own."
                ),
            },
        ],
        "friends": [  # EXPANDED — specific NPC names from PDF not extractable from ability pages
            "A Guild inspector who looks the other way",
            "A parts dealer with no questions asked",
            "An ex-partner who owes you a debt",
        ],
        "rivals": [  # EXPANDED
            "A Guild auditor tracking unlicensed work",
            "A mechanic whose sabotage nearly killed you",
        ],
        # SOURCE: Scum and Villainy.pdf, p.72 — Mechanic Items
        "items": [
            "Fine hacking rig",
            "Fine ship repair tools",
            "Small drone",
            "Vision-enhancing goggles",
            "Spare parts",
            "Genius pet",
        ],
        "xp_trigger": "Address a challenge with expertise or ingenuity.",  # EXPANDED
    },
    # SOURCE: Scum and Villainy.pdf, p.75 (playbook header)
    "Muscle": {
        "setting": "procyon",
        "description": (
            "Violence is your trade. You're the enforcer, the soldier, the one the "
            "crew relies on when negotiations collapse and the shooting starts. "
            "Every crew needs someone who can handle the worst — that's you."
        ),
        "special_abilities": [
            # SOURCE: Scum and Villainy.pdf, p.76 — starting ability name confirmed
            # p.79 'Playing a Muscle' references "Bodyguard" and "Backup"
            {
                "name": "Battleborn",  # EXPANDED — name from game community reference
                "description": (  # EXPANDED
                    "You may push yourself to negate a consequence that would cause you "
                    "harm in combat. Your training lets you turn a bad situation around."
                ),
            },
            {
                "name": "Bodyguard",  # SOURCE: p.79 cross-reference confirmed
                "description": (  # EXPANDED
                    "When you protect a teammate, the consequences that would affect them "
                    "affect you instead. You may push yourself to take a consequence for "
                    "an ally even when you are not adjacent."
                ),
            },
            {
                "name": "Backup",  # SOURCE: p.79 'Playing a Muscle' cross-reference confirmed
                "description": (  # EXPANDED
                    "When you assist a crew member and they use your assistance die, "
                    "you may also take +1d on your next action in the same scene."
                ),
            },
            {
                "name": "Brawler",  # EXPANDED
                "description": (  # EXPANDED
                    "When you engage in close combat, you have potency. You may use "
                    "Scramble instead of Scrap for melee fighting."
                ),
            },
            {
                "name": "Gunslinger",  # EXPANDED
                "description": (  # EXPANDED
                    "You can wield two pistols simultaneously without penalty. When you "
                    "Scrap with firearms at close range, take +1d."
                ),
            },
            {
                "name": "Not To Be Trifled With",  # EXPANDED
                "description": (  # EXPANDED
                    "You can push yourself to do one of: perform a feat of superhuman "
                    "strength; take on a small gang on equal footing in close combat."
                ),
            },
            {
                "name": "Scary",  # EXPANDED
                "description": (  # EXPANDED
                    "You instill fear in those you face. You may Command through "
                    "physical intimidation to compel obedience without speaking."
                ),
            },
            {
                "name": "Veteran",  # EXPANDED — standard veteran ability pattern
                "description": (  # EXPANDED
                    "Choose one special ability from another playbook. You've seen "
                    "enough to have picked it up."
                ),
            },
        ],
        "friends": [  # EXPANDED
            "A soldier who looks the other way",
            "An arms dealer with rare stock",
            "A medic who patches you up without questions",
        ],
        "rivals": [  # EXPANDED
            "A former squadmate who calls you a deserter",
            "A bounty hunter with your face on their board",
        ],
        # SOURCE: Scum and Villainy.pdf, p.78 — Muscle Items
        "items": [
            "Krieger, a fine blaster pistol",
            "Vera, a fine sniper rifle",
            "Zmei, a fine flamethrower",
            "Sunder, a fine vibro-blade",
            "Zarathustra, a detonator launcher",
            "Fine martial arts style",
            "Mystic ammunition",
        ],
        "xp_trigger": "Express your character's nature through acts of violence or protection.",  # EXPANDED
    },
    # SOURCE: Scum and Villainy.pdf, p.81 (playbook header)
    "Mystic": {
        "setting": "procyon",
        "description": (
            "You touch the Way — the strange resonance underlying all existence. "
            "Mystics are feared, misunderstood, and essential. Your attunement to "
            "the Way gives the crew an edge that no amount of technology can replicate."
        ),
        "special_abilities": [
            # SOURCE: Scum and Villainy.pdf, p.82 — starting ability
            # p.85 'Playing a Mystic' references "Psy-Blade" and "Kinetics"
            {
                "name": "Attune",  # EXPANDED — starting ability name
                "description": (  # EXPANDED
                    "When you open your mind to the Way, you may communicate with "
                    "non-sentient creatures and machines, sense danger, or perceive "
                    "the emotions of those nearby. Take stress equal to magnitude."
                ),
            },
            {
                "name": "Psy-Blade",  # SOURCE: p.85 cross-reference confirmed
                "description": (  # EXPANDED
                    "When you channel Way energy through a melee weapon, it becomes "
                    "a devastating force. Push yourself to deal devastating harm "
                    "that bypasses armor."
                ),
            },
            {
                "name": "Kinetics",  # SOURCE: p.85 cross-reference confirmed
                "description": (  # EXPANDED
                    "You can move objects with your mind. Push yourself to hurl objects "
                    "with enough force to harm, or to protect allies by deflecting "
                    "incoming fire."
                ),
            },
            {
                "name": "Warded",  # EXPANDED
                "description": (  # EXPANDED
                    "You may push yourself to resist the Way abilities of other Mystics "
                    "or nullify their effects for a scene. You sense Way use within "
                    "your vicinity."
                ),
            },
            {
                "name": "Presence",  # EXPANDED
                "description": (  # EXPANDED
                    "Your Way attunement is visible to those sensitive to it. You may "
                    "push yourself to project an aura of authority or terror. "
                    "Take +1d on Command or Sway when your presence is on display."
                ),
            },
            {
                "name": "Tempest",  # EXPANDED
                "description": (  # EXPANDED
                    "You can push yourself to unleash a burst of Way energy, causing "
                    "chaos and confusion across a wide area. Affects everyone in range, "
                    "friend and foe."
                ),
            },
            {
                "name": "Foresight",  # EXPANDED
                "description": (  # EXPANDED
                    "Two or three times per session, you can assist a crew member after "
                    "the fact with 'I had a vision about this.' They may reroll any "
                    "single die on their action."
                ),
            },
            {
                "name": "Veteran",  # EXPANDED — standard veteran ability pattern
                "description": (  # EXPANDED
                    "Choose one special ability from another playbook. The Way has "
                    "led you to expand your skills."
                ),
            },
        ],
        "friends": [  # EXPANDED
            "An elder Mystic who mentors you from a distance",
            "A researcher studying Way phenomena",
            "A Nightspeaker who owes you a debt",
        ],
        "rivals": [  # EXPANDED
            "The Nightspeakers who view you as dangerous and untrained",
            "A Hegemony inquisitor hunting rogue Mystics",
        ],
        # SOURCE: Scum and Villainy.pdf, p.84 — Mystic Items
        "items": [
            "Fine melee weapon",
            "Offerings",
            "Trappings of religion",
            "Outdated religious outfit",
            "Memento of your travels",
            "Precursor artifact",
        ],
        "xp_trigger": "Use your Way abilities and accept the stress or consequences it brings.",  # EXPANDED
    },
    # SOURCE: Scum and Villainy.pdf, p.87 (playbook header)
    "Pilot": {
        "setting": "procyon",
        "description": (
            "You are one with the ship. No debris field too thick, no pursuit too "
            "relentless, no lane too dark. When the crew needs to get somewhere or "
            "escape from somewhere fast, they look to you."
        ),
        "special_abilities": [
            # SOURCE: Scum and Villainy.pdf, p.88 — starting ability
            # p.91 'Playing a Pilot' references "Commander", "Daredevil" (veteran), "Traveler"
            {
                "name": "Ace Pilot",  # EXPANDED — starting ability
                "description": (  # EXPANDED
                    "When you make an action roll for the ship using Helm, you may "
                    "push yourself to take +1d. You never have to roll to do basic "
                    "piloting tasks."
                ),
            },
            {
                "name": "Commander",  # SOURCE: p.91 cross-reference confirmed
                "description": (  # EXPANDED
                    "When you lead a coordinated shipboard action, each crew member "
                    "who follows your direction takes +1d on their first roll. "
                    "You may use Helm to lead ground operations from the air."
                ),
            },
            {
                "name": "Traveler",  # SOURCE: p.85 Mystic cross-reference, p.91 Pilot cross-reference confirmed
                "description": (  # EXPANDED
                    "You have extensive knowledge of the Procyon sector. You always "
                    "know the fastest route between two points. Once per session, "
                    "you may declare you know a secret hyperspace lane."
                ),
            },
            {
                "name": "Talons",  # EXPANDED
                "description": (  # EXPANDED
                    "In ship-to-ship combat, you may use Helm to make an attack "
                    "roll against an enemy vessel by outmaneuvering them into "
                    "a dangerous position."
                ),
            },
            {
                "name": "Afterburner",  # EXPANDED
                "description": (  # EXPANDED
                    "When you push the engines to their absolute limit, ignore one "
                    "system damage during the maneuver. The engines take the damage "
                    "after the scene ends."
                ),
            },
            {
                "name": "Ghost Lane",  # EXPANDED
                "description": (  # EXPANDED
                    "You know uncharted jump lanes throughout Procyon. When you plot "
                    "a course to avoid Hegemony patrols, the engagement roll is treated "
                    "as one step better."
                ),
            },
            {
                "name": "The Devil's Footrest",  # EXPANDED
                "description": (  # EXPANDED
                    "When you fail a Helm roll, you may push yourself to succeed "
                    "anyway. The ship takes 1 damage from the strain of the maneuver."
                ),
            },
            {
                "name": "Veteran",  # EXPANDED — standard veteran ability pattern
                "description": (  # EXPANDED
                    "Choose one special ability from another playbook. The stars "
                    "have taught you more than just piloting."
                ),
            },
        ],
        "friends": [  # EXPANDED
            "A traffic controller who clears your lane",
            "A racer who taught you the best tricks",
            "A cartographer with secret routes",
        ],
        "rivals": [  # EXPANDED
            "A Hegemony pilot who has made catching you personal",
            "A rival smuggler who undercuts your routes",
        ],
        # SOURCE: Scum and Villainy.pdf, p.90 — Pilot Items
        "items": [
            "Fine customized spacesuit",
            "Fine small Urbot",
            "Fine mechanics kit",
            "Grappling hook",
            "Guild license",
            "Victory cigars",
        ],
        "xp_trigger": "Execute a daring or creative maneuver under pressure.",  # EXPANDED
    },
    # SOURCE: Scum and Villainy.pdf, p.93 (playbook header)
    "Scoundrel": {
        "setting": "procyon",
        "description": (
            "Charming, quick, and always working an angle. You operate in the grey "
            "zone between legality and crime, using wit and audacity where others "
            "rely on force. Every room has an exit if you know where to look."
        ),
        "special_abilities": [
            # SOURCE: Scum and Villainy.pdf, p.94 — starting ability
            # p.97 'Playing a Scoundrel' references "Daredevil", "Tenacious"
            {
                "name": "Daredevil",  # SOURCE: p.91 and p.97 cross-references confirmed
                "description": (  # EXPANDED
                    "When you roll a desperate action, you may take +1d. The higher "
                    "the stakes, the sharper your focus becomes."
                ),
            },
            {
                "name": "Tenacious",  # SOURCE: p.79 Muscle 'Playing a Muscle' cross-reference confirmed
                "description": (  # EXPANDED
                    "Penalties from harm are one level less severe for you. You are "
                    "hard to put down and nearly impossible to keep down."
                ),
            },
            {
                "name": "Infiltrator",  # EXPANDED
                "description": (  # EXPANDED
                    "You are not affected by any 'Amateur' status for being somewhere "
                    "you shouldn't. When you infiltrate a location, take +1d to avoid "
                    "notice and bypass simple security."
                ),
            },
            {
                "name": "Ambush",  # EXPANDED
                "description": (  # EXPANDED
                    "When you attack from hiding or from a position of surprise, "
                    "you deal additional harm equal to your Skulk rating."
                ),
            },
            {
                "name": "Lucky",  # EXPANDED
                "description": (  # EXPANDED
                    "Once per session, you can choose to avoid any single consequence. "
                    "Something unlikely saves you — but it costs 2 stress."
                ),
            },
            {
                "name": "Ghost",  # EXPANDED
                "description": (  # EXPANDED
                    "You can move through a crowd or small group of people without "
                    "registering. Push yourself to become effectively invisible "
                    "while moving through any size group."
                ),
            },
            {
                "name": "Pickpocket",  # EXPANDED
                "description": (  # EXPANDED
                    "When you lift items from someone without them noticing, treat "
                    "your position as controlled regardless of the circumstances."
                ),
            },
            {
                "name": "Veteran",  # EXPANDED — standard veteran ability pattern
                "description": (  # EXPANDED
                    "Choose one special ability from another playbook. You've run "
                    "enough jobs to pick up a few tricks."
                ),
            },
        ],
        "friends": [  # EXPANDED
            "A fence who moves your questionable goods",
            "A gambler who owes you a fortune",
            "A Guild clerk who forges documents",
        ],
        "rivals": [  # EXPANDED
            "A mark who figured out your game and wants revenge",
            "A scoundrel who stole your identity",
        ],
        # SOURCE: Scum and Villainy.pdf, p.96 — Scoundrel Items
        "items": [
            "Fine blaster pistol (or matching pair)",
            "Fine coat",
            "Loaded dice or trick holo-cards",
            "Forged documents",
            "Mystic ammunition",
            "Personal memento",
        ],
        "xp_trigger": "Address a challenge with deception, misdirection, or audacity.",  # EXPANDED
    },
    # SOURCE: Scum and Villainy.pdf, p.99 (playbook header)
    "Speaker": {
        "setting": "procyon",
        "description": (
            "Words are your weapons. You negotiate, persuade, threaten, and "
            "manipulate with equal facility. In a sector where information and "
            "alliances are worth more than credits, your skills are invaluable."
        ),
        "special_abilities": [
            # SOURCE: Scum and Villainy.pdf, p.100 — starting ability
            # p.73 Mechanic references "Old Friends"; p.109 Stitch references "Heart-to-Heart"
            {
                "name": "Old Friends",  # SOURCE: p.73 Mechanic 'Playing a Mechanic' cross-reference confirmed
                "description": (  # EXPANDED
                    "Once per score, you may call on an old friend or contact to assist "
                    "you. You may also have one additional contact from any background."
                ),
            },
            {
                "name": "Heart-to-Heart",  # SOURCE: p.109 Stitch 'Playing a Stitch' cross-reference confirmed
                "description": (  # EXPANDED
                    "When you have a personal conversation with someone and open up to "
                    "them, you may clear 1 stress for yourself and for them. You may "
                    "also ask the GM one question about their goals or fears."
                ),
            },
            {
                "name": "Disarming",  # SOURCE: p.97 Scoundrel 'Playing a Scoundrel' cross-reference confirmed
                "description": (  # EXPANDED
                    "When you Consort or Sway someone, on a critical success they become "
                    "a lasting ally or asset. Your social finesse leaves a mark."
                ),
            },
            {
                "name": "Fixer",  # EXPANDED
                "description": (  # EXPANDED
                    "When you negotiate payment or reduce heat with a faction, "
                    "treat your effect as elevated. You always know the right words "
                    "to smooth over a situation."
                ),
            },
            {
                "name": "Infiltrator",  # EXPANDED
                "description": (  # EXPANDED
                    "You are not affected by any 'Outsider' status when operating in "
                    "a social environment you shouldn't be in. You blend seamlessly "
                    "into any social stratum."
                ),
            },
            {
                "name": "Subterfuge",  # EXPANDED
                "description": (  # EXPANDED
                    "You can push yourself to plant a false belief in someone's mind "
                    "that lasts until they have reason to question it. This works "
                    "on individuals, not crowds."
                ),
            },
            {
                "name": "Leverage",  # EXPANDED
                "description": (  # EXPANDED
                    "When you Study a target for leverage, you may ask the GM two "
                    "additional questions about their secrets, desires, or weaknesses."
                ),
            },
            {
                "name": "Veteran",  # EXPANDED — standard veteran ability pattern
                "description": (  # EXPANDED
                    "Choose one special ability from another playbook. Connections "
                    "open all kinds of doors."
                ),
            },
        ],
        "friends": [  # EXPANDED
            "A Hegemony official who likes you rather too much",
            "A journalist who owes you a story",
            "A criminal syndicate fixer",
        ],
        "rivals": [  # EXPANDED
            "A Speaker whose network you disrupted",
            "A mark you burned who now works against you",
        ],
        # SOURCE: Scum and Villainy.pdf, p.102 — Speaker Items (page text confirmed present)
        "items": [  # EXPANDED — p.102 items page text not fully extracted
            "Subvocal communicator",
            "Encrypted data tablet with contacts",
            "Luxury clothing",
            "Fine forgery tools",
            "Bribery funds",
            "Disguise kit",
        ],
        "xp_trigger": "Advance the crew's goals through social manipulation, negotiation, or information.",  # EXPANDED
    },
    # SOURCE: Scum and Villainy.pdf, p.105 (playbook header)
    "Stitch": {
        "setting": "procyon",
        "description": (
            "You patch up the crew, dose them with stims, and keep them functional "
            "through jobs that should have killed them. You deal in flesh and chemistry, "
            "from battlefield triage to exotic compounds only you can synthesize."
        ),
        "special_abilities": [
            # SOURCE: Scum and Villainy.pdf, p.106 — starting ability
            # p.109 references 'Book Learning', 'Dr. Strange', 'Welcome Anywhere', 'Moral Compass'
            {
                "name": "Patch",  # EXPANDED — starting ability
                "description": (  # EXPANDED
                    "When you tend to a crew member's harm, you may substitute your "
                    "Doctor rating for any other action rating for a push, and you get "
                    "a moment to reference your past training or research."
                ),
            },
            {
                "name": "Book Learning",  # SOURCE: p.109 cross-reference confirmed
                "description": (  # EXPANDED
                    "When you Study to research a topic, take +1d. Your education "
                    "covers an extraordinary range of subjects. You may substitute "
                    "Study for Doctor when diagnosing."
                ),
            },
            {
                "name": "Moral Compass",  # SOURCE: p.97 Scoundrel cross-reference confirmed
                "description": (  # EXPANDED
                    "When you help someone and they accept your guidance, you may "
                    "clear 1 stress. When you act against your values, you gain "
                    "1 stress instead of taking a consequence."
                ),
            },
            {
                "name": "Welcome Anywhere",  # SOURCE: p.109 'Xeno Stitches' cross-reference confirmed
                "description": (  # EXPANDED
                    "You are welcomed by most folks as a physician. You may enter "
                    "normally hostile territory under a flag of medical neutrality. "
                    "Take +1d on Consort and Sway in such situations."
                ),
            },
            {
                "name": "Surgeoneer",  # EXPANDED
                "description": (  # EXPANDED
                    "When you perform complex surgery or synthesize an unusual compound, "
                    "you may attempt to remove permanent harm that would otherwise "
                    "require special resources."
                ),
            },
            {
                "name": "Toxicologist",  # EXPANDED
                "description": (  # EXPANDED
                    "You craft poisons, antidotes, and sedatives of exceptional quality. "
                    "When you Rig or Doctor to deploy a toxin, your effect is always "
                    "elevated one step."
                ),
            },
            {
                "name": "Physicker",  # EXPANDED
                "description": (  # EXPANDED
                    "When you use your medical knowledge offensively — targeting weak "
                    "points, applying pressure to nerves — you may use Doctor for "
                    "Scrap actions and treat your position as one step better."
                ),
            },
            {
                "name": "Veteran",  # EXPANDED — standard veteran ability pattern
                "description": (  # EXPANDED
                    "Choose one special ability from another playbook. The galaxy "
                    "has taught you more than medicine."
                ),
            },
        ],
        "friends": [  # EXPANDED
            "A black market organ and supplies dealer",
            "A Hegemony medic who trades supplies off the books",
            "A former patient who became fiercely loyal",
        ],
        "rivals": [  # EXPANDED
            "A Guild pharmacist whose licensed trade you undercut",
            "A patient who blames you for a botched procedure",
        ],
        # SOURCE: Scum and Villainy.pdf, p.108 — Stitch Items
        "items": [
            "Fine medkit",
            "Fine bedside manner",
            "Fine clothing",
            "Recognizable medic garb",
            "Candies and treats",
            "Syringes and applicators",
        ],
        "xp_trigger": "Patch up the crew under pressure or use medical expertise in an unexpected way.",  # EXPANDED
    },
}

# =========================================================================
# HERITAGES
# SOURCE: Scum and Villainy.pdf, p.58 — heritage list confirmed
# 4 heritages: Colonist, Imperial, Spacer, Syndicate
# Descriptions EXPANDED — heritage description text not fully extracted from PDF
# =========================================================================

HERITAGES: dict = {
    # SOURCE: Scum and Villainy.pdf, p.58 (heritage confirmed)
    "Colonist": {
        "setting": "procyon",
        "description": (  # EXPANDED
            "You come from one of the many colonial worlds in the Procyon Cluster. "
            "Life on the frontier was hard but honest. The Hegemony was always a "
            "distant rumble, and you learned self-reliance before you could walk."
        ),
    },
    # SOURCE: Scum and Villainy.pdf, p.58 (heritage confirmed)
    "Imperial": {
        "setting": "procyon",
        "description": (  # EXPANDED
            "You grew up in Hegemony culture — orderly, disciplined, obedient. "
            "You know how the machine works because you were a cog in it. Whether "
            "you fled or walked away, the Hegemony's mark is still on you."
        ),
    },
    # SOURCE: Scum and Villainy.pdf, p.58 (heritage confirmed)
    "Spacer": {
        "setting": "procyon",
        "description": (  # EXPANDED
            "You were born on a ship or station and have never felt fully comfortable "
            "with ground beneath your feet. Space is home. You understand vessels, "
            "orbital mechanics, and the void in ways planet-born people never will."
        ),
    },
    # SOURCE: Scum and Villainy.pdf, p.58 (heritage confirmed)
    "Syndicate": {
        "setting": "procyon",
        "description": (  # EXPANDED
            "You emerged from one of the criminal organizations flourishing in the "
            "shadows of the Hegemony's reach. You learned that loyalty is the only "
            "currency that matters, and that the law is just another gang with "
            "better uniforms."
        ),
    },
}

# =========================================================================
# BACKGROUNDS
# SOURCE: Scum and Villainy.pdf, p.59 — full list confirmed from PDF text
# =========================================================================

BACKGROUNDS: dict = {
    # SOURCE: Scum and Villainy.pdf, p.59
    "Academic": "A professor, student, researcher, or other knowledge-driven vocation.",
    "Labor": "A factory worker, driver, dockhand, miner, or other tradesperson. The majority of the Hegemony is of this background.",
    "Cult": "Part of a Cult, officially sanctioned or not. A holy warrior, priest, or religious devotee.",
    "Guilder": "Involved in the machinations of a Guild, such as a ship designer, financial analyst, or logistics officer.",
    "Military": "A Hegemonic soldier, mercenary, intelligence operative, strategist, or training instructor.",
    "Noble": "Living the life of luxury, such as a dilettante, someone caught up in House politics.",
    "Syndicate": "Part of an organized criminal gang, from the lowest lookout to ousted former crime lord.",
}

# =========================================================================
# VICE TYPES
# SOURCE: Scum and Villainy.pdf, p.60 — complete list confirmed from PDF text
# Exactly 7 vices. "Bravado" and "Thrills" are NOT in the book.
# =========================================================================

VICE_TYPES: list = [
    "Faith",       # SOURCE: p.60 — you're part of a Cult, or observe specific ceremonies
    "Gambling",    # SOURCE: p.60 — you crave games of chance, or bet on sporting events
    "Luxury",      # SOURCE: p.60 — you seek the high life with expensive, ostentatious displays
    "Obligation",  # SOURCE: p.60 — you're devoted to a family, cause, organization, charity
    "Pleasure",    # SOURCE: p.60 — you seek hedonistic gratification from lovers, food, drink
    "Stupor",      # SOURCE: p.60 — you dull the senses with drug abuse, excessive drinking
    "Weird",       # SOURCE: p.60 — you perform strange experiments, explore the Way, commune with Ur artifacts
]

# =========================================================================
# STANDARD ITEMS (common gear available to all crew)
# SOURCE: Scum and Villainy.pdf, p.66 — complete list confirmed from PDF text
# =========================================================================

STANDARD_ITEMS: dict = {
    # SOURCE: Scum and Villainy.pdf, p.66
    "Armor": "Really unsubtle, full body stuff. Stops a few bolts. Will shrug off a knife without noticing. Powered. Assists in movement.",
    "Blaster Pistol": "Shoots bolts of hot plasma. Accurate only at close range. Makes 'pew pew' noises (mandatory). Comes in a variety of shapes.",
    "Communicator": "Has a few bands, likely even a few encrypted. Works only when within orbit.",
    "Detonator": "Extremely deadly explosive weapon. Fits in the palm of your hand and can be thrown. Illegal.",
    "Hacking Tools": "Deck, splicing pliers, plugs and ports, keypad crackers, specialized software, custom-modified chips, rainbow dictionaries, automated exploits.",
    "Heavy Blaster": "Can do considerable damage to vehicles and things like unshielded doors. Will do serious and messy harm to people. Illegal.",
    "Illicit Drugs": "What's your poison, space cowboy? For personal use, catching a dangerous bounty, or entertainment while traveling.",
    "Medkit": "Blood for a few common races, gauze, anti-radiation injector, laser scalpel, antiseptics, thread, painkillers.",
    "Melee Weapon": "Sharp. Blunt. Pointy. Stabby. Slicy. All different sizes. Some come with laser edges. Some vibrate.",
    "Repair Tools": "Things you need to fix ship engines, speeders, hovercars. Hammers, a welder, screwdrivers, wrenches, battery chargers, spray-painters.",
    "Spacesuit": "Some radiation protection, survival in toxic atmospheres, EVA. Half a day of oxygen.",
    "Spy Gear": "Disguises, voice modulators, mini-cameras, thermal scanners, false thumbprints, and audio filters.",
}

__all__ = ["PLAYBOOKS", "HERITAGES", "BACKGROUNDS", "VICE_TYPES", "STANDARD_ITEMS"]
