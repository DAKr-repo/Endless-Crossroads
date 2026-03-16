"""
codex/core/sheet_renderer.py - Character Sheet Renderer
========================================================

Rich terminal renderers for all 9 game system character sheets.
Each system gets a faithful representation of its paper sheet using
Rich Panels, Tables, Layouts, and styled Text.

Router: render_sheet(engine, system_id, width) -> Panel
"""

from typing import Any, Dict, List, Optional, Tuple

from rich.console import Group
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box


# =========================================================================
# COLOR PALETTES (3 colors each: accent, secondary, border)
# =========================================================================

_PALETTES = {
    "dnd5e":     ("#DAA520", "#F5E6C8", "#DAA520"),   # gold / parchment / gold
    "stc":       ("#4169E1", "#FFB347", "#4169E1"),    # blue / amber / blue
    "bitd":      ("#E8A317", "#36454F", "#36454F"),    # amber / charcoal / charcoal
    "sav":       ("#00FF7F", "#7B68EE", "#7B68EE"),    # neon green / nebula / nebula
    "bob":       ("#6B8E23", "#800020", "#6B8E23"),    # olive / burgundy / olive
    "cbrpnk":    ("#FF1493", "#00FFFF", "#FF1493"),    # hot pink / cyan / pink
    "candela":   ("#C5A55A", "#4A0E4E", "#4A0E4E"),    # tarnished gold / purple / purple
    "crown":     ("#8B0000", "#FFD700", "#8B0000"),    # crimson / gold / crimson
    "burnwillow": ("#00FFCC", "#FFD700", "#2D5016"),   # cyan / gold / decay green
}


def _pal(system_id: str) -> Tuple[str, str, str]:
    return _PALETTES.get(system_id, ("#FFFFFF", "#AAAAAA", "#FFFFFF"))


# =========================================================================
# SHARED HELPERS
# =========================================================================

def _render_action_dots(val: int, max_dots: int = 4) -> Text:
    """Render action dots: ●●●○"""
    t = Text()
    for i in range(max_dots):
        if i < val:
            t.append("\u25cf", style="bold white")
        else:
            t.append("\u25cb", style="dim")
    return t


def _render_stress_track(cur: int, max_val: int = 9) -> Text:
    """Render: STRESS [■■■■□□□□□] 4/9"""
    t = Text()
    t.append("STRESS ", style="bold yellow")
    t.append("[")
    for i in range(max_val):
        if i < cur:
            t.append("\u25a0", style="bold red")
        else:
            t.append("\u25a1", style="dim")
    t.append(f"] {cur}/{max_val}")
    return t


def _render_mark_track(cur: int, max_val: int = 3, label: str = "") -> Text:
    """Render: Body  [■■□] 2/3"""
    t = Text()
    if label:
        t.append(f"{label:6s}", style="bold")
    t.append("[")
    for i in range(max_val):
        if i < cur:
            t.append("\u25a0", style="bold red")
        else:
            t.append("\u25a1", style="dim")
    t.append(f"] {cur}/{max_val}")
    return t


def _render_hp_bar(cur: int, max_val: int, width: int = 16) -> Text:
    """Render: [████████░░░░] 24/36"""
    max_val = max(1, max_val)
    pct = max(0.0, min(1.0, cur / max_val))
    filled = int(width * pct)
    empty = width - filled

    if pct > 0.6:
        color = "green"
    elif pct > 0.3:
        color = "yellow"
    else:
        color = "red"

    t = Text()
    t.append("[")
    t.append("\u2588" * filled, style=color)
    t.append("\u2591" * empty, style="dim")
    t.append(f"] {cur}/{max_val}")
    return t


def _render_resource_gauge(cur: int, max_val: int, label: str = "",
                           color: str = "cyan") -> Text:
    """Render: Focus [████░░░░] 4/8"""
    max_val = max(1, max_val)
    bar_w = 8
    filled = int(bar_w * max(0.0, min(1.0, cur / max_val)))
    empty = bar_w - filled

    t = Text()
    if label:
        t.append(f"{label} ", style="bold")
    t.append("[")
    t.append("\u2588" * filled, style=color)
    t.append("\u2591" * empty, style="dim")
    t.append(f"] {cur}/{max_val}")
    return t


def _render_sway_gauge(sway: int, terms: Dict[str, str]) -> Text:
    """Render: CROWN ◄═══▼═══► CREW"""
    left = terms.get("crown_label", "CROWN")
    right = terms.get("crew_label", "CREW")

    # sway ranges -3 to +3, map to 7 positions
    pos = sway + 3  # 0..6
    t = Text()
    t.append(f"{left} ", style="bold red")
    t.append("\u25c4")
    for i in range(7):
        if i == pos:
            t.append("\u25bc", style="bold white")
        else:
            t.append("\u2550", style="dim")
    t.append("\u25ba")
    t.append(f" {right}", style="bold green")
    return t


def _action_group_table(name: str, actions: List[Tuple[str, int]],
                        style: str = "white") -> Table:
    """Named column of action dots."""
    tbl = Table.grid(padding=(0, 1))
    tbl.add_column(style="bold " + style, min_width=10)
    tbl.add_column()
    tbl.add_row(f"[underline]{name}[/underline]", "")
    for action_name, dots in actions:
        tbl.add_row(f"  {action_name.capitalize()}", _render_action_dots(dots))
    return tbl


def _mod(score: int) -> str:
    """Format ability modifier: +3 or -1."""
    m = (score - 10) // 2
    return f"{m:+d}"


# =========================================================================
# SYSTEM RENDERERS
# =========================================================================

def _render_dnd5e(engine, width: int) -> Panel:
    """D&D 5e character sheet — two-column layout."""
    accent, secondary, border = _pal("dnd5e")
    char = getattr(engine, 'character', None)
    if not char:
        return Panel("[dim]No character created.[/dim]",
                     title="CHARACTER SHEET", border_style=border)

    # Header
    header = Text()
    header.append(f"{char.name}", style=f"bold {accent}")
    race = getattr(char, 'race', '') or ''
    cls = getattr(char, 'character_class', '') or ''
    level = getattr(char, 'level', 1)
    header.append(f"  Level {level} {race} {cls}".rstrip(), style=secondary)
    bg = getattr(char, 'background', '') or ''
    xp = getattr(char, 'xp', 0)
    if bg or xp:
        header.append(f"\nBackground: {bg}" if bg else "")
        header.append(f"  XP: {xp:,}" if xp else "")

    # Left column: ability scores + saving throws
    left = Table.grid(padding=(0, 1))
    left.add_column(style=f"bold {accent}", min_width=6)
    left.add_column(style="white", justify="right", min_width=3)
    left.add_column(style="cyan", min_width=5)

    abilities = [
        ("STR", getattr(char, 'strength', 10)),
        ("DEX", getattr(char, 'dexterity', 10)),
        ("CON", getattr(char, 'constitution', 10)),
        ("INT", getattr(char, 'intelligence', 10)),
        ("WIS", getattr(char, 'wisdom', 10)),
        ("CHA", getattr(char, 'charisma', 10)),
    ]

    left.add_row("[underline]ABILITY SCORES[/underline]", "", "")
    for ab_name, score in abilities:
        left.add_row(f"  {ab_name}", str(score), f"({_mod(score)})")

    # Saving throw proficiency (class-based)
    _SAVE_PROFS = {
        "barbarian": {"STR", "CON"}, "bard": {"DEX", "CHA"},
        "cleric": {"WIS", "CHA"}, "druid": {"INT", "WIS"},
        "fighter": {"STR", "CON"}, "monk": {"STR", "DEX"},
        "paladin": {"WIS", "CHA"}, "ranger": {"STR", "DEX"},
        "rogue": {"DEX", "INT"}, "sorcerer": {"CON", "CHA"},
        "warlock": {"WIS", "CHA"}, "wizard": {"INT", "WIS"},
    }
    prof_set = _SAVE_PROFS.get((cls or '').lower(), set())
    prof_bonus = getattr(char, 'proficiency_bonus', 2)

    left.add_row("", "", "")
    left.add_row("[underline]SAVING THROWS[/underline]", "", "")
    for ab_name, score in abilities:
        mod_val = (score - 10) // 2
        is_prof = ab_name in prof_set
        total = mod_val + (prof_bonus if is_prof else 0)
        pip = "\u25cf" if is_prof else "\u25cb"
        left.add_row(f"  {pip} {ab_name}", "", f"{total:+d}")

    # Right column: combat stats + HP + features
    right_lines = Text()

    ac = getattr(char, 'armor_class', 10)
    init_mod = (getattr(char, 'dexterity', 10) - 10) // 2
    speed = "30ft"
    right_lines.append(f"AC: {ac}   Init: {init_mod:+d}   Speed: {speed}\n\n",
                       style=f"bold {accent}")

    right_lines.append("HIT POINTS\n", style=f"bold {accent}")
    hp_cur = getattr(char, 'current_hp', 0)
    hp_max = getattr(char, 'max_hp', 1)
    right_lines.append(_render_hp_bar(hp_cur, hp_max))
    right_lines.append("\n")

    hd_remain = getattr(char, 'hit_dice_remaining', level)
    hd_type = getattr(char, 'hit_die_type', 8)
    right_lines.append(f"Hit Dice: {hd_remain}/{level} d{hd_type}\n\n")

    right_lines.append(f"PROFICIENCY BONUS: +{prof_bonus}\n\n",
                       style=f"bold {accent}")

    features = getattr(char, 'features', [])
    if features:
        right_lines.append("FEATURES\n", style=f"bold {accent}")
        right_lines.append(f"  {', '.join(features[:6])}\n")

    profs = getattr(char, 'proficiencies', [])
    if profs:
        right_lines.append("\nPROFICIENCIES\n", style=f"bold {accent}")
        right_lines.append(f"  {', '.join(profs[:6])}\n")

    # Layout
    layout = Layout()
    layout.split_row(
        Layout(Panel(left, border_style="dim", box=box.SIMPLE), ratio=1),
        Layout(Panel(right_lines, border_style="dim", box=box.SIMPLE), ratio=2),
    )

    return Panel(
        Group(header, "", layout),
        title=f"[bold {accent}]CHARACTER SHEET[/]",
        border_style=border, box=box.DOUBLE, width=width, padding=(1, 2),
    )


def _render_stc(engine, width: int) -> Panel:
    """Stormlight/Cosmere character sheet."""
    accent, secondary, border = _pal("stc")
    char = getattr(engine, 'character', None)
    if not char:
        return Panel("[dim]No character created.[/dim]",
                     title="RADIANT CHARACTER SHEET", border_style=border)

    header = Text()
    header.append(f"{char.name}", style=f"bold {accent}")
    order = getattr(char, 'order', '') or ''
    heritage = getattr(char, 'heritage', '') or ''
    header.append(f"  {order.title()} ({heritage})", style=secondary)
    ideal = getattr(char, 'ideal_level', 1)
    header.append(f"\nIdeal Level: {ideal}")

    body = Text()

    # Attributes
    body.append("ATTRIBUTES\n", style=f"bold {accent}")
    for attr_name, attr_key in [("STR", "strength"), ("SPD", "speed"), ("INT", "intellect")]:
        val = getattr(char, attr_key, 10)
        body.append(f"  {attr_name}  {val:>2} ({_mod(val)})\n")

    body.append("\n")

    # Combat
    body.append("COMBAT\n", style=f"bold {accent}")
    defense = getattr(char, 'defense', 10)
    body.append(f"  Defense: {defense}\n")
    body.append("  HP ")
    body.append(_render_hp_bar(
        getattr(char, 'current_hp', 0),
        getattr(char, 'max_hp', 1),
    ))
    body.append("\n\n")

    # Stormlight / Focus
    focus = getattr(char, 'focus', 0)
    max_focus = getattr(char, 'max_focus', 8)
    body.append("STORMLIGHT\n", style=f"bold {secondary}")
    body.append("  ")
    body.append(_render_resource_gauge(focus, max_focus, "Focus", "cyan"))
    body.append("\n\n")

    # Surges
    surges = []
    if hasattr(char, 'get_surges'):
        surges = char.get_surges()
    if surges:
        body.append("SURGES\n", style=f"bold {accent}")
        for s in surges:
            body.append(f"  \u25c8 {s.title()}\n", style="cyan")

    return Panel(
        Group(header, "", body),
        title=f"[bold {accent}]RADIANT CHARACTER SHEET[/]",
        border_style=border, box=box.DOUBLE, width=width, padding=(1, 2),
    )


def _render_fitd_3col(engine, system_id: str, width: int,
                      title_text: str,
                      char_subtitle_fn,
                      action_groups: List[Tuple[str, List[str]]],
                      bottom_fn) -> Panel:
    """Shared 3-column FITD renderer for BitD/SaV/CBR+PNK."""
    accent, secondary, border = _pal(system_id)
    char = getattr(engine, 'character', None)
    if not char:
        return Panel("[dim]No character created.[/dim]",
                     title=title_text, border_style=border)

    # Header
    header = Text()
    header.append(f"{char.name}", style=f"bold {accent}")
    header.append(f"  {char_subtitle_fn(char)}", style=secondary)
    vice = getattr(char, 'vice', '')
    if vice:
        header.append(f"\nVice: {vice}")

    # Action groups as 3-column grid
    grid = Table.grid(padding=(0, 2))
    for _ in action_groups:
        grid.add_column()

    cols = []
    for group_name, action_names in action_groups:
        actions = [(a, getattr(char, a, 0)) for a in action_names]
        cols.append(_action_group_table(group_name, actions, accent))
    grid.add_row(*cols)

    # Stress track
    stress_text = Text()
    clocks = getattr(engine, 'stress_clocks', {})
    clock = clocks.get(char.name)
    if clock:
        stress_text = _render_stress_track(clock.current_stress, clock.max_stress)
        if clock.traumas:
            stress_text.append(f"\nTRAUMA ", style="bold red")
            stress_text.append(", ".join(clock.traumas))
    else:
        stress_text.append("STRESS [no clock]", style="dim")

    # System-specific bottom section
    bottom = bottom_fn(engine, char, accent, secondary)

    return Panel(
        Group(header, "", grid, "", stress_text, "", bottom),
        title=f"[bold {accent}]{title_text}[/]",
        border_style=border, box=box.DOUBLE, width=width, padding=(1, 2),
    )


def _bitd_subtitle(char) -> str:
    pb = getattr(char, 'playbook', '') or ''
    her = getattr(char, 'heritage', '') or ''
    return f"{pb} ({her})".strip(" ()")


def _bitd_bottom(engine, char, accent, secondary) -> Text:
    t = Text()
    crew = getattr(engine, 'crew_name', '')
    ctype = getattr(engine, 'crew_type', '')
    if crew or ctype:
        label = f"{crew}" + (f" ({ctype})" if ctype else "")
        t.append(f"\u2500\u2500 CREW: {label} \u2500\u2500\n", style=f"bold {accent}")
    heat = getattr(engine, 'heat', 0)
    wanted = getattr(engine, 'wanted_level', 0)
    rep = getattr(engine, 'rep', 0)
    coin = getattr(engine, 'coin', 0)
    turf = getattr(engine, 'turf', 0)
    t.append(f"Heat: {heat}  Wanted: {wanted}  Rep: {rep}  Coin: {coin}  Turf: {turf}")
    return t


def _render_bitd(engine, width: int) -> Panel:
    return _render_fitd_3col(
        engine, "bitd", width,
        title_text="SCOUNDREL SHEET",
        char_subtitle_fn=_bitd_subtitle,
        action_groups=[
            ("INSIGHT", ["hunt", "study", "survey", "tinker"]),
            ("PROWESS", ["finesse", "prowl", "skirmish", "wreck"]),
            ("RESOLVE", ["attune", "command", "consort", "sway"]),
        ],
        bottom_fn=_bitd_bottom,
    )


def _sav_subtitle(char) -> str:
    pb = getattr(char, 'playbook', '') or ''
    her = getattr(char, 'heritage', '') or ''
    return f"{pb} ({her})".strip(" ()")


def _sav_bottom(engine, char, accent, secondary) -> Text:
    t = Text()
    ship = getattr(engine, 'ship_name', '')
    sclass = getattr(engine, 'ship_class', '')
    if ship or sclass:
        label = f"{ship}" + (f" ({sclass})" if sclass else "")
        t.append(f"\u2500\u2500 SHIP: {label} \u2500\u2500\n", style=f"bold {accent}")
    heat = getattr(engine, 'heat', 0)
    rep = getattr(engine, 'rep', 0)
    coin = getattr(engine, 'coin', 0)
    t.append(f"Heat: {heat}  Rep: {rep}  Coin: {coin}")
    return t


def _render_sav(engine, width: int) -> Panel:
    return _render_fitd_3col(
        engine, "sav", width,
        title_text="SPACER SHEET",
        char_subtitle_fn=_sav_subtitle,
        action_groups=[
            ("INSIGHT", ["doctor", "hack", "rig", "study"]),
            ("PROWESS", ["helm", "scramble", "scrap", "skulk"]),
            ("RESOLVE", ["attune", "command", "consort", "sway"]),
        ],
        bottom_fn=_sav_bottom,
    )


def _cbrpnk_subtitle(char) -> str:
    arch = getattr(char, 'archetype', '') or ''
    bg = getattr(char, 'background', '') or ''
    return f"{arch} ({bg})".strip(" ()")


def _cbrpnk_bottom(engine, char, accent, secondary) -> Text:
    t = Text()
    chrome = getattr(char, 'chrome', [])
    if chrome:
        t.append("CHROME\n", style=f"bold {secondary}")
        for i, c in enumerate(chrome):
            prefix = "\u2514" if i == len(chrome) - 1 else "\u251c"
            t.append(f"  {prefix} {c}\n")
    heat = getattr(engine, 'heat', 0)
    glitch = getattr(engine, 'glitch_die', 0)
    t.append(f"Heat: {heat}  Glitch Die: {glitch}")
    return t


def _render_cbrpnk(engine, width: int) -> Panel:
    return _render_fitd_3col(
        engine, "cbrpnk", width,
        title_text="RUNNER SHEET",
        char_subtitle_fn=_cbrpnk_subtitle,
        action_groups=[
            ("INSIGHT", ["hack", "override", "scan", "study"]),
            ("PROWESS", ["scramble", "scrap", "skulk", "shoot"]),
            ("RESOLVE", ["attune", "command", "consort", "sway"]),
        ],
        bottom_fn=_cbrpnk_bottom,
    )


def _render_bob(engine, width: int) -> Panel:
    """Band of Blades — two-column actions + Legion sub-panel."""
    accent, secondary, border = _pal("bob")
    char = getattr(engine, 'character', None)
    if not char:
        return Panel("[dim]No character created.[/dim]",
                     title="LEGIONNAIRE SHEET", border_style=border)

    # Header
    header = Text()
    header.append(f"{char.name}", style=f"bold {accent}")
    pb = getattr(char, 'playbook', '') or ''
    her = getattr(char, 'heritage', '') or ''
    header.append(f"  {pb} ({her})", style=secondary)

    # Actions — BoB has 10 actions, display in two columns
    all_actions = [
        ("doctor", getattr(char, 'doctor', 0)),
        ("marshal", getattr(char, 'marshal', 0)),
        ("research", getattr(char, 'research', 0)),
        ("scout", getattr(char, 'scout_action', 0)),
        ("maneuver", getattr(char, 'maneuver', 0)),
        ("skirmish", getattr(char, 'skirmish', 0)),
        ("wreck", getattr(char, 'wreck', 0)),
        ("consort", getattr(char, 'consort', 0)),
        ("discipline", getattr(char, 'discipline', 0)),
        ("sway", getattr(char, 'sway', 0)),
    ]
    left_actions = all_actions[:5]
    right_actions = all_actions[5:]

    grid = Table.grid(padding=(0, 3))
    grid.add_column()
    grid.add_column()

    left_tbl = Table.grid(padding=(0, 1))
    left_tbl.add_column(style=f"bold {accent}", min_width=12)
    left_tbl.add_column()
    left_tbl.add_row("[underline]ACTIONS[/underline]", "")
    for name, dots in left_actions:
        left_tbl.add_row(f"  {name.capitalize()}", _render_action_dots(dots))

    right_tbl = Table.grid(padding=(0, 1))
    right_tbl.add_column(style=f"bold {accent}", min_width=12)
    right_tbl.add_column()
    right_tbl.add_row("", "")
    for name, dots in right_actions:
        right_tbl.add_row(f"  {name.capitalize()}", _render_action_dots(dots))

    grid.add_row(left_tbl, right_tbl)

    # Stress
    stress_text = Text()
    clocks = getattr(engine, 'stress_clocks', {})
    clock = clocks.get(char.name)
    if clock:
        stress_text = _render_stress_track(clock.current_stress, clock.max_stress)
        if clock.traumas:
            stress_text.append(f"\nTRAUMA ", style="bold red")
            stress_text.append(", ".join(clock.traumas))

    # Legion sub-panel
    legion = getattr(engine, 'legion', None)
    legion_text = Text()
    chosen = getattr(engine, 'chosen', '')
    phase = getattr(engine, 'campaign_phase', '')
    if chosen or phase:
        legion_text.append(f"Chosen: {chosen}", style=f"bold {accent}")
        if phase:
            legion_text.append(f"  Phase: {phase.title()}")
        legion_text.append("\n")

    if legion:
        for label, attr, max_val in [
            ("Supply", "supply", 10), ("Intel", "intel", 10),
            ("Morale", "morale", 10), ("Pressure", "pressure", 6),
        ]:
            val = getattr(legion, attr, 0)
            legion_text.append("  ")
            legion_text.append(_render_resource_gauge(val, max_val, label,
                               "red" if label == "Pressure" else accent))
            legion_text.append("\n")

    legion_panel = Panel(
        legion_text,
        title=f"[bold {accent}]THE LEGION[/]",
        border_style=secondary, box=box.ROUNDED,
    )

    return Panel(
        Group(header, "", grid, "", stress_text, "", legion_panel),
        title=f"[bold {accent}]LEGIONNAIRE SHEET[/]",
        border_style=border, box=box.DOUBLE, width=width, padding=(1, 2),
    )


def _render_candela(engine, width: int) -> Panel:
    """Candela Obscura — three drives + Body/Brain/Bleed marks."""
    accent, secondary, border = _pal("candela")
    char = getattr(engine, 'character', None)
    if not char:
        return Panel("[dim]No character created.[/dim]",
                     title="INVESTIGATOR SHEET", border_style=border)

    # Header
    header = Text()
    header.append(f"{char.name}", style=f"bold {accent}")
    role = getattr(char, 'role', '') or ''
    spec = getattr(char, 'specialization', '') or ''
    header.append(f"  {role}", style=secondary)
    if spec:
        header.append(f" ({spec})", style=secondary)
    bg = getattr(char, 'background', '') or ''
    catalyst = getattr(char, 'catalyst', '') or ''
    if bg or catalyst:
        header.append(f"\nBackground: {bg}" if bg else "")
        header.append(f"  Catalyst: {catalyst}" if catalyst else "")

    # Action groups (3 drives)
    grid = Table.grid(padding=(0, 2))
    grid.add_column()
    grid.add_column()
    grid.add_column()
    grid.add_row(
        _action_group_table("NERVE", [
            ("move", getattr(char, 'move', 0)),
            ("strike", getattr(char, 'strike', 0)),
            ("control", getattr(char, 'control', 0)),
        ], accent),
        _action_group_table("CUNNING", [
            ("sway", getattr(char, 'sway', 0)),
            ("read", getattr(char, 'read', 0)),
            ("hide", getattr(char, 'hide', 0)),
        ], accent),
        _action_group_table("INTUITION", [
            ("survey", getattr(char, 'survey', 0)),
            ("focus", getattr(char, 'focus', 0)),
            ("sense", getattr(char, 'sense', 0)),
        ], accent),
    )

    # Resistance marks
    marks_text = Text()
    marks_text.append("RESISTANCE MARKS\n", style=f"bold {accent}")
    marks_text.append("  ")
    marks_text.append(_render_mark_track(
        getattr(char, 'body', 0), getattr(char, 'body_max', 3), "Body"))
    marks_text.append("   ")
    marks_text.append(_render_mark_track(
        getattr(char, 'brain', 0), getattr(char, 'brain_max', 3), "Brain"))
    marks_text.append("   ")
    marks_text.append(_render_mark_track(
        getattr(char, 'bleed', 0), getattr(char, 'bleed_max', 3), "Bleed"))

    # Circle info
    circle_text = Text()
    circle = getattr(engine, 'circle_name', '')
    assignments = getattr(engine, 'assignments_completed', 0)
    if circle:
        circle_text.append(
            f"\u2500\u2500 CIRCLE: {circle} \u2500\u2500\n",
            style=f"bold {accent}")
    circle_text.append(f"Assignments Completed: {assignments}")

    return Panel(
        Group(header, "", grid, "", marks_text, "", circle_text),
        title=f"[bold {accent}]INVESTIGATOR SHEET[/]",
        border_style=border, box=box.DOUBLE, width=width, padding=(1, 2),
    )


def _render_crown(engine, width: int) -> Panel:
    """Crown & Crew — narrative state (no character class)."""
    accent, secondary, border = _pal("crown")

    day = getattr(engine, 'day', 1)
    arc_length = getattr(engine, 'arc_length', 5)
    sway_val = getattr(engine, 'sway', 0)
    terms = getattr(engine, 'terms', {})
    dna = getattr(engine, 'dna', {})
    patron = getattr(engine, 'patron', '')
    leader = getattr(engine, 'leader', '')

    # Header
    header = Text()
    header.append(f"Day {day} of {arc_length}", style=f"bold {secondary}")

    # Sway gauge
    sway_section = Text()
    sway_section.append("SWAY\n", style=f"bold {accent}")
    sway_section.append("  ")
    sway_section.append(_render_sway_gauge(sway_val, terms))

    # Import SWAY_TIERS for label
    try:
        from codex.games.crown.engine import SWAY_TIERS
        tier = SWAY_TIERS.get(sway_val, SWAY_TIERS.get(0, {}))
        tier_name = tier.get("name", "Unknown")
    except ImportError:
        tier_name = "Unknown"
    sign = "+" if sway_val > 0 else ""
    sway_section.append(f"\n  Current: {sign}{sway_val} ({tier_name})")

    # Narrative DNA
    dna_section = Text()
    dna_section.append("\nNARRATIVE DNA\n", style=f"bold {accent}")
    max_dna = max(dna.values()) if dna else 1
    bar_max = max(10, max_dna)
    for tag in ["BLOOD", "GUILE", "HEARTH", "SILENCE", "DEFIANCE"]:
        val = dna.get(tag, 0)
        filled = int(10 * val / bar_max) if bar_max > 0 else 0
        empty = 10 - filled
        dna_section.append(f"  {tag:10s}", style=f"bold {secondary}")
        dna_section.append("\u2588" * filled, style=accent)
        dna_section.append("\u2591" * empty, style="dim")
        dna_section.append(f"  {val}\n")

    # Footer
    footer = Text()
    if patron or leader:
        footer.append(f"\nPatron: {patron}", style=secondary)
        footer.append(f"  |  Leader: {leader}", style=secondary)

    return Panel(
        Group(header, "", sway_section, dna_section, footer),
        title=f"[bold {accent}]ALLEGIANCE REPORT[/]",
        border_style=border, box=box.DOUBLE, width=width, padding=(1, 2),
    )


def _render_burnwillow(engine, width: int) -> Panel:
    """Delegate to existing paper_doll.py renderer."""
    char = getattr(engine, 'character', None)
    if not char:
        return Panel("[dim]No character created.[/dim]",
                     title="CHARACTER SHEET", border_style="#2D5016")
    try:
        from codex.games.burnwillow.paper_doll import render_paper_doll
        return render_paper_doll(char, console_width=width)
    except (ImportError, TypeError, AttributeError):
        # Minimal fallback if paper_doll can't render (e.g. mock objects)
        hp_cur = getattr(char, 'current_hp', 0)
        hp_max = getattr(char, 'max_hp', 1)
        return Panel(
            f"{char.name}\nHP: {hp_cur}/{hp_max}",
            title="CHARACTER SHEET", border_style="#2D5016",
        )


# =========================================================================
# ROUTER
# =========================================================================

_RENDERERS = {
    "dnd5e":     _render_dnd5e,
    "stc":       _render_stc,
    "bitd":      _render_bitd,
    "sav":       _render_sav,
    "bob":       _render_bob,
    "cbrpnk":    _render_cbrpnk,
    "candela":   _render_candela,
    "crown":     _render_crown,
    "burnwillow": _render_burnwillow,
}


def render_sheet(engine, system_id: str, width: int = 76) -> Panel:
    """Render a full character sheet for the given system.

    Dispatches to a system-specific renderer. Falls back to a generic
    engine.get_status() dump for unknown systems.

    Args:
        engine: Game engine instance.
        system_id: System identifier (e.g. "dnd5e", "bitd").
        width: Panel width in columns.

    Returns:
        Rich Panel containing the rendered character sheet.
    """
    renderer = _RENDERERS.get(system_id)
    if renderer:
        return renderer(engine, width)

    # Generic fallback
    status = ""
    if hasattr(engine, 'get_status'):
        status = engine.get_status()
    elif hasattr(engine, 'character') and engine.character:
        char = engine.character
        status = f"{char.name}\n"
        if hasattr(char, 'current_hp'):
            status += f"HP: {char.current_hp}/{char.max_hp}\n"
    else:
        status = "No character data available."

    return Panel(
        status,
        title="CHARACTER SHEET",
        border_style="white",
        box=box.DOUBLE,
        width=width,
    )
