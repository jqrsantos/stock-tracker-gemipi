#!/usr/bin/env python3
"""
CLI tool to evaluate a single stock using the Buffett Strategic Analyst's centralized valuation engine.
"""

import sys
import os

# Adjust path to import data_fetcher
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_fetcher import YFinanceFetcher

def main():
    if len(sys.argv) < 2:
        print("Error: Missing ticker symbol.", file=sys.stderr)
        print("Usage: python evaluate_stock.py <TICKER>", file=sys.stderr)
        sys.exit(1)
        
    ticker = sys.argv[1].strip().upper()
    
    fetcher = YFinanceFetcher()
    data = fetcher.fetch_data(ticker)
    
    if not data:
        print(f"Error: No data retrieved for ticker '{ticker}'.", file=sys.stderr)
        sys.exit(1)
        
    # Serialize data into structured text format easily consumed by the agent
    print("=== STOCK EVALUATION DATA ===")
    print(f"Ticker: {data.ticker}")
    print(f"Name: {data.name}")
    print(f"Industry: {data.industry}")
    print(f"Current Price: {data.current_price} {data.currency}")
    print(f"ROIC: {data.roic:.4f}")
    print(f"Debt to Equity: {data.debt_to_equity:.4f}")
    print(f"FCF Yield: {data.fcf_yield:.4f}")
    print(f"Current PE: {data.current_pe:.2f}")
    print(f"5-Year Avg PE: {data.pe_5yr_avg:.2f}")
    print(f"Valuation Methodology: {data.valuation_methodology}")
    print(f"Bargain Price: {data.bargain_price:.2f} {data.currency}")
    print(f"Fair Price: {data.fair_price:.2f} {data.currency}")
    print(f"Expensive Price: {data.expensive_price:.2f} {data.currency}")
    print(f"Is Too Hard: {data.is_too_hard}")
    print(f"Error Message: {data.error_message}")
    print(f"Implied Growth Rate: {data.implied_growth_rate:.4f}")
    print(f"Expected Growth Rate: {data.expected_growth_rate*100:.2f}%")
    print("=============================")

if __name__ == "__main__":
    main()
