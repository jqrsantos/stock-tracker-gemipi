# ui/app.py
import streamlit as st
import requests
import os
import pandas as pd
import plotly.graph_objects as go

API_URL = os.getenv("API_URL", "http://api:8000")

st.set_page_config(page_title="Stock Portfolio Tracker", layout="wide")
st.title("📈 Stock Portfolio Tracker")

with st.sidebar:
    st.header("Lookup")
    ticker = st.text_input("Enter Ticker (e.g., AAPL)").upper()
    if st.button("Get Price"):
        if ticker:
            try:
                res = requests.get(f"{API_URL}/price/{ticker}")
                if res.status_code == 200:
                    data = res.json()
                    st.success(f"The current price of {ticker} is ${data['price']:.2f}")
                else:
                    st.error(f"Error: {res.json().get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"Could not connect to API: {e}")
        else:
            st.warning("Please enter a ticker symbol")

# Performance Section
st.divider()
st.subheader("Portfolio Performance (EUR)")
try:
    metrics_res = requests.get(f"{API_URL}/portfolio/metrics")
    if metrics_res.status_code == 200:
        m = metrics_res.json()
        fx_rate = m.get("usd_eur_rate", 1.0)
        
        # Top Metrics (EUR Focus)
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        col1.metric("Portfolio Value", f"€{m['total_portfolio_value']:,.2f}", 
                   delta=f"€{m['total_portfolio_value'] - m['total_contributed']:,.2f}")
        
        cash_val = m['cash_balance']
        if cash_val < 0:
            col2.metric("Portfolio Debt", f"€{abs(cash_val):,.2f}", delta="Negative Cash", delta_color="inverse")
        else:
            col2.metric("Available Cash", f"€{cash_val:,.2f}")
            
        col3.metric("Stock Value", f"€{m['stock_value']:,.2f}")
        col4.metric("Net Contribution", f"€{m['total_contributed']:,.2f}")
        col5.metric("XIRR (Annual)", f"{m['xirr']*100:.2f}%")
        col6.metric("CAGR", f"{m['cagr']*100:.2f}%")
        
        # Investment Evolution Chart
        if m.get('invested_series'):
            st.write("### 📈 Portfolio Evolution (EUR)")
            hist_df = pd.DataFrame(m['invested_series'])
            hist_df['date'] = pd.to_datetime(hist_df['date'], format='ISO8601')
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hist_df['date'], y=hist_df['stocks'],
                name='Stocks (EUR)', mode='lines', line=dict(width=0.5, color='#1fb5ff'),
                stackgroup='one', fillcolor='rgba(31, 181, 255, 0.4)'
            ))
            fig.add_trace(go.Scatter(
                x=hist_df['date'], y=hist_df['cash'],
                name='Cash (EUR)', mode='lines', line=dict(width=0.5, color='#00ff88'),
                stackgroup='one', fillcolor='rgba(0, 255, 136, 0.2)'
            ))
            
            fig.update_layout(
                margin=dict(l=0, r=0, t=20, b=0),
                height=400,
                xaxis_title="",
                yaxis_title="EUR (€)",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False),
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

        # Tabs
        tab1, tab2, tab3 = st.tabs(["📊 Open Positions", "💰 Realized Gains", "✅ Historical Reports"])
        
        with tab1:
            if m.get('open_positions'):
                pos_df = pd.DataFrame(m['open_positions'])
                
                # Format native currency price columns with their correct prefix/suffix symbols dynamically per row
                def format_native_price(row, val_col):
                    currency = row.get("native_currency", "EUR")
                    val = row[val_col]
                    if currency == "USD":
                        return f"${val:,.2f}"
                    elif currency == "EUR":
                        return f"€{val:,.2f}"
                    elif currency == "GBP":
                        return f"£{val:,.2f}"
                    elif currency == "GBp":
                        return f"{val:,.2f}p"
                    return f"{val:,.2f} {currency}"
                
                pos_df['avg_price_native_str'] = pos_df.apply(lambda r: format_native_price(r, 'avg_price_native'), axis=1)
                pos_df['current_price_native_str'] = pos_df.apply(lambda r: format_native_price(r, 'current_price_native'), axis=1)
                
                st.dataframe(
                    pos_df,
                    use_container_width=True,
                    column_config={
                        "ticker": "Ticker",
                        "quantity": st.column_config.NumberColumn("Shares", format="%.4f"),
                        "avg_price": st.column_config.NumberColumn("Avg Buy (EUR)", format="€ %.2f"),
                        "avg_price_native_str": "Avg Buy (Native)",
                        "current_price": st.column_config.NumberColumn("Current Price (EUR)", format="€ %.2f"),
                        "current_price_native_str": "Current Price (Native)",
                        "market_value": st.column_config.NumberColumn("Market Value (EUR)", format="€ %.2f"),
                        "return_pct": st.column_config.NumberColumn("Return %", format="%.2f%%"),
                    },
                    hide_index=True
                )
                st.caption(f"Exchange Rate: 1 USD = {fx_rate:.4f} EUR")
            else:
                st.info("No open positions at the moment.")

        with tab2:
            if m.get('closed_positions'):
                closed_df = pd.DataFrame(m['closed_positions'])
                st.dataframe(
                    closed_df,
                    use_container_width=True,
                    column_config={
                        "ticker": "Ticker",
                        "total_sold_qty": st.column_config.NumberColumn("Total Sold Qty", format="%.4f"),
                        "realized_profit": st.column_config.NumberColumn("Realized Profit (EUR)", format="€ %.2f"),
                        "return_pct": st.column_config.NumberColumn("Total Return (%)", format="%.2f%%"),
                    },
                    hide_index=True
                )
            else:
                st.info("No realized gains yet.")

        with tab3:
            REPORTS_DIR = "knowledge_base/daily_reports"
            if os.path.exists(REPORTS_DIR):
                files = sorted([f for f in os.listdir(REPORTS_DIR) if f.endswith(".md")], reverse=True)
                if files:
                    selected_file = st.selectbox("Select Report Date", files)
                    if selected_file:
                        with open(os.path.join(REPORTS_DIR, selected_file), "r") as f:
                            st.markdown(f.read())

except Exception as e:
    st.error(f"Metrics fetch failed: {e}")

# Transaction Form
st.divider()
st.subheader("Manage Transactions")
col_a, col_b = st.columns(2)

with col_a:
    with st.expander("➕ Record New Transaction"):
        with st.form("add_tx", clear_on_submit=True):
            col1, col2, colc = st.columns([2, 2, 1])
            ticker_input = col1.text_input("Ticker").upper().strip()
            action = col2.selectbox("Action", ["BUY", "SELL", "DIVIDEND", "WITHDRAWAL", "DEPOSIT"])
            currency = colc.selectbox("Currency", ["EUR", "USD", "GBP", "GBp"])
            
            col3, col4, col5 = st.columns(3)
            if action == "DIVIDEND":
                qty = col3.number_input("Shares Owned", min_value=0.0, value=1.0, format="%.4f")
                price = col4.number_input("Dividend", min_value=0.0, format="%.2f")
            elif action in ["DEPOSIT", "WITHDRAWAL"]:
                qty = 1.0
                price = col4.number_input("Amount", min_value=0.0, format="%.2f")
                ticker_input = "CASH"
            else:
                qty = col3.number_input("Quantity", min_value=0.0, format="%.4f")
                price = col4.number_input("Price (Native)", min_value=0.0, format="%.2f")
            tx_date = col5.date_input("Date", value=pd.Timestamp.now().date())
            submitted = st.form_submit_button("Submit Transaction")
            if submitted:
                if ticker_input and qty > 0 and price > 0:
                    payload = {
                        "ticker": ticker_input, 
                        "action": action, 
                        "quantity": qty, 
                        "price": price, 
                        "currency": currency,
                        "timestamp": tx_date.isoformat()
                    }
                    res = requests.post(f"{API_URL}/transactions/", json=payload)
                    if res.status_code == 200:
                        st.toast(f"✅ Recorded {action}!", icon="💰")
                        st.rerun()
                    else:
                        st.error(f"Failed to record transaction: {res.text}")
                else: st.warning("Please fill all fields")

with col_b:
    with st.expander("📁 Batch Upload (CSV)"):
        uploaded_file = st.file_uploader("Upload CSV", type="csv")
        if uploaded_file is not None:
            try:
                batch_df = pd.read_csv(uploaded_file)
                st.write("Preview:")
                st.dataframe(batch_df.head(), use_container_width=True)
                
                # Check for required columns
                required = {'ticker', 'action', 'quantity', 'price'}
                if required.issubset(batch_df.columns.str.lower()):
                    batch_default_currency = st.selectbox(
                        "Default Currency (if not specified in CSV)", 
                        ["Stock's Native Currency", "EUR", "USD", "GBP", "GBp"]
                    )
                    if st.button("Confirm Batch Upload"):
                        # Normalize columns
                        batch_df.columns = batch_df.columns.str.lower()
                        batch_txs = []
                        for _, row in batch_df.iterrows():
                            # Handle date defensively to avoid NaT/NaN JSON serialization crashes
                            ts = None
                            if 'date' in row and not pd.isna(row['date']):
                                val = pd.to_datetime(row['date'], format='mixed')
                                if not pd.isna(val):
                                    ts = val.isoformat()
                            elif 'timestamp' in row and not pd.isna(row['timestamp']):
                                val = pd.to_datetime(row['timestamp'], format='mixed')
                                if not pd.isna(val):
                                    ts = val.isoformat()
                            
                            # Handle currency dynamically - let backend auto-detect native currency if missing or empty
                            currency_val = None
                            if 'currency' in row and not pd.isna(row['currency']):
                                val = str(row['currency']).strip().upper()
                                if val:
                                    currency_val = val
                            
                            if not currency_val:
                                if batch_default_currency != "Stock's Native Currency":
                                    currency_val = batch_default_currency
                            
                            # Parse quantity and price defensively
                            qty_val = 0.0
                            if 'quantity' in row and not pd.isna(row['quantity']):
                                try:
                                    qty_val = float(row['quantity'])
                                except:
                                    pass
                                    
                            price_val = 0.0
                            if 'price' in row and not pd.isna(row['price']):
                                try:
                                    price_val = float(row['price'])
                                except:
                                    pass
                            
                            batch_txs.append({
                                "ticker": str(row['ticker']).upper().strip(),
                                "action": str(row['action']).upper().strip(),
                                "quantity": qty_val,
                                "price": price_val,
                                "currency": currency_val,
                                "timestamp": ts
                            })
                        
                        batch_res = requests.post(f"{API_URL}/transactions/batch", json=batch_txs)
                        if batch_res.status_code == 200:
                            st.success(f"Successfully uploaded {len(batch_txs)} transactions!")
                            st.rerun()
                        else:
                            st.error(f"Batch upload failed: {batch_res.text}")
                else:
                    st.error(f"CSV must contain: {required}")
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

# History Section
st.divider()
st.subheader("Transaction History")
try:
    tx_res = requests.get(f"{API_URL}/transactions/")
    if tx_res.status_code == 200:
        df = pd.DataFrame(tx_res.json())
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
            df = df.sort_values(by='timestamp', ascending=False)
            df['date'] = df['timestamp'].dt.date
            
            # Deletion Control
            with st.expander("🗑️ Delete Transactions"):
                to_delete = st.selectbox("Select Transaction to Remove", 
                                        options=df['id'].tolist(),
                                        format_func=lambda x: f"ID {x}: {df[df['id']==x]['ticker'].values[0]} {df[df['id']==x]['action'].values[0]} ({df[df['id']==x]['date'].values[0]})")
                if st.button("Confirm Delete", type="primary"):
                    del_res = requests.delete(f"{API_URL}/transactions/{to_delete}")
                    if del_res.status_code == 200:
                        st.success(f"Deleted transaction {to_delete}")
                        st.rerun()
                    else:
                        st.error("Failed to delete")

            st.dataframe(
                df[['id', 'date', 'ticker', 'action', 'quantity', 'price', 'currency']], 
                use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID"),
                    "price": st.column_config.NumberColumn("Price (Native)", format="%.2f"),
                    "currency": "Currency",
                    "quantity": st.column_config.NumberColumn(format="%.4f"),
                    "date": st.column_config.DateColumn("Date")
                },
                hide_index=True
            )
except Exception as e: st.error(f"History fetch failed: {e}")
