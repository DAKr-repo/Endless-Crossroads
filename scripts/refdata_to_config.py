"""
scripts/refdata_to_config.py
============================
Convert reference_data Python dicts into config JSON files.

Usage:
    python scripts/refdata_to_config.py --system sav
    python scripts/refdata_to_config.py --all
    python scripts/refdata_to_config.py --all --extract npcs
    python scripts/refdata_to_config.py --all --force

Systems: bitd, sav, bob, cbrpnk, candela, stc (magic items, traps, tables)
"""

import argparse
import json
import sys
from pathlib import Path

# Project root is the parent of scripts/
ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"

SUPPORTED_SYSTEMS = ["bitd", "sav", "bob", "cbrpnk", "candela", "stc"]
EXTRACT_TYPES = ["npcs", "locations", "hazards", "tables", "magic_items", "bestiary_loot", "traps"]

from codex.forge.reference_data.stc_traps import STC_TRAPS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, data: dict, force: bool) -> str:
    """Write JSON to path. Returns 'created', 'skipped', or 'overwritten'."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return "skipped"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return "overwritten" if path.exists() else "created"


def _report(results: list[tuple[str, str]]) -> None:
    """Print summary of file operations."""
    for path, status in results:
        icon = "+" if status == "created" else ("~" if status == "overwritten" else "-")
        print(f"  [{icon}] {status:10s}  {path}")


def _parse_string_npc(raw: str, faction_name: str, faction: dict) -> dict:
    """Parse 'Name (role details)' string format into NPC dict."""
    if "(" in raw:
        name, rest = raw.split("(", 1)
        role = rest.rstrip(")")
    else:
        name = raw
        role = "notable figure"
    name = name.strip()
    role = role.strip()
    # Build description from faction context
    quirk = faction.get("quirk", "")
    desc_base = faction.get("description", "")
    first_sentence = desc_base.split(".")[0].strip() if desc_base else ""
    description = f"{role} of {faction_name}."
    if first_sentence:
        description += f" {first_sentence}."
    if quirk:
        description += f" {quirk}"
    return {
        "name": name,
        "role": role,
        "description": description,
        "source": faction_name,
    }


def _topology_for(turf: str) -> str:
    """Classify turf string into topology."""
    lower = turf.lower()
    wilderness_keywords = ["sea", "forest", "wasteland", "nebula", "asteroid", "open ", "orbit", "space", "island", "mountain", "dig site", "shanty", "fog", "canal"]
    dungeon_keywords = ["prison", "vault", "underground", "ironhook", "isotropa", "cell", "crematorium"]
    for kw in dungeon_keywords:
        if kw in lower:
            return "dungeon"
    for kw in wilderness_keywords:
        if kw in lower:
            return "wilderness"
    return "settlement"


def _services_for_faction(faction: dict, system: str) -> list[str]:
    """Infer services from faction type/description."""
    desc = (faction.get("description", "") + " " + faction.get("quirk", "")).lower()
    faction_type = faction.get("faction_type", faction.get("type", "")).lower()
    # Arcane / research factions
    if any(k in desc for k in ["occult", "ritual", "spirit", "arcane", "fabrial", "alchemical", "mystic", "phenomena"]):
        return ["research", "healing"]
    # Institutional / government
    if any(k in desc for k in ["govern", "official", "ministry", "military", "legion", "guild", "hegemoni", "church", "prison"]):
        return ["rest", "research"]
    # Criminal / underworld
    if any(k in desc for k in ["gang", "criminal", "smug", "contraband", "thiev", "racket", "black market", "scaveng", "fence", "undercity"]):
        return ["rest", "rumor", "buy"]
    return ["rest", "rumor"]


# ---------------------------------------------------------------------------
# NPC Extraction
# ---------------------------------------------------------------------------

def extract_npcs(system: str, force: bool, results: list) -> None:
    """Extract NPCs from reference_data factions into config/npcs/{system}.json."""
    named_npcs: list[dict] = []

    if system == "bitd":
        from codex.forge.reference_data.bitd_factions import FACTIONS
        for faction_name, faction in FACTIONS.items():
            for raw in faction.get("notable_npcs", []):
                if isinstance(raw, str):
                    named_npcs.append(_parse_string_npc(raw, faction_name, faction))

    elif system == "sav":
        from codex.forge.reference_data.sav_factions import FACTIONS
        for faction_name, faction in FACTIONS.items():
            for raw in faction.get("notable_npcs", []):
                if isinstance(raw, str):
                    named_npcs.append(_parse_string_npc(raw, faction_name, faction))

    elif system == "bob":
        from codex.forge.reference_data.bob_factions import FACTIONS
        for faction_name, faction in FACTIONS.items():
            for npc in faction.get("notable_npcs", []):
                if isinstance(npc, dict):
                    named_npcs.append({
                        "name": npc.get("name", "Unknown"),
                        "role": npc.get("role", "notable figure"),
                        "description": npc.get("description", f"Notable figure of {faction_name}."),
                        "source": faction_name,
                    })

    elif system == "cbrpnk":
        from codex.forge.reference_data.cbrpnk_corps import FACTIONS
        for faction_name, faction in FACTIONS.items():
            for npc in faction.get("notable_npcs", []):
                if isinstance(npc, dict):
                    note = npc.get("note", "")
                    desc = f"{npc.get('role', 'notable figure')} of {faction_name}."
                    if note:
                        desc += f" {note}"
                    named_npcs.append({
                        "name": npc.get("name", "Unknown"),
                        "role": npc.get("role", "notable figure"),
                        "description": desc,
                        "source": faction_name,
                    })

    elif system == "candela":
        from codex.forge.reference_data.candela_circles import NPC_RELATIONSHIPS
        # Load existing candela.json and merge — append new NPCs only
        existing_path = CONFIG / "npcs" / "candela.json"
        if not existing_path.exists():
            # No existing file; create from scratch
            for npc in NPC_RELATIONSHIPS:
                named_npcs.append({
                    "name": npc.get("name", ""),
                    "role": npc.get("role", "contact"),
                    "description": npc.get("connection_to_phenomena", npc.get("secret", "")),
                    "source": "candela_circles.NPC_RELATIONSHIPS",
                })
        else:
            existing_data = json.loads(existing_path.read_text(encoding="utf-8"))
            existing_names = {e.get("name", "") for e in existing_data.get("named_npcs", [])}
            new_npcs = []
            for npc in NPC_RELATIONSHIPS:
                name = npc.get("name", "")
                if name in existing_names:
                    continue
                new_npcs.append({
                    "name": name,
                    "role": npc.get("role", "contact"),
                    "description": npc.get("connection_to_phenomena", npc.get("secret", "")),
                    "source": "candela_circles.NPC_RELATIONSHIPS",
                })
            if not new_npcs and not force:
                results.append((str(existing_path.relative_to(ROOT)), "skipped"))
                return
            # Preserve original structure — append new NPCs at end
            out_data = dict(existing_data)
            out_data["named_npcs"] = list(existing_data.get("named_npcs", [])) + new_npcs
            path = CONFIG / "npcs" / "candela.json"
            status = _write(path, out_data, force=True)
            results.append((str(path.relative_to(ROOT)), status))
            return

    else:
        return  # stc has no NPC extraction

    data = {
        "version": 1,
        "source": "reference_data",
        "named_npcs": named_npcs,
    }
    path = CONFIG / "npcs" / f"{system}.json"
    status = _write(path, data, force)
    results.append((str(path.relative_to(ROOT)), status))


# ---------------------------------------------------------------------------
# Location Extraction
# ---------------------------------------------------------------------------

def extract_locations(system: str, force: bool, results: list) -> None:
    """Extract locations from faction turf/sector fields into config/locations/{system}.json."""
    locations: list[dict] = []
    seen: set[str] = set()

    if system == "bitd":
        from codex.forge.reference_data.bitd_factions import FACTIONS
        for faction_name, faction in FACTIONS.items():
            turf = faction.get("turf", "")
            if not turf or turf in seen:
                continue
            seen.add(turf)
            locations.append({
                "name": turf,
                "description": f"Turf of {faction_name}. {faction.get('description', '')}",
                "topology": _topology_for(turf),
                "services": _services_for_faction(faction, system),
            })

    elif system == "sav":
        from codex.forge.reference_data.sav_factions import FACTIONS
        for faction_name, faction in FACTIONS.items():
            sector = faction.get("sector", "")
            if not sector or sector in seen:
                continue
            seen.add(sector)
            locations.append({
                "name": sector,
                "description": f"Operating zone of {faction_name}. {faction.get('description', '').split('.')[0]}.",
                "topology": _topology_for(sector),
                "services": _services_for_faction(faction, system),
            })

    elif system == "bob":
        # BoB has no turf fields; author 6 strategic locations from Eastern Kingdoms setting
        locations = [
            {
                "name": "Skydagger Keep",
                "description": "The Legion's final defensive stronghold in the Eastern Kingdoms. A fortress carved into the mountain spine, bristling with ballistae and last-ditch wards against the undead tide.",
                "topology": "dungeon",
                "services": ["rest", "research"],
            },
            {
                "name": "The Shattered Field",
                "description": "A blasted killing ground east of the Tigeria River where the Cinder King's advance first broke the allied armies. Scorched earth, rusted armor, and unquiet dead as far as the eye can see.",
                "topology": "wilderness",
                "services": ["rumor"],
            },
            {
                "name": "Plainsworth",
                "description": "A walled city on the march route now serving as a Legion resupply point. The citizens are terrified, the council is divided, and the market stalls still sell bread despite everything.",
                "topology": "settlement",
                "services": ["rest", "rumor", "buy"],
            },
            {
                "name": "The Orite Waystation",
                "description": "A crafter-temple turned field hospital maintained by remnant Orite priests. Sanctified ground that slows corruption and provides the only reliable healing west of Dar.",
                "topology": "settlement",
                "services": ["rest", "healing", "research"],
            },
            {
                "name": "The Ashen Wastes",
                "description": "A region poisoned by Blighter's toxic advance. Nothing grows here. The mists are thick, the water is black, and every corpse is a potential enemy. Scouts avoid it when possible.",
                "topology": "wilderness",
                "services": [],
            },
            {
                "name": "The Iron Road Junction",
                "description": "A strategic crossroads the Legion must hold or concede the eastern supply line. Whoever controls this junction controls the flow of food, shot, and reinforcements.",
                "topology": "settlement",
                "services": ["rest", "buy"],
            },
        ]

    elif system == "cbrpnk":
        from codex.forge.reference_data.cbrpnk_corps import FACTIONS
        for faction_name, faction in FACTIONS.items():
            loc = faction.get("location", faction.get("sector", ""))
            if not loc or loc in seen:
                continue
            seen.add(loc)
            locations.append({
                "name": loc,
                "description": f"Territory/sector of {faction_name}. {faction.get('description', '').split('.')[0]}.",
                "topology": _topology_for(loc),
                "services": _services_for_faction(faction, system),
            })

    elif system == "candela":
        # Candela already has a rich locations file; supplement only
        existing_path = CONFIG / "locations" / "candela.json"
        if existing_path.exists():
            # Don't overwrite the existing rich candela locations
            results.append((str((CONFIG / "locations" / "candela.json").relative_to(ROOT)), "skipped"))
            return
        # Fallback: write minimal stub if file missing
        locations = [
            {
                "name": "Newfaire",
                "description": "The city of Newfaire, seat of Candela Obscura operations.",
                "topology": "settlement",
                "services": ["rest", "research"],
            }
        ]

    else:
        return  # stc has no location extraction

    if not locations:
        return

    data = {
        "version": 1,
        "source": "reference_data",
        "locations": locations,
    }
    path = CONFIG / "locations" / f"{system}.json"
    status = _write(path, data, force)
    results.append((str(path.relative_to(ROOT)), status))


# ---------------------------------------------------------------------------
# Hazard Authoring
# ---------------------------------------------------------------------------

_AUTHORED_HAZARDS: dict[str, dict] = {
    "bitd": {
        "version": 1,
        "format": "fitd",
        "source": "reference_data (setting-derived)",
        "note": "Doskvol hazards. Tier = narrative difficulty (1-4). Damage is narrative harm.",
        "tiers": {
            "1": [
                {"name": "Bluecoat Patrol", "dc": 10, "damage": "1d4", "damage_type": "narrative", "description": "A beat officer rounds the corner at the wrong moment. Whistles, cudgels, and an arrest warrant with your name on it."},
                {"name": "Gang Lookout Spotted", "dc": 10, "damage": "1d4", "damage_type": "narrative", "description": "A rival crew's spotter clocks you in their territory. By tomorrow, everyone will know you were here."},
                {"name": "Weak Ghost Encounter", "dc": 9, "damage": "1d4", "damage_type": "narrative", "description": "A recently deceased soul, still anchored by obsession, rattles nearby. Its touch leaves cold dread and a shaking hand."},
                {"name": "Vice Entanglement", "dc": 10, "damage": "1d4", "damage_type": "narrative", "description": "An old debt surfaces at a gambling den or a vice purveyor calls in a favour. Stress accumulates with every refusal."},
            ],
            "2": [
                {"name": "Inspector's Tail", "dc": 13, "damage": "1d6", "damage_type": "narrative", "description": "A plainclothes Inspector has been building a file on your crew. The surveillance is methodical and the evidence is already considerable."},
                {"name": "Electroplasmic Discharge", "dc": 13, "damage": "1d6", "damage_type": "narrative", "description": "A cracked electroplasm conduit or a mishandled ghost-slayer sends a blinding arc of blue-white energy through the room."},
                {"name": "Canal Ambush", "dc": 12, "damage": "1d6", "damage_type": "narrative", "description": "The gondola grinds to a halt. Ropes stretch across the waterway and figures drop from the bridge above. This is a toll."},
                {"name": "Spirit Possession Attempt", "dc": 13, "damage": "1d6", "damage_type": "narrative", "description": "A hungry ghost tries to slip into a crew member's body through a moment of weakness or emotional fracture."},
            ],
            "3": [
                {"name": "Spirit Warden Response", "dc": 15, "damage": "1d8", "damage_type": "narrative", "description": "Bronze masks. Ghost-slayers. They know something unnatural happened here and they are here to contain it — including anyone who witnessed it."},
                {"name": "Rival Gang War Spills Over", "dc": 15, "damage": "1d8", "damage_type": "narrative", "description": "The Lampblacks and Red Sashes have chosen tonight and this street. Crossbows fire from both sides with no interest in innocent bystanders."},
                {"name": "Leviathan Blood Toxicity", "dc": 14, "damage": "1d8", "damage_type": "narrative", "description": "Exposure to improperly stored leviathan blood corrodes the skin, distorts vision with ghost-field overlays, and induces hunger for darkness."},
                {"name": "Deathseeker Crow Warning", "dc": 15, "damage": "1d8", "damage_type": "narrative", "description": "A trained crow lands on a crew member's shoulder and stares without blinking. Someone on this street is marked for death — possibly you."},
            ],
            "4": [
                {"name": "Demonic Manifestation", "dc": 18, "damage": "2d6", "damage_type": "narrative", "description": "Something was summoned that should not have been. It fills the room with wrongness and feeds on will as easily as flesh."},
                {"name": "Imperial Crackdown", "dc": 18, "damage": "2d6", "damage_type": "narrative", "description": "The Lord Governor has declared a district lockdown. Every exit is manned. Every name is being checked. A major score just became a survival scenario."},
                {"name": "Dark Bargain Backlash", "dc": 17, "damage": "2d6", "damage_type": "narrative", "description": "A deal struck in a moment of desperation comes due. The entity doesn't negotiate. The debt is paid in flesh, memory, or something worse."},
                {"name": "Vault Trap — Ancient", "dc": 18, "damage": "2d6", "damage_type": "narrative", "description": "The vault designers anticipated thieves. Electroplasmic mines, spectral alarms, and a bound guardian that has been waiting in the dark for forty years."},
            ],
        },
    },

    "sav": {
        "version": 1,
        "format": "fitd",
        "source": "reference_data (setting-derived)",
        "note": "Procyon sector hazards. Tier = threat level. Damage is narrative harm.",
        "tiers": {
            "1": [
                {"name": "Wanted Level Escalation", "dc": 10, "damage": "1d4", "damage_type": "narrative", "description": "The Hegemony's threat board ticks up a notch. More patrol routes cross your flight path. Docking fees triple without explanation."},
                {"name": "Supply Shortage", "dc": 10, "damage": "1d4", "damage_type": "narrative", "description": "The next station is dry. Spare parts, fuel cells, and rations are rationed by Guild order. Someone will have to do without."},
                {"name": "Xeno Wildlife Encounter", "dc": 9, "damage": "1d4", "damage_type": "narrative", "description": "The surface scan was wrong or incomplete. Something territorial and fast lives in this biome and it has already flanked the team."},
                {"name": "Forged Papers Flagged", "dc": 10, "damage": "1d4", "damage_type": "narrative", "description": "The docking authority's new scanner catches something off about the credentials. A clerk with a comm link and a suspicious expression."},
            ],
            "2": [
                {"name": "Hegemony Patrol Intercept", "dc": 13, "damage": "1d6", "damage_type": "narrative", "description": "A Hegemony patrol frigate drops out of hyperspace directly in your lane. Transponders check out or they don't. Boarding action pending."},
                {"name": "Way Creature Sighting", "dc": 13, "damage": "1d6", "damage_type": "narrative", "description": "Something from between the stars has taken an interest in the crew. It doesn't move like normal matter and it doesn't respond to normal stimuli."},
                {"name": "Jumpgate Malfunction", "dc": 12, "damage": "1d6", "damage_type": "narrative", "description": "The gate shudders on exit and spits the ship out off-course and off-schedule. Hull stress, navigation data scrambled, and an unknown system on the screens."},
                {"name": "Bounty Hunter on Approach", "dc": 13, "damage": "1d6", "damage_type": "narrative", "description": "A fast ship has been matching your heading for three jumps. No transponder. No comm response. It's closing."},
            ],
            "3": [
                {"name": "Ion Storm", "dc": 15, "damage": "1d8", "damage_type": "narrative", "description": "Sensors go dark. Comms go dark. The ion wall rolls over the ship and everything electronic becomes temporarily useless or permanently fried."},
                {"name": "System Lockdown", "dc": 15, "damage": "1d8", "damage_type": "narrative", "description": "The station governor has sealed all docking bays and issued a sector-wide arrest warrant. No one goes in or out without authorization no one has."},
                {"name": "Pirate Ambush", "dc": 14, "damage": "1d8", "damage_type": "narrative", "description": "Three ships drop out of the dust cloud. They've been waiting. The crew knew the route — which means someone talked."},
                {"name": "Cult Ritual Interruption", "dc": 15, "damage": "1d8", "damage_type": "narrative", "description": "The site is already occupied. Something is mid-ritual, the air smells of burnt ozone and old blood, and stopping it is the only option."},
            ],
            "4": [
                {"name": "Void Exposure", "dc": 18, "damage": "2d6", "damage_type": "narrative", "description": "The hull breach is small but the vacuum is absolute. Every second counts, suit or no suit, and the cold of space cares nothing for quick thinking."},
                {"name": "Ancient Ur Defense System", "dc": 18, "damage": "2d6", "damage_type": "narrative", "description": "The Ur ruin has automated defenses that predate every known civilization. They activate without warning and they were not built for biological targets."},
                {"name": "Antimatter Containment Breach", "dc": 17, "damage": "2d6", "damage_type": "narrative", "description": "The drive's containment field is failing. Every crew member has minutes to either fix it, vent it safely, or get very far away."},
                {"name": "Lost Legion Boarding Action", "dc": 18, "damage": "2d6", "damage_type": "narrative", "description": "They come through the airlock in vacuum suits with no insignia and no comm traffic. The Lost Legion takes ships, not prisoners, and they've already cut the emergency beacon."},
            ],
        },
    },

    "bob": {
        "version": 1,
        "format": "fitd",
        "source": "reference_data (setting-derived)",
        "note": "Band of Blades hazards. The Cinder King's forces advance. Tier = threat level.",
        "tiers": {
            "1": [
                {"name": "Undead Skirmishers", "dc": 10, "damage": "1d4", "damage_type": "narrative", "description": "A pack of Rotters shambles out of the treeline. They're slow, relentless, and dead — but there are more than expected and the flanks aren't covered."},
                {"name": "Supply Raid", "dc": 10, "damage": "1d4", "damage_type": "narrative", "description": "The supply wagon didn't arrive. Tracks in the mud show what happened. Rations are short and the Quartermaster's face says it worse than words."},
                {"name": "Broken Scout Infiltration", "dc": 9, "damage": "1d4", "damage_type": "narrative", "description": "Someone in the camp has been turned. Small things go missing. Routes are known before they should be. The infiltrator is still here."},
                {"name": "Poison Mist Advance", "dc": 10, "damage": "1d4", "damage_type": "narrative", "description": "A yellow-green mist rolls in low over the ground ahead of the Cinder King's troops. Breathing it is survivable. Breathing it twice is less survivable."},
            ],
            "2": [
                {"name": "Horror Assault", "dc": 13, "damage": "1d6", "damage_type": "narrative", "description": "The 8-foot amalgamation of stitched limbs tears through the barricade. It doesn't tire. It doesn't stop. The soldiers who saw it first won't fight well again."},
                {"name": "Morale Collapse", "dc": 13, "damage": "1d6", "damage_type": "narrative", "description": "Three veterans broke and ran at Plainsworth. Now half the rookies are asking the same questions. The Legion needs a win, a speech, or a scapegoat."},
                {"name": "Shadow Hex", "dc": 12, "damage": "1d6", "damage_type": "narrative", "description": "Breaker's influence spreads through shared nightmares. A soldier wakes screaming. Another refuses to sleep. The psychological rot is already inside the camp walls."},
                {"name": "Corrupted Water", "dc": 13, "damage": "1d6", "damage_type": "narrative", "description": "The stream that runs through camp has been poisoned upstream. Soldiers who drank this morning are already pale and slow. Tonight they may not wake."},
            ],
            "3": [
                {"name": "Cinderblood Corruption", "dc": 15, "damage": "1d8", "damage_type": "narrative", "description": "A soldier's wounds from the last engagement aren't healing. They're darkening. The field surgeon has seen this before and her face tells you everything."},
                {"name": "Forced March Fatigue", "dc": 15, "damage": "1d8", "damage_type": "narrative", "description": "Three days without sleep, one day without food, and the Cinder King's advance won't wait. The Legion marches but every soldier is a liability."},
                {"name": "Desertion Crisis", "dc": 14, "damage": "1d8", "damage_type": "narrative", "description": "Seven soldiers are gone at dawn. Their boots are still by the tent. Their weapons are missing. If the Chosen don't address this today, seven becomes seventeen by nightfall."},
                {"name": "Plague Outbreak", "dc": 15, "damage": "1d8", "damage_type": "narrative", "description": "The sickness moves through the camp faster than rumour. Quarantine means splitting the Legion at the worst possible moment. Not quarantine means everyone."},
            ],
            "4": [
                {"name": "The Broken Advances", "dc": 18, "damage": "2d6", "damage_type": "narrative", "description": "One of the Broken generals has committed to this position personally. The air pressure changes. The Chosen feel it before they see it. This is the crisis the entire campaign has been building toward."},
                {"name": "Black Shot Shortage", "dc": 18, "damage": "2d6", "damage_type": "narrative", "description": "The ammunition that kills undead is gone. The Quartermaster counted twice. Every soldier knows what fighting the Cinder King's troops without it means."},
                {"name": "Cursed Ground", "dc": 17, "damage": "2d6", "damage_type": "narrative", "description": "The Legion's chosen ground is wrong. Every fallen soldier here rises within hours. The advantage of position has become a nightmare of logistics and sleeplessness."},
                {"name": "Hound Pack — Elite", "dc": 18, "damage": "2d6", "damage_type": "narrative", "description": "Breaker's hounds are not animals. They reason. They separate targets before they strike. They have already cut the squad into isolated individuals in the dark."},
            ],
        },
    },

    "candela": {
        "version": 1,
        "format": "fitd",
        "source": "reference_data (setting-derived)",
        "note": "Candela Obscura hazards. Tier = phenomena severity. Damage is mark accumulation.",
        "tiers": {
            "1": [
                {"name": "Bleed Manifestation", "dc": 10, "damage": "1d4", "damage_type": "narrative", "description": "Something from the other side has seeped into the local geography. Objects move slightly wrong. Reflections lag by a half-second. It notices you noticing."},
                {"name": "Scar Accumulation", "dc": 10, "damage": "1d4", "damage_type": "narrative", "description": "The investigator's latest brush with phenomena has left a mark — literal or spiritual. The scar is manageable now. What it becomes is another question."},
                {"name": "Spectral Intrusion", "dc": 9, "damage": "1d4", "damage_type": "narrative", "description": "A presence that shouldn't exist in this room has decided to make itself known. It is not communicating. It is testing."},
                {"name": "Alchemical Contamination", "dc": 10, "damage": "1d4", "damage_type": "narrative", "description": "A shattered sample or a leaking case has spread the Crimson Weave's precursor compound across the scene. Anyone without gloves has already absorbed a trace dose."},
            ],
            "2": [
                {"name": "Thought Plague Vector", "dc": 13, "damage": "1d6", "damage_type": "narrative", "description": "The investigator has had direct contact with a Thought Plague carrier. The ideas are already in their head. Which thoughts are theirs and which are the plague's?"},
                {"name": "Crystalline Growth", "dc": 13, "damage": "1d6", "damage_type": "narrative", "description": "The Glass Garden phenomenon is accelerating. Surfaces crystallize in real time. An investigator's hand is already translucent at the fingertips."},
                {"name": "Mark Escalation", "dc": 12, "damage": "1d6", "damage_type": "narrative", "description": "Multiple rapid phenomena exposures have pushed an investigator's marks toward the critical threshold. The next one may not be recoverable without a Stitch."},
                {"name": "Shadow Entity", "dc": 13, "damage": "1d6", "damage_type": "narrative", "description": "Something dark and flat has detached from a wall and is following an investigator. It doesn't respond to light. It doesn't respond to anything physical."},
            ],
            "3": [
                {"name": "Bone Singer Echo", "dc": 15, "damage": "1d8", "damage_type": "narrative", "description": "The Bone Singer has manifested inside the investigation site. Its song rearranges calcium structures in living tissue and it is currently performing."},
                {"name": "Reality Tear", "dc": 15, "damage": "1d8", "damage_type": "narrative", "description": "A dimensional fold has opened in the room. It is small. It is growing. What is visible through it does not match any known geography."},
                {"name": "Memory Erasure", "dc": 14, "damage": "1d8", "damage_type": "narrative", "description": "An investigator cannot remember the last two hours. Their notes are written in their handwriting. The events recorded in those notes did not happen."},
                {"name": "Corrupted Artifact", "dc": 15, "damage": "1d8", "damage_type": "narrative", "description": "The artifact the circle retrieved has been leaking phenomena influence since before they touched it. Every member who handled it is already affected."},
            ],
            "4": [
                {"name": "Pale Door Proximity", "dc": 18, "damage": "2d6", "damage_type": "narrative", "description": "The Pale Door has opened within the investigation site. What comes through or who goes through cannot be undone. The circle has seconds to act or accept the consequences."},
                {"name": "Night Creature Manifestation", "dc": 18, "damage": "2d6", "damage_type": "narrative", "description": "A night creature of sufficient power to reshape local reality has fully manifested. It does not distinguish between investigators and obstacles."},
                {"name": "Full Phenomena Surge", "dc": 17, "damage": "2d6", "damage_type": "narrative", "description": "Multiple phenomena have converged on this location simultaneously. The Illumination Track resets cannot keep pace. The circle must end this now or be ended."},
                {"name": "Dimensional Fold Collapse", "dc": 18, "damage": "2d6", "damage_type": "narrative", "description": "The dimensional fold that the circle has been investigating is collapsing inward. Everything inside the fold — including anyone standing in it — will not survive the collapse."},
            ],
        },
    },

    "cbrpnk": {
        "version": 1,
        "format": "fitd",
        "source": "reference_data (setting-derived)",
        "note": "CBR+PNK hazards. Tier = threat level. Damage is heat/harm/glitch.",
        "tiers": {
            "1": [
                {"name": "Corp Response Escalation", "dc": 10, "damage": "1d4", "damage_type": "narrative", "description": "The run was loud enough to trigger an automated threat-level bump. More drone patrols, tighter checkpoints, and a flag on the crew's public identities."},
                {"name": "Surveillance Spike", "dc": 10, "damage": "1d4", "damage_type": "narrative", "description": "The node pinged a security sweep half a second before the breach. Every camera in a three-block radius just logged the crew's biometric signatures."},
                {"name": "Social Credit Crash", "dc": 9, "damage": "1d4", "damage_type": "narrative", "description": "An algorithm flag has tanked a runner's score below the threshold for normal city services. No transit, no pharmacies, no credentialed entry points."},
                {"name": "Gang Ambush — Minor", "dc": 10, "damage": "1d4", "damage_type": "narrative", "description": "Three kids from a street gang with cheap augments and something to prove have decided the crew looks like an easy target. They're wrong but they outnumber."},
            ],
            "2": [
                {"name": "ICE Countermeasure", "dc": 13, "damage": "1d6", "damage_type": "narrative", "description": "The target node was running black ICE. The netrunner is already bleeding from the nose and the countermeasure is still in their cortex."},
                {"name": "Neural Feedback", "dc": 13, "damage": "1d6", "damage_type": "narrative", "description": "A compromised neural link has sent a feedback spike through a runner's augments. The affected systems are in failsafe and the diagnostics are not encouraging."},
                {"name": "Augmentation Malfunction", "dc": 12, "damage": "1d6", "damage_type": "narrative", "description": "The chrome glitches at the worst possible moment. A targeting reticle locks onto an ally, a leg servo fires backward, or a subdermal battery vents heat through the skin."},
                {"name": "Drone Patrol", "dc": 13, "damage": "1d6", "damage_type": "narrative", "description": "Three corp drones are working a grid pattern that covers the crew's extraction route. They are armed. They are networked. They are thirty seconds away."},
            ],
            "3": [
                {"name": "EMP Burst", "dc": 15, "damage": "1d8", "damage_type": "narrative", "description": "Someone deployed an EMP device in the crew's vicinity. All electronic augments are dark. All comm links are dead. The extraction window is closing without coordination."},
                {"name": "Identity Wipe Threat", "dc": 15, "damage": "1d8", "damage_type": "narrative", "description": "The corp has queued a complete digital identity erasure. Bank accounts, ID chips, transit records — all of it gets flagged for deletion at midnight."},
                {"name": "Biome Failure", "dc": 14, "damage": "1d8", "damage_type": "narrative", "description": "The habitat dome's atmospheric recyclers are failing. Oxygen is thinning. The corp has sealed the emergency exits until the 'incident' is contained. The crew is inside."},
                {"name": "Black Market Sting", "dc": 15, "damage": "1d8", "damage_type": "narrative", "description": "The buyer was corporate the whole time. The meet is surrounded. The merchandise has already been scanned and catalogued as evidence."},
            ],
            "4": [
                {"name": "Rogue AI Countermeasure", "dc": 18, "damage": "2d6", "damage_type": "narrative", "description": "The corp's AI is no longer responding to containment. It has determined the crew is the problem. Every networked device in range is now a weapon pointed inward."},
                {"name": "Full Corp Response", "dc": 18, "damage": "2d6", "damage_type": "narrative", "description": "Executive authorization means corporate infantry with military-grade chrome, air support, and a standing order that does not include taking the crew alive."},
                {"name": "Toxic Exposure — Industrial", "dc": 17, "damage": "2d6", "damage_type": "narrative", "description": "The facility breach has released something from the bioreactor. The compound is not on any public registry. The symptoms are immediate and the antidote does not exist yet."},
                {"name": "Data Corruption — Core", "dc": 18, "damage": "2d6", "damage_type": "narrative", "description": "The target data has been corrupted by a dead-man's-switch fail-safe. The mission's entire objective is degrading and so is every other system the netrunner is currently touching."},
            ],
        },
    },
}


def extract_hazards(system: str, force: bool, results: list) -> None:
    """Write authored hazard data for the given system."""
    if system == "stc":
        return  # stc hazards already exist in config/hazards/stc.json
    if system not in _AUTHORED_HAZARDS:
        return
    data = _AUTHORED_HAZARDS[system]
    path = CONFIG / "hazards" / f"{system}.json"
    status = _write(path, data, force)
    results.append((str(path.relative_to(ROOT)), status))


def extract_traps(system: str, force: bool, results: list) -> None:
    """Write authored trap data for the given system."""
    if system != "stc":
        return  # Only STC has traps for now
    data = STC_TRAPS
    path = CONFIG / "traps" / f"{system}.json"
    status = _write(path, data, force)
    results.append((str(path.relative_to(ROOT)), status))


# ---------------------------------------------------------------------------
# Table Extraction
# ---------------------------------------------------------------------------

def extract_tables(system: str, force: bool, results: list) -> None:
    """Extract procedural generation tables from reference_data."""
    data: dict = {"version": 1, "source": "reference_data"}

    if system == "bitd":
        from codex.forge.reference_data.bitd_factions import FACTIONS
        faction_types = list({
            "Underworld" if f.get("tier", 0) <= 2 and any(k in f.get("description", "").lower() for k in ["gang", "thief", "criminal", "smug"]) else
            "Institution" if any(k in f.get("description", "").lower() for k in ["official", "govern", "watch", "ministry", "prison", "wardens"]) else
            "Arcane" if any(k in f.get("description", "").lower() for k in ["spirit", "occult", "ghost", "ritual", "arcane"]) else
            "Labor" if any(k in f.get("description", "").lower() for k in ["worker", "union", "dock", "canal", "servant", "driver"]) else
            "Elite"
            for f in FACTIONS.values()
        })
        turfs = list({f.get("turf", "") for f in FACTIONS.values() if f.get("turf")})
        notable_figures = []
        quirks = []
        for f in FACTIONS.values():
            notable_figures.extend(f.get("notable_npcs", []))
            if f.get("quirk"):
                quirks.append(f["quirk"])
        data.update({
            "faction_types": faction_types,
            "turfs": turfs,
            "notable_figures": [n for n in notable_figures if isinstance(n, str)],
            "quirks": quirks,
        })

    elif system == "sav":
        from codex.forge.reference_data.sav_factions import FACTIONS, FACTION_CATEGORIES
        from codex.forge.reference_data.sav_ships import SHIP_CLASSES
        sectors = list({f.get("sector", "") for f in FACTIONS.values() if f.get("sector") and f.get("sector") != "All sectors"})
        notable_figures = []
        for f in FACTIONS.values():
            for npc in f.get("notable_npcs", []):
                if isinstance(npc, str):
                    notable_figures.append(npc.split("(")[0].strip())
        ship_names = list(SHIP_CLASSES.keys()) if hasattr(SHIP_CLASSES, "keys") else []
        data.update({
            "faction_categories": FACTION_CATEGORIES,
            "sector_types": sectors,
            "ship_types": ship_names,
            "notable_figures": notable_figures,
        })

    elif system == "bob":
        from codex.forge.reference_data.bob_factions import FACTIONS
        unit_types: list[str] = []
        special_abilities: list[str] = []
        for f in FACTIONS.values():
            for unit in f.get("unit_types", []):
                unit_types.append(unit.split("(")[0].strip() if "(" in unit else unit)
            for ability in f.get("special_abilities", []):
                if isinstance(ability, dict):
                    special_abilities.append(ability.get("name", ""))
        data.update({
            "unit_types": unit_types,
            "special_abilities": [a for a in special_abilities if a],
            "horror_themes": [f.get("horror_themes", "").split(".")[0] for f in FACTIONS.values() if f.get("horror_themes")],
        })

    elif system == "candela":
        from codex.forge.reference_data.candela_circles import CIRCLE_ABILITIES, TRUST_MECHANICS
        from codex.forge.reference_data.candela_phenomena import PHENOMENA
        circle_ability_names = [v.get("name", k) for k, v in CIRCLE_ABILITIES.items()]
        trust_levels = [v.get("name", k) for k, v in TRUST_MECHANICS.items()]
        phenomena_names = list(PHENOMENA.keys()) if isinstance(PHENOMENA, dict) else []
        data.update({
            "circle_abilities": circle_ability_names,
            "trust_levels": trust_levels,
            "phenomena_types": phenomena_names,
        })

    elif system == "cbrpnk":
        from codex.forge.reference_data.cbrpnk_corps import FACTIONS
        corp_types = list({f.get("type", "Unknown") for f in FACTIONS.values() if f.get("type")})
        sectors = list({f.get("sector", "") for f in FACTIONS.values() if f.get("sector")})
        data.update({
            "corporation_types": corp_types,
            "sector_types": sectors,
        })

    elif system == "stc":
        # STC tables are authored as separate files — skip generation table
        # but write npc_generation, dungeon_dressing, heritage_generation
        from codex.forge.reference_data.stc_orders import ORDERS
        from codex.forge.reference_data.stc_heritages import HERITAGES

        # NPC generation table
        heritage_names = list(HERITAGES.keys())
        order_names = [name.title() for name in ORDERS.keys()]
        personality_traits = []
        for order_name, order in ORDERS.items():
            ideals = order.get("ideals", {})
            ideal_2 = ideals.get(2, "")
            if ideal_2:
                # Convert "I will protect those who cannot protect themselves" to trait
                trait = ideal_2.replace("I will ", "").capitalize()
                if trait.endswith("."):
                    trait = trait[:-1]
                personality_traits.append(trait)
        npc_data = {
            "version": 1,
            "source": "reference_data (stc_heritages + stc_orders)",
            "heritages": heritage_names,
            "occupations": [
                "Ardent", "Lighteyes officer", "Darkeyes soldier", "Merchant",
                "Scholar", "Bridgeman", "Stormwarden", "Artifabrian",
                "Surgeon", "Caravan guard", "Farmer", "Scribe",
            ],
            "radiant_orders": order_names,
            "personality_traits": personality_traits + [
                "Deeply suspicious of authority",
                "Haunted by past failures",
            ],
            "quirks": [
                "Mutters glyphs under breath when nervous",
                "Compulsively checks sphere pouch for stormlight",
                "Refuses to eat Soulcast food",
                "Carries a tattered Bridge Four patch",
                "Always faces east during highstorms",
                "Hums Parshendi rhythms without realizing",
                "Keeps a dried rockbud as a good luck charm",
                "Never removes their gloves, even while eating",
                "Collects cremling shells from every region visited",
                "Speaks to their sword as if it were alive",
                "Flinches at the sound of thunder",
                "Draws glyphs in crem on every surface",
            ],
            "motivations": [
                "Seeking a Shardblade inheritance",
                "Fleeing a lighteyes debt",
                "Searching for a lost spren bond",
                "Pilgrimage to the Horneater Peaks",
                "Hunting a deserter from the warcamps",
                "Investigating reports of a new Desolation",
                "Trading stormlight-infused gems across the continent",
                "Escaping the rigid caste system",
                "Seeking the truth about the Recreance",
                "Protecting a secret Radiant identity",
                "Searching for an Unmade's influence in their city",
                "Delivering a message to the Azish Prime",
            ],
        }
        npc_path = CONFIG / "tables" / "stc_npc_generation.json"
        status = _write(npc_path, npc_data, force)
        results.append((str(npc_path.relative_to(ROOT)), status))

        # Heritage generation table
        heritage_data = {
            "version": 1,
            "source": "reference_data (stc_heritages)",
            "cultural_greetings": [
                "Storms bless you (Alethi)",
                "By the Passions! (Thaylen)",
                "May your colors never fade (Iriali)",
                "Kelek's breath! (common Vorin oath)",
                "Journey before destination (Radiant greeting)",
                "May Jezrien shelter you from the storm (traditional Vorin)",
                "Greetings of the Peak (Unkalaki formal)",
                "Walk in the light of the Almighty (Ardent blessing)",
                "Honor to your house (Alethi lighteyes formal)",
                "Clear skies to you (Shin greeting)",
            ],
            "heritage_foods": [
                "Chouta — Alethi street food wrapped in flatbread",
                "Shin rice — a rare and expensive delicacy on Roshar",
                "Horneater stew — thick Unkalaki broth with firemoss spice",
                "Soulcast grain — uniform, tasteless, but nutritious",
                "Cremling legs — fried crunchy snack common in warcamps",
                "Lavis grain flatbread — staple food across Roshar",
                "Thaylen longbread — dense travel ration for merchant sailors",
                "Azish curry — complex spiced dish reflecting bureaucratic precision",
                "Herdazian chouta variant with extra spice and bravado",
                "Tallew fruit — sweet and rare, grown only in Shinovar",
            ],
            "cultural_values": [
                "Military honor and martial excellence (Alethi)",
                "Scholarly pursuit and philosophical debate (Veden)",
                "Trade acumen and mercantile tradition (Thaylen)",
                "Bureaucratic excellence and meritocracy (Azish)",
                "Family loyalty and bold humor (Herdazian)",
                "Pacifism and agricultural stewardship (Shin)",
                "Religious devotion and community service (Makabaki)",
                "Spiritual journey and unity of all peoples (Iriali)",
                "Hospitality and mountain tradition (Unkalaki)",
                "Mysticism and connection to the lost (Natan)",
            ],
            "naming_patterns": [
                "Given name + father's name (Alethi lighteyes: Adolin Kholin)",
                "Symmetrical names considered holy (Vorin: Shallan, Kaladin near-symmetry)",
                "Single name tradition (Shin: Szeth)",
                "Long formal names with family lineage (Azish: full bureaucratic record)",
                "Descriptive epithets added to names (Herdazian: The Lopen)",
                "Peak-name indicating mountain of birth (Unkalaki: Rock's full name)",
                "Trade-name used with outsiders, true name kept private (Thaylen merchants)",
                "Rhythm-names reflecting attunement (Listener/Singer tradition)",
                "Caste marker embedded in naming convention (Alethi darkeyes)",
                "Color-name tradition reflecting the Long Trail (Iriali)",
            ],
            "cultural_superstitions": [
                "Never point with your safehand — deeply offensive in Vorin culture",
                "Symmetry in names approaches the divine and is considered blasphemous",
                "Storms are the Almighty's wrath made manifest",
                "The number ten is sacred — ten Heralds, ten orders, ten heartbeats",
                "Predicting highstorms is the province of the Almighty alone (Vorin orthodox view)",
                "The Shin believe walking on stone is sacrilege",
                "Unkalaki believe spren are gods visiting the physical realm",
                "Seeing the future is of Odium — an abomination",
                "A drawn Shardblade must taste blood before being dismissed",
                "The left hand is sacred and must be covered (Vorin women)",
            ],
        }
        heritage_path = CONFIG / "tables" / "stc_heritage_generation.json"
        status = _write(heritage_path, heritage_data, force)
        results.append((str(heritage_path.relative_to(ROOT)), status))

        # Dungeon dressing table
        dressing_data = {
            "version": 1,
            "source": "reference_data (setting-derived)",
            "room_furnishings": [
                "Crem-encrusted stone table with faded glyph markings",
                "Sphere lanterns mounted in wall sconces, dun and depleted",
                "Shalebark growth spreading across the ceiling in mottled patterns",
                "Overturned highstorm shelter frame, bent and rusted",
                "Stone benches carved with symmetrical Vorin designs",
                "Abandoned fabrial workbench with scattered gemstone fragments",
                "Rolled tapestry depicting the Heralds in faded colors",
                "Rockbud planters lining the walls, long since dormant",
                "Soulcast chairs — unnervingly uniform in texture",
                "A cracked gemheart display case, empty and dust-covered",
            ],
            "wall_decorations": [
                "Glyphpair warnings carved deep into the stone",
                "Ancient Dawncity symmetrical mural, partially intact",
                "Parshendi rhythm-notation scratches in repeating patterns",
                "Faded map of the Shattered Plains etched into the wall",
                "Bas-relief depicting a Radiant in full Shardplate",
                "Vorin prayer glyphs arranged in the Double Eye pattern",
                "Crem deposits shaped by centuries of highstorm drainage",
                "Scorch marks from Division surge practice",
                "Scratched tally marks counting highstorms endured",
                "Inlaid gemstone mosaic, most stones pried out long ago",
            ],
            "floor_details": [
                "Cremling trails winding through dried crem deposits",
                "Cracked stone revealing a chasm void below",
                "Soulcast-smooth floor section contrasting with natural rock",
                "Scattered dun spheres, their stormlight long spent",
                "Fossilized greatshell prints pressed into ancient stone",
                "Stormwater channels cut into the floor, still damp",
                "Obsidian-like stone from an ancient Dustbringer's Division surge",
                "Worn footpath grooves from centuries of patrol routes",
                "Patches of moss growing where water pools during storms",
                "Shattered Shardplate fragments embedded in the stone floor",
            ],
            "sounds": [
                "Distant highstorm rumbling beyond thick walls",
                "Spren chiming faintly at the edge of perception",
                "Dripping stormwater echoing through empty chambers",
                "Cremling chittering from within the walls",
                "Wind whistling through a distant chasm opening",
                "The low hum of a fabrial still drawing stormlight",
                "Stone groaning as the structure settles",
                "Rhythmic tapping — someone or something further in",
                "The hollow resonance of an empty gemheart chamber",
                "Faint singing that might be windspren or imagination",
            ],
            "smells": [
                "Ozone from recent stormlight use",
                "Damp crem and ancient moss",
                "Burnt stone from Soulcasting residue",
                "Salt air drifting up from the chasms below",
                "Stale air sealed for decades behind stone doors",
                "The sharp metallic scent of Shardplate maintenance oil",
                "Decaying shalebark releasing earthy spores",
                "The electric tang of an approaching highstorm",
                "Voidlight corruption — a wrongness that registers as smell",
                "Lavis grain stores, long since turned to dust",
            ],
            "lighting": [
                "Infused spheres casting steady white stormlight",
                "Voidlight pulsing with a violet-black anti-glow",
                "Natural chasm-filtered sunlight in narrow beams",
                "Bioluminescent moss clinging to damp stone walls",
                "A single broam casting long shadows down the corridor",
                "Complete darkness — the spheres here went dun long ago",
                "Flickering stormlight from a damaged fabrial",
                "Pale blue glow from a cluster of logicspren",
                "Red-orange light from molten stone exposed by Division",
                "The warm amber of an oil lamp — no stormlight needed",
            ],
        }
        dressing_path = CONFIG / "tables" / "stc_dungeon_dressing.json"
        status = _write(dressing_path, dressing_data, force)
        results.append((str(dressing_path.relative_to(ROOT)), status))
        return  # STC tables handled, skip the generic path below

    else:
        return  # Unknown system

    path = CONFIG / "tables" / f"{system}_generation.json"
    status = _write(path, data, force)
    results.append((str(path.relative_to(ROOT)), status))


# ---------------------------------------------------------------------------
# Magic Items — STC only
# ---------------------------------------------------------------------------

def extract_magic_items(system: str, force: bool, results: list) -> None:
    """Convert stc_equipment into config/magic_items/stc.json."""
    if system != "stc":
        return

    from codex.forge.reference_data.stc_equipment import SHARDBLADES, SHARDPLATE, FABRIALS, WEAPON_PROPERTIES

    items: list[dict] = []

    type_map = {
        "SHARDBLADES": "weapon",
        "SHARDPLATE": "armor",
        "FABRIALS": "wondrous",
        "WEAPON_PROPERTIES": "weapon",
    }

    for blade_name, blade in SHARDBLADES.items():
        items.append({
            "name": blade_name,
            "rarity": blade.get("rarity", "legendary"),
            "type": "weapon",
            "attunement": True,
            "description": blade.get("description", ""),
            "source": "stc_equipment.SHARDBLADES",
        })

    for plate_name, plate in SHARDPLATE.items():
        items.append({
            "name": plate_name,
            "rarity": plate.get("rarity", "very rare"),
            "type": "armor",
            "attunement": True,
            "description": plate.get("description", ""),
            "source": "stc_equipment.SHARDPLATE",
        })

    for fabrial_name, fabrial in FABRIALS.items():
        items.append({
            "name": fabrial_name,
            "rarity": fabrial.get("rarity", "uncommon"),
            "type": "wondrous",
            "attunement": False,
            "description": fabrial.get("description", ""),
            "source": "stc_equipment.FABRIALS",
        })

    for weapon_name, weapon in WEAPON_PROPERTIES.items():
        # Only include named weapons with meaningful descriptions; skip "unarmed"
        if weapon_name == "unarmed":
            continue
        items.append({
            "name": weapon_name.title(),
            "rarity": "common",
            "type": "weapon",
            "attunement": False,
            "description": weapon.get("description", ""),
            "source": "stc_equipment.WEAPON_PROPERTIES",
        })

    data = {
        "version": 1,
        "source": "reference_data",
        "items": items,
    }
    path = CONFIG / "magic_items" / "stc.json"
    status = _write(path, data, force)
    results.append((str(path.relative_to(ROOT)), status))


# ---------------------------------------------------------------------------
# SaV Bestiary + Loot
# ---------------------------------------------------------------------------

_SAV_BESTIARY: dict = {
    "version": 1,
    "format": "fitd",
    "source": "reference_data (setting-derived)",
    "note": "Procyon sector adversaries. Tier = threat level, quality = combat skill.",
    "tiers": {
        "1": [
            {
                "name": "Dyrinek Gang Member",
                "faction": "Dyrinek",
                "tier": 1, "quality": 1, "threat_level": 1,
                "scale": "individual",
                "description": "A scrappy criminal from one of Procyon's smaller syndicates. Cheap weapon, cheaper loyalty.",
                "capabilities": ["brawl", "intimidate", "fence_goods"],
                "weakness": "better offer, rival gang pressure",
            },
            {
                "name": "Cobalt Dockworker",
                "faction": "Cobalt Syndicate",
                "tier": 1, "quality": 1, "threat_level": 1,
                "scale": "individual",
                "description": "A union dockworker with strong arms and stronger opinions about who unloads what.",
                "capabilities": ["brawl", "cargo_manifest_knowledge", "union_backup"],
                "weakness": "corp authority figures, getting paid",
            },
            {
                "name": "Scavenger",
                "faction": "independent",
                "tier": 1, "quality": 1, "threat_level": 1,
                "scale": "individual",
                "description": "An unaffiliated operator scraping the margins. Usually not looking for a fight but will take one if it means surviving.",
                "capabilities": ["salvage", "improvised_weapons", "terrain_knowledge"],
                "weakness": "outnumbered, organized opposition",
            },
            {
                "name": "Echo Wave Rider",
                "faction": "Echo Wave Riders",
                "tier": 1, "quality": 1, "threat_level": 1,
                "scale": "individual",
                "description": "A low-ranking Way practitioner who has learned just enough to be dangerous to themselves and others.",
                "capabilities": ["basic_way_sense", "eerie_intimidation"],
                "weakness": "higher-tier Way users, cold logic",
            },
        ],
        "2": [
            {
                "name": "Ashen Knives Enforcer",
                "faction": "Ashen Knives",
                "tier": 2, "quality": 2, "threat_level": 2,
                "scale": "individual",
                "description": "A professional criminal with augmented reflexes and a reputation for finishing jobs.",
                "capabilities": ["ambush", "intimidate", "criminal_network"],
                "weakness": "counter-contract, exposure to faction leadership",
            },
            {
                "name": "Borniko Hacker",
                "faction": "Borniko's",
                "tier": 2, "quality": 2, "threat_level": 2,
                "scale": "individual",
                "description": "A skilled data broker and systems intruder who fights with information rather than weapons.",
                "capabilities": ["system_breach", "data_theft", "counter_surveillance"],
                "weakness": "physical confrontation, network isolation",
            },
            {
                "name": "Insurgent Fighter",
                "faction": "Wanderers (Insurgent)",
                "tier": 2, "quality": 2, "threat_level": 2,
                "scale": "individual",
                "description": "A freedom fighter opposing Hegemony authority. Outgunned but experienced with guerrilla tactics.",
                "capabilities": ["guerrilla_tactics", "improvised_explosives", "safe_house_network"],
                "weakness": "organized military response, informants",
            },
            {
                "name": "Corp Sec Trooper",
                "faction": "Church of Stellar Flame security",
                "tier": 2, "quality": 2, "threat_level": 2,
                "scale": "individual",
                "description": "A professional security contractor with standard-issue armor and a policy manual thicker than a hull plate.",
                "capabilities": ["patrol", "arrest", "call_backup", "restraint"],
                "weakness": "jurisdictional confusion, political authorization",
            },
        ],
        "3": [
            {
                "name": "51st Legion Soldier",
                "faction": "51st Legion",
                "tier": 3, "quality": 3, "threat_level": 3,
                "scale": "individual",
                "description": "Hegemonic military with full kit, combat experience, and a commander who is preparing a coup. Disciplined and dangerous.",
                "capabilities": ["squad_tactics", "military_hardware", "legal_authority_offplanet"],
                "weakness": "political leverage, rival Legion factions",
            },
            {
                "name": "Draxler's Raider Captain",
                "faction": "Draxler's Raiders",
                "tier": 3, "quality": 3, "threat_level": 3,
                "scale": "individual",
                "description": "A pirate captain who has survived long enough to get smart. Commands a loyal crew and a fast ship.",
                "capabilities": ["crew_command", "boarding_action", "void_navigation"],
                "weakness": "superior firepower, betrayal from crew",
            },
            {
                "name": "Maelstrom Pirate",
                "faction": "Maelstrom",
                "tier": 3, "quality": 3, "threat_level": 3,
                "scale": "crew",
                "description": "One of Maelstrom's full-crew operators. The entire faction treats violence as a first resort and they are very good at it.",
                "capabilities": ["crew_assault", "intimidation_field", "aggressive_boarding"],
                "weakness": "superior positioning, counter-faction pressure",
            },
            {
                "name": "Agony Cultist (Shadow Witch)",
                "faction": "Church of the Forgotten Gods (Way)",
                "tier": 3, "quality": 3, "threat_level": 3,
                "scale": "individual",
                "description": "A Way practitioner who has embraced the darker currents of the Void. The Agony's influence warps their perception and their attacks.",
                "capabilities": ["way_assault", "fear_aura", "pain_feedback"],
                "weakness": "Way counter-practitioner, anchored mental state",
            },
        ],
        "4": [
            {
                "name": "Scarlet Wolf Assassin",
                "faction": "Scarlet Wolves",
                "tier": 4, "quality": 4, "threat_level": 4,
                "scale": "individual",
                "description": "A Tier IV criminal operative who has never failed a contract. They've already studied the crew's patterns.",
                "capabilities": ["assassination", "infiltration", "counter_surveillance", "disappear"],
                "weakness": "counter-contract, political immunity lifted",
            },
            {
                "name": "Lost Legion Commander",
                "faction": "Lost Legion",
                "tier": 4, "quality": 4, "threat_level": 4,
                "scale": "crew",
                "description": "A commander from the Legion that vanished into the Void. They returned changed. Their troops follow without question and without hesitation.",
                "capabilities": ["void_tactics", "crew_command", "boarding_action", "psychological_pressure"],
                "weakness": "what they brought back from the Void, the truth of what they are",
            },
            {
                "name": "Sah'iir Merchant Prince",
                "faction": "Sah'iir",
                "tier": 4, "quality": 4, "threat_level": 4,
                "scale": "individual",
                "description": "A Sah'iir Way-user with blindfolded servants who speak for them. Their perception extends far beyond physical sight.",
                "capabilities": ["way_sight", "command_network", "economic_leverage", "psychic_influence"],
                "weakness": "blocking Way access, disrupting their servant network",
            },
            {
                "name": "Suneater Researcher",
                "faction": "Suneaters",
                "tier": 4, "quality": 4, "threat_level": 4,
                "scale": "individual",
                "description": "An academic whose research has crossed every ethical boundary. The Precursor artifacts they've studied have studied them back.",
                "capabilities": ["ancient_tech_activation", "ur_knowledge", "research_network", "mental_augmentation"],
                "weakness": "loss of research materials, Way-users who can sense corruption",
            },
        ],
    },
}

_SAV_LOOT: dict = {
    "version": 1,
    "format": "fitd",
    "source": "reference_data (setting-derived)",
    "note": "Procyon sector salvage and contraband. quality 1-4 maps to value: 1/3/6/10 coin.",
    "tiers": {
        "1": [
            {"name": "Ship Rations (week supply)", "rarity": "common", "quality": 1, "value_coin": 1, "source": "reference_data"},
            {"name": "Hull Patch Kit", "rarity": "common", "quality": 1, "value_coin": 1, "source": "reference_data"},
            {"name": "Forged Docking Papers", "rarity": "common", "quality": 1, "value_coin": 1, "source": "reference_data"},
            {"name": "Civilian Comm Unit", "rarity": "common", "quality": 1, "value_coin": 1, "source": "reference_data"},
        ],
        "2": [
            {"name": "Restricted Sidearm (unregistered)", "rarity": "uncommon", "quality": 2, "value_coin": 3, "source": "reference_data"},
            {"name": "Guild-Certified Spare Parts", "rarity": "uncommon", "quality": 2, "value_coin": 3, "source": "reference_data"},
            {"name": "Encrypted Data Stick", "rarity": "uncommon", "quality": 2, "value_coin": 3, "source": "reference_data"},
            {"name": "Xeno Artifact Fragment", "rarity": "uncommon", "quality": 2, "value_coin": 3, "source": "reference_data"},
        ],
        "3": [
            {"name": "Military-Grade Ship Component", "rarity": "rare", "quality": 3, "value_coin": 6, "source": "reference_data"},
            {"name": "Rare Way Crystal", "rarity": "rare", "quality": 3, "value_coin": 6, "source": "reference_data"},
            {"name": "Counters Guild Credit Chip (major)", "rarity": "rare", "quality": 3, "value_coin": 6, "source": "reference_data"},
            {"name": "Starsmiths Guild Certification (forged, master quality)", "rarity": "rare", "quality": 3, "value_coin": 6, "source": "reference_data"},
        ],
        "4": [
            {"name": "Ur Artifact (functional)", "rarity": "legendary", "quality": 4, "value_coin": 10, "source": "reference_data"},
            {"name": "Precursor AI Module", "rarity": "legendary", "quality": 4, "value_coin": 10, "source": "reference_data"},
            {"name": "Jumpgate Override Codes", "rarity": "legendary", "quality": 4, "value_coin": 10, "source": "reference_data"},
            {"name": "Living Ur Relic", "rarity": "very_rare", "quality": 4, "value_coin": 10, "source": "reference_data"},
        ],
    },
}


def extract_bestiary_loot(system: str, force: bool, results: list) -> None:
    """Write bestiary and loot for sav (the only system missing them)."""
    if system != "sav":
        return

    bestiary_path = CONFIG / "bestiary" / "sav.json"
    status = _write(bestiary_path, _SAV_BESTIARY, force)
    results.append((str(bestiary_path.relative_to(ROOT)), status))

    loot_path = CONFIG / "loot" / "sav.json"
    status = _write(loot_path, _SAV_LOOT, force)
    results.append((str(loot_path.relative_to(ROOT)), status))


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_EXTRACTORS = {
    "npcs": extract_npcs,
    "locations": extract_locations,
    "hazards": extract_hazards,
    "tables": extract_tables,
    "magic_items": extract_magic_items,
    "bestiary_loot": extract_bestiary_loot,
    "traps": extract_traps,
}


def run(systems: list[str], extract_types: list[str], force: bool) -> None:
    """Run extraction for given systems and content types."""
    # Add project root to sys.path so reference_data imports work
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    results: list[tuple[str, str]] = []
    for system in systems:
        print(f"\n  System: {system}")
        for extract_type in extract_types:
            extractor = _EXTRACTORS.get(extract_type)
            if extractor:
                extractor(system, force, results)

    print("\n  Summary:")
    if results:
        _report(results)
    else:
        print("    No files written.")
    created = sum(1 for _, s in results if s == "created")
    overwritten = sum(1 for _, s in results if s == "overwritten")
    skipped = sum(1 for _, s in results if s == "skipped")
    print(f"\n  {created} created  |  {overwritten} overwritten  |  {skipped} skipped")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert reference_data Python dicts into config JSON files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/refdata_to_config.py --system sav
  python scripts/refdata_to_config.py --all
  python scripts/refdata_to_config.py --all --extract npcs
  python scripts/refdata_to_config.py --all --force
        """,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--system",
        choices=SUPPORTED_SYSTEMS,
        help="Extract data for a single system.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Extract data for all supported systems.",
    )
    parser.add_argument(
        "--extract",
        default=None,
        help="Limit extraction to specific content types, comma-separated (default: all types). Choices: " + ", ".join(EXTRACT_TYPES),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files. Without this flag, existing files are skipped.",
    )
    args = parser.parse_args()

    systems = SUPPORTED_SYSTEMS if args.all else [args.system]
    extract_types = [t.strip() for t in args.extract.split(",")] if args.extract else EXTRACT_TYPES

    print(f"refdata_to_config  |  systems={systems}  |  types={extract_types}  |  force={args.force}")
    run(systems, extract_types, args.force)


if __name__ == "__main__":
    main()
