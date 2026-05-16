"""
Database Connection - الاتصال بقاعدة البيانات
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
import pandas as pd
from loguru import logger

from config import DB_PATH


class Database:
    """SQLite Database Handler"""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        logger.info(f"Database initialized: {db_path}")
    
    def connect(self) -> sqlite3.Connection:
        """Create database connection"""
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self._connection.row_factory = sqlite3.Row
        return self._connection
    
    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    @contextmanager
    def get_cursor(self):
        """Get database cursor with context manager"""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    def execute(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute query and return results as list of dicts"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def execute_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Execute query and return single result"""
        results = self.execute(query, params)
        return results[0] if results else None
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute insert and return last row id"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.lastrowid
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute update and return affected rows"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount


class PriceDataDB:
    """معالجة بيانات الأسعار"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_daily_prices(self, ticker: str, days: int = 365) -> pd.DataFrame:
        """الحصول على الأسعار اليومية"""
        query = """
            SELECT 
                sph.date,
                sph.open as open,
                sph.high as high,
                sph.low as low,
                sph.close as close,
                sph.volume
            FROM stock_price_history sph
            JOIN stocks s ON s.id = sph.stock_id
            WHERE s.ticker = ?
            ORDER BY sph.date DESC
            LIMIT ?
        """
        results = self.db.execute(query, (ticker, days))
        
        if not results:
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df = df.set_index('date')
        
        return df
    
    def get_all_tickers(self) -> List[str]:
        """الحصول على كل الأسهم"""
        query = "SELECT ticker FROM stocks WHERE is_active = 1 ORDER BY ticker"
        results = self.db.execute(query)
        return [r['ticker'] for r in results]
    
    def get_latest_prices(self) -> pd.DataFrame:
        """الحصول على آخر أسعار لكل الأسهم"""
        query = """
            SELECT 
                s.ticker,
                s.current_price as price,
                s.volume,
                s.last_update as date
            FROM stocks s
            WHERE s.is_active = 1
        """
        results = self.db.execute(query)
        return pd.DataFrame(results)


class OptimizedParamsDB:
    """معالجة البارامترات المحسنة"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_active_params(self) -> Optional[Dict]:
        """الحصول على البارامترات الفعالة"""
        query = """
            SELECT * FROM OptimizedParameters
            WHERE is_active = 1
            ORDER BY win_rate DESC
            LIMIT 1
        """
        return self.db.execute_one(query)
    
    def save_params(self, params: Dict) -> int:
        """حفظ بارامترات جديدة"""
        query = """
            INSERT INTO OptimizedParameters (
                id, name, win_rate, total_trades,
                rsi_oversold, rsi_overbought, rsi_weight,
                macd_weight, ma_weight, bollinger_weight,
                stop_loss_min, stop_loss_max, target_multiplier,
                confidence_threshold, min_indicators_agree, volume_weight,
                is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
        """
        return self.db.execute_insert(query, (
            params['id'],
            params['name'],
            params['win_rate'],
            params['total_trades'],
            params['rsi_oversold'],
            params['rsi_overbought'],
            params['rsi_weight'],
            params['macd_weight'],
            params['ma_weight'],
            params['bollinger_weight'],
            params['stop_loss_min'],
            params['stop_loss_max'],
            params['target_multiplier'],
            params['confidence_threshold'],
            params['min_indicators_agree'],
            params['volume_weight']
        ))
    
    def get_all_params(self) -> List[Dict]:
        """الحصول على كل البارامترات"""
        query = """
            SELECT * FROM OptimizedParameters
            ORDER BY win_rate DESC
        """
        return self.db.execute(query)


# Global database instance
db = Database()
price_db = PriceDataDB(db)
params_db = OptimizedParamsDB(db)
