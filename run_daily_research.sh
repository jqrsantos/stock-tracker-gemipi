#!/bin/bash

cd "$(dirname "$0")"

# 1. Fetch current unique tickers from the API (requires jq to be installed on Pi)
PORTFOLIO_TICKERS=$(curl -s http://localhost:8000/transactions/ | jq -r '.[].ticker' | sort | uniq | paste -sd, -)

if [ -z "$PORTFOLIO_TICKERS" ] || [ "$PORTFOLIO_TICKERS" == "null" ]; then
  PORTFOLIO_TICKERS="No stocks currently in portfolio."
fi

# 2. Execute Gemini CLI
gemini "You are an expert financial analyst. 

1. **Portfolio Review:** Using google_web_search, fetch today's top financial news and analyst ratings for the following stocks currently in my portfolio: $PORTFOLIO_TICKERS. Provide explicit SELL, HOLD, or BUY targets for each based on current momentum and fundamentals.
2. **Macro Economics:** Search for the latest global macro economic data (Inflation, Fed Rates, Sector rotation). 
   - Read the existing context in 'knowledge_base/macro_trends.md'.
   - Compare today's macro news against the existing context to identify ongoing trends.
3. **Promising Opportunities:** Search the web for 2-3 NEW stocks outside of my portfolio that look highly promising right now based on the macro environment. Provide a brief thesis for each.
4. **Knowledge Base Update:** Append today's Macro summary to 'knowledge_base/macro_trends.md' (append only, do not overwrite history).
5. **Report Generation:** Save the complete Daily Report (Portfolio review, Macro analysis, Promising stocks) as a markdown file in 'knowledge_base/daily_reports/$(date +%Y-%m-%d)-report.md'.
6. **Notification:** Finally, run 'uv run python agent/notifier.py' to send the report to Telegram." --yes
