#!/usr/bin/env python3
"""
Mocked unit tests for YFinanceFetcher to ensure robust offline testing.
"""

import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_fetcher import YFinanceFetcher

class TestYFinanceFetcherMocked(unittest.TestCase):
    def setUp(self):
        self.fetcher = YFinanceFetcher()

    @patch('yfinance.Ticker')
    def test_fetch_standard_dcf_mocked(self, mock_ticker_class):
        """
        Verify Standard DCF pipeline using fully mocked financial statement data.
        """
        mock_ticker = MagicMock()
        mock_ticker_class.return_value = mock_ticker
        
        # 1. Mock Ticker Info
        mock_ticker.info = {
            "longName": "Test Stable Corp",
            "industry": "Consumer Goods",
            "currentPrice": 100.0,
            "currency": "USD",
            "trailingPE": 15.0,
            "fiveYearAvgPE": 15.0,
            "sharesOutstanding": 10000000,
            "marketCap": 1000000000
        }
        
        # 2. Mock Balance Sheet (Equity = 500M, Debt = 200M, Cash = 100M -> Invested Capital = 600M)
        mock_ticker.balance_sheet = pd.DataFrame(
            [[500000000], [200000000], [100000000]],
            index=["StockholdersEquity", "TotalDebt", "CashAndCashEquivalents"],
            columns=["2023-12-31"]
        )
        
        # 3. Mock Income Statement (EBIT = 80M, Tax = 16.8M -> NOPAT = 63.2M)
        mock_ticker.income_stmt = pd.DataFrame(
            [[80000000], [16800000], [80000000]],
            index=["EBIT", "TaxProvision", "PretaxIncome"],
            columns=["2023-12-31"]
        )
        
        # 4. Mock Cashflow (FCF = 60M)
        mock_ticker.cashflow = pd.DataFrame(
            [[60000000]],
            index=["FreeCashFlow"],
            columns=["2023-12-31"]
        )
        
        # Execute
        data = self.fetcher.fetch_data("TEST")
        
        # Assertions
        self.assertIsNotNone(data)
        self.assertEqual(data.ticker, "TEST")
        self.assertEqual(data.valuation_methodology, "Standard DCF")
        self.assertFalse(data.is_too_hard)
        self.assertGreater(data.roic, 0.10)
        self.assertGreater(data.intrinsic_value, 0.0)
        self.assertGreater(data.bargain_price, 0.0)

    @patch('yfinance.Ticker')
    def test_fetch_too_hard_missing_data(self, mock_ticker_class):
        """
        Verify that missing sharesOutstanding or invalid pricing is set to 'Too Hard'.
        """
        mock_ticker = MagicMock()
        mock_ticker_class.return_value = mock_ticker
        
        mock_ticker.info = {
            "longName": "Incomplete Corp",
            "currentPrice": 0.0,
            "sharesOutstanding": None
        }
        mock_ticker.balance_sheet = pd.DataFrame()
        mock_ticker.income_stmt = pd.DataFrame()
        mock_ticker.cashflow = pd.DataFrame()
        
        data = self.fetcher.fetch_data("INCOMP")
        self.assertIsNotNone(data)
        self.assertTrue(data.is_too_hard)
        self.assertEqual(data.intrinsic_value, 0.0)

    @patch('yfinance.Ticker')
    def test_fetch_declining_fcf_is_mid_cycle(self, mock_ticker_class):
        """
        Verify that a stock with declining FCF that drops below 80% of median triggers Mid-Cycle Normalized.
        """
        mock_ticker = MagicMock()
        mock_ticker_class.return_value = mock_ticker
        
        mock_ticker.info = {
            "longName": "Declining Corp",
            "industry": "Consumer Goods",
            "currentPrice": 50.0,
            "currency": "USD",
            "trailingPE": 10.0,
            "fiveYearAvgPE": 10.0,
            "sharesOutstanding": 1000000,
            "marketCap": 50000000
        }
        
        # Decline FCF: newest is 60M (idx 0), oldest is 100M (idx 2)
        # cashflow index is newest to oldest
        mock_ticker.cashflow = pd.DataFrame(
            [[60000000, 80000000, 100000000], [60000000, 80000000, 100000000]], 
            index=["FreeCashFlow", "FreeCashFlow"],
            columns=["2023-12-31", "2022-12-31", "2021-12-31"]
        )
        mock_ticker.balance_sheet = pd.DataFrame(
            [[30000000, 30000000, 30000000], [10000000, 10000000, 10000000], [5000000, 5000000, 5000000]],
            index=["StockholdersEquity", "TotalDebt", "CashAndCashEquivalents"],
            columns=["2023-12-31", "2022-12-31", "2021-12-31"]
        )
        mock_ticker.income_stmt = pd.DataFrame(
            [[10000000, 10000000, 10000000], [2100000, 2100000, 2100000], [10000000, 10000000, 10000000]],
            index=["EBIT", "TaxProvision", "PretaxIncome"],
            columns=["2023-12-31", "2022-12-31", "2021-12-31"]
        )
        
        data = self.fetcher.fetch_data("DECL")
        self.assertIsNotNone(data)
        self.assertFalse(data.is_too_hard)
        self.assertEqual(data.valuation_methodology, "Mid-Cycle Normalized")
        
    @patch('yfinance.Ticker')
    def test_fetch_negative_median_fcf_is_too_hard(self, mock_ticker_class):
        """
        Verify that a stock with negative multi-year median FCF is marked as Too Hard.
        """
        mock_ticker = MagicMock()
        mock_ticker_class.return_value = mock_ticker
        
        mock_ticker.info = {
            "longName": "Negative FCF Corp",
            "industry": "Consumer Goods",
            "currentPrice": 50.0,
            "currency": "USD",
            "trailingPE": 10.0,
            "fiveYearAvgPE": 10.0,
            "sharesOutstanding": 1000000,
            "marketCap": 50000000
        }
        
        # FCF: [10M, -60M, -80M] -> Median is -60M
        # With fcf_history[0] = 10M, it bypasses the Category 2 fcf_history[0] <= 0 check
        mock_ticker.cashflow = pd.DataFrame(
            [[10000000, -60000000, -80000000], [10000000, -60000000, -80000000]], 
            index=["FreeCashFlow", "FreeCashFlow"],
            columns=["2023-12-31", "2022-12-31", "2021-12-31"]
        )
        mock_ticker.balance_sheet = pd.DataFrame(
            [[30000000, 30000000, 30000000], [10000000, 10000000, 10000000], [5000000, 5000000, 5000000]],
            index=["StockholdersEquity", "TotalDebt", "CashAndCashEquivalents"],
            columns=["2023-12-31", "2022-12-31", "2021-12-31"]
        )
        mock_ticker.income_stmt = pd.DataFrame(
            [[10000000, 10000000, 10000000], [2100000, 2100000, 2100000], [10000000, 10000000, 10000000]],
            index=["EBIT", "TaxProvision", "PretaxIncome"],
            columns=["2023-12-31", "2022-12-31", "2021-12-31"]
        )
        
        data = self.fetcher.fetch_data("NEG")
        self.assertIsNotNone(data)
        self.assertTrue(data.is_too_hard)
        self.assertIn("Negative multi-year median", data.error_message)

    @patch('yfinance.Ticker')
    def test_fetch_cash_rich_roic_fallback(self, mock_ticker_class):
        """
        Verify that a cash-rich stock does not get 0% ROIC due to negative invested capital.
        """
        mock_ticker = MagicMock()
        mock_ticker_class.return_value = mock_ticker
        
        # Cash-rich setup: equity = 10M, debt = 20M, cash = 35M -> invested_capital = -5M
        mock_ticker.info = {
            "longName": "Cash Rich Corp",
            "industry": "Consumer Goods",
            "currentPrice": 50.0,
            "currency": "USD",
            "trailingPE": 15.0,
            "fiveYearAvgPE": 15.0,
            "sharesOutstanding": 1000000,
            "marketCap": 50000000
        }
        mock_ticker.cashflow = pd.DataFrame(
            [[10000000, 10000000, 10000000], [10000000, 10000000, 10000000]], 
            index=["FreeCashFlow", "FreeCashFlow"],
            columns=["2023-12-31", "2022-12-31", "2021-12-31"]
        )
        mock_ticker.balance_sheet = pd.DataFrame(
            [[10000000, 10000000, 10000000], [20000000, 20000000, 20000000], [35000000, 35000000, 35000000]],
            index=["StockholdersEquity", "TotalDebt", "CashAndCashEquivalents"],
            columns=["2023-12-31", "2022-12-31", "2021-12-31"]
        )
        mock_ticker.income_stmt = pd.DataFrame(
            [[10000000, 10000000, 10000000], [2100000, 2100000, 2100000], [10000000, 10000000, 10000000]],
            index=["EBIT", "TaxProvision", "PretaxIncome"],
            columns=["2023-12-31", "2022-12-31", "2021-12-31"]
        )
        
        data = self.fetcher.fetch_data("RICH")
        self.assertIsNotNone(data)
        # NOPAT = 7.9M. Fallback Invested Capital = Equity + Debt = 30M.
        # Expected ROIC = 7.9M / 30M = ~26.3%
        self.assertGreater(data.roic, 0.0)
        self.assertAlmostEqual(data.roic, 7900000.0 / 30000000.0, places=4)

    @patch('yfinance.Ticker')
    def test_fetch_flat_cagr(self, mock_ticker_class):
        """
        Verify that flat FCF (CAGR = 0.0) calculates expected growth rate of 0.0 instead of defaulting to 8%.
        """
        mock_ticker = MagicMock()
        mock_ticker_class.return_value = mock_ticker
        
        mock_ticker.info = {
            "longName": "Flat Corp",
            "industry": "Utilities",
            "currentPrice": 100.0,
            "currency": "USD",
            "trailingPE": 15.0,
            "fiveYearAvgPE": 15.0,
            "sharesOutstanding": 1000000,
            "marketCap": 100000000
        }
        mock_ticker.cashflow = pd.DataFrame(
            [[50000000, 50000000, 50000000]], 
            index=["FreeCashFlow"],
            columns=["2023-12-31", "2022-12-31", "2021-12-31"]
        )
        mock_ticker.balance_sheet = pd.DataFrame(
            [[50000000, 50000000, 50000000], [20000000, 20000000, 20000000], [10000000, 10000000, 10000000]],
            index=["StockholdersEquity", "TotalDebt", "CashAndCashEquivalents"],
            columns=["2023-12-31", "2022-12-31", "2021-12-31"]
        )
        mock_ticker.income_stmt = pd.DataFrame(
            [[10000000, 10000000, 10000000], [2100000, 2100000, 2100000], [10000000, 10000000, 10000000]],
            index=["EBIT", "TaxProvision", "PretaxIncome"],
            columns=["2023-12-31", "2022-12-31", "2021-12-31"]
        )
        
        data = self.fetcher.fetch_data("TESTFLAT")
        self.assertIsNotNone(data)
        self.assertEqual(data.expected_growth_rate, 0.0)

    @patch('yfinance.Ticker')
    def test_fetch_recent_negative_fcf_allowed(self, mock_ticker_class):
        """
        Verify that a stock with negative recent FCF but positive multi-year median FCF
        is not marked as Too Hard, but instead valued appropriately.
        """
        mock_ticker = MagicMock()
        mock_ticker_class.return_value = mock_ticker
        
        mock_ticker.info = {
            "longName": "Temporary Hiccup Corp",
            "industry": "Software",
            "currentPrice": 50.0,
            "currency": "USD",
            "trailingPE": 15.0,
            "fiveYearAvgPE": 15.0,
            "sharesOutstanding": 1000000,
            "marketCap": 50000000
        }
        
        # FCF: [-10M, 40M, 50M] -> Median is 40M, recent is -10M.
        mock_ticker.cashflow = pd.DataFrame(
            [[-10000000, 40000000, 50000000], [-10000000, 40000000, 50000000]], 
            index=["FreeCashFlow", "FreeCashFlow"],
            columns=["2023-12-31", "2022-12-31", "2021-12-31"]
        )
        mock_ticker.balance_sheet = pd.DataFrame(
            [[30000000, 30000000, 30000000], [10000000, 10000000, 10000000], [5000000, 5000000, 5000000]],
            index=["StockholdersEquity", "TotalDebt", "CashAndCashEquivalents"],
            columns=["2023-12-31", "2022-12-31", "2021-12-31"]
        )
        mock_ticker.income_stmt = pd.DataFrame(
            [[10000000, 10000000, 10000000], [2100000, 2100000, 2100000], [10000000, 10000000, 10000000]],
            index=["EBIT", "TaxProvision", "PretaxIncome"],
            columns=["2023-12-31", "2022-12-31", "2021-12-31"]
        )
        
        data = self.fetcher.fetch_data("HICCUP")
        self.assertIsNotNone(data)
        # Should not be 'too hard' simply due to recent negative FCF
        self.assertFalse(data.is_too_hard)

if __name__ == "__main__":
    unittest.main()
