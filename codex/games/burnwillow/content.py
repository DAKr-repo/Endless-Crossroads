#!/usr/bin/env python3
"""
burnwillow_content.py - Burnwillow Content Database
====================================================

Comprehensive enemy, loot, hazard, and description tables for the Burnwillow
dungeon crawler. Organized by tier (1-4) and aligned with the Burnwillow SRD.

This module is the "content vault" that the BurnwillowAdapter draws from.

Design Principles:
  - Tier-based scaling (Tier 1 = entry, Tier 4 = deep dungeon)
  - Lore-driven naming (rust, decay, blight, corruption)
  - Mechanical variety (different enemy behaviors, hazard types)
  - SRD alignment (dice pools, DC values, gear tiers match rulebook)

Version: 1.0
"""

import random
from typing import Dict, List, Tuple

# =============================================================================
# ENEMY TABLES — BY TIER
# =============================================================================

# Enemy structure: (name, hp_base, hp_variance, defense, damage_dice, special)
# hp_variance is added randomly (e.g., hp_base=5, variance=3 -> 5-8 HP)
# damage_dice is a string like "1d6" or "2d6"

ENEMY_TABLES: Dict[int, List[Tuple[str, int, int, int, str, str]]] = {
    1: [
        # Tier 1: Scrap creatures, pests, minor threats
        ("Rot-Beetle", 4, 0, 8, "2", "Skitter: Ranged attacks against this enemy suffer -1d6 penalty due to erratic movement."),
        ("Fungal Mite", 3, 1, 10, "1d6", "Explodes on death, spore cloud (DC 10 Grit or cough for 1 turn)."),
        ("Scrap Imp", 5, 2, 11, "1d6", "Throws debris. Range 20ft."),
        ("Oil Slick", 6, 2, 10, "1d6", "Ignites if exposed to fire (2d6 fire damage to adjacent enemies)."),
        ("Blighted Mouse", 2, 1, 9, "1d6", "Tiny. Hard to hit (-1 to attack rolls)."),
    ],
    2: [
        # Tier 2: Corrupted workers, clockwork, Ironbark constructs
        ("Clockwork Spider", 8, 3, 12, "2d6", "Mechanical. Immune to poison. Weak to lightning."),
        ("Hollowed Scavenger", 10, 0, 12, "1d6+2", "Muscle Memory: On death, roll 1d6. On a 6, rises with 1 HP and attacks immediately."),
        ("Ironbark Hound", 12, 4, 12, "2d6", "Fast. Dashes 40ft. Pack tactics (+1d6 if ally adjacent)."),
        ("Shambling Moss", 9, 2, 10, "1d6", "Regenerates 1 HP/turn unless burned."),
        ("Rust Serpent", 7, 3, 13, "2d6", "Coils around target (DC 12 Might to escape, restrained)."),
        ("Blight-Hawk", 8, 2, 13, "2d6", "Flies. Rot-spore talons: On hit, DC 12 Grit or poisoned (1d6 next turn)."),
    ],
    3: [
        # Tier 3: Elite sentinels, wraiths, Heartwood constructs
        ("Blighted Sentinel", 15, 5, 14, "3d6", "Armored. DR 2. Patrols fixed routes."),
        ("Forge Wraith", 12, 4, 13, "3d6", "Ethereal. Can phase through walls. Weak to Aether attacks."),
        ("Heartwood Serpent", 14, 5, 14, "3d6", "Constricts (ongoing 1d6 damage per turn)."),
        ("Ashwood Treant", 18, 6, 12, "2d6", "Huge. Innate [Whirlwind] — sweeping branch slam hits all enemies. AOE."),
        ("Corrupted Artificer", 13, 4, 13, "3d6", "Casts Tier II scrolls. Carries loot."),
        ("Spore-Crawler", 12, 3, 13, "2d6", "Innate [Inferno] — spore burst deals fire-like damage + Burning. AOE. Rooms visited become hazardous."),
    ],
    4: [
        # Tier 4: Dungeon lords, Ambercore constructs, Blight avatars
        ("Ambercore Golem", 25, 8, 16, "4d6", "Legendary. DR 3. Reflects magic (50% chance spell rebounds)."),
        ("Void Sentinel", 22, 7, 15, "4d6", "Drains Aether on hit (lose 1 Aether per hit, cannot cast at 0)."),
        ("Burnwillow Shade", 20, 6, 14, "5d6", "Boss-tier. Summons 1d3 Tier 2 enemies per turn."),
        ("Blight Warden", 28, 10, 16, "4d6", "Elite. Heals allies for 2d6 HP (action). Must be killed first."),
        ("Ironroot Tyrant", 30, 10, 17, "5d6", "Colossal. Innate [Shockwave] — ground slam stuns and damages nearby. AOE."),
    ]
}


# =============================================================================
# LOOT TABLES — BY TIER
# =============================================================================

# Loot structure: (name, slot, tier, special_traits, description)
# Aligned with Burnwillow SRD gear slots and tier system

LOOT_TABLES: Dict[int, List[Tuple[str, str, int, List[str], str]]] = {
    1: [
        # Tier I: Scrap/Wood (+1d6)
        ("Rusted Shortsword", "R.Hand", 1, [], "A corroded blade. Better than your fists."),
        ("Splintered Club", "R.Hand", 1, [], "A wooden cudgel. Cracks on heavy impact."),
        ("Padded Jerkin", "Chest", 1, [], "Quilted cloth armor. DR 1."),
        ("Leather Cap", "Head", 1, [], "Worn headgear. Provides minor protection."),
        ("Old Oak Wand", "R.Hand", 1, [], "A gnarled wand. Channels Aether poorly. +1d6 magic attack."),
        ("Burglar's Gloves", "Arms", 1, ["[Lockpick]"], "Leather gloves with lockpicks sewn in. +1d6 Wits for lockpicking."),
        ("Pot Lid Shield", "L.Hand", 1, ["[Intercept]"], "Makeshift shield. DR 1. Can intercept hits for allies."),
        ("Tattered Cloak", "Shoulders", 1, [], "Ragged fabric. Provides warmth, little else."),
        ("Rope Sandals", "Legs", 1, [], "Bound footwear. Worn soles."),
        ("Bandage Pouch", "Legs", 1, ["[Heal]"], "Heals 1d6 HP (3 charges)."),
        ("Spore-Woven Vest", "Chest", 1, [], "Mushroom fibre vest. Hums with faint Aether. +1d6 Aether pool."),
        ("Spore Mask", "Head", 1, [], "Resin-sealed bark mask. Immunity to Rot spore effects for 1 hour."),
        ("Amber Lantern", "L.Hand", 1, ["[Light]"], "Sap-fueled lantern. Dispels darkness for 3 rooms. Costs 1 Aether."),
        ("Amber Shard", "Neck", 1, [], "Hardened Aether. Holds a faint memory. Trade currency and crafting material."),
        # WO-V17.0: Support/Control items
        ("Warhorn", "L.Hand", 1, ["[Command]"], "Battered brass horn. Shout orders to rally allies. +1d6 Might pool."),
        ("Healer's Satchel", "Arms", 1, ["[Triage]"], "Bandages and salves. Wits-based healing. 3 charges."),
        # Aether-variant items (fixed slot overrides)
        ("Sap-Woven Gloves", "Arms", 1, [], "Woven from living Aether-threads. Channels residual sap energy through the fingertips. +1d6 Aether pool."),
        # Aether items for missing slots
        ("Resonance Wand", "R.Hand", 1, ["[Spellslot]"], "A tuning fork of living amber. Channels the Root-Song as force. +1d6 Aether attack."),
        ("Sap-Cord Mantle", "Shoulders", 1, [], "Shoulder drape woven from sap-soaked cord. The Root-Song vibrates through it faintly. +1d6 Aether pool."),
    ],
    2: [
        # Tier II: Ironbark/Cured Hide (+2d6)
        ("Ironbark Longsword", "R.Hand", 2, [], "A solid blade carved from dense Ironbark. Well-balanced. +2d6 Might attack."),
        ("Ironbark Crossbow", "R.Hand", 2, [], "Mechanical ranged weapon of laminated wood. +2d6 Wits attack, 60ft range."),
        ("Cured Hide Cuirass", "Chest", 2, [], "Leather armor treated with tree sap. DR 2."),
        ("Ironbark Helm", "Head", 2, [], "Heavy wooden helmet with Ironbark plates. DR 1. Protects against headshots."),
        ("Ash Wand", "R.Hand", 2, [], "Charred wood wand. +2d6 Aether attack."),
        ("Thief's Toolkit", "Arms", 2, ["[Lockpick]"], "Professional lockpicks carved from bone. +2d6 Wits for locks and traps."),
        ("Ironbark Shield", "L.Hand", 2, ["[Intercept]"], "Heavy shield of dense hardwood. DR 2. Can intercept and block."),
        ("Cured Hide Coif", "Head", 2, [], "Leather hood reinforced with bark strips. DR 1."),
        ("Traveler's Boots", "Legs", 2, [], "Sturdy leather boots. +5ft movement speed."),
        ("Healing Salve", "Neck", 2, ["[Heal]"], "Restores 2d6 HP (2 charges)."),
        ("Sapweave Robe", "Chest", 2, [], "Ironbark-fibre robe infused with sap. Channels Aether. +2d6 Aether pool."),
        ("Cloak of Shadows", "Shoulders", 2, [], "Dark-dyed hide that bends light. +2d6 Wits pool."),
        ("Spiked Pauldrons", "Shoulders", 2, [], "Ironbark shoulder guards with jagged spikes. +2d6 Grit pool."),
        ("Aether Vial", "Neck", 2, ["[Heal]"], "Liquid golden sap. Restores 1 Aether point. Burns if spilled on the Rot."),
        ("Root-Song Charm", "Neck", 2, [], "A knot of living wood that hums faintly. +2d6 to perception checks within the tree."),
        ("Seer's Lens", "Head", 2, ["[Reveal]"], "Amber-crystal monocle. Reveals hidden exits and secret passages. Costs 1 Aether."),
        ("Kindler's Lantern", "L.Hand", 2, [], "Fueled by a Sun-Shard fragment. 30ft bright light. Rot creatures take 1d6 within 10ft."),
        # WO-V17.0: Support/Control items
        ("Battle Standard", "L.Hand", 2, ["[Command]"], "A tattered banner that still inspires. Grant an ally a free action. +2d6 Might pool."),
        ("Shaman's Totem", "Neck", 2, ["[Bolster]"], "Carved ancestor totem. Channel Aether to empower an ally's next action."),
        ("Field Medic Kit", "Arms", 2, ["[Triage]"], "Professional healer's tools. Wits-based healing. 5 charges."),
        # WO-V32.0: AoE Cleave weapons
        ("Ironbark War Scythe", "R.Hand", 2, ["[Cleave]"], "Wide-bladed scythe of dense Ironbark. Sweeping strikes hit multiple foes. +2d6 Might attack."),
        # WO-V36.0: Expanded AoE gear
        ("Quake Hammer", "R.Hand", 2, ["[Shockwave]"], "Ironbark maul that sends tremors through the floor. Stuns nearby foes. +2d6 Might attack."),
        ("Gale Glaive", "R.Hand", 2, ["[Whirlwind]"], "Curved polearm that cuts in a full arc. Hits all enemies in reach. +2d6 Might attack."),
        ("Flashbang Pouch", "Arms", 2, ["[Flash]"], "Clay pellets filled with phosphor dust. Blind nearby enemies. +2d6 Wits pool."),
        ("Bolas of Binding", "Arms", 2, ["[Snare]"], "Weighted cords that tangle limbs. Reduces enemy defense. +2d6 Wits pool."),
        ("War Horn", "L.Hand", 2, ["[Rally]"], "Bronze horn inscribed with rally glyphs. Inspires allies to strike true. +2d6 Wits pool."),
        ("Embertongue Wand", "R.Hand", 2, ["[Inferno]"], "Wand tipped with an ember shard. Spews gouts of flame. +2d6 Aether attack."),
        ("Stormcaller Rod", "R.Hand", 2, ["[Tempest]"], "Rod of magnetized Ironbark. Calls down lightning arcs. +2d6 Aether attack."),
        ("Herbalist's Satchel", "Arms", 2, ["[Mending]"], "Poultices and binding herbs for group healing. +2d6 Wits pool."),
        # Aether-variant items (fixed slot overrides)
        ("Aether-Traced Greaves", "Legs", 2, [], "Ironbark leg guards with Aether channels etched into the grain. Warmth pulses through them with each step. +2d6 Aether pool."),
        ("Sap-Singer's Helm", "Head", 2, [], "A bark helm lined with sap-soaked moss. Amplifies the wearer's sensitivity to Root-Song vibrations. +2d6 Aether pool."),
        ("Resonance Staff", "R.Hand", 2, ["[Spellslot]"], "Ironbark staff carved with song-runes. The Root-Song flows through it like water through a channel. +2d6 Aether attack."),
        ("Sap-Light Buckler", "L.Hand", 2, ["[Reflect]"], "A small amber-inlaid shield that pulses with Aether. Redirects hostile resonance. +2d6 Aether pool."),
        ("Mycelium Epaulette", "Shoulders", 2, [], "Living fungal growth on shoulder pads. Bioluminescent threads pulse with the network's rhythm. +2d6 Aether pool."),
        ("Spore Ring", "L.Ring", 2, [], "A band of hardened mycelium. Rot-touched but alive — the healthy kind. Amplifies natural Aether. +2d6 Aether pool."),
    ],
    3: [
        # Tier III: Petrified Heartwood/Moonstone (+3d6)
        ("Heartwood Greatsword", "R.Hand", 3, [], "A massive two-hander carved from ancient petrified wood. +3d6 Might attack. Requires both hands."),
        ("Heartwood Longbow", "R.Hand", 3, [], "Elegant ranged weapon of fossilized wood. +3d6 Wits attack, 100ft range."),
        ("Heartwood Armor", "Chest", 3, [], "Segmented plates of petrified wood. DR 3. Heavy (move -5ft)."),
        ("Moonstone Helm", "Head", 3, [], "Enclosed helmet with moonstone eye-slits. DR 2. Protects fully."),
        ("Moonstone Staff", "R.Hand", 3, [], "Enchanted focus wrapped in pale wood. +3d6 Aether attack. Glows in darkness."),
        ("Moonstone Pendant", "Neck", 3, [], "Polished moonstone amulet. +1 Aether modifier for all spells."),
        ("Heartwood Tower Shield", "L.Hand", 3, ["[Intercept]", "[Guard]"], "Massive shield carved from a single trunk. DR 3. Can guard adjacent allies."),
        ("Heartwood Gauntlets", "Arms", 3, [], "Armored gloves of segmented wood. DR 1. Unarmed strikes do +1d6."),
        ("Heartwood Greaves", "Legs", 3, [], "Leg armor of petrified wood. DR 1. Immune to caltrops and floor hazards."),
        ("Elixir of Vitality", "Neck", 3, ["[Heal]"], "Restores 3d6 HP and cures poison (1 charge)."),
        ("Aetherial Vestments", "Chest", 3, [], "Moonstone-threaded robes. Trades armour for raw Aether power. +3d6 Aether pool."),
        ("Signet of Flame", "R.Ring", 3, [], "A moonstone ring that burns cold. Channels offensive Aether. +3d6 Aether pool."),
        ("Iron Band", "L.Ring", 3, [], "A heavy iron ring. Anchors the body against harm. +3d6 Might pool."),
        ("Sun-Fruit", "Neck", 3, ["[Heal]"], "Golden fruit from the Crown. Restores 3d6 HP and cures poison. Extremely rare."),
        ("Ironbark Armor", "Chest", 3, [], "Arborist relic. Sung wood harder than steel. DR 3."),
        # WO-V17.0: Support/Control items
        ("Arborist Relic", "L.Hand", 3, ["[Sanctify]"], "Ancient holy relic of the tree-shapers. Slam into the ground to create a safe zone."),
        ("Commander's Horn", "L.Hand", 3, ["[Command]"], "Horn of the old wardens. Orders carry Aether weight. +3d6 Wits pool."),
        ("Heartwood Talisman", "Neck", 3, ["[Bolster]"], "Empowers allies with the tree's ancient strength. +3d6 Aether pool."),
        # WO-V32.0: AoE Cleave weapons
        ("Heartwood Halberd", "R.Hand", 3, ["[Cleave]"], "Long-hafted polearm of petrified Heartwood. Sweeping arc hits multiple targets. +3d6 Might attack."),
        # WO-V36.0: Expanded AoE gear
        ("Earthsplitter Maul", "R.Hand", 3, ["[Shockwave]"], "Petrified warhammer that cracks stone. Shockwave stuns clusters of enemies. +3d6 Might attack."),
        ("Cyclone Blade", "R.Hand", 3, ["[Whirlwind]"], "Heartwood blade balanced for full rotational strikes. Hits every enemy in the room. +3d6 Might attack."),
        ("Sunburst Lantern", "L.Hand", 3, ["[Flash]"], "Moonstone lantern that erupts with blinding radiance. +3d6 Wits pool."),
        ("Rootweave Net", "Arms", 3, ["[Snare]"], "Living root net that constricts on contact. Reduces enemy defense. +3d6 Wits pool."),
        ("Commander's Pennant", "L.Hand", 3, ["[Rally]"], "Battle standard of the old wardens. Rallies all allies to strike harder. +3d6 Wits pool."),
        ("Inferno Staff", "R.Hand", 3, ["[Inferno]"], "Staff crowned with a caged flame elemental. Rains fire on groups. +3d6 Aether attack."),
        ("Voidstone Focus", "R.Hand", 3, ["[Voidgrip]"], "Crystallized void shard. Drains life from enemies. +3d6 Aether attack."),
        ("Renewal Chalice", "Neck", 3, ["[Renewal]"], "Moonstone cup that radiates healing energy over time. +3d6 Aether pool."),
        # Aether-variant items (fixed slot overrides)
        ("Resonance Greaves", "Legs", 3, [], "Heartwood leg guards that hum when the Root-Song passes through them. The wearer's stride falls into rhythm with the tree. +3d6 Aether pool."),
        ("Whisper Crown", "Head", 3, [], "A circlet of petrified Heartwood that amplifies whispered intentions into Aether pulses. The air around it shimmers faintly. +3d6 Aether pool."),
        ("Song-Forged Staff", "R.Hand", 3, ["[Spellslot]", "[Bolster]"], "A staff grown from Heartwood, never carved. The Root-Song sings through it constantly. +3d6 Aether attack."),
        ("Amber Aegis", "L.Hand", 3, ["[Intercept]", "[Reflect]"], "A shield of solid amber. Memories swim inside it. It remembers how to protect. +3d6 Aether pool."),
        ("Choir-Silk Mantle", "Shoulders", 3, [], "Woven from Canopy Court moth-silk. The fabric hums with stored resonance. +3d6 Aether pool."),
        ("Root-Woven Band", "L.Ring", 3, [], "A ring of living rootwood. It grows tighter when Aether flows through it. +3d6 Aether pool."),
    ],
    4: [
        # Tier IV: Ambercore/Sunresin (+4d6)
        ("Ambercore Blade", "R.Hand", 4, [], "Legendary sword of translucent golden amber. +4d6 Might attack. Crits on 5-6."),
        ("Dragonbone Bow", "R.Hand", 4, [], "Ancient artifact of fossilized bone. +4d6 Wits attack, 150ft range, ignores DR 1."),
        ("Sunresin Plate Armor", "Chest", 4, [], "Full plate of hardened Sunresin. DR 5. Heavy (move -10ft)."),
        ("Crown of Insight", "Head", 4, [], "Ambercore circlet with trapped fireflies. +2 Wits modifier. See invisible."),
        ("Sunresin Wand of Dominion", "R.Hand", 4, [], "Royal wand of golden resin. +4d6 Aether attack. Can Command (charm) DC 16."),
        ("Master Lockpicks", "Arms", 4, ["[Lockpick]"], "Enchanted tools carved from Moonstone. +4d6 Wits. Auto-open DC 12 locks."),
        ("Aegis Shield", "L.Hand", 4, ["[Intercept]", "[Guard]", "[Reflect]"], "Mythic shield of Ambercore. DR 4. Reflects ranged attacks."),
        ("Soulstone Amulet", "Neck", 4, [], "Moonstone with trapped soul. Revive once with 1 HP on death (consumes amulet)."),
        ("Boots of Haste", "Legs", 4, [], "Enchanted footwear of Sunresin. +15ft movement speed. Dash as bonus action."),
        ("Phoenix Tears", "Neck", 4, ["[Heal]"], "Restores full HP and cures all conditions (1 charge)."),
        ("Voidweave Mantle", "Chest", 4, [], "Robes woven from void-stuff. No physical protection, immense Aether. +4d6 Aether pool."),
        ("Ring of the Burnwillow", "R.Ring", 4, [], "Ambercore ring pulsing with the heart of the Willow. +4d6 Aether pool."),
        ("Memory Seed", "Neck", 4, [], "Crystallized blueprint from the Amber Vaults. Unlocks a legendary crafting recipe at Emberhome for this campaign."),
        # WO-V17.0: Memory Seed Legendary Items (Tier 4)
        ("Arborist's Aegis", "L.Hand", 4, ["[Intercept]"], "Legendary shield of the tree-shapers. +5 DR, reflects 1d6 melee damage back to attacker."),
        ("Warden's Warhorn", "L.Hand", 4, ["[Command]"], "Legendary horn of the old wardens. Grants ally free attack + free movement, +3 bonus damage."),
        ("Crown Talisman", "Neck", 4, ["[Bolster]"], "Legendary talisman of the Crown. +3d6 to ally's next roll, AoE: all adjacent allies get +1d6."),
        ("Lifebloom Satchel", "Arms", 4, ["[Triage]"], "Legendary healer's kit. 4d6 heal, 8 charges, AoE heals all adjacent allies for 1d6."),
        ("Sun-Relic", "L.Hand", 4, ["[Sanctify]"], "Legendary relic of the sun. 3d6 fire damage to all enemies, creates 2-turn safe zone."),
        # WO-V32.0: AoE Cleave weapons
        ("Sun-Cleaver", "R.Hand", 4, ["[Cleave]"], "Legendary greatsword of golden Sunresin. Cleaving arc hits up to 3 targets. +4d6 Might attack. Crits on 5-6."),
        # WO-V36.0: Expanded AoE gear
        ("Worldbreaker", "R.Hand", 4, ["[Shockwave]"], "Legendary maul of Ambercore. Each strike fractures reality, stunning all nearby. +4d6 Might attack."),
        ("Tempest Annihilator", "R.Hand", 4, ["[Tempest]"], "Sunresin rod crackling with perpetual storm. Chain lightning devastates groups. +4d6 Aether attack."),
        ("Void Scepter", "R.Hand", 4, ["[Voidgrip]"], "Scepter of condensed void. Drains life force from multiple enemies. +4d6 Aether attack."),
        ("Arcanist's Aegis", "L.Hand", 4, ["[Aegis]"], "Legendary shield of woven Aether. Projects a protective ward on all allies. DR 4."),
        ("Lifebinder's Mantle", "Shoulders", 4, ["[Mending]"], "Legendary vestment that pulses healing light. Mends the entire party at once. +4d6 Wits pool."),
        ("Eternity Bloom", "Neck", 4, ["[Renewal]"], "Living flower of Sunresin. Radiates perpetual healing aura. +4d6 Aether pool."),
        ("Flashfire Crown", "Head", 4, ["[Flash]"], "Crown of trapped lightning. Blinds all enemies in a searing flash. +4d6 Wits pool."),
        ("Warden's Bastion", "L.Hand", 4, ["[Aegis]"], "Tower shield of the last warden. Extends DR to the entire party. DR 5."),
        # Aether-variant items (fixed slot overrides)
        ("Root-Song Greaves", "Legs", 4, [], "Ambercore leg armor that resonates with the fundamental vibration of the tree. Each step sends ripples through the Aether. +4d6 Aether pool."),
        ("Crown of Resonance", "Head", 4, [], "An Arborist circlet of pure Ambercore. The Root-Song is deafening when worn. Aether flows like a river through the wearer's skull. +4d6 Aether pool."),
        ("Conductor's Baton", "R.Hand", 4, ["[Spellslot]", "[Summon]"], "An Arborist conductor's wand of pure Ambercore. The tree sings through it. Armies answer. +4d6 Aether attack."),
        ("Amber Mirror Shield", "L.Hand", 4, ["[Reflect]", "[Nullify]"], "A shield of flawless amber. It does not block — it makes attacks not arrive. +4d6 Aether pool."),
        ("Arborist's Mantle", "Shoulders", 4, [], "Woven from Heartwood fibres by the last Silencers. The Root-Song wraps around your shoulders like a warm breath. +4d6 Aether pool."),
        ("Ring of the Root-Song", "L.Ring", 4, [], "Carved from the First Ring's wood. The vibration is constant, deep, and older than language. +4d6 Aether pool."),
    ]
}


# =============================================================================
# DICE POOL ASSIGNMENTS FOR WILDCARD-SLOT ITEMS (WO V20.3)
# =============================================================================
# Items in wildcard slots (Shoulders, Neck, R.Ring, L.Ring) must declare
# which stat pool they feed. Items in fixed slots (hands, head, arms, chest, legs)
# may also override via this map. Items NOT listed use SLOT_STAT_MAP defaults.

LOOT_PRIMARY_STATS: Dict[str, str] = {
    # Tier 1 — Shoulders
    "Tattered Cloak":         "GRIT",     # Warmth = survivability
    "Spore-Woven Vest":       "AETHER",   # Aether armor trade
    # Tier 2 — Shoulders & Neck
    "Healing Salve":          "GRIT",     # Healing focus
    "Sapweave Robe":          "AETHER",   # Aether armor trade
    "Cloak of Shadows":       "WITS",     # Stealth
    "Spiked Pauldrons":       "GRIT",     # Physical defence
    # Tier 3 — Neck, Rings, Aether armor
    "Moonstone Pendant":      "AETHER",   # Aether focus
    "Elixir of Vitality":     "GRIT",     # Healing focus
    "Aetherial Vestments":    "AETHER",   # Aether armor trade (chest override)
    "Signet of Flame":        "AETHER",   # Offensive Aether ring
    "Iron Band":              "MIGHT",    # Physical ring
    # Tier 4 — Neck, Rings, Aether armor
    "Soulstone Amulet":       "AETHER",   # Soul magic
    "Phoenix Tears":          "GRIT",     # Healing focus
    "Voidweave Mantle":       "AETHER",   # Aether armor trade (chest override)
    "Ring of the Burnwillow": "AETHER",   # Ultimate Aether ring
    # Rot Hunter loot (wildcard slots)
    "Hunter's Heartstone":    "AETHER",   # Neck
    "Blighthide Mantle":      "GRIT",     # Shoulders
    # WO-V16.2: Shamanic Awakening items (wildcard slots)
    "Amber Shard":            "AETHER",   # Neck — crystallized Aether
    "Aether Vial":            "AETHER",   # Neck — healing
    "Root-Song Charm":        "WITS",     # Neck — perception
    "Sun-Fruit":              "GRIT",     # Neck — healing
    "Memory Seed":            "AETHER",   # Neck — crafting relic
    # WO-V17.0: Support/Control items (wildcard slots)
    "Shaman's Totem":         "AETHER",   # Neck — Bolster
    "Heartwood Talisman":     "AETHER",   # Neck — Bolster
    "Crown Talisman":         "AETHER",   # Neck — Bolster legendary
    # WO-V36.0: Expanded AoE items (wildcard slots)
    "Renewal Chalice":        "AETHER",   # Neck — Renewal HoT
    "Eternity Bloom":         "AETHER",   # Neck — Renewal legendary
    "Lifebinder's Mantle":    "WITS",     # Shoulders — Mending legendary
    # Aether items in fixed slots (override SLOT_STAT_MAP)
    "Sap-Woven Gloves":       "AETHER",   # Arms — Tier I
    "Aether-Traced Greaves":  "AETHER",   # Legs — Tier II
    "Sap-Singer's Helm":      "AETHER",   # Head — Tier II
    "Resonance Greaves":      "AETHER",   # Legs — Tier III
    "Whisper Crown":          "AETHER",   # Head — Tier III
    "Root-Song Greaves":      "AETHER",   # Legs — Tier IV
    "Crown of Resonance":     "AETHER",   # Head — Tier IV
    # New Aether items for missing slots (#204)
    "Resonance Wand":         "AETHER",   # R.Hand — Tier I
    "Sap-Cord Mantle":        "AETHER",   # Shoulders — Tier I
    "Resonance Staff":        "AETHER",   # R.Hand — Tier II
    "Sap-Light Buckler":      "AETHER",   # L.Hand — Tier II
    "Mycelium Epaulette":     "AETHER",   # Shoulders — Tier II
    "Spore Ring":             "AETHER",   # L.Ring — Tier II
    "Song-Forged Staff":      "AETHER",   # R.Hand — Tier III
    "Amber Aegis":            "AETHER",   # L.Hand — Tier III
    "Choir-Silk Mantle":      "AETHER",   # Shoulders — Tier III
    "Root-Woven Band":        "AETHER",   # L.Ring — Tier III
    "Conductor's Baton":      "AETHER",   # R.Hand — Tier IV
    "Amber Mirror Shield":    "AETHER",   # L.Hand — Tier IV
    "Arborist's Mantle":      "AETHER",   # Shoulders — Tier IV
    "Ring of the Root-Song":  "AETHER",   # L.Ring — Tier IV
}


# =============================================================================
# GEAR SET IDS — Maps item names to set membership
# =============================================================================

LOOT_SET_IDS: Dict[str, str] = {
    # Arborist's Legacy
    "Moonstone Staff": "arborist_legacy",
    "Aetherial Vestments": "arborist_legacy",
    "Root-Song Charm": "arborist_legacy",
    "Arborist Relic": "arborist_legacy",
    # Warden's Watch
    "Commander's Horn": "wardens_watch",
    "Heartwood Tower Shield": "wardens_watch",
    "Heartwood Greaves": "wardens_watch",
    "Moonstone Helm": "wardens_watch",
    # Rot Hunter's Trophy (Ambercore prefix from rot_hunter_loot)
    "Ambercore Rotclaw Fang": "rot_hunter_trophy",
    "Ambercore Hunter's Heartstone": "rot_hunter_trophy",
    "Ambercore Blighthide Mantle": "rot_hunter_trophy",
    "Ambercore Rot-Tendril Gauntlets": "rot_hunter_trophy",
    # Moonstone Circle
    "Moonstone Pendant": "moonstone_circle",
    "Renewal Chalice": "moonstone_circle",
    "Herbalist's Satchel": "moonstone_circle",
    "Heartwood Talisman": "moonstone_circle",
    # Shadowweave
    "Cloak of Shadows": "shadowweave",
    "Burglar's Gloves": "shadowweave",
    "Boots of Haste": "shadowweave",
    "Spore Mask": "shadowweave",
}


# =============================================================================
# HAZARD TABLES — BY TIER
# =============================================================================

# Hazard structure: (name, stat, dc, effect, description)
# stat: which stat to roll against (Might, Wits, Grit, Aether)
# effect: what happens on failure

HAZARD_TABLES: Dict[int, List[Tuple[str, str, int, str, str]]] = {
    1: [
        ("Rusty Spike Trap", "Wits", 11, "Take 1d6 piercing damage and contract tetanus (DC 11 Grit or -1 Might for 1 day).", "Hidden floor spikes, crusted with rust."),
        ("Poison Gas Vent", "Grit", 11, "Take 1d6 poison damage and cough uncontrollably (disadvantage on Wits checks for 1 hour).", "Green gas hisses from wall cracks."),
        ("Collapsing Floor", "Wits", 11, "Fall 10ft into pit (1d6 damage). Climb DC 11 Might to escape.", "The floorboards creak ominously."),
        ("Oil Slick", "Wits", 11, "Slip and fall prone. Lose turn. If ignited, take 2d6 fire damage.", "Black oil coats the floor."),
        ("Spore Cloud", "Grit", 11, "Inhale spores. Hallucinate for 1 hour (GM describes false threats).", "Mushrooms burst, releasing pale dust."),
    ],
    2: [
        ("Blade Pendulum", "Wits", 15, "Take 2d6 slashing damage. If reduced to 0 HP, decapitated (instant death).", "A massive blade swings across the corridor."),
        ("Electrified Floor", "Grit", 15, "Take 2d6 lightning damage. Drop held metal items (DC 15 Might to hold on).", "Sparks arc across metal plating."),
        ("Acid Pool", "Wits", 15, "Step in acid, take 2d6 acid damage. Boots destroyed (lose Legs slot item).", "Bubbling green liquid fills a depression."),
        ("Arcane Ward", "Aether", 15, "Drain 1 Aether. Cannot cast spells until rested.", "Glowing runes repel magic."),
        ("Pit Trap with Spikes", "Wits", 15, "Fall 20ft (2d6 damage), then impaled (additional 1d6, bleeding 1 HP/turn).", "Concealed trapdoor. Deadly spikes below."),
    ],
    3: [
        ("Crushing Walls", "Might", 15, "Take 3d6 damage and restrained. DC 15 Might check each turn to escape or take 1d6 ongoing.", "Stone walls grind together."),
        ("Fireball Rune", "Wits", 15, "Triggered explosion. 3d6 fire damage to all in 15ft radius. Dex save for half.", "Ancient glyph glows red-hot."),
        ("Petrifying Gaze Statue", "Aether", 15, "Meet the statue's eyes. DC 15 or turn to stone for 1 hour (paralyzed).", "A stone sentinel's eyes glow green."),
        ("Cursed Altar", "Grit", 15, "Touch altar. Cursed: max HP reduced by half until curse lifted (requires Tier III scroll).", "A dark shrine radiates malice."),
        ("Void Rift", "Aether", 22, "Reality tears. Pulled toward rift (DC 22 Might or sucked in). Reappear in random room, lose 1 gear item.", "Space warps and bends unnaturally."),
    ],
    4: [
        ("Disintegration Beam", "Wits", 22, "Laser turret fires. 4d6 force damage. On crit fail, one equipped item destroyed.", "A crystal emitter tracks movement."),
        ("Gravity Reversal", "Might", 22, "Slam into ceiling (4d6 damage). Fall back down (4d6 damage). Total 8d6 unless DC 22 Might to grab ledge.", "Gravity inverts violently."),
        ("Soul Drain Sigil", "Aether", 22, "Sigil activates. Lose 2 Aether and all spell slots. Cannot cast until long rest.", "A circle of runes pulses with void energy."),
        ("Time Loop", "Aether", 22, "Trapped in 10-second loop. Repeat last turn until DC 22 Aether check succeeds.", "Time stutters. You've been here before."),
        ("Blight Corruption", "Grit", 22, "Exposed to raw Blight. Max HP reduced by 1d6 permanently. Roll Grit DC 22 each day or lose 1 more.", "The Burnwillow's roots pierce the air."),
    ]
}


# =============================================================================
# ROOM DESCRIPTIONS — BY TIER
# =============================================================================

# Atmospheric descriptions for procedurally generated rooms
# Organized by tier for thematic consistency

ROOM_DESCRIPTIONS: Dict[int, List[str]] = {
    1: [
        "Iron filings crunch underfoot. The walls weep orange rust — you taste oxide on your tongue. A pipe drips somewhere behind the rubble.",
        "Mildew reek hits you first, thick and wet. Moss fur coats the brickwork. The floor is slick with condensation and rat leavings.",
        "A low hiss from a cracked pipe. Oily water pools under a sagging beam, and the drip echoes off dented sheet metal nailed over a breach.",
        "Grit and glass grind under your boots. A collapsed workbench spills corroded tools across the floor. The air tastes of old grease.",
        "The ceiling sags low enough to touch — don't. Plaster crumbles at a breath. Water has pooled in the corners, breeding a skin of green scum.",
        "Rat musk and copper. Droppings crunch on every step. Debris chokes half the room — splintered crates, bent pipe, a boot with no owner.",
        "Cold oil smell, sharp and mineral. A generator casing sits gutted in the corner, its wiring pulled like tendons. The walls are pitted deep.",
        "Damp air clings to your skin. Faded signs hang by single bolts, text eaten by rust. A draft hisses through a crack you cannot find.",
    ],
    2: [
        "Brass teeth crunch underfoot — scattered gears from a split housing. The stone walls are cold and slick. A flywheel creaks on a dead axle.",
        "Cold radiates from the Ironbark beams bracing the ceiling. The floor is cracked flagstone, and moss fills every seam with dark green thread.",
        "Stale ash coats your lips. A dead furnace squats against the far wall, its grate choked with clinite. Cold iron pings as it contracts.",
        "Silence presses in. Conveyor rollers sit locked in grime, half-buried under fallen stone. The air is still, and your breathing sounds too loud.",
        "Your fingers come away black from the walls — soot and machine oil, layered deep. Ironbark pegs hold empty tool racks in rigid rows.",
        "Cured hide straps hang from ceiling hooks, swaying in a draft that carries the tang of old tannin. The stone floor is worn smooth in paths.",
        "A fractured mirror throws your face back in pieces. The frame is Ironbark, split along the grain. Glass splinters crackle when you shift weight.",
        "Mossy damp and gear oil, mingled. A clockwork armature stands frozen mid-reach, its joints seized with green corrosion. Water drips from its elbow.",
    ],
    3: [
        "Stone-hard wood pillars, cold to the touch. Faint light pulses from carved grooves — not warm, not welcoming. The floor vibrates underfoot.",
        "Dead coals in a Heartwood forge, cold for centuries. Ash crumbles at a breath. The bellows leather has cracked and curled inward like a fist.",
        "A low grind echoes from deep below — stone on stone, rhythmic. The Heartwood walls are smooth as bone and just as pale. The air bites cold.",
        "Moonstone inlay traces patterns across the walls, each line faintly luminous. The light gives no heat. Your breath fogs in the blue-white glow.",
        "Glass shards snap under your heel — a fallen chandelier, its crystal arms shattered across the floor. Each piece catches the faint rune-light and splits it.",
        "Statues brace the walls, arms raised to hold nothing. Their faces are ground smooth by centuries of dripping water. The stone reeks of wet calcium.",
        "Your arm hair lifts. The air hums at a frequency you feel in your teeth, not your ears. Residual Aether bleeds from the Heartwood grain.",
        "A stone slab dominates the center, carved with route lines that no longer match the corridors outside. The carved channels are filled with cold dust.",
    ],
    4: [
        "Smooth Ambercore walls press close, warm to the touch and faintly translucent. Shapes move inside — slow, suspended. The air tastes of hot resin.",
        "Golden light bleeds through cracks that should not exist. The Blight smell is here — sweetrot and copper. The floor hisses where the light touches stone.",
        "Roots split the ceiling, black and wet, pushing through Ambercore like fingers through wax. They pulse. The drip from their tips burns where it lands.",
        "Your shadow arrives a half-second late. Afterimages trail your hands. Time sags in this room — you feel it drag against your skin like cobweb.",
        "Ozone and hot ash coat your tongue. Your breath mists despite the heat radiating from the walls. The Ambercore grain has begun to splinter and crack.",
        "A throne of charred Heartwood, split down the spine. The armrests are scored with claw marks, deep and parallel. Dust coats everything but the seat.",
        "The room bends at the edges. Straight lines curve if you watch them. A low crack runs through the floor where reality has pulled apart at the seam.",
        "Polished obsidian floor, black and depthless. Press your palm to it and the cold bites bone-deep. Shapes drift beneath the surface, slow and pale.",
    ]
}


# =============================================================================
# SPECIAL ROOM DESCRIPTIONS — BY TYPE
# =============================================================================

# Room-type-specific descriptions that override tier defaults

SPECIAL_ROOM_DESCRIPTIONS: Dict[str, List[str]] = {
    "start": [
        "Cold air rolls out when the Ironbark door grinds open — rot and wet iron, the dungeon breathing in your face. Darkness swallows the torchlight at ten paces.",
        "Daylight dies on the threshold. The stone beyond is slick and the silence has weight. Your footsteps echo once, then the dark eats the sound.",
        "Rune-cuts in the door frame glow dull red as you cross. The stone is warm under your palm. Behind you, the light narrows to a slit, then nothing.",
        "The spiral stair drops into black. Each step is worn to a shallow bowl at the center. A draft hisses upward, carrying the smell of old stone and lamp oil.",
    ],
    "boss": [
        "The air presses down on your chest. A heavy scrape echoes from the dark — deliberate, grinding. The floor is scored with claw marks, deep parallel grooves.",
        "Rust flakes drift from the vaulted ceiling like dead skin. A Heartwood throne sits at the far end, its back split. The room reeks of iron and rot.",
        "Bone fragments snap underfoot — old, dry, scattered thick. The air is dense and still. A low vibration hums through the floor, felt in your knees.",
        "Rune-light pulses from a circle cut into the flagstone, casting everything in sick amber. The walls are gouged. The chamber was built for one purpose.",
    ],
    "treasure": [
        "A metallic glint through the dust. Your boot kicks a coin — the ring of it carries too far in the silence. The floor around the cache is suspiciously clean.",
        "A chest sits dead center, lid cracked open. No dust on the hinges. The lock is intact. The air smells of pine tar and something sharper underneath.",
        "Coins spill from a split crate, green with tarnish. A dark stain spreads beneath the pile — old, soaked into the stone. The loot has a body count.",
        "The vault door hangs ajar on one hinge. The lock is twisted outward — forced from the inside. Scratch marks rake the interior walls, frantic and deep.",
    ],
    "secret": [
        "Stale air, undisturbed for decades. The dust lies in an even sheet across the floor. Your first footprint is the only mark. The walls are dry and sealed tight.",
        "Cracked vellum lines the shelves, brittle to the touch. The ink has faded to brown ghosts of letters. A reading stand holds one tome, spine-cracked and open.",
        "A faint glow from a stone alcove — Moonstone, still carrying charge after all this time. An offering bowl sits empty, its rim worn smooth by hands long gone.",
        "The air is dead still. No draft, no drip, no creak. Sound dies two feet from your mouth. The chamber has been holding its breath for a very long time.",
    ],
    "return_gate": [
        "A stone arch hums with residual warmth. Beyond it, the faintest smell of pine sap and hearth-smoke.",
        "Rune-marks on the floor pulse in a slow rhythm — an old extraction circle, still charged.",
        "The walls here are dry and clean. A bronze bell hangs from a bracket, green with age but intact.",
        "Light filters from above — not rune-light, not blight-glow. Actual daylight, thin but real.",
    ],
    "hidden_portal": [
        "The air crackles with arcane energy. A shimmering tear in reality hangs at eye level, edges burning with pale fire.",
        "Ozone coats your tongue. A portal of swirling violet light hovers above a circle of runes carved into the floor.",
        "Visual distortion warps the far wall. Where stone should be, you see flickering images of somewhere else entirely.",
        "A low thrum vibrates through your teeth. An archway of crystallized magic stands free of any wall, surface rippling like water.",
    ],
    "border_crossing": [
        "The trees thin. Beyond the last twisted trunk, open ground stretches to a wall of grey fog — the Border.",
        "A stone marker, half-buried, reads a name you cannot pronounce. Beyond it, the jurisdiction of the Crown ends.",
        "Wagon ruts cut deep into the mud. This road was used recently. The crossing is close.",
        "The air changes. Cleaner, colder. The oppressive weight of the Patron's reach loosens, just barely.",
    ],
}


# =============================================================================
# BOSS ENEMY TEMPLATES — SPECIAL ENCOUNTERS
# =============================================================================

# Boss enemies are unique, not pulled from the standard tier tables
# Structure: (name, hp, defense, damage, special_abilities, lore)

BOSS_TEMPLATES: List[Tuple[str, int, int, str, List[str], str]] = [
    (
        "Hollowed Bear",
        25,
        14,
        "1d6+4",
        [
            "Terrifying Roar: At the start of combat, all characters must pass a Grit DC 12 check or suffer -1d6 to all rolls for 3 turns.",
            "Thrash: On a critical hit (roll 6 on final die), hits ALL adjacent targets for full damage."
        ],
        "A massive bear, fur matted with rot, eyes burning with unnatural hunger. Its roar echoes with the voices of all it has consumed."
    ),
    (
        "The Rust King",
        50,
        16,
        "5d6",
        [
            "Corroding Touch: On hit, target's armor loses 1 DR permanently.",
            "Summon Rot-Beetles: Action. Summon 1d6 Rot-Beetles.",
            "Ironbark Throne: Immune to Might-based attacks. Weak to Aether."
        ],
        "Once a great artificer, now a corroded tyrant bound to his throne of petrified wood."
    ),
    (
        "The Blight Mother",
        60,
        15,
        "4d6",
        [
            "Spore Burst: AOE 20ft. DC 16 Grit or poisoned (1d6/turn for 5 turns).",
            "Root Network: Heals 2d6 HP per turn while standing in dungeon.",
            "Fungal Rebirth: On death, explodes (3d6 to all in 15ft) and spawns 2 Shambling Moss."
        ],
        "The source of the Blight. A grotesque fusion of tree and flesh."
    ),
    (
        "The Clockwork Archon",
        45,
        18,
        "5d6",
        [
            "Precision Strike: Critical hits on 4-6 instead of 6.",
            "Repair Protocol: Action. Restore 3d6 HP (3 charges).",
            "Overload: When reduced below 15 HP, explodes (5d6 lightning, 20ft radius)."
        ],
        "An ancient war machine, still following its last command: 'Kill all intruders.'"
    ),
    (
        "The Void Herald",
        40,
        17,
        "4d6",
        [
            "Aether Drain: On hit, target loses 1 Aether permanently.",
            "Phase Shift: Bonus action. Become ethereal (immune to physical damage) for 1 turn.",
            "Void Gaze: DC 18 Aether or paralyzed for 1d3 turns."
        ],
        "A creature from between dimensions. It should not exist."
    ),
]


# =============================================================================
# UTILITY FUNCTIONS — WEIGHTED RANDOM SELECTION
# =============================================================================

def weighted_choice(options: List[Tuple[str, float]], rng: random.Random) -> str:
    """
    Select an item from a weighted list.

    Args:
        options: List of (item, weight) tuples
        rng: Random number generator (for determinism)

    Returns:
        Selected item
    """
    total = sum(weight for _, weight in options)
    r = rng.uniform(0, total)
    cumulative = 0
    for item, weight in options:
        cumulative += weight
        if r <= cumulative:
            return item
    return options[-1][0]  # Fallback to last item


# Archetype classification for content enemies
CONTENT_ARCHETYPES = {
    # Tier 1
    "Rot-Beetle": "beast", "Fungal Mite": "beast", "Scrap Imp": "scavenger",
    "Oil Slick": "aetherial", "Blighted Mouse": "beast",
    # Tier 2
    "Clockwork Spider": "construct", "Hollowed Scavenger": "scavenger",
    "Ironbark Hound": "construct", "Shambling Moss": "beast", "Rust Serpent": "beast",
    "Blight-Hawk": "beast",
    # Tier 3
    "Blighted Sentinel": "construct", "Forge Wraith": "aetherial",
    "Heartwood Serpent": "beast", "Ashwood Treant": "beast", "Corrupted Artificer": "scavenger",
    "Spore-Crawler": "beast",
    # Tier 4
    "Ambercore Golem": "construct", "Void Sentinel": "aetherial",
    "Burnwillow Shade": "aetherial", "Blight Warden": "construct", "Ironroot Tyrant": "construct",
}
CONTENT_DR_BY_TIER = {1: 0, 2: 1, 3: 2, 4: 3}

# Enemy → faction alignment (for reputation changes on kill)
ENEMY_FACTIONS: Dict[str, str] = {
    # Hive-aligned (insect creatures)
    "Rot-Beetle": "hive", "Fungal Mite": "mycelium", "Blight-Hawk": "hive",
    # Mycelium-aligned (fungal creatures)
    "Shambling Moss": "mycelium", "Spore-Crawler": "mycelium",
    # Heartwood-aligned (constructs, guardians)
    "Clockwork Spider": "heartwood_elders", "Ironbark Hound": "heartwood_elders",
    "Ambercore Golem": "heartwood_elders", "Ironroot Tyrant": "heartwood_elders",
    "Blighted Sentinel": "heartwood_elders",
    # Hag-aligned (rot creatures with intelligence)
    "Blight Warden": "hag_circle",
    # Canopy-aligned (upper zone creatures)
    "Wind Hawk": "canopy_court", "Branch Stalker": "canopy_court",
    "Canopy Warden": "canopy_court", "Storm Raptor": "canopy_court",
    # Dam-Wright aligned (engineering creatures)
    "Rust Serpent": "dam_wrights",
}

# Loot item → gear set membership
LOOT_SET_IDS: Dict[str, str] = {
    # Arborist's Legacy
    "Root-Song Charm": "arborist_legacy",
    "Sap-Singer's Helm": "arborist_legacy",
    "Resonance Greaves": "arborist_legacy",
    "Crown of Resonance": "arborist_legacy",
    # Warden's Watch
    "Ironbark Helm": "wardens_watch",
    "Ironbark Shield": "wardens_watch",
    "Ironbark Greaves": "wardens_watch",
    "Ironbark Armor": "wardens_watch",
    # Rot Hunter's Trophy
    "Blight-Fang Dagger": "rot_hunter_trophy",
    "Rot Hunter's Mantle": "rot_hunter_trophy",
    "Spore-Sight Goggles": "rot_hunter_trophy",
    "Heartstone Amulet": "rot_hunter_trophy",
    # Moonstone Circle
    "Moonstone Pendant": "moonstone_circle",
    "Herbalist's Satchel": "moonstone_circle",
    "Renewal Chalice": "moonstone_circle",
    "Lifebinder's Mantle": "moonstone_circle",
    # Shadowweave
    "Shadow Cloak": "shadowweave",
    "Burglar's Gloves": "shadowweave",
    "Silent Boots": "shadowweave",
    "Mask of Whispers": "shadowweave",
}


# =============================================================================
# WAVE ENEMIES — Doom-triggered spawns (WO-V17.0)
# =============================================================================
# Wave 1: Stationary ambush (Doom 10) — placed in unvisited rooms
# Wave 2: Slow roamers (Doom 15) — spawn at entrance, BFS every 2 doom ticks

WAVE_ENEMIES: Dict[int, List[Tuple[str, int, int, int, str, str]]] = {
    1: [  # Stationary ambush — placed in random unvisited rooms
        ("Blight-Hawk", 8, 2, 13, "2d6", "Flies. Rot-spore talons: DC 12 Grit or poisoned (1d6 next turn)."),
        ("Hollowed Scavenger", 10, 0, 12, "1d6+2", "Muscle Memory: On death, roll 1d6. On a 6, rises with 1 HP."),
    ],
    2: [  # Slow roamers — spawn at entrance, BFS every 2 doom ticks
        ("Blighted Sentinel", 15, 5, 14, "3d6", "Armored. DR 2. Patrols fixed routes."),
        ("Spore-Crawler", 12, 3, 13, "2d6", "Spore trail: rooms visited become hazardous."),
    ],
}


def get_random_enemy(tier: int, rng: random.Random) -> dict:
    """
    Get a random enemy from the tier-appropriate pool.

    Args:
        tier: Difficulty tier (1-4)
        rng: Random number generator

    Returns:
        Enemy dict with name, hp, defense, damage, special, dr, archetype
    """
    tier = max(1, min(4, tier))  # Clamp to 1-4
    pool = ENEMY_TABLES[tier]
    name, hp_base, hp_var, defense, damage, special = rng.choice(pool)

    enemy = {
        "name": name,
        "hp": hp_base + rng.randint(0, hp_var),
        "defense": defense,
        "damage": damage,
        "special": special,
        "tier": tier,
        "dr": CONTENT_DR_BY_TIER.get(tier, 0),
        "archetype": CONTENT_ARCHETYPES.get(name, "beast"),
    }
    # Faction alignment — for reputation changes on kill
    faction = ENEMY_FACTIONS.get(name)
    if faction:
        enemy["faction_id"] = faction
    return enemy


def get_random_loot(tier: int, rng: random.Random) -> dict:
    """
    Get a random loot item from the tier-appropriate pool.

    Args:
        tier: Difficulty tier (1-4)
        rng: Random number generator

    Returns:
        Loot dict with name, slot, tier, special_traits, description, primary_stat
    """
    tier = max(1, min(4, tier))
    pool = LOOT_TABLES[tier]
    name, slot, item_tier, traits, desc = rng.choice(pool)

    result = {
        "name": name,
        "slot": slot,
        "tier": item_tier,
        "special_traits": traits,
        "description": desc,
    }
    ps = LOOT_PRIMARY_STATS.get(name)
    if ps:
        result["primary_stat"] = ps

    # Gear Set membership
    sid = LOOT_SET_IDS.get(name)
    if sid:
        result["set_id"] = sid

    # Randomized Affixes
    from codex.games.burnwillow.engine import roll_affixes
    prefix, suffix = roll_affixes(item_tier, zone_depth=tier)
    if prefix:
        result["prefix"] = prefix
    if suffix:
        result["suffix"] = suffix

    return result


def get_random_hazard(tier: int, rng: random.Random) -> dict:
    """
    Get a random hazard from the tier-appropriate pool.

    Args:
        tier: Difficulty tier (1-4)
        rng: Random number generator

    Returns:
        Hazard dict with name, stat, dc, effect, description
    """
    tier = max(1, min(4, tier))
    pool = HAZARD_TABLES[tier]
    name, stat, dc, effect, desc = rng.choice(pool)

    return {
        "name": name,
        "stat": stat,
        "dc": dc,
        "effect": effect,
        "description": desc
    }


def get_room_description(tier: int, room_type: str, rng: random.Random) -> str:
    """
    Get a random room description.

    Args:
        tier: Difficulty tier (1-4)
        room_type: Room type (start, boss, treasure, secret, normal)
        rng: Random number generator

    Returns:
        Description string
    """
    # Check for special room type first
    if room_type in SPECIAL_ROOM_DESCRIPTIONS:
        pool = SPECIAL_ROOM_DESCRIPTIONS[room_type]
        return rng.choice(pool)

    # Otherwise use tier-based generic descriptions
    tier = max(1, min(4, tier))
    pool = ROOM_DESCRIPTIONS[tier]
    return rng.choice(pool)


def get_boss_enemy(tier: int, rng: random.Random) -> dict:
    """
    Get a boss enemy appropriate for the tier.

    Args:
        tier: Difficulty tier (1-4)
        rng: Random number generator

    Returns:
        Boss dict with name, hp, defense, damage, special_abilities, lore
    """
    # Select a boss template randomly
    name, hp, defense, damage, abilities, lore = rng.choice(BOSS_TEMPLATES)

    # Scale HP by tier
    scaled_hp = hp + ((tier - 2) * 10)  # Tier 2 = base, Tier 4 = +20 HP

    return {
        "name": name,
        "hp": scaled_hp,
        "defense": defense,
        "damage": damage,
        "special_abilities": abilities,
        "lore": lore,
        "is_boss": True,
        "tier": tier
    }


# =============================================================================
# CANOPY CONTENT TABLES — ASCENDING PATH
# =============================================================================
# Canopy tiers: Tier 1 = trunk base, Tier 2 = mid branches,
# Tier 3 = high canopy, Tier 4 = the Crown itself

CANOPY_ENEMY_TABLES: Dict[int, List[Tuple[str, int, int, int, str, str]]] = {
    1: [
        ("Sap Leech", 4, 1, 9, "1d6", "Attaches on hit. Drains 1 HP/turn until removed (DC 10 Might)."),
        ("Bark Beetle", 3, 1, 10, "2", "Burrows into gear. On hit, 50% chance to damage equipped armor (-1 DR)."),
        ("Amber Spider", 5, 2, 11, "1d6", "Web shot: Target restrained (DC 10 Wits to escape). Range 15ft."),
        ("Trunk Rat", 3, 0, 9, "1d6", "Pack. Always appears in groups of 2-3."),
        ("Sap Sprite", 4, 1, 10, "1d6", "Heals nearby allies 1 HP/turn. Kill first."),
    ],
    2: [
        ("Wind Hawk", 8, 3, 13, "2d6", "Diving strike: +1d6 damage if attacking from above. Flies."),
        ("Branch Stalker", 10, 3, 12, "2d6", "Ambush predator. Always gets surprise round."),
        ("Vine Strangler", 9, 2, 11, "1d6+2", "Grapple on hit (DC 12 Might or restrained, 1d6/turn)."),
        ("Hollow Nester", 7, 3, 12, "2d6", "Summons 1d3 Bark Beetles on death."),
        ("Resin Golem", 12, 4, 13, "2d6", "Hardened sap armor. DR 2. Slow. Immune to fire."),
    ],
    3: [
        ("Canopy Warden", 15, 5, 14, "3d6", "Guardian construct of living wood. DR 2. Regenerates 1 HP in sunlight."),
        ("Storm Raptor", 13, 4, 15, "3d6", "Lightning dive: 3d6 damage in line. Flies. Immune to lightning."),
        ("Thornweaver", 14, 4, 13, "3d6", "Casts thorn wall (blocks movement, 1d6 to pass through). Range 30ft."),
        ("Sap Elemental", 16, 5, 12, "2d6", "Absorbs fire damage as healing. Explodes on death (2d6 to adjacent)."),
        ("Crown Sentinel", 15, 5, 14, "3d6", "Ancient guardian. Calls for reinforcements (50% chance each turn)."),
    ],
    4: [
        ("The Sap Warden", 30, 8, 16, "4d6", "Guardian of the Crown. Regenerates 2d6/turn in Crown room. Immune to sap damage."),
        ("Emberstorm Phoenix", 25, 7, 15, "5d6", "Flies. On death, rebirths with 10 HP after 1 turn. Must be killed twice."),
        ("Living Crown", 28, 8, 15, "4d6", "The tree's immune system. Summons 1 Canopy Warden per turn. DR 3."),
        ("Amber Colossus", 35, 10, 17, "5d6", "Titanic. AOE slam (15ft, DC 16 Might or 3d6 + prone). Immune to mundane weapons."),
    ],
}

CANOPY_ROOM_DESCRIPTIONS: Dict[int, List[str]] = {
    1: [
        "The trunk interior is hollow and vast. Sap veins trace golden lines up walls of living bark. The air is warm and thick with resin.",
        "Amber light filters through knotholes. The heartwood floor is smooth, worn by centuries of sap flow. Something skitters in the walls.",
        "A vertical shaft opens above, ringed with shelf fungus and climbing roots. The bark is warm to the touch, almost feverish.",
        "Sap pools in a hollow, golden and viscous. The walls pulse with a slow rhythm. The tree is alive around you, breathing.",
    ],
    2: [
        "The branch splits into a natural platform. Wind howls through gaps in the bark canopy. The ground sways with each gust.",
        "A nest of woven branches forms a crude room. Feathers and bones litter the floor. Something large lives here.",
        "Sunlight cuts through the leaf cover in blinding shafts. The bark walkway narrows ahead. Below: nothing but air.",
        "Moss carpets the branch junction. Water collects in bark hollows, clear and cold. The view between the leaves is dizzying.",
    ],
    3: [
        "The canopy thins to a lattice of golden leaves. The sky is visible through gaps. Wind-stripped boughs creak and groan.",
        "A platform of woven vines, impossibly high. The world below is a patchwork of green and brown. The air tastes of ozone.",
        "Sap-light blazes from every vein in the wood. The leaves are translucent, flooding everything in amber. Your shadow burns gold.",
        "The boughs here are ancient, thick as castle walls. Carved symbols mark the bark — old wards, still humming with power.",
    ],
    4: [
        "The Crown. A cathedral of living gold. Sap-fire pulses through every branch, every leaf. The air thrums with ancient power.",
        "You stand at the apex of the Burnwillow. The sap reservoir glows below your feet, deep and golden. This is what keeps Emberhome alive.",
        "Light pours from every surface. The Crown is not a place — it is a living furnace. The heat is not painful. It is sacred.",
        "The Burnwillow's heart beats here. Sap surges in arterial channels, golden and molten. The tree knows you are here.",
    ],
}

CANOPY_LOOT_TABLES: Dict[int, List[Tuple[str, str, int, List[str], str]]] = {
    1: [
        ("Sap-Hardened Club", "R.Hand", 1, [], "A club coated in crystallized sap. Sticky but effective."),
        ("Bark-Weave Vest", "Chest", 1, [], "Layered bark strips. DR 1. Smells of pine."),
        ("Climbing Hooks", "Arms", 1, ["[Climb]"], "Iron hooks on leather straps. +1d6 to climbing checks."),
        ("Amber Shard", "Neck", 1, [], "A fragment of crystallized sap. Glows faintly. +1d6 Aether."),
        ("Resin-Sealed Boots", "Legs", 1, [], "Waterproof. Grip on bark surfaces. +5ft climb speed."),
    ],
    2: [
        ("Branch-Bone Bow", "R.Hand", 2, [], "Flexible branch with sinew string. +2d6 Wits attack, 60ft range."),
        ("Sap-Lacquered Armor", "Chest", 2, [], "Hardened sap over cured hide. DR 2. Light. Amber sheen."),
        ("Wind-Caller's Staff", "R.Hand", 2, [], "Carved from a singing branch. +2d6 Aether attack. Hums in wind."),
        ("Canopy Cloak", "Shoulders", 2, [], "Woven leaves. Camouflage in foliage (+2d6 Wits for stealth)."),
        ("Healer's Moss Pack", "Neck", 2, ["[Heal]"], "Living moss compress. Restores 2d6 HP (2 charges)."),
    ],
    3: [
        ("Crown-Wood Spear", "R.Hand", 3, [], "Weapon of the Canopy Wardens. +3d6 Might attack. Reach 10ft."),
        ("Warden's Plate", "Chest", 3, [], "Shaped from living crown-wood. DR 3. Regenerates 1 DR/day if damaged."),
        ("Storm Feather Talisman", "Neck", 3, [], "Raptor feather crackling with static. +1 Aether modifier. Lightning resist."),
        ("Thornweave Gauntlets", "Arms", 3, [], "Thorn-studded gloves. Unarmed +2d6. Grapple targets take 1d6/turn."),
        ("Canopy Walker Greaves", "Legs", 3, [], "Enchanted boots of woven vine. Cannot fall. Immune to knockback."),
    ],
    4: [
        ("Sap-Fire Blade", "R.Hand", 4, [], "A sword of crystallized sap, burning with inner flame. +4d6 Might. 1d6 fire on hit."),
        ("Crown Mantle", "Chest", 4, [], "Armor of the Crown itself. DR 4. Regenerates 1 HP/turn in sunlight."),
        ("Burnwillow Sap Vial", "Neck", 4, ["[Fuel]"], "The prize. Pure Burnwillow sap. Fuels the protective fire for one season."),
        ("Phoenix Pinion", "Shoulders", 4, [], "A feather from the Emberstorm Phoenix. Revive once with 5 HP on death."),
        ("Ring of the Crown", "R.Ring", 4, [], "Living wood ring. +4d6 Aether. Speak with plants at will."),
    ],
}

# Archetype classification for canopy enemies
CANOPY_ARCHETYPES = {
    "Sap Leech": "beast", "Bark Beetle": "beast", "Amber Spider": "beast",
    "Trunk Rat": "beast", "Sap Sprite": "aetherial",
    "Wind Hawk": "beast", "Branch Stalker": "beast", "Vine Strangler": "beast",
    "Hollow Nester": "beast", "Resin Golem": "construct",
    "Canopy Warden": "construct", "Storm Raptor": "beast",
    "Thornweaver": "aetherial", "Sap Elemental": "aetherial", "Crown Sentinel": "construct",
    "The Sap Warden": "construct", "Emberstorm Phoenix": "aetherial",
    "Living Crown": "aetherial", "Amber Colossus": "construct",
}


# =============================================================================
# CONTENT-WIDE CONSTANTS (WO-V17.0 / WO-V32.0)
# =============================================================================

# DR (damage reduction) by tier — bosses use tier + 1
CONTENT_DR_BY_TIER: Dict[int, int] = {1: 0, 2: 1, 3: 2, 4: 3}

# Archetype classification for standard dungeon enemies
CONTENT_ARCHETYPES: Dict[str, str] = {
    # Tier 1
    "Rot-Beetle": "beast", "Fungal Mite": "beast", "Scrap Imp": "scavenger",
    "Oil Slick": "construct", "Blighted Mouse": "beast",
    # Tier 2
    "Clockwork Spider": "construct", "Hollowed Scavenger": "scavenger",
    "Ironbark Hound": "beast", "Shambling Moss": "beast",
    "Rust Serpent": "beast", "Blight-Hawk": "beast",
    # Tier 3
    "Blighted Sentinel": "construct", "Forge Wraith": "aetherial",
    "Heartwood Serpent": "beast", "Ashwood Treant": "beast",
    "Corrupted Artificer": "scavenger", "Spore-Crawler": "beast",
    # Tier 4
    "Ambercore Golem": "construct", "Void Sentinel": "construct",
    "Burnwillow Shade": "aetherial", "Blight Warden": "aetherial",
    "Ironroot Tyrant": "construct",
}

# Wave spawn tables — enemies spawned by the wave escalation system
# Structure matches ENEMY_TABLES: (name, hp_base, hp_var, defense, damage, special)
WAVE_ENEMIES: Dict[int, List[Tuple[str, int, int, int, str, str]]] = {
    1: [
        # Wave 1 (Doom 10): Stationary ambush creatures in unvisited rooms
        ("Blight-Hawk", 8, 2, 13, "2d6", "Flies. Rot-spore talons: On hit, DC 12 Grit or poisoned (1d6 next turn)."),
        ("Hollowed Scavenger", 10, 0, 12, "1d6+2", "Muscle Memory: On death, roll 1d6. On a 6, rises with 1 HP and attacks immediately."),
    ],
    2: [
        # Wave 2 (Doom 15): Slow roamers that start at dungeon entrance
        ("Blighted Sentinel", 15, 5, 14, "3d6", "Armored. DR 2. Patrols fixed routes."),
        ("Spore-Crawler", 12, 3, 13, "2d6", "Spore trail: rooms visited become hazardous."),
    ],
}

# Party size scaling — HP and damage multipliers for encounter balancing
PARTY_SCALING: Dict[int, Dict[str, float]] = {
    1: {"hp_mult": 0.8, "dmg_mult": 0.8},
    2: {"hp_mult": 0.9, "dmg_mult": 0.9},
    3: {"hp_mult": 1.0, "dmg_mult": 1.0},
    4: {"hp_mult": 1.0, "dmg_mult": 1.0},
    5: {"hp_mult": 1.15, "dmg_mult": 1.1},
    6: {"hp_mult": 1.3, "dmg_mult": 1.2},
}


def get_party_scaling(party_size: int) -> Dict[str, float]:
    """Return hp_mult/dmg_mult dict for the given party size."""
    return PARTY_SCALING.get(party_size, PARTY_SCALING[4])


# =============================================================================
# CONDITION TRIGGERS — Enemy special abilities that apply conditions (WO-V34.0)
# =============================================================================
# Maps enemy names to conditions they apply on hit.
# Used by ConditionTracker integration in the dashboard.

ENEMY_CONDITION_TRIGGERS: Dict[str, Dict[str, object]] = {
    "Blight-Hawk": {
        "condition": "Blighted",
        "duration": 2,
        "save_dc": 12,
        "save_stat": "GRIT",
        "source": "Rot-spore talons",
    },
    "Spore-Crawler": {
        "condition": "Poisoned",
        "duration": 3,
        "save_dc": 13,
        "save_stat": "GRIT",
        "source": "Spore trail",
    },
    "Fungal Mite": {
        "condition": "Poisoned",
        "duration": 1,
        "save_dc": 10,
        "save_stat": "GRIT",
        "source": "Spore cloud",
    },
    "Rust Serpent": {
        "condition": "Grappled",
        "duration": -1,
        "save_dc": 12,
        "save_stat": "MIGHT",
        "source": "Constriction",
    },
    "Heartwood Serpent": {
        "condition": "Grappled",
        "duration": -1,
        "save_dc": 14,
        "save_stat": "MIGHT",
        "source": "Constriction",
    },
    "Void Sentinel": {
        "condition": "Blighted",
        "duration": -2,
        "save_dc": 0,
        "save_stat": "",
        "source": "Aether drain",
    },
    "Ashwood Treant": {
        "condition": "Stunned",
        "duration": 1,
        "save_dc": 14,
        "save_stat": "MIGHT",
        "source": "Ground slam",
    },
}


# =============================================================================
# COMBAT INTRO QUIPS — "The Rot Heart" themed
# =============================================================================

COMBAT_INTRO_QUIPS = [
    "Blades out. The Rot Heart hungers.",
    "Steel yourselves. The deep stirs.",
    "They've found you. Fight or fall.",
    "The corruption takes shape. Stand ready.",
    "Something moves in the dark. Weapons up.",
    "The roots shudder. Combat is upon you.",
    "No running now. The Rot Heart knows you're here.",
    "Death comes creeping. Answer in kind.",
]


# =============================================================================
# LORE ENTRIES — Shamanic Setting Data (WO-V16.2)
# =============================================================================

LORE_ENTRIES: Dict[str, List[str]] = {
    "rot": [
        "The Rot is a parasitic fungal corruption rising from the deep roots. It is cold, grey, and silent — it eats living things from the inside out and turns them into Hollows.",
        "The Blight seeks the heart of the Burnwillow to extinguish its fire forever. Where the Rot spreads, the Root-Song falls silent.",
    ],
    "sunfruit": [
        "Sun-Fruits grow only in the Crown — the highest branches of the Burnwillow. They carry the tree's fire-light and can restore what the Rot takes. The climb to harvest them is lethal.",
    ],
    "amber": [
        "Amber is hardened Aether — the golden lifeblood of the tree, frozen in time. Each shard holds a memory: ancestor spirits, stored sunlight, echoes of the Root-Song. It is currency, crafting material, and sacred relic.",
    ],
    "groves": [
        "There are four Groves — four world-trees, each a season. Burnwillow is Autumn, the dying hearth. Verdhollow is Spring, drowning in growth. Solheart is Summer, blazing and droughted. Ashenmere is Winter, frozen and still. Deep beneath each tree, the Root-Roads connect them all.",
    ],
    "ambervault": [
        "Amber Vaults are indestructible Iron-Amber spheres sealed by the Arborists during the Golden Age collapse. Clean air inside — no Rot. Guarded by Wood-Golem Constructs. Primary source of legendary loot.",
    ],
    "memoryseed": [
        "Memory Seeds are fossilized nuts found in Amber Vaults. Each holds a crafting blueprint. Bring one to Emberhome to unlock a legendary recipe — but carrying it doubles the Doom Clock and makes stealth impossible.",
    ],
}


# =============================================================================
# BESTIARY INDEX — Flat lookup from all enemy tables (WO-V16.2)
# =============================================================================

BESTIARY: Dict[str, dict] = {}


def _build_bestiary():
    """Build flat name->statblock index from all enemy tables."""
    for tier, enemies in ENEMY_TABLES.items():
        for name, hp, hp_var, defense, damage, special in enemies:
            BESTIARY[name.lower()] = {
                "name": name, "hp": f"{hp}-{hp+hp_var}", "defense": defense,
                "damage": damage, "special": special, "tier": tier,
                "source": "Dungeon", "archetype": CONTENT_ARCHETYPES.get(name, "unknown"),
                "dr": CONTENT_DR_BY_TIER.get(tier, 0),
            }
    for tier, enemies in CANOPY_ENEMY_TABLES.items():
        for name, hp, hp_var, defense, damage, special in enemies:
            BESTIARY[name.lower()] = {
                "name": name, "hp": f"{hp}-{hp+hp_var}", "defense": defense,
                "damage": damage, "special": special, "tier": tier,
                "source": "Canopy", "archetype": CANOPY_ARCHETYPES.get(name, "unknown"),
                "dr": CONTENT_DR_BY_TIER.get(tier, 0),
            }
    for name, hp, defense, damage, abilities, lore in BOSS_TEMPLATES:
        BESTIARY[name.lower()] = {
            "name": name, "hp": str(hp), "defense": defense,
            "damage": damage, "special": " | ".join(abilities), "tier": "Boss",
            "source": "Boss", "archetype": "boss", "dr": "varies", "lore": lore,
        }
    # Aliases
    BESTIARY["hollow"] = BESTIARY.get("hollowed scavenger", {})
    BESTIARY["bear"] = BESTIARY.get("hollowed bear", {})
    BESTIARY["blight mother"] = BESTIARY.get("the blight mother", {})
    BESTIARY["rust king"] = BESTIARY.get("the rust king", {})


_build_bestiary()


def lookup_creature(query: str) -> str | None:
    """Search bestiary by exact or substring match. Returns formatted statblock or None."""
    q = query.strip().lower()
    # Exact match
    entry = BESTIARY.get(q)
    if not entry:
        # Substring match
        matches = [(k, v) for k, v in BESTIARY.items() if q in k]
        if len(matches) == 1:
            entry = matches[0][1]
        elif len(matches) > 1:
            names = [m[1]["name"] for m in matches[:6]]
            return f"Multiple matches: {', '.join(names)}. Be more specific."
        else:
            return None

    lines = [
        f"**{entry['name']}** (Tier {entry['tier']} {entry['source']})",
        f"HP: {entry['hp']} | DEF: {entry['defense']} | DMG: {entry['damage']} | DR: {entry['dr']}",
        f"Type: {entry['archetype']}",
        f"Special: {entry['special']}",
    ]
    if entry.get("lore"):
        lines.append(f"Lore: {entry['lore']}")
    return "\n".join(lines)


# =============================================================================
# DEMO / TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("BURNWILLOW CONTENT DATABASE v1.0 - STANDALONE TEST")
    print("=" * 70)

    rng = random.Random(42)  # Deterministic seed for testing

    for tier in [1, 2, 3, 4]:
        print(f"\n{'='*70}")
        print(f"TIER {tier} CONTENT SAMPLES")
        print(f"{'='*70}")

        # Enemy
        print("\n[ENEMY]")
        enemy = get_random_enemy(tier, rng)
        print(f"  Name: {enemy['name']}")
        print(f"  HP: {enemy['hp']} | Defense: {enemy['defense']} | Damage: {enemy['damage']}")
        print(f"  Special: {enemy['special']}")

        # Loot
        print("\n[LOOT]")
        loot = get_random_loot(tier, rng)
        print(f"  Name: {loot['name']}")
        print(f"  Slot: {loot['slot']} | Tier: {loot['tier']}")
        print(f"  Traits: {', '.join(loot['special_traits']) if loot['special_traits'] else 'None'}")
        print(f"  Desc: {loot['description']}")

        # Hazard
        print("\n[HAZARD]")
        hazard = get_random_hazard(tier, rng)
        print(f"  Name: {hazard['name']}")
        print(f"  Check: {hazard['stat']} DC {hazard['dc']}")
        print(f"  Effect: {hazard['effect']}")
        print(f"  Desc: {hazard['description']}")

        # Room Description
        print("\n[ROOM DESCRIPTION]")
        desc = get_room_description(tier, "normal", rng)
        print(f"  {desc}")

    # Boss Sample
    print(f"\n{'='*70}")
    print("BOSS ENCOUNTER SAMPLE")
    print(f"{'='*70}")
    boss = get_boss_enemy(3, rng)
    print(f"\nName: {boss['name']}")
    print(f"HP: {boss['hp']} | Defense: {boss['defense']} | Damage: {boss['damage']}")
    print(f"Lore: {boss['lore']}")
    print("Special Abilities:")
    for ability in boss['special_abilities']:
        print(f"  - {ability}")

    print(f"\n{'='*70}")
    print("DEMO COMPLETE")
    print(f"{'='*70}")
