# Spatial Map Renderer — Visual Examples

This document shows what the rendered output looks like for each theme.

---

## THEME: RUST (Burnwillow — Industrial Decay)

```
╔════════════════════════════════════════════════════════════════════════════╗
║            BURNWILLOW :: BIOLUMINESCENT DECAY                              ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  ┌──────────────────────────────────┬───────────────────────┐             ║
║  │ THE MINIMAP                      │ CURRENT ROOM          │             ║
║  ├──────────────────────────────────┼───────────────────────┤             ║
║  │                                  │ Storage Bay #3        │             ║
║  │  ████████··········████████░░░░  │                       │             ║
║  │  █······█··········█······█░░░░  │ "Rusted pipes drip    │             ║
║  │  █·····@█          █······█░░░░  │  oily water..."       │             ║
║  │  █··$···█          █E·····█      │                       │             ║
║  │  ████████          ████████      │ ───────────────────   │             ║
║  │     ·                            │                       │             ║
║  │  ████████          ████████      │ HP: [████████░░] 8    │             ║
║  │  █··E···█          █······█      │                       │             ║
║  │  █······█          █······█      │ Depth: Floor 3        │             ║
║  │  ████████          ████████      │                       │             ║
║  │                                  │ ENEMIES: 2            │             ║
║  │  ░░░░░░░░                        │ • Rust Rat (5 HP)     │             ║
║  │  ░░░░░░░░          ░░░░░░░░      │ • Oil Slick (3 HP)    │             ║
║  │  ░░░░░░░░          ░░░░░░░░      │                       │             ║
║  │                                  │ LOOT: 1               │             ║
║  │                                  │ • Rusted Shortsword   │             ║
║  │                                  │                       │             ║
║  │                                  │ EXITS: N, S           │             ║
║  └──────────────────────────────────┴───────────────────────┘             ║
║                                                                            ║
║  LEGEND                                                                    ║
║  ───────────────────────────────────────                                  ║
║    @   Player        E   Enemy        $   Loot                            ║
║    S   Start         B   Boss         ░   Unexplored                      ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

**Visual Characteristics:**
- **Walls**: Heavy `█` blocks (industrial, claustrophobic)
- **Floor**: Metal grating `·` (sparse, allows seeing through)
- **Fog**: Bioluminescent spores `░` (purple-ish in actual render)
- **Player**: `@` in bright cyan (glowing fungus aesthetic)
- **Enemies**: `E` in rust orange (corroded metal)
- **Loot**: `$` in gold (willow tree coins)

**Color Scheme:**
- Current room: Bright cyan borders
- Visited rooms: Dimmed green
- Unexplored: Purple fog

---

## THEME: STONE (D&D Classic Dungeon)

```
╔════════════════════════════════════════════════════════════════════════════╗
║                  D&D :: TORCHLIT DUNGEON                                   ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  ┌──────────────────────────────────┬───────────────────────┐             ║
║  │ THE MINIMAP                      │ CURRENT ROOM          │             ║
║  ├──────────────────────────────────┼───────────────────────┤             ║
║  │                                  │ Storage Bay #3        │             ║
║  │  ########..........########~~~~  │                       │             ║
║  │  #......#..........#......#~~~~  │ "Stone walls echo     │             ║
║  │  #.....@#          #......#~~~~  │  with your steps..."  │             ║
║  │  #..*...#          #M.....#      │                       │             ║
║  │  ########          ########      │ ───────────────────   │             ║
║  │     .                            │                       │             ║
║  │  ########          ########      │ HP: [████████░░] 8    │             ║
║  │  #..M...#          #......#      │                       │             ║
║  │  #......#          #......#      │ Depth: Floor 3        │             ║
║  │  ########          ########      │                       │             ║
║  │                                  │ ENEMIES: 2            │             ║
║  │  ~~~~~~~~                        │ • Goblin (5 HP)       │             ║
║  │  ~~~~~~~~          ~~~~~~~~      │ • Rat Swarm (3 HP)    │             ║
║  │  ~~~~~~~~          ~~~~~~~~      │                       │             ║
║  │                                  │ LOOT: 1               │             ║
║  │                                  │ • Iron Shortsword     │             ║
║  │                                  │                       │             ║
║  │                                  │ EXITS: N, S           │             ║
║  └──────────────────────────────────┴───────────────────────┘             ║
║                                                                            ║
║  LEGEND                                                                    ║
║  ───────────────────────────────────────                                  ║
║    @   Player        M   Monster      *   Treasure                        ║
║    S   Start         B   Boss         ~   Shadow                          ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

**Visual Characteristics:**
- **Walls**: Stone blocks `#` (classic roguelike aesthetic)
- **Floor**: Flagstone `.` (traditional dungeon)
- **Fog**: Shadow `~` (darkness creeping in)
- **Player**: `@` in gold (torchlight)
- **Enemies**: `M` in orange (monster silhouettes)
- **Loot**: `*` in gold (treasure glint)

**Color Scheme:**
- Current room: Bright gold borders
- Visited rooms: Dimmed grey stone
- Unexplored: Deep shadow

---

## THEME: GOTHIC (Ashburn High — Victorian Horror)

```
╔════════════════════════════════════════════════════════════════════════════╗
║               ASHBURN HIGH :: CURSED HALLS                                 ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  ┌──────────────────────────────────┬───────────────────────┐             ║
║  │ THE MINIMAP                      │ CURRENT ROOM          │             ║
║  ├──────────────────────────────────┼───────────────────────┤             ║
║  │                                  │ The Grand Foyer       │             ║
║  │  ╔══════╗░░░░░░░░░░╔══════╗▒▒▒▒  │                       │             ║
║  │  ║░░░░░░║░░░░░░░░░░║░░░░░░║▒▒▒▒  │ "Velvet curtains      │             ║
║  │  ║░░░☥░║          ║░░░░░░║▒▒▒▒  │  hide shadows..."     │             ║
║  │  ║░░✦░░║          ║Σ░░░░░║      │                       │             ║
║  │  ╚══════╝          ╚══════╝      │ ───────────────────   │             ║
║  │     ║                            │                       │             ║
║  │  ╔══════╗          ╔══════╗      │ HP: [████████░░] 8    │             ║
║  │  ║░░Σ░░░║          ║░░░░░░║      │                       │             ║
║  │  ║░░░░░░║          ║░░░░░░║      │ Depth: Floor 3        │             ║
║  │  ╚══════╝          ╚══════╝      │                       │             ║
║  │                                  │ ENEMIES: 2            │             ║
║  │  ▒▒▒▒▒▒▒▒                        │ • Cursed Spirit (5HP) │             ║
║  │  ▒▒▒▒▒▒▒▒          ▒▒▒▒▒▒▒▒      │ • Shadow Thing (3HP)  │             ║
║  │  ▒▒▒▒▒▒▒▒          ▒▒▒▒▒▒▒▒      │                       │             ║
║  │                                  │ LOOT: 1               │             ║
║  │                                  │ • Antique Locket      │             ║
║  │                                  │                       │             ║
║  │                                  │ EXITS: N, S           │             ║
║  └──────────────────────────────────┴───────────────────────┘             ║
║                                                                            ║
║  LEGEND                                                                    ║
║  ───────────────────────────────────────                                  ║
║    ☥   Player        Σ   Entity       ✦   Treasure                        ║
║    §   Start         Ω   Boss         ▒   Darkness                        ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

**Visual Characteristics:**
- **Walls**: Box-drawing chars `╔═╗║╚╝` (architectural precision)
- **Floor**: Carpet/marble `░` (Victorian elegance)
- **Fog**: Dense darkness `▒` (eldritch gloom)
- **Player**: Ankh `☥` in bone white (death motif)
- **Enemies**: Sigma `Σ` in blood red (otherworldly)
- **Loot**: Star `✦` in gold (precious heirlooms)

**Color Scheme:**
- Current room: Bright bone white borders
- Visited rooms: Dimmed purple slate
- Unexplored: Deep purple darkness

---

## Visibility States Comparison

### CURRENT Room (Player is here)
```
RUST:              STONE:             GOTHIC:
████████           ########           ╔══════╗
█··@··E█           #..@..M#           ║░░☥░░Σ║
█··$···█           #..*...#           ║░░✦░░░║
████████           ########           ╚══════╝
(Bright cyan)      (Bright gold)      (Bright white)
```

### VISITED Room (Player has been here)
```
RUST:              STONE:             GOTHIC:
████████           ########           ╔══════╗
█······█           #......#           ║░░░░░░║
█······█           #......#           ║░░░░░░║
████████           ########           ╚══════╝
(Dimmed green)     (Dimmed grey)      (Dimmed purple)
```

### UNEXPLORED Room (Never visited)
```
RUST:              STONE:             GOTHIC:
░░░░░░░░           ~~~~~~~~           ▒▒▒▒▒▒▒▒
░░░░░░░░           ~~~~~~~~           ▒▒▒▒▒▒▒▒
░░░░░░░░           ~~~~~~~~           ▒▒▒▒▒▒▒▒
░░░░░░░░           ~~~~~~~~           ▒▒▒▒▒▒▒▒
(Purple fog)       (Shadow)           (Darkness)
```

---

## Corridor Rendering

### Horizontal Corridor
```
RUST:              STONE:             GOTHIC:
████████···········████████
█······█···········█······█
█······█           █······█
████████           ████████
```

### Vertical Corridor
```
RUST:              STONE:             GOTHIC:
████████           ████████           ╔══════╗
█······█           #......#           ║░░░░░░║
████████           ########           ╚══════╝
   ·                  .                  ║
   ·                  .                  ║
████████           ########           ╔══════╗
█······█           #......#           ║░░░░░░║
████████           ########           ╚══════╝
```

### L-Shaped Corridor (Typical Connection)
```
████████
█······█···········
████████          ·
                  ·
                  ·
              ████████
              █······█
              ████████
```

---

## Entity Scatter Pattern

Entities are positioned at strategic points inside rooms:

```
████████████
█1·········█    1: Top-left interior
█··········█    2: Top-right interior
█··········2█   3: Bottom-left interior
█··········█    4: Bottom-right interior
█····@·····█    @: Player (always center)
█··········█
█3·········█
█··········4█
████████████
```

For a room with 2 enemies and 1 loot:
- Enemy 1 → Position 1 (top-left)
- Enemy 2 → Position 2 (top-right)
- Loot → Position 3 (bottom-left)
- Player → Center (always)

---

## Full Layout Example (All Three Themes Side-by-Side)

When running the standalone demo (`python codex_map_renderer.py`), you'll see all three themes rendered sequentially with the same dungeon layout, allowing direct comparison.

The demo creates this dungeon structure:

```
[START]───[ROOM1]───[ROOM2]
   │                    │
[ROOM3*]            [ROOM4]───[BOSS]
   │
[TREASURE]───[TREASURE2]

* = Current room (player location)
```

Each theme renders this with:
- Visited rooms: START, ROOM1, ROOM2
- Current room: ROOM3 (with 2 enemies, 1 loot)
- Unexplored: ROOM4, BOSS, TREASURE, TREASURE2

---

## Terminal Compatibility

### Tested Terminals
- ✅ **GNOME Terminal** (Linux): Full 24-bit color support
- ✅ **Kitty** (Linux/Mac): Perfect rendering, font ligatures optional
- ✅ **iTerm2** (Mac): Excellent support
- ✅ **Windows Terminal**: Good support (enable UTF-8)
- ⚠️ **PuTTY**: Limited color, box-drawing chars may render as ASCII
- ⚠️ **SSH sessions**: Verify TERM=xterm-256color

### Font Recommendations
- **Best**: Fira Code, Cascadia Code, JetBrains Mono (with ligatures)
- **Good**: DejaVu Sans Mono, Consolas, Courier New
- **Avoid**: Variable-width fonts, emoji fonts

---

**For testing**: Run `python codex_map_renderer.py` to see all themes in action!
