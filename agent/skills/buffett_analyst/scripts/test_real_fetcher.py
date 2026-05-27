#!/usr/bin/env python3
"""
Unit tests for YFinanceFetcher.
"""

import unittest
import sys
import os

# Adjust path to import data_fetcher
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_fetcher import YFinanceFetcher

class TestYFinanceFetcher(unittest.TestCase):
    def setUp(self):
        self.fetcher = YFinanceFetcher()

    def test_fetch_aapl(self):
        """
        Verify that AAPL data is fetched and populated with positive values.
        """
        data = self.fetcher.fetch_data("AAPL")
        self.assertIsNotNone(data)
        self.assertEqual(data.ticker, "AAPL")
        self.assertEqual(data.name, "Apple Inc.")
        self.assertIn("Apple", data.name)
        
        # Apple should have positive ROIC and manageable Debt/Equity
        self.assertGreater(data.roic, 0.0)
        self.assertGreaterEqual(data.debt_to_equity, 0.0)
        self.assertGreater(data.current_price, 0.0)
        
        # Intrinsic value should be positive and computed
        self.assertFalse(data.is_too_hard)
        self.assertGreater(data.intrinsic_value, 0.0)
        self.assertGreater(data.bargain_price, 0.0)
        self.assertGreater(data.fair_price, 0.0)
        self.assertGreater(data.expensive_price, 0.0)

    def test_fetch_invalid_ticker(self):
        """
        Verify that an invalid ticker is classified as 'Too Hard' and doesn't crash the script.
        """
        data = self.fetcher.fetch_data("INVALIDTICKER12345")
        self.assertIsNotNone(data)
        self.assertTrue(data.is_too_hard)
        self.assertEqual(data.intrinsic_value, 0.0)

    def test_fetch_nvda_hypergrowth(self):
        """
        Verify that NVDA is categorized as Reverse DCF and yields valid boundaries.
        """
        data = self.fetcher.fetch_data("NVDA")
        self.assertIsNotNone(data)
        self.assertEqual(data.ticker, "NVDA")
        self.assertEqual(data.valuation_methodology, "Reverse DCF")
        self.assertGreater(data.implied_growth_rate, 0.0)
        self.assertGreater(data.intrinsic_value, 0.0)
        self.assertGreater(data.bargain_price, 0.0)
        self.assertGreater(data.fair_price, 0.0)
        self.assertGreater(data.expensive_price, 0.0)

    def test_fetch_intc_cyclical(self):
        """
        Verify that INTC (cyclical/low ROIC) is evaluated using Mid-Cycle Normalized Multiple.
        """
        data = self.fetcher.fetch_data("INTC")
        self.assertIsNotNone(data)
        self.assertEqual(data.ticker, "INTC")
        self.assertEqual(data.valuation_methodology, "Mid-Cycle Normalized")
        self.assertGreater(data.intrinsic_value, 0.0)
        self.assertGreater(data.bargain_price, 0.0)
        self.assertGreater(data.fair_price, 0.0)
        self.assertGreater(data.expensive_price, 0.0)

if __name__ == "__main__":
    unittest.main()
