# ui/app.py
import streamlit as st
import requests
import os

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

st.info("Portfolio metrics and transaction entry coming soon...")
