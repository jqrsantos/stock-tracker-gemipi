# api/tests/test_currency_and_insert.py
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch
from pydantic import ValidationError
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
    with patch("main.fetch_stock_info") as mock_fetch:
        # Verify CASH defaults to EUR without network query
        assert get_native_currency("CASH") == "EUR"
        
        # Non-existing ticker falls back to EUR
        mock_fetch.return_value = (None, None)
        assert get_native_currency("NONEXISTINGTICKERZZZZ") == "EUR"
        
        # Apple is USD
        mock_fetch.return_value = (150.0, "USD")
        assert get_native_currency("AAPL") == "USD"
        
        # BP is GBp (not USD or EUR), should fallback to EUR
        mock_fetch.return_value = (450.0, "GBp")
        assert get_native_currency("BP.L") == "EUR"


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
    # Valid currencies
    tx_eur = TransactionCreate(ticker="AAPL", action="BUY", quantity=1.0, price=100.0, currency="eur")
    assert tx_eur.currency == "EUR"
    
    tx_usd = TransactionCreate(ticker="AAPL", action="BUY", quantity=1.0, price=100.0, currency=" USD ")
    assert tx_usd.currency == "USD"
    
    tx_none = TransactionCreate(ticker="AAPL", action="BUY", quantity=1.0, price=100.0, currency=None)
    assert tx_none.currency is None

    # Invalid currency
    with pytest.raises(ValidationError):
        TransactionCreate(ticker="AAPL", action="BUY", quantity=1.0, price=100.0, currency="GBP")


def test_get_exchange_rate_simplification():
    # Identical currency should return 1.0
    assert get_exchange_rate("EUR", "EUR") == 1.0
    assert get_exchange_rate("USD", "USD") == 1.0

