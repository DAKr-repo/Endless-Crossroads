"""
CapacityManager — Universal weight / slot encumbrance service.
================================================================

Provides :func:`check_capacity` which works in either SLOTS or WEIGHT
mode and returns a status dict with ratio, remaining space, and a
human-readable warning message.
"""

from enum import Enum


class CapacityMode(Enum):
    SLOTS = "slots"
    WEIGHT = "weight"


class CapacityStatus(Enum):
    OK = "ok"
    WARNING = "warning"         # > 80%
    OVER_CAPACITY = "over"      # > 100%


def check_capacity(mode: CapacityMode, limit: float, current: float) -> dict:
    """Evaluate current load against a capacity limit.

    Args:
        mode: SLOTS or WEIGHT.
        limit: Maximum capacity (e.g. 10 slots, 50.0 lbs).
        current: Current load.

    Returns:
        Dict with keys:
            status   - CapacityStatus value string
            ratio    - float 0.0-1.0+ (current / limit)
            remaining - float (limit - current)
            message  - Human-readable warning (empty if OK)
    """
    if limit <= 0:
        ratio = 1.0 if current > 0 else 0.0
    else:
        ratio = current / limit

    remaining = limit - current

    if ratio > 1.0:
        status = CapacityStatus.OVER_CAPACITY
        message = (f"OVER-ENCUMBERED! {current}/{limit} "
                   f"{mode.value} ({ratio:.0%}). Drop items to move.")
    elif ratio > 0.8:
        status = CapacityStatus.WARNING
        message = (f"Inventory heavy: {current}/{limit} "
                   f"{mode.value} ({ratio:.0%}).")
    else:
        status = CapacityStatus.OK
        message = ""

    return {
        "status": status.value,
        "ratio": round(ratio, 3),
        "remaining": round(remaining, 2),
        "message": message,
    }
