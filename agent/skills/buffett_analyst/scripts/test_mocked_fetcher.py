#!/usr/bin/env python3
"""
Unit tests for simplified YFinanceFetcher financial snapshot.
"""

import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_fetcher import YFinanceFetcher, StockData, is_peaceful_stock


class TestSimplifiedFetcher(unittest.TestCase):
    def setUp(self):
        self.fetcher = YFinanceFetcher()

    def test_peaceful_check(self):
        self.assertTrue(is_peaceful_stock("Consumer Electronics", "Apple Inc.", "AAPL"))
        self.assertFalse(is_peaceful_stock("Aerospace & Defense", "Lockheed Martin", "LMT"))
        self.assertFalse(is_peaceful_stock("Software - Infrastructure", "Palantir Technologies", "PLTR"))

    @patch("data_fetcher.yf.Ticker")
    def test_fetch_snapshot_metrics(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "longName": "Apple Inc.",
            "industry": "Consumer Electronics",
            "sector": "Technology",
            "currentPrice": 200.0,
            "currency": "USD",
            "fiftyTwoWeekLow": 160.0,
            "fiftyTwoWeekHigh": 230.0,
            "trailingPE": 30.0,
            "forwardPE": 26.5,
            "fiveYearAvgPE": 28.0,
            "marketCap": 3000000000000.0,
            "returnOnEquity": 1.45,
            "grossMargins": 0.46,
            "operatingMargins": 0.31,
            "revenueGrowth": 0.08,
        }

        dates = pd.to_datetime(["2025-09-30", "2024-09-30", "2023-09-30", "2022-09-30"])
        mock_ticker.income_stmt = pd.DataFrame(
            {
                dates[0]: [120e9, 25e9, 125e9, 400e9],
                dates[1]: [115e9, 24e9, 120e9, 380e9],
                dates[2]: [110e9, 22e9, 115e9, 360e9],
                dates[3]: [105e9, 20e9, 110e9, 330e9],
            },
            index=["EBIT", "TaxProvision", "PretaxIncome", "TotalRevenue"],
        )
        mock_ticker.balance_sheet = pd.DataFrame(
            {
                dates[0]: [60e9, 100e9],
                dates[1]: [62e9, 105e9],
                dates[2]: [60e9, 110e9],
                dates[3]: [55e9, 115e9],
            },
            index=["StockholdersEquity", "TotalDebt"],
        )
        mock_ticker.cashflow = pd.DataFrame(
            {
                dates[0]: [110e9],
                dates[1]: [100e9],
                dates[2]: [95e9],
                dates[3]: [90e9],
            },
            index=["FreeCashFlow"],
        )
        mock_ticker_cls.return_value = mock_ticker

        data = self.fetcher.fetch_data("AAPL")
        self.assertIsNotNone(data)
        self.assertEqual(data.ticker, "AAPL")
        self.assertEqual(data.name, "Apple Inc.")
        self.assertTrue(data.is_peaceful)
        self.assertAlmostEqual(data.gross_margin, 0.46)
        self.assertAlmostEqual(data.operating_margin, 0.31)
        self.assertGreater(data.roic, 0.50)
        self.assertAlmostEqual(data.debt_to_equity, 100e9 / 60e9, places=2)
        self.assertAlmostEqual(data.fcf_yield, 110e9 / 3000e9, places=4)
        self.assertEqual(data.fcf_trend, "Growing")
        self.assertGreater(data.revenue_cagr_3yr, 0.05)


if __name__ == "__main__":
    unittest.main()
