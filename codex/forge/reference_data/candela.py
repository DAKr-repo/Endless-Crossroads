"""
codex.forge.reference_data.candela
====================================
Aggregator module that re-exports all Candela Obscura reference data.

Sub-modules:
    candela_roles      — ROLES, CATALYSTS
    candela_phenomena  — PHENOMENA
    candela_circles    — CIRCLE_ABILITIES, TRUST_MECHANICS, NPC_RELATIONSHIPS
"""

from codex.forge.reference_data.candela_roles import ROLES, CATALYSTS
from codex.forge.reference_data.candela_phenomena import PHENOMENA
from codex.forge.reference_data.candela_circles import (
    CIRCLE_ABILITIES,
    TRUST_MECHANICS,
    NPC_RELATIONSHIPS,
)

__all__ = [
    "ROLES",
    "CATALYSTS",
    "PHENOMENA",
    "CIRCLE_ABILITIES",
    "TRUST_MECHANICS",
    "NPC_RELATIONSHIPS",
]
