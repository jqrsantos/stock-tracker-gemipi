# Peaceful Investing Filters and Telegram Bot Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the Telegram bot portfolio fetching NameError bug and refine the "peaceful" stock exclusion filter to allow dual-use technology companies (e.g. NVIDIA, Microsoft, Google) while continuing to strictly exclude direct weapons manufacturers (e.g. Lockheed Martin, Raytheon) and dedicated espionage/combat software providers (e.g. Palantir).

**Architecture:** We will import the `requests` library in the Telegram bot main entrypoint to resolve the runtime crash. We will then rewrite the "Peaceful" mandate prompts and documentation in both the Telegram bot script and the analyst skill markdown files to draw clear, exact boundaries for AI reasoning on stock exclusions.

**Tech Stack:** Python 3, python-telegram-bot, requests, Markdown, Git

---

### Task 1: Fix Telegram Bot Portfolio Fetching Bug (Import Missing)

**Files:**
- Modify: `listener/main.py:1-10`

- [ ] **Step 1: Write a failing verification check**
  We will verify that importing `requests` within the `listener/main` module fails because it hasn't been imported yet.
  
  Run the following verification command:
  ```bash
  python3 -c "import sys; sys.path.append('listener'); import main; print(main.requests)"
  ```
  Expected output:
  `AttributeError: module 'main' has no attribute 'requests'`

- [ ] **Step 2: Add `requests` import to `listener/main.py`**
  Modify [listener/main.py](file:///Users/joaosantos/stock-tracker/listener/main.py) to import the `requests` library at the top of the file.
  
  Replace lines 1-10:
  ```python
  import os
  import subprocess
  import logging
  import smtplib
  from email.message import EmailMessage
  from telegram import Update
  from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
  
  logging.basicConfig(level=logging.INFO)
  logger = logging.getLogger(__name__)
  ```
  
  With:
  ```python
  import os
  import subprocess
  import logging
  import smtplib
  import requests
  from email.message import EmailMessage
  from telegram import Update
  from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
  
  logging.basicConfig(level=logging.INFO)
  logger = logging.getLogger(__name__)
  ```

- [ ] **Step 3: Run verification check to verify it passes**
  Run the verification command:
  ```bash
  python3 -c "import sys; sys.path.append('listener'); import main; print(main.requests)"
  ```
  Expected output:
  `<module 'requests' from ...>` (indicating requests is successfully imported)

- [ ] **Step 4: Verify syntax and compile status**
  Run compilation check to ensure there are no other syntax issues in `listener/main.py`:
  ```bash
  python3 -m py_compile listener/main.py
  ```
  Expected output: Exit code 0 (no output means successful compilation)

- [ ] **Step 5: Commit changes**
  Run:
  ```bash
  git add listener/main.py
  git commit -m "fix(listener): import requests to fix portfolio holdings fetch NameError"
  ```

---

### Task 2: Refine Peaceful Investing Mandate inside Telegram Prompt

**Files:**
- Modify: `listener/main.py:80-99`

- [ ] **Step 1: Update the prompt definition in `listener/main.py`**
  Modify [listener/main.py](file:///Users/joaosantos/stock-tracker/listener/main.py) to update the `prompt` string in the `handle_message` function (around lines 82-87).
  
  Replace:
  ```python
          f"3. **STRICT MANDATE:** Verify if the company is 'Peaceful'. Strictly exclude companies that create 'killing products directly' or provide mission-critical combat technology (e.g., Lockheed Martin, Palantir, Raytheon). If the stock is NOT peaceful, your Action must be 'SELL' or 'AVOID' with a clear warning.\n"
  ```
  
  With:
  ```python
          f"3. **STRICT MANDATE:** Verify if the company is 'Peaceful'.\n"
          f"   - STRICTLY EXCLUDE: Companies that directly manufacture weapon systems, munitions, firearms, tactical hardware, military explosives, nuclear weapons, or warships (e.g., Lockheed Martin, Raytheon, Northrop Grumman), AND companies producing specialized software or systems designed specifically for intelligence, espionage, surveillance, warfare, and tactical combat operations (e.g., Palantir).\n"
          f"   - EXPLICITLY ALLOW: Companies producing general-purpose or dual-use technologies (e.g., standard consumer electronics, microchips, GPUs, enterprise software, general search/cloud infrastructure, commercial aviation) even if they have partnerships, research relationships, or general contracts with defense departments (e.g., NVIDIA, Microsoft, Google), unless their direct products are weapons or dedicated combat/espionage systems. If the stock is NOT peaceful according to these exact guidelines, your Action must be 'SELL' or 'AVOID' with a clear warning.\n"
  ```

- [ ] **Step 2: Verify syntax and compile status**
  Run compilation check to ensure there are no syntax errors in `listener/main.py`:
  ```bash
  python3 -m py_compile listener/main.py
  ```
  Expected output: Exit status 0

- [ ] **Step 3: Commit changes**
  Run:
  ```bash
  git add listener/main.py
  git commit -m "feat(listener): refine Peaceful Investing mandate in telegram bot prompt"
  ```

---

### Task 3: Refine Core Mandates inside Buffett Strategic Analyst Skill

**Files:**
- Modify: `agent/skills/buffett_analyst/SKILL.md:1-15`

- [ ] **Step 1: Update `agent/skills/buffett_analyst/SKILL.md` peaceful investing criteria**
  Modify [SKILL.md](file:///Users/joaosantos/stock-tracker/agent/skills/buffett_analyst/SKILL.md) to align the **Core Mandates** with our refined criteria.
  
  Replace lines 9-15:
  ```markdown
  1.  **"Peaceful" Investing:** Strictly exclude all "War-oriented" stocks. This includes companies that create "killing products directly" or provide mission-critical technology for combat (e.g., Lockheed Martin, Palantir, Northrop Grumman, Raytheon). We do not profit from products designed for conflict or destruction.
  2.  **Quality First:** Prioritize businesses with high ROIC (>15%), strong competitive moats (Brand, Switching Costs, Network Effects), and robust balance sheets (Debt/Equity < 1.0).
  3.  **Margin of Safety:** Never recommend a stock without a clear margin of safety. Valuation must be attractive relative to intrinsic value (Owner Earnings/FCF).
  ```
  
  With:
  ```markdown
  1.  **"Peaceful" Investing:** Strictly exclude all "War-oriented" stocks.
      *   **Strictly Exclude:** Companies that directly manufacture weapon systems, munitions, firearms, tactical hardware, military explosives, nuclear weapons, or warships (e.g., Lockheed Martin, Raytheon, Northrop Grumman), AND companies producing specialized software or systems designed specifically for intelligence, espionage, surveillance, warfare, and tactical combat operations (e.g., Palantir). We do not profit from products designed for conflict or destruction.
      *   **Explicitly Allow:** Companies producing general-purpose or dual-use technologies (e.g., standard consumer electronics, microchips, GPUs, enterprise software, general search/cloud infrastructure, commercial aviation) even if they have partnerships, research relationships, or general contracts with defense departments (e.g., NVIDIA, Microsoft, Google), unless their direct products are weapons or dedicated combat/espionage systems.
  2.  **Quality First:** Prioritize businesses with high ROIC (>15%), strong competitive moats (Brand, Switching Costs, Network Effects), and robust balance sheets (Debt/Equity < 1.0).
  3.  **Margin of Safety:** Never recommend a stock without a clear margin of safety. Valuation must be attractive relative to intrinsic value (Owner Earnings/FCF).
  ```

- [ ] **Step 2: Commit changes**
  Run:
  ```bash
  git add agent/skills/buffett_analyst/SKILL.md
  git commit -m "docs(buffett): refine Peaceful Investing mandate in core skill definition"
  ```
