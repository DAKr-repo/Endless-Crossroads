"""
codex.spatial.willow_wood — Willow Wood Overworld Zone (WO-V62.0 Track B)
=========================================================================

Semi-procedural overworld between Emberhome and dungeon entries.
8 fixed landmark rooms + 3-5 procedural rooms per destination path.
GRAPES-reactive descriptions, multi-pillar encounters, secrets.
"""

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


_BLUEPRINT_PATH = Path(__file__).parent / "blueprints" / "willow_wood.json"


@dataclass
class WoodRoom:
    """A room in the Willow Wood."""

    id: Any  # int for landmarks, str like "path_descent_0" for procedural
    name: str
    room_type: str
    tier: int
    description: str
    connections: List[Any] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    grapes_binding: Optional[str] = None
    encounter_chance: float = 0.0
    exit_type: Optional[str] = None  # "descend" or "ascend" for gates
    gate_id: Optional[str] = None   # Set for destination gates
    is_landmark: bool = True
    is_gate: bool = False


@dataclass
class WoodEncounter:
    """A multi-pillar encounter."""

    name: str
    description: str
    approaches: Dict[str, dict]  # pillar -> {dc, reward, description, skill?}


@dataclass
class WoodSecret:
    """A discoverable secret."""

    secret_type: str
    room_types: List[str]
    dc: int = 0
    skill: str = ""
    one_per_session: bool = False
    prerequisite: str = ""
    prerequisite_sessions: int = 0
    drop_chance: float = 0.0
    reward: str = ""


class WillowWoodZone:
    """The Willow Wood overworld zone.

    Loads from blueprint, generates procedural paths between landmark rooms
    and destination gates, applies GRAPES world-state bindings to room
    descriptions and services.

    Usage::

        zone = WillowWoodZone(session_seed=42, grapes_health={"economics": 0.5})
        zone.generate()
        heart = zone.get_room(0)
        gates = zone.gate_rooms()
    """

    def __init__(
        self,
        session_seed: int = 42,
        grapes_health: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Args:
            session_seed: Seed for procedural path generation (typically derived
                          from the session number so each session has stable paths).
            grapes_health: Dict mapping GRAPES category name -> health score
                           (-1.0 = very bad, 0.0 = neutral, +1.0 = very good).
                           Missing categories are treated as neutral.
        """
        self._seed = session_seed
        self._grapes_health: Dict[str, float] = grapes_health or {}
        self._rooms: Dict[Any, WoodRoom] = {}
        self._encounters: Dict[str, WoodEncounter] = {}
        self._secrets: Dict[str, WoodSecret] = {}
        self._blueprint: dict = {}
        self._generated: bool = False

        # Persistence: survive across sessions (load via load_save_dict)
        self._discovered_secrets: Set[str] = set()
        # Cleared on each generate() call (one-per-session gate)
        self._found_secrets_this_session: Set[str] = set()

    # ─── Generation ──────────────────────────────────────────────────────────

    def generate(self) -> None:
        """Load the blueprint and generate the full zone.

        Safe to call multiple times; resets procedural state each call.
        """
        self._rooms.clear()
        self._encounters.clear()
        self._secrets.clear()
        self._found_secrets_this_session.clear()

        self._load_blueprint()
        self._build_landmarks()
        self._generate_paths()
        self._apply_grapes_bindings()
        self._load_encounters()
        self._load_secrets()
        self._generated = True

    def _load_blueprint(self) -> None:
        """Load the Willow Wood blueprint JSON from disk."""
        if _BLUEPRINT_PATH.exists():
            with open(_BLUEPRINT_PATH, "r", encoding="utf-8") as fh:
                self._blueprint = json.load(fh)
        else:
            # Minimal fallback so the class is usable without the blueprint file
            self._blueprint = {
                "landmark_rooms": [
                    {
                        "id": 0,
                        "type": "grove_heart",
                        "name": "Heart of the Wood",
                        "tier": 0,
                        "description": "The heart of the Willow Wood.",
                        "connections": [],
                    }
                ],
                "destination_gates": [],
                "path_room_pool": [],
                "encounters": {},
                "secrets": {},
                "grapes_bindings": {},
            }

    def _build_landmarks(self) -> None:
        """Instantiate WoodRoom objects for every landmark room in the blueprint."""
        for room_data in self._blueprint.get("landmark_rooms", []):
            room = WoodRoom(
                id=room_data["id"],
                name=room_data["name"],
                room_type=room_data["type"],
                tier=room_data.get("tier", 0),
                description=room_data["description"],
                connections=list(room_data.get("connections", [])),
                services=list(room_data.get("services", [])),
                grapes_binding=room_data.get("grapes_binding"),
                is_landmark=True,
            )
            self._rooms[room.id] = room

    def _generate_paths(self) -> None:
        """Generate procedural path rooms for each destination gate.

        Each gate has a path of 3-5 procedural rooms connecting from a
        landmark room to the gate entrance.  Path length and room selection
        are seeded per-gate so they are stable across calls with the same
        session_seed.
        """
        pool = self._blueprint.get("path_room_pool", [])

        for gate_data in self._blueprint.get("destination_gates", []):
            gate_key = gate_data["gate_id"]
            # Skip gates that require discovery if not yet discovered
            req_discovery = gate_data.get("requires_discovery")
            if req_discovery and req_discovery not in self._discovered_secrets:
                continue
            path_from = gate_data.get("path_from", 0)
            min_rooms = gate_data.get("path_rooms_min", 3)
            max_rooms = gate_data.get("path_rooms_max", 5)
            gate_tier = gate_data.get("tier", 1)

            gate_rng = random.Random(self._seed ^ hash(gate_key))

            if pool:
                count = gate_rng.randint(min_rooms, max_rooms)
                available = [r for r in pool if r["tier"] <= gate_tier]
                if not available:
                    available = pool[:]
                # Allow repeats only if the pool is smaller than requested count
                if len(available) >= count:
                    selected = gate_rng.sample(available, count)
                else:
                    selected = available[:]
                    while len(selected) < count:
                        selected.append(gate_rng.choice(available))

                # Build chain of path rooms
                prev_id: Any = path_from
                for i, template in enumerate(selected):
                    room_id = f"path_{gate_key}_{i}"
                    name = gate_rng.choice(template["name_pool"])
                    desc = gate_rng.choice(template["description_pool"])
                    room = WoodRoom(
                        id=room_id,
                        name=name,
                        room_type=template["type"],
                        tier=template["tier"],
                        description=desc,
                        encounter_chance=template.get("encounter_chance", 0.0),
                        is_landmark=False,
                    )
                    # Bidirectional connection to previous node
                    room.connections.append(prev_id)
                    if prev_id in self._rooms:
                        self._rooms[prev_id].connections.append(room_id)
                    self._rooms[room_id] = room
                    prev_id = room_id

                # Gate connects to last path room
                gate = self._make_gate(gate_data)
                gate.connections.append(prev_id)
                if prev_id in self._rooms:
                    self._rooms[prev_id].connections.append(gate.id)
            else:
                # No path pool: connect gate directly to the landmark
                gate = self._make_gate(gate_data)
                if path_from in self._rooms:
                    self._rooms[path_from].connections.append(gate.id)
                    gate.connections.append(path_from)

            self._rooms[gate.id] = gate

    def _make_gate(self, gate_data: dict) -> WoodRoom:
        """Create a WoodRoom representing a destination gate."""
        return WoodRoom(
            id=f"gate_{gate_data['gate_id']}",
            name=gate_data["name"],
            room_type="gate",
            tier=gate_data.get("tier", 1),
            description=gate_data["description"],
            exit_type=gate_data.get("exit_type", "descend"),
            gate_id=gate_data["gate_id"],
            is_landmark=False,
            is_gate=True,
        )

    def _apply_grapes_bindings(self) -> None:
        """Modify room descriptions and services based on GRAPES world health.

        A health score > +0.3 applies the positive variant;
        < -0.3 applies the negative variant; in between is left neutral.
        """
        bindings = self._blueprint.get("grapes_bindings", {})
        for category, binding in bindings.items():
            health = self._grapes_health.get(category, 0.0)
            room_id = binding.get("room_id")
            if room_id is None or room_id not in self._rooms:
                continue
            room = self._rooms[room_id]

            if health > 0.3:
                suffix = binding.get("positive_suffix", "")
                if suffix:
                    room.description = room.description.rstrip() + suffix
                services = binding.get("positive_services")
                if services is not None:
                    room.services = list(services)
            elif health < -0.3:
                suffix = binding.get("negative_suffix", "")
                if suffix:
                    room.description = room.description.rstrip() + suffix
                services = binding.get("negative_services")
                if services is not None:
                    room.services = list(services)

    def _load_encounters(self) -> None:
        """Populate internal encounter registry from blueprint."""
        for enc_id, enc_data in self._blueprint.get("encounters", {}).items():
            self._encounters[enc_id] = WoodEncounter(
                name=enc_data["name"],
                description=enc_data["description"],
                approaches=enc_data.get("approaches", {}),
            )

    def _load_secrets(self) -> None:
        """Populate internal secret registry from blueprint."""
        for sec_id, sec_data in self._blueprint.get("secrets", {}).items():
            self._secrets[sec_id] = WoodSecret(
                secret_type=sec_id,
                room_types=sec_data.get("rooms", []),
                dc=sec_data.get("dc", 0),
                skill=sec_data.get("skill", ""),
                one_per_session=sec_data.get("one_per_session", False),
                prerequisite=sec_data.get("prerequisite", ""),
                prerequisite_sessions=sec_data.get("prerequisite_sessions", 0),
                drop_chance=sec_data.get("drop_chance", 0.0),
                reward=sec_data.get("reward", sec_data.get("trigger", "")),
            )

    # ─── Public API ───────────────────────────────────────────────────────────

    def get_room(self, room_id: Any) -> Optional[WoodRoom]:
        """Return a room by its ID, or None if not found."""
        return self._rooms.get(room_id)

    def all_rooms(self) -> Dict[Any, WoodRoom]:
        """Return a copy of the full room map."""
        return dict(self._rooms)

    def landmark_rooms(self) -> List[WoodRoom]:
        """Return all fixed landmark rooms."""
        return [r for r in self._rooms.values() if r.is_landmark]

    def gate_rooms(self) -> List[WoodRoom]:
        """Return all destination gate rooms."""
        return [r for r in self._rooms.values() if r.is_gate]

    def path_rooms(self, gate_id: str) -> List[WoodRoom]:
        """Return procedural path rooms for the given gate, in chain order."""
        prefix = f"path_{gate_id}_"
        rooms = [
            r
            for r in self._rooms.values()
            if isinstance(r.id, str) and r.id.startswith(prefix)
        ]
        return sorted(rooms, key=lambda r: r.id)

    def get_gate(self, room_id: Any) -> Optional[WoodRoom]:
        """Return the room if it is a gate, otherwise None."""
        room = self._rooms.get(room_id)
        return room if (room and room.is_gate) else None

    def roll_encounter(
        self,
        room_id: Any,
        rng: Optional[random.Random] = None,
    ) -> Optional[WoodEncounter]:
        """Probabilistically roll for an encounter in a room.

        Args:
            room_id: The room to check.
            rng: Optional seeded RNG; defaults to a fresh random.Random().

        Returns:
            A WoodEncounter, or None if no encounter triggered.
        """
        room = self._rooms.get(room_id)
        if not room or room.encounter_chance <= 0.0:
            return None
        if rng is None:
            rng = random.Random()
        if rng.random() > room.encounter_chance:
            return None

        tier = room.tier
        tier_key = f"tier_{tier}"
        encounter_table = self._blueprint.get("encounter_table", {})
        enc_pool = encounter_table.get(tier_key, [])
        if not enc_pool:
            return None

        enc_id = rng.choice(enc_pool)
        return self._encounters.get(enc_id)

    def check_secrets(
        self,
        room_id: Any,
        session_number: int = 1,
    ) -> List[WoodSecret]:
        """Return all secrets currently available in a given room.

        Filters by:
        - Room type match
        - one_per_session gate (already found this session)
        - prerequisite_sessions (not enough sessions played)
        - prerequisite secret discovered this session
        """
        room = self._rooms.get(room_id)
        if not room:
            return []

        available: List[WoodSecret] = []
        for sec_id, secret in self._secrets.items():
            # Room type gate
            if secret.room_types and room.room_type not in secret.room_types:
                continue
            # One-per-session gate
            if secret.one_per_session and sec_id in self._found_secrets_this_session:
                continue
            # Minimum sessions gate
            if secret.prerequisite_sessions > 0 and session_number < secret.prerequisite_sessions:
                continue
            # Prerequisite secret gate
            if secret.prerequisite == "has_lore_inscription":
                if "lore_inscription" not in self._found_secrets_this_session:
                    continue
            available.append(secret)
        return available

    def discover_secret(self, secret_type: str) -> None:
        """Mark a secret as discovered (this session and permanently)."""
        self._found_secrets_this_session.add(secret_type)
        self._discovered_secrets.add(secret_type)

    def get_discovered_secrets(self) -> Set[str]:
        """Return the set of all permanently discovered secrets."""
        return set(self._discovered_secrets)

    def set_discovered_secrets(self, secrets: Set[str]) -> None:
        """Restore previously persisted discovered secrets."""
        self._discovered_secrets = set(secrets)

    # ─── Persistence ─────────────────────────────────────────────────────────

    def to_save_dict(self) -> dict:
        """Serialize persistent state for inclusion in a campaign save."""
        return {
            "discovered_secrets": sorted(self._discovered_secrets),
        }

    def load_save_dict(self, data: dict) -> None:
        """Restore persistent state from a campaign save dict."""
        self._discovered_secrets = set(data.get("discovered_secrets", []))
