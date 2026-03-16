#!/usr/bin/env python3
"""
vault_processor.py — Integrated Equipment Extractor for C.O.D.E.X. Registry

Integrates with the existing C.O.D.E.X. registry architecture to extract
equipment/loot data from PDFs and update system configuration files.

Author: @Archivist Agent
Date: 2026-02-04
Work Order: 047-B
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

try:
    import pypdf
except ImportError:
    print("ERROR: pypdf not installed. Run: pip install pypdf")
    sys.exit(1)

try:
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.console import Console
    USE_RICH = True
except ImportError:
    USE_RICH = False


# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # -> Codex/
BRANDING_REGISTRY = BASE_DIR / "config" / "branding_registry.json"
CONFIG_DIR = BASE_DIR / "config" / "systems"
VAULT_DIR = BASE_DIR / "vault"

# Vault subdirectory name -> System ID mapping
# Supports both flat (vault/dnd5e) and nested (vault/FITD/bitd) paths.
VAULT_SYSTEM_MAP = {
    "dnd5e": "DND5E",
    "burnwillow": "BURNWILLOW",
    "bitd": "BITD",
    "sav": "SAV",
    "bob": "BOB",
    "stc": "STC",
    "cbr_pnk": "CBRPNK",
    "candela_obscura": "CANDELA",
    "crown": "CROWN",
}

# Maps system_id -> system_family for equipment metadata enrichment.
VAULT_FAMILY_MAP = {
    "BITD": "FITD",
    "SAV": "FITD",
    "BOB": "FITD",
    "CBRPNK": "FITD",
    "CANDELA": "ILLUMINATED_WORLDS",
    "DND5E": "DND5E",
    "BURNWILLOW": "BURNWILLOW",
    "STC": "STC",
    "CROWN": "CROWN",
}


# ============================================================================
# REGEX PATTERNS FOR EQUIPMENT DETECTION
# ============================================================================

# Damage dice patterns (1d6, 2d8, 3d10+2, etc.)
DAMAGE_PATTERN = re.compile(r'\b\d+d\d+(?:\s*[+\-]\s*\d+)?\b', re.IGNORECASE)

# AC/Armor Class patterns
AC_PATTERN = re.compile(r'\b(?:AC|Armor\s+Class)\s*[:=]?\s*(\d+(?:\s*\+\s*Dex)?)', re.IGNORECASE)

# Cost/Price patterns (gp, sp, cp, gold, silver, copper, credits, coin)
COST_PATTERN = re.compile(
    r'\b(\d+(?:,\d{3})*)\s*(?:gp|sp|cp|gold|silver|copper|credits?|coins?|cred)\b',
    re.IGNORECASE
)

# Weight patterns
WEIGHT_PATTERN = re.compile(r'\b(\d+(?:\.\d+)?)\s*(?:lb|lbs|pounds?|kg)\b', re.IGNORECASE)

# Table header detection (equipment lists often have headers)
TABLE_HEADER_PATTERN = re.compile(
    r'\b(?:Name|Item|Weapon|Armor|Equipment)\s+(?:Cost|Price|Value|Damage|AC|Weight)\b',
    re.IGNORECASE
)

# Weapon keywords
WEAPON_KEYWORDS = [
    'sword', 'axe', 'mace', 'dagger', 'bow', 'crossbow', 'spear', 'hammer',
    'blade', 'rapier', 'scimitar', 'whip', 'staff', 'club', 'javelin',
    'melee', 'ranged', 'martial', 'simple', 'weapon', 'longsword', 'shortsword',
    'greatsword', 'battleaxe', 'warhammer', 'flail', 'pike', 'lance', 'trident',
    'gun', 'pistol', 'rifle', 'blaster', 'laser'
]

# Armor keywords
ARMOR_KEYWORDS = [
    'armor', 'shield', 'plate', 'mail', 'leather', 'hide', 'chain',
    'breastplate', 'scale', 'splint', 'padded', 'studded', 'protection',
    'vest', 'helmet', 'gauntlet', 'greaves'
]

# Potion/consumable keywords
POTION_KEYWORDS = [
    'potion', 'elixir', 'draught', 'brew', 'tincture', 'philter',
    'scroll', 'consumable', 'dose', 'vial', 'flask'
]

# General equipment keywords
GENERAL_KEYWORDS = [
    'adventuring gear', 'equipment', 'tools', 'kit', 'rope', 'torch',
    'lantern', 'backpack', 'bedroll', 'rations', 'waterskin', 'trinket'
]

# Magic item keywords
MAGIC_ITEM_KEYWORDS = [
    'wondrous item', 'requires attunement', 'uncommon', 'rare', 'very rare',
    'legendary', 'artifact', 'magic weapon', 'magic armor', 'enchanted',
    '+1', '+2', '+3', 'cursed', 'sentient'
]

# Section headers that indicate magic item sections
MAGIC_SECTION_HEADERS = [
    'magic items', 'appendix d', 'wondrous items', 'treasure',
    'sentient items', 'artifacts'
]


# ============================================================================
# CATEGORIZATION LOGIC
# ============================================================================

def categorize_item(text_line: str, context_header: str = "") -> str:
    """
    Determine item category based on text content.

    Args:
        text_line: The text line to categorize
        context_header: Optional section header for context

    Returns:
        Category string: "weapons", "armor", "potions", "magic_items", or "general"
    """
    text_lower = text_line.lower()
    context_lower = context_header.lower()

    # Check for magic items FIRST (rarity keywords, attunement, +N bonus)
    if any(keyword in text_lower for keyword in MAGIC_ITEM_KEYWORDS):
        return "magic_items"
    if any(header in context_lower for header in MAGIC_SECTION_HEADERS):
        return "magic_items"

    # Check for potions/consumables (specific category)
    if any(keyword in text_lower for keyword in POTION_KEYWORDS):
        return "potions"

    # Check for weapons (has damage dice or weapon keywords)
    if DAMAGE_PATTERN.search(text_line):
        if not any(keyword in text_lower for keyword in ARMOR_KEYWORDS):
            return "weapons"

    if any(keyword in text_lower for keyword in WEAPON_KEYWORDS):
        return "weapons"

    # Check for armor (has AC or armor keywords)
    if AC_PATTERN.search(text_line) or any(keyword in text_lower for keyword in ARMOR_KEYWORDS):
        return "armor"

    # Check context header for category hints
    if any(keyword in context_lower for keyword in WEAPON_KEYWORDS):
        if COST_PATTERN.search(text_line):
            return "weapons"

    if any(keyword in context_lower for keyword in ARMOR_KEYWORDS):
        if COST_PATTERN.search(text_line):
            return "armor"

    # Default to general equipment
    return "general"


def extract_item_name(text_line: str) -> Optional[str]:
    """
    Extract item name from a text line.

    Uses heuristics to find the item name, typically at the start of the line.
    """
    # Remove leading/trailing whitespace
    text = text_line.strip()

    # Try to extract name before first number or special delimiter
    # Pattern: Capitalized words before cost/stats
    name_match = re.match(r'^([A-Z][a-zA-Z\s\-\']+?)(?:\s+[\d\(]|\s*\.{2,}|\s*,|\s+\d)', text)
    if name_match:
        return name_match.group(1).strip()

    # Fallback: take first 3-6 words if they're capitalized
    words = text.split()
    if words and words[0][0].isupper():
        name_words = []
        for word in words[:6]:
            if word[0].isupper() or word.lower() in ['of', 'the', 'and', 'or']:
                name_words.append(word)
            else:
                break
        if name_words:
            return " ".join(name_words)

    return None


def extract_item_data(text_line: str, category: str, source_file: str, page_num: int) -> Optional[Dict[str, Any]]:
    """
    Extract structured data from a text line based on category.

    Args:
        text_line: The line of text to parse
        category: Item category (weapons, armor, potions, general)
        source_file: PDF filename
        page_num: Page number in PDF

    Returns:
        Dictionary with extracted item data, or None if insufficient data
    """
    # Extract common fields
    cost_match = COST_PATTERN.search(text_line)
    weight_match = WEIGHT_PATTERN.search(text_line)
    name = extract_item_name(text_line)

    if not name:
        return None

    item = {
        "name": name,
        "source": source_file,
        "page": page_num
    }

    if cost_match:
        item["cost"] = f"{cost_match.group(1)} {cost_match.group(2) if len(cost_match.groups()) > 1 else 'gp'}"

    if weight_match:
        item["weight"] = f"{weight_match.group(1)} lb"

    # Category-specific fields
    if category == "weapons":
        damage_match = DAMAGE_PATTERN.search(text_line)
        if damage_match:
            item["damage"] = damage_match.group(0)

            # Try to extract damage type (slashing, piercing, bludgeoning, etc.)
            damage_types = ['slashing', 'piercing', 'bludgeoning', 'fire', 'cold', 'lightning', 'acid', 'poison', 'radiant', 'necrotic', 'psychic', 'force', 'thunder']
            for dtype in damage_types:
                if dtype in text_line.lower():
                    item["damage_type"] = dtype
                    break

        # Extract properties (finesse, heavy, light, etc.)
        properties = []
        prop_keywords = ['finesse', 'heavy', 'light', 'loading', 'range', 'reach', 'thrown', 'two-handed', 'versatile', 'ammunition']
        for prop in prop_keywords:
            if prop in text_line.lower():
                properties.append(prop)
        if properties:
            item["properties"] = properties

    elif category == "armor":
        ac_match = AC_PATTERN.search(text_line)
        if ac_match:
            item["ac"] = ac_match.group(1)

        # Extract armor type
        if 'light' in text_line.lower():
            item["type"] = "light"
        elif 'medium' in text_line.lower():
            item["type"] = "medium"
        elif 'heavy' in text_line.lower():
            item["type"] = "heavy"
        elif 'shield' in text_line.lower():
            item["type"] = "shield"

        # Check for stealth disadvantage
        if 'disadvantage' in text_line.lower() and 'stealth' in text_line.lower():
            item["stealth"] = "disadvantage"

    elif category == "potions":
        # Extract rarity
        rarities = ['common', 'uncommon', 'rare', 'very rare', 'legendary', 'artifact']
        for rarity in rarities:
            if rarity in text_line.lower():
                item["rarity"] = rarity
                break

        # Store description/effect (first 150 chars)
        item["effect"] = text_line[:150]

    else:  # general
        # Store description
        item["description"] = text_line[:200]

    # Only return item if it has meaningful data (name + at least one other field)
    if len(item) > 3:  # name, source, page + at least one more field
        return item

    return None


# ============================================================================
# PDF PROCESSING CORE
# ============================================================================

class EquipmentExtractor:
    """Extracts equipment data from PDFs for a specific TTRPG system."""

    def __init__(self, system_id: str, system_vault_path: Path):
        self.system_id = system_id
        self.vault_path = system_vault_path
        self.equipment = {
            "weapons": [],
            "armor": [],
            "potions": [],
            "general": [],
            "magic_items": [],
        }
        self.stats = {
            "pdfs_processed": 0,
            "pages_processed": 0,
            "items_extracted": 0,
            "errors": 0
        }

        if USE_RICH:
            self.console = Console()

    def find_pdfs(self) -> List[Path]:
        """Find all PDFs in the system's vault directory."""
        if not self.vault_path.exists():
            return []
        return sorted(self.vault_path.rglob("*.pdf"))

    def process_pdf(self, pdf_path: Path, progress_task=None, progress=None) -> None:
        """Process a single PDF and extract equipment data."""
        try:
            reader = pypdf.PdfReader(str(pdf_path))
            total_pages = len(reader.pages)
            current_section = ""
            in_equipment_section = False

            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text()
                    if not text:
                        continue

                    lines = text.split('\n')

                    for line in lines:
                        line = line.strip()
                        if not line or len(line) < 5:
                            continue

                        # Detect section headers
                        if line.isupper() and len(line) < 60:
                            current_section = line
                            # Check if we're entering equipment-related section
                            in_equipment_section = any(
                                keyword in line.lower()
                                for keyword in [
                                    'equipment', 'weapon', 'armor', 'item', 'gear',
                                    'treasure', 'loot', 'magic items', 'appendix d',
                                    'wondrous items', 'artifacts',
                                ]
                            )
                            continue

                        # Skip if not in equipment section (optimization)
                        if not in_equipment_section:
                            # But still check for table headers
                            if TABLE_HEADER_PATTERN.search(line):
                                in_equipment_section = True
                            else:
                                continue

                        # Check for equipment-like patterns
                        has_damage = bool(DAMAGE_PATTERN.search(line))
                        has_ac = bool(AC_PATTERN.search(line))
                        has_cost = bool(COST_PATTERN.search(line))

                        # Only process lines with at least one equipment indicator
                        if has_damage or has_ac or has_cost:
                            category = categorize_item(line, current_section)
                            item_data = extract_item_data(line, category, pdf_path.name, page_num)

                            if item_data:
                                self.equipment[category].append(item_data)
                                self.stats["items_extracted"] += 1

                    self.stats["pages_processed"] += 1

                    if progress and progress_task is not None:
                        progress.update(
                            progress_task,
                            advance=1,
                            description=f"[cyan]{pdf_path.name}[/cyan] ({page_num}/{total_pages}) - {self.stats['items_extracted']} items"
                        )

                except Exception as e:
                    self.stats["errors"] += 1
                    if USE_RICH:
                        self.console.print(f"[yellow]Warning: Page {page_num} of {pdf_path.name}: {e}[/yellow]")

            self.stats["pdfs_processed"] += 1

        except Exception as e:
            self.stats["errors"] += 1
            if USE_RICH:
                self.console.print(f"[red]Error processing {pdf_path.name}: {e}[/red]")
            else:
                print(f"ERROR: {pdf_path.name}: {e}")

    def extract_all(self) -> Dict[str, Any]:
        """Extract equipment from all PDFs in the system's vault."""
        pdfs = self.find_pdfs()

        if not pdfs:
            if USE_RICH:
                self.console.print(f"[yellow]No PDFs found for {self.system_id} in {self.vault_path}[/yellow]")
            else:
                print(f"No PDFs found for {self.system_id}")
            return self.equipment

        # Count total pages for progress bar
        total_pages = 0
        for pdf in pdfs:
            try:
                reader = pypdf.PdfReader(str(pdf))
                total_pages += len(reader.pages)
            except:
                pass

        if USE_RICH:
            self.console.print(f"\n[bold cyan]Processing {self.system_id}:[/bold cyan] {len(pdfs)} PDFs, {total_pages} pages")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console
            ) as progress:
                task = progress.add_task(f"Extracting {self.system_id}...", total=total_pages)

                for pdf_path in pdfs:
                    self.process_pdf(pdf_path, task, progress)
        else:
            for i, pdf_path in enumerate(pdfs, 1):
                print(f"[{i}/{len(pdfs)}] Processing {pdf_path.name}...")
                self.process_pdf(pdf_path)

        return self.equipment


# ============================================================================
# REGISTRY INTEGRATION
# ============================================================================

def load_branding_registry() -> Dict[str, Any]:
    """Load the branding registry to identify active systems."""
    if not BRANDING_REGISTRY.exists():
        print(f"ERROR: Branding registry not found at {BRANDING_REGISTRY}")
        return {}

    with open(BRANDING_REGISTRY, 'r') as f:
        return json.load(f)


def load_or_create_system_config(system_id: str) -> Dict[str, Any]:
    """Load existing system config or create new one."""
    config_file = CONFIG_DIR / f"rules_{system_id}.json"

    if config_file.exists():
        with open(config_file, 'r') as f:
            return json.load(f)
    else:
        # Create minimal config
        return {
            "name": f"System {system_id}",
            "mechanics": {}
        }


def save_system_config(system_id: str, config_data: Dict[str, Any]) -> None:
    """Save updated system config with equipment data."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_file = CONFIG_DIR / f"rules_{system_id}.json"

    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=4)

    if USE_RICH:
        console = Console()
        console.print(f"[green]✓ Updated: {config_file}[/green]")
    else:
        print(f"Updated: {config_file}")


def merge_equipment_data(existing_equipment: Dict[str, List], new_equipment: Dict[str, List]) -> Dict[str, List]:
    """
    Merge new equipment data into existing data, avoiding duplicates.

    Deduplication is based on item name.
    """
    merged = {}

    for category in ["weapons", "armor", "potions", "general", "magic_items"]:
        existing = existing_equipment.get(category, [])
        new = new_equipment.get(category, [])

        # Create a dict keyed by name for deduplication
        items_dict = {}

        # Add existing items
        for item in existing:
            name = item.get("name", "")
            if name:
                items_dict[name] = item

        # Add new items (overwrite if same name)
        for item in new:
            name = item.get("name", "")
            if name:
                items_dict[name] = item

        # Convert back to list, sorted by name
        merged[category] = sorted(items_dict.values(), key=lambda x: x.get("name", ""))

    return merged


# ============================================================================
# MAIN PROCESSOR
# ============================================================================

def main():
    """Main entry point for integrated vault processor."""
    if USE_RICH:
        console = Console()
        console.print("\n[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]  C.O.D.E.X. INTEGRATED VAULT PROCESSOR  [/bold cyan]")
        console.print("[bold cyan]  @Archivist Agent - Equipment Extraction  [/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]\n")
    else:
        print("\n" + "="*50)
        print("  C.O.D.E.X. INTEGRATED VAULT PROCESSOR")
        print("  @Archivist Agent - Equipment Extraction")
        print("="*50 + "\n")

    # Load branding registry
    registry = load_branding_registry()
    if not registry:
        print("ERROR: No systems found in branding registry.")
        sys.exit(1)

    if USE_RICH:
        console.print(f"[cyan]Found {len(registry)} registered systems:[/cyan]")
        for system_id in registry.keys():
            console.print(f"  • {system_id}: {registry[system_id]['title']}")
    else:
        print(f"Found {len(registry)} registered systems:")
        for system_id in registry.keys():
            print(f"  • {system_id}: {registry[system_id]['title']}")

    # Process each system
    total_items_extracted = 0

    for vault_name, system_id in VAULT_SYSTEM_MAP.items():
        if system_id not in registry:
            continue

        vault_path = VAULT_DIR / vault_name

        if not vault_path.exists():
            if USE_RICH:
                console.print(f"[yellow]Skipping {system_id}: vault directory not found at {vault_path}[/yellow]")
            else:
                print(f"Skipping {system_id}: vault directory not found")
            continue

        # Extract equipment
        extractor = EquipmentExtractor(system_id, vault_path)
        equipment = extractor.extract_all()

        if extractor.stats["items_extracted"] == 0:
            if USE_RICH:
                console.print(f"[yellow]No equipment extracted for {system_id}[/yellow]")
            else:
                print(f"No equipment extracted for {system_id}")
            continue

        # Load existing system config
        config = load_or_create_system_config(system_id)

        # Merge equipment data
        existing_equipment = config.get("equipment", {})
        merged_equipment = merge_equipment_data(existing_equipment, equipment)

        # Add metadata
        merged_equipment["_metadata"] = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "extraction_stats": {
                "pdfs_processed": extractor.stats["pdfs_processed"],
                "pages_processed": extractor.stats["pages_processed"],
                "total_items": sum(len(items) for items in merged_equipment.values() if isinstance(items, list)),
                "errors": extractor.stats["errors"]
            }
        }

        # Update config
        config["equipment"] = merged_equipment

        # Save
        save_system_config(system_id, config)

        # Stats
        items_count = sum(len(items) for items in merged_equipment.values() if isinstance(items, list))
        total_items_extracted += items_count

        if USE_RICH:
            console.print(f"\n[green]✓ {system_id} Equipment Summary:[/green]")
            console.print(f"  Weapons: {len(merged_equipment.get('weapons', []))}")
            console.print(f"  Armor: {len(merged_equipment.get('armor', []))}")
            console.print(f"  Potions: {len(merged_equipment.get('potions', []))}")
            console.print(f"  General: {len(merged_equipment.get('general', []))}")
            console.print(f"  [bold]Total: {items_count} items[/bold]")
        else:
            print(f"\n{system_id} Equipment Summary:")
            print(f"  Weapons: {len(merged_equipment.get('weapons', []))}")
            print(f"  Armor: {len(merged_equipment.get('armor', []))}")
            print(f"  Potions: {len(merged_equipment.get('potions', []))}")
            print(f"  General: {len(merged_equipment.get('general', []))}")
            print(f"  Total: {items_count} items")

    # Final summary
    if USE_RICH:
        console.print(f"\n[bold green]════════════════════════════════════════════[/bold green]")
        console.print(f"[bold green]  EXTRACTION COMPLETE  [/bold green]")
        console.print(f"[bold green]  Total items processed: {total_items_extracted}  [/bold green]")
        console.print(f"[bold green]════════════════════════════════════════════[/bold green]\n")
    else:
        print(f"\n{'='*50}")
        print(f"  EXTRACTION COMPLETE")
        print(f"  Total items processed: {total_items_extracted}")
        print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
