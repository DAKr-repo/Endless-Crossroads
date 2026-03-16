"""
codex.games.cbrpnk.hacking
============================
Grid/hacking subsystem for CBR+PNK.

Provides:
  - ICE dataclass: individual intrusion countermeasure electronics
  - GridState dataclass: full state of a target grid
  - GridManager: jack in, fight ICE, extract data, manage alarms
  - ICE_TYPES: base stat reference for each ICE category

ICE Types (SOURCE: cbrpnk_01_gm-guide.pdf):
  - Artemisia-I: basic network scanner, low threat
  - Defender: active firewall, deploys ICP on contact
  - Encryption: cloaks data node, must be bypassed to extract
  - I.C.P.: Intrusion Countermeasure Protocol, attacks brain directly, high threat
"""

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# =========================================================================
# ICE TYPE REFERENCE
# SOURCE: cbrpnk_01_gm-guide.pdf
#
# The 4 canonical ICE types from the PDF. Previous fabricated types
# (Patrol, Killer, Tracer, Firewall, Black) have been replaced.
# Behavior mappings preserve GridManager mechanics while using correct names.
# =========================================================================

ICE_TYPES: Dict[str, Dict[str, Any]] = {
    "Artemisia-I": {
        "description": (
            "Basic network scanner ICE. Monitors the GRID for unauthorized "
            "access signatures and alerts the system when intrusions are detected."
        ),
        "base_rating": 1,
        "behavior": "Raises alarm by 1 on contact; does not directly attack",
        "threat": "low",
        # Equivalent to old "Patrol" for GridManager mechanics
    },
    "Defender": {
        "description": (
            "Active firewall ICE that blocks unauthorized access and deploys "
            "ICP (Intrusion Countermeasure Protocol) subroutines on contact. "
            "Defender blocks data extraction and escalates threat."
        ),
        "base_rating": 3,
        "behavior": "Blocks data extraction until bypassed; on contact deploys ICP (alarm escalation + stress)",
        "threat": "medium",
        "deploys_icp": True,
        # Equivalent to old "Firewall" + "Tracer" combo for GridManager mechanics
    },
    "Encryption": {
        "description": (
            "Cloaks a local database or data node behind heavy encryption. "
            "The protected data cannot be extracted until the encryption is broken."
        ),
        "base_rating": 2,
        "behavior": "Blocks data extraction from protected nodes; does not attack",
        "threat": "medium",
        # Equivalent to old "Firewall" for GridManager mechanics
    },
    "I.C.P.": {
        "description": (
            "Intrusion Countermeasure Protocol. Attacks the Runner's brain directly "
            "through their neural interface. Causes real-world harm to jacked-in hackers. "
            "The most dangerous GRID threat."
        ),
        "base_rating": 5,
        "behavior": "On contact: deals stress equal to rating; catastrophic on failure; must be destroyed",
        "threat": "critical",
        "direct_brain_attack": True,
        # Equivalent to old "Black" + "Killer" combo for GridManager mechanics
    },
}


# =========================================================================
# ICE DATACLASS
# =========================================================================

@dataclass
class ICE:
    """An individual Intrusion Countermeasure Electronics program.

    Args:
        name: Unique identifier within the grid.
        ice_type: Category from ICE_TYPES keys.
        rating: Strength/difficulty rating (1-5).
        active: Whether the ICE is currently running.
        description: Flavor text for the ICE's appearance in the Grid.
    """
    name: str
    ice_type: str
    rating: int
    active: bool
    description: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for save/load."""
        return {
            "name": self.name,
            "ice_type": self.ice_type,
            "rating": self.rating,
            "active": self.active,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ICE":
        """Deserialize from a plain dict."""
        return cls(
            name=data["name"],
            ice_type=data["ice_type"],
            rating=data["rating"],
            active=data["active"],
            description=data.get("description", ""),
        )


# =========================================================================
# GRID STATE DATACLASS
# =========================================================================

@dataclass
class GridState:
    """Full state of a target Grid being infiltrated.

    Args:
        grid_name: Human-readable name of the target grid.
        alarm_level: Current alert status (0=silent, 5=full lockdown).
        ice_list: All ICE programs on the grid.
        data_nodes: Available data targets (list of dicts with name/value/protected keys).
        extracted_data: Data nodes successfully stolen.
        jacked_in: Whether a hacker is currently connected.
    """
    grid_name: str
    alarm_level: int = 0
    ice_list: List[ICE] = field(default_factory=list)
    data_nodes: List[Dict[str, Any]] = field(default_factory=list)
    extracted_data: List[Dict[str, Any]] = field(default_factory=list)
    jacked_in: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize full grid state for save/load."""
        return {
            "grid_name": self.grid_name,
            "alarm_level": self.alarm_level,
            "ice_list": [ice.to_dict() for ice in self.ice_list],
            "data_nodes": list(self.data_nodes),
            "extracted_data": list(self.extracted_data),
            "jacked_in": self.jacked_in,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GridState":
        """Deserialize from a plain dict."""
        gs = cls(
            grid_name=data["grid_name"],
            alarm_level=data.get("alarm_level", 0),
            ice_list=[ICE.from_dict(i) for i in data.get("ice_list", [])],
            data_nodes=data.get("data_nodes", []),
            extracted_data=data.get("extracted_data", []),
            jacked_in=data.get("jacked_in", False),
        )
        return gs


# =========================================================================
# GRID MANAGER
# =========================================================================

# ICE flavor descriptions per type
# SOURCE: cbrpnk_01_gm-guide.pdf (type names); flavor text EXPANDED for gameplay
_ICE_DESCRIPTIONS = {
    "Artemisia-I": [
        "A flickering blue polygon that sweeps methodically through the data corridors.",
        "A sphere of dull light that bobs through the architecture like a searching eye.",
        "A wire-frame hound that traces access paths with mechanical persistence.",
    ],
    "Defender": [
        "A shimmering barrier of layered code that pulses red when triggered.",
        "A dense wall of active subroutines — it blocks, traces, and retaliates.",
        "An angular construct that deploys countermeasure threads the moment it detects you.",
    ],
    "Encryption": [
        "A wall of dense cipher blocks, impenetrable and static.",
        "A shimmering barrier of layered encryption, tall as a data tower.",
        "An invisible force that simply refuses to acknowledge intrusion attempts.",
    ],
    "I.C.P.": [
        "A void construct that should not exist in any commercial grid.",
        "Something writhing and dark, encoded with kill instructions at the hardware level.",
        "An illegal ICE that hunts the physical source — through the cable, into your skull.",
    ],
}

# Data node name pool
_NODE_NAMES = [
    "Personnel Files", "Financial Ledger", "Security Protocols",
    "R&D Archives", "Executive Communications", "Supply Chain Manifest",
    "Client Database", "Surveillance Logs", "Patent Filings",
    "Black Budget Records", "Weapon Schematics", "Biometric Data",
]

_NODE_VALUES = ["Low", "Medium", "High", "Critical"]


class GridManager:
    """Manages grid generation, intrusion rolls, and alarm escalation.

    All roll-based methods accept an optional ``rng`` parameter for
    deterministic testing.
    """

    def generate_grid(
        self, difficulty: int = 1, rng: Optional[random.Random] = None
    ) -> GridState:
        """Create a random grid appropriate to the given difficulty.

        Args:
            difficulty: 1 (low-security) to 5 (military/black-site). Scales
                ICE count, rating, and node value.
            rng: Optional Random instance for deterministic generation.

        Returns:
            A populated GridState ready for infiltration.
        """
        _rng = rng or random.Random()
        difficulty = max(1, min(5, difficulty))

        # Grid names by difficulty
        grid_names = {
            1: ["SmallCo Internal", "Municipal Subnet", "Retail Data Hub"],
            2: ["Mid-Corp Archive", "Security Contractor Grid", "Logistics Network"],
            3: ["Division HQ Grid", "Pharma Research Net", "Financial Exchange"],
            4: ["Corp Tier-1 Grid", "Military Contractor Net", "Black Site Archive"],
            5: ["Nexion Core Grid", "Kuroda-Tanaka Black Ops", "Zero-Day Vault"],
        }
        grid_name = _rng.choice(grid_names[difficulty])

        # Generate ICE
        ice_count = _rng.randint(difficulty, difficulty + 2)
        ice_types = list(ICE_TYPES.keys())
        # Higher difficulty = higher chance of dangerous ICE
        # Weights map to [Artemisia-I, Defender, Encryption, I.C.P.]
        # SOURCE: cbrpnk_01_gm-guide.pdf (type names); weight distribution EXPANDED
        ice_weights = {
            1: [55, 20, 20, 5],
            2: [40, 25, 25, 10],
            3: [25, 30, 25, 20],
            4: [15, 30, 20, 35],
            5: [5, 25, 15, 55],
        }
        weights = ice_weights[difficulty]

        ice_list = []
        for i in range(ice_count):
            ice_type = _rng.choices(ice_types, weights=weights, k=1)[0]
            base = ICE_TYPES[ice_type]["base_rating"]
            rating = max(1, min(5, base + _rng.randint(0, difficulty - 1)))
            desc_pool = _ICE_DESCRIPTIONS.get(ice_type, ["An unknown ICE construct."])
            description = _rng.choice(desc_pool)
            # Some ICE starts dormant
            active = _rng.random() < (0.5 + difficulty * 0.1)
            ice_list.append(ICE(
                name=f"{ice_type}-{i + 1:02d}",
                ice_type=ice_type,
                rating=rating,
                active=active,
                description=description,
            ))

        # Generate data nodes
        node_count = _rng.randint(2, 2 + difficulty)
        data_nodes = []
        node_names = _rng.sample(_NODE_NAMES, min(node_count, len(_NODE_NAMES)))
        for j, name in enumerate(node_names):
            value_idx = min(3, _rng.randint(0, difficulty))
            protected = _rng.random() < 0.4
            data_nodes.append({
                "name": name,
                "value": _NODE_VALUES[value_idx],
                "protected": protected,
                "index": j,
            })

        return GridState(
            grid_name=grid_name,
            alarm_level=0,
            ice_list=ice_list,
            data_nodes=data_nodes,
            extracted_data=[],
            jacked_in=False,
        )

    def jack_in(
        self,
        hacker_dots: int,
        grid: GridState,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """Attempt initial intrusion into a grid.

        Args:
            hacker_dots: Number of action dice for the hacker's hack attribute.
            grid: The target GridState.
            rng: Optional Random instance.

        Returns:
            Dict with: success (bool), outcome (str), alarm_raised (bool),
            alarm_level (int), message (str).
        """
        from codex.core.services.fitd_engine import FITDActionRoll, Position, Effect
        _rng = rng or random.Random()

        roll = FITDActionRoll(
            dice_count=hacker_dots,
            position=Position.RISKY,
            effect=Effect.STANDARD,
        )
        result = roll.roll(rng=_rng)

        grid.jacked_in = True
        alarm_raised = False
        message = ""

        if result.outcome == "failure":
            grid.alarm_level = min(5, grid.alarm_level + 2)
            alarm_raised = True
            message = (
                f"Intrusion detected. Grid alarms triggered. "
                f"Alarm level: {grid.alarm_level}. ICE activating."
            )
            # Activate dormant ICE on intrusion failure
            for ice in grid.ice_list:
                if not ice.active:
                    ice.active = True
        elif result.outcome == "mixed":
            grid.alarm_level = min(5, grid.alarm_level + 1)
            alarm_raised = True
            message = (
                f"You're in, but something pinged. "
                f"Alarm level: {grid.alarm_level}."
            )
        elif result.outcome in ("success", "critical"):
            message = "Clean entry. The grid opens before you like a neon cathedral."

        return {
            "success": result.outcome in ("mixed", "success", "critical"),
            "outcome": result.outcome,
            "alarm_raised": alarm_raised,
            "alarm_level": grid.alarm_level,
            "message": message,
            "dice": result.all_dice,
        }

    def intrusion_roll(
        self,
        hacker_dots: int,
        target_ice: ICE,
        grid: GridState,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """Attempt to neutralize or bypass a specific ICE.

        Args:
            hacker_dots: Number of action dice for the hacker's hack attribute.
            target_ice: The ICE being attacked.
            grid: The parent GridState (alarm may escalate).
            rng: Optional Random instance.

        Returns:
            Dict with: success (bool), outcome (str), ice_disabled (bool),
            alarm_level (int), stress_cost (int), message (str).
        """
        from codex.core.services.fitd_engine import FITDActionRoll, Position, Effect
        _rng = rng or random.Random()

        # ICE rating affects position
        if target_ice.rating <= 2:
            position = Position.CONTROLLED
        elif target_ice.rating <= 4:
            position = Position.RISKY
        else:
            position = Position.DESPERATE

        roll = FITDActionRoll(
            dice_count=hacker_dots,
            position=position,
            effect=Effect.STANDARD,
        )
        result = roll.roll(rng=_rng)

        ice_disabled = False
        stress_cost = 0
        message = ""

        if result.outcome == "critical":
            target_ice.active = False
            ice_disabled = True
            message = f"Perfect splice. {target_ice.name} deactivated without a trace."
        elif result.outcome == "success":
            target_ice.active = False
            ice_disabled = True
            grid.alarm_level = min(5, grid.alarm_level + 1)
            message = f"{target_ice.name} neutralized. Minor alert ripple — alarm at {grid.alarm_level}."
        elif result.outcome == "mixed":
            # Partial: ICE still active but wounded
            stress_cost = 1
            grid.alarm_level = min(5, grid.alarm_level + 1)
            message = (
                f"{target_ice.name} damaged but still active. "
                f"You take 1 stress from feedback. Alarm at {grid.alarm_level}."
            )
        else:  # failure
            stress_cost = target_ice.rating
            grid.alarm_level = min(5, grid.alarm_level + 2)
            message = (
                f"{target_ice.name} hit you back. "
                f"Take {stress_cost} stress. Alarm at {grid.alarm_level}."
            )

        return {
            "success": result.outcome in ("mixed", "success", "critical"),
            "outcome": result.outcome,
            "ice_disabled": ice_disabled,
            "alarm_level": grid.alarm_level,
            "stress_cost": stress_cost,
            "message": message,
            "dice": result.all_dice,
        }

    def extract_data(
        self, grid: GridState, node_index: int
    ) -> Dict[str, Any]:
        """Extract data from a target node.

        Extraction requires no active Firewall ICE adjacent to the node.
        Protected nodes require all active ICE to be cleared.

        Args:
            grid: The target GridState.
            node_index: Index into grid.data_nodes.

        Returns:
            Dict with: success (bool), node (dict or None), message (str).
        """
        if not grid.jacked_in:
            return {"success": False, "node": None, "message": "Not jacked in."}

        if node_index < 0 or node_index >= len(grid.data_nodes):
            return {
                "success": False,
                "node": None,
                "message": f"No data node at index {node_index}.",
            }

        node = grid.data_nodes[node_index]

        # Check for blocking ICE
        # Encryption ICE blocks all data extraction.
        # Defender ICE blocks extraction from protected nodes (via its ICP deployment).
        # SOURCE: cbrpnk_01_gm-guide.pdf
        active_ice = [i for i in grid.ice_list if i.active]
        active_encryption = [
            i for i in active_ice if i.ice_type in ("Encryption", "Defender")
        ]

        if node.get("protected") and active_ice:
            active_names = ", ".join(i.name for i in active_ice)
            return {
                "success": False,
                "node": None,
                "message": (
                    f"Node is protected. Active ICE blocks extraction: {active_names}."
                ),
            }

        if active_encryption:
            enc_names = ", ".join(i.name for i in active_encryption)
            return {
                "success": False,
                "node": None,
                "message": (
                    f"Encryption/Defender ICE is blocking: {enc_names}. "
                    "Neutralize it first."
                ),
            }

        # Extract
        extracted = grid.data_nodes.pop(node_index)
        grid.extracted_data.append(extracted)
        return {
            "success": True,
            "node": extracted,
            "message": (
                f"Data extracted: '{extracted['name']}' "
                f"(value: {extracted['value']})."
            ),
        }

    def grid_alarm_tick(self, grid: GridState) -> Dict[str, Any]:
        """Advance the grid's alarm escalation by one tick.

        Each tick: if alarm >= 3, activate dormant ICE. If alarm >= 5,
        generate a new Killer ICE.

        Args:
            grid: The target GridState.

        Returns:
            Dict with: alarm_level (int), new_ice (ICE or None), message (str).
        """
        new_ice: Optional[ICE] = None
        messages = []

        if grid.alarm_level >= 5:
            # Spawn reinforcement ICE — at full lockdown, the grid deploys I.C.P.
            # SOURCE: cbrpnk_01_gm-guide.pdf (I.C.P. is the lethal response ICE)
            ice_id = len(grid.ice_list) + 1
            new_ice = ICE(
                name=f"ICP-R{ice_id:02d}",
                ice_type="I.C.P.",
                rating=min(5, 3 + (grid.alarm_level - 5)),
                active=True,
                description="Emergency I.C.P. deployed — it is already targeting your neural link.",
            )
            grid.ice_list.append(new_ice)
            messages.append(
                f"LOCKDOWN: I.C.P. deployed ({new_ice.name}, rating {new_ice.rating})."
            )
        elif grid.alarm_level >= 3:
            # Activate dormant ICE
            dormant = [i for i in grid.ice_list if not i.active]
            if dormant:
                dormant[0].active = True
                messages.append(
                    f"Alarm escalation: {dormant[0].name} ({dormant[0].ice_type}) has activated."
                )
            else:
                messages.append("Alarm rising — no dormant ICE remaining.")
        else:
            messages.append(f"Grid at alert level {grid.alarm_level}. Monitoring intensifying.")

        return {
            "alarm_level": grid.alarm_level,
            "new_ice": new_ice,
            "message": " ".join(messages) if messages else "Grid tick processed.",
        }

    def jack_out(self, grid: GridState) -> Dict[str, Any]:
        """Safely disconnect from the grid.

        Args:
            grid: The active GridState.

        Returns:
            Dict with: success (bool), extracted_count (int), message (str).
        """
        if not grid.jacked_in:
            return {
                "success": False,
                "extracted_count": 0,
                "message": "Not currently jacked in.",
            }

        grid.jacked_in = False
        count = len(grid.extracted_data)
        alarm = grid.alarm_level

        if alarm >= 4:
            message = (
                f"Emergency disconnect. You pulled out under fire. "
                f"{count} data package(s) secured. Alarm level: {alarm}."
            )
        elif alarm >= 2:
            message = (
                f"Tactical withdrawal. {count} data package(s) extracted. "
                f"Grid will remember your signature."
            )
        else:
            message = (
                f"Clean exit. {count} data package(s) secured. "
                "No trace left behind."
            )

        return {
            "success": True,
            "extracted_count": count,
            "message": message,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize manager state (stateless — returns empty dict)."""
        return {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GridManager":
        """Deserialize manager (stateless — returns new instance)."""
        return cls()


__all__ = ["ICE", "GridState", "GridManager", "ICE_TYPES"]
