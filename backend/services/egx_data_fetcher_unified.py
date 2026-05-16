#!/usr/bin/env python3
"""
EGX Data Fetcher - Unified Version for Hostinger VPS
====================================================
Fetches stock data from TradingView and updates the Next.js database.

Features:
- Reads tickers from existing Next.js database
- Fetches correct prices from TradingView (not yfinance - it's wrong for EGX)
- Updates stock prices in database
- Calculates PE ratio from price and EPS
- Runs as a background service

Usage:
    python3 egx_data_fetcher_unified.py --once     # Run once
    python3 egx_data_fetcher_unified.py --daemon   # Run as daemon (every 5 min)

Author: Z.ai
"""

import os
import sys
import json
import time
import sqlite3
import argparse
import signal
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Suppress warnings
import warnings
warnings.filterwarnings('ignore')

# Try to import TradingView
try:
    from tradingview_ta import TA_Handler, Interval
    TV_AVAILABLE = True
    print("✓ TradingView TA available")
except ImportError:
    TV_AVAILABLE = False
    print("✗ TradingView TA not available - install with: pip install tradingview-ta")

# Configuration
DATABASE_PATH = os.environ.get('DATABASE_PATH', '/home/z/invest/app/db/egx_investment.db')
BATCH_SIZE = 10  # TradingView limits - reduced to avoid rate limits
SYNC_INTERVAL = 300  # 5 minutes
RATE_LIMIT_DELAY = 2.0  # seconds between batches - increased to avoid rate limits
REQUEST_DELAY = 0.3  # seconds between individual requests

# EPS values for major EGX stocks (manually curated from company reports)
# These are approximate values - should be updated quarterly
EPS_VALUES = {
    # Banks
    "COMI": 5.77,      # Commercial International Bank
    "HRHO": 1.55,      # EFG Hermes
    "CIEB": 1.93,      # Credit Agricole
    "SAIB": 0.0,       # Saib Bank
    "ADIB": 0.0,       # Abu Dhabi Islamic Bank

    # Telecommunications
    "ETEL": 3.42,      # Telecom Egypt
    "FWRY": 0.48,      # Fawry

    # Real Estate
    "TMGH": 3.98,      # Talaat Moustafa
    "PHDC": 1.08,      # Palm Hills
    "MNHD": 3.27,      # Madinet Nasr
    "HELI": 0.34,      # Heliopolis Housing
    "ORHD": 1.21,      # Orascom Development

    # Industrial
    "ESRS": 6.28,      # Ezz Steel
    "SWDY": 2.93,      # Elsewedy Electric
    "ABUK": 7.07,      # Abu Qir Fertilizers
    "SKPC": 0.64,      # Sidi Kerir Petrochemicals

    # Food & Beverages
    "JUFO": 0.97,      # Juhayna
    "EKHO": 0.03,      # Eastern Company (approximate)

    # Construction
    "OCDI": 1.49,      # Orascom Construction
    "ORAS": 0.0,       # Orascom Construction (alternate ticker)

    # Others
    "AMER": 0.17,      # Amer Group
    "ALCN": 1.21,      # Alexandria Container
    "GTHE": 0.12,      # Global Telecom
    "ESGH": 2.69,      # Ezz Steel Rebars

    # More stocks
    "BTFH": 0.28,      # Beltone Financial
    "CCAP": 0.0,       # Citadel Capital
    "CIRA": 0.58,      # Cairo Investment
    "AMOC": 1.85,      # Alexandria Mineral Oils
    "MCQE": 0.42,      # Misr Chemical Industries
    "EMFD": 0.0,       # Egyptian Financial Group
    "EGCH": 0.0,       # Egyptian Chemicals
    "EGAS": 0.0,       # Egyptian Natural Gas
    "PORT": 0.0,       # Alexandria Port
    "EZDK": 0.0,       # Ezz Dekheila
}

# Sector mapping for stocks
SECTOR_MAP = {
    "COMI": "Financial Services", "HRHO": "Financial Services", "CIEB": "Financial Services",
    "SAIB": "Financial Services", "ADIB": "Financial Services", "BTFH": "Financial Services",
    "ETEL": "Telecommunications", "FWRY": "Technology",
    "TMGH": "Real Estate", "PHDC": "Real Estate", "MNHD": "Real Estate", "HELI": "Real Estate", "ORHD": "Real Estate",
    "ESRS": "Basic Materials", "SWDY": "Industrials", "ABUK": "Basic Materials", "SKPC": "Energy",
    "JUFO": "Consumer Defensive", "EKHO": "Consumer Defensive",
    "OCDI": "Industrials", "ORAS": "Industrials",
    "AMER": "Real Estate", "ALCN": "Industrials", "GTHE": "Communication Services",
    "ESGH": "Basic Materials", "AMOC": "Energy", "MCQE": "Basic Materials",
}


class EGXDataFetcher:
    """Fetches EGX stock data from TradingView."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.running = True
        self.stats = {
            "total_fetched": 0,
            "total_updated": 0,
            "total_errors": 0,
            "last_sync": None
        }

        # Handle shutdown signals
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum, frame):
        """Handle shutdown signals."""
        print("\nShutdown signal received. Stopping...")
        self.running = False

    def get_db_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_tickers_from_db(self) -> List[str]:
        """Get all stock tickers from the database."""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT ticker FROM stocks WHERE is_active = 1 OR is_active IS NULL")
            tickers = [row['ticker'] for row in cursor.fetchall()]
            print(f"Found {len(tickers)} tickers in database")
            return tickers
        except Exception as e:
            print(f"Error reading tickers: {e}")
            return []
        finally:
            conn.close()

    def fetch_quote(self, ticker: str) -> Optional[Dict]:
        """Fetch a single stock quote from TradingView."""
        if not TV_AVAILABLE:
            return None

        try:
            handler = TA_Handler(
                symbol=ticker,
                screener="egypt",
                exchange="EGX",
                interval=Interval.INTERVAL_1_DAY
            )
            analysis = handler.get_analysis()

            if analysis:
                indicators = analysis.indicators
                price = indicators.get('close', 0)
                prev_close = indicators.get('previous_close', price)

                change = price - prev_close if prev_close else 0
                change_pct = (change / prev_close * 100) if prev_close else 0

                # Get EPS and calculate PE ratio
                eps = EPS_VALUES.get(ticker, 0)
                pe_ratio = round(price / eps, 2) if eps > 0 else None

                return {
                    "ticker": ticker,
                    "current_price": round(price, 4) if price else None,
                    "previous_close": round(prev_close, 4) if prev_close else None,
                    "open_price": round(indicators.get('open', price), 4),
                    "high_price": round(indicators.get('high', price), 4),
                    "low_price": round(indicators.get('low', price), 4),
                    "volume": int(indicators.get('volume', 0) or 0),
                    "price_change": round(change, 4),
                    "price_change_percent": round(change_pct, 4),
                    "pe_ratio": pe_ratio,
                    "eps": eps,
                    "sector": SECTOR_MAP.get(ticker),
                    "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "source": "tradingview"
                }
        except Exception as e:
            print(f"  Error fetching {ticker}: {e}")
            return None

    def fetch_batch(self, tickers: List[str]) -> Tuple[List[Dict], List[str]]:
        """Fetch quotes for multiple tickers with rate limiting."""
        results = []
        errors = []

        print(f"Fetching {len(tickers)} stocks...")

        for i in range(0, len(tickers), BATCH_SIZE):
            batch = tickers[i:i+BATCH_SIZE]
            print(f"  Batch {i//BATCH_SIZE + 1}: {batch}")

            for ticker in batch:
                quote = self.fetch_quote(ticker)
                if quote:
                    results.append(quote)
                else:
                    errors.append(ticker)
                # Add delay between individual requests to avoid rate limiting
                time.sleep(REQUEST_DELAY)

            # Rate limiting between batches
            if i + BATCH_SIZE < len(tickers):
                print(f"    Waiting {RATE_LIMIT_DELAY}s before next batch...")
                time.sleep(RATE_LIMIT_DELAY)

        return results, errors

    def update_database(self, quotes: List[Dict]) -> int:
        """Update database with fetched quotes."""
        if not quotes:
            return 0

        conn = self.get_db_connection()
        cursor = conn.cursor()
        updated = 0

        try:
            for quote in quotes:
                cursor.execute('''
                    UPDATE stocks SET
                        current_price = ?,
                        previous_close = ?,
                        open_price = ?,
                        high_price = ?,
                        low_price = ?,
                        volume = ?,
                        pe_ratio = ?,
                        eps = ?,
                        sector = ?,
                        last_update = ?
                    WHERE ticker = ?
                ''', (
                    quote['current_price'],
                    quote['previous_close'],
                    quote['open_price'],
                    quote['high_price'],
                    quote['low_price'],
                    quote['volume'],
                    quote['pe_ratio'],
                    quote['eps'],
                    quote['sector'],
                    quote['last_update'],
                    quote['ticker']
                ))

                if cursor.rowcount > 0:
                    updated += 1

            conn.commit()
            print(f"Updated {updated} stocks in database")

        except Exception as e:
            print(f"Error updating database: {e}")
            conn.rollback()
        finally:
            conn.close()

        return updated

    def run_once(self):
        """Run fetcher once."""
        print(f"\n{'='*60}")
        print(f"EGX Data Fetcher - Starting at {datetime.now()}")
        print(f"{'='*60}")

        # Get tickers from database
        tickers = self.get_tickers_from_db()
        if not tickers:
            print("No tickers found in database!")
            return

        # Fetch quotes
        quotes, errors = self.fetch_batch(tickers)

        # Update database
        updated = self.update_database(quotes)

        # Update stats
        self.stats['total_fetched'] += len(quotes)
        self.stats['total_updated'] += updated
        self.stats['total_errors'] += len(errors)
        self.stats['last_sync'] = datetime.now().isoformat()

        print(f"\nSummary:")
        print(f"  Fetched: {len(quotes)}")
        print(f"  Updated: {updated}")
        print(f"  Errors: {len(errors)}")
        if errors:
            print(f"  Failed tickers: {errors[:10]}{'...' if len(errors) > 10 else ''}")

    def run_daemon(self):
        """Run fetcher as daemon."""
        print(f"Starting EGX Data Fetcher daemon...")
        print(f"Database: {self.db_path}")
        print(f"Sync interval: {SYNC_INTERVAL} seconds")
        print(f"Press Ctrl+C to stop\n")

        while self.running:
            try:
                self.run_once()
                print(f"\nSleeping for {SYNC_INTERVAL} seconds...")
                for _ in range(SYNC_INTERVAL):
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as e:
                print(f"Error in daemon loop: {e}")
                time.sleep(60)

        print("\nFetcher stopped.")

    def get_stats(self) -> Dict:
        """Get fetcher statistics."""
        return self.stats


def main():
    parser = argparse.ArgumentParser(description='EGX Data Fetcher')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--test', action='store_true', help='Test mode - fetch only 10 stocks')
    parser.add_argument('--db', type=str, help='Database path')
    parser.add_argument('--tickers', type=str, help='Comma-separated list of tickers to fetch')

    args = parser.parse_args()

    # Set database path
    db_path = args.db or DATABASE_PATH

    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        print("Set DATABASE_PATH environment variable or use --db option")
        sys.exit(1)

    # Create fetcher
    fetcher = EGXDataFetcher(db_path)

    # Run based on mode
    if args.test:
        # Test mode - fetch only popular stocks
        test_tickers = ["COMI", "HRHO", "ETEL", "SWDY", "TMGH", "PHDC", "ABUK", "ORHD", "HELI", "JUFO"]
        print(f"\n{'='*60}")
        print(f"EGX Data Fetcher - TEST MODE")
        print(f"{'='*60}")
        print(f"Testing with {len(test_tickers)} popular stocks")
        
        quotes, errors = fetcher.fetch_batch(test_tickers)
        updated = fetcher.update_database(quotes)
        
        print(f"\nTest Results:")
        print(f"  Fetched: {len(quotes)}")
        print(f"  Updated: {updated}")
        print(f"  Errors: {len(errors)}")
        if quotes:
            print(f"\nSample data:")
            for q in quotes[:5]:
                print(f"  {q['ticker']}: {q['current_price']} EGP (PE: {q['pe_ratio']})")
    elif args.once:
        fetcher.run_once()
    elif args.daemon:
        fetcher.run_daemon()
    else:
        # Default: run once
        fetcher.run_once()


if __name__ == "__main__":
    main()
