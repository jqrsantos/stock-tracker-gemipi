from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from functools import lru_cache
import yfinance as yf
import logging
from . import models, database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
