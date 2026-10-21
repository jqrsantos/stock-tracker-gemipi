#!/usr/bin/env python3
"""
Unit tests for evaluate_stock.py
"""

import unittest
from unittest.mock import patch
import io
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_fetcher import StockData
from evaluate_stock import main as evaluate_stock_main


class TestEvaluateStock(unittest.TestCase):
    @patch("sys.argv", ["evaluate_stock.py"])
    def test_missing_arguments(self):
        with self.assertRaises(SystemExit) as cm, patch("sys.stderr", new=io.StringIO()) as mock_stderr:
            evaluate_stock_main()
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error: Missing ticker symbol.", mock_stderr.getvalue())

    @patch("sys.argv", ["evaluate_stock.py", "AAPL"])
    @patch("data_fetcher.YFinanceFetcher.fetch_data")
    def test_successful_evaluation(self, mock_fetch):
        mock_fetch.return_value = StockData(
            ticker="AAPL",
            name="Apple Inc.",
            industry="Consumer Electronics",
            sector="Technology",
            is_peaceful=True,
            current_price=200.0,
            currency="USD",
            low_52w=160.0,
            high_52w=230.0,
            current_pe=30.0,
            forward_pe=26.5,
            pe_5yr_avg=28.0,
            gross_margin=0.46,
            operating_margin=0.31,
            roic=0.55,
            roe=1.45,
            debt_to_equity=1.67,
            fcf_yield=0.0367,
            revenue_growth_yoy=0.08,
            revenue_cagr_3yr=0.066,
            fcf_trend="Growing",
        )

        with patch("sys.stdout", new=io.StringIO()) as mock_stdout:
            evaluate_stock_main()

        output = mock_stdout.getvalue()
        self.assertIn("=== STOCK SNAPSHOT: AAPL ===", output)
        self.assertIn("Name: Apple Inc.", output)
        self.assertIn("Peaceful Status: PEACEFUL", output)
        self.assertIn("Gross Margin: 46.0%", output)
        self.assertIn("Operating Margin: 31.0%", output)
        self.assertIn("ROIC (5Y Median): 55.0%", output)
        self.assertIn("Trailing P/E: 30.00 (5Y Avg: 28.00 | Forward P/E: 26.50)", output)
        self.assertIn("FCF Trend: Growing", output)


if __name__ == "__main__":
    unittest.main()
