from pyxirr import xirr
from datetime import datetime
from decimal import Decimal

def calculate_portfolio_performance(transactions, current_prices):
    if not transactions:
        return {"xirr": 0.0, "cagr": 0.0}
    
    now = datetime.utcnow()
    # Sort transactions by timestamp to ensure last_price is most recent
    sorted_txs = sorted(transactions, key=lambda x: x.timestamp)
    
    portfolio = {}
    dates, amounts = [], []
    
    first_date = sorted_txs[0].timestamp
    total_cost = Decimal('0')
    
    for tx in sorted_txs:
        # Precision: Keep as Decimal
        qty = Decimal(str(tx.quantity))
        price = Decimal(str(tx.price))
        
        dates.append(tx.timestamp)
        val = qty * price
        amt = -val if tx.action == "BUY" else val
        amounts.append(float(amt))
        
        if tx.action == "BUY":
            total_cost += val
        
        # Track holdings
        t = tx.ticker
        if t not in portfolio:
            portfolio[t] = {"qty": Decimal('0'), "last_price": price}
        
        if tx.action == "BUY":
            portfolio[t]["qty"] += qty
        else:
            portfolio[t]["qty"] -= qty
            
        portfolio[t]["last_price"] = price # Tracks most recent price as fallback

    # Add current value
    total_value = Decimal('0')
    for t, data in portfolio.items():
        if data["qty"] > 0:
            # Use current_price or fallback to last_price
            current_price = current_prices.get(t)
            if current_price is not None:
                price = Decimal(str(current_price))
            else:
                price = Decimal(str(data["last_price"]))
                
            val = data["qty"] * price
            total_value += val
            dates.append(now)
            amounts.append(float(val))

    # XIRR
    try:
        x_val = xirr(dates, amounts) or 0.0
    except Exception:
        x_val = 0.0
        
    # CAGR: (Ending Value / Beginning Value)^(1 / Years) - 1
    years = (now - first_date).days / 365.25
    if total_cost > 0 and years > 0:
        c_val = float(total_value / total_cost) ** (1 / years) - 1
    else:
        c_val = 0.0

    return {"xirr": float(x_val), "cagr": float(c_val)}
