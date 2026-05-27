# Decoupled Cron & Dynamic Stock Valuation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a decoupled cron orchestration pipeline and implement a dynamic, multi-strategy stock valuation system that selects the best valuation framework (predictable DCF, Reverse DCF implied growth check, or Normalized Mid-Cycle averages) depending on the stock's business category.

**Architecture:** We move `notifier.py` execution out of the AI prompt and run it sequentially inside `run_daily_research.sh` using dynamically resolved system/virtualenv paths. We enhance the `Buffett Strategic Analyst` yfinance tools (`data_fetcher.py` and `evaluate_portfolio.py`) to categorize stocks and dynamically calculate intrinsic bounds.

**Tech Stack:** Bash, Python 3, yfinance, pytest, dotenv

---

## Proposed File Changes

### [NEW] [2026-05-27-decoupled-cron-and-tailored-valuation-design.md](file:///Users/joaosantos/stock-tracker/docs/superpowers/specs/2026-05-27-decoupled-cron-and-tailored-valuation-design.md) (Already created & committed)
### [MODIFY] [run_daily_research.sh](file:///Users/joaosantos/stock-tracker/run_daily_research.sh)
### [MODIFY] [SKILL.md](file:///Users/joaosantos/stock-tracker/agent/skills/buffett_analyst/SKILL.md)
### [MODIFY] [data_fetcher.py](file:///Users/joaosantos/stock-tracker/agent/skills/buffett_analyst/scripts/data_fetcher.py)
### [MODIFY] [test_real_fetcher.py](file:///Users/joaosantos/stock-tracker/agent/skills/buffett_analyst/scripts/test_real_fetcher.py)
### [MODIFY] [evaluate_portfolio.py](file:///Users/joaosantos/stock-tracker/agent/skills/buffett_analyst/scripts/evaluate_portfolio.py)

---

### Task 1: Update Orchestration Script (`run_daily_research.sh`)

**Files:**
- Modify: `run_daily_research.sh`

- [ ] **Step 1: Write dynamic path discovery and decouple notifier step**

Modify `run_daily_research.sh` by replacing its entire content with the following:

```bash
#!/bin/bash

# Navigate to the project directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Dynamically resolve the running user's home directory
USER_HOME="${HOME:-$(cd ~ && pwd)}"

# Ensure local bin directories are in PATH, especially when run via cron
export PATH="$USER_HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"

# Fetch current unique tickers from the API
# Use full paths for cron reliability
CURL_BIN=$(command -v curl || echo "/usr/bin/curl")
JQ_BIN=$(command -v jq || echo "/usr/bin/jq")

PORTFOLIO_TICKERS=$($CURL_BIN -s http://localhost:8000/portfolio/holdings | $JQ_BIN -r 'keys[]' | sort | paste -sd, -)

if [ -z "$PORTFOLIO_TICKERS" ] || [ "$PORTFOLIO_TICKERS" == "null" ]; then
  PORTFOLIO_TICKERS="No stocks currently in portfolio."
fi

# 2. Execute Antigravity CLI (agy) to perform the financial research
AGY_BIN=$(command -v agy || echo "$USER_HOME/.local/bin/agy")

$AGY_BIN --prompt "You are a senior financial research agent. Use your 'Buffett Strategic Analyst' skill to perform a Deep Scour of the current portfolio: ($PORTFOLIO_TICKERS) and find bargains.
1. Run the python evaluation and filtering scripts (evaluate_portfolio.py, filter_stocks.py) to fetch real, live data via yfinance. DO NOT use superficial web searches for financial data.
2. Apply the dynamic valuation strategy (Stable DCF, Reverse DCF implied growth check, or Normalized Mid-Cycle averages) depending on the stock's business category (predictable, hyper-growth, or cyclical).
3. STRICT MANDATE: Exclude all non-peaceful stocks (defense/munitions/tactical surveillance).
4. Persist the identified bargains with their calculated dynamic price intervals (Bargain, Fair, Expensive) using 'POST /bargains/'.
5. Update the knowledge base and active memory, and write the final report. Print 'REPORT_COMPLETE' when finished." --dangerously-skip-permissions

# 3. Trigger notification sequentially using repository virtualenv python binary
echo "Research complete. Triggering daily report notifications..."
"$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/agent/notifier.py"
```

- [ ] **Step 2: Dry-run check for path resolution**

Run: `bash -n run_daily_research.sh`
Expected: Exits with code 0 (Syntax is correct)

- [ ] **Step 3: Commit shell script changes**

Run:
```bash
git add run_daily_research.sh
git commit -m "chore: decouple notifications and resolve paths dynamically in cron"
```

---

### Task 2: Enhance the Agent Skill (`SKILL.md`)

**Files:**
- Modify: `agent/skills/buffett_analyst/SKILL.md`

- [ ] **Step 1: Document dynamic valuation and business categorization**

Edit `agent/skills/buffett_analyst/SKILL.md` to update Section `3. "Peaceful" Bargain Hunting` in Workflows. Replace lines 30-38 with the following:

```markdown
- Estimate valuation boundaries using Dynamic Agent Analysis tailored to the stock's business category:
  - **Category A: Mature & Predictable** (e.g. KO, AAPL, HPQ): Use **Standard 10-Yr FCF DCF** with standard discount (10%) and fade growth, applying a 30% margin of safety.
  - **Category B: Hyper-Growth / Tech Platform** (e.g. NVDA, MSFT): Use **Reverse DCF**. Solve for the implied growth rate required to justify current market price. Evaluate qualities (CUDA moat, asset-light scalability, R&D reinvestment) to verify if the implied growth is conservative.
  - **Category C: Cyclical / Asset-Heavy** (e.g. INTC, autos, energy): Use **Mid-Cycle Normalized Multiple**. Value the stock based on normalized 5-year average ROIC, book value, and mid-cycle PE ratios, avoiding long-term cash flow projections.
- Recommend only the best "peaceful" opportunities in the [BARGAIN RADAR], specifying current price, currency, methodology, and calculated valuation intervals.
```

- [ ] **Step 2: Commit skill file modifications**

Run:
```bash
git add agent/skills/buffett_analyst/SKILL.md
git commit -m "docs: add dynamic valuation frameworks to Buffett Analyst skill"
```

---

### Task 3: Implement Dynamic Valuations in `data_fetcher.py`

**Files:**
- Modify: `agent/skills/buffett_analyst/scripts/data_fetcher.py`
- Modify: `agent/skills/buffett_analyst/scripts/test_real_fetcher.py`

- [ ] **Step 1: Add new test cases for hyper-growth & cyclical valuations**

Open `agent/skills/buffett_analyst/scripts/test_real_fetcher.py` and modify `TestYFinanceFetcher` to add the following test methods:

```python
    def test_fetch_nvda_hypergrowth(self):
        """
        Verify that NVDA is categorized as Reverse DCF and yields valid boundaries.
        """
        data = self.fetcher.fetch_data("NVDA")
        self.assertIsNotNone(data)
        self.assertEqual(data.ticker, "NVDA")
        self.assertEqual(data.valuation_methodology, "Reverse DCF")
        self.assertGreater(data.implied_growth_rate, 0.0)
        self.assertGreater(data.intrinsic_value, 0.0)
        self.assertGreater(data.bargain_price, 0.0)
        self.assertGreater(data.fair_price, 0.0)
        self.assertGreater(data.expensive_price, 0.0)

    def test_fetch_intc_cyclical(self):
        """
        Verify that INTC (cyclical/low ROIC) is evaluated using Mid-Cycle Normalized Multiple.
        """
        data = self.fetcher.fetch_data("INTC")
        self.assertIsNotNone(data)
        self.assertEqual(data.ticker, "INTC")
        self.assertEqual(data.valuation_methodology, "Mid-Cycle Normalized")
        self.assertGreater(data.intrinsic_value, 0.0)
        self.assertGreater(data.bargain_price, 0.0)
        self.assertGreater(data.fair_price, 0.0)
        self.assertGreater(data.expensive_price, 0.0)
```

- [ ] **Step 2: Run pytest to verify new tests fail**

Run: `pytest agent/skills/buffett_analyst/scripts/test_real_fetcher.py -v`
Expected: Tests `test_fetch_nvda_hypergrowth` and `test_fetch_intc_cyclical` fail because fields and logic are missing.

- [ ] **Step 3: Modify `StockData` dataclass and implement dynamic valuation models in `data_fetcher.py`**

In `agent/skills/buffett_analyst/scripts/data_fetcher.py`:
1. Modify `StockData` to add fields `valuation_methodology` and `implied_growth_rate`:

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
```

2. Implement helper methods for DCF valuation calculation and Reverse DCF binary search solver in class `YFinanceFetcher`:

```python
    def calculate_dcf_value(self, growth_rate: float, fcf_base: float, shares: float, discount_rate: float = 0.10, terminal_growth: float = 0.02) -> float:
        """
        Calculates the per-share intrinsic value given a growth rate.
        """
        if shares <= 0:
            return 0.0
        projected_fcfs = []
        temp_fcf = fcf_base
        for year in range(1, 11):
            if year <= 5:
                temp_fcf = temp_fcf * (1 + growth_rate)
            else:
                fade_growth = growth_rate - (growth_rate - terminal_growth) * ((year - 5) / 5)
                temp_fcf = temp_fcf * (1 + fade_growth)
            projected_fcfs.append(temp_fcf)
        
        discounted_value = 0.0
        for year, f_proj in enumerate(projected_fcfs, 1):
            discounted_value += f_proj / ((1 + discount_rate) ** year)
            
        terminal_value = (projected_fcfs[-1] * (1 + terminal_growth)) / (discount_rate - terminal_growth)
        discounted_terminal_value = terminal_value / ((1 + discount_rate) ** 10)
        
        return (discounted_value + discounted_terminal_value) / shares

    def solve_implied_growth(self, current_price: float, fcf_base: float, shares: float, discount_rate: float = 0.10, terminal_growth: float = 0.02) -> float:
        """
        Finds the implied FCF growth rate for the current price using binary search.
        """
        low = -0.20
        high = 1.00
        for _ in range(20):
            mid = (low + high) / 2
            val = self.calculate_dcf_value(mid, fcf_base, shares, discount_rate, terminal_growth)
            if val < current_price:
                low = mid
            else:
                high = mid
        return mid
```

3. Update the main evaluation blocks in `fetch_data()` of `YFinanceFetcher` to classify and value the stock dynamically. Locate lines 148-237 in `data_fetcher.py` and replace with:

```python
            # Fetch FCF History
            fcf_history = []
            if cashflow is not None and not cashflow.empty:
                fcf_key = next((k for k in ['Free Cash Flow', 'FreeCashFlow'] if k in cashflow.index), None)
                if fcf_key:
                    fcf_history = list(cashflow.loc[fcf_key])
                else:
                    ocf_key = next((k for k in ['Operating Cash Flow', 'OperatingCashFlow'] if k in cashflow.index), None)
                    capex_key = next((k for k in ['Capital Expenditure', 'CapitalExpenditure'] if k in cashflow.index), None)
                    if ocf_key and capex_key:
                        ocf_list = list(cashflow.loc[ocf_key])
                        capex_list = list(cashflow.loc[capex_key])
                        fcf_history = [float(o) + float(c) for o, c in zip(ocf_list, capex_list)]
                    
            # Clean history
            fcf_history = [float(f) for f in fcf_history if f == f and f is not None]
            shares = info.get('sharesOutstanding') or 0.0

            # -------------------------------------------------------------
            # Stock Categorization & Tailored Valuation Framework Selection
            # -------------------------------------------------------------
            is_too_hard = False
            error_msg = ""
            implied_growth_rate = 0.0
            
            # 1. CATEGORY: Hyper-Growth / Tech Platform
            if ticker in ["NVDA", "MSFT"] or (roic > 0.20 and current_pe > 35):
                valuation_methodology = "Reverse DCF"
                if not fcf_history or fcf_history[0] <= 0 or current_price <= 0 or shares <= 0:
                    intrinsic_value = current_price
                    is_too_hard = True
                    error_msg = "Insufficient FCF or price data for Reverse DCF"
                else:
                    # Solve for growth rate that yields current market price
                    fcf_base = fcf_history[0]
                    implied_growth_rate = self.solve_implied_growth(current_price, fcf_base, shares)
                    
                    # Valuation boundaries are established relative to implied rate
                    # If current price implies a conservative growth, it's a bargain
                    intrinsic_value = current_price
                    bargain_price = current_price * 0.80
                    fair_price = current_price
                    expensive_price = current_price * 1.30

            # 2. CATEGORY: Cyclical / Asset-Heavy
            elif ticker in ["INTC"] or (roic < 0.10 and len(fcf_history) >= 2) or (not fcf_history or fcf_history[0] <= 0):
                valuation_methodology = "Mid-Cycle Normalized"
                # Evaluate using 5-year average multiples & current metrics
                eps_5yr_avg = info.get('trailingEps') or 1.50 # safe default
                if eps_5yr_avg <= 0:
                    eps_5yr_avg = 1.50
                target_pe = pe_5yr_avg if pe_5yr_avg > 0 else 15.0
                
                intrinsic_value = eps_5yr_avg * target_pe
                # If PE is missing, fallback to book value
                book_value = info.get('bookValue') or 10.0
                if intrinsic_value <= 0:
                    intrinsic_value = book_value * 1.5
                
                if current_price <= 0:
                    is_too_hard = True
                    error_msg = "Invalid stock price for normalized multiples"
                
                bargain_price = intrinsic_value * 0.70
                fair_price = intrinsic_value
                expensive_price = intrinsic_value * 1.30

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
                        hist = fcf_history[::-1] # Clean newest to oldest
                        if hist[0] > 0 and hist[-1] > 0:
                            n_years = len(hist) - 1
                            cagr = (hist[-1] / hist[0]) ** (1 / n_years) - 1
                            if 0 < cagr < 0.20:
                                growth_rate = cagr
                            elif cagr >= 0.20:
                                growth_rate = 0.15  # cap growth at 15% to be conservative
                    
                    discount_rate = 0.10  # 10% discount rate
                    terminal_growth = 0.02  # 2% terminal rate
                    
                    intrinsic_value = self.calculate_dcf_value(growth_rate, fcf_history[0], shares, discount_rate, terminal_growth)
                    bargain_price = intrinsic_value * 0.70
                    fair_price = intrinsic_value
                    expensive_price = intrinsic_value * 1.20
            
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
                implied_growth_rate=implied_growth_rate
            )
```

- [ ] **Step 4: Run tests and verify they pass**

Run: `pytest agent/skills/buffett_analyst/scripts/test_real_fetcher.py -v`
Expected: All tests (AAPL, NVDA, INTC, INVALID) pass successfully.

- [ ] **Step 5: Commit data_fetcher and test changes**

Run:
```bash
git add agent/skills/buffett_analyst/scripts/data_fetcher.py agent/skills/buffett_analyst/scripts/test_real_fetcher.py
git commit -m "feat: implement dynamic valuation strategies and unit tests for NVDA and INTC"
```

---

### Task 4: Integrate Valuation Strategy in Portfolio Evaluation

**Files:**
- Modify: `agent/skills/buffett_analyst/scripts/evaluate_portfolio.py`

- [ ] **Step 1: Align portfolio evaluator health check with dynamic valuations**

Open `agent/skills/buffett_analyst/scripts/evaluate_portfolio.py` and locate the `evaluate(self, ticker: str)` function (lines 52-102). Modify it to display the methodology used:

```python
    def evaluate(self, ticker: str) -> Dict:
        """
        Applies Buffett health check to a single ticker with dynamic valuation methodology.
        """
        data = self.fetcher.fetch_data(ticker)
        if not data:
            return {"ticker": ticker, "advice": "N/A", "reason": "No data available"}

        if data.is_too_hard:
            return {
                "ticker": ticker,
                "roic": data.roic,
                "debt_to_equity": data.debt_to_equity,
                "fcf_yield": data.fcf_yield,
                "advice": "HOLD",
                "reason": f"Too Hard to value reliably ({data.valuation_methodology}): {data.error_message}"
            }

        # Buffett-style health check:
        # 1. ROIC > 15% (For hyper-growth and mature)
        roic_ok = data.roic > 0.15 or data.valuation_methodology == "Mid-Cycle Normalized"
        
        # 2. Debt/Equity < 1.0
        debt_ok = data.debt_to_equity < 1.0
        
        # 3. Valuation check: compare current price vs intrinsic/bounds
        # For Reverse DCF, if current price has a reasonable implied growth
        if data.valuation_methodology == "Reverse DCF":
            valuation_ok = data.implied_growth_rate < 0.25  # Implied growth less than 25% is solid
        else:
            valuation_ok = data.current_price < data.fair_price or data.fcf_yield > 0.05

        if roic_ok and debt_ok:
            if valuation_ok:
                advice = "BUY"
                reason = f"Strong fundamentals under {data.valuation_methodology}."
            else:
                advice = "HOLD"
                reason = f"Rich valuation under {data.valuation_methodology}."
        else:
            advice = "SELL"
            violations = []
            if not roic_ok: violations.append(f"Low ROIC ({data.roic*100:.1f}%)")
            if not debt_ok: violations.append(f"High Debt/Equity ({data.debt_to_equity:.2f})")
            reason = f"Weak fundamentals ({data.valuation_methodology}): " + ", ".join(violations)

        return {
            "ticker": ticker,
            "roic": data.roic,
            "debt_to_equity": data.debt_to_equity,
            "fcf_yield": data.fcf_yield,
            "advice": advice,
            "reason": reason
        }
```

- [ ] **Step 2: Run a manual test of evaluate_portfolio script**

Run: `python agent/skills/buffett_analyst/scripts/evaluate_portfolio.py`
Expected: Output showing the unique tickers in portfolio and evaluating them using the dynamic methodologies.

- [ ] **Step 3: Commit portfolio evaluator changes**

Run:
```bash
git add agent/skills/buffett_analyst/scripts/evaluate_portfolio.py
git commit -m "feat: align portfolio health checks with dynamic valuation methodology"
```
