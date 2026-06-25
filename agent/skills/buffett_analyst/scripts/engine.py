# agent/skills/buffett_analyst/scripts/engine.py
import os
import sys
import time
import argparse
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

# RI values for Consistency Ratio calculation (indices 1 to 10)
# Removed AHP and TOPSIS imports/logic

def generate_action_matrix(df: pd.DataFrame, holdings: List[str]) -> pd.DataFrame:
    """
    Maps absolute valuations to STRONG BUY, BUY, HOLD, STRONG SELL, or IGNORE.
    """
    holdings_upper = [t.upper() for t in holdings]
    actions = []
    
    for idx, row in df.iterrows():
        ticker = str(row['Ticker']).upper()
        price = row.get('Price', 0)
        fair = row.get('Fair_Price', 0)
        bargain = row.get('Bargain_Price', 0)
        expensive = row.get('Expensive_Price', 0)
        owned = ticker in holdings_upper
        
        # Absolute valuation actions
        if price <= bargain and price > 0:
            action = "STRONG BUY"
        elif price <= fair and price > 0:
            action = "BUY" if not owned else "HOLD"
        elif price <= expensive and price > 0:
            action = "HOLD"
        elif price > expensive:
            action = "STRONG SELL" if owned else "IGNORE"
        else:
            action = "IGNORE"
            
        actions.append(action)
        
    df['Action'] = actions
    return df

def generate_ascii_table(df: pd.DataFrame, holdings: List[str]) -> str:
    """
    Renders the absolute valuation results as an ASCII terminal summary table.
    Supports dynamic column widths.
    """
    if df.empty:
        return (
            "+--------+---------------+------------------------+---------+------------+---------------+\n"
            "| No data available to display.                                                      |\n"
            "+--------+---------------+------------------------+---------+------------+---------------+"
        )
        
    holdings_upper = [t.upper() for t in holdings]
    df['Status'] = df['Ticker'].apply(lambda t: "Owned" if str(t).upper() in holdings_upper else "Watchlist")
    
    # Calculate MoS %
    def calc_mos(row):
        fair = row.get('Fair_Price', 0)
        price = row.get('Price', 0)
        if fair and fair > 0:
            return ((fair - price) / fair) * 100
        return 0.0
    
    df['MoS'] = df.apply(calc_mos, axis=1)
    
    df_str = df.copy()
    df_str['Price_str'] = df_str['Price'].apply(lambda s: f"{s:.2f}" if pd.notna(s) else "N/A")
    df_str['Fair_str'] = df_str['Fair_Price'].apply(lambda s: f"{s:.2f}" if pd.notna(s) else "N/A")
    df_str['MoS_str'] = df_str['MoS'].apply(lambda s: f"{s:.1f}%" if pd.notna(s) else "N/A")
    
    w_ticker = max(6, df_str['Ticker'].astype(str).str.len().max())
    w_price = max(13, df_str['Price_str'].astype(str).str.len().max())
    w_fair = max(22, df_str['Fair_str'].astype(str).str.len().max())
    w_mos = max(7, df_str['MoS_str'].astype(str).str.len().max())
    w_status = max(10, df_str['Status'].astype(str).str.len().max())
    w_action = max(13, df_str['Action'].astype(str).str.len().max())
    
    border = f"+-{'-'*w_ticker}-+-{'-'*w_price}-+-{'-'*w_fair}-+-{'-'*w_mos}-+-{'-'*w_status}-+-{'-'*w_action}-+"
    header = f"| {'Ticker':<{w_ticker}} | {'Current Price':<{w_price}} | {'Fair Value (Intrinsic)':<{w_fair}} | {'MoS %':<{w_mos}} | {'Status':<{w_status}} | {'Action':<{w_action}} |"
    
    lines = [border, header, border]
    for _, row in df_str.iterrows():
        ticker = f"{str(row['Ticker']):<{w_ticker}}"
        price = f"{str(row['Price_str']):<{w_price}}"
        fair = f"{str(row['Fair_str']):<{w_fair}}"
        mos = f"{str(row['MoS_str']):<{w_mos}}"
        status = f"{str(row['Status']):<{w_status}}"
        action = f"{str(row['Action']):<{w_action}}"
        lines.append(f"| {ticker} | {price} | {fair} | {mos} | {status} | {action} |")
    lines.append(border)
    return "\n".join(lines)

def fetch_live_data(tickers: List[str], delay: float = 1.0) -> Optional[pd.DataFrame]:
    """
    Fetches live fundamental data for each ticker via YFinanceFetcher.
    """
    try:
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
        
        return {
            'Ticker': ticker.upper(),
            'Price': round(stock.current_price, 2) if getattr(stock, 'current_price', None) else 0.0,
            'Fair_Price': round(stock.fair_price, 2) if getattr(stock, 'fair_price', None) else 0.0,
            'Bargain_Price': round(stock.bargain_price, 2) if getattr(stock, 'bargain_price', None) else 0.0,
            'Expensive_Price': round(stock.expensive_price, 2) if getattr(stock, 'expensive_price', None) else 0.0,
            'Business_Type': getattr(stock, 'business_type', 'Unknown'),
            'CROIC': round(stock.croic, 4) if getattr(stock, 'croic', None) else 0.0,
            'EV_to_FCF': round(stock.ev_to_fcf, 2) if getattr(stock, 'ev_to_fcf', None) else 0.0,
            'Error_Msg': getattr(stock, 'error_message', ''),
            'Currency': getattr(stock, 'currency', 'USD'),
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
    parser = argparse.ArgumentParser(description="Absolute Valuation Portfolio Decision Engine")
    parser.add_argument("--data-path", type=str, help="Path to CSV data (fallback)")
    parser.add_argument("--holdings", type=str, default="", help="Comma-separated list of currently owned tickers")
    parser.add_argument("--watchlist", type=str, default="", help="Comma-separated list of watchlist/bargain candidate tickers")
    parser.add_argument("--live", action="store_true", help="Fetch live fundamental data from Yahoo Finance via yfinance")
    args = parser.parse_args()

    holdings_list = [t.strip().upper() for t in args.holdings.split(",") if t.strip()]
    watchlist_list = [t.strip().upper() for t in args.watchlist.split(",") if t.strip()]
    all_tickers = list(dict.fromkeys(holdings_list + watchlist_list))  # preserve order, deduplicate

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
        print("[ERROR] No --live flag or --data-path provided. Cannot run Absolute Valuation without data.")
        sys.exit(1)

    # 1. Map actions
    df = generate_action_matrix(df, holdings_list)

    # 2. Output
    print(generate_ascii_table(df, holdings_list))


if __name__ == "__main__":
    main()
