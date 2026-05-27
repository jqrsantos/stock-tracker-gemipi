#!/usr/bin/env python3
"""
Task 3: Portfolio Integration Script
Evaluates current portfolio holdings based on Buffett-style fundamental health checks.
"""

import requests
import logging
import sys
import os
from typing import List, Dict, Optional, Any

# Adjust path to import data_fetcher
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_fetcher import YFinanceFetcher, StockData

logger = logging.getLogger(__name__)

# Constants
API_BASE_URL = "http://localhost:8000"

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

    def evaluate(self, ticker: str) -> Dict[str, Any]:
        """
        Applies Buffett health check to a single ticker with dynamic valuation methodology.
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
                "reason": f"Too Hard to value reliably ({data.valuation_methodology}): {data.error_message}"
            }

        # Buffett-style health check:
        # 1. ROIC > 15% (For hyper-growth and mature)
        roic_ok = data.roic > 0.15 or data.valuation_methodology == "Mid-Cycle Normalized"
        
        # 2. Debt/Equity < 1.0
        debt_ok = data.debt_to_equity < 1.0
        
        # 3. Valuation check: compare current price vs intrinsic/bounds
        # For Reverse DCF, if current price has a reasonable implied growth
        if data.valuation_methodology == "Reverse DCF":
            valuation_ok = data.implied_growth_rate < 0.25  # Implied growth less than 25% is solid
        else:
            valuation_ok = data.current_price < data.fair_price or data.fcf_yield > 0.05

        if roic_ok and debt_ok:
            if valuation_ok:
                advice = "BUY"
                reason = f"Strong fundamentals under {data.valuation_methodology}."
            else:
                advice = "HOLD"
                reason = f"Rich valuation under {data.valuation_methodology}."
        else:
            advice = "SELL"
            violations = []
            if not roic_ok: violations.append(f"Low ROIC ({data.roic*100:.1f}%)")
            if not debt_ok: violations.append(f"High Debt/Equity ({data.debt_to_equity:.2f})")
            reason = f"Weak fundamentals ({data.valuation_methodology}): " + ", ".join(violations)

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
            logger.warning("No tickers to evaluate. Ensure the API is running and has transaction data.")
            return

        print("\n" + "="*80)
        print(f"{'BUFFETT PORTFOLIO HEALTH REPORT':^80}")
        print("="*80)
        print(f"{'Ticker':<10} {'ROIC':<8} {'D/E':<8} {'FCF Yld':<8} {'Advice':<10} {'Reason'}")
        print("-"*80)

        for ticker in tickers:
            res = self.evaluate(ticker)
            
            # Format outputs safely in case of None values in dictionary
            roic_val = res.get('roic')
            roic_str = f"{roic_val * 100:>6.1f}%" if roic_val is not None else "   N/A "
            
            de_val = res.get('debt_to_equity')
            de_str = f"{de_val:>8.2f}" if de_val is not None else "    N/A "
            
            fcf_val = res.get('fcf_yield')
            fcf_str = f"{fcf_val * 100:>7.1f}%" if fcf_val is not None else "   N/A "
            
            print(f"{res['ticker']:<10} {roic_str} {de_str} {fcf_str} {res['advice']:<10} {res['reason']}")
        
        print("="*80)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    fetcher = YFinanceFetcher()
    evaluator = PortfolioEvaluator(fetcher)
    evaluator.run_report()
