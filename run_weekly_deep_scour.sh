#!/bin/bash

# Navigate to project directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Dynamically resolve the running user's home directory
USER_HOME="${HOME:-$(cd ~ && pwd)}"

# Ensure local bin directories are in PATH
export PATH="$USER_HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"

CURL_BIN=$(command -v curl || echo "/usr/bin/curl")
JQ_BIN=$(command -v jq || echo "/usr/bin/jq")

echo "========================================================"
echo " 🚀 INITIATING WEEKLY DEEP SCOUR SWARM & WATCHLIST AUDIT"
echo "========================================================"

# Fetch current unique scouted tickers from the API
if BARGAINS_JSON=$("$CURL_BIN" -s -f http://localhost:8000/bargains/ 2>/dev/null); then
  SCOUTED_TICKERS=$(echo "$BARGAINS_JSON" | "$JQ_BIN" -r '.[].ticker' 2>/dev/null | sort -u | paste -sd, -)
else
  SCOUTED_TICKERS=""
fi

if [[ -z "$SCOUTED_TICKERS" ]] || [[ "$SCOUTED_TICKERS" == "null" ]]; then
  SCOUTED_TICKERS="NOW,ADBE,ASML,MSFT,GOOGL"
  echo "No active bargains found in DB. Falling back to key watchlist: $SCOUTED_TICKERS"
else
  echo "Found tracked candidate tickers to audit: $SCOUTED_TICKERS"
fi

# Execute Antigravity CLI (agy) with high-reasoning Gemini Argon
AGY_BIN=$(command -v agy || echo "$USER_HOME/.local/bin/agy")

mkdir -p knowledge_base/weekly_reports

PROMPT="You are the Lead Forensic Investment Auditor using the 'deep_scour_swarm' skill (agent/skills/deep_scour_swarm/SKILL.md).
Operate with MAXIMUM REASONING EFFORT (Gemini Argon). Conduct a comprehensive weekly research audit on the following tracked candidate stocks: ($SCOUTED_TICKERS).

1. Retrieve candidate data from 'GET http://localhost:8000/bargains/' and portfolio positions from 'GET http://localhost:8000/portfolio/holdings'.
2. For each tracked stock, dispatch a parallel 3-agent investigative swarm:
   - 'sec_filings_investigator': 10-K/10-Q accounting forensics, organic revenue vs acquisitions, SBC as % of revenue, debt maturity schedule, CapEx vs Depreciation.
   - 'moat_threat_analyst': Moat verification, pricing power proof, 5-year competitive counter-thesis & disruption vectors, customer churn.
   - 'catalyst_risk_scout': Regulatory & legal overhangs, customer concentration (>10%), macro sensitivities, upcoming quarterly catalysts.
3. Review all findings with deep critical thinking. Invert assumptions. Decide for each stock whether it is:
   - 'ACTIVE' (High Conviction, durable moat, clean accounting): Establish an optimal Buying Zone / Dip Target.
   - 'DISMISSED' (Broken thesis, structural disruption, excessive leverage, or deceptive accounting): Formulate an explicit, punchy dismissal reason.
4. For every audited stock, update its status in the database:
   POST http://localhost:8000/bargains/{ticker}/status
   Payload: {\"status\": \"ACTIVE\" or \"DISMISSED\", \"dismissal_reason\": \"...\", \"deep_dossier\": \"...\"}
5. Query 'GET http://localhost:8000/bargains/performance' to analyze post-alert price action and dip opportunities (highlighting cases like NOW where waiting for post-alert weakness produced peak returns).
6. Compile the complete dossier into 'knowledge_base/weekly_reports/\$(date +%F)-weekly-audit.md' with:
   - ## [EXECUTIVE WATCHLIST PRUNING]
   - ## [DIP OPPORTUNITY SCORECARD]
   - ## [DEEP COMPANY AUDITS]
Print 'WEEKLY_AUDIT_COMPLETE' when finished."

echo "Dispatching 3-agent research swarm via Antigravity CLI..."
if ! "$AGY_BIN" --print-timeout 45m --prompt "$PROMPT" --dangerously-skip-permissions; then
  echo "Error: Weekly deep scour swarm failed." >&2
  exit 1
fi

echo "Weekly research complete. Triggering dedicated weekly email dossier..."
if ! "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/agent/notifier.py" --weekly; then
  echo "Error: Weekly notification script failed." >&2
  exit 1
fi

echo "✅ Weekly deep scour audit successfully completed and emailed."
