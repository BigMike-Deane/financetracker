"""
Data Fetcher Module
Wrapper around yfinance for fetching stock data with caching and error handling.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import time


class DataFetcher:
    """Fetches and caches stock data from Yahoo Finance."""

    def __init__(self, cache_timeout_minutes: int = 30):
        self.cache: Dict[str, Tuple[datetime, Any]] = {}
        self.cache_timeout = timedelta(minutes=cache_timeout_minutes)
        self.retry_count = 3
        self.retry_delay = 1  # seconds

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached data if still valid."""
        if key in self.cache:
            cached_time, data = self.cache[key]
            if datetime.now() - cached_time < self.cache_timeout:
                return data
        return None

    def _set_cached(self, key: str, data: Any) -> None:
        """Cache data with current timestamp."""
        self.cache[key] = (datetime.now(), data)

    def _fetch_with_retry(self, fetch_func, *args, **kwargs) -> Optional[Any]:
        """Execute fetch function with retry logic."""
        for attempt in range(self.retry_count):
            try:
                result = fetch_func(*args, **kwargs)
                return result
            except Exception as e:
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    return None
        return None

    def get_stock_info(self, ticker: str) -> Optional[Dict]:
        """Fetch basic stock information."""
        cache_key = f"info_{ticker}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        def fetch():
            stock = yf.Ticker(ticker)
            info = stock.info
            return info if info else None

        result = self._fetch_with_retry(fetch)
        if result:
            self._set_cached(cache_key, result)
        return result

    def get_historical_prices(self, ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
        """Fetch historical price data."""
        cache_key = f"history_{ticker}_{period}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        def fetch():
            stock = yf.Ticker(ticker)
            history = stock.history(period=period)
            return history if not history.empty else None

        result = self._fetch_with_retry(fetch)
        if result is not None:
            self._set_cached(cache_key, result)
        return result

    def get_quarterly_financials(self, ticker: str) -> Optional[pd.DataFrame]:
        """Fetch quarterly income statement data."""
        cache_key = f"quarterly_{ticker}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        def fetch():
            stock = yf.Ticker(ticker)
            financials = stock.quarterly_income_stmt
            return financials if financials is not None and not financials.empty else None

        result = self._fetch_with_retry(fetch)
        if result is not None:
            self._set_cached(cache_key, result)
        return result

    def get_annual_financials(self, ticker: str) -> Optional[pd.DataFrame]:
        """Fetch annual income statement data."""
        cache_key = f"annual_{ticker}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        def fetch():
            stock = yf.Ticker(ticker)
            financials = stock.income_stmt
            return financials if financials is not None and not financials.empty else None

        result = self._fetch_with_retry(fetch)
        if result is not None:
            self._set_cached(cache_key, result)
        return result

    def get_institutional_holders(self, ticker: str) -> Optional[pd.DataFrame]:
        """Fetch institutional holdings data."""
        cache_key = f"inst_{ticker}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        def fetch():
            stock = yf.Ticker(ticker)
            holders = stock.institutional_holders
            return holders if holders is not None and not holders.empty else None

        result = self._fetch_with_retry(fetch)
        if result is not None:
            self._set_cached(cache_key, result)
        return result

    def get_sp500_data(self, period: str = "1y") -> Optional[pd.DataFrame]:
        """Fetch S&P 500 index data for market comparison."""
        return self.get_historical_prices("^GSPC", period)

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get the current stock price."""
        info = self.get_stock_info(ticker)
        if info:
            return info.get('currentPrice') or info.get('regularMarketPrice')
        return None

    def get_52_week_high(self, ticker: str) -> Optional[float]:
        """Get 52-week high price."""
        info = self.get_stock_info(ticker)
        if info:
            return info.get('fiftyTwoWeekHigh')
        return None

    def get_50_day_avg_volume(self, ticker: str) -> Optional[float]:
        """Get 50-day average volume."""
        info = self.get_stock_info(ticker)
        if info:
            return info.get('averageVolume')
        return None

    def get_institutional_ownership_pct(self, ticker: str) -> Optional[float]:
        """Get institutional ownership percentage."""
        info = self.get_stock_info(ticker)
        if info:
            pct = info.get('heldPercentInstitutions')
            if pct is not None:
                return pct * 100  # Convert to percentage
        return None

    def get_eps_data(self, ticker: str) -> Dict[str, Any]:
        """Get EPS data for CANSLIM analysis."""
        result = {
            'quarterly_eps': [],
            'annual_eps': [],
            'ttm_eps': None
        }

        # Get trailing twelve months EPS
        info = self.get_stock_info(ticker)
        if info:
            result['ttm_eps'] = info.get('trailingEps')

        # Get quarterly EPS from financials
        quarterly = self.get_quarterly_financials(ticker)
        if quarterly is not None:
            try:
                # Try to get Net Income and Shares Outstanding to calculate EPS
                if 'Net Income' in quarterly.index:
                    net_income = quarterly.loc['Net Income']
                    result['quarterly_eps'] = net_income.dropna().tolist()[:4]  # Last 4 quarters
            except Exception:
                pass

        # Get annual EPS from financials
        annual = self.get_annual_financials(ticker)
        if annual is not None:
            try:
                if 'Net Income' in annual.index:
                    net_income = annual.loc['Net Income']
                    result['annual_eps'] = net_income.dropna().tolist()[:3]  # Last 3 years
            except Exception:
                pass

        return result

    def get_moving_average(self, ticker: str, window: int = 200) -> Optional[float]:
        """Calculate moving average for a stock."""
        history = self.get_historical_prices(ticker)
        if history is not None and len(history) >= window:
            return history['Close'].rolling(window=window).mean().iloc[-1]
        return None

    def is_valid_ticker(self, ticker: str) -> bool:
        """Check if a ticker has valid data available."""
        info = self.get_stock_info(ticker)
        if info is None:
            return False

        # Check for essential data
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        return current_price is not None


if __name__ == "__main__":
    # Test the data fetcher
    fetcher = DataFetcher()

    print("Testing DataFetcher with AAPL...")
    print(f"Current Price: {fetcher.get_current_price('AAPL')}")
    print(f"52-Week High: {fetcher.get_52_week_high('AAPL')}")
    print(f"Institutional Ownership: {fetcher.get_institutional_ownership_pct('AAPL')}%")

    history = fetcher.get_historical_prices('AAPL')
    if history is not None:
        print(f"Historical data points: {len(history)}")
