# Multi-Agent Global Research & AHP-TOPSIS Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a specialized multi-agent global macro and stock tracking workflow coordinated by a main orchestrator, backed by an AHP-TOPSIS quantitative portfolio decision engine, rendering results in a spacious, dyslexia-friendly layout.

**Architecture:** 
1. The `Buffett Strategic Analyst` skill is modified to orchestrate 4 parallel subagents (Macro, Portfolio, Bargain, News).
2. The orchestrator calls `engine.py`, which executes AHP-TOPSIS rankings to outputs an ASCII Action Matrix.
3. The notifier layout is updated to compile spacious `$360\text{px}$-wide$ cards and group news at the bottom.

**Tech Stack:** Python 3, Pandas, NumPy, yfinance, Markdown, FastAPI, SMTP.

---

### Task 1: Create the AHP-TOPSIS Decision Engine

**Files:**
- Create: `agent/skills/buffett_analyst/scripts/engine.py`

- [ ] **Step 1: Write the engine logic**
  Create the `engine.py` file with the complete AHP-TOPSIS computation matrix, Consistency Ratio validation, vector normalization, Ideal values distance metrics, and the Action Matrix mapping CLI.

```python
# agent/skills/buffett_analyst/scripts/engine.py
import sys
import argparse
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

# RI values for Consistency Ratio calculation (indices 1 to 10)
RI_VALUES = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}

def run_ahp(pairwise_matrix: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Computes AHP weight vectors and checks the Consistency Ratio (CR).
    """
    n = pairwise_matrix.shape[0]
    # Find eigenvalues and eigenvectors
    eigvals, eigvecs = np.linalg.eig(pairwise_matrix)
    max_idx = np.argmax(np.real(eigvals))
    lambda_max = np.real(eigvals[max_idx])
    
    # Extract corresponding eigenvector and normalize to sum to 1
    weights = np.real(eigvecs[:, max_idx])
    weights = weights / np.sum(weights)
    
    # Calculate CI and CR
    if n <= 2:
        cr = 0.0
    else:
        ci = (lambda_max - n) / (n - 1)
        ri = RI_VALUES.get(n, 1.49)
        cr = ci / ri
        
    return weights, cr

def run_topsis(matrix: np.ndarray, weights: np.ndarray, criteria_beneficial: List[bool]) -> np.ndarray:
    """
    Runs TOPSIS vectorization on a decision matrix and returns Closeness Coefficients.
    """
    m, n = matrix.shape
    # Normalize the decision matrix using vector norm
    norm_matrix = np.zeros((m, n))
    for j in range(n):
        col_norm = np.sqrt(np.sum(matrix[:, j] ** 2))
        if col_norm == 0:
            norm_matrix[:, j] = 0
        else:
            norm_matrix[:, j] = matrix[:, j] / col_norm
            
    # Calculate Weighted Normalized Decision Matrix
    weighted_matrix = norm_matrix * weights
    
    # Determine Positive-Ideal and Negative-Ideal Solutions
    ideal_pos = np.zeros(n)
    ideal_neg = np.zeros(n)
    for j in range(n):
        if criteria_beneficial[j]:
            ideal_pos[j] = np.max(weighted_matrix[:, j])
            ideal_neg[j] = np.min(weighted_matrix[:, j])
        else:
            ideal_pos[j] = np.min(weighted_matrix[:, j])
            ideal_neg[j] = np.max(weighted_matrix[:, j])
            
    # Calculate Euclidean distances
    dist_pos = np.sqrt(np.sum((weighted_matrix - ideal_pos) ** 2, axis=1))
    dist_neg = np.sqrt(np.sum((weighted_matrix - ideal_neg) ** 2, axis=1))
    
    # Compute Closeness Coefficient
    closeness = np.zeros(m)
    for i in range(m):
        denom = dist_pos[i] + dist_neg[i]
        closeness[i] = dist_neg[i] / denom if denom > 0 else 0.0
        
    return closeness

def generate_action_matrix(df: pd.DataFrame, holdings: List[str]) -> pd.DataFrame:
    """
    Maps closeness scores to STRONG BUY, STRONG HOLD, STRONG SELL, IGNORE, or HOLD.
    """
    holdings_upper = [t.upper() for t in holdings]
    actions = []
    
    for idx, row in df.iterrows():
        ticker = row['Ticker'].upper()
        score = row['Score']
        owned = ticker in holdings_upper
        
        if score >= 0.70:
            action = "STRONG HOLD" if owned else "STRONG BUY"
        elif score <= 0.40:
            action = "STRONG SELL" if owned else "IGNORE"
        else:
            action = "HOLD" if owned else "IGNORE"
            
        actions.append(action)
        
    df['Matrix Action'] = actions
    return df

def generate_ascii_table(df: pd.DataFrame, holdings: List[str]) -> str:
    """
    Renders the final ranked matrix as an ASCII terminal summary table.
    """
    holdings_upper = [t.upper() for t in holdings]
    df['Status'] = df['Ticker'].apply(lambda t: "Owned" if t.upper() in holdings_upper else "Watchlist")
    
    lines = []
    lines.append("+--------+------------+--------------+---------------+")
    lines.append("| Ticker | Status     | TOPSIS Score | Matrix Action |")
    lines.append("+--------+------------+--------------+---------------+")
    for _, row in df.iterrows():
        ticker = f"{row['Ticker']:<6}"
        status = f"{row['Status']:<10}"
        score = f"{row['Score']:.4f}"
        action = f"{row['Matrix Action']:<13}"
        lines.append(f"| {ticker} | {status} |     {score}   | {action} |")
    lines.append("+--------+------------+--------------+---------------+")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="AHP-TOPSIS Portfolio Decision Engine")
    parser.add_argument("--data-path", type=str, help="Path to csv containing stock data columns: Ticker, ROIC, ROE, PE, DebtToEquity, OperatingMargin")
    parser.add_argument("--holdings", type=str, default="", help="Comma-separated list of currently owned tickers")
    args = parser.parse_args()
    
    # 1. Define standard criteria weights (AHP reciprocal matrix)
    # Order: ROIC, ROE, PE (non-beneficial), DebtToEquity (non-beneficial), OperatingMargin
    # Default consistent Buffett-weighted matrix
    pairwise = np.array([
        [1.0, 2.0, 4.0, 3.0, 2.0],
        [0.5, 1.0, 3.0, 2.0, 1.0],
        [0.25, 0.33, 1.0, 0.5, 0.33],
        [0.33, 0.5, 2.0, 1.0, 0.5],
        [0.5, 1.0, 3.0, 2.0, 1.0]
    ])
    
    weights, cr = run_ahp(pairwise)
    if cr >= 0.10:
        print(f"Warning: AHP matrix inconsistency detected (CR = {cr:.4f} >= 0.10). Using equal weights fallback.")
        weights = np.ones(5) / 5.0
        
    # 2. Ingest Data
    if args.data_path:
        df = pd.read_csv(args.data_path)
    else:
        # Load a default mockup CSV dataset
        mockup_data = {
            "Ticker": ["AAPL", "MSFT", "KO", "HPQ", "INTC"],
            "ROIC": [0.245, 0.221, 0.192, 0.084, 0.045],
            "ROE": [0.352, 0.312, 0.264, 0.112, 0.062],
            "PE": [28.5, 32.1, 19.8, 12.4, 38.5],
            "DebtToEquity": [0.85, 0.65, 0.92, 1.45, 0.52],
            "OperatingMargin": [0.284, 0.354, 0.251, 0.082, 0.041]
        }
        df = pd.DataFrame(mockup_data)
        
    # Standardize column extraction
    tickers = df['Ticker'].tolist()
    criteria_matrix = df[['ROIC', 'ROE', 'PE', 'DebtToEquity', 'OperatingMargin']].to_numpy()
    
    # Beneficial boolean mapping matching our criteria order
    beneficial = [True, True, False, False, True]
    
    # 3. Calculate scores
    scores = run_topsis(criteria_matrix, weights, beneficial)
    df['Score'] = scores
    
    # Sort descending by score
    df = df.sort_values(by='Score', ascending=False).reset_index(drop=True)
    
    # 4. Map actions
    holdings_list = [t.strip().upper() for t in args.holdings.split(",") if t.strip()]
    df = generate_action_matrix(df, holdings_list)
    
    # 5. Output
    print(generate_ascii_table(df, holdings_list))

if __name__ == "__main__":
    main()
```

---

### Task 2: Implement Decision Engine Tests

**Files:**
- Create: `agent/skills/buffett_analyst/scripts/test_engine.py`

- [ ] **Step 1: Write unit tests for engine math**
  Write tests checking vector norms, reciprocal eigenvectors, Consistency Ratio boundaries, and correct action mappings.

```python
# agent/skills/buffett_analyst/scripts/test_engine.py
import pytest
import numpy as np
import pandas as pd
from engine import run_ahp, run_topsis, generate_action_matrix

def test_ahp_consistency():
    # Perfect consistency comparison matrix (CR should be 0.0)
    pairwise = np.array([
        [1.0, 2.0, 4.0],
        [0.5, 1.0, 2.0],
        [0.25, 0.5, 1.0]
    ])
    weights, cr = run_ahp(pairwise)
    assert cr < 0.01
    assert np.allclose(np.sum(weights), 1.0)
    assert weights[0] > weights[1] > weights[2]

def test_topsis_rankings():
    # 3 alternatives, 3 criteria (all beneficial)
    # Alternative 0 should score highest as it dominates all values
    decision_matrix = np.array([
        [0.9, 0.9, 0.9],
        [0.5, 0.5, 0.5],
        [0.1, 0.1, 0.1]
    ])
    weights = np.array([0.5, 0.3, 0.2])
    beneficial = [True, True, True]
    
    scores = run_topsis(decision_matrix, weights, beneficial)
    assert scores[0] > scores[1] > scores[2]
    assert 0.9 < scores[0] <= 1.0
    assert 0.0 <= scores[2] < 0.1

def test_action_matrix():
    data = {
        "Ticker": ["AAPL", "MSFT", "HPQ"],
        "Score": [0.85, 0.55, 0.25]
    }
    df = pd.DataFrame(data)
    holdings = ["AAPL", "HPQ"]
    
    result_df = generate_action_matrix(df, holdings)
    
    # AAPL is owned + score >= 0.70 -> STRONG HOLD
    assert result_df.loc[result_df['Ticker'] == 'AAPL', 'Matrix Action'].values[0] == 'STRONG HOLD'
    # MSFT is watchlist + 0.40 < score < 0.70 -> IGNORE (or HOLD if owned)
    assert result_df.loc[result_df['Ticker'] == 'MSFT', 'Matrix Action'].values[0] == 'IGNORE'
    # HPQ is owned + score <= 0.40 -> STRONG SELL
    assert result_df.loc[result_df['Ticker'] == 'HPQ', 'Matrix Action'].values[0] == 'STRONG SELL'
```

- [ ] **Step 2: Run tests to verify they pass**
  Run: `.venv/bin/pytest agent/skills/buffett_analyst/scripts/test_engine.py -v`
  Expected: `3 passed`

- [ ] **Step 3: Commit files**
  Run:
  ```bash
  git add agent/skills/buffett_analyst/scripts/engine.py agent/skills/buffett_analyst/scripts/test_engine.py
  git commit -m "feat: add AHP-TOPSIS engine and corresponding test suite"
  ```

---

### Task 3: Update Main Analyst Skill to Orchestrate Subagents

**Files:**
- Modify: `agent/skills/buffett_analyst/SKILL.md`

- [ ] **Step 1: Rewrite the orchestrator workflow instructions**
  Update the workflows to direct the primary agent to define and invoke subagents concurrently, run the decision engine, and gather reports.

```diff
-### 4. Daily Report Generation
-- Create a structured report at `knowledge_base/daily_reports/YYYY-MM-DD-report.md`.
-- Include the following sections:
-    - `[MACRO DASHBOARD]`: Key indicators and Bullish/Bearish impact.
-    - `[PORTFOLIO HEALTH]`: Current holdings status and advice.
-    - `[GLOBAL NARRATIVE]`: Regional analysis and event synthesis.
-    - `[BARGAIN RADAR]`: Top 3 high-quality "peaceful" opportunities.
-- Use `notifier.py` to send the report via Email and Telegram once finalized.
+### 4. Orchestrated Multi-Agent Workflow
+When executed, the primary agent MUST orchestrate parallel subagents:
+1. **Define Subagents:** Define four specialized subagents using `define_subagent`:
+   - `macro_analyst`: Focused on US, EU, JP central bank decisions, yields, currencies, geopolitics, commodities, and supply chains.
+   - `portfolio_analyst`: Focused on retrieving holdings (`GET /portfolio/holdings`), running portfolio check metrics.
+   - `bargain_hunter`: Focused on scanning indices and applying DCF models.
+   - `company_news_agent`: Focused on crawling latest news catalysts.
+2. **Invoke Subagents:** Use `invoke_subagent` in parallel, passing each their context.
+3. **Execute Decision Engine:** Run the AHP-TOPSIS engine by running `python agent/skills/buffett_analyst/scripts/engine.py --holdings <owned_tickers_comma_separated>` capturing the ASCII matrix.
+4. **Generate Report:** Compile outputs into `knowledge_base/daily_reports/YYYY-MM-DD-report.md`. Include sections:
+   - `[MACRO DASHBOARD]`: Integrated US, EU, Japan economic/interest policies & geopolitical narratives.
+   - `[DECISION MATRIX]`: Embed the engine ASCII table output inside a code block.
+   - `[PORTFOLIO HEALTH]`: Metrics and stock properties ready for cards.
+   - `[BARGAIN RADAR]`: 3 bargains and their parameters.
+   - `[GLOBAL COMPANY NEWS]`: Dynamic news summaries grouped at the bottom.
+5. **Update Memory:** Save macro highlights to `knowledge_base/active_memory.md`.
+6. Run `notifier.py` to distribute.
```

- [ ] **Step 2: Commit changes**
  Run:
  ```bash
  git add agent/skills/buffett_analyst/SKILL.md
  git commit -m "refactor: update Buffett Strategic Analyst skill workflow to support multi-agent orchestration"
  ```

---

### Task 4: Redesign the Notifier Visual Template

**Files:**
- Modify: `agent/notifier.py`

- [ ] **Step 1: Rewrite HTML builder inside `agent/notifier.py`**
  Modify `build_html_body` and CSS replacement rules to target card structures (`max-width: 360px` with left borders) and isolate news.

```diff
-    styled_html = re.sub(r'<h3>(.*?)</h3>', r'<h3 style="margin: 28px 0 12px 0; font-size: 1.1rem; font-weight: 700; color: #0f172a; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">\1</h3>', styled_html)
-    styled_html = re.sub(r'<h2>(.*?)</h2>', r'<h2 style="margin: 24px 0 12px 0; font-size: 1.25rem; font-weight: 700; color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">\1</h2>', styled_html)
+    # Replace sections to support spacious spacing and dyslexia-friendly typography
+    styled_html = styled_html.replace("<p>", '<p style="margin-bottom: 16px; line-height: 1.8; text-align: left;">')
+    
+    # Style headers with clear spacing
+    styled_html = re.sub(r'<h2>(.*?)</h2>', r'<h2 style="font-size: 1.35rem; font-weight: 800; color: #0f172a; margin-top: 40px; margin-bottom: 16px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; text-transform: uppercase;">\1</h2>', styled_html)
+    styled_html = re.sub(r'<h3>(.*?)</h3>', r'<h3 style="font-size: 1.15rem; font-weight: 700; color: #1e293b; margin-top: 24px; margin-bottom: 12px;">\1</h3>', styled_html)
+
+    # Extract ASCII tables inside pre blocks and style them
+    styled_html = styled_html.replace("<pre>", '<pre style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; font-family: monospace; font-size: 0.85rem; line-height: 1.4; overflow-x: auto; margin-bottom: 24px;">')
```

Implement the card replacement engine for stock details parsed from the markdown report:
```python
# Insert inside build_html_body
def format_stock_cards(html_content: str) -> str:
    """
    Parses generated stock metrics blocks into separate visual cards with left border accents.
    """
    # Regex matching markdown sections representing stock profiles
    stock_pattern = r'###\s+([A-Z]+)\s*\((.*?)\)\s*-\s*(STRONG BUY|STRONG HOLD|STRONG SELL|BUY|HOLD|SELL)\s*.*?ROIC:\s*([0-9\.\%]+)\s*.*?Debt/Equity:\s*([0-9\.]+)\s*.*?FCF Yield:\s*([0-9\.\%]+)\s*.*?Valuation:\s*(.*?)(?=\n###|\n\n\n|\n--|$)'
    
    def replace_with_card(match):
        ticker = match.group(1)
        name = match.group(2)
        status = match.group(3).upper()
        roic = match.group(4)
        de = match.group(5)
        fcf = match.group(6)
        val = match.group(7).strip()
        
        # Color mapping
        border_color = "#3b82f6"  # Blue default
        bg_status = "#f1f5f9"
        text_status = "#475569"
        
        if "BUY" in status:
            border_color = "#10b981"  # Green
            bg_status = "#ecfdf5"
            text_status = "#059669"
        elif "SELL" in status:
            border_color = "#ef4444"  # Red
            bg_status = "#fef2f2"
            text_status = "#ef4444"
        elif "HOLD" in status:
            border_color = "#d97706"  # Amber
            bg_status = "#fffbeb"
            text_status = "#d97706"
            
        return f"""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid {border_color}; border-radius: 8px; padding: 18px 22px; margin-bottom: 28px; max-width: 360px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div>
              <h3 style="margin: 0; font-size: 1.15rem; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">{ticker}</h3>
              <span style="font-size: 0.75rem; color: #64748b; font-weight: 500;">{name}</span>
            </div>
            <span style="background: {bg_status}; color: {text_status}; padding: 4px 10px; border-radius: 100px; font-size: 0.72rem; font-weight: 800; letter-spacing: 0.05em; text-transform: uppercase;">{status}</span>
          </div>
          
          <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem; line-height: 1.4;">
            <tr>
              <td style="padding: 5px 0; border-bottom: 1px dashed #f1f5f9; color: #64748b; text-align: left;">ROIC</td>
              <td style="padding: 5px 0; border-bottom: 1px dashed #f1f5f9; text-align: right; font-weight: 700; color: #0f172a;">{roic}</td>
            </tr>
            <tr>
              <td style="padding: 5px 0; border-bottom: 1px dashed #f1f5f9; color: #64748b; text-align: left;">Debt/Equity</td>
              <td style="padding: 5px 0; border-bottom: 1px dashed #f1f5f9; text-align: right; font-weight: 700; color: #0f172a;">{de}</td>
            </tr>
            <tr>
              <td style="padding: 5px 0; border-bottom: 1px dashed #f1f5f9; color: #64748b; text-align: left;">FCF Yield</td>
              <td style="padding: 5px 0; border-bottom: 1px dashed #f1f5f9; text-align: right; font-weight: 700; color: #0f172a;">{fcf}</td>
            </tr>
            <tr>
              <td style="padding: 5px 0; color: #64748b; text-align: left;">Valuation</td>
              <td style="padding: 5px 0; text-align: right; font-weight: 700; color: {border_color};">{val}</td>
            </tr>
          </table>
        </div>
        """
    return re.sub(stock_pattern, replace_with_card, html_content, flags=re.DOTALL)
```

Apply this custom parsing step prior to wrapping the HTML:
```python
# Inside build_html_body
styled_html = format_stock_cards(styled_html)
```

- [ ] **Step 2: Commit updates**
  Run:
  ```bash
  git add agent/notifier.py
  git commit -m "style: implement compact card parser and dyslexia-friendly margins in notifier"
  ```

---

### Task 5: End-to-End Validation Run

**Files:**
- Modify: `run_daily_research.sh`

- [ ] **Step 1: Check orchestration run execution**
  Trigger the research script directly using mock data parameters to ensure no syntax/runtime issues exist.
  Run: `bash run_daily_research.sh` (or executing it via python locally)
  Expected: Completed run, creation of YYYY-MM-DD-report.md, console output of `REPORT_COMPLETE`.

- [ ] **Step 2: Commit any final configurations**
  Run: `git commit -am "fix: complete integration hooks"`
