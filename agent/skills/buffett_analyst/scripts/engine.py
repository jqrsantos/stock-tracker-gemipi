# agent/skills/buffett_analyst/scripts/engine.py
import os
import sys
import time
import argparse
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

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
    
    # Extract corresponding eigenvector, ensure elements are positive, and normalize to sum to 1
    weights = np.real(eigvecs[:, max_idx])
    weights = np.abs(weights)
    weights = weights / np.sum(weights)
    
    # Calculate CI and CR
    if n <= 2:
        cr = 0.0
    else:
        ci = (lambda_max - n) / (n - 1)
        ri = RI_VALUES.get(n, 1.49)
        cr = ci / ri
        
    return weights, cr

def get_ahp_weights(pairwise_matrix: np.ndarray) -> np.ndarray:
    """
    Calculates weights from pairwise AHP matrix, checking CR and falling back if needed.
    """
    n = pairwise_matrix.shape[0]
    weights, cr = run_ahp(pairwise_matrix)
    if cr >= 0.10:
        print(f"Warning: AHP matrix inconsistency detected (CR = {cr:.4f} >= 0.10). Using equal weights fallback.")
        weights = np.ones(n) / float(n)
    return weights

def run_topsis(matrix: np.ndarray, weights: np.ndarray, criteria_beneficial: List[bool]) -> np.ndarray:
    """
    Runs TOPSIS vectorization on a decision matrix and returns Closeness Coefficients.
    """
    m, n = matrix.shape
    if m == 0:
        return np.zeros(0)
        
    # Dimensionality Validation
    if len(weights) != n:
        raise ValueError(f"Length of weights ({len(weights)}) does not match number of criteria ({n})")
    if len(criteria_beneficial) != n:
        raise ValueError(f"Length of criteria_beneficial ({len(criteria_beneficial)}) does not match number of criteria ({n})")
        
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
        ticker = str(row['Ticker']).upper()
        score = row['Score']
        owned = ticker in holdings_upper
        
        if score >= 0.60:
            action = "STRONG HOLD" if owned else "STRONG BUY"
        elif score <= 0.20:
            action = "STRONG SELL" if owned else "IGNORE"
        else:
            action = "HOLD" if owned else "IGNORE"
            
        actions.append(action)
        
    df['Matrix Action'] = actions
    return df

def generate_ascii_table(df: pd.DataFrame, holdings: List[str]) -> str:
    """
    Renders the final ranked matrix as an ASCII terminal summary table.
    Supports dynamic column widths.
    """
    if df.empty:
        return (
            "+--------+------------+--------------+---------------+\n"
            "| No data available to display.                      |\n"
            "+--------+------------+--------------+---------------+"
        )
        
    holdings_upper = [t.upper() for t in holdings]
    df['Status'] = df['Ticker'].apply(lambda t: "Owned" if str(t).upper() in holdings_upper else "Watchlist")
    
    # Convert score to 4 decimal places string for proper width calculations
    df_str = df.copy()
    df_str['Score_str'] = df_str['Score'].apply(lambda s: f"{s:.4f}")
    
    # Determine dynamic widths
    w_ticker = max(6, df_str['Ticker'].astype(str).str.len().max())
    w_status = max(10, df_str['Status'].astype(str).str.len().max())
    w_score = max(12, df_str['Score_str'].astype(str).str.len().max())
    w_action = max(13, df_str['Matrix Action'].astype(str).str.len().max())
    
    # Create formatting lines
    border = f"+-{'-'*w_ticker}-+-{'-'*w_status}-+-{'-'*w_score}-+-{'-'*w_action}-+"
    header = f"| {'Ticker':<{w_ticker}} | {'Status':<{w_status}} | {'TOPSIS Score':<{w_score}} | {'Matrix Action':<{w_action}} |"
    
    lines = []
    lines.append(border)
    lines.append(header)
    lines.append(border)
    for _, row in df_str.iterrows():
        ticker = f"{str(row['Ticker']):<{w_ticker}}"
        status = f"{str(row['Status']):<{w_status}}"
        score = f"{row['Score_str']:<{w_score}}"
        action = f"{str(row['Matrix Action']):<{w_action}}"
        lines.append(f"| {ticker} | {status} | {score} | {action} |")
    lines.append(border)
    return "\n".join(lines)

def fetch_live_data(tickers: List[str], delay: float = 1.0) -> Optional[pd.DataFrame]:
    """
    Fetches live fundamental data for each ticker via YFinanceFetcher.
    Returns a DataFrame with columns: Ticker, ROIC, ROE, PE, DebtToEquity, OperatingMargin, Price.
    Tickers that fail or return is_too_hard are skipped with a warning.
    """
    try:
        # Import here to avoid hard dependency when running in CSV/mockup mode
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        from data_fetcher import YFinanceFetcher
    except ImportError as e:
        print(f"Error: Could not import YFinanceFetcher: {e}")
        return None

    fetcher = YFinanceFetcher()
    rows = []
    failed = []

    def fetch_single(ticker):
        print(f"  Fetching live data: {ticker}...", flush=True)
        stock = fetcher.fetch_data(ticker)
        if stock is None:
            return None, ticker
        
        # ROE is not directly in StockData; approximate from yfinance info
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            roe = info.get('returnOnEquity')
            if roe is None:
                # If ROE is missing due to negative book equity, use ROA or ROIC as a proxy
                roe = info.get('returnOnAssets') or stock.roic or 0.0
            op_margin = info.get('operatingMargins') or 0.0
        except Exception:
            roe = 0.0
            op_margin = 0.0

        # Clamp metrics to reasonable bounds to prevent extreme outliers
        # (e.g. AAPL negative book equity inflates ROIC to 5x+) from distorting TOPSIS
        roic_clamped = round(min(max(stock.roic, -0.5), 0.5), 4)
        roe_clamped = round(min(max(roe, -0.5), 0.5), 4)
        pe_val = round(stock.current_pe, 2) if stock.current_pe > 0 else 999.0  # missing P/E → treat as expensive
        de_clamped = round(min(stock.debt_to_equity, 10.0), 4)  # cap extreme leverage
        op_margin_clamped = round(min(max(op_margin, -0.5), 0.5), 4)

        return {
            'Ticker': ticker.upper(),
            'ROIC': roic_clamped,
            'ROE': roe_clamped,
            'PE': pe_val,
            'DebtToEquity': de_clamped,
            'OperatingMargin': op_margin_clamped,
            'Price': round(stock.current_price, 2),
            'Currency': stock.currency,
        }, None

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(tickers) or 1)) as executor:
        futures = {executor.submit(fetch_single, ticker): ticker for ticker in tickers}
        for future in concurrent.futures.as_completed(futures):
            try:
                row, err_ticker = future.result()
                if row:
                    rows.append(row)
                elif err_ticker:
                    failed.append(err_ticker)
            except Exception as e:
                ticker = futures[future]
                print(f"Error fetching {ticker}: {e}")
                failed.append(ticker)

    if failed:
        print(f"\n[WARNING] Skipped {len(failed)} ticker(s) due to fetch errors: {', '.join(failed)}")

    if not rows:
        return None

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="AHP-TOPSIS Portfolio Decision Engine")
    parser.add_argument("--data-path", type=str, help="Path to CSV: Ticker, ROIC, ROE, PE, DebtToEquity, OperatingMargin")
    parser.add_argument("--holdings", type=str, default="", help="Comma-separated list of currently owned tickers")
    parser.add_argument("--watchlist", type=str, default="", help="Comma-separated list of watchlist/bargain candidate tickers")
    parser.add_argument("--live", action="store_true", help="Fetch live fundamental data from Yahoo Finance via yfinance")
    args = parser.parse_args()

    holdings_list = [t.strip().upper() for t in args.holdings.split(",") if t.strip()]
    watchlist_list = [t.strip().upper() for t in args.watchlist.split(",") if t.strip()]
    all_tickers = list(dict.fromkeys(holdings_list + watchlist_list))  # preserve order, deduplicate

    # 1. AHP weights
    pairwise = np.array([
        [1.0, 2.0, 4.0, 3.0, 2.0],
        [0.5, 1.0, 3.0, 2.0, 1.0],
        [0.25, 0.33, 1.0, 0.5, 0.33],
        [0.33, 0.5, 2.0, 1.0, 0.5],
        [0.5, 1.0, 3.0, 2.0, 1.0]
    ])
    weights = get_ahp_weights(pairwise)

    # 2. Ingest Data
    if args.live:
        if not all_tickers:
            print("Error: --live requires at least one ticker via --holdings or --watchlist.")
            sys.exit(1)
        print(f"Fetching live yfinance data for: {', '.join(all_tickers)}\n")
        df = fetch_live_data(all_tickers)
        if df is None or df.empty:
            print("Error: Live data fetch returned no usable results. Check network/SSL.")
            sys.exit(1)
        # Update holdings_list to only include tickers that successfully fetched
        fetched_tickers = set(df['Ticker'].str.upper())
        holdings_list = [t for t in holdings_list if t in fetched_tickers]
        print(f"\nLive data loaded for {len(df)} ticker(s).\n")
    elif args.data_path:
        if not os.path.exists(args.data_path):
            print(f"Error: Data path '{args.data_path}' does not exist.")
            sys.exit(1)
        try:
            df = pd.read_csv(args.data_path)
        except Exception as e:
            print(f"Error: Failed to read CSV file: {e}")
            sys.exit(1)
    else:
        # Mockup fallback
        print("[INFO] No --live flag or --data-path provided. Using built-in mockup dataset.")
        mockup_data = {
            "Ticker": ["AAPL", "MSFT", "KO", "HPQ", "INTC"],
            "ROIC": [0.245, 0.221, 0.192, 0.084, 0.045],
            "ROE": [0.352, 0.312, 0.264, 0.112, 0.062],
            "PE": [28.5, 32.1, 19.8, 12.4, 38.5],
            "DebtToEquity": [0.85, 0.65, 0.92, 1.45, 0.52],
            "OperatingMargin": [0.284, 0.354, 0.251, 0.082, 0.041]
        }
        df = pd.DataFrame(mockup_data)

    # Schema Validation
    required_columns = ['Ticker', 'ROIC', 'ROE', 'PE', 'DebtToEquity', 'OperatingMargin']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Error: Input data is missing required columns: {missing_columns}")
        sys.exit(1)
    criteria_matrix = df[['ROIC', 'ROE', 'PE', 'DebtToEquity', 'OperatingMargin']].to_numpy(dtype=float)
    beneficial = [True, True, False, False, True]

    # 3. Calculate scores
    scores = run_topsis(criteria_matrix, weights, beneficial)
    df['Score'] = scores
    df = df.sort_values(by='Score', ascending=False).reset_index(drop=True)

    # 4. Map actions
    df = generate_action_matrix(df, holdings_list)

    # 5. Output
    # Show live price column if available
    if 'Price' in df.columns:
        df_display = df.copy()
        df_display['Status'] = df_display['Ticker'].apply(
            lambda t: 'Owned' if str(t).upper() in [h.upper() for h in holdings_list] else 'Watchlist'
        )
        holdings_upper = [h.upper() for h in holdings_list]
        w_ticker = max(6, df_display['Ticker'].astype(str).str.len().max())
        w_price = 12
        w_status = max(10, df_display['Status'].astype(str).str.len().max())
        w_score = 12
        w_action = max(13, df_display['Matrix Action'].astype(str).str.len().max())
        border = f"+-{'-'*w_ticker}-+-{'-'*w_price}-+-{'-'*w_status}-+-{'-'*w_score}-+-{'-'*w_action}-+"
        header = (f"| {'Ticker':<{w_ticker}} | {'Price (USD)':<{w_price}} "
                  f"| {'Status':<{w_status}} | {'TOPSIS Score':<{w_score}} | {'Matrix Action':<{w_action}} |")
        lines = [border, header, border]
        for _, row in df_display.iterrows():
            price_str = f"{row['Price']:.2f}" if pd.notna(row.get('Price')) else 'N/A'
            lines.append(
                f"| {str(row['Ticker']):<{w_ticker}} "
                f"| {price_str:<{w_price}} "
                f"| {str(row['Status']):<{w_status}} "
                f"| {row['Score']:.4f}       "
                f"| {str(row['Matrix Action']):<{w_action}} |"
            )
        lines.append(border)
        print('\n'.join(lines))
    else:
        print(generate_ascii_table(df, holdings_list))


if __name__ == "__main__":
    main()
