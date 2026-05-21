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
    await update.message.reply_text(f"🔍 Investigating {ticker} through the Buffett Strategic Analyst lens... This may take a minute.")
    
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
        # Assuming run from project root
        with open("knowledge_base/active_memory.md", "r") as f:
            active_memory = f.read()
    except Exception as e:
        logger.warning(f"Could not read active_memory.md: {e}")

    prompt = (
        f"You are the 'Buffett Strategic Analyst'. Investigate '{ticker}' using value investing principles.\n\n"
        f"**Context:**\n"
        f"- {holdings_context}\n"
        f"- **Active Memory (Macro):**\n{active_memory}\n\n"
        f"**Instructions:**\n"
        f"1. Use google_web_search to find latest news, financials (ROIC, Debt/Equity, FCF Yield), and current price for '{ticker}'.\n"
        f"2. Apply the 'Buffett Check': High-quality business? Margin of safety?\n"
        f"3. **STRICT MANDATE:** Verify if the company is 'Peaceful'.\n"
        f"   - STRICTLY EXCLUDE: Companies that directly manufacture weapon systems, munitions, firearms, tactical hardware, military explosives, nuclear weapons, or warships (e.g., Lockheed Martin, Raytheon, Northrop Grumman), AND companies producing specialized software or systems designed specifically for intelligence, espionage, surveillance, warfare, and tactical combat operations (e.g., Palantir).\n"
        f"   - EXPLICITLY ALLOW: Companies producing general-purpose or dual-use technologies (e.g., standard consumer electronics, microchips, GPUs, enterprise software, general search/cloud infrastructure, commercial aviation) even if they have partnerships, research relationships, or general contracts with defense departments (e.g., NVIDIA, Microsoft, Google), unless their direct products are weapons or dedicated combat/espionage systems. If the stock is NOT peaceful according to these exact guidelines, your Action must be 'SELL' or 'AVOID' with a clear warning.\n"
        f"4. Do NOT run any external notification scripts (like notifier.py). Your response will be handled by the caller.\n"
        f"5. Format your response exactly like this:\n\n"
        f"--- TELEGRAM SUMMARY ---\n"
        f"**Target Stock:** {ticker} - $PRICE\n"
        f"**Action:** BUY/HOLD/SELL/AVOID\n"
        f"**Buffett Lens:** 1-2 sentences on quality, moat, and ROIC.\n"
        f"**Rationale:** 1 sentence on current valuation/timing.\n"
        f"========================\n"
        f"**Portfolio Fit:** How this stock complements or conflicts with existing holdings ({holdings_context}).\n"
        f"**Macro Alignment:** How this fits with the trends in Active Memory.\n\n"
        f"--- FULL REPORT ---\n"
        f"[Your deep dive analysis here, including fundamental metrics and 'Peaceful' status check]"
    )
    
    try:
        # Use gemini CLI with --yolo and --skip-trust for autonomous research
        result = subprocess.run(["gemini", "--prompt", prompt, "--yolo", "--skip-trust"], capture_output=True, text=True, timeout=180)
        
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
