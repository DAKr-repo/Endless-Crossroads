# Implementation Guide: Combat Balance Fixes
**For: @Mechanic**
**Priority: 🔴 BLOCKING - Ship Blocker**
**Estimated Time: 2-3 hours**

---

## Quick Start

**Task:** Fix combat balance for Burnwillow Tier 0 release.

**Changes Required:**
1. Update Rot-Beetle enemy stats (5 min)
2. Add healing potion item (30 min)
3. Add campfire rest mechanic (30 min)
4. Run validation tests (10 min)

**Total Time:** ~1.5 hours (core fixes only)

---

## Change 1: Update Rot-Beetle Stats

### Location
Find the enemy data file. Likely locations:
- `burnwillow_bestiary.json`
- `codex_enemies.json`
- `worlds/burnwillow/enemies.json`
- Hardcoded in `codex_combat_engine.py` (search for "Rot-Beetle")

### Current Stats (BROKEN)
```json
{
  "name": "Rot-Beetle",
  "tier": 0,
  "defense_dc": 8,
  "hp": 4,
  "damage": 2,
  "special": "Skitter (-1d6 to ranged attacks)"
}
```

### New Stats (BALANCED)
```json
{
  "name": "Rot-Beetle",
  "tier": 0,
  "defense_dc": 10,
  "hp": 6,
  "damage": 2,
  "special": "Skitter (-1d6 to ranged attacks)"
}
```

### Validation
Run this quick test after updating:
```bash
python -c "
import random
wins = 0
for _ in range(100):
    p_hp = 10
    e_hp = 6
    while p_hp > 0 and e_hp > 0:
        if sum([random.randint(1,6) for _ in range(2)]) + 1 >= 10:
            e_hp -= 3
        if e_hp <= 0: break
        p_hp -= max(0, 2 - 1)
    if p_hp > 0: wins += 1
print(f'Win rate: {wins}% (target: 75-85%)')
"
```

Expected output: `Win rate: 75-85%`

---

## Change 2: Add Healing Potion System

### Step 2.1: Create Item Class (if not exists)

**File:** `codex_items.py` or `burnwillow_items.py`

```python
import random
from dataclasses import dataclass

@dataclass
class Item:
    """Base item class."""
    name: str
    description: str
    consumable: bool = False

    def use(self, player):
        """Use item on player. Returns message string."""
        raise NotImplementedError


class HealingPotion(Item):
    """Restores 1d6 HP when consumed."""

    def __init__(self):
        super().__init__(
            name="Healing Potion",
            description="A vial of crimson liquid that smells faintly of iron and herbs. Restores 1d6 HP.",
            consumable=True
        )

    def use(self, player):
        """Restore 1d6 HP, cannot exceed max HP."""
        if player.hp >= player.max_hp:
            return "You are already at full health."

        healing = random.randint(1, 6)
        old_hp = player.hp
        player.hp = min(player.max_hp, player.hp + healing)
        actual_healing = player.hp - old_hp

        return f"You drink the healing potion and restore {actual_healing} HP. (HP: {player.hp}/{player.max_hp})"
```

### Step 2.2: Add Inventory System to Player

**File:** `codex_architect.py` or player class file

```python
class Player:
    def __init__(self):
        # ... existing init code ...
        self.inventory = []  # List of Item objects
        self.max_inventory = 10  # Or whatever limit you want

    def add_item(self, item):
        """Add item to inventory if space available."""
        if len(self.inventory) >= self.max_inventory:
            return f"Inventory full! Cannot pick up {item.name}."

        self.inventory.append(item)
        return f"Picked up {item.name}."

    def use_item(self, item_name):
        """Use item from inventory by name."""
        for item in self.inventory:
            if item.name.lower() == item_name.lower():
                if not item.consumable:
                    return f"You cannot consume {item.name}."

                message = item.use(self)
                self.inventory.remove(item)
                return message

        return f"You do not have a {item_name} in your inventory."

    def list_inventory(self):
        """Return formatted inventory list."""
        if not self.inventory:
            return "Your inventory is empty."

        items = {}
        for item in self.inventory:
            items[item.name] = items.get(item.name, 0) + 1

        lines = ["Inventory:"]
        for name, count in items.items():
            if count > 1:
                lines.append(f"  - {name} x{count}")
            else:
                lines.append(f"  - {name}")

        return "\n".join(lines)
```

### Step 2.3: Add Loot Drops

**File:** Combat engine or loot system

```python
def generate_loot(enemy_tier, player_luck=0):
    """Generate random loot after combat victory."""
    loot = []

    # Base loot chance: 30% for Tier 0 enemies
    if random.randint(1, 100) <= (30 + player_luck):
        # Healing potion is common loot
        if random.randint(1, 100) <= 50:
            loot.append(HealingPotion())

    return loot
```

### Step 2.4: Add Commands

**File:** Command parser or main game loop

```python
# Add to command handler
if command == "inventory" or command == "inv":
    print(player.list_inventory())

elif command.startswith("use "):
    item_name = command[4:].strip()
    print(player.use_item(item_name))
```

---

## Change 3: Add Campfire Rest Points

### Step 3.1: Create Campfire Object

**File:** `codex_dungeon.py` or world object file

```python
class Campfire:
    """Rest point that fully restores player HP."""

    def __init__(self, location_id):
        self.location_id = location_id
        self.used = False  # Optional: limit to one use

    def rest(self, player):
        """Fully restore player HP."""
        if self.used:
            return "The campfire has burned out. You cannot rest here again."

        old_hp = player.hp
        player.hp = player.max_hp
        healing = player.hp - old_hp

        self.used = True  # Optional

        return f"You rest by the campfire and feel your wounds mend. Restored {healing} HP. (HP: {player.hp}/{player.max_hp})"
```

### Step 3.2: Place Campfires in Dungeons

**File:** Dungeon generator or level data

```python
def generate_dungeon_level(num_encounters):
    """Generate dungeon with encounters and rest points."""
    encounters = []
    campfires = []

    for i in range(num_encounters):
        encounters.append(generate_enemy_encounter())

        # Place campfire every 4-5 encounters
        if (i + 1) % 4 == 0:
            campfires.append(Campfire(location_id=f"campfire_{i}"))

    return {
        'encounters': encounters,
        'campfires': campfires
    }
```

### Step 3.3: Add Rest Command

```python
# In main game loop or command handler
if command == "rest":
    # Check if player is at a campfire location
    campfire = get_campfire_at_current_location(player.current_location)

    if not campfire:
        print("There is no campfire here. You cannot rest.")
    else:
        print(campfire.rest(player))
```

---

## Change 4: Run Validation Tests

After implementing the above changes, run the test suite:

```bash
# Test 1: Single encounter balance
python burnwillow_combat_sim.py

# Test 2: Multi-configuration comparison
python burnwillow_combat_sim_v2.py

# Test 3: Attrition with healing (requires updated code)
python burnwillow_combat_attrition.py

# Test 4: Quick inline validation
python -c "
import random
wins = 0
for _ in range(1000):
    p_hp = 10
    e_hp = 6
    while p_hp > 0 and e_hp > 0:
        if sum([random.randint(1,6) for _ in range(2)]) + 1 >= 10:
            e_hp -= 3
        if e_hp <= 0: break
        p_hp -= max(0, 2 - 1)
    if p_hp > 0: wins += 1
print(f'Win rate: {wins/10:.1f}% (target: 75-85%)')
"
```

### Expected Results
- Single encounter win rate: 75-85%
- Avg HP remaining: 5-6 / 10
- 3-encounter gauntlet survival (with 2 potions): ~40-60%
- 5-encounter gauntlet survival (with campfire): ~10-20%

---

## Optional Changes (Non-Blocking)

### Optional 1: Redesign Ambush (30 min)

**Current:** 1 free attack before combat
**New:** Free attack + advantage on Round 1

```python
def player_attack(self, has_advantage=False):
    """Roll attack dice, optionally with advantage."""
    if has_advantage:
        # Roll 3d6, keep all (advantage)
        dice_count = 3
    else:
        # Normal 2d6
        dice_count = 2

    dice = [random.randint(1, 6) for _ in range(dice_count)]
    total = sum(dice) + self.stat_modifier
    return total, dice
```

### Optional 2: Implement Wound System (1 hour)

```python
def get_wound_state(player):
    """Determine wound state based on HP percentage."""
    hp_percent = (player.hp / player.max_hp) * 100

    if hp_percent >= 60:
        return "healthy"
    elif hp_percent >= 30:
        return "wounded"
    else:
        return "badly_wounded"


def apply_wound_penalty(attack_roll, wound_state):
    """Apply penalty to attack roll based on wound state."""
    penalties = {
        "healthy": 0,
        "wounded": -1,
        "badly_wounded": -2
    }

    return attack_roll + penalties.get(wound_state, 0)
```

---

## Checklist

### Pre-Implementation
- [ ] Backup current codebase
- [ ] Identify enemy data file location
- [ ] Identify player class location
- [ ] Identify combat engine location

### Implementation
- [ ] Update Rot-Beetle stats (DC 10, HP 6, Damage 2)
- [ ] Create HealingPotion class
- [ ] Add inventory system to Player
- [ ] Add loot generation after combat
- [ ] Create Campfire class
- [ ] Place campfires in dungeon generator
- [ ] Add "use" and "rest" commands
- [ ] Add "inventory" command

### Testing
- [ ] Run burnwillow_combat_sim.py (win rate: 75-85%)
- [ ] Test healing potion usage in-game
- [ ] Test campfire rest in dungeon
- [ ] Test inventory limits
- [ ] Test edge cases (use potion at full HP, rest twice, etc.)

### Documentation
- [ ] Update player manual with healing mechanics
- [ ] Update bestiary with new Rot-Beetle stats
- [ ] Add changelog entry

---

## Common Issues

### Issue 1: Win Rate Still Too High/Low
**Solution:** Adjust stats incrementally:
- If win rate > 85%: Increase DC by 1 or HP by 1
- If win rate < 75%: Decrease DC by 1 or HP by 1

### Issue 2: Healing Too Powerful
**Solution:** Reduce healing die from 1d6 to 1d4, or limit potions to 2 max instead of 3.

### Issue 3: Campfires Too Frequent
**Solution:** Place every 5-6 encounters instead of 4.

### Issue 4: Import Errors
**Solution:** Ensure all new classes are imported in main files:
```python
from codex_items import HealingPotion
from codex_dungeon import Campfire
```

---

## Questions? Blockers?

**Contact:** Codex Playtester (QA lead)
**Test Files:** `/home/pi/Projects/claude_sandbox/Codex/burnwillow_combat_*.py`
**Documentation:** `/home/pi/Projects/claude_sandbox/Codex/GRINDER_FINAL_REPORT.md`

**Status:** 🔴 BLOCKING - Priority implementation required before Tier 0 ship.
