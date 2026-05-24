#!/usr/bin/env python3
"""
Task 3: Portfolio Integration Script
Evaluates current portfolio holdings based on Buffett-style fundamental health checks.
"""

import requests
import logging
import sys
from typing import List, Dict, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Constants
API_BASE_URL = "http://localhost:8000"

from data_fetcher import YFinanceFetcher, StockData

class PortfolioEvaluator:
    """
    Evaluates portfolio health using Buffett principles.
    """
    def __init__(self, fetcher: YFinanceFetcher):
        self.fetcher = fetcher

    def get_unique_tickers(self) -> List[str]:
        """
        Fetches only currently held tickers from the portfolio API.
        """
        try:
            logger.info(f"Fetching open positions from {API_BASE_URL}/portfolio/holdings...")
            response = requests.get(f"{API_BASE_URL}/portfolio/holdings", timeout=5)
            response.raise_for_status()
            holdings = response.json()
            
            # holdings is a dict {ticker: quantity}
            tickers = sorted(list(holdings.keys()))
            
            logger.info(f"Found {len(tickers)} open positions: {', '.join(tickers)}")
            return tickers
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch holdings data: {e}")
            return []

    def evaluate(self, ticker: str) -> Dict:
        """
        Applies Buffett health check to a single ticker.
        """
        data = self.fetcher.fetch_data(ticker)
        if not data:
            return {"ticker": ticker, "advice": "N/A", "reason": "No data available"}

        if data.is_too_hard:
            return {
                "ticker": ticker,
                "roic": data.roic,
                "debt_to_equity": data.debt_to_equity,
                "fcf_yield": data.fcf_yield,
                "advice": "HOLD",
                "reason": f"Too Hard to value reliably: {data.error_message}"
            }

        # Buffett-style health check:
        # 1. ROIC > 15%
        roic_ok = data.roic > 0.15
        
        # 2. Debt/Equity < 1.0
        debt_ok = data.debt_to_equity < 1.0
        
        # 3. Valuation check (Price vs. FCF/Owner Earnings)
        # Using FCF yield > 5% or P/E < 5yr Avg as proxy
        valuation_ok = data.current_pe < data.pe_5yr_avg or data.fcf_yield > 0.05

        if roic_ok and debt_ok:
            if valuation_ok:
                advice = "BUY"
                reason = "Strong fundamentals and attractive valuation."
            else:
                advice = "HOLD"
                reason = "Strong fundamentals but valuation is rich."
        else:
            advice = "SELL"
            violations = []
            if not roic_ok: violations.append(f"Low ROIC ({data.roic*100:.1f}%)")
            if not debt_ok: violations.append(f"High Debt/Equity ({data.debt_to_equity:.2f})")
            reason = "Weak fundamentals: " + ", ".join(violations)

        return {
            "ticker": ticker,
            "roic": data.roic,
            "debt_to_equity": data.debt_to_equity,
            "fcf_yield": data.fcf_yield,
            "advice": advice,
            "reason": reason
        }

    def run_report(self):
        """
        Executes the portfolio evaluation and outputs a summary.
        """
        tickers = self.get_unique_tickers()
        if not tickers:
            print("\n[!] No tickers to evaluate. Ensure the API is running and has transaction data.")
            return

        print("\n" + "="*80)
        print(f"{'BUFFETT PORTFOLIO HEALTH REPORT':^80}")
        print("="*80)
        print(f"{'Ticker':<10} {'ROIC':<8} {'D/E':<8} {'FCF Yld':<8} {'Advice':<10} {'Reason'}")
        print("-"*80)

        for ticker in tickers:
            res = self.evaluate(ticker)
            print(f"{res['ticker']:<10} {res.get('roic', 0)*100:>6.1f}% {res.get('debt_to_equity', 0):>8.2f} {res.get('fcf_yield', 0)*100:>7.1f}% {res['advice']:<10} {res['reason']}")
        
        print("="*80)

if __name__ == "__main__":
    fetcher = YFinanceFetcher()
    evaluator = PortfolioEvaluator(fetcher)
    evaluator.run_report()
