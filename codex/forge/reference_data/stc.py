"""
codex.forge.reference_data.stc
================================
Aggregator module that re-exports all Cosmere RPG (STC) reference data.

Sub-modules:
    stc_orders      — ORDERS, SURGE_TYPES
    stc_equipment   — SHARDBLADES, SHARDPLATE, FABRIALS, SPHERE_TYPES,
                      WEAPON_PROPERTIES
    stc_heritages   — HERITAGES
    stc_traps       — STC_TRAPS
"""

from codex.forge.reference_data.stc_orders import ORDERS, SURGE_TYPES
from codex.forge.reference_data.stc_equipment import (
    SHARDBLADES,
    SHARDPLATE,
    FABRIALS,
    SPHERE_TYPES,
    WEAPON_PROPERTIES,
)
from codex.forge.reference_data.stc_heritages import HERITAGES
from codex.forge.reference_data.stc_traps import STC_TRAPS

__all__ = [
    "ORDERS",
    "SURGE_TYPES",
    "SHARDBLADES",
    "SHARDPLATE",
    "FABRIALS",
    "SPHERE_TYPES",
    "WEAPON_PROPERTIES",
    "HERITAGES",
    "STC_TRAPS",
]
