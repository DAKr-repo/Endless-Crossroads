"""
codex/forge/omni_forge.py — The Dynamic Table & Content Engine (WO-V14.0)
=========================================================================
Deterministic SRD table rolls for loot, lifepaths, and trinkets.
Falls back to AI (Mimir/Architect) only for tables not in the local pool.

core is optional — deterministic ops work without AI.

Author: Codex Team (WO 089, WO-V14.0)
"""

import random
from codex.forge.source_scanner import scan_content_availability
from codex.forge.loot_tables import (
    roll_treasure_hoard,
    roll_lifepath,
    roll_trinket,
    roll_on_srd_table,
    list_tables as _list_tables,
)


class OmniForge:
    """Dynamic content generator — deterministic tables first, AI fallback."""

    def __init__(self, core=None):
        self.core = core
        self.sources = scan_content_availability()

    def refresh_sources(self):
        """Re-scan vault in case PDFs were added at runtime."""
        self.sources = scan_content_availability()

    @staticmethod
    def list_tables() -> list[str]:
        """Return available deterministic table names."""
        return _list_tables()

    async def roll_on_table(self, source_key: str, table_name: str, context: str = "") -> str:
        """Roll on a table — tries deterministic SRD first, then AI fallback.

        Args:
            source_key: "Xanathar", "DMG", "Tasha", "Core", etc.
            table_name: "Life Events", "Trinkets", "Wild Magic Surge"
            context: e.g. "Level 5 Wizard" (helps Mimir contextualize)
        """
        # Try deterministic SRD table first
        result = roll_on_srd_table(table_name)
        if result is not None:
            return f"Roll ({table_name})\n{result}"

        # AI fallback
        if not self.core:
            return f"Table '{table_name}' not found. Available: {', '.join(self.list_tables())}"

        key_map = {"DMG": "Core", "PHB": "Core"}
        resolved = key_map.get(source_key, source_key)

        if resolved not in self.sources and resolved != "Core":
            return f"Source '{source_key}' not found in Vault."

        die_roll = random.randint(1, 100)

        prompt = (
            f"Act as a Dungeon Master referencing {source_key}. "
            f"I have rolled a {die_roll} on the '{table_name}' table. "
            f"{'Context: ' + context + '. ' if context else ''}"
            f"Provide the specific result from the book, "
            f"then add a 1-sentence flavor interpretation."
        )

        try:
            response = await self.core.architect.invoke_model(
                prompt,
                system_prompt=(
                    "You are a Rules Lawyer and Reference Tool. "
                    "Quote rules and tables accurately. Do not hallucinate mechanics."
                )
            )
            return f"Roll: {die_roll} ({table_name})\n{response.content}"
        except Exception as e:
            return f"Roll: {die_roll} ({table_name})\n[AI unavailable: {e}]"

    async def generate_lifepath(self, character_summary: str = "") -> str:
        """Generate a lifepath — deterministic SRD tables, no AI needed."""
        return roll_lifepath()

    async def quick_loot(self, cr_range: str = "0-4") -> str:
        """Roll on treasure hoard table — deterministic, no AI needed."""
        return roll_treasure_hoard(cr_range)

    async def custom_query(self, table_name: str, context: str = "") -> str:
        """Try deterministic SRD table first, fall back to AI."""
        result = roll_on_srd_table(table_name)
        if result is not None:
            return f"Roll ({table_name})\n{result}"
        # AI fallback for unknown tables
        return await self.roll_on_table("Core", table_name, context)
