import json
import os
from pathlib import Path

# PATH SETUP
BASE_DIR = Path(__file__).resolve().parent.parent  # Project root, not maintenance/
CONFIG_DIR = str(BASE_DIR / "config" / "systems")

def create_system_config():
    print("--- C.O.D.E.X.: SYSTEM SCAFFOLDER ---")
    
    # Ensure directory exists
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # Basic Info
    display_name = input("Enter Game System Name (e.g., Cyberpunk Red): ")
    system_id = input("Enter System ID (Short Code, e.g., CPR): ").upper()
    engine = input("Enter Engine Type (e.g., Interlock, d20, PbtA): ")

    # Categories and Archetypes
    archetype_categories = {}
    while True:
        cat_name = input("\nEnter a category name (e.g., 'Classes', 'Roles') or 'done': ")
        if cat_name.lower() == 'done':
            break
        
        members_input = input(f"Enter members for '{cat_name}' separated by commas: ")
        members = [m.strip() for m in members_input.split(',')]
        archetype_categories[cat_name] = members

    # Stats and Resources
    stats_input = input("\nEnter Core Stats separated by commas (e.g., STR, DEX, INT): ")
    stats = [s.strip() for s in stats_input.split(',')]

    res_input = input("Enter Resources separated by commas (e.g., HP, Mana, Stress): ")
    resources = [r.strip() for r in res_input.split(',')]

    # Construct JSON
    system_data = {
        "system_id": system_id,
        "display_name": display_name,
        "engine": engine,
        "archetype_categories": archetype_categories,
        "core_stats": stats,
        "resources": resources
    }

    # Save File
    file_path = os.path.join(CONFIG_DIR, f"rules_{system_id}.json")
    with open(file_path, 'w') as f:
        json.dump(system_data, f, indent=4)
    
    print(f"\n✅ System Config Saved: {file_path}")

if __name__ == "__main__":
    create_system_config()
