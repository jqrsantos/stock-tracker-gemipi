# Strict Execution Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement strict prompt schemas for the valuation table and 10-Q audits, and fix the DCF valuation caps for semiconductor supercycles.

**Architecture:** Modifies the AI's system instructions (`SKILL.md`) to rigidly enforce output schema and audit rules. Modifies `data_fetcher.py` to correctly cap terminal growth at 3.5% and treat specific semiconductor stocks breaking out of historical medians as "Hyper-Growth" rather than purely cyclical.

**Tech Stack:** Python, Markdown Prompts

---

### Task 1: Update `SKILL.md` (Strict Prompt Enforcement)

**Files:**
- Modify: `agent/skills/buffett_analyst/SKILL.md`

- [ ] **Step 1: Rewrite [ABSOLUTE VALUATION TABLE] rules**
Replace the line:
`- [ABSOLUTE VALUATION TABLE]: Embed the engine ASCII table output inside a code block.`
With:
```markdown
   - `[ABSOLUTE VALUATION TABLE]`: You are strictly forbidden from placing valuation metrics and actionable advice into bulleted lists within the `[PORTFOLIO HEALTH]` section. You MUST render the `[ABSOLUTE VALUATION TABLE]` exactly as formatted below, transcribing the output from `engine.py`.
     ```markdown
     ### [ABSOLUTE VALUATION TABLE]
     | Ticker | Current Price | Fair Value (Intrinsic) | MoS % | Status | Action |
     |--------|---------------|-------------------------|-------|--------|--------|
     | [Tk]   | $[Price]      | $[Value]                | [%]   | [Stat] | [Act]  |
     ```
     Allowable Actions: "STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL". Actions must be dictated purely by absolute valuation and moat integrity, NEVER by recent stock momentum. The phrase "lock in profits" is explicitly banned under all circumstances.
```

- [ ] **Step 2: Add 10-Q Audit Rules**
In the "Orchestrated Multi-Agent Workflow" section, add explicit audit output instructions:
```markdown
   - `[10-Q FCF AUDITS]`: IF a stock flags `[REQUIRES 10-Q FCF AUDIT]`, you MUST invoke the `10q_auditor` subagent to analyze the most recent Statement of Cash Flows. You MUST output the findings explicitly using this format:
     >> 10-Q FCF AUDIT FOR [TICKER]: 
     >> OCF Trend: [Growing/Flat/Declining]
     >> CapEx Trend: [Increasing/Decreasing]
     >> Verdict: [Temporary Reinvestment Cycle OR Structural Core Decline]
     If Verdict is "Temporary Reinvestment Cycle", you may BUY/HOLD based on valuation. If "Structural Core Decline", you MUST SELL/STRONG SELL.
```

- [ ] **Step 3: Commit changes**
```bash
git add agent/skills/buffett_analyst/SKILL.md
git commit -m "docs: enforce strict absolute valuation table and 10-q audit schemas"
```

### Task 2: Update `data_fetcher.py` (Macro Caps and MU Supercycle)

**Files:**
- Modify: `agent/skills/buffett_analyst/scripts/data_fetcher.py`

- [ ] **Step 1: Update Terminal Growth Caps**
In `calculate_dcf_value`, `solve_implied_growth`, and `fetch_data` references to `0.025`, change them to `0.035` (3.5%).
Example: 
```python
# In calculate_dcf_value signature
def calculate_dcf_value(self, growth_rate: float, fcf_base: float, shares: float, discount_rate: float = 0.10, terminal_growth: float = 0.035) -> float:

# In solve_implied_growth signature
def solve_implied_growth(self, current_price: float, fcf_base: float, shares: float, discount_rate: float = 0.10, terminal_growth: float = 0.035) -> float:
```
Update any `0.025` calls inside `fetch_data` to `0.035`.

- [ ] **Step 2: Implement Semiconductor Supercycle Logic**
Locate the Category 2 section: `elif ticker in ["INTC", "MU"] or (roic < 0.10 and len(fcf_history) >= 2) or not fcf_history:`
Change it to:
```python
            # 1.5. CATEGORY: Supercycle Semiconductors Breakout
            elif ticker in ["NVDA", "MU", "INTC", "AMD"] and len(fcf_history) >= 3 and current_price > 0 and shares > 0:
                # Check if current FCF is significantly outperforming the 5-year median, indicating a supercycle
                hist_median = statistics.median(fcf_history[:5])
                if fcf_history[0] > 1.5 * hist_median or (hist_median < 0 and fcf_history[0] > 0):
                    valuation_methodology = "Supercycle DCF"
                    growth_rate = 0.20 # Assume 20% growth for supercycle peak
                    expected_growth_rate = growth_rate
                    terminal_growth = 0.035
                    intrinsic_value = self.calculate_dcf_value(growth_rate, fcf_history[0], shares, discount_rate, terminal_growth)
                    bargain_price = intrinsic_value * 0.70
                    fair_price = intrinsic_value
                    expensive_price = intrinsic_value * 1.30
                else:
                    # Fallback to Cyclical if not breaking out
                    valuation_methodology = "Mid-Cycle Normalized"
                    eps_5yr_avg = 0.0
                    if income_stmt is not None and not income_stmt.empty:
                        eps_key = next((k for k in ['Diluted EPS', 'DilutedEPS', 'Basic EPS', 'BasicEPS'] if k in income_stmt.index), None)
                        if eps_key is not None:
                            eps_vals = income_stmt.loc[eps_key]
                            if hasattr(eps_vals, 'iloc'):
                                eps_list = [float(x) for x in eps_vals if x == x and x is not None]
                            else:
                                eps_list = [float(eps_vals)]
                            eps_list = [x for x in eps_list if not math.isnan(x) and not math.isinf(x)]
                            if eps_list:
                                eps_5yr_avg = sum(eps_list) / len(eps_list)
                    target_pe = min(pe_5yr_avg if pe_5yr_avg > 0 else 15.0, 25.0)
                    intrinsic_value = eps_5yr_avg * target_pe
                    if eps_5yr_avg <= 0:
                        intrinsic_value = 0.0
                        is_too_hard = True
                        error_msg = "Structurally negative or missing EPS for cyclical stock"
                        bargain_price = 0.0
                        fair_price = 0.0
                        expensive_price = 0.0
                    else:
                        bargain_price = intrinsic_value * 0.70
                        fair_price = intrinsic_value
                        expensive_price = intrinsic_value * 1.30

            # 2. CATEGORY: Cyclical / Asset-Heavy
            elif (roic < 0.10 and len(fcf_history) >= 2) or not fcf_history:
```

- [ ] **Step 3: Run data_fetcher manually to verify**
Run: `python agent/skills/buffett_analyst/scripts/data_fetcher.py`
Expected: AAPL still works. The script parses without syntax errors.

- [ ] **Step 4: Commit changes**
```bash
git add agent/skills/buffett_analyst/scripts/data_fetcher.py
git commit -m "feat: cap terminal growth at 3.5% and add supercycle semiconductor logic"
```
