# Design Spec: Accurate Valuation and Expanded Bargains Scanner

This design document outlines the updates to improve the accuracy of stock valuations (addressing the HPQ overvaluation bug and cash-rich ROIC calculation anomalies) and to expand the bargain hunting capability from a fixated portfolio/15-stock list to a hybrid curated + dynamic scanner.

---

## 1. Objectives

- **Fix Declining FCF Valuations (HPQ Bug)**: Classify stocks with a negative Free Cash Flow (FCF) compound annual growth rate (CAGR) as "Too Hard" to value via DCF, matching Warren Buffett's philosophy of avoiding declining or unpredictable earnings.
- **Fix Cash-Rich ROIC Anomaly**: Prevent cash-rich companies from outputting `0%` ROIC due to negative net invested capital (i.e. cash > equity + debt) by falling back to a positive invested capital floor.
- **Resolve Advice Inconsistencies**: Eliminate arbitrary valuation escape hatches in the portfolio advice engine. A stock should only be a `BUY` if the current price is strictly below the conservative intrinsic value (fair price).
- **Expand Bargain Scanner**: Transition the scanner from a static 15-stock list to a hybrid scanner using an expanded curated base list of 50+ global stocks and dynamic agent-driven web search candidates.

---

## 2. Detailed Technical Changes

### 2.1. Centralized Valuation Upgrades (`data_fetcher.py`)

We will update [data_fetcher.py](file:///Users/joaosantos/stock-tracker/agent/skills/buffett_analyst/scripts/data_fetcher.py) as follows:

1. **`StockData` Dataclass**:
   - Add `expected_growth_rate: float = 0.0` to the class fields.

2. **Negative growth check in `fetch_data()`**:
   - Calculate FCF CAGR over the historical period.
   - If the calculated CAGR is negative (i.e. `hist[-1] < hist[0]`), set:
     - `is_too_hard = True`
     - `error_message = "Declining FCF growth: Too Hard to value reliably using DCF"`
     - Return the stock data immediately without running a positive growth projection.

3. **Cash-Rich ROIC Fallback**:
   - Update `invested_capital` logic to check if `equity + debt - cash <= 0`.
   - If it is non-positive, set `invested_capital = max(equity + debt, 1.0)`.
   - Calculate `roic = nopat / invested_capital` using the adjusted capital base.

4. **Storing Expected Growth**:
   - Populate `expected_growth_rate` with the growth rate used for Standard DCF or Reverse DCF calculations.

---

### 2.2. Portfolio Advice & Audit Upgrades (`evaluate_portfolio.py` & `evaluate_stock.py`)

We will update the evaluation CLI and recommendation logic:

1. **Valuation Checks in `evaluate_portfolio.py`**:
   - In `PortfolioEvaluator.evaluate()`, change `valuation_ok` to check only whether `current_price < fair_price`.
   - Remove the escape hatches `or implied_growth_rate < 0.25` and `or fcf_yield > 0.05`.

2. **Expected Growth Audit in `evaluate_stock.py`**:
   - Update the print outputs to display the `Expected Growth Rate` as a percentage (e.g. `8.0%`).

---

### 2.3. Scanner Expansion (`filter_stocks.py` & `run_daily_research.sh`)

We will expand candidate acquisition:

1. **CLI Arguments in `filter_stocks.py`**:
   - Modify the script's entry point to parse command-line arguments.
   - If tickers are specified as positional arguments (e.g. `python3 filter_stocks.py TICKER1 TICKER2`), it will scan only those tickers.
   - If no arguments are specified, it will fall back to the curated base list.

2. **Expanded Curated Tickers**:
   - Replace the 15 tech-heavy curated list in `filter_stocks.py` with an expanded base list of 50+ high-quality global companies.
   - Candidate tickers: `AAPL`, `MSFT`, `GOOGL`, `AMZN`, `KO`, `PEP`, `PG`, `JNJ`, `COST`, `MCD`, `NKE`, `V`, `MA`, `ADBE`, `CRM`, `ACN`, `ASML`, `UNH`, `WMT`, `ORCL`, `CSCO`, `BRK-B`, `DIS`, `HD`, `SBUX`, `NSRGY`, `LVMUY`, `ABT`, `MRK`, `PFE`, `LLY`, `JPM`, `BAC`, `AXP`, `CAT`, `HON`, `TXN`, `QCOM`, `INTC`, `DE`, `UPS`, `FDX`, `WM`, `EL`, `TGT`.

3. **Dynamic Agent-Driven Search in `run_daily_research.sh`**:
   - Modify the `agy` command's prompt instructions:
     - Instruct the agent to run web searches to find 5-10 additional bargain candidates (e.g., stocks hitting 52-week lows, undervalued high-ROIC compounders, sector opportunities).
     - Merge these dynamically identified tickers with the baseline curated list and the portfolio tickers, and pass them to `filter_stocks.py` via CLI arguments.

---

## 3. Verification & Testing

1. **Unit Tests**:
   - Run the test suite (`test_real_fetcher.py`, `test_mocked_fetcher.py`) to confirm no regressions.
   - Add a test case for a mocked declining FCF stock and verify it gets flagged as `is_too_hard`.
   - Add a test case for a cash-rich company with negative invested capital and verify its ROIC is computed correctly using the fallback.
2. **End-to-End Test**:
   - Run `python evaluate_stock.py HPQ` and verify it is classified as `Too Hard` (and not valued at an arbitrary positive growth rate).
   - Run `python filter_stocks.py KO AAPL` to verify CLI argument parsing.
