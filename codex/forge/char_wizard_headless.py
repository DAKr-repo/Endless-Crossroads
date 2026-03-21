"""
codex.forge.char_wizard_headless
=================================
UI-agnostic character creation wizard for Discord/Telegram bots.

Extracts pure logic from SystemBuilder step types into a stateful
processor that returns prompts and accepts answers without any
Rich Console or terminal I/O dependency.

Usage:
    wizard = HeadlessWizard(schema)
    prompt = wizard.current_step_prompt()  # → dict with type, options, etc.
    result = wizard.submit_answer(42)      # → {ok, error?, complete?}
    prompt = wizard.current_step_prompt()  # → next step
    ...
    sheet = wizard.sheet                   # → populated CharacterSheet
"""

from __future__ import annotations

import random
from dataclasses import asdict, field
from typing import Any, Dict, List, Optional

from codex.forge.char_wizard import (
    CharacterBuilderEngine,
    CharacterSheet,
    CreationSchema,
)


class HeadlessWizard:
    """Drives character creation step-by-step without UI coupling."""

    def __init__(self, schema: CreationSchema):
        self.schema = schema
        self.sheet = CharacterSheet(
            system_id=schema.system_id,
            setting_id=schema.setting_id,
        )
        self.steps = list(schema.steps)
        self.step_idx = 0
        self._complete = False
        # For stat_pool: pre-rolled pool to present to user
        self._pending_pool: List[int] = []
        self._pending_assign_to: List[str] = []
        # For stat_roll: auto-rolled values
        self._last_rolls: List[int] = []

    @property
    def complete(self) -> bool:
        return self._complete

    def current_step_prompt(self) -> Optional[dict]:
        """Return presentation data for the current step.

        Returns None if wizard is complete. Otherwise returns a dict:
        {
            "type": str,
            "id": str,
            "label": str,
            "prompt": str,
            "step_index": int,
            "total_steps": int,
            # Type-specific fields:
            "options": [...],           # choice, dependent_choice
            "rolled_values": [...],     # stat_roll (auto-applied)
            "pool": [...],              # stat_pool_allocate
            "assign_to": [...],         # stat_pool_allocate
            "categories": [...],        # point_allocate
            "points": int,              # point_allocate
            "max_per_category": int,    # point_allocate
            "current": {...},           # point_allocate (base values)
            "count": int,               # ability_select
            "abilities": [...],         # ability_select
        }
        """
        if self._complete or self.step_idx >= len(self.steps):
            self._complete = True
            return None

        step = self.steps[self.step_idx]
        stype = step.get("type", "text_input")
        step_id = step.get("id", step.get("label", "").lower())
        base = {
            "type": stype,
            "id": step_id,
            "label": step.get("label", ""),
            "prompt": step.get("prompt", ""),
            "step_index": self.step_idx,
            "total_steps": len(self.steps),
        }

        if stype == "text_input":
            return base

        elif stype == "choice":
            options = self._filter_options(step.get("options", []))
            base["options"] = [
                {"value": o.get("value", o.get("label", "")),
                 "label": o.get("label", o.get("value", "")),
                 "description": o.get("description", "")}
                for o in options
            ]
            return base

        elif stype == "stat_roll":
            assign_to = step.get("assign_to", self.schema.stats)
            method = step.get("method", "roll_4d6_drop_lowest")
            rolls = self._roll_stats(method, len(assign_to))
            self._last_rolls = rolls
            # Auto-apply
            for stat_name, value in zip(assign_to, rolls):
                self.sheet.stats[stat_name] = value
            base["rolled_values"] = rolls
            base["assign_to"] = assign_to
            base["auto_applied"] = True
            # Auto-advance
            self.step_idx += 1
            return base

        elif stype == "stat_pool_allocate":
            assign_to = step.get("assign_to", self.schema.stats)
            method = step.get("method", "roll_4d6_drop_lowest")
            if not self._pending_pool:
                pool = self._roll_stats(method, len(assign_to))
                pool.sort(reverse=True)
                self._pending_pool = pool
                self._pending_assign_to = list(assign_to)
            base["pool"] = list(self._pending_pool)
            base["assign_to"] = list(self._pending_assign_to)
            return base

        elif stype == "dependent_choice":
            depends_on = step.get("depends_on", "")
            parent_val = self._resolve_dependency(depends_on)
            # Gilded mode
            preset_gilded = step.get("preset_gilded")
            if preset_gilded is not None:
                preset = preset_gilded.get(parent_val, "")
                from_list = step.get("from", [])
                remaining = [a for a in from_list if a != preset]
                base["preset"] = preset
                base["options"] = [{"value": a, "label": a} for a in remaining]
                base["choose_count"] = step.get("choose_count", 1)
                base["mode"] = "gilded"
                return base
            # Standard dependent choice
            option_groups = step.get("option_groups", {})
            options = option_groups.get(parent_val, [])
            base["options"] = []
            for opt in options:
                if isinstance(opt, dict):
                    base["options"].append({
                        "value": opt.get("value", opt.get("label", "")),
                        "label": opt.get("label", opt.get("value", "")),
                        "description": opt.get("description", ""),
                    })
                else:
                    base["options"].append({"value": opt, "label": str(opt)})
            base["mode"] = "standard"
            return base

        elif stype == "point_allocate":
            categories = step.get("categories", [])
            preset_key = step.get("preset_key", "")
            presets = step.get("presets", {})
            preset_val = self._resolve_dependency(preset_key) if preset_key else ""
            base_vals = presets.get(preset_val, {})
            current = {cat: base_vals.get(cat, 0) for cat in categories}
            base["categories"] = categories
            base["category_groups"] = step.get("category_groups", {})
            base["points"] = step.get("points", 3)
            base["max_per_category"] = step.get("max_per_category", 2)
            base["current"] = current
            base["zero_raise"] = step.get("zero_raise", False)
            base["description"] = step.get("description", "")
            return base

        elif stype == "auto_derive":
            # No user input needed — compute and auto-advance
            self._apply_auto_derive(step)
            self.step_idx += 1
            # Return info about what was derived
            base["auto_applied"] = True
            base["derived_fields"] = list(step.get("derivations", [{}]))
            return base

        elif stype == "ability_select":
            depends_on = step.get("depends_on", "")
            parent_val = self._resolve_dependency(depends_on) if depends_on else ""
            pools = step.get("pools", {})
            pool = pools.get(parent_val, step.get("pool", []))
            base["count"] = step.get("count", 1)
            base["abilities"] = pool
            return base

        # Unknown type — skip
        self.step_idx += 1
        return self.current_step_prompt()

    def submit_answer(self, answer: Any) -> dict:
        """Apply user answer to the current step.

        Args:
            answer: Type depends on step type:
                - text_input: str
                - choice: int (1-based index)
                - stat_pool_allocate: dict {stat_name: chosen_value}
                - dependent_choice: int (1-based) or list[int] (gilded)
                - point_allocate: dict {category: dots}
                - ability_select: list[str]

        Returns:
            {"ok": True, "complete": bool} on success
            {"ok": False, "error": str} on validation failure
        """
        if self._complete:
            return {"ok": True, "complete": True}

        step = self.steps[self.step_idx]
        stype = step.get("type", "text_input")

        try:
            if stype == "text_input":
                return self._apply_text(step, answer)
            elif stype == "choice":
                return self._apply_choice(step, answer)
            elif stype == "stat_pool_allocate":
                return self._apply_stat_pool(step, answer)
            elif stype == "dependent_choice":
                return self._apply_dependent_choice(step, answer)
            elif stype == "point_allocate":
                return self._apply_point_allocate(step, answer)
            elif stype == "ability_select":
                return self._apply_ability_select(step, answer)
            elif stype in ("stat_roll", "auto_derive"):
                # Already auto-applied in current_step_prompt
                return self._advance()
            else:
                return self._advance()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def back(self) -> Optional[dict]:
        """Go back one step. Returns current_step_prompt() for previous step."""
        if self.step_idx > 0:
            self.step_idx -= 1
            self._pending_pool = []
            self._pending_assign_to = []
            return self.current_step_prompt()
        return None

    # ── Apply methods ─────────────────────────────────────────────────

    def _apply_text(self, step: dict, answer: str) -> dict:
        if not answer or not str(answer).strip():
            return {"ok": False, "error": "Please enter a value."}
        value = str(answer).strip()
        step_id = step.get("id", step.get("label", "").lower())
        self.sheet.choices[step_id] = value
        # Map to named sheet fields
        _FIELD_MAP = {
            "name": "name", "catalyst": "catalyst", "question": "question",
            "style": "style", "pronouns": "pronouns", "background": "background",
            "alias": "alias", "look": "look", "friend": "friend", "rival": "rival",
            "vice_purveyor": "vice_purveyor", "heritage_detail": "heritage_detail",
            "purpose": "purpose", "obstacle": "obstacle",
        }
        if step_id in _FIELD_MAP:
            setattr(self.sheet, _FIELD_MAP[step_id], value)
        return self._advance()

    def _apply_choice(self, step: dict, answer: int) -> dict:
        options = self._filter_options(step.get("options", []))
        idx = int(answer) - 1
        if idx < 0 or idx >= len(options):
            return {"ok": False, "error": f"Choose 1-{len(options)}."}
        picked = options[idx]
        step_id = step.get("id", step.get("label", "").lower())
        self.sheet.choices[step_id] = picked
        if step_id == "background":
            val = picked.get("value", picked.get("label", ""))
            self.sheet.background = val if isinstance(val, str) else str(val)
        elif step_id == "relationship":
            val = picked.get("value", picked.get("label", ""))
            self.sheet.relationships.append({"type": val})
        return self._advance()

    def _apply_stat_pool(self, step: dict, answer: dict) -> dict:
        """Answer: {stat_name: chosen_value_from_pool} for ALL stats."""
        assign_to = step.get("assign_to", self.schema.stats)
        pool = list(self._pending_pool)
        for stat_name in assign_to:
            if stat_name not in answer:
                return {"ok": False, "error": f"Missing assignment for {stat_name}."}
            val = answer[stat_name]
            if val not in pool:
                return {"ok": False, "error": f"Value {val} not in remaining pool."}
            pool.remove(val)
            self.sheet.stats[stat_name] = val
        self._pending_pool = []
        self._pending_assign_to = []
        return self._advance()

    def _apply_dependent_choice(self, step: dict, answer) -> dict:
        step_id = step.get("id", step.get("label", "").lower())
        depends_on = step.get("depends_on", "")
        parent_val = self._resolve_dependency(depends_on)

        # Gilded mode
        if step.get("preset_gilded") is not None:
            preset = step["preset_gilded"].get(parent_val, "")
            gilded = [preset] if preset else []
            if isinstance(answer, list):
                gilded.extend(answer)
            else:
                from_list = step.get("from", [])
                remaining = [a for a in from_list if a != preset]
                idx = int(answer) - 1
                if 0 <= idx < len(remaining):
                    gilded.append(remaining[idx])
            self.sheet.gilded_actions = gilded
            self.sheet.choices[step_id] = gilded
            return self._advance()

        # Standard dependent choice
        option_groups = step.get("option_groups", {})
        options = option_groups.get(parent_val, [])
        idx = int(answer) - 1
        if idx < 0 or idx >= len(options):
            return {"ok": False, "error": f"Choose 1-{len(options)}."}
        picked = options[idx]
        if isinstance(picked, dict):
            val = picked.get("value", picked.get("label", ""))
        else:
            val = picked
        self.sheet.choices[step_id] = val
        if step_id == "friend":
            self.sheet.friend = str(val)
        elif step_id == "rival":
            self.sheet.rival = str(val)
        return self._advance()

    def _apply_point_allocate(self, step: dict, answer: dict) -> dict:
        """Answer: {category: total_dots} for all categories being set."""
        step_id = step.get("id", step.get("label", "").lower())
        categories = step.get("categories", [])
        max_per = step.get("max_per_category", 2)
        points = step.get("points", 3)

        # Validate
        total_added = sum(answer.get(cat, 0) for cat in categories)
        preset_key = step.get("preset_key", "")
        presets = step.get("presets", {})
        preset_val = self._resolve_dependency(preset_key) if preset_key else ""
        base = presets.get(preset_val, {})
        base_total = sum(base.get(cat, 0) for cat in categories)

        if total_added - base_total > points:
            return {"ok": False, "error": f"Too many points allocated (max {points})."}

        for cat in categories:
            val = answer.get(cat, base.get(cat, 0))
            if val > max_per:
                return {"ok": False, "error": f"{cat} exceeds max {max_per}."}

        # Apply
        target = step_id
        if "action" in target or target == "action_ratings":
            for cat in categories:
                self.sheet.action_ratings[cat] = answer.get(cat, base.get(cat, 0))
        elif "drive" in target:
            for cat in categories:
                self.sheet.drives[cat] = answer.get(cat, base.get(cat, 0))
        elif "skill" in target:
            for cat in categories:
                self.sheet.skills[cat] = answer.get(cat, base.get(cat, 0))
        else:
            self.sheet.choices[step_id] = answer
        return self._advance()

    def _apply_ability_select(self, step: dict, answer: list) -> dict:
        step_id = step.get("id", step.get("label", "").lower())
        count = step.get("count", 1)
        if len(answer) != count:
            return {"ok": False, "error": f"Select exactly {count} abilities."}
        self.sheet.choices[step_id] = answer
        return self._advance()

    # ── Helpers ────────────────────────────────────────────────────────

    def _advance(self) -> dict:
        self.step_idx += 1
        if self.step_idx >= len(self.steps):
            self._complete = True
            return {"ok": True, "complete": True}
        return {"ok": True, "complete": False}

    def _roll_stats(self, method: str, count: int) -> List[int]:
        rolls = []
        for _ in range(count):
            if method == "roll_4d6_drop_lowest":
                dice = sorted([random.randint(1, 6) for _ in range(4)])
                rolls.append(sum(dice[1:]))
            else:
                rolls.append(10)
        return rolls

    def _filter_options(self, options: list) -> list:
        """Filter options by vault content availability."""
        try:
            from codex.forge.char_wizard import scan_content_availability
            available = scan_content_availability()
            return [o for o in options
                    if o.get("required_source", "Core") in available]
        except ImportError:
            return options

    def _resolve_dependency(self, dep_key: str) -> str:
        """Look up a parent choice value from the sheet."""
        if not dep_key:
            return ""
        val = self.sheet.choices.get(dep_key, "")
        if isinstance(val, dict):
            return val.get("value", val.get("label", ""))
        return str(val)

    def _apply_auto_derive(self, step: dict):
        """Compute derived stats from existing sheet data."""
        derivations = step.get("derivations", [])
        if derivations:
            for d in derivations:
                name = d.get("name", "")
                formula = d.get("formula", "0")
                sources = d.get("sources", [])
                try:
                    val = self._eval_formula(formula, sources)
                    if "resistance" in name.lower():
                        self.sheet.resistances[name] = val
                    else:
                        self.sheet.choices[name] = val
                except Exception:
                    pass
        else:
            # Single source formula
            source = step.get("source", "")
            formula = step.get("formula", "value")
            sid = step.get("id", "")
            val = self.sheet.stats.get(source, self.sheet.choices.get(source, 0))
            try:
                result = eval(formula, {"__builtins__": {}},
                              {"value": val, "floor": lambda x: int(x)})
                self.sheet.choices[sid] = result
            except Exception:
                self.sheet.choices[sid] = 0

    def _eval_formula(self, formula: str, sources: list) -> int:
        """Evaluate a derived stat formula."""
        ns = {"__builtins__": {}, "floor": lambda x: int(x)}
        for src in sources:
            ns[src] = self.sheet.stats.get(src,
                       self.sheet.choices.get(src, 0))
            if isinstance(ns[src], dict):
                ns[src] = ns[src].get("value", 0)
            try:
                ns[src] = int(ns[src])
            except (ValueError, TypeError):
                ns[src] = 0
        try:
            return int(eval(formula, ns))
        except Exception:
            return 0

    # ── Serialization ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize wizard state for session persistence."""
        return {
            "system_id": self.schema.system_id,
            "step_idx": self.step_idx,
            "complete": self._complete,
            "choices": dict(self.sheet.choices),
            "stats": dict(self.sheet.stats),
            "name": self.sheet.name,
            "action_ratings": dict(self.sheet.action_ratings),
            "drives": dict(self.sheet.drives),
            "gilded_actions": list(self.sheet.gilded_actions),
            "pending_pool": self._pending_pool,
            "pending_assign_to": self._pending_assign_to,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HeadlessWizard":
        """Restore wizard state from saved dict."""
        engine = CharacterBuilderEngine()
        schema = engine.get_system(data["system_id"])
        if not schema:
            raise ValueError(f"System '{data['system_id']}' not found in vault.")
        wizard = cls(schema)
        wizard.step_idx = data.get("step_idx", 0)
        wizard._complete = data.get("complete", False)
        wizard.sheet.choices = data.get("choices", {})
        wizard.sheet.stats = data.get("stats", {})
        wizard.sheet.name = data.get("name", "")
        wizard.sheet.action_ratings = data.get("action_ratings", {})
        wizard.sheet.drives = data.get("drives", {})
        wizard.sheet.gilded_actions = data.get("gilded_actions", [])
        wizard._pending_pool = data.get("pending_pool", [])
        wizard._pending_assign_to = data.get("pending_assign_to", [])
        return wizard
