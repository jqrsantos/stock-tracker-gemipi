# Strict Execution Redesign for Buffett Analyst

## Overview
This specification addresses structural execution failures in the Buffett Analyst AI agent. It enforces rigid formatting for the Absolute Valuation Table, mandates the 10-Q FCF Audit Protocol, and resolves a catastrophic DCF valuation failure for semiconductor supercycles (e.g., Micron).

## Requirements

### 1. The Absolute Valuation Table (Rule 1)
- The AI must explicitly render an `[ABSOLUTE VALUATION TABLE]` in Markdown format.
- Bulleted lists containing valuation metrics within `[PORTFOLIO HEALTH]` are strictly forbidden.
- The required table format is:
  ```markdown
  ### [ABSOLUTE VALUATION TABLE]
  | Ticker | Current Price | Fair Value (Intrinsic) | MoS % | Status | Action |
  |--------|---------------|-------------------------|-------|--------|--------|
  | [Tk]   | $[Price]      | $[Value]                | [%]   | [Stat] | [Act]  |
  ```
- Allowable Actions: "STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL".
- Actions must be purely based on absolute valuation and moat integrity, NEVER momentum or "profit-taking".

### 2. 10-Q Negative FCF Audit Protocol (Rule 2 & 3)
- Banned behavior: Labeling a stock "Too Hard" solely due to negative FCF growth.
- Protocol Trigger: If FCF growth is < 0%, the AI must trigger the 10-Q FCF Audit Protocol.
- Output Format for Audit:
  ```
  >> 10-Q FCF AUDIT FOR [TICKER]: 
  >> OCF Trend: [Growing/Flat/Declining]
  >> CapEx Trend: [Increasing/Decreasing]
  >> Verdict: [Temporary Reinvestment Cycle OR Structural Core Decline]
  ```
- Audit-Driven Actions:
  - If "Temporary Reinvestment Cycle": BUY or HOLD is permitted if absolute valuation justifies.
  - If "Structural Core Decline": MUST issue SELL or STRONG SELL.
- Banned Phrase: "lock in profits" is strictly forbidden.

### 3. Macro Valuation Caps & Supercycle Carve-Out (Rule 4)
- **Terminal Growth Cap:** All Terminal Growth Rates must be hard-capped at 3.5% (0.035).
- **Semiconductor Supercycle Carve-Out:** Companies structurally transformed by macroeconomic supercycles (e.g., NVDA, MU, INTC, AMD) must not be valued using backward-looking 5-year average EPS (Mid-Cycle Normalized Multiple) if their current earnings are breaking out.
- Implementation (`data_fetcher.py`):
  - Remove `MU` and `INTC` from the hardcoded `Cyclical / Asset-Heavy` bucket.
  - Create a new logic block for "Supercycle/Semiconductor" that triggers if the ticker is a known semiconductor and current performance massively outpaces historical medians.
  - Value these assets using a DCF model with the growth rate capped appropriately and the terminal rate capped at 3.5%.

## Files to Modify
1. `agent/skills/buffett_analyst/SKILL.md`: Rewrite the prompt instructions to enforce the schema, the 10-Q audit matrix, and the banned phrases.
2. `agent/skills/buffett_analyst/scripts/data_fetcher.py`: Update the terminal growth rate caps to `0.035` and implement the Supercycle DCF logic for Semiconductors.
