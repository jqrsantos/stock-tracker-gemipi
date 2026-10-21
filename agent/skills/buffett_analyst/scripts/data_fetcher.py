#!/usr/bin/env python3
"""
Simplified yfinance Financial Snapshot Fetcher.
Computes factual moat & financial performance metrics for Gemini synthesis:
- Profitability & Moat proxies: Gross Margin, Operating Margin, ROIC (5Y median), ROE
- Financial Health & Growth: Debt/Equity, FCF Yield, Revenue Growth (YoY & 3Y CAGR), FCF Trend
- Relative Valuation Context: Price, 52W Range, Trailing P/E, Forward P/E, 5Y Avg P/E
"""

import logging
import sys
import statistics
import yfinance as yf
import pandas as pd
from dataclasses import dataclass
from typing import Optional, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

EXCLUDED_INDUSTRIES = {
    "Aerospace & Defense",
    "Defense",
    "Aeronautics",
    "Arms & Munitions",
}

EXCLUDED_TICKERS = {
    "LMT", "RTX", "NOC", "GD", "BA", "LHX", "HII", "PLTR", "RHM.DE", "BAE.L"
}


def is_peaceful_stock(industry: str, name: str = "", ticker: str = "") -> bool:
    """Checks whether a company complies with the Peaceful Investing mandate."""
    if ticker.upper() in EXCLUDED_TICKERS:
        return False
    if industry in EXCLUDED_INDUSTRIES:
        return False
    lower_name = (name or "").lower()
    lower_ind = (industry or "").lower()
    for kw in ["defense", "munitions", "weapons", "warfare", "firearms", "palantir"]:
        if kw in lower_name or kw in lower_ind:
            return False
    return True


@dataclass
class StockData:
    ticker: str
    name: str
    industry: str
    sector: str = "Unknown"
    is_peaceful: bool = True
    current_price: float = 0.0
    currency: str = "USD"
    low_52w: float = 0.0
    high_52w: float = 0.0
    current_pe: float = 0.0
    forward_pe: float = 0.0
    pe_5yr_avg: float = 0.0
    gross_margin: float = 0.0
    operating_margin: float = 0.0
    roic: float = 0.0
    roe: float = 0.0
    debt_to_equity: float = 0.0
    fcf_yield: float = 0.0
    revenue_growth_yoy: float = 0.0
    revenue_cagr_3yr: float = 0.0
    fcf_trend: str = "Unknown"
    error_message: str = ""


class YFinanceFetcher:
    """Fetches factual financial performance and moat proxy ratios from Yahoo Finance."""

    def safe_get_row(self, df, keys: List[str], default: float = 0.0) -> float:
        if df is None or df.empty:
            return default
        for key in keys:
            if key in df.index:
                val = df.loc[key]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                if hasattr(val, "index") and key in val.index:
                    val = val[key]
                elif hasattr(val, "iloc"):
                    val = val.iloc[0]
                try:
                    if val == val and val is not None:
                        return float(val)
                except (ValueError, TypeError):
                    pass
        return default

    def safe_get_series(self, df, keys: List[str]) -> pd.Series:
        if df is None or df.empty:
            return pd.Series(dtype=float)
        for key in keys:
            if key in df.index:
                val = df.loc[key]
                if isinstance(val, pd.DataFrame):
                    val = val.iloc[0]
                if isinstance(val, pd.Series):
                    return pd.to_numeric(val, errors="coerce").dropna()
                else:
                    return pd.Series([float(val)], index=[0])
        return pd.Series(dtype=float)

    def fetch_data(self, ticker: str) -> Optional[StockData]:
        try:
            logger.info(f"Fetching financial snapshot for {ticker}...")
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.info

            if not info or not isinstance(info, dict):
                return StockData(
                    ticker=ticker,
                    name=ticker,
                    industry="Unknown",
                    error_message="Ticker info unavailable",
                )

            name = info.get("longName") or info.get("shortName") or ticker
            industry = info.get("industry") or "Unknown"
            sector = info.get("sector") or "Unknown"
            peaceful = is_peaceful_stock(industry, name, ticker)

            current_price = float(info.get("currentPrice") or info.get("previousClose") or 0.0)
            if current_price == 0.0:
                hist = yf_ticker.history(period="5d")
                if not hist.empty:
                    current_price = float(hist["Close"].iloc[-1])

            currency = info.get("currency") or "USD"
            low_52w = float(info.get("fiftyTwoWeekLow") or 0.0)
            high_52w = float(info.get("fiftyTwoWeekHigh") or 0.0)
            current_pe = float(info.get("trailingPE") or 0.0)
            forward_pe = float(info.get("forwardPE") or 0.0)
            pe_5yr_avg = float(info.get("fiveYearAvgPE") or 0.0)

            gross_margin = float(info.get("grossMargins") or 0.0)
            operating_margin = float(info.get("operatingMargins") or 0.0)
            roe = float(info.get("returnOnEquity") or 0.0)
            revenue_growth_yoy = float(info.get("revenueGrowth") or 0.0)

            balance_sheet = yf_ticker.balance_sheet
            cashflow = yf_ticker.cashflow
            income_stmt = yf_ticker.income_stmt

            # Fallback margins from income statement if missing in info
            rev_latest = self.safe_get_row(income_stmt, ["TotalRevenue", "Total Revenue", "OperatingRevenue"])
            if gross_margin == 0.0 and rev_latest > 0:
                gp = self.safe_get_row(income_stmt, ["GrossProfit", "Gross Profit"])
                if gp > 0:
                    gross_margin = gp / rev_latest
            if operating_margin == 0.0 and rev_latest > 0:
                op_inc = self.safe_get_row(income_stmt, ["OperatingIncome", "Operating Income", "EBIT"])
                if op_inc != 0.0:
                    operating_margin = op_inc / rev_latest

            # 3-Year Revenue CAGR
            rev_series = self.safe_get_series(income_stmt, ["TotalRevenue", "Total Revenue", "OperatingRevenue"])
            revenue_cagr_3yr = 0.0
            if len(rev_series) >= 2:
                rev_vals = [float(x) for x in rev_series.tolist() if x > 0]
                if len(rev_vals) >= 2:
                    newest_rev = rev_vals[0]
                    oldest_rev = rev_vals[min(len(rev_vals) - 1, 3)]
                    n_years = min(len(rev_vals) - 1, 3)
                    if oldest_rev > 0 and n_years > 0:
                        revenue_cagr_3yr = (newest_rev / oldest_rev) ** (1.0 / n_years) - 1.0
                    if revenue_growth_yoy == 0.0 and len(rev_vals) >= 2 and rev_vals[1] > 0:
                        revenue_growth_yoy = (rev_vals[0] - rev_vals[1]) / rev_vals[1]

            # Multi-Year Median ROIC
            ebit_series = self.safe_get_series(income_stmt, ["EBIT", "OperatingIncome", "Operating Income"])
            tax_series = self.safe_get_series(income_stmt, ["TaxProvision", "Tax Provision", "IncomeTaxExpense"])
            pretax_series = self.safe_get_series(income_stmt, ["PretaxIncome", "Pre-Tax Income", "Pretax Income"])
            equity_series = self.safe_get_series(
                balance_sheet,
                ["StockholdersEquity", "TotalStockholdersEquity", "Stockholders Equity", "Total Stockholders Equity"],
            )
            debt_series = self.safe_get_series(balance_sheet, ["TotalDebt", "Total Debt"])
            lt_debt_series = self.safe_get_series(balance_sheet, ["LongTermDebt", "Long Term Debt"])
            st_debt_series = self.safe_get_series(balance_sheet, ["ShortLongTermDebt", "Short Long Term Debt"])

            df_align = pd.DataFrame(
                {
                    "ebit": ebit_series,
                    "tax": tax_series,
                    "pretax": pretax_series,
                    "equity": equity_series,
                    "debt": debt_series,
                    "lt_debt": lt_debt_series,
                    "st_debt": st_debt_series,
                }
            ).fillna(0.0)

            roic_history = []
            for _, row in df_align.head(5).iterrows():
                if row["ebit"] == 0.0 and row["equity"] == 0.0:
                    continue
                row_tax_rate = 0.21
                if row["pretax"] > 0 and row["tax"] > 0:
                    row_tax_rate = row["tax"] / row["pretax"]
                    if row_tax_rate < 0 or row_tax_rate > 0.8:
                        row_tax_rate = 0.21
                row_nopat = row["ebit"] * (1.0 - row_tax_rate)
                row_debt_val = row["debt"] if row["debt"] != 0.0 else (row["lt_debt"] + row["st_debt"])
                row_ic = row["equity"] + row_debt_val
                if row_ic > 0:
                    roic_history.append(row_nopat / row_ic)

            roic = statistics.median(roic_history) if roic_history else 0.0

            # Debt to Equity
            equity = self.safe_get_row(
                balance_sheet,
                ["StockholdersEquity", "TotalStockholdersEquity", "Stockholders Equity", "Total Stockholders Equity"],
            )
            debt = self.safe_get_row(balance_sheet, ["TotalDebt", "Total Debt"])
            if debt == 0.0:
                debt = self.safe_get_row(balance_sheet, ["LongTermDebt", "Long Term Debt"]) + self.safe_get_row(
                    balance_sheet, ["ShortLongTermDebt", "Short Long Term Debt"]
                )

            market_cap = float(info.get("marketCap") or 0.0)
            if equity > 0:
                debt_to_equity = debt / equity
            elif market_cap > 0:
                debt_to_equity = debt / market_cap
            else:
                debt_to_equity = 999.0 if debt > 0 else 0.0

            # FCF Yield & FCF Trend
            fcf_series = self.safe_get_series(cashflow, ["FreeCashFlow", "Free Cash Flow"])
            if fcf_series.empty:
                ocf_s = self.safe_get_series(
                    cashflow, ["OperatingCashFlow", "Cash Flow From Operating Activities", "Operating Cash Flow"]
                )
                capex_s = self.safe_get_series(cashflow, ["CapitalExpenditure", "Capital Expenditure"])
                if not ocf_s.empty and not capex_s.empty:
                    fcf_series = (ocf_s + capex_s).dropna()

            fcf_vals = [float(x) for x in fcf_series.tolist() if x == x]
            latest_fcf = fcf_vals[0] if fcf_vals else 0.0
            fcf_yield = (latest_fcf / market_cap) if market_cap > 0 else 0.0

            if not fcf_vals:
                fcf_trend = "Unknown"
            elif latest_fcf < 0:
                fcf_trend = "Negative"
            elif len(fcf_vals) >= 2:
                oldest_fcf = fcf_vals[min(len(fcf_vals) - 1, 3)]
                if oldest_fcf > 0 and latest_fcf > oldest_fcf * 1.05:
                    fcf_trend = "Growing"
                elif oldest_fcf > 0 and latest_fcf < oldest_fcf * 0.90:
                    fcf_trend = "Declining"
                else:
                    fcf_trend = "Stable"
            else:
                fcf_trend = "Positive"

            return StockData(
                ticker=ticker.upper(),
                name=name,
                industry=industry,
                sector=sector,
                is_peaceful=peaceful,
                current_price=current_price,
                currency=currency,
                low_52w=low_52w,
                high_52w=high_52w,
                current_pe=current_pe,
                forward_pe=forward_pe,
                pe_5yr_avg=pe_5yr_avg,
                gross_margin=gross_margin,
                operating_margin=operating_margin,
                roic=roic,
                roe=roe,
                debt_to_equity=debt_to_equity,
                fcf_yield=fcf_yield,
                revenue_growth_yoy=revenue_growth_yoy,
                revenue_cagr_3yr=revenue_cagr_3yr,
                fcf_trend=fcf_trend,
            )

        except Exception as e:
            logger.error(f"Error fetching snapshot for {ticker}: {e}")
            return StockData(
                ticker=ticker.upper(),
                name=ticker.upper(),
                industry="Unknown",
                error_message=str(e),
            )


if __name__ == "__main__":
    fetcher = YFinanceFetcher()
    print(fetcher.fetch_data("AAPL"))
