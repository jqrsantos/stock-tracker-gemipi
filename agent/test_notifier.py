import re
from unittest.mock import patch, mock_open
from notifier import build_html_body, format_stock_cards, extract_tldr, run_daily_notification


def test_format_stock_cards_buy():
    html_input = """
<h3>AAPL (Apple Inc) - BUY</h3>
<ul>
<li>ROIC: 25%</li>
<li>Debt/Equity: 0.1</li>
<li>FCF Yield: 5%</li>
<li>Valuation: Undervalued</li>
</ul>
    """
    formatted = format_stock_cards(html_input)
    assert 'border-left: 5px solid #10b981;' in formatted
    assert "AAPL" in formatted
    assert "Apple Inc" in formatted
    assert "BUY" in formatted
    assert "25%" in formatted
    assert "0.1" in formatted
    assert "5%" in formatted
    assert "Undervalued" in formatted


def test_format_stock_cards_with_moat_and_news():
    html_input = """
<h3>AAPL (Apple Inc) - BUY</h3>
<ul>
<li>Moat: Wide (Ecosystem Switching Costs & Brand)</li>
<li>ROIC: 55.0% (Op Margin: 31.0%)</li>
<li>Debt/Equity: 1.67</li>
<li>FCF Yield: 3.7% (Growing)</li>
<li>Valuation: P/E 30.0x vs 5Y Avg 28.0x</li>
<li>Note: Strong Services growth offsets China hardware headwinds.</li>
</ul>
    """
    formatted = format_stock_cards(html_input)
    assert 'border-left: 5px solid #10b981;' in formatted
    assert "AAPL" in formatted
    assert "Apple Inc" in formatted
    assert "BUY" in formatted
    assert "Wide (Ecosystem Switching Costs & Brand)" in formatted
    assert "55.0%" in formatted
    assert "Strong Services growth offsets China hardware headwinds." in formatted


def test_format_stock_cards_sell():
    html_input = """
<h3>TSLA (Tesla Motors) - SELL</h3>
<ul>
<li><strong>Moat</strong>: Narrow</li>
<li><strong>ROIC</strong>: -2%</li>
<li><strong>Debt/Equity</strong>: 1.5</li>
<li><strong>FCF Yield</strong>: 1%</li>
<li><strong>Valuation</strong>: Overvalued</li>
</ul>
    """
    formatted = format_stock_cards(html_input)
    assert 'border-left: 5px solid #ef4444;' in formatted
    assert "TSLA" in formatted
    assert "Tesla Motors" in formatted
    assert "SELL" in formatted
    assert "Narrow" in formatted
    assert "-2%" in formatted
    assert "1.5" in formatted
    assert "1%" in formatted
    assert "Overvalued" in formatted


def test_build_html_body_styling():
    markdown_content = """
## Macro Section
Some paragraph text here.

### [COMPANY UPDATES]
Another paragraph.

    AHP-TOPSIS Table ASCII content
    Row 1
    Row 2
    """
    html_body = build_html_body("Test Subject", markdown_content)

    # Check paragraph styling
    assert 'style="margin-bottom: 16px; line-height: 1.8; text-align: left;"' in html_body

    # Check header styling
    assert 'style="font-size: 1.35rem; font-weight: 800; color: #0f172a; margin-top: 40px; margin-bottom: 16px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; text-transform: uppercase; text-align: left;"' in html_body
    assert 'style="font-size: 1.15rem; font-weight: 700; color: #1e293b; margin-top: 24px; margin-bottom: 12px; text-align: left;"' in html_body

    # Check pre styling for code block
    assert 'style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.82rem; line-height: 1.35; overflow-x: auto; margin-bottom: 24px; text-align: left; color: #0f172a; white-space: pre;"' in html_body


def test_extract_tldr_decimal_splitting():
    markdown_content = """
## [GLOBAL NARRATIVE]
CPI increased by 3.2% last month. The Fed is expected to pause rate hikes. This is another sentence.
    """
    html_block = extract_tldr(markdown_content)
    # Check that "3.2%" wasn't split.
    assert "3.2% last month" in html_block
    assert "CPI increased by 3.2% last month." in html_block
    assert "The Fed is expected to pause rate hikes." in html_block


def test_extract_tldr_macro_dashboard_heading():
    markdown_content = """
## [MACRO DASHBOARD]
Inflation remains persistent at 4.1%. Unemployment rates are still low at 3.5%.
    """
    html_block = extract_tldr(markdown_content)
    assert "Inflation remains persistent at 4.1%." in html_block
    assert "Unemployment rates are still low at 3.5%." in html_block


def test_extract_tldr_macro_and_scouted():
    markdown_content = """
## [MACRO & GEOPOLITICAL BRIEFING]
US inflation cooled to 2.9% YoY while the ECB signaled caution on eurozone manufacturing. China announced targeted fiscal support.

## [SCOUTED OPPORTUNITIES]
1. **ASML** - Monopoly in EUV lithography.
2. **MSFT** - Enterprise cloud moat.
    """
    html_block = extract_tldr(markdown_content)
    assert "US inflation cooled to 2.9% YoY" in html_block
    assert "ASML, MSFT" in html_block


def test_format_stock_cards_new_layout():
    html_input = """
<h3>AAPL — Apple Inc.</h3>
<p><strong>Valuation Category: B (Hyper-Growth / Tech Platform) → Reverse DCF</strong></p>
<ul>
<li><strong>ROIC: 49–69%</strong> — Among the highest of any company in human history.</li>
<li><strong>Debt/Equity: ~0.85 (market-adjusted)</strong> — Book equity is negative.</li>
<li><strong>FCF Yield: ~3.0%</strong> — Below our 5% target.</li>
<li><strong>P/E: 35.8x vs. 5-yr avg ~28x</strong> — Trading at a 27% premium.</li>
<li><strong>Action: HOLD</strong> — Exceptional quality, but current P/E represents premium.</li>
</ul>
    """
    formatted = format_stock_cards(html_input)
    assert 'border-left: 5px solid #d97706;' in formatted
    assert "AAPL" in formatted
    assert "Apple Inc." in formatted
    assert "HOLD" in formatted
    assert "49" in formatted
    assert "~0.85" in formatted
    assert "~3.0%" in formatted
    assert "35.8x" in formatted
    assert "Exceptional quality" in formatted


def test_run_daily_notification_sends_email_only():
    with patch("notifier.glob.glob", return_value=["/fake/2026-10-21-report.md"]), \
         patch("builtins.open", mock_open(read_data="# Daily Report")), \
         patch("notifier.send_email", return_value=True) as mock_email, \
         patch("notifier.send_telegram") as mock_telegram:
        run_daily_notification("/fake")
        mock_email.assert_called_once()
        mock_telegram.assert_not_called()


def test_run_weekly_notification_sends_email_with_weekly_flag():
    with patch("notifier.glob.glob", return_value=["/fake/2026-10-24-weekly-audit.md"]), \
         patch("builtins.open", mock_open(read_data="# Weekly Report")), \
         patch("notifier.send_email", return_value=True) as mock_email:
        from notifier import run_weekly_notification
        run_weekly_notification("/fake")
        mock_email.assert_called_once()
        args, kwargs = mock_email.call_args
        assert "Weekly Watchlist Audit" in args[0]
        assert kwargs.get("is_weekly") is True


def test_build_html_body_weekly_badges_and_header():
    md = """
## [EXECUTIVE WATCHLIST PRUNING]
- **NOW**: **ACTIVE** (High Conviction)
- **INTC**: **DISMISSED** (Eroding foundry economics)
    """
    html = build_html_body("Weekly Audit", md, is_weekly=True)
    assert "WEEKLY WATCHLIST AUDIT & DEEP SCOUR" in html
    assert "Weekly Watchlist Audit Executive Summary" in html
    assert "ACTIVE" in html
    assert "DISMISSED" in html
    assert 'border: 1px solid #10b981;' in html
    assert 'border: 1px solid #cbd5e1;' in html


def test_format_stock_cards_does_not_swallow_macro_header():
    html_input = """
<h3>Regional Developments Across Major Economies</h3>
<p>1. United States (US):<br>2. Monetary Policy & Inflation: Benchmark 10 year U.S. Treasury yields hover near multi</p>
<h3>ADBE (Adobe Inc.) - BUY</h3>
<ul>
<li>Moat: Wide (Creative Cloud and Document Cloud standard formats, massive switching costs)</li>
<li>ROIC: 27.5% (Op Margin: 34.8%)</li>
<li>Debt/Equity: 0.57</li>
<li>FCF Yield: 9.6% (Growing)</li>
<li>Valuation: P/E 14.7x (5Y Avg: N/A | Fwd: 9.6x)</li>
<li>Note: Adobe continues converting its digital creation monopoly into massive free cash flows.</li>
</ul>
    """
    formatted = format_stock_cards(html_input)
    # Ensure Regional Developments remains outside the stock card
    assert "Regional Developments Across Major Economies</h3>" in formatted
    # Ensure Adobe is cleanly isolated as its own card
    assert "ADBE</h3>" in formatted
    assert "Adobe Inc." in formatted
    assert "BUY" in formatted
    assert "27.5%" in formatted
    # Check that badge has centered styles
    assert "text-align: center" in formatted
    assert "display: inline-block" in formatted


def test_normalize_scouted_opportunities_removes_dense_numbered_bullets():
    from notifier import normalize_scouted_opportunities
    md_input = """
## [SCOUTED OPPORTUNITIES]

Today's top 3 scouted high-quality peaceful opportunities selected for strong moats:

1. ZTS (Zoetis Inc.) - BUY
2. Sector / Industry: Healthcare / Drug Manufacturers
3. Current Price: $81.03 USD (52W Range: $68.77 - $147.93)
4. Moat: Wide (Patented veterinary medications)
5. Financial Health: ROIC 22.1% (5Y Median), Operating Margin 40.7%, Debt/Equity 2.77, FCF Yield 6.82% (Growing)
6. Valuation: Trailing P/E 13.33x | Forward P/E 12.38x
7. Recent News & Catalysts: Supported by defensive healthcare sector rotation.

8. MSFT (Microsoft Corporation) - BUY
9. Sector / Industry: Technology / Software
10. Current Price: $524.51 USD
11. Moat: Wide (Dominant Office 365)
12. Financial Health: ROIC 27.1%, Debt/Equity 0.13, FCF Yield 1.72% (Growing)
13. Valuation: Trailing P/E 29.22x
14. Recent News & Catalysts: Microsoft announced enterprise rollout.
    """
    normalized = normalize_scouted_opportunities(md_input)
    assert "### ZTS (Zoetis Inc.) - BUY" in normalized
    assert "### MSFT (Microsoft Corporation) - BUY" in normalized
    assert "Wide (Patented veterinary medications)" in normalized
    assert "ROIC: 22.1%" in normalized
    assert "Debt/Equity: 2.77" in normalized
    assert "Trailing P/E 13.33x" in normalized
    assert "Supported by defensive healthcare sector rotation." in normalized
    # Numbered list entries should be gone from the card markdown
    assert "1. ZTS" not in normalized
    assert "8. MSFT" not in normalized


def test_scorecard_summary_and_table_polishing():
    md_input = """
## [SCOUTING PERFORMANCE]

Scorecard Summary
- Total Scouted Picks: 51
- Overall Win Rate: 64.71% (33 positive / 1 neutral / 17 negative)
- Average Return Since Day-1: +10.64%
- Top Performer: ACN (+94.85%)
- Lagging Performer: ADBE (-45.04%)

| Ticker | Company Name | Initial Price | Current Price | Return % | Days Tracked | Times Recommended |
|---|---|---|---|---|---|---|
| ACN | Accenture plc | $127.98 | $249.37 | +94.85% | 127 | 73 |
| ADBE | Adobe Inc. | $480.00 | $263.82 | -45.04% | 152 | 102 |
    """
    html = build_html_body("Daily Report", md_input)
    # Check Scorecard KPI Grid is present without bullet list
    assert "Total Scouted" in html
    assert "51" in html
    assert "64.71%" in html
    assert "+10.64%" in html
    assert "ACN" in html
    assert "<li>Total Scouted Picks: 51</li>" not in html
    # Check Table styling has pills
    assert "+94.85%</span>" in html
    assert "-45.04%</span>" in html
    assert "#ecfdf5" in html  # Green return pill
    assert "#fef2f2" in html  # Red return pill
    # Check centered indication badge styles
    assert "text-align: center" in html


def test_format_regional_developments_removes_numbers_and_creates_cards():
    from notifier import format_regional_developments
    md_input = """
### Regional Developments Across Major Economies

1. **United States (US)**:
   - **Monetary Policy & Inflation**: Benchmark 10-year Treasury yields hover near 5.15%.
   - **Economic Activity**: GDP tracking near 4.0% annualized.

2. **European Union (EU)**:
   - **Inflation & Sovereign Pressures**: Eurozone growth near 1.1% for 2026.
   - **Trade Safeguards**: Strict Made in Europe rules planned.

3. **China**:
   - **Growth Resilience**: GDP growth surprise of 4.5% YoY.

4. **Japan**:
   - **Policy Normalization**: BOJ rate at 1.25%.
    """
    formatted = format_regional_developments(md_input)
    # Ensure numbered list markers are completely removed
    assert "1. **United States" not in formatted
    assert "2. **European Union" not in formatted
    assert "3. **China" not in formatted
    assert "4. **Japan" not in formatted
    # Check that regional cards with flags and colored borders exist
    assert "🇺🇸 United States (US)" in formatted
    assert "🇪🇺 European Union (EU)" in formatted
    assert "🇨🇳 China" in formatted
    assert "🇯🇵 Japan" in formatted
    assert "border-left: 5px solid #3b82f6" in formatted  # US card
    assert "Monetary Policy & Inflation:" in formatted
    assert "Benchmark 10-year Treasury yields hover near 5.15%." in formatted

    # Test with level-4 heading markdown syntax as well
    md_heading_input = """
### Regional Developments Across Major Economies

#### 🇺🇸 United States (US)
- **Monetary Policy & Inflation**: Benchmark yields near 5.15%.

#### 🇪🇺 European Union (EU)
- **Inflation & Sovereign Pressures**: Eurozone growth near 1.1%.
    """
    formatted_headings = format_regional_developments(md_heading_input)
    assert "🇺🇸 United States (US)" in formatted_headings
    assert "🇪🇺 European Union (EU)" in formatted_headings
    assert "border-left: 5px solid #3b82f6" in formatted_headings
    assert "Monetary Policy & Inflation:" in formatted_headings


