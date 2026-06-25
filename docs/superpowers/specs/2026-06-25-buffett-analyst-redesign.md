# Buffett Analyst Redesign Specification

## 1. Overview
The `buffett_analyst` agent is being redesigned to move away from rigid, relative scoring systems (like AHP-TOPSIS) toward an absolute valuation model tailored to specific business structures. The update introduces dynamic business classification, exact intrinsic valuation bounds, and qualitative FCF auditing to prevent premature selling and flawed exclusions.

## 2. Architecture Pipeline
The core workflow will be updated to follow this pipeline:

1. **[Fetch Ticker Data]**
2. **[Business Model Classifier]**
   - **Asset-Heavy/Cyclical**: Screen via traditional D/E < 1.0, ROIC > 15%.
   - **Asset-Light/Platform/Franchise**: Screen via EV/FCF vs 5-yr median, CROIC > 15%.
3. **[FCF Trend Check]**
   - If FCF growth is positive: Proceed to DCF Engine.
   - If FCF growth is negative: Trigger **[Qualitative 10-Q Audit Agent]**.
     - If passed (Temporary Reinvestment Cycle): Proceed to DCF Engine.
     - If failed (Structural Core Decline): Force Markdown SELL / Exclude from Bargains.
4. **[10-Year Intrinsic DCF Engine]**
5. **[Generate Absolute Valuation Table]**

## 3. Detailed Component Specs

### 3.1 Absolute Valuation Table
- **Format**: The final report will replace `[DECISION MATRIX]` with `[ABSOLUTE VALUATION TABLE]`.
- **Columns**: `Ticker` | `Current Price` | `Fair Value (Intrinsic)` | `MoS %` | `Status` | `Action`
- **Actions**:
  - **Strong Buy**: Current Price < Bargain Price (e.g., >30% Margin of Safety)
  - **Buy**: Current Price < Fair Value
  - **Hold**: Current Price < Expensive Price AND structural moat intact
  - **Sell / Strong Sell**: Current Price > Expensive Price OR structural core decline
- **DCF Safeguards**: 
  - Terminal growth rate is hard-capped at 2.5% - 3.5% (long-term GDP).
  - Discount Rate (WACC) must be dynamically adjusted based on beta and debt cost, not a static 10%.

### 3.2 Business-Model-Specific Screening
Instead of relying on AI intuition, classification uses programmatic logic:
```python
if (Capital_Expenditures / Operating_Cash_Flow) < 0.20 or (Net_Intangibles_and_Goodwill / Total_Assets) > 0.40:
    business_type = "Asset-Light/Platform"
else:
    business_type = "Asset-Heavy/Cyclical"
```
- **CROIC Formula**: `CROIC = Free Cash Flow / (Total Debt + Total Equity - Cash & Equivalents)`
- **EV/FCF Evaluation**: Compare the current EV/FCF against the company's historical 5-year median EV/FCF to avoid permanently categorizing premium compounders as "Expensive".

### 3.3 FCF Auditing & The Sell Logic
The qualitative 10-Q audit agent will use strict parsing rules when FCF growth drops below 0:
- **Rule 1**: IF Operating Cash Flow (OCF) is steady/growing AND FCF dropped solely due to an increase in Capital Expenditures (CapEx):
  - Identify CapEx target (e.g., Datacenter expansion).
  - Classify as: "Temporary Reinvestment Cycle".
  - Action: Maintain Hold/Buy (if valuation allows).
- **Rule 2**: IF Operating Cash Flow (OCF) is declining due to shrinking Net Income or ballooning inventory/receivables:
  - Classify as: "Structural Core Decline".
  - Action: Downgrade to SELL.
- **Rule 3**: The system is explicitly banned from recommending a sale purely to "lock in profits at historical highs".
