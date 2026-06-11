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
