#!/usr/bin/env python3
"""
scripts/generate_module.py — Procedural Module Generator
==========================================================
Combines a system-agnostic template with system-specific content pools
to produce a complete, playable adventure module.

Usage:
    python scripts/generate_module.py --template heist --system bitd --tier 1
    python scripts/generate_module.py --template investigation --system candela --tier 2 --seed 42
    python scripts/generate_module.py --list-templates

Output: vault_maps/modules/{system}_{template}_{seed}/
    module_manifest.json
    {scene_id}.json  (one per scene)
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path

# Add project root to path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

_TEMPLATES_DIR = _ROOT / "config" / "templates"
_MODULES_DIR = _ROOT / "vault_maps" / "modules"

# Room type mappings by scene role
_ROLE_ROOM_TYPES = {
    "hub":      ["tavern", "market", "town_square"],
    "recon":    ["normal", "library", "residence"],
    "approach": ["normal", "corridor", "normal"],
    "boss":     ["boss", "treasure", "normal"],
    "debrief":  ["tavern", "market", "town_square"],
}

# Room types for dungeon topology
_DUNGEON_ROOM_TYPES = ["normal", "corridor", "treasure", "normal", "normal"]
_SETTLEMENT_ROOM_TYPES = ["tavern", "market", "forge", "temple", "residence", "library"]


def load_template(template_id: str) -> dict:
    """Load a template JSON from config/templates/."""
    path = _TEMPLATES_DIR / f"{template_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    return json.loads(path.read_text())


def list_templates() -> list:
    """List available template IDs."""
    if not _TEMPLATES_DIR.is_dir():
        return []
    return [p.stem for p in sorted(_TEMPLATES_DIR.glob("*.json"))]


def resolve_name(template_str: str, name_pools: dict, rng: random.Random) -> str:
    """Fill {placeholder} strings from name_pools."""
    result = template_str
    for key, pool in name_pools.items():
        placeholder = "{" + key + "}"
        if placeholder in result:
            result = result.replace(placeholder, rng.choice(pool))
    return result


def layout_rooms(room_count: int, topology: str, rng: random.Random) -> list:
    """Generate simple room positions as a connected chain.

    Returns list of dicts with x, y, width, height, connections.
    """
    rooms = []
    spacing_x = 14
    spacing_y = 14

    for i in range(room_count):
        if topology == "settlement":
            # Scatter around a central point
            angle_idx = i % 8
            radius = 1 if i == 0 else 2
            dx = [0, 1, 1, 0, -1, -1, -1, 0, 1][angle_idx]
            dy = [0, 0, 1, 1, 1, 0, -1, -1, -1][angle_idx]
            x = 20 + dx * spacing_x * radius
            y = 20 + dy * spacing_y * radius
        elif topology == "vertical":
            # Stack vertically (floors)
            x = 10
            y = 5 + i * spacing_y
        else:
            # Linear chain (dungeon default)
            x = 5 + i * spacing_x
            y = 10 + rng.randint(-3, 3)

        w = rng.randint(6, 10)
        h = rng.randint(6, 10)

        # Connections: linear chain
        connections = []
        if i > 0:
            connections.append(i - 1)
        if i < room_count - 1:
            connections.append(i + 1)

        rooms.append({
            "x": x, "y": y, "width": w, "height": h,
            "connections": connections,
        })

    return rooms


def pick_room_type(idx: int, total: int, scene: dict, topology: str, rng: random.Random) -> str:
    """Pick a RoomType value for a room."""
    hint = scene.get("room_type_hint")

    if idx == 0:
        if hint:
            return hint
        return "start" if topology == "dungeon" else "town_square"

    if idx == total - 1:
        role = scene.get("role", "")
        if role == "boss":
            return "boss"
        if topology == "settlement":
            return "town_gate"
        return "normal"

    if topology == "settlement":
        return rng.choice(_SETTLEMENT_ROOM_TYPES)
    return rng.choice(_DUNGEON_ROOM_TYPES)


def build_content_hints(scene: dict, pool, rng: random.Random,
                        room_idx: int, room_count: int, tier: int) -> dict:
    """Populate a room's content_hints from template slots + content pool."""
    hints: dict = {}

    # Description for entry room
    if room_idx == 0:
        locations = pool.get_locations()
        if locations:
            loc = rng.choice(locations)
            hints["description"] = loc.description
            hints["read_aloud"] = loc.description[:200]
        else:
            hints["description"] = "You arrive at a new location."

    # NPCs: required in room 0, optional spread across others
    npcs = []
    for slot in scene.get("npc_slots", []):
        if slot.get("required") and room_idx == 0:
            npc_list = pool.get_npcs(tier=tier, role=slot["role"], count=1)
            if npc_list:
                npcs.append(npc_list[0].to_scene_dict())
        elif not slot.get("required") and room_idx > 0:
            target = hash(slot.get("role", "")) % max(1, room_count - 1) + 1
            if room_idx == target:
                npc_list = pool.get_npcs(tier=tier, role=slot["role"], count=1)
                if npc_list:
                    npcs.append(npc_list[0].to_scene_dict())
    if npcs:
        hints["npcs"] = npcs

    # Enemies: place in later rooms (not room 0 for hubs)
    enemies = []
    if room_idx >= room_count // 2:
        for slot in scene.get("enemy_slots", []):
            if slot.get("is_boss") and room_idx == room_count - 1:
                boss = pool.get_boss(tier=tier)
                enemies.append(boss.to_scene_dict())
            elif not slot.get("is_boss"):
                count = slot.get("count", 1)
                for e in pool.get_enemies(tier=tier, count=count):
                    enemies.append(e.to_scene_dict())
    if enemies:
        hints["enemies"] = enemies

    # Loot: randomly distributed
    loot = []
    for slot in scene.get("loot_slots", []):
        target = rng.randint(0, room_count - 1)
        if room_idx == target:
            count = slot.get("count", 1)
            for item in pool.get_loot(tier=tier, count=count):
                loot.append(item.to_scene_dict())
    if loot:
        hints["loot"] = loot

    # Traps: middle rooms (not entry, not boss). Higher chance in defended rooms.
    is_boss_room = room_idx == room_count - 1
    has_enemies = bool(hints.get("enemies"))
    if room_idx > 0 and not is_boss_room:
        # Defended rooms (enemies present) are more likely to have traps
        trap_chance = 0.35 if has_enemies else 0.25
        if rng.random() < trap_chance:
            traps = pool.get_traps(tier=tier, count=1)
            if traps:
                hints["traps"] = traps

    # Table dressing: enrich room descriptions with a random dressing entry
    dressing_table = pool.get_table("dungeon_dressing")
    if dressing_table:
        # Shape 1: {"tables": {"sub_name": [{"roll": ..., "result": ...}, ...]}}
        sub_tables = dressing_table.get("tables", {})
        if sub_tables and isinstance(sub_tables, dict):
            sub = rng.choice(list(sub_tables.values()))
            if sub and isinstance(sub, list):
                entry = rng.choice(sub)
                dressing = entry.get("result", entry) if isinstance(entry, dict) else str(entry)
                hints["description"] = hints.get("description", "") + f" {dressing}".rstrip()
        # Shape 2: {"entries": [...]}
        elif dressing_table.get("entries"):
            entry = rng.choice(dressing_table["entries"])
            dressing = entry.get("result", entry) if isinstance(entry, dict) else str(entry)
            hints["description"] = hints.get("description", "") + f" {dressing}".rstrip()
        # Shape 3: flat named lists (e.g. noises/odors/general_features as string lists)
        else:
            flat_lists = [
                v for v in dressing_table.values()
                if isinstance(v, list) and v and isinstance(v[0], str)
            ]
            if flat_lists:
                chosen_list = rng.choice(flat_lists)
                dressing = rng.choice(chosen_list)
                hints["description"] = hints.get("description", "") + f" {dressing}".rstrip()

    # Location dressing for non-entry rooms without a description yet
    if room_idx > 0 and "description" not in hints and rng.random() < 0.5:
        locations = pool.get_locations()
        if locations:
            loc = rng.choice(locations)
            hints["description"] = loc.description

    # Services: room 0 only
    if room_idx == 0 and scene.get("services"):
        hints["services"] = list(scene["services"])

    # Event triggers: room 0 only
    if room_idx == 0 and scene.get("event_triggers"):
        hints["event_triggers"] = list(scene["event_triggers"])

    return hints


def generate_scene_blueprint(scene: dict, template: dict, pool,
                             rng: random.Random, base_tier: int) -> dict:
    """Generate a single zone blueprint JSON from a scene template."""
    seed = rng.randint(1000, 99999)
    tier_offset = scene.get("tier_offset", 0)
    scene_tier = max(1, min(4, base_tier + tier_offset))
    topology = scene.get("topology", "dungeon")
    room_count = scene.get("room_count", 4)

    display_name = resolve_name(
        scene.get("display_name_template", scene["scene_id"]),
        template.get("name_pools", {}),
        rng,
    )

    room_layouts = layout_rooms(room_count, topology, rng)

    rooms = {}
    for i in range(room_count):
        room_type = pick_room_type(i, room_count, scene, topology, rng)
        layout = room_layouts[i]
        content_hints = build_content_hints(scene, pool, rng, i, room_count, scene_tier)

        rooms[str(i)] = {
            "id": i,
            "x": layout["x"],
            "y": layout["y"],
            "width": layout["width"],
            "height": layout["height"],
            "room_type": room_type,
            "connections": layout["connections"],
            "tier": scene_tier,
            "is_locked": False,
            "is_secret": False,
            "content_hints": content_hints,
        }

    return {
        "seed": seed,
        "width": 80,
        "height": 80,
        "start_room_id": 0,
        "metadata": {
            "zone_id": scene["scene_id"],
            "theme": pool.get_system_theme(),
            "topology": topology,
            "display_name": display_name,
        },
        "rooms": rooms,
    }


def generate_module(template_id: str, system_id: str, tier: int = 1,
                    seed: int | None = None, output_dir: str | None = None,
                    name: str | None = None, dry_run: bool = False) -> str:
    """Generate a complete module from template + content pool.

    Returns the output directory path.
    """
    from codex.forge.content_pool import ContentPool

    if seed is None:
        seed = random.randint(10000, 99999)
    rng = random.Random(seed)

    template = load_template(template_id)
    pool = ContentPool(system_id, seed=seed)

    module_id = f"{system_id}_{template_id}_{seed}"
    base_dir = Path(output_dir) if output_dir else _MODULES_DIR
    module_dir = base_dir / module_id

    if dry_run:
        print(f"DRY RUN: Would generate module at {module_dir}")
        print(f"  Template: {template_id} ({template['display_name']})")
        print(f"  System:   {system_id}")
        print(f"  Tier:     {tier}")
        print(f"  Seed:     {seed}")
        print(f"  Scenes:   {len(template['scenes'])}")
        for scene in template["scenes"]:
            print(f"    - {scene['scene_id']} ({scene['topology']}, "
                  f"tier {tier + scene.get('tier_offset', 0)})")
        return str(module_dir)

    # Generate blueprints
    blueprints = {}
    for scene in template["scenes"]:
        bp = generate_scene_blueprint(scene, template, pool, rng, tier)
        blueprints[scene["scene_id"]] = bp

    # Build chapters from template
    from codex.spatial.module_manifest import ModuleManifest, Chapter, ZoneEntry

    chapters = []
    for ci, ch_def in enumerate(template["chapter_structure"], 1):
        zones = []
        for scene_id in ch_def["scenes"]:
            bp = blueprints[scene_id]
            zones.append(ZoneEntry(
                zone_id=scene_id,
                blueprint=f"{scene_id}.json",
                topology=bp["metadata"]["topology"],
                theme=bp["metadata"]["theme"],
                exit_trigger="boss_defeated" if scene_id == template["scenes"][-1]["scene_id"] else "scene_complete",
            ))
        chapters.append(Chapter(
            chapter_id=ch_def["chapter_id"],
            display_name=ch_def["display_name"],
            order=ci,
            zones=zones,
        ))

    display_name = name or f"{pool.get_display_name()}: {template['display_name']}"
    manifest = ModuleManifest(
        module_id=module_id,
        display_name=display_name,
        system_id=system_id,
        source_type="generated",
        starting_location=template["scenes"][0]["scene_id"],
        recommended_levels={"min": tier, "max": min(4, tier + 2)},
        chapters=chapters,
    )

    # Write files
    module_dir.mkdir(parents=True, exist_ok=True)
    for scene_id, bp in blueprints.items():
        bp_path = module_dir / f"{scene_id}.json"
        bp_path.write_text(json.dumps(bp, indent=2))

    manifest.save(str(module_dir / "module_manifest.json"))

    print(f"Module generated: {module_dir}")
    print(f"  ID:       {module_id}")
    print(f"  Name:     {display_name}")
    print(f"  System:   {system_id}")
    print(f"  Tier:     {tier}")
    print(f"  Seed:     {seed}")
    print(f"  Chapters: {len(chapters)}")
    print(f"  Scenes:   {len(blueprints)}")
    total_rooms = sum(len(bp["rooms"]) for bp in blueprints.values())
    total_npcs = sum(
        len(r.get("content_hints", {}).get("npcs", []))
        for bp in blueprints.values()
        for r in bp["rooms"].values()
    )
    total_enemies = sum(
        len(r.get("content_hints", {}).get("enemies", []))
        for bp in blueprints.values()
        for r in bp["rooms"].values()
    )
    print(f"  Rooms:    {total_rooms}")
    print(f"  NPCs:     {total_npcs}")
    print(f"  Enemies:  {total_enemies}")

    return str(module_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a playable adventure module from a template."
    )
    parser.add_argument("--template", "-t", help="Template ID (e.g. heist, investigation)")
    parser.add_argument("--system", "-s", help="System ID (e.g. bitd, dnd5e, candela)")
    parser.add_argument("--tier", type=int, default=1, help="Base difficulty tier 1-4 (default: 1)")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed for reproducibility")
    parser.add_argument("--output-dir", "-o", default=None, help="Output base directory")
    parser.add_argument("--name", "-n", default=None, help="Custom module display name")
    parser.add_argument("--list-templates", action="store_true", help="List available templates")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without writing files")

    args = parser.parse_args()

    if args.list_templates:
        templates = list_templates()
        if templates:
            print("Available templates:")
            for t in templates:
                try:
                    data = load_template(t)
                    print(f"  {t}: {data.get('display_name', t)} — {data.get('description', '')}")
                except Exception:
                    print(f"  {t}: (error loading)")
        else:
            print("No templates found in config/templates/")
        return

    if not args.template or not args.system:
        parser.error("--template and --system are required")

    generate_module(
        template_id=args.template,
        system_id=args.system,
        tier=args.tier,
        seed=args.seed,
        output_dir=args.output_dir,
        name=args.name,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
