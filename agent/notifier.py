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

import markdown
import re

def extract_tldr(markdown_text: str) -> str:
    """
    Extracts key highlights from the report to create a concise TL;DR block.
    """
    highlights = []
    # Look for GLOBAL NARRATIVE highlights or key sentences
    narrative_section = re.search(r"## \[GLOBAL NARRATIVE\]\s*(.*?)(?=##|$)", markdown_text, re.DOTALL)
    if narrative_section:
        text = narrative_section.group(1).strip()
        sentences = [s.strip() + "." for s in text.split(".") if len(s.strip()) > 10]
        highlights.extend(sentences[:2])
    
    # Look for Bargain Radar picks
    radar_section = re.search(r"## \[BARGAIN RADAR\]\s*(.*?)(?=##|$)", markdown_text, re.DOTALL)
    if radar_section:
        picks = re.findall(r"\d+\.\s+\*\*([A-Z]+)\b", radar_section.group(1))
        if picks:
            highlights.append(f"Highlighted moated bargains: {', '.join(picks)}")
            
    if not highlights:
        highlights = ["Fed rate decisions & energy supply shocks continue to drive macro trends.", "Portfolio evaluated for fundamental strengths & ROIC health."]
        
    li_items = "".join([f"<li style='margin-bottom: 6px;'>{item}</li>" for item in highlights])
    return f"""
    <div style="background: #f8fafc; border-left: 4px solid #3b82f6; border-radius: 4px; padding: 16px; margin-bottom: 24px;">
      <h3 style="margin: 0 0 8px 0; font-size: 0.95rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #1e293b;">⚡ Daily TL;DR Digest</h3>
      <ul style="margin: 0; padding-left: 20px; font-size: 0.875rem; color: #475569;">
        {li_items}
      </ul>
    </div>
    """

def format_stock_cards(html_content: str) -> str:
    """
    Parses generated stock metrics blocks into separate compact visual cards with left border accents.
    """
    # Matches:
    # ### Ticker (Company Name) - STATUS
    # * **ROIC**: value
    # * **Debt/Equity**: value
    # * **FCF Yield**: value
    # * **Valuation**: value
    # Supports optional bullet points (* or -), optional bold tags (**), and spaces/newlines.
    stock_pattern = r'<h3>([A-Z0-9\-\.]+)\s*\((.*?)\)\s*-\s*(STRONG BUY|STRONG HOLD|STRONG SELL|BUY|HOLD|SELL)<\/h3>\s*<ul>\s*<li>(?:<strong>)?ROIC(?:<\/strong>)?:?\s*(.*?)<\/li>\s*<li>(?:<strong>)?Debt/Equity(?:<\/strong>)?:?\s*(.*?)<\/li>\s*<li>(?:<strong>)?FCF Yield(?:<\/strong>)?:?\s*(.*?)<\/li>\s*<li>(?:<strong>)?Valuation(?:<\/strong>)?:?\s*(.*?)<\/li>\s*<\/ul>'
    
    def replace_with_card(match):
        ticker = match.group(1).strip()
        name = match.group(2).strip()
        status = match.group(3).upper()
        roic = match.group(4).strip()
        de = match.group(5).strip()
        fcf = match.group(6).strip()
        val = match.group(7).strip()
        
        # Color mapping
        border_color = "#3b82f6"  # Blue default
        bg_status = "#f1f5f9"
        text_status = "#475569"
        
        if "BUY" in status:
            border_color = "#10b981"  # Green
            bg_status = "#ecfdf5"
            text_status = "#059669"
        elif "SELL" in status:
            border_color = "#ef4444"  # Red
            bg_status = "#fef2f2"
            text_status = "#ef4444"
        elif "HOLD" in status:
            border_color = "#d97706"  # Amber
            bg_status = "#fffbeb"
            text_status = "#d97706"
            
        return f"""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid {border_color}; border-radius: 8px; padding: 18px 22px; margin-bottom: 28px; max-width: 360px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div>
              <h3 style="margin: 0; font-size: 1.15rem; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">{ticker}</h3>
              <span style="font-size: 0.75rem; color: #64748b; font-weight: 500;">{name}</span>
            </div>
            <span style="background: {bg_status}; color: {text_status}; padding: 4px 10px; border-radius: 100px; font-size: 0.72rem; font-weight: 800; letter-spacing: 0.05em; text-transform: uppercase;">{status}</span>
          </div>
          
          <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem; line-height: 1.4;">
            <tr>
              <td style="padding: 5px 0; border-bottom: 1px dashed #f1f5f9; color: #64748b; text-align: left;">ROIC</td>
              <td style="padding: 5px 0; border-bottom: 1px dashed #f1f5f9; text-align: right; font-weight: 700; color: #0f172a;">{roic}</td>
            </tr>
            <tr>
              <td style="padding: 5px 0; border-bottom: 1px dashed #f1f5f9; color: #64748b; text-align: left;">Debt/Equity</td>
              <td style="padding: 5px 0; border-bottom: 1px dashed #f1f5f9; text-align: right; font-weight: 700; color: #0f172a;">{de}</td>
            </tr>
            <tr>
              <td style="padding: 5px 0; border-bottom: 1px dashed #f1f5f9; color: #64748b; text-align: left;">FCF Yield</td>
              <td style="padding: 5px 0; border-bottom: 1px dashed #f1f5f9; text-align: right; font-weight: 700; color: #0f172a;">{fcf}</td>
            </tr>
            <tr>
              <td style="padding: 5px 0; color: #64748b; text-align: left;">Valuation</td>
              <td style="padding: 5px 0; text-align: right; font-weight: 700; color: {border_color};">{val}</td>
            </tr>
          </table>
        </div>
        """
    return re.sub(stock_pattern, replace_with_card, html_content, flags=re.DOTALL)

def build_html_body(subject: str, markdown_content: str) -> str:
    """
    Converts report markdown into a beautifully designed HTML document.
    """
    tldr_html = extract_tldr(markdown_content)
    
    # Parse markdown using tables extension
    raw_html = markdown.markdown(markdown_content, extensions=['tables'])
    
    # Style standard elements generated by markdown parser
    styled_html = raw_html
    styled_html = styled_html.replace("<table>", '<table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.875rem; text-align: left;">')
    styled_html = styled_html.replace("<thead>", '<thead style="background: #f8fafc; color: #475569; font-weight: 600; border-bottom: 2px solid #e2e8f0;">')
    styled_html = styled_html.replace("<th>", '<th style="padding: 10px 12px; border-bottom: 2px solid #e2e8f0;">')
    styled_html = styled_html.replace("<td>", '<td style="padding: 10px 12px; border-bottom: 1px solid #f1f5f9;">')
    
    # Bold and styling alerts
    styled_html = styled_html.replace("<strong>BUY</strong>", '<span style="background: #ecfdf5; color: #10b981; padding: 2px 6px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">BUY</span>')
    styled_html = styled_html.replace("<strong>SELL</strong>", '<span style="background: #fef2f2; color: #dc2626; padding: 2px 6px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">SELL</span>')
    styled_html = styled_html.replace("<strong>HOLD</strong>", '<span style="background: #fffbeb; color: #d97706; padding: 2px 6px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">HOLD</span>')
    styled_html = styled_html.replace("<strong>BULLISH</strong>", '<span style="background: #ecfdf5; color: #10b981; padding: 2px 6px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">BULLISH</span>')
    styled_html = styled_html.replace("<strong>BEARISH</strong>", '<span style="background: #fef2f2; color: #ef4444; padding: 2px 6px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">BEARISH</span>')

    # Format stock cards
    styled_html = format_stock_cards(styled_html)

    # Style <p> tags
    styled_html = styled_html.replace("<p>", '<p style="margin-bottom: 16px; line-height: 1.8; text-align: left;">')

    # Style <pre> block to format the AHP-TOPSIS ASCII table properly
    styled_html = styled_html.replace("<pre>", '<pre style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; font-family: monospace; font-size: 0.85rem; line-height: 1.4; overflow-x: auto; margin-bottom: 24px; text-align: left;">')

    # Styled sections
    styled_html = re.sub(r'<h3>(.*?)</h3>', r'<h3 style="font-size: 1.15rem; font-weight: 700; color: #1e293b; margin-top: 24px; margin-bottom: 12px; text-align: left;">\1</h3>', styled_html)
    styled_html = re.sub(r'<h2>(.*?)</h2>', r'<h2 style="font-size: 1.35rem; font-weight: 800; color: #0f172a; margin-top: 40px; margin-bottom: 16px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; text-transform: uppercase; text-align: left;">\1</h2>', styled_html)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
      <div style="max-width: 650px; margin: 20px auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; background: #ffffff; color: #334155; line-height: 1.6; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 32px 24px; color: #ffffff; text-align: center; border-bottom: 4px solid #3b82f6;">
          <h1 style="margin: 0; font-size: 1.75rem; font-weight: 800; letter-spacing: -0.025em; color: #ffffff;">📈 BUFFETT STRATEGIC ANALYST</h1>
          <p style="margin: 6px 0 0 0; font-size: 0.875rem; color: #94a3b8; font-weight: 500;">DAILY FINANCIAL MARKET BRIEFING</p>
        </div>

        <div style="padding: 24px;">
          {tldr_html}
          {styled_html}
        </div>

        <!-- Footer -->
        <div style="background: #f8fafc; padding: 20px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 0.75rem; color: #94a3b8;">
          <p style="margin: 0 0 4px 0;">This research is prepared using Warren Buffett & Charlie Munger's value investing principles.</p>
          <p style="margin: 0;">Stock Tracker Automated Intelligence • Raspberry Pi Station</p>
        </div>
      </div>
    </body>
    </html>
    """

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
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = email_to
        
        # Set plain-text body alternative
        msg.set_content(body)
        
        # Set rich HTML body
        html_body = build_html_body(subject, body)
        msg.add_alternative(html_body, subtype='html')

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
