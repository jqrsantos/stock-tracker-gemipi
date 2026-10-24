#!/bin/bash

# Navigate to the project directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Dynamically resolve the running user's home directory
USER_HOME="${HOME:-$(cd ~ && pwd)}"

# Ensure local bin directories are in PATH, especially when run via cron
export PATH="$USER_HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"

CURL_BIN=$(command -v curl || echo "/usr/bin/curl")
JQ_BIN=$(command -v jq || echo "/usr/bin/jq")
API_BASE="${API_URL:-http://localhost:8000}"

# Fetch portfolio JSON and handle curl/jq errors gracefully
if PORTFOLIO_JSON=$("$CURL_BIN" -s -f "$API_BASE/portfolio/holdings" 2>/dev/null); then
  PORTFOLIO_TICKERS=$(echo "$PORTFOLIO_JSON" | "$JQ_BIN" -r 'keys[]' 2>/dev/null | sort | paste -sd, -)
else
  PORTFOLIO_TICKERS=""
fi

if [[ -z "$PORTFOLIO_TICKERS" ]] || [[ "$PORTFOLIO_TICKERS" == "null" ]]; then
  PORTFOLIO_TICKERS="No stocks currently in portfolio."
fi

# 2. Execute Antigravity CLI (agy) to perform the financial research
AGY_BIN=$(command -v agy || echo "$USER_HOME/.local/bin/agy")

if ! "$AGY_BIN" --print-timeout 15m --prompt "You are a senior financial research agent. Use your 'buffett_analyst' skill (agent/skills/buffett_analyst/SKILL.md) to generate today's report.
1. Read knowledge_base/active_memory.md and search the web for the latest geopolitical and global economy news across major economies (US, EU, China, Japan). Update active_memory.md using manage_memory.py.
2. Scout 2-3 high-quality peaceful market opportunities based on recent news catalysts and strong fundamentals (strictly excluding defense/weapons/surveillance).
3. Run 'python3 agent/skills/buffett_analyst/scripts/evaluate_stock.py' for all current portfolio tickers ($PORTFOLIO_TICKERS) and your 2-3 scouted tickers to get their Moat & Financial Performance snapshots.
4. Search recent company news for the portfolio holdings and scouted stocks, and connect their Moat + Financial Performance + Recent News to assess each company (BUY, HOLD, SELL, or AVOID).
5. Record each of today's 2-3 scouted stocks via 'POST $API_BASE/bargains/' (with ticker, name, industry, current_price, currency, rationale).
6. Query 'GET $API_BASE/bargains/performance' to retrieve the Day-1 scouting performance scorecard.
7. Write the complete daily report to knowledge_base/daily_reports/\$(date +%F)-report.md with sections: [MACRO & GEOPOLITICAL BRIEFING], [PORTFOLIO ASSESSMENT], [SCOUTED OPPORTUNITIES], and [SCOUTING PERFORMANCE]. Print 'REPORT_COMPLETE' when finished." --dangerously-skip-permissions; then
  echo "Error: Financial research run failed." >&2
  exit 1
fi

# 3. Trigger email-only notification sequentially using repository virtualenv python binary
echo "Research complete. Sending daily report via email..."
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
  PYTHON_BIN=$(command -v python3)
fi

if ! "$PYTHON_BIN" "$SCRIPT_DIR/agent/notifier.py"; then
  echo "Error: Email notification script failed." >&2
  exit 1
fi
