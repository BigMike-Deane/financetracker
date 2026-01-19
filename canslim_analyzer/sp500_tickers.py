"""
S&P 500 Ticker Fetcher
Fetches the list of S&P 500 companies from Wikipedia or uses a fallback list.
"""

import requests
from bs4 import BeautifulSoup
from typing import List


def get_sp500_tickers() -> List[str]:
    """
    Fetch S&P 500 tickers from Wikipedia.
    Falls back to a hardcoded list if fetching fails.
    """
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'constituents'})

        if table is None:
            table = soup.find('table', {'class': 'wikitable'})

        tickers = []
        if table:
            rows = table.find_all('tr')[1:]  # Skip header row
            for row in rows:
                cells = row.find_all('td')
                if cells:
                    ticker = cells[0].text.strip()
                    # Clean up ticker (remove footnotes, etc.)
                    ticker = ticker.replace('.', '-')  # BRK.B -> BRK-B for yfinance
                    tickers.append(ticker)

        if tickers:
            return tickers
    except Exception as e:
        print(f"Warning: Could not fetch S&P 500 list from Wikipedia: {e}")

    # Fallback to hardcoded list of major S&P 500 companies
    return get_fallback_tickers()


def get_fallback_tickers() -> List[str]:
    """
    Returns a hardcoded list of major S&P 500 companies.
    This is used as a fallback if Wikipedia scraping fails.
    """
    return [
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "BRK-B", "UNH", "XOM",
        "JNJ", "JPM", "V", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "LLY",
        "PEP", "KO", "AVGO", "COST", "TMO", "MCD", "WMT", "CSCO", "ACN", "ABT",
        "DHR", "NEE", "VZ", "ADBE", "CRM", "NKE", "PM", "TXN", "UPS", "CMCSA",
        "ORCL", "RTX", "HON", "INTC", "QCOM", "T", "LOW", "BMY", "UNP", "AMD",
        "AMGN", "MS", "SPGI", "GS", "CAT", "IBM", "ELV", "DE", "BA", "SBUX",
        "PLD", "GILD", "BLK", "INTU", "MDLZ", "ADP", "ISRG", "CVS", "ADI", "REGN",
        "CI", "BKNG", "NOW", "VRTX", "TJX", "SYK", "CB", "LMT", "MMC", "TMUS",
        "ZTS", "PGR", "SCHW", "MO", "SO", "DUK", "BDX", "CME", "C", "EOG",
        "NOC", "ITW", "SLB", "CL", "BSX", "AON", "FI", "WM", "USB", "EQIX"
    ]


if __name__ == "__main__":
    tickers = get_sp500_tickers()
    print(f"Fetched {len(tickers)} S&P 500 tickers")
    print(f"First 10: {tickers[:10]}")
