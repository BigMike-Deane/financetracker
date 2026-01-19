#!/usr/bin/env python3
"""
CANSLIM Stock Analyzer
Analyzes S&P 500 stocks using William O'Neil's CANSLIM method
and identifies the top 5 stocks with highest projected 6-month growth.
"""

import sys
from datetime import datetime
from typing import List, Tuple, Optional
from dataclasses import dataclass
from tqdm import tqdm

from sp500_tickers import get_sp500_tickers
from data_fetcher import DataFetcher
from canslim_scorer import CANSLIMScorer, CANSLIMScore
from growth_projector import GrowthProjector, GrowthProjection


@dataclass
class StockAnalysis:
    """Complete analysis for a single stock."""
    ticker: str
    name: str
    current_price: float
    canslim_score: CANSLIMScore
    growth_projection: GrowthProjection


def print_header():
    """Print the application header."""
    print("═" * 65)
    print("           CANSLIM STOCK ANALYZER - TOP 5 PICKS")
    print("═" * 65)


def print_market_status(scorer: CANSLIMScorer):
    """Print current market direction."""
    market_score, market_detail = scorer.score_market()
    if market_score >= 12:
        status = "BULLISH"
    elif market_score >= 8:
        status = "NEUTRAL"
    else:
        status = "BEARISH"
    print(f"Market Direction: {status} ({market_detail})")


def print_analysis_info(total_tickers: int, analyzed: int, skipped: int):
    """Print analysis summary."""
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Stocks Analyzed: {analyzed} / {total_tickers}")
    if skipped > 0:
        print(f"Stocks Skipped (insufficient data): {skipped}")
    print("═" * 65)


def print_stock_result(rank: int, analysis: StockAnalysis):
    """Print detailed results for a single stock."""
    score = analysis.canslim_score
    proj = analysis.growth_projection

    print(f"\n#{rank} {analysis.ticker} - {analysis.name}")
    print(f"   Current Price: ${analysis.current_price:.2f}")
    print(f"   CANSLIM Score: {score.total:.0f}/100")
    print(f"   Projected 6-Month Growth: {proj.projected_growth_pct:+.1f}%")
    print(f"   Confidence: {proj.confidence}")
    print()
    print("   Score Breakdown:")
    print(f"   ├─ C (Current Earnings):    {score.current_earnings:.0f}/15 ({score.details['C']})")
    print(f"   ├─ A (Annual Earnings):     {score.annual_earnings:.0f}/15 ({score.details['A']})")
    print(f"   ├─ N (New Highs):           {score.new_highs:.0f}/15 ({score.details['N']})")
    print(f"   ├─ S (Supply/Demand):       {score.supply_demand:.0f}/15 ({score.details['S']})")
    print(f"   ├─ L (Leader):              {score.leader:.0f}/15 ({score.details['L']})")
    print(f"   ├─ I (Institutional):       {score.institutional:.0f}/10 ({score.details['I']})")
    print(f"   └─ M (Market):              {score.market:.0f}/15 ({score.details['M']})")
    print()
    print("   Growth Projection Factors:")
    print(f"   ├─ Momentum (40%):   {proj.momentum_component:+.1f}%")
    print(f"   ├─ Earnings (30%):   {proj.earnings_component:+.1f}%")
    print(f"   ├─ CANSLIM (20%):    {proj.canslim_component:+.1f}%")
    print(f"   └─ Sector (10%):     {proj.sector_component:+.1f}%")


def print_disclaimer():
    """Print disclaimer."""
    print()
    print("═" * 65)
    print("                         DISCLAIMER")
    print("  This is for educational purposes only. Not financial advice.")
    print("  Past performance does not guarantee future results.")
    print("  Always do your own research before making investment decisions.")
    print("═" * 65)


def analyze_stocks(tickers: List[str], max_stocks: Optional[int] = None) -> Tuple[List[StockAnalysis], int, int]:
    """
    Analyze stocks and return sorted results.

    Returns:
        Tuple of (analyses, analyzed_count, skipped_count)
    """
    fetcher = DataFetcher()
    scorer = CANSLIMScorer(fetcher)
    projector = GrowthProjector(fetcher)

    analyses: List[StockAnalysis] = []
    skipped = 0

    # Limit tickers if specified
    if max_stocks:
        tickers = tickers[:max_stocks]

    print("\nAnalyzing stocks...")
    for ticker in tqdm(tickers, desc="Progress", unit="stock"):
        try:
            # Get stock info
            info = fetcher.get_stock_info(ticker)
            if info is None:
                skipped += 1
                continue

            name = info.get('shortName') or info.get('longName') or ticker
            current_price = fetcher.get_current_price(ticker)

            if current_price is None:
                skipped += 1
                continue

            # Calculate CANSLIM score
            canslim_score = scorer.calculate_score(ticker)
            if canslim_score is None:
                skipped += 1
                continue

            # Project growth
            growth_proj = projector.project_growth(ticker, canslim_score)
            if growth_proj is None:
                skipped += 1
                continue

            analyses.append(StockAnalysis(
                ticker=ticker,
                name=name[:40],  # Truncate long names
                current_price=current_price,
                canslim_score=canslim_score,
                growth_projection=growth_proj
            ))

        except Exception as e:
            skipped += 1
            continue

    # Sort by projected growth (descending)
    analyses.sort(key=lambda x: x.growth_projection.projected_growth_pct, reverse=True)

    return analyses, len(analyses), skipped


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="CANSLIM Stock Analyzer - Find top growth stocks using O'Neil's method"
    )
    parser.add_argument(
        '--top', '-t',
        type=int,
        default=5,
        help="Number of top stocks to display (default: 5)"
    )
    parser.add_argument(
        '--max-analyze', '-m',
        type=int,
        default=None,
        help="Maximum number of stocks to analyze (default: all S&P 500)"
    )
    parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help="Quick mode: analyze top 100 stocks by market cap"
    )

    args = parser.parse_args()

    # Get tickers
    print("Fetching S&P 500 ticker list...")
    tickers = get_sp500_tickers()
    print(f"Found {len(tickers)} tickers")

    # Quick mode limits to first 100 tickers
    max_analyze = args.max_analyze
    if args.quick:
        max_analyze = 100

    # Run analysis
    analyses, analyzed, skipped = analyze_stocks(tickers, max_analyze)

    if not analyses:
        print("\nNo stocks could be analyzed. Check your internet connection.")
        sys.exit(1)

    # Create scorer for market status
    fetcher = DataFetcher()
    scorer = CANSLIMScorer(fetcher)

    # Print results
    print("\n")
    print_header()
    print_market_status(scorer)
    print_analysis_info(len(tickers), analyzed, skipped)

    # Print top stocks
    top_n = min(args.top, len(analyses))
    for i, analysis in enumerate(analyses[:top_n], 1):
        print_stock_result(i, analysis)

    print_disclaimer()

    return 0


if __name__ == "__main__":
    sys.exit(main())
