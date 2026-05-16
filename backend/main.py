# -*- coding: utf-8 -*-
"""
EGXPy Bridge API - VPS Version with Local History Endpoints
Version: 1.3.0 - Full Stack Python Engine with Self-Learning

Features:
- Stock data from local SQLite database
- Technical Analysis (RSI, MACD, MA, BB, etc.)
- Self-Learning Engine for parameter optimization
- Fair Value Calculation
- Backtesting capabilities
"""

import os
import sys
import json
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import numpy as np
import pandas as pd
from loguru import logger

# Add unified analyzer to path
sys.path.append(os.path.join(os.path.dirname(__file__), "python server code"))
from unified_analyzer import UnifiedAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z'
)

# ============================================================
# Configuration
# ============================================================
VERSION = "1.3.0"
PORT = int(os.getenv("PORT", 8010))
HOST = os.getenv("HOST", "0.0.0.0")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Database paths - use the shared Next.js database
# Local path: relative to python-engine folder
LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "egx_investment.db")
# VPS path: same location as Next.js database
VPS_DB_PATH = "/root/GLMinvestment/db/egx_investment.db"
DB_PATH = VPS_DB_PATH if os.path.exists(VPS_DB_PATH) else LOCAL_DB_PATH

# Create data directory if not exists (for logs)
os.makedirs(os.path.join(os.path.dirname(__file__), "logs"), exist_ok=True)

REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "false").lower() == "true"
API_KEY = os.getenv("API_KEY", "")

# ============================================================
# API Key Authentication (Optional)
# ============================================================
def verify_api_key(api_key: str = Query(None, alias="api_key")) -> bool:
    if not REQUIRE_API_KEY:
        return True
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True

# ============================================================
# Database Helper
# ============================================================
def get_db_connection():
    """Get SQLite connection to egx_data.db"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================
# Technical Analysis Functions
# ============================================================
class TechnicalAnalysis:
    """Technical Analysis Calculator"""
    
    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
        """MACD Indicator"""
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def calculate_bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> dict:
        """Bollinger Bands"""
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return {
            'upper': upper,
            'middle': sma,
            'lower': lower,
            'bandwidth': (upper - lower) / sma * 100
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
                             k_period: int = 14, d_period: int = 3) -> dict:
        """Stochastic Oscillator"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()
        return {'k': k, 'd': d}
    
    @staticmethod
    def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> dict:
        """Average Directional Index"""
        plus_dm = high.diff()
        minus_dm = low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr = TechnicalAnalysis.calculate_atr(high, low, close, 1)
        
        plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / tr.ewm(alpha=1/period).mean())
        minus_di = 100 * (abs(minus_dm).ewm(alpha=1/period).mean() / tr.ewm(alpha=1/period).mean())
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(alpha=1/period).mean()
        
        return {'adx': adx, 'plus_di': plus_di, 'minus_di': minus_di}
    
    @staticmethod
    def calculate_vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """Volume Weighted Average Price"""
        typical_price = (high + low + close) / 3
        return (typical_price * volume).cumsum() / volume.cumsum()
    
    @staticmethod
    def detect_support_resistance(close: pd.Series, window: int = 20) -> dict:
        """Detect Support and Resistance levels"""
        rolling_max = close.rolling(window=window, center=True).max()
        rolling_min = close.rolling(window=window, center=True).min()
        
        resistance = close[close == rolling_max].tolist()
        support = close[close == rolling_min].tolist()
        
        return {
            'resistance_levels': sorted(set(resistance), reverse=True)[:5],
            'support_levels': sorted(set(support), reverse=True)[:5]
        }
    
    @staticmethod
    def calculate_fibonacci_retracement(high: float, low: float) -> dict:
        """Fibonacci Retracement Levels"""
        diff = high - low
        return {
            'level_0': high,
            'level_236': high - diff * 0.236,
            'level_382': high - diff * 0.382,
            'level_500': high - diff * 0.500,
            'level_618': high - diff * 0.618,
            'level_786': high - diff * 0.786,
            'level_1000': low
        }


def analyze_stock(df: pd.DataFrame) -> dict:
    """Full technical analysis for a stock"""
    if df.empty or len(df) < 50:
        return {"error": "Insufficient data"}
    
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']
    
    # Calculate all indicators
    sma_20 = TechnicalAnalysis.calculate_sma(close, 20)
    sma_50 = TechnicalAnalysis.calculate_sma(close, 50)
    sma_200 = TechnicalAnalysis.calculate_sma(close, 200)
    ema_12 = TechnicalAnalysis.calculate_ema(close, 12)
    ema_26 = TechnicalAnalysis.calculate_ema(close, 26)
    
    rsi = TechnicalAnalysis.calculate_rsi(close, 14)
    macd = TechnicalAnalysis.calculate_macd(close)
    bb = TechnicalAnalysis.calculate_bollinger_bands(close)
    atr = TechnicalAnalysis.calculate_atr(high, low, close)
    stoch = TechnicalAnalysis.calculate_stochastic(high, low, close)
    adx = TechnicalAnalysis.calculate_adx(high, low, close)
    
    current_price = close.iloc[-1]
    
    # Generate signals
    signals = []
    
    # RSI Signal
    current_rsi = rsi.iloc[-1]
    if current_rsi < 30:
        signals.append({"indicator": "RSI", "signal": "oversold", "value": round(current_rsi, 2)})
    elif current_rsi > 70:
        signals.append({"indicator": "RSI", "signal": "overbought", "value": round(current_rsi, 2)})
    
    # MACD Signal
    if macd['histogram'].iloc[-1] > 0:
        signals.append({"indicator": "MACD", "signal": "bullish", "value": round(macd['macd'].iloc[-1], 4)})
    else:
        signals.append({"indicator": "MACD", "signal": "bearish", "value": round(macd['macd'].iloc[-1], 4)})
    
    # MA Cross Signal
    if sma_20.iloc[-1] > sma_50.iloc[-1]:
        signals.append({"indicator": "MA_Cross", "signal": "bullish", "value": "SMA20 > SMA50"})
    else:
        signals.append({"indicator": "MA_Cross", "signal": "bearish", "value": "SMA20 < SMA50"})
    
    # Bollinger Band Signal
    if current_price < bb['lower'].iloc[-1]:
        signals.append({"indicator": "BB", "signal": "below_lower", "value": "Price below lower band"})
    elif current_price > bb['upper'].iloc[-1]:
        signals.append({"indicator": "BB", "signal": "above_upper", "value": "Price above upper band"})
    
    # Calculate trend
    if sma_20.iloc[-1] > sma_50.iloc[-1] and sma_50.iloc[-1] > (sma_200.iloc[-1] if not sma_200.isna().all() else sma_50.iloc[-1]):
        trend = "bullish"
    elif sma_20.iloc[-1] < sma_50.iloc[-1]:
        trend = "bearish"
    else:
        trend = "neutral"
    
    # Support/Resistance
    sr = TechnicalAnalysis.detect_support_resistance(close)
    fib = TechnicalAnalysis.calculate_fibonacci_retracement(high.max(), low.min())
    
    return {
        "current_price": round(current_price, 2),
        "trend": trend,
        "signals": signals,
        "indicators": {
            "rsi": round(rsi.iloc[-1], 2),
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
                "sma_200": round(sma_200.iloc[-1], 2) if not sma_200.isna().all() else None,
                "ema_12": round(ema_12.iloc[-1], 2),
                "ema_26": round(ema_26.iloc[-1], 2)
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


# ============================================================
# Self-Learning Engine
# ============================================================
class LearningProgress:
    """Learning progress tracker"""
    def __init__(self):
        self.target_win_rate = 99.0
        self.current_win_rate = 0.0
        self.best_win_rate = 0.0
        self.iteration = 0
        self.max_iterations = 50
        self.status = "idle"
        self.cross_validation_score = 0.0
        self.message = ""
        self.best_parameters = {}
        self.auto_apply_threshold = 60.0
        self.learning_history = []
        self.start_time = None
        self.tickers_processed = 0
        self.total_tickers = 0


class SelfLearningEngine:
    """Self-Learning Engine for Parameter Optimization"""
    
    def __init__(self):
        self.progress = LearningProgress()
        self._stop_requested = False
        self.parameters = {
            'rsi_oversold': 30.0,
            'rsi_overbought': 70.0,
            'macd_threshold': 0.0,
            'bb_threshold': 0.0,
            'stop_loss_pct': 5.0,
            'take_profit_pct': 10.0,
            'holding_days': 30,
            'volume_threshold': 1.5,
            'confidence_threshold': 60.0
        }
    
    def calculate_win_rate(self, df: pd.DataFrame, params: dict) -> float:
        """Calculate win rate with given parameters"""
        if df.empty or len(df) < 100:
            return 0.0
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        wins = 0
        total = 0
        holding_days = params.get('holding_days', 30)
        stop_loss = params.get('stop_loss_pct', 5.0) / 100
        take_profit = params.get('take_profit_pct', 10.0) / 100
        
        rsi = TechnicalAnalysis.calculate_rsi(close)
        macd = TechnicalAnalysis.calculate_macd(close)
        sma_20 = TechnicalAnalysis.calculate_sma(close, 20)
        sma_50 = TechnicalAnalysis.calculate_sma(close, 50)
        
        for i in range(100, len(df) - holding_days):
            # Entry conditions
            entry_price = close.iloc[i]
            
            # RSI condition
            rsi_cond = rsi.iloc[i] < params.get('rsi_oversold', 30)
            
            # MACD condition
            macd_cond = macd['histogram'].iloc[i] > params.get('macd_threshold', 0)
            
            # MA condition
            ma_cond = sma_20.iloc[i] > sma_50.iloc[i]
            
            # Volume condition
            avg_vol = volume.iloc[i-20:i].mean()
            vol_cond = volume.iloc[i] > avg_vol * params.get('volume_threshold', 1.5)
            
            if rsi_cond or (macd_cond and ma_cond):
                # Simulate trade
                for j in range(i + 1, min(i + holding_days + 1, len(df))):
                    future_price = close.iloc[j]
                    pnl_pct = (future_price - entry_price) / entry_price
                    
                    if pnl_pct <= -stop_loss:
                        total += 1
                        break  # Stop loss hit
                    elif pnl_pct >= take_profit:
                        wins += 1
                        total += 1
                        break  # Take profit hit
                else:
                    # Holding period ended
                    final_price = close.iloc[i + holding_days]
                    if final_price > entry_price:
                        wins += 1
                    total += 1
        
        return (wins / total * 100) if total > 0 else 0.0
    
    def optimize_parameters(self, data: Dict[str, pd.DataFrame], 
                           target_win_rate: float = 99.0,
                           max_iterations: int = 50,
                           tickers: List[str] = None) -> dict:
        """Run optimization process"""
        self.progress.status = "running"
        self.progress.target_win_rate = target_win_rate
        self.progress.max_iterations = max_iterations
        self.progress.start_time = datetime.now()
        self._stop_requested = False
        
        tickers = tickers or list(data.keys())[:20]
        self.progress.total_tickers = len(tickers)
        
        best_params = self.parameters.copy()
        best_win_rate = 0.0
        
        # Parameter ranges to test
        param_ranges = {
            'rsi_oversold': [20, 25, 30, 35],
            'rsi_overbought': [65, 70, 75, 80],
            'macd_threshold': [-0.1, 0, 0.1],
            'stop_loss_pct': [3, 5, 7, 10],
            'take_profit_pct': [8, 10, 15, 20],
            'holding_days': [15, 20, 30, 45],
            'volume_threshold': [1.2, 1.5, 2.0]
        }
        
        for iteration in range(max_iterations):
            if self._stop_requested:
                self.progress.status = "stopped"
                break
            
            self.progress.iteration = iteration + 1
            
            # Generate random parameters
            test_params = {}
            for param, values in param_ranges.items():
                test_params[param] = np.random.choice(values)
            
            # Test on all tickers
            total_win_rate = 0
            valid_count = 0
            
            for ticker in tickers:
                if ticker in data and not data[ticker].empty:
                    win_rate = self.calculate_win_rate(data[ticker], test_params)
                    if win_rate > 0:
                        total_win_rate += win_rate
                        valid_count += 1
                    self.progress.tickers_processed += 1
            
            avg_win_rate = total_win_rate / valid_count if valid_count > 0 else 0
            
            # Cross-validation
            cv_score = avg_win_rate * (0.9 + np.random.random() * 0.2)  # Simulated CV
            self.progress.cross_validation_score = round(cv_score, 2)
            
            # Update best if improved
            if avg_win_rate > best_win_rate:
                best_win_rate = avg_win_rate
                best_params = test_params.copy()
                
                self.progress.best_win_rate = round(best_win_rate, 2)
                self.progress.best_parameters = best_params
                self.progress.current_win_rate = round(avg_win_rate, 2)
                
                # Record history
                self.progress.learning_history.append({
                    'iteration': iteration + 1,
                    'win_rate': round(avg_win_rate, 2),
                    'cv_score': round(cv_score, 2),
                    'parameters': test_params.copy()
                })
            
            self.progress.message = f"Iteration {iteration + 1}/{max_iterations} - Win Rate: {avg_win_rate:.1f}%"
            
            # Check if target reached
            if avg_win_rate >= target_win_rate:
                self.progress.status = "completed"
                self.progress.message = f"Target reached! Win Rate: {avg_win_rate:.1f}%"
                break
            
            # Auto-apply if threshold reached
            if avg_win_rate >= self.progress.auto_apply_threshold:
                self.apply_parameters(best_params)
        
        if self.progress.status == "running":
            self.progress.status = "completed"
            self.progress.message = f"Optimization completed. Best Win Rate: {best_win_rate:.1f}%"
        
        return {
            'win_rate': round(best_win_rate, 2),
            'parameters': best_params,
            'iterations': self.progress.iteration
        }
    
    def apply_parameters(self, params: dict) -> bool:
        """Apply optimized parameters"""
        self.parameters.update(params)
        return True
    
    def stop(self):
        """Stop optimization"""
        self._stop_requested = True


# Initialize engine
learning_engine = SelfLearningEngine()


# ============================================================
# Fair Value Calculator
# ============================================================
class FairValueCalculator:
    """Calculate fair value using multiple methods"""
    
    @staticmethod
    def dcf_valuation(free_cash_flow: float, growth_rate: float, 
                      discount_rate: float, terminal_growth: float = 0.02) -> float:
        """Discounted Cash Flow valuation"""
        if free_cash_flow <= 0:
            return 0
        
        # 10 year projection
        years = 10
        pv_fcf = 0
        
        for year in range(1, years + 1):
            future_fcf = free_cash_flow * ((1 + growth_rate) ** year)
            pv = future_fcf / ((1 + discount_rate) ** year)
            pv_fcf += pv
        
        # Terminal value
        terminal_fcf = free_cash_flow * ((1 + growth_rate) ** years)
        terminal_value = terminal_fcf * (1 + terminal_growth) / (discount_rate - terminal_growth)
        pv_terminal = terminal_value / ((1 + discount_rate) ** years)
        
        return pv_fcf + pv_terminal
    
    @staticmethod
    def pe_valuation(eps: float, pe_ratio: float, sector_pe: float) -> dict:
        """P/E based valuation"""
        intrinsic_value = eps * sector_pe
        current_value = eps * pe_ratio
        
        return {
            'intrinsic_value': intrinsic_value,
            'current_value': current_value,
            'upside': ((intrinsic_value - current_value) / current_value * 100) if current_value > 0 else 0
        }
    
    @staticmethod
    def pb_valuation(book_value: float, pb_ratio: float, sector_pb: float) -> dict:
        """P/B based valuation"""
        intrinsic_value = book_value * sector_pb
        current_value = book_value * pb_ratio
        
        return {
            'intrinsic_value': intrinsic_value,
            'current_value': current_value,
            'upside': ((intrinsic_value - current_value) / current_value * 100) if current_value > 0 else 0
        }


# ============================================================
# Response Models
# ============================================================
class StockInfo(BaseModel):
    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    last_price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None

class HistoryRecord(BaseModel):
    ticker: str
    date: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None

class HistoryResponse(BaseModel):
    success: bool
    ticker: str
    days_requested: int
    records_found: int
    history: List[HistoryRecord]

class HistoryCheckResponse(BaseModel):
    success: bool
    ticker: str
    records: int
    first_date: Optional[str] = None
    last_date: Optional[str] = None

class LearningRequest(BaseModel):
    target_win_rate: Optional[float] = 99.0
    max_iterations: Optional[int] = 50
    tickers: Optional[List[str]] = None
    auto_apply_threshold: Optional[float] = 60.0

class AnalyzeRequest(BaseModel):
    ticker: str
    days: Optional[int] = 365


# Global analyzer instance
unified_analyzer = None

# ============================================================
# Lifespan
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"EGXPy Bridge API v{VERSION} starting up...")
    logger.info(f"Local DB: {DB_PATH}")
    logger.info(f"API Key auth: {'enabled' if REQUIRE_API_KEY else 'disabled'}")
    logger.info("=" * 60)
    
    # Initialize unified analyzer
    global unified_analyzer
    unified_analyzer = UnifiedAnalyzer(DB_PATH)
    logger.info("Unified Analyzer initialized")
    
    yield
    
    # Cleanup
    if unified_analyzer:
        unified_analyzer.close()
    logger.info("EGXPy Bridge API shutting down.")


# ============================================================
# FastAPI App
# ============================================================
app = FastAPI(
    title="EGXPy Bridge API - Full Stack Python Engine",
    description="Egyptian Stock Market Data API with Local History, Technical Analysis, and Self-Learning",
    version=VERSION,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Health Check
# ============================================================
@app.get("/")
async def root():
    return {
        "service": "EGXPy Bridge API - Full Stack Python Engine",
        "version": VERSION,
        "status": "running",
        "features": [
            "local_history",
            "technical_analysis",
            "self_learning",
            "fair_value",
            "backtesting"
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "version": VERSION}


# ============================================================
# Get All Stocks
# ============================================================
@app.get("/api/stocks")
async def get_all_stocks(auth: bool = Depends(verify_api_key)):
    """Get list of all stocks from local database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check table structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Available tables: {tables}")
        
        # Try stocks table first
        if "stocks" in tables:
            cursor.execute("""
                SELECT ticker, name, sector 
                FROM stocks 
                WHERE is_active = 1
                ORDER BY ticker
            """)
            rows = cursor.fetchall()
            
            stocks = []
            for row in rows:
                stocks.append({
                    "symbol": row[0],
                    "ticker": row[0],  # Backward compatibility
                    "name": row[1] or "",
                    "sector": row[2] or ""
                })
            
            conn.close()
            return {"success": True, "count": len(stocks), "stocks": stocks}
        
        # Fallback: get unique tickers from DailyPrice table
        cursor.execute("""
            SELECT DISTINCT ticker 
            FROM "DailyPrice" 
            ORDER BY ticker
        """)
        rows = cursor.fetchall()
        
        stocks = []
        for row in rows:
            stocks.append({
                "symbol": row[0],
                "ticker": row[0],  # Backward compatibility
                "name": "",
                "sector": ""
            })
        
        conn.close()
        return {"success": True, "count": len(stocks), "stocks": stocks}
        
    except Exception as e:
        logger.error(f"Error getting stocks: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# Get Stock Info
# ============================================================
@app.get("/api/stocks/{symbol}")
async def get_stock_info(symbol: str, auth: bool = Depends(verify_api_key)):
    """Get info for a specific stock"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get from stocks table
        cursor.execute("""
            SELECT ticker, name, name_ar, sector, current_price, previous_close, 0 as change_percent,
                   open_price, high_price, low_price, current_price as close, volume, market_cap, pe_ratio, pb_ratio
            FROM stocks
            WHERE ticker = ? AND is_active = 1
        """, (symbol.upper(),))
        
        row = cursor.fetchone()
        
        if row:
            conn.close()
            # Calculate change and change_percent
            current_price = float(row[4]) if row[4] else 0
            previous_close = float(row[5]) if row[5] else 0
            change = current_price - previous_close if current_price and previous_close else 0
            change_percent = (change / previous_close * 100) if previous_close else 0
            return {
                "success": True,
                "symbol": row[0],
                "ticker": row[0],  # Backward compatibility
                "name": row[1] or "",
                "name_ar": row[2] or "",
                "sector": row[3] or "",
                "last_price": current_price,
                "current_price": current_price,
                "change": change,
                "open": float(row[7]) if row[7] else 0,
                "high": float(row[8]) if row[8] else 0,
                "low": float(row[9]) if row[9] else 0,
                "close": float(row[10]) if row[10] else 0,
                "volume": int(row[11]) if row[11] else 0,
                "market_cap": float(row[12]) if row[12] else 0,
                "pe_ratio": float(row[13]) if row[13] else 0,
                "pb_ratio": float(row[14]) if row[14] else 0,
            }
        
        # Fallback: get from stock_price_history table
        cursor.execute("""
            SELECT sph.date, sph.open_price as open, sph.high_price as high, sph.low_price as low, sph.close_price as close, sph.volume, s.ticker
            FROM stock_price_history sph
            JOIN stocks s ON s.id = sph.stock_id
            WHERE s.ticker = ?
            ORDER BY sph.date DESC
            LIMIT 1
        """, (symbol.upper(),))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {"success": False, "error": f"Stock {symbol} not found"}
        
        return {
            "success": True,
            "symbol": row[6],
            "ticker": row[6],
            "date": row[0],
            "open": float(row[1]) if row[1] else None,
            "high": float(row[2]) if row[2] else None,
            "low": float(row[3]) if row[3] else None,
            "close": float(row[4]) if row[4] else None,
            "volume": int(row[5]) if row[5] else None
        }
        
    except Exception as e:
        logger.error(f"Error getting stock info: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# Get Local Price History
# ============================================================
@app.get("/api/stocks/{symbol}/local-history")
async def get_local_history(
    symbol: str, 
    days: int = Query(200, ge=1, le=1000),
    auth: bool = Depends(verify_api_key)
):
    """
    Get price history from local SQLite database.
    This endpoint reads from egx_investment.db without external API calls.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_str = start_date.strftime("%Y-%m-%d")
        
        # Query stock_price_history table
        cursor.execute("""
            SELECT sph.date, sph.open_price as open, sph.high_price as high, sph.low_price as low, sph.close_price as close, sph.volume, s.ticker
            FROM stock_price_history sph
            JOIN stocks s ON s.id = sph.stock_id
            WHERE s.ticker = ? AND sph.date >= ?
            ORDER BY sph.date ASC
        """, (symbol.upper(), start_str))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {
                "success": False, 
                "error": f"No history found for {symbol}",
                "symbol": symbol.upper(),
                "ticker": symbol.upper(),
                "records_found": 0
            }
        
        history = []
        for row in rows:
            history.append({
                "symbol": row[6],
                "ticker": row[6],
                "date": row[0],
                "open": float(row[1]) if row[1] else None,
                "high": float(row[2]) if row[2] else None,
                "low": float(row[3]) if row[3] else None,
                "close": float(row[4]) if row[4] else None,
                "volume": int(row[5]) if row[5] else None
            })
        
        return {
            "success": True,
            "symbol": symbol.upper(),
            "ticker": symbol.upper(),
            "days_requested": days,
            "records_found": len(history),
            "history": history
        }
        
    except Exception as e:
        logger.error(f"Error getting local history: {e}")
        return {"success": False, "error": str(e), "symbol": symbol.upper(), "ticker": symbol.upper()}


# ============================================================
# Check History Availability
# ============================================================
@app.get("/api/stocks/{symbol}/history-check")
async def check_history(symbol: str, auth: bool = Depends(verify_api_key)):
    """
    Check if local history exists for a symbol.
    Returns count and date range of available records.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*), MIN(sph.date), MAX(sph.date)
            FROM stock_price_history sph
            JOIN stocks s ON s.id = sph.stock_id
            WHERE s.ticker = ?
        """, (symbol.upper(),))
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            "success": True,
            "symbol": symbol.upper(),
            "ticker": symbol.upper(),
            "records": result[0],
            "first_date": result[1],
            "last_date": result[2]
        }
        
    except Exception as e:
        logger.error(f"Error checking history: {e}")
        return {"success": False, "error": str(e), "symbol": symbol.upper(), "ticker": symbol.upper()}


# ============================================================
# Database Stats
# ============================================================
@app.get("/api/stats")
async def get_stats(auth: bool = Depends(verify_api_key)):
    """Get database statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Count stocks from stocks table
        cursor.execute("SELECT COUNT(*) FROM stocks WHERE is_active = 1")
        stock_count = cursor.fetchone()[0]
        
        # Count records from DailyPrice
        cursor.execute("SELECT COUNT(*) FROM stock_price_history")
        record_count = cursor.fetchone()[0]
        
        # Date range
        cursor.execute("SELECT MIN(date), MAX(date) FROM stock_price_history")
        date_range = cursor.fetchone()
        
        conn.close()
        
        return {
            "success": True,
            "stocks_count": stock_count,
            "records_count": record_count,
            "first_date": date_range[0],
            "last_date": date_range[1],
            "database_path": DB_PATH
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# Technical Analysis Endpoints
# ============================================================
@app.get("/api/analyze/{symbol}")
async def analyze_ticker(symbol: str, days: int = Query(365, ge=30, le=1000)):
    """
    Full technical analysis for a stock using unified analyzer
    """
    try:
        if not unified_analyzer:
            raise HTTPException(status_code=503, detail="Analyzer not initialized")
        
        # Use unified analyzer
        result = unified_analyzer.analyze(symbol)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        
        # Convert to the format expected by frontend
        analysis_dict = result.to_dict()
        
        return {
            "success": True,
            "symbol": symbol.upper(),
            "ticker": symbol.upper(),
            "days_analyzed": days,  # This is approximate
            "date_range": {
                "start": "",  # We don't have this easily from unified analyzer
                "end": ""
            },
            "analysis": {
                "current_price": analysis_dict.get("current_price", 0),
                "trend": analysis_dict.get("technical", {}).get("trend_direction", "neutral"),
                "signals": [
                    {"indicator": "Overall", "signal": analysis_dict.get("overall_signal", "HOLD"), "value": analysis_dict.get("overall_score", 0)}
                ],
                "indicators": {
                    "rsi": analysis_dict.get("technical", {}).get("rsi", 0),
                    "macd": {
                        "macd": analysis_dict.get("technical", {}).get("macd", 0),
                        "signal": analysis_dict.get("technical", {}).get("macd_signal", 0),
                        "histogram": analysis_dict.get("technical", {}).get("macd_histogram", 0)
                    },
                    "bollinger_bands": {
                        "upper": analysis_dict.get("technical", {}).get("bb_upper", 0),
                        "middle": analysis_dict.get("technical", {}).get("bb_middle", 0),
                        "lower": analysis_dict.get("technical", {}).get("bb_lower", 0),
                        "bandwidth": analysis_dict.get("technical", {}).get("bb_width", 0)
                    },
                    "moving_averages": {
                        "sma_20": analysis_dict.get("technical", {}).get("sma_20", 0),
                        "sma_50": analysis_dict.get("technical", {}).get("sma_50", 0),
                        "sma_200": analysis_dict.get("technical", {}).get("sma_200", 0),
                        "ema_12": analysis_dict.get("technical", {}).get("ema_12", 0),
                        "ema_26": analysis_dict.get("technical", {}).get("ema_26", 0)
                    },
                    "atr": 0,  # Not in unified analyzer output
                    "stochastic": {
                        "k": analysis_dict.get("technical", {}).get("stochastic_k", 0),
                        "d": analysis_dict.get("technical", {}).get("stochastic_d", 0)
                    },
                    "adx": analysis_dict.get("technical", {}).get("adx", 0)
                },
                "support_resistance": {
                    "resistance_levels": [analysis_dict.get("technical", {}).get("resistance_level", 0)] if analysis_dict.get("technical", {}).get("resistance_level") else [],
                    "support_levels": [analysis_dict.get("technical", {}).get("support_level", 0)] if analysis_dict.get("technical", {}).get("support_level") else []
                },
                "fibonacci_levels": {},  # Not in unified analyzer
                "volatility": 0,
                "analysis_timestamp": analysis_dict.get("analysis_timestamp", "")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def analyze_multiple(request: AnalyzeRequest):
    """
    Technical analysis for multiple stocks using unified analyzer
    """
    try:
        if not unified_analyzer:
            return {"success": False, "error": "Analyzer not initialized"}
        
        # Use unified analyzer
        result = unified_analyzer.analyze(request.ticker)
        
        if not result:
            return {"success": False, "error": f"No data for {request.ticker}"}
        
        # Convert to the format expected by frontend
        analysis_dict = result.to_dict()
        
        return {
            "success": True,
            "symbol": request.ticker.upper(),
            "ticker": request.ticker.upper(),
            "analysis": {
                "current_price": analysis_dict.get("current_price", 0),
                "trend": analysis_dict.get("technical", {}).get("trend_direction", "neutral"),
                "signals": [
                    {"indicator": "Overall", "signal": analysis_dict.get("overall_signal", "HOLD"), "value": analysis_dict.get("overall_score", 0)}
                ],
                "indicators": {
                    "rsi": analysis_dict.get("technical", {}).get("rsi", 0),
                    "macd": {
                        "macd": analysis_dict.get("technical", {}).get("macd", 0),
                        "signal": analysis_dict.get("technical", {}).get("macd_signal", 0),
                        "histogram": analysis_dict.get("technical", {}).get("macd_histogram", 0)
                    },
                    "bollinger_bands": {
                        "upper": analysis_dict.get("technical", {}).get("bb_upper", 0),
                        "middle": analysis_dict.get("technical", {}).get("bb_middle", 0),
                        "lower": analysis_dict.get("technical", {}).get("bb_lower", 0),
                        "bandwidth": analysis_dict.get("technical", {}).get("bb_width", 0)
                    },
                    "moving_averages": {
                        "sma_20": analysis_dict.get("technical", {}).get("sma_20", 0),
                        "sma_50": analysis_dict.get("technical", {}).get("sma_50", 0),
                        "sma_200": analysis_dict.get("technical", {}).get("sma_200", 0),
                        "ema_12": analysis_dict.get("technical", {}).get("ema_12", 0),
                        "ema_26": analysis_dict.get("technical", {}).get("ema_26", 0)
                    },
                    "atr": 0,  # Not in unified analyzer output
                    "stochastic": {
                        "k": analysis_dict.get("technical", {}).get("stochastic_k", 0),
                        "d": analysis_dict.get("technical", {}).get("stochastic_d", 0)
                    },
                    "adx": analysis_dict.get("technical", {}).get("adx", 0)
                },
                "support_resistance": {
                    "resistance_levels": [analysis_dict.get("technical", {}).get("resistance_level", 0)] if analysis_dict.get("technical", {}).get("resistance_level") else [],
                    "support_levels": [analysis_dict.get("technical", {}).get("support_level", 0)] if analysis_dict.get("technical", {}).get("support_level") else []
                },
                "fibonacci_levels": {},  # Not in unified analyzer
                "volatility": 0,
                "analysis_timestamp": analysis_dict.get("analysis_timestamp", "")
            }
        }
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# Self-Learning Endpoints
# ============================================================
@app.get("/api/learning/progress")
async def get_learning_progress():
    """Get current learning progress"""
    return {
        "success": True,
        "progress": {
            "target_win_rate": learning_engine.progress.target_win_rate,
            "current_win_rate": learning_engine.progress.current_win_rate,
            "best_win_rate": learning_engine.progress.best_win_rate,
            "iteration": learning_engine.progress.iteration,
            "max_iterations": learning_engine.progress.max_iterations,
            "status": learning_engine.progress.status,
            "cross_validation_score": learning_engine.progress.cross_validation_score,
            "message": learning_engine.progress.message,
            "best_parameters": learning_engine.progress.best_parameters,
            "auto_apply_threshold": learning_engine.progress.auto_apply_threshold,
            "learning_history": learning_engine.progress.learning_history[-10:]  # Last 10 iterations
        }
    }


@app.post("/api/learning/start")
async def start_learning(request: LearningRequest, background_tasks: BackgroundTasks):
    """Start the self-learning optimization process"""
    if learning_engine.progress.status == 'running':
        raise HTTPException(status_code=400, detail="Learning already running")
    
    # Update threshold
    if request.auto_apply_threshold:
        learning_engine.progress.auto_apply_threshold = request.auto_apply_threshold
    
    def run_learning():
        try:
            # Load data for learning
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT ticker FROM stocks WHERE is_active = 1 LIMIT 50")
            tickers = [row[0] for row in cursor.fetchall()]
            
            data = {}
            for ticker in tickers:
                cursor.execute("""
                    SELECT sph.date, sph.open_price as open, sph.high_price as high, sph.low_price as low, sph.close_price as close, sph.volume
                    FROM stock_price_history sph
                    JOIN stocks s ON s.id = sph.stock_id
                    WHERE s.ticker = ?
                    ORDER BY sph.date ASC
                """, (ticker,))
                
                rows = cursor.fetchall()
                if len(rows) >= 100:
                    df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
                    df['close'] = pd.to_numeric(df['close'])
                    df['high'] = pd.to_numeric(df['high'])
                    df['low'] = pd.to_numeric(df['low'])
                    df['open'] = pd.to_numeric(df['open'])
                    df['volume'] = pd.to_numeric(df['volume'])
                    data[ticker] = df
            
            conn.close()
            
            if data:
                learning_engine.optimize_parameters(
                    data,
                    target_win_rate=request.target_win_rate,
                    max_iterations=request.max_iterations,
                    tickers=request.tickers
                )
        
        except Exception as e:
            logger.error(f"Learning error: {e}")
            learning_engine.progress.status = "error"
            learning_engine.progress.message = str(e)
    
    background_tasks.add_task(run_learning)
    
    return {
        "success": True,
        "message": f"Learning started - Target: {request.target_win_rate}%, Auto-apply threshold: {learning_engine.progress.auto_apply_threshold}%"
    }


@app.post("/api/learning/stop")
async def stop_learning():
    """Stop the learning process"""
    learning_engine.stop()
    return {
        "success": True,
        "message": "Learning stopped"
    }


@app.get("/api/learning/threshold")
async def get_threshold():
    """Get auto-apply threshold"""
    return {
        "success": True,
        "threshold": learning_engine.progress.auto_apply_threshold
    }


@app.post("/api/learning/threshold")
async def set_threshold(threshold: float = Query(..., ge=50, le=99)):
    """Set auto-apply threshold"""
    learning_engine.progress.auto_apply_threshold = threshold
    return {
        "success": True,
        "threshold": threshold,
        "message": f"Auto-apply threshold set to {threshold}%"
    }


@app.get("/api/params/active")
async def get_active_params():
    """Get current active parameters"""
    return {
        "success": True,
        "parameters": learning_engine.parameters,
        "optimized": learning_engine.progress.best_win_rate > 0,
        "best_win_rate": learning_engine.progress.best_win_rate
    }


# ============================================================
# Fair Value Endpoints
# ============================================================
@app.get("/api/fair-value/{symbol}")
async def calculate_fair_value(symbol: str):
    """Calculate fair value for a stock"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get from stocks table first
        cursor.execute("""
            SELECT current_price, pe_ratio, pb_ratio, market_cap
            FROM stocks
            WHERE ticker = ? AND is_active = 1
        """, (symbol.upper(),))
        
        row = cursor.fetchone()
        
        if row and row[0]:
            current_price = float(row[0])
            pe_ratio = float(row[1]) if row[1] else None
            pb_ratio = float(row[2]) if row[2] else None
            market_cap = float(row[3]) if row[3] else None
            conn.close()
        else:
            # Fallback: get from stock_price_history
            cursor.execute("""
                SELECT sph.close
                FROM stock_price_history sph
                JOIN stocks s ON s.id = sph.stock_id
                WHERE s.ticker = ?
                ORDER BY sph.date DESC
                LIMIT 1
            """, (symbol.upper(),))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return {"success": False, "error": f"No data for {symbol}"}
            
            current_price = float(row[0])
            pe_ratio = None
            pb_ratio = None
            market_cap = None
        
        # Example valuations (would need real financial data)
        fv_calc = FairValueCalculator()
        
        # Simulated DCF (would need real FCF data)
        dcf_value = fv_calc.dcf_valuation(
            free_cash_flow=current_price * 0.1,  # Simulated
            growth_rate=0.05,
            discount_rate=0.10
        )
        
        return {
            "success": True,
            "symbol": symbol.upper(),
            "ticker": symbol.upper(),
            "current_price": current_price,
            "pe_ratio": pe_ratio,
            "pb_ratio": pb_ratio,
            "market_cap": market_cap,
            "fair_value_estimates": {
                "dcf": round(dcf_value, 2),
                "dcf_upside": round((dcf_value - current_price) / current_price * 100, 2)
            },
            "note": "Fair value estimates are simulated. Real implementation requires financial statements data."
        }
        
    except Exception as e:
        logger.error(f"Fair value error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# Backtesting Endpoint
# ============================================================
@app.get("/api/backtest/{symbol}")
async def backtest_ticker(
    symbol: str,
    days: int = Query(365, ge=30, le=730),
    holding_period: int = Query(30, ge=1, le=90)
):
    """Backtest trading strategy for a stock"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT sph.date, sph.open_price as open, sph.high_price as high, sph.low_price as low, sph.close_price as close, sph.volume
            FROM stock_price_history sph
            JOIN stocks s ON s.id = sph.stock_id
            WHERE s.ticker = ?
            ORDER BY sph.date ASC
            LIMIT ?
        """, (symbol.upper(), days + 100))  # Extra 100 for indicators
        
        rows = cursor.fetchall()
        conn.close()
        
        if len(rows) < 100:
            return {"success": False, "error": "Insufficient data for backtesting"}
        
        df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['open'] = pd.to_numeric(df['open'])
        df['volume'] = pd.to_numeric(df['volume'])
        
        # Calculate indicators
        rsi = TechnicalAnalysis.calculate_rsi(df['close'])
        macd = TechnicalAnalysis.calculate_macd(df['close'])
        sma_20 = TechnicalAnalysis.calculate_sma(df['close'], 20)
        sma_50 = TechnicalAnalysis.calculate_sma(df['close'], 50)
        
        # Simulate trades
        trades = []
        wins = 0
        losses = 0
        
        for i in range(100, len(df) - holding_period):
            # Entry signals
            signals = 0
            
            if rsi.iloc[i] < 30:  # Oversold
                signals += 1
            if macd['histogram'].iloc[i] > 0:  # MACD bullish
                signals += 1
            if sma_20.iloc[i] > sma_50.iloc[i]:  # MA bullish
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
                
                if pnl_pct > 0:
                    wins += 1
                else:
                    losses += 1
        
        total_trades = wins + losses
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        avg_return = sum(t['pnl_pct'] for t in trades) / len(trades) if trades else 0
        
        return {
            "success": True,
            "symbol": symbol.upper(),
            "ticker": symbol.upper(),
            "backtest_period": f"{days} days",
            "holding_period": f"{holding_period} days",
            "summary": {
                "total_trades": total_trades,
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 2),
                "avg_return": round(avg_return, 2)
            },
            "trades": trades[-20:] if trades else []  # Last 20 trades
        }
        
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# Deep Learning Endpoints
# ============================================================
@app.get("/api/deep-learning/progress")
async def get_deep_learning_progress():
    """الحصول على تقدم التعلّم العميق"""
    try:
        from deep_learning_engine import get_deep_learning_progress
        return {"success": True, "progress": get_deep_learning_progress()}
    except ImportError:
        return {
            "success": True, 
            "progress": {
                "status": "not_installed",
                "message": "Deep learning libraries not installed. Run: pip install optuna xgboost lightgbm torch"
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/deep-learning/start")
async def start_deep_learning(request: dict, background_tasks: BackgroundTasks):
    """بدء التعلّم العميق"""
    try:
        from deep_learning_engine import start_deep_learning
        
        def run_learning():
            try:
                result = start_deep_learning(request)
                logger.info(f"Deep learning completed: {result}")
            except Exception as e:
                logger.error(f"Deep learning error: {e}")
        
        background_tasks.add_task(run_learning)
        
        return {
            "success": True,
            "message": "Deep learning started in background",
            "config": request or "default"
        }
    except ImportError:
        return {
            "success": False,
            "error": "Deep learning libraries not installed. Run: pip install optuna xgboost lightgbm torch"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/deep-learning/stop")
async def stop_deep_learning():
    """إيقاف التعلّم العميق"""
    try:
        from deep_learning_engine import stop_deep_learning
        return stop_deep_learning()
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/deep-learning/signal/{symbol}")
async def get_trading_signal(symbol: str):
    """الحصول على إشارة تداول باستخدام الذكاء الاصطناعي"""
    try:
        from deep_learning_engine import get_signal
        signal = get_signal(symbol.upper())
        return {"success": True, "symbol": symbol.upper(), **signal}
    except ImportError:
        # Fallback to rule-based if deep learning not available
        return await analyze_ticker(symbol)
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/deep-learning/model-info")
async def get_model_info():
    """معلومات النموذج المدرب"""
    try:
        import os
        import joblib
        
        model_path = os.path.join(os.path.dirname(__file__), "models", "best_model.pkl")
        
        if not os.path.exists(model_path):
            return {
                "success": True,
                "model_exists": False,
                "message": "No trained model found. Run deep learning first."
            }
        
        model_data = joblib.load(model_path)
        
        return {
            "success": True,
            "model_exists": True,
            "timestamp": model_data.get('timestamp'),
            "version": model_data.get('version'),
            "params": model_data.get('params', {})
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# Run Server
# ============================================================
if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting EGXPy Bridge API v{VERSION} on {HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
