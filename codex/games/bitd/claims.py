"""
codex/games/bitd/claims.py — Crew Claims Map
==============================================
A 15-node graph representing the crew's territory and holdings.
Each claim provides a mechanical benefit when controlled.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Claim:
    """A single claim on the crew's territory map."""

    name: str
    benefit: str          # Mechanical benefit description
    controlled: bool = False
    adjacent: List[str] = field(default_factory=list)  # Names of adjacent claims


# Default BitD claims map — Assassins/Bravos/etc all share this base map
DEFAULT_CLAIMS: List[dict] = [
    {"name": "Lair", "benefit": "Your crew's base of operations", "adjacent": ["Turf", "Vice Den", "Fixer"]},
    {"name": "Turf", "benefit": "+1 coin for scores in your turf", "adjacent": ["Lair", "Hagfish Farm", "Cover Operation"]},
    {"name": "Vice Den", "benefit": "+1d to vice rolls", "adjacent": ["Lair", "Informants", "Tavern"]},
    {"name": "Fixer", "benefit": "+2 coin for scores involving deals", "adjacent": ["Lair", "Luxury Fence", "Infirmary"]},
    {"name": "Hagfish Farm", "benefit": "Body disposal — reduce heat by 1 after a kill", "adjacent": ["Turf", "Cover Operation"]},
    {"name": "Cover Operation", "benefit": "-2 heat per score", "adjacent": ["Turf", "Hagfish Farm", "Tavern"]},
    {"name": "Informants", "benefit": "+1d to gather information rolls", "adjacent": ["Vice Den", "Cover Identity", "Tavern"]},
    {"name": "Tavern", "benefit": "+1d to consort and sway rolls on your turf", "adjacent": ["Vice Den", "Cover Operation", "Informants", "Street Fence"]},
    {"name": "Luxury Fence", "benefit": "+2 coin when selling loot", "adjacent": ["Fixer", "Infirmary"]},
    {"name": "Infirmary", "benefit": "+1d to healing rolls during downtime", "adjacent": ["Fixer", "Luxury Fence", "Cover Identity"]},
    {"name": "Cover Identity", "benefit": "+1d to deceive when using cover", "adjacent": ["Informants", "Infirmary", "Warehouse"]},
    {"name": "Street Fence", "benefit": "+1 coin when selling loot", "adjacent": ["Tavern", "Warehouse"]},
    {"name": "Warehouse", "benefit": "Store extra contraband safely", "adjacent": ["Cover Identity", "Street Fence", "Covert Drops"]},
    {"name": "Covert Drops", "benefit": "+2 coin for smuggling jobs", "adjacent": ["Warehouse", "Secret Pathways"]},
    {"name": "Secret Pathways", "benefit": "+1d to prowl when escaping", "adjacent": ["Covert Drops"]},
]


@dataclass
class ClaimsMap:
    """15-node claims graph for BitD crews.

    The Lair is always controlled from the start and cannot be lost.
    All other claims must be adjacent to a controlled node to be taken.
    """

    claims: Dict[str, Claim] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Populate from DEFAULT_CLAIMS if no claims were provided."""
        if not self.claims:
            self._build_default()

    def _build_default(self) -> None:
        """Build the default claims map with Lair pre-controlled."""
        for c in DEFAULT_CLAIMS:
            self.claims[c["name"]] = Claim(
                name=c["name"],
                benefit=c["benefit"],
                adjacent=list(c["adjacent"]),
            )
        # Lair is always controlled from the start
        if "Lair" in self.claims:
            self.claims["Lair"].controlled = True

    def claim(self, name: str) -> dict:
        """Attempt to claim a territory node.

        The target must be adjacent to at least one currently controlled node.

        Args:
            name: The name of the claim to take.

        Returns:
            Dict with 'success' (bool). On success: 'name' and 'benefit'.
            On failure: 'error' describing why the claim failed.
        """
        claim = self.claims.get(name)
        if not claim:
            return {"success": False, "error": f"Unknown claim: {name}"}
        if claim.controlled:
            return {"success": False, "error": f"{name} is already controlled"}
        # Check adjacency to any currently controlled node
        has_adjacent = any(
            self.claims.get(adj, Claim(name="", benefit="")).controlled
            for adj in claim.adjacent
        )
        if not has_adjacent:
            return {"success": False, "error": f"{name} is not adjacent to any controlled territory"}
        claim.controlled = True
        return {"success": True, "name": name, "benefit": claim.benefit}

    def lose_claim(self, name: str) -> dict:
        """Lose control of a claim (from faction action, entanglement, etc.).

        The Lair can never be lost — it's the crew's permanent base.

        Args:
            name: The name of the claim to give up.

        Returns:
            Dict with 'success' (bool). On failure: 'error' string.
        """
        claim = self.claims.get(name)
        if not claim:
            return {"success": False, "error": f"Unknown claim: {name}"}
        if name == "Lair":
            return {"success": False, "error": "Cannot lose the Lair"}
        if not claim.controlled:
            return {"success": False, "error": f"{name} is not controlled"}
        claim.controlled = False
        return {"success": True, "name": name}

    def controlled_count(self) -> int:
        """Return the number of currently controlled claims.

        Returns:
            Integer count of controlled claim nodes.
        """
        return sum(1 for c in self.claims.values() if c.controlled)

    def get_available(self) -> List[str]:
        """Return names of claims that can currently be taken.

        A claim is available if it is uncontrolled and adjacent to a
        controlled node.

        Returns:
            List of claim name strings.
        """
        available = []
        for name, claim in self.claims.items():
            if claim.controlled:
                continue
            if any(
                self.claims.get(adj, Claim(name="", benefit="")).controlled
                for adj in claim.adjacent
            ):
                available.append(name)
        return available

    def display(self) -> str:
        """Return a human-readable claims map.

        Returns:
            Multi-line string showing all claims with controlled status,
            total controlled count, and currently available claims.
        """
        lines = ["Claims Map:"]
        for name, claim in self.claims.items():
            status = "[X]" if claim.controlled else "[ ]"
            lines.append(f"  {status} {name}: {claim.benefit}")
        controlled = self.controlled_count()
        lines.append(f"\nControlled: {controlled}/{len(self.claims)}")
        available = self.get_available()
        if available:
            lines.append(f"Available: {', '.join(available)}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize controlled state to a JSON-safe dict.

        Only persists the controlled flag — structure is rebuilt from
        DEFAULT_CLAIMS on from_dict().

        Returns:
            Dict with 'claims' key mapping name -> {controlled: bool}.
        """
        return {
            "claims": {
                name: {"controlled": c.controlled}
                for name, c in self.claims.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClaimsMap":
        """Restore a ClaimsMap from a previously serialized dict.

        Rebuilds the graph structure from DEFAULT_CLAIMS, then overlays
        the persisted controlled flags.

        Args:
            data: Dict from to_dict().

        Returns:
            ClaimsMap instance with controlled flags restored.
        """
        m = cls()
        for name, state in data.get("claims", {}).items():
            if name in m.claims:
                m.claims[name].controlled = state.get("controlled", False)
        return m
