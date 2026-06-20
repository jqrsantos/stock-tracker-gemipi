import re
from notifier import build_html_body, format_stock_cards, extract_tldr

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
    assert '<div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid #10b981;' in formatted
    assert "AAPL" in formatted
    assert "Apple Inc" in formatted
    assert "BUY" in formatted
    assert "25%" in formatted
    assert "0.1" in formatted
    assert "5%" in formatted
    assert "Undervalued" in formatted

def test_format_stock_cards_sell():
    html_input = """
<h3>TSLA (Tesla Motors) - SELL</h3>
<ul>
<li><strong>ROIC</strong>: -2%</li>
<li><strong>Debt/Equity</strong>: 1.5</li>
<li><strong>FCF Yield</strong>: 1%</li>
<li><strong>Valuation</strong>: Overvalued</li>
</ul>
    """
    formatted = format_stock_cards(html_input)
    assert '<div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid #ef4444;' in formatted
    assert "TSLA" in formatted
    assert "Tesla Motors" in formatted
    assert "SELL" in formatted
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
