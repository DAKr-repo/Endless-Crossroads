"""
codex.games.crown.politics
============================
Political simulation subsystem for Crown & Crew.

Classes:
    FactionInfluenceTracker  — Track and modify faction influence/territory/resources
    AllianceSystem           — Form, break, and query inter-faction alliances
    PoliticalGravityEngine   — Orchestrate council votes, power balance, and faction actions

All classes support to_dict() / from_dict() for save-load round-trips.
"""

import random
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# CONSTANTS
# =============================================================================

INFLUENCE_MIN: int = 0
INFLUENCE_MAX: int = 10

RELATIONSHIP_STATUSES = frozenset(["alliance", "rivalry", "tension", "neutral"])

# Faction action types
ACTION_TYPES = frozenset([
    "propaganda",   # influence gain
    "sabotage",     # target loses resources
    "recruit",      # soldiers gain
    "bribe",        # gold transfer to influence
    "intimidate",   # tension → rivalry
    "negotiate",    # tension → neutral
])


# =============================================================================
# FACTION INFLUENCE TRACKER
# =============================================================================

class FactionInfluenceTracker:
    """
    Tracks influence, territory, and resource state for all active factions.

    Initialized from FACTIONS reference data or a custom dict.
    All modifications go through the public API to ensure capping.
    """

    def __init__(self, factions: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        """
        Args:
            factions: Optional dict mapping faction name → initial state dict.
                      If None, loads from reference data.
        """
        if factions is None:
            from codex.forge.reference_data.crown_factions import FACTIONS
            factions = FACTIONS

        # Deep-copy mutable fields to avoid mutating reference data
        self.factions: Dict[str, Dict[str, Any]] = {}
        for name, data in factions.items():
            self.factions[name] = {
                "influence": int(data.get("influence", 5)),
                "territory": list(data.get("territory", [])),
                "resources": dict(data.get("resources", {})),
                "agenda_progress": {
                    goal: False
                    for goal in data.get("agenda", [])
                },
                "description": data.get("description", ""),
                "ideology": data.get("ideology", ""),
            }

    # ── Influence ─────────────────────────────────────────────────────────

    def shift_influence(self, faction_name: str, amount: int) -> Dict[str, Any]:
        """
        Modify a faction's influence by amount (positive or negative).

        Returns:
            dict with keys: faction, old_influence, new_influence, capped (bool)
        """
        if faction_name not in self.factions:
            return {"error": f"Unknown faction: {faction_name}"}

        faction = self.factions[faction_name]
        old = faction["influence"]
        raw = old + amount
        new = max(INFLUENCE_MIN, min(INFLUENCE_MAX, raw))
        faction["influence"] = new

        return {
            "faction": faction_name,
            "old_influence": old,
            "new_influence": new,
            "delta": new - old,
            "capped": raw != new,
        }

    def get_dominant_faction(self) -> str:
        """Return the faction name with the highest influence. Ties broken alphabetically."""
        if not self.factions:
            return ""
        return max(self.factions.keys(), key=lambda n: (self.factions[n]["influence"], n))

    # ── Territory ─────────────────────────────────────────────────────────

    def transfer_territory(
        self, from_faction: str, to_faction: str, district: str
    ) -> Dict[str, Any]:
        """
        Move a district from one faction's territory to another's.

        Returns:
            dict with keys: success (bool), from_faction, to_faction, district, reason
        """
        if from_faction not in self.factions:
            return {"success": False, "reason": f"Unknown faction: {from_faction}"}
        if to_faction not in self.factions:
            return {"success": False, "reason": f"Unknown faction: {to_faction}"}

        from_territory = self.factions[from_faction]["territory"]
        if district not in from_territory:
            return {
                "success": False,
                "reason": f"{district} not in {from_faction}'s territory",
            }

        from_territory.remove(district)
        self.factions[to_faction]["territory"].append(district)

        return {
            "success": True,
            "from_faction": from_faction,
            "to_faction": to_faction,
            "district": district,
        }

    # ── Resources ─────────────────────────────────────────────────────────

    def resource_action(
        self,
        faction_name: str,
        resource: str,
        action: str = "gain",
        amount: int = 1,
    ) -> Dict[str, Any]:
        """
        Gain or spend a faction resource.

        Args:
            faction_name: Target faction.
            resource: Resource key (gold / soldiers / spies / influence).
            action: "gain" or "spend".
            amount: Integer amount.

        Returns:
            dict with keys: faction, resource, action, old, new, success (bool)
        """
        if faction_name not in self.factions:
            return {"success": False, "error": f"Unknown faction: {faction_name}"}

        resources = self.factions[faction_name]["resources"]
        old = resources.get(resource, 0)

        if action == "gain":
            new = max(0, min(10, old + amount))
        elif action == "spend":
            if old < amount:
                return {
                    "success": False,
                    "faction": faction_name,
                    "resource": resource,
                    "reason": f"Insufficient {resource} ({old} < {amount})",
                }
            new = old - amount
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

        resources[resource] = new
        return {
            "success": True,
            "faction": faction_name,
            "resource": resource,
            "action": action,
            "old": old,
            "new": new,
        }

    # ── Status ─────────────────────────────────────────────────────────────

    def get_faction_status(self, name: str) -> Dict[str, Any]:
        """Return the full state dict for a faction."""
        if name not in self.factions:
            return {"error": f"Unknown faction: {name}"}
        return {
            "name": name,
            **self.factions[name],
        }

    def get_all_statuses(self) -> List[Dict[str, Any]]:
        """Return a sorted list of faction status dicts (by influence, descending)."""
        statuses = [self.get_faction_status(n) for n in self.factions]
        return sorted(statuses, key=lambda s: s.get("influence", 0), reverse=True)

    # ── Serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {"factions": {k: dict(v) for k, v in self.factions.items()}}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactionInfluenceTracker":
        tracker = cls.__new__(cls)
        tracker.factions = {}
        for name, fdata in data.get("factions", {}).items():
            tracker.factions[name] = dict(fdata)
        return tracker


# =============================================================================
# ALLIANCE SYSTEM
# =============================================================================

class AllianceSystem:
    """
    Manages inter-faction relationships.

    Relationships are stored as a dict keyed by frozenset pairs (unordered).
    History records all changes for narrative trace-back.
    """

    def __init__(self) -> None:
        # Keyed by tuple(sorted([faction_a, faction_b])) → status string
        self.alliances: Dict[Tuple[str, str], str] = {}
        self.alliance_history: List[Dict[str, Any]] = []
        self._load_defaults()

    def _sorted_pair(self, a: str, b: str) -> Tuple[str, str]:
        return tuple(sorted([a, b]))  # type: ignore[return-value]

    def _load_defaults(self) -> None:
        """Seed initial relationships from reference data."""
        try:
            from codex.forge.reference_data.crown_factions import FACTION_RELATIONSHIPS
            for faction_a, relations in FACTION_RELATIONSHIPS.items():
                for faction_b, status in relations.items():
                    pair = self._sorted_pair(faction_a, faction_b)
                    # Only write if not already set (avoids double-writing symmetric pairs)
                    if pair not in self.alliances:
                        self.alliances[pair] = status
        except ImportError:
            pass

    def _set_relationship(
        self, faction_a: str, faction_b: str, status: str, reason: str = ""
    ) -> Dict[str, Any]:
        """Internal: set a relationship and record in history."""
        pair = self._sorted_pair(faction_a, faction_b)
        old_status = self.alliances.get(pair, "neutral")
        self.alliances[pair] = status
        record = {
            "faction_a": faction_a,
            "faction_b": faction_b,
            "old_status": old_status,
            "new_status": status,
            "reason": reason,
        }
        self.alliance_history.append(record)
        return record

    # ── Relationship Mutations ─────────────────────────────────────────────

    def form_alliance(self, faction_a: str, faction_b: str) -> Dict[str, Any]:
        """Establish an alliance between two factions."""
        return self._set_relationship(faction_a, faction_b, "alliance", "Alliance formed")

    def break_alliance(self, faction_a: str, faction_b: str, reason: str = "") -> Dict[str, Any]:
        """Break an existing alliance; defaults to tension."""
        return self._set_relationship(
            faction_a, faction_b, "tension", reason or "Alliance dissolved"
        )

    def declare_rivalry(self, faction_a: str, faction_b: str) -> Dict[str, Any]:
        """Escalate relationship to active rivalry."""
        return self._set_relationship(faction_a, faction_b, "rivalry", "Rivalry declared")

    def normalize(self, faction_a: str, faction_b: str, reason: str = "") -> Dict[str, Any]:
        """Move relationship toward neutral."""
        return self._set_relationship(
            faction_a, faction_b, "neutral", reason or "Relations normalized"
        )

    # ── Queries ────────────────────────────────────────────────────────────

    def get_relationship(self, faction_a: str, faction_b: str) -> str:
        """Return the current relationship status between two factions."""
        pair = self._sorted_pair(faction_a, faction_b)
        return self.alliances.get(pair, "neutral")

    def get_allies(self, faction_name: str) -> List[str]:
        """Return list of factions in alliance with faction_name."""
        allies = []
        for pair, status in self.alliances.items():
            if status == "alliance" and faction_name in pair:
                other = pair[0] if pair[1] == faction_name else pair[1]
                allies.append(other)
        return allies

    def get_enemies(self, faction_name: str) -> List[str]:
        """Return list of factions in rivalry with faction_name."""
        enemies = []
        for pair, status in self.alliances.items():
            if status == "rivalry" and faction_name in pair:
                other = pair[0] if pair[1] == faction_name else pair[1]
                enemies.append(other)
        return enemies

    def check_alliance_stability(self, rng: Optional[random.Random] = None) -> Dict[str, Any]:
        """
        Randomly fluctuate one tension relationship per call.

        Returns:
            dict with keys: changed (bool), faction_a, faction_b, old_status, new_status
        """
        _rng = rng or random
        tension_pairs = [
            pair for pair, status in self.alliances.items() if status == "tension"
        ]
        if not tension_pairs:
            return {"changed": False, "reason": "No tense relationships to fluctuate"}

        pair = _rng.choice(tension_pairs)
        new_status = _rng.choice(["neutral", "rivalry"])
        result = self._set_relationship(
            pair[0], pair[1], new_status,
            "Political pressure caused relationship to shift"
        )
        result["changed"] = True
        return result

    # ── Serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alliances": {
                f"{k[0]}|{k[1]}": v for k, v in self.alliances.items()
            },
            "alliance_history": list(self.alliance_history),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AllianceSystem":
        system = cls.__new__(cls)
        system.alliances = {}
        system.alliance_history = list(data.get("alliance_history", []))
        for key, status in data.get("alliances", {}).items():
            parts = key.split("|", 1)
            if len(parts) == 2:
                pair = tuple(sorted(parts))
                system.alliances[pair] = status  # type: ignore[assignment]
        return system


# =============================================================================
# POLITICAL GRAVITY ENGINE
# =============================================================================

class PoliticalGravityEngine:
    """
    Orchestrates the macro-political simulation.

    Combines FactionInfluenceTracker and AllianceSystem into a unified
    interface, and tracks the overall power balance on a -1.0 to +1.0 scale
    (negative = Crown-dominant, positive = Crew-dominant).
    """

    def __init__(
        self,
        influence_tracker: Optional[FactionInfluenceTracker] = None,
        alliance_system: Optional[AllianceSystem] = None,
    ) -> None:
        self.influence_tracker = influence_tracker or FactionInfluenceTracker()
        self.alliance_system = alliance_system or AllianceSystem()
        # Power balance: -1.0 (Crown absolute) to +1.0 (Crew absolute)
        self.power_balance: float = 0.0

    # ── Council Vote ───────────────────────────────────────────────────────

    def council_vote(
        self,
        proposal: str,
        factions_voting: Dict[str, str],
        sway_modifier: int = 0,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """
        Simulate a council vote with faction influence weights.

        Args:
            proposal: Description of what is being voted on.
            factions_voting: dict mapping faction_name → "crown" | "crew"
            sway_modifier: Additional weight on the player's side (from sway).
            rng: Optional Random for deterministic testing.

        Returns:
            dict with keys: proposal, winner, crown_weight, crew_weight,
                            margin, participating_factions, flavor
        """
        _rng = rng or random
        crown_weight = 0
        crew_weight = 0
        participating = []

        for faction_name, side in factions_voting.items():
            influence = self.influence_tracker.factions.get(
                faction_name, {}
            ).get("influence", 1)
            # Add small random variance to simulate political uncertainty
            weight = influence + _rng.randint(-1, 1)
            weight = max(1, weight)

            participating.append({
                "faction": faction_name,
                "side": side,
                "weight": weight,
            })

            if side == "crown":
                crown_weight += weight
            elif side == "crew":
                crew_weight += weight

        # Apply player sway modifier
        if sway_modifier > 0:
            crew_weight += sway_modifier
        elif sway_modifier < 0:
            crown_weight += abs(sway_modifier)

        if crown_weight > crew_weight:
            winner = "crown"
        elif crew_weight > crown_weight:
            winner = "crew"
        else:
            winner = _rng.choice(["crown", "crew"])

        margin = abs(crown_weight - crew_weight)
        if margin >= 8:
            flavor = f"The council's voice is unanimous. {winner.upper()} carries the day without challenge."
        elif margin >= 4:
            flavor = f"A clear majority for {winner.upper()}. Dissenters are noted but overruled."
        elif margin >= 2:
            flavor = f"{winner.upper()} prevails, but the opposition was vocal. The wound lingers."
        else:
            flavor = f"A razor-thin vote for {winner.upper()}. Half the council is already planning revenge."

        # Update power balance based on result
        shift = 0.05 if winner == "crew" else -0.05
        self.power_balance = max(-1.0, min(1.0, self.power_balance + shift))

        return {
            "proposal": proposal,
            "winner": winner,
            "crown_weight": crown_weight,
            "crew_weight": crew_weight,
            "margin": margin,
            "participating_factions": participating,
            "flavor": flavor,
        }

    # ── Power Shift ────────────────────────────────────────────────────────

    def power_shift(self, amount: float, reason: str = "") -> Dict[str, Any]:
        """
        Directly shift the power balance by amount.

        Args:
            amount: Float delta. Positive = toward Crew, negative = toward Crown.
            reason: Narrative reason for the shift.

        Returns:
            dict with keys: old_balance, new_balance, reason, dominant
        """
        old = self.power_balance
        self.power_balance = max(-1.0, min(1.0, old + amount))

        if self.power_balance < -0.3:
            dominant = "Crown"
        elif self.power_balance > 0.3:
            dominant = "Crew"
        else:
            dominant = "Contested"

        return {
            "old_balance": round(old, 3),
            "new_balance": round(self.power_balance, 3),
            "reason": reason,
            "dominant": dominant,
        }

    # ── Gravity Calculation ────────────────────────────────────────────────

    def calculate_gravity(self) -> Dict[str, Any]:
        """
        Return a comprehensive political landscape summary.

        Returns:
            dict with power_balance, dominant_faction, alliance_count,
                  rivalry_count, faction_summary
        """
        dominant_faction = self.influence_tracker.get_dominant_faction()
        all_statuses = self.influence_tracker.get_all_statuses()

        alliance_count = sum(
            1 for s in self.alliance_system.alliances.values() if s == "alliance"
        )
        rivalry_count = sum(
            1 for s in self.alliance_system.alliances.values() if s == "rivalry"
        )

        if self.power_balance < -0.5:
            balance_label = "Crown Dominant"
        elif self.power_balance < -0.2:
            balance_label = "Crown Favored"
        elif self.power_balance < 0.2:
            balance_label = "Contested"
        elif self.power_balance < 0.5:
            balance_label = "Crew Favored"
        else:
            balance_label = "Crew Dominant"

        return {
            "power_balance": round(self.power_balance, 3),
            "balance_label": balance_label,
            "dominant_faction": dominant_faction,
            "alliance_count": alliance_count,
            "rivalry_count": rivalry_count,
            "faction_summary": [
                {
                    "name": s["name"],
                    "influence": s["influence"],
                    "territory_count": len(s.get("territory", [])),
                }
                for s in all_statuses
            ],
        }

    # ── Faction Action ─────────────────────────────────────────────────────

    def faction_action(
        self,
        faction_name: str,
        action_type: str,
        target: str = "",
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """
        Execute an autonomous faction action.

        Args:
            faction_name: Acting faction.
            action_type: One of ACTION_TYPES.
            target: Target faction name (required for some actions).
            rng: Optional Random for deterministic testing.

        Returns:
            dict describing the action's outcome.
        """
        _rng = rng or random

        if faction_name not in self.influence_tracker.factions:
            return {"success": False, "error": f"Unknown faction: {faction_name}"}
        if action_type not in ACTION_TYPES:
            return {"success": False, "error": f"Unknown action type: {action_type}"}

        result: Dict[str, Any] = {
            "acting_faction": faction_name,
            "action": action_type,
            "target": target,
            "success": True,
        }

        if action_type == "propaganda":
            # Influence gain for acting faction
            shift = _rng.randint(1, 3)
            result.update(self.influence_tracker.shift_influence(faction_name, shift))
            result["narrative"] = f"{faction_name} launches a propaganda campaign and gains political ground."

        elif action_type == "sabotage" and target:
            # Target loses resources
            if target not in self.influence_tracker.factions:
                result["success"] = False
                result["error"] = f"Unknown target: {target}"
            else:
                resource = _rng.choice(["gold", "soldiers", "spies"])
                loss = _rng.randint(1, 2)
                result.update(
                    self.influence_tracker.resource_action(target, resource, "spend", loss)
                )
                result["narrative"] = (
                    f"{faction_name} sabotages {target}'s {resource} operations."
                )

        elif action_type == "recruit":
            result.update(
                self.influence_tracker.resource_action(faction_name, "soldiers", "gain", 1)
            )
            result["narrative"] = f"{faction_name} recruits new fighters."

        elif action_type == "bribe" and target:
            # Spend gold, gain influence
            spend = self.influence_tracker.resource_action(faction_name, "gold", "spend", 2)
            if not spend.get("success"):
                result["success"] = False
                result["narrative"] = f"{faction_name} lacks gold to bribe {target}."
            else:
                gain = self.influence_tracker.shift_influence(faction_name, 1)
                result.update(gain)
                result["narrative"] = f"{faction_name} bribes officials and gains political influence."

        elif action_type == "intimidate" and target:
            if target not in self.influence_tracker.factions:
                result["success"] = False
                result["error"] = f"Unknown target: {target}"
            else:
                rel = self.alliance_system.get_relationship(faction_name, target)
                if rel in ("neutral", "tension"):
                    self.alliance_system.declare_rivalry(faction_name, target)
                    result["narrative"] = (
                        f"{faction_name} openly threatens {target}. "
                        f"Relations deteriorate to rivalry."
                    )
                else:
                    result["narrative"] = (
                        f"{faction_name} attempts to intimidate {target} "
                        f"but the relationship can't get much worse."
                    )

        elif action_type == "negotiate" and target:
            if target not in self.influence_tracker.factions:
                result["success"] = False
                result["error"] = f"Unknown target: {target}"
            else:
                self.alliance_system.normalize(faction_name, target, "Negotiated settlement")
                result["narrative"] = (
                    f"{faction_name} opens negotiations with {target}. "
                    f"Relations ease to neutral."
                )

        else:
            result["success"] = False
            result["narrative"] = f"Action '{action_type}' requires a valid target."

        return result

    # ── Serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "power_balance": self.power_balance,
            "influence_tracker": self.influence_tracker.to_dict(),
            "alliance_system": self.alliance_system.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PoliticalGravityEngine":
        engine = cls.__new__(cls)
        engine.power_balance = float(data.get("power_balance", 0.0))
        engine.influence_tracker = FactionInfluenceTracker.from_dict(
            data.get("influence_tracker", {})
        )
        engine.alliance_system = AllianceSystem.from_dict(
            data.get("alliance_system", {})
        )
        return engine
