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
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Open Positions",
            "💰 Realized Gains",
            "🎯 Scouting Performance",
            "✅ Historical Reports",
        ])
        
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
            try:
                scout_res = requests.get(f"{API_URL}/bargains/performance", timeout=10)
                if scout_res.status_code == 200:
                    scout_data = scout_res.json()
                    summary = scout_data.get("summary", {})
                    picks = scout_data.get("picks", [])

                    if picks:
                        sc1, sc2, sc3, sc4 = st.columns(4)
                        sc1.metric("Total Scouted Stocks", summary.get("total_scouted", 0))
                        sc2.metric("Active / Dismissed", f"{summary.get('active_count', 0)} / {summary.get('dismissed_count', 0)}")
                        sc3.metric("Avg Alert Return", f"{summary.get('avg_return_pct', 0.0):+.2f}%")
                        best = summary.get("best_pick")
                        if best:
                            sc4.metric("Best Scouted Pick", best["ticker"], f"{best['return_pct']:+.2f}%")
                        else:
                            sc4.metric("Best Scouted Pick", "N/A")

                        scout_df = pd.DataFrame(picks)
                        scout_df["first_date"] = pd.to_datetime(scout_df["first_recommended_at"], format="ISO8601").dt.date
                        if "status" not in scout_df.columns:
                            scout_df["status"] = "ACTIVE"
                        if "dismissal_reason" not in scout_df.columns:
                            scout_df["dismissal_reason"] = ""
                        if "deep_dossier" not in scout_df.columns:
                            scout_df["deep_dossier"] = ""
                        if "lowest_price_since_alert" not in scout_df.columns:
                            scout_df["lowest_price_since_alert"] = scout_df["initial_price"]
                        if "max_dip_discount_pct" not in scout_df.columns:
                            scout_df["max_dip_discount_pct"] = 0.0
                        if "peak_dip_return_pct" not in scout_df.columns:
                            scout_df["peak_dip_return_pct"] = scout_df["return_pct"]

                        # Filter Controls
                        col_f1, col_f2 = st.columns([2, 2])
                        with col_f1:
                            filter_mode = st.radio(
                                "Watchlist Filter:",
                                [
                                    "Active Conviction (High Moat)",
                                    "All Recommendations",
                                    "Dismissed Archive (Broken Thesis)",
                                ],
                                horizontal=True,
                            )
                        with col_f2:
                            sort_by = st.selectbox(
                                "Sort by:",
                                [
                                    "Highest Alert Return (%)",
                                    "Highest Peak Dip Return (%)",
                                    "Deepest Max Dip (%)",
                                    "Most Frequently Picked",
                                    "Newest",
                                    "Oldest",
                                ],
                            )

                        filtered_df = scout_df.copy()
                        if filter_mode == "Active Conviction (High Moat)":
                            filtered_df = filtered_df[filtered_df["status"] == "ACTIVE"]
                        elif filter_mode == "Dismissed Archive (Broken Thesis)":
                            filtered_df = filtered_df[filtered_df["status"] == "DISMISSED"]

                        if sort_by == "Highest Alert Return (%)":
                            filtered_df = filtered_df.sort_values(by="return_pct", ascending=False)
                        elif sort_by == "Highest Peak Dip Return (%)":
                            filtered_df = filtered_df.sort_values(by="peak_dip_return_pct", ascending=False)
                        elif sort_by == "Deepest Max Dip (%)":
                            filtered_df = filtered_df.sort_values(by="max_dip_discount_pct", ascending=True)
                        elif sort_by == "Most Frequently Picked":
                            filtered_df = filtered_df.sort_values(by="times_recommended", ascending=False)
                        elif sort_by == "Newest":
                            filtered_df = filtered_df.sort_values(by="first_recommended_at", ascending=False)
                        elif sort_by == "Oldest":
                            filtered_df = filtered_df.sort_values(by="first_recommended_at", ascending=True)

                        if filtered_df.empty:
                            st.info(f"No stocks found matching '{filter_mode}'.")
                        else:
                            st.caption(f"Showing {len(filtered_df)} of {len(scout_df)} scouted companies")
                            st.dataframe(
                                filtered_df[[
                                    "ticker",
                                    "name",
                                    "industry",
                                    "status",
                                    "first_date",
                                    "days_tracked",
                                    "initial_price",
                                    "lowest_price_since_alert",
                                    "current_price",
                                    "currency",
                                    "return_pct",
                                    "max_dip_discount_pct",
                                    "peak_dip_return_pct",
                                    "times_recommended",
                                    "dismissal_reason",
                                    "rationale",
                                ]],
                                use_container_width=True,
                                column_config={
                                    "ticker": "Ticker",
                                    "name": "Company",
                                    "industry": "Industry",
                                    "status": "Status",
                                    "first_date": st.column_config.DateColumn("First Recommended"),
                                    "days_tracked": st.column_config.NumberColumn("Days Tracked"),
                                    "initial_price": st.column_config.NumberColumn("Alert Price", format="%.2f"),
                                    "lowest_price_since_alert": st.column_config.NumberColumn("Lowest Dip", format="%.2f"),
                                    "current_price": st.column_config.NumberColumn("Current Price", format="%.2f"),
                                    "currency": "Currency",
                                    "return_pct": st.column_config.NumberColumn("Alert Return %", format="%+.2f%%"),
                                    "max_dip_discount_pct": st.column_config.NumberColumn("Max Dip %", format="%+.2f%%"),
                                    "peak_dip_return_pct": st.column_config.NumberColumn("Peak Dip Return %", format="%+.2f%%"),
                                    "times_recommended": st.column_config.NumberColumn("Times Picked"),
                                    "dismissal_reason": "Dismissal Reason",
                                    "rationale": "Latest Moat & News Assessment",
                                },
                                hide_index=True,
                            )

                            with st.expander("🔍 View Deep Audit Dossiers (Weekly Swarm Intelligence)"):
                                stocks_with_dossier = filtered_df[
                                    filtered_df["deep_dossier"].notna()
                                    & (filtered_df["deep_dossier"].astype(str).str.strip() != "")
                                    & (filtered_df["deep_dossier"].astype(str).str.strip() != "None")
                                ]
                                if not stocks_with_dossier.empty:
                                    selected_ticker = st.selectbox(
                                        "Select Stock Dossier:",
                                        stocks_with_dossier["ticker"].tolist(),
                                        format_func=lambda t: f"{t} - {stocks_with_dossier[stocks_with_dossier['ticker'] == t]['name'].values[0]} ({stocks_with_dossier[stocks_with_dossier['ticker'] == t]['status'].values[0]})",
                                    )
                                    if selected_ticker:
                                        dossier_text = stocks_with_dossier[
                                            stocks_with_dossier["ticker"] == selected_ticker
                                        ]["deep_dossier"].values[0]
                                        st.markdown(dossier_text)
                                else:
                                    st.info("No deep audit dossiers recorded yet. Run ./run_weekly_deep_scour.sh to generate weekly swarm audits.")
                    else:
                        st.info("No scouted stock recommendations recorded yet.")
                else:
                    st.warning("Could not load scouting performance data.")
            except Exception as e:
                st.error(f"Failed to fetch scouting performance: {e}")

        with tab4:
            report_kind = st.radio("Report Category:", ["Daily Market Briefings", "Weekly Swarm Audits"], horizontal=True)
            target_dir = "knowledge_base/daily_reports" if report_kind == "Daily Market Briefings" else "knowledge_base/weekly_reports"
            if os.path.exists(target_dir):
                files = sorted([f for f in os.listdir(target_dir) if f.endswith(".md")], reverse=True)
                if files:
                    selected_file = st.selectbox("Select Report Date", files)
                    if selected_file:
                        pdf_candidate = os.path.splitext(selected_file)[0] + ".pdf"
                        pdf_full_path = os.path.join(target_dir, pdf_candidate)
                        if os.path.exists(pdf_full_path):
                            with open(pdf_full_path, "rb") as pdf_file:
                                st.download_button(
                                    label=f"📥 Download Full 24-Page PDF Dossier ({pdf_candidate})",
                                    data=pdf_file.read(),
                                    file_name=pdf_candidate,
                                    mime="application/pdf",
                                    use_container_width=True,
                                )
                        with open(os.path.join(target_dir, selected_file), "r") as f:
                            st.markdown(f.read())
                else:
                    st.info(f"No {report_kind.lower()} found yet.")
            else:
                st.info(f"Directory '{target_dir}' does not exist yet.")

except Exception as e:
    st.error(f"Metrics fetch failed: {e}")

# Transaction Form
st.divider()
st.subheader("Manage Transactions")
col_a, col_b = st.columns(2)

with col_a:
    with st.expander("➕ Record New Transaction"):
        # Action is pulled OUT of the st.form to trigger immediate Streamlit re-run
        action = st.selectbox("Action", ["BUY", "SELL", "DIVIDEND", "WITHDRAWAL", "DEPOSIT"])
        
        with st.form("add_tx", clear_on_submit=True):
            col1, colc = st.columns([3, 1])
            currency = colc.selectbox("Currency", ["EUR", "USD"])
            
            # Conditionally render fields based on action
            if action in ["DEPOSIT", "WITHDRAWAL"]:
                ticker_input = "CASH"
                col1.info("Transaction type: CASH")
            else:
                ticker_input = col1.text_input("Ticker").upper().strip()

            col3, col4, col5 = st.columns(3)
            
            if action == "DIVIDEND":
                qty = col3.number_input("Shares Owned", min_value=0.0, value=1.0, format="%.4f")
                price = col4.number_input("Dividend", min_value=0.0, format="%.2f")
            elif action in ["DEPOSIT", "WITHDRAWAL"]:
                qty = 1.0
                price = col4.number_input("Amount", min_value=0.0, format="%.2f")
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
                    try:
                        res = requests.post(f"{API_URL}/transactions/", json=payload)
                        if res.status_code == 200:
                            st.toast(f"✅ Recorded {action}!", icon="💰")
                            st.rerun()
                        else:
                            st.error(f"Failed to record transaction: {res.text}")
                    except Exception as e:
                        st.error(f"Network error: Could not connect to API ({e})")
                else:
                    st.warning("Please fill all fields with non-zero values")

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
                        ["Stock's Native (EUR/USD only, others default to EUR)", "EUR", "USD"]
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
                            
                            # Handle currency dynamically
                            currency_val = None
                            if 'currency' in row and not pd.isna(row['currency']):
                                val = str(row['currency']).strip().upper()
                                if val in ["EUR", "USD"]:
                                    currency_val = val
                            
                            if not currency_val:
                                if batch_default_currency != "Stock's Native (EUR/USD only, others default to EUR)":
                                    currency_val = batch_default_currency
                            
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
                        
                        try:
                            batch_res = requests.post(f"{API_URL}/transactions/batch", json=batch_txs)
                            if batch_res.status_code == 200:
                                st.success(f"Successfully uploaded {len(batch_txs)} transactions!")
                                st.rerun()
                            else:
                                st.error(f"Batch upload failed: {batch_res.text}")
                        except Exception as e:
                            st.error(f"Network error during batch upload: Could not connect to API ({e})")
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
                    try:
                        del_res = requests.delete(f"{API_URL}/transactions/{to_delete}")
                        if del_res.status_code == 200:
                            st.success(f"Deleted transaction {to_delete}")
                            st.rerun()
                        else:
                            st.error("Failed to delete")
                    except Exception as e:
                        st.error(f"Network error during deletion: Could not connect to API ({e})")

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
