#!/usr/bin/env python3
"""
Recommendation Verification API
================================
API لتقييم التوصيات والاختبار الخلفي

Endpoints:
- POST /api/verify/recommendation - Verify a single recommendation
- POST /api/verify/batch - Verify multiple recommendations
- GET /api/backtest/<ticker> - Backtest a stock
- GET /api/performance/summary - Get performance summary
- POST /api/compare/expert - Compare AI vs Expert performance

Run: python recommendation_api.py --port 8011
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Flask, request, jsonify
from flask_cors import CORS

# Import verification engine
try:
    from recommendation_verifier import (
        RecommendationVerifier, 
        BacktestEngine, 
        Recommendation,
        PerformanceAnalyzer
    )
    VERIFIER_AVAILABLE = True
except ImportError:
    VERIFIER_AVAILABLE = False

# Import unified configuration
try:
    from config import DATABASE_PATH, API_PORT
    PORT = int(os.environ.get('PORT', 8011))  # Use different port for this service
except ImportError:
    # Fallback if config.py not available
    DATABASE_PATH = os.environ.get('DATABASE_PATH', '/root/GLMinvestment/db/egx_investment.db')
    PORT = int(os.environ.get('PORT', 8011))

API_KEY = os.environ.get('API_KEY', 'mubasher-sync-2024-secret')

app = Flask(__name__)
CORS(app)

# ============================================================================
# AUTHENTICATION
# ============================================================================

def check_auth():
    """Check API key authentication"""
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    if api_key != API_KEY:
        return False
    return True

@app.before_request
def before_request():
    """Check authentication for all requests"""
    # Skip auth for health check
    if request.path == '/health':
        return None
    
    if not check_auth():
        return jsonify({
            "success": False,
            "error": "Unauthorized - Invalid API key"
        }), 401

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "recommendation-verification-api",
        "version": "1.0.0",
        "verifier_available": VERIFIER_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    })

# ============================================================================
# VERIFICATION ENDPOINTS
# ============================================================================

@app.route('/api/verify/recommendation', methods=['POST'])
def verify_recommendation():
    """
    Verify a single recommendation against actual prices
    
    Request body:
    {
        "ticker": "COMI",
        "action": "BUY",
        "entry_price": 25.50,
        "target_price": 28.00,
        "stop_loss": 24.00,
        "recommendation_date": "2025-01-01",
        "days_to_check": 30
    }
    """
    if not VERIFIER_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Verification engine not available"
        }), 500
    
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    required = ['ticker', 'action', 'entry_price', 'recommendation_date']
    for field in required:
        if field not in data:
            return jsonify({"success": False, "error": f"Missing field: {field}"}), 400
    
    try:
        verifier = RecommendationVerifier(DATABASE_PATH)
        
        rec = Recommendation(
            id=str(uuid.uuid4()),
            ticker=data['ticker'].upper(),
            action=data['action'].upper(),
            entry_price=float(data['entry_price']),
            target_price=float(data['target_price']) if data.get('target_price') else None,
            stop_loss=float(data['stop_loss']) if data.get('stop_loss') else None,
            recommendation_date=data['recommendation_date'],
            expert_name=data.get('expert_name'),
            source=data.get('source', 'MANUAL')
        )
        
        days = data.get('days_to_check', 30)
        result = verifier.verify_recommendation(rec, days)
        
        return jsonify({
            "success": True,
            "verification": {
                "ticker": result.ticker,
                "action": result.action,
                "entry_price": result.entry_price,
                "target_price": result.target_price,
                "stop_loss": result.stop_loss,
                "highest_price_after": result.highest_price_after,
                "lowest_price_after": result.lowest_price_after,
                "final_price": result.final_price,
                "hit_target": result.hit_target,
                "hit_stop_loss": result.hit_stop_loss,
                "status": result.status,
                "profit_loss_percent": result.profit_loss_percent,
                "days_checked": result.days_checked,
                "verification_date": result.verification_date
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/verify/batch', methods=['POST'])
def verify_batch():
    """
    Verify multiple recommendations at once
    
    Request body:
    {
        "recommendations": [
            {...},
            {...}
        ],
        "days_to_check": 30
    }
    """
    if not VERIFIER_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Verification engine not available"
        }), 500
    
    data = request.get_json()
    
    if not data or 'recommendations' not in data:
        return jsonify({"success": False, "error": "No recommendations provided"}), 400
    
    try:
        verifier = RecommendationVerifier(DATABASE_PATH)
        days = data.get('days_to_check', 30)
        
        results = []
        success_count = 0
        stopped_count = 0
        pending_count = 0
        
        for rec_data in data['recommendations']:
            try:
                rec = Recommendation(
                    id=rec_data.get('id', str(uuid.uuid4())),
                    ticker=rec_data['ticker'].upper(),
                    action=rec_data['action'].upper(),
                    entry_price=float(rec_data['entry_price']),
                    target_price=float(rec_data['target_price']) if rec_data.get('target_price') else None,
                    stop_loss=float(rec_data['stop_loss']) if rec_data.get('stop_loss') else None,
                    recommendation_date=rec_data['recommendation_date'],
                    expert_name=rec_data.get('expert_name'),
                    source=rec_data.get('source', 'BATCH')
                )
                
                result = verifier.verify_recommendation(rec, days)
                
                if result.hit_target:
                    success_count += 1
                elif result.hit_stop_loss:
                    stopped_count += 1
                elif result.status == "PENDING":
                    pending_count += 1
                
                results.append({
                    "ticker": result.ticker,
                    "status": result.status,
                    "hit_target": result.hit_target,
                    "profit_loss_percent": result.profit_loss_percent
                })
                
            except Exception as e:
                results.append({
                    "ticker": rec_data.get('ticker', 'UNKNOWN'),
                    "error": str(e)
                })
        
        total = len(results)
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        return jsonify({
            "success": True,
            "summary": {
                "total": total,
                "success_count": success_count,
                "stopped_count": stopped_count,
                "pending_count": pending_count,
                "success_rate": round(success_rate, 2)
            },
            "results": results
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# BACKTEST ENDPOINTS
# ============================================================================

@app.route('/api/backtest/<ticker>', methods=['GET'])
def backtest_stock(ticker):
    """
    Backtest a specific stock
    
    Query params:
    - days: Number of days to backtest (default: 90)
    - holding_period: Days to hold each position (default: 5)
    """
    if not VERIFIER_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Verification engine not available"
        }), 500
    
    try:
        engine = BacktestEngine(DATABASE_PATH)
        
        days = request.args.get('days', 90, type=int)
        holding_period = request.args.get('holding_period', 5, type=int)
        
        result = engine.backtest_stock(ticker.upper(), days, holding_period)
        
        return jsonify({
            "success": True,
            "backtest": {
                "ticker": result.ticker,
                "period_days": result.period_days,
                "total_trades": result.total_trades,
                "winning_trades": result.winning_trades,
                "losing_trades": result.losing_trades,
                "win_rate": round(result.win_rate, 2),
                "avg_return": round(result.avg_return, 2),
                "max_return": round(result.max_return, 2),
                "max_loss": round(result.max_loss, 2),
                "total_return": round(result.total_return, 2),
                "signals": result.signals
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/backtest/popular', methods=['GET'])
def backtest_popular():
    """
    Backtest popular EGX stocks
    
    Query params:
    - days: Number of days to backtest (default: 90)
    """
    if not VERIFIER_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Verification engine not available"
        }), 500
    
    try:
        engine = BacktestEngine(DATABASE_PATH)
        days = request.args.get('days', 90, type=int)
        
        popular = ["COMI", "HRHO", "SWDY", "ETEL", "EKHO", "TMGH", "PHDC", "GTHE", 
                   "ESRS", "ORHD", "CIEB", "AMER", "HELI", "OCDI", "JUFO", "ABUK"]
        
        results = engine.backtest_multiple(popular, days)
        
        summary = []
        total_trades = 0
        total_wins = 0
        total_return = 0
        
        for ticker, result in results.items():
            total_trades += result.total_trades
            total_wins += result.winning_trades
            total_return += result.total_return
            
            summary.append({
                "ticker": result.ticker,
                "total_trades": result.total_trades,
                "win_rate": round(result.win_rate, 2),
                "avg_return": round(result.avg_return, 2),
                "total_return": round(result.total_return, 2)
            })
        
        overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        
        return jsonify({
            "success": True,
            "summary": {
                "stocks_tested": len(results),
                "total_trades": total_trades,
                "overall_win_rate": round(overall_win_rate, 2),
                "total_return": round(total_return, 2)
            },
            "stocks": sorted(summary, key=lambda x: x['win_rate'], reverse=True)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# PERFORMANCE ENDPOINTS
# ============================================================================

@app.route('/api/performance/summary', methods=['GET'])
def performance_summary():
    """
    Get overall performance summary of the recommendation system
    """
    if not VERIFIER_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Verification engine not available"
        }), 500
    
    try:
        engine = BacktestEngine(DATABASE_PATH)
        
        # Backtest top stocks
        top_stocks = ["COMI", "HRHO", "SWDY", "ETEL", "EKHO"]
        results = engine.backtest_multiple(top_stocks, 90)
        
        total_predictions = 0
        successful = 0
        total_return = 0
        
        for ticker, result in results.items():
            total_predictions += result.total_trades
            successful += result.winning_trades
            total_return += result.total_return
        
        success_rate = (successful / total_predictions * 100) if total_predictions > 0 else 0
        
        return jsonify({
            "success": True,
            "performance": {
                "period": "90 days",
                "total_predictions": total_predictions,
                "successful": successful,
                "success_rate": round(success_rate, 2),
                "total_return": round(total_return, 2),
                "avg_return_per_trade": round(total_return / total_predictions, 2) if total_predictions > 0 else 0
            },
            "by_stock": {
                ticker: {
                    "win_rate": result.win_rate,
                    "total_return": result.total_return
                }
                for ticker, result in results.items()
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/compare/expert', methods=['POST'])
def compare_expert():
    """
    Compare AI performance vs Expert performance
    
    Request body:
    {
        "expert_recommendations": [
            {
                "ticker": "EHDR",
                "action": "BUY",
                "entry_price": 2.35,
                "target_price": 2.48,
                "stop_loss": 2.27,
                "recommendation_date": "2026-05-14",
                "expert_name": "ريمون رؤوف"
            }
        ],
        "days_to_check": 30
    }
    """
    if not VERIFIER_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Verification engine not available"
        }), 500
    
    data = request.get_json()
    
    if not data or 'expert_recommendations' not in data:
        return jsonify({"success": False, "error": "No expert recommendations provided"}), 400
    
    try:
        engine = BacktestEngine(DATABASE_PATH)
        days = data.get('days_to_check', 30)
        
        comparison = engine.compare_with_expert(data['expert_recommendations'], days)
        
        return jsonify({
            "success": True,
            "comparison": comparison
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print(f"\n{'='*60}")
    print("Recommendation Verification API")
    print(f"{'='*60}")
    print(f"Port: {PORT}")
    print(f"Database: {DATABASE_PATH}")
    print(f"Verifier Available: {VERIFIER_AVAILABLE}")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
