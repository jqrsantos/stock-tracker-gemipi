from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
from functools import lru_cache
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from decimal import Decimal
import logging
import yfinance as yf
import pandas as pd

import models
import database
import metrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

class TransactionResponse(BaseModel):
    id: int
    ticker: str
    action: str
    quantity: Decimal
    price: Decimal
    currency: str
    timestamp: datetime

    class Config:
        from_attributes = True

class BargainCreate(BaseModel):
    ticker: str
    name: str
    industry: str
    current_price: Decimal
    currency: str = "USD"
    bargain_price: Decimal
    fair_price: Decimal
    expensive_price: Decimal
    rationale: str

class BargainResponse(BaseModel):
    id: int
    ticker: str
    name: str
    industry: str
    current_price: Decimal
    currency: str
    bargain_price: Decimal
    fair_price: Decimal
    expensive_price: Decimal
    rationale: str
    timestamp: datetime

    class Config:
        from_attributes = True

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

import time

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables with retries
    max_retries = 5
    for i in range(max_retries):
        try:
            logger.info(f"Initializing database... (Attempt {i+1}/{max_retries})")
            models.Base.metadata.create_all(bind=database.engine)
            logger.info("Database initialized successfully.")
            break
        except Exception as e:
            if i == max_retries - 1:
                logger.error("Could not connect to database after several attempts.")
                raise e
            logger.warning(f"Database not ready, retrying in 5 seconds... ({e})")
            time.sleep(5)
    yield

app = FastAPI(lifespan=lifespan)

@lru_cache(maxsize=100)
def fetch_stock_info(ticker: str):
    stock = yf.Ticker(ticker)
    history = stock.history(period="1d")
    if history.empty:
        return None, None
    price = float(history['Close'].iloc[-1])
    # Fetch currency from info, default to USD if not found
    try:
        currency = stock.info.get('currency', 'USD')
    except:
        currency = 'USD'
    return price, currency

@app.get("/price/{ticker}")
def get_price(ticker: str):
    try:
        price, currency = fetch_stock_info(ticker)
        if price is None:
            raise HTTPException(status_code=404, detail="Ticker not found")
        return {"ticker": ticker, "price": price, "currency": currency}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching price for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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

@app.post("/transactions/", response_model=TransactionResponse)
def add_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    try:
        tx_currency = transaction.currency
        if not tx_currency or tx_currency.strip() == "":
            tx_currency = get_native_currency(transaction.ticker)
            
        # Convert Pydantic model to SQLAlchemy model
        db_tx = models.Transaction(
            ticker=transaction.ticker,
            action=transaction.action,
            quantity=transaction.quantity,
            price=transaction.price,
            currency=tx_currency,
            timestamp=transaction.timestamp if transaction.timestamp else datetime.utcnow()
        )
        db.add(db_tx)
        db.commit()
        db.refresh(db_tx)
        logger.info(f"Added transaction: {db_tx.id} for {db_tx.ticker}")
        return db_tx
    except Exception as e:
        logger.error(f"Error adding transaction: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transactions/batch")
def add_transactions_batch(transactions: List[TransactionCreate], db: Session = Depends(get_db)):
    try:
        db_txs = []
        for tx in transactions:
            tx_currency = tx.currency
            if not tx_currency or tx_currency.strip() == "":
                tx_currency = get_native_currency(tx.ticker)
                
            db_tx = models.Transaction(
                ticker=tx.ticker,
                action=tx.action,
                quantity=tx.quantity,
                price=tx.price,
                currency=tx_currency,
                timestamp=tx.timestamp if tx.timestamp else datetime.utcnow()
            )
            db.add(db_tx)
            db_txs.append(db_tx)
        db.commit()
        logger.info(f"Added {len(db_txs)} transactions in batch")
        return {"count": len(db_txs)}
    except Exception as e:
        logger.error(f"Error adding batch transactions: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/transactions/", response_model=List[TransactionResponse])
def get_transactions(db: Session = Depends(get_db)):
    return db.query(models.Transaction).all()

@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    db_tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not db_tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(db_tx)
    db.commit()
    return {"detail": "Transaction deleted"}

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

@app.get("/portfolio/metrics")
def get_metrics(db: Session = Depends(get_db)):
    transactions = db.query(models.Transaction).all()
    if not transactions:
        return {"xirr": 0.0, "cagr": 0.0}
    
    # Pre-calculate EUR prices for all transactions
    eur_transactions = []
    exchange_rates_cache = {}

    class MockTx:
        def __init__(self, t, a, q, p, ts, id, native_currency, native_price):
            self.ticker = t
            self.action = a
            self.quantity = q
            self.price = Decimal(str(p))
            self.timestamp = ts
            self.id = id
            self.native_currency = native_currency
            self.native_price = Decimal(str(native_price))

    def get_cached_rate(from_curr, to_curr, dt):
        if from_curr == to_curr: return 1.0
        # Use date as key for historical cache
        key = (from_curr, to_curr, dt.date() if dt else None)
        if key not in exchange_rates_cache:
            exchange_rates_cache[key] = get_exchange_rate(from_curr, to_curr, dt)
        return exchange_rates_cache[key]

    for tx in transactions:
        rate = get_cached_rate(tx.currency, "EUR", tx.timestamp)
        eur_price = float(tx.price) * rate
        eur_transactions.append(MockTx(tx.ticker, tx.action, tx.quantity, eur_price, tx.timestamp, tx.id, tx.currency, tx.price))
        
    # Only fetch current prices for stocks with an open position
    open_positions = metrics.get_open_positions(eur_transactions)
    open_tickers = list(open_positions.keys())
    
    current_prices = {}
    current_prices_native = {}
    for t in open_tickers:
        try:
            raw_price, currency = fetch_stock_info(t)
            if raw_price is None: continue
            
            current_prices_native[t] = raw_price
            # Use current rate for current price
            rate = get_cached_rate(currency, "EUR", None)
            current_prices[t] = raw_price * rate
        except:
            pass
            
    usd_eur_rate = get_cached_rate("USD", "EUR", None)
    data = metrics.calculate_portfolio_performance(eur_transactions, current_prices, current_prices_native)
    data["usd_eur_rate"] = usd_eur_rate
    return data

@app.get("/portfolio/holdings")
def get_holdings(db: Session = Depends(get_db)):
    transactions = db.query(models.Transaction).all()
    return metrics.get_open_positions(transactions)

@app.post("/bargains/", response_model=BargainResponse)
def add_bargain(bargain: BargainCreate, db: Session = Depends(get_db)):
    try:
        db_bargain = models.Bargain(
            ticker=bargain.ticker.upper(),
            name=bargain.name,
            industry=bargain.industry,
            current_price=bargain.current_price,
            currency=bargain.currency,
            bargain_price=bargain.bargain_price,
            fair_price=bargain.fair_price,
            expensive_price=bargain.expensive_price,
            rationale=bargain.rationale
        )
        db.add(db_bargain)
        db.commit()
        db.refresh(db_bargain)
        logger.info(f"Recorded bargain stock: {db_bargain.ticker}")
        return db_bargain
    except Exception as e:
        logger.error(f"Error adding bargain: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bargains/", response_model=List[BargainResponse])
def get_bargains(db: Session = Depends(get_db)):
    try:
        return db.query(models.Bargain).order_by(models.Bargain.timestamp.desc()).all()
    except Exception as e:
        logger.error(f"Error fetching bargains: {e}")
        raise HTTPException(status_code=500, detail=str(e))
