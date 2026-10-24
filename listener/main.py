import os
import sys
import glob
import asyncio
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Resolve repository root
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if not os.path.exists(os.path.join(PROJECT_ROOT, "run_daily_research.sh")):
    PROJECT_ROOT = CURRENT_DIR

AUTHORIZED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Persistent touch keyboard buttons for mobile Telegram UI
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🌅 Run Daily Briefing"), KeyboardButton("🦅 Run Weekly Deep Scour")],
        [KeyboardButton("📊 Watchlist & Status"), KeyboardButton("❓ Help")],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

# Concurrency state for long-running research jobs
job_lock = asyncio.Lock()
current_job: Optional[Dict[str, Any]] = None


def is_authorized(update: Update) -> bool:
    if not AUTHORIZED_CHAT_ID or not update.effective_chat:
        return False
    return str(update.effective_chat.id) == str(AUTHORIZED_CHAT_ID)


async def send_chunked_reply(update: Update, text: str, reply_markup=MAIN_KEYBOARD):
    chunk_size = 4000
    text = text.strip() or "No response generated."
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        is_last = (i + chunk_size) >= len(text)
        await update.message.reply_text(
            chunk,
            reply_markup=reply_markup if is_last else None,
            parse_mode="Markdown" if ("*" in chunk or "`" in chunk) else None,
        )


def get_latest_report_info(subfolder: str) -> str:
    folder = os.path.join(PROJECT_ROOT, "knowledge_base", subfolder)
    if os.path.exists(folder):
        files = sorted(glob.glob(os.path.join(folder, "*.md")), reverse=True)
        if files:
            return os.path.basename(files[0])
    return "None recorded"


async def execute_job_in_background(chat_id: str, bot, job_name: str, script_name: str):
    global current_job
    started_at = datetime.now()
    script_path = os.path.join(PROJECT_ROOT, script_name)
    logger.info(f"Starting background job '{job_name}' via {script_path}")

    try:
        proc = await asyncio.create_subprocess_exec(
            "/bin/bash",
            script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=PROJECT_ROOT,
            env=os.environ.copy(),
        )
        stdout, stderr = await proc.communicate()
        duration_mins = (datetime.now() - started_at).total_seconds() / 60.0

        if proc.returncode == 0:
            logger.info(f"Background job '{job_name}' completed successfully in {duration_mins:.1f}m")
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ **{job_name} Completed!**\n\n"
                    f"⏱️ Duration: *{duration_mins:.1f} minutes*\n"
                    f"📧 Full responsive report & dossier has been sent to your email.\n"
                    f"📊 Check /status or tap **📊 Watchlist & Status** to view updated metrics."
                ),
                reply_markup=MAIN_KEYBOARD,
                parse_mode="Markdown",
            )
        else:
            err_text = stderr.decode("utf-8", errors="replace").strip()
            err_tail = err_text[-400:] if err_text else "No stderr details provided."
            logger.error(f"Job '{job_name}' failed (code {proc.returncode}): {err_tail}")
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    f"❌ **{job_name} Encountered an Error**\n\n"
                    f"⏱️ Duration: *{duration_mins:.1f}m* | Exit Code: `{proc.returncode}`\n\n"
                    f"```\n{err_tail}\n```\n"
                    f"Please check server logs for troubleshooting."
                ),
                reply_markup=MAIN_KEYBOARD,
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.exception(f"Unexpected error running {job_name}: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Internal error running {job_name}: {e}",
            reply_markup=MAIN_KEYBOARD,
        )
    finally:
        async with job_lock:
            current_job = None


async def handle_start_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        logger.warning(f"Unauthorized /start or /help from {update.effective_chat.id if update.effective_chat else 'unknown'}")
        return

    help_msg = (
        "📈 **Buffett Strategic Command Hub**\n\n"
        "Control your stock tracker on the go using the touch buttons below or slash commands:\n\n"
        "• 🌅 **Run Daily Briefing** (`/daily`)\n"
        "  Scans global macro news, audits open positions, scouts 2-3 dip opportunities, updates active memory, and emails your daily briefing (~3-5 mins).\n\n"
        "• 🦅 **Run Weekly Deep Scour** (`/weekly`)\n"
        "  Dispatches the multi-agent swarm with Gemini Argon Lead Orchestrator to forensic-audit candidate stocks, prune the watchlist, set Dip Buying Zones, and deliver your weekend dossier (~15-30 mins).\n\n"
        "• 📊 **Watchlist & Status** (`/status`)\n"
        "  View active background tasks, current high-conviction picks, win rates, and post-alert dip returns.\n\n"
        "• 🔍 **Single Stock Evaluation**\n"
        "  Type any ticker symbol (e.g. `NOW`, `AAPL`, `MSFT`) to run an immediate Moat + Financial Snapshot + News analysis."
    )
    await update.message.reply_text(help_msg, reply_markup=MAIN_KEYBOARD, parse_mode="Markdown")


async def handle_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        logger.warning(f"Unauthorized /daily from {update.effective_chat.id if update.effective_chat else 'unknown'}")
        return

    global current_job
    async with job_lock:
        if current_job is not None:
            elapsed = (datetime.now() - current_job["started_at"]).total_seconds() / 60.0
            await update.message.reply_text(
                f"⚠️ A job is already in progress:\n**{current_job['name']}** (running for {elapsed:.1f}m).\n\n"
                "Please wait for it to finish before launching another research run.",
                reply_markup=MAIN_KEYBOARD,
                parse_mode="Markdown",
            )
            return

        current_job = {"name": "Daily Market Briefing", "started_at": datetime.now()}

    chat_id = str(update.effective_chat.id)
    await update.message.reply_text(
        "🚀 **Starting Daily Market Briefing...**\n\n"
        "• Scanning macro & geopolitical news (US, EU, China, Japan)\n"
        "• Evaluating portfolio holdings & scouting dip candidates\n"
        "• Updating active memory and dispatching email report\n\n"
        "⏳ *Estimated duration: ~3-5 minutes. I will ping you here once complete!*",
        reply_markup=MAIN_KEYBOARD,
        parse_mode="Markdown",
    )

    asyncio.create_task(
        execute_job_in_background(chat_id, context.bot, "Daily Market Briefing", "run_daily_research.sh")
    )


async def handle_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        logger.warning(f"Unauthorized /weekly from {update.effective_chat.id if update.effective_chat else 'unknown'}")
        return

    global current_job
    async with job_lock:
        if current_job is not None:
            elapsed = (datetime.now() - current_job["started_at"]).total_seconds() / 60.0
            await update.message.reply_text(
                f"⚠️ A job is already in progress:\n**{current_job['name']}** (running for {elapsed:.1f}m).\n\n"
                "Please wait for it to finish before launching another research run.",
                reply_markup=MAIN_KEYBOARD,
                parse_mode="Markdown",
            )
            return

        current_job = {"name": "Weekly Deep Scour Swarm", "started_at": datetime.now()}

    chat_id = str(update.effective_chat.id)
    await update.message.reply_text(
        "🦅 **Launching Weekly Deep Scour Swarm & Watchlist Audit!**\n\n"
        "• **Lead Orchestrator:** Gemini Argon (Maximum Reasoning Effort)\n"
        "• **Investigative Swarm:** SEC Filings Investigator, Moat Threat Analyst, Catalyst Scout\n"
        "• **Objective:** Audit all tracked bargain stocks, prune broken theses, set Buying Zones, and deliver the weekend email dossier.\n\n"
        "⏳ *Estimated duration: ~15-30 minutes. You can safely close Telegram—I will notify you the moment it finishes!*",
        reply_markup=MAIN_KEYBOARD,
        parse_mode="Markdown",
    )

    asyncio.create_task(
        execute_job_in_background(chat_id, context.bot, "Weekly Deep Scour Swarm", "run_weekly_deep_scour.sh")
    )


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        logger.warning(f"Unauthorized /status from {update.effective_chat.id if update.effective_chat else 'unknown'}")
        return

    # 1. Background job status
    if current_job is not None:
        elapsed = (datetime.now() - current_job["started_at"]).total_seconds() / 60.0
        job_status_line = f"⏳ **Running:** *{current_job['name']}* ({elapsed:.1f}m elapsed)"
    else:
        job_status_line = "🟢 **Idle** (Ready for jobs)"

    # 2. Scouting watchlist metrics from API
    watchlist_text = "Could not fetch watchlist metrics."
    try:
        res = requests.get(f"{API_URL}/bargains/performance", timeout=8)
        if res.status_code == 200:
            data = res.json()
            summary = data.get("summary", {})
            picks = data.get("picks", [])

            active_picks = [p["ticker"] for p in picks if p.get("status", "ACTIVE") == "ACTIVE"]
            active_str = ", ".join(active_picks) if active_picks else "None"

            best = summary.get("best_pick")
            best_str = f"{best['ticker']} ({best['return_pct']:+.1f}%)" if best else "N/A"

            watchlist_text = (
                f"• Total Tracked: `{summary.get('total_scouted', 0)}`\n"
                f"• Active Conviction: `{summary.get('active_count', len(active_picks))}` ({active_str})\n"
                f"• Dismissed Archive: `{summary.get('dismissed_count', 0)}`\n"
                f"• Win Rate: `{summary.get('win_rate_pct', 0.0):.1f}%` | Avg Alert Return: `{summary.get('avg_return_pct', 0.0):+.2f}%`\n"
                f"• Best Pick: `{best_str}`"
            )
    except Exception as e:
        watchlist_text = f"API unreachable: {e}"

    # 3. Latest reports
    latest_daily = get_latest_report_info("daily_reports")
    latest_weekly = get_latest_report_info("weekly_reports")

    status_msg = (
        "📊 **Stock Tracker — System Status**\n\n"
        f"**Engine Status:**\n{job_status_line}\n\n"
        f"**Watchlist & Scouting Performance:**\n{watchlist_text}\n\n"
        "**Latest Generated Reports:**\n"
        f"• Daily Briefing: `{latest_daily}`\n"
        f"• Weekly Audit: `{latest_weekly}`"
    )
    await update.message.reply_text(status_msg, reply_markup=MAIN_KEYBOARD, parse_mode="Markdown")


async def evaluate_single_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    ticker = user_input.upper()

    await update.message.reply_text(
        f"🔍 Evaluating **{ticker}** (Moat + Financial Performance + Recent News)... This may take a minute.",
        reply_markup=MAIN_KEYBOARD,
        parse_mode="Markdown",
    )

    # 1. Fetch current holdings for context
    holdings_context = "No holdings data available."
    try:
        holdings_res = requests.get(f"{API_URL}/portfolio/holdings", timeout=5)
        if holdings_res.status_code == 200:
            holdings = holdings_res.json()
            if holdings:
                holdings_str = ", ".join([f"{t}: {q}" for t, q in holdings.items()])
                holdings_context = f"Current Open Positions: {holdings_str}"
            else:
                holdings_context = "Portfolio is currently empty (no open positions)."
    except Exception as e:
        logger.warning(f"Could not fetch holdings from {API_URL}: {e}")

    # 2. Read active memory for macro context
    active_memory = ""
    memory_path = os.path.join(PROJECT_ROOT, "knowledge_base/active_memory.md")
    try:
        with open(memory_path, "r") as f:
            active_memory = f.read()
    except Exception as e:
        logger.warning(f"Could not read active_memory.md at {memory_path}: {e}")

    prompt = (
        f"You are the 'Buffett Strategic Analyst'. Evaluate '{ticker}' by connecting its competitive moat, "
        f"financial performance snapshot, and recent company/macro news.\n\n"
        f"**Context:**\n"
        f"- {holdings_context}\n"
        f"- **Active Memory (Macro & Geopolitics):**\n{active_memory}\n\n"
        f"**Instructions:**\n"
        f"1. Run `python3 agent/skills/buffett_analyst/scripts/evaluate_stock.py {ticker}` to get its financial performance snapshot "
        f"(Gross/Operating Margins, ROIC, ROE, Debt/Equity, FCF Yield & Trend, Revenue Growth, and P/E vs 5Y Average).\n"
        f"2. Perform a web search for recent news, earnings catalysts, and competitive developments for '{ticker}'.\n"
        f"3. **STRICT PEACEFUL MANDATE:** Exclude companies manufacturing weapons, munitions, defense hardware, or dedicated military/espionage surveillance systems (e.g., Lockheed Martin, Raytheon, Palantir). Dual-use commercial tech (e.g., Apple, Microsoft, NVIDIA) is allowed. If non-peaceful, Action MUST be AVOID/SELL.\n"
        f"4. Connect your findings into a clear assessment without inventing rigid DCF price bounds:\n"
        f"   - Assess the **Moat** (Switching Costs, Brand, Network Effects, Cost/Tech Advantage) backed by margins & ROIC.\n"
        f"   - Assess **Financial Health & Relative Valuation** (balance sheet D/E, FCF generation, growth, and current P/E vs 5-yr average).\n"
        f"   - Connect with **Recent News & Global Macro**.\n"
        f"5. Do NOT run any external notification scripts. Format your response between the markers below:\n\n"
        f"--- TELEGRAM RESPONSE ---\n"
        f"🎯 **{ticker} — [Company Name]** ([Current Price] [Currency])\n"
        f"**Verdict:** BUY / HOLD / SELL / AVOID\n\n"
        f"🏰 **Moat Assessment:** [2-3 sentences on competitive advantage & margin/ROIC durability]\n\n"
        f"📊 **Financial Snapshot:**\n"
        f"• Margins (Gross / Op): [X% / Y%]\n"
        f"• ROIC / ROE: [X% / Y%]\n"
        f"• Balance Sheet & Cash: D/E [X] | FCF Yield [Y%] ([Trend])\n"
        f"• Growth & Valuation: Rev YoY [X%] | P/E [X] vs 5Y Avg [Y]\n\n"
        f"📰 **News & Macro Synthesis:** [How recent company news and global macro trends connect to the numbers]\n\n"
        f"💼 **Portfolio Fit:** [How it fits with {holdings_context}]\n"
        f"--- END RESPONSE ---"
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            "agy",
            "--prompt",
            prompt,
            "--dangerously-skip-permissions",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=PROJECT_ROOT,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=240)
            if proc.returncode == 0:
                output = stdout.decode("utf-8", errors="replace")
                if "--- TELEGRAM RESPONSE ---" in output:
                    reply_text = (
                        output.split("--- TELEGRAM RESPONSE ---")[1]
                        .split("--- END RESPONSE ---")[0]
                        .strip()
                    )
                else:
                    reply_text = output.strip()
                await send_chunked_reply(update, reply_text, reply_markup=MAIN_KEYBOARD)
            else:
                err_msg = stderr.decode("utf-8", errors="replace")
                logger.error(f"Antigravity CLI (agy) Error: {err_msg}")
                await update.message.reply_text(
                    "❌ An error occurred while generating the evaluation. Please check server logs.",
                    reply_markup=MAIN_KEYBOARD,
                )
        except asyncio.TimeoutError:
            proc.kill()
            await update.message.reply_text("⏱️ The investigation timed out.", reply_markup=MAIN_KEYBOARD)
    except Exception as e:
        logger.error(f"Unexpected Error during single stock evaluation: {e}")
        await update.message.reply_text(f"⚠️ Internal error: {e}", reply_markup=MAIN_KEYBOARD)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        logger.warning(f"Unauthorized text message from {update.effective_chat.id if update.effective_chat else 'unknown'}")
        return

    text = update.message.text.strip()
    # Route touch keyboard buttons
    if text == "🌅 Run Daily Briefing":
        await handle_daily(update, context)
    elif text == "🦅 Run Weekly Deep Scour":
        await handle_weekly(update, context)
    elif text == "📊 Watchlist & Status":
        await handle_status(update, context)
    elif text == "❓ Help":
        await handle_start_help(update, context)
    else:
        await evaluate_single_stock(update, context)


async def post_init(application):
    try:
        await application.bot.set_my_commands(
            [
                BotCommand("daily", "Run daily market briefing & email report"),
                BotCommand("weekly", "Run weekly deep scour swarm & audit watchlist"),
                BotCommand("status", "Show active watchlist, dip scorecard & job status"),
                BotCommand("help", "Show commands & mobile instructions"),
            ]
        )
        logger.info("Bot commands successfully registered with Telegram.")
    except Exception as e:
        logger.warning(f"Could not register Telegram bot commands: {e}")


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not AUTHORIZED_CHAT_ID:
        logger.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables.")
        return

    app = ApplicationBuilder().token(token).post_init(post_init).build()

    # Slash command handlers
    app.add_handler(CommandHandler("start", handle_start_help))
    app.add_handler(CommandHandler("help", handle_start_help))
    app.add_handler(CommandHandler("daily", handle_daily))
    app.add_handler(CommandHandler("weekly", handle_weekly))
    app.add_handler(CommandHandler("status", handle_status))

    # Text message handler (routes touch buttons & stock tickers)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text_message))

    logger.info("Starting Telegram Command Hub with interactive buttons and background runners...")
    app.run_polling()


if __name__ == "__main__":
    main()
