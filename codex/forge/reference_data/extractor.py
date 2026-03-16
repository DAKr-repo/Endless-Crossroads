"""
codex.forge.reference_data.extractor -- PDF Reference Data Extractor
=====================================================================

Extracts structured reference data from vault PDFs using pypdf for text
extraction and regex patterns to identify game elements.

Output: JSON files in vault/{system}/reference/ that override hardcoded data.
Triggered manually via CLI or Librarian TUI command.

This is infrastructure — patterns will be refined as more PDFs are processed.
"""

import json
import os
import re
from typing import Dict, List, Optional, Any

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class ReferenceExtractor:
    """Extract structured reference data from vault PDFs.

    Uses pypdf for text extraction + regex patterns to identify:
    - Subrace/subclass names and descriptions
    - Feat names, prerequisites, descriptions
    - Spell names, levels, schools, components
    - Equipment names, costs, weights, properties
    """

    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = vault_path or os.path.join(_ROOT, "vault")
        self._patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for content extraction."""
        return {
            "subclass_header": re.compile(
                r'^(?:Path of|College of|Domain:|Circle of|Way of|Oath of|'
                r'School of|The |Pact of)\s+(.+?)$',
                re.MULTILINE
            ),
            "feat_header": re.compile(
                r'^([A-Z][A-Za-z\s\'-]+)$\n\s*(?:Prerequisite:\s*(.+?)$)?',
                re.MULTILINE
            ),
            "spell_entry": re.compile(
                r'^([A-Z][a-z\s\']+)\s*$\n\s*(?:(\d+)(?:st|nd|rd|th)-level\s+(\w+)|(\w+)\s+cantrip)',
                re.MULTILINE
            ),
            "equipment_entry": re.compile(
                r'^\s*([A-Z][a-z\s,]+?)\s+(\d+)\s*(?:gp|sp|cp)\s+(\d+d\d+\s+\w+)?\s*(\d+\.?\d*)\s*lb',
                re.MULTILINE
            ),
        }

    def extract_from_pdf(self, pdf_path: str, content_type: str = "auto") -> Dict[str, Any]:
        """Extract structured reference data from a PDF.

        Args:
            pdf_path: Path to the PDF file
            content_type: Type of content to extract:
                "auto" - detect from filename
                "subclasses" - subclass names and descriptions
                "feats" - feat names, prereqs, descriptions
                "spells" - spell names, levels, schools
                "equipment" - item names, costs, weights

        Returns:
            Dict of extracted data, ready to be saved as JSON override.
        """
        try:
            from pypdf import PdfReader
        except ImportError:
            return {"error": "pypdf not installed. Run: pip install pypdf"}

        try:
            reader = PdfReader(pdf_path)
        except Exception as e:
            return {"error": f"Failed to read PDF: {e}"}

        # Extract all text
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

        if not full_text.strip():
            return {"error": "No text extracted from PDF"}

        if content_type == "auto":
            content_type = self._detect_content_type(pdf_path, full_text)

        extractors = {
            "subclasses": self._extract_subclasses,
            "feats": self._extract_feats,
            "spells": self._extract_spells,
            "equipment": self._extract_equipment,
        }

        extractor = extractors.get(content_type)
        if extractor:
            return extractor(full_text)

        return {"warning": f"Unknown content type: {content_type}", "raw_length": len(full_text)}

    def _detect_content_type(self, pdf_path: str, text: str) -> str:
        """Auto-detect content type from filename and content."""
        name = os.path.basename(pdf_path).lower()
        if "spell" in name:
            return "spells"
        if "feat" in name:
            return "feats"
        if "equipment" in name or "gear" in name:
            return "equipment"
        # Default to subclasses for rulebooks
        return "subclasses"

    def _extract_subclasses(self, text: str) -> Dict:
        """Extract subclass names from text."""
        matches = self._patterns["subclass_header"].findall(text)
        return {"subclasses": [{"name": m.strip(), "source": "extracted"} for m in matches if len(m.strip()) > 3]}

    def _extract_feats(self, text: str) -> Dict:
        """Extract feat names and prerequisites from text."""
        results = []
        for match in self._patterns["feat_header"].finditer(text):
            name = match.group(1).strip()
            prereq = match.group(2).strip() if match.group(2) else None
            if len(name) > 3 and len(name) < 40:
                results.append({"name": name, "prereq": prereq, "source": "extracted"})
        return {"feats": results}

    def _extract_spells(self, text: str) -> Dict:
        """Extract spell names and levels from text."""
        results = []
        for match in self._patterns["spell_entry"].finditer(text):
            name = match.group(1).strip()
            if match.group(4):  # cantrip
                level = 0
                school = match.group(4)
            else:
                level = int(match.group(2))
                school = match.group(3)
            results.append({"name": name, "level": level, "school": school, "source": "extracted"})
        return {"spells": results}

    def _extract_equipment(self, text: str) -> Dict:
        """Extract equipment entries from text."""
        results = []
        for match in self._patterns["equipment_entry"].finditer(text):
            name = match.group(1).strip()
            cost = int(match.group(2))
            damage = match.group(3) or ""
            weight = float(match.group(4))
            results.append({"name": name, "cost": cost, "damage": damage, "weight": weight, "source": "extracted"})
        return {"equipment": results}

    def extract_all(self, system_id: str = "dnd5e") -> Dict[str, int]:
        """Extract from all PDFs in a vault system directory.

        Scans vault/{system_id}/SOURCE/ for PDFs and extracts data.
        Saves results to vault/{system_id}/reference/{type}.json.

        Returns:
            Dict of {filename: num_items_extracted}
        """
        source_dir = os.path.join(self.vault_path, system_id, "SOURCE")
        output_dir = os.path.join(self.vault_path, system_id, "reference")

        if not os.path.isdir(source_dir):
            return {"error": f"No SOURCE directory found at {source_dir}"}

        os.makedirs(output_dir, exist_ok=True)

        results = {}
        for filename in sorted(os.listdir(source_dir)):
            if not filename.lower().endswith(".pdf"):
                continue
            pdf_path = os.path.join(source_dir, filename)
            extracted = self.extract_from_pdf(pdf_path)

            if "error" not in extracted:
                # Save each extracted category to its own JSON file
                for category, items in extracted.items():
                    if isinstance(items, list) and items:
                        out_path = os.path.join(output_dir, f"{category}.json")
                        # Merge with existing
                        existing = {}
                        if os.path.isfile(out_path):
                            with open(out_path, "r") as f:
                                existing = json.load(f)
                        if isinstance(existing, dict) and category in existing:
                            existing[category].extend(items)
                        else:
                            existing[category] = items
                        with open(out_path, "w") as f:
                            json.dump(existing, f, indent=2)
                        results[filename] = len(items)
            else:
                results[filename] = 0

        return results
