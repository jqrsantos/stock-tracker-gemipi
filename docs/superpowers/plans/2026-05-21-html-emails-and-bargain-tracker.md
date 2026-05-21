# HTML Emails & stock Bargain Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a database table and FastAPI endpoints to persistently store Warren Buffett-style stock bargains with calculated boundaries (Bargain, Fair, Expensive), and automatically parse the daily markdown reports into stunning, responsive HTML emails with a TL;DR digest at the top.

**Architecture:** Use SQLAlchemy in FastAPI to append a new `Bargain` database table with GET/POST routes. In the notification pipeline, utilize Python's standard `markdown` package with the `tables` extension to parse reports on the fly, inject responsive inline CSS, prepend an extracted TL;DR summary, and dispatch HTML email briefs.

**Tech Stack:** Python 3.11, SQLAlchemy, FastAPI, Pydantic, Python-markdown.

---

## File Structure & Decomposition
We will create and modify the following files:
1. `api/models.py` (Modify): Add the `Bargain` SQLAlchemy DB schema model.
2. `api/main.py` (Modify): Declare Pydantic schemas and expose `POST /bargains/` and `GET /bargains/` endpoints.
3. `agent/skills/buffett_analyst/SKILL.md` (Modify): Refine LLM directives to compute custom intervals (Bargain, Fair, Expensive) and POST findings to the API database.
4. `pyproject.toml` and `agent/pyproject.toml` (Modify): Add the `markdown` library package dependency.
5. `agent/notifier.py` (Modify): Re-architect to extract the TL;DR header, convert markdown to HTML, apply custom responsive CSS layouts, and send standard multi-part HTML emails.

---

### Task 1: Database Migration & Model Setup

**Files:**
* Modify: [api/models.py](file:///Users/joaosantos/stock-tracker/api/models.py)
* Test: Run a manual compilation check to verify SQLAlchemy schema load.

- [ ] **Step 1: Write the `Bargain` SQLAlchemy model**
  
  Add the `Bargain` model definition to [api/models.py](file:///Users/joaosantos/stock-tracker/api/models.py) at the bottom of the file:
  
  ```python
  class Bargain(Base):
      __tablename__ = "bargains"
      id = Column(Integer, primary_key=True, index=True)
      ticker = Column(String, index=True, nullable=False)
      name = Column(String, nullable=False)
      industry = Column(String, nullable=False)
      current_price = Column(Numeric(18, 8), nullable=False)
      currency = Column(String, nullable=False, default="USD")
      
      # Valuation intervals calculated dynamically by LLM
      bargain_price = Column(Numeric(18, 8), nullable=False)  # Buy Limit
      fair_price = Column(Numeric(18, 8), nullable=False)     # Intrinsic Value
      expensive_price = Column(Numeric(18, 8), nullable=False) # Sell Limit
      
      rationale = Column(String, nullable=False)
      timestamp = Column(DateTime, server_default=func.now())
  ```

- [ ] **Step 2: Run syntax compilation check**
  
  Verify the modified file contains no syntax issues:
  ```bash
  python3 -m py_compile api/models.py
  ```
  Expected: Exit code 0 (no output).

- [ ] **Step 3: Commit database schema changes**
  ```bash
  git add api/models.py
  git commit -m "feat(api): add Bargain database model to track stock valuation intervals"
  ```

---

### Task 2: Pydantic Validation & API Routes

**Files:**
* Modify: [api/main.py](file:///Users/joaosantos/stock-tracker/api/main.py)
* Test: Run API verification using manual curl execution once FastAPI restarts.

- [ ] **Step 1: Declare Pydantic models for validation**
  
  Add Pydantic classes to [api/main.py](file:///Users/joaosantos/stock-tracker/api/main.py) right below `TransactionResponse` (around line 40):
  
  ```python
  class BargainCreate(BaseModel):
      ticker: str
      name: str
      industry: str
      current_price: float
      currency: str = "USD"
      bargain_price: float
      fair_price: float
      expensive_price: float
      rationale: str

  class BargainResponse(BaseModel):
      id: int
      ticker: str
      name: str
      industry: str
      current_price: float
      currency: str
      bargain_price: float
      fair_price: float
      expensive_price: float
      rationale: str
      timestamp: datetime

      class Config:
          from_attributes = True
  ```

- [ ] **Step 2: Implement FastAPI endpoints**
  
  Expose `POST /bargains/` and `GET /bargains/` routes at the bottom of [api/main.py](file:///Users/joaosantos/stock-tracker/api/main.py):
  
  ```python
  @app.post("/bargains/", response_model=BargainResponse)
  def add_bargain(bargain: BargainCreate, db: Session = Depends(get_db)):
      try:
          db_bargain = models.Bargain(
              ticker=bargain.ticker.upper(),
              name=bargain.name,
              industry=bargain.industry,
              current_price=bargain.current_price,
              currency=bargain.currency,
              bargain_price=bargain.bargain_price,
              fair_price=bargain.fair_price,
              expensive_price=bargain.expensive_price,
              rationale=bargain.rationale
          )
          db.add(db_bargain)
          db.commit()
          db.refresh(db_bargain)
          logger.info(f"Recorded bargain stock: {db_bargain.ticker}")
          return db_bargain
      except Exception as e:
          logger.error(f"Error adding bargain: {e}")
          db.rollback()
          raise HTTPException(status_code=500, detail=str(e))

  @app.get("/bargains/", response_model=List[BargainResponse])
  def get_bargains(db: Session = Depends(get_db)):
      try:
          return db.query(models.Bargain).order_by(models.Bargain.timestamp.desc()).all()
      except Exception as e:
          logger.error(f"Error fetching bargains: {e}")
          raise HTTPException(status_code=500, detail=str(e))
  ```

- [ ] **Step 3: Run syntax check and verify endpoints compile**
  
  Run:
  ```bash
  python3 -m py_compile api/main.py
  ```
  Expected: Exit code 0 (no output).

- [ ] **Step 4: Commit API changes**
  ```bash
  git add api/main.py
  git commit -m "feat(api): expose POST and GET endpoints for tracking stock bargains"
  ```

---

### Task 3: Refine Agent Skill & Prompts

**Files:**
* Modify: [agent/skills/buffett_analyst/SKILL.md](file:///Users/joaosantos/stock-tracker/agent/skills/buffett_analyst/SKILL.md)
* Modify: [run_daily_research.sh](file:///Users/joaosantos/stock-tracker/run_daily_research.sh)

- [ ] **Step 1: Refine the "Peaceful" Bargain Hunting section in `SKILL.md`**
  
  Update `agent/skills/buffett_analyst/SKILL.md` lines 30-35:
  
  ```markdown
  ### 3. "Peaceful" Bargain Hunting
  - Scan indexes (S&P 500, Nasdaq 100, Stoxx 600) for high-quality candidates.
  - Apply quantitative filters: ROIC > 15%, Debt/Equity < 1.0, FCF Yield > 5%, P/E < 5-year average.
  - Conduct a qualitative "Moat" assessment on the top 3 candidates.
  - Estimate valuation boundaries using Dynamic Agent Analysis:
    - **Bargain Price**: Intrinsic value discounted by a calculated Margin of Safety (typically 20% to 30% depending on risk metrics).
    - **Fair Price**: Intrinsic value derived from discounted Owner Earnings/FCF.
    - **Expensive Price**: Intrinsic value + a premium threshold (typically 20% to 30%).
  - Recommend only the best "peaceful" opportunities in the [BARGAIN RADAR], specifying current price, currency, and calculated valuation intervals.
  - **Save to Database:** Persist the final identified bargains by issuing `POST http://localhost:8000/bargains/` requests for each bargain with its current price and boundaries.
  ```

- [ ] **Step 2: Update the daily research execution shell prompt**
  
  Modify [run_daily_research.sh](file:///Users/joaosantos/stock-tracker/run_daily_research.sh) line 22 to explicitly command the agent to determine the price intervals and post them to the API:
  
  ```bash
  $GEMINI_BIN --prompt "You are a senior financial research agent. Use your 'Buffett Strategic Analyst' skill to perform a Deep Scour, evaluate the current portfolio holdings: ($PORTFOLIO_TICKERS). Hunt for bargains, calculate dynamic price intervals (bargain, fair, expensive) for each bargain pick, persist them using the 'POST /bargains/' API endpoint, and update the knowledge base. Ensure you update the active memory and write the final report. Print 'REPORT_COMPLETE' when finished." --yolo --skip-trust
  ```

- [ ] **Step 3: Commit Prompt and Skill modifications**
  ```bash
  git add agent/skills/buffett_analyst/SKILL.md run_daily_research.sh
  git commit -m "feat(prompt): instruct research agent to calculate price intervals and persist them to DB"
  ```

---

### Task 4: Dependency Setup & HTML Email Generation

**Files:**
* Modify: [pyproject.toml](file:///Users/joaosantos/stock-tracker/pyproject.toml)
* Modify: [agent/pyproject.toml](file:///Users/joaosantos/stock-tracker/agent/pyproject.toml)
* Modify: [agent/notifier.py](file:///Users/joaosantos/stock-tracker/agent/notifier.py)

- [ ] **Step 1: Add `markdown` to dependencies**
  
  Add `"markdown"` package under `dependencies` in [pyproject.toml](file:///Users/joaosantos/stock-tracker/pyproject.toml):
  ```toml
  dependencies = [
      "requests",
      "python-dotenv",
      "markdown",
  ]
  ```
  
  And also in [agent/pyproject.toml](file:///Users/joaosantos/stock-tracker/agent/pyproject.toml):
  ```toml
  dependencies = [
      "requests",
      "python-dotenv",
      "markdown",
  ]
  ```

- [ ] **Step 2: Re-architect `agent/notifier.py` to send HTML emails**
  
  Replace the `send_email` and command line block in [agent/notifier.py](file:///Users/joaosantos/stock-tracker/agent/notifier.py) (lines 40-93) to include markdown parsing, TL;DR extraction, and visual custom styling:
  
  ```python
  import markdown
  import re

  def extract_tldr(markdown_text: str) -> str:
      """
      Extracts key highlights from the report to create a concise TL;DR block.
      """
      highlights = []
      # Look for GLOBAL NARRATIVE highlights or key sentences
      narrative_section = re.search(r"## \[GLOBAL NARRATIVE\]\s*(.*?)(?=##|$)", markdown_text, re.DOTALL)
      if narrative_section:
          text = narrative_section.group(1).strip()
          sentences = [s.strip() + "." for s in text.split(".") if len(s.strip()) > 10]
          highlights.extend(sentences[:2])
      
      # Look for Bargain Radar picks
      radar_section = re.search(r"## \[BARGAIN RADAR\]\s*(.*?)(?=##|$)", markdown_text, re.DOTALL)
      if radar_section:
          picks = re.findall(r"\d+\.\s+\*\*([A-Z]+)\b", radar_section.group(1))
          if picks:
              highlights.append(f"Highlighted moated bargains: {', '.join(picks)}")
              
      if not highlights:
          highlights = ["Fed rate decisions & energy supply shocks continue to drive macro trends.", "Portfolio evaluated for fundamental strengths & ROIC health."]
          
      li_items = "".join([f"<li style='margin-bottom: 6px;'>{item}</li>" for item in highlights])
      return f"""
      <div style="background: #f8fafc; border-left: 4px solid #3b82f6; border-radius: 4px; padding: 16px; margin-bottom: 24px;">
        <h3 style="margin: 0 0 8px 0; font-size: 0.95rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #1e293b;">⚡ Daily TL;DR Digest</h3>
        <ul style="margin: 0; padding-left: 20px; font-size: 0.875rem; color: #475569;">
          {li_items}
        </ul>
      </div>
      """

  def build_html_body(subject: str, markdown_content: str) -> str:
      """
      Converts report markdown into a beautifully designed HTML document.
      """
      tldr_html = extract_tldr(markdown_content)
      
      # Parse markdown using tables extension
      raw_html = markdown.markdown(markdown_content, extensions=['tables'])
      
      # Style standard elements generated by markdown parser
      styled_html = raw_html
      styled_html = styled_html.replace("<table>", '<table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.875rem; text-align: left;">')
      styled_html = styled_html.replace("<thead>", '<thead style="background: #f8fafc; color: #475569; font-weight: 600; border-bottom: 2px solid #e2e8f0;">')
      styled_html = styled_html.replace("<th>", '<th style="padding: 10px 12px; border-bottom: 2px solid #e2e8f0;">')
      styled_html = styled_html.replace("<td>", '<td style="padding: 10px 12px; border-bottom: 1px solid #f1f5f9;">')
      
      # Bold and styling alerts
      styled_html = styled_html.replace("<strong>BUY</strong>", '<span style="background: #ecfdf5; color: #10b981; padding: 2px 6px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">BUY</span>')
      styled_html = styled_html.replace("<strong>SELL</strong>", '<span style="background: #fef2f2; color: #dc2626; padding: 2px 6px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">SELL</span>')
      styled_html = styled_html.replace("<strong>HOLD</strong>", '<span style="background: #fffbeb; color: #d97706; padding: 2px 6px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">HOLD</span>')
      styled_html = styled_html.replace("<strong>BULLISH</strong>", '<span style="background: #ecfdf5; color: #10b981; padding: 2px 6px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">BULLISH</span>')
      styled_html = styled_html.replace("<strong>BEARISH</strong>", '<span style="background: #fef2f2; color: #ef4444; padding: 2px 6px; border-radius: 12px; font-size: 0.75rem; font-weight: 700;">BEARISH</span>')

      # Styled sections
      styled_html = re.sub(r'<h3>(.*?)</h3>', r'<h3 style="margin: 28px 0 12px 0; font-size: 1.1rem; font-weight: 700; color: #0f172a; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">\1</h3>', styled_html)
      styled_html = re.sub(r'<h2>(.*?)</h2>', r'<h2 style="margin: 24px 0 12px 0; font-size: 1.25rem; font-weight: 700; color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px;">\1</h2>', styled_html)

      return f"""
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
      </head>
      <body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        <div style="max-width: 650px; margin: 20px auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; background: #ffffff; color: #334155; line-height: 1.6; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
          
          <!-- Header -->
          <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 32px 24px; color: #ffffff; text-align: center; border-bottom: 4px solid #3b82f6;">
            <h1 style="margin: 0; font-size: 1.75rem; font-weight: 800; letter-spacing: -0.025em; color: #ffffff;">📈 BUFFETT STRATEGIC ANALYST</h1>
            <p style="margin: 6px 0 0 0; font-size: 0.875rem; color: #94a3b8; font-weight: 500;">DAILY FINANCIAL MARKET BRIEFING</p>
          </div>

          <div style="padding: 24px;">
            {tldr_html}
            {styled_html}
          </div>

          <!-- Footer -->
          <div style="background: #f8fafc; padding: 20px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 0.75rem; color: #94a3b8;">
            <p style="margin: 0 0 4px 0;">This research is prepared using Warren Buffett & Charlie Munger's value investing principles.</p>
            <p style="margin: 0;">Stock Tracker Automated Intelligence • Raspberry Pi Station</p>
          </div>
        </div>
      </body>
      </html>
      """

  def send_email(subject: str, body: str):
      smtp_server = os.getenv("SMTP_SERVER")
      smtp_port = os.getenv("SMTP_PORT", "587")
      smtp_user = os.getenv("SMTP_USER")
      smtp_password = os.getenv("SMTP_PASSWORD")
      email_to = os.getenv("EMAIL_TO")
      
      if not all([smtp_server, smtp_user, smtp_password, email_to]):
          logger.warning("Email credentials missing. Skipping email notification.")
          return False
          
      try:
          msg = EmailMessage()
          msg['Subject'] = subject
          msg['From'] = smtp_user
          msg['To'] = email_to
          
          # Set plain-text body alternative
          msg.set_content(body)
          
          # Set rich HTML body
          html_body = build_html_body(subject, body)
          msg.add_alternative(html_body, subtype='html')

          port = int(smtp_port)
          if port == 465:
              server = smtplib.SMTP_SSL(smtp_server, port)
          else:
              server = smtplib.SMTP(smtp_server, port)
              server.starttls()
              
          server.login(smtp_user, smtp_password)
          server.send_message(msg)
          server.quit()
          return True
      except Exception as e:
          logger.error(f"Email network error: {e}")
          return False

  if __name__ == "__main__":
      logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
      from dotenv import load_dotenv
      load_dotenv()
      
      base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
      report_dir = os.path.join(base_dir, "knowledge_base", "daily_reports")
      
      list_of_files = glob.glob(f"{report_dir}/*.md")
      if not list_of_files:
          logger.warning("No reports found to send.")
      else:
          latest_file = max(list_of_files, key=os.path.getctime)
          with open(latest_file, 'r') as f:
              content = f.read()
          logger.info(f"Sending latest report: {os.path.basename(latest_file)}")
          send_telegram(content)
          send_email(f"Daily Report: {os.path.basename(latest_file)}", content)
  ```

- [ ] **Step 3: Run compilation check**
  
  Verify the modified file has no syntax errors:
  ```bash
  python3 -m py_compile agent/notifier.py
  ```
  Expected: Exit code 0 (no output).

- [ ] **Step 4: Commit changes**
  ```bash
  git add pyproject.toml agent/pyproject.toml agent/notifier.py
  git commit -m "feat(email): parse markdown report to stunning custom HTML email with TL;DR digest"
  ```
