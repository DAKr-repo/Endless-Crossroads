"""
codex.forge.reference_data.stc_traps
=====================================
Rosharan trap reference data for the Cosmere RPG (STC).

SOURCE AUTHORITY:
  No canonical PDF source for traps — these are setting-derived,
  authored for this codebase using Rosharan lore and the D&D 5e trap
  schema (name, tier, trigger, dc_detect, dc_disarm, damage,
  damage_type, description, source).

SCHEMA:
  STC_TRAPS = {
      "version": int,
      "source": str,
      "note": str,
      "traps": [
          {
              "name": str,
              "tier": int (1-4),
              "trigger": str,
              "dc_detect": int,
              "dc_disarm": int,
              "damage": str (dice notation),
              "damage_type": str,
              "description": str,
              "source": "stc",
          },
          ...
      ],
  }
"""

STC_TRAPS: dict = {
    "version": 1,
    "source": "reference_data (setting-derived)",
    "note": "Rosharan traps for Stormlight/Cosmere RPG. Tier 1-4, follows D&D 5e trap schema.",
    "traps": [
        # Tier 1 (DC 10-12)
        {"name": "Crem-Covered Pit", "tier": 1, "trigger": "pressure plate", "dc_detect": 10, "dc_disarm": 11, "damage": "2d6", "damage_type": "impact", "description": "A weathered chasm floor conceals a deep gap beneath a thin crust of hardened crem. The surface cracks under weight, dropping victims into darkness below.", "source": "stc"},
        {"name": "Rockbud Snare", "tier": 1, "trigger": "tripwire", "dc_detect": 11, "dc_disarm": 10, "damage": "0", "damage_type": "none", "description": "Cultivated rockbud tendrils stretch across a narrow passage at ankle height. When disturbed, the tendrils contract and grip tightly, immobilizing the victim until cut free.", "source": "stc"},
        {"name": "Stormlight Tripwire", "tier": 1, "trigger": "proximity", "dc_detect": 12, "dc_disarm": 11, "damage": "1d6", "damage_type": "keen", "description": "A razor-thin line of stormlight-infused wire stretches at ankle height across a corridor. Nearly invisible in dim light, it slices cleanly through boot leather and flesh.", "source": "stc"},
        {"name": "Alerter Fabrial Ward", "tier": 1, "trigger": "proximity", "dc_detect": 11, "dc_disarm": 12, "damage": "0", "damage_type": "none", "description": "A hidden fabrial concealed in a wall niche pulses with a faint hum when living creatures pass within ten feet, triggering an alarm audible to nearby guards.", "source": "stc"},
        {"name": "Cremling Swarm Nest", "tier": 1, "trigger": "touch", "dc_detect": 10, "dc_disarm": 10, "damage": "1d4", "damage_type": "keen", "description": "A hollow section of wall or floor contains a dormant cremling colony. Disturbing the nest releases hundreds of biting cremlings that swarm over the intruder.", "source": "stc"},
        # Tier 2 (DC 13-14)
        {"name": "Soulcast Floor Trap", "tier": 2, "trigger": "pressure plate", "dc_detect": 13, "dc_disarm": 14, "damage": "2d8", "damage_type": "impact", "description": "A section of floor has been prepared with a delayed Soulcasting trigger. When sufficient weight is applied, the stone transmutes to air, creating a twenty-foot drop into the chamber below.", "source": "stc"},
        {"name": "Shardplate Shard Launcher", "tier": 2, "trigger": "tripwire", "dc_detect": 14, "dc_disarm": 13, "damage": "2d6", "damage_type": "keen", "description": "Broken fragments of dead Shardplate are loaded into spring-driven wall slots. A tripwire releases the mechanism, firing razor-sharp plate shards across the corridor.", "source": "stc"},
        {"name": "Stormlight Drain Field", "tier": 2, "trigger": "proximity", "dc_detect": 13, "dc_disarm": 14, "damage": "2d6", "damage_type": "spirit", "description": "A carefully tuned fabrial creates a field that siphons stormlight from spheres and surgebinders alike. Infused gems go dun within seconds, and Radiants feel their investiture pulled away.", "source": "stc"},
        {"name": "Parshendi Warform Ambush", "tier": 2, "trigger": "proximity", "dc_detect": 14, "dc_disarm": 13, "damage": "2d6", "damage_type": "keen", "description": "Listeners in warform wait motionless in concealed wall niches, their carapace blending with the stone. They strike with coordinated precision when prey passes between them.", "source": "stc"},
        {"name": "Highstorm Funnel", "tier": 2, "trigger": "opening", "dc_detect": 13, "dc_disarm": 14, "damage": "2d8", "damage_type": "impact", "description": "A corridor engineered to channel highstorm winds into a concentrated blast. Opening the wrong door or triggering the mechanism unleashes devastating winds through the passage.", "source": "stc"},
        # Tier 3 (DC 15-16)
        {"name": "Thunderclast Awakening", "tier": 3, "trigger": "pressure plate", "dc_detect": 15, "dc_disarm": 16, "damage": "3d8", "damage_type": "impact", "description": "A section of wall contains a dormant thunderclast fragment. Sufficient pressure on a trigger plate causes the stone construct to animate partially, smashing outward with devastating force.", "source": "stc"},
        {"name": "Voidlight Corruption Trap", "tier": 3, "trigger": "touch", "dc_detect": 16, "dc_disarm": 15, "damage": "3d6", "damage_type": "spirit", "description": "A corrupted gemstone leaks Odium's voidlight influence in a subtle aura. Those who touch or linger near it feel rage building within them, eroding rational thought and turning allies against each other.", "source": "stc"},
        {"name": "Gravity Reversal Fabrial", "tier": 3, "trigger": "proximity", "dc_detect": 15, "dc_disarm": 16, "damage": "3d6", "damage_type": "impact", "description": "A Reverser fabrial hidden in the ceiling inverts gravity in a twenty-foot zone. Victims are hurled upward to slam against the ceiling, then fall again when the effect cycles.", "source": "stc"},
        {"name": "Unmade Whisper Trap", "tier": 3, "trigger": "proximity", "dc_detect": 16, "dc_disarm": 15, "damage": "2d8", "damage_type": "spirit", "description": "A psychic emanation from a sealed Unmade fragment fills the area with whispered terrors. Victims experience overwhelming fear and confusion, unable to distinguish reality from hallucination.", "source": "stc"},
        {"name": "Chasmfiend Lure", "tier": 3, "trigger": "tripwire", "dc_detect": 15, "dc_disarm": 16, "damage": "3d8", "damage_type": "keen", "description": "A concealed mechanism generates vibrations that mimic a chrysalis cracking. Within 1d4 rounds, a chasmfiend arrives to investigate, attacking anything in its path.", "source": "stc"},
        # Tier 4 (DC 18-20)
        {"name": "Oathgate Misalignment", "tier": 4, "trigger": "touch", "dc_detect": 18, "dc_disarm": 20, "damage": "4d10", "damage_type": "spirit", "description": "A sabotaged Oathgate platform has been retuned to shunt travellers into Shadesmar rather than their intended destination. Victims arrive in the cognitive realm without preparation or means of return.", "source": "stc"},
        {"name": "Dawnshard Resonance", "tier": 4, "trigger": "proximity", "dc_detect": 19, "dc_disarm": 18, "damage": "4d8", "damage_type": "spirit", "description": "An ancient Dawncity defense mechanism activates when intruders approach, unleashing devastating light that resonates with the fundamental forces of creation itself.", "source": "stc"},
        {"name": "Midnight Essence Spawner", "tier": 4, "trigger": "opening", "dc_detect": 18, "dc_disarm": 19, "damage": "4d6", "damage_type": "spirit", "description": "A sealed chamber contains a fragment of Re-Shephir, the Midnight Mother. Opening the seal allows the fragment to produce midnight essence creatures that attack relentlessly.", "source": "stc"},
        {"name": "Everstorm Conduit", "tier": 4, "trigger": "proximity", "dc_detect": 19, "dc_disarm": 18, "damage": "4d10", "damage_type": "impact", "description": "Trapped Voidspren within a reinforced gemstone array channel everstorm energy through a corridor. The destructive inverse-stormlight tears at both physical and spiritual aspects of anyone caught in the blast.", "source": "stc"},
        {"name": "Fused Ambush Point", "tier": 4, "trigger": "touch", "dc_detect": 18, "dc_disarm": 20, "damage": "4d8", "damage_type": "keen", "description": "An ancient Fused warrior lies dormant within the stone, awaiting the touch of stormlight or an unwary hand on the sealed gemstone that serves as their prison. Once awakened, they attack with millennia of combat experience.", "source": "stc"},
    ],
}
