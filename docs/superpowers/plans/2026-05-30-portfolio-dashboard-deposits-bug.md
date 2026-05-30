# Portfolio Dashboard Deposits Bug & Currency Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the Streamlit form dynamic rendering issue to allow transaction deposit/withdrawal insertion, restrict currencies to EUR and USD, and purge the test LSE (`BP.L`) transaction to correct the portfolio metrics.

**Architecture:** 
1. **Frontend (`ui/app.py`)**: Move the Action selectbox outside of the `st.form` block under the `"➕ Record New Transaction"` expander to trigger a page re-run and dynamic widget updates when changing the transaction type. Restrict currency inputs to only EUR and USD.
2. **Backend (`api/main.py` & `api/metrics.py`)**: Update currency auto-detection and validations to limit options to EUR and USD (defaulting to EUR on fallback/unknown currencies), simplifying exchange rate caching.
3. **Database (`db/stock_tracker.db`)**: Delete transaction ID `3` (the `BP.L` test transaction).

**Tech Stack:** Python 3.13, Streamlit, FastAPI, SQLAlchemy, SQLite, Pytest.

---

### Task 1: Database - Purge test LSE (`BP.L`) transaction

**Files:**
- Modify: `db/stock_tracker.db`

- [x] **Step 1: Run SQLite script to delete the transaction**

Run:
```bash
.venv/bin/python -c "import sqlite3; conn = sqlite3.connect('db/stock_tracker.db'); cursor = conn.cursor(); cursor.execute('DELETE FROM transactions WHERE id = 3'); conn.commit(); print('Successfully deleted transaction ID 3'); conn.close()"
```

Expected Output:
```
Successfully deleted transaction ID 3
```

- [x] **Step 2: Commit database removal**

Run:
```bash
git commit -am "db: purge test BP.L transaction from stock tracker database"
```

---

### Task 2: Backend - Simplify currency logic to EUR & USD

**Files:**
- Modify: `api/main.py`

- [ ] **Step 1: Modify `get_native_currency` in `api/main.py:124-133`**

We will update the `get_native_currency` function to only return `"USD"` or `"EUR"`.

```python
def get_native_currency(ticker: str) -> str:
    if ticker.upper() == "CASH":
        return "EUR"
    try:
        price, currency = fetch_stock_info(ticker)
        if currency:
            currency_upper = currency.upper()
            if currency_upper in ["USD", "EUR"]:
                return currency_upper
    except Exception as e:
        logger.warning(f"Failed to fetch stock info for auto-currency lookup on {ticker}: {e}")
    return "EUR"
```

- [ ] **Step 2: Modify `TransactionCreate` validator/schema in `api/main.py:21-27`**

We will add a field validator to `TransactionCreate` in `api/main.py` to enforce that the currency can only be `"EUR"` or `"USD"` (or `None`).

```python
from pydantic import BaseModel, field_validator

class TransactionCreate(BaseModel):
    ticker: str
    action: str
    quantity: Decimal
    price: Decimal
    currency: Optional[str] = None
    timestamp: Optional[datetime] = None

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_upper = v.strip().upper()
            if v_upper not in ["EUR", "USD"]:
                raise ValueError("Currency must be EUR or USD")
            return v_upper
        return v
```

- [ ] **Step 3: Modify `get_exchange_rate` in `api/main.py:201-233`**

Simplify exchange rate to only resolve EUR and USD. Remove GBp and GBP pence divisions entirely.

```python
def get_exchange_rate(from_currency: str, to_currency: str, date_obj: Optional[datetime] = None):
    if from_currency == to_currency:
        return 1.0
    ticker = f"{from_currency}{to_currency}=X"
    try:
        stock = yf.Ticker(ticker)
        if date_obj:
            start_date = date_obj.strftime('%Y-%m-%d')
            end_date = (date_obj + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            hist = stock.history(start=start_date, end=end_date)
            if not hist.empty:
                rate = float(hist['Close'].iloc[0])
                logger.info(f"Historical rate for {ticker} on {start_date}: {rate}")
                return rate
            else:
                logger.warning(f"No historical data for {ticker} on {start_date}")
        
        # Fallback to current rate
        history = stock.history(period="1d")
        if not history.empty:
            rate = float(history['Close'].iloc[-1])
            logger.info(f"Current rate for {ticker}: {rate}")
            return rate
        
        logger.warning(f"No data found for {ticker}, returning 1.0")
        return 1.0
    except Exception as e:
        logger.error(f"Error fetching exchange rate for {ticker}: {e}")
        return 1.0
```

- [ ] **Step 4: Commit backend simplifications**

Run:
```bash
git commit -am "api: restrict transaction currencies to EUR/USD and simplify exchange rate calculations"
```

---

### Task 3: Tests - Update API tests to match currency changes

**Files:**
- Modify: `api/tests/test_currency_and_insert.py`

- [ ] **Step 1: Update `test_get_native_currency_fallback` in `api/tests/test_currency_and_insert.py:22-31`**

We will update the test to expect `EUR` as a fallback for any non-USD/EUR currency (like LSE ticker fallback/defaults).

```python
def test_get_native_currency_fallback():
    # Verify auto-detection defaults to EUR or fetches appropriately
    assert get_native_currency("CASH") == "EUR"
    
    # Non-existing ticker falls back to EUR
    assert get_native_currency("NONEXISTINGTICKERZZZZ") == "EUR"
    
    # Apple is USD
    assert get_native_currency("AAPL") == "USD"
```

- [ ] **Step 2: Run pytest to ensure all tests pass**

Run:
```bash
../.venv/bin/python -m pytest tests
```

Expected Output:
```
======================== 3 passed, 3 warnings in 4.77s =========================
```

- [ ] **Step 3: Commit test updates**

Run:
```bash
git commit -am "api/tests: update test cases for simplified native currency fallback rules"
```

---

### Task 4: Frontend - Dynamic Streamlit Transaction Form Re-architecture

**Files:**
- Modify: `ui/app.py:161-282`

- [ ] **Step 1: Refactor `Record New Transaction` expander inside `ui/app.py`**

We will move the Action selectbox outside the form block (directly inside the expander) to force dynamic UI updates.
We will restrict currency selections in the selectboxes to `EUR` and `USD`.
We will hide the "Ticker" input if the action is `DEPOSIT` or `WITHDRAWAL`, automatically setting it to `"CASH"`.
We will also clean up batch default currency choices.

```python
# ui/app.py lines 161 to 282 replacement code:
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
                    res = requests.post(f"{API_URL}/transactions/", json=payload)
                    if res.status_code == 200:
                        st.toast(f"✅ Recorded {action}!", icon="💰")
                        st.rerun()
                    else:
                        st.error(f"Failed to record transaction: {res.text}")
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
                        ["Stock's Native Currency", "EUR", "USD"]
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
                                if batch_default_currency != "Stock's Native Currency":
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
```

- [ ] **Step 2: Commit frontend form refactoring**

Run:
```bash
git add ui/app.py
git commit -m "ui: pull action selectbox outside st.form to enable dynamic fields rendering"
```

---

### Task 5: Verification - End-to-End Test Verification

**Files:**
- Run local servers
- Verify API & Streamlit dynamic behavior

- [ ] **Step 1: Verify all unit tests pass successfully**

Run:
```bash
../.venv/bin/python -m pytest tests
```

Expected Output:
```
======================== 3 passed, 3 warnings in 4.77s =========================
```
