"""
Growth Projector Module
Projects 6-month stock growth using multiple factors.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict
from dataclasses import dataclass
from scipy import stats
from data_fetcher import DataFetcher
from canslim_scorer import CANSLIMScore


@dataclass
class GrowthProjection:
    """Holds growth projection data for a stock."""
    ticker: str
    current_price: float
    projected_price: float
    projected_growth_pct: float
    momentum_component: float      # 40% weight
    earnings_component: float      # 30% weight
    canslim_component: float       # 20% weight
    sector_component: float        # 10% weight
    confidence: str                # Low, Medium, High


class GrowthProjector:
    """Projects 6-month stock growth based on multiple factors."""

    # Sector ETF mappings for sector momentum
    SECTOR_ETFS = {
        'Technology': 'XLK',
        'Healthcare': 'XLV',
        'Financial Services': 'XLF',
        'Consumer Cyclical': 'XLY',
        'Consumer Defensive': 'XLP',
        'Industrials': 'XLI',
        'Energy': 'XLE',
        'Utilities': 'XLU',
        'Real Estate': 'XLRE',
        'Basic Materials': 'XLB',
        'Communication Services': 'XLC'
    }

    def __init__(self, data_fetcher: DataFetcher):
        self.fetcher = data_fetcher
        self._sector_cache: Dict[str, float] = {}

    def project_momentum_growth(self, ticker: str) -> Optional[float]:
        """
        Project growth based on historical momentum (40% weight).
        Uses linear regression to extrapolate 6-month trend.
        """
        history = self.fetcher.get_historical_prices(ticker, period="6mo")
        if history is None or len(history) < 60:
            return None

        try:
            prices = history['Close'].values
            days = np.arange(len(prices))

            # Linear regression
            slope, intercept, r_value, p_value, std_err = stats.linregress(days, prices)

            # Project forward 126 trading days (6 months)
            current_price = prices[-1]
            projected_price = intercept + slope * (len(prices) + 126)

            # Calculate projected growth
            projected_growth = ((projected_price - current_price) / current_price) * 100

            # Cap extreme projections
            projected_growth = max(-50, min(100, projected_growth))

            return projected_growth
        except Exception:
            return None

    def project_earnings_growth(self, ticker: str) -> Optional[float]:
        """
        Project growth based on earnings trajectory (30% weight).
        Projects EPS growth and applies P/E ratio assumptions.
        """
        quarterly = self.fetcher.get_quarterly_financials(ticker)
        info = self.fetcher.get_stock_info(ticker)

        if quarterly is None or info is None:
            return None

        try:
            # Get recent earnings trend
            if 'Net Income' in quarterly.index:
                net_income = quarterly.loc['Net Income'].dropna()
                if len(net_income) >= 4:
                    # Calculate average quarterly growth rate
                    growth_rates = []
                    for i in range(len(net_income) - 1):
                        if net_income.iloc[i+1] != 0:
                            rate = (net_income.iloc[i] - net_income.iloc[i+1]) / abs(net_income.iloc[i+1])
                            growth_rates.append(rate)

                    if growth_rates:
                        avg_quarterly_growth = np.mean(growth_rates)
                        # Project 2 quarters forward (6 months)
                        projected_earnings_growth = ((1 + avg_quarterly_growth) ** 2 - 1) * 100

                        # Assume stock price follows earnings with some correlation
                        # Moderate the projection
                        projected_growth = projected_earnings_growth * 0.8

                        # Cap extreme projections
                        projected_growth = max(-40, min(80, projected_growth))

                        return projected_growth
        except Exception:
            pass

        return None

    def calculate_canslim_factor(self, canslim_score: CANSLIMScore) -> float:
        """
        Calculate growth factor based on CANSLIM score (20% weight).
        Higher CANSLIM scores correlate with stronger expected growth.
        """
        # Normalize score to 0-1 range
        normalized_score = canslim_score.total / canslim_score.max_score

        # Apply multiplier: scores above 70 get positive factor, below get negative
        if normalized_score >= 0.7:
            factor = (normalized_score - 0.7) * 100  # Up to +30% for perfect score
        elif normalized_score >= 0.5:
            factor = (normalized_score - 0.5) * 50   # Up to +10% for good score
        else:
            factor = (normalized_score - 0.5) * 30   # Negative for poor scores

        return factor

    def calculate_sector_momentum(self, ticker: str) -> Optional[float]:
        """
        Calculate sector momentum bonus (10% weight).
        Compares stock's sector performance.
        """
        info = self.fetcher.get_stock_info(ticker)
        if info is None:
            return None

        sector = info.get('sector')
        if sector is None or sector not in self.SECTOR_ETFS:
            return 0.0

        # Check cache
        if sector in self._sector_cache:
            sector_return = self._sector_cache[sector]
        else:
            # Get sector ETF performance
            sector_etf = self.SECTOR_ETFS[sector]
            sector_history = self.fetcher.get_historical_prices(sector_etf, period="6mo")
            sp500_history = self.fetcher.get_sp500_data(period="6mo")

            if sector_history is None or sp500_history is None:
                return 0.0

            try:
                sector_return = (sector_history['Close'].iloc[-1] / sector_history['Close'].iloc[0] - 1) * 100
                sp500_return = (sp500_history['Close'].iloc[-1] / sp500_history['Close'].iloc[0] - 1) * 100

                # Calculate sector outperformance
                sector_return = sector_return - sp500_return
                self._sector_cache[sector] = sector_return
            except Exception:
                return 0.0

        # Leaders in outperforming sectors get bonus
        if sector_return > 5:
            return sector_return * 0.5  # Half of sector outperformance as bonus
        elif sector_return > 0:
            return sector_return * 0.3
        else:
            return sector_return * 0.2  # Small penalty for lagging sectors

    def project_growth(self, ticker: str, canslim_score: CANSLIMScore) -> Optional[GrowthProjection]:
        """
        Calculate comprehensive 6-month growth projection.

        Formula:
        Projected Growth = (Momentum * 0.4) + (Earnings * 0.3) +
                          (CANSLIM_factor * 0.2) + (Sector_bonus * 0.1)
        """
        current_price = self.fetcher.get_current_price(ticker)
        if current_price is None:
            return None

        # Calculate each component
        momentum_growth = self.project_momentum_growth(ticker)
        earnings_growth = self.project_earnings_growth(ticker)
        canslim_factor = self.calculate_canslim_factor(canslim_score)
        sector_bonus = self.calculate_sector_momentum(ticker)

        # Handle missing components with defaults
        components_available = 0
        total_weight = 0

        # Momentum component (40%)
        if momentum_growth is not None:
            momentum_contrib = momentum_growth * 0.4
            components_available += 1
            total_weight += 0.4
        else:
            momentum_contrib = 0
            momentum_growth = 0

        # Earnings component (30%)
        if earnings_growth is not None:
            earnings_contrib = earnings_growth * 0.3
            components_available += 1
            total_weight += 0.3
        else:
            earnings_contrib = 0
            earnings_growth = 0

        # CANSLIM component (20%) - always available if we have a score
        canslim_contrib = canslim_factor * 0.2
        components_available += 1
        total_weight += 0.2

        # Sector component (10%)
        if sector_bonus is not None:
            sector_contrib = sector_bonus * 0.1
            components_available += 1
            total_weight += 0.1
        else:
            sector_contrib = 0
            sector_bonus = 0

        # Calculate total projected growth
        if total_weight > 0:
            # Normalize if some components missing
            adjustment = 1.0 / total_weight if total_weight < 1.0 else 1.0
            projected_growth = (momentum_contrib + earnings_contrib +
                               canslim_contrib + sector_contrib) * adjustment
        else:
            projected_growth = 0

        # Cap extreme projections
        projected_growth = max(-50, min(150, projected_growth))

        # Calculate projected price
        projected_price = current_price * (1 + projected_growth / 100)

        # Determine confidence level based on data availability
        if components_available >= 4:
            confidence = "High"
        elif components_available >= 3:
            confidence = "Medium"
        else:
            confidence = "Low"

        return GrowthProjection(
            ticker=ticker,
            current_price=current_price,
            projected_price=projected_price,
            projected_growth_pct=projected_growth,
            momentum_component=momentum_growth,
            earnings_component=earnings_growth,
            canslim_component=canslim_factor,
            sector_component=sector_bonus,
            confidence=confidence
        )


if __name__ == "__main__":
    from canslim_scorer import CANSLIMScorer

    # Test the projector
    fetcher = DataFetcher()
    scorer = CANSLIMScorer(fetcher)
    projector = GrowthProjector(fetcher)

    test_ticker = "NVDA"
    print(f"Testing growth projection for {test_ticker}...")

    score = scorer.calculate_score(test_ticker)
    if score:
        projection = projector.project_growth(test_ticker, score)
        if projection:
            print(f"\nCurrent Price: ${projection.current_price:.2f}")
            print(f"Projected Price (6mo): ${projection.projected_price:.2f}")
            print(f"Projected Growth: {projection.projected_growth_pct:+.1f}%")
            print(f"\nComponent Breakdown:")
            print(f"  Momentum (40%): {projection.momentum_component:+.1f}%")
            print(f"  Earnings (30%): {projection.earnings_component:+.1f}%")
            print(f"  CANSLIM (20%):  {projection.canslim_component:+.1f}%")
            print(f"  Sector (10%):   {projection.sector_component:+.1f}%")
            print(f"\nConfidence: {projection.confidence}")
        else:
            print("Could not project growth")
    else:
        print("Could not calculate CANSLIM score")
