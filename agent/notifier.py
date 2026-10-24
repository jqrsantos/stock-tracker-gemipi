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
    # Look for GLOBAL NARRATIVE / MACRO DASHBOARD / MACRO & GEOPOLITICAL BRIEFING highlights
    narrative_section = re.search(r"## \[(GLOBAL NARRATIVE|MACRO DASHBOARD|MACRO & GEOPOLITICAL BRIEFING)\]\s*(.*?)(?=##|$)", markdown_text, re.DOTALL)
    if narrative_section:
        text = narrative_section.group(2).strip()
        sentences = re.split(r'\.(?=\s+[A-Z]|\s*$)', text)
        sentences = [s.strip() + "." for s in sentences if len(s.strip()) > 10]
        highlights.extend(sentences[:2])
    
    # Look for Bargain Radar / Scouted Opportunities picks
    radar_section = re.search(r"## \[(BARGAIN RADAR|SCOUTED OPPORTUNITIES)\]\s*(.*?)(?=##|$)", markdown_text, re.DOTALL)
    if radar_section:
        picks = re.findall(r"\d+\.\s+\*\*([A-Z]+)\b", radar_section.group(2))
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
    # Match any <h3>...</h3> followed by <ul>...</ul> block
    # We use a pattern that allows arbitrary formatting, newlines, and optional paragraphs in between.
    pattern = r'<h3>(.*?)</h3>\s*(?:<p>.*?</p>\s*)?<ul>\s*(.*?)\s*</ul>'
    
    def replace_with_card(match):
        header_text = match.group(1).strip()
        ul_content = match.group(2).strip()
        
        # Check if this is a stock health card by verifying if ROIC or Moat is mentioned in the list
        ul_lower = ul_content.lower()
        if "roic" not in ul_lower and "moat" not in ul_lower:
            return match.group(0) # Keep original HTML unchanged
            
        # 1. Parse header
        # Check if header is of form: AAPL (Apple Inc) - BUY
        ticker = ""
        name = ""
        status = ""
        
        orig_match = re.match(r'^([A-Z0-9\-\.]+)\s*\((.*?)\)\s*-\s*(STRONG BUY|STRONG HOLD|STRONG SELL|BUY|HOLD|SELL)$', header_text, re.IGNORECASE)
        if orig_match:
            ticker = orig_match.group(1).strip()
            name = orig_match.group(2).strip()
            status = orig_match.group(3).upper()
        else:
            # Maybe it is: AAPL — Apple Inc.
            parts = re.split(r'\s*(?:[\u2014\u2013]|-)\s*', header_text)
            if len(parts) >= 2:
                ticker = parts[0].strip()
                name = parts[1].strip()
            else:
                ticker = header_text
                name = ""
                
        # 2. Parse list items
        # Find all <li>...</li> blocks
        li_items = re.findall(r'<li>(.*?)</li>', ul_content, re.DOTALL)
        
        moat = ""
        roic = "N/A"
        de = "N/A"
        fcf = "N/A"
        val = "N/A"
        comment = ""
        
        def clean_val(text):
            # Strip html tags
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            # Split only on space-surrounded em-dash, en-dash, or hyphen
            subparts = re.split(r'\s+(?:[\u2014\u2013]|-)\s+', clean_text)
            return subparts[0].strip(), subparts[1].strip() if len(subparts) > 1 else ""
            
        for li in li_items:
            li_text = re.sub(r'<[^>]+>', '', li).strip()
            
            # Match ROIC at start of line
            if re.match(r'^\s*ROIC', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*ROIC\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                roic, _ = clean_val(val_part)
            # Match Moat at start of line
            elif re.match(r'^\s*Moat', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*Moat\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                moat = re.sub(r'<[^>]+>', '', val_part).strip()
            # Match Debt/Equity at start of line
            elif re.match(r'^\s*(?:Debt/Equity|Debt to Equity|D/E)', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*(?:Debt/Equity|Debt to Equity|D/E)\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                de, _ = clean_val(val_part)
            # Match FCF Yield at start of line
            elif re.match(r'^\s*FCF Yield', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*FCF Yield\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                fcf, _ = clean_val(val_part)
            # Match Valuation or P/E at start of line
            elif re.match(r'^\s*(?:Valuation|P/E|PE)', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*(?:Valuation|P/E|PE)\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                val, _ = clean_val(val_part)
            # Match Action/Status at start of line
            elif re.match(r'^\s*(?:Action|Status)', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*(?:Action|Status)\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                status_val, desc_val = clean_val(val_part)
                if not status:
                    status = status_val.upper()
                if desc_val:
                    comment = desc_val
            # Match Comment/Note at start of line
            elif re.match(r'^\s*(?:Comment|Note)', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*(?:Comment|Note)\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                _, desc_val = clean_val(val_part)
                if desc_val:
                    comment = desc_val
                else:
                    comment = val_part
                    
        # Apply default status mapping colors
        border_color = "#3b82f6"  # Blue default
        bg_status = "#f1f5f9"
        text_status = "#475569"
        
        status = status.strip()
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
            
        moat_row = ""
        if moat:
            moat_row = f"""
            <tr>
              <td style="padding: 5px 0; border-bottom: 1px dashed #f1f5f9; color: #64748b; text-align: left;">Moat</td>
              <td style="padding: 5px 0; border-bottom: 1px dashed #f1f5f9; text-align: right; font-weight: 700; color: #0f172a;">{moat}</td>
            </tr>
            """
            
        comment_row = ""
        if comment:
            comment_row = f"""
            <tr>
              <td colspan="2" style="padding: 10px 0 0 0; border-top: 1px dashed #e2e8f0; color: #475569; font-size: 0.78rem; font-style: italic; line-height: 1.35; text-align: left;">
                <span style="font-weight: 700; color: #475569;">Note:</span> {comment}
              </td>
            </tr>
            """
            
        return f"""
        <!-- STOCK_CARD_START -->
        <div class="stock-card-item" style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid {border_color}; border-radius: 10px; padding: 18px 20px; margin-bottom: 16px; box-sizing: border-box; width: 100%; box-shadow: 0 2px 6px -1px rgba(0,0,0,0.06);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #f1f5f9;">
            <div>
              <h3 style="margin: 0; font-size: 1.2rem; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">{ticker}</h3>
              <span style="font-size: 0.8rem; color: #64748b; font-weight: 500;">{name}</span>
            </div>
            <span style="background: {bg_status}; color: {text_status}; border: 1px solid {border_color}33; padding: 4px 12px; border-radius: 100px; font-size: 0.75rem; font-weight: 800; letter-spacing: 0.05em; text-transform: uppercase;">{status}</span>
          </div>
          
          <table style="width: 100%; border-collapse: collapse; font-size: 0.88rem; line-height: 1.5;">
            {moat_row}
            <tr>
              <td style="padding: 6px 0; border-bottom: 1px dashed #f1f5f9; color: #64748b; text-align: left; width: 35%;">ROIC</td>
              <td style="padding: 6px 0; border-bottom: 1px dashed #f1f5f9; text-align: right; font-weight: 700; color: #0f172a;">{roic}</td>
            </tr>
            <tr>
              <td style="padding: 6px 0; border-bottom: 1px dashed #f1f5f9; color: #64748b; text-align: left;">Debt/Equity</td>
              <td style="padding: 6px 0; border-bottom: 1px dashed #f1f5f9; text-align: right; font-weight: 700; color: #0f172a;">{de}</td>
            </tr>
            <tr>
              <td style="padding: 6px 0; border-bottom: 1px dashed #f1f5f9; color: #64748b; text-align: left;">FCF Yield</td>
              <td style="padding: 6px 0; border-bottom: 1px dashed #f1f5f9; text-align: right; font-weight: 700; color: #0f172a;">{fcf}</td>
            </tr>
            <tr>
              <td style="padding: 6px 0; color: #64748b; text-align: left;">Valuation</td>
              <td style="padding: 6px 0; text-align: right; font-weight: 700; color: {border_color};">{val}</td>
            </tr>
            {comment_row}
          </table>
        </div>
        <!-- STOCK_CARD_END -->
        """
    # Replace individual cards
    replaced_html = re.sub(pattern, replace_with_card, html_content, flags=re.DOTALL)
    
    # Clean container: Stack vertically full-width with consistent margins
    container_start = '<div style="margin: 20px 0 28px 0; width: 100%;">'
    container_end = '</div>'
    
    def wrap_group(match):
        group_content = match.group(0)
        group_content = group_content.replace('<!-- STOCK_CARD_START -->', '')
        group_content = group_content.replace('<!-- STOCK_CARD_END -->', '')
        return f"{container_start}\n{group_content}{container_end}"
        
    replaced_html = re.sub(
        r'(?:[ \t\n]*<!-- STOCK_CARD_START -->.*?<!-- STOCK_CARD_END -->[ \t\n]*)+', 
        wrap_group, 
        replaced_html, 
        flags=re.DOTALL
    )
    
    return replaced_html

def build_html_body(subject: str, markdown_content: str, is_weekly: bool = False) -> str:
    """
    Converts report markdown into a beautifully designed HTML document.
    """
    tldr_html = extract_tldr(markdown_content)
    
    # Pre-process ASCII grid tables from tabulate into proper Markdown tables 
    # if they are just inside <pre> blocks or standard markdown
    markdown_content = re.sub(r'(?:<pre><code>|```[a-zA-Z]*\n)\s*(\|.*?\|)\s*(?:</code></pre>|```)', r'\n\1\n', markdown_content, flags=re.DOTALL)
    
    # Parse markdown using tables and fenced_code extensions
    raw_html = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
    
    # Style standard elements generated by markdown parser
    styled_html = raw_html
    styled_html = styled_html.replace("<table>", '<div style="overflow-x: auto; margin-bottom: 24px;"><table style="width: 100%; border-collapse: collapse; font-size: 0.875rem; text-align: left;">')
    styled_html = styled_html.replace("</table>", '</table></div>')
    styled_html = styled_html.replace("<thead>", '<thead style="background: #f8fafc; color: #475569; font-weight: 600; border-bottom: 2px solid #e2e8f0;">')
    styled_html = styled_html.replace("<th>", '<th style="padding: 10px 12px; border-bottom: 2px solid #e2e8f0;">')
    styled_html = styled_html.replace("<td>", '<td style="padding: 10px 12px; border-bottom: 1px solid #f1f5f9;">')
    
    # Bold and styling alerts
    styled_html = styled_html.replace("<strong>ACTIVE</strong>", '<span style="background: #d1fae5; color: #065f46; border: 1px solid #10b981; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 800; white-space: nowrap;">ACTIVE</span>')
    styled_html = styled_html.replace("<strong>DISMISSED</strong>", '<span style="background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 800; white-space: nowrap;">DISMISSED</span>')
    styled_html = styled_html.replace("<strong>STRONG BUY</strong>", '<span style="background: #d1fae5; color: #065f46; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 800; white-space: nowrap;">STRONG BUY</span>')
    styled_html = styled_html.replace("<strong>STRONG HOLD</strong>", '<span style="background: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 800; white-space: nowrap;">STRONG HOLD</span>')
    styled_html = styled_html.replace("<strong>STRONG SELL</strong>", '<span style="background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 800; white-space: nowrap;">STRONG SELL</span>')
    styled_html = styled_html.replace("<strong>BUY</strong>", '<span style="background: #ecfdf5; color: #10b981; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 800; white-space: nowrap;">BUY</span>')
    styled_html = styled_html.replace("<strong>SELL</strong>", '<span style="background: #fef2f2; color: #dc2626; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 800; white-space: nowrap;">SELL</span>')
    styled_html = styled_html.replace("<strong>HOLD</strong>", '<span style="background: #fffbeb; color: #d97706; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 800; white-space: nowrap;">HOLD</span>')
    styled_html = styled_html.replace("<strong>IGNORE</strong>", '<span style="background: #f3f4f6; color: #374151; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 800; white-space: nowrap;">IGNORE</span>')
    styled_html = styled_html.replace("<strong>BULLISH</strong>", '<span style="background: #ecfdf5; color: #10b981; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 800;">BULLISH</span>')
    styled_html = styled_html.replace("<strong>BEARISH</strong>", '<span style="background: #fef2f2; color: #ef4444; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 800;">BEARISH</span>')

    # Format stock cards
    styled_html = format_stock_cards(styled_html)

    # Style <p> tags
    styled_html = styled_html.replace("<p>", '<p style="margin-bottom: 16px; line-height: 1.8; text-align: left;">')

    # Style <pre><code> block to format the AHP-TOPSIS ASCII table properly with monospace
    styled_html = styled_html.replace("<pre><code>", '<pre style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.82rem; line-height: 1.35; overflow-x: auto; margin-bottom: 24px; text-align: left; color: #0f172a; white-space: pre;"><code style="font-family: inherit; font-size: inherit; color: inherit; background: none; border: none; padding: 0; margin: 0; white-space: inherit;">')
    styled_html = styled_html.replace("</code></pre>", '</code></pre>')

    # Styled sections
    styled_html = re.sub(r'<h3>(.*?)</h3>', r'<h3 style="font-size: 1.15rem; font-weight: 700; color: #1e293b; margin-top: 24px; margin-bottom: 12px; text-align: left;">\1</h3>', styled_html)
    styled_html = re.sub(r'<h2>(.*?)</h2>', r'<h2 style="font-size: 1.35rem; font-weight: 800; color: #0f172a; margin-top: 40px; margin-bottom: 16px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; text-transform: uppercase; text-align: left;">\1</h2>', styled_html)

    subtitle = "WEEKLY WATCHLIST AUDIT & DEEP SCOUR" if is_weekly else "DAILY FINANCIAL MARKET BRIEFING"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
      <meta name="x-apple-disable-message-reformatting">
      <meta name="format-detection" content="telephone=no, date=no, address=no, email=no">
      <style>
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0 !important;
          padding: 0 !important;
          width: 100% !important;
          min-width: 100% !important;
          background-color: #f1f5f9;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
          -webkit-text-size-adjust: 100%;
          -ms-text-size-adjust: 100%;
        }}
        .email-outer-table {{
          width: 100% !important;
          border-collapse: collapse;
          margin: 0 auto;
          background-color: #f1f5f9;
        }}
        .email-container-cell {{
          padding: 20px 10px;
        }}
        .email-card-wrapper {{
          width: 100%;
          max-width: 680px;
          margin: 0 auto;
          background-color: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          overflow: hidden;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
        }}
        .content-body {{
          padding: 24px 20px;
        }}
        @media only screen and (max-width: 600px) {{
          .email-container-cell {{ padding: 8px 4px !important; }}
          .content-body {{ padding: 18px 14px !important; }}
          .stock-card-item {{ padding: 14px 14px !important; }}
          h1 {{ font-size: 1.4rem !important; }}
          h2 {{ font-size: 1.15rem !important; margin-top: 28px !important; }}
        }}
      </style>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
      <table role="presentation" border="0" cellpadding="0" cellspacing="0" class="email-outer-table" width="100%">
        <tr>
          <td align="center" class="email-container-cell">
            <div class="email-card-wrapper">
              
              <!-- Header -->
              <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 32px 20px; color: #ffffff; text-align: center; border-bottom: 4px solid #3b82f6;">
                <h1 style="margin: 0; font-size: 1.7rem; font-weight: 800; letter-spacing: -0.025em; color: #ffffff;">📈 BUFFETT STRATEGIC ANALYST</h1>
                <p style="margin: 6px 0 0 0; font-size: 0.85rem; color: #94a3b8; font-weight: 500; letter-spacing: 0.05em;">{subtitle}</p>
              </div>

              <!-- Content -->
              <div class="content-body" style="padding: 28px 24px;">
                {tldr_html}
                {styled_html}
              </div>

              <!-- Footer -->
              <div style="background: #f8fafc; padding: 20px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 0.75rem; color: #94a3b8; line-height: 1.5;">
                <p style="margin: 0 0 4px 0;">This research is prepared using Warren Buffett & Charlie Munger's value investing principles.</p>
                <p style="margin: 0;">Stock Tracker Automated Intelligence • Raspberry Pi Station</p>
              </div>
            </div>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

def send_email(subject: str, body: str, is_weekly: bool = False):
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
        html_body = build_html_body(subject, body, is_weekly=is_weekly)
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


def run_daily_notification(report_dir: str) -> bool:
    list_of_files = glob.glob(f"{report_dir}/*.md")
    if not list_of_files:
        logger.warning("No reports found to send.")
        return False
    latest_file = max(list_of_files, key=os.path.basename)
    with open(latest_file, 'r') as f:
        content = f.read()
    logger.info(f"Sending latest daily report via email only: {os.path.basename(latest_file)}")
    return send_email(f"Daily Report: {os.path.basename(latest_file)}", content, is_weekly=False)


def run_weekly_notification(report_dir: str) -> bool:
    list_of_files = glob.glob(f"{report_dir}/*.md")
    if not list_of_files:
        logger.warning("No weekly reports found to send.")
        return False
    latest_file = max(list_of_files, key=os.path.basename)
    with open(latest_file, 'r') as f:
        content = f.read()
    logger.info(f"Sending latest weekly deep scour report via email: {os.path.basename(latest_file)}")
    return send_email(f"Weekly Watchlist Audit & Deep Scour Dossier: {os.path.basename(latest_file)}", content, is_weekly=True)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    from dotenv import load_dotenv
    load_dotenv()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "--weekly" in sys.argv:
        report_dir = os.path.join(base_dir, "knowledge_base", "weekly_reports")
        run_weekly_notification(report_dir)
    else:
        report_dir = os.path.join(base_dir, "knowledge_base", "daily_reports")
        run_daily_notification(report_dir)
