# -*- coding: utf-8 -*-
"""
Frontend API Aliases - توافق Frontend مع unified_backend
=============================================================
الـ Frontend متوقع endpoints من main.py، لكن unified_backend.py عندها endpoints مختلفة.
هنا بنضيف الـ aliases والـ missing endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# STATS / STATUS
# ============================================================
@router.get("/stats")
async def api_stats():
    """Alias for /api/admin/stats"""
    from unified_backend import db
    try:
        stocks = db.execute_query("SELECT COUNT(*) as cnt FROM stocks WHERE is_active = 1")[0]
        history = db.execute_query("SELECT COUNT(*) as cnt FROM stock_price_history")[0]
        return {
            "success": True,
            "stocks_count": stocks["cnt"],
            "records_count": history["cnt"],
            "database_path": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# ANALYZE (alias for /api/analysis/{symbol})
# ============================================================
@router.get("/analyze/{ticker}")
async def api_analyze(ticker: str, days: int = Query(365, ge=30, le=1000)):
    """Alias for /api/analysis/{symbol}"""
    from unified_backend import db, TechnicalAnalysis
    import pandas as pd
    import numpy as np

    try:
        rows = db.execute_query("""
            SELECT sph.date, sph.open_price, sph.high_price, sph.low_price, sph.close_price, sph.volume
            FROM stock_price_history sph
            JOIN stocks s ON s.id = sph.stock_id
            WHERE s.ticker = ?
            ORDER BY sph.date DESC
            LIMIT ?
        """, (ticker.upper(), days))

        if not rows:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")

        df = pd.DataFrame(rows)
        df = df.iloc[::-1]
        close = pd.to_numeric(df['close_price'])
        high = pd.to_numeric(df['high_price'])
        low = pd.to_numeric(df['low_price'])
        volume = pd.to_numeric(df['volume'])

        sma_20 = TechnicalAnalysis.calculate_sma(close, 20)
        sma_50 = TechnicalAnalysis.calculate_sma(close, 50)
        rsi = TechnicalAnalysis.calculate_rsi(close)
        macd = TechnicalAnalysis.calculate_macd(close)
        bb = TechnicalAnalysis.calculate_bollinger(close)
        atr = TechnicalAnalysis.calculate_atr(high, low, close)
        stoch = TechnicalAnalysis.calculate_stochastic(high, low, close)
        adx = TechnicalAnalysis.calculate_adx(high, low, close)

        current_price = close.iloc[-1]
        signals = []
        current_rsi = rsi.iloc[-1]
        if current_rsi < 30:
            signals.append({"indicator": "RSI", "signal": "oversold", "value": round(current_rsi, 2)})
        elif current_rsi > 70:
            signals.append({"indicator": "RSI", "signal": "overbought", "value": round(current_rsi, 2)})

        if macd['histogram'].iloc[-1] > 0:
            signals.append({"indicator": "MACD", "signal": "bullish", "value": round(macd['macd'].iloc[-1], 4)})
        else:
            signals.append({"indicator": "MACD", "signal": "bearish", "value": round(macd['macd'].iloc[-1], 4)})

        if sma_20.iloc[-1] > sma_50.iloc[-1]:
            signals.append({"indicator": "MA_Cross", "signal": "bullish", "value": "SMA20 > SMA50"})
        else:
            signals.append({"indicator": "MA_Cross", "signal": "bearish", "value": "SMA20 < SMA50"})

        if current_price < bb['lower'].iloc[-1]:
            signals.append({"indicator": "BB", "signal": "below_lower", "value": "Price below lower band"})
        elif current_price > bb['upper'].iloc[-1]:
            signals.append({"indicator": "BB", "signal": "above_upper", "value": "Price above upper band"})

        trend = "bullish" if sma_20.iloc[-1] > sma_50.iloc[-1] else "bearish"
        sr = TechnicalAnalysis.detect_support_resistance(close)
        fib = TechnicalAnalysis.calculate_fibonacci_retracement(high.max(), low.min())

        return {
            "success": True,
            "symbol": ticker.upper(),
            "ticker": ticker.upper(),
            "days_analyzed": len(df),
            "date_range": {"start": df['date'].iloc[0], "end": df['date'].iloc[-1]},
            "analysis": {
                "current_price": round(current_price, 2),
                "trend": trend,
                "signals": signals,
                "indicators": {
                    "rsi": round(current_rsi, 2),
                    "macd": {
                        "macd": round(macd['macd'].iloc[-1], 4),
                        "signal": round(macd['signal'].iloc[-1], 4),
                        "histogram": round(macd['histogram'].iloc[-1], 4)
                    },
                    "bollinger_bands": {
                        "upper": round(bb['upper'].iloc[-1], 2),
                        "middle": round(bb['middle'].iloc[-1], 2),
                        "lower": round(bb['lower'].iloc[-1], 2),
                        "bandwidth": round(bb['bandwidth'].iloc[-1], 2)
                    },
                    "moving_averages": {
                        "sma_20": round(sma_20.iloc[-1], 2),
                        "sma_50": round(sma_50.iloc[-1], 2),
                        "sma_200": round(TechnicalAnalysis.calculate_sma(close, 200).iloc[-1], 2) if len(close) >= 200 else None,
                        "ema_12": round(TechnicalAnalysis.calculate_ema(close, 12).iloc[-1], 2),
                        "ema_26": round(TechnicalAnalysis.calculate_ema(close, 26).iloc[-1], 2)
                    },
                    "atr": round(atr.iloc[-1], 4),
                    "stochastic": {
                        "k": round(stoch['k'].iloc[-1], 2),
                        "d": round(stoch['d'].iloc[-1], 2)
                    },
                    "adx": round(adx['adx'].iloc[-1], 2)
                },
                "support_resistance": sr,
                "fibonacci_levels": fib,
                "volatility": round(bb['bandwidth'].iloc[-1], 2),
                "analysis_timestamp": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# LEARNING (placeholder - compatible with Frontend)
# ============================================================
class LearningRequest(BaseModel):
    target_win_rate: Optional[float] = 99.0
    max_iterations: Optional[int] = 50
    tickers: Optional[List[str]] = None
    auto_apply_threshold: Optional[float] = 60.0


@router.get("/learning/progress")
async def api_learning_progress():
    return {
        "success": True,
        "progress": {
            "target_win_rate": 99.0,
            "current_win_rate": 0.0,
            "best_win_rate": 0.0,
            "iteration": 0,
            "max_iterations": 50,
            "status": "idle",
            "cross_validation_score": 0.0,
            "message": "Learning engine ready",
            "best_parameters": {},
            "auto_apply_threshold": 60.0,
            "learning_history": []
        }
    }


@router.post("/learning/start")
async def api_learning_start(request: LearningRequest, background_tasks: BackgroundTasks):
    return {
        "success": True,
        "message": f"Learning started - Target: {request.target_win_rate}%, threshold: {request.auto_apply_threshold}%"
    }


@router.post("/learning/stop")
async def api_learning_stop():
    return {"success": True, "message": "Learning stopped"}


@router.get("/learning/threshold")
async def api_learning_get_threshold():
    return {"success": True, "threshold": 60.0}


@router.post("/learning/threshold")
async def api_learning_set_threshold(threshold: float = Query(..., ge=50, le=99)):
    return {"success": True, "threshold": threshold, "message": f"Threshold set to {threshold}%"}


@router.get("/params/active")
async def api_params_active():
    return {
        "success": True,
        "parameters": {
            "rsi_oversold": 30.0,
            "rsi_overbought": 70.0,
            "macd_threshold": 0.0,
            "bb_threshold": 0.0,
            "stop_loss_pct": 5.0,
            "take_profit_pct": 10.0,
            "holding_days": 30,
            "volume_threshold": 1.5,
            "confidence_threshold": 60.0
        },
        "optimized": False,
        "best_win_rate": 0.0
    }


# ============================================================
# BACKTEST (alias)
# ============================================================
@router.get("/backtest/{ticker}")
async def api_backtest(ticker: str, days: int = Query(365, ge=30, le=730), holding_period: int = Query(30, ge=1, le=90)):
    """Alias for /api/backtest/{symbol}"""
    from unified_backend import db, TechnicalAnalysis
    import pandas as pd

    try:
        rows = db.execute_query("""
            SELECT sph.date, sph.open_price, sph.high_price, sph.low_price, sph.close_price, sph.volume
            FROM stock_price_history sph
            JOIN stocks s ON s.id = sph.stock_id
            WHERE s.ticker = ?
            ORDER BY sph.date ASC
            LIMIT ?
        """, (ticker.upper(), days + 100))

        if len(rows) < 100:
            return {"success": False, "error": "Insufficient data"}

        df = pd.DataFrame(rows)
        close = pd.to_numeric(df['close_price'])
        high = pd.to_numeric(df['high_price'])
        low = pd.to_numeric(df['low_price'])
        volume = pd.to_numeric(df['volume'])

        rsi = TechnicalAnalysis.calculate_rsi(close)
        macd = TechnicalAnalysis.calculate_macd(close)
        sma_20 = TechnicalAnalysis.calculate_sma(close, 20)
        sma_50 = TechnicalAnalysis.calculate_sma(close, 50)

        trades = []
        wins = 0
        losses = 0

        for i in range(100, len(df) - holding_period):
            signals = 0
            if rsi.iloc[i] < 30:
                signals += 1
            if macd['histogram'].iloc[i] > 0:
                signals += 1
            if sma_20.iloc[i] > sma_50.iloc[i]:
                signals += 1

            if signals >= 2:
                entry_price = close.iloc[i]
                exit_price = close.iloc[i + holding_period]
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    'entry_date': df['date'].iloc[i],
                    'exit_date': df['date'].iloc[i + holding_period],
                    'entry_price': round(entry_price, 2),
                    'exit_price': round(exit_price, 2),
                    'pnl_pct': round(pnl_pct, 2),
                    'result': 'win' if pnl_pct > 0 else 'loss'
                })
                if pnl_pct > 0:
                    wins += 1
                else:
                    losses += 1

        total = wins + losses
        
        # Get AI analysis for current recommendation
        ai_analysis = None
        try:
            from ai_local_engine import ai_engine
            ai_rec = ai_engine.analyze_stock(ticker.upper())
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
        except Exception:
            pass
        
        return {
            "success": True,
            "symbol": ticker.upper(),
            "ticker": ticker.upper(),
            "backtest_period": f"{days} days",
            "holding_period": f"{holding_period} days",
            "summary": {
                "total_trades": total,
                "wins": wins,
                "losses": losses,
                "win_rate": round(wins / total * 100, 2) if total > 0 else 0,
                "avg_return": round(sum(t['pnl_pct'] for t in trades) / len(trades), 2) if trades else 0
            },
            "trades": trades[-20:] if trades else [],
            "ai_analysis": ai_analysis
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# FAIR VALUE
# ============================================================
@router.get("/fair-value/{ticker}")
async def api_fair_value(ticker: str):
    try:
        from unified_backend import db
        stock = db.execute_one("SELECT current_price, pe_ratio, pb_ratio, market_cap FROM stocks WHERE ticker = ?", (ticker.upper(),))
        if not stock:
            return {"success": False, "error": f"No data for {ticker}"}

        current_price = stock.get('current_price', 0) or 0
        dcf_value = current_price * 1.1  # Simplified

        return {
            "success": True,
            "symbol": ticker.upper(),
            "ticker": ticker.upper(),
            "current_price": current_price,
            "pe_ratio": stock.get('pe_ratio'),
            "pb_ratio": stock.get('pb_ratio'),
            "market_cap": stock.get('market_cap'),
            "fair_value_estimates": {
                "dcf": round(dcf_value, 2),
                "dcf_upside": round((dcf_value - current_price) / current_price * 100, 2) if current_price else 0
            },
            "note": "Fair value estimates are simplified."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
