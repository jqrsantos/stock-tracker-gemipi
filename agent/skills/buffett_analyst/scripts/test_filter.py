import unittest
from filter_stocks import StockData, BuffettQuantitativeFilter, PeacefulFilter

class TestBuffettFilter(unittest.TestCase):
    def setUp(self):
        self.filter = BuffettQuantitativeFilter()

    def test_identify_bargains(self):
        """Tests if the filter correctly identifies a stock that meets all criteria."""
        bargain = StockData(
            ticker="GOOD",
            name="Great Company",
            industry="Tech",
            roic=0.20,           # > 0.15
            debt_to_equity=0.5,  # < 1.0
            fcf_yield=0.07,      # > 0.05
            current_pe=15.0,     # < 20.0
            pe_5yr_avg=20.0
        )
        
        results = self.filter.filter([bargain])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].ticker, "GOOD")

    def test_exclude_low_roic(self):
        """Tests exclusion when ROIC is too low."""
        bad_roic = StockData(
            ticker="LOW_ROIC",
            name="Low ROIC Co",
            industry="Retail",
            roic=0.10,           # < 0.15
            debt_to_equity=0.5,
            fcf_yield=0.07,
            current_pe=15.0,
            pe_5yr_avg=20.0
        )
        results = self.filter.filter([bad_roic])
        self.assertEqual(len(results), 0)

    def test_exclude_high_debt(self):
        """Tests exclusion when Debt/Equity is too high."""
        high_debt = StockData(
            ticker="DEBT",
            name="Debt Heavy Co",
            industry="Manufacturing",
            roic=0.20,
            debt_to_equity=1.5,  # > 1.0
            fcf_yield=0.07,
            current_pe=15.0,
            pe_5yr_avg=20.0
        )
        results = self.filter.filter([high_debt])
        self.assertEqual(len(results), 0)

    def test_exclude_low_fcf_yield(self):
        """Tests exclusion when FCF Yield is too low."""
        low_fcf = StockData(
            ticker="LOW_FCF",
            name="Low FCF Co",
            industry="Tech",
            roic=0.20,
            debt_to_equity=0.5,
            fcf_yield=0.03,      # < 0.05
            current_pe=15.0,
            pe_5yr_avg=20.0
        )
        results = self.filter.filter([low_fcf])
        self.assertEqual(len(results), 0)

    def test_exclude_high_pe(self):
        """Tests exclusion when current P/E is higher than 5-year average."""
        high_pe = StockData(
            ticker="EXPENSIVE",
            name="Expensive Co",
            industry="Tech",
            roic=0.20,
            debt_to_equity=0.5,
            fcf_yield=0.07,
            current_pe=25.0,     # > 20.0
            pe_5yr_avg=20.0
        )
        results = self.filter.filter([high_pe])
        self.assertEqual(len(results), 0)

    def test_peaceful_exclusion(self):
        """Tests that defense stocks are ALWAYS excluded even if they have great financials."""
        defense_stock = StockData(
            ticker="LMT",
            name="Lockheed Martin",
            industry="Aerospace & Defense",
            roic=0.30,           # Great
            debt_to_equity=0.2,  # Great
            fcf_yield=0.10,      # Great
            current_pe=10.0,     # Great
            pe_5yr_avg=20.0
        )
        
        # Test individual industries
        for industry in PeacefulFilter.EXCLUDED_INDUSTRIES:
            stock = StockData(
                ticker="WAR", name="War Co", industry=industry,
                roic=0.30, debt_to_equity=0.2, fcf_yield=0.10, current_pe=10.0, pe_5yr_avg=20.0
            )
            results = self.filter.filter([stock])
            self.assertEqual(len(results), 0, f"Failed to exclude {industry}")

    def test_multiple_stocks(self):
        """Tests a mix of good and bad stocks."""
        stocks = [
            StockData("GOOD", "Good", "Tech", 0.2, 0.5, 0.07, 15, 20),
            StockData("WAR", "War", "Defense", 0.3, 0.2, 0.1, 10, 20),
            StockData("DEBT", "Debt", "Tech", 0.2, 1.5, 0.07, 15, 20)
        ]
        results = self.filter.filter(stocks)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].ticker, "GOOD")

if __name__ == "__main__":
    unittest.main()
