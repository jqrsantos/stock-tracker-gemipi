from fastapi import FastAPI, HTTPException, Depends
from contextlib import asynccontextmanager
from functools import lru_cache
import yfinance as yf
import logging
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from . import models, database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransactionCreate(BaseModel):
    ticker: str
    action: str
    quantity: float
    price: float
    timestamp: Optional[datetime] = None

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables
    models.Base.metadata.create_all(bind=database.engine)
    yield

app = FastAPI(lifespan=lifespan)

@lru_cache(maxsize=100)
def fetch_stock_price(ticker: str):
    stock = yf.Ticker(ticker)
    history = stock.history(period="1d")
    if history.empty:
        return None
    return float(history['Close'].iloc[-1])

@app.get("/price/{ticker}")
def get_price(ticker: str):
    try:
        price = fetch_stock_price(ticker)
        if price is None:
            raise HTTPException(status_code=404, detail="Ticker not found")
        return {"ticker": ticker, "price": price}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching price for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/transactions/")
def add_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    # Convert Pydantic model to SQLAlchemy model
    db_tx = models.Transaction(
        ticker=transaction.ticker,
        action=transaction.action,
        quantity=transaction.quantity,
        price=transaction.price,
        timestamp=transaction.timestamp if transaction.timestamp else datetime.utcnow()
    )
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx

@app.get("/transactions/")
def get_transactions(db: Session = Depends(get_db)):
    return db.query(models.Transaction).all()
