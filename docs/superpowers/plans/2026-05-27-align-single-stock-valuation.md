# Align Single Stock Valuation with 6 AM Daily Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a centralized CLI helper script `evaluate_stock.py` that utilizes `YFinanceFetcher` to perform single stock evaluations, and adjust the Telegram listener prompt to run this script to ensure valuation consistency between single stock searches and the 6 AM daily report.

**Architecture:** Create a new command-line script under the existing `agent/skills/buffett_analyst/scripts` directory and a corresponding unit test file. Modify `listener/main.py`'s prompt string to instruct the agent to run the new script, read its stdout, and use the exact calculated metrics.

**Tech Stack:** Python 3, yfinance, unittest, pytest.

---

### Task 1: Create the CLI Stock Evaluation Helper Script

**Files:**
- Create: [evaluate_stock.py](file:///Users/joaosantos/stock-tracker/agent/skills/buffett_analyst/scripts/evaluate_stock.py)

- [ ] **Step 1: Create evaluate_stock.py**
  Create the file `agent/skills/buffett_analyst/scripts/evaluate_stock.py` with the following implementation:

  ```python
  #!/usr/bin/env python3
  """
  CLI tool to evaluate a single stock using the Buffett Strategic Analyst's centralized valuation engine.
  """

  import sys
  import os

  # Adjust path to import data_fetcher
  sys.path.append(os.path.dirname(os.path.abspath(__file__)))
  from data_fetcher import YFinanceFetcher

  def main():
      if len(sys.argv) < 2:
          print("Error: Missing ticker symbol.", file=sys.stderr)
          print("Usage: python evaluate_stock.py <TICKER>", file=sys.stderr)
          sys.exit(1)
          
      ticker = sys.argv[1].strip().upper()
      
      fetcher = YFinanceFetcher()
      data = fetcher.fetch_data(ticker)
      
      if not data:
          print(f"Error: No data retrieved for ticker '{ticker}'.", file=sys.stderr)
          sys.exit(1)
          
      # Serialize data into structured text format easily consumed by the agent
      print("=== STOCK EVALUATION DATA ===")
      print(f"Ticker: {data.ticker}")
      print(f"Name: {data.name}")
      print(f"Industry: {data.industry}")
      print(f"Current Price: {data.current_price} {data.currency}")
      print(f"ROIC: {data.roic:.4f}")
      print(f"Debt to Equity: {data.debt_to_equity:.4f}")
      print(f"FCF Yield: {data.fcf_yield:.4f}")
      print(f"Current PE: {data.current_pe:.2f}")
      print(f"5-Year Avg PE: {data.pe_5yr_avg:.2f}")
      print(f"Valuation Methodology: {data.valuation_methodology}")
      print(f"Bargain Price: {data.bargain_price:.2f} {data.currency}")
      print(f"Fair Price: {data.fair_price:.2f} {data.currency}")
      print(f"Expensive Price: {data.expensive_price:.2f} {data.currency}")
      print(f"Is Too Hard: {data.is_too_hard}")
      print(f"Error Message: {data.error_message}")
      print(f"Implied Growth Rate: {data.implied_growth_rate:.4f}")
      print("=============================")

  if __name__ == "__main__":
      main()
  ```

- [ ] **Step 2: Make the script executable**
  Run: `chmod +x agent/skills/buffett_analyst/scripts/evaluate_stock.py`

- [ ] **Step 3: Manually test the script on a valid ticker**
  Run: `.venv/bin/python agent/skills/buffett_analyst/scripts/evaluate_stock.py AAPL`
  Expected Output: A structured evaluation printed to console containing AAPL's metrics and dynamic price intervals using the Standard DCF methodology.

---

### Task 2: Create Unit Tests for `evaluate_stock.py`

**Files:**
- Create: [test_evaluate_stock.py](file:///Users/joaosantos/stock-tracker/agent/skills/buffett_analyst/scripts/test_evaluate_stock.py)

- [ ] **Step 1: Write the test suite**
  Create the unit test file `agent/skills/buffett_analyst/scripts/test_evaluate_stock.py` with the following implementation:

  ```python
  #!/usr/bin/env python3
  """
  Unit tests for evaluate_stock.py
  """

  import unittest
  from unittest.mock import MagicMock, patch
  import io
  import sys
  import os

  sys.path.append(os.path.dirname(os.path.abspath(__file__)))
  from evaluate_stock import main as evaluate_stock_main

  class TestEvaluateStock(unittest.TestCase):
      @patch('sys.argv', ['evaluate_stock.py'])
      def test_missing_arguments(self):
          """Verify that the script exits with error code when no ticker is passed."""
          with self.assertRaises(SystemExit) as cm, patch('sys.stderr', new=io.StringIO()) as mock_stderr:
              evaluate_stock_main()
          self.assertEqual(cm.exception.code, 1)
          self.assertIn("Error: Missing ticker symbol.", mock_stderr.getvalue())

      @patch('sys.argv', ['evaluate_stock.py', 'AAPL'])
      @patch('data_fetcher.YFinanceFetcher.fetch_data')
      def test_successful_evaluation(self, mock_fetch):
          """Verify that a successful evaluation prints the correct data."""
          mock_data = MagicMock()
          mock_data.ticker = "AAPL"
          mock_data.name = "Apple Inc."
          mock_data.industry = "Consumer Electronics"
          mock_data.current_price = 150.0
          mock_data.currency = "USD"
          mock_data.roic = 0.25
          mock_data.debt_to_equity = 0.5
          mock_data.fcf_yield = 0.06
          mock_data.current_pe = 25.0
          mock_data.pe_5yr_avg = 22.0
          mock_data.valuation_methodology = "Standard DCF"
          mock_data.bargain_price = 105.0
          mock_data.fair_price = 150.0
          mock_data.expensive_price = 180.0
          mock_data.is_too_hard = False
          mock_data.error_message = ""
          mock_data.implied_growth_rate = 0.0
          
          mock_fetch.return_value = mock_data
          
          with patch('sys.stdout', new=io.StringIO()) as mock_stdout:
              evaluate_stock_main()
              
          output = mock_stdout.getvalue()
          self.assertIn("=== STOCK EVALUATION DATA ===", output)
          self.assertIn("Ticker: AAPL", output)
          self.assertIn("Name: Apple Inc.", output)
          self.assertIn("ROIC: 0.2500", output)
          self.assertIn("Valuation Methodology: Standard DCF", output)
          self.assertIn("Bargain Price: 105.00 USD", output)
          self.assertIn("Is Too Hard: False", output)
  ```

- [ ] **Step 2: Run pytest to verify all tests pass**
  Run: `.venv/bin/pytest agent/skills/buffett_analyst/scripts/ -v`
  Expected Output: All tests, including the new `test_evaluate_stock.py` suite, pass successfully.

- [ ] **Step 3: Commit Task 1 and Task 2 changes**
  Run:
  ```bash
  git add agent/skills/buffett_analyst/scripts/evaluate_stock.py agent/skills/buffett_analyst/scripts/test_evaluate_stock.py
  git commit -m "feat: add evaluate_stock.py script and its unit tests"
  ```

---

### Task 3: Modify the Antigravity Prompt inside `listener/main.py`

**Files:**
- Modify: [main.py](file:///Users/joaosantos/stock-tracker/listener/main.py#L78-L106)

- [ ] **Step 1: Apply replacement in main.py**
  Replace lines 78 to 106 in `listener/main.py` with the following clean instructions:

  ```python
      prompt = (
          f"You are the 'Buffett Strategic Analyst'. Investigate '{ticker}' using value investing principles.\n\n"
          f"**Context:**\n"
          f"- {holdings_context}\n"
          f"- **Active Memory (Macro):**\n{active_memory}\n\n"
          f"**Instructions:**\n"
          f"1. Run the python script 'agent/skills/buffett_analyst/scripts/evaluate_stock.py' for '{ticker}' to fetch its real-time financials and dynamic valuation metrics. DO NOT use superficial web searches or perform custom manual DCF calculations.\n"
          f"2. Read the console output of the script to extract the exact calculated values:\n"
          f"   - ROIC, Debt to Equity, and FCF Yield.\n"
          f"   - Valuation Methodology (e.g., Standard DCF, Reverse DCF, or Mid-Cycle Normalized).\n"
          f"   - Intrinsic Value / Fair Price, Bargain Price, and Expensive Price.\n"
          f"   - If 'Is Too Hard' is True, classify the stock as 'Too Hard' to value and return an AVOID/HOLD with the script's warning message.\n"
          f"3. Apply the 'Buffett Check' using the script's exact metrics. Note that ROIC > 15% and Debt/Equity < 1.0 are the standards, but follow the script's advice if it overrides them based on stock categorization (e.g. cyclical/hyper-growth exceptions).\n"
          f"4. **STRICT MANDATE:** Verify if the company is 'Peaceful'.\n"
          f"   - STRICTLY EXCLUDE: Companies that directly manufacture weapon systems, munitions, firearms, tactical hardware, military explosives, nuclear weapons, or warships (e.g., Lockheed Martin, Raytheon, Northrop Grumman), AND companies producing specialized software or systems designed specifically for intelligence, espionage, surveillance, warfare, and tactical combat operations (e.g., Palantir).\n"
          f"   - EXPLICITLY ALLOW: Companies producing general-purpose or dual-use technologies (e.g., standard consumer electronics, microchips, GPUs, enterprise software, general search/cloud infrastructure, commercial aviation) even if they have partnerships, research relationships, or general contracts with defense departments (e.g., NVIDIA, Microsoft, Google), unless their direct products are weapons or dedicated combat/espionage systems. If the stock is NOT peaceful according to these exact guidelines, your Action must be 'SELL' or 'AVOID' with a clear warning.\n"
          f"5. Do NOT run any external notification scripts (like notifier.py). Your response will be handled by the caller.\n"
          f"6. Format your response exactly like this:\n\n"
          f"--- TELEGRAM SUMMARY ---\n"
          f"**Target Stock:** {ticker} - $PRICE\n"
          f"**Action:** BUY/HOLD/SELL/AVOID\n"
          f"**Buffett Lens:** 1-2 sentences on quality, moat, and ROIC.\n"
          f"**Rationale:** 1 sentence on current valuation/timing.\n"
          f"========================\n"
          f"**Portfolio Fit:** How this stock complements or conflicts with existing holdings ({holdings_context}).\n"
          f"**Macro Alignment:** How this fits with the trends in Active Memory.\n\n"
          f"--- FULL REPORT ---\n"
          f"[Your deep dive analysis here, including fundamental metrics and 'Peaceful' status check]"
      )
  ```

- [ ] **Step 2: Commit Prompt changes**
  Run:
  ```bash
  git add listener/main.py
  git commit -m "feat: align single stock investigation prompt with centralized evaluate_stock script"
  ```
