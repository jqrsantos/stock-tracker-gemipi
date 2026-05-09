import google.generativeai as genai
import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()
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

def perform_daily_research(tickers: list):
    if not api_key: return "API Key missing"
    
    model = genai.GenerativeModel('gemini-pro')
    # Note: In future tasks, we will inject real news here.
    prompt = f"Analyze {tickers}. Provide macro view and price windows. NOTE: Use your internal knowledge but prioritize reasoning over specific recent dates if data isn't provided."
    
    try:
        response = model.generate_content(prompt)
        report_content = response.text
        
        # Save to DB
        db = SessionLocal()
        new_report = ResearchReport(content=report_content)
        db.add(new_report)
        db.commit()
        db.close()
        
        return report_content
    except Exception as e:
        logger.error(f"Failed: {e}")
        return str(e)
