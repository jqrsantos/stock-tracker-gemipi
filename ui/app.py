# ui/app.py
import streamlit as st
import requests
import os
import pandas as pd

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
st.subheader("Portfolio Performance")
try:
    metrics_res = requests.get(f"{API_URL}/portfolio/metrics")
    if metrics_res.status_code == 200:
        m = metrics_res.json()
        c1, c2 = st.columns(2)
        c1.metric("Annualized Return (XIRR)", f"{m['xirr']*100:.2f}%")
        c2.metric("Growth Rate (CAGR)", f"{m['cagr']*100:.2f}%")
except Exception as e:
    st.error(f"Metrics fetch failed: {e}")

# Transaction Form
st.divider()
st.subheader("Manage Transactions")

with st.expander("➕ Record New Transaction"):
    with st.form("add_tx", clear_on_submit=True):
        col1, col2 = st.columns(2)
        ticker_input = col1.text_input("Ticker").upper()
        action = col2.selectbox("Action", ["BUY", "SELL"])
        
        col3, col4 = st.columns(2)
        qty = col3.number_input("Quantity", min_value=0.0, format="%.4f")
        price = col4.number_input("Price", min_value=0.0, format="%.2f")
        
        submitted = st.form_submit_button("Submit Transaction")
        if submitted:
            if ticker_input and qty > 0 and price > 0:
                payload = {
                    "ticker": ticker_input,
                    "action": action,
                    "quantity": qty,
                    "price": price
                }
                res = requests.post(f"{API_URL}/transactions/", json=payload)
                if res.status_code == 200:
                    st.toast(f"✅ Recorded {action} {qty} {ticker_input}!", icon="💰")
                    st.rerun()
                else:
                    st.error("Failed to record transaction")
            else:
                st.warning("Please fill all fields")

# History Section
st.divider()
st.subheader("Transaction History")
try:
    tx_res = requests.get(f"{API_URL}/transactions/")
    if tx_res.status_code == 200:
        df = pd.DataFrame(tx_res.json())
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values(by='timestamp', ascending=False)
            st.dataframe(
                df, 
                use_container_width=True,
                column_config={
                    "price": st.column_config.NumberColumn(format="$ %.2f"),
                    "quantity": st.column_config.NumberColumn(format="%.4f"),
                }
            )
        else:
            st.info("No transactions recorded yet")
except:
    st.error("Could not load history")
