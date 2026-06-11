# Memory System Upgrade - Structured Active Memory & Auto-Consolidation

* **Date:** 2026-06-11
* **Status:** Approved
* **Authors:** Antigravity (Gemini 3.5 Flash)

---

## 1. Goal & Requirements
Upgrade the Buffett Strategic Analyst's memory system from a raw, append-only Markdown file (`active_memory.md`) to a structured, auto-consolidating memory layer. This will prevent token bloat and context poisoning from stale macro-economic data.

### Key Constraints:
1. **Compatibility:** The listener (`listener/main.py`) and agent (`SKILL.md`) expect a markdown file at `knowledge_base/active_memory.md`. We must preserve this file path.
2. **Pruning Rules:** Macro entries expire after 90 days by default. Old entries must be archived rather than completely deleted to preserve historical logs.
3. **Categories:** Entries should be categorized under: `Monetary Policy`, `Energy`, `Geopolitics`, or `Regional` (US/EU/China/Japan).

---

## 2. Technical Architecture

We will implement a two-file architecture:

1. **`knowledge_base/active_memory.json` (Source of Truth):**
   Stores the full list of insights, including metadata and archive status.
2. **`knowledge_base/active_memory.md` (Compiled Markdown View):**
   Automatically regenerated on every update to show only `active` entries (entries where the current date is before `expires_at` and `status == "active"`).

### Data Flow Diagram:
```
[User/Agent Input]
       |
       v
[manage_memory.py] (adds entry, computes expiration)
       |
       +---> Writes to: [active_memory.json] (all entries)
       |
       +---> Triggers Consolidation (checks dates, updates status to "archived")
       |
       +---> Compiles active entries into: [active_memory.md]
                                                   |
                                                   v
                                          [LLM Agent Context]
```

### JSON Entry Schema:
```json
{
  "date": "YYYY-MM-DD",
  "category": "Monetary Policy | Energy | Geopolitics | Regional",
  "insight": "Description of the macro insight...",
  "status": "active | archived",
  "expires_at": "YYYY-MM-DD"
}
```

---

## 3. Migration & Backwards Compatibility
1. **Bootstrapping:** The upgraded `manage_memory.py` will search for `active_memory.json`. If missing, it will parse the existing `active_memory.md` to populate the initial JSON database.
2. **Default Categorization:** During bootstrapping, regex rules will classify existing entries based on keywords (e.g. "Fed" -> "Monetary Policy", "energy" -> "Energy", etc.).
3. **Expiration Logic:** Bootstrapped historical entries will have their expiration dates calculated from their log date (date + 90 days).
