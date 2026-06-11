import unittest
from unittest.mock import MagicMock
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from evaluate_portfolio import PortfolioEvaluator
from data_fetcher import StockData

class TestPortfolioEvaluator(unittest.TestCase):
    def test_evaluate_strict_valuation(self):
        fetcher = MagicMock()
        evaluator = PortfolioEvaluator(fetcher)
        
        # Overvalued stock with high FCF yield should be HOLD, not BUY
        data = StockData(
            ticker="TEST", name="Test", industry="Tech",
            roic=0.20, debt_to_equity=0.5, fcf_yield=0.08,
            current_pe=20.0, pe_5yr_avg=20.0, current_price=120.0,
            fair_price=100.0, bargain_price=70.0, valuation_methodology="Standard DCF"
        )
        fetcher.fetch_data.return_value = data
        res = evaluator.evaluate("TEST")
        self.assertEqual(res["advice"], "HOLD") # Strict check avoids BUY
