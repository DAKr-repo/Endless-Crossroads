"""
tutorial_content.py -- C.O.D.E.X. Interactive Tutorial Content
===============================================================

Registers all tutorial modules at import time via TutorialRegistry.register().
Pure Python data -- no file I/O, no side effects beyond registration.

Content is organized into five categories:
  - platform   (6 modules)  General C.O.D.E.X. usage
  - burnwillow (8 modules)  Burnwillow dungeon-crawler specifics
  - crown      (3 modules)  Crown & Crew narrative card game
  - fitd       (4 modules)  Forged in the Dark family
  - dnd5e      (1 module)   D&D 5th Edition tools

22 modules, ~61 pages, 3 interactive sandbox pages.
"""

from codex.core.services.tutorial import TutorialPage, TutorialModule, TutorialRegistry


# ============================================================================
# CATEGORY: platform (6 modules)
# ============================================================================

# ---- 1. platform_overview (3 pages) ----------------------------------------

_PLATFORM_OVERVIEW = TutorialModule(
    module_id="platform_overview",
    title="Welcome to C.O.D.E.X.",
    description="Learn what C.O.D.E.X. can do",
    system_id="platform",
    category="platform",
    pages=[
        TutorialPage(
            page_id="platform_overview_1",
            title="What is C.O.D.E.X.?",
            content=(
                "[bold cyan]Chronicles of Destiny: Endless Crossroads[/bold cyan]\n"
                "\n"
                "C.O.D.E.X. is a tabletop RPG platform that runs entirely on a\n"
                "Raspberry Pi. No cloud subscriptions, no logins -- just you,\n"
                "your terminal, and a world of dice.\n"
                "\n"
                "What you get:\n"
                "  [bold white]Multiple game systems[/bold white] -- from Blades in the\n"
                "  Dark to D&D 5e, each with full rules support.\n"
                "  [bold white]AI Dungeon Master[/bold white] -- Mimir, a local LLM oracle\n"
                "  who answers lore questions in-character.\n"
                "  [bold white]Lore Vault[/bold white] -- a searchable library of source\n"
                "  material, world-building tools, and generated content.\n"
                "  [bold white]Two interfaces[/bold white] -- a Rich terminal TUI for solo\n"
                "  play, and a Discord bot for group sessions."
            ),
        ),
        TutorialPage(
            page_id="platform_overview_2",
            title="Main Menu",
            content=(
                "[bold cyan]The Seven Doors[/bold cyan]\n"
                "\n"
                "When C.O.D.E.X. launches you see the main menu. Each option\n"
                "leads to a distinct experience:\n"
                "\n"
                "  [bold yellow]1.[/bold yellow] [bold]Codex of Chronicles[/bold] -- Forged in the Dark\n"
                "     games (Blades, Scum & Villainy, Band of Blades, CBR+PNK).\n"
                "  [bold yellow]2.[/bold yellow] [bold]Crown & Crew[/bold] -- A narrative card\n"
                "     game of allegiance and consequence.\n"
                "  [bold yellow]3.[/bold yellow] [bold]Burnwillow[/bold] -- Roguelike dungeon crawler\n"
                "     with spatial maps, gear grids, and a rising Doom Clock.\n"
                "  [bold yellow]4.[/bold yellow] [bold]D&D 5e Tools[/bold] -- Fifth Edition character\n"
                "     sheets, hit dice, rest mechanics, and leveling.\n"
                "  [bold yellow]5.[/bold yellow] [bold]Cosmere (Stormlight)[/bold] -- Ideals, surges,\n"
                "     and the Stormlight RPG engine.\n"
                "  [bold yellow]6.[/bold yellow] [bold]DM Tools[/bold] -- Dice roller, NPC generator,\n"
                "     Omni-Forge character builder, World Genesis.\n"
                "  [bold yellow]7.[/bold yellow] [bold]Mimir's Vault[/bold] -- The Librarian TUI.\n"
                "     Browse source material, query the oracle.\n"
                "  [bold yellow]8.[/bold yellow] [bold]System Status[/bold] -- Thermal vitals, memory\n"
                "     usage, service health.\n"
                "  [bold yellow]9.[/bold yellow] [bold]Exit[/bold] -- Shut down cleanly."
            ),
        ),
        TutorialPage(
            page_id="platform_overview_3",
            title="Getting Started",
            content=(
                "[bold cyan]Where to Begin[/bold cyan]\n"
                "\n"
                "[bold green]New players:[/bold green] Start with [bold]Burnwillow[/bold].\n"
                "It is a self-contained dungeon crawler that teaches core\n"
                "mechanics (movement, combat, gear) through play. No prior\n"
                "tabletop experience needed.\n"
                "\n"
                "[bold green]Narrative players:[/bold green] Try [bold]Crown & Crew[/bold]\n"
                "next. A campaign driven by choices and faction\n"
                "allegiance. Quick to learn, deep to master.\n"
                "\n"
                "[bold green]Experienced RPG players:[/bold green] Dive into the\n"
                "[bold]Codex of Chronicles[/bold] for full Forged in the Dark\n"
                "systems with stress, clocks, and faction play.\n"
                "\n"
                "[bold green]D&D veterans:[/bold green] Try [bold]D&D 5e Tools[/bold]\n"
                "for familiar hit dice, rest, and leveling mechanics.\n"
                "\n"
                "[bold green]Cosmere fans:[/bold green] The [bold]Stormlight[/bold]\n"
                "engine features Ideals, surges, and oath progression.\n"
                "\n"
                "[dim]The [bold]help[/bold] command works everywhere in C.O.D.E.X.\n"
                "When in doubt, type it.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_PLATFORM_OVERVIEW)


# ---- 2. mimir_guide (3 pages) ----------------------------------------------

_MIMIR_GUIDE = TutorialModule(
    module_id="mimir_guide",
    title="Mimir: The All-Knowing",
    description="How to use the AI oracle",
    system_id="platform",
    category="platform",
    pages=[
        TutorialPage(
            page_id="mimir_guide_1",
            title="Who is Mimir?",
            content=(
                "[bold cyan]The Oracle Beneath the Roots[/bold cyan]\n"
                "\n"
                "Mimir is C.O.D.E.X.'s AI oracle -- a local large language\n"
                "model running on Ollama. No internet required. No data\n"
                "leaves your Pi.\n"
                "\n"
                "Mimir answers lore questions [italic]in character[/italic],\n"
                "drawing on the vault's source material. Ask about factions,\n"
                "NPCs, rules, history -- anything the books contain.\n"
                "\n"
                "Where to find Mimir:\n"
                "  [bold white]Mimir's Vault[/bold white] -- dedicated query mode\n"
                "  [bold white]In-game[/bold white] -- the [bold]ask[/bold] command\n"
                "     during any active session\n"
                "  [bold white]Discord[/bold white] -- mention or DM the bot"
            ),
        ),
        TutorialPage(
            page_id="mimir_guide_2",
            title="Asking Good Questions",
            content=(
                "[bold cyan]The Art of the Query[/bold cyan]\n"
                "\n"
                "Mimir performs best with specific, contextual questions.\n"
                "\n"
                "  [green]Good:[/green] \"What are the major factions in Doskvol?\"\n"
                "  [green]Good:[/green] \"How does stress work in Blades in the Dark?\"\n"
                "  [green]Good:[/green] \"Describe the Arborists of Burnwillow.\"\n"
                "\n"
                "  [red]Vague:[/red] \"Tell me about the world.\"\n"
                "  [red]Vague:[/red] \"What should I do next?\"\n"
                "\n"
                "Reference the current game system. Mimir scopes its\n"
                "answers to the active session when possible.\n"
                "\n"
                "[dim]Mimir's context window is limited (4096 tokens on the\n"
                "default model). Concise questions get better answers.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="mimir_guide_3",
            title="Mimir in the Vault",
            content=(
                "[bold cyan]Scoped Queries[/bold cyan]\n"
                "\n"
                "Inside the Librarian TUI, Mimir's answers are scoped to\n"
                "whichever tome you have open. This means:\n"
                "\n"
                "  1. Open a tome (e.g. the Burnwillow SRD).\n"
                "  2. Type [bold]ask <your question>[/bold].\n"
                "  3. Mimir searches that tome's content first.\n"
                "\n"
                "Results are cached locally -- repeat queries return\n"
                "instantly.\n"
                "\n"
                "[dim]Mimir can take 10-30 seconds on the first query\n"
                "while the model warms up. Subsequent queries are faster.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_MIMIR_GUIDE)


# ---- 3. librarian_guide (4 pages) ------------------------------------------

_LIBRARIAN_GUIDE = TutorialModule(
    module_id="librarian_guide",
    title="The Librarian's Archive",
    description="Navigate the vault and its special collections",
    system_id="platform",
    category="platform",
    pages=[
        TutorialPage(
            page_id="librarian_guide_1",
            title="Navigating the Vault",
            content=(
                "[bold cyan]Three-Panel Layout[/bold cyan]\n"
                "\n"
                "The Librarian TUI splits the terminal into three panels:\n"
                "\n"
                "  [bold white]Left -- Tome Index[/bold white]\n"
                "  A numbered list of available tomes and chapters.\n"
                "  Type a number to select.\n"
                "\n"
                "  [bold white]Center -- Open Page[/bold white]\n"
                "  The content of the selected chapter. Scrolls with\n"
                "  standard page controls.\n"
                "\n"
                "  [bold white]Right -- Consult Mimir[/bold white]\n"
                "  Recent oracle queries and responses, scoped to the\n"
                "  open tome.\n"
                "\n"
                "Use [bold]back[/bold] or [bold]b[/bold] to return to the\n"
                "previous view at any time."
            ),
        ),
        TutorialPage(
            page_id="librarian_guide_2",
            title="Special Collections",
            content=(
                "[bold cyan]Beyond the Books[/bold cyan]\n"
                "\n"
                "The vault contains more than source material:\n"
                "\n"
                "  [bold yellow]Seed Vault[/bold yellow] ([bold]seeds[/bold])\n"
                "  Saved dungeon seeds for replay. Each seed recreates\n"
                "  the exact same dungeon layout.\n"
                "\n"
                "  [bold yellow]Hall of Heroes[/bold yellow] ([bold]grave[/bold])\n"
                "  A memorial for fallen characters. Every death is\n"
                "  recorded with cause, dungeon depth, and final words.\n"
                "\n"
                "  [bold yellow]World Atlas[/bold yellow] ([bold]atlas[/bold])\n"
                "  Browse generated worlds with full G.R.A.P.E.S. detail.\n"
                "\n"
                "  [bold yellow]Chronology[/bold yellow] ([bold]chrono[/bold])\n"
                "  A timeline of historical events recorded by the\n"
                "  World Ledger during play."
            ),
        ),
        TutorialPage(
            page_id="librarian_guide_3",
            title="PDF Reading",
            content=(
                "[bold cyan]Reader Mode[/bold cyan]\n"
                "\n"
                "Select a PDF chapter to enter the built-in reader.\n"
                "Pages are rendered as Rich text with ligature sanitization.\n"
                "\n"
                "  [bold white]n[/bold white] -- Next page\n"
                "  [bold white]p[/bold white] -- Previous page\n"
                "  [bold white]<number>[/bold white] -- Jump to page\n"
                "  [bold white]b[/bold white] -- Back to chapter list\n"
                "\n"
                "Pages are lazy-loaded: only the current page is parsed\n"
                "at a time, keeping memory usage low on the Pi.\n"
                "\n"
                "[dim]Large PDFs may take a moment on first load while\n"
                "the page count is determined.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="librarian_guide_4",
            title="Commands Reference",
            content=(
                "[bold cyan]Librarian Commands[/bold cyan]\n"
                "\n"
                "  [bold white]<number>[/bold white]    Select tome or chapter\n"
                "  [bold white]open <tome>[/bold white]  Open a tome by name\n"
                "  [bold white]ask <q>[/bold white]      Query Mimir (scoped)\n"
                "  [bold white]list[/bold white]         List all tomes\n"
                "  [bold white]back[/bold white]         Return to previous view\n"
                "  [bold white]maps[/bold white]         View dungeon maps\n"
                "  [bold white]grave[/bold white]        Hall of Heroes\n"
                "  [bold white]seeds[/bold white]        Dungeon Seed Vault\n"
                "  [bold white]atlas[/bold white]        World Atlas browser\n"
                "  [bold white]chrono[/bold white]       Chronology timeline\n"
                "  [bold white]laws[/bold white]         System laws / rules\n"
                "  [bold white]carto[/bold white]        Cartography overview\n"
                "  [bold white]tutorial[/bold white]     Open this tutorial\n"
                "  [bold white]quit[/bold white]         Exit the Librarian"
            ),
        ),
    ],
)
TutorialRegistry.register(_LIBRARIAN_GUIDE)


# ---- 4. forge_guide (2 pages) ----------------------------------------------

_FORGE_GUIDE = TutorialModule(
    module_id="forge_guide",
    title="The Omni-Forge",
    description="Character creation and generator tables",
    system_id="platform",
    category="platform",
    pages=[
        TutorialPage(
            page_id="forge_guide_1",
            title="Character Creation",
            content=(
                "[bold cyan]The Forge Awaits[/bold cyan]\n"
                "\n"
                "The Omni-Forge builds characters for any system\n"
                "registered in C.O.D.E.X. -- Burnwillow adventurers,\n"
                "Blades scoundrels, Scum & Villainy spacers, and more.\n"
                "\n"
                "The process:\n"
                "  1. Choose a game system.\n"
                "  2. Allocate stats (rolled or point-buy).\n"
                "  3. Select gear loadout from the system's tables.\n"
                "  4. Roll or choose background traits.\n"
                "\n"
                "Access from [bold]DM Tools[/bold] in the main menu,\n"
                "or [bold]!forge[/bold] on Discord."
            ),
        ),
        TutorialPage(
            page_id="forge_guide_2",
            title="Tables & Generators",
            content=(
                "[bold cyan]Quick Generation[/bold cyan]\n"
                "\n"
                "Beyond full character builds, the Forge provides:\n"
                "\n"
                "  [bold yellow]Quick Loot[/bold yellow]\n"
                "  Roll on SRD loot tables by CR tier. Weapons, armor,\n"
                "  potions, and general goods.\n"
                "\n"
                "  [bold yellow]Lifepath Generator[/bold yellow]\n"
                "  Roll a complete backstory: origin, pivotal event,\n"
                "  profession, personality, and a secret.\n"
                "\n"
                "  [bold yellow]Treasure Hoards[/bold yellow]\n"
                "  Four CR tiers of treasure with coinage, gems, and\n"
                "  magic items.\n"
                "\n"
                "All tables are deterministic -- pass a seed for\n"
                "reproducible results."
            ),
        ),
    ],
)
TutorialRegistry.register(_FORGE_GUIDE)


# ---- 5. genesis_guide (3 pages) --------------------------------------------

_GENESIS_GUIDE = TutorialModule(
    module_id="genesis_guide",
    title="World Genesis",
    description="Build entire worlds with G.R.A.P.E.S.",
    system_id="platform",
    category="platform",
    pages=[
        TutorialPage(
            page_id="genesis_guide_1",
            title="G.R.A.P.E.S. System",
            content=(
                "[bold cyan]Six Pillars of a World[/bold cyan]\n"
                "\n"
                "Every generated world is built on the G.R.A.P.E.S.\n"
                "framework -- six categories that define a civilization:\n"
                "\n"
                "  [bold green]G[/bold green]eography   -- Terrain, climate, resources\n"
                "  [bold green]R[/bold green]eligion    -- Faiths, cults, sacred sites\n"
                "  [bold green]A[/bold green]rts        -- Music, literature, craftsmanship\n"
                "  [bold green]P[/bold green]olitics    -- Government, factions, laws\n"
                "  [bold green]E[/bold green]conomics   -- Trade, currency, industry\n"
                "  [bold green]S[/bold green]ocial      -- Classes, customs, taboos\n"
                "\n"
                "Each category generates 1-3 entries with combinatorial\n"
                "names drawn from 15 templates per category."
            ),
        ),
        TutorialPage(
            page_id="genesis_guide_2",
            title="Creating a World",
            content=(
                "[bold cyan]The Genesis Ritual[/bold cyan]\n"
                "\n"
                "  1. Open [bold]DM Tools[/bold] from the main menu.\n"
                "  2. Select [bold]World Genesis[/bold].\n"
                "  3. The engine rolls a complete world: name, genre,\n"
                "     tone, and all six G.R.A.P.E.S. categories.\n"
                "  4. Review the result in the Genesis display panel.\n"
                "  5. Reroll individual categories if desired.\n"
                "  6. Save to the [bold]worlds/[/bold] directory.\n"
                "\n"
                "Saved worlds persist across sessions and appear in the\n"
                "Librarian's World Atlas ([bold]atlas[/bold] command).\n"
                "\n"
                "[dim]Worlds also include architecture styles, fashion\n"
                "profiles, and aesthetic motifs for richer narration.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="genesis_guide_3",
            title="Language & Culture",
            content=(
                "[bold cyan]Cultural DNA[/bold cyan]\n"
                "\n"
                "Generated worlds include procedural language and culture:\n"
                "\n"
                "  [bold yellow]Language Profiles[/bold yellow]\n"
                "  Phoneme types (harsh, flowing, guttural), vowel and\n"
                "  consonant sets, syllable patterns (CV, CVC), naming\n"
                "  suffixes, and honorific titles. NPCs draw their names\n"
                "  from these profiles.\n"
                "\n"
                "  [bold yellow]Cultural Values[/bold yellow]\n"
                "  Each value has a tenet (core belief), an expression\n"
                "  (how it manifests), and a consequence (what happens\n"
                "  when violated). These shape NPC dialogue and faction\n"
                "  behavior through the Bias Lens system.\n"
                "\n"
                "[dim]15 language profiles and 15 cultural value templates\n"
                "provide thousands of unique combinations.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_GENESIS_GUIDE)


# ---- 6. voice_guide (2 pages) ----------------------------------------------

_VOICE_GUIDE = TutorialModule(
    module_id="voice_guide",
    title="Voice & Discord",
    description="Discord bot setup and text-to-speech",
    system_id="platform",
    category="platform",
    pages=[
        TutorialPage(
            page_id="voice_guide_1",
            title="Discord Setup",
            content=(
                "[bold cyan]The Bot Joins the Table[/bold cyan]\n"
                "\n"
                "C.O.D.E.X. runs a Discord bot for group play. The bot\n"
                "joins voice channels and narrates the game aloud using\n"
                "Piper TTS -- local, no cloud, no latency.\n"
                "\n"
                "  [bold white]!summon[/bold white]  -- Call the bot to your voice channel\n"
                "  [bold white]!dismiss[/bold white] -- Send the bot away\n"
                "  [bold white]!status[/bold white]  -- Check thermal vitals and uptime\n"
                "\n"
                "Game sessions on Discord use the same engines as the\n"
                "terminal -- Burnwillow, Crown & Crew, and all FITD\n"
                "systems are available via slash commands and buttons."
            ),
        ),
        TutorialPage(
            page_id="voice_guide_2",
            title="Text-to-Speech",
            content=(
                "[bold cyan]The Butler Speaks[/bold cyan]\n"
                "\n"
                "The Butler service handles TTS narration during\n"
                "active game sessions. It speaks:\n"
                "\n"
                "  [dim white]Room descriptions[/dim white] when you enter a new area\n"
                "  [dim white]Combat events[/dim white] -- attacks, damage, kills\n"
                "  [dim white]Death and victory[/dim white] -- dramatic moments\n"
                "  [dim white]NPC dialogue[/dim white] when talking to characters\n"
                "\n"
                "Voice output is managed by the voice watchdog, which\n"
                "monitors queue depth and thermal state to prevent\n"
                "overloading the Pi.\n"
                "\n"
                "[dim]TTS runs on port 5001 (Mouth service). STT\n"
                "recognition on port 5000 (Ears service).[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_VOICE_GUIDE)


# ============================================================================
# CATEGORY: burnwillow (8 modules)
# ============================================================================

# ---- 7. burnwillow_movement (4 pages, 2 interactive) -----------------------

_BURNWILLOW_MOVEMENT = TutorialModule(
    module_id="burnwillow_movement",
    title="Exploring the Dungeon",
    description="Movement, scouting, and the spatial map",
    system_id="burnwillow",
    category="burnwillow",
    pages=[
        TutorialPage(
            page_id="burnwillow_movement_1",
            title="Room Navigation",
            content=(
                "[bold cyan]A Network of Rooms[/bold cyan]\n"
                "\n"
                "The Burnwillow dungeon is a network of rooms arranged on\n"
                "a spatial grid. Rooms connect via corridors in compass\n"
                "directions.\n"
                "\n"
                "  [bold white]Movement commands:[/bold white]\n"
                "  [bold]n[/bold] [bold]s[/bold] [bold]e[/bold] [bold]w[/bold]"
                "  -- Cardinal directions\n"
                "  [bold]ne[/bold] [bold]nw[/bold] [bold]se[/bold] [bold]sw[/bold]"
                "  -- Diagonal directions\n"
                "  [bold]move <room_id>[/bold]  -- Move to a specific room\n"
                "\n"
                "Movement is [bold green]free[/bold green] -- it does not\n"
                "advance the Doom Clock. Move freely to explore.\n"
                "\n"
                "[dim]The map command shows your position and all\n"
                "discovered rooms.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="burnwillow_movement_2",
            title="Try Moving",
            content=(
                "[bold cyan]Hands On[/bold cyan]\n"
                "\n"
                "In the dungeon, you navigate by typing compass\n"
                "directions. The most common: [bold]n[/bold] for north,\n"
                "[bold]s[/bold] for south, [bold]e[/bold] for east,\n"
                "[bold]w[/bold] for west.\n"
                "\n"
                "Let's practice. Imagine you stand at the entrance\n"
                "and the corridor stretches north into the dark."
            ),
            page_type="interactive",
            prompt="Try moving north by typing: n",
            valid_inputs=["n", "north"],
            success_message="You moved north! Compass directions are the fastest way to navigate.",
        ),
        TutorialPage(
            page_id="burnwillow_movement_3",
            title="Scouting & Looking",
            content=(
                "[bold cyan]Eyes Before Feet[/bold cyan]\n"
                "\n"
                "Two commands help you gather information without risk:\n"
                "\n"
                "  [bold white]look[/bold white] (or [bold]l[/bold])\n"
                "  Describes the current room: enemies, items, exits,\n"
                "  and environmental details. Costs nothing.\n"
                "\n"
                "  [bold white]scout[/bold white]\n"
                "  Peeks at an adjacent room without entering. You see\n"
                "  what lies ahead without triggering encounters.\n"
                "\n"
                "  [bold white]map[/bold white]\n"
                "  Opens the full dungeon layout with your current\n"
                "  position marked. Discovered rooms are visible;\n"
                "  undiscovered rooms appear as fog.\n"
                "\n"
                "[dim]Always look when entering a new room. Surprises\n"
                "in Burnwillow are rarely pleasant.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="burnwillow_movement_4",
            title="Try Looking",
            content=(
                "[bold cyan]Hands On[/bold cyan]\n"
                "\n"
                "You've entered a new chamber. Dust motes drift through\n"
                "a shaft of amber light. Something scrapes in the\n"
                "shadows beyond the threshold.\n"
                "\n"
                "Before you act, survey the room."
            ),
            page_type="interactive",
            prompt="Try looking around by typing: look",
            valid_inputs=["look", "l"],
            success_message="You surveyed the room! Always look when entering a new area.",
        ),
    ],
)
TutorialRegistry.register(_BURNWILLOW_MOVEMENT)


# ---- 8. burnwillow_combat (5 pages, 1 interactive) -------------------------

_BURNWILLOW_COMBAT = TutorialModule(
    module_id="burnwillow_combat",
    title="Combat & Survival",
    description="Fighting enemies, taking damage, and staying alive",
    system_id="burnwillow",
    category="burnwillow",
    pages=[
        TutorialPage(
            page_id="burnwillow_combat_1",
            title="Entering Combat",
            content=(
                "[bold cyan]Steel Meets Rot[/bold cyan]\n"
                "\n"
                "Enemies lurk in dungeon rooms. When you enter a room\n"
                "with hostile creatures, combat begins.\n"
                "\n"
                "  [bold white]attack[/bold white] (or [bold]atk[/bold],"
                " [bold]fight[/bold])\n"
                "  Engages the first enemy in the room.\n"
                "\n"
                "  [bold white]Attack roll:[/bold white] Roll your Might dice pool\n"
                "  (up to 5d6) vs the enemy's [bold]Defense[/bold] score.\n"
                "\n"
                "  Hit? Roll your weapon's damage dice.\n"
                "  Miss? The enemy gets to strike back.\n"
                "\n"
                "[dim]Tip: Use [bold]look[/bold] before attacking to see\n"
                "enemy stats and plan your approach.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="burnwillow_combat_2",
            title="Damage & Death",
            content=(
                "[bold cyan]The Cost of War[/bold cyan]\n"
                "\n"
                "  [bold white]Dealing damage:[/bold white]\n"
                "  Damage = weapon dice roll - enemy DR (Damage Reduction).\n"
                "  Higher-tier enemies have higher DR.\n"
                "\n"
                "  [bold white]Taking damage:[/bold white]\n"
                "  Enemies roll damage against [italic]your[/italic] Defense.\n"
                "  HP = 10 + Grit modifier. When HP reaches 0, you die.\n"
                "\n"
                "  [bold white]Party combat:[/bold white]\n"
                "  Each party member acts once per round. After all\n"
                "  adventurers have acted, enemies take their turns.\n"
                "\n"
                "[bold red]Death is permanent.[/bold red] Fallen characters\n"
                "are memorialized in the Hall of Heroes."
            ),
        ),
        TutorialPage(
            page_id="burnwillow_combat_3",
            title="Special Actions",
            content=(
                "[bold cyan]Beyond the Blade[/bold cyan]\n"
                "\n"
                "Combat offers more than basic attacks:\n"
                "\n"
                "  [bold yellow]guard[/bold yellow]     -- +2 DR until your next turn.\n"
                "                  Brace against incoming damage.\n"
                "  [bold yellow]intercept[/bold yellow] -- Defend an ally. Requires a\n"
                "                  gear item with the [Intercept] trait.\n"
                "  [bold yellow]command[/bold yellow]   -- Grant bonus damage to an ally.\n"
                "                  Requires [Command] trait. Wits DC 12.\n"
                "  [bold yellow]bolster[/bold yellow]   -- Buff your next roll with bonus\n"
                "                  dice. Requires [Bolster] trait.\n"
                "  [bold yellow]triage[/bold yellow]    -- Heal a party member. Requires\n"
                "                  [Triage] trait. Wits DC 12.\n"
                "\n"
                "[dim]Special actions require specific gear traits.\n"
                "Check your inventory with [bold]inv[/bold].[/dim]"
            ),
        ),
        TutorialPage(
            page_id="burnwillow_combat_4",
            title="Retreat",
            content=(
                "[bold cyan]Discretion Over Valor[/bold cyan]\n"
                "\n"
                "Sometimes the wise choice is to run.\n"
                "\n"
                "  [bold white]retreat[/bold white] (or [bold]flee[/bold])\n"
                "  Attempt to escape combat and fall back to the\n"
                "  previous room.\n"
                "\n"
                "  [bold white]Grit check:[/bold white] DC 10.\n"
                "  [bold green]Success:[/bold green] You escape. Move to the room\n"
                "  you came from.\n"
                "  [bold red]Failure:[/bold red] Enemies get a free attack against\n"
                "  you before you can try again next round.\n"
                "\n"
                "[dim]Retreat is especially important when Doom is high\n"
                "and enemies outmatch your gear tier.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="burnwillow_combat_5",
            title="Try Attacking",
            content=(
                "[bold cyan]Hands On[/bold cyan]\n"
                "\n"
                "A [bold red]Rust Beetle[/bold red] skitters across the\n"
                "chamber floor, mandibles clicking. Its carapace is\n"
                "flaked with corrosion -- a Tier 1 creature, manageable\n"
                "with basic gear.\n"
                "\n"
                "Draw your weapon and strike."
            ),
            page_type="interactive",
            prompt="You encounter a Rust Beetle! Type: attack",
            valid_inputs=["attack", "atk", "fight"],
            success_message="You attack! In real combat, you'd roll your Might dice pool vs Defense.",
        ),
    ],
)
TutorialRegistry.register(_BURNWILLOW_COMBAT)


# ---- 9. burnwillow_gear (4 pages) ------------------------------------------

_BURNWILLOW_GEAR = TutorialModule(
    module_id="burnwillow_gear",
    title="Gear Grid & Equipment",
    description="Slots, tiers, traits, and inventory management",
    system_id="burnwillow",
    category="burnwillow",
    pages=[
        TutorialPage(
            page_id="burnwillow_gear_1",
            title="The Gear Grid",
            content=(
                "[bold cyan]Ten Slots, Infinite Possibilities[/bold cyan]\n"
                "\n"
                "Your character has ten gear slots:\n"
                "\n"
                "  [bold white]R.Hand[/bold white]     -- Primary weapon\n"
                "  [bold white]L.Hand[/bold white]     -- Off-hand weapon or shield\n"
                "  [bold white]Head[/bold white]       -- Helm, circlet, or mask\n"
                "  [bold white]Chest[/bold white]      -- Armor or vest\n"
                "  [bold white]Arms[/bold white]       -- Gloves, bracers, gauntlets\n"
                "  [bold white]Legs[/bold white]       -- Boots, greaves, leggings\n"
                "  [bold white]Shoulders[/bold white]  -- Cloaks, pauldrons, mantles\n"
                "  [bold white]Neck[/bold white]       -- Amulets, charms, pendants\n"
                "  [bold white]R.Ring[/bold white]     -- Right ring slot\n"
                "  [bold white]L.Ring[/bold white]     -- Left ring slot\n"
                "\n"
                "Each item has a [bold]tier[/bold] (1-4) that determines\n"
                "its power, and optional [bold]traits[/bold] that unlock\n"
                "special abilities in combat."
            ),
        ),
        TutorialPage(
            page_id="burnwillow_gear_2",
            title="Finding & Equipping",
            content=(
                "[bold cyan]From Floor to Grid[/bold cyan]\n"
                "\n"
                "  [bold yellow]search[/bold yellow]  -- Search the current room for\n"
                "            hidden items. Costs [bold red]+1 Doom[/bold red].\n"
                "  [bold yellow]loot[/bold yellow]    -- Pick up a visible item from the\n"
                "            room floor into your backpack.\n"
                "  [bold yellow]equip <id>[/bold yellow] -- Move a backpack item into\n"
                "               the appropriate gear slot.\n"
                "  [bold yellow]drop <id>[/bold yellow]  -- Discard an item from your\n"
                "              backpack or grid.\n"
                "\n"
                "Items found through [bold]search[/bold] appear on the\n"
                "room floor. You must [bold]loot[/bold] them, then\n"
                "[bold]equip[/bold] to wear them.\n"
                "\n"
                "[dim]Your backpack has limited space. Drop lesser gear\n"
                "to make room for upgrades.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="burnwillow_gear_3",
            title="Item Traits",
            content=(
                "[bold cyan]The Trait System[/bold cyan]\n"
                "\n"
                "Some items carry traits -- special keywords in brackets\n"
                "that unlock abilities:\n"
                "\n"
                "  [bold green][Lockpick][/bold green]\n"
                "  Opens locked doors and chests without a key.\n"
                "\n"
                "  [bold green][Intercept][/bold green]\n"
                "  Allows the [bold]intercept[/bold] combat action to\n"
                "  defend an ally, absorbing damage.\n"
                "\n"
                "  [bold green][Command][/bold green]\n"
                "  Enables the [bold]command[/bold] action: grant bonus\n"
                "  damage to a party member.\n"
                "\n"
                "  [bold green][Bolster][/bold green]\n"
                "  Enables [bold]bolster[/bold]: add bonus dice to your\n"
                "  next roll.\n"
                "\n"
                "  [bold green][Triage][/bold green]\n"
                "  Enables [bold]triage[/bold]: heal a party member."
            ),
        ),
        TutorialPage(
            page_id="burnwillow_gear_4",
            title="Tier Scaling",
            content=(
                "[bold cyan]The Weight of Quality[/bold cyan]\n"
                "\n"
                "Every item belongs to a tier that defines its power:\n"
                "\n"
                "  [dim]Tier 1[/dim] -- [bold]Rusted / Basic[/bold]\n"
                "  Scrap-quality. Minimal stats. Starting gear.\n"
                "\n"
                "  [bold white]Tier 2[/bold white] -- [bold]Reinforced / Quality[/bold]\n"
                "  Solid craftsmanship. Reliable in mid-depth rooms.\n"
                "\n"
                "  [bold yellow]Tier 3[/bold yellow] -- [bold]Masterwork / Enchanted[/bold]\n"
                "  Rare finds. Strong stats, potent trait effects.\n"
                "\n"
                "  [bold magenta]Tier 4[/bold magenta] -- [bold]Legendary / Artifact[/bold]\n"
                "  The deepest dungeon yields these. Devastating power\n"
                "  and unique abilities.\n"
                "\n"
                "[dim]Higher-tier trait items scale their effects:\n"
                "Intercept T1 = +2 DR, T4 = +5 DR + reflect.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_BURNWILLOW_GEAR)


# ---- 10. burnwillow_doom (3 pages) -----------------------------------------

_BURNWILLOW_DOOM = TutorialModule(
    module_id="burnwillow_doom",
    title="The Doom Clock",
    description="The rising threat that devours the slow",
    system_id="burnwillow",
    category="burnwillow",
    pages=[
        TutorialPage(
            page_id="burnwillow_doom_1",
            title="What is Doom?",
            content=(
                "[bold cyan]The Clock is Always Ticking[/bold cyan]\n"
                "\n"
                "Doom is a rising threat counter that measures how much\n"
                "attention the dungeon pays to your presence. The more\n"
                "you linger, the worse things get.\n"
                "\n"
                "  [bold white]Actions that raise Doom:[/bold white]\n"
                "  [bold red]+1[/bold red]  Searching a room\n"
                "  [bold red]+1[/bold red]  Resting to heal\n"
                "  [bold red]+1[/bold red]  Failed skill checks\n"
                "\n"
                "When Doom reaches certain thresholds, the dungeon\n"
                "responds -- spawning enemies, increasing danger, and\n"
                "eventually unleashing the Rot Hunter.\n"
                "\n"
                "[bold yellow]Speed is survival.[/bold yellow]"
            ),
        ),
        TutorialPage(
            page_id="burnwillow_doom_2",
            title="Doom Thresholds",
            content=(
                "[bold cyan]What Lurks at Each Threshold[/bold cyan]\n"
                "\n"
                "  [bold white] 5[/bold white]  Minor environmental shift. The dungeon\n"
                "      stirs. Descriptions grow darker.\n"
                "  [bold yellow]10[/bold yellow]  [bold]Wave 1[/bold] -- Stationary ambush enemies\n"
                "      spawn in unvisited rooms. Blight-Hawks and\n"
                "      Hollowed Scavengers lie in wait.\n"
                "  [bold yellow]13[/bold yellow]  Pressure increases. More hazards appear.\n"
                "  [bold red]15[/bold red]  [bold]Wave 2[/bold] -- Slow roaming enemies spawn\n"
                "      at the entrance. They hunt via BFS, moving\n"
                "      every 2 Doom ticks.\n"
                "  [bold red]17[/bold red]  Danger escalates further.\n"
                "  [bold magenta]20[/bold magenta]  [bold]Wave 3: Rot Hunter[/bold] -- A relentless\n"
                "      pursuer spawns. Moves every tick. Cannot be\n"
                "      outrun, only fought or evaded temporarily.\n"
                "  [bold magenta]22[/bold magenta]  Maximum threat. The dungeon is fully\n"
                "      hostile."
            ),
        ),
        TutorialPage(
            page_id="burnwillow_doom_3",
            title="Managing Doom",
            content=(
                "[bold cyan]Keeping the Clock Low[/bold cyan]\n"
                "\n"
                "  [bold green]Free actions[/bold green] (no Doom cost):\n"
                "  Moving between rooms, looking, checking inventory,\n"
                "  viewing the map, talking to NPCs.\n"
                "\n"
                "  [bold red]Costly actions[/bold red]:\n"
                "  Searching (+1), resting (+1), some failed checks.\n"
                "\n"
                "  [bold white]Strategy:[/bold white]\n"
                "  - Plan your route before committing to deep rooms.\n"
                "  - Only search rooms that look promising.\n"
                "  - Rest only when HP is critically low.\n"
                "  - Clear rooms quickly before waves spawn.\n"
                "  - Use the map to avoid backtracking.\n"
                "\n"
                "[dim]A skilled player can clear a dungeon at Doom 8-12.\n"
                "Anything above 15 is a desperate sprint.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_BURNWILLOW_DOOM)


# ---- 11. burnwillow_settlement (2 pages) -----------------------------------

_BURNWILLOW_SETTLEMENT = TutorialModule(
    module_id="burnwillow_settlement",
    title="Emberhome Settlement",
    description="The hearth between dungeon delves",
    system_id="burnwillow",
    category="burnwillow",
    pages=[
        TutorialPage(
            page_id="burnwillow_settlement_1",
            title="Welcome to Emberhome",
            content=(
                "[bold cyan]A Lantern in the Dark[/bold cyan]\n"
                "\n"
                "Between dungeon runs, you return to Emberhome -- a\n"
                "settlement built into the roots of the great Burnwillow\n"
                "tree. It is a spatial map you walk through, just like\n"
                "the dungeon.\n"
                "\n"
                "  [bold white]Buildings:[/bold white]\n"
                "  [bold yellow]Smithy[/bold yellow]     -- Weld the forge-master. Repair\n"
                "               and upgrade gear.\n"
                "  [bold yellow]Chapel[/bold yellow]     -- Rest and reflection. Lore.\n"
                "  [bold yellow]Tavern[/bold yellow]     -- Rumors, quests, and drink.\n"
                "  [bold yellow]Market[/bold yellow]     -- Birsa the merchant. Buy and sell.\n"
                "  [bold yellow]Town Gate[/bold yellow]  -- The threshold to the dungeon."
            ),
        ),
        TutorialPage(
            page_id="burnwillow_settlement_2",
            title="Settlement Actions",
            content=(
                "[bold cyan]Life Above Ground[/bold cyan]\n"
                "\n"
                "Navigate Emberhome with the same compass directions\n"
                "used in the dungeon: [bold]n[/bold] [bold]s[/bold]\n"
                "[bold]e[/bold] [bold]w[/bold].\n"
                "\n"
                "  [bold white]talk <name>[/bold white] -- Speak with an NPC.\n"
                "  Each resident has a history, a secret, and something\n"
                "  to say about recent events.\n"
                "\n"
                "  [bold white]quest[/bold white]       -- View active quests and rumors.\n"
                "  [bold white]forge[/bold white]       -- Open the smithy interface (at\n"
                "                 the Smithy building).\n"
                "  [bold white]descend[/bold white]     -- Enter the dungeon from the\n"
                "                 Town Gate.\n"
                "  [bold white]ascend[/bold white]      -- Return to Emberhome from the\n"
                "                 dungeon entrance."
            ),
        ),
    ],
)
TutorialRegistry.register(_BURNWILLOW_SETTLEMENT)


# ---- 12. burnwillow_party (3 pages) ----------------------------------------

_BURNWILLOW_PARTY = TutorialModule(
    module_id="burnwillow_party",
    title="Party System",
    description="Adventuring with allies and summoned minions",
    system_id="burnwillow",
    category="burnwillow",
    pages=[
        TutorialPage(
            page_id="burnwillow_party_1",
            title="Party Basics",
            content=(
                "[bold cyan]Strength in Numbers[/bold cyan]\n"
                "\n"
                "You can adventure with 1 to 6 party members. Each has\n"
                "their own stats:\n"
                "\n"
                "  [bold white]Might[/bold white]  -- Melee attacks, feats of strength\n"
                "  [bold white]Wits[/bold white]   -- Perception, skill checks, Defense\n"
                "  [bold white]Grit[/bold white]   -- Endurance, HP, resist effects\n"
                "  [bold white]Aether[/bold white] -- Magic, summoning, special abilities\n"
                "\n"
                "In combat, [italic]every[/italic] party member acts once\n"
                "per round before enemies take their turns. A full party\n"
                "of six gets six actions per round.\n"
                "\n"
                "[dim]HP = 10 + Grit modifier. Defense = 10 + Wits modifier.\n"
                "Slots 5 and 6 start with a Warhorn and Healer's Satchel.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="burnwillow_party_2",
            title="Party Tactics",
            content=(
                "[bold cyan]Roles and Synergy[/bold cyan]\n"
                "\n"
                "  [bold white]switch <index>[/bold white] -- Control a different party\n"
                "  member during exploration. In combat, each member\n"
                "  acts in sequence automatically.\n"
                "\n"
                "  [bold yellow]Suggested roles:[/bold yellow]\n"
                "\n"
                "  [bold]Fighter[/bold] (high Might)\n"
                "  Leads the attack. Equip the best weapon.\n"
                "\n"
                "  [bold]Scout[/bold] (high Wits)\n"
                "  High Defense, good at skill checks. Carries\n"
                "  [Lockpick] gear for locked doors.\n"
                "\n"
                "  [bold]Healer[/bold] (high Aether)\n"
                "  Equip [Triage] gear. Keep the party alive with\n"
                "  healing between fights.\n"
                "\n"
                "[dim]Mix and match -- there are no hard class restrictions.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="burnwillow_party_3",
            title="Summoned Minions",
            content=(
                "[bold cyan]Echoes of the Root-Song[/bold cyan]\n"
                "\n"
                "  [bold white]summon[/bold white] -- Create a temporary ally\n"
                "  during combat. Requires Aether.\n"
                "\n"
                "  [bold white]Minion stats:[/bold white]\n"
                "  HP = 3 + Aether modifier. Lasts 3 rounds.\n"
                "  Acts independently each combat round.\n"
                "\n"
                "Minions are disposable -- they vanish after 3 rounds\n"
                "or when killed. They do not consume Doom. Use them\n"
                "to absorb hits or deal extra damage during tough\n"
                "encounters.\n"
                "\n"
                "[dim]Only one minion can be active at a time.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_BURNWILLOW_PARTY)


# ---- 13. burnwillow_waves (2 pages) ----------------------------------------

_BURNWILLOW_WAVES = TutorialModule(
    module_id="burnwillow_waves",
    title="Wave Threat Escalation",
    description="The three waves that hunt the slow",
    system_id="burnwillow",
    category="burnwillow",
    pages=[
        TutorialPage(
            page_id="burnwillow_waves_1",
            title="Three Waves",
            content=(
                "[bold cyan]The Dungeon Wakes[/bold cyan]\n"
                "\n"
                "As Doom rises, the dungeon spawns enemies in three\n"
                "escalating waves:\n"
                "\n"
                "  [bold yellow]Wave 1[/bold yellow] (Doom 10)\n"
                "  2-3 [italic]stationary[/italic] ambush enemies appear in\n"
                "  unvisited rooms. Blight-Hawks and Hollowed Scavengers.\n"
                "  They wait. You walk into them.\n"
                "\n"
                "  [bold red]Wave 2[/bold red] (Doom 15)\n"
                "  1-2 [italic]slow roaming[/italic] enemies spawn at the\n"
                "  dungeon entrance. Blighted Sentinels and Spore-Crawlers.\n"
                "  They move toward you via BFS every 2 Doom ticks.\n"
                "\n"
                "  [bold magenta]Wave 3[/bold magenta] (Doom 20)\n"
                "  The [bold]Rot Hunter[/bold] spawns. It moves every single\n"
                "  Doom tick. Relentless. Inevitable."
            ),
        ),
        TutorialPage(
            page_id="burnwillow_waves_2",
            title="Survival Strategy",
            content=(
                "[bold cyan]Outpace the Dark[/bold cyan]\n"
                "\n"
                "  [bold green]Before Wave 1 (Doom < 10):[/bold green]\n"
                "  Move fast. Search only high-value rooms. Keep Doom\n"
                "  below 10 as long as possible.\n"
                "\n"
                "  [bold yellow]During Wave 1 (Doom 10-14):[/bold yellow]\n"
                "  Ambush enemies are stationary. Check the map before\n"
                "  entering new rooms. You can route around them.\n"
                "\n"
                "  [bold red]During Wave 2 (Doom 15-19):[/bold red]\n"
                "  Roamers are slow but persistent. Move toward your\n"
                "  objective. Do not backtrack.\n"
                "\n"
                "  [bold magenta]Wave 3 (Doom 20+):[/bold magenta]\n"
                "  The Rot Hunter cannot be outrun. Fight it, or\n"
                "  reach the exit. Every tick counts.\n"
                "\n"
                "[dim]Speed runs that clear the dungeon at Doom 8-10\n"
                "avoid all waves entirely.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_BURNWILLOW_WAVES)


# ---- 14. burnwillow_scaling (3 pages) ----------------------------------------

_BURNWILLOW_SCALING = TutorialModule(
    module_id="burnwillow_scaling",
    title="Party Scaling & AoE",
    description="How the game adapts to larger parties",
    system_id="burnwillow",
    category="burnwillow",
    pages=[
        TutorialPage(
            page_id="burnwillow_scaling_1",
            title="Enemy Scaling",
            content=(
                "[bold cyan]The Dungeon Adapts[/bold cyan]\n"
                "\n"
                "Enemies scale to your party size. A solo adventurer\n"
                "faces weakened foes; a full six-player party faces\n"
                "tougher ones.\n"
                "\n"
                "  [bold white]HP Multiplier[/bold white]\n"
                "  Solo: 0.8x  |  2 players: 0.9x  |  3-4: 1.0x\n"
                "  5 players: 1.15x  |  6 players: 1.3x\n"
                "\n"
                "  [bold white]Damage Multiplier[/bold white]\n"
                "  Solo: 0.8x  |  2 players: 0.9x  |  3-4: 1.0x\n"
                "  5 players: 1.1x  |  6 players: 1.2x\n"
                "\n"
                "This applies to room encounters, wave spawns, and\n"
                "pre-populated dungeon enemies.\n"
                "\n"
                "[dim]Scaling ensures the game remains challenging at\n"
                "any party size without becoming impossible solo.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="burnwillow_scaling_2",
            title="AoE Combat",
            content=(
                "[bold cyan]Area Attacks — 12 AoE Trait Types[/bold cyan]\n"
                "\n"
                "[bold white]Damage AoE (auto-trigger on weapon hit):[/bold white]\n"
                "  [bold yellow]Cleave[/bold yellow]     Might — 50% splash to extra targets\n"
                "  [bold yellow]Shockwave[/bold yellow]  Might 12 — Damage + Stun 1 round\n"
                "  [bold yellow]Whirlwind[/bold yellow]  Might 14 — 75% damage to ALL enemies\n"
                "  [bold yellow]Inferno[/bold yellow]    Aether 14 — Fire + Burning 2 rounds\n"
                "  [bold yellow]Tempest[/bold yellow]    Aether 12 — Lightning to 1-3 targets\n"
                "  [bold yellow]Voidgrip[/bold yellow]   Aether 14 — Necrotic + Blighted 2 rds\n"
                "\n"
                "[bold white]Utility AoE (manual combat commands):[/bold white]\n"
                "  [bold yellow]Flash[/bold yellow]      Wits 12 — Blind 1-2 enemies 2 rounds\n"
                "  [bold yellow]Snare[/bold yellow]      Wits 12 — Reduce enemy defense\n"
                "  [bold yellow]Rally[/bold yellow]      Wits 10 — +1 bonus die to all allies\n"
                "  [bold yellow]Mending[/bold yellow]    Wits 10 — Heal all party members\n"
                "  [bold yellow]Renewal[/bold yellow]    Aether 12 — HoT: 1d4/round, 3 rounds\n"
                "  [bold yellow]Aegis[/bold yellow]      Grit 10 — +tier DR to all allies 2 rds\n"
                "\n"
                "[bold red]Enemy AoE:[/bold red] Enemies carry AoE gear just like\n"
                "players (Treants wield Whirlwind, Tyrants carry\n"
                "Shockwave). Larger parties absorb AoE better.\n"
                "\n"
                "[dim]Damage AoE fires automatically on hit. Utility\n"
                "AoE requires typing the command in combat.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="burnwillow_scaling_3",
            title="Companions & Doom",
            content=(
                "[bold cyan]AI Companions & Doom Rate[/bold cyan]\n"
                "\n"
                "  [bold yellow]Companion Backfill[/bold yellow]\n"
                "  If your party has fewer than 6 members at game start,\n"
                "  you are offered AI companions to fill empty slots.\n"
                "  These are controlled by heuristic autopilot and act\n"
                "  automatically in combat and exploration.\n"
                "\n"
                "  [bold white]How to summon:[/bold white]\n"
                "  [bold]companion[/bold]   -- Type at Emberhome hub to summon\n"
                "  [bold]recap[/bold]       -- View session stats (kills, loot, rooms)\n"
                "  [bold]--companion[/bold]  -- CLI flag at launch\n"
                "  [bold]--autopilot[/bold] -- Full AI control (hands-free)\n"
                "\n"
                "  [bold red]Doom Rate Scaling[/bold red]\n"
                "  Larger parties advance the Doom Clock faster:\n"
                "  5 players: 1.1x doom rate\n"
                "  6 players: 1.2x doom rate\n"
                "\n"
                "[dim]More actions per round, but less time to use them.\n"
                "Plan your route before the clock catches up.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_BURNWILLOW_SCALING)


# ============================================================================
# CATEGORY: crown (3 modules)
# ============================================================================

# ---- 14. crown_basics (3 pages) --------------------------------------------

_CROWN_BASICS = TutorialModule(
    module_id="crown_basics",
    title="Crown & Crew Fundamentals",
    description="The journey of allegiance and consequence",
    system_id="crown",
    category="crown",
    pages=[
        TutorialPage(
            page_id="crown_basics_1",
            title="The Journey",
            content=(
                "[bold cyan]A Road With Two Endings[/bold cyan]\n"
                "\n"
                "Crown & Crew is a narrative card game played over several\n"
                "in-game days. You lead a band of travelers on a journey\n"
                "to a distant destination.\n"
                "\n"
                "  [bold white]Each day:[/bold white]\n"
                "  [bold yellow]Morning[/bold yellow]  -- A random road event shapes the\n"
                "             day's mood and may bias the sway.\n"
                "  [bold yellow]Day[/bold yellow]      -- Travel, action, and encounters.\n"
                "  [bold yellow]Evening[/bold yellow]  -- The council convenes. A dilemma\n"
                "             demands a choice.\n"
                "\n"
                "Your choices across the journey determine whether\n"
                "authority or freedom prevails at journey's end."
            ),
        ),
        TutorialPage(
            page_id="crown_basics_2",
            title="Allegiance & Sway",
            content=(
                "[bold cyan]Two Forces, One Bar[/bold cyan]\n"
                "\n"
                "Two factions vie for your loyalty:\n"
                "\n"
                "  [bold yellow]Crown[/bold yellow] -- Authority. Order. Tradition.\n"
                "  Choices that enforce law, hierarchy, and stability.\n"
                "\n"
                "  [bold blue]Crew[/bold blue] -- Freedom. Solidarity. Rebellion.\n"
                "  Choices that favor the common folk, independence,\n"
                "  and breaking from the old ways.\n"
                "\n"
                "The [bold]sway bar[/bold] tracks the balance. Each\n"
                "choice shifts it toward Crown or Crew. Morning events\n"
                "may add additional bias.\n"
                "\n"
                "Day 5's resolution depends on which side dominates."
            ),
        ),
        TutorialPage(
            page_id="crown_basics_3",
            title="Making Choices",
            content=(
                "[bold cyan]Every Vote Counts[/bold cyan]\n"
                "\n"
                "Each evening council dilemma presents two options.\n"
                "One leans Crown, the other leans Crew -- though some\n"
                "are deliberately ambiguous.\n"
                "\n"
                "  [bold white]In terminal:[/bold white] You choose directly.\n"
                "  [bold white]On Discord:[/bold white] All players vote. Majority\n"
                "  rules.\n"
                "\n"
                "Morning events add context and may shift the sway\n"
                "by +1 or -1 before the day's dilemma.\n"
                "\n"
                "There are no wrong answers -- only consequences.\n"
                "The story remembers what you chose.\n"
                "\n"
                "[dim]8 unique council dilemmas and 10 morning events\n"
                "ensure varied playthroughs.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_CROWN_BASICS)


# ---- 15. crown_allegiance (2 pages) ----------------------------------------

_CROWN_ALLEGIANCE = TutorialModule(
    module_id="crown_allegiance",
    title="The Allegiance System",
    description="Sway mechanics and endgame resolution",
    system_id="crown",
    category="crown",
    pages=[
        TutorialPage(
            page_id="crown_allegiance_1",
            title="Sway Mechanics",
            content=(
                "[bold cyan]Measuring the Wind[/bold cyan]\n"
                "\n"
                "The sway bar is a number ranging from\n"
                "[bold blue]-3[/bold blue] (full Crew) to\n"
                "[bold yellow]+3[/bold yellow] (full Crown).\n"
                "\n"
                "  [bold white]How sway changes:[/bold white]\n"
                "  - Council choices shift sway by 1-2 points.\n"
                "  - Morning events may add +1 (Crown bias) or\n"
                "    -1 (Crew bias) to the day's total.\n"
                "  - Some events are neutral (no bias).\n"
                "\n"
                "The sway bar is visible throughout the game, so\n"
                "you always know where allegiance stands.\n"
                "\n"
                "[dim]A perfectly balanced game (sway = 0) triggers\n"
                "the rarest ending: the compromise.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="crown_allegiance_2",
            title="Endgame",
            content=(
                "[bold cyan]Day 5: The Reckoning[/bold cyan]\n"
                "\n"
                "On Day 5, the journey ends and the sway bar determines\n"
                "the resolution:\n"
                "\n"
                "  [bold yellow]Crown dominant[/bold yellow] (sway > 0)\n"
                "  The authority ending. Order is restored, but at\n"
                "  what cost to those who dreamed of freedom?\n"
                "\n"
                "  [bold blue]Crew dominant[/bold blue] (sway < 0)\n"
                "  The freedom ending. The old chains break, but\n"
                "  the road ahead is uncertain and wild.\n"
                "\n"
                "  [bold green]Balanced[/bold green] (sway = 0)\n"
                "  The compromise ending. Neither side wins cleanly.\n"
                "  A fragile truce, and a story that could tip\n"
                "  either way.\n"
                "\n"
                "[dim]Each ending has unique narrative text shaped\n"
                "by the specific choices made along the way.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_CROWN_ALLEGIANCE)


# ---- 16. crown_council (2 pages) -------------------------------------------

_CROWN_COUNCIL = TutorialModule(
    module_id="crown_council",
    title="The Council Chamber",
    description="Dilemmas, morning events, and the weight of choice",
    system_id="crown",
    category="crown",
    pages=[
        TutorialPage(
            page_id="crown_council_1",
            title="Council Dilemmas",
            content=(
                "[bold cyan]The Fire Burns Low[/bold cyan]\n"
                "\n"
                "Each evening, the council gathers around the fire.\n"
                "A dilemma is presented -- a situation with no easy\n"
                "answer and two paths forward.\n"
                "\n"
                "  [bold white]Option A[/bold white] -- Often favors one faction.\n"
                "  [bold white]Option B[/bold white] -- Often favors the other.\n"
                "\n"
                "Some dilemmas are explicit (\"Enforce the Crown's\n"
                "decree\" vs \"Side with the laborers\"). Others are\n"
                "subtle, with consequences that reveal themselves\n"
                "only later.\n"
                "\n"
                "  [bold white]Terminal:[/bold white] You choose directly.\n"
                "  [bold white]Discord:[/bold white] Players vote. Majority wins.\n"
                "     Ties default to the current sway direction."
            ),
        ),
        TutorialPage(
            page_id="crown_council_2",
            title="Morning Events",
            content=(
                "[bold cyan]The Road Speaks[/bold cyan]\n"
                "\n"
                "Each morning after Day 1, a random road event occurs.\n"
                "These are short narrative moments that add flavor and\n"
                "may bias the day's sway:\n"
                "\n"
                "  [bold yellow]Crown-biased[/bold yellow] events remind the party of\n"
                "  duty, tradition, and the weight of the crown.\n"
                "\n"
                "  [bold blue]Crew-biased[/bold blue] events stir thoughts of\n"
                "  freedom, solidarity, and the open road.\n"
                "\n"
                "  [bold white]Neutral[/bold white] events add atmosphere without\n"
                "  shifting sway.\n"
                "\n"
                "10 unique morning events are available, tagged by\n"
                "bias. No event repeats within a single campaign.\n"
                "\n"
                "[dim]Day 1 always uses a neutral event to establish\n"
                "the journey's tone.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_CROWN_COUNCIL)


# ============================================================================
# CATEGORY: fitd (4 modules)
# ============================================================================

# ---- 17. fitd_core (4 pages) -----------------------------------------------

_FITD_CORE = TutorialModule(
    module_id="fitd_core",
    title="Forged in the Dark",
    description="Shared mechanics across all FITD systems",
    system_id="fitd",
    category="fitd",
    pages=[
        TutorialPage(
            page_id="fitd_core_1",
            title="What is FITD?",
            content=(
                "[bold cyan]A Family of Games[/bold cyan]\n"
                "\n"
                "Forged in the Dark is a family of tabletop RPG systems\n"
                "built on the engine created by [italic]Blades in the\n"
                "Dark[/italic]. All share a common mechanical DNA:\n"
                "\n"
                "  [bold white]Action rolls[/bold white] -- Pools of d6 dice.\n"
                "  [bold white]Stress[/bold white]       -- A resource spent to push\n"
                "                 yourself beyond normal limits.\n"
                "  [bold white]Clocks[/bold white]       -- Visual progress trackers\n"
                "                 for factions, threats, and projects.\n"
                "  [bold white]Factions[/bold white]     -- The world is alive with\n"
                "                 competing interests.\n"
                "\n"
                "C.O.D.E.X. supports three FITD systems: Blades in\n"
                "the Dark, Scum and Villainy, and Band of Blades."
            ),
        ),
        TutorialPage(
            page_id="fitd_core_2",
            title="Action Rolls",
            content=(
                "[bold cyan]The Bones Decide[/bold cyan]\n"
                "\n"
                "FITD uses pools of d6 dice. You roll and keep the\n"
                "[bold]highest single die[/bold]:\n"
                "\n"
                "  [bold green]6[/bold green]     -- Full success. You do it.\n"
                "  [bold yellow]4-5[/bold yellow]   -- Partial success. You do it, but\n"
                "          there is a complication or cost.\n"
                "  [bold red]1-3[/bold red]   -- Failure. Things go wrong.\n"
                "\n"
                "  [bold cyan]Critical (two+ 6s)[/bold cyan] -- Enhanced success.\n"
                "  Extra effect or bonus.\n"
                "\n"
                "More dice in your pool = better odds of a 6.\n"
                "\n"
                "  [bold white]Position[/bold white] (Controlled / Risky / Desperate)\n"
                "  determines the severity of failure consequences.\n"
                "  [bold white]Effect[/bold white] (Limited / Standard / Great)\n"
                "  determines how much you accomplish on success."
            ),
        ),
        TutorialPage(
            page_id="fitd_core_3",
            title="Stress & Consequences",
            content=(
                "[bold cyan]The Price of Pushing[/bold cyan]\n"
                "\n"
                "Characters accumulate [bold]stress[/bold] when they:\n"
                "\n"
                "  - [bold]Push themselves[/bold] for +1d6 on a roll.\n"
                "  - [bold]Resist[/bold] a consequence to reduce harm.\n"
                "  - Use certain [bold]special abilities[/bold].\n"
                "\n"
                "Stress fills a track (usually 9 boxes). When it\n"
                "overflows, the character suffers [bold red]trauma[/bold red]\n"
                "-- a permanent psychological scar.\n"
                "\n"
                "  [dim]Trauma examples: Cold, Haunted, Obsessed,\n"
                "  Reckless, Soft, Unstable, Vicious, Volatile.[/dim]\n"
                "\n"
                "Four traumas and the character retires. Manage stress\n"
                "carefully -- it is the most important resource in FITD."
            ),
        ),
        TutorialPage(
            page_id="fitd_core_4",
            title="Faction Clocks",
            content=(
                "[bold cyan]The World Turns[/bold cyan]\n"
                "\n"
                "Clocks are circular progress trackers (4, 6, or 8\n"
                "segments) that represent ongoing processes:\n"
                "\n"
                "  [bold white]Faction clocks[/bold white] -- A rival gang is arming\n"
                "  up (6-clock). Each session, tick one segment.\n"
                "  When full, they attack.\n"
                "\n"
                "  [bold white]Project clocks[/bold white] -- Your crew is building\n"
                "  a network of informants (8-clock). Downtime\n"
                "  actions fill segments.\n"
                "\n"
                "  [bold white]Danger clocks[/bold white] -- The spirit ward is\n"
                "  weakening (4-clock). When full, ghosts flood\n"
                "  the district.\n"
                "\n"
                "Clocks make the world feel alive. Threats and\n"
                "opportunities advance whether you act or not."
            ),
        ),
    ],
)
TutorialRegistry.register(_FITD_CORE)


# ---- 18. bitd_specifics (2 pages) ------------------------------------------

_BITD_SPECIFICS = TutorialModule(
    module_id="bitd_specifics",
    title="Blades in the Dark",
    description="Heists, scoundrels, and the haunted city of Doskvol",
    system_id="bitd",
    category="fitd",
    pages=[
        TutorialPage(
            page_id="bitd_specifics_1",
            title="Doskvol",
            content=(
                "[bold cyan]A Haunted Victorian City[/bold cyan]\n"
                "\n"
                "Doskvol is a city of perpetual darkness, hemmed in by\n"
                "lightning barriers that keep the ghosts at bay. You\n"
                "play a crew of scoundrels -- thieves, assassins, and\n"
                "occultists carving out territory.\n"
                "\n"
                "  [bold white]12 Actions:[/bold white]\n"
                "  [dim]Attune, Command, Consort, Finesse, Hunt,\n"
                "  Prowl, Skirmish, Study, Survey, Sway, Tinker,\n"
                "  Wreck[/dim]\n"
                "\n"
                "Each action covers a style of approach. Your ratings\n"
                "determine your dice pools.\n"
                "\n"
                "[dim]The setting drips with industrial gothic atmosphere:\n"
                "leviathan blood fuels the city, spirits haunt the\n"
                "canals, and every faction has a knife behind its back.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="bitd_specifics_2",
            title="Crew Types",
            content=(
                "[bold cyan]What Kind of Scoundrels?[/bold cyan]\n"
                "\n"
                "Your crew type defines your approach to the underworld:\n"
                "\n"
                "  [bold yellow]Assassins[/bold yellow]  -- Wetwork. Poison. Silence.\n"
                "  [bold yellow]Bravos[/bold yellow]     -- Street fighters. Territory.\n"
                "  [bold yellow]Cult[/bold yellow]       -- Occult power. Forbidden rites.\n"
                "  [bold yellow]Hawkers[/bold yellow]    -- Dealers. Supply and demand.\n"
                "  [bold yellow]Shadows[/bold yellow]    -- Thieves. Infiltration. Stealth.\n"
                "  [bold yellow]Smugglers[/bold yellow]  -- Contraband. Borders. Boats.\n"
                "\n"
                "Each crew has unique abilities, a preferred hunting\n"
                "ground, and a reputation that precedes them.\n"
                "\n"
                "[dim]Crew advancement unlocks new abilities, territory\n"
                "claims, and NPC contacts.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_BITD_SPECIFICS)


# ---- 19. sav_specifics (2 pages) -------------------------------------------

_SAV_SPECIFICS = TutorialModule(
    module_id="sav_specifics",
    title="Scum and Villainy",
    description="Space opera in the Procyon Sector",
    system_id="sav",
    category="fitd",
    pages=[
        TutorialPage(
            page_id="sav_specifics_1",
            title="The Procyon Sector",
            content=(
                "[bold cyan]Among the Stars[/bold cyan]\n"
                "\n"
                "Scum and Villainy takes the FITD engine into space.\n"
                "You crew a starship in the Procyon Sector -- a lawless\n"
                "stretch of space teeming with factions, bounties, and\n"
                "opportunities.\n"
                "\n"
                "The core loop: take jobs, manage your ship, deal with\n"
                "factions, and try not to get blown out of the sky.\n"
                "\n"
                "  [bold white]Your ship defines your crew:[/bold white]\n"
                "  The vessel you choose shapes your playstyle,\n"
                "  available upgrades, and the kind of jobs you take.\n"
                "\n"
                "[dim]Think Firefly meets Star Wars with the mechanical\n"
                "elegance of Blades in the Dark.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="sav_specifics_2",
            title="Spacefaring",
            content=(
                "[bold cyan]Three Ships, Three Paths[/bold cyan]\n"
                "\n"
                "  [bold yellow]Stardancer[/bold yellow] -- Smugglers and couriers.\n"
                "  Fast, agile, built for running blockades and\n"
                "  hauling contraband past Hegemony patrols.\n"
                "\n"
                "  [bold yellow]Cerberus[/bold yellow]   -- Bounty hunters and mercs.\n"
                "  Armed to the teeth. Take the dangerous jobs.\n"
                "  Track targets across the sector.\n"
                "\n"
                "  [bold yellow]Firedrake[/bold yellow]  -- Rebels and revolutionaries.\n"
                "  Fight the Hegemony. Liberate the oppressed.\n"
                "  Inspire the downtrodden.\n"
                "\n"
                "Ship upgrades and crew advancement unlock new\n"
                "capabilities. Your reputation with factions opens\n"
                "and closes doors across the sector."
            ),
        ),
    ],
)
TutorialRegistry.register(_SAV_SPECIFICS)


# ---- 20. bob_specifics (2 pages) -------------------------------------------

_BOB_SPECIFICS = TutorialModule(
    module_id="bob_specifics",
    title="Band of Blades",
    description="Military dark fantasy -- the retreating legion",
    system_id="bob",
    category="fitd",
    pages=[
        TutorialPage(
            page_id="bob_specifics_1",
            title="The Retreating Legion",
            content=(
                "[bold cyan]The Dead March Behind You[/bold cyan]\n"
                "\n"
                "Band of Blades is military dark fantasy. You command\n"
                "a legion retreating from an unstoppable undead army\n"
                "called the Cinder King's forces.\n"
                "\n"
                "This is not a game about winning. It is a game about\n"
                "what you sacrifice to survive.\n"
                "\n"
                "  [bold white]Key differences from other FITD:[/bold white]\n"
                "  - You manage a [italic]company[/italic], not a crew.\n"
                "  - Soldiers die. Permanently. Often.\n"
                "  - Resources (food, supply, morale) dwindle.\n"
                "  - Each session is a mission chosen by the Commander.\n"
                "\n"
                "[dim]The tone is desperate, somber, and deeply human.\n"
                "Small victories against impossible odds.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="bob_specifics_2",
            title="Mission Types",
            content=(
                "[bold cyan]The Commander Decides[/bold cyan]\n"
                "\n"
                "Each session, the Commander chooses a mission. The\n"
                "Marshal assigns specialists from the company roster.\n"
                "\n"
                "  [bold yellow]Assault[/bold yellow]   -- Attack an undead position.\n"
                "  High risk, high reward. May capture supplies\n"
                "  or eliminate a threat.\n"
                "\n"
                "  [bold yellow]Recon[/bold yellow]     -- Scout ahead. Map the route.\n"
                "  Lower risk, vital intelligence. Failure means\n"
                "  the legion walks into an ambush.\n"
                "\n"
                "  [bold yellow]Religious[/bold yellow] -- Consecrate ground. Recover\n"
                "  relics. Bolster morale. The Chosen leads.\n"
                "\n"
                "  [bold yellow]Supply[/bold yellow]    -- Forage, trade, or raid for\n"
                "  food and materiel. The legion starves without it.\n"
                "\n"
                "[dim]Not every mission succeeds. Failed missions have\n"
                "consequences that ripple through the campaign.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_BOB_SPECIFICS)


# ============================================================================
# CATEGORY: dnd5e (1 module)
# ============================================================================

# ---- 21. dnd5e_basics (3 pages) --------------------------------------------

_DND5E_BASICS = TutorialModule(
    module_id="dnd5e_basics",
    title="D&D 5th Edition",
    description="Classic fantasy RPG tools in C.O.D.E.X.",
    system_id="dnd5e",
    category="dnd5e",
    pages=[
        TutorialPage(
            page_id="dnd5e_basics_1",
            title="Classic Fantasy",
            content=(
                "[bold cyan]The World's Game[/bold cyan]\n"
                "\n"
                "Dungeons & Dragons 5th Edition needs no introduction.\n"
                "Classes, races, spells, monsters -- the foundation of\n"
                "modern tabletop RPGs.\n"
                "\n"
                "C.O.D.E.X. provides a suite of tools for D&D 5e play:\n"
                "\n"
                "  [bold white]Dungeon generation[/bold white] -- Procedural maps\n"
                "  with room descriptions and encounter tables.\n"
                "  [bold white]Loot tables[/bold white] -- SRD-compliant treasure\n"
                "  by CR tier.\n"
                "  [bold white]AI-assisted narration[/bold white] -- Mimir describes\n"
                "  rooms, NPCs, and events in real time.\n"
                "  [bold white]Character creation[/bold white] -- Via the Omni-Forge.\n"
                "\n"
                "[dim]C.O.D.E.X. uses SRD content only. No proprietary\n"
                "material is included.[/dim]"
            ),
        ),
        TutorialPage(
            page_id="dnd5e_basics_2",
            title="D&D in C.O.D.E.X.",
            content=(
                "[bold cyan]Your Toolkit[/bold cyan]\n"
                "\n"
                "  [bold yellow]Character Creation[/bold yellow]\n"
                "  Use the Omni-Forge (DM Tools menu). Select D&D 5e\n"
                "  as the system. Roll or assign stats, choose class\n"
                "  and race, equip starting gear.\n"
                "\n"
                "  [bold yellow]Dungeon Sessions[/bold yellow]\n"
                "  Generate a dungeon map and explore with Mimir as\n"
                "  narrator. Room descriptions, traps, and encounters\n"
                "  are procedurally generated.\n"
                "\n"
                "  [bold yellow]Loot & Encounters[/bold yellow]\n"
                "  SRD loot tables (weapons, armor, potions, general\n"
                "  goods). Treasure hoards by CR tier. NPC generators\n"
                "  for on-the-fly improvisation.\n"
                "\n"
                "  [bold yellow]Discord Integration[/bold yellow]\n"
                "  Run D&D sessions on Discord with dice rolling,\n"
                "  voice narration, and shared maps."
            ),
        ),
        TutorialPage(
            page_id="dnd5e_basics_3",
            title="Vault Resources",
            content=(
                "[bold cyan]The D&D Tome[/bold cyan]\n"
                "\n"
                "The D&D 5e vault contains source material organized\n"
                "for quick reference during play:\n"
                "\n"
                "  [bold white]Rules references[/bold white] -- Core mechanics, action\n"
                "  economy, spell rules, conditions.\n"
                "\n"
                "  [bold white]Monster entries[/bold white] -- SRD creatures with stats,\n"
                "  abilities, and encounter notes.\n"
                "\n"
                "  [bold white]Generated content[/bold white] -- Dungeons, NPCs, and\n"
                "  loot tables created during your sessions.\n"
                "\n"
                "Access via [bold]Mimir's Vault[/bold] on the main menu,\n"
                "then select the D&D 5e tome. Use [bold]ask[/bold] to\n"
                "query Mimir about any rules question -- he will search\n"
                "the tome and answer in character.\n"
                "\n"
                "[dim]Vault contents grow as you play. Generated dungeons\n"
                "and NPCs are saved automatically.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_DND5E_BASICS)


# ============================================================================
# CATEGORY: fitd — additional systems
# ============================================================================

# ---- 22. cbrpnk_basics (2 pages) ------------------------------------------

_CBRPNK_BASICS = TutorialModule(
    module_id="cbrpnk_basics",
    title="CBR+PNK",
    description="Cyberpunk heist one-shots powered by Forged in the Dark",
    system_id="cbrpnk",
    category="fitd",
    prerequisite="fitd_core",
    pages=[
        TutorialPage(
            page_id="cbrpnk_basics_1",
            title="The Sprawl Awaits",
            content=(
                "[bold cyan]CBR+PNK -- Cyberpunk Heist One-Shots[/bold cyan]\n"
                "\n"
                "You are [bold white]Runners[/bold white] -- freelance operatives\n"
                "pulling jobs in a neon-soaked megacity. Corps own everything.\n"
                "You own your chrome and your nerve.\n"
                "\n"
                "[bold yellow]Archetypes:[/bold yellow]\n"
                "  [bold white]Hacker[/bold white]  -- Grid intrusion, data theft\n"
                "  [bold white]Punk[/bold white]    -- Street muscle, direct action\n"
                "  [bold white]Fixer[/bold white]   -- Connections, negotiation\n"
                "  [bold white]Ghost[/bold white]   -- Stealth, infiltration\n"
                "\n"
                "[bold yellow]Core Actions (12 dots):[/bold yellow]\n"
                "  [dim]hack, override, scan, study, scramble, scrap,\n"
                "  skulk, shoot, attune, command, consort, sway[/dim]\n"
                "\n"
                "CBR+PNK uses the FITD d6-pool system but adds two\n"
                "unique trackers: [bold red]Heat[/bold red] (corporate response\n"
                "level) and the [bold red]Glitch Die[/bold red]."
            ),
        ),
        TutorialPage(
            page_id="cbrpnk_basics_2",
            title="Heat & Glitch",
            content=(
                "[bold cyan]The Glitch Die & Heat System[/bold cyan]\n"
                "\n"
                "[bold white]Heat[/bold white] tracks how much corporate attention\n"
                "your crew has drawn. High Heat means reinforcements,\n"
                "lockdowns, and kill-squads.\n"
                "\n"
                "[bold white]Glitch Die[/bold white] accumulates on failed rolls.\n"
                "Each failure feeds instability into the system --\n"
                "your chrome glitches, the Grid fights back, reality\n"
                "stutters. When the Glitch Die peaks, everything goes\n"
                "sideways at once.\n"
                "\n"
                "[bold yellow]Key Commands:[/bold yellow]\n"
                "  [bold white]roll_action[/bold white]   -- Roll a d6-pool action\n"
                "  [bold white]jack_in[/bold white]       -- Enter the Grid\n"
                "  [bold white]glitch_status[/bold white] -- Check Glitch Die & Heat\n"
                "  [bold white]crew_status[/bold white]   -- Runner stress overview\n"
                "\n"
                "[dim]Chrome augmentations enhance your capabilities but\n"
                "feed the Glitch Die when they malfunction. Every edge\n"
                "has a cost in the Sprawl.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_CBRPNK_BASICS)


# ============================================================================
# CATEGORY: illuminated (Illuminated Worlds)
# ============================================================================

# ---- 23. candela_basics (2 pages) -----------------------------------------

_CANDELA_BASICS = TutorialModule(
    module_id="candela_basics",
    title="Candela Obscura",
    description="Supernatural noir investigation in the Illuminated Worlds system",
    system_id="candela",
    category="illuminated",
    pages=[
        TutorialPage(
            page_id="candela_basics_1",
            title="The Circle",
            content=(
                "[bold cyan]Candela Obscura -- Supernatural Noir Investigation[/bold cyan]\n"
                "\n"
                "You belong to a [bold white]Circle[/bold white] -- a secret\n"
                "society of investigators who confront the supernatural\n"
                "threats that lurk beneath the gaslight.\n"
                "\n"
                "Candela uses the [bold yellow]Illuminated Worlds[/bold yellow]\n"
                "system -- related to Forged in the Dark but with a\n"
                "distinct damage model.\n"
                "\n"
                "[bold yellow]Roles:[/bold yellow]\n"
                "  [bold white]Face[/bold white]    -- Social manipulation, persuasion\n"
                "  [bold white]Muscle[/bold white]  -- Physical confrontation, protection\n"
                "  [bold white]Scholar[/bold white] -- Research, knowledge, deduction\n"
                "  [bold white]Slink[/bold white]   -- Stealth, subterfuge, trickery\n"
                "  [bold white]Weird[/bold white]   -- Occult sensitivity, supernatural\n"
                "\n"
                "[bold yellow]Action Drives:[/bold yellow]\n"
                "  [dim]Nerve: move, strike, control\n"
                "  Cunning: sway, read, hide\n"
                "  Intuition: survey, focus, sense[/dim]"
            ),
        ),
        TutorialPage(
            page_id="candela_basics_2",
            title="Body, Brain & Bleed",
            content=(
                "[bold cyan]The Three Marks[/bold cyan]\n"
                "\n"
                "Instead of a single stress track, Candela Obscura\n"
                "uses [bold red]three resource tracks[/bold red]:\n"
                "\n"
                "  [bold white]Body[/bold white]  (max 3) -- Physical harm, exhaustion,\n"
                "  injury. Taken from violence and exertion.\n"
                "\n"
                "  [bold white]Brain[/bold white] (max 3) -- Mental strain, fear, shock.\n"
                "  Taken from trauma and forbidden knowledge.\n"
                "\n"
                "  [bold white]Bleed[/bold white] (max 3) -- Supernatural corruption.\n"
                "  Taken from contact with magick and the unknown.\n"
                "\n"
                "When [bold red]all three tracks are full[/bold red], your\n"
                "investigator breaks -- physically wounded, mentally\n"
                "traumatized, and supernaturally corrupted.\n"
                "\n"
                "[bold yellow]Key Commands:[/bold yellow]\n"
                "  [bold white]roll_action[/bold white]    -- d6-pool action check\n"
                "  [bold white]take_mark[/bold white]      -- Mark Body/Brain/Bleed\n"
                "  [bold white]circle_status[/bold white]  -- Circle name & assignments\n"
                "  [bold white]party_status[/bold white]   -- All investigator tracks\n"
                "\n"
                "[dim]Each Catalyst (Curiosity, Duty, Revenge, Guilt)\n"
                "drives your investigator forward even as the marks\n"
                "accumulate. The question is never if you break --\n"
                "it is what you uncover before you do.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_CANDELA_BASICS)


# ============================================================================
# CATEGORY: cosmere (Cosmere Roleplaying Game)
# ============================================================================

# ---- 24. cosmere_basics (2 pages) -----------------------------------------

_COSMERE_BASICS = TutorialModule(
    module_id="cosmere_basics",
    title="Cosmere Roleplaying Game",
    description="Epic fantasy on Roshar with Radiant Orders and Surgebinding",
    system_id="stc",
    category="cosmere",
    pages=[
        TutorialPage(
            page_id="cosmere_basics_1",
            title="Welcome to Roshar",
            content=(
                "[bold cyan]Cosmere Roleplaying Game -- Stormlight Chronicles[/bold cyan]\n"
                "\n"
                "Roshar is a world of storms, Shardblades, and ancient\n"
                "oaths. You are a [bold white]Knight Radiant[/bold white] --\n"
                "bound to a spren, wielding Surges that reshape reality.\n"
                "\n"
                "[bold yellow]Three Attributes:[/bold yellow]\n"
                "  [bold white]Strength[/bold white]  -- Melee, endurance, Shardplate\n"
                "  [bold white]Speed[/bold white]     -- Agility, defense, Lashings\n"
                "  [bold white]Intellect[/bold white] -- Knowledge, Focus, Stormlight\n"
                "\n"
                "[bold yellow]Resolution:[/bold yellow] 1d20 + modifier (not d6 pools)\n"
                "  HP = 10 + STR mod | Defense = 10 + SPD mod\n"
                "  Focus = INT mod + 2 (Stormlight spending)\n"
                "\n"
                "[bold yellow]Heritage (Peoples of Roshar):[/bold yellow]\n"
                "  [dim]Alethi, Veden, Shin, Herdazian, Thaylen,\n"
                "  Azish, Listener, Iriali[/dim]\n"
                "\n"
                "C.O.D.E.X. provides full spatial dungeon crawling\n"
                "with the Cosmere adapter -- explore ruins, fight\n"
                "Voidbringers, and discover ancient fabrials."
            ),
        ),
        TutorialPage(
            page_id="cosmere_basics_2",
            title="Radiant Orders & Surges",
            content=(
                "[bold cyan]The Ten Radiant Orders[/bold cyan]\n"
                "\n"
                "Each Order grants access to [bold white]two Surges[/bold white]\n"
                "(magical abilities) and follows an Ideal:\n"
                "\n"
                "  [bold yellow]Windrunner[/bold yellow]    Adhesion + Gravitation\n"
                "    [dim]\"I will protect.\"[/dim]\n"
                "  [bold yellow]Skybreaker[/bold yellow]    Gravitation + Division\n"
                "    [dim]\"I will seek justice.\"[/dim]\n"
                "  [bold yellow]Dustbringer[/bold yellow]   Division + Abrasion\n"
                "    [dim]\"I will seek self-mastery.\"[/dim]\n"
                "  [bold yellow]Edgedancer[/bold yellow]    Abrasion + Progression\n"
                "    [dim]\"I will remember.\"[/dim]\n"
                "  [bold yellow]Truthwatcher[/bold yellow]  Progression + Illumination\n"
                "    [dim]\"I will seek truth.\"[/dim]\n"
                "  [bold yellow]Lightweaver[/bold yellow]   Illumination + Transformation\n"
                "    [dim]\"I will speak my truth.\"[/dim]\n"
                "  [bold yellow]Elsecaller[/bold yellow]    Transformation + Transportation\n"
                "    [dim]\"I will reach my potential.\"[/dim]\n"
                "  [bold yellow]Willshaper[/bold yellow]    Transportation + Cohesion\n"
                "    [dim]\"I will seek freedom.\"[/dim]\n"
                "  [bold yellow]Stoneward[/bold yellow]     Cohesion + Tension\n"
                "    [dim]\"I will be there when needed.\"[/dim]\n"
                "  [bold yellow]Bondsmith[/bold yellow]     Tension + Adhesion\n"
                "    [dim]\"I will unite.\"[/dim]\n"
                "\n"
                "[dim]Stormlight fuels your Surges. Spend Focus Points\n"
                "to enhance skills, heal, or unleash your Order's\n"
                "power. Enemies scale from Cremlings (T1) to the\n"
                "Unmade (T4) across four tiers of challenge.[/dim]"
            ),
        ),
    ],
)
TutorialRegistry.register(_COSMERE_BASICS)
