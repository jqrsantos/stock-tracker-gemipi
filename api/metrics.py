from pyxirr import xirr
import pandas as pd
from datetime import datetime

def calculate_portfolio_performance(transactions, current_prices):
    """
    Calculates XIRR for a list of transactions given current market prices.
    """
    if not transactions:
        return {"xirr": 0.0, "cagr": 0.0}
    
    dates = []
    amounts = []
    
    # Historical Cash Flows
    for tx in transactions:
        dates.append(tx.timestamp)
        # Cash OUT (BUY) is negative, Cash IN (SELL) is positive
        value = float(tx.quantity * tx.price)
        amounts.append(-value if tx.action == "BUY" else value)
    
    # Add "Virtual Sell" for current holdings (Cash IN if sold today)
    for ticker, price in current_prices.items():
        # Calculate net quantity
        ticker_txs = [tx for tx in transactions if tx.ticker == ticker]
        net_qty = sum(tx.quantity if tx.action == "BUY" else -tx.quantity for tx in ticker_txs)
        
        if net_qty > 0:
            dates.append(datetime.utcnow())
            amounts.append(float(net_qty * price))
            
    try:
        if len(dates) < 2:
            return {"xirr": 0.0, "cagr": 0.0}
        
        # calculate xirr
        result = xirr(dates, amounts)
        if result is None:
            return {"xirr": 0.0, "cagr": 0.0}
            
        return {"xirr": float(result), "cagr": float(result)}
    except Exception:
        return {"xirr": 0.0, "cagr": 0.0}
