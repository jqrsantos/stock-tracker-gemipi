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

@dataclass
class StockData:
    ticker: str
    roic: float
    debt_to_equity: float
    fcf_yield: float
    current_pe: float
    pe_5yr_avg: float

class DataFetcher:
    """
    Fetches financial data for stocks.
    Mock implementation for Task 3.
    """
    def fetch_data(self, ticker: str) -> Optional[StockData]:
        # Mocked data for demonstration
        # In Task 3, we mock the data fetching or use a simple placeholder.
        mock_data = {
            "NVDA": StockData("NVDA", 0.45, 0.2, 0.03, 75, 50),
            "EDP.SG": StockData("EDP.SG", 0.08, 1.5, 0.06, 15, 18),
            "AAPL": StockData("AAPL", 0.25, 0.8, 0.06, 25, 28),
            "KO": StockData("KO", 0.12, 1.2, 0.04, 24, 22),
            "MSFT": StockData("MSFT", 0.20, 0.4, 0.05, 30, 32),
            "GOOGL": StockData("GOOGL", 0.18, 0.1, 0.07, 22, 25),
        }
        
        if ticker in mock_data:
            return mock_data[ticker]
        
        # Generic mock for other tickers (Passes Buffett health check)
        return StockData(ticker, 0.18, 0.4, 0.06, 18, 22)

class PortfolioEvaluator:
    """
    Evaluates portfolio health using Buffett principles.
    """
    def __init__(self, fetcher: DataFetcher):
        self.fetcher = fetcher

    def get_unique_tickers(self) -> List[str]:
        """
        Fetches unique tickers from the portfolio API.
        """
        try:
            logger.info(f"Fetching transactions from {API_BASE_URL}/transactions/...")
            response = requests.get(f"{API_BASE_URL}/transactions/", timeout=5)
            response.raise_for_status()
            transactions = response.json()
            
            # Extract unique tickers, excluding CASH
            tickers = sorted(list(set(
                tx['ticker'] for tx in transactions 
                if tx.get('ticker') and tx['ticker'] != "CASH"
            )))
            
            logger.info(f"Found {len(tickers)} unique tickers in portfolio: {', '.join(tickers)}")
            return tickers
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch portfolio data: {e}")
            return []

    def evaluate(self, ticker: str) -> Dict:
        """
        Applies Buffett health check to a single ticker.
        """
        data = self.fetcher.fetch_data(ticker)
        if not data:
            return {"ticker": ticker, "advice": "N/A", "reason": "No data available"}

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
    fetcher = DataFetcher()
    evaluator = PortfolioEvaluator(fetcher)
    evaluator.run_report()
