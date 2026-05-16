# -*- coding: utf-8 -*-
"""
TradingView EGX Sync — سحب بيانات الأسهم المصرية من TradingView
===============================================================
بديل Yahoo Finance — بيانات EGX الحقيقية من TradingView (مجاني)

Features:
- Fetches all active EGX stocks from TradingView
- Updates stocks table with current prices, OHLCV
- Inserts into stock_price_history for technical analysis
- Rate-limited to avoid blocks (2s between batches)
"""

import os
import sys
import time
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from loguru import logger

# Try to import TradingView
try:
    from tradingview_ta import TA_Handler, Interval
    TV_AVAILABLE = True
except ImportError:
    TV_AVAILABLE = False
    logger.error("tradingview-ta not installed. Run: pip install tradingview-ta")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "egx_investment.db")

# EPS values for PE ratio calculation
EPS_VALUES = {
    "COMI": 5.77, "HRHO": 1.55, "CIEB": 1.93, "SAIB": 0.0, "ADIB": 0.0,
    "ETEL": 3.42, "FWRY": 0.48, "TMGH": 3.98, "PHDC": 1.08, "MNHD": 3.27,
    "HELI": 0.34, "ORHD": 1.21, "ESRS": 6.28, "SWDY": 2.93, "ABUK": 7.07,
    "SKPC": 0.64, "JUFO": 0.97, "EKHO": 0.03, "OCDI": 1.49, "ORAS": 0.0,
    "AMER": 0.17, "ALCN": 1.21, "GTHE": 0.12, "ESGH": 2.69, "BTFH": 0.28,
    "CCAP": 0.0, "CIRA": 0.58, "AMOC": 1.85, "MCQE": 0.42, "EMFD": 0.0,
    "EGCH": 0.0, "EGAS": 0.0, "PORT": 0.0, "EZDK": 0.0,
}

BATCH_SIZE = 10
REQUEST_DELAY = 0.3
RATE_LIMIT_DELAY = 2.0


class TradingViewEGXSync:
    """Sync EGX stock data from TradingView"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.stats = {"fetched": 0, "updated": 0, "history_inserted": 0, "errors": []}

    def get_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def get_tickers(self) -> List[str]:
        """Get all stock tickers from database"""
        conn = self.get_db()
        try:
            rows = conn.execute(
                "SELECT ticker FROM stocks WHERE is_active = 1 OR is_active IS NULL"
            ).fetchall()
            return [r["ticker"] for r in rows]
        finally:
            conn.close()

    def fetch_quote(self, ticker: str) -> Optional[Dict]:
        """Fetch single stock from TradingView"""
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

            if not analysis or not analysis.indicators:
                return None

            ind = analysis.indicators
            price = ind.get("close", 0)
            prev = ind.get("previous_close", price) or price
            open_p = ind.get("open", price) or price
            high = ind.get("high", price) or price
            low = ind.get("low", price) or price
            vol = int(ind.get("volume", 0) or 0)

            change = price - prev if prev else 0
            change_pct = (change / prev * 100) if prev else 0

            eps = EPS_VALUES.get(ticker, 0)
            pe = round(price / eps, 2) if eps > 0 else None

            return {
                "ticker": ticker,
                "current_price": round(price, 4) if price else None,
                "previous_close": round(prev, 4) if prev else None,
                "open_price": round(open_p, 4),
                "high_price": round(high, 4),
                "low_price": round(low, 4),
                "volume": vol,
                "change": round(change, 4),
                "change_percent": round(change_pct, 4),
                "pe_ratio": pe,
                "eps": eps,
                "source": "tradingview",
                "fetched_at": datetime.now().isoformat(),
            }
        except Exception as e:
            self.stats["errors"].append(f"{ticker}: {str(e)}")
            return None

    def fetch_batch(self, tickers: List[str]) -> Tuple[List[Dict], List[str]]:
        """Fetch multiple tickers with rate limiting"""
        results = []
        errors = []

        logger.info(f"[TradingView] Fetching {len(tickers)} stocks...")

        for i in range(0, len(tickers), BATCH_SIZE):
            batch = tickers[i:i + BATCH_SIZE]
            logger.info(f"  Batch {i//BATCH_SIZE + 1}: {batch}")

            for ticker in batch:
                quote = self.fetch_quote(ticker)
                if quote:
                    results.append(quote)
                else:
                    errors.append(ticker)
                time.sleep(REQUEST_DELAY)

            if i + BATCH_SIZE < len(tickers):
                time.sleep(RATE_LIMIT_DELAY)

        return results, errors

    def update_database(self, quotes: List[Dict]) -> Dict:
        """Update stocks + insert history"""
        if not quotes:
            return {"updated": 0, "history": 0}

        conn = self.get_db()
        today = datetime.now().strftime("%Y-%m-%d")
        updated = 0
        history_inserted = 0

        try:
            for q in quotes:
                # Update stocks table (only columns that exist)
                conn.execute("""
                    UPDATE stocks SET
                        current_price = ?,
                        previous_close = ?,
                        open_price = ?,
                        high_price = ?,
                        low_price = ?,
                        volume = ?,
                        pe_ratio = ?,
                        last_update = datetime('now')
                    WHERE ticker = ?
                """, (
                    q["current_price"], q["previous_close"], q["open_price"],
                    q["high_price"], q["low_price"], q["volume"],
                    q["pe_ratio"], q["ticker"]
                ))
                if conn.total_changes > 0:
                    updated += 1

                # Insert into stock_price_history
                # Get stock_id first
                row = conn.execute("SELECT id FROM stocks WHERE ticker = ?", (q["ticker"],)).fetchone()
                if row:
                    stock_id = row["id"]
                    conn.execute("""
                        INSERT OR REPLACE INTO stock_price_history
                        (stock_id, date, open_price, high_price, low_price, close_price, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        stock_id, today, q["open_price"], q["high_price"],
                        q["low_price"], q["current_price"], q["volume"]
                    ))
                    history_inserted += 1

            conn.commit()
        except Exception as e:
            logger.error(f"[TradingView] DB error: {e}")
            conn.rollback()
        finally:
            conn.close()

        return {"updated": updated, "history": history_inserted}

    def sync(self, tickers: List[str] = None, test_mode: bool = False) -> Dict:
        """Main sync function"""
        if not TV_AVAILABLE:
            return {"success": False, "error": "tradingview-ta not installed"}

        if test_mode:
            tickers = ["COMI", "HRHO", "ETEL", "SWDY", "TMGH", "PHDC", "ABUK", "ORHD", "HELI", "JUFO"]
        elif not tickers:
            tickers = self.get_tickers()

        if not tickers:
            return {"success": False, "error": "No tickers found"}

        logger.info(f"[TradingView] Starting sync for {len(tickers)} tickers")
        start = datetime.now()

        quotes, errors = self.fetch_batch(tickers)
        db_result = self.update_database(quotes)

        elapsed = (datetime.now() - start).total_seconds()

        self.stats["fetched"] += len(quotes)
        self.stats["updated"] += db_result["updated"]
        self.stats["history_inserted"] += db_result["history"]

        return {
            "success": True,
            "tickers_total": len(tickers),
            "fetched": len(quotes),
            "updated": db_result["updated"],
            "history_inserted": db_result["history"],
            "errors": len(errors),
            "error_tickers": errors[:10],
            "elapsed_seconds": round(elapsed, 2),
        }


# Singleton
tv_sync = TradingViewEGXSync()


def sync_tradingview(tickers: List[str] = None, test_mode: bool = False) -> Dict:
    """Convenience function"""
    return tv_sync.sync(tickers=tickers, test_mode=test_mode)


if __name__ == "__main__":
    import json
    result = sync_tradingview(test_mode=True)
    print(json.dumps(result, indent=2, ensure_ascii=False))
