#!/usr/bin/env python3
"""
ASHBURN TAROT CARD SYSTEM
-------------------------
Institutional Tarot aesthetics for narrative prompt display.

Five symbolic cards map to game event types:
- Crown → Sun Ring (institutional power)
- Crew → Registry Key (hidden knowledge)
- Campfire → Dead Tree (endurance)
- World → Wolf (hidden threat)
- Legacy → Moon (concealment)

All art is terminal-safe ASCII using standard box-drawing characters.
"""

from rich.console import Console
from rich.panel import Panel
from rich import box
import textwrap

# =============================================================================
# TAROT CARD DATA
# =============================================================================

TAROT_CARDS = {
    "sun_ring": {
        "title": "THE SUN RING",
        "symbol": "☀",
        "art": """       ╔═══╗
      ╔╝   ╚╗
     ╔╝     ╚╗
     ║   ☀   ║
     ╚╗     ╔╝
      ╚╗   ╔╝
       ╚═══╝""",
        "border_color": "#DAA520",  # Dark goldenrod
        "title_color": "#FFD700",   # Gold
        "context": "crown",
        "meaning": "Power that burns. The gilded cage. Authority's radiance."
    },

    "registry_key": {
        "title": "THE REGISTRY KEY",
        "symbol": "🗝",
        "art": """     ╔═══════════╗
     ║  ┌─────┐  ║
     ║  └─────┘  ║
     ╚═════╤═════╝
           │
      ╔════╪════╗
      ║ ╔══╧══╗ ║
      ╚═╝     ╚═╝""",
        "border_color": "grey50",
        "title_color": "#CD853F",   # Peru/Ember
        "context": "crew",
        "meaning": "What unlocks also imprisons. The weight of truth."
    },

    "dead_tree": {
        "title": "THE DEAD TREE",
        "symbol": "🌲",
        "art": """       ╱│╲
      ╱ │ ╲
     ╱  │  ╲
    │  ╱╲  │
    │ ╱  ╲ │
     ╱    ╲
    │      │
    │      │
    └──────┘""",
        "border_color": "#556B2F",  # Dark olive
        "title_color": "grey70",
        "context": "campfire",
        "meaning": "Bare survival. Gnarled defiance. What endured."
    },

    "wolf": {
        "title": "THE WOLF",
        "symbol": "🐺",
        "art": """         ╱╲
        ╱  ╲╲
       │ ●  ││
       │    ╱╱
        ╲  ╱
      ╱╱ ╲╱╲╲
     ││  │  ││
     ╰╯  ╰  ╰╯""",
        "border_color": "#4B0082",  # Indigo
        "title_color": "#8B0000",   # Dark red
        "context": "world",
        "meaning": "Hidden danger. Transformation. Something watches."
    },

    "moon": {
        "title": "THE MOON",
        "symbol": "🌑",
        "art": """         ╔══╗
        ╔╝  ║
       ╔╝   ║
       ║    ║
       ╚╗   ║
        ╚╗  ║
         ╚══╝""",
        "border_color": "#191970",  # Midnight blue
        "title_color": "#C0C0C0",   # Silver
        "context": "legacy",
        "meaning": "Concealment. Eclipse. What the school hides."
    }
}


# =============================================================================
# RENDERING FUNCTION
# =============================================================================

def render_tarot_card(
    card_key: str,
    prompt_text: str,
    custom_title: str | None = None,
    width: int = 40
) -> Panel:
    """
    Render a game prompt inside a vertical Tarot card frame.

    Args:
        card_key: Key from TAROT_CARDS dict (sun_ring, registry_key, dead_tree, wolf, moon)
        prompt_text: The narrative text to display in the card body
        custom_title: Override the card's default title (optional)
        width: Panel width (default 40)

    Returns:
        Rich Panel object ready for console.print()

    Example:
        >>> card = render_tarot_card("sun_ring", "The Board convenes.")
        >>> console.print(card)
    """
    # Look up card data
    if card_key not in TAROT_CARDS:
        # Fallback to plain panel if card not found
        return Panel(
            prompt_text,
            title=f"[bold]{custom_title or 'UNKNOWN CARD'}[/bold]",
            border_style="grey50",
            box=box.HEAVY,
            width=width,
            padding=(1, 1)
        )

    card = TAROT_CARDS[card_key]

    # Build card content
    # Line 1: Card title (centered, styled)
    title_line = f"[{card['title_color']}]═══ {card['title']} ═══[/]"

    # Line 2: ASCII art (centered)
    art_lines = card['art']

    # Line 3: Prompt text (word-wrapped to fit width - 4 for padding)
    wrap_width = width - 4
    wrapped_prompt = textwrap.fill(prompt_text, width=wrap_width)

    # Assemble content
    content_parts = [
        title_line,
        "",
        f"[dim]{art_lines}[/]",
        "",
        f"[italic]{wrapped_prompt}[/italic]"
    ]

    card_content = "\n".join(content_parts)

    # Wrap in Rich Panel
    return Panel(
        card_content,
        box=box.HEAVY,
        border_style=card['border_color'],
        title=custom_title if custom_title else None,
        width=width,
        padding=(1, 1)
    )


def get_card_for_context(context: str) -> str:
    """
    Map a game context to the appropriate tarot card key.

    Args:
        context: One of "crown", "crew", "campfire", "world", "legacy"

    Returns:
        Card key string for use with render_tarot_card()

    Example:
        >>> key = get_card_for_context("crown")
        >>> card = render_tarot_card(key, "The Board convenes.")
    """
    context_map = {
        "crown": "sun_ring",
        "crew": "registry_key",
        "campfire": "dead_tree",
        "world": "wolf",
        "legacy": "moon"
    }

    return context_map.get(context.lower(), "moon")


def format_tarot_text(card_key: str, prompt_text: str, width: int = 40) -> str:
    """Render a tarot card as plain text for Discord/Telegram bots.

    Returns a box-drawn card string without Rich markup, suitable for
    wrapping in a code block (```).

    Args:
        card_key: Key from TAROT_CARDS dict
        prompt_text: The narrative text to display in the card body
        width: Character width of the card (default 40)

    Returns:
        Plain text string with box-drawing characters
    """
    if card_key not in TAROT_CARDS:
        return prompt_text
    card = TAROT_CARDS[card_key]
    border = "═" * (width - 2)
    lines = [
        f"╔{border}╗",
        f"║ {card['symbol']} {card['title']} {card['symbol']}".ljust(width - 1) + "║",
        f"╠{border}╣",
    ]
    for art_line in card['art'].strip().split('\n'):
        lines.append(f"║ {art_line}".ljust(width - 1) + "║")
    lines.append(f"╠{border}╣")
    for text_line in textwrap.wrap(prompt_text, width - 4):
        lines.append(f"║ {text_line}".ljust(width - 1) + "║")
    lines.append(f"╚{border}╝")
    return "\n".join(lines)


# =============================================================================
# INTEGRATION TEST
# =============================================================================

if __name__ == "__main__":
    console = Console()

    console.print("\n[bold gold1]═══ ASHBURN TAROT CARD SYSTEM ═══[/bold gold1]\n")

    # Test each card with sample prompts
    test_prompts = {
        "sun_ring": "The Board of Regents convenes behind mirrored glass. Their agenda: control.",
        "registry_key": "A note slides under your door: 'The Furnace. Midnight. Bring no light.'",
        "dead_tree": "In the boiler room beneath the chapel, someone has left a candle burning.",
        "wolf": "The Lunar Filter bathes the courtyard in pale silver. Nothing feels real here.",
        "moon": "LEGACY CALL: Headmaster Alaric demands intel on the Crew."
    }

    for card_key, prompt in test_prompts.items():
        card = render_tarot_card(card_key, prompt)
        console.print(card)
        console.print()

    console.print("[dim]All 5 cards rendered successfully.[/dim]")
    console.print()
