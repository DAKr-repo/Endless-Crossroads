"""
CROWN & CREW: QUEST ARCHETYPES
-------------------------------
Seven narrative templates that reshape the Crown & Crew decision engine
around a specific dramatic premise. Each archetype replaces the default
prompt pools, terminology, morning events, council dilemmas, and patron/leader
rosters while preserving the core Blind Allegiance loop and Sway mechanics.

Feed `archetype.to_world_state()` into `CrownAndCrewEngine(world_state=...)`.

Version: 1.0
"""

from __future__ import annotations

from dataclasses import dataclass, field


# =============================================================================
# QUEST ARCHETYPE DATACLASS
# =============================================================================

@dataclass
class QuestArchetype:
    """A self-contained narrative template for a Crown & Crew campaign.

    Attributes:
        name:              Display name shown to the player.
        slug:              Registry lookup key (lowercase, no spaces).
        arc_length:        Default number of days for this quest.
        terms:             Crown/Crew/Neutral/Campfire/World terminology overrides.
        morning_events:    Sway-biased road encounters (text/bias/tag).
        council_dilemmas:  Group vote scenarios (prompt/crown option/crew option).
        prompts_crown:     Temptation-of-order allegiance prompts.
        prompts_crew:      Burden-of-loyalty allegiance prompts.
        prompts_world:     Environment and terrain descriptions.
        prompts_campfire:  Campfire reflection prompts.
        secret_witness:    Breach day special event text.
        special_mechanics: Quest-specific rule overrides.
        rest_config:       Rest/recovery configuration overrides.
        patrons:           Authority-side patron pool.
        leaders:           Rebellion-side leader pool.
        description:       Player-facing quest summary.
    """

    name: str
    slug: str
    arc_length: int
    terms: dict[str, str]
    morning_events: list[dict]
    council_dilemmas: list[dict]
    prompts_crown: list[str]
    prompts_crew: list[str]
    prompts_world: list[str]
    prompts_campfire: list[str]
    secret_witness: str
    special_mechanics: dict = field(default_factory=dict)
    rest_config: dict = field(default_factory=dict)
    patrons: list[str] = field(default_factory=list)
    leaders: list[str] = field(default_factory=list)
    description: str = ""

    def to_world_state(self) -> dict:
        """Convert to the dict format CrownAndCrewEngine.__post_init__ expects.

        Returns a world_state dict with all prompt pools, terms, patron/leader
        lists, and the secret witness string ready for engine injection.
        """
        return {
            "terms": dict(self.terms),
            "prompts_crown": list(self.prompts_crown),
            "prompts_crew": list(self.prompts_crew),
            "prompts_world": list(self.prompts_world),
            "prompts_campfire": list(self.prompts_campfire),
            "secret_witness": self.secret_witness,
            "patrons": list(self.patrons),
            "leaders": list(self.leaders),
            "morning_events": list(self.morning_events),
            "council_dilemmas": list(self.council_dilemmas),
            "arc_length": self.arc_length,
            "quest_name": self.name,
            "quest_slug": self.slug,
            "special_mechanics": dict(self.special_mechanics),
            "rest_config": dict(self.rest_config),
        }


# =============================================================================
# QUEST ARCHETYPE DEFINITIONS
# =============================================================================

_SIEGE = QuestArchetype(
    name="Siege Defense",
    slug="siege",
    arc_length=7,
    description=(
        "The walls are cracked and the granary burns low. Seven days until "
        "the relief column arrives -- or doesn't. Every mouth fed is a sword "
        "unfed. Every gate opened is a gate that cannot close."
    ),
    terms={
        "crown": "The Garrison",
        "crew": "The Holdouts",
        "neutral": "The Deserter",
        "campfire": "The Watch Fire",
        "world": "The Siege",
    },
    patrons=[
        "Commander Ashfeld",
        "The Lord Castellan",
        "Siege-Marshal Ordenna",
        "The Quartermaster General",
    ],
    leaders=[
        "Old Marta of the Undermines",
        "Sergeant Harke the Burned",
        "Sister Vael, the Wall-Preacher",
        "Digger Croy",
    ],
    prompts_crown=[
        "The Castellan orders the eastern slum torched to deny the enemy cover. "
        "Forty families still shelter there. He hands you the brand and says, "
        "'Discipline, not cruelty. Do it before they wake.'",

        "A wounded soldier confesses he's been selling grain through the sewers "
        "to feed his children on the other side of the wall. The Castellan wants "
        "him hanged at dawn as an example. You hold the rope.",

        "The relief column's courier is captured -- alive. The Castellan wants "
        "false intelligence sent back: 'Tell them we've fallen. Let the enemy "
        "relax.' It means no reinforcements. Ever.",

        "A section of wall can be shored up, but only by collapsing the cistern "
        "beneath it. The Garrison keeps its stone. The Holdouts lose their water. "
        "The engineers await your word.",

        "The Castellan offers you a commission -- land, title, name scrubbed clean "
        "-- if you identify which of the Holdouts has been signaling the enemy "
        "with lantern-light from the bell tower.",
    ],
    prompts_crew=[
        "The youngest Holdout found a gap in the wall wide enough for a child. "
        "She wants to crawl through and beg the enemy for food. Old Marta says "
        "no. The girl hasn't eaten in three days. She looks at you.",

        "Sergeant Harke wants to open the postern gate at midnight and let "
        "the wounded civilians out -- into enemy lines. 'They'll take prisoners,' "
        "he says. 'Prisoners get fed.' He might be right.",

        "The Holdouts have been stealing water from the Garrison's reserve. "
        "Marta asks you to stand watch tonight and look the other way. "
        "'The soldiers drink first,' she says. 'Always the soldiers.'",

        "A dying man in the infirmary claims to know a tunnel under the north "
        "tower. He'll only tell you -- not the Garrison. He wants your oath "
        "that you'll use it to get the children out, not the officers.",

        "Sister Vael has been carving names into the wall -- every soul who's "
        "died since the siege began. The Garrison wants it whitewashed. "
        "She asks you to stand between her and the lime bucket.",
    ],
    prompts_world=[
        "Dawn breaks grey over the curtain wall. Smoke from the enemy camp "
        "smudges the horizon in every direction. The catapult stones have "
        "stopped -- which means they're building something worse.",

        "Rain turns the courtyard to a churning mire of mud and ash. The well "
        "water tastes of sulfur. Somewhere below, the sappers are digging, "
        "and you can feel the earth tremble through your boots.",

        "The third wall has fallen. Rubble chokes the market district. "
        "From the remaining battlements you count the enemy's fires -- "
        "more than last night. Always more.",

        "A fog rolls in from the river, thick as wool. Visibility drops to "
        "an arm's length. The sentries can't see the wall's edge. "
        "Something scrapes at the stone below the parapet.",

        "The sun is a white wound behind the smoke. Heat radiates from the "
        "walls -- the enemy poured burning pitch on the eastern face at dawn. "
        "The stones are too hot to touch. The defenders have nowhere to lean.",
    ],
    prompts_campfire=[
        "Someone pulls a fiddle from the rubble. It's missing a string. "
        "They play anyway -- a hymn from before the siege, when the gate "
        "was a gate and not a grave. Who taught you that song?",

        "The watch fire gutters low. A child asks you what the sky looks "
        "like without smoke. You try to remember. When was the last time "
        "you saw stars?",

        "A soldier shows you a letter he'll never send -- addressed to "
        "someone on the other side of the wall. 'Do you think they know?' "
        "he asks. You don't answer.",

        "The Holdouts share a single heel of bread, passing it hand to hand. "
        "When it reaches you, it's mostly crumbs. Someone says grace anyway. "
        "What do you pray for tonight?",

        "Old Marta sits with her back to the fire, watching the wall. "
        "'I built that gate,' she says. 'Thirty years ago. Hung every hinge.' "
        "She's quiet for a long time. 'They won't get through my gate.'",
    ],
    morning_events=[
        {
            "text": "A white flag rises over the enemy lines at dawn. A herald "
                    "approaches the gate with terms -- generous terms. The "
                    "Castellan watches from the parapet, jaw tight.",
            "bias": "crown", "tag": "GUILE",
        },
        {
            "text": "You wake to screaming. A section of the outer wall collapsed "
                    "in the night. Three sentries are buried. The Holdouts are "
                    "already digging with their hands.",
            "bias": "crew", "tag": "BLOOD",
        },
        {
            "text": "A pigeon lands on the battlements carrying a message from "
                    "the relief column. The cipher is one you don't recognize. "
                    "The Castellan can read it. So can Old Marta.",
            "bias": "neutral", "tag": "SILENCE",
        },
        {
            "text": "Smoke pours from the granary. Someone set a fire in the night. "
                    "The Garrison blames the Holdouts. The Holdouts blame the "
                    "Garrison. A week's grain is ash.",
            "bias": "neutral", "tag": "DEFIANCE",
        },
        {
            "text": "A Garrison officer is found dead in the latrine with a Holdout "
                    "knife in his back. Harke says it was self-defense. The Castellan "
                    "says it was murder. Both are lying.",
            "bias": "crew", "tag": "BLOOD",
        },
    ],
    council_dilemmas=[
        {
            "prompt": "The grain stores will last three more days at current rations. "
                      "The Garrison proposes cutting civilian rations in half. The "
                      "Holdouts demand the soldiers share equally.",
            "crown": "Military discipline. Half rations for civilians, full for fighters.",
            "crew": "Equal shares. Every belly growls the same, sword or no sword.",
        },
        {
            "prompt": "Enemy sappers have been spotted beneath the north tower. The "
                      "Garrison wants to flood the tunnels. The Holdout children "
                      "shelter directly above.",
            "crown": "Flood the tunnels. Relocate the children to the already-crowded south ward.",
            "crew": "Collapse the tunnel entrance instead. Riskier, but no one moves.",
        },
        {
            "prompt": "A traitor has been feeding the enemy information. The Castellan "
                      "wants to execute all suspected sympathizers. Marta wants a trial.",
            "crown": "Execute the suspects. The siege allows no luxury of doubt.",
            "crew": "Hold a trial. Even surrounded, justice has a shape.",
        },
        {
            "prompt": "The enemy offers to let the women and children leave unharmed if "
                      "the Garrison surrenders its weapons. The Castellan refuses. "
                      "The Holdouts are divided.",
            "crown": "Refuse. Surrendering arms means death for everyone, eventually.",
            "crew": "Accept for the children. Find other ways to fight.",
        },
        {
            "prompt": "A section of wall can be repaired, but the stone must come from "
                      "the temple. The Holdouts consider it sacred. The Garrison "
                      "considers it rubble.",
            "crown": "Tear down the temple. Stone is stone. Survival is sacred.",
            "crew": "Defend the temple. Some things matter more than walls.",
        },
    ],
    secret_witness=(
        "A figure crawls through the breach in the north wall -- not an enemy soldier, "
        "but a child from the other side. She carries a doll stuffed with a message. "
        "The message is addressed to you. It is written in your handwriting."
    ),
    special_mechanics={
        "supply_track": True,
        "wall_integrity": 3,
        "breach_day_override": 4,
    },
    rest_config={
        "heal_amount": 0,
        "ration_cost": 1,
        "morale_decay": True,
    },
)


_SUMMIT = QuestArchetype(
    name="Diplomatic Summit",
    slug="summit",
    arc_length=4,
    description=(
        "Four days of negotiation in a marble hall where every smile hides a "
        "blade. The treaty could end a war or start three more. Every word "
        "you speak will be carved into history -- or used against you."
    ),
    terms={
        "crown": "The Delegation",
        "crew": "The Dissidents",
        "neutral": "The Abstainer",
        "campfire": "The Evening Reception",
        "world": "The Summit Hall",
    },
    patrons=[
        "Ambassador Selene Kray",
        "The Arch-Chancellor",
        "Lord Provost Dain",
    ],
    leaders=[
        "Exile-Speaker Renn",
        "The Masked Delegate",
        "Councillor Ashe, the Defector",
    ],
    prompts_crown=[
        "The Arch-Chancellor slides a draft treaty across the table. It cedes "
        "the northern provinces in exchange for ten years of peace. 'Sign it,' "
        "she says. 'The provinces were lost already.'",

        "A rival delegate has evidence of your past -- letters, ledgers, a name "
        "you buried. The Delegation offers to make it disappear. The price is "
        "your vote on the tariff resolution.",

        "The Ambassador asks you to plant forged documents in the Dissident "
        "quarters -- proof of a conspiracy that doesn't exist. 'We need them "
        "discredited before the final vote,' she says. 'Truth is a luxury.'",

        "A trade agreement would bring prosperity to three cities and poverty to "
        "twelve villages. The Delegation calls it progress. They need your seal "
        "before the ink dries.",

        "Lord Provost Dain offers you a seat on the permanent council. A lifetime "
        "appointment. All you must do is abstain from tomorrow's vote on refugee "
        "resettlement. 'Silence is not betrayal,' he says.",
    ],
    prompts_crew=[
        "Exile-Speaker Renn shows you a list of names -- dissidents who vanished "
        "after the last summit. She asks you to read them aloud in the hall "
        "tomorrow. 'Let the marble remember,' she says.",

        "The Masked Delegate wants to leak the Delegation's private correspondence "
        "to the public press. The letters prove corruption. They also endanger "
        "three operatives behind enemy lines.",

        "Councillor Ashe has been poisoned -- slowly, over three days. She suspects "
        "her own aide. She asks you to switch her wine cup with the Ambassador's "
        "at tonight's reception. 'Let them taste their own medicine.'",

        "The Dissidents plan to walk out of the summit in protest. If you join them, "
        "the treaty collapses. If you stay, you legitimize the process they call "
        "a farce. Renn watches your face.",

        "A servant brings you a note: the Delegation plans to arrest the Dissidents "
        "at dawn under diplomatic immunity revocation. You have six hours. Renn's "
        "quarters are on the third floor. The guards change at midnight.",
    ],
    prompts_world=[
        "The summit hall is carved from a single block of white stone, veined "
        "with gold. Every whisper echoes. Every silence is louder. The chandeliers "
        "cast shadows that move when no one does.",

        "Rain hammers the leaded windows of the embassy. The gardens below are "
        "drowning. Delegates huddle in corridors, speaking in languages you half "
        "understand. A locked door on the second floor has no keyhole.",

        "The banquet table stretches forty feet. Silver platters, crystal goblets, "
        "and a centerpiece of fresh roses -- in winter. Someone spent a fortune "
        "to remind you who holds the purse strings.",

        "The gallery above the main hall is closed to delegates. You see shadows "
        "moving behind the lattice -- scribes, you're told. But scribes don't "
        "carry crossbows.",

        "The summit grounds are ringed by an iron fence older than the treaty. "
        "Beyond it, a crowd has gathered -- silent, watching. They hold no signs. "
        "They carry no weapons. They simply wait.",
    ],
    prompts_campfire=[
        "The reception hall empties. You pour yourself a glass of something "
        "expensive and stand at the window. The crowd is still there, torches "
        "flickering in the rain. What do they want from you?",

        "A junior delegate sits alone in the garden, soaked to the bone. He "
        "tells you he came here to change things. 'Instead, I learned how "
        "small my voice is.' What do you tell him?",

        "Someone left a book of poetry on your chair -- dog-eared to a page "
        "about a king who traded his crown for a fishing boat. There's no "
        "note. Who do you think left it?",

        "You catch your reflection in the polished table. The face looking "
        "back wears the same mask as everyone else in this building. When "
        "did you learn to smile like that?",

        "The Arch-Chancellor's aide approaches you in the empty corridor. "
        "'Off the record,' she says. 'Do you actually believe any of this "
        "matters?' She seems genuinely curious.",
    ],
    morning_events=[
        {
            "text": "A pamphlet appears under every door overnight. It lists the "
                    "Delegation's private holdings and asks a single question: "
                    "'Who profits from peace?'",
            "bias": "crew", "tag": "DEFIANCE",
        },
        {
            "text": "The Ambassador's personal guard doubles. She walks the halls "
                    "with an escort of six. Something has changed. She won't say what.",
            "bias": "crown", "tag": "SILENCE",
        },
        {
            "text": "A delegate from a neutral state withdraws without explanation. "
                    "Her seat sits empty in the hall, a bouquet of white lilies "
                    "placed on the cushion. No one claims them.",
            "bias": "neutral", "tag": "GUILE",
        },
        {
            "text": "You find a knife embedded in your door at dawn. No note. No "
                    "blood. The Delegation calls it a prank. The Dissidents call it "
                    "a warning. The blade is very real.",
            "bias": "neutral", "tag": "BLOOD",
        },
        {
            "text": "The Masked Delegate removes his mask in the breakfast hall. "
                    "The face beneath is scarred -- burns, old and deep. 'Now you "
                    "know what the last treaty cost,' he says.",
            "bias": "crew", "tag": "HEARTH",
        },
    ],
    council_dilemmas=[
        {
            "prompt": "The treaty's final clause demands hostage exchanges -- noble "
                      "children from both sides as guarantees of peace. The Delegation "
                      "has already chosen the children. The Dissidents have not.",
            "crown": "Accept the exchange. Hostages are tradition, not cruelty.",
            "crew": "Reject it. No treaty built on children's fear deserves a seal.",
        },
        {
            "prompt": "A border province has declared independence from both factions. "
                      "The treaty can recognize them or partition them. Recognition "
                      "means a precedent. Partition means war.",
            "crown": "Partition. Precedent is more dangerous than any single war.",
            "crew": "Recognize. Self-determination is the only right worth defending.",
        },
        {
            "prompt": "The summit's host nation demands a 'truth commission' to "
                      "investigate war crimes. Both sides committed atrocities. "
                      "Both sides have evidence.",
            "crown": "Oppose. The commission would destabilize the peace process.",
            "crew": "Support. Peace without justice is just a longer silence.",
        },
        {
            "prompt": "An assassination attempt is made on the Arch-Chancellor. The "
                      "assassin carries Dissident tokens. Renn says they're planted. "
                      "The Delegation demands expulsion.",
            "crown": "Expel the Dissidents. Security cannot be compromised.",
            "crew": "Demand an investigation. Planted evidence is the oldest trick at court.",
        },
        {
            "prompt": "The final treaty draft is ready. It is imperfect -- both sides "
                      "lose something sacred. But it is finished. Do you sign?",
            "crown": "Sign. An imperfect peace is better than a perfect war.",
            "crew": "Refuse. This treaty only delays the reckoning.",
        },
    ],
    secret_witness=(
        "During the midnight reception, a servant drops a tray and a sealed "
        "letter slides across the marble floor to your feet. It bears your "
        "family's wax seal -- broken. Inside, in a hand you recognize, a single "
        "line: 'They know what you did at Kennford. Come home.' The hall is watching."
    ),
    special_mechanics={
        "influence_track": True,
        "leverage_tokens": 2,
        "private_meetings": True,
    },
    rest_config={
        "heal_amount": 1,
        "ration_cost": 0,
        "morale_decay": False,
    },
)


_TRIAL = QuestArchetype(
    name="Trial of the Accused",
    slug="trial",
    arc_length=5,
    description=(
        "The accused sits in chains. The evidence is damning -- or manufactured. "
        "Five days to determine the truth, if truth still lives in a city where "
        "justice is bought by the yard."
    ),
    terms={
        "crown": "The Tribunal",
        "crew": "The Accused",
        "neutral": "The Juror",
        "campfire": "The Vigil",
        "world": "The Court",
    },
    patrons=[
        "High Magistrate Vren",
        "The Lord Prosecutor",
        "Justiciar Oram, the Unyielding",
    ],
    leaders=[
        "The Accused (who will not speak their name)",
        "Advocate Lira, the Last Defender",
        "Brother Salk, the Cellkeeper",
    ],
    prompts_crown=[
        "The Lord Prosecutor presents a ledger of the Accused's transactions. "
        "Every entry is damning. Every entry is also in someone else's "
        "handwriting. He asks if you noticed. You did.",

        "High Magistrate Vren offers you a private audience. 'The verdict is "
        "already decided,' she says. 'Your role is to make it look earned.' "
        "She pours you wine from a crystal decanter.",

        "A witness recants on the stand -- then recants the recantation when "
        "the Prosecutor's aide enters the gallery. The Magistrate asks if "
        "you'd like the testimony stricken. The aide watches you.",

        "Evidence arrives sealed in the Tribunal's own wax -- a confession, "
        "signed by the Accused. The signature is perfect. Too perfect. "
        "The Prosecutor says authenticity is not your concern.",

        "Justiciar Oram tells you the Accused has information that could "
        "expose a network of corruption reaching the highest offices. 'A "
        "conviction keeps the lid on,' he says. 'An acquittal opens the box.'",
    ],
    prompts_crew=[
        "Advocate Lira slides a note under the table. It reads: 'The witness "
        "they're calling tomorrow was paid. I can prove it. But the proof "
        "implicates someone you love.' She doesn't look up.",

        "Brother Salk brings you to the cells at midnight. The Accused speaks "
        "for the first time: 'I did what they say. But not why they say. "
        "Ask them about the children.' Then silence.",

        "The Accused's family waits outside the court every morning. A daughter, "
        "no older than ten, holds a drawing of a house with smoke coming from "
        "the chimney. She asks you if her parent is coming home.",

        "Lira tells you a previous juror was found face-down in the canal last "
        "month. 'Slipped,' the report said. 'Ask yourself why the Tribunal "
        "needs twelve new jurors every season.'",

        "A guard slips you a key to the evidence vault. Inside: a second ledger "
        "that contradicts the first. Someone has been building this case for "
        "years -- and building it wrong. On purpose.",
    ],
    prompts_world=[
        "The courthouse was a cathedral once. The nave is the gallery, the altar "
        "is the bench, and the confessionals have been converted to holding cells. "
        "The stained glass still shows mercy. The building has forgotten the word.",

        "Rain drips through a crack in the courthouse dome, pooling on the marble "
        "scales carved into the floor. One side of the scale is submerged. "
        "The other is dry. No one remarks on the symbolism.",

        "The courtyard fills with onlookers before dawn. They bring food, blankets, "
        "opinions. A man sells small effigies of the Accused -- some with nooses, "
        "some with halos. Both sell equally well.",

        "The evidence room smells of dust and old paper. Shelves stretch to the "
        "ceiling, stuffed with cases no one will ever reopen. Your case file is "
        "thin. Suspiciously thin.",

        "The bell tower above the courthouse rings once at sunrise, once at "
        "verdict. It has not rung at sunset in fourteen years. The last time "
        "it did, three judges were hanged from its frame.",
    ],
    prompts_campfire=[
        "The vigil candle burns in the window of the jurors' quarters. Someone "
        "asks what justice means. Not the legal definition -- the real one. "
        "The one that keeps you awake. What do you say?",

        "Lira sits on the courthouse steps, shoes off, feet in the rain. "
        "'I've defended sixty-three people in this court,' she says. 'Eleven "
        "were innocent. I saved four.' She counts on her fingers.",

        "A fellow juror breaks down weeping in the corridor. He recognized "
        "the Accused -- a childhood friend, from before. 'I can't judge him,' "
        "he says. 'I can't not.' Who do you comfort?",

        "You find the Accused's effects in a box behind the bench: a ring, "
        "a letter never sent, a child's tooth wrapped in cloth. Evidence of "
        "what? Of being human. Does it matter?",

        "The vigil candle gutters out. In the dark, someone whispers: 'We all "
        "know what happened. The question is whether knowing is enough.' "
        "You don't recognize the voice.",
    ],
    morning_events=[
        {
            "text": "A crowd gathers outside the courthouse at dawn, split by a "
                    "rope -- supporters on one side, accusers on the other. The "
                    "rope is fraying in the middle.",
            "bias": "neutral", "tag": "DEFIANCE",
        },
        {
            "text": "The Prosecutor's carriage arrives flanked by armed guards. "
                    "He steps out smiling. He has never lost a case. His smile "
                    "does not reach his eyes.",
            "bias": "crown", "tag": "GUILE",
        },
        {
            "text": "A note is nailed to the courthouse door: 'THE VERDICT WAS "
                    "WRITTEN BEFORE THE TRIAL BEGAN.' The guards tear it down. "
                    "Another appears by noon.",
            "bias": "crew", "tag": "DEFIANCE",
        },
        {
            "text": "You pass the Accused being led from the cells. They catch "
                    "your eye and mouth a single word you cannot hear. Their "
                    "wrists are raw from the irons.",
            "bias": "crew", "tag": "HEARTH",
        },
        {
            "text": "High Magistrate Vren walks the gallery alone before court opens. "
                    "She pauses at the empty witness stand and touches the railing "
                    "like a doctor checking a pulse.",
            "bias": "crown", "tag": "SILENCE",
        },
    ],
    council_dilemmas=[
        {
            "prompt": "A new witness has come forward -- but their testimony was "
                      "obtained under duress. The Tribunal wants to admit it. "
                      "The defense wants it thrown out.",
            "crown": "Admit the testimony. The court decides its weight.",
            "crew": "Exclude it. Evidence born from pain is evidence of nothing.",
        },
        {
            "prompt": "The Accused requests to address the court directly. The "
                      "Tribunal fears a public spectacle. The defense argues it "
                      "is a fundamental right.",
            "crown": "Deny the request. Order must be maintained.",
            "crew": "Grant it. A voice silenced is a verdict predetermined.",
        },
        {
            "prompt": "Evidence has surfaced that another person may have committed "
                      "the crime. Pursuing the lead would delay the trial by weeks "
                      "and cost the court's credibility.",
            "crown": "Proceed with the current defendant. The evidence is sufficient.",
            "crew": "Delay the trial. One wrong conviction poisons every future verdict.",
        },
        {
            "prompt": "The Accused offers to plead guilty in exchange for exile rather "
                      "than execution. The Tribunal sees efficiency. The Accused's "
                      "family sees surrender.",
            "crown": "Accept the plea. Swift resolution serves justice.",
            "crew": "Reject it. A forced confession is the Tribunal's confession, not theirs.",
        },
        {
            "prompt": "A juror has been seen meeting with the Prosecutor in private. "
                      "Removing them delays the verdict. Keeping them taints it.",
            "crown": "Keep the juror. Accusation is not proof -- the trial must continue.",
            "crew": "Remove the juror. The trial is already bleeding. Stop the wound.",
        },
    ],
    secret_witness=(
        "The courthouse doors are sealed for the evening when a figure in a "
        "hooded cloak enters through the crypt passage. They carry a box -- "
        "inside it, the real evidence. The evidence that condemns not the "
        "Accused, but the Tribunal itself. They set it on the bench and leave. "
        "The box has your name on the lid."
    ),
    special_mechanics={
        "evidence_track": True,
        "testimony_slots": 3,
        "jury_opinion": 0,
    },
    rest_config={
        "heal_amount": 1,
        "ration_cost": 0,
        "morale_decay": False,
    },
)


_CARAVAN = QuestArchetype(
    name="Caravan Expedition",
    slug="caravan",
    arc_length=6,
    description=(
        "Six days across the Ashwaste with forty souls, twelve wagons, and "
        "whatever the desert decides to take. The Company pays for cargo "
        "delivered. The Stragglers pay for every mile walked."
    ),
    terms={
        "crown": "The Company",
        "crew": "The Stragglers",
        "neutral": "The Drifter",
        "campfire": "The Circle",
        "world": "The Waste",
    },
    patrons=[
        "Trade-Captain Osen Blacktallow",
        "The Comptroller",
        "Factor Giraud of the Syndicate",
        "Wagonmaster Hel",
    ],
    leaders=[
        "Kess the Water-Finder",
        "Old Dalla, the Straggler Queen",
        "The Burned Cartographer",
        "Selem, who walks barefoot",
    ],
    prompts_crown=[
        "The Trade-Captain weighs the cargo against the water supply and "
        "announces that two wagons must be abandoned. One carries silk worth "
        "a fortune. The other carries the Stragglers' medicine. He asks which.",

        "A shortcut through the Bone Canyon would save two days. The canyon "
        "is marked on no map -- the Comptroller bought the route from a dying "
        "prospector. The Stragglers say the canyon eats caravans.",

        "Factor Giraud offers to double your share if you inventory the "
        "Stragglers' personal belongings. 'Contraband check,' he calls it. "
        "You know he's looking for the Water-Finder's maps.",

        "The oxen are failing. The Company proposes leaving the weakest animals "
        "and redistributing their loads to the Stragglers -- on their backs. "
        "'They walk anyway,' says Hel. 'Might as well carry something.'",

        "A rider from the Syndicate catches up with sealed orders. The cargo "
        "you've been hauling is not silk -- it's weapons. The buyer is the "
        "warlord whose territory you're crossing. Giraud smiles.",
    ],
    prompts_crew=[
        "Kess finds water -- a seep beneath a dead acacia. Enough for the "
        "Stragglers, not the whole caravan. Old Dalla says to drink quietly "
        "and fill the skins before dawn. 'Let the Company buy its own water.'",

        "A Straggler child wandered from camp last night and hasn't returned. "
        "The Company will not stop the caravan to search. Old Dalla looks at "
        "you. The desert is patient and does not give things back.",

        "Selem has been stealing grain from the Company wagons -- a handful "
        "each night, ground between stones. The Stragglers have been eating "
        "flat cakes they shouldn't have. Selem asks for your silence.",

        "The Burned Cartographer unfolds a map drawn on human skin. It shows "
        "a route to an oasis the Company doesn't know about. Taking it means "
        "splitting from the caravan. The Stragglers would be alone.",

        "Old Dalla is dying. Sun-sickness, dehydration, age. She asks you "
        "to carry her bones to the border -- not for burial, but for proof. "
        "'Tell them a free woman walked the Waste and finished the crossing.'",
    ],
    prompts_world=[
        "The Ashwaste stretches flat and featureless to the horizon. The heat "
        "makes the air shimmer. A wagon wheel cracks and the sound carries for "
        "miles. Vultures circle, patient as creditors.",

        "Salt flats give way to red dunes at midday. The sand sings when the "
        "wind hits it -- a low, mournful tone that crawls into your skull. "
        "The oxen won't cross without blindfolds.",

        "You camp in the ruins of a way-station. The walls are scorched. The "
        "cistern is dry. Someone carved a single word into the stone above "
        "the door: TURN. The next way-station is four days out.",

        "A sandstorm builds on the western horizon, a wall of orange and "
        "brown three hundred feet tall. The caravan has two hours to find "
        "shelter. There is no shelter.",

        "The trail drops into a canyon carved by a river that died a thousand "
        "years ago. Petrified trees line the banks like sentries. The rock "
        "walls are close enough to touch from the wagon seats. Sound echoes "
        "strangely here -- your own footsteps return a half-beat late.",
    ],
    prompts_campfire=[
        "The circle gathers around a fire made of scrub brush and dried dung. "
        "Someone produces a flask -- the last of the brandy. It goes around "
        "once. What toast do you make?",

        "A Straggler hums a song from the coast. It's about rain. Half the "
        "circle closes their eyes. When was the last time you felt rain on "
        "your face? What were you doing?",

        "Kess draws a map in the sand by firelight. Not a map of the route -- "
        "a map of home. She points to a spot on the coast. 'That's where "
        "the water tastes like pears.' Where is your spot?",

        "The Burned Cartographer peels the wrapping from his hands. The scars "
        "beneath are deliberate -- letters, in a language you don't recognize. "
        "'My contract,' he says. 'Signed in the only ink they trusted.'",

        "Old Dalla tells a story about a caravan that crossed the Waste without "
        "losing a single soul. 'No one believes it,' she says. 'But it happened. "
        "Once.' She doesn't say what was different.",
    ],
    morning_events=[
        {
            "text": "You wake to find two wagons gone -- driven out in the night "
                    "by Company drovers heading back east. The Trade-Captain says "
                    "nothing. The cargo manifests have been revised.",
            "bias": "crown", "tag": "GUILE",
        },
        {
            "text": "Buzzards land on the supply wagon at dawn and won't scatter. "
                    "The Stragglers say it's an omen. The Company says it's protein. "
                    "Someone gets the crossbow.",
            "bias": "neutral", "tag": "BLOOD",
        },
        {
            "text": "Riders on the horizon. They keep their distance, matching your "
                    "pace. The Company counts fifteen. The Stragglers count twenty. "
                    "No one can agree on the banners.",
            "bias": "neutral", "tag": "SILENCE",
        },
        {
            "text": "Kess wakes screaming. She dreamed of water -- and then of "
                    "something in the water. She says the oasis ahead is wrong. "
                    "The Company doesn't listen to dreams.",
            "bias": "crew", "tag": "HEARTH",
        },
        {
            "text": "A Straggler finds a Company lockbox fallen from a wagon, seal "
                    "cracked open. Inside: letters of credit, a pistol, and a list "
                    "of names. Every Straggler is on it.",
            "bias": "crew", "tag": "DEFIANCE",
        },
    ],
    council_dilemmas=[
        {
            "prompt": "The water supply is fouled. Half the barrels taste of copper "
                      "and bile. The Company wants to press on to the next source. "
                      "The Stragglers want to boil and filter what remains.",
            "crown": "Press on. Speed saves more lives than caution in the Waste.",
            "crew": "Stop and filter. Poisoned water kills faster than thirst.",
        },
        {
            "prompt": "The riders on the horizon have sent an emissary. They demand "
                      "a 'crossing tax' -- one wagon of goods. The Company refuses. "
                      "The Stragglers note they're outnumbered.",
            "crown": "Refuse and arm the caravan. Paying once means paying forever.",
            "crew": "Pay the tax. One wagon is cheaper than a battle in the open.",
        },
        {
            "prompt": "A sick ox must be put down. Its meat could feed everyone for "
                      "two days, but the Stragglers believe the animal carries a curse. "
                      "The Company calls that superstition.",
            "crown": "Butcher the ox. Hunger is the only curse that matters.",
            "crew": "Leave it. The Stragglers know this land better than the manifest.",
        },
        {
            "prompt": "The shortcut through the dunes saves a day but crosses a "
                      "burial ground. The Stragglers won't walk on the dead. The "
                      "Company doesn't believe in ghosts.",
            "crown": "Take the shortcut. The dead don't own the sand.",
            "crew": "Go around. Respect costs a day. Disrespect costs more.",
        },
        {
            "prompt": "A Straggler woman has gone into labor. The caravan must stop "
                      "or she must be left behind with a guard. The Company sees "
                      "mathematics. The Stragglers see a life beginning.",
            "crown": "Leave a guard and continue. The many cannot wait for the one.",
            "crew": "Stop the caravan. A life born in the Waste deserves witnesses.",
        },
    ],
    secret_witness=(
        "On the fourth night, a figure walks into camp from the direction no one "
        "came from -- due south, where the maps show nothing. They are sun-blackened, "
        "barefoot, and carry a water skin that is impossibly full. They pour a cup, "
        "offer it to you, and say: 'I was sent to find the one who carries the "
        "wrong name.' Then they sit down and wait."
    ),
    special_mechanics={
        "supply_track": True,
        "water_per_day": 2,
        "terrain_hazard_chance": 0.3,
    },
    rest_config={
        "heal_amount": 1,
        "ration_cost": 2,
        "morale_decay": True,
    },
)


_HEIST = QuestArchetype(
    name="The Grand Heist",
    slug="heist",
    arc_length=3,
    description=(
        "Three days. One vault. A crew of liars, thieves, and desperate souls "
        "bound by nothing but the promise of what's inside. The Mark has more "
        "guards than you have plans. But plans are cheap."
    ),
    terms={
        "crown": "The Mark",
        "crew": "The Crew",
        "neutral": "The Freelancer",
        "campfire": "The Back Room",
        "world": "The District",
    },
    patrons=[
        "Lord-Merchant Caul Vennick",
        "The Keeper of the Vault",
        "Overseer Brynn, the Eye",
    ],
    leaders=[
        "Sable, the Planner",
        "Finch, who picks any lock",
        "The Inside Man (no name given)",
    ],
    prompts_crown=[
        "Lord-Merchant Vennick's agent finds you in the market. He knows about "
        "the job. He offers triple your cut to walk away -- and quadruple if "
        "you bring him Sable's real name.",

        "The Vault's security rotation has changed. The new pattern is impossible "
        "to crack -- unless you turn yourself in at the gate and let them process "
        "you. The Mark's bureaucracy is the only way in.",

        "Overseer Brynn intercepts you in the warehouse district. She doesn't "
        "threaten. She offers: a clean record, a house in the upper quarter, "
        "a pension. 'All I need is the entry point and the time.'",

        "A guard you bribed sends word: he wants out. He'll raise the alarm at "
        "midnight unless you double his payment. The only money left is the "
        "Crew's emergency fund -- the one that gets them out alive if it goes wrong.",

        "The Keeper of the Vault sends a chess piece to your safehouse. A white "
        "king, toppled. The message is clear: surrender now and he'll let the "
        "Crew scatter. Continue, and he'll make an example.",
    ],
    prompts_crew=[
        "Sable changes the plan for the third time. The new route goes through "
        "the sewers -- and through the Keeper's private quarters. 'Trust me,' "
        "she says. Her hands are shaking. She's never shaken before.",

        "Finch tells you the Inside Man is compromised. He doesn't know it yet. "
        "'We can still use him,' Finch says. 'One last time. He walks in clean "
        "and walks out burned. We get the window we need.'",

        "The Crew's safecracker is dead -- killed in an unrelated bar fight last "
        "night. The only replacement is a kid, barely eighteen, with fast hands "
        "and no idea what she's walking into. Sable says she'll do.",

        "The Inside Man passes you a note in the crowd: 'They moved the contents "
        "yesterday. Vault is empty. But the Keeper's office has something better.' "
        "He doesn't say what. He doesn't say how he knows.",

        "Sable pulls you aside after the final briefing. 'If this goes sideways, "
        "I'm not coming back for anyone. That includes you.' She holds your gaze. "
        "'Tell me you understand.'",
    ],
    prompts_world=[
        "The merchant district hums with money -- gold in the counting houses, "
        "silk in the warehouses, blood in the gutters. The Vault sits at the end "
        "of Coin Street like a fist made of granite, windowless and absolute.",

        "Rain slicks the cobblestones. Gas lamps hiss and flicker in the alley "
        "behind the Vault. Two guards share a cigarette at the service entrance. "
        "Their shift changes in nine minutes. You counted.",

        "The safehouse is a room above a tannery. The stench is useful -- no one "
        "lingers. Maps cover every wall. Red string connects entry points to "
        "escape routes. One string has been cut. No one will say who did it.",

        "The upper quarter sleeps behind wrought-iron gates and private guards. "
        "Every window dark, every door locked, every shadow owned. The Vault "
        "sits among mansions like a church among sinners -- the only honest "
        "building on the street.",

        "Market day. The district floods with bodies -- porters, merchants, "
        "pickpockets, guards. Noise covers everything. The Crew moves through "
        "the crowd like fish through water. Today is the day.",
    ],
    prompts_campfire=[
        "The back room is quiet. Sable deals cards no one plays. Someone asks "
        "what you'll do with your share. Not what you'll buy -- what you'll "
        "do. Where you'll go. Who you'll become.",

        "Finch sharpens her picks by candlelight. Thirty-two picks, each named "
        "after someone who taught her something. She holds up the smallest one. "
        "'This one's called Mercy.' She doesn't explain.",

        "The Inside Man joins you for the last time. He drinks water, not wine. "
        "He says he has a daughter. He's never mentioned a daughter before. "
        "He asks if you think it's worth it.",

        "Someone found a cat in the alley. It sits on the map table, pawing at "
        "the Vault's blueprints. Sable says it's a good omen. Finch says "
        "there are no good omens. The cat doesn't care.",

        "You can't sleep. The ceiling of the safehouse has a crack shaped like "
        "a river. You trace it in the dark. Tomorrow you'll be rich, or dead, "
        "or in irons. Which one scares you most?",
    ],
    morning_events=[
        {
            "text": "A city watch patrol stops outside the safehouse at dawn. "
                    "They hammer on the tannery door, ask questions, and leave. "
                    "They were looking for someone else. This time.",
            "bias": "crown", "tag": "SILENCE",
        },
        {
            "text": "Finch returns from reconnaissance pale-faced. The Vault has "
                    "new locks -- Dwarvish mechanisms, triple-tumbler. She can crack "
                    "them, but not quietly. And not quickly.",
            "bias": "crew", "tag": "GUILE",
        },
        {
            "text": "A broadsheet in the market square describes a 'daring theft' "
                    "at a rival merchant's warehouse. The method is identical to "
                    "your plan. Coincidence, or a message.",
            "bias": "neutral", "tag": "DEFIANCE",
        },
        {
            "text": "You find a gold coin on your pillow when you wake. It bears "
                    "the Vault's seal. No one in the safehouse left it. No one "
                    "in the safehouse could have.",
            "bias": "neutral", "tag": "HEARTH",
        },
        {
            "text": "The Inside Man doesn't show for the morning briefing. His chair "
                    "sits empty. Sable waits an hour, then crosses his name off "
                    "the roster without a word.",
            "bias": "crew", "tag": "BLOOD",
        },
    ],
    council_dilemmas=[
        {
            "prompt": "The entry plan has two options: the sewer tunnel (slow, safe, "
                      "filthy) or the rooftop traverse (fast, exposed, lethal if "
                      "spotted). The Crew is split.",
            "crown": "Rooftop. Speed is safety. Hesitation is the real risk.",
            "crew": "Sewers. Pride gets you killed. Dirt washes off.",
        },
        {
            "prompt": "A guard recognizes Finch from a previous job. He'll keep quiet "
                      "for a price -- or he can be silenced permanently. Sable leaves "
                      "the decision to you.",
            "crown": "Pay him. Dead guards attract investigators.",
            "crew": "Silence him. Witnesses are liabilities, not assets.",
        },
        {
            "prompt": "The Vault contains more than expected. Taking it all means "
                      "overloading the escape route. Taking only the target means "
                      "leaving a fortune behind.",
            "crown": "Take the target only. Greed is how heists become massacres.",
            "crew": "Take everything. You'll never get this chance again.",
        },
        {
            "prompt": "The escape route passes through a residential block. A fire "
                      "diversion would guarantee a clean exit. Twelve families live "
                      "in those buildings.",
            "crown": "Set the fire. Twelve families wake up scared. The Crew wakes up free.",
            "crew": "Find another way. We're thieves, not murderers.",
        },
        {
            "prompt": "After the job, the Crew can scatter immediately or hide in the "
                      "safehouse for three days until the search dies down. Scattering "
                      "is riskier but leaves no evidence. Hiding is safer but a single "
                      "tip destroys everyone.",
            "crown": "Scatter. Individual risk is better than collective ruin.",
            "crew": "Hide together. We finish this the way we started -- together.",
        },
    ],
    secret_witness=(
        "On the eve of the job, a figure steps from the shadows of the tannery "
        "alley. They wear the Vault's livery and carry a ring of keys -- every key "
        "to every door you planned to crack. They set the ring on the windowsill "
        "and say: 'The Keeper sends his regards. He wants to see what you do "
        "when the locks don't matter.' Then they're gone."
    ),
    special_mechanics={
        "heat_track": 0,
        "heat_max": 10,
        "crew_trust": 3,
        "noise_threshold": 5,
    },
    rest_config={
        "heal_amount": 2,
        "ration_cost": 0,
        "morale_decay": False,
    },
)


_SUCCESSION = QuestArchetype(
    name="Succession Crisis",
    slug="succession",
    arc_length=5,
    description=(
        "The king is dead and the throne is a wound. The Heir has the blood. "
        "The Pretender has the army. Five days until coronation or civil war. "
        "Every noble, priest, and cutthroat in the capital is choosing sides."
    ),
    terms={
        "crown": "The Heir",
        "crew": "The Pretender",
        "neutral": "The Uncommitted",
        "campfire": "The Private Chamber",
        "world": "The Capital",
    },
    patrons=[
        "Prince-Regent Aldric",
        "The Grand Chamberlain",
        "Dowager Queen Ysabel",
    ],
    leaders=[
        "General Torvald, the Pretender's Sword",
        "Lady Sera, the Pretender's Voice",
        "The Bastard (name struck from the rolls)",
    ],
    prompts_crown=[
        "The Grand Chamberlain presents the Heir's genealogy scroll -- verified "
        "by the Archivists, stamped by the High Septon. One line has been "
        "added in fresher ink. The Chamberlain asks you not to look too closely.",

        "Prince-Regent Aldric offers you the Lord Marshalship -- command of the "
        "capital garrison. The previous Marshal was found in the river this "
        "morning. Aldric says it was suicide. The body had no hands.",

        "Dowager Queen Ysabel asks you to visit the Pretender under a flag of "
        "truce. 'Offer them a duchy,' she says. 'A comfortable exile. And if "
        "they refuse -- remember their guard rotation for me.'",

        "A courier brings the Heir's private correspondence -- love letters to "
        "the Pretender's spouse, written years ago. The Chamberlain wants them "
        "burned. 'Not because they're damaging,' he says. 'Because they're true.'",

        "The coronation requires the blessing of the High Septon. The Septon is "
        "old, frightened, and open to persuasion. Aldric says: 'Persuade him. "
        "I don't care how. A crown without blessing is just metal.'",
    ],
    prompts_crew=[
        "General Torvald shows you a map of the capital with the garrison positions "
        "marked in red. 'Three gates,' he says. 'I need two. Give me the name of "
        "the gate captain who drinks, and I'll give you a seat at the new table.'",

        "Lady Sera asks you to forge a document -- a royal writ, predating the "
        "king's death, naming the Pretender as successor. 'The truth is whatever "
        "the people believe,' she says. 'Help them believe correctly.'",

        "The Bastard takes you to a cellar beneath the old palace. Inside: a vault "
        "of evidence -- letters, ledgers, witnesses' statements -- proving the "
        "Heir's family murdered their way to the bloodline. 'The throne was stolen "
        "before it was inherited.'",

        "Torvald's soldiers are growing restless. They came for a coronation, not "
        "a siege. The General needs a show of strength -- a public defection from "
        "the Heir's camp. He needs you to be that defection.",

        "Lady Sera discovers a plot to assassinate the Pretender during the "
        "coronation ceremony. She can stop it, but only by revealing her network "
        "of informants inside the palace. She asks what you would sacrifice.",
    ],
    prompts_world=[
        "The capital smells of jasmine and sewage in equal measure. Banners hang "
        "from every window -- the Heir's gold, the Pretender's silver -- and in "
        "the poorest quarters, no banners at all. Just shuttered windows and silence.",

        "The coronation hall is a cathedral of vaulted stone and ancient glass. "
        "The throne sits on a dais of seven steps, each carved with the name of "
        "a dynasty. The newest step is unmarked, waiting.",

        "The city's walls are manned by soldiers wearing two different crests. "
        "They share wine and dice at the guardhouses. No one has given the order "
        "to choose sides. When it comes, the walls will bleed.",

        "Market day in the capital, but the stalls are half-empty. Merchants "
        "have fled or are hoarding. A baker sells bread at triple price. A "
        "beggar wears a tin crown and bows to everyone. No one laughs.",

        "The royal crypts are open -- by tradition, the dead king lies in state "
        "until the successor is crowned. Candles line the passage. The air is "
        "cold and still. Someone has placed two crowns on the sarcophagus. "
        "Neither is the real one.",
    ],
    prompts_campfire=[
        "The private chamber is yours for the night. A fire crackles in the "
        "grate. On the desk: a letter you started writing three days ago. You "
        "haven't finished it. Who is it to, and why can't you find the words?",

        "A servant brings wine and a question: 'Who do you think should rule?' "
        "It's the first honest question anyone has asked you since you arrived. "
        "The servant waits. The wine grows warm.",

        "You stand at the window overlooking the city. Somewhere, a bell rings "
        "-- not the coronation bell, just a temple calling vespers. How many "
        "people below are praying tonight? What do they pray for?",

        "The Bastard sits uninvited in your chamber. He doesn't want the throne. "
        "He says so plainly. 'I want the name,' he says. 'My father's name. "
        "The one they scratched from the rolls.' What would you give for a name?",

        "You find a child's drawing tucked behind a tapestry -- two stick figures "
        "holding hands, labeled in a child's script: the Heir's name and the "
        "Pretender's. They were friends, once. Perhaps more. The drawing is old.",
    ],
    morning_events=[
        {
            "text": "A crowd gathers at the palace gates at dawn, chanting the "
                    "Pretender's name. The Heir's guard watches from the ramparts "
                    "with crossbows loaded. A single stone is thrown.",
            "bias": "crew", "tag": "DEFIANCE",
        },
        {
            "text": "The Grand Chamberlain is found unconscious in his study. His "
                    "papers are scattered. The genealogy scroll is missing. Both "
                    "sides accuse the other.",
            "bias": "neutral", "tag": "GUILE",
        },
        {
            "text": "A noble house declares for the Heir publicly, then sends a "
                    "private courier to the Pretender. You intercept the courier. "
                    "The message reads: 'We back whoever wins. Name your price.'",
            "bias": "crown", "tag": "GUILE",
        },
        {
            "text": "The body of a palace servant is found in the fountain -- dressed "
                    "in the Heir's colors, hands bound. No one claims the body. "
                    "No one asks questions.",
            "bias": "crew", "tag": "BLOOD",
        },
        {
            "text": "Bells ring at dawn -- every temple in the city, simultaneously. "
                    "No one ordered it. The High Septon says it was the will of the "
                    "gods. The gods are keeping their own counsel.",
            "bias": "neutral", "tag": "SILENCE",
        },
    ],
    council_dilemmas=[
        {
            "prompt": "The coronation is in two days. Both claimants can be crowned -- "
                      "or neither. A dual coronation would split the kingdom legally. "
                      "Choosing one risks civil war.",
            "crown": "Crown the Heir. Bloodline is law. Law is order.",
            "crew": "Crown the Pretender. The people chose. Their voice is the law now.",
        },
        {
            "prompt": "A mercenary company offers its swords to whoever pays first. "
                      "Their price is the contents of the royal treasury. Hiring them "
                      "guarantees victory and bankruptcy.",
            "crown": "Hire them for the Heir. An empty treasury rebuilds. A lost throne doesn't.",
            "crew": "Hire them for the Pretender. Spend the gold before the Heir can.",
        },
        {
            "prompt": "The High Septon will bless only one claimant. His blessing "
                      "carries the weight of divine right. He asks for a private "
                      "audience with you before deciding.",
            "crown": "Advocate for the Heir. Tradition and blood are the pillars of the faith.",
            "crew": "Advocate for the Pretender. The gods care for the living, not the lineage.",
        },
        {
            "prompt": "An ancient law allows trial by combat to settle succession disputes. "
                      "The Heir's champion is undefeated. The Pretender has no champion -- "
                      "unless you volunteer.",
            "crown": "Invoke the law and let combat decide. The blade doesn't lie.",
            "crew": "Reject the law. Trial by combat is murder dressed in ceremony.",
        },
        {
            "prompt": "A compromise is proposed: the Heir rules, but the Pretender "
                      "commands the army. Shared power. Mutual distrust. A kingdom "
                      "with two heads and one neck.",
            "crown": "Accept. Imperfect unity is better than perfect division.",
            "crew": "Reject. Two rulers means two wars -- just delayed.",
        },
    ],
    secret_witness=(
        "Midnight in the coronation hall. A cloaked figure kneels before the "
        "empty throne and places a blood-stained glove on the lowest step. You "
        "recognize the glove -- it belonged to the dead king. The figure rises, "
        "pulls back their hood, and you see a face that is both the Heir's and "
        "the Pretender's. They speak your name. They've been waiting."
    ),
    special_mechanics={
        "faction_influence": {"heir": 0, "pretender": 0},
        "noble_houses_declared": 0,
        "coronation_countdown": 5,
    },
    rest_config={
        "heal_amount": 2,
        "ration_cost": 0,
        "morale_decay": False,
    },
)


_OUTBREAK = QuestArchetype(
    name="Outbreak Response",
    slug="outbreak",
    arc_length=5,
    description=(
        "The sickness came from the well, or the river, or the sky -- no one "
        "agrees. The Quarantine says containment. The Infected say freedom. "
        "Five days until the fever breaks or the gates do."
    ),
    terms={
        "crown": "The Quarantine",
        "crew": "The Infected",
        "neutral": "The Untouched",
        "campfire": "The Sick Ward",
        "world": "The Afflicted Town",
    },
    patrons=[
        "Surgeon-General Maren Kalt",
        "The Warden of the Cordon",
        "Apothecary-Royal Drest",
    ],
    leaders=[
        "Feverman Josse, voice of the sick ward",
        "Midwife Aelith, who won't leave the infected",
        "The Marked Boy (first to show symptoms, last to fall)",
    ],
    prompts_crown=[
        "Surgeon-General Kalt unfolds a map of the town with red circles "
        "expanding outward from the well. 'We burn everything inside the "
        "third circle,' she says. 'Homes, livestock, possessions. It's the "
        "only way to stop the spread.' Forty families live inside the third circle.",

        "The Warden of the Cordon proposes sealing the eastern gate permanently. "
        "No one in, no one out. The Infected on the eastern side would be "
        "cut off from the only apothecary. 'Sacrifice is mathematics,' he says.",

        "Apothecary Drest has developed a treatment -- untested, expensive, "
        "sufficient for thirty doses. The town has two hundred sick. He asks "
        "you to choose who receives treatment. The list must be ready by morning.",

        "A group of the Infected attempts to flee through the cordon. The guards "
        "hold the line. Kalt asks you to give the order: 'Turn them back, by "
        "any means necessary.' A child is among them.",

        "A merchant caravan approaches the town. They carry food, medicine, hope. "
        "The Warden says letting them in means exposing them to the sickness. "
        "Turning them away means the town starves. 'Your call,' he says.",
    ],
    prompts_crew=[
        "Feverman Josse pulls you into the sick ward. The cots are full. The "
        "floor is full. People are lying in the corridor. 'They locked the "
        "medicine behind the Quarantine line,' he says. 'We need it. Tonight. "
        "Can you get through?'",

        "Midwife Aelith shows you a newborn -- born to a sick mother, showing "
        "no symptoms. 'If the Quarantine finds out, they'll take the child to "
        "the clean zone and the mother will never see it again.' She wraps the "
        "baby tighter. 'Help me hide them.'",

        "The Marked Boy draws in the dirt outside the sick ward. A map of the "
        "town, with tunnels the Quarantine doesn't know about -- old drainage "
        "channels, cellars connected by generations of bootleggers. 'We can "
        "get people out,' he says. 'The sick ones. Before they become numbers.'",

        "A woman in the sick ward has stopped eating. She says the Quarantine "
        "took her husband three days ago for 'examination.' He hasn't returned. "
        "Josse says others have disappeared too. 'Ask where they take them,' "
        "he says. 'Ask what examination means.'",

        "Midwife Aelith has been treating the sick with herbs from the old "
        "tradition -- remedies the Surgeon-General calls superstition. Three "
        "of her patients are walking. None of Kalt's are. She asks you to "
        "protect her from the Quarantine inspectors.",
    ],
    prompts_world=[
        "The town smells of vinegar and smoke. Every door is marked -- white "
        "chalk for clean, red for sick, black for dead. A dog noses at a "
        "black-marked door. No one calls it away.",

        "Fog settles over the town at dawn, thick and yellow-grey. The cordon "
        "fires burn through it like distant stars. Somewhere, someone is "
        "coughing -- the sound carries in the mist, directionless, constant.",

        "The well is sealed now -- chains and a padlock, by Quarantine order. "
        "People gather around it anyway, staring at the stones as if the "
        "water might speak. A priest sprinkles salt. A child drops a coin "
        "through the chain links.",

        "The market square has become a triage station. Cots line the fountain. "
        "The fountain still runs -- clean water, the only source left. Guards "
        "ration it by the cup. The line stretches around the block.",

        "Night falls and the town goes quiet -- not peaceful quiet, but the "
        "silence of held breath. Candles burn in every window. Not for light. "
        "For vigil. When a candle goes out, the neighbors know.",
    ],
    prompts_campfire=[
        "The sick ward empties as patients sleep or pretend to. You sit by a "
        "candle and clean your hands for the twelfth time. They still smell "
        "of vinegar. Someone asks if you're afraid. Are you?",

        "Midwife Aelith sits beside a sleeping child, humming a lullaby that "
        "is older than the town. She asks where you grew up. What you were "
        "afraid of as a child. 'Not this,' she guesses.",

        "A recovered patient -- one of the first -- sits in the doorway of "
        "the sick ward, watching the stars. 'I died for three minutes,' he "
        "says. 'I saw my mother.' He's quiet. 'She was angry.'",

        "Feverman Josse shares a pipe of bitter tobacco. 'Before the sickness,' "
        "he says, 'I was a schoolteacher. History.' He exhales. 'Plagues always "
        "end. The question is what's left.' What do you think will be left?",

        "A candle goes out in the window across the street. No one screams. "
        "No one cries. Someone simply walks to the door and ties a black "
        "ribbon to the handle. You've seen twelve ribbons today. How many "
        "can you carry before the weight is real?",
    ],
    morning_events=[
        {
            "text": "Three new cases overnight -- all from the clean zone. The "
                    "cordon has failed somewhere. The Warden doubles the patrols. "
                    "The Infected say the sickness doesn't care about lines on a map.",
            "bias": "crew", "tag": "DEFIANCE",
        },
        {
            "text": "A Quarantine inspector collapses in the market square. Red "
                    "marks on his hands. He's one of them now. The guards don't "
                    "know whether to help him or arrest him.",
            "bias": "neutral", "tag": "BLOOD",
        },
        {
            "text": "Apothecary Drest announces a breakthrough -- a tincture that "
                    "slows the fever. He needs volunteers to test it. The Infected "
                    "line up. The Quarantine insists on selecting the subjects.",
            "bias": "crown", "tag": "GUILE",
        },
        {
            "text": "You wake to the sound of hammering. The Quarantine is boarding "
                    "up the sick ward windows. 'Ventilation control,' the Warden says. "
                    "Josse calls it something else.",
            "bias": "crew", "tag": "HEARTH",
        },
        {
            "text": "A rider arrives from the capital with sealed orders. The Warden "
                    "reads them and says nothing. He folds the paper and walks to "
                    "the cordon line. The guards straighten. Something has changed.",
            "bias": "crown", "tag": "SILENCE",
        },
    ],
    council_dilemmas=[
        {
            "prompt": "The sickness is spreading faster than the treatment can be "
                      "produced. The Quarantine proposes mandatory isolation for "
                      "all symptomatic cases. The Infected say isolation is a death "
                      "sentence without care.",
            "crown": "Isolate. Containment saves the many, even at cost to the few.",
            "crew": "Refuse isolation. People die faster alone than sick.",
        },
        {
            "prompt": "A ship in the harbor could evacuate fifty people to a clean "
                      "port -- but any one of them might carry the sickness. The "
                      "Quarantine wants to burn the ship. The Infected want to board it.",
            "crown": "Burn the ship. One outbreak is enough.",
            "crew": "Let them board. Fifty lives saved is fifty lives saved.",
        },
        {
            "prompt": "Midwife Aelith's herbal treatment works, but slowly. Drest's "
                      "tincture works faster, but three patients have died from the "
                      "side effects. The town must choose one protocol.",
            "crown": "Drest's tincture. Speed matters more than comfort in a plague.",
            "crew": "Aelith's herbs. Medicine that kills is not medicine.",
        },
        {
            "prompt": "The dead are piling up. The Quarantine wants to burn the bodies "
                      "immediately. The Infected want to bury them in the old cemetery "
                      "with proper rites. Burning is safer. Burial is human.",
            "crown": "Burn the dead. Grief is a luxury the living cannot afford.",
            "crew": "Bury them properly. We are not so far gone that we forget our dead.",
        },
        {
            "prompt": "A healthy family tries to break through the cordon with their "
                      "children. The guards have orders to stop all crossings. The "
                      "family is clean. The orders are clear.",
            "crown": "Hold the cordon. One exception and the line means nothing.",
            "crew": "Let them through. The cordon protects no one if it traps the healthy with the sick.",
        },
    ],
    secret_witness=(
        "At the stroke of midnight, every candle in the sick ward flickers and dies "
        "at once. In the darkness, a figure stands at the foot of the Marked Boy's "
        "cot. They are not sick and they are not well. They hold a vial of black "
        "liquid -- the source, or the cure, or both. They offer it to you with "
        "hands that do not tremble. 'Choose,' they say. 'But know that every "
        "plague is a question, and this is the answer no one asked for.'"
    ),
    special_mechanics={
        "infection_track": 0,
        "infection_max": 20,
        "cure_progress": 0,
        "cure_threshold": 10,
        "daily_spread": 3,
    },
    rest_config={
        "heal_amount": 0,
        "ration_cost": 1,
        "morale_decay": True,
    },
)


# =============================================================================
# QUEST REGISTRY
# =============================================================================

QUEST_REGISTRY: dict[str, QuestArchetype] = {
    _SIEGE.slug: _SIEGE,
    _SUMMIT.slug: _SUMMIT,
    _TRIAL.slug: _TRIAL,
    _CARAVAN.slug: _CARAVAN,
    _HEIST.slug: _HEIST,
    _SUCCESSION.slug: _SUCCESSION,
    _OUTBREAK.slug: _OUTBREAK,
}


# =============================================================================
# LOOKUP FUNCTIONS
# =============================================================================

def get_quest(slug: str) -> QuestArchetype | None:
    """Retrieve a quest archetype by its slug.

    Args:
        slug: Lowercase lookup key (e.g. "siege", "heist").

    Returns:
        The matching QuestArchetype, or None if not found.
    """
    return QUEST_REGISTRY.get(slug)


def list_quests() -> list[QuestArchetype]:
    """Return all registered quest archetypes, sorted by arc length ascending.

    Returns:
        A list of all QuestArchetype instances in the registry.
    """
    return sorted(QUEST_REGISTRY.values(), key=lambda q: q.arc_length)
