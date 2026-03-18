"""
NPC Persistent Memory — Cognitive Sovereignty System (WO-V12.1)
================================================================

Lightweight NPC memory system that:
  - Filters broadcast events by location/role relevance
  - Applies cultural bias via BiasLens (pure string ops, Pi 5 safe)
  - Persists to disk as JSON (state/npc_memory.json)
  - Injects memory context into Mimir dialogue prompts

Reuses MemoryShard + ShardType from codex.core.memory (no duplication).
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from codex.core.memory import MemoryShard, ShardType

log = logging.getLogger(__name__)


# =========================================================================
# BIAS TABLES — pure keyword substitution per cultural archetype
# =========================================================================

BIAS_TABLES: Dict[str, Dict[str, str]] = {
    "freedom": {
        "reinforced": "tightened their grip on",
        "patrol": "surveillance sweep",
        "order restored": "dissent silenced",
        "secured": "locked down",
        "protection": "control",
    },
    "honor": {
        "retreat": "tactical withdrawal",
        "fled": "withdrew with purpose",
        "surrendered": "yielded the field",
        "coward": "one who chose life",
        "defeat": "setback",
    },
    "hospitality": {
        "stranger": "guest",
        "outsider": "traveler",
        "intruder": "unexpected visitor",
        "enemy territory": "unwelcoming lands",
    },
    "tradition": {
        "new method": "untested approach",
        "innovation": "deviation from custom",
        "change": "upheaval",
        "reform": "disruption of the old ways",
    },
    "survival": {
        "abundance": "temporary surplus",
        "feast": "rare bounty",
        "safe": "quiet for now",
        "peace": "lull before the next storm",
        "prosperity": "fragile plenty",
    },
}


# =========================================================================
# BIAS LENS — rewrites event text through a cultural filter
# =========================================================================

@dataclass
class BiasLens:
    """Applies cultural bias to event text before NPC recording.

    Uses pure string substitution from BIAS_TABLES — no Mimir calls.
    """
    cultural_value: Any = None  # CulturalValue dataclass

    def rewrite(self, raw_text: str) -> str:
        """Rewrite event text through cultural bias.

        Returns original text if no CulturalValue is set.
        """
        if not raw_text:
            return raw_text
        if self.cultural_value is None:
            return raw_text

        tenet = getattr(self.cultural_value, "tenet", "")
        expression = getattr(self.cultural_value, "expression", "")

        # Find matching archetype from tenet keywords
        archetype = self._detect_archetype(tenet)

        if archetype and archetype in BIAS_TABLES:
            result = raw_text
            for keyword, replacement in BIAS_TABLES[archetype].items():
                result = re.sub(re.escape(keyword), replacement, result, flags=re.IGNORECASE)
            return result

        # Fallback: append cultural expression as parenthetical
        if expression:
            return f"{raw_text} ({expression})"
        return raw_text

    @staticmethod
    def _detect_archetype(tenet: str) -> Optional[str]:
        """Map a CulturalValue.tenet to a BIAS_TABLES archetype."""
        tenet_lower = tenet.lower()
        for archetype in BIAS_TABLES:
            if archetype in tenet_lower:
                return archetype
        return None

    def to_dict(self) -> dict:
        if self.cultural_value is None:
            return {}
        return {"cultural_value": self.cultural_value.to_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> "BiasLens":
        cv_data = data.get("cultural_value")
        if cv_data:
            try:
                from codex.core.world.grapes_engine import CulturalValue
                return cls(cultural_value=CulturalValue.from_dict(cv_data))
            except (ImportError, Exception):
                pass
        return cls()


# =========================================================================
# NPC MEMORY BANK — per-NPC shard store
# =========================================================================

MAX_SHARDS = 8


@dataclass
class NPCMemoryBank:
    """Per-NPC memory store. Reuses MemoryShard from codex.core.memory."""

    npc_name: str = ""
    npc_role: str = ""
    npc_location: str = ""
    faction: str = ""
    shards: List[MemoryShard] = field(default_factory=list)
    bias_lens: BiasLens = field(default_factory=BiasLens)

    def record(self, content: str, tags: Optional[List[str]] = None,
               source: str = "broadcast") -> MemoryShard:
        """Record an ECHO shard with bias applied. Enforces MAX_SHARDS cap."""
        biased = self.bias_lens.rewrite(content)
        shard = MemoryShard(
            shard_type=ShardType.ECHO,
            content=biased,
            tags=tags or [],
            source=source,
        )
        self.shards.append(shard)
        self._decay()
        return shard

    def record_anchor(self, content: str, tags: Optional[List[str]] = None,
                      source: str = "broadcast") -> MemoryShard:
        """Record an ANCHOR shard (high-importance). Enforces cap."""
        biased = self.bias_lens.rewrite(content)
        shard = MemoryShard(
            shard_type=ShardType.ANCHOR,
            content=biased,
            tags=tags or [],
            source=source,
        )
        self.shards.append(shard)
        self._decay()
        return shard

    def weave_context(self, token_budget: int = 150) -> str:
        """Build ~100-150 token context string for dialogue injection.

        ANCHORs first, then ECHOs by recency. Truncated to budget.
        Returns empty string if no shards.
        """
        if not self.shards:
            return ""

        anchors = sorted(
            [s for s in self.shards if s.shard_type == ShardType.ANCHOR],
            key=lambda s: s.timestamp, reverse=True,
        )
        echoes = sorted(
            [s for s in self.shards if s.shard_type == ShardType.ECHO],
            key=lambda s: s.timestamp, reverse=True,
        )

        bullets = []
        used_tokens = 0
        header = f"{self.npc_name} remembers:\n"
        used_tokens += len(header) // 4

        for shard in anchors + echoes:
            line = f"- {shard.content}"
            line_tokens = len(line) // 4
            if used_tokens + line_tokens > token_budget:
                break
            bullets.append(line)
            used_tokens += line_tokens

        if not bullets:
            return ""
        return header + "\n".join(bullets)

    def get_recent_shards(self, n: int = 3) -> list:
        """Return the N most recent shards, newest-first."""
        return sorted(self.shards, key=lambda s: s.timestamp, reverse=True)[:n]

    def _decay(self):
        """Purge oldest shards when over MAX_SHARDS cap.

        Eviction order: oldest ECHOs first, then oldest ANCHORs.
        """
        while len(self.shards) > MAX_SHARDS:
            echoes = [s for s in self.shards if s.shard_type == ShardType.ECHO]
            if echoes:
                oldest = min(echoes, key=lambda s: s.timestamp)
                self.shards.remove(oldest)
            else:
                anchors = [s for s in self.shards if s.shard_type == ShardType.ANCHOR]
                if anchors:
                    oldest = min(anchors, key=lambda s: s.timestamp)
                    self.shards.remove(oldest)
                else:
                    # Shouldn't happen, but safety valve
                    self.shards.pop(0)

    def to_dict(self) -> dict:
        return {
            "npc_name": self.npc_name,
            "npc_role": self.npc_role,
            "npc_location": self.npc_location,
            "faction": self.faction,
            "shards": [s.to_dict() for s in self.shards],
            "bias_lens": self.bias_lens.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict, bias_lens: Optional[BiasLens] = None) -> "NPCMemoryBank":
        bank = cls(
            npc_name=data.get("npc_name", ""),
            npc_role=data.get("npc_role", ""),
            npc_location=data.get("npc_location", ""),
            faction=data.get("faction", ""),
            shards=[MemoryShard.from_dict(s) for s in data.get("shards", [])],
        )
        if bias_lens is not None:
            bank.bias_lens = bias_lens
        else:
            lens_data = data.get("bias_lens", {})
            if lens_data:
                bank.bias_lens = BiasLens.from_dict(lens_data)
        return bank


# =========================================================================
# CIVIC EVENT ROLE MAP — which NPC roles care about which civic categories
# =========================================================================

CIVIC_ROLE_MAP: Dict[str, List[str]] = {
    "trade": ["merchant"],
    "security": ["leader", "quest_giver"],
    "rumor": ["informant"],
    "infrastructure": ["merchant", "leader"],
    "morale": ["healer"],
}


# =========================================================================
# NPC MEMORY MANAGER — orchestrator
# =========================================================================

class NPCMemoryManager:
    """Orchestrates NPC memory banks. Subscribes to GlobalBroadcastManager."""

    SUBSCRIBED_EVENTS = [
        "HIGH_IMPACT_DECISION",
        "MAP_UPDATE",
        "FACTION_CLOCK_TICK",
        "CIVIC_EVENT",
        "TRAIT_ACTIVATED",
    ]

    def __init__(self, broadcast_manager=None,
                 cultural_values: Optional[List[Any]] = None):
        self._banks: Dict[str, NPCMemoryBank] = {}
        self._broadcast_manager = broadcast_manager
        self._cultural_values: List[Any] = cultural_values or []
        self._callbacks: List[tuple] = []  # (event_type, callback) for cleanup

        if broadcast_manager:
            self._subscribe_all()

    def _subscribe_all(self):
        """Subscribe to all relevant broadcast events."""
        for event_type in self.SUBSCRIBED_EVENTS:
            self._broadcast_manager.subscribe(event_type, self._on_broadcast)
            self._callbacks.append((event_type, self._on_broadcast))

    def unsubscribe(self):
        """Remove all broadcast subscriptions (cleanup on session end)."""
        if self._broadcast_manager:
            for event_type, cb in self._callbacks:
                try:
                    self._broadcast_manager.unsubscribe(event_type, cb)
                except Exception:
                    pass
        self._callbacks.clear()

    # -----------------------------------------------------------------
    # NPC Registration
    # -----------------------------------------------------------------

    def register_npc(self, name: str, role: str, location: str = "",
                     faction: str = "") -> NPCMemoryBank:
        """Register an NPC and create a memory bank.

        Idempotent: returns existing bank if NPC already registered.
        BiasLens assigned deterministically via hash(name) % len(cultural_values).
        """
        if name in self._banks:
            return self._banks[name]

        lens = BiasLens()
        if self._cultural_values:
            idx = hash(name) % len(self._cultural_values)
            lens = BiasLens(cultural_value=self._cultural_values[idx])

        bank = NPCMemoryBank(
            npc_name=name,
            npc_role=role,
            npc_location=location,
            faction=faction,
            bias_lens=lens,
        )
        self._banks[name] = bank
        return bank

    def get_bank(self, name: str) -> Optional[NPCMemoryBank]:
        """Get a specific NPC's memory bank."""
        return self._banks.get(name)

    def get_dialogue_context(self, name: str) -> str:
        """Get woven dialogue context for an NPC. Returns '' if unknown."""
        bank = self._banks.get(name)
        if bank is None:
            return ""
        return bank.weave_context()

    # -----------------------------------------------------------------
    # Broadcast Handler
    # -----------------------------------------------------------------

    def _on_broadcast(self, payload: dict) -> None:
        """Route broadcast events to relevant NPC banks."""
        event_tag = payload.get("event_tag", "") or payload.get("_event_type", "")
        summary = self._summarize_event(payload)
        if not summary:
            return

        for name, bank in self._banks.items():
            if self._should_npc_witness(bank, payload):
                # High-impact and trait events are anchor-worthy
                event_type = payload.get("_event_type", event_tag)
                if event_type in ("HIGH_IMPACT_DECISION", "TRAIT_ACTIVATED"):
                    bank.record_anchor(summary, tags=[event_tag or event_type])
                else:
                    bank.record(summary, tags=[event_tag or event_type])

    def _should_npc_witness(self, bank: NPCMemoryBank, payload: dict) -> bool:
        """Determine if an NPC should witness this event."""
        event_type = payload.get("_event_type", "")

        # HIGH_IMPACT and TRAIT_ACTIVATED: all NPCs (settlement-wide news)
        if event_type in ("HIGH_IMPACT_DECISION", "TRAIT_ACTIVATED"):
            return True

        # MAP_UPDATE: all NPCs (low-priority room activity)
        if event_type == "MAP_UPDATE":
            return True

        # FACTION_CLOCK_TICK: informant/leader roles + matching faction
        if event_type == "FACTION_CLOCK_TICK":
            if bank.npc_role in ("informant", "leader", "quest_giver"):
                return True
            faction_name = payload.get("faction", "")
            if faction_name and bank.faction and faction_name.lower() == bank.faction.lower():
                return True
            return False

        # CIVIC_EVENT: route by category
        if event_type == "CIVIC_EVENT":
            category = payload.get("category", "")
            allowed_roles = CIVIC_ROLE_MAP.get(category, [])
            return bank.npc_role in allowed_roles

        # Fallback: check for event_tag or category in payload
        category = payload.get("category", "")
        if category:
            allowed_roles = CIVIC_ROLE_MAP.get(category, [])
            if allowed_roles:
                return bank.npc_role in allowed_roles

        # Default: all NPCs witness unclassified events
        return True

    @staticmethod
    def _summarize_event(payload: dict) -> str:
        """Create a 1-line summary from a broadcast payload."""
        # Try explicit summary field first
        summary = payload.get("summary", "")
        if summary:
            return summary[:200]

        # Build from available fields
        parts = []
        event_tag = payload.get("event_tag", "")
        if event_tag:
            parts.append(event_tag.replace("_", " ").title())

        category = payload.get("category", "")
        if category:
            parts.append(f"({category})")

        detail = payload.get("detail", "") or payload.get("description", "")
        if detail:
            parts.append(detail[:150])

        if not parts:
            # Truly empty payload — skip recording
            return ""

        return " ".join(parts)[:200]

    # -----------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------

    def save(self) -> None:
        """Save all NPC memory banks to state/npc_memory.json."""
        try:
            from codex.paths import NPC_MEMORY_FILE, safe_save_json
            data = {
                "version": "1.0",
                "banks": {name: bank.to_dict() for name, bank in self._banks.items()},
            }
            safe_save_json(NPC_MEMORY_FILE, data)
        except Exception as e:
            log.warning("Failed to save NPC memory: %s", e)

    def load(self) -> None:
        """Load NPC memory banks from state/npc_memory.json.

        Gracefully handles missing file or corrupt data.
        Restores BiasLens deterministically from cultural_values.
        """
        try:
            from codex.paths import NPC_MEMORY_FILE
            if not NPC_MEMORY_FILE.exists():
                return

            with open(NPC_MEMORY_FILE, "r") as f:
                data = json.load(f)

            for name, bank_data in data.get("banks", {}).items():
                # Restore bias lens deterministically
                lens = BiasLens()
                if self._cultural_values:
                    idx = hash(name) % len(self._cultural_values)
                    lens = BiasLens(cultural_value=self._cultural_values[idx])

                bank = NPCMemoryBank.from_dict(bank_data, bias_lens=lens)
                self._banks[name] = bank

            log.info("Loaded NPC memory: %d banks", len(self._banks))
        except Exception as e:
            log.warning("Failed to load NPC memory: %s", e)
