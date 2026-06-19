# agent/skills/buffett_analyst/scripts/test_engine.py
import unittest
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
            'Score': [0.85, 0.55, 0.25]
        })
        holdings = ['AAPL', 'KO']
        
        result_df = generate_action_matrix(df, holdings)
        # AAPL: owned, score >= 0.70 -> STRONG HOLD
        # MSFT: not owned, score between 0.40 and 0.70 -> IGNORE
        # KO: owned, score <= 0.40 -> STRONG SELL
        
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

if __name__ == '__main__':
    unittest.main()
