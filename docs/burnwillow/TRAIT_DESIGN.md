# Burnwillow Trait System — Complete Design Document

## GM NOTE: Magic Source Truth
> The settlers of Emberhome do not distinguish between natural Rot and the
> Blight. They call it all "the corruption." The Choir is simply "evil."
> The Void is unknown to most. This document uses the TRUE taxonomy.
> Player-facing descriptions should use the unreliable narrator.

---

## 1. Magic Sources

### Natural (Burnwillow = Autumn)
| Source | Theme | Stat Affinity |
|--------|-------|---------------|
| **Root/Wood** | The tree's body. Physical force, growth, reshaping. | Might |
| **Amber/Sap** | The tree's blood. Healing, preservation, shielding. | Grit |
| **Fire/Ember** | The autumn hearth. Warmth, light, controlled burn. | Might/Wits |
| **Rot (natural)** | Decomposition that feeds regrowth. The Mycelium. | Grit/Aether |
| **Root-Song** | The tree's vibration. Arborist Song-Craft. Aether is its medium. | Aether |

### Choir-Corrupted (wrong-season intrusions, Zone 3+/Undergrove/Choir enemies)
| Natural | Corrupted | Wrong Season | Theme |
|---------|-----------|-------------|-------|
| Rot | **Blight** | (silence) | Decay without regrowth. Silences Root-Song. |
| Fire | **Blaze** | Solheart (Summer) | Uncontrollable napalm. Burns everything, no rebirth. |
| Amber | **Ice** | Ashenmere (Winter) | Cold imprisonment. Freezes, doesn't preserve. |
| Root/Wood | **Overgrowth** | Verdhollow (Spring) | Strangling, smothering. Drowning in life. |

### Void (Anti-Aether, extremely rare — Void enemies only, quest rewards)
| Theme | Expression |
|-------|------------|
| Negation | Cancel abilities, strip defenses |
| Debuff | Reduce stats, drain Aether, diminish |
| Gravity | Pull, crush, pin, compress space |
| Absence | Erasure. Things stop existing. |

---

## 2. Active Traits by Source

### Root/Wood (Might)
| Trait | Type | Effect |
|-------|------|--------|
| **CLEAVE** | Active | Splash damage to adjacent enemies. Targets = min(3, tier). |
| **SHOCKWAVE** | Active | Might DC 11. Damage + Stun 1 round, 1-3 targets. |
| **WHIRLWIND** | Active | Might DC 15. 75% damage to ALL enemies in room. |
| **CHARGE** | Active | Might DC 5. Bonus 1d6 damage on next attack. |
| **SET_TRAP** | Active | Wits DC 5. Create a hazard in the room. |

### Amber/Sap (Grit)
| Trait | Type | Effect |
|-------|------|--------|
| **GUARD** | Active (buff) | +tier DR to self until next turn. |
| **REFLECT** | Active (buff) | Next attack reflects tier damage back. |
| **INTERCEPT** | Reaction | Trigger: ally takes damage. Absorb hit, +tier DR. |
| **AEGIS** | Active | Grit DC 11. +tier DR to ALL allies for 2 rounds. |
| **RESIST_BLIGHT** | Passive | +2 DR vs Blight hazards. |
| **HEAL** | Active | Restore 1d6 per tier HP from consumable. Cost: 1 Aether. |

### Fire/Ember (Might/Wits)
| Trait | Type | Effect |
|-------|------|--------|
| **INFERNO** | Active | Aether DC 15. Fire damage + Burning 2 rounds, 1-3 targets. |
| **TEMPEST** | Active | Aether DC 11. Lightning damage, 1-3 targets. |
| **FLASH** | Active | Wits DC 11. Blind 1-2 enemies for 2 rounds. |
| **LIGHT** | Active | Dispel darkness for 3 rooms. Cost: 1 Aether. |
| **HEARTHFLARE** | Reaction | Trigger: you take damage. Attacker takes 1d4 fire. |

### Rot — Natural (Grit/Aether)
| Trait | Type | Effect |
|-------|------|--------|
| **SNARE** | Active | Wits DC 11. Reduce defense of 1-3 enemies by tier. |
| **RENEWAL** | Active | Aether DC 11. HoT: 1d4 HP/round for 3 rounds, all allies. |
| **MENDING** | Active | Wits DC 11. Heal 1d6*tier HP to ALL party members. |
| **SPORE_ADAPTATION** | Reaction | Trigger: you fail a poison/Blight save. Reroll with +2. |

### Root-Song (Aether)
| Trait | Type | Effect |
|-------|------|--------|
| **SPELLSLOT** | Active | Aether check vs enemy defense. 1d6 per tier damage. Cost: 2 Aether. |
| **SUMMON** | Active | Call a spirit minion (Root-Song echo). Cost: 3 Aether. |
| **BOLSTER** | Active | Aether DC 11. Grant +tier bonus dice on next roll. |
| **RALLY** | Active | Wits DC 11. ALL allies +1d6 next attack. |
| **COMMAND** | Active | Wits DC 11. Grant ally a free attack + tier bonus damage. |
| **SANCTIFY** | Active | Aether DC 15. AoE sacred song damage. |
| **FAR_SIGHT** | Passive | Scout DC reduced by 2. |
| **REVEAL** | Active | Discover hidden exits and secrets. Cost: 1 Aether. |
| **HARMONIC** | Reaction | Trigger: ally fails a check. Grant +1d6 retroactive assist. |

### Physical (no magic source)
| Trait | Type | Effect |
|-------|------|--------|
| **BACKSTAB** | Active | Double damage from surprise or vs blinded. |
| **RANGED** | Active | Attack from distance using weapon's pool stat. |
| **LOCKPICK** | Active | Wits DC (11 - tier). Open locked doors. |
| **TRIAGE** | Active | Wits DC 11. Emergency heal 1d6*tier. Free on success. |

---

## 3. Corrupted Choir Traits (Zone 3+, Undergrove, Choir enemies)

### Corrupted Actives
| Natural Trait | Choir Version | Source | Effect | Cost |
|---------------|---------------|--------|--------|------|
| INFERNO (Fire) | **HELLFIRE** | Solheart Blaze | 2x damage, Burning 3 rounds. BUT: room catches fire — 1d4/round to everyone including party until room is left. | 2 Aether |
| SNARE (Rot) | **BLIGHTWEB** | Blight | Targets snared AND Blighted (1 HP/round decay). Snare can't be broken by the target. | 2 Aether + 1 HP |
| GUARD (Amber) | **ICEWALL** | Ashenmere Ice | +tier*2 DR. BUT: you can't move or act next round (frozen in place). | 1 Aether |
| CLEAVE (Wood) | **OVERGROWTH_LASH** | Verdhollow Spring | Hits ALL enemies for full damage (not 50%). BUT: vines also grapple one random ally (DC 11 Might to escape). | 2 Aether |
| SUMMON (Song) | **CHOIR_CALL** | Choir Song | Summon 2 minions instead of 1, higher stats. BUT: +1 Resonance exposure per use. | 3 Aether |

### Corrupted Reactions
| Natural Reaction | Choir Version | Trigger | Effect | Cost |
|------------------|---------------|---------|--------|------|
| HEARTHFLARE | **SOLFLARE** | You take damage | 2d6 fire to attacker AND all adjacent (including allies) | Free |
| ROOTCATCH | **BLIGHTGRASP** | Ally at 0 HP | Stabilize at 1 HP but target gains Blighted condition | Free |
| SPORE_ADAPTATION | **CHOIR_RESONANCE** | You fail a save | Auto-succeed but +1 Resonance exposure | Free |

---

## 4. Void Traits (Void enemies ONLY, quest rewards, rare events)

| Trait | Type | Stat | Effect | Cost |
|-------|------|------|--------|------|
| **NULLIFY** | Reaction | Aether DC 11 | Trigger: enemy uses special ability. On success: fizzles, enemy's action wasted. On fail: Aether spent, nothing happens. | 2 Aether |
| **VOIDGRIP** | Active | Aether DC 15 | Necrotic damage (1d6/tier) + Drained 2 rounds (target damage reduced by tier). | 2 Aether |
| **COLLAPSE** | Active | Aether DC 15 | Gravity well. ALL enemies pulled together, take 1d4 per enemy caught. Pinned 1 round (-2 defense, can't move). | 3 Aether |
| **WITHER** | Active | Aether DC 15 | Reduce target max HP by 1d6/tier for encounter. vs Bosses: also reduce damage die by 1 step. | 3 Aether + 1 HP |
| **UNMAKE** | Active | Aether DC 22 | Non-boss: erased from existence (no drops, no corpse, no kill triggers). Boss: 3d6/tier unresistable damage. Caster gains Void Exhaustion (long rest to clear: -1d6 all checks, half Aether pool). | ALL Aether + 2 HP |

### Void Acquisition
| Trait | Source |
|-------|--------|
| NULLIFY | Void Herald kill drop, or choose to keep a Void artifact quest |
| VOIDGRIP | Undergrove-only drops (move existing Voidstone Focus to Undergrove loot) |
| COLLAPSE | Choir Conductor kill drop |
| WITHER | Rare quest reward — NPC offers it with explicit warning |
| UNMAKE | Void Herald's weapon. Only source. |

---

## 5. Combos by Source Theme

### Natural Combos
| Setup + Payoff | Name | Source | Effect |
|----------------|------|--------|--------|
| SNARE + CLEAVE | **Root Crush** | Rot + Wood | +1d6 bonus to all cleave targets |
| SNARE + RANGED | **Pinned Prey** | Rot + Physical | DC reduced by snare value, re-roll on miss |
| FLASH + BACKSTAB | **Ember Shadow** | Fire + Stealth | Confirms double damage (already wired via blind) |
| FLASH + SPELLSLOT | **Sunburst** | Fire + Song | DC -3, re-roll on miss against blinded |
| GUARD + REFLECT | **Amber Mirror** | Amber + Amber | Reflect damage doubled |
| CHARGE + CLEAVE | **Timber Fall** | Wood + Wood | Charge bonus carries into splash targets |
| LIGHT + REVEAL | **Song Echo** | Fire + Song | Reveal extends to adjacent + 2-hop rooms |

### Corrupted Choir Combos (Zone 3+, Undergrove)
| Setup + Payoff | Name | Source | Effect | Cost |
|----------------|------|--------|--------|------|
| BLIGHTWEB + CLEAVE | **Blight Crush** | Choir Rot + Wood | +1d6 to cleave AND targets gain Blighted | 1 HP |
| FLASH + HELLFIRE | **Solar Flare** | Fire + Solheart | 2x AoE damage but hits allies too | - |
| ICEWALL + REFLECT | **Ice Mirror** | Ashenmere + Amber | 3x reflect damage but -1 DR to armor (permanent) | - |
| LIGHT + CHOIR_CALL | **Choir Pulse** | Fire + Choir | Reveals entire floor map but +1 Resonance | - |

### Void Combos (endgame, extremely rare)
| Setup + Payoff | Name | Effect |
|----------------|------|--------|
| NULLIFY + WITHER | **Unraveling** | Wither's max HP reduction doubled (defenses already stripped) |
| COLLAPSE + any AoE | **Event Horizon** | AoE damage +50% to pinned/collapsed targets |

---

## 6. Reactions Summary

| Source | Reaction | Trigger | Effect |
|--------|----------|---------|--------|
| **Amber** | INTERCEPT | Ally takes damage | Absorb hit, +tier DR |
| **Fire** | HEARTHFLARE | You take damage | Attacker takes 1d4 fire |
| **Root/Wood** | ROOTCATCH | Ally at 0 HP | Stabilize at 1 HP, once per encounter |
| **Rot** | SPORE_ADAPTATION | You fail poison/Blight save | Reroll with +2 |
| **Root-Song** | HARMONIC | Ally fails a check | Grant +1d6 retroactive |
| **Void** | NULLIFY | Enemy uses special ability | Counterspell, ability fizzles |
| **Choir (Fire)** | SOLFLARE | You take damage | 2d6 fire to attacker + all adjacent (including allies) |
| **Choir (Wood)** | BLIGHTGRASP | Ally at 0 HP | Stabilize at 1 but Blighted |
| **Choir (Rot)** | CHOIR_RESONANCE | You fail a save | Auto-succeed but +1 Resonance |

---

## 7. Affixes by Source

### Natural Affixes (Zone 1+)
| Affix | Source | Effect |
|-------|--------|--------|
| Blazing | Fire/Ember | On hit: 1d4 fire |
| Keen | Physical/Craft | Crit on 5-6 |
| Rooted | Root/Wood | +1 DR when stationary |
| of Thorns | Root/Wood | Reflect 1 damage on hit taken |
| of Mending | Rot (natural) | Regen 1 HP per room |
| of the Willow | Amber | Blight resistance |
| of the Canopy | Root-Song/Aether | +1 Aether pool |
| of Haste | Fire/Ember | +1 movement |

### Corrupted Affixes (Zone 3+, Undergrove, Choir enemies)
| Affix | Source | Effect | Cost/Risk |
|-------|--------|--------|-----------|
| Volatile | Solheart Blaze | +2 damage | Self-damage 1 on fumble |
| Vampiric | Blight | Heal 1 on kill | Drains life unnaturally |
| Frozen | Ashenmere Ice | 10% slow | Cold that doesn't belong here |

### Void Affixes (Void enemies only)
| Affix | Source | Effect | Cost/Risk |
|-------|--------|--------|-----------|
| Voidscarred | Void | On hit: drain 1 Aether from target | Weapon feels wrong to hold |
| of Negation | Void | Immune to one enemy buff per encounter | -1 max Aether while equipped |

---

## 8. Drop Zone Restrictions

| Tier | Zones | Available Sources |
|------|-------|-------------------|
| **Natural** | Zone 1+ (everywhere) | Root/Wood, Amber, Fire, Rot, Root-Song, Physical |
| **Corrupted (Choir)** | Zone 3+, Undergrove, Choir-aligned enemies | Blight, Blaze, Ice, Overgrowth, Choir Song |
| **Void** | Void enemies only, specific quest rewards | Negation, Gravity, Absence |

---

## 9. Archetype Detection (for #170)

When a character equips enough gear from one source, they gain a passive identity:

| Archetype | Required | Source | Passive Bonus |
|-----------|----------|--------|---------------|
| **Rootwarden** | 3+ Root/Wood traits | Root/Wood | +1 DR, Rootcatch range extends to 2 allies |
| **Amberwright** | 3+ Amber traits | Amber | Guard/Reflect last 1 extra round |
| **Embercaller** | 3+ Fire traits | Fire | Hearthflare upgrades to 1d6 |
| **Sporecaster** | 3+ Rot traits | Rot | Snare affects +1 target |
| **Songweaver** | 3+ Root-Song traits | Root-Song | Harmonic grants +2d6 instead of +1d6 |
| **Blightwalker** | 3+ Choir traits | Corrupted | Immune to Blighted, but -1 max HP permanently |
| **Voidtouched** | 2+ Void traits | Void | Nullify costs 1 Aether instead of 2, but permanent -1 Aether pool |
