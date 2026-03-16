# CoD:EX — Chronicles of Destiny: Endless Crossroads

A modular TTRPG engine built on a Raspberry Pi 5, designed to run tabletop RPG campaigns through terminal, Discord, and Telegram interfaces.

## Supported Game Systems

| System | Engine Type | Status |
|--------|------------|--------|
| D&D 5e | Spatial Dungeon | Playable |
| **Burnwillow** | Spatial Dungeon | Playable |
| **Crown & Crew** | Standalone | Playable |
| Blades in the Dark | FITD Scene | Playable |
| Scum and Villainy | FITD Scene | Playable |
| Band of Blades | FITD Scene | Playable |
| CBR+PNK | FITD Scene | Playable |
| Candela Obscura | FITD Scene | Playable |
| Stormlight Chronicles | Spatial Dungeon | Playable |

**Burnwillow** and **Crown & Crew** are original game systems created by [DAKr-repo](https://github.com/DAKr-repo). Burnwillow is a doom-clock-driven dungeon crawler with gear-based character identity, and Crown & Crew is a political intrigue campaign with faction diplomacy and legacy mechanics. See [docs/burnwillow/](docs/burnwillow/) for the Burnwillow SRD and game design documents.

## Features

- BSP-generated dungeon maps with Rich terminal rendering
- Multi-zone adventure modules with hand-authored content
- Party system with companions and minion summoning
- Travel system with role assignment and terrain events
- NPC dialogue powered by local LLM (Ollama)
- Forgotten Realms wiki integration via Kiwix
- Push-to-talk voice input and TTS narration
- Cross-system engine stacking (play multiple systems in one campaign)
- DM Dashboard view for game masters
- Session momentum tracking and narrative recaps

## Requirements

- Python 3.11+
- Raspberry Pi 5 (recommended) or any Linux system
- Ollama (for LLM features)
- Kiwix (optional, for wiki integration)

## Quick Start

```bash
# Clone and set up
git clone <repo-url>
cd Codex
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Discord/Telegram tokens (optional)

# Launch
python codex_agent_main.py
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | No | Discord bot token |
| `TELEGRAM_TOKEN` | No | Telegram bot token |
| `ADMIN_ID` | No | Discord admin user ID |
| `GEMINI_API_KEY` | No | Google Gemini API key |
| `KNOWLEDGE_POOL` | No | Path to wiki/ZIM storage |

## Project Structure

```
codex/
  core/       - Engine protocols, mechanics, services
  games/      - Game-specific engines (burnwillow, bridge, etc.)
  spatial/    - Map generation and rendering
  forge/      - Character creation and content tools
  bots/       - Discord and Telegram interfaces
  services/   - Voice input (ears) and TTS (mouth)
  integrations/ - Mimir LLM, FR Wiki, Tarot
config/       - JSON data files (bestiary, loot, travel events)
vault_maps/   - Adventure module blueprints
scripts/      - Build tools and utilities
tests/        - Test suite
```

## License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for details.
