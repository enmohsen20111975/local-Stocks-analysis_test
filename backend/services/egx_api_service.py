#!/usr/bin/env python3
"""
EGX Data API Service - Fixed Version
=====================================
VPS-based API for EGX stock data with technical indicators and predictions.

Features:
- Historical data from VPS SQLite database
- Technical indicators calculated from database
- Trading signals and predictions
- Price alerts system
- Daily reports

VPS: http://72.61.137.86:8010
Database: Uses config.py for unified database path
"""

import os
import json
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from flask import Flask, jsonify, request, g
from flask_cors import CORS

# Import unified configuration
try:
    from config import DATABASE_PATH, API_PORT, get_db_connection, print_config
    PORT = API_PORT
except ImportError:
    # Fallback if config.py not available
    DATABASE_PATH = os.environ.get('DATABASE_PATH', '/root/GLMinvestment/db/egx_investment.db')
    PORT = int(os.environ.get('PORT', 8010))

# Try to import data sources
DATA_SOURCES = {}

try:
    from tradingview_ta import TA_Handler, get_multiple_analysis, Interval
    DATA_SOURCES['tradingview'] = True
    print("✓ TradingView TA available")
except ImportError:
    DATA_SOURCES['tradingview'] = False
    print("✗ TradingView TA not available")

try:
    import numpy as np
    DATA_SOURCES['numpy'] = True
    print("✓ numpy available")
except ImportError:
    DATA_SOURCES['numpy'] = False
    print("✗ numpy not available")

try:
    import pandas as pd
    DATA_SOURCES['pandas'] = True
    print("✓ pandas available")
except ImportError:
    DATA_SOURCES['pandas'] = False
    print("✗ pandas not available")

app = Flask(__name__)
CORS(app)

# ============================================================================
# ALL EGX STOCKS - COMPLETE LIST (295 stocks)
# ============================================================================

EGX_ALL_STOCKS = [
    "AALR", "ABUK", "ACAMD", "ACAP", "ACGC", "ACRO", "ACTF", "ADCI", "ADIB", "ADPC",
    "ADRI", "AFDI", "AFMC", "AIDC", "AIFI", "AIH", "AIHC", "AJWA", "ALCN", "ALEX",
    "ALUM", "AMER", "AMES", "AMIA", "AMOC", "AMPI", "ANFI", "APPC", "APRI", "APSW",
    "ARAB", "ARCC", "AREH", "ARPI", "ARVA", "ASCM", "ASPI", "ATLC", "ATQA", "AXPH",
    "BIDI", "BIGP", "BINV", "BIOC", "BLDG", "BONY", "BTFH", "CAED", "CALT", "CANA",
    "CAPE", "CCAP", "CCRS", "CEFM", "CERA", "CFGH", "CICH", "CIEB", "CIRA", "CLHO",
    "CNFN", "COMI", "COPR", "COSG", "CPCI", "CPME", "CRST", "CSAG", "DAPH", "DCCC",
    "DCRC", "DEIN", "DGTZ", "DIFC", "DMNH", "DOMT", "DSCW", "DTPP", "EALR", "EASB",
    "EAST", "EBSC", "ECAP", "EDBM", "EDFM", "EEII", "EFIC", "EFID", "EFIH", "EGAL",
    "EGAS", "EGBE", "EGCH", "EGREF", "EGSA", "EGTS", "EHDR", "EITP", "EIUD", "EKHO",
    "ELEC", "ELKA", "ELNA", "ELSH", "ELWA", "EMFD", "ENGC", "EOSB", "EPCO", "EPPK",
    "ESAC", "ESGH", "ESRS", "ETEL", "ETRS", "EXPA", "FAIT", "FAITA", "FERC", "FIRE",
    "FNAR", "FTNS", "FWRY", "GBCO", "GDWA", "GETO", "GGCC", "GGRN", "GIHD", "GMCC",
    "GMCI", "GOCO", "GPIM", "GPPL", "GRCA", "GSSC", "GTEX", "GTHE", "GTWL", "HBCO",
    "HCFI", "HDBK", "HELI", "HRHO", "IBCT", "ICFC", "ICID", "ICMI", "IDRE", "IEEC",
    "IFAP", "INEG", "INFI", "IRAX", "IRON", "ISMA", "ISMQ", "ISPH", "JUFO", "KABO",
    "KAHA", "KASABF", "KRDI", "KWIN", "KZPC", "LCSW", "LUTS", "MAAL", "MASR", "MBEG",
    "MBSC", "MCQE", "MCRO", "MEGM", "MENA", "MEPA", "MFPC", "MFSC", "MHOT", "MICH",
    "MILS", "MIPH", "MISR", "MKIT", "MMAT", "MNHD", "MOED", "MOIL", "MOIN", "MOSC",
    "MPCI", "MPCO", "MPRC", "MTEZ", "MTIE", "NAHO", "NAPR", "NARE", "NBKE", "NCCW",
    "NCGC", "NDRL", "NEDA", "NHPS", "NINH", "NIPH", "NSGB", "OBRI", "OCDI", "OCIC",
    "OCPH", "ODIN", "OFH", "OIH", "OLFI", "ORAS", "ORHD", "ORTE", "ORWE", "PACH",
    "PACL", "PETR", "PHAR", "PHDC", "PHGC", "PHTV", "PHYG", "PIOH", "PORT", "POUL",
    "PRCL", "PRDC", "PRMH", "PTCC", "QNBE", "RACC", "RAKT", "RAYA", "REAC", "RKAZ",
    "RMDA", "RMTV", "ROTO", "RREI", "RTVC", "RUBX", "SAIB", "SAUD", "SCEM", "SCFM",
    "SCTS", "SDTI", "SEIG", "SEIGA", "SIMO", "SIPC", "SKPC", "SMFR", "SMPP", "SNFC",
    "SNFI", "SPHT", "SPIN", "SPMD", "SUCE", "SUGR", "SVCE", "SWDY", "TALM", "TANM",
    "TAQA", "TELE", "TEXT", "TMGH", "TORA", "TRST", "TRTO", "TWSA", "UASG", "UBEE",
    "UEFM", "UEGC", "UNIP", "UNIT", "UPMS", "UTOP", "VALU", "VERT", "VLMR", "VLMRA",
    "WATP", "WCDF", "WKOL", "ZEOT", "ZMID"
]

# Popular EGX stocks (most traded)
EGX_POPULAR = [
    "COMI", "HRHO", "SWDY", "ETEL", "EKHO", "TMGH", "PHDC", "GTHE", "ESRS", "ORHD",
    "CIEB", "AMER", "HELI", "OCDI", "JUFO", "ABUK", "SKPC", "MNHD", "ESGH", "ALCN"
]

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
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    signal = "overbought" if rsi >= 70 else "oversold" if rsi <= 30 else "neutral"
    
    return {
        "value": round(rsi, 2),
        "signal": signal,
        "period": period
    }

def calculate_macd(prices: List[float]) -> Optional[Dict]:
    """Calculate MACD indicator."""
    if len(prices) < 26:
        return None
    
    ema_12 = calculate_ema(prices, 12)
    ema_26 = calculate_ema(prices, 26)
    
    if ema_12 is None or ema_26 is None:
        return None
    
    macd_line = ema_12 - ema_26
    signal_line = macd_line * 0.9  # Simplified signal
    histogram = macd_line - signal_line
    
    if macd_line > signal_line and histogram > 0:
        trend = "bullish"
    elif macd_line < signal_line and histogram < 0:
        trend = "bearish"
    else:
        trend = "neutral"
    
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
        "current": round(prices[-1], 2),
        "period": period
    }

def calculate_all_indicators(prices: List[float]) -> Dict:
    """Calculate all technical indicators."""
    indicators = {
        "sma": {},
        "ema": {},
        "rsi": None,
        "macd": None,
        "bollinger_bands": None,
        "data_points": len(prices)
    }
    
    # Calculate SMAs and EMAs
    for period in [5, 10, 20, 50, 100, 200]:
        sma = calculate_sma(prices, period)
        ema = calculate_ema(prices, period)
        if sma:
            indicators["sma"][period] = round(sma, 2)
        if ema:
            indicators["ema"][period] = round(ema, 2)
    
    # Calculate other indicators
    indicators["rsi"] = calculate_rsi(prices)
    indicators["macd"] = calculate_macd(prices)
    indicators["bollinger_bands"] = calculate_bollinger_bands(prices)
    
    return indicators

# ============================================================================
# PREDICTION ENGINE
# ============================================================================

def generate_prediction(prices: List[float], symbol: str) -> Dict:
    """Generate trading prediction based on technical analysis."""
    if len(prices) < 50:
        return {
            "symbol": symbol,
            "signal": "insufficient_data",
            "confidence": 0,
            "reason": f"Need at least 50 data points, got {len(prices)}"
        }
    
    signals = []
    total_score = 0
    
    # RSI Signal
    rsi_data = calculate_rsi(prices)
    if rsi_data:
        rsi = rsi_data["value"]
        if rsi <= 30:
            signals.append({"indicator": "RSI", "signal": "BUY", "value": rsi, "reason": "Oversold"})
            total_score += 2
        elif rsi >= 70:
            signals.append({"indicator": "RSI", "signal": "SELL", "value": rsi, "reason": "Overbought"})
            total_score -= 2
        else:
            signals.append({"indicator": "RSI", "signal": "HOLD", "value": rsi, "reason": "Neutral"})
    
    # MACD Signal
    macd_data = calculate_macd(prices)
    if macd_data:
        if macd_data["trend"] == "bullish":
            signals.append({"indicator": "MACD", "signal": "BUY", "trend": macd_data["trend"]})
            total_score += 1
        elif macd_data["trend"] == "bearish":
            signals.append({"indicator": "MACD", "signal": "SELL", "trend": macd_data["trend"]})
            total_score -= 1
        else:
            signals.append({"indicator": "MACD", "signal": "HOLD", "trend": macd_data["trend"]})
    
    # Moving Average Signal
    current_price = prices[-1]
    sma_20 = calculate_sma(prices, 20)
    sma_50 = calculate_sma(prices, 50)
    
    if sma_20 and sma_50:
        if current_price > sma_20 > sma_50:
            signals.append({"indicator": "MA_Cross", "signal": "BUY", "reason": "Price above MAs, bullish alignment"})
            total_score += 1
        elif current_price < sma_20 < sma_50:
            signals.append({"indicator": "MA_Cross", "signal": "SELL", "reason": "Price below MAs, bearish alignment"})
            total_score -= 1
        else:
            signals.append({"indicator": "MA_Cross", "signal": "HOLD", "reason": "Mixed signals"})
    
    # Bollinger Bands Signal
    bb_data = calculate_bollinger_bands(prices)
    if bb_data:
        if current_price <= bb_data["lower"]:
            signals.append({"indicator": "Bollinger", "signal": "BUY", "reason": "Price at lower band"})
            total_score += 1
        elif current_price >= bb_data["upper"]:
            signals.append({"indicator": "Bollinger", "signal": "SELL", "reason": "Price at upper band"})
            total_score -= 1
    
    # Calculate final signal
    if total_score >= 2:
        final_signal = "STRONG_BUY"
        confidence = min(80 + total_score * 5, 95)
    elif total_score == 1:
        final_signal = "BUY"
        confidence = 65
    elif total_score == 0:
        final_signal = "HOLD"
        confidence = 50
    elif total_score == -1:
        final_signal = "SELL"
        confidence = 65
    else:
        final_signal = "STRONG_SELL"
        confidence = min(80 + abs(total_score) * 5, 95)
    
    # Calculate price targets
    recent_high = max(prices[-20:])
    recent_low = min(prices[-20:])
    
    return {
        "symbol": symbol,
        "signal": final_signal,
        "confidence": confidence,
        "score": total_score,
        "signals": signals,
        "current_price": round(current_price, 2),
        "targets": {
            "support": round(recent_low, 2),
            "resistance": round(recent_high, 2),
            "stop_loss": round(recent_low * 0.98, 2),
            "take_profit": round(recent_high * 1.02, 2)
        },
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# DATA FETCHING FUNCTIONS
# ============================================================================

def get_price_history_from_db(symbol: str, days: int = 365) -> List[Dict]:
    """Get historical prices from VPS database."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT date, open, high, low, close, volume 
        FROM price_history 
        WHERE symbol = ? 
        ORDER BY date ASC
        LIMIT ?
    ''', (symbol.upper(), days))
    
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

def get_stocks_from_db() -> List[Dict]:
    """Get all stocks with prices from database."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT symbol, exchange, name, current_price, previous_close,
               open_price, high_price, low_price, volume,
               change_amount, change_percent, last_updated
        FROM stocks 
        WHERE current_price IS NOT NULL
        ORDER BY symbol
    ''')
    
    return [dict(row) for row in cursor.fetchall()]

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM stocks")
        stock_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM price_history")
        history_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM stocks WHERE current_price IS NOT NULL")
        priced_count = cursor.fetchone()[0]
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "4.0.0",
            "data_sources": DATA_SOURCES,
            "database": DATABASE_PATH,
            "port": PORT,
            "stats": {
                "stocks_count": stock_count,
                "stocks_with_prices": priced_count,
                "history_count": history_count,
                "predictions_count": 0
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/stocks/all', methods=['GET'])
def get_all_stocks():
    """Get ALL stocks from database."""
    try:
        stocks = get_stocks_from_db()
        return jsonify({
            "success": True,
            "count": len(stocks),
            "data": stocks,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    """Get stocks with optional filtering."""
    try:
        limit = request.args.get('limit', type=int)
        search = request.args.get('search', '').upper()
        
        stocks = get_stocks_from_db()
        
        if search:
            stocks = [s for s in stocks if search in s.get('symbol', '')]
        
        if limit:
            stocks = stocks[:limit]
        
        return jsonify({
            "success": True,
            "count": len(stocks),
            "data": stocks
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/stock/<symbol>', methods=['GET'])
def get_stock(symbol):
    """Get single stock details."""
    try:
        symbol = symbol.upper()
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM stocks WHERE symbol = ?', (symbol,))
        row = cursor.fetchone()
        
        if row:
            return jsonify({"success": True, "data": dict(row)})
        
        return jsonify({"success": False, "error": "Stock not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/history/<symbol>', methods=['GET'])
def get_history(symbol):
    """Get historical price data from VPS database."""
    try:
        symbol = symbol.upper()
        days = request.args.get('days', 365, type=int)
        
        rows = get_price_history_from_db(symbol, days)
        
        if rows:
            return jsonify({
                "success": True,
                "data": {
                    "symbol": symbol,
                    "points": len(rows),
                    "rows": rows,
                    "source": "vps_database"
                }
            })
        
        return jsonify({"success": False, "error": "No historical data found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/indicators/<symbol>', methods=['GET'])
def get_indicators(symbol):
    """Get technical indicators for a stock using VPS database."""
    try:
        symbol = symbol.upper()
        
        # Get historical data from VPS database
        rows = get_price_history_from_db(symbol, 365)
        
        if not rows or len(rows) < 10:
            return jsonify({
                "success": False,
                "error": f"Insufficient data for {symbol}. Found {len(rows)} data points, need at least 10."
            }), 404
        
        # Extract close prices (reverse to oldest first for calculations)
        closes = [r['close'] for r in rows]
        closes.reverse()  # Now oldest first
        
        # Calculate indicators
        indicators = calculate_all_indicators(closes)
        
        return jsonify({
            "success": True,
            "data": {
                "symbol": symbol,
                "current_price": closes[-1] if closes else None,
                "data_points": len(closes),
                "indicators": indicators,
                "source": "vps_database"
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/predict/<symbol>', methods=['GET'])
def get_prediction(symbol):
    """Get trading prediction for a stock."""
    try:
        symbol = symbol.upper()
        
        # Get historical data from VPS database
        rows = get_price_history_from_db(symbol, 365)
        
        if not rows or len(rows) < 50:
            return jsonify({
                "success": False,
                "error": f"Insufficient data for prediction. Found {len(rows)} data points, need at least 50."
            }), 404
        
        # Extract close prices (reverse to oldest first)
        closes = [r['close'] for r in rows]
        closes.reverse()
        
        # Generate prediction
        prediction = generate_prediction(closes, symbol)
        
        return jsonify({
            "success": True,
            "data": prediction
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/sync', methods=['GET', 'POST'])
def sync_data():
    """Sync data from external sources or receive data upload."""
    try:
        if request.method == 'GET':
            # Return sync status
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM stocks WHERE current_price IS NOT NULL")
            priced = cursor.fetchone()[0]
            
            cursor.execute("SELECT MAX(last_updated) FROM stocks")
            last_sync = cursor.fetchone()[0]
            
            return jsonify({
                "success": True,
                "message": "Sync status",
                "stocks_with_prices": priced,
                "last_sync": last_sync,
                "timestamp": datetime.now().isoformat()
            })
        
        # POST - receive data sync
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        updated = 0
        
        # Handle stocks data
        if 'stocks' in data:
            for stock in data['stocks']:
                symbol = stock.get('symbol', '').upper()
                if not symbol:
                    continue
                
                cursor.execute('''
                    INSERT OR REPLACE INTO stocks 
                    (symbol, exchange, name, current_price, previous_close, 
                     open_price, high_price, low_price, volume, 
                     change_amount, change_percent, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    stock.get('exchange', 'EGX'),
                    stock.get('name'),
                    stock.get('current_price') or stock.get('price'),
                    stock.get('previous_close'),
                    stock.get('open_price') or stock.get('open'),
                    stock.get('high_price') or stock.get('high'),
                    stock.get('low_price') or stock.get('low'),
                    stock.get('volume'),
                    stock.get('change_amount') or stock.get('change'),
                    stock.get('change_percent'),
                    stock.get('last_updated') or datetime.now().isoformat()
                ))
                updated += 1
        
        conn.commit()
        
        return jsonify({
            "success": True,
            "message": f"Updated {updated} stocks",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/data/export', methods=['GET'])
def data_export():
    """Export all database data as JSON for backup."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Export stocks
        cursor.execute('''
            SELECT symbol, exchange, name, current_price, previous_close,
                   open_price, high_price, low_price, volume,
                   change_amount, change_percent, last_updated
            FROM stocks
        ''')
        stocks = [dict(row) for row in cursor.fetchall()]
        
        # Export price history (limit for performance)
        cursor.execute('''
            SELECT symbol, exchange, date, open, high, low, close, volume
            FROM price_history
            WHERE date >= date('now', '-365 days')
            ORDER BY symbol, date DESC
        ''')
        price_history = [dict(row) for row in cursor.fetchall()]
        
        # Get counts
        cursor.execute("SELECT COUNT(*) FROM price_history")
        total_history = cursor.fetchone()[0]
        
        return jsonify({
            "success": True,
            "export_timestamp": datetime.now().isoformat(),
            "source": "vps_egx_api",
            "database": DATABASE_PATH,
            "counts": {
                "stocks": len(stocks),
                "price_history_exported": len(price_history),
                "price_history_total": total_history
            },
            "data": {
                "stocks": stocks,
                "price_history": price_history
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/reports/daily', methods=['GET'])
def get_daily_report():
    """Get daily market report."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get market stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN change_percent > 0 THEN 1 ELSE 0 END) as gainers,
                SUM(CASE WHEN change_percent < 0 THEN 1 ELSE 0 END) as losers,
                AVG(change_percent) as avg_change
            FROM stocks WHERE current_price IS NOT NULL
        ''')
        stats = dict(cursor.fetchone())
        
        # Top gainers
        cursor.execute('''
            SELECT symbol, current_price, change_percent, volume
            FROM stocks 
            WHERE current_price IS NOT NULL AND change_percent > 0
            ORDER BY change_percent DESC LIMIT 10
        ''')
        gainers = [dict(row) for row in cursor.fetchall()]
        
        # Top losers
        cursor.execute('''
            SELECT symbol, current_price, change_percent, volume
            FROM stocks 
            WHERE current_price IS NOT NULL AND change_percent < 0
            ORDER BY change_percent ASC LIMIT 10
        ''')
        losers = [dict(row) for row in cursor.fetchall()]
        
        # Most active
        cursor.execute('''
            SELECT symbol, current_price, change_percent, volume
            FROM stocks 
            WHERE current_price IS NOT NULL AND volume > 0
            ORDER BY volume DESC LIMIT 10
        ''')
        active = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            "success": True,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
            "gainers": gainers,
            "losers": losers,
            "most_active": active
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print(f"\n{'='*60}")
    print(f"EGX Data API Service v4.0.0")
    print(f"{'='*60}")
    print(f"Database: {DATABASE_PATH}")
    print(f"Port: {PORT}")
    print(f"Data Sources: {DATA_SOURCES}")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
