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

if ! "$AGY_BIN" --print-timeout 15m --prompt "You are a senior financial research agent. Use your 'Buffett Strategic Analyst' skill to perform a Deep Scour of the current portfolio: ($PORTFOLIO_TICKERS) and find bargains.
1. Perform web searches to identify 5-10 undervalued high-quality compounders, stocks hitting 52-week lows, or sector-specific opportunities (excluding defense/espionage).
2. Combine these dynamically searched tickers with the portfolio tickers.
3. Run engine.py for absolute valuation in parallel passing all these tickers as a comma-separated string with the --csv flag (e.g. 'uv run python agent/skills/buffett_analyst/scripts/engine.py --live --watchlist AAPL,MSFT,HPQ --csv'). This fetches data in parallel and outputs all metrics (Bargain, Fair, Expensive, Category, Methodology, ErrorMsg) synchronously in under 10 seconds. Do NOT write your own sequential python scratch scripts to fetch stock data.
4. Apply the dynamic valuation strategy (Stable DCF, Reverse DCF, or Normalized Mid-Cycle averages) depending on the stock's business category (predictable, hyper-growth, or cyclical). Mandate the 10-Q audit agent for negative FCF.
5. STRICT MANDATE: Exclude all non-peaceful stocks (defense/munitions/tactical surveillance).
6. Persist identified bargains with their calculated dynamic price intervals (Bargain, Fair, Expensive) using 'POST /bargains/'.
7. Update the knowledge base and active memory, and write the final report. Print 'REPORT_COMPLETE' when finished.
8. CRITICAL SYNCHRONICITY INSTRUCTION: When calling run_command, always set WaitMsBeforeAsync to 10000. Since engine.py with --csv runs in parallel, it will complete synchronously in ~6 seconds. Ensure it does not go to the background. Do NOT let commands go to the background or pause/end your turn until the entire report has been written and 'REPORT_COMPLETE' has been printed." --dangerously-skip-permissions; then
  echo "Error: Financial research run failed." >&2
  exit 1
fi

# 3. Trigger notification sequentially using repository virtualenv python binary
echo "Research complete. Triggering daily report notifications..."
if ! "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/agent/notifier.py"; then
  echo "Error: Notification script failed." >&2
  exit 1
fi
