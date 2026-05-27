# Design Specification: Decoupled Cron & Dynamic Stock Valuation

This design spec details two major enhancements to the daily research pipeline:
1. **Decoupling System Notifications from the AI Agent**: Moving `notifier.py` execution from the AI agent prompt to a structured sequential bash pipeline inside `run_daily_research.sh` with robust, non-hardcoded host path fallbacks.
2. **Dynamic Stock Valuation Strategy**: Upgrading the `Buffett Strategic Analyst` skill and financial model script tools to allow classification of stocks and application of tailored valuation frameworks (predictable DCF, hyper-growth Reverse DCF, or mid-cycle multiples).

---

## 1. Decoupled & Robust Cron Pipeline Design

### Current Architecture & Flaws
Previously, the daily cron script `run_daily_research.sh` was configured to delegate execution of `notifier.py` to the AI agent via its prompt. To achieve this, a host-specific absolute python path (`/home/joaosantos/...`) was hardcoded. This was highly brittle, broke local macOS testing, and increased the cognitive load on the AI agent.

### Proposed Architecture
* **Concern Isolation**: The AI agent focuses purely on financial research, KB updates, and database persistence. The shell script handles system execution and notifications.
* **Host Portability**: Absolute home and workspace paths are removed. Paths are dynamically resolved relative to the script directory (`$SCRIPT_DIR`) and the running user's home directory.
* **Cron-Resilient Path Discovery**: We build dynamic home directory and PATH auto-discovery to ensure binaries like `agy`, `curl`, and `jq` are found even under cron's minimal shell environment.

```
┌────────────────────────────────────────────────────────┐
│               run_daily_research.sh                    │
│                                                        │
│  1. Resolve SCRIPT_DIR and USER_HOME                   │
│  2. Build dynamic PATH including Brew/Local            │
│  3. Execute agy CLI (Synchronous Financial Research)   │
│  4. Execute notifier.py via relative venv python       │
└────────────────────────────────────────────────────────┘
```

---

## 2. Dynamic Stock Valuation Strategy

### Philosophy
Warren Buffett and Charlie Munger teach us that different business models require completely different valuation yardsticks. Forcing a standard, 15%-capped CAGR backward-looking DCF on a fabless hyper-growth tech platform like **NVIDIA** leads to erratic valuations or false "Too Hard" classifications. 

We will upgrade the **Buffett Strategic Analyst** framework to classify businesses and select the optimal valuation model.

### Valuation Matrix

| Category | Typical Example | Key Financial Indicators | Valuation Framework | Pricing Boundaries |
| :--- | :--- | :--- | :--- | :--- |
| **1. Mature & Stable** | Apple (AAPL), HP (HPQ), Coca-Cola (KO) | Stable positive FCF, moderate revenue growth (<15%), ROIC > 15% | **Standard 10-Yr FCF DCF** | **Bargain**: Intrinsic - 30%<br>**Fair**: Intrinsic value<br>**Expensive**: Intrinsic + 20% |
| **2. Hyper-Growth / Platform** | NVIDIA (NVDA), Microsoft (MSFT) | Hyper-growth (>15%), asset-light/high-margin, massive ROIC (>25%), strong moats (e.g. CUDA, high switching costs) | **Reverse DCF & Moat Optionality**<br>(Solve for implied growth, then sanity check against TAM and switching costs) | **Bargain**: Current price if implied growth is conservative relative to moat<br>**Fair**: Implied growth is fully priced in<br>**Expensive**: Implied growth requires unrealistic TAM |
| **3. Cyclical / Asset-Heavy** | Intel (INTC), Banks, Energy, Autos | Volatile/erratic cash flows, heavy capital requirements, ROIC < 10% | **Normalized Mid-Cycle Valuation**<br>(Use 5-year average ROIC, book value, and normalized multiples) | **Bargain**: Tangible Book Value<br>**Fair**: Mid-cycle normalized multiple<br>**Expensive**: Multiples > historical 5-year average |

---

## Proposed Changes

### [MODIFY] [run_daily_research.sh](file:///Users/joaosantos/stock-tracker/run_daily_research.sh)
* Add dynamic `$USER_HOME` detection: `USER_HOME="${HOME:-$(cd ~ && pwd)}"`
* Export robust path fallbacks including `/opt/homebrew/bin`, `/usr/local/bin`, and `~/.local/bin`.
* Remove all email/telegram notification execution details from the AI agent prompt.
* Execute `notifier.py` directly using the local virtual environment: `"$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/agent/notifier.py"`.

### [MODIFY] [SKILL.md](file:///Users/joaosantos/stock-tracker/agent/skills/buffett_analyst/SKILL.md)
* Update "Core Mandates" and "Workflows" to instruct the agent to dynamically categorize target stocks (Mature, Hyper-growth, Cyclical).
* Formally detail the dynamic valuation strategies so the agent has explicit instructions on how to evaluate companies like NVIDIA using Reverse DCF or Franchise Value.

### [MODIFY] [data_fetcher.py](file:///Users/joaosantos/stock-tracker/agent/skills/buffett_analyst/scripts/data_fetcher.py)
* Update `StockData` dataclass to hold additional metadata fields like `valuation_methodology` and `implied_growth_rate`.
* Refactor `fetch_data()` or introduce dedicated helpers to support calculating implied growth rates (Reverse DCF) for companies labeled high-growth, as well as normalized multi-year averages for asset-heavy cyclicals.

### [MODIFY] [evaluate_portfolio.py](file:///Users/joaosantos/stock-tracker/agent/skills/buffett_analyst/scripts/evaluate_portfolio.py)
* Align portfolio health checks with dynamic valuations. Companies will no longer be lazily flagged as "Too Hard" simply due to high growth or cyclical FCF; instead, the correct valuation framework will be invoked.

---

## Verification Plan

### Automated Verification
* Run a dry run of the updated `run_daily_research.sh` locally on macOS and verify that it locates all binaries (`agy`, local `python` venv) dynamically without hardcoding.
* Run the python test suite or data fetcher manually on mature stocks (like `AAPL`/`HPQ`) and hyper-growth stocks (like `NVDA`) to ensure the tailored valuation strategies output proper intrinsic bounds.

### Manual Verification
* Deploy to staging/production server under a minimal cron shell simulator to ensure `run_daily_research.sh` executes end-to-end and successfully fires notifications.
