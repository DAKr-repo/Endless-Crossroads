#!/usr/bin/env python3
"""
Burnwillow Discord Embed Translation
=====================================
Converts Paper Doll character sheets to Discord embeds.

Author: Codex Designer
Companion to: burnwillow_paper_doll.py
"""

from typing import Dict, List, Optional
from codex.games.burnwillow.paper_doll import Character, GearItem


def render_dice_pips_discord(count: int, max_pips: int = 5) -> str:
    """
    Render dice pips for Discord (emoji-based).

    Args:
        count: Number of filled pips
        max_pips: Total pips to display

    Returns:
        String with Unicode pips
    """
    filled = "🟢" * min(count, max_pips)
    empty = "⚫" * (max_pips - count)
    return f"`[{filled}{empty}]`"


def render_hp_bar_discord(current: int, maximum: int, width: int = 10) -> str:
    """
    Render HP bar for Discord using Unicode blocks.

    Args:
        current: Current HP
        maximum: Max HP
        width: Bar width

    Returns:
        Discord-formatted HP bar
    """
    percent = max(0, min(1, current / maximum))
    filled = int(width * percent)
    empty = width - filled

    # Choose emoji based on HP threshold
    if percent > 0.6:
        fill_char = "🟦"  # Cyan-ish
    elif percent > 0.3:
        fill_char = "🟨"  # Yellow
    else:
        fill_char = "🟥"  # Red

    empty_char = "⬛"

    return f"`{fill_char * filled}{empty_char * empty}` **{current}/{maximum}**"


def render_doom_pips_discord(doom: int, max_doom: int = 10) -> str:
    """
    Render doom counter for Discord.

    Args:
        doom: Current doom level
        max_doom: Maximum doom

    Returns:
        Discord-formatted doom pips
    """
    filled = "🔴" * min(doom, max_doom)
    empty = "⚫" * (max_doom - doom)
    return f"`{filled}{empty}`"


def character_to_discord_embed(character: Character) -> Dict:
    """
    Convert Character to Discord embed JSON.

    Args:
        character: Character object from burnwillow_paper_doll

    Returns:
        Discord embed dict (ready for discord.py or API)
    """
    # Calculate derived values
    hp_max = character.stats.hp_max
    defense = character.stats.defense
    dice_pool = character.calculate_dice_pool()

    # Build equipment list
    equipment_fields = []

    slots = [
        ("🎩 Head", character.head),
        ("🧥 Shoulders", character.shoulders),
        ("📿 Neck", character.neck),
        ("👕 Chest", character.chest),
        ("🦾 Arms", character.arms),
        ("👖 Legs", character.legs),
        ("🗡️ Right Hand", character.right_hand),
        ("🛡️ Left Hand", character.left_hand),
        ("💍 Right Ring", character.right_ring),
        ("💎 Left Ring", character.left_ring),
    ]

    for slot_name, item in slots:
        if item:
            value = f"**{item.name}** {render_dice_pips_discord(item.dice_contribution)}"
        else:
            value = f"*Empty* {render_dice_pips_discord(0)}"

        equipment_fields.append({
            "name": slot_name,
            "value": value,
            "inline": True
        })

    # Build stats block
    stats_text = (
        f"**MIGHT:** {character.stats.might} `({character.stats.might_mod:+d})`\n"
        f"**WITS:** {character.stats.wits} `({character.stats.wits_mod:+d})`\n"
        f"**GRIT:** {character.stats.grit} `({character.stats.grit_mod:+d})`\n"
        f"**AETHER:** {character.stats.aether} `({character.stats.aether_mod:+d})`\n"
    )

    # Build dice pool display
    dice_pool_text = f"{render_dice_pips_discord(dice_pool)} **{dice_pool}d6**"

    # Embed color (Decay Green)
    embed_color = 0x2D5016  # DECAY_GREEN in hex

    # Construct full embed
    embed = {
        "title": f"⚙️ {character.name.upper()} ⚙️",
        "description": f"*\"{character.title}\"*",
        "color": embed_color,
        "fields": [
            {
                "name": "❤️ HP",
                "value": render_hp_bar_discord(character.hp_current, hp_max),
                "inline": True
            },
            {
                "name": "🛡️ Defense",
                "value": f"`{defense}`",
                "inline": True
            },
            {
                "name": "💀 Doom",
                "value": render_doom_pips_discord(character.doom),
                "inline": False
            },
            {
                "name": "📊 Stats",
                "value": stats_text,
                "inline": False
            },
            {
                "name": "🎲 Dice Pool",
                "value": dice_pool_text,
                "inline": False
            },
            {
                "name": "═══════════════════",
                "value": "**EQUIPMENT**",
                "inline": False
            }
        ] + equipment_fields,
        "footer": {
            "text": "Burnwillow • Bioluminescent Decay"
        }
    }

    return embed


def render_condition_icons_discord(conditions) -> str:
    """Render condition icons for Discord embeds.

    Accepts list of Condition objects or dicts (from ConditionTracker.to_dict()).
    Returns emoji string suitable for Discord embed field.
    """
    if not conditions:
        return ""
    try:
        from codex.core.mechanics.conditions import (
            format_condition_icons, Condition, ConditionType,
        )
    except ImportError:
        return ""

    # If list of dicts (serialised), convert to Condition objects
    parts = []
    for c in conditions:
        if isinstance(c, dict):
            try:
                ctype = ConditionType(c.get("type", ""))
                from codex.core.mechanics.conditions import CONDITION_ICONS
                icon = CONDITION_ICONS.get(ctype, "\u2753")
                parts.append(f"{icon}{ctype.value}")
            except (ValueError, KeyError):
                parts.append(f"\u2753{c.get('type', '?')}")
        else:
            # Assume Condition object
            from codex.core.mechanics.conditions import CONDITION_ICONS
            icon = CONDITION_ICONS.get(c.condition_type, "\u2753")
            parts.append(f"{icon}{c.condition_type.value}")
    return " ".join(parts)


def character_to_discord_embed_compact(character: Character, conditions=None) -> Dict:
    """
    Compact version for quick status checks (fewer fields).

    Args:
        character: Character object

    Returns:
        Minimal Discord embed
    """
    hp_max = character.stats.hp_max
    defense = character.stats.defense
    dice_pool = character.calculate_dice_pool()

    # Count equipped items
    equipped_count = sum([
        1 for slot in [
            character.head, character.shoulders, character.chest,
            character.arms, character.legs, character.right_hand,
            character.left_hand, character.right_ring, character.left_ring,
            character.neck
        ] if slot is not None
    ])

    embed = {
        "title": f"⚙️ {character.name.upper()}",
        "description": f"*\"{character.title}\"*",
        "color": 0x2D5016,
        "fields": [
            {
                "name": "❤️ HP",
                "value": render_hp_bar_discord(character.hp_current, hp_max),
                "inline": False
            },
            {
                "name": "🛡️ DEF | 🎲 Dice Pool | 💀 Doom",
                "value": (
                    f"`{defense}` | "
                    f"{render_dice_pips_discord(dice_pool)} `{dice_pool}d6` | "
                    f"`{character.doom}/10`"
                ),
                "inline": False
            },
            {
                "name": "\u2699\ufe0f Equipment",
                "value": f"`{equipped_count}/10` slots filled",
                "inline": False
            }
        ],
        "footer": {
            "text": "Use /sheet for full details"
        }
    }

    # WO-V35.0: Add status effects field if conditions present
    if conditions:
        icons = render_condition_icons_discord(conditions)
        if icons:
            embed["fields"].append({
                "name": "\U0001f9ea Status Effects",
                "value": icons,
                "inline": False,
            })

    return embed


# === DEMO ===
if __name__ == "__main__":
    import json
    from burnwillow_paper_doll import CharacterStats

    # Sample character
    stats = CharacterStats(might=14, wits=12, grit=16, aether=10)
    sample = Character(
        name="Moss",
        title="The Wanderer",
        hp_current=12,
        stats=stats,
        doom=3,
        chest=GearItem(name="Bark Jerkin", tier=1, dice_contribution=1),
        legs=GearItem(name="Thornwalker Boots", tier=2, dice_contribution=2),
        right_hand=GearItem(name="Sap Cudgel", tier=2, dice_contribution=2),
        left_hand=GearItem(name="Scrap Shield", tier=1, dice_contribution=1)
    )

    # Generate full embed
    full_embed = character_to_discord_embed(sample)
    print("=== FULL EMBED JSON ===")
    print(json.dumps(full_embed, indent=2))

    print("\n" + "="*50 + "\n")

    # Generate compact embed
    compact_embed = character_to_discord_embed_compact(sample)
    print("=== COMPACT EMBED JSON ===")
    print(json.dumps(compact_embed, indent=2))
