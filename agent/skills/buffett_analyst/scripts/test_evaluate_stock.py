#!/usr/bin/env python3
"""
Unit tests for evaluate_stock.py
"""

import unittest
from unittest.mock import MagicMock, patch
import io
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from evaluate_stock import main as evaluate_stock_main

class TestEvaluateStock(unittest.TestCase):
    @patch('sys.argv', ['evaluate_stock.py'])
    def test_missing_arguments(self):
        """Verify that the script exits with error code when no ticker is passed."""
        with self.assertRaises(SystemExit) as cm, patch('sys.stderr', new=io.StringIO()) as mock_stderr:
            evaluate_stock_main()
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Error: Missing ticker symbol.", mock_stderr.getvalue())

    @patch('sys.argv', ['evaluate_stock.py', 'AAPL'])
    @patch('data_fetcher.YFinanceFetcher.fetch_data')
    def test_successful_evaluation(self, mock_fetch):
        """Verify that a successful evaluation prints the correct data."""
        mock_data = MagicMock()
        mock_data.ticker = "AAPL"
        mock_data.name = "Apple Inc."
        mock_data.industry = "Consumer Electronics"
        mock_data.current_price = 150.0
        mock_data.currency = "USD"
        mock_data.roic = 0.25
        mock_data.debt_to_equity = 0.5
        mock_data.fcf_yield = 0.06
        mock_data.current_pe = 25.0
        mock_data.pe_5yr_avg = 22.0
        mock_data.valuation_methodology = "Standard DCF"
        mock_data.bargain_price = 105.0
        mock_data.fair_price = 150.0
        mock_data.expensive_price = 180.0
        mock_data.is_too_hard = False
        mock_data.error_message = ""
        mock_data.implied_growth_rate = 0.0
        
        mock_fetch.return_value = mock_data
        
        with patch('sys.stdout', new=io.StringIO()) as mock_stdout:
            evaluate_stock_main()
            
        output = mock_stdout.getvalue()
        self.assertIn("=== STOCK EVALUATION DATA ===", output)
        self.assertIn("Ticker: AAPL", output)
        self.assertIn("Name: Apple Inc.", output)
        self.assertIn("ROIC: 0.2500", output)
        self.assertIn("Valuation Methodology: Standard DCF", output)
        self.assertIn("Bargain Price: 105.00 USD", output)
        self.assertIn("Is Too Hard: False", output)
