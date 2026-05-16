# -*- coding: utf-8 -*-
"""
MubasherTrade Sync - سحب البيانات من تطبيق MubasherTrade وتحديث Local DB
============================================================================
يقرأ من:
  - history.db: daily candles (open, high, low, close, volume, change%)
  - HistoricalTrade/CASE/YYYYMMDD.db: individual trades (last price, VWAP)
  - INTRADAY_MASTER.db: intraday data (fallback)

ويحدث:
  - data/egx_investment.db: stocks table + price_history tables
"""

import os
import sys
import json
import sqlite3
import glob
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger

# Paths
MUBASHER_BASE = Path("C:/Users/DELL/AppData/Roaming/MubasherTrade/PRO Egypt")
HISTORY_DB = MUBASHER_BASE / "UserData/488274428/History/CASE/history.db"
INTRADAY_DB = MUBASHER_BASE / "UserData/488274428/Intraday/CASE/INTRADAY_MASTER.db"
TRADE_DIR = MUBASHER_BASE / "UserData/488274428/HistoricalTrade/CASE"

LOCAL_DB = Path(os.path.join(os.path.dirname(__file__), "data", "egx_investment.db"))


def _get_trade_dbs() -> List[Path]:
    """Get all HistoricalTrade DBs sorted by date"""
    files = sorted(TRADE_DIR.glob("*.db"))
    return files


def _extract_ticker_tables(conn: sqlite3.Connection) -> List[str]:
    """Get all ticker tables from history.db (tables starting with _)"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '_%'")
    return [r[0] for r in cursor.fetchall()]


def _clean_ticker_name(table_name: str) -> str:
    """Convert _COMI → COMI, _EGX30 → EGX30"""
    return table_name.lstrip('_')


def _parse_history_row(row: sqlite3.Row) -> Dict:
    """Parse a row from history.db ticker table"""
    d = dict(row)
    return {
        'date': str(d.get('DATE', '')),
        'open': float(d.get('OP', 0) or 0),
        'high': float(d.get('HIG', 0) or 0),
        'low': float(d.get('LOW', 0) or 0),
        'close': float(d.get('CLS', 0) or 0),
        'volume': int(float(d.get('VOL', 0) or 0)),
        'turnover': float(d.get('TOVR', 0) or 0),
        'num_trades': int(float(d.get('NOTR', 0) or 0)),
        'vwap': float(d.get('VWAP', 0) or 0),
        'change': float(d.get('CHG', 0) or 0),
        'change_pct': float(d.get('PCHG', 0) or 0),
        'prev_close': float(d.get('PCLS', 0) or 0) if d.get('PCLS') not in (None, '-1', -1) else None,
        'last_trade_price': float(d.get('LTP', 0) or 0) if d.get('LTP') not in (None, '-1', -1) else None,
        'best_bid': float(d.get('BBP', 0) or 0) if d.get('BBP') not in (None, '-1', -1) else None,
        'best_ask': float(d.get('BAP', 0) or 0) if d.get('BAP') not in (None, '-1', -1) else None,
    }


def _get_latest_history_date(conn: sqlite3.Connection, ticker_table: str) -> Optional[str]:
    """Get latest date from history table"""
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT MAX(DATE) FROM {ticker_table}")
        row = cursor.fetchone()
        return str(row[0]) if row and row[0] else None
    except Exception as e:
        logger.warning(f"Error getting latest date for {ticker_table}: {e}")
        return None


def _get_latest_trade_for_symbol(trade_db_path: Path, symbol: str) -> Optional[Dict]:
    """Get latest trade for a symbol from HistoricalTrade DB"""
    try:
        conn = sqlite3.connect(str(trade_db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM TRADES 
            WHERE SYMBOL = ? 
            ORDER BY TRADETIME DESC 
            LIMIT 1
        """, (symbol,))
        row = cursor.fetchone()
        conn.close()
        if row:
            d = dict(row)
            return {
                'symbol': d.get('SYMBOL'),
                'trade_time': d.get('TRADETIME'),
                'price': float(d.get('TRADEPRICE', 0) or 0),
                'quantity': int(float(d.get('TRADEQUANTITY', 0) or 0)),
                'change': float(d.get('NETCHANGE', 0) or 0),
                'change_pct': float(d.get('PERCENTCHANGE', 0) or 0),
                'vwap': float(d.get('VWAP', 0) or 0) if d.get('VWAP') != '-1.0' else None,
            }
    except Exception as e:
        logger.warning(f"Error reading trade DB {trade_db_path}: {e}")
    return None


def _get_daily_summary_from_trades(trade_db_path: Path, symbol: str) -> Optional[Dict]:
    """Compute OHLCV from individual trades for a symbol"""
    try:
        conn = sqlite3.connect(str(trade_db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TRADEPRICE, TRADEQUANTITY, TRADETIME 
            FROM TRADES 
            WHERE SYMBOL = ? 
            ORDER BY TRADETIME
        """, (symbol,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return None
        
        prices = [float(r['TRADEPRICE']) for r in rows]
        volumes = [int(float(r['TRADEQUANTITY'])) for r in rows]
        
        return {
            'open': prices[0],
            'high': max(prices),
            'low': min(prices),
            'close': prices[-1],
            'volume': sum(volumes),
            'num_trades': len(rows),
        }
    except Exception as e:
        logger.warning(f"Error computing daily summary for {symbol}: {e}")
    return None


class MubasherSync:
    """Sync data from MubasherTrade to local DB"""
    
    def __init__(self):
        self.local_db_path = str(LOCAL_DB)
        self.stats = {
            'stocks_updated': 0,
            'prices_inserted': 0,
            'errors': []
        }
    
    def _get_local_conn(self):
        conn = sqlite3.connect(self.local_db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def sync_stocks_current_prices(self) -> Dict:
        """
        Sync current prices from MubasherTrade history.db to local stocks table.
        Uses the latest daily candle from history.db.
        """
        if not HISTORY_DB.exists():
            return {"error": f"history.db not found at {HISTORY_DB}"}
        
        logger.info("[MubasherSync] Starting stock price sync from history.db")
        
        # Connect to Mubasher history.db
        mubasher_conn = sqlite3.connect(str(HISTORY_DB))
        mubasher_conn.row_factory = sqlite3.Row
        
        # Get all ticker tables
        ticker_tables = _extract_ticker_tables(mubasher_conn)
        logger.info(f"[MubasherSync] Found {len(ticker_tables)} tickers in history.db")
        
        local_conn = self._get_local_conn()
        updated = 0
        skipped = 0
        errors = 0
        
        try:
            for table in ticker_tables:
                try:
                    ticker = _clean_ticker_name(table)
                    
                    # Get latest row from history
                    cursor = mubasher_conn.cursor()
                    cursor.execute(f"SELECT * FROM {table} ORDER BY DATE DESC LIMIT 1")
                    row = cursor.fetchone()
                    
                    if not row:
                        skipped += 1
                        continue
                    
                    data = _parse_history_row(row)
                    # Convert YYYYMMDD to YYYY-MM-DD
                    raw_date = data['date']
                    if raw_date and len(str(raw_date)) == 8:
                        date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
                    else:
                        date_str = raw_date
                    close_price = data['close']
                    change_pct = data['change_pct']
                    volume = data['volume']
                    high = data['high']
                    low = data['low']
                    open_price = data['open']
                    prev_close = data['prev_close'] or close_price
                    
                    # Update stocks table
                    local_conn.execute("""
                        UPDATE stocks 
                        SET current_price = ?, previous_close = ?, volume = ?,
                            high_price = ?, low_price = ?, open_price = ?,
                            last_update = ?
                        WHERE ticker = ?
                    """, (close_price, prev_close, volume, high, low, open_price,
                          datetime.now().isoformat(), ticker))
                    
                    if local_conn.total_changes > 0:
                        updated += 1
                    
                    # Also insert into price_history for technical analysis
                    local_conn.execute("""
                        INSERT OR REPLACE INTO stock_price_history 
                        (stock_id, date, open_price, high_price, low_price, close_price, volume)
                        VALUES (
                            (SELECT id FROM stocks WHERE ticker = ?),
                            ?, ?, ?, ?, ?, ?
                        )
                    """, (ticker, date_str, open_price, high, low, close_price, volume))
                    
                except Exception as e:
                    errors += 1
                    logger.warning(f"[MubasherSync] Error syncing {table}: {e}")
            
            local_conn.commit()
            
        finally:
            mubasher_conn.close()
            local_conn.close()
        
        result = {
            "success": True,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
            "source": str(HISTORY_DB),
            "latest_date": date_str if 'date_str' in dir() else None
        }
        logger.info(f"[MubasherSync] Stock sync complete: {result}")
        return result
    
    def sync_from_trade_files(self, days_back: int = 7) -> Dict:
        """
        Sync from HistoricalTrade DBs (individual trades).
        These have more recent data than history.db.
        """
        trade_dbs = _get_trade_dbs()
        if not trade_dbs:
            return {"error": "No trade DBs found"}
        
        # Take last N days
        recent_dbs = trade_dbs[-days_back:]
        logger.info(f"[MubasherSync] Processing {len(recent_dbs)} trade DBs: {[p.name for p in recent_dbs]}")
        
        local_conn = self._get_local_conn()
        total_trades = 0
        total_symbols = 0
        
        try:
            for db_path in recent_dbs:
                raw_date = db_path.stem  # YYYYMMDD
                date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if len(raw_date) == 8 else raw_date
                
                try:
                    mconn = sqlite3.connect(str(db_path))
                    mconn.row_factory = sqlite3.Row
                    mcursor = mconn.cursor()
                    
                    # Get all symbols in this DB
                    mcursor.execute("SELECT DISTINCT SYMBOL FROM TRADES")
                    symbols = [r[0] for r in mcursor.fetchall()]
                    total_symbols += len(symbols)
                    
                    for symbol in symbols:
                        # Compute daily summary from trades
                        summary = _get_daily_summary_from_trades(db_path, symbol)
                        if not summary:
                            continue
                        
                        # Update stocks table with latest close as current_price
                        local_conn.execute("""
                            UPDATE stocks 
                            SET current_price = ?, volume = ?, last_update = ?
                            WHERE ticker = ?
                        """, (summary['close'], summary['volume'], datetime.now().isoformat(), symbol))
                        
                        # Insert into price_history
                        local_conn.execute("""
                            INSERT OR REPLACE INTO stock_price_history 
                            (stock_id, date, open_price, high_price, low_price, close_price, volume)
                            VALUES (
                                (SELECT id FROM stocks WHERE ticker = ?),
                                ?, ?, ?, ?, ?, ?
                            )
                        """, (symbol, date_str, summary['open'], summary['high'],
                              summary['low'], summary['close'], summary['volume']))
                        
                        total_trades += summary['num_trades']
                    
                    mconn.close()
                    
                except Exception as e:
                    logger.warning(f"[MubasherSync] Error processing {db_path}: {e}")
            
            local_conn.commit()
            
        finally:
            local_conn.close()
        
        result = {
            "success": True,
            "trade_dbs_processed": len(recent_dbs),
            "symbols_updated": total_symbols,
            "total_trades": total_trades,
            "latest_db": recent_dbs[-1].name if recent_dbs else None
        }
        logger.info(f"[MubasherSync] Trade sync complete: {result}")
        return result
    
    def full_sync(self) -> Dict:
        """Run complete sync: history + trades"""
        logger.info("=" * 50)
        logger.info("[MubasherSync] FULL SYNC STARTING")
        logger.info("=" * 50)
        
        r1 = self.sync_stocks_current_prices()
        r2 = self.sync_from_trade_files(days_back=7)
        
        return {
            "history_sync": r1,
            "trade_sync": r2,
            "success": r1.get('success', False) and r2.get('success', False)
        }


# Singleton
mubasher_sync = MubasherSync()

if __name__ == "__main__":
    result = mubasher_sync.full_sync()
    print(json.dumps(result, indent=2, ensure_ascii=False))
