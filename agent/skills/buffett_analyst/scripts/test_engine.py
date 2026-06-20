# agent/skills/buffett_analyst/scripts/test_engine.py
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from engine import run_ahp, get_ahp_weights, run_topsis, generate_action_matrix, generate_ascii_table

class TestEngine(unittest.TestCase):
    def test_run_ahp_consistent(self):
        # A perfectly consistent 3x3 matrix
        pairwise = np.array([
            [1.0, 2.0, 4.0],
            [0.5, 1.0, 2.0],
            [0.25, 0.5, 1.0]
        ])
        weights, cr = run_ahp(pairwise)
        self.assertAlmostEqual(cr, 0.0, places=4)
        self.assertAlmostEqual(np.sum(weights), 1.0, places=4)
        self.assertTrue(weights[0] > weights[1])
        self.assertTrue(weights[1] > weights[2])

    def test_ahp_fallback(self):
        # A highly inconsistent 3x3 matrix (which should yield CR >= 0.10)
        pairwise = np.array([
            [1.0, 9.0, 1.0/9.0],
            [1.0/9.0, 1.0, 9.0],
            [9.0, 1.0/9.0, 1.0]
        ])
        weights = get_ahp_weights(pairwise)
        # CR should exceed 0.10, triggering fallback to equal weights [1/3, 1/3, 1/3]
        np.testing.assert_allclose(weights, np.array([1.0/3.0, 1.0/3.0, 1.0/3.0]), rtol=1e-5)

    def test_run_topsis(self):
        # 3 alternatives, 2 criteria (both beneficial)
        matrix = np.array([
            [10.0, 2.0],
            [5.0, 5.0],
            [1.0, 10.0]
        ])
        weights = np.array([0.6, 0.4])
        criteria_beneficial = [True, True]
        
        closeness = run_topsis(matrix, weights, criteria_beneficial)
        self.assertEqual(len(closeness), 3)
        self.assertTrue(all(0.0 <= c <= 1.0 for c in closeness))

    def test_topsis_non_beneficial(self):
        # 2 alternatives, 1 criterion (non-beneficial, like PE)
        # Alt 1 has higher PE (worse), Alt 2 has lower PE (better)
        matrix = np.array([
            [30.0],
            [15.0]
        ])
        weights = np.array([1.0])
        criteria_beneficial = [False] # non-beneficial
        
        closeness = run_topsis(matrix, weights, criteria_beneficial)
        # Higher score means closer to positive-ideal (which for non-beneficial means the lower value)
        # So Alt 2 (15.0 PE) should have a higher closeness score than Alt 1 (30.0 PE)
        self.assertTrue(closeness[1] > closeness[0])

    def test_topsis_dimension_mismatch(self):
        matrix = np.array([[1.0, 2.0]])
        
        # Mismatch in weights
        weights = np.array([1.0])
        criteria_beneficial = [True, True]
        with self.assertRaises(ValueError):
            run_topsis(matrix, weights, criteria_beneficial)
            
        # Mismatch in criteria_beneficial
        weights = np.array([0.5, 0.5])
        criteria_beneficial = [True]
        with self.assertRaises(ValueError):
            run_topsis(matrix, weights, criteria_beneficial)

    def test_engine_empty_data(self):
        matrix = np.zeros((0, 3))
        weights = np.array([0.3, 0.3, 0.4])
        criteria_beneficial = [True, False, True]
        closeness = run_topsis(matrix, weights, criteria_beneficial)
        self.assertEqual(len(closeness), 0)
        
        # Test generate_ascii_table with empty df
        df = pd.DataFrame(columns=['Ticker', 'Score', 'Matrix Action'])
        table = generate_ascii_table(df, [])
        self.assertIn("No data available", table)

    def test_generate_action_matrix(self):
        df = pd.DataFrame({
            'Ticker': ['AAPL', 'MSFT', 'KO'],
            'Score': [0.85, 0.55, 0.15]
        })
        holdings = ['AAPL', 'KO']
        
        result_df = generate_action_matrix(df, holdings)
        # AAPL: owned, score >= 0.60 -> STRONG HOLD
        # MSFT: not owned, score < 0.60 -> IGNORE
        # KO: owned, score <= 0.20 -> STRONG SELL
        
        self.assertEqual(result_df.loc[result_df['Ticker'] == 'AAPL', 'Matrix Action'].values[0], 'STRONG HOLD')
        self.assertEqual(result_df.loc[result_df['Ticker'] == 'MSFT', 'Matrix Action'].values[0], 'IGNORE')
        self.assertEqual(result_df.loc[result_df['Ticker'] == 'KO', 'Matrix Action'].values[0], 'STRONG SELL')

    def test_generate_ascii_table(self):
        df = pd.DataFrame({
            'Ticker': ['AAPL', 'MSFT'],
            'Score': [0.85, 0.55],
            'Matrix Action': ['STRONG HOLD', 'IGNORE']
        })
        holdings = ['AAPL']
        table = generate_ascii_table(df, holdings)
        self.assertIn("AAPL", table)
        self.assertIn("MSFT", table)
        self.assertIn("STRONG HOLD", table)
        self.assertIn("IGNORE", table)

    @patch('yfinance.Ticker')
    @patch('data_fetcher.YFinanceFetcher')
    def test_fetch_live_data_clamping(self, mock_fetcher_cls, mock_ticker_cls):
        # Create a mock StockData object
        mock_stock = MagicMock()
        mock_stock.ticker = 'AAPL'
        mock_stock.roic = 0.8228
        mock_stock.current_pe = 36.12
        mock_stock.debt_to_equity = 1.3380
        mock_stock.current_price = 298.01
        mock_stock.currency = 'USD'
        mock_stock.is_too_hard = False
        mock_stock.error_message = ''
        
        # Configure mock fetcher instance
        mock_fetcher = mock_fetcher_cls.return_value
        mock_fetcher.fetch_data.return_value = mock_stock
        
        # Configure mock yf.Ticker info
        mock_ticker = mock_ticker_cls.return_value
        mock_ticker.info = {
            'returnOnEquity': 1.4147,
            'operatingMargins': 0.3227
        }
        
        from engine import fetch_live_data
        df = fetch_live_data(['AAPL'], delay=0.0)
        
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 1)
        row = df.iloc[0]
        self.assertEqual(row['Ticker'], 'AAPL')
        # Check clamping (capped to 0.5)
        self.assertEqual(row['ROIC'], 0.5)
        self.assertEqual(row['ROE'], 0.5)
        self.assertEqual(row['PE'], 36.12)
        self.assertEqual(row['DebtToEquity'], 1.3380)
        self.assertEqual(row['OperatingMargin'], 0.3227)
        self.assertEqual(row['Price'], 298.01)

    @patch('yfinance.Ticker')
    @patch('data_fetcher.YFinanceFetcher')
    def test_fetch_live_data_missing_roe(self, mock_fetcher_cls, mock_ticker_cls):
        # Create a mock StockData object
        mock_stock = MagicMock()
        mock_stock.ticker = 'BKNG'
        mock_stock.roic = 0.4873
        mock_stock.current_pe = 22.66
        mock_stock.debt_to_equity = 0.1449
        mock_stock.current_price = 171.78
        mock_stock.currency = 'USD'
        mock_stock.is_too_hard = False
        
        mock_fetcher = mock_fetcher_cls.return_value
        mock_fetcher.fetch_data.return_value = mock_stock
        
        # returnOnEquity is missing (None) in info
        mock_ticker = mock_ticker_cls.return_value
        mock_ticker.info = {
            'returnOnEquity': None,
            'returnOnAssets': 0.2226,
            'operatingMargins': 0.2504
        }
        
        from engine import fetch_live_data
        df = fetch_live_data(['BKNG'], delay=0.0)
        
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 1)
        row = df.iloc[0]
        # ROE should fall back to returnOnAssets (0.2226)
        self.assertEqual(row['ROE'], 0.2226)
        self.assertEqual(row['ROIC'], 0.4873)

if __name__ == '__main__':
    unittest.main()
