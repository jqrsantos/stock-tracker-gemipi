import os
import subprocess
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTHORIZED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


async def send_chunked_reply(update: Update, text: str):
    chunk_size = 4000
    text = text.strip() or "No response generated."
    for i in range(0, len(text), chunk_size):
        await update.message.reply_text(text[i : i + chunk_size])


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if chat_id != AUTHORIZED_CHAT_ID:
        logger.warning(f"Unauthorized access from {chat_id}")
        return

    user_input = update.message.text.strip()
    ticker = user_input.upper()
    await update.message.reply_text(
        f"🔍 Evaluating {ticker} (Moat + Financial Performance + Recent News)... This may take a minute."
    )

    # 1. Fetch current holdings for context
    holdings_context = "No holdings data available."
    api_url = os.getenv("API_URL", "http://localhost:8000")
    try:
        holdings_res = requests.get(f"{api_url}/portfolio/holdings", timeout=5)
        if holdings_res.status_code == 200:
            holdings = holdings_res.json()
            if holdings:
                holdings_str = ", ".join([f"{t}: {q}" for t, q in holdings.items()])
                holdings_context = f"Current Open Positions: {holdings_str}"
            else:
                holdings_context = "Portfolio is currently empty (no open positions)."
    except Exception as e:
        logger.warning(f"Could not fetch holdings from {api_url}: {e}")

    # 2. Read active memory for macro context
    active_memory = ""
    try:
        with open("knowledge_base/active_memory.md", "r") as f:
            active_memory = f.read()
    except Exception as e:
        logger.warning(f"Could not read active_memory.md: {e}")

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
        result = subprocess.run(
            ["agy", "--prompt", prompt, "--dangerously-skip-permissions"],
            capture_output=True,
            text=True,
            timeout=180,
        )

        if result.returncode == 0:
            output = result.stdout
            if "--- TELEGRAM RESPONSE ---" in output:
                reply_text = output.split("--- TELEGRAM RESPONSE ---")[1].split("--- END RESPONSE ---")[0].strip()
            else:
                reply_text = output.strip()

            await send_chunked_reply(update, reply_text)
        else:
            logger.error(f"Antigravity CLI (agy) Error: {result.stderr}")
            await update.message.reply_text("❌ An error occurred while generating the evaluation. Please check the server logs.")

    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏱️ The investigation timed out.")
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        await update.message.reply_text("⚠️ An unexpected internal error occurred.")


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not AUTHORIZED_CHAT_ID:
        logger.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return

    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info("Starting Telegram Listener (Telegram-only reply mode)...")
    app.run_polling()


if __name__ == "__main__":
    main()
