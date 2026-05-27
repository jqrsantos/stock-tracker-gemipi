# Design Spec: Aligning Single Stock Valuation with 6 AM Daily Report

## Status: Approved
**Author**: Antigravity (AI Coding Assistant)  
**Date**: 2026-05-27  
**Branch**: `feat/align-single-stock-valuation`

---

## 1. Problem Statement & Context

Currently, there is a discrepancy between the **6 AM Daily Report** and the **Telegram Single Stock Investigation** processes when evaluating stock candidates:
1. **Valuation Inconsistency**: The 6 AM Daily Report uses the centralized `data_fetcher.py` and `YFinanceFetcher` to dynamically categorize and evaluate stocks (Standard 10-Yr DCF for mature companies, Reverse DCF for hyper-growth/tech platforms, and Mid-Cycle Normalized Multiples for cyclical/asset-heavy companies). The single stock process in `listener/main.py` hardcodes standard 10-Yr DCF and static pricing boundaries, leading to conflicting metrics and recommendations.
2. **Incorrect Script Reference**: The single stock prompt tells the agent to run `evaluate_portfolio.py`, which is designed to evaluate the *entire* portfolio, not a single ticker.
3. **Valuation Boundaries**: The single stock prompt hardcodes static 30% margin of safety margins (`* 0.70`, `* 1.20`) which overrides the custom, dynamic boundaries calculated in `data_fetcher.py` (e.g. Reverse DCF has specific boundaries).

To resolve these, we will introduce a new, lightweight `evaluate_stock.py` command-line helper script that utilizes the centralized `YFinanceFetcher` to output identical metrics. Then, we will update the Antigravity prompt inside `listener/main.py` to instruct the agent to run this new script, read its output, and consume its exact calculations.

---

## 2. Proposed Changes

### 2.1. [NEW] `agent/skills/buffett_analyst/scripts/evaluate_stock.py`
This script acts as the CLI wrapper for evaluating a single stock.

*   **Usage**: `python agent/skills/buffett_analyst/scripts/evaluate_stock.py <ticker>`
*   **Logic**:
    1. Parse the target ticker argument from `sys.argv`.
    2. Instantiate `YFinanceFetcher` and run `fetch_data(ticker)`.
    3. Output the metrics in a clean, human-readable format or standard JSON for the agent to parse.
*   **Output Details**:
    *   Ticker name and company long name
    *   Industry
    *   Current Price
    *   ROIC, Debt to Equity, FCF Yield
    *   Valuation Methodology (e.g., "Standard DCF", "Reverse DCF", "Mid-Cycle Normalized")
    *   Calculated Boundaries (Bargain, Fair, Expensive)
    *   Is Too Hard status and error message (if any)

### 2.2. [NEW] `agent/skills/buffett_analyst/scripts/test_evaluate_stock.py`
A new unit test suite using `unittest` and `unittest.mock` to verify the new CLI script behavior.

### 2.3. [MODIFY] `listener/main.py`
We will rewrite instructions 1-4 of the Prompt passed to `agy` inside `listener/main.py`'s `handle_message` function to:
1. Mandate the execution of `agent/skills/buffett_analyst/scripts/evaluate_stock.py <ticker>`.
2. Instruct the agent to parse and use the exact outputs (metrics, methodology, boundaries, too-hard status) printed by the script in both the Telegram summary and the email report.

---

## 3. Verification Plan

### 3.1. Automated Unit Tests
*   Run the new unit test suite to ensure the CLI script integrates perfectly with `data_fetcher.py`.
    ```bash
    .venv/bin/pytest agent/skills/buffett_analyst/scripts/
    ```

### 3.2. Manual Verification
*   Execute the script directly from the terminal to verify its output:
    ```bash
    python agent/skills/buffett_analyst/scripts/evaluate_stock.py AAPL
    python agent/skills/buffett_analyst/scripts/evaluate_stock.py NVDA
    python agent/skills/buffett_analyst/scripts/evaluate_stock.py INTC
    ```
*   Verify that the output contains the identical metrics and methodology to those calculated by the central valuation engine.
