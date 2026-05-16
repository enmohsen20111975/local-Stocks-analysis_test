#!/usr/bin/env python3
"""
EGX Data API Service - Local Version
=====================================
Local API for EGX stock data with technical indicators and predictions.

Features:
- Historical data from local SQLite database
- Technical indicators calculated from database
- Trading signals and predictions
- Compatible with existing database schema

Database: Uses config.py for unified database path
Port: 8010 (configurable via PORT environment variable)
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
    # Fallback if config.py not available - use environment or local path
    DATABASE_PATH = os.environ.get('DATABASE_PATH', '/home/z/my-project/GLMinvestment/db/egx_investment.db')
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
# DATA FETCHING FUNCTIONS (Adapted for local database schema)
# ============================================================================

def get_price_history_from_db(ticker: str, days: int = 365) -> List[Dict]:
    """Get historical prices from local database.
    
    Uses stock_price_history table joined with stocks table via stock_id.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Join stock_price_history with stocks to get data by ticker
    cursor.execute('''
        SELECT sph.date, sph.open_price as open, sph.high_price as high, 
               sph.low_price as low, sph.close_price as close, sph.volume 
        FROM stock_price_history sph
        JOIN stocks s ON sph.stock_id = s.id
        WHERE s.ticker = ? 
        ORDER BY sph.date ASC
        LIMIT ?
    ''', (ticker.upper(), days))
    
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

def get_stocks_from_db() -> List[Dict]:
    """Get all stocks with prices from database.
    
    Uses stocks table with ticker column.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT ticker as symbol, 'EGX' as exchange, name, name_ar,
               current_price, previous_close, open_price, high_price, low_price, 
               volume, sector, pe_ratio, eps, market_cap,
               ma_50, ma_200, rsi, last_update as last_updated
        FROM stocks 
        WHERE current_price IS NOT NULL
        ORDER BY ticker
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
        
        cursor.execute("SELECT COUNT(*) FROM stock_price_history")
        history_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM stocks WHERE current_price IS NOT NULL")
        priced_count = cursor.fetchone()[0]
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "5.0.0-local",
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
            stocks = [s for s in stocks if search in s.get('symbol', '') or search in s.get('name', '')]
        
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
        
        cursor.execute('''
            SELECT ticker as symbol, 'EGX' as exchange, name, name_ar,
                   current_price, previous_close, open_price, high_price, low_price, 
                   volume, sector, pe_ratio, eps, market_cap,
                   ma_50, ma_200, rsi, support_level, resistance_level,
                   dividend_yield, roe, debt_to_equity, egx30_member, egx70_member,
                   is_halal, compliance_status, last_update as last_updated
            FROM stocks 
            WHERE ticker = ?
        ''', (symbol,))
        row = cursor.fetchone()
        
        if row:
            return jsonify({"success": True, "data": dict(row)})
        
        return jsonify({"success": False, "error": "Stock not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/history/<symbol>', methods=['GET'])
def get_history(symbol):
    """Get historical price data from database."""
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
                    "source": "local_database"
                }
            })
        
        return jsonify({"success": False, "error": "No historical data found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/indicators/<symbol>', methods=['GET'])
def get_indicators(symbol):
    """Get technical indicators for a stock using database."""
    try:
        symbol = symbol.upper()
        
        # Get historical data from database
        rows = get_price_history_from_db(symbol, 365)
        
        if not rows or len(rows) < 10:
            return jsonify({
                "success": False,
                "error": f"Insufficient data for {symbol}. Found {len(rows)} data points, need at least 10."
            }), 404
        
        # Extract close prices (already ordered oldest first from query)
        closes = [r['close'] for r in rows]
        
        # Calculate indicators
        indicators = calculate_all_indicators(closes)
        
        return jsonify({
            "success": True,
            "data": {
                "symbol": symbol,
                "current_price": closes[-1] if closes else None,
                "data_points": len(closes),
                "indicators": indicators,
                "source": "local_database"
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/predict/<symbol>', methods=['GET'])
def get_prediction(symbol):
    """Get trading prediction for a stock."""
    try:
        symbol = symbol.upper()
        
        # Get historical data from database
        rows = get_price_history_from_db(symbol, 365)
        
        if not rows or len(rows) < 50:
            return jsonify({
                "success": False,
                "error": f"Insufficient data for prediction. Found {len(rows)} data points, need at least 50."
            }), 404
        
        # Extract close prices
        closes = [r['close'] for r in rows]
        
        # Generate prediction
        prediction = generate_prediction(closes, symbol)
        
        return jsonify({
            "success": True,
            "data": prediction
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/scan-all', methods=['GET', 'POST'])
def scan_all_stocks():
    """Scan all stocks for trading signals - used by Advanced Analysis."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all stocks with price data
        cursor.execute('''
            SELECT ticker as symbol, current_price, previous_close, volume,
                   sector, pe_ratio, ma_50, ma_200, rsi
            FROM stocks 
            WHERE current_price IS NOT NULL AND is_active = 1
            ORDER BY ticker
        ''')
        stocks = [dict(row) for row in cursor.fetchall()]
        
        results = []
        buy_signals = []
        sell_signals = []
        
        for stock in stocks:
            symbol = stock['symbol']
            
            # Get price history for this stock
            rows = get_price_history_from_db(symbol, 100)
            
            if len(rows) >= 50:
                closes = [r['close'] for r in rows]
                prediction = generate_prediction(closes, symbol)
                
                result = {
                    "symbol": symbol,
                    "current_price": stock['current_price'],
                    "previous_close": stock['previous_close'],
                    "change_percent": round(((stock['current_price'] or 0) - (stock['previous_close'] or 0)) / (stock['previous_close'] or 1) * 100, 2) if stock['previous_close'] else 0,
                    "volume": stock['volume'],
                    "sector": stock['sector'],
                    "signal": prediction['signal'],
                    "confidence": prediction['confidence'],
                    "score": prediction['score'],
                    "signals": prediction['signals'],
                    "targets": prediction['targets']
                }
                results.append(result)
                
                if prediction['signal'] in ['BUY', 'STRONG_BUY']:
                    buy_signals.append(result)
                elif prediction['signal'] in ['SELL', 'STRONG_SELL']:
                    sell_signals.append(result)
        
        # Sort by confidence
        buy_signals.sort(key=lambda x: x['confidence'], reverse=True)
        sell_signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "total_stocks": len(stocks),
            "analyzed_stocks": len(results),
            "summary": {
                "total_analyzed": len(results),
                "buy_signals": len(buy_signals),
                "sell_signals": len(sell_signals),
                "hold_signals": len(results) - len(buy_signals) - len(sell_signals)
            },
            "buy_signals": buy_signals[:20],  # Top 20 buy signals
            "sell_signals": sell_signals[:20],  # Top 20 sell signals
            "all_results": results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/sync', methods=['GET', 'POST'])
def sync_data():
    """Sync data status."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM stocks WHERE current_price IS NOT NULL")
        priced = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(last_update) FROM stocks")
        last_sync = cursor.fetchone()[0]
        
        return jsonify({
            "success": True,
            "message": "Sync status",
            "stocks_with_prices": priced,
            "last_sync": last_sync,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/reports/daily', methods=['GET'])
def get_daily_report():
    """Get daily market report."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Calculate change_percent for each stock
        cursor.execute('''
            SELECT ticker as symbol, current_price, previous_close, volume, sector
            FROM stocks WHERE current_price IS NOT NULL
        ''')
        stocks = [dict(row) for row in cursor.fetchall()]
        
        gainers = []
        losers = []
        
        for s in stocks:
            if s.get('previous_close') and s['previous_close'] > 0:
                change_pct = ((s['current_price'] or 0) - s['previous_close']) / s['previous_close'] * 100
                s['change_percent'] = round(change_pct, 2)
                if change_pct > 0:
                    gainers.append(s)
                elif change_pct < 0:
                    losers.append(s)
        
        gainers = sorted(gainers, key=lambda x: x['change_percent'], reverse=True)[:10]
        losers = sorted(losers, key=lambda x: x['change_percent'])[:10]
        most_active = sorted(stocks, key=lambda x: x.get('volume') or 0, reverse=True)[:10]
        
        return jsonify({
            "success": True,
            "date": datetime.now().strftime("%Y-%m-%d"),
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
            SELECT ticker as symbol, name, name_ar, current_price, previous_close,
                   open_price, high_price, low_price, volume, sector
            FROM stocks WHERE current_price IS NOT NULL
        ''')
        stocks = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            "success": True,
            "export_timestamp": datetime.now().isoformat(),
            "source": "local_egx_api",
            "database": DATABASE_PATH,
            "counts": {
                "stocks": len(stocks)
            },
            "data": {
                "stocks": stocks
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print(f"\n{'='*60}")
    print(f"EGX Data API Service v5.0.0-local")
    print(f"{'='*60}")
    print(f"Database: {DATABASE_PATH}")
    print(f"Port: {PORT}")
    print(f"Data Sources: {DATA_SOURCES}")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
