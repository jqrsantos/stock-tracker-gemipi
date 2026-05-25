from pyxirr import xirr
from datetime import datetime, date
from decimal import Decimal
import math
import pandas as pd

def sanitize_float(val):
    if val is None or math.isnan(val) or math.isinf(val):
        return 0.0
    if val > 100.0: return 100.0
    if val < -1.0: return -1.0
    return val

def calculate_portfolio_performance(transactions, current_prices, current_prices_native=None):
    if current_prices_native is None:
        current_prices_native = {}
        
    if not transactions:
        return {
            "xirr": 0.0, "cagr": 0.0, "total_contributed": 0.0, 
            "cash_balance": 0.0, "stock_value": 0.0, 
            "total_portfolio_value": 0.0, "invested_series": [], 
            "open_positions": [], "closed_positions": []
        }
    
    now = date.today()
    # Use stable sort to preserve order of transactions on the same day if they were entered in order
    # We also sort by ID if available to ensure consistent results
    try:
        sorted_txs = sorted(transactions, key=lambda x: (x.timestamp.date() if hasattr(x.timestamp, 'date') else x.timestamp, getattr(x, 'id', 0)))
    except:
        sorted_txs = sorted(transactions, key=lambda x: x.timestamp)
    
    cash_balance = Decimal('0')
    total_contributed = Decimal('0')
    holdings = {}
    realized_details = {}
    
    dates, flows = [], []
    portfolio_history = []
    latest_known_prices = {}
    
    for tx in sorted_txs:
        t = tx.ticker.strip().upper()
        # print(f"DEBUG: Processing {t} {tx.action} {tx.quantity}")
        qty = Decimal(str(tx.quantity)).quantize(Decimal('1.00000000'))
        price = Decimal(str(tx.price)).quantize(Decimal('1.00000000'))
        val = qty * price
        tx_date = tx.timestamp.date()
        
        if t != "CASH" and tx.action in ["BUY", "SELL"]:
            latest_known_prices[t] = price
        
        if tx.action == "DEPOSIT":
            cash_balance += val
            total_contributed += val
            dates.append(tx_date)
            flows.append(float(-val))
            
        elif tx.action == "WITHDRAWAL":
            cash_balance -= val
            total_contributed -= val
            dates.append(tx_date)
            flows.append(float(val))
            
        elif tx.action == "BUY":
            cash_balance -= val
            if t not in holdings: holdings[t] = []
            native_price = Decimal(str(getattr(tx, "native_price", price))).quantize(Decimal('1.00000000'))
            native_currency = getattr(tx, "native_currency", "EUR")
            holdings[t].append({
                "qty": qty, 
                "price": price, 
                "native_price": native_price, 
                "native_currency": native_currency
            })
            
        elif tx.action == "SELL":
            cash_balance += val
            if t not in realized_details:
                realized_details[t] = {"total_cost": Decimal('0'), "total_proceeds": Decimal('0'), "total_qty_sold": Decimal('0')}
            realized_details[t]["total_proceeds"] += val
            realized_details[t]["total_qty_sold"] += qty
            
            remaining_to_sell = qty
            if t in holdings:
                while remaining_to_sell > 0 and holdings[t]:
                    lot = holdings[t][0]
                    if lot["qty"] <= remaining_to_sell + Decimal('0.000001'):
                        realized_details[t]["total_cost"] += lot["qty"] * lot["price"]
                        remaining_to_sell -= lot["qty"]
                        holdings[t].pop(0)
                    else:
                        realized_details[t]["total_cost"] += remaining_to_sell * lot["price"]
                        lot["qty"] -= remaining_to_sell
                        remaining_to_sell = 0
                
                # If after selling the holding is effectively empty, remove it
                if not holdings[t] or sum(l["qty"] for l in holdings[t]) < Decimal('0.000001'):
                    holdings.pop(t, None)
                        
        elif tx.action == "DIVIDEND":
            cash_balance += val
            if t not in realized_details:
                realized_details[t] = {"total_cost": Decimal('0'), "total_proceeds": Decimal('0'), "total_qty_sold": Decimal('0')}
            # Dividends are 100% profit, so we add to proceeds but don't increase qty sold or cost
            realized_details[t]["total_proceeds"] += val
            # Note: We don't increment total_qty_sold for dividends to avoid distorting avg return
            
        current_stock_market_val = Decimal('0')
        for tick, lots in holdings.items():
            current_stock_market_val += sum(lot["qty"] for lot in lots) * latest_known_prices.get(tick, Decimal('0'))
        
        total_val_at_time = float(cash_balance + current_stock_market_val)
        date_str = tx_date.isoformat()
        if not portfolio_history or portfolio_history[-1]["date"] != date_str:
            portfolio_history.append({
                "date": date_str, "total_value": total_val_at_time,
                "cash": float(cash_balance), "stocks": float(current_stock_market_val)
            })
        else:
            portfolio_history[-1]["total_value"] = total_val_at_time
            portfolio_history[-1]["cash"] = float(cash_balance)
            portfolio_history[-1]["stocks"] = float(current_stock_market_val)

    stock_value = Decimal('0')
    open_positions = []
    for t, lots in holdings.items():
        qty_owned = sum(lot["qty"] for lot in lots)
        if qty_owned > 0:
            cur_price_eur = Decimal(str(current_prices.get(t) or latest_known_prices.get(t, sorted_txs[-1].price)))
            market_val_eur = qty_owned * cur_price_eur
            stock_value += market_val_eur
            avg_buy_eur = sum(lot["qty"] * lot["price"] for lot in lots) / qty_owned
            ret_pct = (cur_price_eur / avg_buy_eur - 1) * 100
            
            # Retrieve native details from the lots
            native_currency = lots[0].get("native_currency", "EUR")
            avg_buy_native = sum(lot["qty"] * lot.get("native_price", lot["price"]) for lot in lots) / qty_owned
            cur_price_native = Decimal(str(current_prices_native.get(t) or lots[-1].get("native_price", lots[-1]["price"])))
            
            open_positions.append({
                "ticker": t, 
                "quantity": float(qty_owned), 
                "avg_price": float(avg_buy_eur),
                "avg_price_native": float(avg_buy_native),
                "current_price": float(cur_price_eur), 
                "current_price_native": float(cur_price_native),
                "market_value": float(market_val_eur), 
                "return_pct": float(ret_pct), 
                "native_currency": native_currency
            })
            
    total_portfolio_value = cash_balance + stock_value
    days = (now - sorted_txs[0].timestamp.date()).days
    years = max(days / 365.25, 0.001)

    # --- XIRR and CAGR Calculation ---
    denom = float(total_contributed)
    use_fallback_mode = (denom <= 0)
    
    xirr_dates, xirr_flows = [], []
    
    if not use_fallback_mode:
        # Deposit-based flows
        for tx in sorted_txs:
            if tx.action == "DEPOSIT":
                xirr_dates.append(tx.timestamp.date())
                xirr_flows.append(float(-tx.quantity * tx.price))
            elif tx.action == "WITHDRAWAL":
                xirr_dates.append(tx.timestamp.date())
                xirr_flows.append(float(tx.quantity * tx.price))
        
        # Final flow is the total equity (Cash + Stocks)
        if total_portfolio_value != 0:
            xirr_dates.append(now)
            xirr_flows.append(float(total_portfolio_value))
    else:
        # Transaction-based flows (no deposits)
        for tx in sorted_txs:
            t = tx.ticker.strip().upper()
            qty = Decimal(str(tx.quantity))
            price = Decimal(str(tx.price))
            val = float(qty * price)
            tx_date = tx.timestamp.date()
            
            if tx.action == "BUY":
                xirr_dates.append(tx_date)
                xirr_flows.append(-val)
            elif tx.action == "SELL":
                xirr_dates.append(tx_date)
                xirr_flows.append(val)
            elif tx.action == "DIVIDEND":
                xirr_dates.append(tx_date)
                xirr_flows.append(val)
        
        # Final flow is JUST the stock value (Cash is already accounted for in Buys/Sells/Divs)
        if stock_value != 0:
            xirr_dates.append(now)
            xirr_flows.append(float(stock_value))
        
        # Fallback denom is total buys
        buys = sum(tx.quantity * tx.price for tx in sorted_txs if tx.action == "BUY")
        denom = float(buys)

    try:
        df_x = pd.DataFrame({'date': xirr_dates, 'amount': xirr_flows})
        grouped_x = df_x.groupby('date')['amount'].sum().reset_index()
        if (grouped_x['amount'] < 0).any() and (grouped_x['amount'] > 0).any():
            x_val = xirr(grouped_x['date'], grouped_x['amount']) or 0.0
        else:
            x_val = 0.0
    except:
        x_val = 0.0

    if denom > 0 and years > 0.01:
        try:
            if use_fallback_mode:
                # In fallback, total_portfolio_value is profit. 
                # Ratio = (Profit + Denom) / Denom
                ratio = (float(total_portfolio_value) + denom) / denom
            else:
                ratio = float(total_portfolio_value) / denom
                
            if ratio > 0:
                cagr = (ratio ** (1 / years) - 1)
            else:
                cagr = -1.0
        except:
            cagr = 0.0
    else:
        cagr = 0.0

    # Add final data point for today to make graph "spot on"
    today_str = now.isoformat()
    if not portfolio_history or portfolio_history[-1]["date"] != today_str:
        portfolio_history.append({
            "date": today_str, 
            "total_value": float(total_portfolio_value),
            "cash": float(cash_balance), 
            "stocks": float(stock_value)
        })
    else:
        portfolio_history[-1]["total_value"] = float(total_portfolio_value)
        portfolio_history[-1]["cash"] = float(cash_balance)
        portfolio_history[-1]["stocks"] = float(stock_value)

    return {
        "xirr": sanitize_float(float(x_val)), 
        "cagr": sanitize_float(float(cagr)),
        "total_contributed": float(total_contributed),
        "cash_balance": float(cash_balance),
        "stock_value": float(stock_value),
        "total_portfolio_value": float(total_portfolio_value),
        "open_positions": open_positions,
        "closed_positions": [
            {
                "ticker": t,
                "total_sold_qty": float(d["total_qty_sold"]),
                "realized_profit": float(d["total_proceeds"] - d["total_cost"]),
                "return_pct": float((d["total_proceeds"] / d["total_cost"] - 1) * 100) if d["total_cost"] > 0 else 100.0
            } for t, d in realized_details.items() if d["total_qty_sold"] > 0
        ],
        "invested_series": portfolio_history
    }

def get_open_positions(transactions):
    """
    Returns a dictionary of ticker: quantity for all currently open stock positions.
    Ignores CASH tickers and filters out closed or near-zero positions.
    """
    if not transactions:
        return {}
    
    try:
        sorted_txs = sorted(transactions, key=lambda x: (x.timestamp.date() if hasattr(x.timestamp, 'date') else x.timestamp, getattr(x, 'id', 0)))
    except:
        sorted_txs = sorted(transactions, key=lambda x: x.timestamp)
    
    holdings = {}
    
    for tx in sorted_txs:
        t = tx.ticker.strip().upper()
        if t == "CASH": continue
        
        qty = Decimal(str(tx.quantity)).quantize(Decimal('1.00000000'))
        
        if tx.action == "BUY":
            if t not in holdings: holdings[t] = Decimal('0')
            holdings[t] += qty
        elif tx.action == "SELL":
            if t in holdings:
                holdings[t] -= qty
                if holdings[t] < Decimal('0.000001'):
                    holdings.pop(t)
    
    return {t: float(q) for t, q in holdings.items() if q > 0}
