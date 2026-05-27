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

# Fetch portfolio JSON and handle curl/jq errors gracefully
if PORTFOLIO_JSON=$("$CURL_BIN" -s -f http://localhost:8000/portfolio/holdings 2>/dev/null); then
  PORTFOLIO_TICKERS=$(echo "$PORTFOLIO_JSON" | "$JQ_BIN" -r 'keys[]' 2>/dev/null | sort | paste -sd, -)
else
  PORTFOLIO_TICKERS=""
fi

if [[ -z "$PORTFOLIO_TICKERS" ]] || [[ "$PORTFOLIO_TICKERS" == "null" ]]; then
  PORTFOLIO_TICKERS="No stocks currently in portfolio."
fi

# 2. Execute Antigravity CLI (agy) to perform the financial research
AGY_BIN=$(command -v agy || echo "$USER_HOME/.local/bin/agy")

if ! "$AGY_BIN" --prompt "You are a senior financial research agent. Use your 'Buffett Strategic Analyst' skill to perform a Deep Scour of the current portfolio: ($PORTFOLIO_TICKERS) and find bargains.
1. Run the python evaluation and filtering scripts (evaluate_portfolio.py, filter_stocks.py) to fetch real, live data via yfinance. DO NOT use superficial web searches for financial data.
2. Apply the dynamic valuation strategy (Stable DCF, Reverse DCF implied growth check, or Normalized Mid-Cycle averages) depending on the stock's business category (predictable, hyper-growth, or cyclical).
3. STRICT MANDATE: Exclude all non-peaceful stocks (defense/munitions/tactical surveillance).
4. Persist the identified bargains with their calculated dynamic price intervals (Bargain, Fair, Expensive) using 'POST /bargains/'.
5. Update the knowledge base and active memory, and write the final report. Print 'REPORT_COMPLETE' when finished." --dangerously-skip-permissions; then
  echo "Error: Financial research run failed." >&2
  exit 1
fi

# 3. Trigger notification sequentially using repository virtualenv python binary
echo "Research complete. Triggering daily report notifications..."
if ! "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/agent/notifier.py"; then
  echo "Error: Notification script failed." >&2
  exit 1
fi
