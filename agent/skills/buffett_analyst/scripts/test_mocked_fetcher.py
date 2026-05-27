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
        balance_sheet_data = {
            "StockholdersEquity": [500000000],
            "TotalDebt": [200000000],
            "CashAndCashEquivalents": [100000000]
        }
        mock_ticker.balance_sheet = pd.DataFrame(balance_sheet_data, index=balance_sheet_data.keys())
        
        # 3. Mock Income Statement (EBIT = 80M, Tax = 16.8M -> NOPAT = 63.2M)
        income_stmt_data = {
            "EBIT": [80000000],
            "TaxProvision": [16800000],
            "PretaxIncome": [80000000]
        }
        mock_ticker.income_stmt = pd.DataFrame(income_stmt_data, index=income_stmt_data.keys())
        
        # 4. Mock Cashflow (FCF = 60M)
        cashflow_data = {
            "FreeCashFlow": [60000000]
        }
        mock_ticker.cashflow = pd.DataFrame(cashflow_data, index=cashflow_data.keys())
        
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

if __name__ == "__main__":
    unittest.main()
