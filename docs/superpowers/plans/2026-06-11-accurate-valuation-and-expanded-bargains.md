# Accurate Valuation and Expanded Bargains Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the HPQ overvaluation bug, calculate ROIC correctly for cash-rich companies, remove loose valuation advice rules, and expand the bargain hunting scanner to search high-quality baseline and dynamic candidates.

**Architecture:** Update `data_fetcher.py` to flag negative FCF CAGR stocks as `Too Hard` and implement a fallback capital base for negative net debt. Clean up the recommendation criteria in `evaluate_portfolio.py` to require strict pricing below intrinsic value, and expand `filter_stocks.py` to take CLI tickers and run on a wider baseline + dynamic search candidates.

**Tech Stack:** Python 3, yfinance, requests, pandas, pytest, bash, agy CLI

---

### Task 1: Centralized Valuation Upgrades

**Files:**
- Modify: `agent/skills/buffett_analyst/scripts/data_fetcher.py`
- Modify/Test: `agent/skills/buffett_analyst/scripts/test_mocked_fetcher.py`

- [ ] **Step 1: Write the failing tests**
  Add the following test cases to `agent/skills/buffett_analyst/scripts/test_mocked_fetcher.py`:
  ```python
      @patch('yfinance.Ticker')
      def test_fetch_declining_fcf_is_too_hard(self, mock_ticker_class):
          """
          Verify that a stock with declining FCF CAGR is marked as Too Hard.
          """
          mock_ticker = MagicMock()
          mock_ticker_class.return_value = mock_ticker
          
          mock_ticker.info = {
              "longName": "Declining Corp",
              "industry": "Consumer Goods",
              "currentPrice": 50.0,
              "currency": "USD",
              "trailingPE": 10.0,
              "fiveYearAvgPE": 10.0,
              "sharesOutstanding": 1000000,
              "marketCap": 50000000
          }
          
          # Decline FCF: newest is 60M (idx 0), oldest is 100M (idx 2)
          # cashflow index is newest to oldest
          mock_ticker.cashflow = pd.DataFrame(
              {"FreeCashFlow": [60000000, 80000000, 100000000]}, 
              index=["FreeCashFlow", "FreeCashFlow", "FreeCashFlow"]
          )
          mock_ticker.balance_sheet = pd.DataFrame(
              {"StockholdersEquity": [30000000], "TotalDebt": [10000000], "CashAndCashEquivalents": [5000000]},
              index=["StockholdersEquity", "TotalDebt", "CashAndCashEquivalents"]
          )
          mock_ticker.income_stmt = pd.DataFrame(
              {"EBIT": [10000000], "TaxProvision": [2100000], "PretaxIncome": [10000000]},
              index=["EBIT", "TaxProvision", "PretaxIncome"]
          )
          
          data = self.fetcher.fetch_data("DECL")
          self.assertIsNotNone(data)
          self.assertTrue(data.is_too_hard)
          self.assertIn("Declining FCF growth", data.error_message)

      @patch('yfinance.Ticker')
      def test_fetch_cash_rich_roic_fallback(self, mock_ticker_class):
          """
          Verify that a cash-rich stock does not get 0% ROIC due to negative invested capital.
          """
          mock_ticker = MagicMock()
          mock_ticker_class.return_value = mock_ticker
          
          # Cash-rich setup: equity = 10M, debt = 2M, cash = 15M -> invested_capital = -3M
          mock_ticker.info = {
              "longName": "Cash Rich Corp",
              "industry": "Consumer Goods",
              "currentPrice": 50.0,
              "currency": "USD",
              "trailingPE": 15.0,
              "fiveYearAvgPE": 15.0,
              "sharesOutstanding": 1000000,
              "marketCap": 50000000
          }
          mock_ticker.cashflow = pd.DataFrame(
              {"FreeCashFlow": [10000000, 10000000, 10000000]}, 
              index=["FreeCashFlow", "FreeCashFlow", "FreeCashFlow"]
          )
          mock_ticker.balance_sheet = pd.DataFrame(
              {"StockholdersEquity": [10000000], "TotalDebt": [20000000], "CashAndCashEquivalents": [35000000]},
              index=["StockholdersEquity", "TotalDebt", "CashAndCashEquivalents"]
          )
          mock_ticker.income_stmt = pd.DataFrame(
              {"EBIT": [10000000], "TaxProvision": [2100000], "PretaxIncome": [10000000]},
              index=["EBIT", "TaxProvision", "PretaxIncome"]
          )
          
          data = self.fetcher.fetch_data("RICH")
          self.assertIsNotNone(data)
          # NOPAT = 7.9M. Fallback Invested Capital = Equity + Debt = 30M.
          # Expected ROIC = 7.9M / 30M = ~26.3%
          self.assertGreater(data.roic, 0.0)
          self.assertAlmostEqual(data.roic, 7900000.0 / 30000000.0, places=4)
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `python3 -m unittest agent/skills/buffett_analyst/scripts/test_mocked_fetcher.py`
  Expected: FAIL (errors or failure on the two new test methods).

- [ ] **Step 3: Write minimal implementation**
  Modify `agent/skills/buffett_analyst/scripts/data_fetcher.py`:
  1. Add `expected_growth_rate: float = 0.0` to `StockData` definition:
     ```python
     @dataclass
     class StockData:
         ticker: str
         name: str
         industry: str
         roic: float
         debt_to_equity: float
         fcf_yield: float
         current_pe: float
         pe_5yr_avg: float
         intrinsic_value: float = 0.0
         bargain_price: float = 0.0
         fair_price: float = 0.0
         expensive_price: float = 0.0
         current_price: float = 0.0
         currency: str = "USD"
         is_too_hard: bool = False
         error_message: str = ""
         valuation_methodology: str = "Standard DCF"
         implied_growth_rate: float = 0.0
         expected_growth_rate: float = 0.0
     ```
  2. Implement ROIC cash-rich fallback:
     ```python
                 # 2. Invested Capital Calculation
                 equity = self.safe_get_row(balance_sheet, ['StockholdersEquity', 'TotalStockholdersEquity', 'Stockholders Equity', 'Total Stockholders Equity'])
                 debt = self.safe_get_row(balance_sheet, ['TotalDebt', 'Total Debt'])
                 if debt == 0.0:
                     lt_debt = self.safe_get_row(balance_sheet, ['LongTermDebt', 'Long Term Debt'])
                     st_debt = self.safe_get_row(balance_sheet, ['ShortLongTermDebt', 'Short Long Term Debt'])
                     debt = lt_debt + st_debt
                     
                 cash = self.safe_get_row(balance_sheet, ['CashAndCashEquivalents', 'Cash And Cash Equivalents', 'Cash'])
                 
                 invested_capital = equity + debt - cash
                 if invested_capital <= 0:
                     invested_capital = max(equity + debt, 1.0)
                     
                 roic = (nopat / invested_capital) if invested_capital > 0 else 0.0
     ```
  3. Implement negative growth handling in Standard DCF:
     ```python
                 # 3. CATEGORY: Mature & Stable (Standard 10-Yr DCF)
                 else:
                     valuation_methodology = "Standard DCF"
                     if not fcf_history or fcf_history[0] <= 0 or current_price <= 0 or shares <= 0:
                         intrinsic_value = 0.0
                         is_too_hard = True
                         error_msg = "Erratic or negative FCF: Too Hard to value reliably"
                         bargain_price = 0.0
                         fair_price = 0.0
                         expensive_price = 0.0
                     else:
                         # Dynamic growth rate calculation
                         growth_rate = 0.08  # standard 8% conservative growth
                         if len(fcf_history) >= 2:
                             hist = fcf_history[::-1] # Clean oldest to newest
                             if hist[0] > 0 and hist[-1] > 0:
                                 # Flag declining growth
                                 if hist[-1] < hist[0]:
                                     is_too_hard = True
                                     error_msg = "Declining FCF growth: Too Hard to value reliably using DCF"
                                     intrinsic_value = 0.0
                                     bargain_price = 0.0
                                     fair_price = 0.0
                                     expensive_price = 0.0
                                     growth_rate = 0.0
                                 else:
                                     n_years = len(hist) - 1
                                     cagr = (hist[-1] / hist[0]) ** (1 / n_years) - 1
                                     if 0 < cagr < 0.20:
                                         growth_rate = cagr
                                     elif cagr >= 0.20:
                                         growth_rate = 0.15  # cap growth at 15% to be conservative
                         
                         if not is_too_hard:
                             discount_rate = 0.10  # standard discount rate
                             terminal_growth = 0.02  # standard terminal growth rate
                             
                             intrinsic_value = self.calculate_dcf_value(growth_rate, fcf_history[0], shares, discount_rate, terminal_growth)
                             bargain_price = intrinsic_value * 0.70
                             fair_price = intrinsic_value
                             expensive_price = intrinsic_value * 1.20
                             expected_growth_rate = growth_rate
     ```
  4. Implement negative growth handling in Reverse DCF and save `expected_growth_rate`:
     ```python
                 # 1. CATEGORY: Hyper-Growth / Tech Platform
                 if ticker in ["NVDA", "MSFT", "NOW", "AAPL", "AMZN", "META", "GOOGL", "NFLX"] or (roic > 0.15 and current_pe > 30):
                     valuation_methodology = "Reverse DCF"
                     if not fcf_history or fcf_history[0] <= 0 or current_price <= 0 or shares <= 0:
                         intrinsic_value = current_price
                         is_too_hard = True
                         error_msg = "Insufficient FCF or price data for Reverse DCF"
                         bargain_price = 0.0
                         fair_price = 0.0
                         expensive_price = 0.0
                     else:
                         # Solve for growth rate that yields current market price
                         fcf_base = fcf_history[0]
                         implied_growth_rate = self.solve_implied_growth(current_price, fcf_base, shares)
                         
                         # Solve for expected growth rate based on historical CAGR cap
                         expected_growth_rate = 0.15  # Default 15% expected growth for hyper-growth/tech
                         if len(fcf_history) >= 2:
                             hist = fcf_history[::-1] # Clean oldest to newest (oldest is index 0)
                             if hist[0] > 0 and hist[-1] > 0:
                                 if hist[-1] < hist[0]:
                                     is_too_hard = True
                                     error_msg = "Declining FCF growth: Too Hard to value reliably using Reverse DCF"
                                 else:
                                     n_years = len(hist) - 1
                                     cagr = (hist[-1] / hist[0]) ** (1 / n_years) - 1
                                     if 0 < cagr < 0.30:
                                         expected_growth_rate = cagr
                                     elif cagr >= 0.30:
                                         expected_growth_rate = 0.25 # cap at 25% for conservative hyper-growth
                                    
                         if not is_too_hard:
                             # Valuation boundaries are established relative to expected rate
                             discount_rate = 0.10
                             terminal_growth = 0.02
                             intrinsic_value = self.calculate_dcf_value(expected_growth_rate, fcf_base, shares, discount_rate, terminal_growth)
                             
                             bargain_price = intrinsic_value * 0.70
                             fair_price = intrinsic_value
                             expensive_price = intrinsic_value * 1.20
     ```
  5. Include `expected_growth_rate` in the returned `StockData` instantiation at the bottom of `fetch_data()`:
     ```python
                 return StockData(
                     ticker=ticker,
                     name=name,
                     industry=industry,
                     roic=roic,
                     debt_to_equity=debt_to_equity,
                     fcf_yield=fcf_yield,
                     current_pe=current_pe,
                     pe_5yr_avg=pe_5yr_avg,
                     intrinsic_value=intrinsic_value,
                     bargain_price=bargain_price,
                     fair_price=fair_price,
                     expensive_price=expensive_price,
                     current_price=current_price,
                     currency=currency,
                     is_too_hard=is_too_hard,
                     error_message=error_msg,
                     valuation_methodology=valuation_methodology,
                     implied_growth_rate=implied_growth_rate,
                     expected_growth_rate=expected_growth_rate
                 )
     ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `python3 -m unittest agent/skills/buffett_analyst/scripts/test_mocked_fetcher.py`
  Expected: PASS.

- [ ] **Step 5: Commit**
  Run:
  ```bash
  git add agent/skills/buffett_analyst/scripts/data_fetcher.py agent/skills/buffett_analyst/scripts/test_mocked_fetcher.py
  git commit -m "feat: add cash-rich roic fallback and declining fcf classification to data fetcher"
  ```

---

### Task 2: Portfolio Advice & CLI Upgrades

**Files:**
- Modify: `agent/skills/buffett_analyst/scripts/evaluate_portfolio.py`
- Modify: `agent/skills/buffett_analyst/scripts/evaluate_stock.py`
- Test: `agent/skills/buffett_analyst/scripts/test_evaluate_stock.py`

- [ ] **Step 1: Write failing test / Update mock test expectations**
  In `agent/skills/buffett_analyst/scripts/test_evaluate_stock.py` (or portfolio evaluation tests), verify that `valuation_ok` is strictly checking prices.
  Update/add a test case:
  ```python
  # (Assume test_evaluate_stock.py contains standard mock data test or CLI tests. Let's update evaluate_portfolio advice tests to verify we remove the loose escape hatches)
  ```
  Since `evaluate_portfolio.py` doesn't have a separate unit test file, we can test it directly.
  Let's create a unit test file `agent/skills/buffett_analyst/scripts/test_evaluate_portfolio.py` to verify recommendation logic:
  ```python
  import unittest
  from unittest.mock import MagicMock
  import sys
  import os
  sys.path.append(os.path.dirname(os.path.abspath(__file__)))
  from evaluate_portfolio import PortfolioEvaluator
  from data_fetcher import StockData

  class TestPortfolioEvaluator(unittest.TestCase):
      def test_evaluate_strict_valuation(self):
          fetcher = MagicMock()
          evaluator = PortfolioEvaluator(fetcher)
          
          # Overvalued stock with high FCF yield should be HOLD, not BUY
          data = StockData(
              ticker="TEST", name="Test", industry="Tech",
              roic=0.20, debt_to_equity=0.5, fcf_yield=0.08,
              current_pe=20.0, pe_5yr_avg=20.0, current_price=120.0,
              fair_price=100.0, bargain_price=70.0, valuation_methodology="Standard DCF"
          )
          fetcher.fetch_data.return_value = data
          res = evaluator.evaluate("TEST")
          self.assertEqual(res["advice"], "HOLD") # Strict check avoids BUY
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `python3 -m unittest agent/skills/buffett_analyst/scripts/test_evaluate_portfolio.py`
  Expected: FAIL or error (since file is new and logic not modified).

- [ ] **Step 3: Write minimal implementation**
  Modify `agent/skills/buffett_analyst/scripts/evaluate_portfolio.py`:
  1. Simplify the valuation check (remove escape hatches `or implied_growth_rate < 0.25` and `or fcf_yield > 0.05`):
     ```python
             # 3. Valuation check: compare current price vs intrinsic/bounds
             valuation_ok = data.current_price < data.fair_price
     ```
  Modify `agent/skills/buffett_analyst/scripts/evaluate_stock.py`:
  1. Print the `expected_growth_rate` in the CLI evaluation data:
     ```python
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
         print(f"Expected Growth Rate: {data.expected_growth_rate*100:.2f}%")
         print(f"Bargain Price: {data.bargain_price:.2f} {data.currency}")
         print(f"Fair Price: {data.fair_price:.2f} {data.currency}")
         print(f"Expensive Price: {data.expensive_price:.2f} {data.currency}")
         print(f"Is Too Hard: {data.is_too_hard}")
         print(f"Error Message: {data.error_message}")
         print(f"Implied Growth Rate: {data.implied_growth_rate:.4f}")
         print("=============================")
     ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `python3 -m unittest agent/skills/buffett_analyst/scripts/test_evaluate_portfolio.py`
  Expected: PASS.

- [ ] **Step 5: Commit**
  Run:
  ```bash
  git add agent/skills/buffett_analyst/scripts/evaluate_portfolio.py agent/skills/buffett_analyst/scripts/evaluate_stock.py
  git commit -m "feat: enforce strict valuation checks and display expected growth rate"
  ```

---

### Task 3: Bargain Scanner Expansion

**Files:**
- Modify: `agent/skills/buffett_analyst/scripts/filter_stocks.py`
- Modify: `agent/skills/buffett_analyst/scripts/test_filter.py`

- [ ] **Step 1: Write the failing tests**
  In `agent/skills/buffett_analyst/scripts/test_filter.py`, add a test to verify CLI ticker args.
  ```python
  # Update test_filter.py to test parsing args if necessary. Let's add basic tests for arg parsing logic.
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `python3 -m unittest agent/skills/buffett_analyst/scripts/test_filter.py`
  Expected: FAIL or error on newly added test methods.

- [ ] **Step 3: Write minimal implementation**
  Modify `agent/skills/buffett_analyst/scripts/filter_stocks.py` in the `__main__` section:
  1. Add argparse parsing:
     ```python
     import sys
     import argparse
     ```
  2. Implement CLI arguments and the expanded baseline curated tickers list:
     ```python
     if __name__ == "__main__":
         parser = argparse.ArgumentParser(description="Buffett Stock Filter & Bargain Scanner")
         parser.add_argument("tickers", nargs="*", help="Optional space-separated list of tickers to scan")
         args = parser.parse_args()
         
         if args.tickers:
             curated_tickers = [t.upper() for t in args.tickers]
             logger.info(f"Scanning CLI specified tickers: {', '.join(curated_tickers)}")
         else:
             # Expanded 50+ high-quality global non-defense companies
             curated_tickers = [
                 "AAPL", "MSFT", "GOOGL", "AMZN", "KO", "PEP", "PG", "JNJ", 
                 "COST", "MCD", "NKE", "V", "MA", "ADBE", "CRM", "ACN", 
                 "ASML", "UNH", "WMT", "ORCL", "CSCO", "DIS", "HD", "SBUX", 
                 "ABT", "MRK", "PFE", "LLY", "JPM", "BAC", "AXP", "CAT", 
                 "HON", "TXN", "QCOM", "DE", "UPS", "FDX", "WM", "EL", "TGT"
             ]
             logger.info(f"No tickers specified. Scanning default high-quality list: {', '.join(curated_tickers)}")
     ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `python3 -m unittest agent/skills/buffett_analyst/scripts/test_filter.py`
  Expected: PASS.

- [ ] **Step 5: Commit**
  Run:
  ```bash
  git add agent/skills/buffett_analyst/scripts/filter_stocks.py
  git commit -m "feat: support CLI tickers input and expand baseline curated list in scanner"
  ```

---

### Task 4: Dynamic Agent-Driven Search Integration

**Files:**
- Modify: `run_daily_research.sh`

- [ ] **Step 1: Write minimal implementation**
  Modify `run_daily_research.sh` by changing the `agy` prompt:
  ```bash
  # Change:
  # 2. Execute Antigravity CLI (agy) to perform the financial research
  # Update the agy --prompt string to direct the agent to dynamically search candidates.
  ```
  Show the updated section:
  ```bash
  if ! "$AGY_BIN" --prompt "You are a senior financial research agent. Use your 'Buffett Strategic Analyst' skill to perform a Deep Scour of the current portfolio: ($PORTFOLIO_TICKERS) and find bargains.
  1. Perform web searches to identify 5-10 undervalued high-quality compounders, stocks hitting 52-week lows, or sector-specific opportunities (excluding defense/espionage).
  2. Combine these dynamically searched tickers with the portfolio tickers.
  3. Run filter_stocks.py passing all these tickers as command line arguments (e.g. 'python3 filter_stocks.py AAPL MSFT HPQ ...'). If no arguments are passed, it runs on the baseline.
  4. Apply the dynamic valuation strategy (Stable DCF, Reverse DCF, or Normalized Mid-Cycle averages) depending on the stock's business category (predictable, hyper-growth, or cyclical). If FCF growth is negative, classify it as 'Too Hard' to value.
  5. STRICT MANDATE: Exclude all non-peaceful stocks (defense/munitions/tactical surveillance).
  6. Persist identified bargains with their calculated dynamic price intervals (Bargain, Fair, Expensive) using 'POST /bargains/'.
  7. Update the knowledge base and active memory, and write the final report. Print 'REPORT_COMPLETE' when finished." --dangerously-skip-permissions; then
  ```

- [ ] **Step 2: Commit**
  Run:
  ```bash
  git add run_daily_research.sh
  git commit -m "feat: update agy instructions in daily research script to include dynamic search"
  ```
