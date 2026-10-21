#!/usr/bin/env python3
"""
CLI tool to fetch a clean financial performance & moat proxy snapshot for one or more tickers.
Usage: python evaluate_stock.py <TICKER_1> [TICKER_2 ...]
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_fetcher import YFinanceFetcher


def format_snapshot(data) -> str:
    peaceful_str = "PEACEFUL" if data.is_peaceful else "NON-PEACEFUL (EXCLUDED - Defense/Surveillance)"
    pe_5y_str = f"{data.pe_5yr_avg:.2f}" if data.pe_5yr_avg > 0 else "N/A"
    fwd_pe_str = f"{data.forward_pe:.2f}" if data.forward_pe > 0 else "N/A"
    cur_pe_str = f"{data.current_pe:.2f}" if data.current_pe > 0 else "N/A"

    lines = [
        f"=== STOCK SNAPSHOT: {data.ticker} ===",
        f"Name: {data.name}",
        f"Sector / Industry: {data.sector} / {data.industry}",
        f"Peaceful Status: {peaceful_str}",
        f"Current Price: {data.current_price:.2f} {data.currency} (52W Range: {data.low_52w:.2f} - {data.high_52w:.2f})",
        "--- Moat & Profitability Proxies ---",
        f"Gross Margin: {data.gross_margin * 100:.1f}%",
        f"Operating Margin: {data.operating_margin * 100:.1f}%",
        f"ROIC (5Y Median): {data.roic * 100:.1f}%",
        f"ROE: {data.roe * 100:.1f}%",
        "--- Financial Health & Growth ---",
        f"Debt to Equity: {data.debt_to_equity:.2f}",
        f"FCF Yield: {data.fcf_yield * 100:.2f}%",
        f"FCF Trend: {data.fcf_trend}",
        f"Revenue Growth (YoY): {data.revenue_growth_yoy * 100:.1f}%",
        f"Revenue CAGR (3Y): {data.revenue_cagr_3yr * 100:.1f}%",
        "--- Relative Valuation Context ---",
        f"Trailing P/E: {cur_pe_str} (5Y Avg: {pe_5y_str} | Forward P/E: {fwd_pe_str})",
    ]
    if data.error_message:
        lines.append(f"Warning: {data.error_message}")
    lines.append("=" * 35)
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Error: Missing ticker symbol.", file=sys.stderr)
        print("Usage: python evaluate_stock.py <TICKER> [TICKER2 ...]", file=sys.stderr)
        sys.exit(1)

    tickers = [arg.strip().upper() for arg in sys.argv[1:] if arg.strip()]
    fetcher = YFinanceFetcher()

    for ticker in tickers:
        data = fetcher.fetch_data(ticker)
        if not data:
            print(f"Error: No data retrieved for ticker '{ticker}'.", file=sys.stderr)
            continue
        print(format_snapshot(data))


if __name__ == "__main__":
    main()
