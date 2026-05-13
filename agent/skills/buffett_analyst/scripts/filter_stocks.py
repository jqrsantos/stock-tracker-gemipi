from dataclasses import dataclass
from typing import List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class StockData:
    ticker: str
    name: str
    industry: str
    roic: float  # Return on Invested Capital (as decimal, e.g., 0.16 for 16%)
    debt_to_equity: float
    fcf_yield: float  # Free Cash Flow Yield (as decimal, e.g., 0.06 for 6%)
    current_pe: float
    pe_5yr_avg: float

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

            # 5. P/E < 5-year average
            if stock.current_pe >= stock.pe_5yr_avg:
                continue

            filtered_stocks.append(stock)
            logger.info(f"Bargain identified: {stock.ticker} ({stock.name})")

        return filtered_stocks

class DataFetcher:
    """
    Interface for fetching stock data.
    """
    def fetch_stocks(self, tickers: List[str]) -> List[StockData]:
        raise NotImplementedError("Subclasses must implement fetch_stocks")

# Example of a Mock Data Fetcher for testing
class MockDataFetcher(DataFetcher):
    def __init__(self, mock_data: List[StockData]):
        self.mock_data = mock_data

    def fetch_stocks(self, tickers: List[str]) -> List[StockData]:
        # Filter mock data by tickers if provided, else return all
        if not tickers:
            return self.mock_data
        return [s for s in self.mock_data if s.ticker in tickers]

if __name__ == "__main__":
    # Example usage
    sample_data = [
        StockData(
            ticker="AAPL", name="Apple Inc.", industry="Consumer Electronics",
            roic=0.25, debt_to_equity=0.8, fcf_yield=0.06, current_pe=25, pe_5yr_avg=28
        ),
        StockData(
            ticker="LMT", name="Lockheed Martin", industry="Aerospace & Defense",
            roic=0.20, debt_to_equity=0.5, fcf_yield=0.07, current_pe=15, pe_5yr_avg=18
        ),
        StockData(
            ticker="KO", name="Coca-Cola", industry="Beverages",
            roic=0.12, debt_to_equity=1.2, fcf_yield=0.04, current_pe=24, pe_5yr_avg=22
        )
    ]
    
    fetcher = MockDataFetcher(sample_data)
    stocks = fetcher.fetch_stocks(["AAPL", "LMT", "KO"])
    
    buffett_filter = BuffettQuantitativeFilter()
    results = buffett_filter.filter(stocks)
    
    print("\nFiltered Results:")
    for res in results:
        print(f"- {res.ticker}: {res.name}")
