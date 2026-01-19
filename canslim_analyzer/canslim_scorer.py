"""
CANSLIM Scorer Module
Implements William O'Neil's CANSLIM stock evaluation method.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from data_fetcher import DataFetcher


@dataclass
class CANSLIMScore:
    """Holds individual CANSLIM component scores and total."""
    ticker: str
    current_earnings: float  # C - 15 pts max
    annual_earnings: float   # A - 15 pts max
    new_highs: float         # N - 15 pts max
    supply_demand: float     # S - 15 pts max
    leader: float            # L - 15 pts max
    institutional: float     # I - 10 pts max
    market: float            # M - 15 pts max
    total: float             # Sum of all scores
    details: Dict[str, str]  # Detailed breakdown for display

    @property
    def max_score(self) -> int:
        return 100


class CANSLIMScorer:
    """Calculates CANSLIM scores for stocks."""

    def __init__(self, data_fetcher: DataFetcher):
        self.fetcher = data_fetcher
        self._market_score: Optional[Tuple[float, str]] = None

    def score_current_earnings(self, ticker: str) -> Tuple[float, str]:
        """
        C - Current Quarterly Earnings (15 pts max)
        Score based on quarter-over-quarter EPS growth.
        15 pts if QoQ growth >= 25%, scaled down proportionally.
        """
        quarterly = self.fetcher.get_quarterly_financials(ticker)
        if quarterly is None:
            return 0.0, "No quarterly data available"

        try:
            # Try to get Net Income for EPS proxy
            if 'Net Income' in quarterly.index:
                net_income = quarterly.loc['Net Income'].dropna()
                if len(net_income) >= 2:
                    current = net_income.iloc[0]
                    previous = net_income.iloc[1]

                    if previous > 0:
                        qoq_growth = ((current - previous) / previous) * 100
                    elif previous < 0 and current > previous:
                        qoq_growth = 25  # Turnaround scenario
                    else:
                        qoq_growth = 0

                    # Score: 15 pts if >= 25% growth, scaled down
                    if qoq_growth >= 25:
                        score = 15.0
                    elif qoq_growth > 0:
                        score = (qoq_growth / 25) * 15
                    else:
                        score = 0.0

                    return score, f"QoQ: {qoq_growth:+.1f}%"
        except Exception:
            pass

        return 0.0, "Could not calculate QoQ growth"

    def score_annual_earnings(self, ticker: str) -> Tuple[float, str]:
        """
        A - Annual Earnings Growth (15 pts max)
        Score based on 3-year compound annual growth rate (CAGR) of earnings.
        15 pts if CAGR >= 25%, scaled down proportionally.
        """
        annual = self.fetcher.get_annual_financials(ticker)
        if annual is None:
            return 0.0, "No annual data available"

        try:
            if 'Net Income' in annual.index:
                net_income = annual.loc['Net Income'].dropna()
                if len(net_income) >= 3:
                    recent = net_income.iloc[0]
                    oldest = net_income.iloc[2]

                    if oldest > 0 and recent > 0:
                        # Calculate 3-year CAGR
                        cagr = ((recent / oldest) ** (1/3) - 1) * 100

                        # Score: 15 pts if >= 25% CAGR, scaled down
                        if cagr >= 25:
                            score = 15.0
                        elif cagr > 0:
                            score = (cagr / 25) * 15
                        else:
                            score = 0.0

                        return score, f"3yr CAGR: {cagr:.1f}%"
        except Exception:
            pass

        return 0.0, "Could not calculate annual growth"

    def score_new_highs(self, ticker: str) -> Tuple[float, str]:
        """
        N - New Highs / Innovation (15 pts max)
        Score based on proximity to 52-week high.
        15 pts if within 5%, 10 pts if within 10%, 5 pts if within 15%.
        """
        current_price = self.fetcher.get_current_price(ticker)
        high_52wk = self.fetcher.get_52_week_high(ticker)

        if current_price is None or high_52wk is None or high_52wk == 0:
            return 0.0, "Price data unavailable"

        pct_from_high = ((high_52wk - current_price) / high_52wk) * 100

        if pct_from_high <= 5:
            score = 15.0
        elif pct_from_high <= 10:
            score = 10.0
        elif pct_from_high <= 15:
            score = 5.0
        else:
            score = 0.0

        return score, f"within {pct_from_high:.1f}% of 52wk high"

    def score_supply_demand(self, ticker: str) -> Tuple[float, str]:
        """
        S - Supply & Demand (15 pts max)
        Score based on volume patterns and accumulation/distribution.
        Compares recent volume to 50-day average with price action.
        """
        history = self.fetcher.get_historical_prices(ticker)
        if history is None or len(history) < 50:
            return 0.0, "Insufficient historical data"

        try:
            # Calculate recent volume vs 50-day average
            recent_volume = history['Volume'].iloc[-5:].mean()
            avg_volume = history['Volume'].iloc[-50:].mean()

            if avg_volume == 0:
                return 0.0, "No volume data"

            volume_ratio = recent_volume / avg_volume

            # Check price trend (accumulation vs distribution)
            recent_close = history['Close'].iloc[-1]
            close_5_days_ago = history['Close'].iloc[-5]
            price_change = ((recent_close - close_5_days_ago) / close_5_days_ago) * 100

            # Score based on volume surge with positive price action
            if volume_ratio > 1.5 and price_change > 0:
                score = 15.0
                detail = f"vol {volume_ratio:.1f}x avg, rising"
            elif volume_ratio > 1.2 and price_change > 0:
                score = 10.0
                detail = f"vol {volume_ratio:.1f}x avg, rising"
            elif volume_ratio > 1.0 and price_change > 0:
                score = 7.0
                detail = f"vol {volume_ratio:.1f}x avg, rising"
            elif price_change > 0:
                score = 5.0
                detail = f"price rising, avg volume"
            else:
                score = 0.0
                detail = f"weak accumulation pattern"

            return score, detail
        except Exception:
            pass

        return 0.0, "Could not calculate supply/demand"

    def score_leader(self, ticker: str) -> Tuple[float, str]:
        """
        L - Leader vs Laggard (15 pts max)
        Score based on Relative Strength vs S&P 500 over 12 months.
        15 pts if RS > 1.3, scaled down to 0 if RS < 0.7.
        """
        stock_history = self.fetcher.get_historical_prices(ticker)
        sp500_history = self.fetcher.get_sp500_data()

        if stock_history is None or sp500_history is None:
            return 0.0, "Insufficient data for RS calculation"

        try:
            if len(stock_history) < 252 or len(sp500_history) < 252:
                # Use available data
                min_len = min(len(stock_history), len(sp500_history))
                if min_len < 50:
                    return 0.0, "Insufficient historical data"

            # Calculate 12-month returns (or available period)
            stock_return = (stock_history['Close'].iloc[-1] / stock_history['Close'].iloc[0] - 1) * 100
            sp500_return = (sp500_history['Close'].iloc[-1] / sp500_history['Close'].iloc[0] - 1) * 100

            # Calculate Relative Strength
            if sp500_return != 0:
                rs = (1 + stock_return/100) / (1 + sp500_return/100)
            else:
                rs = 1 + stock_return/100

            # Score based on RS
            if rs > 1.3:
                score = 15.0
            elif rs > 1.0:
                score = ((rs - 1.0) / 0.3) * 15
            elif rs > 0.7:
                score = ((rs - 0.7) / 0.3) * 7.5
            else:
                score = 0.0

            return score, f"RS: {rs:.2f}"
        except Exception:
            pass

        return 0.0, "Could not calculate RS"

    def score_institutional(self, ticker: str) -> Tuple[float, str]:
        """
        I - Institutional Ownership (10 pts max)
        Score based on institutional ownership percentage.
        10 pts if 20-60% (sweet spot), lower for extremes.
        """
        inst_pct = self.fetcher.get_institutional_ownership_pct(ticker)

        if inst_pct is None:
            return 5.0, "ownership data unavailable"  # Give benefit of doubt

        # Sweet spot is 20-60% institutional ownership
        if 20 <= inst_pct <= 60:
            score = 10.0
        elif 10 <= inst_pct < 20:
            score = 7.0
        elif 60 < inst_pct <= 80:
            score = 7.0
        elif inst_pct < 10:
            score = 3.0
        else:  # > 80%
            score = 3.0

        return score, f"{inst_pct:.0f}% inst. owned"

    def score_market(self) -> Tuple[float, str]:
        """
        M - Market Direction (15 pts max)
        Score based on S&P 500 trend indicators.
        Checks if market is above 200-day and 50-day moving averages.
        """
        # Cache market score since it's the same for all stocks
        if self._market_score is not None:
            return self._market_score

        sp500_history = self.fetcher.get_sp500_data()
        if sp500_history is None or len(sp500_history) < 200:
            self._market_score = (7.5, "market data limited")
            return self._market_score

        try:
            current_price = sp500_history['Close'].iloc[-1]
            ma_200 = sp500_history['Close'].rolling(window=200).mean().iloc[-1]
            ma_50 = sp500_history['Close'].rolling(window=50).mean().iloc[-1]

            above_200 = current_price > ma_200
            above_50 = current_price > ma_50

            if above_200 and above_50:
                score = 15.0
                trend = "bullish market"
            elif above_200:
                score = 10.0
                trend = "mixed market"
            elif above_50:
                score = 5.0
                trend = "cautious market"
            else:
                score = 0.0
                trend = "bearish market"

            self._market_score = (score, trend)
            return self._market_score
        except Exception:
            pass

        self._market_score = (7.5, "market analysis error")
        return self._market_score

    def calculate_score(self, ticker: str) -> Optional[CANSLIMScore]:
        """Calculate complete CANSLIM score for a stock."""
        # Validate ticker has data
        if not self.fetcher.is_valid_ticker(ticker):
            return None

        details = {}

        # Calculate each component
        c_score, c_detail = self.score_current_earnings(ticker)
        details['C'] = c_detail

        a_score, a_detail = self.score_annual_earnings(ticker)
        details['A'] = a_detail

        n_score, n_detail = self.score_new_highs(ticker)
        details['N'] = n_detail

        s_score, s_detail = self.score_supply_demand(ticker)
        details['S'] = s_detail

        l_score, l_detail = self.score_leader(ticker)
        details['L'] = l_detail

        i_score, i_detail = self.score_institutional(ticker)
        details['I'] = i_detail

        m_score, m_detail = self.score_market()
        details['M'] = m_detail

        total = c_score + a_score + n_score + s_score + l_score + i_score + m_score

        return CANSLIMScore(
            ticker=ticker,
            current_earnings=c_score,
            annual_earnings=a_score,
            new_highs=n_score,
            supply_demand=s_score,
            leader=l_score,
            institutional=i_score,
            market=m_score,
            total=total,
            details=details
        )


if __name__ == "__main__":
    # Test the scorer
    fetcher = DataFetcher()
    scorer = CANSLIMScorer(fetcher)

    test_ticker = "NVDA"
    print(f"Testing CANSLIM score for {test_ticker}...")

    score = scorer.calculate_score(test_ticker)
    if score:
        print(f"\nTotal Score: {score.total:.1f}/100")
        print(f"C (Current Earnings): {score.current_earnings:.1f}/15 - {score.details['C']}")
        print(f"A (Annual Earnings):  {score.annual_earnings:.1f}/15 - {score.details['A']}")
        print(f"N (New Highs):        {score.new_highs:.1f}/15 - {score.details['N']}")
        print(f"S (Supply/Demand):    {score.supply_demand:.1f}/15 - {score.details['S']}")
        print(f"L (Leader):           {score.leader:.1f}/15 - {score.details['L']}")
        print(f"I (Institutional):    {score.institutional:.1f}/10 - {score.details['I']}")
        print(f"M (Market):           {score.market:.1f}/15 - {score.details['M']}")
    else:
        print("Could not calculate score - insufficient data")
