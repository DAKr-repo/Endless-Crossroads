"""
Quest Reward Materializer
=========================

Converts quest reward dicts into concrete game effects with setting-aware
currency names and material flavors. Extensible per-setting via
SETTING_MATERIAL_PALETTES.
"""

from __future__ import annotations

from typing import Dict, Any


# -------------------------------------------------------------------------
# Setting Material Palettes — keyed by setting_id, then by tier
# -------------------------------------------------------------------------

SETTING_MATERIAL_PALETTES: Dict[str, Dict[int, Dict[str, str]]] = {
    "burnwillow": {
        1: {"currency": "bark-chips", "material": "Scrap"},
        2: {"currency": "amber-shards", "material": "Ironbark"},
        3: {"currency": "heartwood-coins", "material": "Heartwood"},
        4: {"currency": "sunresin-tokens", "material": "Ambercore"},
    },
    "roshar": {
        1: {"currency": "chips", "material": "Crem-forged"},
        2: {"currency": "marks", "material": "Stormlight-tempered"},
        3: {"currency": "broams", "material": "Shardplate-fragment"},
        4: {"currency": "perfect gems", "material": "Radiant-forged"},
    },
}

# Default fallback palette for unknown settings
_DEFAULT_PALETTE: Dict[int, Dict[str, str]] = {
    1: {"currency": "coins", "material": "Common"},
    2: {"currency": "coins", "material": "Uncommon"},
    3: {"currency": "coins", "material": "Rare"},
    4: {"currency": "coins", "material": "Legendary"},
}


def materialize_reward(
    reward_dict: dict,
    setting_id: str = "",
    tier: int = 1,
) -> Dict[str, Any]:
    """Convert a quest reward template into concrete rewards with setting flavor.

    Args:
        reward_dict: Raw reward from Quest.reward_text ({"gold": int, "item": str, "description": str}).
        setting_id: Setting identifier for currency/material flavor.
        tier: Dungeon tier (1-4) for scaling.

    Returns:
        {"gold": int, "item_name": str, "item_desc": str, "currency_name": str, "message": str}
    """
    palette = SETTING_MATERIAL_PALETTES.get(setting_id, _DEFAULT_PALETTE)
    tier_data = palette.get(tier, palette.get(1, {"currency": "coins", "material": "Common"}))

    gold = reward_dict.get("gold", 0)
    item_name = reward_dict.get("item", "")
    item_desc = reward_dict.get("description", "")
    currency_name = tier_data["currency"]

    parts = []
    if gold:
        parts.append(f"{gold} {currency_name}")
    if item_name:
        parts.append(item_name)

    message = "Reward: " + ", ".join(parts) if parts else "No reward."

    return {
        "gold": gold,
        "item_name": item_name,
        "item_desc": item_desc,
        "currency_name": currency_name,
        "material": tier_data["material"],
        "message": message,
    }


def format_reward_panel(reward: dict) -> str:
    """Format a reward dict into a Rich-compatible display string."""
    parts = []
    if reward.get("gold"):
        parts.append(f"[yellow]{reward['gold']} {reward.get('currency_name', 'gold')}[/]")
    if reward.get("item_name"):
        parts.append(f"[bold cyan]{reward['item_name']}[/]")
        if reward.get("item_desc"):
            parts.append(f"[dim]{reward['item_desc']}[/]")
    return " | ".join(parts) if parts else "[dim]No reward.[/]"
