# Save this temporarily to test_roic.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'agent', 'skills', 'buffett_analyst', 'scripts')))
from data_fetcher import YFinanceFetcher
import pandas as pd

def test_missing_data_exclusion():
    fetcher = YFinanceFetcher()
    # Mock data with one missing year
    ebit = pd.Series([100, 120, 0, 150])
    tax = pd.Series([20, 25, 0, 30])
    pretax = pd.Series([100, 120, 0, 150])
    equity = pd.Series([500, 500, 0, 500])
    debt = pd.Series([100, 100, 0, 100])
    
    df_align = pd.DataFrame({'ebit': ebit, 'tax': tax, 'pretax': pretax, 'equity': equity, 'debt': debt}).fillna(0.0)
    roic_history = []
    
    for _, row in df_align.iterrows():
        # strict exclusion check we are going to implement
        if row['ebit'] == 0.0 and row['equity'] == 0.0:
            continue
            
        row_tax_rate = 0.21
        row_nopat = row['ebit'] * (1 - row_tax_rate)
        row_ic = row['equity'] + row['debt']
        if row_ic > 0:
            roic_history.append(row_nopat / row_ic)
            
    assert len(roic_history) == 3, f"Expected 3 valid years, got {len(roic_history)}"

if __name__ == "__main__":
    test_missing_data_exclusion()
    print("ROIC missing data logic test passed.")
