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
    assert "ACTIVE" in html
    assert "DISMISSED" in html
    assert 'border: 1px solid #10b981;' in html
    assert 'border: 1px solid #cbd5e1;' in html
