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


from main import BargainCreate, compute_scouting_performance


def test_bargain_create_without_dcf_bounds():
    b = BargainCreate(
        ticker="ASML",
        name="ASML Holding",
        industry="Semiconductors",
        current_price=Decimal("850.00"),
        currency="EUR",
        rationale="Monopoly EUV lithography moat with strong backlog.",
    )
    assert b.ticker == "ASML"
    assert b.bargain_price == Decimal("0.0")
    assert b.fair_price == Decimal("0.0")
    assert b.expensive_price == Decimal("0.0")


def test_compute_scouting_performance_preserves_first_day_price():
    class MockBargainRow:
        def __init__(self, ticker, name, industry, current_price, currency, rationale, timestamp):
            self.ticker = ticker
            self.name = name
            self.industry = industry
            self.current_price = Decimal(str(current_price))
            self.currency = currency
            self.rationale = rationale
            self.timestamp = timestamp

    t1 = datetime(2026, 5, 1, 10, 0, 0)
    t2 = datetime(2026, 6, 1, 10, 0, 0)
    rows = [
        MockBargainRow("ADBE", "Adobe Inc.", "Software", 400.0, "USD", "Initial pick rationale", t1),
        MockBargainRow("ADBE", "Adobe Inc.", "Software", 440.0, "USD", "Updated rationale in June", t2),
        MockBargainRow("NVO", "Novo Nordisk", "Biotech", 120.0, "USD", "GLP-1 moat", t2),
    ]

    live_prices = {"ADBE": 500.0, "NVO": 108.0}
    result = compute_scouting_performance(rows, live_prices, now=datetime(2026, 7, 1, 10, 0, 0))

    assert result["summary"]["total_scouted"] == 2
    assert result["summary"]["win_rate_pct"] == 50.0
    # ADBE: (500 - 400)/400 = +25.0%, NVO: (108 - 120)/120 = -10.0% -> avg = +7.5%
    assert abs(result["summary"]["avg_return_pct"] - 7.5) < 0.01
    assert result["summary"]["best_pick"]["ticker"] == "ADBE"
    assert result["summary"]["worst_pick"]["ticker"] == "NVO"

    adbe_pick = next(p for p in result["picks"] if p["ticker"] == "ADBE")
    assert adbe_pick["initial_price"] == 400.0
    assert adbe_pick["current_price"] == 500.0
    assert adbe_pick["return_pct"] == 25.0
    assert adbe_pick["times_recommended"] == 2
    assert adbe_pick["rationale"] == "Updated rationale in June"
    assert adbe_pick["days_tracked"] == 61


def test_compute_scouting_performance_with_dip_and_status():
    class MockBargainRowWithStatus:
        def __init__(self, ticker, name, industry, current_price, currency, rationale, timestamp, status="ACTIVE", dismissal_reason=None):
            self.ticker = ticker
            self.name = name
            self.industry = industry
            self.current_price = Decimal(str(current_price))
            self.currency = currency
            self.rationale = rationale
            self.timestamp = timestamp
            self.status = status
            self.dismissal_reason = dismissal_reason
            self.deep_dossier = None

    t1 = datetime(2026, 5, 1, 10, 0, 0)
    rows = [
        # NOW: Alerted at 100, dipped to 80 (20% discount), now at 120
        # Alert Return = +20%, Peak Dip Return = +50%
        MockBargainRowWithStatus("NOW", "ServiceNow", "Software", 100.0, "USD", "Initial alert", t1, "ACTIVE"),
        # INTC: Alerted at 30, dipped to 20, now at 22, DISMISSED
        MockBargainRowWithStatus("INTC", "Intel Corp", "Semiconductors", 30.0, "USD", "Old dip", t1, "DISMISSED", "Foundry execution risks"),
    ]

    live_prices = {"NOW": 120.0, "INTC": 22.0}
    lowest_prices = {"NOW": 80.0, "INTC": 20.0}

    result = compute_scouting_performance(rows, live_prices, lowest_prices=lowest_prices, now=datetime(2026, 7, 1, 10, 0, 0))

    assert result["summary"]["total_scouted"] == 2
    assert result["summary"]["active_count"] == 1
    assert result["summary"]["dismissed_count"] == 1

    now_pick = next(p for p in result["picks"] if p["ticker"] == "NOW")
    assert now_pick["status"] == "ACTIVE"
    assert now_pick["initial_price"] == 100.0
    assert now_pick["lowest_price_since_alert"] == 80.0
    assert now_pick["current_price"] == 120.0
    assert now_pick["return_pct"] == 20.0
    assert now_pick["max_dip_discount_pct"] == -20.0
    assert now_pick["peak_dip_return_pct"] == 50.0

    intc_pick = next(p for p in result["picks"] if p["ticker"] == "INTC")
    assert intc_pick["status"] == "DISMISSED"
    assert intc_pick["dismissal_reason"] == "Foundry execution risks"
    assert intc_pick["lowest_price_since_alert"] == 20.0
    assert intc_pick["max_dip_discount_pct"] == -33.33
    assert intc_pick["peak_dip_return_pct"] == 10.0


