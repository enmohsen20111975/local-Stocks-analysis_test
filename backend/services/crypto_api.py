#!/usr/bin/env python3
"""
Crypto Analysis API
===================
API لتحليل العملات الرقمية

Endpoints:
- GET /api/crypto/<coin_id> - تحليل عملة
- GET /api/crypto/top/<limit> - أفضل العملات
- GET /api/crypto/market - بيانات السوق
- GET /api/crypto/timing/<coin_id> - تحليل الوقت

Run: python crypto_api.py --port 8012
"""

import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# Import analyzer
try:
    from crypto_analyzer import CryptoAnalyzer, CryptoDataFetcher
    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False

# Configuration
PORT = int(os.environ.get('PORT', 8012))
API_KEY = os.environ.get('API_KEY', 'mubasher-sync-2024-secret')

app = Flask(__name__)
CORS(app)

# Cache
analyzer = None
fetcher = None

def get_analyzer():
    global analyzer
    if analyzer is None and ANALYZER_AVAILABLE:
        analyzer = CryptoAnalyzer()
    return analyzer

def get_fetcher():
    global fetcher
    if fetcher is None and ANALYZER_AVAILABLE:
        fetcher = CryptoDataFetcher()
    return fetcher

# ============================================================================
# AUTHENTICATION
# ============================================================================

def check_auth():
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    return api_key == API_KEY

@app.before_request
def before_request():
    if request.path == '/health':
        return None
    if not check_auth():
        return jsonify({"success": False, "error": "Unauthorized"}), 401

# ============================================================================
# HEALTH
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "crypto-analysis-api",
        "version": "2.0.0",
        "analyzer_available": ANALYZER_AVAILABLE,
        "features": [
            "crypto_analysis",
            "market_data",
            "timing_analysis",
            "risk_management",
            "adx_indicator",
            "multi_timeframe",
            "open_interest",
            "pattern_recognition",
            "fibonacci_clusters",
            "candlestick_patterns"
        ],
        "endpoints": {
            "crypto": [
                "/api/crypto/<coin_id>",
                "/api/crypto/top/<limit>",
                "/api/crypto/market",
                "/api/crypto/timing/<coin_id>",
                "/api/crypto/list",
                "/api/crypto/<coin_id>/open-interest",
                "/api/crypto/<coin_id>/oi-divergence"
            ],
            "risk": [
                "/api/risk/evaluate",
                "/api/risk/position-size",
                "/api/risk/adx",
                "/api/risk/multi-timeframe"
            ],
            "patterns": [
                "/api/patterns/detect",
                "/api/patterns/head-shoulders",
                "/api/patterns/triangles"
            ],
            "fibonacci": [
                "/api/fibonacci/retracement",
                "/api/fibonacci/extension",
                "/api/fibonacci/clusters",
                "/api/fibonacci/pattern-integration"
            ],
            "candlestick": [
                "/api/candlestick/analyze",
                "/api/candlestick/single",
                "/api/candlestick/hammer",
                "/api/candlestick/morning-star",
                "/api/candlestick/evening-star",
                "/api/candlestick/piercing-line",
                "/api/candlestick/dark-cloud",
                "/api/candlestick/patterns-list"
            ]
        },
        "timestamp": datetime.now().isoformat()
    })

# ============================================================================
# CRYPTO ENDPOINTS
# ============================================================================

@app.route('/api/crypto/<coin_id>', methods=['GET'])
def analyze_crypto(coin_id):
    """
    Full analysis of a cryptocurrency
    
    Example: /api/crypto/bitcoin
    """
    if not ANALYZER_AVAILABLE:
        return jsonify({"success": False, "error": "Analyzer not available"}), 500
    
    try:
        result = get_analyzer().analyze(coin_id.lower())
        
        if not result:
            return jsonify({"success": False, "error": "Crypto not found"}), 404
        
        return jsonify({
            "success": True,
            "analysis": {
                "coin_id": result.coin_id,
                "symbol": result.symbol,
                "name": result.name,
                "current_price": result.current_price,
                "signal": result.overall_signal,
                "confidence": result.confidence,
                "score": result.overall_score,
                "entry_price": result.entry_price,
                "target_price": result.target_price,
                "stop_loss": result.stop_loss,
                "support_levels": result.support_levels,
                "resistance_levels": result.resistance_levels,
                "reasons": result.reasons,
                "warnings": result.warnings,
                "technical": {
                    "rsi": result.technical.rsi,
                    "rsi_signal": result.technical.rsi_signal,
                    "macd": result.technical.macd,
                    "trend": result.technical.overall_trend,
                    "sma_20": result.technical.sma_20,
                    "sma_50": result.technical.sma_50
                },
                "fundamental": {
                    "rank": result.fundamental.market_cap_rank,
                    "sentiment": result.fundamental.market_sentiment,
                    "from_ath": result.fundamental.price_vs_ath_percent,
                    "whale_activity": result.fundamental.whale_activity
                },
                "timing": {
                    "session": result.timing.current_session,
                    "hour_utc": result.timing.current_hour_utc,
                    "recommendation": result.timing.recommendation_timing,
                    "best_buy_hours": result.timing.best_hours_to_buy,
                    "best_sell_hours": result.timing.best_hours_to_sell
                }
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/crypto/top/<int:limit>', methods=['GET'])
def get_top(limit):
    """
    Get top cryptocurrencies by market cap
    
    Example: /api/crypto/top/10
    """
    if not ANALYZER_AVAILABLE:
        return jsonify({"success": False, "error": "Analyzer not available"}), 500
    
    try:
        limit = min(limit, 50)  # Max 50
        results = get_analyzer().analyze_top(limit)
        
        return jsonify({
            "success": True,
            "count": len(results),
            "cryptos": [{
                "symbol": r.symbol,
                "name": r.name,
                "price": r.current_price,
                "signal": r.overall_signal,
                "confidence": r.confidence,
                "score": r.overall_score,
                "top_reason": r.reasons[0] if r.reasons else None
            } for r in results]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/crypto/market', methods=['GET'])
def get_market():
    """Get global market data"""
    if not ANALYZER_AVAILABLE:
        return jsonify({"success": False, "error": "Analyzer not available"}), 500
    
    try:
        global_data = get_fetcher().get_global_data()
        
        if not global_data:
            return jsonify({"success": False, "error": "Failed to fetch market data"}), 500
        
        data = global_data.get('data', {})
        
        return jsonify({
            "success": True,
            "market": {
                "total_market_cap_usd": data.get('total_market_cap', {}).get('usd'),
                "total_volume_usd": data.get('total_volume', {}).get('usd'),
                "btc_dominance": data.get('market_cap_percentage', {}).get('btc'),
                "eth_dominance": data.get('market_cap_percentage', {}).get('eth'),
                "market_cap_change_24h": data.get('market_cap_change_percentage_24h_usd'),
                "active_cryptos": data.get('active_cryptocurrencies'),
                "markets": data.get('markets'),
                "updated_at": data.get('updated_at')
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/crypto/timing/<coin_id>', methods=['GET'])
def get_timing(coin_id):
    """Get timing analysis for a cryptocurrency"""
    if not ANALYZER_AVAILABLE:
        return jsonify({"success": False, "error": "Analyzer not available"}), 500
    
    try:
        crypto = get_fetcher().get_crypto(coin_id.lower())
        
        if not crypto:
            return jsonify({"success": False, "error": "Crypto not found"}), 404
        
        from crypto_analyzer import TimeAnalyzer
        timing = TimeAnalyzer().analyze(crypto)
        
        return jsonify({
            "success": True,
            "timing": {
                "current_hour_utc": timing.current_hour_utc,
                "current_session": timing.current_session,
                "recommendation": timing.recommendation_timing,
                "best_hours_to_buy": timing.best_hours_to_buy,
                "best_hours_to_sell": timing.best_hours_to_sell,
                "weekly_pattern": timing.weekly_pattern,
                "next_event": timing.next_important_event
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/crypto/list', methods=['GET'])
def list_cryptos():
    """Get list of top cryptocurrencies (quick, no analysis)"""
    if not ANALYZER_AVAILABLE:
        return jsonify({"success": False, "error": "Analyzer not available"}), 500
    
    try:
        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 100)
        
        cryptos = get_fetcher().get_top_cryptos(limit)
        
        return jsonify({
            "success": True,
            "count": len(cryptos),
            "cryptos": [{
                "id": c.coin_id,
                "symbol": c.symbol,
                "name": c.name,
                "price": c.current_price,
                "change_24h": c.price_change_percent_24h,
                "market_cap": c.market_cap,
                "rank": c.market_cap_rank
            } for c in cryptos]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# RISK MANAGEMENT ENDPOINTS ⭐ NEW
# ============================================================================

@app.route('/api/risk/evaluate', methods=['POST'])
def evaluate_risk():
    """
    تقييم المخاطرة للصفقة
    
    Request body:
    {
        "entry_price": 100,
        "target_price": 112,
        "stop_loss": 95,
        "signal": "BUY",
        "capital": 10000,
        "risk_percent": 2.0
    }
    """
    try:
        data = request.get_json()
        
        entry_price = float(data.get('entry_price', 0))
        target_price = float(data.get('target_price')) if data.get('target_price') else None
        stop_loss = float(data.get('stop_loss')) if data.get('stop_loss') else None
        signal = data.get('signal', 'BUY')
        capital = float(data.get('capital', 10000))
        risk_percent = float(data.get('risk_percent', 2.0))
        support = float(data.get('support_level')) if data.get('support_level') else None
        resistance = float(data.get('resistance_level')) if data.get('resistance_level') else None
        
        if entry_price <= 0:
            return jsonify({"success": False, "error": "entry_price is required"}), 400
        
        # Import RiskManager from unified_analyzer
        from unified_analyzer import RiskManager
        
        manager = RiskManager(capital=capital, risk_percent=risk_percent)
        assessment = manager.evaluate_trade(
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            signal=signal,
            support_level=support,
            resistance_level=resistance
        )
        
        return jsonify({
            "success": True,
            "assessment": assessment.to_dict()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/risk/position-size', methods=['POST'])
def calculate_position_size():
    """
    حساب حجم الصفقة
    
    Request body:
    {
        "entry_price": 100,
        "stop_loss": 95,
        "capital": 10000,
        "risk_percent": 2.0
    }
    """
    try:
        data = request.get_json()
        
        entry_price = float(data.get('entry_price', 0))
        stop_loss = float(data.get('stop_loss', 0))
        capital = float(data.get('capital', 10000))
        risk_percent = float(data.get('risk_percent', 2.0))
        
        if entry_price <= 0 or stop_loss <= 0:
            return jsonify({"success": False, "error": "entry_price and stop_loss are required"}), 400
        
        risk_amount = capital * (risk_percent / 100)
        sl_distance = abs(entry_price - stop_loss)
        shares = risk_amount / sl_distance if sl_distance > 0 else 0
        position_value = shares * entry_price
        
        return jsonify({
            "success": True,
            "position_size": {
                "capital": capital,
                "risk_percent": risk_percent,
                "risk_amount": risk_amount,
                "shares": round(shares, 2),
                "position_value": round(position_value, 2),
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "formula": f"Shares = ({capital} × {risk_percent}%) / {sl_distance:.2f} = {shares:.2f}"
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/risk/adx', methods=['POST'])
def calculate_adx():
    """
    حساب ADX
    
    Request body:
    {
        "highs": [100, 102, 101, ...],
        "lows": [95, 96, 94, ...],
        "closes": [98, 100, 99, ...],
        "period": 14
    }
    """
    try:
        data = request.get_json()
        
        highs = data.get('highs', [])
        lows = data.get('lows', [])
        closes = data.get('closes', [])
        period = int(data.get('period', 14))
        
        if not highs or not lows or not closes:
            return jsonify({"success": False, "error": "highs, lows, and closes are required"}), 400
        
        from unified_analyzer import ADXAnalyzer
        
        result = ADXAnalyzer.calculate(highs, lows, closes, period)
        
        return jsonify({
            "success": True,
            "adx_analysis": result,
            "interpretation": {
                "trend_type": "Trending Market" if result['adx'] and result['adx'] > 25 else "Ranging Market",
                "trading_strategy": "Follow the trend" if result['adx'] and result['adx'] > 25 else "Range trading / Wait for breakout"
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/risk/multi-timeframe', methods=['POST'])
def analyze_multi_timeframe():
    """
    تحليل متعدد الأطر الزمنية
    
    Request body:
    {
        "timeframes": {
            "weekly": {"trend": "BULLISH", "score": 2, "rsi": 45},
            "daily": {"trend": "BULLISH", "score": 3, "rsi": 50},
            "4h": {"trend": "BEARISH", "score": -1, "rsi": 65}
        }
    }
    """
    try:
        data = request.get_json()
        timeframes = data.get('timeframes', {})
        
        if not timeframes:
            return jsonify({"success": False, "error": "timeframes data is required"}), 400
        
        from unified_analyzer import MultiTimeframeAnalyzer
        
        result = MultiTimeframeAnalyzer.analyze(timeframes)
        
        return jsonify({
            "success": True,
            "multi_timeframe_analysis": result
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# OPEN INTEREST ENDPOINT ⭐ NEW
# ============================================================================

@app.route('/api/crypto/<coin_id>/open-interest', methods=['GET'])
def get_open_interest(coin_id):
    """
    Get Open Interest for a cryptocurrency (from CoinGecko)
    
    Example: /api/crypto/bitcoin/open-interest
    """
    if not ANALYZER_AVAILABLE:
        return jsonify({"success": False, "error": "Analyzer not available"}), 500
    
    try:
        # Get detailed coin data including derivatives
        import urllib.request
        
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id.lower()}/derivatives?include_tickers='all'"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        })
        
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
        
        if data:
            # Extract relevant info
            total_open_interest = sum(d.get('open_interest_usd', 0) or 0 for d in data)
            exchanges = set(d.get('market', '').split()[0] for d in data if d.get('market'))
            
            return jsonify({
                "success": True,
                "coin_id": coin_id.lower(),
                "open_interest": {
                    "total_usd": total_open_interest,
                    "exchanges": list(exchanges),
                    "data_points": len(data)
                }
            })
        
        return jsonify({
            "success": True,
            "coin_id": coin_id.lower(),
            "open_interest": None,
            "message": "No open interest data available"
        })
    except Exception as e:
        return jsonify({"success": True, "coin_id": coin_id.lower(), "open_interest": None, "error": str(e)})

# ============================================================================
# PATTERN RECOGNITION ENDPOINT ⭐ NEW
# ============================================================================

@app.route('/api/patterns/detect', methods=['POST'])
def detect_patterns():
    """
    التعرف على النماذج السعرية
    
    Request body:
    {
        "highs": [100, 102, 101, ...],
        "lows": [95, 96, 94, ...],
        "closes": [98, 100, 99, ...],
        "volumes": [1000, 1200, 1100, ...]  // optional
    }
    """
    try:
        data = request.get_json()
        
        highs = data.get('highs', [])
        lows = data.get('lows', [])
        closes = data.get('closes', [])
        volumes = data.get('volumes')
        
        if not highs or not lows or not closes:
            return jsonify({"success": False, "error": "highs, lows, and closes are required"}), 400
        
        if len(closes) < 50:
            return jsonify({
                "success": True,
                "patterns": [],
                "message": "Insufficient data (minimum 50 points required)"
            })
        
        from unified_analyzer import PatternRecognitionEngine
        
        engine = PatternRecognitionEngine()
        patterns = engine.analyze(highs, lows, closes, volumes)
        
        return jsonify({
            "success": True,
            "patterns_count": len(patterns),
            "patterns": [p.to_dict() for p in patterns],
            "pattern_score": engine.get_pattern_score()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/patterns/head-shoulders', methods=['POST'])
def detect_head_shoulders():
    """
    التعرف على نموذج الرأس والكتفين فقط
    
    Request body:
    {
        "highs": [100, 102, 101, ...],
        "lows": [95, 96, 94, ...],
        "closes": [98, 100, 99, ...]
    }
    """
    try:
        data = request.get_json()
        
        highs = data.get('highs', [])
        lows = data.get('lows', [])
        closes = data.get('closes', [])
        volumes = data.get('volumes')
        
        if not highs or not lows or not closes:
            return jsonify({"success": False, "error": "highs, lows, and closes are required"}), 400
        
        from unified_analyzer import PatternRecognitionEngine
        
        engine = PatternRecognitionEngine()
        engine._detect_head_and_shoulders(highs, lows, closes, volumes)
        
        hs_patterns = [p for p in engine.patterns_found if p.pattern_type == "HEAD_AND_SHOULDERS"]
        
        return jsonify({
            "success": True,
            "head_and_shoulders": [p.to_dict() for p in hs_patterns],
            "found": len(hs_patterns) > 0
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/patterns/triangles', methods=['POST'])
def detect_triangles():
    """
    التعرف على المثلثات السعرية
    
    Returns: Ascending, Descending, Symmetrical triangles
    """
    try:
        data = request.get_json()
        
        highs = data.get('highs', [])
        lows = data.get('lows', [])
        closes = data.get('closes', [])
        volumes = data.get('volumes')
        
        if not highs or not lows or not closes:
            return jsonify({"success": False, "error": "highs, lows, and closes are required"}), 400
        
        from unified_analyzer import PatternRecognitionEngine
        
        engine = PatternRecognitionEngine()
        engine._detect_triangles(highs, lows, closes, volumes)
        
        triangle_patterns = [p for p in engine.patterns_found if 'TRIANGLE' in p.pattern_type]
        
        return jsonify({
            "success": True,
            "triangles": [p.to_dict() for p in triangle_patterns],
            "found": len(triangle_patterns) > 0
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# OPEN INTEREST DIVERGENCE ENDPOINT ⭐ NEW (للكريبتو)
# ============================================================================

@app.route('/api/crypto/<coin_id>/oi-divergence', methods=['GET'])
def analyze_oi_divergence(coin_id):
    """
    تحليل تباعد العقود المفتوحة للكريبتو
    
    Bearish Divergence: السعر يصعد + OI يتناقص = تحذير
    Bullish Divergence: السعر يهبط + OI يتناقص = فرصة
    """
    try:
        period = request.args.get('period', 14, type=int)
        
        # الحصول على بيانات السعر
        crypto = get_fetcher().get_crypto(coin_id.lower())
        
        if not crypto:
            return jsonify({"success": False, "error": "Crypto not found"}), 404
        
        # الحصول على تاريخ الأسعار
        market_chart = get_fetcher().get_market_chart(coin_id, days=period)
        
        if not market_chart or 'prices' not in market_chart:
            return jsonify({"success": False, "error": "Price data not available"}), 404
        
        prices = [p[1] for p in market_chart['prices']]
        
        # محاولة الحصول على بيانات Open Interest
        # ملاحظة: CoinGecko API المجاني لا يوفر OI مباشرة
        # يمكن استخدام APIs أخرى مثل Coinglass أو Binance Futures
        
        # للعرض التوضيحي، نحسب تقدير بناءً على الحجم
        volumes = [v[1] for v in market_chart.get('total_volumes', [])]
        
        from unified_analyzer import OpenInterestAnalyzer
        
        # تقدير OI من الحجم (تقريبي)
        estimated_oi = volumes if volumes else None
        
        if estimated_oi and len(prices) >= period and len(estimated_oi) >= period:
            result = OpenInterestAnalyzer.analyze_divergence(prices, estimated_oi, period)
        else:
            result = {
                "divergence": None,
                "signal": "INSUFFICIENT_DATA",
                "warning": "Open Interest data not directly available from free API"
            }
        
        return jsonify({
            "success": True,
            "coin_id": coin_id.lower(),
            "current_price": crypto.current_price,
            "analysis": result,
            "note": "For accurate OI divergence, use premium APIs like Coinglass or Binance Futures"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# FIBONACCI ANALYZER ENDPOINT ⭐ NEW
# ============================================================================

@app.route('/api/fibonacci/retracement', methods=['POST'])
def calculate_fibonacci_retracement():
    """
    حساب مستويات تصحيح فيبوناتشي
    
    Request body:
    {
        "swing_high": 100,
        "swing_low": 80,
        "current_price": 90
    }
    """
    try:
        data = request.get_json()
        
        swing_high = float(data.get('swing_high', 0))
        swing_low = float(data.get('swing_low', 0))
        current_price = float(data.get('current_price', 0)) if data.get('current_price') else None
        
        if swing_high <= 0 or swing_low <= 0:
            return jsonify({"success": False, "error": "swing_high and swing_low are required"}), 400
        
        from unified_analyzer import FibonacciAnalyzer
        
        fib = FibonacciAnalyzer()
        levels = fib.calculate_retracement(swing_high, swing_low, current_price)
        
        # تحويل للـ dict
        levels_data = []
        for level in levels:
            levels_data.append({
                "level_name": level.level_name,
                "level_value": level.level_value,
                "price": level.price,
                "significance": level.significance,
                "description": level.description
            })
        
        # فحص إذا كان السعر الحالي عند مستوى ذهبي
        golden_check = None
        if current_price:
            golden_check = fib.check_price_at_golden_level(current_price)
        
        return jsonify({
            "success": True,
            "swing_high": swing_high,
            "swing_low": swing_low,
            "price_range": swing_high - swing_low,
            "retracement_levels": levels_data,
            "golden_level_check": golden_check,
            "golden_ratio_618": {
                "level": "61.8%",
                "price": swing_high - ((swing_high - swing_low) * 0.618),
                "significance": "CRITICAL - أقوى مستوى دعم/مقاومة"
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/fibonacci/extension', methods=['POST'])
def calculate_fibonacci_extension():
    """
    حساب امتدادات فيبوناتشي للأهداف السعرية
    
    Request body:
    {
        "wave_start": 100,      # بداية الموجة
        "wave_end": 120,        # نهاية الموجة
        "wave_retracement": 110  # نقطة التصحيح
    }
    """
    try:
        data = request.get_json()
        
        wave_start = float(data.get('wave_start', 0))
        wave_end = float(data.get('wave_end', 0))
        wave_retracement = float(data.get('wave_retracement', 0))
        
        if wave_start <= 0 or wave_end <= 0 or wave_retracement <= 0:
            return jsonify({"success": False, "error": "All wave parameters are required"}), 400
        
        from unified_analyzer import FibonacciAnalyzer
        
        fib = FibonacciAnalyzer()
        levels = fib.calculate_extension(wave_start, wave_end, wave_retracement)
        
        # تحويل للـ dict
        levels_data = []
        for level in levels:
            levels_data.append({
                "level_name": level.level_name,
                "level_value": level.level_value,
                "price": level.price,
                "significance": level.significance,
                "description": level.description
            })
        
        return jsonify({
            "success": True,
            "wave_start": wave_start,
            "wave_end": wave_end,
            "wave_retracement": wave_retracement,
            "wave_length": abs(wave_end - wave_start),
            "extension_levels": levels_data,
            "golden_extension_1618": {
                "level": "161.8%",
                "price": wave_retracement + (abs(wave_end - wave_start) * 1.618),
                "significance": "CRITICAL - الهدف الذهبي"
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/fibonacci/clusters', methods=['POST'])
def find_fibonacci_clusters():
    """
    البحث عن مناطق الكلستر (Fibonacci Clusters)
    
    الكلستر = تقاطع مستويين أو أكثر من فيبوناتشي
    أقوى مناطق الدعم والمقاومة
    
    Request body:
    {
        "swing_high": 100,
        "swing_low": 80,
        "current_price": 90
    }
    """
    try:
        data = request.get_json()
        
        swing_high = float(data.get('swing_high', 0))
        swing_low = float(data.get('swing_low', 0))
        current_price = float(data.get('current_price', 0)) if data.get('current_price') else (swing_high + swing_low) / 2
        
        if swing_high <= 0 or swing_low <= 0:
            return jsonify({"success": False, "error": "swing_high and swing_low are required"}), 400
        
        from unified_analyzer import FibonacciAnalyzer
        
        fib = FibonacciAnalyzer()
        retracements = fib.calculate_retracement(swing_high, swing_low, current_price)
        extensions = fib.calculate_extension(swing_low, swing_high, current_price)
        clusters = fib.find_cluster_zones(retracements, extensions)
        
        # تحويل للـ dict
        clusters_data = []
        for cluster in clusters:
            clusters_data.append({
                "price_zone_start": cluster.price_zone_start,
                "price_zone_end": cluster.price_zone_end,
                "levels_converging": cluster.levels_converging,
                "strength": cluster.strength,
                "confidence_boost": cluster.confidence_boost,
                "description": cluster.description
            })
        
        # تحقق إذا كان السعر الحالي في منطقة كلستر
        in_cluster = None
        for cluster in clusters:
            if cluster.price_zone_start <= current_price <= cluster.price_zone_end:
                in_cluster = {
                    "in_cluster": True,
                    "cluster": cluster.description,
                    "strength": cluster.strength
                }
                break
        
        return jsonify({
            "success": True,
            "swing_high": swing_high,
            "swing_low": swing_low,
            "current_price": current_price,
            "clusters_found": len(clusters),
            "clusters": clusters_data,
            "price_in_cluster": in_cluster,
            "trading_signal": "STRONG BUY/SELL" if in_cluster and in_cluster["strength"] == "VERY_STRONG" else "MODERATE" if in_cluster else "NEUTRAL"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/fibonacci/pattern-integration', methods=['POST'])
def fibonacci_pattern_integration():
    """
    دمج فيبوناتشي مع النماذج السعرية
    
    Request body:
    {
        "pattern_type": "HEAD_AND_SHOULERS",
        "pattern_high": 110,
        "pattern_low": 90,
        "current_price": 100
    }
    """
    try:
        data = request.get_json()
        
        pattern_type = data.get('pattern_type', 'UNKNOWN')
        pattern_high = float(data.get('pattern_high', 0))
        pattern_low = float(data.get('pattern_low', 0))
        current_price = float(data.get('current_price', 0))
        
        if pattern_high <= 0 or pattern_low <= 0:
            return jsonify({"success": False, "error": "pattern_high and pattern_low are required"}), 400
        
        from unified_analyzer import FibonacciAnalyzer
        
        fib = FibonacciAnalyzer()
        result = fib.integrate_with_pattern(pattern_type, pattern_high, pattern_low, current_price)
        
        return jsonify({
            "success": True,
            "pattern_type": pattern_type,
            "pattern_high": pattern_high,
            "pattern_low": pattern_low,
            "current_price": current_price,
            "fibonacci_integration": result["fibonacci_integration"],
            "confidence_boost": result["confidence_boost"],
            "signals": result["signals"],
            "enhanced_confidence": f"+{result['confidence_boost']}%" if result['confidence_boost'] > 0 else "No boost"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# CANDLESTICK PATTERN ANALYZER ENDPOINTS ⭐ "الفلتر النهائي"
# ============================================================================

@app.route('/api/candlestick/analyze', methods=['POST'])
def analyze_candlestick():
    """
    تحليل الشموع اليابانية - "الفلتر النهائي"
    
    النظام يعمل بطريقة الفلترة المزدوجة:
    1. منطقة الإشارة: Stochastics %D < 20 أو > 80
    2. التلاقي مع المستويات: فيبوناتشي 61.8% أو مناطق الكلستر
    
    Request body:
    {
        "candles": [
            {"open": 100, "high": 105, "low": 98, "close": 103},
            {"open": 103, "high": 108, "low": 102, "close": 107},
            ...
        ],
        "trend": "UPTREND",  // أو DOWNTREND أو NEUTRAL
        "stochastic_d": 25,   // اختياري - للفلترة
        "stochastic_k": 30,   // اختياري
        "fibonacci": {        // اختياري - للفلترة
            "swing_high": 110,
            "swing_low": 90
        }
    }
    """
    try:
        data = request.get_json()
        
        candles_data = data.get('candles', [])
        trend = data.get('trend', 'NEUTRAL')
        stochastic_d = data.get('stochastic_d')
        stochastic_k = data.get('stochastic_k')
        fib_data = data.get('fibonacci')
        
        if not candles_data or len(candles_data) < 1:
            return jsonify({"success": False, "error": "At least one candle is required"}), 400
        
        from unified_analyzer import CandlestickAnalyzer, CandleData, FibonacciAnalyzer
        
        # إنشاء محلل فيبوناتشي إذا توفرت البيانات
        fib_analyzer = None
        if fib_data and fib_data.get('swing_high') and fib_data.get('swing_low'):
            fib_analyzer = FibonacciAnalyzer()
            fib_analyzer.calculate_retracement(
                fib_data['swing_high'],
                fib_data['swing_low'],
                candles_data[-1]['close']
            )
        
        # إنشاء محلل الشموع
        analyzer = CandlestickAnalyzer(
            fibonacci_analyzer=fib_analyzer,
            stochastic_k=stochastic_k,
            stochastic_d=stochastic_d
        )
        
        # تحويل البيانات لكائنات CandleData
        candles = []
        for c in candles_data:
            candles.append(CandleData(
                open=float(c['open']),
                high=float(c['high']),
                low=float(c['low']),
                close=float(c['close']),
                volume=c.get('volume')
            ))
        
        # تحليل الشموع
        signals = analyzer.analyze_candles_batch(candles, trend)
        
        # أفضل إشارة
        best_signal = analyzer.get_best_signal()
        
        return jsonify({
            "success": True,
            "candles_analyzed": len(candles),
            "trend": trend,
            "patterns_found": len(signals),
            "signals": [
                {
                    "pattern": s.pattern_name,
                    "pattern_ar": s.pattern_name_ar,
                    "direction": s.signal_direction,
                    "confidence": s.confidence,
                    "strength": s.strength,
                    "entry": s.entry_price,
                    "stop_loss": s.stop_loss,
                    "target": s.target_price,
                    "description": s.description,
                    "confirmation_rules": s.confirmation_rules,
                    "filter_status": s.filter_status,
                    "risk_reward": s.risk_reward_ratio
                }
                for s in signals
            ],
            "best_signal": {
                "pattern": best_signal.pattern_name,
                "pattern_ar": best_signal.pattern_name_ar,
                "direction": best_signal.signal_direction,
                "confidence": best_signal.confidence,
                "strength": best_signal.strength,
                "entry": best_signal.entry_price,
                "stop_loss": best_signal.stop_loss,
                "target": best_signal.target_price,
                "filters_passed": best_signal.filter_status.get("overall_filter_passed", False)
            } if best_signal else None
        })
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "trace": traceback.format_exc()}), 500


@app.route('/api/candlestick/single', methods=['POST'])
def analyze_single_candle():
    """
    تحليل شمعة واحدة
    
    Request body:
    {
        "current": {"open": 100, "high": 105, "low": 98, "close": 103},
        "previous": {"open": 103, "high": 108, "low": 102, "close": 99},  // اختياري
        "prev2": {"open": 99, "high": 104, "low": 97, "close": 103},     // اختياري
        "trend": "DOWNTREND"
    }
    """
    try:
        data = request.get_json()
        
        current_data = data.get('current')
        prev_data = data.get('previous')
        prev2_data = data.get('prev2')
        trend = data.get('trend', 'NEUTRAL')
        
        if not current_data:
            return jsonify({"success": False, "error": "Current candle is required"}), 400
        
        from unified_analyzer import CandlestickAnalyzer, CandleData
        
        analyzer = CandlestickAnalyzer()
        
        current = CandleData(
            open=float(current_data['open']),
            high=float(current_data['high']),
            low=float(current_data['low']),
            close=float(current_data['close'])
        )
        
        prev = None
        if prev_data:
            prev = CandleData(
                open=float(prev_data['open']),
                high=float(prev_data['high']),
                low=float(prev_data['low']),
                close=float(prev_data['close'])
            )
        
        prev2 = None
        if prev2_data:
            prev2 = CandleData(
                open=float(prev2_data['open']),
                high=float(prev2_data['high']),
                low=float(prev2_data['low']),
                close=float(prev2_data['close'])
            )
        
        signals = analyzer.analyze_candle(current, prev, prev2, trend)
        
        return jsonify({
            "success": True,
            "trend": trend,
            "candle_info": {
                "body": current.body,
                "upper_shadow": current.upper_shadow,
                "lower_shadow": current.lower_shadow,
                "total_range": current.total_range,
                "is_bullish": current.is_bullish,
                "is_doji": current.is_doji,
                "body_to_range_ratio": round(current.body_to_range_ratio, 3)
            },
            "patterns_found": len(signals),
            "signals": [
                {
                    "pattern": s.pattern_name,
                    "pattern_ar": s.pattern_name_ar,
                    "direction": s.signal_direction,
                    "confidence": s.confidence,
                    "strength": s.strength,
                    "entry": s.entry_price,
                    "stop_loss": s.stop_loss,
                    "target": s.target_price,
                    "description": s.description,
                    "confirmation_rules": s.confirmation_rules
                }
                for s in signals
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/candlestick/hammer', methods=['POST'])
def detect_hammer():
    """
    كشف المطرقة (Hammer) - نموذج انعكاس صاعد
    
    الشروط:
    - جسم صغير في الجزء العلوي
    - ظل سفلي طويل (ضعفي الجسم على الأقل)
    - ظل علوي صغير أو معدوم
    """
    try:
        data = request.get_json()
        candle_data = data.get('candle')
        
        if not candle_data:
            return jsonify({"success": False, "error": "Candle data is required"}), 400
        
        from unified_analyzer import CandlestickAnalyzer, CandleData
        
        analyzer = CandlestickAnalyzer()
        candle = CandleData(
            open=float(candle_data['open']),
            high=float(candle_data['high']),
            low=float(candle_data['low']),
            close=float(candle_data['close'])
        )
        
        signal = analyzer._detect_hammer(candle, data.get('trend', 'DOWNTREND'))
        
        if signal:
            return jsonify({
                "success": True,
                "hammer_detected": True,
                "signal": {
                    "pattern": signal.pattern_name,
                    "pattern_ar": signal.pattern_name_ar,
                    "direction": signal.signal_direction,
                    "confidence": signal.confidence,
                    "entry": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "target": signal.target_price,
                    "confirmation_rules": signal.confirmation_rules
                }
            })
        else:
            return jsonify({
                "success": True,
                "hammer_detected": False,
                "reason": "Candle does not meet Hammer pattern criteria",
                "candle_analysis": {
                    "body_to_range_ratio": round(candle.body_to_range_ratio, 3),
                    "lower_shadow_to_body_ratio": round(candle.lower_shadow / candle.body, 2) if candle.body > 0 else 0,
                    "upper_shadow_to_body_ratio": round(candle.upper_shadow / candle.body, 2) if candle.body > 0 else 0,
                    "criteria": {
                        "small_body": candle.body_to_range_ratio <= 0.35,
                        "long_lower_shadow": candle.lower_shadow >= candle.body * 2 if candle.body > 0 else False,
                        "small_upper_shadow": candle.upper_shadow <= candle.body * 0.5 if candle.body > 0 else True
                    }
                }
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/candlestick/morning-star', methods=['POST'])
def detect_morning_star():
    """
    كشف نجمة الصباح (Morning Star) - نموذج انعكاس صاعد قوي
    
    النموذج المكون من 3 شمعات:
    1. شمعة سوداء طويلة
    2. شمعة صغيرة "نجمة"
    3. شمعة بيضاء تغلق فوق منتصف الشمعة الأولى
    """
    try:
        data = request.get_json()
        
        candles = data.get('candles', [])
        if len(candles) < 3:
            return jsonify({"success": False, "error": "At least 3 candles are required for Morning Star"}), 400
        
        from unified_analyzer import CandlestickAnalyzer, CandleData
        
        analyzer = CandlestickAnalyzer()
        
        candle = CandleData(
            open=float(candles[-1]['open']),
            high=float(candles[-1]['high']),
            low=float(candles[-1]['low']),
            close=float(candles[-1]['close'])
        )
        
        prev = CandleData(
            open=float(candles[-2]['open']),
            high=float(candles[-2]['high']),
            low=float(candles[-2]['low']),
            close=float(candles[-2]['close'])
        )
        
        prev2 = CandleData(
            open=float(candles[-3]['open']),
            high=float(candles[-3]['high']),
            low=float(candles[-3]['low']),
            close=float(candles[-3]['close'])
        )
        
        signal = analyzer._detect_morning_star(candle, prev, prev2)
        
        if signal:
            return jsonify({
                "success": True,
                "morning_star_detected": True,
                "signal": {
                    "pattern": signal.pattern_name,
                    "pattern_ar": signal.pattern_name_ar,
                    "confidence": signal.confidence,
                    "entry": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "target": signal.target_price,
                    "confirmation_rules": signal.confirmation_rules
                }
            })
        else:
            return jsonify({
                "success": True,
                "morning_star_detected": False,
                "reason": "Candles do not meet Morning Star criteria"
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/candlestick/evening-star', methods=['POST'])
def detect_evening_star():
    """
    كشف نجمة المساء (Evening Star) - نموذج انعكاس هابط قوي
    
    عكس نجمة الصباح:
    1. شمعة بيضاء طويلة
    2. شمعة صغيرة "نجمة"
    3. شمعة سوداء تغلق تحت منتصف الشمعة الأولى
    """
    try:
        data = request.get_json()
        
        candles = data.get('candles', [])
        if len(candles) < 3:
            return jsonify({"success": False, "error": "At least 3 candles are required for Evening Star"}), 400
        
        from unified_analyzer import CandlestickAnalyzer, CandleData
        
        analyzer = CandlestickAnalyzer()
        
        candle = CandleData(
            open=float(candles[-1]['open']),
            high=float(candles[-1]['high']),
            low=float(candles[-1]['low']),
            close=float(candles[-1]['close'])
        )
        
        prev = CandleData(
            open=float(candles[-2]['open']),
            high=float(candles[-2]['high']),
            low=float(candles[-2]['low']),
            close=float(candles[-2]['close'])
        )
        
        prev2 = CandleData(
            open=float(candles[-3]['open']),
            high=float(candles[-3]['high']),
            low=float(candles[-3]['low']),
            close=float(candles[-3]['close'])
        )
        
        signal = analyzer._detect_evening_star(candle, prev, prev2)
        
        if signal:
            return jsonify({
                "success": True,
                "evening_star_detected": True,
                "signal": {
                    "pattern": signal.pattern_name,
                    "pattern_ar": signal.pattern_name_ar,
                    "confidence": signal.confidence,
                    "entry": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "target": signal.target_price,
                    "confirmation_rules": signal.confirmation_rules
                }
            })
        else:
            return jsonify({
                "success": True,
                "evening_star_detected": False,
                "reason": "Candles do not meet Evening Star criteria"
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/candlestick/piercing-line', methods=['POST'])
def detect_piercing_line():
    """
    كشف الخط الثاقب (Piercing Line) - نموذج انعكاس صاعد
    
    الشروط:
    1. شمعة سوداء طويلة
    2. شمعة بيضاء تفتح بفجوة لأسفل
    3. تغلق فوق منتصف جسم الشمعة السوداء (قاعدة الـ 50%)
    """
    try:
        data = request.get_json()
        
        candles = data.get('candles', [])
        if len(candles) < 2:
            return jsonify({"success": False, "error": "At least 2 candles are required for Piercing Line"}), 400
        
        from unified_analyzer import CandlestickAnalyzer, CandleData
        
        analyzer = CandlestickAnalyzer()
        
        candle = CandleData(
            open=float(candles[-1]['open']),
            high=float(candles[-1]['high']),
            low=float(candles[-1]['low']),
            close=float(candles[-1]['close'])
        )
        
        prev = CandleData(
            open=float(candles[-2]['open']),
            high=float(candles[-2]['high']),
            low=float(candles[-2]['low']),
            close=float(candles[-2]['close'])
        )
        
        signal = analyzer._detect_piercing_line(candle, prev)
        
        if signal:
            return jsonify({
                "success": True,
                "piercing_line_detected": True,
                "signal": {
                    "pattern": signal.pattern_name,
                    "pattern_ar": signal.pattern_name_ar,
                    "confidence": signal.confidence,
                    "entry": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "target": signal.target_price,
                    "confirmation_rules": signal.confirmation_rules
                }
            })
        else:
            return jsonify({
                "success": True,
                "piercing_line_detected": False,
                "reason": "Candles do not meet Piercing Line criteria (50% rule not satisfied)"
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/candlestick/dark-cloud', methods=['POST'])
def detect_dark_cloud():
    """
    كشف سحابة الظلام (Dark Cloud Cover) - نموذج انعكاس هابط
    
    الشروط:
    1. شمعة بيضاء طويلة
    2. شمعة سوداء تفتح بفجوة لأعلى
    3. تغلق تحت منتصف جسم الشمعة البيضاء (قاعدة الـ 50%)
    """
    try:
        data = request.get_json()
        
        candles = data.get('candles', [])
        if len(candles) < 2:
            return jsonify({"success": False, "error": "At least 2 candles are required for Dark Cloud Cover"}), 400
        
        from unified_analyzer import CandlestickAnalyzer, CandleData
        
        analyzer = CandlestickAnalyzer()
        
        candle = CandleData(
            open=float(candles[-1]['open']),
            high=float(candles[-1]['high']),
            low=float(candles[-1]['low']),
            close=float(candles[-1]['close'])
        )
        
        prev = CandleData(
            open=float(candles[-2]['open']),
            high=float(candles[-2]['high']),
            low=float(candles[-2]['low']),
            close=float(candles[-2]['close'])
        )
        
        signal = analyzer._detect_dark_cloud_cover(candle, prev)
        
        if signal:
            return jsonify({
                "success": True,
                "dark_cloud_detected": True,
                "signal": {
                    "pattern": signal.pattern_name,
                    "pattern_ar": signal.pattern_name_ar,
                    "confidence": signal.confidence,
                    "entry": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "target": signal.target_price,
                    "confirmation_rules": signal.confirmation_rules
                }
            })
        else:
            return jsonify({
                "success": True,
                "dark_cloud_detected": False,
                "reason": "Candles do not meet Dark Cloud Cover criteria (50% rule not satisfied)"
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/candlestick/patterns-list', methods=['GET'])
def list_candlestick_patterns():
    """
    قائمة جميع النماذج المدعومة
    """
    return jsonify({
        "success": True,
        "patterns": {
            "bullish_reversal": [
                {"name": "Hammer", "name_ar": "المطرقة", "confidence": 75, "description": "انعكاس صاعد عند القاع"},
                {"name": "Inverted Hammer", "name_ar": "المطرقة المقلوبة", "confidence": 70, "description": "انعكاس صاعد يحتاج تأكيد"},
                {"name": "Morning Star", "name_ar": "نجمة الصباح", "confidence": 85, "description": "انعكاس صاعد قوي (3 شمعات)"},
                {"name": "Piercing Line", "name_ar": "الخط الثاقب", "confidence": 80, "description": "انعكاس صاعد مع قاعدة 50%"},
                {"name": "Bullish Engulfing", "name_ar": "الابتلاع الصاعد", "confidence": 82, "description": "انعكاس صاعد قوي جداً"},
                {"name": "Bullish Harami", "name_ar": "هارامي صاعد", "confidence": 65, "description": "انعكاس يحتاج تأكيد"}
            ],
            "bearish_reversal": [
                {"name": "Shooting Star", "name_ar": "الشهاب", "confidence": 75, "description": "انعكاس هابط عند القمة"},
                {"name": "Evening Star", "name_ar": "نجمة المساء", "confidence": 85, "description": "انعكاس هابط قوي (3 شمعات)"},
                {"name": "Dark Cloud Cover", "name_ar": "سحابة الظلام", "confidence": 80, "description": "انعكاس هابط مع قاعدة 50%"},
                {"name": "Bearish Engulfing", "name_ar": "الابتلاع الهابط", "confidence": 82, "description": "انعكاس هابط قوي جداً"},
                {"name": "Bearish Harami", "name_ar": "هارامي هابط", "confidence": 65, "description": "انعكاس يحتاج تأكيد"}
            ],
            "continuation": [
                {"name": "Marubozu", "name_ar": "ماروبوزو", "confidence": 80, "description": "قوة اتجاهية واضحة"},
                {"name": "Spinning Top", "name_ar": "القمة المغزلية", "confidence": 45, "description": "حيرة وتردد"},
                {"name": "Doji", "name_ar": "دوجي", "confidence": 50, "description": "تردد - لا إشارة"}
            ]
        },
        "filter_rules": {
            "stochastic_filter": {
                "bullish": "Stochastics %D < 20 (ذروة البيع)",
                "bearish": "Stochastics %D > 80 (ذروة الشراء)"
            },
            "fibonacci_filter": "السعر عند مستوى 61.8% أو منطقة كلستر",
            "confidence_adjustment": {
                "filters_passed": "+10% to +25% confidence boost",
                "no_filters": "-50% confidence penalty"
            }
        },
        "risk_management": {
            "stop_loss_bullish": "تحت أدنى نقطة للظل السفلي بمسافة أمان",
            "stop_loss_bearish": "فوق أعلى قمة للظل العلوي بمسافة أمان",
            "risk_reward": "1:3 (الهدف = 3 × المسافة للوقف)"
        }
    })


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print(f"\n{'='*60}")
    print(" Crypto Analysis API - Enhanced")
    print(f"{'='*60}")
    print(f"Port: {PORT}")
    print(f"Analyzer Available: {ANALYZER_AVAILABLE}")
    print(f"Features:")
    print(f"  - Pattern Recognition (Head & Shoulders, Triangles, etc.)")
    print(f"  - Fibonacci Clusters & Golden Levels")
    print(f"  - Candlestick Patterns (الفلتر النهائي)")
    print(f"  - Open Interest Divergence")
    print(f"  - Dual Filter System (Stochastics + Fibonacci)")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
