"""
codex.forge.reference_data.candela_phenomena
=============================================
Candela Obscura — Supernatural Phenomena reference data.

The Candela Obscura Core Rulebook (November 2023) does NOT enumerate a fixed
catalogue of named phenomena. Instead it defines phenomena as GM-created
supernatural occurrences (pp.65-69) and gives brief named examples:

  Creatures & Monsters examples (p.66):
    Coventis, Chemighast, Bilgecreepers

  Environment & Hazards examples (p.66):
    The Grim Branches, The Bloodfall, The Fatal Flora

  Spirits & Entities examples (p.69):
    The Phantom Fiddler, The Crimson Woman, The Laughing Boy

  Artifacts examples (p.69):
    The Conjurer's Companion, The Nightshade Necklace, Facade's Foil

  In-play example creature (pp.57-61):
    The Umbralisk (shadow-manipulating snake-like creature)

All entries below are therefore EXPANDED — they are original content
designed to be consistent with the Candela Obscura setting, tone, and the
four phenomenon categories implied by the game's mechanics and setting text.

Each phenomenon must belong to one of four categories inferred from the
game's mark types and world description:
  Spectral    — spirits, hauntings, entities (Brain/Bleed primary)
  Alchemical  — chemical / ancient Oldfairen contamination (Body/Bleed)
  Biological  — living organisms, infections, colonies (Body primary)
  Dimensional — Flare thinnings, planar intrusions (Bleed/Brain primary)

SOURCE: Candela Obscura Core Rulebook PDF - November 2023, pp.65-69

Phenomenon structure:
    name         (str)  — Display name
    category     (str)  — Spectral / Alchemical / Biological / Dimensional
    threat_level (int)  — 1 (minor) to 5 (cataclysmic)
    description  (str)  — Narrative overview
    signs        (list) — Observable clue hints (what investigators find)
    mechanics    (dict) — Rules effects during investigation/confrontation
    weakness     (str)  — How to neutralize or illuminate this phenomenon
"""

from typing import Dict, Any, List

# =========================================================================
# PHENOMENA
# =========================================================================
# All entries below are EXPANDED original content consistent with the
# Candela Obscura setting. See module docstring for sourcing rationale.

PHENOMENA: Dict[str, Dict[str, Any]] = {

    "crimson_weave": {
        # SOURCE: EXPANDED — inspired by "The Bloodfall" environment hazard (p.66)
        "setting": "newfaire",
        "name": "The Crimson Weave",
        "category": "Alchemical",
        "threat_level": 3,
        "description": (
            "A self-replicating alchemical contamination that spreads through "
            "water sources. Victims absorb it through skin contact, entering "
            "a fugue state where they carry out the Weave's agenda — sourcing "
            "more water to contaminate. The Weave appears to have a collective "
            "hive intelligence."
        ),
        "signs": [
            "Crimson discoloration in standing water, pipes, and wells",
            "Victims found wandering with milky red-tinged eyes",
            "Alchemical residue burns with a sulfur-copper smell",
            "Affected individuals can communicate briefly before fully turning",
            "Local animals avoid contaminated areas entirely",
        ],
        "mechanics": {
            "exposure_check": "Body mark on failed Control roll near contaminated water",
            "spread_rate": "Doubles every 48 in-game hours if not contained",
            "hive_sense": "The Weave is aware of investigators within 30 ft of large contamination",
            "danger_escalation": "Danger +1 each time the Weave contaminates a new water source",
        },
        "weakness": (
            "The Weave is neutralized by sustained high heat applied to the primary "
            "source. A ritual using alchemical salts can accelerate the process. "
            "Victims who have not fully turned can be purged with the correct antitoxin."
        ),
    },

    "hollow_choir": {
        # SOURCE: EXPANDED — consistent with Spirits & Entities framework (p.69)
        "setting": "newfaire",
        "name": "Hollow Choir",
        "category": "Spectral",
        "threat_level": 2,
        "description": (
            "A phenomenon born from mass traumatic death — massacre, plague, "
            "or catastrophic accident. The psychic residue of many deaths "
            "condenses into an auditory haunting. Those who hear the Choir "
            "experience vivid hallucinations of the original event and begin "
            "to lose the distinction between past and present."
        ),
        "signs": [
            "Faint singing or crying heard in empty rooms, especially at night",
            "Witnesses report hallucinations of historical or violent events",
            "Glass surfaces show faint reflections of people who are not present",
            "Clocks and timepieces stop or run backward in affected areas",
            "Written records in the building contain impossible anachronisms",
        ],
        "mechanics": {
            "hallucination": "Brain mark when investigators experience a vision",
            "time_distortion": "Investigation rolls take double the in-fiction time",
            "contagion": "Characters who sleep in the affected area add 1 Brain mark",
            "crescendo": "Danger 4+ triggers full manifestation; all in area roll Brain",
        },
        "weakness": (
            "The Hollow Choir is dissolved by a direct acknowledgment of the "
            "original traumatic event — a formal account read aloud, a proper "
            "burial of remains, or a ritual of remembrance. The Choir seeks "
            "witness, not destruction."
        ),
    },

    "flickering_man": {
        # SOURCE: EXPANDED — consistent with Dimensional/Flare intrusion framework (pp.65, 69)
        "setting": "newfaire",
        "name": "The Flickering Man",
        "category": "Dimensional",
        "threat_level": 4,
        "description": (
            "An entity that exists partially outside normal space. It appears "
            "as a humanoid figure whose outline strobes between the material "
            "plane and somewhere else — somewhere dark. It cannot be killed, "
            "only redirected. It is drawn to investigators who carry emotional "
            "trauma, which it feeds on by re-enacting their worst memories."
        ),
        "signs": [
            "Peripheral motion sightings — figure vanishes when looked at directly",
            "Photographs and mirrors show a blurred humanoid form observers missed",
            "Witnesses report reliving specific traumatic memories in vivid detail",
            "Electromagnetic interference causes lights to strobe rhythmically",
            "Investigators' notes contain words they do not remember writing",
        ],
        "mechanics": {
            "phasing": "Cannot be physically harmed; weapon strikes pass through",
            "memory_attack": "2 Brain marks when it focuses on a traumatized character",
            "dimensional_bleed": "Bleed marks count double while the Flickering Man is present",
            "tracking": "It moves toward the character with the most Brain marks",
        },
        "weakness": (
            "The Flickering Man cannot anchor to a plane where the emotional "
            "trauma that attracted it has been openly confronted and resolved. "
            "A cathartic illumination ritual — having the targeted investigator "
            "narrate and release their trauma — forces it to seek another anchor "
            "or dissipate entirely."
        ),
    },

    "glass_garden": {
        # SOURCE: EXPANDED — consistent with Alchemical/Oldfaire contamination framework (p.70)
        "setting": "newfaire",
        "name": "Glass Garden",
        "category": "Alchemical",
        "threat_level": 3,
        "description": (
            "An alchemical spill that crystallizes organic matter on contact. "
            "The crystals are beautiful and grow outward from the original "
            "contamination point, creating an eerie geometric landscape. "
            "Victims crystallized alive remain semi-conscious inside — their "
            "thoughts detectable by sensitive investigators."
        ),
        "signs": [
            "Expanding field of geometric crystal formations in unusual locations",
            "Crystallized animals, plants, and occasionally humans at the center",
            "Faint heartbeats detectable within larger crystal formations",
            "Alchemical burn marks along the growth vectors",
            "The crystals hum at a frequency that causes nausea in proximity",
        ],
        "mechanics": {
            "crystallization": "Body mark on contact with active growth edge",
            "encasement": "Desperate position to extract a living victim",
            "growth_rate": "Expands 1 ft per hour; accelerates under moonlight",
            "resonance": "Proximity causes 1 Body mark from harmonic vibration",
        },
        "weakness": (
            "The original alchemical catalyst must be neutralized at the source. "
            "A counter-reagent introduced to the primary crystal will reverse "
            "growth and begin dissolving the formation over 24 hours. "
            "Crystallized victims can be safely released if this occurs within "
            "72 hours of encasement."
        ),
    },

    "whispering_archive": {
        # SOURCE: EXPANDED — consistent with Spirits & knowledge-entity framework (p.69)
        "setting": "newfaire",
        "name": "The Whispering Archive",
        "category": "Spectral",
        "threat_level": 2,
        "description": (
            "A spectral information entity that haunts a repository of knowledge — "
            "library, archive, or record hall. It has absorbed the contents of "
            "every document in its host location. It shares this knowledge freely "
            "but its price is memory: investigators who bargain with it lose "
            "personal recollections, one at a time."
        ),
        "signs": [
            "Books open to relevant pages without being touched",
            "Investigators find notes in their own handwriting they don't remember writing",
            "Whispered voices reciting text when the archive is quiet",
            "Gaps in personal memory following visits — small things forgotten",
            "The archive's catalog is impossibly complete and supernaturally cross-referenced",
        ],
        "mechanics": {
            "knowledge_trade": "Provides one verified clue per Brain mark willingly given",
            "passive_drain": "1 Brain mark per hour spent researching in its presence",
            "memory_gap": "Each transaction removes one specific personal memory",
            "negotiation": "Investigator may bargain for better terms with a Sway roll",
        },
        "weakness": (
            "The Whispering Archive dissolves if its host location is destroyed "
            "or if the original trauma that seeded it — typically a scholar's "
            "obsessive death — is directly addressed and resolved through ritual."
        ),
    },

    "moth_swarm": {
        # SOURCE: EXPANDED — inspired by Biological phenomenon framework (p.65)
        "setting": "newfaire",
        "name": "The Moth Swarm",
        "category": "Biological",
        "threat_level": 3,
        "description": (
            "A biological phenomenon of uncertain origin. Moths carrying a "
            "supernatural pathogen swarm locations of occult significance, "
            "attracted to Bleed energy. Carriers spread a condition called "
            "'the Pale Sleep' — a coma-like state where victims dream in "
            "foreign memories. The swarm acts with coordinated intelligence."
        ),
        "signs": [
            "Massive moth populations appearing suddenly and without natural explanation",
            "Victims enter the Pale Sleep within 24 hours of heavy exposure",
            "Sleeping victims murmur in languages they do not know",
            "Moth wing-dust leaves geometric patterns, not random distribution",
            "The swarm responds aggressively to open flames and Bleed-marked individuals",
        ],
        "mechanics": {
            "pale_sleep": "Body mark after exposure; fail a Control roll for Pale Sleep",
            "bleed_attraction": "Swarm prioritizes investigators with 2+ Bleed marks",
            "fire_aversion": "Open flame forces the swarm back; torches provide protection",
            "coordinated_response": "The swarm acts with Danger equal to threat_level",
        },
        "weakness": (
            "Burning the nest eliminates the swarm. The pathogen is neutralized by "
            "a specific alchemical compound the Doctor specialization can formulate. "
            "Pale Sleep victims can be awakened if the swarm is destroyed within "
            "48 hours of their falling asleep."
        ),
    },

    "undying_fire": {
        # SOURCE: EXPANDED — consistent with Dimensional/Flare framework (pp.65, 70)
        "setting": "newfaire",
        "name": "The Undying Fire",
        "category": "Dimensional",
        "threat_level": 5,
        "description": (
            "A flame that cannot be extinguished by any natural means. It began "
            "as a single candle and has spread for months. It does not burn "
            "materials — it burns memories. What the fire touches becomes "
            "forgotten by everyone who knew it. The fire is building toward "
            "something: an event, a place, a person. When it reaches its "
            "target, that thing will cease to have existed."
        ),
        "signs": [
            "Flame that produces no smoke and leaves no ash",
            "Survivors unable to remember what stood where the fire has passed",
            "Historical records in affected areas contain blank pages or erasures",
            "Investigators experience 'tip of the tongue' amnesia for relevant facts",
            "The fire moves with deliberate direction, not random spread",
        ],
        "mechanics": {
            "memory_erasure": "Brain scar on direct contact; target forgotten by all present",
            "record_corruption": "Verified clues in affected areas are randomly de-verified",
            "inextinguishable": "No conventional fire suppression works",
            "progression": "Danger +2 per session until it reaches its target",
        },
        "weakness": (
            "The Undying Fire is anchored to a specific act of deliberate forgetting — "
            "someone who chose to erase a memory they could not bear. Uncovering and "
            "voicing what was forgotten in the presence of the flame causes it to "
            "collapse inward. The memories it consumed may partially return."
        ),
    },

    "shattered_mirror": {
        # SOURCE: EXPANDED — consistent with Spectral/haunting framework (p.69)
        "setting": "newfaire",
        "name": "Shattered Mirror",
        "category": "Spectral",
        "threat_level": 2,
        "description": (
            "A haunting bound to a specific reflective surface — or surfaces — "
            "that shows alternative versions of the present. Observers see "
            "themselves as they would have been if they had made different "
            "choices. Extended exposure causes investigators to question their "
            "own identity and decisions."
        ),
        "signs": [
            "Reflective surfaces show the viewer in different clothing, contexts, or states",
            "Observers report hearing their 'mirror self' speak or gesture",
            "Glass in the vicinity develops hairline cracks over time",
            "Investigators begin doubting recent decisions and second-guessing each other",
            "Photographs taken near the phenomenon show subjects they don't recognize",
        ],
        "mechanics": {
            "identity_doubt": "Brain mark per scene spent near active reflections",
            "mirror_pull": "Characters with unresolved guilt are especially vulnerable",
            "fracture": "Breaking the mirror doubles the haunting, affecting all reflectives nearby",
            "confrontation": "Direct eye contact with the mirror self triggers a Brain roll",
        },
        "weakness": (
            "The haunting is released when the observer acknowledges their 'mirror self' "
            "as a genuine alternative — not a false path. A ritual of acceptance, "
            "rather than rejection, causes the reflection to still and the haunting to lift."
        ),
    },

    "hunger_below": {
        # SOURCE: EXPANDED — inspired by Biological/underground phenomenon framework (p.65)
        "setting": "newfaire",
        "name": "The Hunger Below",
        "category": "Biological",
        "threat_level": 4,
        "description": (
            "Something vast and biological has colonized the underground beneath "
            "a populated area. Its mycelial network spreads through soil and "
            "foundation, releasing spores that cause ravenous appetite and "
            "compulsive digging behavior in those affected. The Hunger Below "
            "is growing and seems to be waiting to breach the surface."
        ),
        "signs": [
            "Residents in the area report insatiable hunger regardless of food consumed",
            "People found excavating basements, gardens, or streets in a fugue state",
            "A faint bioluminescent glow visible in fresh excavations at night",
            "The ground feels soft and warm in a spreading radius",
            "Animals in the area have disappeared — absorbed, investigators discover",
        ],
        "mechanics": {
            "spore_exposure": "Body mark and compulsion to dig on failed Control roll",
            "network_awareness": "Any digging in the radius alerts the phenomenon",
            "breach_countdown": "Danger 5 triggers surface breach; mass spore event",
            "depth": "The primary organism is 20 ft below grade at minimum",
        },
        "weakness": (
            "The Hunger Below can be starved by cutting off its nutrient chains above. "
            "A coordinated effort to eliminate surface contamination combined with "
            "a ritual sealing of the primary access point will cause the organism "
            "to collapse inward. This requires the circle to work simultaneously "
            "at multiple locations."
        ),
    },

    "bone_singer": {
        # SOURCE: EXPANDED — consistent with Spectral entity framework (p.69)
        "setting": "newfaire",
        "name": "Bone Singer",
        "category": "Spectral",
        "threat_level": 3,
        "description": (
            "An entity that animates skeletal remains and uses them as a choir. "
            "It requires specific harmonic conditions to manifest — usually a "
            "location with acoustic properties. Once active, the Bone Singer "
            "compels listeners to stand motionless and listen until they die "
            "of exposure. The song is described as achingly beautiful."
        ),
        "signs": [
            "Remains found in standing positions, facing inward in a circle",
            "Survivors describe music they cannot forget but cannot reproduce",
            "Acoustic chambers — churches, theaters, caves — show signs of gathering",
            "Stone walls in affected locations vibrate at subsonic frequencies",
            "Animals in the area display compulsive stillness near the location",
        ],
        "mechanics": {
            "compulsion": "Brain mark; fail a Focus roll to act while the song plays",
            "immobility": "Two failures: character stands motionless until the scene ends",
            "ear_protection": "Blocked ears grant advantage on Focus rolls",
            "acoustic_reliance": "The entity cannot manifest outside strong acoustic spaces",
        },
        "weakness": (
            "Destroying the acoustic integrity of the location — breaking windows, "
            "blocking resonance chambers, or introducing discordant sound above "
            "the song's frequency — disrupts the entity's ability to hold form. "
            "A direct sound-based ritual at the center of the space will silence "
            "it permanently."
        ),
    },

    "thought_plague": {
        # SOURCE: EXPANDED — consistent with Dimensional memetic framework (pp.65-66)
        "setting": "newfaire",
        "name": "Thought Plague",
        "category": "Dimensional",
        "threat_level": 4,
        "description": (
            "A memetic phenomenon that propagates through the act of description. "
            "Explaining the Thought Plague transmits it; reading detailed accounts "
            "of it transmits it; even thinking too specifically about it may "
            "accelerate its spread in the thinker. Once infected, a person "
            "cannot stop thinking about it — and cannot stop talking about it."
        ),
        "signs": [
            "Victims who cannot stop describing the same concept, regardless of context",
            "Written materials about the phenomenon multiply and appear in new places",
            "Investigators notice intrusive thoughts about the phenomenon between sessions",
            "Infected individuals have elevated Bleed marks with no physical cause",
            "The phenomenon grows more coherent as more people become aware of it",
        ],
        "mechanics": {
            "transmission": "Reading a full account or hearing a detailed description risks infection",
            "bleed_drain": "Infected characters gain 1 Bleed mark per scene they don't discuss it",
            "investigation_paradox": "Verifying clues about it may spread awareness further",
            "critical_mass": "If 10+ NPCs become infected, Danger jumps to 5",
        },
        "weakness": (
            "The Thought Plague is neutralized by total epistemic containment: "
            "every infected individual must simultaneously receive a counter-memetic "
            "ritual that replaces the compulsive concept with a neutral anchor. "
            "All written materials about it must be destroyed in the same event. "
            "This is extraordinarily difficult to coordinate."
        ),
    },

    "pale_door": {
        # SOURCE: EXPANDED — inspired by Flare/thinning framework (p.3, p.65)
        "setting": "newfaire",
        "name": "The Pale Door",
        "category": "Dimensional",
        "threat_level": 5,
        "description": (
            "A portal to a location that should not exist: a perfect white room "
            "with no walls, no ceiling, and no floor — only endless pale space. "
            "Those who enter often do not return. Those who do return are different: "
            "quieter, more certain, and unwilling to describe what they saw. "
            "The Door has appeared in seven cities. Each time, it leaves behind "
            "a permanent architectural scar that future Doors appear near."
        ),
        "signs": [
            "A door appearing in an impossible location — a wall, a ceiling, mid-air",
            "The door is pale white with no handle, hinges, or frame markings",
            "Those who approach report a sense of certainty that they must open it",
            "Returned individuals refuse to discuss the interior; they share no nightmares",
            "Photographs of the door come out entirely white",
        ],
        "mechanics": {
            "compulsion": "Brain mark; resist with Focus or feel compelled to enter",
            "interior": "Entering the Pale Door removes all marks — and 1 random memory",
            "scar": "Closing the Door leaves a permanent mark on the location",
            "recurrence": "Scars from previous Doors attract new manifestations",
        },
        "weakness": (
            "The Pale Door can be closed from the outside by a circle that refuses "
            "the compulsion collectively — no member entering. A sealing ritual "
            "performed by a Weird specialist on the threshold will permanently "
            "prevent re-manifestation at this scar. What lies inside remains unknown."
        ),
    },
}


__all__ = ["PHENOMENA"]
