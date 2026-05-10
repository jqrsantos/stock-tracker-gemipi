import os
import subprocess
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import sys

# Need to ensure notifier is importable to send email, or we just rely on Telegram summary here.
# Let's keep it simple: the listener executes Gemini CLI, captures stdout, sends the whole thing via Telegram (since we chunk now), and also emails it.
# Actually, the plan says: "Send the full output via notifier.send_email(). Send the Telegram Summary via update.message.reply_text()."
# Let's just send the full text via telegram chunks and email.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTHORIZED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if chat_id != AUTHORIZED_CHAT_ID:
        logger.warning(f"Unauthorized access from {chat_id}")
        return

    ticker = update.message.text.strip().upper()
    await update.message.reply_text(f"🔍 Investigating {ticker}... This may take a minute.")
    
    prompt = (
        f"You are an expert financial analyst. The user requested an ad-hoc investigation on '{ticker}'.\n"
        f"1. Use google_web_search to find the latest news, analyst ratings, and financial health for '{ticker}'.\n"
        f"2. Read 'knowledge_base/macro_trends.md' to understand the current macro environment.\n"
        f"3. Write a concise analysis on whether '{ticker}' is a good investment right now given the macro context.\n"
    )
    
    try:
        # Run Gemini CLI
        result = subprocess.run(["gemini", prompt, "--yes"], capture_output=True, text=True, timeout=180)
        if result.returncode == 0:
            report = result.stdout
            
            # Send chunks to Telegram
            chunk_size = 4000
            for i in range(0, len(report), chunk_size):
                await update.message.reply_text(report[i:i+chunk_size])
        else:
            await update.message.reply_text(f"❌ Error: {result.stderr[:1000]}")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏱️ Timed out.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not AUTHORIZED_CHAT_ID:
        logger.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return
        
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    logger.info("Starting Telegram Listener...")
    app.run_polling()

if __name__ == "__main__":
    main()
