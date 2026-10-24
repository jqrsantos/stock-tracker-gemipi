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


def normalize_scouted_opportunities(markdown_text: str) -> str:
    """
    Transforms dense/dyslexic-unfriendly numbered lists of scouted stocks into
    clean, consistent card-format markdown blocks before HTML conversion.
    """
    section_match = re.search(
        r'(## \[(?:BARGAIN RADAR|SCOUTED OPPORTUNITIES)\]\s*)(.*?)(?=##|$)',
        markdown_text,
        re.DOTALL | re.IGNORECASE,
    )
    if not section_match:
        return markdown_text

    section_body = section_match.group(2)

    # If it already uses clean card headers (### TICKER ...), leave it alone
    if re.search(r'###\s+[A-Z0-9\.\-]+\s*\(.*?\)\s*-\s*(?:STRONG )?(?:BUY|HOLD|SELL)', section_body):
        return markdown_text

    # Split by stock entries: 1. TICKER (Company Name) - BUY or TICKER (Company Name) - BUY
    stock_start_regex = r'(?:^|\n)\s*(?:\d+\.\s+)?(?:\*\*)?([A-Z0-9\.\-]+)\s*\((.*?)\)\s*(?:\*\*)?\s*-\s*(STRONG BUY|STRONG HOLD|STRONG SELL|BUY|HOLD|SELL)\b'
    splits = re.split(r'(?=(?:^|\n)\s*(?:\d+\.\s+)?(?:\*\*)?[A-Z0-9\.\-]+\s*\(.*?\)\s*(?:\*\*)?\s*-\s*(?:STRONG )?(?:BUY|HOLD|SELL)\b)', section_body)
    if len(splits) <= 1:
        return markdown_text

    intro = splits[0].strip()
    stock_cards = []

    for block in splits[1:]:
        head_match = re.search(stock_start_regex, block)
        if not head_match:
            continue
        ticker = head_match.group(1).strip()
        name = head_match.group(2).strip()
        action = head_match.group(3).strip().upper()

        moat_m = re.search(r'(?:Moat|Competitive Advantage)\s*:?\s*([^\n]+)', block, re.IGNORECASE)
        moat_val = re.sub(r'^\d+\.\s*', '', moat_m.group(1)).strip() if moat_m else ""

        fh_m = re.search(r'(?:Financial Health|Financial Snapshot|ROIC)\s*:?\s*([^\n]+)', block, re.IGNORECASE)
        fh_val = re.sub(r'^\d+\.\s*', '', fh_m.group(1)).strip() if fh_m else ""

        val_m = re.search(r'\b(?:Valuation|Trailing P/E|Forward P/E|P/E)\b\s*:?\s*([^\n]+)', block, re.IGNORECASE)
        val_val = re.sub(r'^\d+\.\s*', '', val_m.group(1)).strip() if val_m else ""

        note_m = re.search(r'(?:Recent News & Catalysts|Recent News|Catalysts|Note|Comment)\s*:?\s*(.*?)(?=\n\s*(?:\d+\.|\*|-|[A-Z0-9\.\-]+\s*\()|$)', block, re.DOTALL | re.IGNORECASE)
        note_val = re.sub(r'^\d+\.\s*', '', note_m.group(1)).strip() if note_m else ""

        # Parse sub-metrics from fh_val if present
        roic_sub = ""
        de_sub = ""
        fcf_sub = ""
        if "ROIC" in fh_val:
            rm = re.search(r'ROIC\s*([0-9\.]+%)', fh_val)
            if rm:
                roic_sub = rm.group(1)
        if "Debt/Equity" in fh_val:
            dem = re.search(r'Debt/Equity\s*([0-9\.]+)', fh_val)
            if dem:
                de_sub = dem.group(1)
        if "FCF Yield" in fh_val:
            fcfm = re.search(r'FCF Yield\s*([0-9\.]+%[^\,\)]*(?:\([^\)]+\))?)', fh_val)
            if fcfm:
                fcf_sub = fcfm.group(1).strip()

        card_md = f"### {ticker} ({name}) - {action}\n"
        if moat_val:
            card_md += f"- Moat: {moat_val}\n"
        if roic_sub:
            card_md += f"- ROIC: {roic_sub}\n"
        elif fh_val:
            card_md += f"- ROIC: {fh_val}\n"
        if de_sub:
            card_md += f"- Debt/Equity: {de_sub}\n"
        if fcf_sub:
            card_md += f"- FCF Yield: {fcf_sub}\n"
        if val_val:
            card_md += f"- Valuation: {val_val}\n"
        if note_val:
            card_md += f"- Note: {note_val}\n"

        stock_cards.append(card_md)

    if stock_cards:
        new_section_body = (intro + "\n\n" if intro else "") + "\n\n".join(stock_cards) + "\n\n"
        start_idx = section_match.start(2)
        end_idx = section_match.end(2)
        return markdown_text[:start_idx] + new_section_body + markdown_text[end_idx:]

    return markdown_text


def format_scorecard_summary(html_content: str) -> str:
    """
    Replaces dense bulleted Scorecard Summary lists with a clean, executive
    4-box KPI grid with no bullet points.
    """
    pattern = r'(?:<h[34][^>]*>|<p[^>]*><strong>|<p[^>]*>)\s*Scorecard Summary.*?(?:</h[34]>|</strong></p>|</p>)\s*<ul>(.*?)</ul>|<p[^>]*>\s*Scorecard Summary\s*[\n<](.*?)</p>'
    match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
    if not match:
        return html_content

    ul_content = match.group(1) or match.group(2) or ""

    total_picks = "N/A"
    win_rate = "N/A"
    avg_return = "N/A"
    top_performer = "N/A"

    m_total = re.search(r'Total Scouted(?: Picks)?\s*:?\s*(\d+)', ul_content, re.IGNORECASE)
    if m_total:
        total_picks = m_total.group(1)

    m_win = re.search(r'Overall Win Rate\s*:?\s*([0-9\.]+%)', ul_content, re.IGNORECASE)
    if m_win:
        win_rate = m_win.group(1)

    m_avg = re.search(r'Average Return(?: Since Day-1)?\s*:?\s*([+\-]?[0-9\.]+%)', ul_content, re.IGNORECASE)
    if m_avg:
        avg_return = m_avg.group(1)

    m_top = re.search(r'Top Performer\s*:?\s*([^\n<]+)', ul_content, re.IGNORECASE)
    if m_top:
        top_performer = m_top.group(1).strip()

    avg_color = "#dc2626" if avg_return.startswith("-") else "#059669"
    win_color = "#059669"

    kpi_grid = f"""
    <div style="margin: 20px 0 24px 0;">
      <h3 style="font-size: 1.15rem; font-weight: 800; color: #0f172a; margin: 0 0 12px 0; text-transform: uppercase; letter-spacing: 0.03em;">🎯 Scouting Performance Scorecard</h3>
      <table style="width: 100%; border-collapse: separate; border-spacing: 8px 0; margin: 0 -8px;">
        <tr>
          <td style="width: 25%; background: #ffffff; border: 1px solid #e2e8f0; border-top: 4px solid #3b82f6; border-radius: 8px; padding: 14px 10px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Total Scouted</div>
            <div style="font-size: 1.35rem; font-weight: 800; color: #0f172a; margin-top: 4px; line-height: 1.2;">{total_picks}</div>
          </td>
          <td style="width: 25%; background: #ffffff; border: 1px solid #e2e8f0; border-top: 4px solid #10b981; border-radius: 8px; padding: 14px 10px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Win Rate</div>
            <div style="font-size: 1.35rem; font-weight: 800; color: {win_color}; margin-top: 4px; line-height: 1.2;">{win_rate}</div>
          </td>
          <td style="width: 25%; background: #ffffff; border: 1px solid #e2e8f0; border-top: 4px solid {avg_color}; border-radius: 8px; padding: 14px 10px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Avg Return</div>
            <div style="font-size: 1.35rem; font-weight: 800; color: {avg_color}; margin-top: 4px; line-height: 1.2;">{avg_return}</div>
          </td>
          <td style="width: 25%; background: #ffffff; border: 1px solid #e2e8f0; border-top: 4px solid #8b5cf6; border-radius: 8px; padding: 14px 10px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Top Performer</div>
            <div style="font-size: 0.95rem; font-weight: 800; color: #0f172a; margin-top: 8px; line-height: 1.2;">{top_performer}</div>
          </td>
        </tr>
      </table>
    </div>
    """
    return html_content[:match.start()] + kpi_grid + html_content[match.end():]


def format_data_tables(html_content: str) -> str:
    """
    Polishes data tables with clean borders, zebra rows, right-aligned numbers,
    and colored pill badges for return percentages.
    """
    def polish_table(match):
        table_html = match.group(0)

        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
        if len(rows) <= 1:
            return table_html

        header_row = rows[0]
        # Polish header cells
        header_row_polished = re.sub(
            r'<th[^>]*>(.*?)</th>',
            r'<th style="background: #f1f5f9; color: #334155; font-weight: 700; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; padding: 11px 12px; border-bottom: 2px solid #cbd5e1; text-align: left; white-space: nowrap;">\1</th>',
            header_row,
            flags=re.DOTALL,
        )

        new_body_rows = []
        for idx, r_content in enumerate(rows[1:]):
            bg = "#ffffff" if idx % 2 == 0 else "#f8fafc"
            cells = re.findall(r'<td[^>]*>(.*?)</td>', r_content, re.DOTALL)
            new_cells = []
            for c in cells:
                c_clean = c.strip()
                # Check if cell is return percentage (+94.85% or -45.04% or 0.00%)
                if re.match(r'^[+\-][0-9\.]+\%$', c_clean):
                    if c_clean.startswith('+'):
                        pill = f'<span style="display: inline-block; text-align: center; background: #ecfdf5; color: #059669; font-weight: 700; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; white-space: nowrap; line-height: 1.2;">{c_clean}</span>'
                    else:
                        pill = f'<span style="display: inline-block; text-align: center; background: #fef2f2; color: #dc2626; font-weight: 700; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; white-space: nowrap; line-height: 1.2;">{c_clean}</span>'
                    new_cells.append(f'<td style="padding: 10px 12px; border-bottom: 1px solid #f1f5f9; text-align: right;">{pill}</td>')
                elif re.match(r'^\$?[0-9\.]+$', c_clean) or re.match(r'^\d+$', c_clean):
                    new_cells.append(f'<td style="padding: 10px 12px; border-bottom: 1px solid #f1f5f9; text-align: right; color: #334155; font-variant-numeric: tabular-nums;">{c_clean}</td>')
                else:
                    if re.match(r'^[A-Z0-9\.\-]+$', c_clean) and len(c_clean) <= 6:
                        c_clean = f'<strong style="color: #0f172a; font-weight: 700;">{c_clean}</strong>'
                    new_cells.append(f'<td style="padding: 10px 12px; border-bottom: 1px solid #f1f5f9; color: #1e293b;">{c_clean}</td>')

            cells_html = "".join(new_cells)
            new_body_rows.append(f'<tr style="background: {bg};">{cells_html}</tr>')

        tbody_html = "".join(new_body_rows)
        return (
            '<div style="overflow-x: auto; margin: 18px 0 28px 0; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); background: #ffffff;">'
            '<table style="width: 100%; min-width: 580px; border-collapse: collapse; font-size: 0.82rem; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; text-align: left;">'
            f'<thead><tr>{header_row_polished}</tr></thead>'
            f'<tbody>{tbody_html}</tbody>'
            '</table></div>'
        )

    return re.sub(r'<table[^>]*>.*?</table>', polish_table, html_content, flags=re.DOTALL)


def format_stock_cards(html_content: str) -> str:
    # Match any <h3|h4> followed by <ul> block, strictly forbidding heading tags in between
    # This prevents swallowing earlier macro section headings into the first stock card.
    pattern = r'<h[34]>((?:(?!</?h[1-6]>).)*?)</h[34]>\s*(?:<p>(?:(?!</?h[1-6]>).)*?</p>\s*)?<ul>\s*(.*?)\s*</ul>'

    def replace_with_card(match):
        header_text = match.group(1).strip()
        ul_content = match.group(2).strip()

        # Check if this is a stock health card by verifying if ROIC or Moat is mentioned in the list
        ul_lower = ul_content.lower()
        if "roic" not in ul_lower and "moat" not in ul_lower:
            return match.group(0)  # Keep original HTML unchanged

        clean_header = re.sub(r'<[^>]+>', '', header_text).strip()
        # Reject non-stock macro headers
        if re.search(r'(?:Regional|Developments|Macro|Briefing|Narrative|Dashboard|Economy|Economies|Global|Scorecard)', clean_header, re.IGNORECASE):
            return match.group(0)

        # 1. Parse header
        ticker = ""
        name = ""
        status = ""

        orig_match = re.match(
            r'^([A-Z0-9\-\.]+)\s*\((.*?)\)\s*-\s*(STRONG BUY|STRONG HOLD|STRONG SELL|BUY|HOLD|SELL)$',
            clean_header,
            re.IGNORECASE,
        )
        if orig_match:
            ticker = orig_match.group(1).strip()
            name = orig_match.group(2).strip()
            status = orig_match.group(3).upper()
        else:
            parts = re.split(r'\s*(?:[\u2014\u2013]|-)\s*', clean_header)
            if len(parts) >= 3 and parts[-1].strip().upper() in ("BUY", "HOLD", "SELL", "STRONG BUY", "STRONG HOLD", "STRONG SELL"):
                ticker = parts[0].strip()
                name = parts[1].strip()
                status = parts[-1].strip().upper()
            elif len(parts) >= 2:
                ticker = parts[0].strip()
                name = parts[1].strip()
            else:
                ticker = clean_header
                name = ""

        # 2. Parse list items
        li_items = re.findall(r'<li>(.*?)</li>', ul_content, re.DOTALL)

        moat = ""
        roic = "N/A"
        de = "N/A"
        fcf = "N/A"
        val = "N/A"
        price = ""
        comment = ""

        def clean_val(text):
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            subparts = re.split(r'\s+(?:[\u2014\u2013]|-)\s+', clean_text)
            return subparts[0].strip(), subparts[1].strip() if len(subparts) > 1 else ""

        for li in li_items:
            li_text = re.sub(r'<[^>]+>', '', li).strip()

            if re.match(r'^\s*Moat', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*Moat\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                moat = re.sub(r'<[^>]+>', '', val_part).strip()
            elif re.match(r'^\s*(?:ROIC|Financial Health|Financials)', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*(?:ROIC|Financial Health|Financials)\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                roic, _ = clean_val(val_part)
            elif re.match(r'^\s*(?:Debt/Equity|Debt to Equity|D/E)', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*(?:Debt/Equity|Debt to Equity|D/E)\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                de, _ = clean_val(val_part)
            elif re.match(r'^\s*FCF Yield', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*FCF Yield\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                fcf, _ = clean_val(val_part)
            elif re.match(r'^\s*(?:Valuation|Trailing P/E|Forward P/E|P/E|PE)', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*(?:Valuation|Trailing P/E|Forward P/E|P/E|PE)\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                val, _ = clean_val(val_part)
            elif re.match(r'^\s*(?:Price|Current Price)', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*(?:Price|Current Price)\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                price = re.sub(r'<[^>]+>', '', val_part).strip()
            elif re.match(r'^\s*(?:Action|Status)', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*(?:Action|Status)\s*:?\s*', '', li_text, flags=re.IGNORECASE)
                status_val, desc_val = clean_val(val_part)
                if not status:
                    status = status_val.upper()
                if desc_val:
                    comment = desc_val
            elif re.match(r'^\s*(?:Comment|Note|Recent News & Catalysts|Recent News|Catalysts)', li_text, re.IGNORECASE):
                val_part = re.sub(r'^\s*(?:Comment|Note|Recent News & Catalysts|Recent News|Catalysts)\s*:?\s*', '', li_text, flags=re.IGNORECASE)
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
              <td style="padding: 6px 0; border-bottom: 1px dashed #f1f5f9; color: #64748b; text-align: left; width: 35%;">Moat</td>
              <td style="padding: 6px 0; border-bottom: 1px dashed #f1f5f9; text-align: right; font-weight: 700; color: #0f172a;">{moat}</td>
            </tr>
            """

        price_row = ""
        if price:
            price_row = f"""
            <tr>
              <td style="padding: 6px 0; border-bottom: 1px dashed #f1f5f9; color: #64748b; text-align: left;">Price</td>
              <td style="padding: 6px 0; border-bottom: 1px dashed #f1f5f9; text-align: right; font-weight: 700; color: #0f172a;">{price}</td>
            </tr>
            """

        comment_row = ""
        if comment:
            comment_row = f"""
            <tr>
              <td colspan="2" style="padding: 12px 0 0 0; border-top: 1px dashed #e2e8f0; color: #334155; font-size: 0.85rem; line-height: 1.55; text-align: left;">
                <span style="font-weight: 700; color: #0f172a;">Note:</span> {comment}
              </td>
            </tr>
            """

        return f"""
        <!-- STOCK_CARD_START -->
        <div class="stock-card-item" style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid {border_color}; border-radius: 10px; padding: 18px 20px; margin-bottom: 16px; box-sizing: border-box; width: 100%; box-shadow: 0 2px 6px -1px rgba(0,0,0,0.06);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #f1f5f9;">
            <div style="text-align: left;">
              <h3 style="margin: 0; font-size: 1.25rem; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">{ticker}</h3>
              <span style="font-size: 0.82rem; color: #64748b; font-weight: 500;">{name}</span>
            </div>
            <div style="text-align: right; margin-left: 12px; flex-shrink: 0;">
              <span style="display: inline-block; text-align: center; background: {bg_status}; color: {text_status}; border: 1px solid {border_color}40; padding: 5px 14px; border-radius: 9999px; font-size: 0.75rem; font-weight: 800; letter-spacing: 0.05em; text-transform: uppercase; min-width: 65px; line-height: 1.25; vertical-align: middle; box-sizing: border-box;">{status}</span>
            </div>
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
            {price_row}
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
    # 1. Normalize any numbered scouted opportunities into clean stock cards
    markdown_content = normalize_scouted_opportunities(markdown_content)

    tldr_html = extract_tldr(markdown_content)
    
    # Pre-process ASCII grid tables from tabulate into proper Markdown tables 
    # if they are just inside <pre> blocks or standard markdown
    markdown_content = re.sub(r'(?:<pre><code>|```[a-zA-Z]*\n)\s*(\|.*?\|)\s*(?:</code></pre>|```)', r'\n\1\n', markdown_content, flags=re.DOTALL)
    
    # Parse markdown using tables and fenced_code extensions
    raw_html = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
    
    styled_html = raw_html

    # 2. Format Scorecard Summary KPI grid (no bullet points)
    styled_html = format_scorecard_summary(styled_html)

    # 3. Format polished data tables (zebra rows, right-aligned stats, return pills)
    styled_html = format_data_tables(styled_html)
    
    # 4. Bold and centered styling alerts
    badge_style = "display: inline-block; text-align: center; line-height: 1.25; vertical-align: middle; min-width: 58px; padding: 3px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 800; white-space: nowrap; box-sizing: border-box;"

    styled_html = styled_html.replace("<strong>ACTIVE</strong>", f'<span style="background: #d1fae5; color: #065f46; border: 1px solid #10b981; {badge_style}">ACTIVE</span>')
    styled_html = styled_html.replace("<strong>DISMISSED</strong>", f'<span style="background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1; {badge_style}">DISMISSED</span>')
    styled_html = styled_html.replace("<strong>STRONG BUY</strong>", f'<span style="background: #d1fae5; color: #065f46; {badge_style}">STRONG BUY</span>')
    styled_html = styled_html.replace("<strong>STRONG HOLD</strong>", f'<span style="background: #fef3c7; color: #92400e; {badge_style}">STRONG HOLD</span>')
    styled_html = styled_html.replace("<strong>STRONG SELL</strong>", f'<span style="background: #fee2e2; color: #991b1b; {badge_style}">STRONG SELL</span>')
    styled_html = styled_html.replace("<strong>BUY</strong>", f'<span style="background: #ecfdf5; color: #10b981; border: 1px solid #10b98133; {badge_style}">BUY</span>')
    styled_html = styled_html.replace("<strong>SELL</strong>", f'<span style="background: #fef2f2; color: #dc2626; border: 1px solid #dc262633; {badge_style}">SELL</span>')
    styled_html = styled_html.replace("<strong>HOLD</strong>", f'<span style="background: #fffbeb; color: #d97706; border: 1px solid #d9770633; {badge_style}">HOLD</span>')
    styled_html = styled_html.replace("<strong>IGNORE</strong>", f'<span style="background: #f3f4f6; color: #374151; {badge_style}">IGNORE</span>')
    styled_html = styled_html.replace("<strong>BULLISH</strong>", f'<span style="background: #ecfdf5; color: #10b981; {badge_style}">BULLISH</span>')
    styled_html = styled_html.replace("<strong>BEARISH</strong>", f'<span style="background: #fef2f2; color: #ef4444; {badge_style}">BEARISH</span>')

    # 5. Format stock cards
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
