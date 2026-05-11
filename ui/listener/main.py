import os
import subprocess
import logging
import smtplib
from email.message import EmailMessage
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTHORIZED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_email(subject, body):
    server_addr = os.getenv("SMTP_SERVER")
    port = os.getenv("SMTP_PORT")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    email_to = os.getenv("EMAIL_TO")
    
    if not all([server_addr, port, user, password, email_to]):
        logger.warning("SMTP credentials missing. Email not sent.")
        return

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = email_to

    try:
        port = int(port)
        if port == 465:
            server = smtplib.SMTP_SSL(server_addr, port)
        else:
            server = smtplib.SMTP(server_addr, port)
            server.starttls()
        server.login(user, password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        logger.error(f"Email failed: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if chat_id != AUTHORIZED_CHAT_ID:
        logger.warning(f"Unauthorized access from {chat_id}")
        return

    ticker = update.message.text.strip().upper()
    await update.message.reply_text(f"🔍 Investigating {ticker}... This may take a minute.")
    
    prompt = (
        f"You are an expert financial analyst investigating '{ticker}'.\n"
        f"1. Use google_web_search to find the latest news, current price, and analyst ratings for '{ticker}'.\n"
        f"2. Format your response exactly like this:\n\n"
        f"--- TELEGRAM SUMMARY ---\n"
        f"**Target Stock:** {ticker} - $PRICE\n"
        f"**Action:** BUY/HOLD/SELL\n"
        f"**Rationale:** 1 sentence.\n"
        f"========================\n"
        f"**Portfolio Context:** Briefly note how this fits with the macro trends from 'knowledge_base/macro_trends.md'.\n\n"
        f"--- FULL REPORT ---\n"
        f"[Your deep dive analysis here]"
    )
    
    try:
        result = subprocess.run(["gemini", prompt, "--yes"], capture_output=True, text=True, timeout=180)
        
        if result.returncode == 0:
            output = result.stdout
            parts = output.split("--- FULL REPORT ---")
            
            summary = parts[0].replace("--- TELEGRAM SUMMARY ---", "").strip()
            full_report = parts[1].strip() if len(parts) > 1 else output
            
            await update.message.reply_text(summary[:4000])
            send_email(f"Stock Investigation: {ticker}", full_report)
        else:
            logger.error(f"Gemini CLI Error: {result.stderr}")
            await update.message.reply_text("❌ An error occurred while generating the report. Please check the server logs.")
            
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
    
    logger.info("Starting Telegram Listener...")
    app.run_polling()

if __name__ == "__main__":
    main()
