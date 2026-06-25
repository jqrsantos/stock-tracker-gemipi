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
    narrative_section = re.search(r"## \[(GLOBAL NARRATIVE|MACRO DASHBOARD)\]\s*(.*?)(?=##|$)", markdown_text, re.DOTALL)
    if narrative_section:
        text = narrative_section.group(2).strip()
        sentences = re.split(r'\.(?=\s+[A-Z]|\s*$)', text)
        sentences = [s.strip() + "." for s in sentences if len(s.strip()) > 10]
        highlights.extend(sentences[:2])
    
    radar_section = re.search(r"## \[BARGAIN RADAR\]\s*(.*?)(?=##|$)", markdown_text, re.DOTALL)
    if radar_section:
        picks = re.findall(r"\d+\.\s+\*\*([A-Z]+)\b", radar_section.group(1))
        if picks:
            highlights.append(f"Highlighted moated bargains: {', '.join(picks)}")
            
    if not highlights:
        highlights = ["Fed rate decisions & energy supply shocks continue to drive macro trends.", "Portfolio evaluated for fundamental strengths & ROIC health."]
        
    li_items = "".join([f"<li style='margin-bottom: 8px; line-height: 1.5;'>{item}</li>" for item in highlights])
    return f"""
    <div style="background: rgba(30, 41, 59, 0.7); border-left: 4px solid #38bdf8; border-radius: 8px; padding: 20px; margin-bottom: 30px; backdrop-filter: blur(10px); box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);">
      <h3 style="margin: 0 0 12px 0; font-size: 1rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #f8fafc; display: flex; align-items: center;"><span style="color: #38bdf8; margin-right: 8px;">⚡</span> Daily TL;DR Digest</h3>
      <ul style="margin: 0; padding-left: 20px; font-size: 0.95rem; color: #cbd5e1;">
        {li_items}
      </ul>
    </div>
    """

def format_stock_cards(html_content: str) -> str:
    # Match any <h3>...</h3> followed by <ul>...</ul> block
    pattern = r'<h3>(.*?)</h3>\s*(?:<p>.*?</p>\s*)?<ul>\s*(.*?)\s*</ul>'
    
    def replace_with_card(match):
        header_text = match.group(1).strip()
        ul_content = match.group(2).strip()
        
        if "ROIC" not in ul_content and "roic" not in ul_content.lower():
            return match.group(0) 
            
        ticker = ""
        name = ""
        status = ""
        
        orig_match = re.match(r'^([A-Z0-9\-\.]+)\s*\((.*?)\)\s*-\s*(STRONG BUY|STRONG HOLD|STRONG SELL|BUY|HOLD|SELL)$', header_text, re.IGNORECASE)
        if orig_match:
            ticker = orig_match.group(1).strip()
            name = orig_match.group(2).strip()
            status = orig_match.group(3).upper()
        else:
            parts = re.split(r'\s*(?:[\u2014\u2013]|-)\s*', header_text)
            if len(parts) >= 2:
                ticker = parts[0].strip()
                name = parts[1].strip()
            else:
                ticker = header_text
                name = ""
                
        li_items = re.findall(r'<li>(.*?)</li>', ul_content, re.DOTALL)
        
        roic = "N/A"
        de = "N/A"
        fcf = "N/A"
        val = "N/A"
        comment = ""
        
        def clean_val(text):
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            subparts = re.split(r'\s+(?:[\u2014\u2013]|-)\s+', clean_text)
            return subparts[0].strip(), subparts[1].strip() if len(subparts) > 1 else ""
            
        for li in li_items:
            li_text = re.sub(r'<[^>]+>', '', li).strip()
            if re.match(r'^\s*ROIC', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*ROIC\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                roic, _ = clean_val(val_part)
            elif re.match(r'^\s*(?:Debt/Equity|Debt to Equity|D/E)', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*(?:Debt/Equity|Debt to Equity|D/E)\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                de, _ = clean_val(val_part)
            elif re.match(r'^\s*FCF Yield', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*FCF Yield\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                fcf, _ = clean_val(val_part)
            elif re.match(r'^\s*(?:Valuation|P/E|PE)', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*(?:Valuation|P/E|PE)\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                val, _ = clean_val(val_part)
            elif re.match(r'^\s*(?:Action|Status)', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*(?:Action|Status)\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                status_val, desc_val = clean_val(val_part)
                if not status:
                    status = status_val.upper()
                if desc_val:
                    comment = desc_val
            elif re.match(r'^\s*(?:Comment|Note)', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*(?:Comment|Note)\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                _, desc_val = clean_val(val_part)
                if desc_val:
                    comment = desc_val
                else:
                    comment = val_part
                    
        border_color = "#3b82f6"
        bg_status = "rgba(59, 130, 246, 0.15)"
        text_status = "#60a5fa"
        
        status = status.strip()
        if "BUY" in status:
            border_color = "#10b981"
            bg_status = "rgba(16, 185, 129, 0.15)"
            text_status = "#34d399"
        elif "SELL" in status:
            border_color = "#ef4444"
            bg_status = "rgba(239, 68, 68, 0.15)"
            text_status = "#f87171"
        elif "HOLD" in status:
            border_color = "#f59e0b"
            bg_status = "rgba(245, 158, 11, 0.15)"
            text_status = "#fbbf24"
            
        comment_row = ""
        if comment:
            comment_row = f"""
            <tr>
              <td colspan="2" style="padding: 12px 0 0 0; border-top: 1px solid rgba(255,255,255,0.1); color: #94a3b8; font-size: 0.85rem; font-style: italic; line-height: 1.4; text-align: left;">
                <span style="font-weight: 700; color: #cbd5e1;">Note:</span> {comment}
              </td>
            </tr>
            """
            
        return f"""
        <!-- STOCK_CARD_START -->
        <div class="stock-card-item" style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.05); border-top: 4px solid {border_color}; border-radius: 12px; padding: 20px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); backdrop-filter: blur(10px); margin-bottom: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
            <div>
              <h3 style="margin: 0 0 4px 0; font-size: 1.25rem; font-weight: 800; color: #f8fafc; letter-spacing: 0.02em;">{ticker}</h3>
              <span style="font-size: 0.85rem; color: #94a3b8; font-weight: 500;">{name}</span>
            </div>
            <span style="background: {bg_status}; color: {text_status}; padding: 6px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase;">{status}</span>
          </div>
          
          <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem; line-height: 1.5;">
            <tr>
              <td style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); color: #94a3b8; text-align: left;">ROIC</td>
              <td style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); text-align: right; font-weight: 700; color: #f8fafc;">{roic}</td>
            </tr>
            <tr>
              <td style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); color: #94a3b8; text-align: left;">Debt/Equity</td>
              <td style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); text-align: right; font-weight: 700; color: #f8fafc;">{de}</td>
            </tr>
            <tr>
              <td style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); color: #94a3b8; text-align: left;">FCF Yield</td>
              <td style="padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); text-align: right; font-weight: 700; color: #f8fafc;">{fcf}</td>
            </tr>
            <tr>
              <td style="padding: 8px 0; color: #94a3b8; text-align: left;">Valuation</td>
              <td style="padding: 8px 0; text-align: right; font-weight: 700; color: {text_status};">{val}</td>
            </tr>
            {comment_row}
          </table>
        </div>
        <!-- STOCK_CARD_END -->
        """
        
    replaced_html = re.sub(pattern, replace_with_card, html_content, flags=re.DOTALL)
    
    container_start = '<div class="stock-cards-container" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 24px; margin-bottom: 32px;">'
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

def build_html_body(subject: str, markdown_content: str) -> str:
    """
    Converts report markdown into a beautifully designed HTML document.
    """
    tldr_html = extract_tldr(markdown_content)
    
    markdown_content = re.sub(r'(?:<pre><code>|```[a-zA-Z]*\n)\s*(\|.*?\|)\s*(?:</code></pre>|```)', r'\n\1\n', markdown_content, flags=re.DOTALL)
    
    raw_html = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
    
    styled_html = raw_html
    styled_html = styled_html.replace("<table>", '<div style="overflow-x: auto; margin-bottom: 32px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); background: rgba(15, 23, 42, 0.4);"><table style="width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: left; white-space: nowrap;">')
    styled_html = styled_html.replace("</table>", '</table></div>')
    styled_html = styled_html.replace("<thead>", '<thead style="background: rgba(255,255,255,0.05); color: #cbd5e1; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.8rem;">')
    styled_html = styled_html.replace("<th>", '<th style="padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,0.1);">')
    styled_html = styled_html.replace("<td>", '<td style="padding: 14px 20px; border-bottom: 1px solid rgba(255,255,255,0.05); color: #f8fafc;">')
    
    # Absolute Valuation styling badges
    styled_html = styled_html.replace("<strong>STRONG BUY</strong>", '<span style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; white-space: nowrap; box-shadow: 0 2px 10px rgba(16, 185, 129, 0.3);">STRONG BUY</span>')
    styled_html = styled_html.replace("STRONG BUY", '<span style="color: #34d399; font-weight: 700;">STRONG BUY</span>')
    styled_html = styled_html.replace("<strong>STRONG HOLD</strong>", '<span style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #ffffff; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; white-space: nowrap; box-shadow: 0 2px 10px rgba(245, 158, 11, 0.3);">STRONG HOLD</span>')
    styled_html = styled_html.replace("<strong>STRONG SELL</strong>", '<span style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: #ffffff; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; white-space: nowrap; box-shadow: 0 2px 10px rgba(239, 68, 68, 0.3);">STRONG SELL</span>')
    styled_html = styled_html.replace("STRONG SELL", '<span style="color: #f87171; font-weight: 700;">STRONG SELL</span>')
    styled_html = styled_html.replace("<strong>BUY</strong>", '<span style="background: rgba(16, 185, 129, 0.2); color: #34d399; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; white-space: nowrap; border: 1px solid rgba(16, 185, 129, 0.3);">BUY</span>')
    styled_html = styled_html.replace(" BUY ", ' <span style="color: #34d399; font-weight: 700;">BUY</span> ')
    styled_html = styled_html.replace("<strong>SELL</strong>", '<span style="background: rgba(239, 68, 68, 0.2); color: #f87171; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; white-space: nowrap; border: 1px solid rgba(239, 68, 68, 0.3);">SELL</span>')
    styled_html = styled_html.replace(" SELL ", ' <span style="color: #f87171; font-weight: 700;">SELL</span> ')
    styled_html = styled_html.replace("<strong>HOLD</strong>", '<span style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; white-space: nowrap; border: 1px solid rgba(245, 158, 11, 0.3);">HOLD</span>')
    styled_html = styled_html.replace(" HOLD ", ' <span style="color: #fbbf24; font-weight: 700;">HOLD</span> ')
    styled_html = styled_html.replace("<strong>IGNORE</strong>", '<span style="background: rgba(148, 163, 184, 0.2); color: #cbd5e1; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; white-space: nowrap; border: 1px solid rgba(148, 163, 184, 0.3);">IGNORE</span>')
    styled_html = styled_html.replace(" IGNORE ", ' <span style="color: #cbd5e1; font-weight: 700;">IGNORE</span> ')

    styled_html = format_stock_cards(styled_html)

    styled_html = styled_html.replace("<p>", '<p style="margin-bottom: 20px; line-height: 1.7; text-align: left; color: #cbd5e1; font-size: 1.05rem;">')

    styled_html = styled_html.replace("<pre><code>", '<div style="background: #020617; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; overflow-x: auto; margin-bottom: 30px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);"><pre style="font-family: \'JetBrains Mono\', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.85rem; line-height: 1.5; color: #38bdf8; margin: 0; text-align: left;"><code style="font-family: inherit; font-size: inherit; color: inherit; background: none; border: none; padding: 0; margin: 0; white-space: pre;">')
    styled_html = styled_html.replace("</code></pre>", '</code></pre></div>')

    styled_html = re.sub(r'<h3>(.*?)</h3>', r'<h3 style="font-size: 1.35rem; font-weight: 700; color: #f8fafc; margin-top: 32px; margin-bottom: 16px; text-align: left;">\1</h3>', styled_html)
    styled_html = re.sub(r'<h2>(.*?)</h2>', r'<h2 style="font-size: 1.6rem; font-weight: 800; color: #ffffff; margin-top: 48px; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em; text-align: left; display: flex; align-items: center;"><span style="display: inline-block; width: 4px; height: 24px; background: #38bdf8; margin-right: 12px; border-radius: 4px;"></span>\1</h2>', styled_html)
    styled_html = re.sub(r'<h1>(.*?)</h1>', r'<h1 style="font-size: 2.2rem; font-weight: 900; color: #ffffff; margin-top: 0; margin-bottom: 24px; text-align: center; background: linear-gradient(to right, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">\1</h1>', styled_html)

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap');
        body {{
          margin: 0;
          padding: 0;
          background-color: #0f172a;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
          color: #e2e8f0;
          -webkit-font-smoothing: antialiased;
        }}
        .email-wrapper {{
          background-color: #0f172a;
          width: 100%;
          padding: 40px 20px;
          box-sizing: border-box;
        }}
        .email-content {{
          max-width: 720px;
          margin: 0 auto;
          background: #1e293b;
          border: 1px solid rgba(255, 255, 255, 0.05);
          border-radius: 24px;
          overflow: hidden;
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }}
        .header {{
          background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
          padding: 48px 32px;
          text-align: center;
          position: relative;
          overflow: hidden;
        }}
        .header::before {{
          content: '';
          position: absolute;
          top: 0; right: 0; bottom: 0; left: 0;
          background: radial-gradient(circle at top right, rgba(56, 189, 248, 0.15), transparent 50%);
        }}
        .header h1 {{
          margin: 0;
          font-size: 2rem;
          font-weight: 900;
          letter-spacing: 0.05em;
          color: #ffffff;
          position: relative;
          z-index: 1;
        }}
        .header p {{
          margin: 12px 0 0 0;
          font-size: 1rem;
          color: #94a3b8;
          font-weight: 500;
          letter-spacing: 0.1em;
          position: relative;
          z-index: 1;
        }}
        .body-section {{
          padding: 40px;
        }}
        .footer {{
          background: #0f172a;
          padding: 32px;
          text-align: center;
          border-top: 1px solid rgba(255, 255, 255, 0.05);
        }}
        .footer p {{
          margin: 0 0 8px 0;
          font-size: 0.85rem;
          color: #64748b;
          line-height: 1.5;
        }}
        @media only screen and (max-width: 600px) {{
          .email-wrapper {{ padding: 20px 10px; }}
          .body-section {{ padding: 24px 20px; }}
          .header {{ padding: 32px 20px; }}
          .stock-cards-container {{ display: block !important; }}
          .stock-card-item {{ margin-bottom: 20px; }}
        }}
      </style>
    </head>
    <body>
      <div class="email-wrapper">
        <div class="email-content">
          <!-- Header -->
          <div class="header">
            <h1>BUFFETT STRATEGIC ANALYST</h1>
            <p>DAILY FINANCIAL MARKET BRIEFING</p>
          </div>

          <div class="body-section">
            {tldr_html}
            {styled_html}
          </div>

          <!-- Footer -->
          <div class="footer">
            <p>Prepared using Warren Buffett & Charlie Munger's value investing principles.</p>
            <p style="color: #475569;">Stock Tracker Automated Intelligence • Raspberry Pi Station</p>
          </div>
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
        latest_file = max(list_of_files, key=os.path.basename)
        with open(latest_file, 'r') as f:
            content = f.read()
        logger.info(f"Sending latest report: {os.path.basename(latest_file)}")
        send_telegram(content)
        send_email(f"Daily Report: {os.path.basename(latest_file)}", content)
