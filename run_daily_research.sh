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

# 2. Execute Gemini CLI and CAPTURE the output
# We explicitly tell it to use its tools to read/write files.
GEMINI_BIN=$(command -v gemini || echo "$HOME/.nvm/versions/node/v20.20.1/bin/gemini")

$GEMINI_BIN --prompt "You are a senior financial research agent. Use your 'Buffett Strategic Analyst' skill to perform a Deep Scour, evaluate the current portfolio holdings: ($PORTFOLIO_TICKERS). Hunt for bargains, and update the knowledge base. Ensure you update the active memory and write the final report. Print 'REPORT_COMPLETE' when finished." --yolo --skip-trust

# 3. Completion
# The agent now handles its own notifications as per the SKILL.md mandate.
echo "Research task initiated. Agent will notify upon completion."
