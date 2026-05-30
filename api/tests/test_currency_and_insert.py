# api/tests/test_currency_and_insert.py
import pytest
from decimal import Decimal
from datetime import datetime
from main import TransactionCreate, TransactionResponse, get_native_currency, get_exchange_rate
from models import Transaction
from metrics import calculate_portfolio_performance

def test_transaction_create_decimal():
    # Verify Pydantic TransactionCreate handles Decimal inputs and optional currency
    tx = TransactionCreate(
        ticker="AAPL",
        action="BUY",
        quantity=Decimal("12.34567890"),
        price=Decimal("150.75"),
        currency=None
    )
    assert tx.quantity == Decimal("12.34567890")
    assert tx.price == Decimal("150.75")
    assert tx.currency is None

def test_get_native_currency_fallback():
    # Verify auto-detection defaults to EUR or fetches appropriately
    assert get_native_currency("CASH") == "EUR"
    
    # Non-existing ticker falls back to EUR
    assert get_native_currency("NONEXISTINGTICKERZZZZ") == "EUR"
    
    # Apple is USD
    assert get_native_currency("AAPL") == "USD"

def test_calculate_portfolio_performance_native_currency():
    # Verify metrics correctly computes native price, native avg buy, and returns native currency
    class MockTransaction:
        def __init__(self, ticker, action, quantity, price, timestamp, native_currency, native_price):
            self.ticker = ticker
            self.action = action
            self.quantity = Decimal(str(quantity))
            self.price = Decimal(str(price))
            self.timestamp = timestamp
            self.native_currency = native_currency
            self.native_price = Decimal(str(native_price))

    now = datetime.now()
    transactions = [
        # Bought 10 AAPL in USD at $150 (EUR price: 135)
        MockTransaction("AAPL", "BUY", 10, 135.0, now, "USD", 150.0),
        # Bought 5 AAPL in USD at $160 (EUR price: 144)
        MockTransaction("AAPL", "BUY", 5, 144.0, now, "USD", 160.0),
    ]

    current_prices = {"AAPL": 148.5} # EUR current price
    current_prices_native = {"AAPL": 165.0} # USD current price

    perf = calculate_portfolio_performance(transactions, current_prices, current_prices_native)
    assert perf["stock_value"] == 15 * 148.5
    
    positions = perf["open_positions"]
    assert len(positions) == 1
    aapl_pos = positions[0]
    
    assert aapl_pos["ticker"] == "AAPL"
    assert aapl_pos["quantity"] == 15.0
    assert aapl_pos["native_currency"] == "USD"
    # Weighted average native buy: (10*150 + 5*160)/15 = (1500 + 800)/15 = 2300/15 = 153.333333
    assert abs(aapl_pos["avg_price_native"] - 153.333333) < 0.0001
    assert aapl_pos["current_price_native"] == 165.0

def test_transaction_create_currency_validation():
    # Valid currencies should pass and be converted to uppercase
    tx1 = TransactionCreate(
        ticker="AAPL",
        action="BUY",
        quantity=Decimal("10"),
        price=Decimal("150"),
        currency="usd"
    )
    assert tx1.currency == "USD"

    tx2 = TransactionCreate(
        ticker="AAPL",
        action="BUY",
        quantity=Decimal("10"),
        price=Decimal("150"),
        currency="EUR"
    )
    assert tx2.currency == "EUR"

    # None is allowed (defaults to native currency)
    tx3 = TransactionCreate(
        ticker="AAPL",
        action="BUY",
        quantity=Decimal("10"),
        price=Decimal("150"),
        currency=None
    )
    assert tx3.currency is None

    # Invalid currencies should raise ValueError
    with pytest.raises(ValueError, match="Currency must be EUR or USD"):
        TransactionCreate(
            ticker="AAPL",
            action="BUY",
            quantity=Decimal("10"),
            price=Decimal("150"),
            currency="GBP"
        )

    with pytest.raises(ValueError, match="Currency must be EUR or USD"):
        TransactionCreate(
            ticker="AAPL",
            action="BUY",
            quantity=Decimal("10"),
            price=Decimal("150"),
            currency="GBp"
        )

def test_get_exchange_rate_simplification():
    # Identical currency should return 1.0
    assert get_exchange_rate("EUR", "EUR") == 1.0
    assert get_exchange_rate("USD", "USD") == 1.0

