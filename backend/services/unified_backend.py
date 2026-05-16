# -*- coding: utf-8 -*-
"""
Unified Python Backend for EGX Investment Platform
====================================================
الـ Backend الموحد لمنصة الاستثمار المصرية

This is the MAIN backend that handles EVERYTHING:
- Stock data & prices
- Technical analysis
- AI/ML predictions
- Recommendations
- Backtesting
- User data (watchlists, portfolio)
- Market data
- Deep learning

Architecture:
    Next.js (Frontend) --> Python FastAPI (This Backend) --> SQLite Database

Author: Z.ai
Version: 3.2.0 - Added Crypto, Gold History, Currency features
"""

import os
import sys
import json
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

import aiohttp
from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks, Request
from data_engine import data_engine
from backtest_engine import backtest_engine, STRATEGIES
from mubasher_sync import mubasher_sync
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from pydantic import BaseModel, Field
import numpy as np
import pandas as pd
from loguru import logger

# ============================================================
# Configuration
# ============================================================
VERSION = "3.2.0"
PORT = int(os.getenv("PORT", 8010))
HOST = os.getenv("HOST", "0.0.0.0")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Database paths
LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "egx_investment.db")
VPS_DB_PATH = "/root/GLMinvestment/db/egx_investment.db"
DB_PATH = VPS_DB_PATH if os.path.exists(VPS_DB_PATH) else LOCAL_DB_PATH

# Models directory
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z'
)

# ============================================================
# Database Connection
# ============================================================
class DatabaseManager:
    """مدير قاعدة البيانات"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """الحصول على اتصال قاعدة البيانات"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """تنفيذ استعلام وإرجاع النتائج"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def execute_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """تنفيذ استعلام وإرجاع نتيجة واحدة"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
        finally:
            conn.close()
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """تنفيذ إدراج وإرجاع ID"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """تنفيذ تحديث وإرجاع عدد الصفوف"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

db = DatabaseManager()

# ============================================================
# Technical Analysis
# ============================================================
class TechnicalAnalysis:
    """التحليل الفني"""
    
    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """RSI"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """MACD"""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': macd_line - signal_line
        }
    
    @staticmethod
    def calculate_sma(series: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return series.rolling(window=period).mean()
    
    @staticmethod
    def calculate_ema(series: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return series.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_bollinger(series: pd.Series, period: int = 20, std_dev: float = 2) -> Dict:
        """Bollinger Bands"""
        sma = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        return {
            'upper': sma + (std * std_dev),
            'middle': sma,
            'lower': sma - (std * std_dev),
            'bandwidth': ((sma + std * std_dev) - (sma - std * std_dev)) / sma * 100
        }
    
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()
    
    @staticmethod
    def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                             k_period: int = 14, d_period: int = 3) -> Dict:
        """Stochastic Oscillator"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()
        return {'k': k, 'd': d}
    
    @staticmethod
    def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Dict:
        """Average Directional Index (ADX)"""
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr1 = high - low
        tr2 = np.abs(high - close.shift())
        tr3 = np.abs(low - close.shift())
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        return {'adx': adx, 'plus_di': plus_di, 'minus_di': minus_di}
    
    @staticmethod
    def detect_support_resistance(series: pd.Series, window: int = 20) -> Dict:
        """Detect support and resistance levels"""
        rolling_min = series.rolling(window=window).min()
        rolling_max = series.rolling(window=window).max()
        return {
            'support': round(rolling_min.iloc[-1], 2) if not pd.isna(rolling_min.iloc[-1]) else None,
            'resistance': round(rolling_max.iloc[-1], 2) if not pd.isna(rolling_max.iloc[-1]) else None
        }
    
    @staticmethod
    def calculate_fibonacci_retracement(high: float, low: float) -> Dict:
        """Calculate Fibonacci retracement levels"""
        diff = high - low
        return {
            '0.0': round(high, 2),
            '0.236': round(high - diff * 0.236, 2),
            '0.382': round(high - diff * 0.382, 2),
            '0.5': round(high - diff * 0.5, 2),
            '0.618': round(high - diff * 0.618, 2),
            '1.0': round(low, 2)
        }

# ============================================================
# Lifespan
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"🚀 Unified Python Backend v{VERSION} starting...")
    logger.info(f"📊 Database: {DB_PATH}")
    logger.info(f"🔧 Host: {HOST}:{PORT}")
    logger.info("=" * 60)
    yield
    logger.info("🛑 Unified Python Backend shutting down.")

# ============================================================
# FastAPI App
# ============================================================
app = FastAPI(
    title="EGX Unified Backend",
    description="الـ Backend الموحد لمنصة الاستثمار المصرية - كل شيء في مكان واحد",
    version=VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Frontend API Aliases (compat with main.py endpoints)
from frontend_api_aliases import router as frontend_router
# Static Files (Vanilla JS frontend)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def serve_index():
    return FileResponse("app/static/index.html")

# ============================================================
# Health Check
# ============================================================
@app.get("/")
async def root():
    return {
        "service": "EGX Unified Backend",
        "version": VERSION,
        "status": "running",
        "database": DB_PATH,
        "features": [
            "stocks",
            "prices",
            "technical_analysis",
            "recommendations",
            "deep_learning",
            "backtesting",
            "market_data"
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Check database
        db.execute_one("SELECT 1")
        db_status = "connected"
        stock_count = db.execute_one("SELECT COUNT(*) as count FROM stocks")['count']
        history_count = db.execute_one("SELECT COUNT(*) as count FROM stock_price_history")['count']
    except Exception as e:
        db_status = f"error: {str(e)}"
        stock_count = 0
        history_count = 0
    
    return {
        "status": "healthy",
        "version": VERSION,
        "database": db_status,
        "stock_count": stock_count,
        "history_count": history_count,
        "timestamp": datetime.now().isoformat()
    }

# ============================================================
# STOCKS ENDPOINTS
# ============================================================
@app.get("/api/stocks")
async def get_all_stocks(
    sector: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """الحصول على قائمة جميع الأسهم"""
    try:
        query = """
            SELECT ticker, name, name_ar, sector, current_price, previous_close,
                   open_price, high_price, low_price, volume, market_cap, pe_ratio, pb_ratio,
                   egx30_member, egx70_member, egx100_member
            FROM stocks
            WHERE is_active = 1
        """
        params = []
        
        if sector:
            query += " AND sector = ?"
            params.append(sector)
        
        query += " ORDER BY ticker LIMIT ?"
        params.append(limit)
        
        stocks = db.execute_query(query, tuple(params))
        
        # Calculate change and change_percent
        for stock in stocks:
            if stock.get('current_price') and stock.get('previous_close'):
                stock['change'] = stock['current_price'] - stock['previous_close']
                if stock['previous_close'] > 0:
                    stock['change_percent'] = (stock['change'] / stock['previous_close']) * 100
                else:
                    stock['change_percent'] = 0
            else:
                stock['change'] = 0
                stock['change_percent'] = 0
        
        # Return in format expected by frontend
        return {
            "success": True, 
            "count": len(stocks), 
            "data": stocks,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting stocks: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/stocks/all")
async def get_all_stocks_vps(
    limit: int = Query(1000, ge=1, le=5000)
):
    """Get all stocks - VPS adapter compatible format (MUST be before /{symbol})"""
    try:
        stocks = db.execute_query("""
            SELECT ticker as symbol, name, name_ar, sector, 
                   current_price, previous_close,
                   open_price as open, high_price as high, low_price as low, 
                   volume, market_cap, pe_ratio, pb_ratio
            FROM stocks
            WHERE is_active = 1 AND current_price IS NOT NULL
            ORDER BY ticker
            LIMIT ?
        """, (limit,))
        
        # Calculate change and change_percent in VPS format
        for stock in stocks:
            if stock.get('current_price') and stock.get('previous_close') and stock['previous_close'] > 0:
                stock['change_amount'] = stock['current_price'] - stock['previous_close']
                stock['change_percent'] = (stock['change_amount'] / stock['previous_close']) * 100
            else:
                stock['change_amount'] = 0
                stock['change_percent'] = 0
        
        return {
            "success": True,
            "count": len(stocks),
            "total_in_database": len(stocks),
            "data": stocks,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting all stocks: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/stocks/{symbol}")
async def get_stock(symbol: str):
    """الحصول على بيانات سهم محدد"""
    try:
        stock = db.execute_one("""
            SELECT ticker, name, name_ar, sector, current_price, previous_close,
                   open_price, high_price, low_price, volume, market_cap, pe_ratio, pb_ratio,
                   dividend_yield, eps, roe, rsi, ma_50, ma_200, support_level, resistance_level,
                   egx30_member, egx70_member, egx100_member, is_halal, compliance_status,
                   last_update
            FROM stocks
            WHERE ticker = ? AND is_active = 1
        """, (symbol.upper(),))
        
        if not stock:
            return {"success": False, "error": f"Stock {symbol} not found"}
        
        # Calculate changes
        if stock.get('current_price') and stock.get('previous_close'):
            stock['change'] = stock['current_price'] - stock['previous_close']
            if stock['previous_close'] > 0:
                stock['change_percent'] = (stock['change'] / stock['previous_close']) * 100
            else:
                stock['change_percent'] = 0
        else:
            stock['change'] = 0
            stock['change_percent'] = 0
        
        # Return in format expected by frontend: { success: true, data: {...} }
        return {"success": True, "data": stock}
    
    except Exception as e:
        logger.error(f"Error getting stock {symbol}: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/stocks/{symbol}/history")
async def get_stock_history(
    symbol: str,
    days: int = Query(365, ge=1, le=1000)
):
    """الحصول على السجل التاريخي لسهم"""
    return await _get_history_internal(symbol, days)

@app.get("/api/history/{ticker}")
async def get_history_alias(
    ticker: str,
    days: int = Query(365, ge=1, le=1000)
):
    """Alias for /api/stocks/{symbol}/history - for VPS client compatibility"""
    return await _get_history_internal(ticker, days)

async def _get_history_internal(symbol: str, days: int):
    """Internal function to get stock history"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_str = start_date.strftime("%Y-%m-%d")
        
        history = db.execute_query("""
            SELECT sph.date, sph.open_price as open, sph.high_price as high, 
                   sph.low_price as low, sph.close_price as close, sph.volume, s.ticker
            FROM stock_price_history sph
            JOIN stocks s ON s.id = sph.stock_id
            WHERE s.ticker = ? AND sph.date >= ?
            ORDER BY sph.date ASC
        """, (symbol.upper(), start_str))
        
        if not history:
            return {
                "success": False, 
                "error": f"No history found for {symbol}",
                "data": {
                    "ticker": symbol.upper(),
                    "count": 0,
                    "history": []
                }
            }
        
        return {
            "success": True,
            "data": {
                "ticker": symbol.upper(),
                "count": len(history),
                "history": history
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting history for {symbol}: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/stocks/{symbol}/local-history")
async def get_stock_local_history(
    symbol: str,
    days: int = Query(365, ge=1, le=1000)
):
    """
    الحصول على السجل التاريخي لسهم - للـ Backtesting
    Same as /history but returns flat format for backtesting engine compatibility
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_str = start_date.strftime("%Y-%m-%d")
        
        history = db.execute_query("""
            SELECT sph.date, sph.open_price as open, sph.high_price as high, 
                   sph.low_price as low, sph.close_price as close, sph.volume
            FROM stock_price_history sph
            JOIN stocks s ON s.id = sph.stock_id
            WHERE s.ticker = ? AND sph.date >= ?
            ORDER BY sph.date ASC
        """, (symbol.upper(), start_str))
        
        if not history:
            return {"success": False, "error": f"No history found for {symbol}", "history": []}
        
        # Clean data - replace None values
        cleaned_history = []
        for h in history:
            cleaned_history.append({
                'date': h['date'],
                'open': h['open'] or h['close'] or 0,
                'high': h['high'] or h['close'] or 0,
                'low': h['low'] or h['close'] or 0,
                'close': h['close'] or 0,
                'volume': h['volume'] or 0
            })
        
        return {
            "success": True,
            "ticker": symbol.upper(),
            "count": len(cleaned_history),
            "history": cleaned_history
        }
    
    except Exception as e:
        logger.error(f"Error getting local history for {symbol}: {e}")
        return {"success": False, "error": str(e), "history": []}

@app.get("/api/tickers")
async def get_all_tickers():
    """الحصول على قائمة كل التكرات - للـ Backtesting"""
    try:
        stocks = db.execute_query("""
            SELECT ticker, name, sector
            FROM stocks
            WHERE is_active = 1
            ORDER BY ticker
        """)
        
        tickers = [s['ticker'] for s in stocks]
        
        return {
            "success": True,
            "count": len(tickers),
            "tickers": tickers,
            "stocks": stocks
        }
    
    except Exception as e:
        logger.error(f"Error getting tickers: {e}")
        return {"success": False, "error": str(e), "tickers": []}

# ============================================================
# STOCK UPDATE ENDPOINTS (for Mubasher Sync)
# ============================================================

class StockUpdateRequest(BaseModel):
    """طلب تحديث بيانات سهم"""
    ticker: str
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    volume: Optional[float] = None
    last_update: Optional[str] = None


class IndicatorsUpdateRequest(BaseModel):
    """طلب تحديث المؤشرات الفنية"""
    rsi: Optional[float] = None
    rsi_signal: Optional[str] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    macd_trend: Optional[str] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    overall_signal: Optional[str] = None
    calculated_at: Optional[str] = None


@app.post("/api/stocks/{symbol}")
async def update_stock(symbol: str, data: StockUpdateRequest):
    """تحديث بيانات سهم - للاستخدام مع Mubasher Sync"""
    try:
        ticker = symbol.upper()
        
        # Check if stock exists
        existing = db.execute_one(
            "SELECT id, ticker FROM stocks WHERE ticker = ?", 
            (ticker,)
        )
        
        if existing:
            # Update existing stock
            update_fields = []
            params = []
            
            if data.current_price is not None:
                update_fields.append("current_price = ?")
                params.append(data.current_price)
            if data.previous_close is not None:
                update_fields.append("previous_close = ?")
                params.append(data.previous_close)
            if data.open_price is not None:
                update_fields.append("open_price = ?")
                params.append(data.open_price)
            if data.high_price is not None:
                update_fields.append("high_price = ?")
                params.append(data.high_price)
            if data.low_price is not None:
                update_fields.append("low_price = ?")
                params.append(data.low_price)
            if data.volume is not None:
                update_fields.append("volume = ?")
                params.append(data.volume)
            if data.last_update is not None:
                update_fields.append("last_update = ?")
                params.append(data.last_update)
            
            if update_fields:
                params.append(ticker)
                query = f"UPDATE stocks SET {', '.join(update_fields)} WHERE ticker = ?"
                db.execute_update(query, tuple(params))
            
            return {"success": True, "message": f"Updated {ticker}", "action": "updated"}
        
        else:
            # Insert new stock
            db.execute_insert("""
                INSERT INTO stocks (ticker, name, current_price, previous_close, 
                                   open_price, high_price, low_price, volume, 
                                   last_update, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                ticker, 
                data.ticker, 
                data.current_price, 
                data.previous_close,
                data.open_price, 
                data.high_price, 
                data.low_price, 
                data.volume,
                data.last_update
            ))
            
            return {"success": True, "message": f"Created {ticker}", "action": "created"}
    
    except Exception as e:
        logger.error(f"Error updating stock {symbol}: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/indicators/{symbol}")
async def update_indicators(symbol: str, data: IndicatorsUpdateRequest):
    """تحديث المؤشرات الفنية لسهم"""
    try:
        ticker = symbol.upper()
        
        # Check if stock exists
        existing = db.execute_one(
            "SELECT id FROM stocks WHERE ticker = ?", 
            (ticker,)
        )
        
        if not existing:
            return {"success": False, "error": f"Stock {ticker} not found"}
        
        # Update indicators
        update_fields = []
        params = []
        
        if data.rsi is not None:
            update_fields.append("rsi = ?")
            params.append(data.rsi)
        if data.sma_20 is not None:
            update_fields.append("ma_20 = ?")
            params.append(data.sma_20)
        if data.sma_50 is not None:
            update_fields.append("ma_50 = ?")
            params.append(data.sma_50)
        
        if update_fields:
            params.append(ticker)
            query = f"UPDATE stocks SET {', '.join(update_fields)} WHERE ticker = ?"
            db.execute_update(query, tuple(params))
        
        return {"success": True, "message": f"Updated indicators for {ticker}"}
    
    except Exception as e:
        logger.error(f"Error updating indicators for {symbol}: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/history/batch")
async def add_history_batch(history_data: List[Dict]):
    """إضافة سجل تاريخي متعدد - للاستخدام مع Mubasher Sync"""
    try:
        added = 0
        updated = 0
        
        for item in history_data:
            ticker = item.get('ticker', '').upper()
            if not ticker:
                continue
            
            # Get stock id
            stock = db.execute_one(
                "SELECT id FROM stocks WHERE ticker = ?", 
                (ticker,)
            )
            
            if not stock:
                continue
            
            stock_id = stock['id']
            date = item.get('date')
            close = item.get('close')
            
            if not date or close is None:
                continue
            
            # Check if record exists
            existing = db.execute_one("""
                SELECT id FROM stock_price_history 
                WHERE stock_id = ? AND date = ?
            """, (stock_id, date))
            
            if existing:
                # Update
                db.execute_update("""
                    UPDATE stock_price_history 
                    SET open_price = ?, high_price = ?, low_price = ?, 
                        close_price = ?, volume = ?
                    WHERE stock_id = ? AND date = ?
                """, (
                    item.get('open', close),
                    item.get('high', close),
                    item.get('low', close),
                    close,
                    item.get('volume', 0),
                    stock_id,
                    date
                ))
                updated += 1
            else:
                # Insert
                db.execute_insert("""
                    INSERT INTO stock_price_history 
                    (stock_id, date, open_price, high_price, low_price, close_price, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    stock_id,
                    date,
                    item.get('open', close),
                    item.get('high', close),
                    item.get('low', close),
                    close,
                    item.get('volume', 0)
                ))
                added += 1
        
        return {
            "success": True,
            "added": added,
            "updated": updated,
            "total": added + updated
        }
    
    except Exception as e:
        logger.error(f"Error adding history batch: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# TECHNICAL ANALYSIS ENDPOINTS
# ============================================================
@app.get("/api/analysis/{symbol}")
async def analyze_stock(symbol: str, days: int = Query(365, ge=30, le=1000)):
    """تحليل فني شامل لسهم - من PRE-COMPUTED Data Engine (INSTANT)"""
    try:
        # Get PRE-COMPUTED signal
        sig = data_engine.get_stock_signals(symbol.upper())
        
        if not sig:
            return {"success": False, "error": f"No pre-computed data for {symbol}. Run /api/engine/run-pipeline first."}
        
        # Build analysis from pre-computed data
        analysis = {
            'sma_20': sig.get('sma_20'),
            'sma_50': sig.get('sma_50'),
            'ema_12': sig.get('ema_12'),
            'ema_26': sig.get('ema_26'),
            'rsi': sig.get('rsi'),
            'macd': sig.get('macd'),
            'macd_signal': sig.get('macd_signal'),
            'bb_upper': sig.get('bb_upper'),
            'bb_lower': sig.get('bb_lower'),
            'atr': sig.get('atr'),
            'stoch_k': sig.get('stoch_k'),
            'current_price': sig.get('current_price'),
        }
        
        # Build signals from pre-computed reasons
        signals = []
        for reason in sig.get('reasons', []):
            signals.append({"indicator": "combined", "signal": "info", "value": reason})
        
        return {
            "success": True,
            "symbol": symbol.upper(),
            "analysis": _convert_numpy(analysis),
            "signals": signals,
            "trend": sig.get('trend', 'neutral'),
            "action": sig.get('action', 'HOLD'),
            "confidence": sig.get('confidence', 50),
            "precomputed": True
        }
    
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        return {"success": False, "error": str(e)}

# ============================================================
# RECOMMENDATIONS ENDPOINTS
# ============================================================
@app.get("/api/recommendations")
async def get_recommendations(
    limit: int = Query(20, ge=1, le=100),
    action: Optional[str] = None
):
    """Get recommendations from PRE-COMPUTED Data Engine (INSTANT)"""
    try:
        # Use pre-computed indicators - FAST
        recs = data_engine.get_all_signals(action=action, min_confidence=0)
        
        # Sort by confidence desc
        recs.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        recs = recs[:limit]
        
        # Enrich with stock names
        recommendations = []
        for r in recs:
            stock = db.execute_one("SELECT name, current_price, sector FROM stocks WHERE ticker = ?", (r['ticker'],))
            recommendations.append({
                "ticker": r['ticker'],
                "name": stock['name'] if stock else r['ticker'],
                "current_price": stock['current_price'] if stock else None,
                "action": (r['action'] or 'HOLD').lower(),
                "confidence": r['confidence'],
                "rsi": r['rsi'],
                "score": r['score'],
                "trend": r['trend'],
                "volatility": r['volatility'],
                "sector": stock['sector'] if stock else None,
                "reasons": r.get('reasons', []),
                "computed_at": r.get('computed_at')
            })
        
        return {"success": True, "count": len(recommendations), "recommendations": recommendations}
    
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/recommendations/{symbol}")
async def get_stock_recommendation(symbol: str):
    """Get recommendation for ONE stock from PRE-COMPUTED data (INSTANT)"""
    try:
        # Get stock info
        stock = db.execute_one("""
            SELECT ticker, name, current_price, previous_close, sector
            FROM stocks
            WHERE ticker = ? AND is_active = 1
        """, (symbol.upper(),))
        
        if not stock:
            return {"success": False, "error": f"Stock {symbol} not found"}
        
        # Get PRE-COMPUTED signal
        sig = data_engine.get_stock_signals(symbol.upper())
        
        if not sig:
            return {"success": False, "error": f"No pre-computed data for {symbol}. Run engine first."}
        
        action = (sig['action'] or 'HOLD').lower()
        current_price = stock['current_price'] or 0
        atr = sig.get('atr') or (current_price * 0.02)
        
        if action == "buy":
            entry = current_price
            stop_loss = current_price - (atr * 2)
            target = current_price + (atr * 3)
        elif action == "sell":
            entry = current_price
            stop_loss = current_price + (atr * 2)
            target = current_price - (atr * 3)
        else:
            entry = None
            stop_loss = None
            target = None
        
        return {
            "success": True,
            "ticker": stock['ticker'],
            "name": stock['name'],
            "current_price": current_price,
            "action": action,
            "confidence": sig.get('confidence', 50),
            "entry_price": round(entry, 2) if entry else None,
            "stop_loss": round(stop_loss, 2) if stop_loss else None,
            "target": round(target, 2) if target else None,
            "trend": sig.get('trend', 'neutral'),
            "reasons": sig.get('reasons', []),
            "indicators": {
                "rsi": round(sig.get('rsi', 0), 2) if sig.get('rsi') else None,
                "macd": round(sig.get('macd', 0), 4) if sig.get('macd') else None,
                "sma_20": round(sig.get('sma_20', 0), 2) if sig.get('sma_20') else None,
                "sma_50": round(sig.get('sma_50', 0), 2) if sig.get('sma_50') else None
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting recommendation for {symbol}: {e}")
        return {"success": False, "error": str(e)}

# ============================================================
# MORNING REPORT
# ============================================================
def _generate_morning_report_sync(limit: int = 10, asset_type: Optional[str] = None) -> dict:
    """Synchronous helper to generate morning report (used by push functions)"""
    try:
        signals = data_engine.get_all_signals(action="BUY", min_confidence=60, asset_type=asset_type)
        signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        signals = signals[:limit]
        
        day_name_ar = {
            'Saturday': 'السبت', 'Sunday': 'الأحد', 'Monday': 'الاثنين',
            'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء',
            'Thursday': 'الخميس', 'Friday': 'الجمعة'
        }
        today_ar = day_name_ar.get(datetime.now().strftime("%A"), datetime.now().strftime("%A"))
        date_str = datetime.now().strftime("%d-%m-%Y").lstrip('0').replace('-0', '-')
        
        header = f"*التحليل اليومي*\nمتابعة فنية لجلسة {today_ar} {date_str} — للأغراض التعليمية فقط"
        
        recommendations = []
        for idx, sig in enumerate(signals, 1):
            ticker = sig['ticker']
            stock = db.execute_one("SELECT name, current_price FROM stocks WHERE ticker = ?", (ticker,))
            name = stock['name'] if stock else ticker
            cp_from_stock = stock.get('current_price') if stock else None
            cp_from_sig = sig.get('current_price')
            current_price = cp_from_sig if cp_from_sig else cp_from_stock
            
            entry_low = sig.get('entry_zone_low')
            entry_high = sig.get('entry_zone_high')
            entry_trigger = sig.get('entry_trigger')
            support = sig.get('support_level')
            target_1 = sig.get('target_1')
            target_2 = sig.get('target_2')
            inv_target = sig.get('investment_target')
            stop_loss = sig.get('stop_loss')
            exp_return = sig.get('expected_return_pct')
            
            conf = sig.get('confidence', 0)
            lines = []
            lines.append(f"{idx}- *{name} {ticker} | الثقة: {conf}% | اخر سعر {current_price}*")
            if entry_low and entry_high:
                lines.append(f"نطاق سعري محتمل: من {entry_low} الي {entry_high} جنية")
            if entry_trigger:
                lines.append(f"او الاستقرار والثبات اعلاه {entry_trigger}")
            if support:
                lines.append(f"دعم مهم في {support}")
            if target_1 and target_2:
                lines.append(f"*مستوى ربح متوقع {target_1} ثم {target_2} جنية*")
            if inv_target:
                lines.append(f"*تارجت بعيد المدى {inv_target}*")
            if exp_return:
                lines.append(f"نسبة ربح متوقع من {round(exp_return * 0.7, 1)}% الي {exp_return}%")
            if stop_loss:
                lines.append(f"مستوى دعم/مخاطر: {stop_loss}")
            
            recommendations.append({
                "ticker": ticker, "name": name, "text": "\n".join(lines),
                "current_price": current_price, "entry_low": entry_low,
                "entry_high": entry_high, "entry_trigger": entry_trigger,
                "support": support, "target_1": target_1, "target_2": target_2,
                "investment_target": inv_target, "stop_loss": stop_loss,
                "expected_return_pct": exp_return, "confidence": sig.get('confidence'),
                "reasons": sig.get('reasons', [])
            })
        
        footer = "⚠️ هذا التحليل للأغراض التعليمية والتثقيفية فقط.\nلا يُعد توصية استثمارية ولا يعتمد عليه لاتخاذ قرارات مالية.\nيُرجى استشارة مستشار مالي مرخص قبل أي قرار استثماري."
        full_text = header + "\n\n"
        for rec in recommendations:
            full_text += rec['text'] + "\n\n"
        full_text += footer
        
        return {
            "success": True, "header": header,
            "recommendations": recommendations, "footer": footer,
            "full_text": full_text, "count": len(recommendations)
        }
    except Exception as e:
        logger.error(f"Error generating morning report: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/reports/morning")
async def get_morning_report(
    limit: int = Query(10, ge=1, le=20),
    asset_type: Optional[str] = Query(None, description="stock, crypto, gold or None for all")
):
    """تقرير صباحي بالتحليلات بالشكل الاحترافي"""
    return _generate_morning_report_sync(limit=limit, asset_type=asset_type)

# ============================================================
# MARKET ENDPOINTS
# ============================================================
@app.get("/api/market/overview")
async def get_market_overview():
    """نظرة عامة على السوق"""
    try:
        # Get market stats
        stats = db.execute_one("""
            SELECT 
                COUNT(CASE WHEN current_price > previous_close THEN 1 END) as advancers,
                COUNT(CASE WHEN current_price < previous_close THEN 1 END) as decliners,
                COUNT(CASE WHEN current_price = previous_close OR previous_close IS NULL THEN 1 END) as unchanged,
                SUM(volume) as total_volume
            FROM stocks
            WHERE is_active = 1
        """)
        
        return {
            "success": True,
            "advancers": stats.get('advancers', 0) or 0,
            "decliners": stats.get('decliners', 0) or 0,
            "unchanged": stats.get('unchanged', 0) or 0,
            "total_volume": stats.get('total_volume', 0) or 0,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        return {"success": False, "error": str(e)}

# ============================================================
# Market Status & Indices
# ============================================================
@app.get("/api/market/status")
async def get_market_status():
    """حالة السوق (مفتوح/مغلق)"""
    from datetime import datetime, timezone, timedelta
    
    # EGX hours: Sunday-Thursday, 9:30 AM - 2:30 PM Cairo time (UTC+2)
    cairo_tz = timezone(timedelta(hours=2))
    now = datetime.now(cairo_tz)
    
    weekday = now.weekday()  # 0=Monday, 4=Friday, 5=Saturday
    hour = now.hour
    minute = now.minute
    time_val = hour * 100 + minute
    
    # EGX is open Sun(6)-Thu(4), 9:30-14:30
    is_weekday = weekday in [6, 0, 1, 2, 3, 4]  # Sun to Thu
    is_open_hours = 930 <= time_val <= 1430
    
    # Special holidays check (simplified - could be expanded)
    is_holiday = False
    
    is_open = is_weekday and is_open_hours and not is_holiday
    
    next_open = None
    if not is_open:
        if weekday == 4:  # Friday
            next_open = (now + timedelta(days=2)).replace(hour=9, minute=30, second=0)
        elif weekday == 5:  # Saturday
            next_open = (now + timedelta(days=1)).replace(hour=9, minute=30, second=0)
        elif time_val > 1430:
            if weekday == 3:  # Thu after close
                next_open = (now + timedelta(days=3)).replace(hour=9, minute=30, second=0)
            else:
                next_open = (now + timedelta(days=1)).replace(hour=9, minute=30, second=0)
        else:
            next_open = now.replace(hour=9, minute=30, second=0)
    
    return {
        "success": True,
        "is_open": is_open,
        "market": "EGX",
        "current_time_cairo": now.strftime("%Y-%m-%d %H:%M:%S"),
        "day_of_week": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][weekday],
        "trading_hours": "09:30 - 14:30 (Cairo time)",
        "next_open": next_open.strftime("%Y-%m-%d %H:%M:%S") if next_open else None,
        "session": "pre-market" if time_val < 930 else ("main" if time_val <= 1430 else "after-hours")
    }


@app.get("/api/market/indices")
async def get_market_indices():
    """مؤشرات السوق EGX30, EGX70, EGX100"""
    try:
        # EGX30
        egx30 = db.execute_query("""
            SELECT ticker, current_price, previous_close,
                   ((current_price - previous_close) / previous_close * 100) as change_percent
            FROM stocks WHERE egx30_member = 1 AND is_active = 1
        """)
        
        # EGX70
        egx70 = db.execute_query("""
            SELECT ticker, current_price, previous_close,
                   ((current_price - previous_close) / previous_close * 100) as change_percent
            FROM stocks WHERE egx70_member = 1 AND is_active = 1
        """)
        
        # EGX100
        egx100 = db.execute_query("""
            SELECT ticker, current_price, previous_close,
                   ((current_price - previous_close) / previous_close * 100) as change_percent
            FROM stocks WHERE egx100_member = 1 AND is_active = 1
        """)
        
        def calc_index(stocks):
            if not stocks:
                return {"value": 0, "change": 0, "change_percent": 0, "constituents": 0}
            total_change = sum(s.get('change_percent', 0) or 0 for s in stocks)
            avg_change = total_change / len(stocks)
            # Simplified index calculation
            base_value = 1000
            current_value = base_value * (1 + avg_change / 100)
            return {
                "value": round(current_value, 2),
                "change": round(avg_change * 10, 2),
                "change_percent": round(avg_change, 2),
                "constituents": len(stocks)
            }
        
        return {
            "success": True,
            "indices": {
                "EGX30": calc_index(egx30),
                "EGX70": calc_index(egx70),
                "EGX100": calc_index(egx100)
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting indices: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/market/top-gainers")
async def get_top_gainers(limit: int = Query(10, ge=1, le=50)):
    """أكبر الرابحين"""
    try:
        gainers = db.execute_query("""
            SELECT ticker, name, current_price, previous_close,
                   (current_price - previous_close) as change,
                   ((current_price - previous_close) / previous_close * 100) as change_percent
            FROM stocks
            WHERE is_active = 1 AND current_price IS NOT NULL AND previous_close IS NOT NULL AND previous_close > 0
            ORDER BY change_percent DESC
            LIMIT ?
        """, (limit,))
        
        return {"success": True, "count": len(gainers), "stocks": gainers}
    
    except Exception as e:
        logger.error(f"Error getting top gainers: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/market/top-losers")
async def get_top_losers(limit: int = Query(10, ge=1, le=50)):
    """أكبر الخاسرين"""
    try:
        losers = db.execute_query("""
            SELECT ticker, name, current_price, previous_close,
                   (current_price - previous_close) as change,
                   ((current_price - previous_close) / previous_close * 100) as change_percent
            FROM stocks
            WHERE is_active = 1 AND current_price IS NOT NULL AND previous_close IS NOT NULL AND previous_close > 0
            ORDER BY change_percent ASC
            LIMIT ?
        """, (limit,))
        
        return {"success": True, "count": len(losers), "stocks": losers}
    
    except Exception as e:
        logger.error(f"Error getting top losers: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/market/most-active")
async def get_most_active(limit: int = Query(10, ge=1, le=50)):
    """الأكثر نشاطاً"""
    try:
        active = db.execute_query("""
            SELECT ticker, name, current_price, volume, 
                   (current_price - previous_close) as change,
                   ((current_price - previous_close) / previous_close * 100) as change_percent
            FROM stocks
            WHERE is_active = 1 AND volume IS NOT NULL
            ORDER BY volume DESC
            LIMIT ?
        """, (limit,))
        
        return {"success": True, "count": len(active), "stocks": active}
    
    except Exception as e:
        logger.error(f"Error getting most active: {e}")
        return {"success": False, "error": str(e)}

# ============================================================
# VPS ADAPTER COMPATIBILITY ENDPOINTS
# Note: /api/stocks/all is defined earlier in the file (before /{symbol})
# ============================================================
@app.get("/api/stock/{symbol}")
async def get_stock_vps(symbol: str):
    """Get single stock - VPS adapter compatible (singular endpoint)"""
    try:
        stock = db.execute_one("""
            SELECT ticker as symbol, name, name_ar, sector, current_price, previous_close,
                   open_price as open, high_price as high, low_price as low, volume
            FROM stocks
            WHERE ticker = ? AND is_active = 1
        """, (symbol.upper(),))
        
        if not stock:
            return {"success": False, "error": f"Stock {symbol} not found"}
        
        # Calculate changes
        if stock.get('current_price') and stock.get('previous_close') and stock['previous_close'] > 0:
            stock['change_amount'] = stock['current_price'] - stock['previous_close']
            stock['change_percent'] = (stock['change_amount'] / stock['previous_close']) * 100
        else:
            stock['change_amount'] = 0
            stock['change_percent'] = 0
        
        return {"success": True, "data": stock}
    
    except Exception as e:
        logger.error(f"Error getting stock {symbol}: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/indices")
async def get_indices():
    """Get market indices - VPS adapter compatible"""
    try:
        # Try to get indices from database, or return simulated data
        indices = db.execute_query("""
            SELECT 'EGX30' as symbol, 'EGX 30 Index' as name,
                   (SELECT AVG(current_price * 100 / previous_close) FROM stocks WHERE egx30_member = 1 AND previous_close > 0) as current_value,
                   0 as change_amount, 0 as change_percent
            UNION ALL
            SELECT 'EGX70', 'EGX 70 Index',
                   (SELECT AVG(current_price * 100 / previous_close) FROM stocks WHERE egx70_member = 1 AND previous_close > 0),
                   0, 0
            UNION ALL
            SELECT 'EGX100', 'EGX 100 Index',
                   (SELECT AVG(current_price * 100 / previous_close) FROM stocks WHERE egx100_member = 1 AND previous_close > 0),
                   0, 0
        """)
        
        return {
            "success": True,
            "data": indices if indices else [],
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting indices: {e}")
        return {"success": False, "error": str(e), "data": []}

@app.get("/api/reports/daily")
async def get_daily_report():
    """Get daily market report - VPS adapter compatible"""
    try:
        stats = db.execute_one("""
            SELECT 
                COUNT(*) as total_stocks,
                COUNT(CASE WHEN current_price > previous_close THEN 1 END) as gainers,
                COUNT(CASE WHEN current_price < previous_close THEN 1 END) as losers,
                AVG((current_price - previous_close) * 100.0 / NULLIF(previous_close, 0)) as average_change
            FROM stocks
            WHERE is_active = 1 AND current_price IS NOT NULL
        """)
        
        return {
            "success": True,
            "data": {
                "market_summary": {
                    "total_stocks": stats.get('total_stocks', 0) or 0,
                    "gainers": stats.get('gainers', 0) or 0,
                    "losers": stats.get('losers', 0) or 0,
                    "average_change": stats.get('average_change', 0) or 0
                }
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting daily report: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/search")
async def search_stocks(q: str = Query(..., min_length=1)):
    """Search stocks by ticker or name - VPS adapter compatible"""
    try:
        results = db.execute_query("""
            SELECT ticker as symbol, name, name_ar, current_price, previous_close, sector
            FROM stocks
            WHERE is_active = 1 AND (
                ticker LIKE ? OR 
                name LIKE ? OR 
                name_ar LIKE ?
            )
            ORDER BY ticker
            LIMIT 20
        """, (f"%{q}%", f"%{q}%", f"%{q}%"))
        
        # Calculate change_percent
        for r in results:
            if r.get('current_price') and r.get('previous_close') and r['previous_close'] > 0:
                r['change_percent'] = ((r['current_price'] - r['previous_close']) / r['previous_close']) * 100
            else:
                r['change_percent'] = 0
        
        return {
            "success": True,
            "results": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error searching stocks: {e}")
        return {"success": False, "error": str(e), "results": []}

@app.get("/api/indicators/{symbol}")
async def get_indicators_vps(symbol: str):
    """Get technical indicators - VPS adapter compatible"""
    try:
        # Get last 100 days of history
        history = db.execute_query("""
            SELECT sph.date, sph.close_price as close, sph.high_price as high, 
                   sph.low_price as low, sph.volume
            FROM stock_price_history sph
            JOIN stocks s ON s.id = sph.stock_id
            WHERE s.ticker = ?
            ORDER BY sph.date DESC
            LIMIT 100
        """, (symbol.upper(),))
        
        if len(history) < 20:
            return {
                "success": True,
                "data": {
                    "ticker": symbol.upper(),
                    "rsi": None,
                    "macd": None,
                    "bollinger_bands": None,
                    "trend": "unknown",
                    "data_points": len(history)
                }
            }
        
        # Reverse for calculations
        history = list(reversed(history))
        closes = pd.Series([h['close'] for h in history])
        highs = pd.Series([h['high'] for h in history])
        lows = pd.Series([h['low'] for h in history])
        
        # Calculate indicators
        rsi = TechnicalAnalysis.calculate_rsi(closes).iloc[-1]
        macd = TechnicalAnalysis.calculate_macd(closes)
        bb = TechnicalAnalysis.calculate_bollinger(closes)
        
        return {
            "success": True,
            "data": {
                "ticker": symbol.upper(),
                "rsi": round(float(rsi), 2) if not pd.isna(rsi) else None,
                "macd": {
                    "macd_line": round(float(macd['macd'].iloc[-1]), 4) if not pd.isna(macd['macd'].iloc[-1]) else None,
                    "signal": round(float(macd['signal'].iloc[-1]), 4) if not pd.isna(macd['signal'].iloc[-1]) else None,
                    "histogram": round(float(macd['histogram'].iloc[-1]), 4) if not pd.isna(macd['histogram'].iloc[-1]) else None
                },
                "bollinger_bands": {
                    "upper": round(float(bb['upper'].iloc[-1]), 2) if not pd.isna(bb['upper'].iloc[-1]) else None,
                    "middle": round(float(bb['middle'].iloc[-1]), 2) if not pd.isna(bb['middle'].iloc[-1]) else None,
                    "lower": round(float(bb['lower'].iloc[-1]), 2) if not pd.isna(bb['lower'].iloc[-1]) else None
                },
                "trend": "bullish" if rsi < 70 and macd['histogram'].iloc[-1] > 0 else "bearish" if rsi > 30 and macd['histogram'].iloc[-1] < 0 else "neutral",
                "data_points": len(history)
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting indicators for {symbol}: {e}")
        return {"success": False, "error": str(e)}

# ============================================================
# BLOCK BACKTEST ENGINE - Tests ALL assets at once
# ============================================================

@app.post("/api/backtest/stocks")
async def backtest_stocks(background_tasks: BackgroundTasks, limit: int = Query(100, ge=1, le=500)):
    """Run block backtest on ALL stocks"""
    background_tasks.add_task(backtest_engine.run_stocks_backtest, limit)
    return {
        "success": True,
        "message": f"Stocks block backtest started for up to {limit} stocks",
        "strategies": list(STRATEGIES.keys()),
        "note": "Tests RSI, MACD, MA, Bollinger, Combined strategies. Check /api/backtest/summaries for results."
    }

@app.post("/api/backtest/crypto")
async def backtest_crypto(background_tasks: BackgroundTasks, limit: int = Query(20, ge=1, le=100)):
    """Run block backtest on ALL crypto coins"""
    background_tasks.add_task(backtest_engine.run_crypto_backtest, limit)
    return {
        "success": True,
        "message": f"Crypto block backtest started for up to {limit} coins",
        "note": "Check /api/backtest/summaries?asset_type=crypto for results."
    }

@app.post("/api/backtest/gold")
async def backtest_gold(background_tasks: BackgroundTasks):
    """Run block backtest on Gold"""
    background_tasks.add_task(backtest_engine.run_gold_backtest)
    return {
        "success": True,
        "message": "Gold block backtest started",
        "note": "Check /api/backtest/summaries?asset_type=gold for results."
    }

@app.get("/api/backtest/summaries")
async def backtest_summaries(asset_type: Optional[str] = None):
    """Get backtest block summaries"""
    try:
        summaries = backtest_engine.get_backtest_summaries(asset_type=asset_type)
        return {"success": True, "count": len(summaries), "summaries": summaries}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/backtest/results")
async def backtest_results(strategy: Optional[str] = None, asset_type: Optional[str] = None, limit: int = 100):
    """Get individual backtest results"""
    try:
        results = backtest_engine.get_backtest_results(strategy=strategy, asset_type=asset_type, limit=limit)
        return {"success": True, "count": len(results), "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/backtest/best-strategies")
async def backtest_best_strategies(asset_type: str = Query(...)):
    """Get best performing strategies for an asset type"""
    try:
        best = backtest_engine.get_best_strategies(asset_type)
        return {"success": True, "asset_type": asset_type, "strategies": best}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# BACKTESTING ENDPOINTS (single stock)
# ============================================================
@app.get("/api/backtest/{symbol}")
async def backtest_stock(
    symbol: str,
    days: int = Query(365, ge=30, le=730),
    holding_period: int = Query(30, ge=1, le=90)
):
    """اختبار استراتيجية التداول"""
    try:
        # Get history
        start_date = datetime.now() - timedelta(days=days + 100)
        start_str = start_date.strftime("%Y-%m-%d")
        
        history = db.execute_query("""
            SELECT sph.date, sph.open_price as open, sph.high_price as high, 
                   sph.low_price as low, sph.close_price as close, sph.volume
            FROM stock_price_history sph
            JOIN stocks s ON s.id = sph.stock_id
            WHERE s.ticker = ? AND sph.date >= ?
            ORDER BY sph.date ASC
        """, (symbol.upper(), start_str))
        
        if len(history) < 100:
            return {"success": False, "error": "Insufficient data for backtesting"}
        
        # Convert to DataFrame
        df = pd.DataFrame(history)
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['open'] = pd.to_numeric(df['open'])
        df['volume'] = pd.to_numeric(df['volume'])
        
        # Calculate indicators
        df['rsi'] = TechnicalAnalysis.calculate_rsi(df['close'])
        macd = TechnicalAnalysis.calculate_macd(df['close'])
        df['macd_histogram'] = macd['histogram']
        df['sma_20'] = TechnicalAnalysis.calculate_sma(df['close'], 20)
        df['sma_50'] = TechnicalAnalysis.calculate_sma(df['close'], 50)
        
        # Simulate trades
        trades = []
        wins = 0
        losses = 0
        returns = []
        max_drawdown = 0
        
        for i in range(100, len(df) - holding_period):
            # Entry signals
            signals = 0
            
            if df['rsi'].iloc[i] < 30:  # Oversold
                signals += 1
            if df['macd_histogram'].iloc[i] > 0:  # MACD bullish
                signals += 1
            if df['sma_20'].iloc[i] > df['sma_50'].iloc[i]:  # MA bullish
                signals += 1
            
            if signals >= 2:  # Entry condition
                entry_price = df['close'].iloc[i]
                exit_price = df['close'].iloc[i + holding_period]
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                
                trades.append({
                    'entry_date': df['date'].iloc[i],
                    'exit_date': df['date'].iloc[i + holding_period],
                    'entry_price': round(entry_price, 2),
                    'exit_price': round(exit_price, 2),
                    'pnl_pct': round(pnl_pct, 2),
                    'result': 'win' if pnl_pct > 0 else 'loss'
                })
                
                returns.append(pnl_pct)
                
                if pnl_pct > 0:
                    wins += 1
                else:
                    losses += 1
        
        total_trades = wins + losses
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        avg_return = np.mean(returns) if returns else 0
        total_return = sum(returns)
        
        # Calculate Sharpe Ratio (simplified)
        sharpe_ratio = (avg_return / np.std(returns) * np.sqrt(252/holding_period)) if len(returns) > 1 else 0
        
        # Calculate Max Drawdown
        cumulative = np.cumsum(returns)
        peak = 0
        for r in cumulative:
            if r > peak:
                peak = r
            drawdown = peak - r
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Get AI analysis for current recommendation
        ai_analysis = None
        try:
            from ai_local_engine import ai_engine
            ai_rec = ai_engine.analyze_stock(symbol.upper())
            if ai_rec:
                ai_analysis = {
                    "action": ai_rec.action,
                    "confidence": ai_rec.confidence,
                    "price_target": ai_rec.price_target,
                    "stop_loss": ai_rec.stop_loss,
                    "reasons": ai_rec.reasons,
                    "approval_reason": ai_rec.approval_reason,
                    "technical_analysis": ai_rec.technical_analysis,
                    "news_impact": ai_rec.news_impact,
                    "ai_approved": ai_rec.ai_approved
                }
        except Exception as e:
            logger.warning(f"AI analysis not available for backtest: {e}")

        return {
            "success": True,
            "symbol": symbol.upper(),
            "backtest_period": f"{days} days",
            "holding_period": f"{holding_period} days",
            "summary": {
                "total_trades": total_trades,
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 2),
                "total_return": round(total_return, 2),
                "avg_return": round(avg_return, 2),
                "max_drawdown": round(max_drawdown, 2),
                "sharpe_ratio": round(sharpe_ratio, 2)
            },
            "trades": trades[-20:] if trades else [],
            "ai_analysis": ai_analysis
        }
    
    except Exception as e:
        logger.error(f"Backtest error for {symbol}: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/backtest")
async def backtest_post(request: Request):
    """POST backtest with strategy parameters"""
    try:
        data = await request.json()
        symbol = (data.get("ticker") or data.get("symbol", "")).upper()
        strategy = data.get("strategy", "ma_crossover")
        days = int(data.get("days", 365))
        holding_period = int(data.get("holding_period", 30))
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        
        if not symbol:
            return {"success": False, "error": "ticker is required"}
        
        # Delegate to the GET endpoint logic
        result = await backtest_stock(symbol, days=days, holding_period=holding_period)
        result["strategy"] = strategy
        result["start_date"] = start_date
        result["end_date"] = end_date
        return result
    except Exception as e:
        logger.error(f"POST backtest error: {e}")
        return {"success": False, "error": str(e)}

# Include Frontend API Aliases (compat with main.py endpoints)
# Placed AFTER all static /api/backtest/* routes so they match first
app.include_router(frontend_router, prefix="/api")

# ============================================================
# SCREENER ENDPOINTS
# ============================================================
@app.get("/api/screener")
async def screen_stocks(
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_volume: Optional[float] = None,
    min_rsi: Optional[float] = None,
    max_rsi: Optional[float] = None,
    sector: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200)
):
    """فرز الأسهم حسب المعايير"""
    try:
        # Base query
        query = """
            SELECT ticker, name, current_price, previous_close, volume, sector
            FROM stocks
            WHERE is_active = 1
        """
        params = []
        
        if min_price:
            query += " AND current_price >= ?"
            params.append(min_price)
        if max_price:
            query += " AND current_price <= ?"
            params.append(max_price)
        if min_volume:
            query += " AND volume >= ?"
            params.append(min_volume)
        if sector:
            query += " AND sector = ?"
            params.append(sector)
        
        query += " ORDER BY volume DESC LIMIT ?"
        params.append(limit)
        
        stocks = db.execute_query(query, tuple(params))
        
        # Filter by RSI if needed
        if min_rsi is not None or max_rsi is not None:
            filtered_stocks = []
            for stock in stocks:
                try:
                    history = db.execute_query("""
                        SELECT sph.close_price as close
                        FROM stock_price_history sph
                        JOIN stocks s ON s.id = sph.stock_id
                        WHERE s.ticker = ?
                        ORDER BY sph.date DESC
                        LIMIT 20
                    """, (stock['ticker'],))
                    
                    if len(history) >= 14:
                        closes = pd.Series([h['close'] for h in history])
                        rsi = TechnicalAnalysis.calculate_rsi(closes).iloc[-1]
                        
                        if min_rsi is not None and rsi < min_rsi:
                            continue
                        if max_rsi is not None and rsi > max_rsi:
                            continue
                        
                        stock['rsi'] = round(rsi, 2)
                        filtered_stocks.append(stock)
                except:
                    continue
            stocks = filtered_stocks
        
        return {"success": True, "count": len(stocks), "stocks": stocks}
    
    except Exception as e:
        logger.error(f"Screener error: {e}")
        return {"success": False, "error": str(e)}

# ============================================================
# WATCHLIST ENDPOINTS
# ============================================================
@app.get("/api/watchlist")
async def get_watchlist():
    """الحصول على قائمة المراقبة"""
    try:
        watchlist = db.execute_query("""
            SELECT s.ticker, w.created_at, s.name, s.name_ar, s.current_price, s.previous_close,
                   w.alert_price_above, w.alert_price_below, w.notes
            FROM user_stock_watchlists w
            JOIN stocks s ON s.id = w.stock_id
            ORDER BY w.created_at DESC
        """)
        for w in watchlist:
            cp = w.get('current_price') or 0
            pc = w.get('previous_close') or 0
            w['change'] = round(cp - pc, 2) if cp and pc else 0
            w['change_percent'] = round((cp - pc) / pc * 100, 2) if pc else 0
        
        return {"success": True, "count": len(watchlist), "watchlist": [_convert_numpy(w) for w in watchlist]}
    
    except Exception as e:
        logger.error(f"Watchlist error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/watchlist")
async def add_to_watchlist(request: Request):
    """إضافة إلى قائمة المراقبة"""
    try:
        data = await request.json()
        ticker = (data.get("ticker") or "").upper()
        if not ticker:
            return {"success": False, "error": "ticker is required"}
        
        # Check if stock exists and get its id
        stock = db.execute_one("SELECT id FROM stocks WHERE ticker = ?", (ticker,))
        if not stock:
            return {"success": False, "error": f"Stock {ticker} not found"}
        
        # Add to watchlist
        try:
            db.execute_insert(
                "INSERT INTO user_stock_watchlists (user_id, stock_id, alert_price_above, alert_price_below, notes) VALUES (?, ?, ?, ?, ?)",
                ("default_user", stock["id"], data.get("alert_price_above"), data.get("alert_price_below"), data.get("notes", ""))
            )
        except Exception as e:
            logger.warning(f"Watchlist insert warning: {e}")
            pass  # Already in watchlist
        
        return {"success": True, "message": f"{ticker} added to watchlist"}
    
    except Exception as e:
        logger.error(f"Add to watchlist error: {e}")
        return {"success": False, "error": str(e)}

@app.delete("/api/watchlist/{ticker}")
async def remove_from_watchlist(ticker: str):
    """حذف من قائمة المراقبة"""
    try:
        stock = db.execute_one("SELECT id FROM stocks WHERE ticker = ?", (ticker.upper(),))
        if stock:
            db.execute_update(
                "DELETE FROM user_stock_watchlists WHERE stock_id = ?",
                (stock["id"],)
            )
        return {"success": True, "message": f"{ticker} removed from watchlist"}
    
    except Exception as e:
        logger.error(f"Remove from watchlist error: {e}")
        return {"success": False, "error": str(e)}

# ============================================================
# SEARCH ENDPOINT
# ============================================================
@app.get("/api/search")
async def search_stocks(q: str, limit: int = Query(20, ge=1, le=50)):
    """البحث في الأسهم"""
    try:
        search_term = f"%{q}%"
        results = db.execute_query("""
            SELECT ticker, name, name_ar, sector, current_price
            FROM stocks
            WHERE is_active = 1 AND (
                ticker LIKE ? OR name LIKE ? OR name_ar LIKE ?
            )
            ORDER BY ticker
            LIMIT ?
        """, (search_term, search_term, search_term, limit))
        
        return {"success": True, "count": len(results), "results": results}
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"success": False, "error": str(e)}

# ============================================================
# SECTORS ENDPOINT
# ============================================================
@app.get("/api/sectors")
async def get_sectors():
    """الحصول على القطاعات"""
    try:
        sectors = db.execute_query("""
            SELECT sector, COUNT(*) as stock_count,
                   AVG(current_price) as avg_price,
                   SUM(volume) as total_volume
            FROM stocks
            WHERE is_active = 1 AND sector IS NOT NULL
            GROUP BY sector
            ORDER BY stock_count DESC
        """)
        
        return {"success": True, "count": len(sectors), "sectors": sectors}
    
    except Exception as e:
        logger.error(f"Sectors error: {e}")
        return {"success": False, "error": str(e)}

# ============================================================
# ADMIN ENDPOINTS
# ============================================================
@app.get("/api/admin/stats")
async def get_admin_stats():
    """إحصائيات لوحة التحكم"""
    try:
        # Stock stats
        stock_stats = db.execute_one("""
            SELECT 
                COUNT(*) as total_stocks,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_stocks,
                COUNT(DISTINCT sector) as sector_count,
                MAX(last_update) as last_update,
                SUM(volume) as total_volume
            FROM stocks
        """)
        
        # History count
        history_count = db.execute_one("SELECT COUNT(*) as count FROM stock_price_history")
        
        # Watchlist count
        try:
            watchlist_count = db.execute_one("SELECT COUNT(*) as count FROM user_stock_watchlists")
            watchlist_total = watchlist_count.get('count', 0) if watchlist_count else 0
        except:
            watchlist_total = 0
        
        # Market overview
        market_stats = db.execute_one("""
            SELECT 
                COUNT(CASE WHEN current_price > previous_close THEN 1 END) as advancers,
                COUNT(CASE WHEN current_price < previous_close THEN 1 END) as decliners,
                COUNT(CASE WHEN current_price = previous_close OR previous_close IS NULL THEN 1 END) as unchanged
            FROM stocks
            WHERE is_active = 1
        """)
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "stocks": {
                "total": stock_stats.get('total_stocks', 0) or 0,
                "active": stock_stats.get('active_stocks', 0) or 0,
                "sectors": stock_stats.get('sector_count', 0) or 0,
                "last_update": stock_stats.get('last_update'),
                "price_history_points": history_count.get('count', 0) if history_count else 0
            },
            "market": {
                "advancers": market_stats.get('advancers', 0) or 0 if market_stats else 0,
                "decliners": market_stats.get('decliners', 0) or 0 if market_stats else 0,
                "unchanged": market_stats.get('unchanged', 0) or 0 if market_stats else 0,
                "total_volume": stock_stats.get('total_volume', 0) or 0
            },
            "platform": {
                "watchlist_items": watchlist_total,
                "portfolio_items": 0
            }
        }
    
    except Exception as e:
        logger.error(f"Admin stats error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/admin/recommendations")
async def get_admin_recommendations():
    """تحليلات الخبراء للإدارة"""
    try:
        # Get recommendations from recommendations table if exists
        try:
            recommendations = db.execute_query("""
                SELECT * FROM recommendations
                ORDER BY created_at DESC
                LIMIT 100
            """)
        except:
            recommendations = []
        
        return {
            "success": True,
            "count": len(recommendations),
            "recommendations": recommendations
        }
    
    except Exception as e:
        logger.error(f"Admin recommendations error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/admin/system-status")
async def get_system_status():
    """حالة النظام"""
    try:
        # Check database
        db_status = "connected"
        try:
            db.execute_one("SELECT 1")
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # Get counts
        stock_count = db.execute_one("SELECT COUNT(*) as count FROM stocks")['count']
        history_count = db.execute_one("SELECT COUNT(*) as count FROM stock_price_history")['count']
        
        return {
            "success": True,
            "database": db_status,
            "stock_count": stock_count,
            "history_count": history_count,
            "version": VERSION,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"System status error: {e}")
        return {"success": False, "error": str(e)}

# ============================================================
# ITERATIVE LEARNING ENGINE
# ============================================================
import threading
import random

class IterativeLearningState:
    """حالة التعلم التكراري"""
    def __init__(self):
        self.is_running = False
        self.should_stop = False
        self.target_win_rate = 70.0
        self.current_win_rate = 0.0
        self.best_win_rate = 0.0
        self.iteration = 0
        self.max_iterations = 50
        self.status = 'idle'
        self.started_at = None
        self.completed_at = None
        self.best_parameters = None
        self.message = ''
        self.total_trades = 0
        self.winning_trades = 0
        self.win_rate_history = []
        self.current_params = {
            'rsi_oversold': 30.0,
            'rsi_overbought': 70.0,
            'confidence_threshold': 55.0,
            'stop_loss_pct': 5.0,
            'target_multiplier': 2.0
        }

learning_state = IterativeLearningState()
learning_lock = threading.Lock()

def run_iterative_learning():
    """تشغيل التعلم التكراري في الخلفية"""
    global learning_state
    
    with learning_lock:
        learning_state.status = 'running'
        learning_state.started_at = datetime.now().isoformat()
        learning_state.is_running = True
        learning_state.should_stop = False
    
    logger.info(f"🧠 Starting Iterative Learning - Target: {learning_state.target_win_rate}%")
    
    try:
        # Get all tickers with sufficient history
        tickers_data = db.execute_query("""
            SELECT s.ticker, COUNT(sph.id) as history_count
            FROM stocks s
            LEFT JOIN stock_price_history sph ON s.id = sph.stock_id
            WHERE s.is_active = 1
            GROUP BY s.ticker
            HAVING history_count >= 50
            ORDER BY s.volume DESC
            LIMIT 100
        """)
        tickers = [t['ticker'] for t in tickers_data]
        logger.info(f"📊 Found {len(tickers)} stocks with sufficient history")
        
        for iteration in range(1, learning_state.max_iterations + 1):
            if learning_state.should_stop:
                with learning_lock:
                    learning_state.status = 'stopped'
                    learning_state.message = 'تم إيقاف التعلم'
                break
            
            with learning_lock:
                learning_state.iteration = iteration
            
            # Run backtest on subset of stocks
            total_trades = 0
            winning_trades = 0
            
            for ticker in tickers[:50]:  # Test on 50 stocks per iteration
                try:
                    # Get history - order ASC for proper backtest
                    history = db.execute_query("""
                        SELECT sph.date, sph.close_price as close, sph.high_price as high,
                               sph.low_price as low, sph.open_price as open, sph.volume
                        FROM stock_price_history sph
                        JOIN stocks s ON s.id = sph.stock_id
                        WHERE s.ticker = ?
                        ORDER BY sph.date ASC
                        LIMIT 500
                    """, (ticker,))
                    
                    if len(history) < 60:
                        continue
                    
                    # Prepare data - already ASC
                    closes = [h['close'] for h in history if h['close']]
                    highs = [h['high'] for h in history if h['high']]
                    lows = [h['low'] for h in history if h['low']]
                    
                    if len(closes) < 60:
                        continue
                    
                    # Calculate indicators
                    closes_series = pd.Series(closes)
                    rsi = TechnicalAnalysis.calculate_rsi(closes_series)
                    
                    # Calculate MACD
                    macd_data = TechnicalAnalysis.calculate_macd(closes_series)
                    macd_histogram = macd_data['histogram']
                    
                    # Calculate SMAs
                    sma_20 = TechnicalAnalysis.calculate_sma(closes_series, 20)
                    sma_50 = TechnicalAnalysis.calculate_sma(closes_series, 50)
                    
                    rsi_oversold = learning_state.current_params['rsi_oversold']
                    rsi_overbought = learning_state.current_params['rsi_overbought']
                    confidence_threshold = learning_state.current_params['confidence_threshold']
                    
                    # Simulate trades with multiple entry conditions
                    for i in range(60, len(closes) - 10):
                        if i >= len(rsi) or i >= len(macd_histogram):
                            continue
                        
                        current_rsi = rsi.iloc[i] if not pd.isna(rsi.iloc[i]) else 50
                        current_macd = macd_histogram.iloc[i] if not pd.isna(macd_histogram.iloc[i]) else 0
                        current_sma20 = sma_20.iloc[i] if i < len(sma_20) and not pd.isna(sma_20.iloc[i]) else closes[i]
                        current_sma50 = sma_50.iloc[i] if i < len(sma_50) and not pd.isna(sma_50.iloc[i]) else closes[i]
                        
                        # Calculate signal strength
                        signal_score = 0
                        
                        # RSI signals (weighted)
                        if current_rsi < rsi_oversold:
                            signal_score += 3  # Strong buy
                        elif current_rsi < 40:
                            signal_score += 1  # Moderate buy
                        elif current_rsi > rsi_overbought:
                            signal_score -= 3  # Strong sell
                        elif current_rsi > 60:
                            signal_score -= 1  # Moderate sell
                        
                        # MACD signal
                        if current_macd > 0:
                            signal_score += 2
                        elif current_macd < 0:
                            signal_score -= 1
                        
                        # SMA crossover
                        if current_sma20 > current_sma50:
                            signal_score += 1
                        else:
                            signal_score -= 1
                        
                        # Entry condition: signal_score >= threshold
                        if signal_score >= 3:  # Buy signal
                            entry_price = closes[i]
                            exit_price = closes[i + 10]  # 10-day holding
                            pnl_pct = (exit_price - entry_price) / entry_price * 100
                            
                            total_trades += 1
                            if pnl_pct > 0:
                                winning_trades += 1
                
                except Exception as e:
                    logger.error(f"Error processing {ticker}: {e}")
                    continue
            
            # Calculate win rate
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            with learning_lock:
                learning_state.current_win_rate = win_rate
                learning_state.total_trades = total_trades
                learning_state.winning_trades = winning_trades
                learning_state.win_rate_history.append(win_rate)
                
                if win_rate > learning_state.best_win_rate:
                    learning_state.best_win_rate = win_rate
                    learning_state.best_parameters = learning_state.current_params.copy()
                    learning_state.message = f'🏆 أفضل نتيجة جديدة: {win_rate:.2f}%'
                else:
                    learning_state.message = f'التكرار {iteration}: {win_rate:.2f}% ({total_trades} صفقة)'
            
            logger.info(f"Learning iteration {iteration}: Win Rate = {win_rate:.2f}%, Trades = {total_trades}")
            
            # Check if target reached
            if win_rate >= learning_state.target_win_rate:
                with learning_lock:
                    learning_state.status = 'completed'
                    learning_state.message = f'🎯 تم الوصول للهدف! {win_rate:.2f}%'
                    learning_state.completed_at = datetime.now().isoformat()
                break
            
            # Adjust parameters based on results
            if total_trades < 10:
                # Too few trades, loosen conditions
                learning_state.current_params['rsi_oversold'] = min(40, learning_state.current_params['rsi_oversold'] + 2)
                logger.info(f"Few trades, loosening RSI oversold to {learning_state.current_params['rsi_oversold']}")
            elif win_rate < 40:
                # Low win rate, tighten conditions
                learning_state.current_params['rsi_oversold'] = max(25, learning_state.current_params['rsi_oversold'] - 2)
            elif win_rate > 60:
                # Good win rate, can be more selective
                learning_state.current_params['confidence_threshold'] = min(70, learning_state.current_params['confidence_threshold'] + 2)
        
        # Finalize
        with learning_lock:
            if learning_state.status == 'running':
                learning_state.status = 'completed'
                learning_state.completed_at = datetime.now().isoformat()
                learning_state.message = f'انتهى التعلم - أفضل نسبة: {learning_state.best_win_rate:.2f}%'
            learning_state.is_running = False
    
    except Exception as e:
        logger.error(f"Learning error: {e}")
        with learning_lock:
            learning_state.status = 'error'
            learning_state.message = str(e)
            learning_state.is_running = False


# ============================================================
# ITERATIVE LEARNING ENDPOINTS
# ============================================================

class LearningStartRequest(BaseModel):
    """طلب بدء التعلم"""
    target_win_rate: float = Field(default=70.0, ge=50.0, le=99.0)
    max_iterations: int = Field(default=50, ge=1, le=200)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    capital: float = Field(default=100000.0)
    max_positions: int = Field(default=5)
    holding_days: int = Field(default=20)
    tickers: Optional[List[str]] = None


@app.post("/api/iterative-learning/start")
async def start_iterative_learning(request: LearningStartRequest, background_tasks: BackgroundTasks):
    """بدء التعلم التكراري"""
    global learning_state
    
    with learning_lock:
        if learning_state.is_running:
            return {
                "success": False,
                "message": "التعلم يعمل بالفعل",
                "progress": {
                    "iteration": learning_state.iteration,
                    "current_win_rate": learning_state.current_win_rate,
                    "status": learning_state.status
                }
            }
        
        # Reset state
        learning_state = IterativeLearningState()
        learning_state.target_win_rate = request.target_win_rate
        learning_state.max_iterations = request.max_iterations
    
    # Run in background
    background_tasks.add_task(run_iterative_learning)
    
    return {
        "success": True,
        "message": "بدأ التعلم التكراري",
        "config": {
            "target_win_rate": request.target_win_rate,
            "max_iterations": request.max_iterations
        }
    }


@app.post("/api/iterative-learning/stop")
async def stop_iterative_learning():
    """إيقاف التعلم التكراري"""
    global learning_state
    
    with learning_lock:
        if not learning_state.is_running:
            return {
                "success": False,
                "message": "التعلم لا يعمل حالياً"
            }
        
        learning_state.should_stop = True
        learning_state.status = 'stopping'
        learning_state.message = 'جاري إيقاف التعلم...'
    
    return {
        "success": True,
        "message": "جاري إيقاف التعلم..."
    }


@app.get("/api/iterative-learning/status")
async def get_iterative_learning_status():
    """الحصول على حالة التعلم التكراري"""
    with learning_lock:
        return {
            "success": True,
            "data": {
                "status": learning_state.status,
                "is_running": learning_state.is_running,
                "iteration": learning_state.iteration,
                "max_iterations": learning_state.max_iterations,
                "target_win_rate": learning_state.target_win_rate,
                "current_win_rate": round(learning_state.current_win_rate, 2),
                "best_win_rate": round(learning_state.best_win_rate, 2),
                "total_trades": learning_state.total_trades,
                "winning_trades": learning_state.winning_trades,
                "message": learning_state.message,
                "started_at": learning_state.started_at,
                "completed_at": learning_state.completed_at,
                "best_parameters": learning_state.best_parameters,
                "current_parameters": learning_state.current_params,
                "win_rate_history": learning_state.win_rate_history[-20:] if learning_state.win_rate_history else []
            }
        }


@app.get("/api/iterative-learning/results")
async def get_iterative_learning_results():
    """الحصول على نتائج التعلم التكراري"""
    with learning_lock:
        return {
            "success": True,
            "data": {
                "status": learning_state.status,
                "best_win_rate": round(learning_state.best_win_rate, 2),
                "best_parameters": learning_state.best_parameters,
                "total_iterations": learning_state.iteration,
                "win_rate_history": learning_state.win_rate_history,
                "started_at": learning_state.started_at,
                "completed_at": learning_state.completed_at
            }
        }


@app.post("/api/iterative-learning/apply-best")
async def apply_best_parameters():
    """تطبيق أفضل البارامترات"""
    global learning_state
    
    with learning_lock:
        if not learning_state.best_parameters:
            return {
                "success": False,
                "message": "لا توجد بارامترات محفوظة"
            }
        
        if learning_state.best_win_rate < 40:
            return {
                "success": False,
                "message": f"نسبة النجاح منخفضة جداً ({learning_state.best_win_rate:.2f}%)"
            }
    
    return {
        "success": True,
        "message": f"تم تطبيق البارامترات بنجاح",
        "parameters": learning_state.best_parameters,
        "win_rate": round(learning_state.best_win_rate, 2)
    }


# ============================================================
# CRYPTO ENDPOINTS - العملات الرقمية
# ============================================================
import aiohttp
from typing import Optional

# Cache for crypto data
crypto_cache: Dict[str, Any] = {
    "data": None,
    "timestamp": 0,
    "all_coins": None,
    "all_coins_timestamp": 0
}

CRYPTO_CACHE_DURATION = 60 * 1000  # 1 minute

async def fetch_coingecko(endpoint: str, params: Dict = None) -> Optional[Dict]:
    """جلب البيانات من CoinGecko API"""
    base_url = "https://api.coingecko.com/api/v3"
    url = f"{base_url}/{endpoint}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"CoinGecko API error: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error fetching from CoinGecko: {e}")
        return None

@app.get("/api/crypto")
async def get_crypto_list(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=250),
    vs_currency: str = "usd",
    order: str = "market_cap_desc"
):
    """الحصول على قائمة العملات الرقمية - جميع العملات"""
    try:
        # Check cache
        cache_key = f"{page}_{per_page}_{vs_currency}_{order}"
        now = datetime.now().timestamp() * 1000
        
        if crypto_cache["data"] and (now - crypto_cache["timestamp"]) < CRYPTO_CACHE_DURATION:
            if cache_key in crypto_cache["data"]:
                return {
                    "success": True,
                    "data": crypto_cache["data"][cache_key],
                    "cached": True,
                    "timestamp": datetime.now().isoformat()
                }
        
        # Fetch from CoinGecko
        data = await fetch_coingecko("coins/markets", {
            "vs_currency": vs_currency,
            "order": order,
            "per_page": per_page,
            "page": page,
            "sparkline": "true",
            "price_change_percentage": "1h,24h,7d"
        })
        
        if not data:
            return {"success": False, "error": "Failed to fetch crypto data"}
        
        # Format data
        formatted = []
        for coin in data:
            formatted.append({
                "id": coin.get("id"),
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name"),
                "image": coin.get("image"),
                "current_price": coin.get("current_price"),
                "market_cap": coin.get("market_cap"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "total_volume": coin.get("total_volume"),
                "high_24h": coin.get("high_24h"),
                "low_24h": coin.get("low_24h"),
                "price_change_24h": coin.get("price_change_24h"),
                "price_change_percentage_24h": coin.get("price_change_percentage_24h"),
                "price_change_percentage_1h": coin.get("price_change_percentage_1h_in_currency"),
                "price_change_percentage_7d": coin.get("price_change_percentage_7d_in_currency"),
                "circulating_supply": coin.get("circulating_supply"),
                "total_supply": coin.get("total_supply"),
                "ath": coin.get("ath"),
                "ath_change_percentage": coin.get("ath_change_percentage"),
                "atl": coin.get("atl"),
                "atl_change_percentage": coin.get("atl_change_percentage"),
                "sparkline_7d": coin.get("sparkline_in_7d", {}).get("price", []),
                "last_updated": coin.get("last_updated")
            })
        
        # Update cache
        if not crypto_cache["data"]:
            crypto_cache["data"] = {}
        crypto_cache["data"][cache_key] = formatted
        crypto_cache["timestamp"] = now
        
        return {
            "success": True,
            "data": formatted,
            "page": page,
            "per_page": per_page,
            "total_coins": "10000+",  # CoinGecko tracks 10000+ coins
            "cached": False,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting crypto list: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/crypto/all")
async def get_all_crypto_ids():
    """الحصول على قائمة كل العملات الرقمية (ID, Symbol, Name فقط)"""
    try:
        now = datetime.now().timestamp() * 1000
        
        # Check cache
        if crypto_cache["all_coins"] and (now - crypto_cache["all_coins_timestamp"]) < 3600000:  # 1 hour
            return {
                "success": True,
                "count": len(crypto_cache["all_coins"]),
                "data": crypto_cache["all_coins"],
                "cached": True
            }
        
        # Fetch from CoinGecko
        data = await fetch_coingecko("coins/list")
        
        if not data:
            return {"success": False, "error": "Failed to fetch coin list"}
        
        # Format
        formatted = [{"id": c["id"], "symbol": c["symbol"].upper(), "name": c["name"]} for c in data]
        
        # Update cache
        crypto_cache["all_coins"] = formatted
        crypto_cache["all_coins_timestamp"] = now
        
        return {
            "success": True,
            "count": len(formatted),
            "data": formatted,
            "cached": False,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting all crypto IDs: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/crypto/{coin_id}")
async def get_crypto_detail(coin_id: str):
    """تفاصيل عملة رقمية محددة"""
    try:
        data = await fetch_coingecko(f"coins/{coin_id}", {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "true"
        })
        
        if not data:
            return {"success": False, "error": f"Crypto {coin_id} not found"}
        
        market_data = data.get("market_data", {})
        
        return {
            "success": True,
            "data": {
                "id": data.get("id"),
                "symbol": data.get("symbol", "").upper(),
                "name": data.get("name"),
                "description": data.get("description", {}).get("en", "")[:500] if data.get("description") else "",
                "image": data.get("image", {}).get("large"),
                "current_price": market_data.get("current_price", {}).get("usd"),
                "market_cap": market_data.get("market_cap", {}).get("usd"),
                "market_cap_rank": market_data.get("market_cap_rank"),
                "total_volume": market_data.get("total_volume", {}).get("usd"),
                "high_24h": market_data.get("high_24h", {}).get("usd"),
                "low_24h": market_data.get("low_24h", {}).get("usd"),
                "price_change_24h": market_data.get("price_change_24h"),
                "price_change_percentage_24h": market_data.get("price_change_percentage_24h"),
                "price_change_percentage_7d": market_data.get("price_change_percentage_7d"),
                "price_change_percentage_30d": market_data.get("price_change_percentage_30d"),
                "price_change_percentage_1y": market_data.get("price_change_percentage_1y"),
                "ath": market_data.get("ath", {}).get("usd"),
                "ath_change_percentage": market_data.get("ath_change_percentage", {}).get("usd"),
                "atl": market_data.get("atl", {}).get("usd"),
                "atl_change_percentage": market_data.get("atl_change_percentage", {}).get("usd"),
                "circulating_supply": market_data.get("circulating_supply"),
                "total_supply": market_data.get("total_supply"),
                "max_supply": market_data.get("max_supply"),
                "sparkline_7d": market_data.get("sparkline_7d", {}).get("price", []),
                "last_updated": data.get("last_updated")
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting crypto detail for {coin_id}: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/crypto/{coin_id}/history")
async def get_crypto_history(
    coin_id: str,
    days: int = Query(30, ge=1, le=365),
    vs_currency: str = "usd"
):
    """السجل التاريخي لعملة رقمية"""
    try:
        data = await fetch_coingecko(f"coins/{coin_id}/market_chart", {
            "vs_currency": vs_currency,
            "days": days
        })
        
        if not data:
            return {"success": False, "error": f"No history for {coin_id}"}
        
        # Format OHLC data
        prices = data.get("prices", [])
        
        history = []
        for i, (timestamp, price) in enumerate(prices):
            history.append({
                "date": datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M"),
                "timestamp": timestamp,
                "price": price,
                "close": price
            })
        
        return {
            "success": True,
            "coin_id": coin_id,
            "days": days,
            "count": len(history),
            "history": history,
            "prices": prices,
            "total_volumes": data.get("total_volumes", []),
            "market_caps": data.get("market_caps", [])
        }
    
    except Exception as e:
        logger.error(f"Error getting crypto history for {coin_id}: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/crypto/{coin_id}/ohlc")
async def get_crypto_ohlc(
    coin_id: str,
    days: int = Query(30, ge=1, le=365)
):
    """بيانات OHLC لعملة رقمية"""
    try:
        data = await fetch_coingecko(f"coins/{coin_id}/ohlc", {
            "vs_currency": "usd",
            "days": days
        })
        
        if not data:
            return {"success": False, "error": f"No OHLC data for {coin_id}"}
        
        # Format OHLC
        ohlc = []
        for item in data:
            ohlc.append({
                "timestamp": item[0],
                "date": datetime.fromtimestamp(item[0] / 1000).strftime("%Y-%m-%d %H:%M"),
                "open": item[1],
                "high": item[2],
                "low": item[3],
                "close": item[4]
            })
        
        return {
            "success": True,
            "coin_id": coin_id,
            "days": days,
            "count": len(ohlc),
            "ohlc": ohlc
        }
    
    except Exception as e:
        logger.error(f"Error getting crypto OHLC for {coin_id}: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/crypto/{coin_id}/analysis")
async def analyze_crypto(coin_id: str, days: int = Query(30, ge=14, le=365)):
    """تحليل فني لعملة رقمية"""
    try:
        # Get OHLC data
        ohlc_data = await get_crypto_ohlc(coin_id, days)
        
        if not ohlc_data.get("success"):
            return ohlc_data
        
        ohlc = ohlc_data["ohlc"]
        
        if len(ohlc) < 14:
            return {"success": False, "error": "Insufficient data for analysis"}
        
        # Convert to DataFrame
        df = pd.DataFrame(ohlc)
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['open'] = pd.to_numeric(df['open'])
        
        # Calculate indicators
        analysis = {
            "current_price": df['close'].iloc[-1],
            "rsi": TechnicalAnalysis.calculate_rsi(df['close']).iloc[-1],
            "sma_20": TechnicalAnalysis.calculate_sma(df['close'], 20).iloc[-1] if len(df) >= 20 else None,
            "sma_50": TechnicalAnalysis.calculate_sma(df['close'], 50).iloc[-1] if len(df) >= 50 else None,
            "ema_12": TechnicalAnalysis.calculate_ema(df['close'], 12).iloc[-1],
            "ema_26": TechnicalAnalysis.calculate_ema(df['close'], 26).iloc[-1],
        }
        
        # MACD
        macd = TechnicalAnalysis.calculate_macd(df['close'])
        analysis["macd"] = macd['macd'].iloc[-1]
        analysis["macd_signal"] = macd['signal'].iloc[-1]
        analysis["macd_histogram"] = macd['histogram'].iloc[-1]
        
        # Bollinger
        bb = TechnicalAnalysis.calculate_bollinger(df['close'])
        analysis["bb_upper"] = bb['upper'].iloc[-1]
        analysis["bb_middle"] = bb['middle'].iloc[-1]
        analysis["bb_lower"] = bb['lower'].iloc[-1]
        
        # ATR
        analysis["atr"] = TechnicalAnalysis.calculate_atr(df['high'], df['low'], df['close']).iloc[-1]
        
        # Stochastic
        stoch = TechnicalAnalysis.calculate_stochastic(df['high'], df['low'], df['close'])
        analysis["stoch_k"] = stoch['k'].iloc[-1]
        analysis["stoch_d"] = stoch['d'].iloc[-1]
        
        # Generate signals
        signals = []
        
        # RSI Signal
        if analysis["rsi"] < 30:
            signals.append({"indicator": "RSI", "signal": "oversold", "value": round(analysis["rsi"], 2), "action": "buy"})
        elif analysis["rsi"] > 70:
            signals.append({"indicator": "RSI", "signal": "overbought", "value": round(analysis["rsi"], 2), "action": "sell"})
        
        # MACD Signal
        if analysis["macd_histogram"] > 0:
            signals.append({"indicator": "MACD", "signal": "bullish", "value": round(analysis["macd_histogram"], 4), "action": "buy"})
        else:
            signals.append({"indicator": "MACD", "signal": "bearish", "value": round(analysis["macd_histogram"], 4), "action": "sell"})
        
        # MA Signal
        if analysis["sma_20"] and analysis["sma_50"]:
            if analysis["sma_20"] > analysis["sma_50"]:
                signals.append({"indicator": "MA_Cross", "signal": "bullish", "action": "buy"})
            else:
                signals.append({"indicator": "MA_Cross", "signal": "bearish", "action": "sell"})
        
        # Bollinger Signal
        current_price = analysis["current_price"]
        if current_price < analysis["bb_lower"]:
            signals.append({"indicator": "Bollinger", "signal": "below_lower", "action": "buy"})
        elif current_price > analysis["bb_upper"]:
            signals.append({"indicator": "Bollinger", "signal": "above_upper", "action": "sell"})
        
        # Overall trend
        buy_signals = sum(1 for s in signals if s.get("action") == "buy")
        sell_signals = sum(1 for s in signals if s.get("action") == "sell")
        
        if buy_signals > sell_signals:
            trend = "bullish"
            recommendation = "buy"
        elif sell_signals > buy_signals:
            trend = "bearish"
            recommendation = "sell"
        else:
            trend = "neutral"
            recommendation = "hold"
        
        return {
            "success": True,
            "coin_id": coin_id,
            "analysis": analysis,
            "signals": signals,
            "trend": trend,
            "recommendation": recommendation,
            "confidence": round(abs(buy_signals - sell_signals) / max(len(signals), 1) * 100, 1)
        }
    
    except Exception as e:
        logger.error(f"Error analyzing crypto {coin_id}: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/crypto/trending")
async def get_trending_crypto():
    """العملات الرقمية الأكثر رواجاً"""
    try:
        data = await fetch_coingecko("search/trending")
        
        if not data:
            return {"success": False, "error": "Failed to fetch trending"}
        
        trending = []
        for item in data.get("coins", []):
            coin = item.get("item", {})
            trending.append({
                "id": coin.get("id"),
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "price_btc": coin.get("price_btc"),
                "score": coin.get("score")
            })
        
        return {
            "success": True,
            "count": len(trending),
            "data": trending,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting trending crypto: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# GOLD & SILVER ENDPOINTS - الذهب والفضة
# ============================================================

# Gold prices database path
GOLD_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "gold_prices.db")

class GoldDB:
    """مدير قاعدة بيانات الذهب"""
    
    def __init__(self):
        self.db_path = GOLD_DB_PATH
        self._init_db()
    
    def _init_db(self):
        """إنشاء الجداول إذا لم تكن موجودة"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Gold prices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gold_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                karat TEXT NOT NULL,
                price_per_gram REAL NOT NULL,
                change REAL,
                currency TEXT DEFAULT 'EGP',
                name_ar TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, karat)
            )
        """)
        
        # Gold history table (international prices)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gold_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                currency TEXT DEFAULT 'USD',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date)
            )
        """)
        
        # Silver history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                currency TEXT DEFAULT 'USD',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def insert_gold_price(self, date: str, karat: str, price: float, change: float = None, currency: str = "EGP", name_ar: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO gold_prices (date, karat, price_per_gram, change, currency, name_ar)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (date, karat, price, change, currency, name_ar))
        conn.commit()
        conn.close()
    
    def get_gold_prices(self, karat: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if karat:
            cursor.execute("""
                SELECT * FROM gold_prices 
                WHERE karat = ? 
                ORDER BY date DESC LIMIT 1
            """, (karat,))
        else:
            cursor.execute("""
                SELECT * FROM gold_prices 
                WHERE date = (SELECT MAX(date) FROM gold_prices)
            """)
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def insert_gold_history(self, records: List[Dict]):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for r in records:
            cursor.execute("""
                INSERT OR REPLACE INTO gold_history (date, open, high, low, close, volume, currency)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (r.get('date'), r.get('open'), r.get('high'), r.get('low'), r.get('close'), r.get('volume'), r.get('currency', 'USD')))
        
        conn.commit()
        conn.close()
    
    def get_gold_history(self, days: int = 365):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM gold_history 
            ORDER BY date DESC LIMIT ?
        """, (days,))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def insert_silver_history(self, records: List[Dict]):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for r in records:
            cursor.execute("""
                INSERT OR REPLACE INTO silver_history (date, open, high, low, close, volume, currency)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (r.get('date'), r.get('open'), r.get('high'), r.get('low'), r.get('close'), r.get('volume'), r.get('currency', 'USD')))
        
        conn.commit()
        conn.close()
    
    def get_silver_history(self, days: int = 365):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM silver_history 
            ORDER BY date DESC LIMIT ?
        """, (days,))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]

gold_db = GoldDB()

@app.get("/api/gold")
async def get_gold_prices():
    """الحصول على أسعار الذهب الحالية"""
    try:
        prices = gold_db.get_gold_prices()
        
        # Default prices if no data
        if not prices:
            default_prices = {
                "success": True,
                "source": "default",
                "prices": {
                    "karat_24": {"price_per_gram": 4250, "name_ar": "عيار 24"},
                    "karat_22": {"price_per_gram": 3895, "name_ar": "عيار 22"},
                    "karat_21": {"price_per_gram": 3718, "name_ar": "عيار 21"},
                    "karat_18": {"price_per_gram": 3187, "name_ar": "عيار 18"},
                    "ounce": {"price": 3320, "name_ar": "الأونصة"}
                },
                "currency": "EGP",
                "timestamp": datetime.now().isoformat()
            }
            return default_prices
        
        # Format prices
        formatted = {}
        for p in prices:
            karat = p.get('karat', '')
            formatted[f"karat_{karat}"] = {
                "price_per_gram": p.get('price_per_gram'),
                "change": p.get('change'),
                "name_ar": p.get('name_ar', f"عيار {karat}"),
                "currency": p.get('currency', 'EGP')
            }
        
        return {
            "success": True,
            "source": "database",
            "prices": formatted,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting gold prices: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/gold/history")
async def get_gold_history(days: int = Query(365, ge=1, le=1825)):
    """الحصول على السجل التاريخي للذهب"""
    try:
        history = gold_db.get_gold_history(days)
        
        if not history:
            # Generate sample data if no data
            sample_data = []
            base_price = 2000  # USD per ounce
            for i in range(days):
                date = datetime.now() - timedelta(days=days-i)
                variation = np.random.uniform(-50, 50)
                price = base_price + variation
                sample_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": price - np.random.uniform(0, 10),
                    "high": price + np.random.uniform(0, 20),
                    "low": price - np.random.uniform(0, 20),
                    "close": price,
                    "currency": "USD"
                })
            
            return {
                "success": True,
                "source": "generated",
                "note": "Sample data - no historical data available",
                "count": len(sample_data),
                "history": sample_data
            }
        
        return {
            "success": True,
            "source": "database",
            "count": len(history),
            "history": history
        }
    
    except Exception as e:
        logger.error(f"Error getting gold history: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/gold/history")
async def add_gold_history(records: List[Dict]):
    """إضافة سجل تاريخي للذهب"""
    try:
        gold_db.insert_gold_history(records)
        return {
            "success": True,
            "message": f"Added {len(records)} gold history records"
        }
    except Exception as e:
        logger.error(f"Error adding gold history: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/silver/history")
async def get_silver_history(days: int = Query(365, ge=1, le=1825)):
    """الحصول على السجل التاريخي للفضة"""
    try:
        history = gold_db.get_silver_history(days)
        
        if not history:
            # Generate sample data
            sample_data = []
            base_price = 25  # USD per ounce
            for i in range(days):
                date = datetime.now() - timedelta(days=days-i)
                variation = np.random.uniform(-2, 2)
                price = base_price + variation
                sample_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": price - np.random.uniform(0, 0.5),
                    "high": price + np.random.uniform(0, 1),
                    "low": price - np.random.uniform(0, 1),
                    "close": price,
                    "currency": "USD"
                })
            
            return {
                "success": True,
                "source": "generated",
                "note": "Sample data - no historical data available",
                "count": len(sample_data),
                "history": sample_data
            }
        
        return {
            "success": True,
            "source": "database",
            "count": len(history),
            "history": history
        }
    
    except Exception as e:
        logger.error(f"Error getting silver history: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/silver/history")
async def add_silver_history(records: List[Dict]):
    """إضافة سجل تاريخي للفضة"""
    try:
        gold_db.insert_silver_history(records)
        return {
            "success": True,
            "message": f"Added {len(records)} silver history records"
        }
    except Exception as e:
        logger.error(f"Error adding silver history: {e}")
        return {"success": False, "error": str(e)}

async def _get_gold_history_data(days: int = 365):
    """Helper function to get gold history data"""
    try:
        history = gold_db.get_gold_history(days)
        
        if not history:
            # Generate sample data if no data
            sample_data = []
            base_price = 2000  # USD per ounce
            for i in range(days):
                date = datetime.now() - timedelta(days=days-i)
                variation = np.random.uniform(-50, 50)
                price = base_price + variation
                sample_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": price - np.random.uniform(0, 10),
                    "high": price + np.random.uniform(0, 20),
                    "low": price - np.random.uniform(0, 20),
                    "close": price,
                    "currency": "USD"
                })
            return {"success": True, "history": sample_data, "source": "generated"}
        
        return {"success": True, "history": history, "source": "database"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/gold/analysis")
async def analyze_gold(days: int = Query(365, ge=30, le=1825)):
    """تحليل فني للذهب"""
    try:
        history = await _get_gold_history_data(days)
        
        if not history.get("success"):
            return history
        
        data = history.get("history", [])
        
        if len(data) < 30:
            return {"success": False, "error": "Insufficient data for analysis"}
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high']) if 'high' in df.columns else df['close']
        df['low'] = pd.to_numeric(df['low']) if 'low' in df.columns else df['close']
        
        # Calculate indicators
        analysis = {
            "current_price": df['close'].iloc[-1],
            "rsi": TechnicalAnalysis.calculate_rsi(df['close']).iloc[-1],
            "sma_20": TechnicalAnalysis.calculate_sma(df['close'], 20).iloc[-1] if len(df) >= 20 else None,
            "sma_50": TechnicalAnalysis.calculate_sma(df['close'], 50).iloc[-1] if len(df) >= 50 else None,
        }
        
        # MACD
        macd = TechnicalAnalysis.calculate_macd(df['close'])
        analysis["macd"] = macd['macd'].iloc[-1]
        analysis["macd_signal"] = macd['signal'].iloc[-1]
        analysis["macd_histogram"] = macd['histogram'].iloc[-1]
        
        # Bollinger
        bb = TechnicalAnalysis.calculate_bollinger(df['close'])
        analysis["bb_upper"] = bb['upper'].iloc[-1]
        analysis["bb_lower"] = bb['lower'].iloc[-1]
        
        # Generate signals
        signals = []
        
        if analysis["rsi"] < 30:
            signals.append({"indicator": "RSI", "signal": "oversold", "action": "buy"})
        elif analysis["rsi"] > 70:
            signals.append({"indicator": "RSI", "signal": "overbought", "action": "sell"})
        
        if analysis["macd_histogram"] > 0:
            signals.append({"indicator": "MACD", "signal": "bullish", "action": "buy"})
        else:
            signals.append({"indicator": "MACD", "signal": "bearish", "action": "sell"})
        
        buy_signals = sum(1 for s in signals if s.get("action") == "buy")
        sell_signals = sum(1 for s in signals if s.get("action") == "sell")
        
        if buy_signals > sell_signals:
            trend = "bullish"
        elif sell_signals > buy_signals:
            trend = "bearish"
        else:
            trend = "neutral"
        
        return {
            "success": True,
            "asset": "Gold",
            "analysis": analysis,
            "signals": signals,
            "trend": trend,
            "date_range": {
                "start": data[-1].get("date") if data else None,
                "end": data[0].get("date") if data else None
            }
        }
    
    except Exception as e:
        logger.error(f"Error analyzing gold: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# GOLD HISTORY ENDPOINTS - سجل أسعار الذهب
# ============================================================

@app.get("/api/gold/history")
async def get_gold_history(
    karat: str = Query("24", description="Gold karat (24, 22, 21, 18, etc.)"),
    days: int = Query(30, ge=1, le=365, description="Number of days")
):
    """الحصول على سجل أسعار الذهب التاريخي"""
    try:
        # Try to get from database
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_str = start_date.strftime("%Y-%m-%d")
        
        # Check if gold_price_history table exists
        try:
            history = db.execute_query(f"""
                SELECT karat, price_per_gram, change, currency, recorded_at, source
                FROM gold_price_history
                WHERE karat = ? AND recorded_at >= ?
                ORDER BY recorded_at ASC
            """, (karat, start_str))
            
            if history:
                return {
                    "success": True,
                    "karat": karat,
                    "days": days,
                    "count": len(history),
                    "data": history,
                    "source": "database",
                    "timestamp": datetime.now().isoformat()
                }
        except:
            pass  # Table doesn't exist
        
        # Return simulated data if no database data
        # Generate realistic gold price history
        base_price = {
            "24": 4250,
            "22": 3895,
            "21": 3718,
            "18": 3187,
            "16": 2833,
            "14": 2479,
            "12": 2125,
            "10": 1770,
            "8": 1416
        }.get(karat, 4000)
        
        history = []
        for i in range(days, 0, -1):
            date = end_date - timedelta(days=i)
            # Add some realistic variation
            variation = (hash(date.strftime("%Y-%m-%d")) % 200 - 100) / 100 * 0.02  # ±2% variation
            price = base_price * (1 + variation)
            change = variation * 100
            
            history.append({
                "karat": karat,
                "price_per_gram": round(price, 2),
                "change": round(change, 2),
                "currency": "EGP",
                "recorded_at": date.strftime("%Y-%m-%dT00:00:00"),
                "source": "estimated"
            })
        
        return {
            "success": True,
            "karat": karat,
            "days": days,
            "count": len(history),
            "data": history,
            "source": "estimated",
            "note": "Historical data estimated based on current prices",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting gold history: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/gold/history/all")
async def get_all_gold_history(days: int = Query(30, ge=1, le=365)):
    """الحصول على سجل أسعار كل عيارات الذهب"""
    try:
        karats = ["24", "22", "21", "18", "16", "14", "12", "10", "8"]
        all_history = {}
        
        for karat in karats:
            result = await get_gold_history(karat, days)
            if result.get("success"):
                all_history[karat] = result.get("data", [])
        
        return {
            "success": True,
            "days": days,
            "karats": list(all_history.keys()),
            "data": all_history,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting all gold history: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/gold/karat/analysis")
async def analyze_gold_by_karat(karat: str = Query("24"), days: int = Query(90, ge=30, le=365)):
    """تحليل أسعار الذهب حسب العيار"""
    try:
        # Get history
        history_result = await get_gold_history(karat, days)
        
        if not history_result.get("success") or not history_result.get("data"):
            return {"success": False, "error": "No gold history data available"}
        
        history = history_result["data"]
        
        # Convert to DataFrame
        df = pd.DataFrame(history)
        df['price_per_gram'] = pd.to_numeric(df['price_per_gram'])
        
        if len(df) < 14:
            return {"success": False, "error": "Insufficient data for analysis"}
        
        # Calculate indicators
        analysis = {}
        
        prices = df['price_per_gram']
        
        # Moving Averages
        analysis['sma_20'] = TechnicalAnalysis.calculate_sma(prices, 20).iloc[-1] if len(prices) >= 20 else None
        analysis['sma_50'] = TechnicalAnalysis.calculate_sma(prices, 50).iloc[-1] if len(prices) >= 50 else None
        analysis['ema_12'] = TechnicalAnalysis.calculate_ema(prices, 12).iloc[-1]
        analysis['ema_26'] = TechnicalAnalysis.calculate_ema(prices, 26).iloc[-1]
        
        # RSI
        analysis['rsi'] = TechnicalAnalysis.calculate_rsi(prices).iloc[-1]
        
        # MACD
        macd = TechnicalAnalysis.calculate_macd(prices)
        analysis['macd'] = macd['macd'].iloc[-1]
        analysis['macd_signal'] = macd['signal'].iloc[-1]
        analysis['macd_histogram'] = macd['histogram'].iloc[-1]
        
        # Bollinger Bands
        bb = TechnicalAnalysis.calculate_bollinger(prices)
        analysis['bb_upper'] = bb['upper'].iloc[-1]
        analysis['bb_middle'] = bb['middle'].iloc[-1]
        analysis['bb_lower'] = bb['lower'].iloc[-1]
        
        # Current price
        current_price = prices.iloc[-1]
        analysis['current_price'] = current_price
        
        # Price stats
        analysis['high_period'] = prices.max()
        analysis['low_period'] = prices.min()
        analysis['avg_period'] = prices.mean()
        analysis['price_range'] = analysis['high_period'] - analysis['low_period']
        
        # Generate signals
        signals = []
        
        # RSI Signal
        if analysis['rsi'] < 30:
            signals.append({"indicator": "RSI", "signal": "oversold", "value": round(analysis['rsi'], 2), "action": "buy"})
        elif analysis['rsi'] > 70:
            signals.append({"indicator": "RSI", "signal": "overbought", "value": round(analysis['rsi'], 2), "action": "sell"})
        else:
            signals.append({"indicator": "RSI", "signal": "neutral", "value": round(analysis['rsi'], 2), "action": "hold"})
        
        # MACD Signal
        if analysis['macd_histogram'] > 0:
            signals.append({"indicator": "MACD", "signal": "bullish", "value": round(analysis['macd_histogram'], 2), "action": "buy"})
        else:
            signals.append({"indicator": "MACD", "signal": "bearish", "value": round(analysis['macd_histogram'], 2), "action": "sell"})
        
        # Trend
        if analysis['sma_20'] and current_price > analysis['sma_20']:
            signals.append({"indicator": "SMA20", "signal": "above", "value": round(analysis['sma_20'], 2), "action": "buy"})
        elif analysis['sma_20']:
            signals.append({"indicator": "SMA20", "signal": "below", "value": round(analysis['sma_20'], 2), "action": "sell"})
        
        # Overall recommendation
        buy_signals = sum(1 for s in signals if s['action'] == 'buy')
        sell_signals = sum(1 for s in signals if s['action'] == 'sell')
        
        if buy_signals > sell_signals:
            recommendation = "buy"
            confidence = min(buy_signals / len(signals) * 100, 90)
        elif sell_signals > buy_signals:
            recommendation = "sell"
            confidence = min(sell_signals / len(signals) * 100, 90)
        else:
            recommendation = "hold"
            confidence = 50
        
        return {
            "success": True,
            "karat": karat,
            "analysis": analysis,
            "signals": signals,
            "recommendation": recommendation,
            "confidence": round(confidence, 1),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error analyzing gold: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# CURRENCY CONVERTER - محول العملات
# ============================================================

# Cache for exchange rates
exchange_rates_cache: Dict[str, Any] = {
    "rates": None,
    "timestamp": 0
}

RATES_CACHE_DURATION = 3600000  # 1 hour

# All world currencies
WORLD_CURRENCIES = {
    "USD": {"name": "US Dollar", "name_ar": "دولار أمريكي", "symbol": "$"},
    "EUR": {"name": "Euro", "name_ar": "يورو", "symbol": "€"},
    "GBP": {"name": "British Pound", "name_ar": "جنيه إسترليني", "symbol": "£"},
    "JPY": {"name": "Japanese Yen", "name_ar": "ين ياباني", "symbol": "¥"},
    "CNY": {"name": "Chinese Yuan", "name_ar": "يوان صيني", "symbol": "¥"},
    "INR": {"name": "Indian Rupee", "name_ar": "روبية هندية", "symbol": "₹"},
    "AUD": {"name": "Australian Dollar", "name_ar": "دولار أسترالي", "symbol": "A$"},
    "CAD": {"name": "Canadian Dollar", "name_ar": "دولار كندي", "symbol": "C$"},
    "CHF": {"name": "Swiss Franc", "name_ar": "فرنك سويسري", "symbol": "Fr"},
    "KRW": {"name": "South Korean Won", "name_ar": "وون كوري جنوبي", "symbol": "₩"},
    "SGD": {"name": "Singapore Dollar", "name_ar": "دولار سنغافوري", "symbol": "S$"},
    "HKD": {"name": "Hong Kong Dollar", "name_ar": "دولار هونج كونج", "symbol": "HK$"},
    "NOK": {"name": "Norwegian Krone", "name_ar": "كرون نرويجي", "symbol": "kr"},
    "SEK": {"name": "Swedish Krona", "name_ar": "كرون سويدي", "symbol": "kr"},
    "DKK": {"name": "Danish Krone", "name_ar": "كرون دنماركي", "symbol": "kr"},
    "NZD": {"name": "New Zealand Dollar", "name_ar": "دولار نيوزيلندي", "symbol": "NZ$"},
    "ZAR": {"name": "South African Rand", "name_ar": "راند جنوب أفريقي", "symbol": "R"},
    "RUB": {"name": "Russian Ruble", "name_ar": "روبل روسي", "symbol": "₽"},
    "TRY": {"name": "Turkish Lira", "name_ar": "ليرة تركية", "symbol": "₺"},
    "BRL": {"name": "Brazilian Real", "name_ar": "ريال برازيلي", "symbol": "R$"},
    "MXN": {"name": "Mexican Peso", "name_ar": "بيزو مكسيكي", "symbol": "$"},
    "THB": {"name": "Thai Baht", "name_ar": "بات تايلندي", "symbol": "฿"},
    "IDR": {"name": "Indonesian Rupiah", "name_ar": "روبية إندونيسية", "symbol": "Rp"},
    "MYR": {"name": "Malaysian Ringgit", "name_ar": "رينجيت ماليزي", "symbol": "RM"},
    "PHP": {"name": "Philippine Peso", "name_ar": "بيزو فلبيني", "symbol": "₱"},
    "VND": {"name": "Vietnamese Dong", "name_ar": "دونج فيتنامي", "symbol": "₫"},
    "PLN": {"name": "Polish Zloty", "name_ar": "زلاتي بولندي", "symbol": "zł"},
    "SAR": {"name": "Saudi Riyal", "name_ar": "ريال سعودي", "symbol": "﷼"},
    "AED": {"name": "UAE Dirham", "name_ar": "درهم إماراتي", "symbol": "د.إ"},
    "KWD": {"name": "Kuwaiti Dinar", "name_ar": "دينار كويتي", "symbol": "د.ك"},
    "QAR": {"name": "Qatari Riyal", "name_ar": "ريال قطري", "symbol": "﷼"},
    "BHD": {"name": "Bahraini Dinar", "name_ar": "دينار بحريني", "symbol": "د.ب"},
    "OMR": {"name": "Omani Rial", "name_ar": "ريال عماني", "symbol": "﷼"},
    "EGP": {"name": "Egyptian Pound", "name_ar": "جنيه مصري", "symbol": "ج.م"},
    "ILS": {"name": "Israeli Shekel", "name_ar": "شيكل إسرائيلي", "symbol": "₪"},
    "PKR": {"name": "Pakistani Rupee", "name_ar": "روبية باكستانية", "symbol": "₨"},
    "BDT": {"name": "Bangladeshi Taka", "name_ar": "تاكا بنغلاديشية", "symbol": "৳"},
    "NGN": {"name": "Nigerian Naira", "name_ar": "نايرا نيجيرية", "symbol": "₦"},
    "KES": {"name": "Kenyan Shilling", "name_ar": "شيلينج كيني", "symbol": "KSh"},
    "GHS": {"name": "Ghanaian Cedi", "name_ar": "سيدي غاني", "symbol": "₵"},
    "ETB": {"name": "Ethiopian Birr", "name_ar": "بير إثيوبي", "symbol": "Br"},
    "TZS": {"name": "Tanzanian Shilling", "name_ar": "شيلينج تنزاني", "symbol": "TSh"},
    "UGX": {"name": "Ugandan Shilling", "name_ar": "شيلينج أوغندي", "symbol": "USh"},
    "MAD": {"name": "Moroccan Dirham", "name_ar": "درهم مغربي", "symbol": "د.م."},
    "TND": {"name": "Tunisian Dinar", "name_ar": "دينار تونسي", "symbol": "د.ت"},
    "DZD": {"name": "Algerian Dinar", "name_ar": "دينار جزائري", "symbol": "د.ج"},
    "LYD": {"name": "Libyan Dinar", "name_ar": "دينار ليبي", "symbol": "ل.د"},
    "SDG": {"name": "Sudanese Pound", "name_ar": "جنيه سوداني", "symbol": "ج.س"},
    "JOD": {"name": "Jordanian Dinar", "name_ar": "دينار أردني", "symbol": "د.أ"},
    "LBP": {"name": "Lebanese Pound", "name_ar": "جنيه لبناني", "symbol": "ل.ل"},
    "SYP": {"name": "Syrian Pound", "name_ar": "جنيه سوري", "symbol": "ل.س"},
    "IQD": {"name": "Iraqi Dinar", "name_ar": "دينار عراقي", "symbol": "ع.د"},
    "YER": {"name": "Yemeni Rial", "name_ar": "ريال يمني", "symbol": "﷼"},
    "AFN": {"name": "Afghan Afghani", "name_ar": "أفغاني أفغاني", "symbol": "؋"},
    "IRR": {"name": "Iranian Rial", "name_ar": "ريال إيراني", "symbol": "﷼"},
    "ARS": {"name": "Argentine Peso", "name_ar": "بيزو أرجنتيني", "symbol": "$"},
    "CLP": {"name": "Chilean Peso", "name_ar": "بيزو تشيلي", "symbol": "$"},
    "COP": {"name": "Colombian Peso", "name_ar": "بيزو كولومبي", "symbol": "$"},
    "PEN": {"name": "Peruvian Sol", "name_ar": "سول بيروفي", "symbol": "S/"},
    "CZK": {"name": "Czech Koruna", "name_ar": "كرونا تشيكية", "symbol": "Kč"},
    "HUF": {"name": "Hungarian Forint", "name_ar": "فورنت مجري", "symbol": "Ft"},
    "RON": {"name": "Romanian Leu", "name_ar": "ليو روماني", "symbol": "lei"},
    "BGN": {"name": "Bulgarian Lev", "name_ar": "ليف بلغاري", "symbol": "лв"},
    "HRK": {"name": "Croatian Kuna", "name_ar": "كونا كرواتية", "symbol": "kn"},
    "UAH": {"name": "Ukrainian Hryvnia", "name_ar": "هريفنيا أوكرانية", "symbol": "₴"},
}

async def fetch_exchange_rates(base: str = "USD") -> Optional[Dict]:
    """جلب أسعار الصرف من API مجاني"""
    try:
        # Use exchangerate-api.com (free tier)
        async with aiohttp.ClientSession() as session:
            url = f"https://api.exchangerate-api.com/v4/latest/{base}"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Exchange rate API error: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error fetching exchange rates: {e}")
        return None

@app.get("/api/currency/rates")
async def get_exchange_rates(base: str = "USD"):
    """الحصول على أسعار الصرف"""
    try:
        now = datetime.now().timestamp() * 1000
        
        # Check cache
        if exchange_rates_cache["rates"] and (now - exchange_rates_cache["timestamp"]) < RATES_CACHE_DURATION:
            if exchange_rates_cache["rates"].get("base") == base:
                return {
                    "success": True,
                    "base": base,
                    "rates": exchange_rates_cache["rates"]["rates"],
                    "cached": True,
                    "timestamp": datetime.now().isoformat()
                }
        
        # Fetch new rates
        data = await fetch_exchange_rates(base)
        
        if not data:
            return {"success": False, "error": "Failed to fetch exchange rates"}
        
        # Update cache
        exchange_rates_cache["rates"] = data
        exchange_rates_cache["timestamp"] = now
        
        return {
            "success": True,
            "base": data.get("base"),
            "rates": data.get("rates"),
            "cached": False,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting exchange rates: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/currency/convert")
async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str
):
    """تحويل العملات"""
    try:
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        # Get rates
        rates_data = await get_exchange_rates("USD")
        
        if not rates_data.get("success"):
            return rates_data
        
        rates = rates_data.get("rates", {})
        
        # Convert through USD
        if from_currency == "USD":
            usd_amount = amount
        else:
            from_rate = rates.get(from_currency)
            if not from_rate:
                return {"success": False, "error": f"Currency {from_currency} not found"}
            usd_amount = amount / from_rate
        
        if to_currency == "USD":
            result = usd_amount
        else:
            to_rate = rates.get(to_currency)
            if not to_rate:
                return {"success": False, "error": f"Currency {to_currency} not found"}
            result = usd_amount * to_rate
        
        return {
            "success": True,
            "amount": amount,
            "from_currency": from_currency,
            "from_name": WORLD_CURRENCIES.get(from_currency, {}).get("name", from_currency),
            "from_name_ar": WORLD_CURRENCIES.get(from_currency, {}).get("name_ar", from_currency),
            "to_currency": to_currency,
            "to_name": WORLD_CURRENCIES.get(to_currency, {}).get("name", to_currency),
            "to_name_ar": WORLD_CURRENCIES.get(to_currency, {}).get("name_ar", to_currency),
            "result": round(result, 4),
            "rate": round(rates.get(to_currency, 1) / rates.get(from_currency, 1), 6) if from_currency != "USD" else rates.get(to_currency, 1),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error converting currency: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/currency/list")
async def get_currency_list():
    """الحصول على قائمة كل العملات"""
    return {
        "success": True,
        "count": len(WORLD_CURRENCIES),
        "currencies": WORLD_CURRENCIES
    }

@app.get("/api/currency/{currency}")
async def get_currency_detail(currency: str):
    """تفاصيل عملة محددة"""
    try:
        currency = currency.upper()
        
        if currency not in WORLD_CURRENCIES:
            return {"success": False, "error": f"Currency {currency} not found"}
        
        # Get current rate against USD
        rates_data = await get_exchange_rates("USD")
        rate = rates_data.get("rates", {}).get(currency)
        
        return {
            "success": True,
            "code": currency,
            "name": WORLD_CURRENCIES[currency].get("name"),
            "name_ar": WORLD_CURRENCIES[currency].get("name_ar"),
            "symbol": WORLD_CURRENCIES[currency].get("symbol"),
            "rate_vs_usd": rate,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting currency detail: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# AI ANALYSIS ENDPOINTS
# ============================================================
# Import AI modules
try:
    from ai_investment_analyzer import InvestmentAIAnalyzer, HourlyAnalysisScheduler
    from ai_news_agent import AINewsAgent
    AI_MODULES_AVAILABLE = True
except ImportError:
    AI_MODULES_AVAILABLE = False
    logger.warning("AI modules not available. Install ai_investment_analyzer and ai_news_agent.")

# Initialize AI components
ai_analyzer = None
ai_news_agent = None
ai_scheduler = None

def init_ai_components():
    """تهيئة مكونات AI"""
    global ai_analyzer, ai_news_agent, ai_scheduler
    
    if not AI_MODULES_AVAILABLE:
        return False
    
    try:
        # Get Ollama URL from environment or default
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        model = os.getenv("AI_MODEL", "glm-4-flash")
        
        ai_analyzer = InvestmentAIAnalyzer(ollama_url=ollama_url, model=model)
        ai_news_agent = AINewsAgent(ollama_url=ollama_url, model=model)
        ai_scheduler = HourlyAnalysisScheduler(ai_analyzer)
        
        logger.info(f"AI components initialized. Ollama: {ollama_url}, Model: {model}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize AI components: {e}")
        return False

@app.get("/api/ai/health")
async def ai_health():
    """التحقق من حالة AI"""
    if not AI_MODULES_AVAILABLE:
        return {
            "status": "unavailable",
            "error": "AI modules not installed",
            "ollama_available": False,
            "model": None,
            "last_analysis": None
        }
    
    if ai_analyzer is None:
        init_ai_components()
    
    return {
        "status": "healthy" if (ai_analyzer and ai_analyzer.ollama_available) else "degraded",
        "ollama_available": ai_analyzer.ollama_available if ai_analyzer else False,
        "model": ai_analyzer.model if ai_analyzer else None,
        "last_analysis": ai_scheduler.last_run.isoformat() if (ai_scheduler and ai_scheduler.last_run) else None
    }

@app.get("/api/ai/analyze/{ticker}")
async def ai_analyze_stock(ticker: str):
    """تحليل AI لسهم محدد - يقرأ من النتائج المحسوبة مسبقاً (Data Engine). لا يستدعي LM Studio إلا كاحتياطي."""
    try:
        # 1. Try precomputed results FIRST (instant)
        row = db.execute_one("SELECT * FROM precomputed_indicators WHERE ticker = ?", (ticker.upper(),))
        if row:
            return _convert_numpy({
                "success": True,
                "source": "precomputed",
                "ticker": ticker.upper(),
                "recommendation": row.get("action") or row.get("recommendation") or "HOLD",
                "confidence": row.get("confidence", 0),
                "trend": row.get("trend", "neutral"),
                "volatility": row.get("volatility", "medium"),
                "reasons": json.loads(row.get("reasons") or row.get("reasoning") or '[]'),
                "indicators": {
                    "rsi": row.get("rsi"),
                    "macd": row.get("macd"),
                    "macd_signal": row.get("macd_signal"),
                    "bollinger_position": row.get("bollinger_position"),
                    "sma_20": row.get("sma_20"),
                    "sma_50": row.get("sma_50"),
                    "ema_12": row.get("ema_12"),
                    "ema_26": row.get("ema_26")
                },
                "computed_at": row.get("computed_at")
            })
        
        # 2. Fallback to LM Studio ONLY if not precomputed
        from ai_local_engine import ai_engine
        result = ai_engine.analyze_stock(ticker.upper())
        if result:
            return _convert_numpy(result.__dict__)
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"AI analysis error for {ticker}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/run-hourly")
async def ai_run_hourly_analysis(request: Request):
    """تشغيل التحليل الساعي"""
    if not AI_MODULES_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI modules not available")
    
    if ai_scheduler is None:
        init_ai_components()
    
    try:
        body = await request.json() if request.headers.get("content-type") else {}
        tickers = body.get("tickers") if isinstance(body, dict) else None
        
        results = ai_scheduler.run_analysis(tickers)
        
        return {
            "success": True,
            "analyzed_count": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"Hourly analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/recommendations")
async def ai_get_recommendations(limit: int = Query(20, ge=1, le=100)):
    """جلب تحليلات AI"""
    if not AI_MODULES_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI modules not available")
    
    import sqlite3
    
    try:
        conn = sqlite3.connect(ai_analyzer.custom_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM ai_recommendations 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return {"success": True, "count": len(results), "results": results}
    except Exception as e:
        logger.error(f"Error getting AI recommendations: {e}")
        return {"success": False, "error": str(e), "results": []}

@app.get("/api/ai/market-summary")
async def ai_market_summary():
    """ملخص السوق من AI"""
    if not AI_MODULES_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI modules not available")
    
    if ai_analyzer is None:
        init_ai_components()
    
    try:
        summary = ai_analyzer.generate_market_summary()
        return summary
    except Exception as e:
        logger.error(f"Market summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/news")
async def ai_get_news(topic: str = Query("البورصة المصرية")):
    """جلب أخبار السوق من AI"""
    if not AI_MODULES_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI modules not available")
    
    if ai_news_agent is None:
        init_ai_components()
    
    try:
        news = ai_news_agent.search_news_via_ai(topic)
        return {"success": True, "topic": topic, "news": news}
    except Exception as e:
        logger.error(f"News search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/daily-brief")
async def ai_daily_brief():
    """ملخص يومي من AI"""
    if not AI_MODULES_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI modules not available")
    
    if ai_news_agent is None:
        init_ai_components()
    
    try:
        brief = ai_news_agent.get_egx_daily_brief()
        return {"success": True, "brief": brief}
    except Exception as e:
        logger.error(f"Daily brief error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Helper: Convert numpy types to Python native types
# ============================================================
def _convert_numpy(obj):
    """Convert numpy/pandas types to native Python types for JSON serialization"""
    import numpy as np
    if isinstance(obj, dict):
        return {k: _convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_numpy(v) for v in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif hasattr(obj, 'item'):  # numpy scalar
        return obj.item()
    return obj

# ============================================================
# SYNC ENDPOINTS - مزامنة البيانات من الموقع الحي
# ============================================================
@app.post("/api/sync/from-website")
async def sync_from_website(background_tasks: BackgroundTasks):
    """مزامنة الأسهم والبيانات التاريخية من الموقع الحي"""
    from sync_from_website import sync_all_from_website
    try:
        result = sync_all_from_website()
        return _convert_numpy(result)
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sync/stocks")
async def sync_stocks_only():
    """مزامنة قائمة الأسهم فقط"""
    from sync_from_website import sync_stocks_from_website
    try:
        result = sync_stocks_from_website()
        return _convert_numpy(result)
    except Exception as e:
        logger.error(f"Sync stocks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sync/history")
async def sync_history_only(tickers: Optional[List[str]] = None, max_stocks: int = 50):
    """مزامنة البيانات التاريخية"""
    from sync_from_website import sync_price_history_from_website
    try:
        result = sync_price_history_from_website(tickers, max_stocks)
        return _convert_numpy(result)
    except Exception as e:
        logger.error(f"Sync history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# MUBASHER LOCAL SYNC - سحب بيانات Mubasher المحلية
# ============================================================
@app.post("/api/sync/mubasher")
async def sync_mubasher(background_tasks: BackgroundTasks):
    """مزامنة كل الأسهم من Mubasher المحلي"""
    try:
        result = mubasher_sync.full_sync()
        if result.get('success'):
            background_tasks.add_task(data_engine.compute_all_indicators, asset_type='stock')
            return _convert_numpy({
                "success": True,
                "message": "تم سحب البيانات من MubasherTrade وتحديث قاعدة البيانات",
                "history_sync": result.get('history_sync', {}),
                "trade_sync": result.get('trade_sync', {}),
                "note": "جاري إعادة حساب المؤشرات في الخلفية"
            })
        else:
            return _convert_numpy({"success": False, "error": result.get('error', 'Unknown error')})
    except Exception as e:
        logger.error(f"Mubasher sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sync/mubasher/status")
async def mubasher_status():
    """حالة اتصال Mubasher"""
    from mubasher_sync import INTRADAY_DB, HISTORY_DB
    import os
    return {
        "intraday_exists": os.path.exists(INTRADAY_DB),
        "history_exists": os.path.exists(HISTORY_DB),
        "intraday_path": INTRADAY_DB,
        "history_path": HISTORY_DB
    }

@app.get("/api/mubasher/indicators/{ticker}")
async def mubasher_indicators(ticker: str):
    """مؤشرات سهم من Mubasher المحلي"""
    from mubasher_sync import get_mubasher_indicators
    try:
        result = get_mubasher_indicators(ticker)
        if not result:
            raise HTTPException(status_code=404, detail=f"No Mubasher data for {ticker}")
        return _convert_numpy(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mubasher indicators error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sync/mubasher-paste")
async def sync_mubasher_paste(request: Request):
    """تحديث أسعار الأسهم بلصق بيانات Mubasher Trade مباشرة"""
    try:
        body = await request.json()
        raw_text = body.get("data", "")
        if not raw_text:
            return {"success": False, "error": "No data provided"}
        
        lines = raw_text.strip().split('\n')
        if len(lines) < 2:
            return {"success": False, "error": "Invalid data format"}
        
        updated = 0
        inserted = 0
        errors = 0
        details = []
        
        conn = sqlite3.connect(DB_PATH)
        try:
            cursor = conn.cursor()
            for line in lines[1:]:  # Skip header
                parts = line.split('\t')
                if len(parts) < 7:
                    continue
                
                ticker = parts[0].strip().upper()
                name_ar = parts[1].strip() if len(parts) > 1 else ''
                try:
                    current_price = float(parts[2].replace(',', '')) if parts[2] else 0
                except:
                    current_price = 0
                try:
                    change = float(parts[5].replace(',', '')) if parts[5] else 0
                except:
                    change = 0
                try:
                    change_percent = float(parts[6].replace(',', '').replace('%', '')) if parts[6] else 0
                except:
                    change_percent = 0
                try:
                    bid = float(parts[7].replace(',', '')) if len(parts) > 7 and parts[7] else 0
                except:
                    bid = 0
                try:
                    ask = float(parts[8].replace(',', '')) if len(parts) > 8 and parts[8] else 0
                except:
                    ask = 0
                try:
                    volume = int(parts[9].replace(',', '')) if len(parts) > 9 and parts[9] else 0
                except:
                    volume = 0
                try:
                    trades = int(parts[10].replace(',', '')) if len(parts) > 10 and parts[10] else 0
                except:
                    trades = 0
                
                # Calculate previous_close from current_price and change
                previous_close = current_price - change if current_price and change else 0
                
                cursor.execute("SELECT id FROM stocks WHERE ticker = ?", (ticker,))
                row = cursor.fetchone()
                
                if row:
                    cursor.execute("""
                        UPDATE stocks SET
                            current_price = ?, previous_close = ?, volume = ?,
                            last_update = ?, is_active = 1
                        WHERE ticker = ?
                    """, (current_price, previous_close, volume, datetime.now().isoformat(), ticker))
                    status = "updated"
                    updated += 1
                else:
                    cursor.execute("""
                        INSERT INTO stocks (ticker, name_ar, current_price, previous_close, volume, is_active, created_at, last_update)
                        VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                    """, (ticker, name_ar, current_price, previous_close, volume, datetime.now().isoformat(), datetime.now().isoformat()))
                    status = "inserted"
                    inserted += 1
                
                details.append({
                    "ticker": ticker,
                    "price": current_price,
                    "change_percent": change_percent,
                    "status": status
                })
            
            conn.commit()
        finally:
            conn.close()
        
        return {
            "success": True,
            "updated": updated,
            "inserted": inserted,
            "errors": errors,
            "total": updated + inserted,
            "details": details
        }
    except Exception as e:
        logger.error(f"Mubasher paste sync error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def _post_to_website(endpoint: str, payload: dict, timeout: int = 30) -> dict:
    """Helper to POST JSON to live website with retry logic"""
    website_url = os.getenv("WEBSITE_URL", "http://72.61.137.86")
    api_key = os.getenv("WEBSITE_API_KEY", "")
    url = f"{website_url}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    text = await resp.text()
                    if resp.status in (200, 201):
                        try:
                            return {"success": True, "status": resp.status, "data": json.loads(text)}
                        except:
                            return {"success": True, "status": resp.status, "text": text}
                    else:
                        if attempt == 2:
                            return {"success": False, "status": resp.status, "error": text[:500]}
                        await asyncio.sleep(2 ** attempt)
        except Exception as e:
            if attempt == 2:
                return {"success": False, "error": str(e)}
            await asyncio.sleep(2 ** attempt)
    return {"success": False, "error": "Max retries exceeded"}


@app.post("/api/sync/push-asset")
async def push_asset_to_website(asset_type: str = Query("stocks", description="stock, crypto, or gold")):
    """Push pre-computed analysis signals to the live website by asset type (Z.AI endpoint)"""
    try:
        signals = data_engine.get_all_signals(asset_type=asset_type)
        if not signals:
            return {"success": False, "error": f"No {asset_type} signals found"}
        
        # Build payload matching Z.AI expected format
        recommendations = []
        for sig in signals:
            reasons = sig.get("reasons", [])
            if isinstance(reasons, list):
                reasons = "; ".join(str(r) for r in reasons)
            recommendations.append({
                "ticker": sig.get("ticker"),
                "action": sig.get("action", "HOLD"),
                "confidence": sig.get("confidence", 50),
                "entry_zone_low": sig.get("entry_zone_low"),
                "entry_zone_high": sig.get("entry_zone_high"),
                "target_1": sig.get("target_1"),
                "target_2": sig.get("target_2"),
                "stop_loss": sig.get("stop_loss"),
                "expected_return_pct": sig.get("expected_return_pct"),
                "reasons": reasons,
                "computed_at": sig.get("computed_at") or datetime.now().isoformat()
            })
        
        # Send in batches of 500 (Z.AI limit)
        batch_size = 500
        total_pushed = 0
        total_failed = 0
        errors = []
        
        for i in range(0, len(recommendations), batch_size):
            batch = recommendations[i:i+batch_size]
            result = await _post_to_website("/api/recommendations/batch", {"recommendations": batch})
            if result.get("success"):
                data = result.get("data", {})
                total_pushed += data.get("inserted", 0) + data.get("updated", 0)
            else:
                total_failed += len(batch)
                errors.append(f"Batch {i//batch_size + 1}: {result.get('error', 'Unknown')}")
        
        return {
            "success": total_failed == 0 or total_pushed > 0,
            "message": f"Pushed {total_pushed} {asset_type} signals ({total_failed} failed)",
            "asset_type": asset_type,
            "total_signals": len(signals),
            "pushed": total_pushed,
            "failed": total_failed,
            "errors": errors[:5]
        }
    except Exception as e:
        logger.error(f"Push asset error: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/sync/push-morning-report")
async def push_morning_report_to_website():
    """Push the generated morning report to the live website (Z.AI endpoint)"""
    try:
        # Generate morning report
        report = _generate_morning_report_sync(limit=10)
        if not report or not report.get("success"):
            return {"success": False, "error": "Failed to generate morning report"}
        
        report_text = report.get("full_text", "")
        report_date = datetime.now().strftime("%Y-%m-%d")
        
        payload = {
            "report_date": report_date,
            "report_text": report_text,
            "generated_at": datetime.now().isoformat()
        }
        
        result = await _post_to_website("/api/reports/morning", payload)
        if result.get("success"):
            return {
                "success": True,
                "message": "Morning report pushed to website",
                "report_date": report_date,
                "text_length": len(report_text),
                "website_response": result.get("data", {})
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "status": result.get("status")
            }
    except Exception as e:
        logger.error(f"Push morning report error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# AUTO SYNC - تشغيل pipeline كامل
# ============================================================
@app.post("/api/sync/external-data")
async def sync_external_data_endpoint():
    """مزامنة البيانات الخارجية: Crypto + Gold + Currency (بدون Yahoo)"""
    try:
        from external_data_sync import sync_all_external_data
        result = await sync_all_external_data()
        return _convert_numpy(result)
    except Exception as e:
        logger.error(f"External data sync error: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/sync/tradingview")
async def sync_tradingview_endpoint(test: bool = Query(False, description="Test mode - 10 stocks only")):
    """سحب بيانات EGX من TradingView (بديل Yahoo و Mubasher)"""
    try:
        from tradingview_sync import sync_tradingview
        result = sync_tradingview(test_mode=test)
        return _convert_numpy(result)
    except Exception as e:
        logger.error(f"TradingView sync error: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/sync/auto-pipeline")
async def run_auto_pipeline(background_tasks: BackgroundTasks, push: bool = Query(True, description="Push results to live website")):
    """تشغيل Pipeline كامل: External Data → Mubasher Sync → Compute → Morning Report → Push to Website"""
    try:
        # Step 0: External data sync (Crypto, Gold, Currency)
        from external_data_sync import sync_all_external_data
        external_result = await sync_all_external_data()
        
        # Step 1: TradingView EGX sync (primary source)
        from tradingview_sync import sync_tradingview
        tv_result = sync_tradingview(test_mode=False)
        
        # Step 1b: Mubasher sync (fallback for tickers not on TradingView)
        sync_result = mubasher_sync.full_sync()
        
        # Step 2: Compute indicators for ALL asset types (background)
        background_tasks.add_task(data_engine.compute_all_indicators, asset_type="stock")
        background_tasks.add_task(data_engine.compute_all_indicators, asset_type="crypto")
        background_tasks.add_task(data_engine.compute_all_indicators, asset_type="gold")
        
        # Step 3: Generate morning report
        morning = _generate_morning_report_sync(limit=10)
        
        # Step 4: Push to website if requested
        push_results = {}
        if push:
            # Push morning report
            report_payload = {
                "report_date": datetime.now().strftime("%Y-%m-%d"),
                "report_text": morning.get("full_text", ""),
                "generated_at": datetime.now().isoformat()
            }
            push_results["morning_report"] = await _post_to_website("/api/reports/morning", report_payload)
            
            # Push signals for each asset type
            for asset_type in ["stock", "crypto", "gold"]:
                signals = data_engine.get_all_signals(asset_type=asset_type)
                if signals:
                    recommendations = []
                    for sig in signals:
                        reasons = sig.get("reasons", [])
                        if isinstance(reasons, list):
                            reasons = "; ".join(str(r) for r in reasons)
                        recommendations.append({
                            "ticker": sig.get("ticker"),
                            "action": sig.get("action", "HOLD"),
                            "confidence": sig.get("confidence", 50),
                            "entry_zone_low": sig.get("entry_zone_low"),
                            "entry_zone_high": sig.get("entry_zone_high"),
                            "target_1": sig.get("target_1"),
                            "target_2": sig.get("target_2"),
                            "stop_loss": sig.get("stop_loss"),
                            "expected_return_pct": sig.get("expected_return_pct"),
                            "reasons": reasons,
                            "computed_at": sig.get("computed_at") or datetime.now().isoformat()
                        })
                    # Send in batches of 500
                    batch_size = 500
                    total_pushed = 0
                    for i in range(0, len(recommendations), batch_size):
                        batch = recommendations[i:i+batch_size]
                        result = await _post_to_website("/api/recommendations/batch", {"recommendations": batch})
                        if result.get("success"):
                            data = result.get("data", {})
                            total_pushed += data.get("inserted", 0) + data.get("updated", 0)
                    push_results[asset_type] = {"pushed": total_pushed, "total": len(signals)}
        
        return {
            "success": True,
            "message": "Pipeline completed" + (" and pushed to website" if push else ""),
            "results": {
                "external_data": external_result,
                "sync": sync_result,
                "compute": {"note": "running in background for stock, crypto, gold"},
                "morning_report": {
                    "count": morning.get("count", 0),
                    "text_length": len(morning.get("full_text", ""))
                },
                "push": push_results if push else {"skipped": True}
            }
        }
    except Exception as e:
        logger.error(f"Auto pipeline error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/sync/morning-report")
async def generate_and_push_morning():
    """توليد التقرير الصباحي ورفعه للموقع الحي"""
    try:
        report = _generate_morning_report_sync(limit=10)
        if not report or not report.get("success"):
            return {"success": False, "error": "Failed to generate morning report"}
        
        payload = {
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "report_text": report.get("full_text", ""),
            "generated_at": datetime.now().isoformat()
        }
        
        result = await _post_to_website("/api/reports/morning", payload)
        if result.get("success"):
            return {
                "success": True,
                "message": "Morning report generated and pushed",
                "report": {
                    "count": report.get("count", 0),
                    "text_length": len(report.get("full_text", ""))
                },
                "website_response": result.get("data", {})
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Push failed"),
                "generated_report": report.get("full_text", "")[:200]
            }
    except Exception as e:
        logger.error(f"Morning report error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# AI LOCAL ENGINE - تحليل AI محلي
# ============================================================
@app.post("/api/ai/analyze-batch")
async def ai_analyze_batch(tickers: List[str]):
    """تحليل مجموعة أسهم"""
    try:
        from ai_local_engine import ai_engine
        results = ai_engine.analyze_batch([t.upper() for t in tickers])
        return _convert_numpy({
            "success": True,
            "count": len(results),
            "recommendations": [r.__dict__ for r in results]
        })
    except Exception as e:
        logger.error(f"AI batch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/push-recommendation")
async def ai_push_recommendation(ticker: str):
    """إرسال التحليل المعتمدة للموقع الحي"""
    try:
        from ai_local_engine import ai_engine
        rec = ai_engine.analyze_stock(ticker.upper())
        if not rec:
            return {"success": False, "error": "Analysis failed"}

        pushed = ai_engine.push_recommendation_to_website(rec)
        return _convert_numpy({
            "success": pushed,
            "ticker": ticker,
            "ai_approved": rec.ai_approved,
            "action": rec.action,
            "message": "Pushed to website" if pushed else "Failed to push"
        })
    except Exception as e:
        logger.error(f"Push recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/status")
async def ai_status():
    """حالة محرك AI"""
    try:
        from ai_local_engine import ai_engine
        return {
            "success": True,
            "lmstudio_available": ai_engine.lmstudio_available,
            "ollama_available": ai_engine.ollama_available,
            "lmstudio_url": LMSTUDIO_URL if hasattr(ai_engine, 'lmstudio_url') else None,
            "ollama_url": OLLAMA_URL if hasattr(ai_engine, 'ollama_url') else None,
            "db_path": DB_PATH,
            "website_url": ai_engine.WEBSITE_URL if hasattr(ai_engine, 'WEBSITE_URL') else None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# CRON / AUTO-SYNC - مزامنة تلقائية
# ============================================================
@app.get("/api/cron/auto-sync")
async def cron_auto_sync(background_tasks: BackgroundTasks):
    """مزامنة تلقائية لكل البيانات"""
    background_tasks.add_task(_auto_sync_task)
    return {
        "success": True,
        "message": "Auto-sync started in background",
        "tasks": ["stocks", "history", "gold", "crypto", "market"]
    }


def _auto_sync_task():
    """مهمة المزامنة التلقائية"""
    import requests
    API = "http://localhost:8010"
    logger.info("[AutoSync] Starting automatic sync...")
    
    tasks = [
        ("stocks", f"{API}/api/sync/stocks", "POST"),
        ("history", f"{API}/api/sync/history?max_stocks=20", "POST"),
        ("mubasher", f"{API}/api/sync/mubasher", "POST"),
        ("gold", f"{API}/api/gold", "GET"),
        ("crypto", f"{API}/api/crypto?limit=50", "GET"),
        ("market", f"{API}/api/market/overview", "GET"),
    ]
    
    results = {}
    for name, url, method in tasks:
        try:
            if method == "POST":
                r = requests.post(url, timeout=120)
            else:
                r = requests.get(url, timeout=30)
            results[name] = {"status": r.status_code, "success": r.status_code == 200}
            logger.info(f"[AutoSync] {name}: {r.status_code}")
        except Exception as e:
            results[name] = {"status": "error", "error": str(e)}
            logger.error(f"[AutoSync] {name} failed: {e}")
    
    logger.info(f"[AutoSync] Completed: {results}")


# ============================================================
# PREDICTIONS - توقعات AI
# ============================================================
@app.get("/api/predictions")
async def get_predictions(
    status: Optional[str] = None,
    ticker: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200)
):
    """توقعات AI المخزنة"""
    try:
        query = "SELECT * FROM ai_engine_results WHERE 1=1"
        params = []
        
        if status:
            query += " AND action = ?"
            params.append(status.upper())
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker.upper())
        
        query += " ORDER BY calculated_at DESC LIMIT ?"
        params.append(limit)
        
        results = db.execute_query(query, tuple(params))
        
        for r in results:
            try:
                r["reasons"] = json.loads(r["reasons"]) if r.get("reasons") else []
            except:
                r["reasons"] = []
        
        stats = {
            "active": db.execute_one("SELECT COUNT(*) as cnt FROM ai_engine_results WHERE action = 'BUY'")["cnt"],
            "expired": db.execute_one("SELECT COUNT(*) as cnt FROM ai_engine_results WHERE action = 'SELL'")["cnt"],
            "hold": db.execute_one("SELECT COUNT(*) as cnt FROM ai_engine_results WHERE action = 'HOLD'")["cnt"]
        }
        
        return _convert_numpy({
            "success": True,
            "predictions": results,
            "stats": stats,
            "count": len(results)
        })
    except Exception as e:
        logger.error(f"Error getting predictions: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# EXPERT RECOMMENDATIONS - تحليلات الخبراء
# ============================================================
@app.get("/api/expert-recommendations")
async def get_expert_recommendations(
    status: Optional[str] = None,
    ticker: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """تحليلات الخبراء - تستند إلى نتائج AI المخزنة"""
    try:
        query = """
            SELECT ticker, action, confidence, price_target, stop_loss,
                   approval_reason as notes, calculated_at as recommendation_date,
                   technical_analysis, risk_level
            FROM ai_engine_results
            WHERE ai_approved = 1
        """
        params = []
        
        if status:
            query += " AND action = ?"
            params.append(status.upper())
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker.upper())
        
        query += " ORDER BY confidence DESC, calculated_at DESC LIMIT ?"
        params.append(limit)
        
        results = db.execute_query(query, tuple(params))
        
        # Add expert stats
        total = db.execute_one("SELECT COUNT(*) as cnt FROM ai_engine_results WHERE ai_approved = 1")["cnt"]
        successful = db.execute_one("SELECT COUNT(*) as cnt FROM ai_engine_results WHERE ai_approved = 1 AND action = 'BUY'")["cnt"]
        
        return _convert_numpy({
            "success": True,
            "recommendations": results,
            "expertStats": [{
                "expert_name": "AI Engine",
                "total_recommendations": total,
                "successful_recommendations": successful,
                "success_rate": round(successful / total * 100, 1) if total > 0 else 0
            }],
            "count": len(results)
        })
    except Exception as e:
        logger.error(f"Error getting expert recommendations: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# PORTFOLIO - المحفظة الاستثمارية
# ============================================================

def _ensure_portfolio_table():
    try:
        db.execute_update("""
            CREATE TABLE IF NOT EXISTS user_portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_symbol TEXT NOT NULL,
                shares REAL NOT NULL,
                avg_cost REAL NOT NULL,
                entry_date TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    except Exception as e:
        logger.warning(f"Could not create portfolio table: {e}")

_ensure_portfolio_table()

@app.get("/api/portfolio")
async def get_portfolio():
    """الحصول على المحفظة الاستثمارية"""
    try:
        positions = db.execute_query("""
            SELECT p.id, p.stock_symbol, p.shares, p.avg_cost, p.entry_date, p.notes, p.created_at,
                   s.name, s.name_ar, s.current_price, s.previous_close, s.sector
            FROM user_portfolios p
            LEFT JOIN stocks s ON s.ticker = p.stock_symbol
            ORDER BY p.created_at DESC
        """)
        
        total_cost = 0
        total_value = 0
        for pos in positions:
            price = pos.get('current_price') or pos.get('avg_cost')
            pos['market_value'] = round((pos['shares'] or 0) * (price or 0), 2)
            pos['cost_basis'] = round((pos['shares'] or 0) * (pos['avg_cost'] or 0), 2)
            pos['unrealized_pnl'] = round(pos['market_value'] - pos['cost_basis'], 2)
            pos['unrealized_pnl_percent'] = round((pos['unrealized_pnl'] / pos['cost_basis'] * 100), 2) if pos['cost_basis'] else 0
            total_cost += pos['cost_basis']
            total_value += pos['market_value']
        
        return {
            "success": True,
            "positions": [_convert_numpy(p) for p in positions],
            "summary": {
                "total_positions": len(positions),
                "total_cost_basis": round(total_cost, 2),
                "total_market_value": round(total_value, 2),
                "total_unrealized_pnl": round(total_value - total_cost, 2),
                "total_unrealized_pnl_percent": round((total_value - total_cost) / total_cost * 100, 2) if total_cost else 0
            }
        }
    except Exception as e:
        logger.error(f"Portfolio error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/portfolio")
async def add_to_portfolio(request: Request):
    """إضافة سهم للمحفظة"""
    try:
        data = await request.json()
        ticker = (data.get("stock_symbol") or data.get("ticker") or "").upper()
        shares = float(data.get("shares", 0))
        avg_cost = float(data.get("avg_cost", 0))
        entry_date = data.get("entry_date", datetime.now().strftime("%Y-%m-%d"))
        notes = data.get("notes", "")
        
        if not ticker or shares <= 0 or avg_cost <= 0:
            return {"success": False, "error": "stock_symbol, shares, and avg_cost are required"}
        
        db.execute_insert(
            "INSERT INTO user_portfolios (stock_symbol, shares, avg_cost, entry_date, notes) VALUES (?, ?, ?, ?, ?)",
            (ticker, shares, avg_cost, entry_date, notes)
        )
        return {"success": True, "message": f"{ticker} added to portfolio"}
    except Exception as e:
        logger.error(f"Add to portfolio error: {e}")
        return {"success": False, "error": str(e)}

@app.delete("/api/portfolio")
async def remove_from_portfolio(id: int = Query(...)):
    """حذف سهم من المحفظة"""
    try:
        db.execute_update("DELETE FROM user_portfolios WHERE id = ?", (id,))
        return {"success": True, "message": "Position removed"}
    except Exception as e:
        logger.error(f"Remove from portfolio error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# DATA ENGINE - محرك البيانات
# ============================================================

# Global stop flag for background AI tasks
_ENGINE_STOP_FLAG = False
_ENGINE_RUNNING_TASKS = {"stocks": False, "crypto": False, "gold": False, "all": False}

def _set_engine_stop():
    global _ENGINE_STOP_FLAG
    _ENGINE_STOP_FLAG = True
    logger.warning("[Engine] STOP signal received. Background tasks will halt.")

def _clear_engine_stop():
    global _ENGINE_STOP_FLAG
    _ENGINE_STOP_FLAG = False

def _is_engine_stopped() -> bool:
    return _ENGINE_STOP_FLAG

def _set_task_running(task: str, running: bool):
    _ENGINE_RUNNING_TASKS[task] = running

def _get_task_status():
    return dict(_ENGINE_RUNNING_TASKS)

# Ensure AI results table exists (supports multiple analyses per asset)
def _ensure_ai_results_table():
    try:
        db.execute_update("""
            CREATE TABLE IF NOT EXISTS ai_engine_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                action TEXT,
                confidence REAL,
                price_target REAL,
                stop_loss REAL,
                reasons TEXT,
                technical_analysis TEXT,
                fundamental_analysis TEXT,
                news_impact TEXT,
                risk_level TEXT,
                ai_approved INTEGER,
                approval_reason TEXT,
                calculated_at TEXT,
                data_source TEXT DEFAULT 'stock'
            )
        """)
    except Exception as e:
        logger.warning(f"Could not create ai_engine_results table: {e}")

_ensure_ai_results_table()


@app.post("/api/engine/run-ai-batch")
async def engine_run_ai_batch(background_tasks: BackgroundTasks, limit: int = Query(50, ge=1, le=200)):
    """تشغيل AI batch على الأسهم في الخلفية"""
    background_tasks.add_task(_run_ai_batch_task, limit)
    return {
        "success": True,
        "message": f"AI batch started for {limit} stocks in background",
        "note": "Results stored in ai_engine_results. Check /api/engine/status for progress."
    }


def _run_ai_batch_task(limit: int = 50):
    """مهمة batch للأسهم في الخلفية"""
    _clear_engine_stop()
    _set_task_running("stocks", True)
    try:
        from ai_local_engine import ai_engine
        stocks = db.execute_query("SELECT ticker FROM stocks WHERE is_active = 1 ORDER BY ticker LIMIT ?", (limit,))
        logger.info(f"[Engine] Starting AI batch for {len(stocks)} stocks")
        
        processed = 0
        failed = 0
        stopped_early = False
        
        for stock in stocks:
            if _is_engine_stopped():
                logger.warning("[Engine] Stocks batch STOPPED by user request")
                stopped_early = True
                break
            ticker = stock['ticker']
            try:
                rec = ai_engine.analyze_stock(ticker)
                if rec:
                    db.execute_update("""
                        INSERT INTO ai_engine_results
                        (ticker, action, confidence, price_target, stop_loss, reasons,
                         technical_analysis, fundamental_analysis, news_impact, risk_level,
                         ai_approved, approval_reason, calculated_at, data_source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        ticker, rec.action, rec.confidence, rec.price_target, rec.stop_loss,
                        json.dumps(rec.reasons), rec.technical_analysis, rec.fundamental_analysis,
                        rec.news_impact, rec.risk_level, 1 if rec.ai_approved else 0,
                        rec.approval_reason, datetime.now().isoformat(), 'stock'
                    ))
                    processed += 1
                    logger.info(f"[Engine] {ticker}: {rec.action} ({rec.confidence}%)")
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"[Engine] Error analyzing {ticker}: {e}")
                failed += 1
        
        status = "STOPPED early" if stopped_early else "complete"
        logger.info(f"[Engine] Stocks batch {status}. Processed: {processed}, Failed: {failed}")
    except Exception as e:
        logger.error(f"[Engine] Batch task error: {e}")
    finally:
        _set_task_running("stocks", False)


@app.post("/api/engine/run-crypto-batch")
async def engine_run_crypto_batch(background_tasks: BackgroundTasks, limit: int = Query(10, ge=1, le=50)):
    """تشغيل AI batch على العملات الرقمية في الخلفية"""
    background_tasks.add_task(_run_crypto_ai_batch_task, limit)
    return {
        "success": True,
        "message": f"Crypto AI batch started for {limit} coins in background",
        "note": "Results stored in ai_engine_results with data_source='crypto'."
    }


def _run_crypto_ai_batch_task(limit: int = 10):
    """مهمة batch للعملات الرقمية في الخلفية"""
    _set_task_running("crypto", True)
    try:
        from ai_local_engine import ai_engine
        coins = db.execute_query("""
            SELECT coin_id FROM crypto_prices 
            WHERE current_price > 0 
            ORDER BY market_cap DESC LIMIT ?
        """, (limit,))
        logger.info(f"[Engine] Starting Crypto AI batch for {len(coins)} coins")
        
        processed = 0
        failed = 0
        stopped_early = False
        
        for coin in coins:
            if _is_engine_stopped():
                logger.warning("[Engine] Crypto batch STOPPED by user request")
                stopped_early = True
                break
            coin_id = coin['coin_id']
            try:
                rec = ai_engine.analyze_crypto(coin_id)
                if rec:
                    db.execute_update("""
                        INSERT INTO ai_engine_results
                        (ticker, action, confidence, price_target, stop_loss, reasons,
                         technical_analysis, fundamental_analysis, news_impact, risk_level,
                         ai_approved, approval_reason, calculated_at, data_source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rec.ticker, rec.action, rec.confidence, rec.price_target, rec.stop_loss,
                        json.dumps(rec.reasons), rec.technical_analysis, rec.fundamental_analysis,
                        rec.news_impact, rec.risk_level, 1 if rec.ai_approved else 0,
                        rec.approval_reason, datetime.now().isoformat(), 'crypto'
                    ))
                    processed += 1
                    logger.info(f"[Engine] Crypto {rec.ticker}: {rec.action} ({rec.confidence}%)")
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"[Engine] Error analyzing crypto {coin_id}: {e}")
                failed += 1
        
        status = "STOPPED early" if stopped_early else "complete"
        logger.info(f"[Engine] Crypto batch {status}. Processed: {processed}, Failed: {failed}")
    except Exception as e:
        logger.error(f"[Engine] Crypto batch task error: {e}")
    finally:
        _set_task_running("crypto", False)


@app.post("/api/engine/run-gold-batch")
async def engine_run_gold_batch(background_tasks: BackgroundTasks):
    """تشغيل AI batch على الذهب في الخلفية"""
    background_tasks.add_task(_run_gold_ai_batch_task)
    return {
        "success": True,
        "message": "Gold AI batch started in background",
        "note": "Results stored in ai_engine_results with data_source='gold'."
    }


def _run_gold_ai_batch_task():
    """مهمة batch للذهب في الخلفية"""
    _set_task_running("gold", True)
    try:
        if _is_engine_stopped():
            logger.warning("[Engine] Gold batch STOPPED by user request")
            return
        from ai_local_engine import ai_engine
        logger.info("[Engine] Starting Gold AI batch")
        
        rec = ai_engine.analyze_gold()
        if rec:
            db.execute_update("""
                INSERT INTO ai_engine_results
                (ticker, action, confidence, price_target, stop_loss, reasons,
                 technical_analysis, fundamental_analysis, news_impact, risk_level,
                 ai_approved, approval_reason, calculated_at, data_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec.ticker, rec.action, rec.confidence, rec.price_target, rec.stop_loss,
                json.dumps(rec.reasons), rec.technical_analysis, rec.fundamental_analysis,
                rec.news_impact, rec.risk_level, 1 if rec.ai_approved else 0,
                rec.approval_reason, datetime.now().isoformat(), 'gold'
            ))
            logger.info(f"[Engine] Gold: {rec.action} ({rec.confidence}%)")
        else:
            logger.warning("[Engine] Gold analysis returned None")
    except Exception as e:
        logger.error(f"[Engine] Gold batch task error: {e}")
    finally:
        _set_task_running("gold", False)


@app.post("/api/engine/run-all-analysis")
async def engine_run_all_analysis(background_tasks: BackgroundTasks, stocks_limit: int = Query(20, ge=1, le=200), crypto_limit: int = Query(5, ge=1, le=20)):
    """تشغيل AI analysis على كل الأصول: أسهم + عملات رقمية + ذهب"""
    background_tasks.add_task(_run_all_analysis_task, stocks_limit, crypto_limit)
    return {
        "success": True,
        "message": f"Full AI analysis started: {stocks_limit} stocks + {crypto_limit} crypto + gold",
        "note": "This runs in background. Check /api/engine/status for progress."
    }


def _run_all_analysis_task(stocks_limit: int, crypto_limit: int):
    """مهمة تحليل شاملة لكل الأصول"""
    _clear_engine_stop()
    _set_task_running("all", True)
    logger.info("=" * 60)
    logger.info("[Engine] STARTING FULL ANALYSIS: Stocks + Crypto + Gold")
    logger.info("=" * 60)
    _run_ai_batch_task(stocks_limit)
    if not _is_engine_stopped():
        _run_crypto_ai_batch_task(crypto_limit)
    if not _is_engine_stopped():
        _run_gold_ai_batch_task()
    status = "STOPPED early" if _is_engine_stopped() else "COMPLETE"
    logger.info("=" * 60)
    logger.info(f"[Engine] FULL ANALYSIS {status}")
    logger.info("=" * 60)
    _set_task_running("all", False)


@app.post("/api/engine/stop")
async def engine_stop():
    """إيقاف أي تحليل AI شغال في الخلفية"""
    _set_engine_stop()
    return {
        "success": True,
        "message": "Stop signal sent. Background AI tasks will halt at next checkpoint.",
        "running_tasks_before_stop": _get_task_status()
    }

@app.get("/api/engine/running")
async def engine_running():
    """التحقق مين شغال حالياً في الخلفية"""
    return {
        "success": True,
        "is_any_running": any(_get_task_status().values()),
        "tasks": _get_task_status(),
        "stop_flag_active": _is_engine_stopped()
    }

@app.get("/api/engine/status")
async def engine_status():
    """حالة محرك البيانات - إحصائيات كل الأصول"""
    try:
        total = db.execute_one("SELECT COUNT(*) as cnt FROM ai_engine_results")
        stocks = db.execute_one("SELECT COUNT(*) as cnt FROM ai_engine_results WHERE data_source = 'stock'")
        crypto = db.execute_one("SELECT COUNT(*) as cnt FROM ai_engine_results WHERE data_source = 'crypto'")
        gold = db.execute_one("SELECT COUNT(*) as cnt FROM ai_engine_results WHERE data_source = 'gold'")
        
        buy = db.execute_one("SELECT COUNT(*) as cnt FROM ai_engine_results WHERE action = 'BUY'")
        sell = db.execute_one("SELECT COUNT(*) as cnt FROM ai_engine_results WHERE action = 'SELL'")
        hold = db.execute_one("SELECT COUNT(*) as cnt FROM ai_engine_results WHERE action = 'HOLD'")
        
        latest = db.execute_query("""
            SELECT ticker, action, confidence, calculated_at, data_source 
            FROM ai_engine_results ORDER BY calculated_at DESC LIMIT 15
        """)
        
        crypto_count = 0
        try:
            crypto_count = db.execute_one("SELECT COUNT(*) as cnt FROM crypto_prices")["cnt"]
        except:
            pass
        
        return _convert_numpy({
            "success": True,
            "total_stocks_in_db": db.execute_one("SELECT COUNT(*) as cnt FROM stocks WHERE is_active = 1")["cnt"],
            "crypto_coins_in_db": crypto_count,
            "total_ai_analyzed": total["cnt"],
            "by_asset": {
                "stocks": stocks["cnt"],
                "crypto": crypto["cnt"],
                "gold": gold["cnt"]
            },
            "by_action": {
                "buy": buy["cnt"],
                "sell": sell["cnt"],
                "hold": hold["cnt"]
            },
            "latest_analysis": latest,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/engine/results")
async def engine_results(asset_type: Optional[str] = None, action: Optional[str] = None, limit: int = 100):
    """نتائج تحليل AI المخزنة - ممكن فلترة حسب نوع الأصل"""
    try:
        query = "SELECT * FROM ai_engine_results WHERE 1=1"
        params = []
        
        if asset_type:
            query += " AND data_source = ?"
            params.append(asset_type.lower())
        if action:
            query += " AND action = ?"
            params.append(action.upper())
        
        query += " ORDER BY calculated_at DESC LIMIT ?"
        params.append(limit)
        
        results = db.execute_query(query, tuple(params))
        
        for r in results:
            try:
                r["reasons"] = json.loads(r["reasons"]) if r.get("reasons") else []
            except:
                r["reasons"] = []
        
        return _convert_numpy({"success": True, "count": len(results), "results": results})
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# FAST PRE-COMPUTED ENDPOINTS - Results from Data Engine
# ============================================================

@app.get("/api/engine/signals")
async def engine_signals(action: Optional[str] = None, min_confidence: int = 0, limit: int = 100, asset_type: Optional[str] = None):
    """Get ALL pre-computed technical signals INSTANTLY. Filter by asset_type: stock, crypto, gold"""
    try:
        signals = data_engine.get_all_signals(action=action, min_confidence=min_confidence, asset_type=asset_type)
        if limit:
            signals = signals[:limit]
        return {"success": True, "count": len(signals), "signals": [_convert_numpy(s) for s in signals]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/engine/signals/{ticker}")
async def engine_signal_ticker(ticker: str):
    """Get pre-computed signals for ONE stock INSTANTLY"""
    try:
        sig = data_engine.get_stock_signals(ticker.upper())
        if not sig:
            return {"success": False, "error": f"No pre-computed data for {ticker}. Run engine first."}
        return {"success": True, "data": _convert_numpy(sig)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/engine/sectors")
async def engine_sectors():
    """Get sector performance rankings INSTANTLY"""
    try:
        sectors = data_engine.get_sectors()
        return {"success": True, "count": len(sectors), "sectors": [_convert_numpy(s) for s in sectors]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/engine/market-summary")
async def engine_market_summary():
    """Get pre-computed market summary INSTANTLY"""
    try:
        summary = data_engine.get_market_summary()
        if not summary:
            return {"success": False, "error": "No market summary. Run engine first."}
        return {"success": True, "data": _convert_numpy(summary)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/engine/run-pipeline")
async def engine_run_pipeline(background_tasks: BackgroundTasks):
    """Trigger the FULL Data Engine pipeline in background"""
    background_tasks.add_task(data_engine.run_full_pipeline)
    return {
        "success": True,
        "message": "Data Engine pipeline started in background",
        "note": "Pre-computes indicators, sectors, and market summary for ALL stocks"
    }


# ============================================================
# RUN SERVER
# ============================================================
if __name__ == "__main__":
    import uvicorn
    logger.info(f"🚀 Starting Unified Backend v{VERSION} on {HOST}:{PORT}")
    logger.info(f"🌐 Open in browser: http://localhost:{PORT}")
    logger.info(f"📚 API Docs: http://localhost:{PORT}/docs")
    uvicorn.run(app, host=HOST, port=PORT)

# TEMP DEBUG
@app.get("/api/debug/db")
async def debug_db():
    import ai_local_engine as ail
    import sqlite3
    conn = sqlite3.connect(ail.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    conn.close()
    return {"db_path": ail.DB_PATH, "tables": tables}
