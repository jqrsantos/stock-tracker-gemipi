from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import models, database
import yfinance as yf

# Create database tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

@app.get("/price/{ticker}")
def get_price(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period="1d")
        if history.empty:
             raise HTTPException(status_code=404, detail="Ticker not found")
        return {"ticker": ticker, "price": float(history['Close'].iloc[-1])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
