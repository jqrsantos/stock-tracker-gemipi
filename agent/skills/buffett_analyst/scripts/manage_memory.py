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
            if self._bootstrap_from_markdown():
                self.prune_memory()
                self.save_memory()
            else:
                logger.error("Bootstrap failed. Aborting initialization to prevent data loss.")
                self.entries = []
        else:
            logger.info("No memory files found. Initializing empty database.")
            self.entries = []

    def _classify_insight(self, insight: str) -> str:
        """Classifies a raw insight into one of the 4 defined categories using regex word boundaries."""
        insight_lower = insight.lower()
        
        # Keyword rules
        monetary_keywords = ["fed", "federal reserve", "interest rate", "rate cut", "cpi", "inflation", "ecb", "yield", "pce"]
        energy_keywords = ["energy", "oil", "brent", "gas", "commodity", "commodities", "crude"]
        geopolitical_keywords = ["geopolitical", "geopolitics", "war", "conflict", "election", "sanction", "instability", "military"]
        regional_keywords = ["china", "japan", "us", "eu", "europe", "yen", "stimulus", "eurozone", "tariff", "trade"]

        def matches_any(keywords: List[str]) -> bool:
            for k in keywords:
                pattern = r'\b' + re.escape(k) + r'\b'
                if re.search(pattern, insight_lower):
                    return True
            return False

        if matches_any(monetary_keywords):
            return "Monetary Policy"
        if matches_any(energy_keywords):
            return "Energy"
        if matches_any(geopolitical_keywords):
            return "Geopolitics"
        if matches_any(regional_keywords):
            return "Regional"
        
        return "Monetary Policy" # Default fallback

    def _bootstrap_from_markdown(self) -> bool:
        """Parses the existing Markdown file and converts entries to structured JSON. Returns True on success, False on failure."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find all entries matching "- **YYYY-MM-DD**: Insight"
            pattern = r'-\s*\*\*(\d{4}-\d{2}-\d{2})\*\*:\s*(.*)'
            matches = re.findall(pattern, content)

            temp_entries = []
            for date_str, insight in matches:
                insight_clean = insight.strip()
                category = self._classify_insight(insight_clean)
                
                # Parse date to compute expiration
                log_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                expires_at = log_date + datetime.timedelta(days=DEFAULT_RETENTION_DAYS)
                
                status = "active" if expires_at >= self.reference_date else "archived"

                temp_entries.append({
                    "date": date_str,
                    "category": category,
                    "insight": insight_clean,
                    "status": status,
                    "expires_at": expires_at.strftime("%Y-%m-%d")
                })
            
            self.entries = temp_entries
            logger.info(f"Successfully bootstrapped {len(self.entries)} entries from markdown.")
            return True
        except Exception as e:
            logger.error(f"Error bootstrapping from markdown: {e}")
            return False

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
        
        # Automatically save memory at the end of append_insight so that tests pass.
        self.save_memory()

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
            # Sort by date descending to keep newest entries first
            self.entries.sort(key=lambda x: x["date"], reverse=True)

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
