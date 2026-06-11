# Memory System Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the memory system of the stock-tracker analyst agent from raw Markdown logging to structured JSON data under the hood, featuring auto-consolidation (archiving entries older than 90 days) and automated markdown compilation for LLM compatibility.

**Architecture:** Under the hood, memory is persisted in `knowledge_base/active_memory.json`. A new test suite is created to verify bootstrapping, auto-consolidation, and compilation. On every update or run, the script consolidates stale memories to `archived` status, then rewrites the active ones to `knowledge_base/active_memory.md` to keep the agent's context window small and fresh.

**Tech Stack:** Python 3 (standard library: `json`, `datetime`, `re`, `os`, `sys`), and `pytest` for testing.

---

### Task 1: Create Test Cases for Upgraded MemoryManager

**Files:**
- Create: `agent/skills/buffett_analyst/scripts/test_manage_memory.py`

- [ ] **Step 1: Write test cases covering bootstrapping, appending, consolidation, and markdown compilation**
  Create the test file `agent/skills/buffett_analyst/scripts/test_manage_memory.py` with the following content:
  ```python
  import os
  import tempfile
  import json
  import datetime
  from manage_memory import MemoryManager

  def test_bootstrap_and_classification():
      """
      Verify that the MemoryManager correctly bootstraps from raw markdown
      when no JSON database exists, and classifies topics correctly.
      """
      with tempfile.TemporaryDirectory() as tmpdir:
          md_file = os.path.join(tmpdir, "active_memory.md")
          json_file = os.path.join(tmpdir, "active_memory.json")

          md_content = """# Active Memory - Macro Trends & Strategic Insights

  This file maintains continuity across daily research reports.

  ## Macro Narrative Log

  - **2026-05-13**: Global inflation surging to 4.0% driven by energy shock (Brent 00-20). Fed maintaining 'higher for longer' stance at 3.50%-3.75%. Geopolitical instability in Middle East and Venezuela impacting energy supplies.
  - **2026-05-13**: Federal Reserve maintains interest rates; market expects pivot in Q3.
  - **2024-05-10**: US CPI data came in slightly higher than expected (3.4% YoY). Market is pricing in "higher for longer" interest rates, putting pressure on high-debt utilities and real estate sectors.
  - **2024-05-09**: ECB signaling a potential rate cut in June as Eurozone inflation stabilizes. Bullish for European value stocks with strong export moats.
  - **2024-05-08**: Japanese Yen remains volatile despite recent intervention. Impacting "carry trade" dynamics and providing a mixed outlook for Japanese exporters.
  - **2024-05-07**: China announces new stimulus measures for its property sector. Monitoring impact on global commodity prices and consumer discretionary demand in the region.
  """
          with open(md_file, "w", encoding="utf-8") as f:
              f.write(md_content)

          # Load manager with a dummy fixed reference date (e.g. 2026-06-11)
          # to ensure predictable expiration behavior
          ref_date = datetime.date(2026, 6, 11)
          manager = MemoryManager(file_path=md_file, json_path=json_file, reference_date=ref_date)

          # Verify that JSON database was generated
          assert os.path.exists(json_file)
          with open(json_file, "r") as f:
              data = json.load(f)

          assert len(data) == 6
          
          # Check classifications & metadata for specific items
          # Entry 0: "Global inflation surging..." should be Energy or Geopolitics or Monetary Policy
          assert data[0]["category"] in ["Energy", "Geopolitics", "Monetary Policy"]
          # Entry 1: "Federal Reserve maintains..." -> Monetary Policy
          assert data[1]["category"] == "Monetary Policy"
          # Entry 4: "Japanese Yen..." -> Regional
          assert data[4]["category"] == "Regional"

          # Verify statuses based on ref_date (2026-06-11)
          # 2026-05-13 + 90 days = 2026-08-11 -> Active
          assert data[0]["status"] == "active"
          # 2024-05-10 + 90 days = 2024-08-08 -> Archived
          assert data[2]["status"] == "archived"

  def test_append_insight():
      """
      Verify that appending a new insight computes the correct expiration
      and appends to both JSON and compiled Markdown.
      """
      with tempfile.TemporaryDirectory() as tmpdir:
          md_file = os.path.join(tmpdir, "active_memory.md")
          json_file = os.path.join(tmpdir, "active_memory.json")

          ref_date = datetime.date(2026, 6, 11)
          manager = MemoryManager(file_path=md_file, json_path=json_file, reference_date=ref_date)

          # Append entry
          manager.append_insight(
              insight="ECB keeps policy rates unchanged; signals cuts in Autumn.",
              category="Monetary Policy",
              date_str="2026-06-11"
          )

          # Load JSON directly to check contents
          with open(json_file, "r") as f:
              data = json.load(f)
          
          assert len(data) == 1
          entry = data[0]
          assert entry["insight"] == "ECB keeps policy rates unchanged; signals cuts in Autumn."
          assert entry["category"] == "Monetary Policy"
          assert entry["date"] == "2026-06-11"
          assert entry["expires_at"] == "2026-09-09"
          assert entry["status"] == "active"

          # Check compiled markdown file
          with open(md_file, "r") as f:
              md_content = f.read()

          assert "ECB keeps policy rates unchanged; signals cuts in Autumn." in md_content
          assert "2026-06-11" in md_content

  def test_consolidation():
      """
      Verify that consolidation correctly moves outdated events to archived status
      and removes them from the compiled Markdown file.
      """
      with tempfile.TemporaryDirectory() as tmpdir:
          md_file = os.path.join(tmpdir, "active_memory.md")
          json_file = os.path.join(tmpdir, "active_memory.json")

          ref_date = datetime.date(2026, 6, 11)
          manager = MemoryManager(file_path=md_file, json_path=json_file, reference_date=ref_date)

          # Add an active entry (within 90 days)
          manager.append_insight("Active monetary trend", "Monetary Policy", "2026-06-01")
          # Add an outdated entry (older than 90 days)
          manager.append_insight("Old energy price shock", "Energy", "2026-02-01")

          # Verify active vs archived status
          with open(json_file, "r") as f:
              data = json.load(f)
          
          # We prepended, so "Old energy price shock" is entry 1
          assert data[0]["insight"] == "Active monetary trend"
          assert data[0]["status"] == "active"
          
          assert data[1]["insight"] == "Old energy price shock"
          assert data[1]["status"] == "archived"

          # Verify compiled markdown contains ONLY the active one
          with open(md_file, "r") as f:
              md_content = f.read()

          assert "Active monetary trend" in md_content
          assert "Old energy price shock" not in md_content
  ```

- [ ] **Step 2: Run pytest to verify the new tests fail (since implementation is not done)**
  Run: `pytest agent/skills/buffett_analyst/scripts/test_manage_memory.py -v`
  Expected: FAIL (either ModuleNotFoundError or import/assertion failures)

- [ ] **Step 3: Commit the test file**
  Run:
  ```bash
  git add agent/skills/buffett_analyst/scripts/test_manage_memory.py
  git commit -m "test: add tests for memory manager upgrade"
  ```

---

### Task 2: Implement Upgraded MemoryManager & Auto-Consolidation

**Files:**
- Modify: `agent/skills/buffett_analyst/scripts/manage_memory.py`

- [ ] **Step 1: Replace implementation in `manage_memory.py` with structured JSON support, auto-bootstrapping, categorization logic, and Markdown compilation.**
  Modify the `MemoryManager` implementation in `agent/skills/buffett_analyst/scripts/manage_memory.py` to:
  1. Initialize with both `file_path` (defaults to `.md`) and `json_path` (defaults to `.json` in the same directory).
  2. Implement `_load_memory()` to try loading `json_path` first. If missing, look for `file_path`, parse the markdown entries using regex to bootstrap the JSON data, and write the JSON database.
  3. Implement automatic keyword classification during bootstrap (using keywords for `Monetary Policy`, `Energy`, `Geopolitics`, `Regional`).
  4. Auto-compute `expires_at = date + 90 days`.
  5. Implement `prune_memory()` to mark entries with `expires_at < reference_date` (current date) as `archived`.
  6. Implement `save_memory()` to write all entries to `json_path` and write only the `active` entries to `file_path` in markdown formatting (with standard header).
  7. Handle CLI execution gracefully by mapping arguments to `append_insight` (with default category "Monetary Policy").

  Complete code for `manage_memory.py`:
  ```python
  #!/usr/bin/env python3
  """
  Task 4: Macro Synthesis & Active Memory
  Manages the long-term context for the Buffett Strategic Analyst skill.
  Handles structured JSON storage, auto-consolidation (archiving > 90 days),
  and markdown compilation to prevent context bloat.
  """

  import os
  import datetime
  import json
  import re
  import sys
  import logging
  from typing import List, Dict, Any

  logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s - %(levelname)s - %(message)s',
      handlers=[logging.StreamHandler(sys.stdout)]
  )
  logger = logging.getLogger(__name__)

  MEMORY_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../knowledge_base/active_memory.md"))
  JSON_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../knowledge_base/active_memory.json"))
  DEFAULT_RETENTION_DAYS = 90

  class MemoryManager:
      def __init__(self, file_path: str = MEMORY_FILE_PATH, json_path: str = JSON_FILE_PATH, reference_date: datetime.date = None):
          self.file_path = file_path
          self.json_path = json_path
          self.reference_date = reference_date or datetime.date.today()
          self.entries: List[Dict[str, Any]] = []
          self.header = "# Active Memory - Macro Trends & Strategic Insights\n\nThis file maintains continuity across daily research reports. It tracks global macro shifts, regional geopolitical events, and investment-relevant narratives.\n\n## Macro Narrative Log\n"
          self._load_memory()

      def _load_memory(self):
          """Loads memory from JSON. If JSON is missing, bootstraps it from the Markdown file."""
          if os.path.exists(self.json_path):
              try:
                  with open(self.json_path, 'r', encoding='utf-8') as f:
                      self.entries = json.load(f)
                  logger.info(f"Loaded {len(self.entries)} entries from JSON database.")
                  # Run consolidation to update statuses based on reference_date
                  self.prune_memory()
                  return
              except Exception as e:
                  logger.error(f"Failed to load JSON memory database: {e}")

          # Bootstrap from Markdown file if JSON doesn't exist
          if os.path.exists(self.file_path):
              logger.info(f"JSON database not found. Bootstrapping from {self.file_path}...")
              self._bootstrap_from_markdown()
              self.prune_memory()
              self.save_memory()
          else:
              logger.info("No memory files found. Initializing empty database.")
              self.entries = []

      def _classify_insight(self, insight: str) -> str:
          """Classifies a raw insight into one of the 4 defined categories."""
          insight_lower = insight.lower()
          
          # Keyword rules
          monetary_keywords = ["fed", "federal reserve", "interest rate", "rate cut", "cpi", "inflation", "ecb", "yield", "pce"]
          energy_keywords = ["energy", "oil", "brent", "gas", "commodity", "commodities", "crude"]
          geopolitical_keywords = ["geopolitical", "geopolitics", "war", "conflict", "election", "sanction", "instability", "military"]
          regional_keywords = ["china", "japan", "us", "eu", "europe", "yen", "stimulus", "eurozone", "tariff", "trade"]

          if any(k in insight_lower for k in monetary_keywords):
              return "Monetary Policy"
          if any(k in insight_lower for k in energy_keywords):
              return "Energy"
          if any(k in insight_lower for k in geopolitical_keywords):
              return "Geopolitics"
          if any(k in insight_lower for k in regional_keywords):
              return "Regional"
          
          return "Monetary Policy" # Default fallback

      def _bootstrap_from_markdown(self):
          """Parses the existing Markdown file and converts entries to structured JSON."""
          try:
              with open(self.file_path, 'r', encoding='utf-8') as f:
                  content = f.read()

              # Find all entries matching "- **YYYY-MM-DD**: Insight"
              pattern = r'-\s*\*\*(\d{4}-\d{2}-\d{2})\*\*:\s*(.*)'
              matches = re.findall(pattern, content)

              for date_str, insight in matches:
                  insight_clean = insight.strip()
                  category = self._classify_insight(insight_clean)
                  
                  # Parse date to compute expiration
                  log_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                  expires_at = log_date + datetime.timedelta(days=DEFAULT_RETENTION_DAYS)
                  
                  status = "active" if expires_at >= self.reference_date else "archived"

                  self.entries.append({
                      "date": date_str,
                      "category": category,
                      "insight": insight_clean,
                      "status": status,
                      "expires_at": expires_at.strftime("%Y-%m-%d")
                  })
              
              logger.info(f"Successfully bootstrapped {len(self.entries)} entries from markdown.")
          except Exception as e:
              logger.error(f"Error bootstrapping from markdown: {e}")

      def append_insight(self, insight: str, category: str = None, date_str: str = None):
          """Appends a new insight to the database."""
          if not date_str:
              date_str = self.reference_date.strftime("%Y-%m-%d")
          if not category:
              category = self._classify_insight(insight)

          log_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
          expires_at = log_date + datetime.timedelta(days=DEFAULT_RETENTION_DAYS)
          status = "active" if expires_at >= self.reference_date else "archived"

          new_entry = {
              "date": date_str,
              "category": category,
              "insight": insight.strip(),
              "status": status,
              "expires_at": expires_at.strftime("%Y-%m-%d")
          }
          
          # Prepend to keep newest entries first
          self.entries.insert(0, new_entry)
          logger.info(f"Appended new insight: [{category}] {insight[:40]}...")

      def prune_memory(self):
          """Consolidates entries by updating status to archived if past their expiration date."""
          updated_count = 0
          for entry in self.entries:
              expires_at = datetime.datetime.strptime(entry["expires_at"], "%Y-%m-%d").date()
              if expires_at < self.reference_date and entry["status"] == "active":
                  entry["status"] = "archived"
                  updated_count += 1
          if updated_count > 0:
              logger.info(f"Archived {updated_count} expired entries during consolidation.")

      def save_memory(self):
          """Saves all entries to JSON and updates the Markdown file with only active entries."""
          try:
              # 1. Save JSON database
              os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
              with open(self.json_path, 'w', encoding='utf-8') as f:
                  json.dump(self.entries, f, indent=2)
              logger.info(f"Saved JSON database to {self.json_path}")

              # 2. Compile active entries to Markdown
              active_lines = []
              for entry in self.entries:
                  if entry["status"] == "active":
                      active_lines.append(f"- **{entry['date']}**: {entry['insight']}")

              os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
              with open(self.file_path, 'w', encoding='utf-8') as f:
                  f.write(self.header)
                  if active_lines:
                      f.write("\n")
                      f.write("\n".join(active_lines))
                      f.write("\n")
              logger.info(f"Compiled and saved active memory Markdown to {self.file_path}")
          except Exception as e:
              logger.error(f"Failed to save memory: {e}")
              raise

  def main():
      if len(sys.argv) > 1:
          insight = " ".join(sys.argv[1:])
          manager = MemoryManager()
          manager.append_insight(insight)
          manager.prune_memory()
          manager.save_memory()
      else:
          manager = MemoryManager()
          manager.prune_memory()
          manager.save_memory()

  if __name__ == "__main__":
      main()
  ```

- [ ] **Step 2: Run the test suite and verify they pass**
  Run: `pytest agent/skills/buffett_analyst/scripts/test_manage_memory.py -v`
  Expected: PASS

- [ ] **Step 3: Commit the changes**
  Run:
  ```bash
  git add agent/skills/buffett_analyst/scripts/manage_memory.py
  git commit -m "feat: upgrade memory manager to structured JSON with 90-day auto-consolidation"
  ```
