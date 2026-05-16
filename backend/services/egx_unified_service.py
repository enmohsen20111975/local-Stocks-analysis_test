#!/usr/bin/env python3
"""
EGX Unified Data Service - VPS Edition
======================================
خدمة بيانات EGX الموحدة - إصدار VPS

المميزات:
- استقبال بيانات Mubasher من التطبيق المحلي
- جلب أسعار EGX من TradingView
- التحليلات الفنية (RSI, MACD, SMA, Bollinger)
- Self-Learning Engine للتوقعات
- API للـ Node.js

الإصدار: 4.0.0
المطور: GLMinvestment Team
"""

import os
import sys
import json
import time
import sqlite3
import logging
import argparse
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from flask import Flask, jsonify, request, g
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_PATH = os.environ.get('DATABASE_PATH', '/root/egxpy_service/data/egx_investment.db')
PORT = int(os.environ.get('PORT', 8010))
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
SYNC_INTERVAL = int(os.environ.get('SYNC_INTERVAL', 300))  # 5 minutes

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# ============================================================================
# DATA SOURCES CHECK
# ============================================================================

DATA_SOURCES = {}

try:
    from tradingview_ta import TA_Handler, Interval
    DATA_SOURCES['tradingview'] = True
    logger.info("✓ TradingView TA available")
except ImportError:
    DATA_SOURCES['tradingview'] = False
    logger.warning("✗ TradingView TA not available")

try:
    import numpy as np
    DATA_SOURCES['numpy'] = True
    logger.info("✓ numpy available")
except ImportError:
    DATA_SOURCES['numpy'] = False
    logger.warning("✗ numpy not available")

try:
    import pandas as pd
    DATA_SOURCES['pandas'] = True
    logger.info("✓ pandas available")
except ImportError:
    DATA_SOURCES['pandas'] = False
    logger.warning("✗ pandas not available")

# ============================================================================
# EPS VALUES FOR EGX STOCKS (for PE ratio calculation)
# ============================================================================

EPS_VALUES = {
    # Banks
    "COMI": 5.77, "HRHO": 1.55, "CIEB": 1.93, "SAIB": 0.0, "ADIB": 0.0,
    # Telecommunications
    "ETEL": 3.42, "FWRY": 0.48,
    # Real Estate
    "TMGH": 3.98, "PHDC": 1.08, "MNHD": 3.27, "HELI": 0.34, "ORHD": 1.21,
    # Industrial
    "ESRS": 6.28, "SWDY": 2.93, "ABUK": 7.07, "SKPC": 0.64,
    # Food & Beverages
    "JUFO": 0.97, "EKHO": 0.03,
    # Construction
    "OCDI": 1.49, "ORAS": 0.0,
    # Others
    "AMER": 0.17, "ALCN": 1.21, "GTHE": 0.12, "ESGH": 2.69,
    "BTFH": 0.28, "CCAP": 0.0, "CIRA": 0.58, "AMOC": 1.85, "MCQE": 0.42,
}

SECTOR_MAP = {
    "COMI": "Financial Services", "HRHO": "Financial Services", "CIEB": "Financial Services",
    "ETEL": "Telecommunications", "FWRY": "Technology",
    "TMGH": "Real Estate", "PHDC": "Real Estate", "MNHD": "Real Estate", "HELI": "Real Estate",
    "ESRS": "Basic Materials", "SWDY": "Industrials", "ABUK": "Basic Materials", "SKPC": "Energy",
    "JUFO": "Consumer Defensive", "EKHO": "Consumer Defensive",
    "OCDI": "Industrials", "AMER": "Real Estate", "GTHE": "Communication Services",
}

# ============================================================================
# DATABASE SETUP
# ============================================================================

def get_db():
    """Get database connection."""
    try:
        db = getattr(g, '_database', None)
        if db is None:
            db = g._database = sqlite3.connect(DATABASE_PATH)
            db.row_factory = sqlite3.Row
        return db
    except RuntimeError:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database - create tables if needed."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Stocks table (main stock data)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL UNIQUE,
            name TEXT,
            name_ar TEXT,
            current_price REAL,
            previous_close REAL,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            volume INTEGER,
            pe_ratio REAL,
            eps REAL,
            sector TEXT,
            market_cap REAL,
            is_active INTEGER DEFAULT 1,
            last_update TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Price history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id INTEGER,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            close_price REAL,
            volume INTEGER,
            adjusted_close REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(stock_id, date)
        )
    ''')
    
    # Intraday 5-min data (from Mubasher)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intraday_5m (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            turnover REAL,
            num_trades INTEGER,
            vwap REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, timestamp)
        )
    ''')
    
    # Technical indicators cache
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS technical_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL UNIQUE,
            rsi REAL,
            rsi_signal TEXT,
            macd REAL,
            macd_signal REAL,
            macd_histogram REAL,
            macd_trend TEXT,
            sma_20 REAL,
            sma_50 REAL,
            ema_20 REAL,
            bollinger_upper REAL,
            bollinger_middle REAL,
            bollinger_lower REAL,
            overall_signal TEXT,
            signal_strength REAL,
            calculated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Predictions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            prediction_date TEXT NOT NULL,
            predicted_price REAL,
            current_price REAL,
            confidence REAL,
            trend TEXT,
            model_type TEXT DEFAULT 'linear_regression',
            status TEXT DEFAULT 'pending',
            actual_price REAL,
            accuracy_percent REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            verified_at TEXT
        )
    ''')
    
    # Self-learning signals
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            signal_date TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL,
            stop_loss REAL,
            target_price REAL,
            indicators_used TEXT,
            score REAL,
            executed INTEGER DEFAULT 0,
            result TEXT,
            profit_loss REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Learned lessons
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learned_lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            trigger_conditions TEXT,
            action TEXT,
            confidence REAL DEFAULT 0,
            occurrences INTEGER DEFAULT 1,
            status TEXT DEFAULT 'testing',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_seen TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sync log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_type TEXT NOT NULL,
            source TEXT,
            stocks_updated INTEGER DEFAULT 0,
            records_count INTEGER DEFAULT 0,
            errors INTEGER DEFAULT 0,
            duration_seconds REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_ticker ON stocks(ticker)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_history_ticker ON stock_price_history(ticker)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_history_date ON stock_price_history(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_intraday_symbol ON intraday_5m(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_intraday_timestamp ON intraday_5m(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_predictions_ticker ON predictions(ticker)')
    
    conn.commit()
    conn.close()
    logger.info(f"✓ Database initialized: {DATABASE_PATH}")

def get_table_columns(table_name: str) -> List[str]:
    """Get column names for a table."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]

# ============================================================================
# TECHNICAL INDICATORS
# ============================================================================

def calculate_sma(prices: List[float], period: int) -> Optional[float]:
    """Calculate Simple Moving Average."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """Calculate Exponential Moving Average."""
    if len(prices) < period:
        return None
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calculate_rsi(prices: List[float], period: int = 14) -> Optional[Dict]:
    """Calculate Relative Strength Index."""
    if len(prices) < period + 1:
        return None
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        rsi = 100
    else:
        rsi = 100 - (100 / (1 + avg_gain / avg_loss))
    
    signal = "overbought" if rsi >= 70 else "oversold" if rsi <= 30 else "neutral"
    return {"value": round(rsi, 2), "signal": signal}

def calculate_macd(prices: List[float]) -> Optional[Dict]:
    """Calculate MACD indicator."""
    if len(prices) < 26:
        return None
    
    ema_12 = calculate_ema(prices, 12)
    ema_26 = calculate_ema(prices, 26)
    
    if ema_12 is None or ema_26 is None:
        return None
    
    macd_line = ema_12 - ema_26
    signal_line = macd_line * 0.9  # Simplified
    histogram = macd_line - signal_line
    
    trend = "bullish" if macd_line > signal_line and histogram > 0 else \
            "bearish" if macd_line < signal_line and histogram < 0 else "neutral"
    
    return {
        "macd": round(macd_line, 4),
        "signal": round(signal_line, 4),
        "histogram": round(histogram, 4),
        "trend": trend
    }

def calculate_bollinger_bands(prices: List[float], period: int = 20) -> Optional[Dict]:
    """Calculate Bollinger Bands."""
    if len(prices) < period:
        return None
    
    recent = prices[-period:]
    sma = sum(recent) / period
    variance = sum((p - sma) ** 2 for p in recent) / period
    std_dev = variance ** 0.5
    
    return {
        "upper": round(sma + (2 * std_dev), 2),
        "middle": round(sma, 2),
        "lower": round(sma - (2 * std_dev), 2),
        "current": prices[-1]
    }

def calculate_all_indicators(prices: List[float]) -> Dict:
    """Calculate all technical indicators and generate signal."""
    rsi = calculate_rsi(prices)
    macd = calculate_macd(prices)
    sma_20 = calculate_sma(prices, 20)
    sma_50 = calculate_sma(prices, 50)
    ema_20 = calculate_ema(prices, 20)
    bollinger = calculate_bollinger_bands(prices)
    
    # Calculate overall signal
    buy_signals = 0
    sell_signals = 0
    total_signals = 0
    
    if rsi:
        total_signals += 1
        if rsi['signal'] == 'oversold':
            buy_signals += 1
        elif rsi['signal'] == 'overbought':
            sell_signals += 1
    
    if macd:
        total_signals += 1
        if macd['trend'] == 'bullish':
            buy_signals += 1
        elif macd['trend'] == 'bearish':
            sell_signals += 1
    
    if sma_20 and sma_50 and len(prices) > 0:
        total_signals += 1
        if prices[-1] > sma_20 > sma_50:
            buy_signals += 1
        elif prices[-1] < sma_20 < sma_50:
            sell_signals += 1
    
    # Determine overall signal
    if total_signals > 0:
        buy_ratio = buy_signals / total_signals
        sell_ratio = sell_signals / total_signals
        
        if buy_ratio >= 0.6:
            overall_signal = "BUY"
            signal_strength = buy_ratio
        elif sell_ratio >= 0.6:
            overall_signal = "SELL"
            signal_strength = sell_ratio
        else:
            overall_signal = "HOLD"
            signal_strength = max(buy_ratio, sell_ratio)
    else:
        overall_signal = "INSUFFICIENT_DATA"
        signal_strength = 0
    
    return {
        "rsi": rsi,
        "macd": macd,
        "sma_20": sma_20,
        "sma_50": sma_50,
        "ema_20": ema_20,
        "bollinger": bollinger,
        "overall_signal": overall_signal,
        "signal_strength": round(signal_strength, 2),
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "total_signals": total_signals
    }

# ============================================================================
# PRICE PREDICTION (Linear Regression)
# ============================================================================

def predict_price(prices: List[float], days_ahead: int = 7) -> Dict:
    """Predict price using linear regression."""
    if len(prices) < 30:
        return {"error": "Insufficient data for prediction"}
    
    if DATA_SOURCES.get('numpy'):
        import numpy as np
        
        # Use last 30 prices
        x = np.array(range(len(prices[-30:])))
        y = np.array(prices[-30:])
        
        # Linear regression
        slope, intercept = np.polyfit(x, y, 1)
        predicted = slope * (len(prices[-30:]) + days_ahead) + intercept
        
        # Calculate R-squared for confidence
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        confidence = max(0, min(100, r_squared * 100))
        
        trend = "up" if slope > 0 else "down" if slope < 0 else "neutral"
        
        return {
            "predicted_price": round(float(predicted), 2),
            "confidence": round(confidence, 1),
            "trend": trend,
            "trend_strength": round(abs(float(slope)), 4),
            "days_ahead": days_ahead
        }
    else:
        # Simple calculation without numpy
        recent_avg = sum(prices[-7:]) / 7
        older_avg = sum(prices[-30:-7]) / 23
        trend = (recent_avg - older_avg) / older_avg * 100 if older_avg > 0 else 0
        predicted = prices[-1] * (1 + trend / 100 * days_ahead / 7)
        
        return {
            "predicted_price": round(predicted, 2),
            "confidence": 50,
            "trend": "up" if trend > 0 else "down" if trend < 0 else "neutral",
            "days_ahead": days_ahead
        }

# ============================================================================
# TRADINGVIEW DATA FETCHER
# ============================================================================

def fetch_from_tradingview(symbol: str) -> Optional[Dict]:
    """Fetch stock data from TradingView."""
    if not DATA_SOURCES.get('tradingview'):
        return None
    
    try:
        from tradingview_ta import TA_Handler, Interval
        
        handler = TA_Handler(
            symbol=symbol,
            exchange="EGX",
            screener="egypt",
            interval=Interval.INTERVAL_1_DAY
        )
        analysis = handler.get_analysis()
        
        if analysis:
            indicators = analysis.indicators
            price = indicators.get("close", 0)
            prev_close = indicators.get("previous_close", price)
            
            change = price - prev_close if prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0
            
            eps = EPS_VALUES.get(symbol, 0)
            pe_ratio = round(price / eps, 2) if eps > 0 else None
            
            return {
                "ticker": symbol,
                "current_price": round(price, 4) if price else None,
                "previous_close": round(prev_close, 4) if prev_close else None,
                "open_price": round(indicators.get("open", price), 4),
                "high_price": round(indicators.get("high", price), 4),
                "low_price": round(indicators.get("low", price), 4),
                "volume": int(indicators.get("volume", 0) or 0),
                "price_change": round(change, 4),
                "price_change_percent": round(change_pct, 2),
                "pe_ratio": pe_ratio,
                "eps": eps,
                "sector": SECTOR_MAP.get(symbol),
                "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "source": "tradingview"
            }
    except Exception as e:
        logger.error(f"Error fetching {symbol} from TradingView: {e}")
    return None

def fetch_batch_tradingview(symbols: List[str]) -> Tuple[List[Dict], List[str]]:
    """Fetch multiple stocks from TradingView."""
    results = []
    errors = []
    
    for symbol in symbols:
        data = fetch_from_tradingview(symbol)
        if data:
            results.append(data)
        else:
            errors.append(symbol)
        time.sleep(0.3)  # Rate limiting
    
    return results, errors

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    conn = get_db()
    cursor = conn.cursor()
    
    stats = {}
    try:
        cursor.execute("SELECT COUNT(*) FROM stocks")
        stats['stocks_count'] = cursor.fetchone()[0]
    except:
        stats['stocks_count'] = 0
    
    try:
        cursor.execute("SELECT COUNT(*) FROM stock_price_history")
        stats['history_count'] = cursor.fetchone()[0]
    except:
        stats['history_count'] = 0
    
    try:
        cursor.execute("SELECT COUNT(*) FROM intraday_5m")
        stats['intraday_count'] = cursor.fetchone()[0]
    except:
        stats['intraday_count'] = 0
    
    try:
        cursor.execute("SELECT COUNT(*) FROM predictions")
        stats['predictions_count'] = cursor.fetchone()[0]
    except:
        stats['predictions_count'] = 0
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "4.0.0",
        "data_sources": DATA_SOURCES,
        "database": DATABASE_PATH,
        "stats": stats,
        "port": PORT
    })

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    """Get all stocks."""
    conn = get_db()
    cursor = conn.cursor()
    
    limit = request.args.get('limit', type=int)
    search = request.args.get('search', '').upper()
    
    query = "SELECT * FROM stocks WHERE is_active = 1 OR is_active IS NULL"
    params = []
    
    if search:
        query += " AND (ticker LIKE ? OR name LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])
    
    query += " ORDER BY ticker"
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query, params)
    stocks = [dict(row) for row in cursor.fetchall()]
    
    return jsonify({
        "success": True,
        "count": len(stocks),
        "data": stocks,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/stocks/<ticker>', methods=['GET'])
def get_stock(ticker):
    """Get single stock with indicators."""
    ticker = ticker.upper()
    conn = get_db()
    cursor = conn.cursor()
    
    # Get stock data
    cursor.execute("SELECT * FROM stocks WHERE ticker = ?", (ticker,))
    stock = cursor.fetchone()
    
    if not stock:
        # Try to fetch from TradingView
        data = fetch_from_tradingview(ticker)
        if data:
            return jsonify({"success": True, "data": data})
        return jsonify({"success": False, "error": "Stock not found"}), 404
    
    stock_data = dict(stock)
    
    # Get technical indicators
    cursor.execute("SELECT * FROM technical_indicators WHERE ticker = ?", (ticker,))
    indicators = cursor.fetchone()
    if indicators:
        stock_data['indicators'] = dict(indicators)
    
    # Get latest prediction
    cursor.execute("""
        SELECT * FROM predictions 
        WHERE ticker = ? AND status = 'pending'
        ORDER BY created_at DESC LIMIT 1
    """, (ticker,))
    prediction = cursor.fetchone()
    if prediction:
        stock_data['prediction'] = dict(prediction)
    
    return jsonify({"success": True, "data": stock_data})

@app.route('/api/history/<ticker>', methods=['GET'])
def get_history(ticker):
    """Get historical price data."""
    ticker = ticker.upper()
    days = request.args.get('days', 365, type=int)
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT date, open_price as open, high_price as high,
               low_price as low, close_price as close, volume
        FROM stock_price_history 
        WHERE ticker = ? 
        ORDER BY date DESC LIMIT ?
    ''', (ticker, days))
    
    history = [dict(row) for row in cursor.fetchall()]
    
    if history:
        return jsonify({
            "success": True,
            "data": {
                "ticker": ticker,
                "count": len(history),
                "history": history
            }
        })
    
    return jsonify({"success": False, "error": "No historical data"}), 404

@app.route('/api/intraday/<ticker>', methods=['GET'])
def get_intraday(ticker):
    """Get intraday 5-min data."""
    ticker = ticker.upper()
    limit = request.args.get('limit', 100, type=int)
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM intraday_5m 
        WHERE symbol = ? 
        ORDER BY timestamp DESC LIMIT ?
    ''', (ticker, limit))
    
    data = [dict(row) for row in cursor.fetchall()]
    
    return jsonify({
        "success": True,
        "count": len(data),
        "data": data
    })

@app.route('/api/indicators/<ticker>', methods=['GET'])
def get_indicators(ticker):
    """Get or calculate technical indicators."""
    ticker = ticker.upper()
    conn = get_db()
    cursor = conn.cursor()
    
    # Get historical prices
    cursor.execute('''
        SELECT close_price FROM stock_price_history 
        WHERE ticker = ? 
        ORDER BY date DESC LIMIT 100
    ''', (ticker,))
    
    rows = cursor.fetchall()
    
    if len(rows) >= 20:
        prices = [r['close_price'] for r in reversed(rows)]
        indicators = calculate_all_indicators(prices)
        
        # Save to cache
        cursor.execute('''
            INSERT OR REPLACE INTO technical_indicators 
            (ticker, rsi, rsi_signal, macd, macd_signal, macd_histogram, macd_trend,
             sma_20, sma_50, ema_20, bollinger_upper, bollinger_middle, bollinger_lower,
             overall_signal, signal_strength, calculated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticker,
            indicators['rsi']['value'] if indicators['rsi'] else None,
            indicators['rsi']['signal'] if indicators['rsi'] else None,
            indicators['macd']['macd'] if indicators['macd'] else None,
            indicators['macd']['signal'] if indicators['macd'] else None,
            indicators['macd']['histogram'] if indicators['macd'] else None,
            indicators['macd']['trend'] if indicators['macd'] else None,
            indicators['sma_20'],
            indicators['sma_50'],
            indicators['ema_20'],
            indicators['bollinger']['upper'] if indicators['bollinger'] else None,
            indicators['bollinger']['middle'] if indicators['bollinger'] else None,
            indicators['bollinger']['lower'] if indicators['bollinger'] else None,
            indicators['overall_signal'],
            indicators['signal_strength'],
            datetime.now().isoformat()
        ))
        
        conn.commit()
        
        return jsonify({
            "success": True,
            "data": {
                "ticker": ticker,
                "current_price": prices[-1] if prices else None,
                "indicators": indicators
            }
        })
    
    # Try to get from cache
    cursor.execute("SELECT * FROM technical_indicators WHERE ticker = ?", (ticker,))
    cached = cursor.fetchone()
    
    if cached:
        return jsonify({
            "success": True,
            "data": dict(cached),
            "cached": True
        })
    
    return jsonify({"success": False, "error": "Insufficient data"}), 404

@app.route('/api/predict/<ticker>', methods=['GET'])
def get_prediction(ticker):
    """Get price prediction."""
    ticker = ticker.upper()
    days = request.args.get('days', 7, type=int)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get historical prices
    cursor.execute('''
        SELECT close_price FROM stock_price_history 
        WHERE ticker = ? 
        ORDER BY date DESC LIMIT 60
    ''', (ticker,))
    
    rows = cursor.fetchall()
    
    if len(rows) >= 30:
        prices = [r['close_price'] for r in reversed(rows)]
        prediction = predict_price(prices, days)
        
        # Save prediction
        cursor.execute('''
            INSERT INTO predictions 
            (ticker, prediction_date, predicted_price, current_price, confidence, trend, model_type, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        ''', (
            ticker,
            (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d'),
            prediction.get('predicted_price'),
            prices[-1],
            prediction.get('confidence'),
            prediction.get('trend'),
            'linear_regression'
        ))
        conn.commit()
        
        return jsonify({
            "success": True,
            "data": {
                "ticker": ticker,
                "current_price": prices[-1],
                "prediction": prediction,
                "model": "linear_regression"
            }
        })
    
    return jsonify({"success": False, "error": "Insufficient historical data"}), 400

@app.route('/api/market/overview', methods=['GET'])
def market_overview():
    """Get market overview."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM stocks WHERE current_price IS NOT NULL")
    stocks = [dict(row) for row in cursor.fetchall()]
    
    gainers = []
    losers = []
    
    for s in stocks:
        if s.get('previous_close') and s['previous_close'] > 0:
            change_pct = ((s['current_price'] or 0) - s['previous_close']) / s['previous_close'] * 100
            s['change_percent'] = change_pct
            if change_pct > 0:
                gainers.append(s)
            elif change_pct < 0:
                losers.append(s)
    
    gainers = sorted(gainers, key=lambda x: x['change_percent'], reverse=True)[:10]
    losers = sorted(losers, key=lambda x: x['change_percent'])[:10]
    most_active = sorted(stocks, key=lambda x: x.get('volume') or 0, reverse=True)[:10]
    
    return jsonify({
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "stats": {
            "total": len(stocks),
            "gainers": len(gainers),
            "losers": len(losers)
        },
        "gainers": gainers,
        "losers": losers,
        "most_active": most_active
    })

# ============================================================================
# MUBASHER SYNC ENDPOINT
# ============================================================================

@app.route('/api/mubasher/sync', methods=['POST'])
def mubasher_sync():
    """Receive data from local Mubasher sync app."""
    start_time = time.time()
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    sync_type = data.get('sync_type', 'unknown')
    stocks = data.get('stocks', [])
    intraday = data.get('intraday', [])
    history = data.get('history', [])
    
    conn = get_db()
    cursor = conn.cursor()
    
    stocks_updated = 0
    records_count = 0
    errors = 0
    
    # Process stocks metadata
    for stock in stocks:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO stocks 
                (ticker, name, sector, is_active, last_update)
                VALUES (?, ?, ?, 1, ?)
            ''', (
                stock.get('symbol'),
                stock.get('name'),
                stock.get('sector'),
                datetime.now().isoformat()
            ))
            stocks_updated += 1
        except Exception as e:
            logger.error(f"Error inserting stock {stock.get('symbol')}: {e}")
            errors += 1
    
    # Process intraday data
    for record in intraday:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO intraday_5m 
                (symbol, timestamp, open, high, low, close, volume, turnover, num_trades, vwap)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.get('symbol'),
                record.get('timestamp'),
                record.get('open'),
                record.get('high'),
                record.get('low'),
                record.get('close'),
                record.get('volume'),
                record.get('turnover'),
                record.get('num_trades'),
                record.get('vwap')
            ))
            records_count += 1
        except Exception as e:
            errors += 1
    
    # Process historical data
    for record in history:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO stock_price_history 
                (ticker, date, open_price, high_price, low_price, close_price, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.get('symbol'),
                record.get('date'),
                record.get('open'),
                record.get('high'),
                record.get('low'),
                record.get('close'),
                record.get('volume')
            ))
            records_count += 1
        except Exception as e:
            errors += 1
    
    # Update stock prices from latest intraday
    if intraday:
        latest_prices = {}
        for record in intraday:
            symbol = record.get('symbol')
            ts = record.get('timestamp')
            if symbol and ts:
                if symbol not in latest_prices or ts > latest_prices[symbol]['timestamp']:
                    latest_prices[symbol] = {'close': record.get('close'), 'timestamp': ts}
        
        for symbol, data in latest_prices.items():
            if data['close']:
                cursor.execute('''
                    UPDATE stocks SET current_price = ?, last_update = ?
                    WHERE ticker = ?
                ''', (data['close'], datetime.now().isoformat(), symbol))
    
    # Log sync
    duration = time.time() - start_time
    cursor.execute('''
        INSERT INTO sync_log (sync_type, source, stocks_updated, records_count, errors, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (sync_type, 'mubasher', stocks_updated, records_count, errors, duration))
    
    conn.commit()
    
    return jsonify({
        "success": True,
        "sync_type": sync_type,
        "stocks_updated": stocks_updated,
        "records_count": records_count,
        "errors": errors,
        "duration_seconds": round(duration, 2)
    })

@app.route('/api/mubasher/status', methods=['GET'])
def mubasher_status():
    """Get Mubasher sync status and statistics."""
    conn = get_db()
    cursor = conn.cursor()
    
    stats = {}
    
    try:
        cursor.execute("SELECT COUNT(*) FROM stocks")
        stats['stocks_count'] = cursor.fetchone()[0]
    except:
        stats['stocks_count'] = 0
    
    try:
        cursor.execute("SELECT COUNT(*) FROM intraday_5m")
        stats['intraday_5m_count'] = cursor.fetchone()[0]
    except:
        stats['intraday_5m_count'] = 0
    
    try:
        cursor.execute("SELECT COUNT(*) FROM stock_price_history")
        stats['history_count'] = cursor.fetchone()[0]
    except:
        stats['history_count'] = 0
    
    try:
        cursor.execute("SELECT MAX(created_at) FROM sync_log WHERE source = 'mubasher'")
        stats['last_sync'] = cursor.fetchone()[0]
    except:
        stats['last_sync'] = None
    
    return jsonify({
        "success": True,
        "statistics": stats,
        "timestamp": datetime.now().isoformat()
    })

# ============================================================================
# SYNC FROM TRADINGVIEW
# ============================================================================

@app.route('/api/sync', methods=['POST'])
def sync_stocks():
    """Sync stock prices from TradingView."""
    data = request.get_json() or {}
    symbols = data.get('symbols', ['COMI', 'HRHO', 'ETEL', 'SWDY', 'TMGH', 'PHDC', 'ABUK', 'ESRS', 'ORHD', 'JUFO'])
    
    start_time = time.time()
    results, errors = fetch_batch_tradingview(symbols)
    
    conn = get_db()
    cursor = conn.cursor()
    updated = 0
    
    for stock in results:
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
            stock['current_price'],
            stock['previous_close'],
            stock['open_price'],
            stock['high_price'],
            stock['low_price'],
            stock['volume'],
            stock['pe_ratio'],
            stock['eps'],
            stock['sector'],
            stock['last_update'],
            stock['ticker']
        ))
        if cursor.rowcount > 0:
            updated += 1
    
    duration = time.time() - start_time
    cursor.execute('''
        INSERT INTO sync_log (sync_type, source, stocks_updated, errors, duration_seconds)
        VALUES (?, ?, ?, ?, ?)
    ''', ('manual', 'tradingview', updated, len(errors), duration))
    
    conn.commit()
    
    return jsonify({
        "success": True,
        "synced": updated,
        "errors": len(errors),
        "duration_seconds": round(duration, 2),
        "failed_symbols": errors[:10] if errors else []
    })

# ============================================================================
# DATA EXPORT FOR NODE.JS
# ============================================================================

@app.route('/api/data/export', methods=['GET'])
def export_data():
    """Export data for Node.js."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Export stocks
    cursor.execute("SELECT * FROM stocks WHERE current_price IS NOT NULL")
    stocks = [dict(row) for row in cursor.fetchall()]
    
    # Export recent indicators
    cursor.execute("SELECT * FROM technical_indicators")
    indicators = [dict(row) for row in cursor.fetchall()]
    
    # Export active predictions
    cursor.execute("SELECT * FROM predictions WHERE status = 'pending'")
    predictions = [dict(row) for row in cursor.fetchall()]
    
    return jsonify({
        "success": True,
        "export_timestamp": datetime.now().isoformat(),
        "counts": {
            "stocks": len(stocks),
            "indicators": len(indicators),
            "predictions": len(predictions)
        },
        "data": {
            "stocks": stocks,
            "indicators": indicators,
            "predictions": predictions
        }
    })

# ============================================================================
# SELF-LEARNING ENDPOINTS
# ============================================================================

@app.route('/api/signals/<ticker>', methods=['GET'])
def get_signals(ticker):
    """Get trading signals for a stock."""
    ticker = ticker.upper()
    conn = get_db()
    cursor = conn.cursor()
    
    # Get indicators first
    cursor.execute("SELECT * FROM technical_indicators WHERE ticker = ?", (ticker,))
    indicators = cursor.fetchone()
    
    if not indicators:
        # Calculate indicators
        indicators_resp = get_indicators(ticker)
        indicators_data = indicators_resp.get_json()
        if indicators_data.get('success'):
            indicators = indicators_data.get('data', {}).get('indicators', {})
    
    if not indicators:
        return jsonify({"success": False, "error": "Cannot calculate indicators"}), 400
    
    ind_dict = dict(indicators) if hasattr(indicators, 'keys') else indicators
    
    # Generate signal
    signal = {
        "ticker": ticker,
        "timestamp": datetime.now().isoformat(),
        "overall_signal": ind_dict.get('overall_signal', 'HOLD'),
        "signal_strength": ind_dict.get('signal_strength', 0),
        "indicators": {
            "rsi": {"value": ind_dict.get('rsi'), "signal": ind_dict.get('rsi_signal')},
            "macd": {"trend": ind_dict.get('macd_trend')},
        },
        "recommendation": None
    }
    
    # Generate recommendation
    if ind_dict.get('overall_signal') == 'BUY':
        cursor.execute("SELECT current_price FROM stocks WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        current_price = row['current_price'] if row else None
        
        if current_price:
            signal['recommendation'] = {
                "action": "BUY",
                "entry_price": current_price,
                "stop_loss": round(current_price * 0.95, 2),  # 5% stop loss
                "target": round(current_price * 1.10, 2),  # 10% target
                "risk_reward": "1:2"
            }
    
    # Log signal
    cursor.execute('''
        INSERT INTO signal_logs (ticker, signal_date, direction, entry_price, stop_loss, target_price, score)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        ticker,
        datetime.now().strftime('%Y-%m-%d'),
        signal['overall_signal'],
        signal.get('recommendation', {}).get('entry_price'),
        signal.get('recommendation', {}).get('stop_loss'),
        signal.get('recommendation', {}).get('target'),
        ind_dict.get('signal_strength')
    ))
    conn.commit()
    
    return jsonify({"success": True, "data": signal})

@app.route('/api/lessons', methods=['GET'])
def get_lessons():
    """Get learned lessons."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM learned_lessons WHERE status = 'validated' ORDER BY occurrences DESC")
    lessons = [dict(row) for row in cursor.fetchall()]
    
    return jsonify({
        "success": True,
        "count": len(lessons),
        "data": lessons
    })

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='EGX Unified Data Service')
    parser.add_argument('--port', type=int, default=PORT, help='Port to run on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--init-db', action='store_true', help='Initialize database and exit')
    
    args = parser.parse_args()
    
    # Initialize database
    init_db()
    
    if args.init_db:
        logger.info("Database initialized. Exiting.")
        return
    
    logger.info(f"Starting EGX Unified Data Service v4.0.0 on port {args.port}")
    logger.info(f"Database: {DATABASE_PATH}")
    logger.info(f"Data sources: {DATA_SOURCES}")
    
    app.run(host='0.0.0.0', port=args.port, debug=args.debug or DEBUG)

if __name__ == '__main__':
    main()
