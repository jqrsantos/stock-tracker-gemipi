import google.generativeai as genai
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.warning("GEMINI_API_KEY not found in environment")
else:
    genai.configure(api_key=api_key)

def perform_daily_research(tickers: list):
    """
    Performs macro analysis and generates buy/sell windows using Gemini.
    """
    if not api_key:
        return "Error: Gemini API key not configured."
        
    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = (
            f"Act as a professional stock analyst. Perform a macro-economic analysis "
            f"for the following tickers: {', '.join(tickers)}. \n\n"
            "For each stock, provide:\n"
            "1. A summary of recent news sentiment.\n"
            "2. Estimated 'Cheap', 'Fair', and 'Expensive' price windows.\n"
            "3. A 'Buy/Sell/Hold' recommendation based on current sentiment.\n\n"
            "Also, include a brief Daily Macro Report (Inflation, Interest Rates, Sector moves)."
        )
        
        logger.info(f"Generating research report for {tickers}...")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini research failed: {e}")
        return f"Error during research: {str(e)}"

if __name__ == "__main__":
    # Test run
    test_tickers = ["AAPL", "TSLA", "NVDA"]
    print(perform_daily_research(test_tickers))
