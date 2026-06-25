#!/usr/bin/env python3
"""
Centralized yfinance Financial Statement Fetcher and Intrinsic Value Calculator.
Computes true Warren Buffett investing metrics: ROIC, Debt/Equity, FCF Yield, and 10-Year DCF.
"""

import logging
import sys
import math
import statistics
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
    business_type: str = "Asset-Heavy/Cyclical"
    croic: float = 0.0
    ev_to_fcf: float = 0.0
    ev_to_fcf_5yr_median: float = 0.0
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

    def safe_get_series(self, df, keys: List[str]) -> pd.Series:
        """
        Safely retrieves all annual values for given keys in a DataFrame.
        """
        if df is None or df.empty:
            return pd.Series(dtype=float)
        for key in keys:
            if key in df.index:
                val = df.loc[key]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                if isinstance(val, pd.Series):
                    return pd.to_numeric(val, errors='coerce').fillna(0.0)
                else:
                    return pd.Series([float(val)], index=[0])
        return pd.Series(dtype=float)

    def calculate_dcf_value(self, growth_rate: float, fcf_base: float, shares: float, discount_rate: float = 0.10, terminal_growth: float = 0.035) -> float:
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

    def solve_implied_growth(self, current_price: float, fcf_base: float, shares: float, discount_rate: float = 0.10, terminal_growth: float = 0.035) -> float:
        """
        Finds the implied FCF growth rate for the current price using binary search with dynamic bounds.
        """
        if shares <= 0 or current_price <= 0 or fcf_base <= 0:
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
            yf_ticker = yf.Ticker(ticker)
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
            
            # Current Year values for reporting
            equity = self.safe_get_row(balance_sheet, ['StockholdersEquity', 'TotalStockholdersEquity', 'Stockholders Equity', 'Total Stockholders Equity'])
            debt = self.safe_get_row(balance_sheet, ['TotalDebt', 'Total Debt'])
            if debt == 0.0:
                lt_debt = self.safe_get_row(balance_sheet, ['LongTermDebt', 'Long Term Debt'])
                st_debt = self.safe_get_row(balance_sheet, ['ShortLongTermDebt', 'Short Long Term Debt'])
                debt = lt_debt + st_debt
            
            # 2.5. Multi-Year ROIC Calculation (Insulated)
            ebit_series = self.safe_get_series(income_stmt, ['EBIT', 'OperatingIncome', 'Operating Income'])
            tax_series = self.safe_get_series(income_stmt, ['TaxProvision', 'Tax Provision', 'IncomeTaxExpense'])
            pretax_series = self.safe_get_series(income_stmt, ['PretaxIncome', 'Pre-Tax Income', 'Pretax Income'])
            equity_series = self.safe_get_series(balance_sheet, ['StockholdersEquity', 'TotalStockholdersEquity', 'Stockholders Equity', 'Total Stockholders Equity'])
            debt_series = self.safe_get_series(balance_sheet, ['TotalDebt', 'Total Debt'])
            lt_debt_series = self.safe_get_series(balance_sheet, ['LongTermDebt', 'Long Term Debt'])
            st_debt_series = self.safe_get_series(balance_sheet, ['ShortLongTermDebt', 'Short Long Term Debt'])
            cash_series = self.safe_get_series(balance_sheet, ['CashAndCashEquivalents', 'Cash And Cash Equivalents', 'Cash'])

            df_align = pd.DataFrame({
                'ebit': ebit_series, 'tax': tax_series, 'pretax': pretax_series,
                'equity': equity_series, 'debt': debt_series, 'lt_debt': lt_debt_series,
                'st_debt': st_debt_series, 'cash': cash_series
            }).fillna(0.0)

            roic_history = []
            for _, row in df_align.head(5).iterrows():
                # STRICT FILTERING: Exclude years with missing structural data
                if row['ebit'] == 0.0 and row['equity'] == 0.0:
                    continue
                    
                row_tax_rate = 0.21
                if row['pretax'] > 0 and row['tax'] > 0:
                    row_tax_rate = row['tax'] / row['pretax']
                    if row_tax_rate < 0 or row_tax_rate > 0.8:
                        row_tax_rate = 0.21
                
                row_nopat = row['ebit'] * (1 - row_tax_rate)
                row_debt_val = row['debt'] if row['debt'] != 0.0 else (row['lt_debt'] + row['st_debt'])
                
                # STRICT IC CALCULATION: Equity + Debt (No cash deduction to avoid inflation)
                row_ic = row['equity'] + row_debt_val
                
                if row_ic > 0:
                    roic_history.append(row_nopat / row_ic)

            roic = statistics.median(roic_history) if roic_history else 0.0
            
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
            
            # Calculate CROIC
            cash = self.safe_get_row(balance_sheet, ['CashAndCashEquivalents', 'Cash And Cash Equivalents', 'Cash'])
            total_debt_equity_cash = debt + equity - cash
            croic = (fcf / total_debt_equity_cash) if total_debt_equity_cash > 0 else 0.0
            
            # Calculate EV/FCF
            ev = market_cap + debt - cash
            ev_to_fcf = (ev / fcf) if fcf > 0 else 999.0
            ev_to_fcf_5yr_median = 20.0 # Will be updated after fetching fcf_history

            # Business Model Classifier
            recent_capex = self.safe_get_row(cashflow, ['CapitalExpenditure', 'Capital Expenditure'])
            recent_ocf = self.safe_get_row(cashflow, ['OperatingCashFlow', 'Cash Flow From Operating Activities', 'Operating Cash Flow'])
            net_intangibles = self.safe_get_row(balance_sheet, ['GoodwillAndOtherIntangibleAssets', 'Goodwill', 'IntangibleAssets'])
            total_assets = self.safe_get_row(balance_sheet, ['TotalAssets', 'Total Assets'])

            capex_ocf_ratio = abs(recent_capex / recent_ocf) if recent_ocf > 0 else 1.0
            intangibles_assets_ratio = (net_intangibles / total_assets) if total_assets > 0 else 0.0

            if capex_ocf_ratio < 0.20 or intangibles_assets_ratio > 0.40:
                business_type = "Asset-Light/Platform"
            else:
                business_type = "Asset-Heavy/Cyclical"

            # Dynamic WACC (Discount Rate)
            beta = info.get('beta') or 1.0
            risk_free_rate = 0.04
            equity_risk_premium = 0.05
            cost_of_equity = risk_free_rate + (beta * equity_risk_premium)
            discount_rate = min(max(cost_of_equity, 0.07), 0.15) # Bound between 7% and 15%
            
            # Fallback for current P/E if not in info
            if current_pe == 0.0 and current_price > 0:
                eps = info.get('trailingEps') or 0.0
                if eps > 0:
                    current_pe = current_price / eps
                    
            if not pe_5yr_avg:
                pe_5yr_avg = current_pe or 20.0
                
            # 5. Centralized valuation models tailored by business category
            # Fetch FCF, OCF, and CapEx History
            fcf_history = []
            ocf_history = []
            capex_history = []
            
            if cashflow is not None and not cashflow.empty:
                def get_hist_list(keys):
                    k = next((x for x in keys if x in cashflow.index), None)
                    if not k: return []
                    v = cashflow.loc[k]
                    if isinstance(v, pd.DataFrame): return list(v.iloc[0])
                    if hasattr(v, 'tolist'): return v.tolist()
                    if hasattr(v, 'iloc'): return list(v)
                    return [v]

                fcf_history = get_hist_list(['Free Cash Flow', 'FreeCashFlow'])
                ocf_history = get_hist_list(['Operating Cash Flow', 'OperatingCashFlow', 'Cash Flow From Operating Activities'])
                capex_history = get_hist_list(['Capital Expenditure', 'CapitalExpenditure'])

                if not fcf_history and ocf_history and capex_history:
                    fcf_history = [float(o) + float(c) for o, c in zip(ocf_history, capex_history)]
                    
            # Clean history
            fcf_history = [float(f) for f in fcf_history if f == f and f is not None]
            ocf_history = [float(o) for o in ocf_history if o == o and o is not None]
            capex_history = [abs(float(c)) for c in capex_history if c == c and c is not None]
            
            # Calculate 5-year median EV/FCF using current EV
            if ev > 0 and len(fcf_history) >= 3:
                hist_ev_to_fcf = [(ev / f) if f > 0 else 999.0 for f in fcf_history[:5]]
                ev_to_fcf_5yr_median = statistics.median(hist_ev_to_fcf)
                
            # CapEx Normalization Check
            if len(capex_history) >= 3 and len(ocf_history) >= 1 and len(fcf_history) >= 1:
                recent_capex = capex_history[:5]
                median_capex = statistics.median(recent_capex)
                current_capex = capex_history[0]
                
                if median_capex > 0 and current_capex > 1.5 * median_capex:
                    logger.info(f"{ticker} flagged for Aggressive Capital Reinvestment Cycle. Normalizing FCF.")
                    current_ocf = ocf_history[0]
                    normalized_fcf_base = current_ocf - median_capex
                    fcf_history[0] = normalized_fcf_base
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
                if not fcf_history or current_price <= 0 or shares <= 0:
                    intrinsic_value = 0.0
                    is_too_hard = True
                    error_msg = "Insufficient FCF or price data for Reverse DCF"
                    bargain_price = 0.0
                    fair_price = 0.0
                    expensive_price = 0.0
                elif statistics.median(fcf_history[:5]) < 0:
                    intrinsic_value = 0.0
                    error_msg = "Negative multi-year median FCF [REQUIRES 10-Q FCF AUDIT]"
                    bargain_price = 0.0
                    fair_price = 0.0
                    expensive_price = 0.0
                else:
                    # Solve for growth rate that yields current market price
                    fcf_base = fcf_history[0]
                    implied_growth_rate = self.solve_implied_growth(current_price, fcf_base, shares, discount_rate, 0.035)
                    
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
                    terminal_growth = 0.035
                    intrinsic_value = self.calculate_dcf_value(expected_growth_rate, fcf_base, shares, discount_rate, terminal_growth)
                    
                    bargain_price = intrinsic_value * 0.70
                    fair_price = intrinsic_value
                    expensive_price = intrinsic_value * 1.20

            # 1.5. CATEGORY: Supercycle Semiconductors Breakout
            elif ticker in ["NVDA", "MU", "INTC", "AMD"] and len(fcf_history) >= 3 and current_price > 0 and shares > 0:
                # Check if current FCF is significantly outperforming the 5-year median, indicating a supercycle
                hist_median = statistics.median(fcf_history[:5])
                if (hist_median > 0 and fcf_history[0] > 1.5 * hist_median) or (hist_median <= 0 and fcf_history[0] > 0):
                    valuation_methodology = "Supercycle DCF"
                    growth_rate = 0.20 # Assume 20% growth for supercycle peak
                    expected_growth_rate = growth_rate
                    terminal_growth = 0.035
                    intrinsic_value = self.calculate_dcf_value(growth_rate, fcf_history[0], shares, discount_rate, terminal_growth)
                    bargain_price = intrinsic_value * 0.70
                    fair_price = intrinsic_value
                    expensive_price = intrinsic_value * 1.30
                else:
                    # Fallback to Cyclical if not breaking out
                    valuation_methodology = "Mid-Cycle Normalized"
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
                    target_pe = min(pe_5yr_avg if pe_5yr_avg > 0 else 15.0, 25.0)
                    intrinsic_value = eps_5yr_avg * target_pe
                    if eps_5yr_avg <= 0:
                        intrinsic_value = 0.0
                        is_too_hard = True
                        error_msg = "Structurally negative or missing EPS for cyclical stock"
                        bargain_price = 0.0
                        fair_price = 0.0
                        expensive_price = 0.0
                    else:
                        bargain_price = intrinsic_value * 0.70
                        fair_price = intrinsic_value
                        expensive_price = intrinsic_value * 1.30

            # 2. CATEGORY: Cyclical / Asset-Heavy
            elif (roic < 0.10 and len(fcf_history) >= 2) or not fcf_history:
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
                            
                # Target PE: Revert to company's own average, capped at 25
                target_pe = pe_5yr_avg
                if not target_pe or target_pe <= 0:
                    target_pe = 15.0
                if target_pe > 25.0:
                    target_pe = 25.0
                
                intrinsic_value = eps_5yr_avg * target_pe
                
                # Flaw fix: Do not invent Intrinsic Value if structurally unprofitable
                if eps_5yr_avg <= 0:
                    intrinsic_value = 0.0
                    is_too_hard = True
                    error_msg = "Structurally negative or missing EPS for cyclical stock"
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
                if not fcf_history or current_price <= 0 or shares <= 0:
                    intrinsic_value = 0.0
                    is_too_hard = True
                    error_msg = "Erratic or negative FCF: Too Hard to value reliably"
                    bargain_price = 0.0
                    fair_price = 0.0
                    expensive_price = 0.0
                elif statistics.median(fcf_history[:5]) < 0:
                    intrinsic_value = 0.0
                    error_msg = "Negative multi-year median FCF [REQUIRES 10-Q FCF AUDIT]"
                    bargain_price = 0.0
                    fair_price = 0.0
                    expensive_price = 0.0
                else:
                    historical_median = statistics.median(fcf_history[:5])
                    if fcf_history[0] < 0.80 * historical_median:
                        valuation_methodology = "Mid-Cycle Normalized"
                        normalized_fcf = historical_median
                        intrinsic_value = (normalized_fcf * 15) / shares
                        bargain_price = intrinsic_value * 0.70
                        fair_price = intrinsic_value
                        expensive_price = intrinsic_value * 1.20
                    else:
                        # Dynamic growth rate calculation
                        growth_rate = 0.08  # standard 8% conservative growth
                        if len(fcf_history) >= 2:
                            hist = fcf_history[::-1] # Clean newest to oldest
                            if hist[0] > 0 and hist[-1] > 0:
                                n_years = len(hist) - 1
                                cagr = (hist[-1] / hist[0]) ** (1 / n_years) - 1
                                if 0.0 <= cagr < 0.15:
                                    growth_rate = cagr
                                elif cagr >= 0.15:
                                    growth_rate = 0.15  # STRICT CAP at 15% to prevent fragility
                        
                        expected_growth_rate = growth_rate
                        terminal_growth = 0.035  # capped terminal growth rate
                        
                        intrinsic_value = self.calculate_dcf_value(growth_rate, fcf_history[0], shares, discount_rate, terminal_growth)
                        bargain_price = intrinsic_value * 0.70
                        fair_price = intrinsic_value
                        expensive_price = intrinsic_value * 1.20
            
            # FCF growth check (agent will handle 10-Q audit if negative)
            fcf_growth_negative = False
            if len(fcf_history) >= 2:
                recent_fcf = fcf_history[0]
                prior_fcf = fcf_history[1]
                if recent_fcf < prior_fcf:
                    fcf_growth_negative = True
            
            if fcf_growth_negative:
                error_msg += " [REQUIRES 10-Q FCF AUDIT]"
            
            return StockData(
                ticker=ticker,
                name=name,
                industry=industry,
                roic=roic,
                debt_to_equity=debt_to_equity,
                fcf_yield=fcf_yield,
                current_pe=current_pe,
                pe_5yr_avg=pe_5yr_avg,
                business_type=business_type,
                croic=croic,
                ev_to_fcf=ev_to_fcf,
                ev_to_fcf_5yr_median=ev_to_fcf_5yr_median,
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
