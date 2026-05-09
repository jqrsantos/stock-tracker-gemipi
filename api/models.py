from sqlalchemy import Column, Integer, String, Numeric, DateTime, func
from .database import Base

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    action = Column(String, nullable=False)  # BUY or SELL
    quantity = Column(Numeric(18, 8), nullable=False)
    price = Column(Numeric(18, 8), nullable=False)
    timestamp = Column(DateTime, server_default=func.now())

class ResearchReport(Base):
    __tablename__ = "research_reports"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
