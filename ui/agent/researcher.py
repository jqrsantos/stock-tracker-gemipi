import google.generativeai as genai
from duckduckgo_search import DDGS
import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from notifier import send_telegram

load_dotenv(override=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DB Setup
DB_URL = os.getenv("DATABASE_URL")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class ResearchReport(Base):
    __tablename__ = "research_reports"
    id = Column(Integer, primary_key=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

# Gemini Setup
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def search_stock_news(ticker: str):
    """
    Fetches the latest 5 news items for a given ticker using DuckDuckGo.
    """
    try:
        with DDGS() as ddgs:
            results = ddgs.news(f"{ticker} stock news", max_results=5)
            if not results:
                return f"No recent news found for {ticker}."
            return "\n".join([f"- {r['title']} ({r['date']}): {r['body']}" for r in results])
    except Exception as e:
        return f"Error searching news for {ticker}: {str(e)}"

def perform_daily_research(tickers: list):
    if not api_key: return "API Key missing"
    
    # Grounding logic
    grounding_context = []
    
    # Ticker news
    for ticker in tickers:
        logger.info(f"Fetching news for {ticker}...")
        news = search_stock_news(ticker)
        grounding_context.append(f"RECENT NEWS FOR {ticker}:\n{news}")
        
    # Global Macro News
    logger.info("Fetching global macro news...")
    macro_news = search_stock_news("Global Macro Economic")
    grounding_context.append(f"GLOBAL MACRO ECONOMIC NEWS:\n{macro_news}")
    
    context_text = "\n\n".join(grounding_context)
    
    model = genai.GenerativeModel('gemma-4-26b-a4b-it')
    
    prompt = f"""
    GROUNDING CONTEXT:
    {context_text}
    
    Analyze the following tickers based on the GROUNDING CONTEXT provided above: {tickers}. 
    Provide macro view and price windows. 
    Use the provided GROUNDING CONTEXT specifically for your analysis. 
    If data is missing for a ticker, state it.
    """
    
    try:
        response = model.generate_content(prompt)
        report_content = response.text
        
        # Notify via Telegram (Do this before DB to ensure user gets report)
        send_telegram(report_content)
        
        # Save to DB (Optional for testing)
        try:
            db = SessionLocal()
            new_report = ResearchReport(content=report_content)
            db.add(new_report)
            db.commit()
            db.close()
        except Exception as db_e:
            logger.warning(f"Database save failed (expected if local DB not running): {db_e}")
        
        return report_content
    except Exception as e:
        logger.error(f"Failed: {e}")
        return str(e)
