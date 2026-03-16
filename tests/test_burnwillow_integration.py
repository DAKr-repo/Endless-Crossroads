#!/usr/bin/env python3
"""
Integration test for Burnwillow + Universal Map Engine.

Tests:
1. Engine initialization
2. Character creation
3. Dungeon generation (with seed)
4. Room navigation
5. Content population verification
6. Save/Load with dungeon state
"""

from codex.games.burnwillow.engine import BurnwillowEngine, StatType, DC
import json

def test_full_integration():
    print("=" * 70)
    print("BURNWILLOW INTEGRATION TEST")
    print("=" * 70)

    # Test 1: Engine initialization
    print("\n[TEST 1: Engine Initialization]")
    engine = BurnwillowEngine()
    print("✓ Engine initialized")

    # Test 2: Character creation
    print("\n[TEST 2: Character Creation]")
    hero = engine.create_character("Test Hero")
    print(f"✓ Character created: {hero.name}")
    print(f"  Stats: M{hero.might} W{hero.wits} G{hero.grit} A{hero.aether}")

    # Test 3: Dungeon generation
    print("\n[TEST 3: Dungeon Generation]")
    summary = engine.generate_dungeon(depth=4, seed=12345)
    print(f"✓ Dungeon generated:")
    print(f"  Seed: {summary['seed']}")
    print(f"  Total rooms: {summary['total_rooms']}")
    print(f"  Start room: {summary['start_room']}")
    assert summary['total_rooms'] >= 8, "Expected at least 8 rooms from depth=4"

    # Test 4: Current room
    print("\n[TEST 4: Current Room Inspection]")
    room = engine.get_current_room()
    print(f"✓ Current room: {room['id']}")
    print(f"  Type: {room['type']}")
    print(f"  Tier: {room['tier']}")
    print(f"  Description: {room['description'][:50]}...")
    print(f"  Enemies: {len(room['enemies'])}")
    print(f"  Loot: {len(room['loot'])}")
    print(f"  Hazards: {len(room['hazards'])}")
    assert room['type'] == 'start', "First room should be start room"

    # Test 5: Navigation
    print("\n[TEST 5: Room Navigation]")
    connected = engine.get_connected_rooms()
    print(f"✓ Connected rooms: {len(connected)}")
    for conn in connected:
        print(f"  - Room {conn['id']}: {conn['type']} (Tier {conn['tier']})")

    if connected:
        target = connected[0]['id']
        result = engine.move_to_room(target)
        print(f"✓ Moved to room {target}: {result['message']}")
        assert result['success'], "Movement should succeed"

        new_room = engine.get_current_room()
        print(f"  Now in room {new_room['id']}: {new_room['description'][:40]}...")

    # Test 6: Content verification
    print("\n[TEST 6: Content Population]")
    map_summary = engine.get_dungeon_map_summary()
    boss_rooms = [r for r in map_summary['rooms'] if r['type'] == 'boss']
    treasure_rooms = [r for r in map_summary['rooms'] if r['type'] == 'treasure']
    print(f"✓ Content verification:")
    print(f"  Boss rooms: {len(boss_rooms)}")
    print(f"  Treasure rooms: {len(treasure_rooms)}")
    assert len(boss_rooms) >= 1, "Should have at least 1 boss room"

    # Test 7: Save/Load
    print("\n[TEST 7: Save/Load with Dungeon State]")
    save_data = engine.save_game()
    print(f"✓ Game saved: {len(json.dumps(save_data))} bytes")
    assert save_data['dungeon'] is not None, "Dungeon data should be saved"

    # Reset and reload
    engine.reset()
    print("  Engine reset")
    assert engine.dungeon_graph is None, "Dungeon should be cleared"

    engine.load_game(save_data)
    print("✓ Game loaded")
    restored_room = engine.get_current_room()
    print(f"  Restored to room {restored_room['id']}")
    assert restored_room['id'] == new_room['id'], "Should restore to same room"

    # Test 8: Deterministic generation
    print("\n[TEST 8: Deterministic Generation (Seed Consistency)]")
    engine1 = BurnwillowEngine()
    engine1.generate_dungeon(depth=3, seed=999)
    room1 = engine1.get_current_room()

    engine2 = BurnwillowEngine()
    engine2.generate_dungeon(depth=3, seed=999)
    room2 = engine2.get_current_room()

    print(f"✓ Same seed produces identical dungeon:")
    print(f"  Engine 1 start room: {room1['id']}")
    print(f"  Engine 2 start room: {room2['id']}")
    assert room1['id'] == room2['id'], "Same seed should produce same start room"
    assert room1['description'] == room2['description'], "Same seed should produce same content"

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED")
    print("=" * 70)

if __name__ == "__main__":
    test_full_integration()
