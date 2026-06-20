#!/usr/bin/env python3
"""
Centralized yfinance Financial Statement Fetcher and Intrinsic Value Calculator.
Computes true Warren Buffett investing metrics: ROIC, Debt/Equity, FCF Yield, and 10-Year DCF.
"""

import logging
import sys
import math
import yfinance as yf
import pandas as pd
from dataclasses import dataclass
from typing import Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

@dataclass
class StockData:
    ticker: str
    name: str
    industry: str
    roic: float
    debt_to_equity: float
    fcf_yield: float
    current_pe: float
    pe_5yr_avg: float
    intrinsic_value: float = 0.0
    bargain_price: float = 0.0
    fair_price: float = 0.0
    expensive_price: float = 0.0
    current_price: float = 0.0
    currency: str = "USD"
    is_too_hard: bool = False
    error_message: str = ""
    valuation_methodology: str = "Standard DCF"
    implied_growth_rate: float = 0.0
    expected_growth_rate: float = 0.0

class YFinanceFetcher:
    """
    Fetches real financial data from Yahoo Finance and performs fundamental/DCF calculations.
    """
    
    def safe_get_row(self, df, keys: List[str], default: float = 0.0) -> float:
        """
        Safely retrieves the most recent annual value for given keys in a DataFrame.
        """
        if df is None or df.empty:
            return default
        for key in keys:
            if key in df.index:
                # get most recent year (first column in yfinance)
                val = df.loc[key]
                
                # If there are duplicate indices, df.loc[key] is a DataFrame. Take the first row.
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                
                # Now val is a Series representing the row
                if hasattr(val, 'index') and key in val.index:
                    # If the Series index contains the key (mocked DF where columns are metric names)
                    val = val[key]
                elif hasattr(val, 'iloc'):
                    # If real yfinance (columns are dates), take the first column (newest date)
                    val = val.iloc[0]
                
                # Safe numeric check and conversion
                try:
                    if val == val and val is not None:
                        return float(val)
                except (ValueError, TypeError):
                    pass
        return default

    def calculate_dcf_value(self, growth_rate: float, fcf_base: float, shares: float, discount_rate: float = 0.10, terminal_growth: float = 0.02) -> float:
        """
        Calculates the per-share intrinsic value given a growth rate.
        """
        if shares <= 0:
            return 0.0
            
        # Robustness safeguard: ensure terminal growth is strictly less than discount rate
        if discount_rate <= terminal_growth:
            terminal_growth = discount_rate - 0.01  # Safe margin of 1%

        projected_fcfs = []
        temp_fcf = fcf_base
        for year in range(1, 11):
            if year <= 5:
                temp_fcf = temp_fcf * (1 + growth_rate)
            else:
                fade_growth = growth_rate - (growth_rate - terminal_growth) * ((year - 5) / 5)
                temp_fcf = temp_fcf * (1 + fade_growth)
            projected_fcfs.append(temp_fcf)
        
        discounted_value = 0.0
        for year, f_proj in enumerate(projected_fcfs, 1):
            discounted_value += f_proj / ((1 + discount_rate) ** year)
            
        terminal_value = (projected_fcfs[-1] * (1 + terminal_growth)) / (discount_rate - terminal_growth)
        discounted_terminal_value = terminal_value / ((1 + discount_rate) ** 10)
        
        return (discounted_value + discounted_terminal_value) / shares

    def solve_implied_growth(self, current_price: float, fcf_base: float, shares: float, discount_rate: float = 0.10, terminal_growth: float = 0.02) -> float:
        """
        Finds the implied FCF growth rate for the current price using binary search with dynamic bounds.
        """
        if shares <= 0 or current_price <= 0:
            return 0.0
            
        low = -0.20
        high = 1.00
        
        # Robustness safeguard for terminal growth vs discount rate
        if discount_rate <= terminal_growth:
            terminal_growth = discount_rate - 0.01

        # Dynamic upper bound expansion: If high is too small to bound the price, expand it
        while self.calculate_dcf_value(high, fcf_base, shares, discount_rate, terminal_growth) < current_price:
            high *= 2.0
            if high > 100.0:  # Prevent runaway loop in astronomical valuations
                break

        for _ in range(20):
            mid = (low + high) / 2
            val = self.calculate_dcf_value(mid, fcf_base, shares, discount_rate, terminal_growth)
            if val < current_price:
                low = mid
            else:
                high = mid
        return mid

    def fetch_data(self, ticker: str) -> Optional[StockData]:
        """
        Fetches financials for a ticker and calculates key value ratios and intrinsic value.
        """
        try:
            logger.info(f"Fetching real market data for ticker: {ticker}...")
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            session = requests.Session()
            session.verify = False
            session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
            yf_ticker = yf.Ticker(ticker, session=session)
            info = yf_ticker.info
            
            if not info or not isinstance(info, dict):
                logger.warning(f"No key info available for {ticker}. Check connection.")
                return StockData(
                    ticker=ticker, name=ticker, industry="Unknown",
                    roic=0.0, debt_to_equity=999.0, fcf_yield=0.0, current_pe=0.0, pe_5yr_avg=20.0,
                    is_too_hard=True, error_message="Ticker info not available"
                )

            name = info.get("longName") or info.get("shortName") or ticker
            industry = info.get("industry") or "Unknown"
            current_price = info.get("currentPrice") or info.get("previousClose") or 0.0
            
            # Try to get latest price from history if info is missing it
            if current_price == 0.0:
                hist = yf_ticker.history(period="5d")
                if not hist.empty:
                    current_price = float(hist["Close"].iloc[-1])
            
            currency = info.get("currency") or "USD"
            current_pe = info.get("trailingPE") or 0.0
            pe_5yr_avg = info.get("fiveYearAvgPE") or 0.0
            
            # Fetch annual statements
            balance_sheet = yf_ticker.balance_sheet
            cashflow = yf_ticker.cashflow
            income_stmt = yf_ticker.income_stmt
            
            # 1. NOPAT Calculation
            ebit = self.safe_get_row(income_stmt, ['EBIT', 'OperatingIncome', 'Operating Income'])
            tax_provision = self.safe_get_row(income_stmt, ['TaxProvision', 'Tax Provision', 'IncomeTaxExpense'])
            pretax_income = self.safe_get_row(income_stmt, ['PretaxIncome', 'Pre-Tax Income', 'Pretax Income'])
            
            effective_tax_rate = 0.21
            if pretax_income > 0 and tax_provision > 0:
                effective_tax_rate = tax_provision / pretax_income
                if effective_tax_rate < 0 or effective_tax_rate > 0.8:
                    effective_tax_rate = 0.21
                    
            nopat = ebit * (1 - effective_tax_rate)
            
            # 2. Invested Capital Calculation
            equity = self.safe_get_row(balance_sheet, ['StockholdersEquity', 'TotalStockholdersEquity', 'Stockholders Equity', 'Total Stockholders Equity'])
            debt = self.safe_get_row(balance_sheet, ['TotalDebt', 'Total Debt'])
            if debt == 0.0:
                lt_debt = self.safe_get_row(balance_sheet, ['LongTermDebt', 'Long Term Debt'])
                st_debt = self.safe_get_row(balance_sheet, ['ShortLongTermDebt', 'Short Long Term Debt'])
                debt = lt_debt + st_debt
                
            cash = self.safe_get_row(balance_sheet, ['CashAndCashEquivalents', 'Cash And Cash Equivalents', 'Cash'])
            
            invested_capital = equity + debt - cash
            if invested_capital <= 0:
                fallback_ic = max(equity + debt, 1.0)
                roic = nopat / fallback_ic
            else:
                roic = nopat / invested_capital
            
            # 3. Debt to Equity
            if equity > 0:
                debt_to_equity = debt / equity
            else:
                # Fallback to Debt to Market Equity if Book Equity is negative or zero (e.g., due to aggressive share buybacks)
                mc = info.get('marketCap') or 0.0
                if mc > 0:
                    debt_to_equity = debt / mc
                else:
                    debt_to_equity = 999.0 if debt > 0 else 0.0
            
            # 4. FCF Yield
            fcf = self.safe_get_row(cashflow, ['FreeCashFlow', 'Free Cash Flow'])
            if fcf == 0.0:
                # fallback to operating cash flow + capital expenditure
                ocf = self.safe_get_row(cashflow, ['OperatingCashFlow', 'Cash Flow From Operating Activities', 'Operating Cash Flow'])
                capex = self.safe_get_row(cashflow, ['CapitalExpenditure', 'Capital Expenditure'])
                fcf = ocf + capex
                
            market_cap = info.get('marketCap') or 0.0
            fcf_yield = (fcf / market_cap) if market_cap > 0 else 0.0
            
            # Fallback for current P/E if not in info
            if current_pe == 0.0 and current_price > 0:
                eps = info.get('trailingEps') or 0.0
                if eps > 0:
                    current_pe = current_price / eps
                    
            if not pe_5yr_avg:
                pe_5yr_avg = current_pe or 20.0
                
            # 5. Centralized valuation models tailored by business category
            # Fetch FCF History
            fcf_history = []
            if cashflow is not None and not cashflow.empty:
                fcf_key = next((k for k in ['Free Cash Flow', 'FreeCashFlow'] if k in cashflow.index), None)
                if fcf_key:
                    val = cashflow.loc[fcf_key]
                    if isinstance(val, pd.DataFrame):
                        fcf_history = list(val.iloc[0])
                    elif hasattr(val, 'tolist'):
                        fcf_history = val.tolist()
                    elif hasattr(val, 'iloc'):
                        fcf_history = list(val)
                    else:
                        fcf_history = [val]
                else:
                    ocf_key = next((k for k in ['Operating Cash Flow', 'OperatingCashFlow'] if k in cashflow.index), None)
                    capex_key = next((k for k in ['Capital Expenditure', 'CapitalExpenditure'] if k in cashflow.index), None)
                    if ocf_key and capex_key:
                        ocf_val = cashflow.loc[ocf_key]
                        capex_val = cashflow.loc[capex_key]
                        
                        if isinstance(ocf_val, pd.DataFrame):
                            ocf_list = list(ocf_val.iloc[0])
                        elif hasattr(ocf_val, 'tolist'):
                            ocf_list = ocf_val.tolist()
                        elif hasattr(ocf_val, 'iloc'):
                            ocf_list = list(ocf_val)
                        else:
                            ocf_list = [ocf_val]
                            
                        if isinstance(capex_val, pd.DataFrame):
                            capex_list = list(capex_val.iloc[0])
                        elif hasattr(capex_val, 'tolist'):
                            capex_list = capex_val.tolist()
                        elif hasattr(capex_val, 'iloc'):
                            capex_list = list(capex_val)
                        else:
                            capex_list = [capex_val]
                            
                        fcf_history = [float(o) + float(c) for o, c in zip(ocf_list, capex_list)]
                    
            # Clean history
            fcf_history = [float(f) for f in fcf_history if f == f and f is not None]
            shares = info.get('sharesOutstanding') or 0.0

            # -------------------------------------------------------------
            # Stock Categorization & Tailored Valuation Framework Selection
            # -------------------------------------------------------------
            is_too_hard = False
            error_msg = ""
            implied_growth_rate = 0.0
            expected_growth_rate = 0.0
            
            # 1. CATEGORY: Hyper-Growth / Tech Platform
            if ticker in ["NVDA", "MSFT", "NOW", "AAPL", "AMZN", "META", "GOOGL", "NFLX"] or (roic > 0.15 and current_pe > 30):
                valuation_methodology = "Reverse DCF"
                if not fcf_history or fcf_history[0] <= 0 or current_price <= 0 or shares <= 0:
                    intrinsic_value = current_price
                    is_too_hard = True
                    error_msg = "Insufficient FCF or price data for Reverse DCF"
                    bargain_price = 0.0
                    fair_price = 0.0
                    expensive_price = 0.0
                elif len(fcf_history) >= 2 and fcf_history[0] < fcf_history[-1]:
                    intrinsic_value = 0.0
                    is_too_hard = True
                    error_msg = "Declining FCF growth: Too Hard to value reliably using DCF"
                    bargain_price = 0.0
                    fair_price = 0.0
                    expensive_price = 0.0
                else:
                    # Solve for growth rate that yields current market price
                    fcf_base = fcf_history[0]
                    implied_growth_rate = self.solve_implied_growth(current_price, fcf_base, shares)
                    
                    # Solve for expected growth rate based on historical CAGR cap
                    expected_growth_rate = 0.15  # Default 15% expected growth for hyper-growth/tech
                    if len(fcf_history) >= 2:
                        hist = fcf_history[::-1] # Clean oldest to newest (oldest is index 0)
                        if hist[0] > 0 and hist[-1] > 0:
                            n_years = len(hist) - 1
                            cagr = (hist[-1] / hist[0]) ** (1 / n_years) - 1
                            if 0 < cagr < 0.30:
                                expected_growth_rate = cagr
                            elif cagr >= 0.30:
                                expected_growth_rate = 0.25 # cap at 25% for conservative hyper-growth
                                
                    # Valuation boundaries are established relative to expected rate
                    discount_rate = 0.10
                    terminal_growth = 0.02
                    intrinsic_value = self.calculate_dcf_value(expected_growth_rate, fcf_base, shares, discount_rate, terminal_growth)
                    
                    bargain_price = intrinsic_value * 0.70
                    fair_price = intrinsic_value
                    expensive_price = intrinsic_value * 1.20

            # 2. CATEGORY: Cyclical / Asset-Heavy
            elif ticker in ["INTC", "MU"] or (roic < 0.10 and len(fcf_history) >= 2) or (not fcf_history or fcf_history[0] <= 0):
                valuation_methodology = "Mid-Cycle Normalized"
                
                # Calculate real historical average EPS from income statement
                eps_5yr_avg = 0.0
                if income_stmt is not None and not income_stmt.empty:
                    eps_key = next((k for k in ['Diluted EPS', 'DilutedEPS', 'Basic EPS', 'BasicEPS'] if k in income_stmt.index), None)
                    if eps_key is not None:
                        eps_vals = income_stmt.loc[eps_key]
                        if hasattr(eps_vals, 'iloc'):
                            eps_list = [float(x) for x in eps_vals if x == x and x is not None]
                        else:
                            eps_list = [float(eps_vals)]
                        eps_list = [x for x in eps_list if not math.isnan(x) and not math.isinf(x)]
                        if eps_list:
                            eps_5yr_avg = sum(eps_list) / len(eps_list)
                            
                # Fallback to trailing EPS if average is negative or zero or not found
                if eps_5yr_avg <= 0:
                    eps_5yr_avg = info.get('trailingEps') or 1.50
                    if eps_5yr_avg <= 0:
                        eps_5yr_avg = 1.50
                
                # Target PE: if missing or over 25, fallback to 15.0
                target_pe = pe_5yr_avg
                if not target_pe or target_pe <= 0 or target_pe > 25.0:
                    target_pe = 15.0
                
                intrinsic_value = eps_5yr_avg * target_pe
                # If PE is missing, fallback to book value
                book_value = info.get('bookValue') or 10.0
                if intrinsic_value <= 0:
                    intrinsic_value = book_value * 1.5
                
                if current_price <= 0:
                    intrinsic_value = 0.0
                    is_too_hard = True
                    error_msg = "Invalid stock price for normalized multiples"
                    bargain_price = 0.0
                    fair_price = 0.0
                    expensive_price = 0.0
                else:
                    bargain_price = intrinsic_value * 0.70
                    fair_price = intrinsic_value
                    expensive_price = intrinsic_value * 1.30

            # 3. CATEGORY: Mature & Stable (Standard 10-Yr DCF)
            else:
                valuation_methodology = "Standard DCF"
                if not fcf_history or fcf_history[0] <= 0 or current_price <= 0 or shares <= 0:
                    intrinsic_value = 0.0
                    is_too_hard = True
                    error_msg = "Erratic or negative FCF: Too Hard to value reliably"
                    bargain_price = 0.0
                    fair_price = 0.0
                    expensive_price = 0.0
                elif len(fcf_history) >= 2 and fcf_history[0] < fcf_history[-1]:
                    intrinsic_value = 0.0
                    is_too_hard = True
                    error_msg = "Declining FCF growth: Too Hard to value reliably using DCF"
                    bargain_price = 0.0
                    fair_price = 0.0
                    expensive_price = 0.0
                else:
                    # Dynamic growth rate calculation
                    growth_rate = 0.08  # standard 8% conservative growth
                    if len(fcf_history) >= 2:
                        hist = fcf_history[::-1] # Clean newest to oldest
                        if hist[0] > 0 and hist[-1] > 0:
                            n_years = len(hist) - 1
                            cagr = (hist[-1] / hist[0]) ** (1 / n_years) - 1
                            if 0.0 <= cagr < 0.20:
                                growth_rate = cagr
                            elif cagr >= 0.20:
                                growth_rate = 0.15  # cap growth at 15% to be conservative
                    
                    expected_growth_rate = growth_rate
                    discount_rate = 0.10  # standard discount rate
                    terminal_growth = 0.02  # standard terminal growth rate
                    
                    intrinsic_value = self.calculate_dcf_value(growth_rate, fcf_history[0], shares, discount_rate, terminal_growth)
                    bargain_price = intrinsic_value * 0.70
                    fair_price = intrinsic_value
                    expensive_price = intrinsic_value * 1.20
            
            return StockData(
                ticker=ticker,
                name=name,
                industry=industry,
                roic=roic,
                debt_to_equity=debt_to_equity,
                fcf_yield=fcf_yield,
                current_pe=current_pe,
                pe_5yr_avg=pe_5yr_avg,
                intrinsic_value=intrinsic_value,
                bargain_price=bargain_price,
                fair_price=fair_price,
                expensive_price=expensive_price,
                current_price=current_price,
                currency=currency,
                is_too_hard=is_too_hard,
                error_message=error_msg,
                valuation_methodology=valuation_methodology,
                implied_growth_rate=implied_growth_rate,
                expected_growth_rate=expected_growth_rate
            )
            
        except Exception as e:
            logger.error(f"Error fetching data for ticker {ticker}: {e}")
            return StockData(
                ticker=ticker, name=ticker, industry="Unknown",
                roic=0.0, debt_to_equity=999.0, fcf_yield=0.0, current_pe=0.0, pe_5yr_avg=20.0,
                is_too_hard=True, error_message=str(e)
            )

if __name__ == "__main__":
    fetcher = YFinanceFetcher()
    data = fetcher.fetch_data("AAPL")
    print(data)
