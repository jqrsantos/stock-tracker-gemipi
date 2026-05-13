#!/usr/bin/env python3
"""
Task 4: Macro Synthesis & Active Memory
Manages the long-term context for the Buffett Strategic Analyst skill.
Handles appending new macro insights and pruning old data to prevent context bloat.
"""

import os
import datetime
import logging
import sys
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Constants
MEMORY_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../knowledge_base/active_memory.md"))
MAX_MEMORY_ENTRIES = 30

class MemoryManager:
    """
    Manages the active_memory.md file.
    """
    def __init__(self, file_path: str = MEMORY_FILE_PATH):
        self.file_path = file_path
        self.header = ""
        self.entries = []
        self._load_memory()

    def _load_memory(self):
        """
        Reads the memory file and separates the header from the entries.
        """
        if not os.path.exists(self.file_path):
            logger.warning(f"Memory file not found at {self.file_path}. Initializing new memory.")
            self.header = "# Active Memory - Macro Trends & Strategic Insights\n\nThis file maintains continuity across daily research reports.\n\n## Macro Narrative Log\n"
            self.entries = []
            return

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by the log header
            log_header_marker = "## Macro Narrative Log"
            if log_header_marker in content:
                parts = content.split(log_header_marker)
                self.header = parts[0] + log_header_marker + "\n"
                
                # Parse entries (assuming they start with "- **")
                log_content = parts[1].strip()
                if log_content:
                    # Split into lines and filter for entry-like lines
                    lines = log_content.split('\n')
                    self.entries = [line.strip() for line in lines if line.strip().startswith("- **")]
                else:
                    self.entries = []
            else:
                # If no marker, treat everything as header (not ideal but safe)
                self.header = content.strip() + "\n\n## Macro Narrative Log\n"
                self.entries = []
                
        except Exception as e:
            logger.error(f"Failed to load memory file: {e}")
            raise

    def append_insight(self, insight: str, date_str: str = None):
        """
        Adds a new macro insight to the memory.
        """
        if not date_str:
            date_str = datetime.date.today().strftime("%Y-%m-%d")
        
        new_entry = f"- **{date_str}**: {insight}"
        # Prepend to entries to keep them in reverse chronological order (newest first)
        self.entries.insert(0, new_entry)
        logger.info(f"Appended new insight for {date_str}")

    def prune_memory(self, max_entries: int = MAX_MEMORY_ENTRIES):
        """
        Keeps only the most recent N entries.
        """
        if len(self.entries) > max_entries:
            removed_count = len(self.entries) - max_entries
            self.entries = self.entries[:max_entries]
            logger.info(f"Pruned {removed_count} old entries. Keeping the {max_entries} most recent.")

    def save_memory(self):
        """
        Writes the header and entries back to the file.
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(self.header)
                f.write("\n")
                f.write("\n".join(self.entries))
                f.write("\n")
            
            logger.info(f"Saved memory to {self.file_path}")
        except Exception as e:
            logger.error(f"Failed to save memory file: {e}")
            raise

def main():
    """
    Example usage and CLI interface.
    """
    manager = MemoryManager()
    
    # If arguments are provided, use them to add a new insight
    if len(sys.argv) > 1:
        insight = " ".join(sys.argv[1:])
        manager.append_insight(insight)
        manager.prune_memory()
        manager.save_memory()
    else:
        # Default behavior: just prune and save (standard maintenance)
        print(f"Current entries: {len(manager.entries)}")
        manager.prune_memory()
        manager.save_memory()

if __name__ == "__main__":
    main()
