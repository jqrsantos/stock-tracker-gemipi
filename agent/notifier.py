import requests
import os
import logging
import glob
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

def send_telegram(message: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        logger.warning("Telegram credentials missing. Skipping notification.")
        return False
        
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        
        chunk_size = 4000
        chunks = [message[i:i+chunk_size] for i in range(0, len(message), chunk_size)]
        
        success = True
        for chunk in chunks:
            payload = {
                "chat_id": chat_id,
                "text": chunk
            }
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code != 200:
                logger.error(f"Telegram API error {res.status_code}: {res.text}")
                success = False
                
        return success
    except Exception as e:
        logger.error(f"Telegram network error: {e}")
        return False

def send_email(subject: str, body: str):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT", "587")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    email_to = os.getenv("EMAIL_TO")
    
    if not all([smtp_server, smtp_user, smtp_password, email_to]):
        logger.warning("Email credentials missing. Skipping email notification.")
        return False
        
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = email_to

        port = int(smtp_port)
        if port == 465:
            server = smtplib.SMTP_SSL(smtp_server, port)
        else:
            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
            
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Email network error: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    from dotenv import load_dotenv
    load_dotenv()
    
    # Find the most recent report
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_dir = os.path.join(base_dir, "knowledge_base", "daily_reports")
    
    # Get list of files
    list_of_files = glob.glob(f"{report_dir}/*.md")
    if not list_of_files:
        logger.warning("No reports found to send.")
    else:
        latest_file = max(list_of_files, key=os.path.getctime)
        with open(latest_file, 'r') as f:
            content = f.read()
        logger.info(f"Sending latest report: {os.path.basename(latest_file)}")
        send_telegram(content)
        send_email(f"Daily Report: {os.path.basename(latest_file)}", content)
