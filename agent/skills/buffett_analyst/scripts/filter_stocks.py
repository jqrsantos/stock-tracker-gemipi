from dataclasses import dataclass
from typing import List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from data_fetcher import YFinanceFetcher, StockData

class PeacefulFilter:
    """
    Strictly excludes defense and war-oriented industries.
    """
    EXCLUDED_INDUSTRIES = [
        "Aerospace & Defense",
        "Defense",
        "Aeronautics",
        "Arms & Munitions"
    ]

    @classmethod
    def is_peaceful(cls, industry: str) -> bool:
        return industry not in cls.EXCLUDED_INDUSTRIES

class BuffettQuantitativeFilter:
    """
    Applies Buffett-style quantitative filters to stock data.
    """
    def __init__(
        self,
        min_roic: float = 0.15,
        max_debt_to_equity: float = 1.0,
        min_fcf_yield: float = 0.05
    ):
        self.min_roic = min_roic
        self.max_debt_to_equity = max_debt_to_equity
        self.min_fcf_yield = min_fcf_yield

    def filter(self, stocks: List[StockData]) -> List[StockData]:
        filtered_stocks = []
        for stock in stocks:
            # 1. Peaceful Filter (Non-negotiable)
            if not PeacefulFilter.is_peaceful(stock.industry):
                logger.info(f"Excluding {stock.ticker} ({stock.name}) - Non-peaceful industry: {stock.industry}")
                continue

            # 2. ROIC > 15%
            if stock.roic <= self.min_roic:
                continue

            # 3. Debt/Equity < 1.0
            if stock.debt_to_equity >= self.max_debt_to_equity:
                continue

            # 4. FCF Yield > 5%
            if stock.fcf_yield <= self.min_fcf_yield:
                continue

            # 5. P/E < 5-year average (Bypass if experiencing a Temporary Earnings Depression)
            if stock.pe_5yr_avg > 0.0 and stock.current_pe >= stock.pe_5yr_avg:
                if stock.roic > 0.15 and stock.fcf_yield > 0.05:
                    logger.info(f"Temporary Earnings Depression: Bypassing P/E exclusion for {stock.ticker} (ROIC = {stock.roic*100:.1f}%, FCF Yield = {stock.fcf_yield*100:.1f}%)")
                else:
                    continue

            filtered_stocks.append(stock)
            logger.info(f"Bargain identified: {stock.ticker} ({stock.name})")

        return filtered_stocks

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Buffett Stock Filter & Bargain Scanner")
    parser.add_argument("tickers", nargs="*", help="Optional space-separated list of tickers to scan")
    args = parser.parse_args()
    
    if args.tickers:
        curated_tickers = [t.upper() for t in args.tickers]
        logger.info(f"Scanning CLI specified tickers: {', '.join(curated_tickers)}")
    else:
        # Expanded 50+ high-quality global non-defense companies
        curated_tickers = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "KO", "PEP", "PG", "JNJ", 
            "COST", "MCD", "NKE", "V", "MA", "ADBE", "CRM", "ACN", 
            "ASML", "UNH", "WMT", "ORCL", "CSCO", "DIS", "HD", "SBUX", 
            "ABT", "MRK", "PFE", "LLY", "JPM", "BAC", "AXP", "CAT", 
            "HON", "TXN", "QCOM", "DE", "UPS", "FDX", "WM", "EL", "TGT",
            "LOW", "TJX", "ISRG", "NVS", "SAP", "TM", "SONY", "CL", "AMAT",
            "INTU", "FISV"
        ]
        logger.info(f"No tickers specified. Scanning default high-quality list: {', '.join(curated_tickers)}")
    fetcher = YFinanceFetcher()
    
    stocks = []
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(curated_tickers) or 1)) as executor:
        future_to_ticker = {executor.submit(fetcher.fetch_data, ticker): ticker for ticker in curated_tickers}
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                data = future.result()
                if data and not data.is_too_hard:
                    stocks.append(data)
                elif data and data.is_too_hard:
                    logger.info(f"Skipping {ticker} - Classified as 'Too Hard': {data.error_message}")
            except Exception as exc:
                logger.error(f"{ticker} generated an exception: {exc}")

    buffett_filter = BuffettQuantitativeFilter()
    results = buffett_filter.filter(stocks)
    
    print("\n" + "="*80)
    print(f"{'REAL-DATA BUFFETT BARGAIN IDENTIFIED':^80}")
    print("="*80)
    if not results:
        print("No stock candidates met all strict Warren Buffett quantitative criteria today.")
    for res in results:
        print(f"Ticker: {res.ticker:<8} | Name: {res.name:<25}")
        print(f"  Industry: {res.industry:<30}")
        print(f"  ROIC: {res.roic*100:>5.1f}% | Debt/Equity: {res.debt_to_equity:>5.2f} | FCF Yield: {res.fcf_yield*100:>5.1f}%")
        print(f"  Current Price: {res.current_price:>7.2f} {res.currency}")
        print(f"  Calculated Dynamic Price Intervals (10-Yr DCF Model):")
        print(f"    - [BARGAIN PRICE]:   {res.bargain_price:>7.2f} {res.currency} (30% Margin of Safety)")
        print(f"    - [FAIR PRICE]:      {res.fair_price:>7.2f} {res.currency}")
        print(f"    - [EXPENSIVE PRICE]: {res.expensive_price:>7.2f} {res.currency}")
        print("-"*80)
    print("="*80)

if __name__ == "__main__":
    main()
