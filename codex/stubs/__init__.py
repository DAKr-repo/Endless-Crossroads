"""
codex.stubs — Permanent offline SDK stubs for discord.py.

Usage:
    from codex.stubs import install_discord_stubs
    install_discord_stubs()

    # Now discord_bot.py can be imported without the real discord.py
    from codex.bots.discord_bot import GameCommandView
"""

from codex.stubs.discord_stub import install as install_discord_stubs

__all__ = ["install_discord_stubs"]
