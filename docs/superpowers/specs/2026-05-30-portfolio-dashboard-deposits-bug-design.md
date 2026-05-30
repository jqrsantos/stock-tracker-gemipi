# Spec: Fix Portfolio Dashboard Deposit Insertion & Currency Simplification

**Date**: 2026-05-30
**Topic**: Portfolio Dashboard Deposits Bug & EUR/USD Currency Simplification

---

## 🎯 Goal & Problem Statement

The stock portfolio dashboard has two main issues impacting metrics calculations and usability:
1. **Deposits Bug**: Users cannot insert `DEPOSIT` or `WITHDRAWAL` transactions. In the Streamlit UI, these actions are in a form where selectbox state changes do not trigger re-runs. Because of this, the fields for deposits (like "Amount") are never rendered on the screen before the user submits, resulting in zero-valued prices, validation failures (`price > 0` fails), and the warning `"Please fill all fields"`.
2. **Metrics Distortions**:
   * Without deposits, the portfolio's cash balance is deeply negative, distorting XIRR and CAGR.
   * A test transaction for `BP.L` is recorded in `"GBP"` but priced in pence (`450`), causing the system to calculate the purchase as £450.00/share rather than £4.50, causing a massive artificial loss on the dashboard.

---

## 💡 Proposed Changes

We will fix the Streamlit form behavior to correctly allow deposit/withdrawal insertion, simplify the currency model to support only `EUR` and `USD`, and purge the test `BP.L` transaction.

### 1. Frontend: Streamlit Transaction Form Re-architecture (`ui/app.py`)
* Move the **Action** selectbox outside of the `st.form` block under the `"➕ Record New Transaction"` expander. 
* This allows Streamlit to instantly re-run and render the custom-tailored fields (like "Amount" for deposits) when the Action is changed.
* Keep all other inputs (Ticker, Quantity, Price, Currency, Date) inside the `st.form` block to prevent keystrokes from causing unwanted page re-runs.
* Limit the **Currency** selectbox options to `["EUR", "USD"]`.
* Update dynamic logic for `DEPOSIT` and `WITHDRAWAL` to:
  * Hide the Ticker input (automatically defaulting `ticker_input = "CASH"` on form submission).
  * Show an `"Amount"` field mapping to `price` (with `qty = 1.0` automatically set).
* Limit default currency options in Batch Upload (CSV) to `["Stock's Native Currency", "EUR", "USD"]`.

### 2. Backend: API Simplification (`api/main.py`)
* Update `get_native_currency(ticker)` to only return `"USD"` or `"EUR"`. If a stock's currency fetched from yfinance is not USD, EUR, or if it fails, default to `"EUR"`.
* Restrict `TransactionCreate` validation to only allow `"EUR"` or `"USD"` currencies.
* Simplify the exchange rate engine (`get_exchange_rate`) to only process EUR and USD (remove GBp and GBP-specific handling).

### 3. Database: Test Data Purging
* Execute a SQLite script to remove the test `BP.L` transaction from `db/stock_tracker.db` (Transaction ID `3`).

---

## 🧪 Verification Plan

### Automated Verification
* Run backend tests via pytest to ensure no regressions:
  ```bash
  ../.venv/bin/python -m pytest tests
  ```
* Run a custom script to verify the SQLite database has had the test transaction removed.

### Manual Verification
1. Open the Streamlit dashboard and open the `"➕ Record New Transaction"` expander.
2. Select `"DEPOSIT"` under **Action**. Verify that:
   * The "Ticker" input is hidden.
   * An "Amount" input appears.
   * The Currency dropdown has only `"EUR"` and `"USD"`.
3. Enter `10000.0` EUR and click **Submit Transaction**. Verify that the deposit is successfully saved, a toast appears, and the Cash Balance updates to reflect the new cash.
4. Select `"BUY"` under **Action**. Verify that "Ticker", "Quantity", and "Price (Native)" inputs appear.
