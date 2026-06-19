# agent/skills/buffett_analyst/scripts/test_engine.py
import unittest
import numpy as np
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from engine import run_ahp, run_topsis, generate_action_matrix, generate_ascii_table

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
