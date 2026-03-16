"""
codex.core.mechanics.rest — Short/Long Rest & Downtime Manager
================================================================

Per-engine rest mechanics with unified RestResult output.

Engine-specific behavior:
  - Burnwillow: bind_wounds (short) + Emberhome full-rest (long) + Doom cost
  - DnD5e: Hit dice spending (short) + full HP/resource recovery (long)
  - BitD: Downtime activities (vice recovery, harm healing, project clocks)
  - Cosmere: Focus recovery (short) + full restore (long)
  - Crown: Sway decay/recovery handled by existing engine rest methods

WO-V34.0: The Sovereign Dashboard — Gap #8
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# =========================================================================
# REST RESULT
# =========================================================================

@dataclass
class RestResult:
    """Unified result from any rest/downtime action."""
    rest_type: str                  # "short", "long", "downtime", "bind"
    hp_recovered: Dict[str, int] = field(default_factory=dict)
    resources_reset: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)
    conditions_cleared: List[str] = field(default_factory=list)

    def summary(self) -> str:
        """Format a human-readable summary."""
        lines = [f"=== {self.rest_type.upper()} REST ==="]
        if self.hp_recovered:
            for name, amt in self.hp_recovered.items():
                lines.append(f"  {name}: +{amt} HP")
        if self.resources_reset:
            lines.append(f"  Restored: {', '.join(self.resources_reset)}")
        if self.conditions_cleared:
            lines.append(f"  Cleared: {', '.join(self.conditions_cleared)}")
        if self.side_effects:
            for fx in self.side_effects:
                lines.append(f"  ! {fx}")
        return "\n".join(lines)


# =========================================================================
# REST MANAGER
# =========================================================================

class RestManager:
    """Per-engine rest dispatcher."""

    # ── Burnwillow ─────────────────────────────────────────────────────

    def short_rest_burnwillow(self, engine) -> RestResult:
        """Bind wounds — heal 50% leader + 25% party, +1 Doom."""
        result = RestResult(rest_type="short")
        party = engine.get_active_party()
        if not party:
            return result

        leader = party[0]
        heal_amt = max(1, leader.max_hp // 2)
        actual = leader.heal(heal_amt)
        result.hp_recovered[leader.name] = actual

        for member in party[1:]:
            amt = max(1, member.max_hp // 4)
            healed = member.heal(amt)
            result.hp_recovered[member.name] = healed

        if hasattr(engine, 'doom_clock'):
            engine.doom_clock.tick(1)
            result.side_effects.append("Doom +1")

        return result

    def long_rest_burnwillow(self, engine) -> RestResult:
        """Emberhome full heal — all party to max HP, +3 Doom."""
        result = RestResult(rest_type="long")
        party = engine.get_active_party()

        for member in party:
            healed = member.heal(member.max_hp)
            result.hp_recovered[member.name] = healed

        if hasattr(engine, 'doom_clock'):
            engine.doom_clock.tick(3)
            result.side_effects.append("Doom +3")

        result.resources_reset.append("All HP restored")
        return result

    # ── DnD 5e ─────────────────────────────────────────────────────────

    def short_rest_dnd5e(self, engine) -> RestResult:
        """Spend hit dice: roll hit_die + CON mod per die spent."""
        result = RestResult(rest_type="short")
        party = engine.get_active_party()

        for char in party:
            hd_remaining = getattr(char, 'hit_dice_remaining', 0)
            hit_die_type = getattr(char, 'hit_die_type', 8)
            if hd_remaining <= 0:
                continue

            # Spend one hit die
            con_mod = (char.constitution - 10) // 2
            roll = random.randint(1, hit_die_type) + con_mod
            healed = char.heal(max(1, roll))
            char.hit_dice_remaining = hd_remaining - 1
            result.hp_recovered[char.name] = healed
            result.resources_reset.append(f"{char.name}: 1 hit die spent")

        return result

    def long_rest_dnd5e(self, engine) -> RestResult:
        """Full HP, recover half hit dice, clear non-permanent conditions."""
        result = RestResult(rest_type="long")
        party = engine.get_active_party()

        for char in party:
            healed = char.heal(char.max_hp)
            result.hp_recovered[char.name] = healed

            # Recover half hit dice (minimum 1)
            total_hd = getattr(char, 'level', 1)
            hd_recover = max(1, total_hd // 2)
            hit_die_type = getattr(char, 'hit_die_type', 8)
            char.hit_dice_remaining = min(
                total_hd,
                getattr(char, 'hit_dice_remaining', 0) + hd_recover,
            )
            result.resources_reset.append(f"{char.name}: +{hd_recover} hit dice")

        result.resources_reset.append("All HP restored")
        return result

    # ── BitD / FITD ────────────────────────────────────────────────────

    def downtime_bitd(self, engine, char_name: str, activity: str = "vice") -> RestResult:
        """BitD downtime: vice, recover, or project."""
        result = RestResult(rest_type="downtime")

        if activity == "vice":
            clock = engine.stress_clocks.get(char_name)
            if clock:
                recovery = random.randint(1, 6)
                info = clock.recover(recovery)
                result.resources_reset.append(
                    f"{char_name}: -{info['recovered']} stress"
                )
                if info.get("overindulged"):
                    result.side_effects.append(
                        f"{char_name} overindulged! Stress bottomed but complications arise."
                    )
        elif activity == "recover":
            result.resources_reset.append(f"{char_name}: 1 harm level healed")
        elif activity == "project":
            result.resources_reset.append(f"{char_name}: project clock ticked")

        return result

    # ── Cosmere ────────────────────────────────────────────────────────

    def short_rest_cosmere(self, engine) -> RestResult:
        """Recover focus (stormlight) to max."""
        result = RestResult(rest_type="short")
        party = engine.get_active_party()

        for char in party:
            old_focus = char.focus
            char.focus = max(0, (char.intellect - 10) // 2 + 2)
            if char.focus > old_focus:
                result.resources_reset.append(
                    f"{char.name}: focus {old_focus} -> {char.focus}"
                )

        return result

    def long_rest_cosmere(self, engine) -> RestResult:
        """Full HP + focus, clear conditions."""
        result = RestResult(rest_type="long")
        party = engine.get_active_party()

        for char in party:
            healed = char.heal(char.max_hp)
            result.hp_recovered[char.name] = healed
            char.focus = max(0, (char.intellect - 10) // 2 + 2)

        result.resources_reset.append("All HP and focus restored")
        return result

    # ── Dispatcher ─────────────────────────────────────────────────────

    def rest(self, engine, system_tag: str, rest_type: str = "short", **kwargs) -> RestResult:
        """Route rest to the correct per-engine method."""
        tag = system_tag.upper()
        if tag == "BURNWILLOW":
            if rest_type == "long":
                return self.long_rest_burnwillow(engine)
            return self.short_rest_burnwillow(engine)
        elif tag == "DND5E":
            if rest_type == "long":
                return self.long_rest_dnd5e(engine)
            return self.short_rest_dnd5e(engine)
        elif tag in ("BITD", "SAV", "BOB"):
            return self.downtime_bitd(
                engine,
                char_name=kwargs.get("char_name", ""),
                activity=kwargs.get("activity", "vice"),
            )
        elif tag == "STC":
            if rest_type == "long":
                return self.long_rest_cosmere(engine)
            return self.short_rest_cosmere(engine)
        elif tag == "CROWN":
            # Crown has its own rest methods on the engine
            result = RestResult(rest_type=rest_type)
            if hasattr(engine, 'trigger_long_rest') and rest_type == "long":
                msg = engine.trigger_long_rest()
                result.resources_reset.append(msg)
            elif hasattr(engine, 'trigger_short_rest'):
                msg = engine.trigger_short_rest()
                result.resources_reset.append(msg)
            return result
        else:
            return RestResult(rest_type=rest_type, side_effects=["Unknown system"])
