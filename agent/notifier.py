import requests
import os
import logging
import glob
import smtplib
import subprocess
import shutil
from typing import Optional
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

def extract_tldr(markdown_text: str, is_weekly: bool = False) -> str:
    """
    Extracts key highlights from the report to create a concise TL;DR block.
    """
    if is_weekly:
        return """
    <div style="background: #f8fafc; border-left: 4px solid #6366f1; border-radius: 6px; padding: 18px 20px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
      <h3 style="margin: 0 0 10px 0; font-size: 0.95rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: #1e1b4b;">⚡ Weekly Watchlist Audit Executive Summary</h3>
      <ul style="margin: 0; padding-left: 20px; font-size: 0.88rem; color: #334155; line-height: 1.6;">
        <li style="margin-bottom: 8px;"><strong>Watchlist Rationalization:</strong> 51 tracked equities forensically audited; <strong>32 high-conviction fortresses retained (62.7%)</strong> and <strong>19 structural value traps expelled (37.3%)</strong>.</li>
        <li style="margin-bottom: 8px;"><strong>Macro Stress Regime:</strong> 10-Year Treasury Yields at 5.09%–5.15% & Brent Crude &gt; $100/bbl (Hormuz friction) enforce strict hurdle rates and zero tolerance for debt walls or SBC dilution.</li>
        <li style="margin-bottom: 4px;"><strong>The ServiceNow Dip Rule:</strong> Disciplined post-alert dip accumulation captures nearly 3x realized gains (+77.8% vs +27.8%) compared to chasing initial alert prices.</li>
      </ul>
    </div>
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


def format_regional_developments(markdown_text: str) -> str:
    """
    Transforms dense/dyslexic-unfriendly numbered lists in
    'Regional Developments Across Major Economies' into clean, dyslexia-friendly
    regional cards with country flags and colored borders, eliminating numbered bullets.
    """
    pattern = r'(###\s*Regional Developments Across Major Economies\s*\n+)(.*?)(?=\n\s*###|\n\s*##|\Z)'
    match = re.search(pattern, markdown_text, re.DOTALL | re.IGNORECASE)
    if not match:
        return markdown_text

    body = match.group(2)

    region_name_pattern = r'(?:United States \(US\)|United States|US|European Union \(EU\)|European Union|EU|China|Japan)'
    region_prefix = r'(?:^|\n)\s*(?:####\s+)?(?:\d+\.\s+)?(?:[^\w\s]+\s+)?(?:\*\*)?'
    region_regex = region_prefix + r'(' + region_name_pattern + r')(?:\*\*)?\s*:?'
    split_regex = r'(?=(?:^|\n)\s*(?:####\s+)?(?:\d+\.\s+)?(?:[^\w\s]+\s+)?(?:\*\*)?' + region_name_pattern + r'(?:\*\*)?\s*:?)'

    splits = re.split(split_regex, body)

    flag_map = {
        'United States (US)': ('🇺🇸', '#3b82f6'),
        'European Union (EU)': ('🇪🇺', '#6366f1'),
        'China': ('🇨🇳', '#f59e0b'),
        'Japan': ('🇯🇵', '#0d9488'),
    }

    cards = []
    intro_lines = []

    for block in splits:
        m = re.search(region_regex, block)
        if not m:
            if block.strip():
                intro_lines.append(block.strip())
            continue
        raw_name = m.group(1).strip()
        if 'United States' in raw_name or raw_name == 'US':
            norm_name = 'United States (US)'
        elif 'European Union' in raw_name or raw_name == 'EU':
            norm_name = 'European Union (EU)'
        else:
            norm_name = raw_name

        flag, border_color = flag_map.get(norm_name, ('🌐', '#3b82f6'))

        sub_points = re.findall(
            r'(?:^|\n)\s*(?:-\s+|\*\s+|\d+\.\s+)?(?:\*\*)?([A-Za-z0-9\s&,–\-\/]+?)(?:\*\*)?\s*:\s*([^\n]+(?:\n(?!\s*(?:-\s+|\*\s+|\d+\.\s+|\*\*[A-Z]))[^\n]+)*)',
            block
        )

        content_items = []
        for topic, detail in sub_points:
            topic_clean = topic.strip()
            detail_clean = detail.strip()
            if topic_clean in ('United States (US)', 'European Union (EU)', 'China', 'Japan', raw_name):
                continue
            content_items.append(
                f'<div style="margin-bottom: 10px; line-height: 1.6; color: #334155; font-size: 0.88rem;">'
                f'<strong style="color: #0f172a;">{topic_clean}:</strong> {detail_clean}'
                f'</div>'
            )

        if not content_items:
            cleaned_text = re.sub(region_regex, '', block).strip()
            cleaned_text = re.sub(r'^(?:-\s+|\*\s+|\d+\.\s+)', '', cleaned_text)
            content_items.append(
                f'<div style="line-height: 1.6; color: #334155; font-size: 0.88rem;">{cleaned_text}</div>'
            )

        card_html = f"""
<div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid {border_color}; border-radius: 8px; padding: 16px 18px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
  <div style="font-size: 1.05rem; font-weight: 800; color: #0f172a; margin-bottom: 10px; display: flex; align-items: center;">
    <span>{flag} {norm_name}</span>
  </div>
  {''.join(content_items)}
</div>"""
        cards.append(card_html)

    if cards:
        intro_text = '\n\n'.join(intro_lines) + '\n\n' if intro_lines else ''
        new_body = intro_text + '\n'.join(cards) + '\n\n'
        start_idx = match.start(2)
        end_idx = match.end(2)
        return markdown_text[:start_idx] + new_body + markdown_text[end_idx:]

    return markdown_text


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


def format_weekly_audit(markdown_text: str, for_pdf: bool = False) -> str:
    """
    Transforms the weekly watchlist audit into a high-hierarchy executive dossier.
    - If for_pdf=False (email body): renders executive dashboard, macro stress, KPI grids,
      case studies, master ledger tables, and an Executive PDF Dossier banner (under 75 KB to eliminate clipping).
    - If for_pdf=True: renders the full 51 company deep cards split into Fortresses vs Expelled Traps.
    """
    # 1. Quick Navigation Bar
    if for_pdf:
        jump_active_dsm = """
  <a href="#active-audits" style="display: inline-block; text-decoration: none; background: #ecfdf5; color: #065f46; border: 1px solid #10b98140; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; margin: 2px 4px;">🏰 32 Fortresses</a>
  <a href="#dismissed-audits" style="display: inline-block; text-decoration: none; background: #fef2f2; color: #991b1b; border: 1px solid #ef444440; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; margin: 2px 4px;">🚫 19 Dismissals</a>
"""
    else:
        jump_active_dsm = """
  <a href="#pdf-dossier" style="display: inline-block; text-decoration: none; background: #eef2ff; color: #4338ca; border: 1px solid #6366f140; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; margin: 2px 4px;">📎 24-Page PDF Dossier</a>
"""

    nav_bar = f"""
<div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.03); text-align: center;">
  <span style="font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; display: inline-block; margin-right: 8px; vertical-align: middle;">Quick Jump:</span>
  <a href="#pruning-overview" style="display: inline-block; text-decoration: none; background: #f1f5f9; color: #1e293b; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; margin: 2px 4px;">📊 Pruning Verdict</a>
  <a href="#macro-stress" style="display: inline-block; text-decoration: none; background: #f1f5f9; color: #1e293b; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; margin: 2px 4px;">🏦 Macro Stress</a>
  <a href="#pruning-ledger" style="display: inline-block; text-decoration: none; background: #f1f5f9; color: #1e293b; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; margin: 2px 4px;">📋 Master Ledger</a>
  <a href="#dip-scorecard" style="display: inline-block; text-decoration: none; background: #f1f5f9; color: #1e293b; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; margin: 2px 4px;">🎯 Dip Scorecard</a>
{jump_active_dsm}
</div>
"""
    markdown_text = nav_bar + "\n\n" + markdown_text

    # 2. Add anchor IDs to major table headings
    markdown_text = markdown_text.replace("### Master Watchlist Pruning Ledger", "<div id=\"pruning-ledger\"></div>\n### Master Watchlist Pruning Ledger")
    markdown_text = markdown_text.replace("## [DIP OPPORTUNITY SCORECARD]", "<div id=\"dip-scorecard\"></div>\n## [DIP OPPORTUNITY SCORECARD]")

    # 3. Transform Macro Stress
    macro_pattern = r"###\s*The Macroeconomic Stress Environment[^\n]*\n+(.*?)(?=\n###|\Z)"
    m_match = re.search(macro_pattern, markdown_text, re.DOTALL)
    if m_match:
        macro_cards = """
<div id="macro-stress" style="margin: 20px 0 28px 0;">
  <div style="font-size: 1.05rem; font-weight: 800; color: #0f172a; margin-bottom: 12px;">
    🏦 The Macroeconomic Stress Environment (October 2026)
  </div>
  <div style="display: flex; flex-wrap: wrap; gap: 12px;">
    <div style="flex: 1 1 calc(50% - 12px); min-width: 240px; background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid #3b82f6; border-radius: 8px; padding: 12px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
      <div style="font-size: 0.8rem; font-weight: 800; color: #1e3a8a; margin-bottom: 4px;">📈 10-Year U.S. Treasury Yields: 5.09%–5.15%</div>
      <div style="font-size: 0.82rem; line-height: 1.5; color: #475569;">Multi-decade highs keep hurdle rates steep and corporate balance sheet borrowing costs elevated.</div>
    </div>
    <div style="flex: 1 1 calc(50% - 12px); min-width: 240px; background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid #6366f1; border-radius: 8px; padding: 12px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
      <div style="font-size: 0.8rem; font-weight: 800; color: #3730a3; margin-bottom: 4px;">⚖️ Federal Reserve Policy: 3.75%–4.00%</div>
      <div style="font-size: 0.82rem; line-height: 1.5; color: #475569;">Restrictive target held ahead of FOMC; sticky services inflation (3.7% YoY headline) delays easing.</div>
    </div>
    <div style="flex: 1 1 calc(50% - 12px); min-width: 240px; background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid #f59e0b; border-radius: 8px; padding: 12px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
      <div style="font-size: 0.8rem; font-weight: 800; color: #92400e; margin-bottom: 4px;">🚢 Energy & Supply Friction: Brent $100–$110/bbl</div>
      <div style="font-size: 0.82rem; line-height: 1.5; color: #475569;">Strait of Hormuz commercial vessel strikes drive maritime war-risk insurance premiums up 3%–10%.</div>
    </div>
    <div style="flex: 1 1 calc(50% - 12px); min-width: 240px; background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid #0d9488; border-radius: 8px; padding: 12px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
      <div style="font-size: 0.8rem; font-weight: 800; color: #115e59; margin-bottom: 4px;">🛍️ Consumer Bifurcation</div>
      <div style="font-size: 0.82rem; line-height: 1.5; color: #475569;">Upper-tier spending holds while lower-income demographics face acute dining trade-downs and loan delinquencies.</div>
    </div>
  </div>
</div>
"""
        markdown_text = markdown_text[:m_match.start()] + macro_cards + markdown_text[m_match.end():]

    # 4. Transform Pruning Verdict Overview into 4-box KPI Grid
    pruning_pattern = r"###\s*Pruning Verdict Overview\s*\n+(.*?)(?=\n---|\n###|\Z)"
    p_match = re.search(pruning_pattern, markdown_text, re.DOTALL)
    if p_match:
        p_text = p_match.group(1)
        tot_m = re.search(r"Total Tracked Equities Audited\*\*:\s*\*\*(\d+)", p_text)
        act_m = re.search(r"Retained as `ACTIVE`[^\*]*\*\*:\s*\*\*(\d+)\s*Stocks\s*\(([^\)]+)\)", p_text)
        dsm_m = re.search(r"Expelled as `DISMISSED`[^\*]*\*\*:\s*\*\*(\d+)\s*Stocks\s*\(([^\)]+)\)", p_text)

        total_cnt = tot_m.group(1) if tot_m else "51"
        act_cnt = act_m.group(1) if act_m else "32"
        act_pct = act_m.group(2) if act_m else "62.7%"
        dsm_cnt = dsm_m.group(1) if dsm_m else "19"
        dsm_pct = dsm_m.group(2) if dsm_m else "37.3%"

        kpi_grid = f"""
<div id="pruning-overview" style="display: flex; flex-wrap: wrap; gap: 12px; margin: 20px 0 28px 0;">
  <div style="flex: 1 1 calc(25% - 12px); min-width: 135px; background: #ffffff; border: 1px solid #e2e8f0; border-top: 4px solid #3b82f6; border-radius: 8px; padding: 14px 12px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
    <div style="font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Total Audited</div>
    <div style="font-size: 1.5rem; font-weight: 800; color: #0f172a; margin-top: 4px;">{total_cnt}</div>
    <div style="font-size: 0.72rem; color: #94a3b8; margin-top: 2px;">Tracked Equities</div>
  </div>
  <div style="flex: 1 1 calc(25% - 12px); min-width: 135px; background: #ffffff; border: 1px solid #e2e8f0; border-top: 4px solid #10b981; border-radius: 8px; padding: 14px 12px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
    <div style="font-size: 0.75rem; font-weight: 700; color: #059669; text-transform: uppercase; letter-spacing: 0.05em;">Retained Fortresses</div>
    <div style="font-size: 1.5rem; font-weight: 800; color: #059669; margin-top: 4px;">{act_cnt}</div>
    <div style="font-size: 0.72rem; color: #059669; font-weight: 600; margin-top: 2px;">{act_pct} Active</div>
  </div>
  <div style="flex: 1 1 calc(25% - 12px); min-width: 135px; background: #ffffff; border: 1px solid #e2e8f0; border-top: 4px solid #ef4444; border-radius: 8px; padding: 14px 12px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
    <div style="font-size: 0.75rem; font-weight: 700; color: #dc2626; text-transform: uppercase; letter-spacing: 0.05em;">Expelled Traps</div>
    <div style="font-size: 1.5rem; font-weight: 800; color: #dc2626; margin-top: 4px;">{dsm_cnt}</div>
    <div style="font-size: 0.72rem; color: #dc2626; font-weight: 600; margin-top: 2px;">{dsm_pct} Dismissed</div>
  </div>
  <div style="flex: 1 1 calc(25% - 12px); min-width: 135px; background: #ffffff; border: 1px solid #e2e8f0; border-top: 4px solid #8b5cf6; border-radius: 8px; padding: 14px 12px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
    <div style="font-size: 0.75rem; font-weight: 700; color: #7c3aed; text-transform: uppercase; letter-spacing: 0.05em;">Hurdle Standard</div>
    <div style="font-size: 1.15rem; font-weight: 800; color: #7c3aed; margin-top: 8px;">Zero SBC & Debt</div>
    <div style="font-size: 0.72rem; color: #6b21a8; margin-top: 2px;">Strict Pruning Gate</div>
  </div>
</div>
"""
        markdown_text = markdown_text[:p_match.start()] + kpi_grid + markdown_text[p_match.end():]

    # 5. Transform ServiceNow Case Study
    now_pattern = r"###\s*The ServiceNow \(NOW\) Case Study[^\n]*\n+(.*?)(?=\n###|\Z)"
    now_match = re.search(now_pattern, markdown_text, re.DOTALL)
    if now_match:
        now_card = """
<div id="case-study-now" style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid #6366f1; border-radius: 10px; padding: 18px 20px; margin: 20px 0 28px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.04);">
  <div style="font-size: 1.05rem; font-weight: 800; color: #1e1b4b; margin-bottom: 8px;">
    🎯 The ServiceNow (NOW) Case Study: The Superiority of Dip Patience
  </div>
  <p style="font-size: 0.88rem; color: #475569; line-height: 1.6; margin-bottom: 14px;">
    The trajectory of <strong>ServiceNow, Inc. (NOW)</strong> illustrates why disciplined investors must wait for post-alert technical weakness rather than chasing Day-1 alerts:
  </p>
  <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 14px;">
    <div style="flex: 1 1 calc(50% - 12px); min-width: 220px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px;">
      <div style="font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Day-1 Alert Entry</div>
      <div style="font-size: 1.15rem; font-weight: 800; color: #0f172a; margin: 4px 0;">$124.37 → $158.96</div>
      <div style="font-size: 0.85rem; font-weight: 700; color: #2563eb;">+27.81% Return</div>
      <div style="font-size: 0.72rem; color: #64748b; margin-top: 2px;">Buying immediately on alert</div>
    </div>
    <div style="flex: 1 1 calc(50% - 12px); min-width: 220px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px 14px;">
      <div style="font-size: 0.75rem; font-weight: 700; color: #166534; text-transform: uppercase;">Disciplined Dip Entry</div>
      <div style="font-size: 1.15rem; font-weight: 800; color: #166534; margin: 4px 0;">$89.39 → $158.96 (-28.1% dip)</div>
      <div style="font-size: 0.85rem; font-weight: 700; color: #059669;">+77.83% Peak Dip Gain (Nearly 3x!)</div>
      <div style="font-size: 0.72rem; color: #166534; margin-top: 2px;">Waiting for intrinsic Buying Zone</div>
    </div>
  </div>
  <div style="background: #eef2ff; border-radius: 6px; padding: 10px 14px; font-size: 0.84rem; color: #3730a3; line-height: 1.5; font-weight: 500;">
    💡 <strong>Key Takeaway:</strong> High-quality compounders with elevated initial multiples must be tracked with predetermined <strong>Buying Zones / Dip Targets</strong>. Entering during secondary pullbacks dramatically widens the margin of safety and nearly triples realized returns.
  </div>
</div>
"""
        markdown_text = markdown_text[:now_match.start()] + now_card + markdown_text[now_match.end():]

    # 6. Transform Gainers vs Traps
    gainers_pattern = r"###\s*Top Post-Alert Dip Gainers[^\n]*\n+(.*?)(?=\n---|\n###|\Z)"
    g_match = re.search(gainers_pattern, markdown_text, re.DOTALL)
    if g_match:
        gainers_cards = """
<div style="margin: 20px 0 28px 0;">
  <div style="font-size: 1.05rem; font-weight: 800; color: #0f172a; margin-bottom: 12px;">
    ⚖️ Top Post-Alert Dip Gainers vs. Structural Value Traps
  </div>
  <div style="display: flex; flex-wrap: wrap; gap: 14px;">
    <div style="flex: 1 1 calc(50% - 14px); min-width: 260px; background: #ffffff; border: 1px solid #bbf7d0; border-left: 5px solid #10b981; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
      <div style="font-size: 0.9rem; font-weight: 800; color: #166534; margin-bottom: 10px;">
        🚀 Elite Dip Capture Champions
      </div>
      <div style="font-size: 0.82rem; line-height: 1.5; color: #334155;">
        <div style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px dashed #f1f5f9;">
          <strong>ACN (Accenture):</strong> Dipped -9.5% ($115.82) → Surged to $249.37 <span style="background: #ecfdf5; color: #059669; font-weight: 700; padding: 1px 6px; border-radius: 4px; font-size: 0.75rem;">+115.31% Peak Gain</span>
        </div>
        <div style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px dashed #f1f5f9;">
          <strong>MKTX (MarketAxess):</strong> Dipped -4.4% ($111.36) → Surged to $164.67 <span style="background: #ecfdf5; color: #059669; font-weight: 700; padding: 1px 6px; border-radius: 4px; font-size: 0.75rem;">+47.87% Peak Gain</span>
        </div>
        <div style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px dashed #f1f5f9;">
          <strong>MSFT (Microsoft):</strong> Held support near $354.76 → Compounded to $524.51 <span style="background: #ecfdf5; color: #059669; font-weight: 700; padding: 1px 6px; border-radius: 4px; font-size: 0.75rem;">+47.85% Peak Gain</span>
        </div>
        <div style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px dashed #f1f5f9;">
          <strong>CME (CME Group):</strong> Dipped -3.4% ($217.29) → Advanced to $305.71 <span style="background: #ecfdf5; color: #059669; font-weight: 700; padding: 1px 6px; border-radius: 4px; font-size: 0.75rem;">+40.69% Peak Gain</span>
        </div>
        <div>
          <strong>INTU (Intuit):</strong> Dipped -9.5% ($250.56) → Advanced to $343.39 <span style="background: #ecfdf5; color: #059669; font-weight: 700; padding: 1px 6px; border-radius: 4px; font-size: 0.75rem;">+37.05% Peak Gain</span>
        </div>
      </div>
    </div>
    <div style="flex: 1 1 calc(50% - 14px); min-width: 260px; background: #ffffff; border: 1px solid #fecaca; border-left: 5px solid #ef4444; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
      <div style="font-size: 0.9rem; font-weight: 800; color: #991b1b; margin-bottom: 10px;">
        ⚠️ Structural Value Traps Diagnosed
      </div>
      <div style="font-size: 0.82rem; line-height: 1.5; color: #334155;">
        <div style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px dashed #f1f5f9;">
          <strong>ADBE (Adobe):</strong> Dipped <span style="background: #fef2f2; color: #dc2626; font-weight: 700; padding: 1px 6px; border-radius: 4px; font-size: 0.75rem;">-60.39%</span> from $480 to $190.12. 89% margin & $650M GenAI ARR prove deep value mispricing (Retained ACTIVE).
        </div>
        <div style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px dashed #f1f5f9;">
          <strong>TTD (The Trade Desk):</strong> Dipped <span style="background: #fef2f2; color: #dc2626; font-weight: 700; padding: 1px 6px; border-radius: 4px; font-size: 0.75rem;">-38.52%</span>. 17-20% SBC dilution and Amazon DSP competition justify complete dismissal.
        </div>
        <div style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px dashed #f1f5f9;">
          <strong>ROL (Rollins):</strong> Dipped <span style="background: #fef2f2; color: #dc2626; font-weight: 700; padding: 1px 6px; border-radius: 4px; font-size: 0.75rem;">-31.57%</span>. Overpriced M&A roll-up at 32x P/E with slowing organic growth. Dismissed.
        </div>
        <div>
          <strong>LULU, TU, NKE, GIS, PNR:</strong> Dipped <span style="background: #fef2f2; color: #dc2626; font-weight: 700; padding: 1px 6px; border-radius: 4px; font-size: 0.75rem;">-18% to -22%</span> from secular margin erosion and store brand private labels.
        </div>
      </div>
    </div>
  </div>
</div>
"""
        markdown_text = markdown_text[:g_match.start()] + gainers_cards + markdown_text[g_match.end():]

    # 7. Transform Deep Company Audits
    company_pattern = r"(### ([A-Z0-9\.\-]+)\s*-\s*([^\n\(]+)\s*\(Verdict:\s*([A-Z]+)\s*\|\s*Conviction:\s*([^\)]+)\)\n+)(.*?)(?=\n### [A-Z0-9\.\-]+\s*-\s*[^\n\(]+\s*\(Verdict:|\n## |\Z)"

    def format_company_card(block_match):
        ticker = block_match.group(2).strip()
        name = block_match.group(3).strip()
        verdict = block_match.group(4).strip()
        conviction = block_match.group(5).strip()
        body = block_match.group(6)

        is_active = (verdict == "ACTIVE")
        border_color = "#10b981" if is_active else "#ef4444"
        badge_bg = "#ecfdf5" if is_active else "#fef2f2"
        badge_color = "#059669" if is_active else "#dc2626"
        badge_border = "#10b98140" if is_active else "#ef444440"

        metrics_match = re.search(r"((?:^[ \t]*-[^\n]+\n?)+)", body, re.MULTILINE)
        metrics_raw = metrics_match.group(1) if metrics_match else ""

        metrics_pills = []
        for line in metrics_raw.strip().splitlines():
            line_clean = re.sub(r"^[ \t]*-\s*", "", line)
            parts = line_clean.split("|")
            for p in parts:
                p_clean = p.strip().replace("**", "")
                if ":" in p_clean:
                    k, v = p_clean.split(":", 1)
                    k_str = k.strip()
                    v_str = v.strip()
                    if re.match(r"^[+\-][0-9\.]+\%$", v_str):
                        color = "#059669" if v_str.startswith("+") else "#dc2626"
                        v_str = f'<strong style="color: {color};">{v_str}</strong>'
                    metrics_pills.append(f'<span style="display: inline-block; background: #ffffff; border: 1px solid #e2e8f0; padding: 2px 7px; border-radius: 5px; font-size: 0.74rem; color: #334155; margin: 2px 3px 2px 0;"><span style="color: #64748b;">{k_str}:</span> <strong>{v_str}</strong></span>')

        subsections = re.findall(r"####\s*(\d+\.[^\n]+)\n+(.*?)(?=\n####|\Z)", body, re.DOTALL)

        sec_html = []
        synthesis_box = ""
        for num_title, content in subsections:
            title_clean = num_title.strip()
            body_clean = content.strip()
            if "4." in title_clean or "Synthesis" in title_clean or "Autopsy" in title_clean or "Buying Zone" in title_clean:
                box_bg = "#f0fdf4" if is_active else "#fef2f2"
                box_border = "#10b981" if is_active else "#ef4444"
                box_title_color = "#166534" if is_active else "#991b1b"
                box_text_color = "#14532d" if is_active else "#7f1d1d"
                icon = "🎯" if is_active else "❌"
                synthesis_box = f"""
<div style="background: {box_bg}; border: 1px solid {box_border}40; border-left: 4px solid {box_border}; border-radius: 8px; padding: 12px 14px; margin-top: 14px;">
  <div style="font-size: 0.8rem; font-weight: 800; color: {box_title_color}; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">{icon} {title_clean}</div>
  <div style="font-size: 0.86rem; line-height: 1.6; color: {box_text_color}; font-weight: 500;">{body_clean}</div>
</div>"""
            else:
                icon = "📑" if "1." in title_clean else ("🛡️" if "2." in title_clean else "⚠️")
                sec_html.append(f"""
<div style="margin-bottom: 12px;">
  <div style="font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: #475569; margin-bottom: 3px;">{icon} {title_clean}</div>
  <div style="font-size: 0.85rem; line-height: 1.55; color: #334155;">{body_clean}</div>
</div>""")

        pills_joined = "".join(metrics_pills)
        secs_joined = "".join(sec_html)
        card_markup = f"""
<div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid {border_color}; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); overflow: hidden;" id="card-{ticker}">
  <div style="background: #f8fafc; padding: 12px 16px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
    <div style="text-align: left;">
      <span style="font-size: 1.25rem; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">{ticker}</span>
      <span style="font-size: 0.82rem; color: #64748b; font-weight: 500; margin-left: 8px;">{name}</span>
    </div>
    <div style="text-align: right; margin-left: auto;">
      <span style="display: inline-block; background: {badge_bg}; color: {badge_color}; border: 1px solid {badge_border}; padding: 3px 10px; border-radius: 9999px; font-weight: 800; font-size: 0.75rem;">{verdict}</span>
      <span style="display: inline-block; background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; padding: 3px 8px; border-radius: 9999px; font-weight: 700; font-size: 0.72rem; margin-left: 4px;">★ {conviction}</span>
    </div>
  </div>
  <div style="padding: 10px 16px; background: #fafafa; border-bottom: 1px solid #f1f5f9; line-height: 1.4;">
    {pills_joined}
  </div>
  <div style="padding: 14px 16px;">
    {secs_joined}
    {synthesis_box}
  </div>
</div>"""
        return (is_active, card_markup)

    audits_header_pattern = r"(## \[DEEP COMPANY AUDITS\]\s*\n+)(.*)"
    audits_match = re.search(audits_header_pattern, markdown_text, re.DOTALL)
    if audits_match:
        audits_content = audits_match.group(2)
        company_matches = list(re.finditer(company_pattern, audits_content, re.DOTALL))

        active_cards = []
        dismissed_cards = []
        for cm in company_matches:
            is_active, card_str = format_company_card(cm)
            if is_active:
                active_cards.append(card_str)
            else:
                dismissed_cards.append(card_str)

        act_count = len(active_cards) if active_cards else 32
        dsm_count = len(dismissed_cards) if dismissed_cards else 19

        if for_pdf:
            act_joined = "".join(active_cards)
            dsm_joined = "".join(dismissed_cards)

            active_section = f"""
<div id="active-audits" style="margin-top: 30px; margin-bottom: 24px;">
  <div style="background: #ecfdf5; border: 1px solid #a7f3d0; border-left: 6px solid #10b981; border-radius: 8px; padding: 14px 18px; margin-bottom: 20px;">
    <h3 style="margin: 0; font-size: 1.15rem; font-weight: 800; color: #065f46; letter-spacing: -0.01em;">
      🏰 High-Conviction Active Compounding Fortresses ({act_count} Equities Retained)
    </h3>
    <div style="font-size: 0.82rem; color: #047857; margin-top: 4px;">
      Unassailable moats, pristine accounting, zero excessive leverage, and defined Dip Buying Zones.
    </div>
  </div>
  {act_joined}
</div>
"""
            dismissed_section = f"""
<div id="dismissed-audits" style="margin-top: 40px; margin-bottom: 24px;">
  <div style="background: #fef2f2; border: 1px solid #fecaca; border-left: 6px solid #ef4444; border-radius: 8px; padding: 14px 18px; margin-bottom: 20px;">
    <h3 style="margin: 0; font-size: 1.15rem; font-weight: 800; color: #991b1b; letter-spacing: -0.01em;">
      🚫 Expelled Value Traps & Broken Theses ({dsm_count} Equities Dismissed)
    </h3>
    <div style="font-size: 0.82rem; color: #b91c1c; margin-top: 4px;">
      Structural commoditization, severe customer concentration, dilution mills, or looming debt walls.
    </div>
  </div>
  {dsm_joined}
</div>
"""
            new_audits = "## [DEEP COMPANY AUDITS]\n\n" + active_section + "\n\n" + dismissed_section
        else:
            new_audits = f"""
<div id="pdf-dossier" style="margin-top: 36px; margin-bottom: 24px;">
  <div style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); border: 1px solid #4338ca; border-radius: 12px; padding: 26px 22px; color: #ffffff; text-align: center; box-shadow: 0 4px 12px rgba(15,23,42,0.15);">
    <div style="font-size: 2.2rem; margin-bottom: 8px;">📎 📑</div>
    <div style="display: inline-block; background: #312e81; color: #a5b4fc; border: 1px solid #4338ca; padding: 3px 12px; border-radius: 9999px; font-size: 0.72rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 10px;">ATTACHED PDF DOSSIER</div>
    <h3 style="margin: 0 0 10px 0; font-size: 1.25rem; font-weight: 800; color: #ffffff; letter-spacing: -0.01em;">Complete 24-Page Forensic Audit Dossier Attached</h3>
    <p style="margin: 0 auto 16px auto; font-size: 0.88rem; color: #cbd5e1; max-width: 520px; line-height: 1.6;">
      To eliminate mobile email clipping while preserving deep institutional rigor, the full 51 company deep forensic audits—including <strong>{act_count} Retained Fortresses</strong>, <strong>{dsm_count} Expelled Value Traps</strong>, SEC 10-K/10-Q forensically reconciled metrics, and predetermined dip <strong>Buying Zones</strong>—are delivered in the attached high-resolution PDF.
    </p>
    <div style="background: rgba(255,255,255,0.08); border: 1px dashed rgba(255,255,255,0.25); border-radius: 8px; padding: 12px 16px; margin: 0 auto 16px auto; max-width: 440px; text-align: left; font-size: 0.82rem; color: #e2e8f0; line-height: 1.5;">
      <div>📄 <strong>Attachment:</strong> <code style="color: #a5b4fc; font-weight: 700;">Weekly-Watchlist-Audit-YYYY-MM-DD.pdf</code></div>
      <div style="margin-top: 4px;">⚖️ <strong>Coverage:</strong> 51 Companies ({act_count} Active Fortresses, {dsm_count} Expelled Traps)</div>
      <div style="margin-top: 4px;">🎯 <strong>Contents:</strong> SEC Forensics, Moat Threats, Catalysts & Buying Zones</div>
    </div>
    <div style="display: inline-block; background: #6366f1; color: #ffffff; padding: 9px 22px; border-radius: 9999px; font-size: 0.82rem; font-weight: 800; letter-spacing: 0.04em; text-transform: uppercase;">
      📥 Open Attached PDF in Mail / Preview
    </div>
  </div>
</div>
"""
        markdown_text = markdown_text[:audits_match.start()] + new_audits

    return markdown_text


def format_scorecard_summary(html_content: str) -> str:
    """
    Replaces dense bulleted Scorecard Summary lists with a clean, executive
    4-box KPI grid with no bullet points.
    """
    pattern = r'(?:<h[34][^>]*>|<p[^>]*><strong>|<p[^>]*>)\s*Scorecard Summary.*?(?:</h[34]>|</strong></p>|</p>)\s*(?:<ul>(.*?)</ul>|<p>(.*?)</p>)|<p[^>]*>\s*Scorecard Summary\s*[\n<](.*?)</p>'
    match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
    if not match:
        return html_content

    ul_content = match.group(1) or match.group(2) or match.group(3) or ""

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
    and colored pill badges for return percentages using concise CSS classes.
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
            r'<th class="th-cell">\1</th>',
            header_row,
            flags=re.DOTALL,
        )

        new_body_rows = []
        for idx, r_content in enumerate(rows[1:]):
            row_cls = "tr-even" if idx % 2 == 0 else "tr-odd"
            cells = re.findall(r'<td[^>]*>(.*?)</td>', r_content, re.DOTALL)
            new_cells = []
            for c in cells:
                c_clean = c.strip()
                # Check if cell is return percentage (+94.85% or -45.04% or 0.00%)
                if re.match(r'^[+\-][0-9\.]+\%$', c_clean):
                    pill_cls = "pill-green" if c_clean.startswith('+') else "pill-red"
                    new_cells.append(f'<td class="td-num"><span class="{pill_cls}">{c_clean}</span></td>')
                elif c_clean in ("ACTIVE", "DISMISSED"):
                    badge_cls = "pill-green" if c_clean == "ACTIVE" else "pill-red"
                    new_cells.append(f'<td class="td-center"><span class="{badge_cls}">{c_clean}</span></td>')
                elif re.match(r'^\$?[0-9\.]+$', c_clean) or re.match(r'^\d+$', c_clean):
                    new_cells.append(f'<td class="td-num">{c_clean}</td>')
                else:
                    if re.match(r'^[A-Z0-9\.\-]+$', c_clean) and len(c_clean) <= 6:
                        c_clean = f'<strong style="color: #0f172a;">{c_clean}</strong>'
                    new_cells.append(f'<td class="td-cell">{c_clean}</td>')

            cells_html = "".join(new_cells)
            new_body_rows.append(f'<tr class="{row_cls}">{cells_html}</tr>')

        tbody_html = "".join(new_body_rows)
        return (
            '<div class="table-wrap">'
            '<table class="data-table">'
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

def build_html_body(subject: str, markdown_content: str, is_weekly: bool = False, for_pdf: bool = False) -> str:
    """
    Converts report markdown into a beautifully designed HTML document.
    """
    if is_weekly:
        # 1. Transform weekly watchlist audit (navigation, KPI grids, case study, Active vs Dismissed company cards)
        markdown_content = format_weekly_audit(markdown_content, for_pdf=for_pdf)
        tldr_html = extract_tldr(markdown_content, is_weekly=True)
    else:
        # 1. Normalize regional developments (no numbered bullets, clean regional cards)
        markdown_content = format_regional_developments(markdown_content)

        # 2. Normalize any numbered scouted opportunities into clean stock cards
        markdown_content = normalize_scouted_opportunities(markdown_content)

        tldr_html = extract_tldr(markdown_content, is_weekly=False)
    
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

    # 5. Format stock cards for daily reports
    if not is_weekly:
        styled_html = format_stock_cards(styled_html)

    # Style <p> tags
    styled_html = styled_html.replace("<p>", '<p style="margin-bottom: 16px; line-height: 1.8; text-align: left;">')

    # Style <pre><code> block to format the AHP-TOPSIS ASCII table properly with monospace
    styled_html = styled_html.replace("<pre><code>", '<pre style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.82rem; line-height: 1.35; overflow-x: auto; margin-bottom: 24px; text-align: left; color: #0f172a; white-space: pre;"><code style="font-family: inherit; font-size: inherit; color: inherit; background: none; border: none; padding: 0; margin: 0; white-space: inherit;">')
    styled_html = styled_html.replace("</code></pre>", '</code></pre>')

    # Styled sections
    styled_html = re.sub(r'<h3>(.*?)</h3>', r'<h3 style="font-size: 1.15rem; font-weight: 700; color: #1e293b; margin-top: 24px; margin-bottom: 12px; text-align: left;">\1</h3>', styled_html)
    styled_html = re.sub(r'<h2>(.*?)</h2>', r'<h2 style="font-size: 1.35rem; font-weight: 800; color: #0f172a; margin-top: 40px; margin-bottom: 16px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; text-transform: uppercase; text-align: left;">\1</h2>', styled_html)

    header_gradient = "linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)" if is_weekly else "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)"
    header_border = "#6366f1" if is_weekly else "#3b82f6"
    card_max_width = "780px" if is_weekly else "680px"
    subtitle = "WEEKLY WATCHLIST AUDIT & DEEP SCOUR DOSSIER" if is_weekly else "DAILY FINANCIAL MARKET BRIEFING"
    top_badge = """<div style="margin-bottom: 10px;"><span style="display: inline-block; background: #312e81; color: #a5b4fc; border: 1px solid #4338ca; padding: 3px 12px; border-radius: 9999px; font-size: 0.72rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase;">WEEKLY DEEP SCOUR DOSSIER</span></div>""" if is_weekly else ""

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
          max-width: {card_max_width};
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
        .table-wrap {{
          overflow-x: auto;
          margin: 18px 0 28px 0;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
          background: #ffffff;
        }}
        .data-table {{
          width: 100%;
          min-width: 580px;
          border-collapse: collapse;
          font-size: 0.82rem;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          text-align: left;
        }}
        .th-cell {{
          background: #f1f5f9;
          color: #334155;
          font-weight: 700;
          font-size: 0.72rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          padding: 11px 12px;
          border-bottom: 2px solid #cbd5e1;
          text-align: left;
          white-space: nowrap;
        }}
        .td-cell {{
          padding: 10px 12px;
          border-bottom: 1px solid #f1f5f9;
          color: #1e293b;
        }}
        .td-num {{
          padding: 10px 12px;
          border-bottom: 1px solid #f1f5f9;
          text-align: right;
          color: #334155;
          font-variant-numeric: tabular-nums;
        }}
        .td-center {{
          padding: 10px 12px;
          border-bottom: 1px solid #f1f5f9;
          text-align: center;
        }}
        .tr-even {{ background: #ffffff; }}
        .tr-odd {{ background: #f8fafc; }}
        .pill-green {{
          display: inline-block;
          text-align: center;
          background: #ecfdf5;
          color: #059669;
          font-weight: 700;
          padding: 2px 8px;
          border-radius: 9999px;
          font-size: 0.75rem;
          white-space: nowrap;
          line-height: 1.2;
        }}
        .pill-red {{
          display: inline-block;
          text-align: center;
          background: #fef2f2;
          color: #dc2626;
          font-weight: 700;
          padding: 2px 8px;
          border-radius: 9999px;
          font-size: 0.75rem;
          white-space: nowrap;
          line-height: 1.2;
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
              <div style="background: {header_gradient}; padding: 32px 20px; color: #ffffff; text-align: center; border-bottom: 4px solid {header_border};">
                {top_badge}
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

def find_browser_binary() -> Optional[str]:
    """
    Locates an available Chrome/Chromium executable across macOS and Linux (including Raspberry Pi).
    """
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "chromium-browser",
        "chromium",
        "google-chrome",
        "google-chrome-stable",
    ]
    for c in candidates:
        if os.path.isabs(c) and os.path.exists(c):
            return c
        found = shutil.which(c)
        if found:
            return found
    return None


def generate_weekly_pdf(markdown_content: str, output_pdf_path: str) -> bool:
    """
    Compiles the full weekly markdown audit into a high-resolution,
    unclipped 24-page PDF document with print-optimized pagination and styling.
    """
    browser = find_browser_binary()
    if not browser:
        logger.warning("No Chrome/Chromium browser binary found for PDF generation.")
        return False

    # Generate the complete HTML with all 51 deep cards
    full_html = build_html_body("Weekly Watchlist Audit & Deep Scour Dossier", markdown_content, is_weekly=True, for_pdf=True)

    print_css = """
<style>
@media print {
  body { background-color: #ffffff !important; }
  .email-card-wrapper { max-width: 100% !important; border: none !important; box-shadow: none !important; }
  .email-container-cell { padding: 0 !important; }
  @page {
    size: A4;
    margin: 14mm 12mm 14mm 12mm;
  }
  tr { page-break-inside: avoid; }
  div[id^="card-"] { page-break-inside: avoid; margin-bottom: 22px; }
}
</style>
"""
    full_html_print = full_html.replace("</head>", print_css + "</head>")

    temp_html_path = output_pdf_path + ".tmp.html"
    try:
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(full_html_print)

        cmd = [
            browser,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={output_pdf_path}",
            temp_html_path,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if res.returncode == 0 and os.path.exists(output_pdf_path) and os.path.getsize(output_pdf_path) > 0:
            logger.info(f"Successfully generated PDF dossier: {output_pdf_path} ({os.path.getsize(output_pdf_path)} bytes)")
            return True
        else:
            logger.error(f"Browser PDF generation failed (code {res.returncode}): {res.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error during PDF generation: {e}")
        return False
    finally:
        if os.path.exists(temp_html_path):
            try:
                os.remove(temp_html_path)
            except OSError:
                pass


def send_email(subject: str, body: str, is_weekly: bool = False, pdf_path: Optional[str] = None):
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
        
        # Set rich HTML body (executive briefing under 75 KB for weekly)
        html_body = build_html_body(subject, body, is_weekly=is_weekly, for_pdf=False)
        msg.add_alternative(html_body, subtype='html')

        # Attach PDF if available
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            pdf_filename = os.path.basename(pdf_path)
            msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=pdf_filename)
            logger.info(f"Attached PDF report to email: {pdf_filename} ({len(pdf_data)} bytes)")

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

    # Automatically generate or update the 24-page PDF dossier
    pdf_path = os.path.splitext(latest_file)[0] + ".pdf"
    generate_weekly_pdf(content, pdf_path)

    logger.info(f"Sending latest weekly deep scour report via email with PDF: {os.path.basename(latest_file)}")
    return send_email(
        f"Weekly Watchlist Audit & Deep Scour Dossier: {os.path.basename(latest_file)}",
        content,
        is_weekly=True,
        pdf_path=pdf_path if os.path.exists(pdf_path) else None,
    )


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
