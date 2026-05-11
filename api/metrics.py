from pyxirr import xirr
from datetime import datetime
from decimal import Decimal
import math

def sanitize_float(val):
    if val is None or math.isnan(val) or math.isinf(val):
        return 0.0
    return val

def calculate_portfolio_performance(transactions, current_prices):
    if not transactions:
        return {"xirr": 0.0, "cagr": 0.0}
    
    now = datetime.utcnow()
    # Sort transactions by timestamp
    sorted_txs = sorted(transactions, key=lambda x: x.timestamp)
    
    portfolio = {}
    dates, amounts = [], []
    
    first_date = sorted_txs[0].timestamp
    total_invested = Decimal('0')
    
    for tx in sorted_txs:
        qty = Decimal(str(tx.quantity))
        price = Decimal(str(tx.price))
        
        # Total cash flow for this transaction
        val = qty * price
        
        # Cash flows: BUY is negative (money out), SELL/DIVIDEND is positive (money in)
        if tx.action == "BUY":
            amt = -val
            total_invested += val
        else:
            amt = val
            
        dates.append(tx.timestamp)
        amounts.append(float(amt))
        
        # Track holdings (Dividends don't change quantity)
        t = tx.ticker
        if t not in portfolio:
            portfolio[t] = {"qty": Decimal('0'), "last_price": price}
        
        if tx.action == "BUY":
            portfolio[t]["qty"] += qty
        elif tx.action == "SELL":
            portfolio[t]["qty"] -= qty
            
        portfolio[t]["last_price"] = price

    # Add current value as a final positive cash flow for XIRR
    total_current_value = Decimal('0')
    for t, data in portfolio.items():
        if data["qty"] > 0:
            current_price = current_prices.get(t)
            if current_price is not None:
                price = Decimal(str(current_price))
            else:
                price = Decimal(str(data["last_price"]))
                
            val = data["qty"] * price
            total_current_value += val
            
    if total_current_value > 0:
        dates.append(now)
        amounts.append(float(total_current_value))

    # XIRR calculation
    try:
        x_val = xirr(dates, amounts)
        if x_val is None:
            x_val = 0.0
    except Exception:
        x_val = 0.0
        
    # CAGR calculation
    years = (now - first_date).days / 365.25
    if total_invested > 0 and years > 0.01:
        try:
            # CAGR = (Ending Value / Beginning Value)^(1/years) - 1
            # Here Ending Value = current_value + any dividends/sales (positive cash flows)
            # This is complex with multiple buys. We'll use a simplified total-return CAGR.
            c_val = float(total_current_value / total_invested) ** (1 / years) - 1
        except Exception:
            c_val = 0.0
    else:
        c_val = 0.0

    return {
        "xirr": sanitize_float(float(x_val)), 
        "cagr": sanitize_float(float(c_val))
    }
