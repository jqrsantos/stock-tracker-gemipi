#!/bin/bash

# Navigate to the project directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Fetch current unique tickers from the API
# Use full paths for cron reliability
CURL_BIN=$(command -v curl || echo "/usr/bin/curl")
JQ_BIN=$(command -v jq || echo "/usr/bin/jq")

PORTFOLIO_TICKERS=$($CURL_BIN -s http://localhost:8000/portfolio/holdings | $JQ_BIN -r 'keys[]' | sort | paste -sd, -)

if [ -z "$PORTFOLIO_TICKERS" ] || [ "$PORTFOLIO_TICKERS" == "null" ]; then
  PORTFOLIO_TICKERS="No stocks currently in portfolio."
fi

# 2. Execute Antigravity CLI (agy) and CAPTURE the output
# We explicitly tell it to use its tools to read/write files.
AGY_BIN=$(command -v agy || echo "/usr/local/bin/agy")

$AGY_BIN --prompt "You are a senior financial research agent. Use your 'Buffett Strategic Analyst' skill to perform a Deep Scour of the current portfolio: ($PORTFOLIO_TICKERS) and find bargains.
1. Run the python evaluation and filtering scripts (evaluate_portfolio.py, filter_stocks.py) to fetch real, live data via yfinance. DO NOT use superficial web searches for financial data.
2. Apply a 10-year Discounted Cash Flow (DCF) model of Owner Earnings (FCF) with a 10% discount rate to calculate the Intrinsic Value. Classify companies with negative or erratic cash flows as 'Too Hard' to value.
3. STRICT MANDATE: Exclude all non-peaceful stocks (defense/munitions/tactical surveillance).
4. Persist the identified bargains with their calculated dynamic price intervals (Bargain: 30% margin of safety, Fair, Expensive) using 'POST /bargains/'.
5. Update the knowledge base and active memory, and write the final report. Print 'REPORT_COMPLETE' when finished." --yolo --skip-trust

# 3. Completion
# The agent now handles its own notifications as per the SKILL.md mandate.
echo "Research task initiated. Agent will notify upon completion."
