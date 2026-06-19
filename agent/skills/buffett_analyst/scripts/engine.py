# agent/skills/buffett_analyst/scripts/engine.py
import sys
import argparse
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

# RI values for Consistency Ratio calculation (indices 1 to 10)
RI_VALUES = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}

def run_ahp(pairwise_matrix: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Computes AHP weight vectors and checks the Consistency Ratio (CR).
    """
    n = pairwise_matrix.shape[0]
    # Find eigenvalues and eigenvectors
    eigvals, eigvecs = np.linalg.eig(pairwise_matrix)
    max_idx = np.argmax(np.real(eigvals))
    lambda_max = np.real(eigvals[max_idx])
    
    # Extract corresponding eigenvector and normalize to sum to 1
    weights = np.real(eigvecs[:, max_idx])
    weights = weights / np.sum(weights)
    
    # Calculate CI and CR
    if n <= 2:
        cr = 0.0
    else:
        ci = (lambda_max - n) / (n - 1)
        ri = RI_VALUES.get(n, 1.49)
        cr = ci / ri
        
    return weights, cr

def run_topsis(matrix: np.ndarray, weights: np.ndarray, criteria_beneficial: List[bool]) -> np.ndarray:
    """
    Runs TOPSIS vectorization on a decision matrix and returns Closeness Coefficients.
    """
    m, n = matrix.shape
    # Normalize the decision matrix using vector norm
    norm_matrix = np.zeros((m, n))
    for j in range(n):
        col_norm = np.sqrt(np.sum(matrix[:, j] ** 2))
        if col_norm == 0:
            norm_matrix[:, j] = 0
        else:
            norm_matrix[:, j] = matrix[:, j] / col_norm
            
    # Calculate Weighted Normalized Decision Matrix
    weighted_matrix = norm_matrix * weights
    
    # Determine Positive-Ideal and Negative-Ideal Solutions
    ideal_pos = np.zeros(n)
    ideal_neg = np.zeros(n)
    for j in range(n):
        if criteria_beneficial[j]:
            ideal_pos[j] = np.max(weighted_matrix[:, j])
            ideal_neg[j] = np.min(weighted_matrix[:, j])
        else:
            ideal_pos[j] = np.min(weighted_matrix[:, j])
            ideal_neg[j] = np.max(weighted_matrix[:, j])
            
    # Calculate Euclidean distances
    dist_pos = np.sqrt(np.sum((weighted_matrix - ideal_pos) ** 2, axis=1))
    dist_neg = np.sqrt(np.sum((weighted_matrix - ideal_neg) ** 2, axis=1))
    
    # Compute Closeness Coefficient
    closeness = np.zeros(m)
    for i in range(m):
        denom = dist_pos[i] + dist_neg[i]
        closeness[i] = dist_neg[i] / denom if denom > 0 else 0.0
        
    return closeness

def generate_action_matrix(df: pd.DataFrame, holdings: List[str]) -> pd.DataFrame:
    """
    Maps closeness scores to STRONG BUY, STRONG HOLD, STRONG SELL, IGNORE, or HOLD.
    """
    holdings_upper = [t.upper() for t in holdings]
    actions = []
    
    for idx, row in df.iterrows():
        ticker = row['Ticker'].upper()
        score = row['Score']
        owned = ticker in holdings_upper
        
        if score >= 0.70:
            action = "STRONG HOLD" if owned else "STRONG BUY"
        elif score <= 0.40:
            action = "STRONG SELL" if owned else "IGNORE"
        else:
            action = "HOLD" if owned else "IGNORE"
            
        actions.append(action)
        
    df['Matrix Action'] = actions
    return df

def generate_ascii_table(df: pd.DataFrame, holdings: List[str]) -> str:
    """
    Renders the final ranked matrix as an ASCII terminal summary table.
    """
    holdings_upper = [t.upper() for t in holdings]
    df['Status'] = df['Ticker'].apply(lambda t: "Owned" if t.upper() in holdings_upper else "Watchlist")
    
    lines = []
    lines.append("+--------+------------+--------------+---------------+")
    lines.append("| Ticker | Status     | TOPSIS Score | Matrix Action |")
    lines.append("+--------+------------+--------------+---------------+")
    for _, row in df.iterrows():
        ticker = f"{row['Ticker']:<6}"
        status = f"{row['Status']:<10}"
        score = f"{row['Score']:.4f}"
        action = f"{row['Matrix Action']:<13}"
        lines.append(f"| {ticker} | {status} |     {score}   | {action} |")
    lines.append("+--------+------------+--------------+---------------+")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="AHP-TOPSIS Portfolio Decision Engine")
    parser.add_argument("--data-path", type=str, help="Path to csv containing stock data columns: Ticker, ROIC, ROE, PE, DebtToEquity, OperatingMargin")
    parser.add_argument("--holdings", type=str, default="", help="Comma-separated list of currently owned tickers")
    args = parser.parse_args()
    
    # 1. Define standard criteria weights (AHP reciprocal matrix)
    # Order: ROIC, ROE, PE (non-beneficial), DebtToEquity (non-beneficial), OperatingMargin
    # Default consistent Buffett-weighted matrix
    pairwise = np.array([
        [1.0, 2.0, 4.0, 3.0, 2.0],
        [0.5, 1.0, 3.0, 2.0, 1.0],
        [0.25, 0.33, 1.0, 0.5, 0.33],
        [0.33, 0.5, 2.0, 1.0, 0.5],
        [0.5, 1.0, 3.0, 2.0, 1.0]
    ])
    
    weights, cr = run_ahp(pairwise)
    if cr >= 0.10:
        print(f"Warning: AHP matrix inconsistency detected (CR = {cr:.4f} >= 0.10). Using equal weights fallback.")
        weights = np.ones(5) / 5.0
        
    # 2. Ingest Data
    if args.data_path:
        df = pd.read_csv(args.data_path)
    else:
        # Load a default mockup CSV dataset
        mockup_data = {
            "Ticker": ["AAPL", "MSFT", "KO", "HPQ", "INTC"],
            "ROIC": [0.245, 0.221, 0.192, 0.084, 0.045],
            "ROE": [0.352, 0.312, 0.264, 0.112, 0.062],
            "PE": [28.5, 32.1, 19.8, 12.4, 38.5],
            "DebtToEquity": [0.85, 0.65, 0.92, 1.45, 0.52],
            "OperatingMargin": [0.284, 0.354, 0.251, 0.082, 0.041]
        }
        df = pd.DataFrame(mockup_data)
        
    # Standardize column extraction
    tickers = df['Ticker'].tolist()
    criteria_matrix = df[['ROIC', 'ROE', 'PE', 'DebtToEquity', 'OperatingMargin']].to_numpy()
    
    # Beneficial boolean mapping matching our criteria order
    beneficial = [True, True, False, False, True]
    
    # 3. Calculate scores
    scores = run_topsis(criteria_matrix, weights, beneficial)
    df['Score'] = scores
    
    # Sort descending by score
    df = df.sort_values(by='Score', ascending=False).reset_index(drop=True)
    
    # 4. Map actions
    holdings_list = [t.strip().upper() for t in args.holdings.split(",") if t.strip()]
    df = generate_action_matrix(df, holdings_list)
    
    # 5. Output
    print(generate_ascii_table(df, holdings_list))

if __name__ == "__main__":
    main()
