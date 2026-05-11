# Stock Portfolio Phase 4: Interactive Bot & Smart Notifications

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a secure Telegram listener for ad-hoc queries, and upgrade the notification system to send Full Reports via Email and strictly-formatted Summaries via Telegram.

**Architecture:** 
- **Listener Service:** Python Telegram Bot using long-polling, running in Docker.
- **Notifications:** `agent/notifier.py` upgraded to support `smtplib` for Emails.
- **Prompt Engineering:** Gemini prompts updated to explicitly format a Telegram-friendly summary and a separate full report body.

---

### Task 11: Upgrade Notification System (Email + Summary)

**Files:**
- Modify: `agent/notifier.py`
- Modify: `.env.example`

- [ ] **Step 1: Add Email Capabilities to Notifier**
Update `agent/notifier.py` to include a `send_email(subject, body)` function using `smtplib` and `email.message.EmailMessage`. Use environment variables (`SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_TO`).

- [ ] **Step 2: Update Telegram Sender to Prevent Halving**
If a Telegram message exceeds 4000 characters, the `send_telegram` function should chunk the message and send it as multiple sequential messages rather than truncating it.

- [ ] **Step 3: Commit**
```bash
git add agent/notifier.py .env.example
git commit -m "feat: add email notifications and fix telegram truncation"
```

---

### Task 12: The Secure Interactive Telegram Listener

**Files:**
- Create: `listener/pyproject.toml`
- Create: `listener/Dockerfile`
- Create: `listener/main.py`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Setup Listener Workspace**
Create `listener/pyproject.toml` with dependencies: `python-telegram-bot` and `requests`. Update the root `pyproject.toml` to include `"listener"` in the workspace.

- [ ] **Step 2: Dockerfile with Gemini CLI**
Create `listener/Dockerfile` using `python:3.11-slim`. Install Node.js and `@google/gemini-cli` via `npm` so the listener container can execute Gemini commands. Install python dependencies via `uv`.

- [ ] **Step 3: Implement Long-Polling Bot**
In `listener/main.py`:
1. Use `ApplicationBuilder` from `telegram.ext`.
2. In the message handler, verify `update.effective_chat.id == os.getenv("TELEGRAM_CHAT_ID")`. Drop if false.
3. Extract the text (the requested stock).
4. Execute `gemini` CLI via `subprocess`. The prompt MUST explicitly demand two sections:
   - A TELEGRAM SUMMARY with exact prices, delimited portfolio vs new recommendations.
   - A FULL REPORT.
5. Parse the CLI output. Send the full output via `notifier.send_email()`. Send the Telegram Summary via `update.message.reply_text()`.

- [ ] **Step 4: Update Docker Compose**
Add the `listener` service to `docker-compose.yml`. Mount `~/.gemini:/root/.gemini` to share the host's authentication token.

- [ ] **Step 5: Commit**
```bash
git add listener/ docker-compose.yml pyproject.toml
git commit -m "feat: implement secure interactive telegram listener"
```
