# D&D 5e Source Verification Audit — 2026-04-07

## Summary

964 items checked against 31 indexed D&D 5e PDFs via FAISS semantic similarity.

| Metric | Value |
|--------|-------|
| Total items | 964 |
| Verified (>=75%) | 3 (false positives — matching wrong source) |
| Suspect (55-75%) | 961 |
| Unverified (<55%) | 0 |
| Similarity range | 61.6% — 81.0% |
| Mean similarity | 68.5% |

## By Content Type

| Type | Count | Avg Sim | Min | Max |
|------|-------|---------|-----|-----|
| room_description | 297 | 69.1% | 64.5% | 81.0% |
| read_aloud | 297 | 69.0% | 62.4% | 75.7% |
| npc | 185 | 66.8% | 61.6% | 74.8% |
| bestiary | 185 | 68.5% | 64.1% | 74.0% |

## By Module — Source Fidelity

| Module | Items | Matches Own Source | Verdict |
|--------|-------|--------------------|---------|
| **out_of_abyss** | 116 | 85% | Likely PDF-extracted |
| **dragon_heist** | 168 | 12% | Training data authored |
| **mad_mage** | 92 | 13% | Training data authored |
| **rime_frostmaiden** | 108 | 3% | Training data authored |
| **tyranny_dragons** | 110 | 4% | Training data authored |

## Key Finding

Out of the Abyss is the only module with high source fidelity (85% of items match their own PDF). The other 4 modules (478 items) were authored from LLM training data — descriptions are generically D&D-flavored but not extracted from the actual source PDFs.

The 3 "verified" items are false positives: "Well of Dragons" content matching "Ghosts of Saltmarsh" chunks at 81% due to generic D&D combat language similarity.

## Bestiary & NPCs

Both sit at 65-69% average similarity — generic D&D monster/NPC descriptions not tied to specific source pages. The bestiary needs re-extraction from Monster Manual, Volo's Guide, and Mordenkainen's Tome. NPCs need re-extraction from their respective adventure modules.

## Recommendation

1. Keep Out of the Abyss (85% fidelity)
2. Re-extract Dragon Heist, Mad Mage, Rime of the Frostmaiden, Tyranny of Dragons from their source PDFs
3. Re-extract bestiary from MM/Volo's/Mordenkainen's
4. Re-extract NPCs from their respective modules
5. Mark all re-extracted content with source page citations once PageIndex (#139) is built

## Raw Data

- Full report: `reports/dnd5e_audit.txt`
- JSON results: `reports/dnd5e_audit.json`
