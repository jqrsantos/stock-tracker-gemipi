# agent/notifier.py
import requests
import os
import logging

logger = logging.getLogger(__name__)

def send_telegram(message: str):
    """
    Sends a message via the Telegram Bot API.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        logger.warning("Telegram credentials missing. Skipping notification.")
        return False
        
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        # We truncate to 4096 which is Telegram's limit
        payload = {
            "chat_id": chat_id,
            "text": message[:4000]
        }
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code != 200:
            logger.error(f"Telegram API error {res.status_code}: {res.text}")
            return False
        return True
    except Exception as e:
        logger.error(f"Telegram network error: {e}")
        return False
