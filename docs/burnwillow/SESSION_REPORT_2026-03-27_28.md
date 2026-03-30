# Burnwillow Session Report — 2026-03-27 / 2026-03-29
## For Gemini Review & Continuation

This document summarizes everything discussed, designed, implemented, and documented during this three-day session (March 27-29, 2026). Burnwillow reached feature-complete status for all playability milestones. It is intended as a handoff to Gemini for architectural review, creative feedback, and continuation of open threads.

---

## SESSION OVERVIEW

The session began with backlog organization and pivoted entirely to Burnwillow. We brainstormed deep world-building, designed new mechanics, implemented engine changes, and produced two major documents. The focus was on building Burnwillow into a standalone pen-and-paper TTRPG with rich lore that could stand on its own without digital implementation.

**Key outputs:**
- Setting bible expanded from 480 lines to 1,449 lines
- Sourcebook created and expanded to 3,504 lines (organized as a published TTRPG rulebook)
- Engine mechanics updated (DC rebalance, gear scoring, dice normalization, passive checks, assistance)
- Six new factions, four playable peoples, an antagonist faction, threat ecology, criminal elements, and a complete Arborist civilization history

---

## 1. BACKLOG REORGANIZATION

Reorganized 104 open items from priority-based (P1-P12) to **playability milestone** structure:

| Milestone | Items | Theme |
|-----------|-------|-------|
| M1 | 10 | Stable Baseline (commit, data integrity) |
| M2 | 5 | Burnwillow Plays Right (DC balance, traits, overflow) |
| M3 | 3 | Build Identity (sets, affixes, example builds) |
| M4 | 3 | Living World Design (bible, reputation, NPCs) |
| M5 | 6 | Factions Implementation |
| M6 | 9 | Crafting & Alchemy |
| M7 | 1 | Content Integration |
| M7b | 4 | New Mechanics (vault breach, resonance, Heartwood/Undergrove zones) |
| M7c | 2 | Core Rules (TPK reset, Aether items) |
| M8 | 25 | Other Game Systems |
| M9 | 19 | Multi-System & Platform |
| M10 | 11 | Documentation |

**Burnwillow "finished product" = M1 through M7c (43 items).** Full CODEX platform = all milestones (110 items).

---

## 2. DICE & DC MECHANICS OVERHAUL

### Problem
The original DC tiers (ROUTINE=8, HARD=12, HEROIC=16, LEGENDARY=20) didn't align with the 3.5-per-die mathematical step. Analysis with Gemini showed that HARD (12) was a coin flip at 3d6+2, making mid-game difficulty feel flat.

### Solution Implemented

**New DC Tiers (each step = 3.5, one die's average):**

| DC | Name | Description |
|----|------|-------------|
| 5 | Routine | Easy for any equipped character |
| 11 | Standard | 50/50 for Basic (Tier I-II) gear |
| 15 | Hard | Requires Advanced (Tier III) gear |
| 22 | Elite | Only specialized high-tier characters |
| 30+ | Legendary | 5d6 cap + heavy modifier stacking |

**Gear provides TWO forms of scaling:**
1. **Dice:** Every equipped item contributes exactly **+1d6** to its stat pool, regardless of tier. To get more dice, equip more items. (Changed from old system where Tier IV gave +4d6.)
2. **Stat Score Bonus:** Every item adds its **tier value to the stat score** (not the modifier). Tier I = +1, Tier IV = +4. The D&D formula `(score - 10) // 2` then runs on the combined score, so every +2 to score = +1 modifier.

**Why dice = +1 per item:** A single Tier IV item was maxing the 5d6 pool by itself, making every subsequent item in that stat pool worthless for dice. Now you need 4 items feeding a stat to reach 5d6 (base + 4 items). Quality (tier) and quantity (number of items) are separate progression axes.

**New mechanics added:**
- **Passive Threshold:** If Total Modifier + 1 >= DC, auto-succeed without rolling. Wired into attack and search commands.
- **Gated Checks:** DC 25+ gates content behind gear. Metroidvania gating via dice.
- **Assistance:** Ally grants +1d6 to another's roll (subject to 5d6 cap). New `assist` command in bridge.

**Scaling Reference (with +0 base modifier, score 10):**

| Gear Level | Pool | Score Bonus | New Score | New Mod | Avg Roll |
|-----------|------|------------|-----------|---------|---------|
| Naked | 1d6 | +0 | 10 | +0 | 3.5 |
| Basic | 2d6 | +1 | 11 | +0 | 7.0 |
| Advanced | 3d6 | +2 | 12 | +1 | 11.5 |
| Master | 4d6 | +3 | 13 | +1 | 15.0 |
| Legendary | 5d6 | +10 | 20 | +5 | 22.5 |

**All engine code updated:** DC enum, `get_stat_score_bonus()`, `get_stat_mod()` (adds gear to score before formula), `get_dice_bonus()` (returns 1 for any tier > 0), `passive_check()`, `roll_check(assist=)`. All 14 trait resolver DCs remapped. All hazard DCs remapped. All documentation updated.

---

## 3. COSMOLOGY EXPANSION — SIX GROVES

The cosmos expanded from four Groves to six, adding a vertical axis:

```
        [The Heartwood — Within]
              |
    Burnwillow  Verdhollow  Solheart  Ashenmere
     (Autumn)    (Spring)   (Summer)  (Winter)
              |
        [The Undergrove — Below]
```

### The Heartwood — The First Tree

Accessed by going **inward** through the wood itself — deeper into growth rings until you reach the original seed from which all four Groves branched. Not a direction (up/down), but a depth.

- **Architecture:** Tree anatomy — sap channels as hallways, knots as chambers, resin pockets as vaults
- **Enemies:** Arborist constructs still running ancient commands, amber-locked hostile memories, the tree's immune responses
- **Hidden entrances:** Overgrown passages in abandoned dungeon sections, behind certain Amber Vaults (the golem bows instead of attacking), nooks in branches. Discoverable through faction rep (Allied+), DC 25+ Wits, Arborist relics, NPC rumors.
- **The Vault Connection:** Some Amber Vaults don't contain loot — they contain inward passages. The vault system's real purpose was to seal the Heartwood. The treasure was bait.

### The Undergrove — Where the Roots Remember

The shared root network beneath all four Groves. Where decomposition happens. Where the Rot is native and natural.

- Contains geological memory of **failed Groves** that existed before the current four
- Where Hollows eventually migrate after death
- Where the Choir directs the Rot from
- Entrances in deepest Zone 4 vaults — grey amber, cracked seals, damaged golems. Opening one is a choice: access + opening a door that held Rot back.

---

## 4. THE ARBORISTS — COMPLETE CIVILIZATION HISTORY

### Who They Were: Resonance Engineers

Not builders, not smiths, not mages. **Biological musicians** who shaped the world through acoustic Aether vibration.

- They sang "Notes of Growth" and "Frequencies of Hardening"
- Cities were "Conducted" — planted as seeds and sung into existence over decades
- Memory Seeds are acoustic recordings pressed into amber (first-person experiences, not text)
- Communication Crystals are Resonance Nodes vibrating the sap network (Twitch's crystal still hums)
- Ironbark was created by sitting with a sapling for a year, singing a specific hum

### The Schism: Silencers vs Choir

When Ashenmere began going still, the Arborists panicked:

**The Silencers:** Patience. Don't force the cycle. The tree knows what it's doing.

**The Choir:** Sing a better song. Skip Winter (Autumn → Spring, bypass death/decomposition). Not malice — grief. They couldn't accept the cycle involves dying.

### The Collapse (~500 years ago)

The Choir sang. They disrupted Autumn→Winter. The Undergrove's decomposition cycle had nowhere to send output. Pressure built. The boundary shattered. The Rot leaked upward.

**Ashenmere** was the Choir's first test — they tried to "pause" Winter there. Instead they stopped it permanently. The motionless Hollows there are still listening to the frozen test-song.

### The Great Silencing

The Silencers realized the catastrophe was acoustic. They:
1. Stopped singing entirely
2. Sealed the Heartwood using Amber Vaults as acoustic dampeners
3. Sealed the Root-Roads
4. Withdrew into the Heartwood and entered amber stasis

Three-generation knowledge loss:
- Gen 1 (~500 yrs ago): Knew songs, forbidden to sing
- Gen 2 (~480 yrs ago): Heard whispered fragments
- Gen 3 (~400 yrs ago): Found tools, forgot music. Emberhome founded.

### The Choir — The Antagonist

The Choir went into the Undergrove to sing the Rot into submission. **The Rot learned their music.**

They became the first intentional Hollows — conducting husks. Their song is the Root-Song played in diminished intervals, making living wood rot. They believe the Groves are already dead — just not decomposed yet.

**Structure:**
- **The Conductor** — final boss, deepest Undergrove
- **Section Leaders** — scattered through deep zones, each directs Rot in one area. Kill one = Rot in that zone becomes mindless.
- **The Chorus** — recruited Hollows. Organized, formations, singing. Build fungal structures mimicking Arborist architecture.

### The Choir's Sound (Progression by Zone)

- **Zone 2:** Occasional dissonant undertone. Root-Song stutters.
- **Zone 3:** Two songs competing. Choir bleeds through in sustained passages.
- **Zone 4:** Root-Song absent. Choir only. Constant, low, intimate — diminished intervals that never resolve.
- **Undergrove:** Overpowering, beautiful, insane. Gear hums sympathetically.

### The Endgame — Three Paths

1. **Silence the Choir:** Kill the Conductor. Rot becomes mindless — present but undirected. The Silencers' solution, forever.
2. **Complete the Song:** Fix the Choir's song — add missing notes. Let the Undergrove finish its cycle. The tree partially dies, partially regrows. Ashenmere thaws. Burnwillow changes. The world is permanently different.
3. **Wake the Sleepers:** Revive amber-sealed Arborists. They know the original song. Maybe they can compose something new. Hardest path, requires faction support and a Resonant character.

---

## 5. THE SILENT CULTURE — HEARTWOOD DESCENDANTS

A few hundred Arborist descendants living in the Heartwood for 400 years in total silence.

### The Painted Songs
Murals that encode acoustic information visually. Color = frequency, brushstroke = phase, layering = overtones, thickness = amplitude. Every child learns to read them before walking — they hear the complete Arborist song tradition in their heads, never aloud.

### The Gardens
Hand-gardening replaces wood-singing. Every surface touched over decades. Flowers form Painted Song patterns from above — gardens that are also musical scores.

### Communication Hierarchy
1. **Touch-signs** — daily life. 400 years of evolution, as nuanced as spoken language.
2. **The Whisper** — sacred. Acoustically unique: turbulent airflow without vocal cord vibration = no resonance signature = the tree can't hear it. The Choir can't detect it. A whisper is never wasted on trivia.
3. **Memory Seed notes** — permanence and distance.
4. **Painted Songs** — knowledge that must outlast the tree.

### The Whisper-Key Connection
The Whisper-Key works acoustically, not mechanically. It converts a whisper into vault-opening resonance without adding harmonics. The Arborists designed it intentionally — the safest sound opens the sealed doors.

### First Contact
Player arrives talking in full voice. Descendants react with animal terror. Grab the newcomer, silence them, drag to deep chamber. The eldest leans close. A whisper: *"You are so loud."*

### Descendant Factions
- **The Roots** (majority): Leave us alone. Silence works.
- **The Seedlings** (young): Burn to hear the songs for real. Want surface contact.
- **The Grafters** (pragmatists): Heartwood losing ground. Trade knowledge for military support.

---

## 6. ROOT-ATTUNEMENT — UNIVERSAL CAPACITY (Not a Gene)

**Critical design decision:** Root-Attunement is NOT a genetic trait, bloodline, or inborn gift. It is a universal capacity — like building muscle. Everyone has it. It awakens through exposure to Aether, working with living wood, years near the tree's resonant structures. No eugenics implications. No chosen people.

**Spectrum of Awakening:**
- **Dormant (Aether <12):** Never activated. May develop.
- **Stirring (Aether 12-13):** Awakened by years near Aether. Wood "cooperates." Weld, Scout Lira.
- **Resonant (Aether 14-16):** Fully awake. Hear Root-Song unprompted.
- **True Arborist (Aether 17+):** Lifelong practice + saturation → physical transformation. Result of devotion, not birth.
- **Heartwood Descendants:** 400 years passive immersion. Proof that environment drives attunement.

Attunement can deepen during play. The Aether score is not fixed.

---

## 7. THE FOUR PEOPLES — SHAPED BY SEASON

No traditional fantasy races. The First Tree had one people. The four Groves shaped them over millennia through concentrated Aether at four vibrational frequencies.

| People | Grove | Shaped By | Aether Expression | Stat Bonus |
|--------|-------|-----------|------------------|-----------|
| Autumn-Born | Burnwillow | Decay frequency | Transition — sense change coming | +2 Grit |
| Spring-Born | Verdhollow | Growth frequency | Acceleration — plants respond to touch | +2 Aether |
| Summer-Born | Solheart | Intensity frequency | Force — unconscious Aether channeling | +2 Might |
| Winter-Born | Ashenmere | Stillness frequency | Perception — hear silence, sense absence | +2 Wits |

Emberhome is primarily Autumn-Born. Spring-Born are a significant minority (refugees). Summer-Born rare. Winter-Born almost nonexistent.

---

## 8. SIX FACTIONS — GROUNDED IN REAL WILLOW ECOLOGY

Every faction maps to a real ecological relationship willows have with other organisms.

| Faction | Ecology | Key NPCs | Exalted Reward |
|---------|---------|----------|---------------|
| **The Hive** | Bee/wasp pollination | Queen Mother (dying), Vex ("we"), Stinger (exile) | Royal Jelly (hive-sense) |
| **The Mycelium** | Mycorrhizal fungal network | The Spreading (collective), Maeth (translator), Old Cap (cranky, 400 yrs old) | Mycelium Map (hidden rooms) |
| **The Dam-Wrights** | Beaver hydraulics | Foreman Gnaw (dam fracture secret), Kitspool (dreamer), The Old Dam (blind elder) | Lodgecraft (fortifications) |
| **The Canopy Court** | Moth specialists | Moth Prince (riddles), Silkmother Vray (charges memories), Thorn (exile) | Mothwing Cloak (invisibility) |
| **The Hag Circle** | Bracket fungi decomposers | Brindlemaw (blind, poisons), Kettleblack (jovial cook), Needlewise (teeth collector) | Blight Tolerance |
| **The Heartwood Elders** | Sentient ancient branches | Ashknot (Rot-burned, thinks at human speed) | Root-Sense (Doom warning) |

**Reputation:** Hostile → Wary → Neutral → Friendly → Allied → Exalted
**Opposing pairs:** Hag Circle vs Heartwood Elders, Canopy Court vs Dam-Wrights, Hive vs Mycelium

---

## 9. CONDITIONS & DEBUFFS (12 Status Effects)

| Condition | Effect |
|-----------|--------|
| Sap-Drained | Trait DCs +1, Aether checks disadvantage |
| Spore-Sick | Hallucinations (GM describes 1 false threat per room) |
| Resonance-Touched | Gear hums, enemy spawn +1, Choir prioritizes you |
| Blighted | 1 HP lost per room, can't heal until cured |
| Shaken | -1d6 all rolls 3 rounds, can't Command/Rally |
| Entangled | Can't move, DC 15 Might to break |
| Burning | 1d4 fire/round 2 rounds |
| Frozen | No actions 1 round, then -1d6 Grit 2 rounds |
| Weakened | Might disadvantage, melee damage halved |
| Blinded | Attacks hit random target, -2 Wits 2 rounds |
| Poisoned | -1 all rolls, 1d4 damage/round 3 rounds |
| Gall-Marked | Healing halved, rest attracts Gall Larvae |

---

## 10. THREAT ECOLOGY

Natural threats that existed before the Collapse. The Arborists managed them. Nobody does now.

### The Leech Cascade (Ecosystem Death Spiral)
Sap Leeches drain healthy wood → area weakens → Rot probes → tree immune response → Gall parasites hijack healing → leaked sap attracts more Leeches → spiral accelerates → Choir lets it run for free territory.

The Hive farms Leeches for honeydew. Their "managed" colonies contribute to the cascade. Quest tension: Hive wants protection, Dam-Wrights want destruction, Hag Circle offers synthesis.

4-stage Cascade Room table for Zone 2+ (1-in-6 rooms).

### Other Threats
- **The Gall:** Tumor-like growths hijacking immune response. Gall-Marked condition.
- **Bark Borers:** Structural tunnelers. Collapse hazards, Rot highways.
- **Crown Predators:** Apex wildlife, inadvertent Rot guardians.
- **Hollow Tide:** Choir recruitment via entrainment broadcast.

---

## 11. CRIMINAL ELEMENTS — THE ROT WITHIN EMBERHOME

### The Scrappers
Black market: salvage poaching, amber laundering, gear theft, info brokering. Led by Grimjaw. Not villains — symptoms of scarcity. Threaten Emberhome with cynicism.

### The Hollowborn
Cult believing the Rot will win. Sabotage expeditions, spread small amounts of Blight, recruit the hopeless. Led by The Quiet (anonymous Memory Seed messages). **Don't know the Choir exists** — discovering the Rot is directed would shatter their theology.

### The Ash Runners
5-8 rogue Seekers in Zone 1. Led by Sable. Code: take your best item, let you live. **Sable has found a Heartwood entrance** and doesn't know what it is.

---

## 12. VAULT BREACH ALERT

Opening an Amber Vault breaks its acoustic dampener. For the next **3 rooms**: 100% enemy spawn, +1 enemy count. Vault room spawns immediate wave. Multiple vaults stack. Doom Clock unaffected — local Rot response to noise only.

---

## 13. TOTAL PARTY KILL = FULL RESET

If all characters die in the same run: campaign over. No new characters. No Memory Seeds. No Emberhome upgrades. No meta_state. Full roguelike reset. Death screen: "THE BURNWILLOW FALLS." Silence.

---

## 14. GEAR SETS & AFFIXES (Designed, Not Implemented)

**5 Gear Sets** with 2/3/4-piece bonuses:
Arborist's Legacy, Warden's Watch, Rot Hunter's Trophy, Moonstone Circle, Shadowweave.

**Randomized Affixes** (0-2 per item at drop):
- Prefixes: Blazing, Frozen, Vampiric, Keen, Volatile, Rooted
- Suffixes: ...of the Canopy, ...of Haste, ...of Thorns, ...of Mending, ...of the Willow
- Emergent combos (Blazing + Thorns = fire reflect)

**Example Builds** replaced the removed Archetype system. All abilities come from gear — no skill trees, no class triggers. Builds are descriptions of what emerges from gear choices, not rules.

---

## 15. ALCHEMY & CRAFTING (Designed, Not Implemented)

**Foundation:** Salicylic acid (real willow chemistry).
**12 ingredients** from zones/enemies/factions.
**4 crafting stations** (faction-gated): Blacksmith, Silkweaver (Canopy Court), Hag's Cauldron, Mycelium Forge.
**4 consumable types:** Potions (6), Bombs (6), Oils (5), Elixirs (4).

---

## 16. SOLO PLAY SECTION

Sourcebook Chapter 31 rewritten from "AI Companions" to "Solo Play" — a pen-and-paper guide for playing alone. Companion personalities (Vanguard/Scholar/Scavenger/Healer) reframed as GM-controlled allies with simple heuristic tables. Solo Doom Clock adjustment, difficulty scaling, campaign structure.

---

## 17. CAMPAIGN CHAPTER

Sourcebook Chapter 33 added: session zero, prologue system, session structure (Emberhome → Delve → Climax → Aftermath), campaign arc pacing mapped to zones and sessions, dungeon generation at the table, faction reputation tracking, NPC roleplaying guidance, Doom Clock as physical object, difficulty scaling, between-sessions persistence.

---

## 18. INFRASTRUCTURE FIXES

- Deleted phantom `DND5E_ENCOUNTERS` system (stale stub in config/systems/)
- Fixed RECOVERY default templates in 5 rules JSONs (BURNWILLOW, CROWN, DND5E, STC, GRAVEYARD)
- Cleaned garbage data from all rules JSONs (fake races, classes, subclasses)
- Identified 10 D&D 5e PDFs missing from FAISS index (need `--force` rebuild)

---

## 19. DOCUMENTS PRODUCED

| Document | Lines | Purpose |
|----------|-------|---------|
| `docs/burnwillow_setting_bible.md` | 1,449 | Canonical lore and design reference |
| `docs/burnwillow_sourcebook.md` | 3,504 | Complete TTRPG rulebook (33 chapters + appendices) |
| `docs/burnwillow/NOTEBOOK_LM_UPDATE_2026-03-28.md` | ~420 | NotebookLM import document |
| `docs/burnwillow/brainstorming/archetype_system_draft.md` | ~100 | Archived removed archetype system |
| `docs/burnwillow/SESSION_REPORT_2026-03-27_28.md` | This file |

---

## 20. ENGINE CHANGES MADE

| Change | File | Status |
|--------|------|--------|
| DC enum (5 tiers) | engine.py | Implemented, tested |
| Gear adds to stat SCORE (not modifier) | engine.py `get_stat_mod()`, `get_stat_score_bonus()` | Implemented, tested |
| Every item = +1d6 regardless of tier | engine.py `get_dice_bonus()` | Implemented, tested |
| `passive_check()` function | engine.py | Implemented, wired to bridge |
| `assist` parameter on roll functions | engine.py | Implemented, wired to bridge |
| `get_effective_score()` helper | engine.py | Implemented |
| All trait DCs remapped to new scale | engine.py (14 resolvers) | Implemented |
| All hazard DCs remapped | content.py | Implemented |
| Rules JSON cleaned | config/systems/ + deterministic_core/ | Done |
| Passive check wired to attack + search | bridge.py | Done |
| Assist command added | bridge.py | Done |

---

## 21. WHAT STILL NEEDS IMPLEMENTATION

### Quick Wins (Small)
- Heritage field on Character (+2 stat bonus from Four Peoples)
- Conditions system (enum, tracking, duration, cures)
- Vault Breach Alert (echo counter, spawn boost)
- TPK detection (campaign_over flag, meta_state wipe)

### Content (Data Files Only)
- 18 faction NPCs → config/npcs/burnwillow.json
- 3 criminal NPCs → config/npcs/burnwillow.json
- Cascade/Gall/Borer enemy stat blocks → config/bestiary/burnwillow.json
- Choir enemies (Conductor, Section Leaders, Chorus) → config/bestiary/burnwillow.json
- Heartwood enemies → config/bestiary/burnwillow.json
- Aether-variant items across all slots → content.py LOOT_TABLES
- Faction locations → config/locations/burnwillow.json

### Medium Features
- Faction reputation engine (tracking, gating, opposing pairs, persistence)
- Gear set bonuses (set_id, detection, bonus application)
- Randomized affixes (prefix/suffix fields, roll logic, name generation)

### Large Features
- Alchemy system (ingredients, recipes, stations, UI)
- Heartwood procedural zone (ring-based rooms, unique enemies)
- Undergrove procedural zone (root-mass rooms, Choir encounters)

---

## 22. OPEN QUESTIONS FOR GEMINI

These remain unresolved and would benefit from Gemini's architectural perspective:

1. **Heirloom mechanics** — how are items designated as heirlooms before death? What's the handoff ritual?
2. **Inter-faction politics in other Groves** — do equivalents of the Six Factions exist in Verdhollow, Solheart, Ashenmere?
3. **Faction zone territory** — which factions control which dungeon territory? How does reputation affect encounters?
4. **Alchemy ingredient ecology** — do ingredients respawn? Seasonal? Cultivatable in Emberhome?
5. **The Conductor** — personality, reachability, reasoning. Is there a person inside the Hollow?
6. **Ashenmere** — can it be thawed? What happens to frozen Hollows if the test-song is disrupted?
7. **Failed Groves in the Undergrove** — how many? What killed them? Warning or resource?
8. **Endgame paths** — specific mechanical requirements for each of the three choices
9. **Sable's Heartwood entrance** — what zone? What's behind it?
10. **The Quiet's identity** — is it an existing NPC?
11. **Root-Attunement growth during play** — should Aether score increase with exposure? How to balance?
12. **The Conductor's motivation** — do they know they're wrong? Can the player convince them to stop? What would it take?

---

## 23. DESIGN PRINCIPLES ESTABLISHED

1. **"You Are What You Wear"** — all abilities come from gear. No skill trees, no class triggers, no archetype unlocks.
2. **Dice = quantity, Tier = quality.** More items = more dice. Higher tier = better modifiers and traits. Separate axes.
3. **Root-Attunement is universal.** Not a gene, not a bloodline. A capacity everyone has, awakened by environment and practice.
4. **Factions grounded in real ecology.** Every faction maps to a real willow-tree symbiotic relationship.
5. **The Rot is natural.** Decomposition belongs in the Undergrove. The crisis is a boundary failure, not an invasion.
6. **The Choir is tragic, not evil.** They tried to save the tree by skipping death. They failed. They think they're helping.
7. **Sound is dangerous.** The Root-Song guides the Rot. Silence is survival. The Whisper is sacred.
8. **Total party kill = total reset.** The roguelike loop requires someone to survive and carry knowledge forward.
9. **No digital dependencies.** The sourcebook is a complete pen-and-paper TTRPG. 5d6, character sheets, pencils, this book.
10. **The tree IS the world.** Not a planet with a tree. The canopy is the sky. The roots are the underworld. There is nothing else.
