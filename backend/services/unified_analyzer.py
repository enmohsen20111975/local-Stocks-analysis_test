#!/usr/bin/env python3
"""
Unified Financial Analysis Engine
=================================
نظام تحليل مالي موحد للأسهم والعملات الرقمية

Features:
1. التحليل المالي (Financial Analysis)
   - P/E Ratio, ROE, EPS, Dividends
   - Profit Margins, Debt Ratios
   
2. التحليل الفني (Technical Analysis)
   - RSI, MACD, Moving Averages
   - Support/Resistance, Trend Analysis
   - Volume Analysis
   
3. تحليل التوقيت (Timing Analysis)
   - Best entry/exit times
   - Market sessions
   - Seasonal patterns
   
4. تحليل الأحداث (Event Analysis)
   - Dividend dates
   - Earnings announcements
   - Market news impact
   - Sector trends
   
5. التعلم من الخبرة (Learning from Experience)
   - Track recommendation performance
   - Adjust parameters based on results
   - Pattern recognition

Author: EGX Investment Platform
Version: 1.0.0
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import math

# ============================================================================
# ENUMS
# ============================================================================

class SignalType(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"

class MarketSession(Enum):
    PRE_MARKET = "PRE_MARKET"
    MARKET_OPEN = "MARKET_OPEN"
    MARKET_CLOSE = "MARKET_CLOSE"
    AFTER_HOURS = "AFTER_HOURS"

class AssetType(Enum):
    STOCK = "STOCK"
    CRYPTO = "CRYPTO"

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class FinancialMetrics:
    """المقاييس المالية"""
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    roe: Optional[float] = None  # Return on Equity
    roa: Optional[float] = None  # Return on Assets
    eps: Optional[float] = None  # Earnings Per Share
    dividend_yield: Optional[float] = None
    profit_margin: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    free_cash_flow: Optional[float] = None
    market_cap: Optional[float] = None
    book_value: Optional[float] = None
    
    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class TechnicalIndicators:
    """المؤشرات الفنية"""
    # Moving Averages
    sma_5: Optional[float] = None
    sma_10: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_100: Optional[float] = None
    sma_200: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    
    # Oscillators
    rsi: Optional[float] = None
    rsi_signal: Optional[str] = None
    stochastic_k: Optional[float] = None
    stochastic_d: Optional[float] = None
    williams_r: Optional[float] = None
    cci: Optional[float] = None  # Commodity Channel Index
    
    # MACD
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    macd_trend: Optional[str] = None
    
    # Bollinger Bands
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_width: Optional[float] = None
    bb_position: Optional[str] = None  # upper, middle, lower
    
    # Support/Resistance
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    pivot_point: Optional[float] = None
    
    # Trend
    adx: Optional[float] = None  # Average Directional Index
    trend_strength: Optional[str] = None
    trend_direction: Optional[str] = None
    
    # Volume
    volume_sma: Optional[float] = None
    volume_ratio: Optional[float] = None
    obv: Optional[float] = None  # On-Balance Volume
    
    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class TimingAnalysis:
    """تحليل التوقيت"""
    current_hour_utc: int = 0
    current_session: str = "UNKNOWN"
    day_of_week: int = 0
    month: int = 0
    
    # Best times
    best_buy_hours: List[int] = field(default_factory=list)
    best_sell_hours: List[int] = field(default_factory=list)
    
    # Patterns
    hourly_pattern: Dict[str, float] = field(default_factory=dict)
    weekly_pattern: Dict[str, float] = field(default_factory=dict)
    monthly_pattern: Dict[str, float] = field(default_factory=dict)
    
    # Recommendations
    timing_score: int = 0
    timing_recommendation: str = "NEUTRAL"
    next_important_time: Optional[str] = None
    
    # Events
    upcoming_dividend: Optional[Dict] = None
    upcoming_earnings: Optional[Dict] = None
    market_events: List[Dict] = field(default_factory=list)
    
    def to_dict(self):
        return asdict(self)

@dataclass
class EventImpact:
    """تأثير الأحداث"""
    event_type: str
    event_date: str
    expected_impact: str  # POSITIVE, NEGATIVE, NEUTRAL
    impact_magnitude: float  # 0-1
    description: str
    confidence: float

@dataclass
class UnifiedAnalysisResult:
    """نتيجة التحليل الموحد"""
    # Basic Info
    symbol: str
    name: str
    asset_type: str
    current_price: float
    previous_close: Optional[float]
    
    # Analysis Components
    financial: Optional[FinancialMetrics] = None
    technical: Optional[TechnicalIndicators] = None
    timing: Optional[TimingAnalysis] = None
    events: List[EventImpact] = field(default_factory=list)
    
    # Final Signal
    overall_signal: str = "HOLD"
    overall_score: int = 0
    confidence: float = 0.0
    
    # Price Targets
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    
    # Reasons
    buy_reasons: List[str] = field(default_factory=list)
    sell_reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Metadata
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data_quality: str = "GOOD"  # GOOD, PARTIAL, POOR
    
    def to_dict(self):
        result = {
            "symbol": self.symbol,
            "name": self.name,
            "asset_type": self.asset_type,
            "current_price": self.current_price,
            "previous_close": self.previous_close,
            "overall_signal": self.overall_signal,
            "overall_score": self.overall_score,
            "confidence": self.confidence,
            "entry_price": self.entry_price,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "buy_reasons": self.buy_reasons,
            "sell_reasons": self.sell_reasons,
            "warnings": self.warnings,
            "analysis_timestamp": self.analysis_timestamp,
            "data_quality": self.data_quality
        }
        if self.financial:
            result["financial"] = self.financial.to_dict()
        if self.technical:
            result["technical"] = self.technical.to_dict()
        if self.timing:
            result["timing"] = self.timing.to_dict()
        if self.events:
            result["events"] = [asdict(e) for e in self.events]
        return result

# ============================================================================
# FINANCIAL ANALYZER
# ============================================================================

class FinancialAnalyzer:
    """محلل مالي"""
    
    def __init__(self, db_conn=None):
        self.conn = db_conn
    
    def analyze(self, ticker: str, asset_type: AssetType = AssetType.STOCK) -> Optional[FinancialMetrics]:
        """تحليل مالي للسهم أو العملة"""
        
        if asset_type == AssetType.STOCK:
            return self._analyze_stock(ticker)
        else:
            return self._analyze_crypto(ticker)
    
    def _analyze_stock(self, ticker: str) -> Optional[FinancialMetrics]:
        """تحليل مالي للسهم"""
        if not self.conn:
            return None
            
        cursor = self.conn.cursor()
        
        # Try to get financial data from database
        try:
            cursor.execute('''
                SELECT pe_ratio, pb_ratio, ps_ratio, roe, roa, eps,
                       dividend_yield, profit_margin, debt_to_equity,
                       current_ratio, quick_ratio, free_cash_flow,
                       market_cap, book_value_per_share
                FROM stocks 
                WHERE ticker = ?
            ''', (ticker.upper(),))
            
            row = cursor.fetchone()
            
            if row:
                return FinancialMetrics(
                    pe_ratio=row[0],
                    pb_ratio=row[1],
                    ps_ratio=row[2],
                    roe=row[3],
                    roa=row[4],
                    eps=row[5],
                    dividend_yield=row[6],
                    profit_margin=row[7],
                    debt_to_equity=row[8],
                    current_ratio=row[9],
                    quick_ratio=row[10],
                    free_cash_flow=row[11],
                    market_cap=row[12],
                    book_value=row[13]
                )
        except:
            pass
        
        return None
    
    def _analyze_crypto(self, ticker: str) -> Optional[FinancialMetrics]:
        """تحليل مالي للعملة الرقمية"""
        # For crypto, we focus on different metrics
        # This would typically come from CoinGecko API
        return FinancialMetrics()  # Placeholder
    
    def get_financial_score(self, metrics: FinancialMetrics) -> Tuple[int, List[str], List[str]]:
        """حساب نقاط التحليل المالي"""
        score = 0
        buy_reasons = []
        sell_reasons = []
        
        # P/E Ratio Analysis
        if metrics.pe_ratio:
            if metrics.pe_ratio < 10:
                score += 2
                buy_reasons.append(f"P/E منخفض ({metrics.pe_ratio:.1f}) - سهم رخيص")
            elif metrics.pe_ratio < 20:
                score += 1
                buy_reasons.append(f"P/E معقول ({metrics.pe_ratio:.1f})")
            elif metrics.pe_ratio > 40:
                score -= 1
                sell_reasons.append(f"P/E مرتفع ({metrics.pe_ratio:.1f}) - سهم غالي")
        
        # ROE Analysis
        if metrics.roe:
            if metrics.roe > 20:
                score += 2
                buy_reasons.append(f"ROE ممتاز ({metrics.roe:.1f}%)")
            elif metrics.roe > 10:
                score += 1
                buy_reasons.append(f"ROE جيد ({metrics.roe:.1f}%)")
            elif metrics.roe < 5:
                score -= 1
                sell_reasons.append(f"ROE منخفض ({metrics.roe:.1f}%)")
        
        # Dividend Yield
        if metrics.dividend_yield and metrics.dividend_yield > 0:
            if metrics.dividend_yield > 5:
                score += 1
                buy_reasons.append(f"عائد توزيعات عالي ({metrics.dividend_yield:.1f}%)")
            elif metrics.dividend_yield > 2:
                score += 1
                buy_reasons.append(f"عائد توزيعات جيد ({metrics.dividend_yield:.1f}%)")
        
        # Debt to Equity
        if metrics.debt_to_equity:
            if metrics.debt_to_equity < 0.5:
                score += 1
                buy_reasons.append("ديون منخفضة مقارنة بالحقوق")
            elif metrics.debt_to_equity > 2:
                score -= 1
                sell_reasons.append("ديون مرتفعة مقارنة بالحقوق")
        
        # Profit Margin
        if metrics.profit_margin:
            if metrics.profit_margin > 20:
                score += 1
                buy_reasons.append(f"هامش ربح عالي ({metrics.profit_margin:.1f}%)")
            elif metrics.profit_margin < 5:
                score -= 1
                sell_reasons.append(f"هامش ربح منخفض ({metrics.profit_margin:.1f}%)")
        
        return score, buy_reasons, sell_reasons

# ============================================================================
# TECHNICAL ANALYZER
# ============================================================================

class TechnicalAnalyzer:
    """محلل فني محسن"""
    
    def __init__(self, db_conn=None):
        self.conn = db_conn
    
    def analyze(self, symbol: str, prices: List[float], volumes: List[float] = None) -> TechnicalIndicators:
        """تحليل فني شامل"""
        indicators = TechnicalIndicators()
        
        if len(prices) < 50:
            return indicators
        
        # Moving Averages
        indicators.sma_5 = self._sma(prices, 5)
        indicators.sma_10 = self._sma(prices, 10)
        indicators.sma_20 = self._sma(prices, 20)
        indicators.sma_50 = self._sma(prices, 50)
        indicators.sma_100 = self._sma(prices, 100) if len(prices) >= 100 else None
        indicators.sma_200 = self._sma(prices, 200) if len(prices) >= 200 else None
        
        indicators.ema_12 = self._ema(prices, 12)
        indicators.ema_26 = self._ema(prices, 26)
        
        # RSI
        rsi = self._rsi(prices, 14)
        if rsi:
            indicators.rsi = rsi
            if rsi <= 30:
                indicators.rsi_signal = "OVERSOLD"
            elif rsi >= 70:
                indicators.rsi_signal = "OVERBOUGHT"
            else:
                indicators.rsi_signal = "NEUTRAL"
        
        # MACD
        macd_data = self._macd(prices)
        if macd_data:
            indicators.macd = macd_data['macd']
            indicators.macd_signal = macd_data['signal']
            indicators.macd_histogram = macd_data['histogram']
            indicators.macd_trend = macd_data['trend']
        
        # Bollinger Bands
        bb = self._bollinger_bands(prices, 20)
        if bb:
            indicators.bb_upper = bb['upper']
            indicators.bb_middle = bb['middle']
            indicators.bb_lower = bb['lower']
            indicators.bb_width = bb['width']
            
            current_price = prices[-1]
            if current_price >= bb['upper']:
                indicators.bb_position = "UPPER"
            elif current_price <= bb['lower']:
                indicators.bb_position = "LOWER"
            else:
                indicators.bb_position = "MIDDLE"
        
        # Support/Resistance
        sr = self._support_resistance(prices)
        if sr:
            indicators.support_level = sr['support']
            indicators.resistance_level = sr['resistance']
            indicators.pivot_point = sr['pivot']
        
        # Stochastic
        stoch = self._stochastic(prices, 14)
        if stoch:
            indicators.stochastic_k = stoch['k']
            indicators.stochastic_d = stoch['d']
        
        # ADX (Trend Strength)
        adx = self._adx(prices, 14)
        if adx:
            indicators.adx = adx
            if adx > 25:
                indicators.trend_strength = "STRONG"
            else:
                indicators.trend_strength = "WEAK"
        
        # Volume Analysis
        if volumes and len(volumes) > 20:
            indicators.volume_sma = self._sma(volumes, 20)
            indicators.volume_ratio = volumes[-1] / indicators.volume_sma if indicators.volume_sma else None
        
        return indicators
    
    def _sma(self, prices: List[float], period: int) -> Optional[float]:
        """Simple Moving Average"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    def _ema(self, prices: List[float], period: int) -> Optional[float]:
        """Exponential Moving Average"""
        if len(prices) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        return ema
    
    def _rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Relative Strength Index"""
        if len(prices) < period + 1:
            return None
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _macd(self, prices: List[float]) -> Optional[Dict]:
        """MACD Indicator"""
        if len(prices) < 26:
            return None
        
        ema_12 = self._ema(prices, 12)
        ema_26 = self._ema(prices, 26)
        
        if not ema_12 or not ema_26:
            return None
        
        macd_line = ema_12 - ema_26
        signal_line = macd_line * 0.9  # Simplified
        histogram = macd_line - signal_line
        
        if macd_line > signal_line and histogram > 0:
            trend = "BULLISH"
        elif macd_line < signal_line and histogram < 0:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram,
            'trend': trend
        }
    
    def _bollinger_bands(self, prices: List[float], period: int = 20) -> Optional[Dict]:
        """Bollinger Bands"""
        if len(prices) < period:
            return None
        
        recent = prices[-period:]
        sma = sum(recent) / period
        variance = sum((p - sma) ** 2 for p in recent) / period
        std_dev = variance ** 0.5
        
        return {
            'upper': sma + (2 * std_dev),
            'middle': sma,
            'lower': sma - (2 * std_dev),
            'width': (4 * std_dev) / sma * 100 if sma else 0
        }
    
    def _support_resistance(self, prices: List[float], window: int = 20) -> Optional[Dict]:
        """Support and Resistance Levels"""
        if len(prices) < window:
            return None
        
        recent = prices[-window:]
        support = min(recent)
        resistance = max(recent)
        pivot = (support + resistance + prices[-1]) / 3
        
        return {
            'support': support,
            'resistance': resistance,
            'pivot': pivot
        }
    
    def _stochastic(self, prices: List[float], period: int = 14) -> Optional[Dict]:
        """Stochastic Oscillator"""
        if len(prices) < period:
            return None
        
        recent = prices[-period:]
        highest = max(recent)
        lowest = min(recent)
        
        if highest == lowest:
            return None
        
        k = ((prices[-1] - lowest) / (highest - lowest)) * 100
        d = k * 0.9  # Simplified
        
        return {'k': k, 'd': d}
    
    def _adx(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Average Directional Index (Simplified)"""
        if len(prices) < period * 2:
            return None
        
        # Simplified ADX calculation
        recent = prices[-period:]
        prev = prices[-period*2:-period]
        
        if not prev:
            return None
        
        # Calculate directional movement
        current_range = max(recent) - min(recent)
        prev_range = max(prev) - min(prev)
        
        if prev_range == 0:
            return None
        
        # Simplified strength calculation
        strength = abs(current_range - prev_range) / prev_range * 100
        return min(strength, 100)
    
    def get_technical_score(self, indicators: TechnicalIndicators, current_price: float) -> Tuple[int, List[str], List[str]]:
        """حساب نقاط التحليل الفني"""
        score = 0
        buy_reasons = []
        sell_reasons = []
        
        # RSI Analysis
        if indicators.rsi:
            if indicators.rsi <= 30:
                score += 2
                buy_reasons.append(f"RSI تشبع بيعي ({indicators.rsi:.1f})")
            elif indicators.rsi <= 40:
                score += 1
                buy_reasons.append(f"RSI قريب من التشبع البيعي ({indicators.rsi:.1f})")
            elif indicators.rsi >= 70:
                score -= 2
                sell_reasons.append(f"RSI تشبع شرائي ({indicators.rsi:.1f})")
            elif indicators.rsi >= 60:
                score -= 1
                sell_reasons.append(f"RSI قريب من التشبع الشرائي ({indicators.rsi:.1f})")
        
        # MACD Analysis
        if indicators.macd and indicators.macd_signal:
            if indicators.macd_trend == "BULLISH":
                score += 1
                buy_reasons.append("MACD صاعد")
            elif indicators.macd_trend == "BEARISH":
                score -= 1
                sell_reasons.append("MACD هابط")
        
        # Moving Average Analysis
        if indicators.sma_20 and indicators.sma_50:
            if current_price > indicators.sma_20 > indicators.sma_50:
                score += 2
                buy_reasons.append("السعر فوق المتوسطات - اتجاه صاعد")
            elif current_price < indicators.sma_20 < indicators.sma_50:
                score -= 2
                sell_reasons.append("السعر تحت المتوسطات - اتجاه هابط")
        
        # Bollinger Bands
        if indicators.bb_position:
            if indicators.bb_position == "LOWER":
                score += 1
                buy_reasons.append("السعر عند النطاق السفلي لبولينجر")
            elif indicators.bb_position == "UPPER":
                score -= 1
                sell_reasons.append("السعر عند النطاق العلوي لبولينجر")
        
        # Support/Resistance
        if indicators.support_level and indicators.resistance_level:
            dist_to_support = (current_price - indicators.support_level) / current_price * 100
            dist_to_resistance = (indicators.resistance_level - current_price) / current_price * 100
            
            if dist_to_support < 2:
                score += 1
                buy_reasons.append(f"قريب من مستوى الدعم ({indicators.support_level:.2f})")
            elif dist_to_resistance < 2:
                score -= 1
                sell_reasons.append(f"قريب من مستوى المقاومة ({indicators.resistance_level:.2f})")
        
        # Volume
        if indicators.volume_ratio:
            if indicators.volume_ratio > 1.5:
                buy_reasons.append("حجم تداول مرتفع - اهتمام قوي")
            elif indicators.volume_ratio < 0.5:
                sell_reasons.append("حجم تداول منخفض - قلة الاهتمام")
        
        return score, buy_reasons, sell_reasons

# ============================================================================
# TIMING ANALYZER
# ============================================================================

class TimingAnalyzer:
    """محلل التوقيت"""
    
    def __init__(self):
        # Best trading hours based on historical analysis
        self.best_buy_hours_stock = [10, 11, 14, 15]  # EGX hours
        self.best_sell_hours_stock = [12, 13, 15, 16]
        
        # Crypto is 24/7 but has patterns
        self.best_buy_hours_crypto = [2, 3, 4, 14, 15, 16]  # UTC
        self.best_sell_hours_crypto = [8, 9, 10, 20, 21, 22]  # UTC
        
        # Weekly patterns (0=Monday, 6=Sunday)
        self.best_buy_days = [0, 1, 4]  # Mon, Tue, Fri
        self.best_sell_days = [3, 4]    # Thu, Fri
    
    def analyze(self, asset_type: AssetType = AssetType.STOCK) -> TimingAnalysis:
        """تحليل التوقيت"""
        now = datetime.utcnow()
        
        timing = TimingAnalysis(
            current_hour_utc=now.hour,
            current_session=self._get_market_session(now, asset_type),
            day_of_week=now.weekday(),
            month=now.month
        )
        
        if asset_type == AssetType.STOCK:
            timing.best_buy_hours = self.best_buy_hours_stock
            timing.best_sell_hours = self.best_sell_hours_stock
        else:
            timing.best_buy_hours = self.best_buy_hours_crypto
            timing.best_sell_hours = self.best_sell_hours_crypto
        
        # Calculate timing score
        timing.timing_score = self._calculate_timing_score(timing, asset_type)
        timing.timing_recommendation = self._get_timing_recommendation(timing)
        
        return timing
    
    def _get_market_session(self, dt: datetime, asset_type: AssetType) -> str:
        """Get current market session"""
        if asset_type == AssetType.CRYPTO:
            return "24/7"
        
        # EGX Market Hours (Cairo time, UTC+2)
        hour = dt.hour
        
        if hour < 7:
            return "PRE_MARKET"
        elif 7 <= hour < 9:
            return "PRE_MARKET"
        elif 9 <= hour < 11:
            return "MARKET_OPEN"
        elif 11 <= hour < 14:
            return "MARKET_OPEN"
        elif 14 <= hour < 15:
            return "MARKET_CLOSE"
        else:
            return "AFTER_HOURS"
    
    def _calculate_timing_score(self, timing: TimingAnalysis, asset_type: AssetType) -> int:
        """Calculate timing score (-5 to +5)"""
        score = 0
        
        # Hour-based scoring
        if timing.current_hour_utc in timing.best_buy_hours:
            score += 2
        elif timing.current_hour_utc in timing.best_sell_hours:
            score -= 1
        
        # Day-based scoring
        if timing.day_of_week in self.best_buy_days:
            score += 1
        elif timing.day_of_week in self.best_sell_days:
            score -= 1
        
        # Month patterns (if known)
        # Typically, end of month can be bearish due to profit taking
        if timing.month in [12, 1]:  # Year end / beginning
            score += 1  # Often bullish
        
        return score
    
    def _get_timing_recommendation(self, timing: TimingAnalysis) -> str:
        """Get timing recommendation"""
        if timing.timing_score >= 2:
            return "TIMING_EXCELLENT"
        elif timing.timing_score >= 1:
            return "TIMING_GOOD"
        elif timing.timing_score <= -2:
            return "TIMING_POOR"
        else:
            return "TIMING_NEUTRAL"

# ============================================================================
# EVENT ANALYZER
# ============================================================================

class EventAnalyzer:
    """محلل الأحداث"""
    
    def __init__(self, db_conn=None):
        self.conn = db_conn
    
    def analyze(self, symbol: str, asset_type: AssetType = AssetType.STOCK) -> List[EventImpact]:
        """تحليل الأحداث المؤثرة"""
        events = []
        
        # Check for dividends
        dividend = self._check_dividend(symbol)
        if dividend:
            events.append(dividend)
        
        # Check for earnings
        earnings = self._check_earnings(symbol)
        if earnings:
            events.append(earnings)
        
        # Check for market events
        market_events = self._check_market_events(asset_type)
        events.extend(market_events)
        
        return events
    
    def _check_dividend(self, symbol: str) -> Optional[EventImpact]:
        """Check for upcoming dividend"""
        # This would typically query a dividends table
        # Placeholder implementation
        return None
    
    def _check_earnings(self, symbol: str) -> Optional[EventImpact]:
        """Check for upcoming earnings announcement"""
        # This would typically query an earnings calendar
        return None
    
    def _check_market_events(self, asset_type: AssetType) -> List[EventImpact]:
        """Check for general market events"""
        events = []
        
        # Example: FOMC meetings, economic data releases
        # This would typically come from an events calendar
        
        return events
    
    def get_event_score(self, events: List[EventImpact]) -> Tuple[int, List[str]]:
        """Calculate event impact score"""
        score = 0
        warnings = []
        
        for event in events:
            if event.expected_impact == "POSITIVE":
                score += int(event.impact_magnitude * 2)
            elif event.expected_impact == "NEGATIVE":
                score -= int(event.impact_magnitude * 2)
            
            if event.confidence > 0.7:
                warnings.append(f"{event.event_type}: {event.description}")
        
        return score, warnings

# ============================================================================
# UNIFIED ANALYZER
# ============================================================================

class UnifiedAnalyzer:
    """المحلل الموحد"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.conn = None
        
        if db_path and os.path.exists(db_path):
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
        
        self.financial_analyzer = FinancialAnalyzer(self.conn)
        self.technical_analyzer = TechnicalAnalyzer(self.conn)
        self.timing_analyzer = TimingAnalyzer()
        self.event_analyzer = EventAnalyzer(self.conn)
    
    def analyze(self, symbol: str, asset_type: str = "STOCK") -> Optional[UnifiedAnalysisResult]:
        """تحليل شامل"""
        
        asset = AssetType.STOCK if asset_type.upper() == "STOCK" else AssetType.CRYPTO
        
        # Get basic stock info
        stock_info = self._get_stock_info(symbol)
        if not stock_info:
            return None
        
        result = UnifiedAnalysisResult(
            symbol=symbol.upper(),
            name=stock_info.get('name', ''),
            asset_type=asset_type,
            current_price=stock_info.get('current_price', 0),
            previous_close=stock_info.get('previous_close')
        )
        
        # Get price history
        prices = self._get_price_history(symbol)
        volumes = self._get_volume_history(symbol)
        
        if len(prices) < 50:
            result.data_quality = "POOR"
            result.warnings.append("بيانات غير كافية للتحليل (أقل من 50 يوم)")
            return result
        
        # 1. Financial Analysis
        result.financial = self.financial_analyzer.analyze(symbol, asset)
        
        # 2. Technical Analysis
        result.technical = self.technical_analyzer.analyze(symbol, prices, volumes)
        
        # 3. Timing Analysis
        result.timing = self.timing_analyzer.analyze(asset)
        
        # 4. Event Analysis
        result.events = self.event_analyzer.analyze(symbol, asset)
        
        # Calculate overall score
        total_score = 0
        
        # Financial score
        if result.financial:
            fin_score, fin_buy, fin_sell = self.financial_analyzer.get_financial_score(result.financial)
            total_score += fin_score
            result.buy_reasons.extend(fin_buy)
            result.sell_reasons.extend(fin_sell)
        
        # Technical score
        if result.technical:
            tech_score, tech_buy, tech_sell = self.technical_analyzer.get_technical_score(
                result.technical, result.current_price
            )
            total_score += tech_score
            result.buy_reasons.extend(tech_buy)
            result.sell_reasons.extend(tech_sell)
        
        # Timing score
        if result.timing:
            total_score += result.timing.timing_score
            
            if result.timing.timing_recommendation == "TIMING_EXCELLENT":
                result.buy_reasons.append("توقيت ممتاز للشراء")
            elif result.timing.timing_recommendation == "TIMING_POOR":
                result.sell_reasons.append("توقيت غير مناسب")
        
        # Event score
        if result.events:
            event_score, event_warnings = self.event_analyzer.get_event_score(result.events)
            total_score += event_score
            result.warnings.extend(event_warnings)
        
        # Set overall score and signal
        result.overall_score = total_score
        
        if total_score >= 5:
            result.overall_signal = "STRONG_BUY"
            result.confidence = min(80 + total_score * 2, 95)
        elif total_score >= 2:
            result.overall_signal = "BUY"
            result.confidence = 60 + total_score * 5
        elif total_score <= -5:
            result.overall_signal = "STRONG_SELL"
            result.confidence = min(80 + abs(total_score) * 2, 95)
        elif total_score <= -2:
            result.overall_signal = "SELL"
            result.confidence = 60 + abs(total_score) * 5
        else:
            result.overall_signal = "HOLD"
            result.confidence = 50
        
        # Calculate price targets
        if result.technical:
            result.entry_price = result.current_price
            result.target_price = result.technical.resistance_level
            result.stop_loss = result.technical.support_level
            
            if not result.target_price:
                result.target_price = result.current_price * 1.05
            if not result.stop_loss:
                result.stop_loss = result.current_price * 0.97
        
        return result
    
    def _get_stock_info(self, symbol: str) -> Optional[Dict]:
        """Get stock basic info"""
        if not self.conn:
            return {'name': symbol, 'current_price': 0}
        
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT ticker, name, current_price, previous_close
                FROM stocks 
                WHERE ticker = ?
            ''', (symbol.upper(),))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
        except:
            pass
        
        return None
    
    def _get_price_history(self, symbol: str, days: int = 365) -> List[float]:
        """Get price history"""
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        try:
            # Use stock_price_history with JOIN to stocks
            cursor.execute('''
                SELECT sph.close_price 
                FROM stock_price_history sph
                JOIN stocks s ON sph.stock_id = s.id
                WHERE s.ticker = ? 
                ORDER BY sph.date ASC
                LIMIT ?
            ''', (symbol.upper(), days))
            
            rows = cursor.fetchall()
            return [row[0] for row in rows if row[0]]
        except Exception as e:
            print(f"Error getting price history: {e}")
            return []
    
    def _get_volume_history(self, symbol: str, days: int = 365) -> List[float]:
        """Get volume history"""
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        try:
            # Use stock_price_history with JOIN to stocks
            cursor.execute('''
                SELECT sph.volume 
                FROM stock_price_history sph
                JOIN stocks s ON sph.stock_id = s.id
                WHERE s.ticker = ? 
                ORDER BY sph.date ASC
                LIMIT ?
            ''', (symbol.upper(), days))
            
            rows = cursor.fetchall()
            return [row[0] for row in rows if row[0]]
        except Exception as e:
            print(f"Error getting volume history: {e}")
            return []
    
    def get_top_recommendations(self, limit: int = 10, signal_filter: str = None) -> List[UnifiedAnalysisResult]:
        """Get top recommendations"""
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT ticker FROM stocks 
            WHERE current_price IS NOT NULL
            ORDER BY ticker
        ''')
        
        symbols = [row[0] for row in cursor.fetchall()]
        results = []
        
        for symbol in symbols[:100]:  # Limit for performance
            try:
                result = self.analyze(symbol)
                if result:
                    if signal_filter:
                        if signal_filter.upper() in ["BUY", "STRONG_BUY"] and result.overall_score >= 2:
                            results.append(result)
                        elif signal_filter.upper() in ["SELL", "STRONG_SELL"] and result.overall_score <= -2:
                            results.append(result)
                    else:
                        results.append(result)
            except:
                continue
        
        # Sort by score
        results.sort(key=lambda x: x.overall_score, reverse=True)
        return results[:limit]
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def evaluate_risk(
        self,
        symbol: str,
        capital: float = 10000,
        risk_percent: float = 2.0,
        entry_price: Optional[float] = None,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None
    ) -> Optional[Dict]:
        """
        تقييم المخاطرة للصفقة
        
        Args:
            symbol: رمز السهم
            capital: رأس المال
            risk_percent: نسبة المخاطرة (1-5%)
            entry_price: سعر الدخول (اختياري - يستخدم السعر الحالي)
            target_price: سعر الهدف
            stop_loss: سعر وقف الخسارة
        """
        # الحصول على التحليل
        result = self.analyze(symbol)
        if not result:
            return None
        
        # استخدام السعر الحالي إذا لم يُحدد سعر الدخول
        if not entry_price:
            entry_price = result.current_price
        
        # استخدام الهدف والوقف من التحليل إذا لم يُحددا
        if not target_price and result.target_price:
            target_price = result.target_price
        if not stop_loss and result.stop_loss:
            stop_loss = result.stop_loss
        
        # حساب المخاطرة
        risk_manager = RiskManager(capital=capital, risk_percent=risk_percent)
        
        assessment = risk_manager.evaluate_trade(
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            signal=result.overall_signal,
            support_level=result.technical.support_level if result.technical else None,
            resistance_level=result.technical.resistance_level if result.technical else None
        )
        
        return {
            "symbol": symbol,
            "analysis": result.to_dict(),
            "risk_assessment": assessment.to_dict() if hasattr(assessment, 'to_dict') else assessment
        }

# ============================================================================
# RISK MANAGEMENT SYSTEM (قواعد التداول العقلاني)
# ============================================================================

class RiskLevel(Enum):
    """مستويات المخاطرة"""
    CONSERVATIVE = "CONSERVATIVE"  # 1-2% risk
    MODERATE = "MODERATE"          # 2-3% risk
    AGGRESSIVE = "AGGRESSIVE"      # 3-5% risk

@dataclass
class RiskAssessment:
    """تقييم المخاطرة"""
    # القرار
    action: str                      # APPROVED, REJECTED, CAUTION
    confidence: float                # ثقة التقييم
    
    # تفاصيل المخاطرة
    risk_percent: float              # نسبة المخاطرة الفعلية
    risk_amount: float               # مبلغ المخاطرة
    position_size: float             # حجم العقد
    shares_units: float              # عدد الأسهم
    
    # Risk-Reward
    risk_reward_ratio: float         # نسبة الربح للمخاطرة
    potential_profit: float          # الربح المحتمل
    potential_loss: float            # الخسارة المحتملة
    rr_quality: str                  # EXCELLENT, GOOD, POOR
    
    # Stop Loss & Take Profit
    stop_loss_price: float
    take_profit_price: float
    stop_loss_percent: float
    take_profit_percent: float
    
    # التوصيات
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)

class RiskManager:
    """
    مدير المخاطر المتقدم
    
    القواعد:
    1. المخاطرة بحد أقصى 2-5% من رأس المال
    2. نسبة R:R المثالية 1:3
    3. وقف الخسارة تحت الدعم + 10 نقاط
    4. تجنب Margin Call
    """
    
    MIN_RR_RATIO = 2.0
    GOOD_RR_RATIO = 3.0
    MAX_RISK_PERCENT = 5.0
    
    def __init__(
        self,
        capital: float = 10000,
        risk_percent: float = 2.0,
        leverage: float = 1.0
    ):
        self.capital = capital
        self.risk_percent = min(risk_percent, self.MAX_RISK_PERCENT)
        self.leverage = leverage
    
    def evaluate_trade(
        self,
        entry_price: float,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        signal: str = "BUY",
        support_level: Optional[float] = None,
        resistance_level: Optional[float] = None
    ) -> RiskAssessment:
        """تقييم الصفقة"""
        
        is_buy = signal.upper() in ["BUY", "STRONG_BUY"]
        
        # حساب وقف الخسارة الذكي
        if not stop_loss:
            stop_loss = self._calculate_smart_sl(
                entry_price, is_buy, support_level, resistance_level
            )
        
        # حساب الهدف
        if not target_price:
            target_price = self._calculate_target(entry_price, stop_loss, is_buy)
        
        # حساب Risk-Reward
        rr_ratio, rr_quality = self._calculate_rr(entry_price, stop_loss, target_price, is_buy)
        
        # حساب حجم الصفقة
        risk_amount = self.capital * (self.risk_percent / 100)
        sl_distance = abs(entry_price - stop_loss)
        shares = risk_amount / sl_distance if sl_distance > 0 else 0
        position_size = shares * entry_price
        
        # حساب الأرباح والخسائر المحتملة
        potential_profit = abs(target_price - entry_price) * shares
        potential_loss = sl_distance * shares
        
        # اتخاذ القرار
        action, confidence, recommendations, warnings = self._make_decision(
            rr_ratio, rr_quality, (potential_loss / self.capital) * 100
        )
        
        return RiskAssessment(
            action=action,
            confidence=confidence,
            risk_percent=(potential_loss / self.capital) * 100,
            risk_amount=potential_loss,
            position_size=position_size,
            shares_units=shares,
            risk_reward_ratio=rr_ratio,
            potential_profit=potential_profit,
            potential_loss=potential_loss,
            rr_quality=rr_quality,
            stop_loss_price=stop_loss,
            take_profit_price=target_price,
            stop_loss_percent=(sl_distance / entry_price) * 100,
            take_profit_percent=(abs(target_price - entry_price) / entry_price) * 100,
            recommendations=recommendations,
            warnings=warnings
        )
    
    def _calculate_smart_sl(
        self,
        entry_price: float,
        is_buy: bool,
        support: Optional[float],
        resistance: Optional[float]
    ) -> float:
        """حساب وقف الخسارة الذكي"""
        if is_buy:
            base = support or entry_price * 0.97
            buffer = max(10, base * 0.005)  # 10 نقاط أو 0.5%
            return base - buffer
        else:
            base = resistance or entry_price * 1.03
            buffer = max(15, base * 0.005)  # 15 نقطة أو 0.5%
            return base + buffer
    
    def _calculate_target(
        self,
        entry: float,
        sl: float,
        is_buy: bool
    ) -> float:
        """حساب الهدف بناءً على R:R 1:3"""
        risk = abs(entry - sl)
        reward = risk * self.GOOD_RR_RATIO
        return entry + reward if is_buy else entry - reward
    
    def _calculate_rr(
        self,
        entry: float,
        sl: float,
        tp: float,
        is_buy: bool
    ) -> Tuple[float, str]:
        """حساب نسبة R:R"""
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        
        if risk == 0:
            return 0, "INVALID"
        
        rr = reward / risk
        
        if rr >= self.GOOD_RR_RATIO:
            quality = "EXCELLENT" if rr >= 5 else "GOOD"
        elif rr >= self.MIN_RR_RATIO:
            quality = "ACCEPTABLE"
        else:
            quality = "POOR"
        
        return rr, quality
    
    def _make_decision(
        self,
        rr_ratio: float,
        rr_quality: str,
        risk_pct: float
    ) -> Tuple[str, float, List[str], List[str]]:
        """اتخاذ القرار"""
        recommendations = []
        warnings = []
        action = "APPROVED"
        confidence = 70.0
        
        # فحص R:R
        if rr_quality in ["EXCELLENT", "GOOD"]:
            confidence += 15
            recommendations.append(f"✅ نسبة R:R جيدة ({rr_ratio:.1f}:1)")
        elif rr_quality == "POOR":
            action = "REJECTED"
            confidence -= 20
            warnings.append(f"❌ نسبة R:R ضعيفة ({rr_ratio:.1f}:1)")
        
        # فحص المخاطرة
        if risk_pct > self.MAX_RISK_PERCENT:
            action = "REJECTED"
            warnings.append(f"❌ المخاطرة عالية جداً ({risk_pct:.1f}%)")
        else:
            recommendations.append(f"✅ المخاطرة ضمن الحدود ({risk_pct:.1f}%)")
        
        if action == "APPROVED":
            recommendations.append("🎯 الصفقة مقبولة")
        
        return action, max(0, min(100, confidence)), recommendations, warnings

# ============================================================================
# ADX INDICATOR (Enhanced)
# ============================================================================

class ADXAnalyzer:
    """
    محلل ADX المتقدم
    
    ADX > 25 = Trend (اتجاه قوي)
    ADX < 20 = Range (تذبذب)
    """
    
    @staticmethod
    def calculate(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14
    ) -> Dict:
        """حساب ADX و +DI و -DI"""
        
        if len(highs) < period * 2:
            return {
                "adx": None,
                "plus_di": None,
                "minus_di": None,
                "trend_strength": "INSUFFICIENT_DATA",
                "trend_direction": "UNKNOWN"
            }
        
        # حساب True Range
        tr_list = []
        plus_dm = []
        minus_dm = []
        
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)
            
            up_move = highs[i] - highs[i-1]
            down_move = lows[i-1] - lows[i]
            
            if up_move > down_move and up_move > 0:
                plus_dm.append(up_move)
                minus_dm.append(0)
            elif down_move > up_move and down_move > 0:
                plus_dm.append(0)
                minus_dm.append(down_move)
            else:
                plus_dm.append(0)
                minus_dm.append(0)
        
        # حساب المتوسطات
        def smooth(values: List[float], period: int) -> List[float]:
            smoothed = [sum(values[:period])]
            for i in range(period, len(values)):
                smoothed.append(smoothed[-1] - smoothed[-1]/period + values[i])
            return smoothed
        
        atr = smooth(tr_list, period)
        plus_di_raw = smooth(plus_dm, period)
        minus_di_raw = smooth(minus_dm, period)
        
        # حساب DI
        plus_di = [(pdi / atr[i]) * 100 if atr[i] > 0 else 0 
                   for i, pdi in enumerate(plus_di_raw)]
        minus_di = [(mdi / atr[i]) * 100 if atr[i] > 0 else 0 
                    for i, mdi in enumerate(minus_di_raw)]
        
        # حساب DX و ADX
        dx = []
        for i in range(len(plus_di)):
            di_sum = plus_di[i] + minus_di[i]
            if di_sum > 0:
                dx.append(abs(plus_di[i] - minus_di[i]) / di_sum * 100)
            else:
                dx.append(0)
        
        adx = sum(dx[-period:]) / period if len(dx) >= period else 0
        
        last_plus_di = plus_di[-1] if plus_di else 0
        last_minus_di = minus_di[-1] if minus_di else 0
        
        # تحديد القوة والاتجاه
        if adx > 50:
            trend_strength = "VERY_STRONG"
        elif adx > 25:
            trend_strength = "STRONG"
        elif adx > 20:
            trend_strength = "DEVELOPING"
        else:
            trend_strength = "WEAK_RANGE"
        
        trend_direction = "BULLISH" if last_plus_di > last_minus_di else "BEARISH" if last_minus_di > last_plus_di else "NEUTRAL"
        
        return {
            "adx": round(adx, 2),
            "plus_di": round(last_plus_di, 2),
            "minus_di": round(last_minus_di, 2),
            "trend_strength": trend_strength,
            "trend_direction": trend_direction
        }

# ============================================================================
# MULTI-TIMEFRAME ANALYSIS
# ============================================================================

class MultiTimeframeAnalyzer:
    """
    محلل متعدد الأطر الزمنية
    شهري ← أسبوعي ← يومي ← 4H ← hourly ← 5min
    """
    
    TIMEFRAMES = {
        "monthly": {"weight": 30, "priority": 1},
        "weekly": {"weight": 25, "priority": 2},
        "daily": {"weight": 20, "priority": 3},
        "4h": {"weight": 15, "priority": 4},
        "hourly": {"weight": 7, "priority": 5},
        "5m": {"weight": 3, "priority": 6}
    }
    
    @classmethod
    def analyze(cls, timeframe_data: Dict[str, Dict]) -> Dict:
        """تحليل متعدد الأطر"""
        
        analysis = {}
        weighted_score = 0
        total_weight = 0
        trends = []
        
        for tf, data in timeframe_data.items():
            if tf in cls.TIMEFRAMES:
                weight = cls.TIMEFRAMES[tf]["weight"]
                score = data.get("score", 0)
                trend = data.get("trend", "NEUTRAL")
                
                weighted_score += score * weight
                total_weight += weight
                trends.append(trend)
                
                analysis[tf] = {
                    "trend": trend,
                    "score": score,
                    "weight": weight
                }
        
        final_score = weighted_score / total_weight if total_weight > 0 else 0
        
        bullish = sum(1 for t in trends if "BULL" in t)
        bearish = sum(1 for t in trends if "BEAR" in t)
        
        if bullish >= 3:
            overall = "STRONG_BULLISH" if bullish >= 4 else "BULLISH"
        elif bearish >= 3:
            overall = "STRONG_BEARISH" if bearish >= 4 else "BEARISH"
        else:
            overall = "NEUTRAL"
        
        return {
            "overall_trend": overall,
            "trend_alignment": bullish >= 3 or bearish >= 3,
            "weighted_score": round(final_score, 2),
            "timeframe_analysis": analysis,
            "recommendation": "BUY" if final_score >= 1.5 else "SELL" if final_score <= -1.5 else "HOLD"
        }

# ============================================================================
# PATTERN RECOGNITION ENGINE (محرك النماذج السعرية)
# ============================================================================
# Priority 4: Automated Pattern Recognition
# الأكثر ثقة تاريخياً من المصادر

@dataclass
class PatternResult:
    """نتيجة التعرف على النموذج"""
    pattern_type: str           # HEAD_SHOULDERS, TRIANGLE, DOUBLE_TOP, etc.
    pattern_name: str           # الاسم بالعربية
    direction: str              # BULLISH, BEARISH, NEUTRAL
    confidence: float           # 0-100
    completion_percent: float   # نسبة اكتمال النموذج
    breakout_level: Optional[float]  # مستوى الاختراق المتوقع
    target_price: Optional[float]     # الهدف المتوقع
    stop_loss: Optional[float]        # وقف الخسارة المقترح
    volume_confirmation: bool         # تأكيد حجم التداول
    signal: str                       # BUY, SELL, HOLD
    description: str                  # وصف النموذج
    risk_reward_ratio: Optional[float]
    
    def to_dict(self):
        return asdict(self)


class PatternRecognitionEngine:
    """
    محرك التعرف على النماذج السعرية
    
    النماذج المدعومة:
    1. الرأس والكتفين (Head & Shoulders) - الأكثر ثقة
    2. المثلثات (Triangles) - تصاعدي، تنازلي، متماثل
    3. القمم والقيعان المزدوجة (Double Top/Bottom)
    4. الأعلام والأوتاد (Flags & Wedges)
    5. القنوات السعرية (Channels)
    """
    
    # عتبات التعرف على النماذج
    MIN_DATA_POINTS = 50        # الحد الأدنى للبيانات
    SHOULDER_TOLERANCE = 0.05   # تفاوت مسموح بين الكتفين (5%)
    NECKLINE_BUFFER = 0.02      # منطقة كسر خط الرقبة
    VOLUME_THRESHOLD = 1.3      # عتبة تأكيد الحجم (1.3x المتوسط)
    
    def __init__(self):
        self.patterns_found: List[PatternResult] = []
        self.fibonacci_analyzer = FibonacciAnalyzer()
    
    def analyze(
        self, 
        highs: List[float], 
        lows: List[float], 
        closes: List[float],
        volumes: List[float] = None,
        enable_fibonacci: bool = True
    ) -> List[PatternResult]:
        """
        تحليل شامل للنماذج السعرية
        
        Args:
            highs: قائمة أعلى الأسعار
            lows: قائمة أدنى الأسعار
            closes: قائمة أسعار الإغلاق
            volumes: قائمة أحجام التداول (اختياري)
            enable_fibonacci: تفعيل دمج مستويات فيبوناتشي
        """
        self.patterns_found = []
        
        if len(closes) < self.MIN_DATA_POINTS:
            return self.patterns_found
        
        # 1. الرأس والكتفين (الأولوية القصوى)
        self._detect_head_and_shoulders(highs, lows, closes, volumes, enable_fibonacci)
        
        # 2. المثلثات
        self._detect_triangles(highs, lows, closes, volumes, enable_fibonacci)
        
        # 3. القمم والقيعان المزدوجة
        self._detect_double_patterns(highs, lows, closes, volumes, enable_fibonacci)
        
        # 4. الأعلام والأوتاد
        self._detect_flags_and_wedges(highs, lows, closes, volumes)
        
        # 5. القنوات السعرية
        self._detect_channels(highs, lows, closes, volumes)
        
        # 6. تطبيق فيبوناتشي على النماذج المكتشفة
        if enable_fibonacci:
            self._apply_fibonacci_enhancement(closes)
        
        return self.patterns_found
    
    def _apply_fibonacci_enhancement(self, closes: List[float]):
        """
        تطبيق تحسينات فيبوناتشي على النماذج المكتشفة
        """
        current_price = closes[-1]
        
        for i, pattern in enumerate(self.patterns_found):
            # دمج فيبوناتشي مع النموذج
            fib_result = self.fibonacci_analyzer.integrate_with_pattern(
                pattern_type=pattern.pattern_type,
                pattern_high=pattern.stop_loss * 1.05 if pattern.stop_loss else closes[-20:][max(closes[-20:])],
                pattern_low=pattern.target_price * 0.95 if pattern.target_price else closes[-20:][min(closes[-20:])],
                current_price=current_price
            )
            
            # تحديث الثقة
            if fib_result["confidence_boost"] > 0:
                self.patterns_found[i].confidence = min(95, pattern.confidence + fib_result["confidence_boost"])
                self.patterns_found[i].description += f" | {' '.join(fib_result['signals'])}"
    
    # =========================================================================
    # 1. الرأس والكتفين (Head & Shoulders) - الأكثر ثقة تاريخياً
    # =========================================================================
    
    def _detect_head_and_shoulders(
        self, 
        highs: List[float], 
        lows: List[float], 
        closes: List[float],
        volumes: List[float],
        enable_fibonacci: bool = True
    ):
        """
        التعرف على نموذج الرأس والكتفين
        
        الشروط البرمجية:
        1. الكتف الأيسر: قمة يتبعها هبوط
        2. الرأس: قمة أعلى من الكتف الأيسر
        3. الكتف الأيمن: قمة مساوية أو أقل من الكتف الأيسر (تفاوت 5%)
        4. خط الرقبة: خط يربط بين قيعان الكتفين
        5. الإشارة: بيع عند كسر خط الرقبة لأسفل
        """
        if len(highs) < 30:
            return
        
        # البحث عن القمم المحلية
        peaks = self._find_peaks(highs, window=5)
        
        if len(peaks) < 3:
            return
        
        # فحص آخر 3 قمم للنموذج العكسي (بيع)
        for i in range(len(peaks) - 2):
            left_shoulder_idx, left_shoulder_price = peaks[i]
            head_idx, head_price = peaks[i + 1]
            right_shoulder_idx, right_shoulder_price = peaks[i + 2]
            
            # التحقق من شروط النموذج
            # 1. الرأس أعلى من الكتفين
            if not (head_price > left_shoulder_price and head_price > right_shoulder_price):
                continue
            
            # 2. الكتفين متقاربين (تفاوت 5%)
            shoulder_diff = abs(left_shoulder_price - right_shoulder_price) / left_shoulder_price
            if shoulder_diff > self.SHOULDER_TOLERANCE:
                continue
            
            # 3. إيجاد خط الرقبة (أدنى نقطة بين الكتفين)
            neckline_left = min(lows[left_shoulder_idx:head_idx])
            neckline_right = min(lows[head_idx:right_shoulder_idx])
            neckline = (neckline_left + neckline_right) / 2
            
            # 4. حساب نسبة اكتمال النموذج
            current_price = closes[-1]
            completion = 0
            
            if current_price < neckline:
                completion = 100  # النموذج مكتمل ومكسور
            else:
                # حساب المسافة للرقبة
                distance_to_neckline = (current_price - neckline) / current_price * 100
                completion = max(0, 100 - distance_to_neckline * 10)
            
            # 5. حساب الهدف ووقف الخسارة
            head_height = head_price - neckline
            target = neckline - head_height  # الهدف = الرقبة - ارتفاع الرأس
            stop_loss = right_shoulder_price  # الوقف = أعلى الكتف الأيمن
            
            # 6. تأكيد حجم التداول
            volume_confirmed = self._check_volume_confirmation(
                volumes, right_shoulder_idx, len(closes) - 1
            )
            
            # 7. حساب نسبة المخاطرة للعائد
            risk = current_price - stop_loss
            reward = target - current_price
            rr_ratio = abs(reward / risk) if risk != 0 else 0
            
            pattern = PatternResult(
                pattern_type="HEAD_AND_SHOULDERS",
                pattern_name="رأس وكتفين (انعكاسي هابط)",
                direction="BEARISH",
                confidence=min(85, 60 + completion * 0.25),
                completion_percent=completion,
                breakout_level=neckline,
                target_price=target,
                stop_loss=stop_loss,
                volume_confirmation=volume_confirmed,
                signal="SELL" if completion >= 80 else "HOLD",
                description=f"نموذج رأس وكتفين مكتمل بنسبة {completion:.0f}%. الرأس عند {head_price:.2f}، خط الرقبة عند {neckline:.2f}",
                risk_reward_ratio=round(rr_ratio, 2)
            )
            self.patterns_found.append(pattern)
            return  # نكتفي بنموذج واحد
    
    # =========================================================================
    # 2. المثلثات (Triangles)
    # =========================================================================
    
    def _detect_triangles(
        self, 
        highs: List[float], 
        lows: List[float], 
        closes: List[float],
        volumes: List[float],
        enable_fibonacci: bool = True
    ):
        """
        التعرف على المثلثات السعرية
        
        الأنواع:
        - مثلث تصاعدي (Ascending): قمة أفريقية وقيعان صاعدة
        - مثلث تنازلي (Descending): قيعان أفريقية وقمم هابطة  
        - مثلث متماثل (Symmetrical): قمم هابطة وقيعان صاعدة
        """
        if len(highs) < 20:
            return
        
        # تحليل آخر 20 شمعة
        recent_highs = highs[-20:]
        recent_lows = lows[-20:]
        
        # حساب خطوط الاتجاه
        high_trend = self._calculate_trend_line(recent_highs)
        low_trend = self._calculate_trend_line(recent_lows)
        
        # تحديد نوع المثلث
        pattern_type = None
        direction = "NEUTRAL"
        
        # مثلث تصاعدي: القمم أفريقية (high_trend ≈ 0) والقيعان صاعدة (low_trend > 0)
        if abs(high_trend) < 0.1 and low_trend > 0.2:
            pattern_type = "ASCENDING_TRIANGLE"
            pattern_name = "مثلث تصاعدي (استمراري صاعد)"
            direction = "BULLISH"
        
        # مثلث تنازلي: القيعان أفريقية (low_trend ≈ 0) والقمم هابطة (high_trend < 0)
        elif abs(low_trend) < 0.1 and high_trend < -0.2:
            pattern_type = "DESCENDING_TRIANGLE"
            pattern_name = "مثلث تنازلي (استمراري هابط)"
            direction = "BEARISH"
        
        # مثلث متماثل: القمم هابطة والقيعان صاعدة
        elif high_trend < -0.1 and low_trend > 0.1:
            pattern_type = "SYMMETRICAL_TRIANGLE"
            pattern_name = "مثلث متماثل (انتظار الاختراق)"
            direction = "NEUTRAL"
        
        if not pattern_type:
            return
        
        # حساب مستوى الاختراق والهدف
        current_price = closes[-1]
        resistance = max(recent_highs)
        support = min(recent_lows)
        
        # عرض المثلث
        triangle_width = resistance - support
        completion = 100 - (triangle_width / current_price * 100 * 5)
        completion = min(100, max(0, completion))
        
        # تحديد الهدف حسب نوع المثلث
        if direction == "BULLISH":
            target = resistance + triangle_width
            stop_loss = support - (triangle_width * 0.1)
            signal = "BUY" if current_price > resistance * 0.98 else "HOLD"
        elif direction == "BEARISH":
            target = support - triangle_width
            stop_loss = resistance + (triangle_width * 0.1)
            signal = "SELL" if current_price < support * 1.02 else "HOLD"
        else:
            # متماثل - ننتظر الاختراق
            target = None
            stop_loss = None
            signal = "HOLD"
        
        # تأكيد الحجم
        volume_confirmed = self._check_volume_confirmation(volumes, -10, -1)
        
        pattern = PatternResult(
            pattern_type=pattern_type,
            pattern_name=pattern_name,
            direction=direction,
            confidence=min(75, 50 + completion * 0.25),
            completion_percent=completion,
            breakout_level=resistance if direction == "BULLISH" else support,
            target_price=target,
            stop_loss=stop_loss,
            volume_confirmation=volume_confirmed,
            signal=signal,
            description=f"{pattern_name}. العرض: {triangle_width:.2f}. انتظار اختراق {'المقاومة' if direction == 'BULLISH' else 'الدعم'}",
            risk_reward_ratio=None
        )
        self.patterns_found.append(pattern)
    
    # =========================================================================
    # 3. القمم والقيعان المزدوجة
    # =========================================================================
    
    def _detect_double_patterns(
        self, 
        highs: List[float], 
        lows: List[float], 
        closes: List[float],
        volumes: List[float],
        enable_fibonacci: bool = True
    ):
        """
        التعرف على القمم والقيعان المزدوجة
        
        Double Top: قمتان متقاربتان على نفس المستوى → إشارة بيع
        Double Bottom: قاعان متقاربان على نفس المستوى → إشارة شراء
        """
        if len(highs) < 20:
            return
        
        peaks = self._find_peaks(highs, window=5)
        troughs = self._find_troughs(lows, window=5)
        
        # ========== Double Top (قمتان مزدوجتان) ==========
        if len(peaks) >= 2:
            peak1_idx, peak1_price = peaks[-2]
            peak2_idx, peak2_price = peaks[-1]
            
            # القمتين متقاربتين (تفاوت 3%)
            if abs(peak1_price - peak2_price) / peak1_price < 0.03:
                # القاع بين القمتين
                valley_price = min(lows[peak1_idx:peak2_idx])
                current_price = closes[-1]
                
                # الإشارة: بيع عند كسر القاع
                if current_price < valley_price:
                    # حساب الهدف
                    pattern_height = peak1_price - valley_price
                    target = valley_price - pattern_height
                    stop_loss = peak2_price
                    
                    volume_confirmed = self._check_volume_confirmation(volumes, peak2_idx, -1)
                    
                    pattern = PatternResult(
                        pattern_type="DOUBLE_TOP",
                        pattern_name="قمة مزدوجة (انعكاسي هابط)",
                        direction="BEARISH",
                        confidence=75,
                        completion_percent=100,
                        breakout_level=valley_price,
                        target_price=target,
                        stop_loss=stop_loss,
                        volume_confirmation=volume_confirmed,
                        signal="SELL",
                        description=f"قمة مزدوجة عند {peak1_price:.2f}. كسر القاع عند {valley_price:.2f}",
                        risk_reward_ratio=abs(target - current_price) / abs(stop_loss - current_price)
                    )
                    self.patterns_found.append(pattern)
        
        # ========== Double Bottom (قاعان مزدوجان) ==========
        if len(troughs) >= 2:
            trough1_idx, trough1_price = troughs[-2]
            trough2_idx, trough2_price = troughs[-1]
            
            # القاعين متقاربين
            if abs(trough1_price - trough2_price) / trough1_price < 0.03:
                # القمة بين القاعين
                peak_price = max(highs[trough1_idx:trough2_idx])
                current_price = closes[-1]
                
                # الإشارة: شراء عند كسر القمة لأعلى
                if current_price > peak_price:
                    pattern_height = peak_price - trough1_price
                    target = peak_price + pattern_height
                    stop_loss = trough2_price
                    
                    volume_confirmed = self._check_volume_confirmation(volumes, trough2_idx, -1)
                    
                    pattern = PatternResult(
                        pattern_type="DOUBLE_BOTTOM",
                        pattern_name="قاع مزدوج (انعكاسي صاعد)",
                        direction="BULLISH",
                        confidence=75,
                        completion_percent=100,
                        breakout_level=peak_price,
                        target_price=target,
                        stop_loss=stop_loss,
                        volume_confirmation=volume_confirmed,
                        signal="BUY",
                        description=f"قاع مزدوج عند {trough1_price:.2f}. كسر القمة عند {peak_price:.2f}",
                        risk_reward_ratio=abs(target - current_price) / abs(stop_loss - current_price)
                    )
                    self.patterns_found.append(pattern)
    
    # =========================================================================
    # 4. الأعلام والأوتاد
    # =========================================================================
    
    def _detect_flags_and_wedges(
        self, 
        highs: List[float], 
        lows: List[float], 
        closes: List[float],
        volumes: List[float]
    ):
        """
        التعرف على الأعلام والأوتاد
        
        Flag: راية صغيرة بعد حركة قوية
        Wedge: وتد صاعد (هابط) أو وتد هابط (صاعد)
        """
        if len(highs) < 30:
            return
        
        # تحديد الحركة القوية السابقة
        pole_start = closes[-30]
        pole_end = closes[-20]
        pole_move = (pole_end - pole_start) / pole_start * 100
        
        # راية بعد حركة قوية (>5%)
        if abs(pole_move) > 5:
            recent_highs = highs[-20:]
            recent_lows = lows[-20:]
            
            # العلم: نطاق ضيق بعد الحركة
            range_high = max(recent_highs)
            range_low = min(recent_lows)
            range_width = (range_high - range_low) / range_low * 100
            
            if range_width < 3:  # نطاق ضيق
                direction = "BULLISH" if pole_move > 0 else "BEARISH"
                
                pattern = PatternResult(
                    pattern_type="FLAG",
                    pattern_name="علم (" + ("صاعد" if direction == "BULLISH" else "هابط") + ")",
                    direction=direction,
                    confidence=70,
                    completion_percent=80,
                    breakout_level=range_high if direction == "BULLISH" else range_low,
                    target_price=closes[-1] * (1 + pole_move/100 * 0.5),
                    stop_loss=range_low if direction == "BULLISH" else range_high,
                    volume_confirmation=self._check_volume_confirmation(volumes, -20, -1),
                    signal="BUY" if direction == "BULLISH" else "SELL",
                    description=f"علم {'صاعد' if direction == 'BULLISH' else 'هابط'} بعد حركة {abs(pole_move):.1f}%",
                    risk_reward_ratio=2.0
                )
                self.patterns_found.append(pattern)
        
        # الوتد الهابط (صاعد)
        recent_high_trend = self._calculate_trend_line(highs[-15:])
        recent_low_trend = self._calculate_trend_line(lows[-15:])
        
        if recent_high_trend < -0.2 and recent_low_trend < -0.2:
            # وتد هابط = إشارة صاعدة
            pattern = PatternResult(
                pattern_type="FALLING_WEDGE",
                pattern_name="وتد هابط (انعكاسي صاعد)",
                direction="BULLISH",
                confidence=70,
                completion_percent=75,
                breakout_level=max(highs[-15:]),
                target_price=closes[-1] * 1.1,
                stop_loss=min(lows[-15:]) * 0.98,
                volume_confirmation=self._check_volume_confirmation(volumes, -15, -1),
                signal="BUY",
                description="وتد هابط - انتظار اختراق لأعلى",
                risk_reward_ratio=2.5
            )
            self.patterns_found.append(pattern)
        
        elif recent_high_trend > 0.2 and recent_low_trend > 0.2:
            # وتد صاعد = إشارة هابطة
            pattern = PatternResult(
                pattern_type="RISING_WEDGE",
                pattern_name="وتد صاعد (انعكاسي هابط)",
                direction="BEARISH",
                confidence=70,
                completion_percent=75,
                breakout_level=min(lows[-15:]),
                target_price=closes[-1] * 0.9,
                stop_loss=max(highs[-15:]) * 1.02,
                volume_confirmation=self._check_volume_confirmation(volumes, -15, -1),
                signal="SELL",
                description="وتد صاعد - انتظار كسر لأسفل",
                risk_reward_ratio=2.5
            )
            self.patterns_found.append(pattern)
    
    # =========================================================================
    # 5. القنوات السعرية
    # =========================================================================
    
    def _detect_channels(
        self, 
        highs: List[float], 
        lows: List[float], 
        closes: List[float],
        volumes: List[float]
    ):
        """
        التعرف على القنوات السعرية
        
        قناة صاعدة: قمم وقيعان صاعدة
        قناة هابطة: قمم وقيعان هابطة
        قناة أفقية: تداول جانبي
        """
        if len(highs) < 30:
            return
        
        high_trend = self._calculate_trend_line(highs[-30:])
        low_trend = self._calculate_trend_line(lows[-30:])
        
        # قناة صاعدة
        if high_trend > 0.15 and low_trend > 0.15:
            pattern = PatternResult(
                pattern_type="ASCENDING_CHANNEL",
                pattern_name="قناة صاعدة (استمراري)",
                direction="BULLISH",
                confidence=65,
                completion_percent=70,
                breakout_level=max(highs[-30:]),
                target_price=closes[-1] * 1.08,
                stop_loss=min(lows[-30:]) * 0.97,
                volume_confirmation=self._check_volume_confirmation(volumes, -20, -1),
                signal="BUY",
                description="قناة صاعدة - شراء عند القاع",
                risk_reward_ratio=2.0
            )
            self.patterns_found.append(pattern)
        
        # قناة هابطة
        elif high_trend < -0.15 and low_trend < -0.15:
            pattern = PatternResult(
                pattern_type="DESCENDING_CHANNEL",
                pattern_name="قناة هابطة (استمراري)",
                direction="BEARISH",
                confidence=65,
                completion_percent=70,
                breakout_level=min(lows[-30:]),
                target_price=closes[-1] * 0.92,
                stop_loss=max(highs[-30:]) * 1.03,
                volume_confirmation=self._check_volume_confirmation(volumes, -20, -1),
                signal="SELL",
                description="قناة هابطة - بيع عند القمة",
                risk_reward_ratio=2.0
            )
            self.patterns_found.append(pattern)
    
    # =========================================================================
    # دوال مساعدة
    # =========================================================================
    
    def _find_peaks(self, data: List[float], window: int = 5) -> List[Tuple[int, float]]:
        """البحث عن القمم المحلية"""
        peaks = []
        for i in range(window, len(data) - window):
            if all(data[i] >= data[i-j] for j in range(1, window+1)) and \
               all(data[i] >= data[i+j] for j in range(1, window+1)):
                peaks.append((i, data[i]))
        return peaks
    
    def _find_troughs(self, data: List[float], window: int = 5) -> List[Tuple[int, float]]:
        """البحث عن القيعان المحلية"""
        troughs = []
        for i in range(window, len(data) - window):
            if all(data[i] <= data[i-j] for j in range(1, window+1)) and \
               all(data[i] <= data[i+j] for j in range(1, window+1)):
                troughs.append((i, data[i]))
        return troughs
    
    def _calculate_trend_line(self, data: List[float]) -> float:
        """حساب ميل خط الاتجاه"""
        if len(data) < 2:
            return 0
        
        # Simple linear regression
        n = len(data)
        x = list(range(n))
        
        sum_x = sum(x)
        sum_y = sum(data)
        sum_xy = sum(x[i] * data[i] for i in range(n))
        sum_x2 = sum(xi ** 2 for xi in x)
        
        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return 0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        # Normalize by average price
        avg_price = sum_y / n
        normalized_slope = (slope * n) / avg_price * 100 if avg_price else 0
        
        return normalized_slope
    
    def _check_volume_confirmation(
        self, 
        volumes: List[float], 
        start_idx: int, 
        end_idx: int
    ) -> bool:
        """
        التحقق من تأكيد حجم التداول
        
        القاعدة: يجب أن يكون الحجم أعلى من المتوسط بـ 30%+ عند الاختراق
        """
        if not volumes or len(volumes) < 20:
            return False
        
        avg_volume = sum(volumes[-20:]) / 20
        
        if start_idx < 0:
            start_idx = len(volumes) + start_idx
        if end_idx < 0:
            end_idx = len(volumes) + end_idx
        
        if start_idx >= end_idx or start_idx < 0 or end_idx > len(volumes):
            return False
        
        recent_volume = sum(volumes[start_idx:end_idx]) / (end_idx - start_idx)
        
        return recent_volume > avg_volume * self.VOLUME_THRESHOLD
    
    def get_pattern_score(self) -> Tuple[int, List[str], List[str]]:
        """حساب نقاط النماذج"""
        score = 0
        buy_reasons = []
        sell_reasons = []
        
        for pattern in self.patterns_found:
            if pattern.confidence < 60:
                continue
            
            weight = pattern.confidence / 100
            
            if pattern.signal == "BUY":
                score += int(3 * weight)
                buy_reasons.append(f"📊 {pattern.pattern_name} ({pattern.confidence:.0f}%)")
            elif pattern.signal == "SELL":
                score -= int(3 * weight)
                sell_reasons.append(f"📊 {pattern.pattern_name} ({pattern.confidence:.0f}%)")
        
        return score, buy_reasons, sell_reasons


# ============================================================================
# OPEN INTEREST DIVERGENCE (للكريبتو)
# ============================================================================

class OpenInterestAnalyzer:
    """
    محلل العقود المفتوحة للكريبتو
    
    التباعد (Divergence):
    - السعر يصعد + OI يتناقص = إشارة هابطة (Bearish Divergence)
    - السعر يهبط + OI يتناقص = إشارة صاعدة (Bullish Divergence)
    """
    
    @staticmethod
    def analyze_divergence(
        prices: List[float],
        open_interest: List[float],
        period: int = 14
    ) -> Dict:
        """
        تحليل التباعد بين السعر والعقود المفتوحة
        """
        if len(prices) < period or len(open_interest) < period:
            return {"divergence": None, "signal": "NEUTRAL"}
        
        # حساب اتجاه السعر
        price_change = (prices[-1] - prices[-period]) / prices[-period] * 100
        
        # حساب اتجاه OI
        oi_change = (open_interest[-1] - open_interest[-period]) / open_interest[-period] * 100
        
        # تحديد التباعد
        divergence_type = None
        signal = "NEUTRAL"
        warning = None
        
        # Bearish Divergence: سعر يصعد وOI يهبط
        if price_change > 3 and oi_change < -5:
            divergence_type = "BEARISH_DIVERGENCE"
            signal = "CAUTION"
            warning = f"⚠️ تباعد هابط: السعر +{price_change:.1f}% لكن OI {oi_change:.1f}% - المشترين يخرجون"
        
        # Bullish Divergence: سعر يهبط وOI يهبط
        elif price_change < -3 and oi_change < -5:
            divergence_type = "BULLISH_DIVERGENCE"
            signal = "OPPORTUNITY"
            warning = f"✅ تباعد صاعد: السعر {price_change:.1f}% وOI {oi_change:.1f}% - البائعين يستسلمون"
        
        # Strong Trend: سعر وOI في نفس الاتجاه
        elif price_change > 3 and oi_change > 5:
            divergence_type = "STRONG_BULLISH_TREND"
            signal = "CONFIRMED_BUY"
            warning = f"✅ اتجاه قوي مؤكد: السعر +{price_change:.1f}% وOI +{oi_change:.1f}%"
        
        elif price_change < -3 and oi_change > 5:
            divergence_type = "STRONG_BEARISH_TREND"
            signal = "CONFIRMED_SELL"
            warning = f"⚠️ اتجاه هابط قوي: السعر {price_change:.1f}% وOI +{oi_change:.1f}%"
        
        return {
            "divergence": divergence_type,
            "signal": signal,
            "price_change_percent": round(price_change, 2),
            "oi_change_percent": round(oi_change, 2),
            "warning": warning
        }


# ============================================================================
# FIBONACCI ANALYZER - مستويات فيبوناتشي
# ============================================================================

@dataclass
class FibonacciLevel:
    """مستوى فيبوناتشي"""
    level_name: str
    level_value: float
    price: float
    significance: str  # CRITICAL, IMPORTANT, MINOR
    description: str


@dataclass
class FibonacciCluster:
    """منطقة كلستر فيبوناتشي"""
    price_zone_start: float
    price_zone_end: float
    levels_converging: List[str]
    strength: str  # VERY_STRONG, STRONG, MODERATE
    confidence_boost: float
    description: str


class FibonacciAnalyzer:
    """
    محلل مستويات فيبوناتشي المتقدم
    
    النسب الذهبية:
    - 0.236 (23.6%)
    - 0.382 (38.2%)
    - 0.500 (50.0%)
    - 0.618 (61.8%) - النسبة الذهبية
    - 0.786 (78.6%)
    
    امتدادات فيبوناتشي:
    - 1.000 (100%)
    - 1.272 (127.2%)
    - 1.414 (141.4%)
    - 1.618 (161.8%) - النسبة الذهبية للامتداد
    - 2.618 (261.8%)
    """
    
    # النسب الأساسية
    RETRACEMENT_LEVELS = {
        0.236: ("23.6%", "MINOR", "تصحيح ضعيف"),
        0.382: ("38.2%", "IMPORTANT", "تصحيح متوسط"),
        0.500: ("50.0%", "IMPORTANT", "تصحيح نصف الموجة"),
        0.618: ("61.8%", "CRITICAL", "النسبة الذهبية - أقوى مستوى"),
        0.786: ("78.6%", "IMPORTANT", "تصحيح عميق")
    }
    
    EXTENSION_LEVELS = {
        1.000: ("100%", "IMPORTANT", "هدف أولي"),
        1.272: ("127.2%", "IMPORTANT", "هدف متقدم"),
        1.618: ("161.8%", "CRITICAL", "النسبة الذهبية للامتداد"),
        2.000: ("200%", "IMPORTANT", "هدف بعيد"),
        2.618: ("261.8%", "MINOR", "هدف بعيد جداً")
    }
    
    # عتبات الكلستر
    CLUSTER_THRESHOLD = 0.01  # 1% تفاوت للكلستر
    CLUSTER_MIN_LEVELS = 2    # الحد الأدنى لتقاطع المستويات
    
    def __init__(self):
        self.retracement_levels: List[FibonacciLevel] = []
        self.extension_levels: List[FibonacciLevel] = []
        self.clusters: List[FibonacciCluster] = []
    
    def calculate_retracement(
        self,
        swing_high: float,
        swing_low: float,
        current_price: Optional[float] = None
    ) -> List[FibonacciLevel]:
        """
        حساب مستويات تصحيح فيبوناتشي
        
        Args:
            swing_high: القمة (أعلى نقطة في الموجة)
            swing_low: القاع (أدنى نقطة في الموجة)
            current_price: السعر الحالي (اختياري)
        """
        self.retracement_levels = []
        
        price_range = swing_high - swing_low
        
        for level, (name, significance, desc) in self.RETRACEMENT_LEVELS.items():
            # للاتجاه الهابط: السعر يصحح من القمة
            price = swing_high - (price_range * level)
            
            fib_level = FibonacciLevel(
                level_name=f"Retracement {name}",
                level_value=level,
                price=round(price, 4),
                significance=significance,
                description=f"{desc} عند {price:.2f}"
            )
            self.retracement_levels.append(fib_level)
        
        return self.retracement_levels
    
    def calculate_extension(
        self,
        wave_start: float,
        wave_end: float,
        wave_retracement: float
    ) -> List[FibonacciLevel]:
        """
        حساب امتدادات فيبوناتشي للأهداف السعرية
        
        Args:
            wave_start: بداية الموجة (الموجة 1)
            wave_end: نهاية الموجة (قمة الموجة 1)
            wave_retracement: نقطة التصحيح (قاع الموجة 2)
        """
        self.extension_levels = []
        
        wave_length = abs(wave_end - wave_start)
        
        for level, (name, significance, desc) in self.EXTENSION_LEVELS.items():
            # الهدف = نقطة التصحيح + (طول الموجة × نسبة الامتداد)
            price = wave_retracement + (wave_length * level)
            
            fib_level = FibonacciLevel(
                level_name=f"Extension {name}",
                level_value=level,
                price=round(price, 4),
                significance=significance,
                description=f"{desc} عند {price:.2f}"
            )
            self.extension_levels.append(fib_level)
        
        return self.extension_levels
    
    def find_cluster_zones(
        self,
        retracement_levels: List[FibonacciLevel],
        extension_levels: List[FibonacciLevel]
    ) -> List[FibonacciCluster]:
        """
        البحث عن مناطق الكلستر (تقاطع المستويات)
        
        الكلستر = تقاطع مستويين أو أكثر من فيبوناتشي
        في منطقة سعرية ضيقة (أقوى إشارات الدعم/المقاومة)
        """
        self.clusters = []
        
        all_levels = retracement_levels + extension_levels
        
        for i, level1 in enumerate(all_levels):
            cluster_levels = [level1.level_name]
            cluster_prices = [level1.price]
            
            for j, level2 in enumerate(all_levels):
                if i == j:
                    continue
                
                # حساب المسافة النسبية
                avg_price = (level1.price + level2.price) / 2
                distance = abs(level1.price - level2.price) / avg_price
                
                if distance <= self.CLUSTER_THRESHOLD:
                    cluster_levels.append(level2.level_name)
                    cluster_prices.append(level2.price)
            
            # إذا وجدنا كلستر (مستويين أو أكثر)
            if len(cluster_levels) >= self.CLUSTER_MIN_LEVELS:
                zone_start = min(cluster_prices)
                zone_end = max(cluster_prices)
                
                # تحديد قوة الكلستر
                if len(cluster_levels) >= 4:
                    strength = "VERY_STRONG"
                    confidence_boost = 25.0
                elif len(cluster_levels) >= 3:
                    strength = "STRONG"
                    confidence_boost = 15.0
                else:
                    strength = "MODERATE"
                    confidence_boost = 10.0
                
                cluster = FibonacciCluster(
                    price_zone_start=zone_start,
                    price_zone_end=zone_end,
                    levels_converging=cluster_levels,
                    strength=strength,
                    confidence_boost=confidence_boost,
                    description=f"منطقة كلستر {strength}: {len(cluster_levels)} مستويات متقاطعة بين {zone_start:.2f} و{zone_end:.2f}"
                )
                self.clusters.append(cluster)
        
        # إزالة الكلسترات المكررة
        unique_clusters = []
        seen_zones = set()
        for cluster in self.clusters:
            zone_key = (round(cluster.price_zone_start, 2), round(cluster.price_zone_end, 2))
            if zone_key not in seen_zones:
                seen_zones.add(zone_key)
                unique_clusters.append(cluster)
        
        self.clusters = unique_clusters
        return self.clusters
    
    def check_price_at_golden_level(
        self,
        price: float,
        tolerance: float = 0.005
    ) -> Dict:
        """
        التحقق من وجود السعر عند مستوى ذهبي
        
        Args:
            price: السعر المراد فحصه
            tolerance: نسبة التفاوت المسموح (0.5% افتراضياً)
        """
        golden_levels = []
        
        for level in self.retracement_levels + self.extension_levels:
            distance_percent = abs(price - level.price) / level.price
            
            if distance_percent <= tolerance:
                golden_levels.append({
                    "level": level.level_name,
                    "price": level.price,
                    "distance_percent": round(distance_percent * 100, 2),
                    "significance": level.significance
                })
        
        return {
            "is_at_golden_level": len(golden_levels) > 0,
            "golden_levels": golden_levels,
            "strength": "STRONG" if len(golden_levels) >= 2 else "MODERATE" if golden_levels else "NONE"
        }
    
    def integrate_with_pattern(
        self,
        pattern_type: str,
        pattern_high: float,
        pattern_low: float,
        current_price: float
    ) -> Dict:
        """
        دمج فيبوناتشي مع النماذج السعرية
        
        المعادلات حسب نوع النموذج:
        - Head & Shoulders: الكتف الأيمن عند 61.8%
        - Triangles: امتداد 161.8% للهدف
        - Double Bottom: القاع عند 61.8% من الموجة الكبرى
        """
        result = {
            "pattern_type": pattern_type,
            "fibonacci_integration": None,
            "confidence_boost": 0,
            "signals": []
        }
        
        # حساب المستويات
        retracements = self.calculate_retracement(pattern_high, pattern_low, current_price)
        
        # فحص تقاطع السعر مع المستوى الذهبي
        golden_check = self.check_price_at_golden_level(current_price)
        
        if pattern_type == "HEAD_AND_SHOULDERS":
            # للرأس والكتفين: فحص إذا كان الكتف الأيمن عند 61.8%
            golden_618 = None
            for level in retracements:
                if level.level_value == 0.618:
                    golden_618 = level
                    break
            
            if golden_618:
                shoulder_deviation = abs(current_price - golden_618.price) / golden_618.price
                
                if shoulder_deviation <= 0.02:  # ضمن 2%
                    result["fibonacci_integration"] = {
                        "type": "GOLDEN_SHOULDER",
                        "level": golden_618.level_name,
                        "price": golden_618.price,
                        "deviation_percent": round(shoulder_deviation * 100, 2)
                    }
                    result["confidence_boost"] = 20
                    result["signals"].append("🎯 الكتف الأيمن عند النسبة الذهبية 61.8% - نموذج عالي الدقة!")
        
        elif pattern_type in ["ASCENDING_TRIANGLE", "DESCENDING_TRIANGLE", "SYMMETRICAL_TRIANGLE"]:
            # للمثلثات: حساب هدف 161.8%
            price_range = pattern_high - pattern_low
            target_1618 = current_price + (price_range * 0.618)  # للاتجاه الصاعد
            
            result["fibonacci_integration"] = {
                "type": "FIBONACCI_TARGET",
                "target_1618": round(target_1618, 2),
                "target_100": round(current_price + price_range, 2)
            }
            result["confidence_boost"] = 15
            result["signals"].append(f"🎯 هدف فيبوناتشي 161.8% عند {target_1618:.2f}")
        
        elif pattern_type in ["DOUBLE_BOTTOM", "DOUBLE_TOP"]:
            # للقمم والقيعان المزدوجة
            if golden_check["is_at_golden_level"]:
                result["fibonacci_integration"] = {
                    "type": "GOLDEN_RETRACEMENT",
                    "levels": golden_check["golden_levels"]
                }
                result["confidence_boost"] = 25
                result["signals"].append("🎯 القاع/القمة عند مستوى فيبوناتشي ذهبي!")
        
        # فحص الكلستر
        extensions = self.calculate_extension(pattern_low, pattern_high, current_price)
        clusters = self.find_cluster_zones(retracements, extensions)
        
        for cluster in clusters:
            if cluster.price_zone_start <= current_price <= cluster.price_zone_end:
                result["confidence_boost"] += cluster.confidence_boost
                result["signals"].append(f"🌟 {cluster.description}")
                break
        
        return result


# ============================================================================
# CANDLESTICK PATTERN ANALYZER - "الفلتر النهائي"
# ============================================================================
# الشموع اليابانية: تصوير سيكولوجي لعقلية التجار
# النظام يحول البرنامج من "راصد فني" إلى "نظام تداول خبير"
# ============================================================================

class CandleType(Enum):
    """أنواع الشموع"""
    # نماذج انعكاس صاعد (Bullish Reversals)
    HAMMER = "HAMMER"                      # المطرقة
    INVERTED_HAMMER = "INVERTED_HAMMER"    # المطرقة المقلوبة
    MORNING_STAR = "MORNING_STAR"          # نجمة الصباح
    PIERCING_LINE = "PIERCING_LINE"        # الخط الثاقب
    BULLISH_ENGULFING = "BULLISH_ENGULFING"  # الابتلاع الصاعد
    BULLISH_HARAMI = "BULLISH_HARAMI"      # هارامي صاعد
    THREE_WHITE_SOLDIERS = "THREE_WHITE_SOLDIERS"  # ثلاثة جنود بيض
    
    # نماذج انعكاس هابط (Bearish Reversals)
    SHOOTING_STAR = "SHOOTING_STAR"        # الشهاب
    EVENING_STAR = "EVENING_STAR"          # نجمة المساء
    DARK_CLOUD_COVER = "DARK_CLOUD_COVER"  # سحابة الظلام
    BEARISH_ENGULFING = "BEARISH_ENGULFING"  # الابتلاع الهابط
    BEARISH_HARAMI = "BEARISH_HARAMI"      # هارامي هابط
    THREE_BLACK_CROWS = "THREE_BLACK_CROWS"  # ثلاثة غربان سود
    
    # نماذج استمرار (Continuation)
    DOJI = "DOJI"                          # دوجي (تردد)
    SPINNING_TOP = "SPINNING_TOP"          # القمة المغزلية
    MARUBOZU = "MARUBOZU"                  # ماروبوزو (شمعة كاملة)


@dataclass
class CandleData:
    """بيانات شمعة واحدة"""
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    timestamp: Optional[str] = None
    
    @property
    def body(self) -> float:
        """حجم الجسم"""
        return abs(self.close - self.open)
    
    @property
    def upper_shadow(self) -> float:
        """الظل العلوي"""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_shadow(self) -> float:
        """الظل السفلي"""
        return min(self.open, self.close) - self.low
    
    @property
    def total_range(self) -> float:
        """النطاق الكلي"""
        return self.high - self.low
    
    @property
    def is_bullish(self) -> bool:
        """هل الشمعة صاعدة؟"""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """هل الشمعة هابطة؟"""
        return self.close < self.open
    
    @property
    def is_doji(self) -> bool:
        """هل شمعة دوجي؟ (فتح ≈ إغلاق)"""
        if self.total_range == 0:
            return False
        return self.body / self.total_range < 0.1
    
    @property
    def body_to_range_ratio(self) -> float:
        """نسبة الجسم للنطاق الكلي"""
        if self.total_range == 0:
            return 0
        return self.body / self.total_range


@dataclass
class CandlestickSignal:
    """إشارة شمعة يابانية"""
    pattern_type: CandleType
    pattern_name: str
    pattern_name_ar: str
    signal_direction: str  # BULLISH, BEARISH, NEUTRAL
    confidence: float
    strength: str  # STRONG, MODERATE, WEAK
    entry_price: float
    stop_loss: float
    target_price: float
    description: str
    confirmation_rules: List[str]
    filter_status: Dict[str, Any]  # حالة الفلاتر
    risk_reward_ratio: float


class CandlestickAnalyzer:
    """
    محلل الشموع اليابانية - "الفلتر النهائي"
    
    النظام يعمل بطريقة "الفلترة المزدوجة":
    1. منطقة الإشارة: Stochastics %D < 20 أو > 80
    2. التلاقي مع المستويات: فيبوناتشي 61.8% أو مناطق الكلستر
    """
    
    # ثوابت التحليل
    OVERSOLD_THRESHOLD = 20      # ذروة البيع
    OVERBOUGHT_THRESHOLD = 80    # ذروة الشراء
    BODY_MIN_RATIO = 0.3         # أقل نسبة للجسم
    SHADOW_MIN_RATIO = 2.0       # أقل نسبة للظل (ضعف الجسم)
    DOJI_BODY_RATIO = 0.1        # نسبة جسم الدوجي
    GAP_TOLERANCE = 0.002        # نسبة الفجوة المسموحة
    
    def __init__(
        self,
        fibonacci_analyzer: Optional['FibonacciAnalyzer'] = None,
        stochastic_k: Optional[float] = None,
        stochastic_d: Optional[float] = None
    ):
        """
        تهيئة المحلل
        
        Args:
            fibonacci_analyzer: محلل فيبوناتشي للفلترة
            stochastic_k: قيمة K للمؤشر Stochastic
            stochastic_d: قيمة D للمؤشر Stochastic
        """
        self.fibonacci_analyzer = fibonacci_analyzer
        self.stochastic_k = stochastic_k
        self.stochastic_d = stochastic_d
        self.signals: List[CandlestickSignal] = []
    
    def analyze_candle(
        self,
        candle: CandleData,
        prev_candle: Optional[CandleData] = None,
        prev2_candle: Optional[CandleData] = None,
        trend: str = "NEUTRAL",
        volume_avg: Optional[float] = None
    ) -> List[CandlestickSignal]:
        """
        تحليل شمعة واحدة مع السياق
        
        Args:
            candle: الشمعة الحالية
            prev_candle: الشمعة السابقة
            prev2_candle: الشمعة قبل السابقة
            trend: الاتجاه العام (UPTREND, DOWNTREND, NEUTRAL)
            volume_avg: متوسط الحجم
        """
        signals = []
        
        # تجاهل الدوجي (تردد السوق)
        if candle.is_doji:
            return self._handle_doji(candle, prev_candle)
        
        # ========== نماذج انعكاس صاعد ==========
        # تظهر في القيعان (DOWNTREND أو NEUTRAL)
        if trend in ["DOWNTREND", "NEUTRAL"]:
            # المطرقة
            hammer = self._detect_hammer(candle, trend)
            if hammer:
                signals.append(hammer)
            
            # المطرقة المقلوبة
            inverted_hammer = self._detect_inverted_hammer(candle, trend)
            if inverted_hammer:
                signals.append(inverted_hammer)
            
            # نجمة الصباح (3 شمعات)
            if prev_candle and prev2_candle:
                morning_star = self._detect_morning_star(candle, prev_candle, prev2_candle)
                if morning_star:
                    signals.append(morning_star)
            
            # الخط الثاقب (شمعتان)
            if prev_candle:
                piercing_line = self._detect_piercing_line(candle, prev_candle)
                if piercing_line:
                    signals.append(piercing_line)
                
                # الابتلاع الصاعد
                bullish_engulfing = self._detect_bullish_engulfing(candle, prev_candle)
                if bullish_engulfing:
                    signals.append(bullish_engulfing)
                
                # هارامي صاعد
                bullish_harami = self._detect_bullish_harami(candle, prev_candle)
                if bullish_harami:
                    signals.append(bullish_harami)
        
        # ========== نماذج انعكاس هابط ==========
        # تظهر في القمم (UPTREND أو NEUTRAL)
        if trend in ["UPTREND", "NEUTRAL"]:
            # الشهاب
            shooting_star = self._detect_shooting_star(candle, trend)
            if shooting_star:
                signals.append(shooting_star)
            
            # نجمة المساء (3 شمعات)
            if prev_candle and prev2_candle:
                evening_star = self._detect_evening_star(candle, prev_candle, prev2_candle)
                if evening_star:
                    signals.append(evening_star)
            
            # سحابة الظلام (شمعتان)
            if prev_candle:
                dark_cloud = self._detect_dark_cloud_cover(candle, prev_candle)
                if dark_cloud:
                    signals.append(dark_cloud)
                
                # الابتلاع الهابط
                bearish_engulfing = self._detect_bearish_engulfing(candle, prev_candle)
                if bearish_engulfing:
                    signals.append(bearish_engulfing)
                
                # هارامي هابط
                bearish_harami = self._detect_bearish_harami(candle, prev_candle)
                if bearish_harami:
                    signals.append(bearish_harami)
        
        # ========== نماذج استمرار ==========
        spinning_top = self._detect_spinning_top(candle)
        if spinning_top:
            signals.append(spinning_top)
        
        marubozu = self._detect_marubozu(candle)
        if marubozu:
            signals.append(marubozu)
        
        # تطبيق الفلترة المزدوجة على جميع الإشارات
        filtered_signals = []
        for signal in signals:
            filtered_signal = self._apply_dual_filter(signal, candle)
            if filtered_signal:
                filtered_signals.append(filtered_signal)
        
        return filtered_signals
    
    # ========== كاشفات النماذج الصاعدة ==========
    
    def _detect_hammer(self, candle: CandleData, trend: str) -> Optional[CandlestickSignal]:
        """
        كشف المطرقة (Hammer)
        
        الشروط:
        - جسم صغير في الجزء العلوي
        - ظل سفلي طويل (ضعفي الجسم على الأقل)
        - ظل علوي صغير أو معدوم
        - تظهر عند قاع الموجة
        """
        # جسم صغير
        if candle.body_to_range_ratio > 0.35:
            return None
        
        # ظل سفلي طويل
        if candle.lower_shadow < candle.body * self.SHADOW_MIN_RATIO:
            return None
        
        # ظل علوي صغير
        if candle.upper_shadow > candle.body * 0.5:
            return None
        
        # حساب المستويات
        entry = candle.close
        stop_loss = candle.low - (candle.total_range * 0.1)  # تحت الظل السفلي
        target = entry + (entry - stop_loss) * 3  # R:R = 1:3
        
        return CandlestickSignal(
            pattern_type=CandleType.HAMMER,
            pattern_name="Hammer",
            pattern_name_ar="المطرقة",
            signal_direction="BULLISH",
            confidence=75.0,
            strength="MODERATE",
            entry_price=entry,
            stop_loss=stop_loss,
            target_price=target,
            description="مطرقة: إشارة انعكاس صاعد قوية عند القاع",
            confirmation_rules=[
                "الجسم صغير في الجزء العلوي",
                f"الظل السفلي ({candle.lower_shadow:.2f}) = {candle.lower_shadow/candle.body:.1f}x الجسم",
                "الظل العلوي صغير أو معدوم"
            ],
            filter_status={},
            risk_reward_ratio=3.0
        )
    
    def _detect_inverted_hammer(self, candle: CandleData, trend: str) -> Optional[CandlestickSignal]:
        """
        كشف المطرقة المقلوبة (Inverted Hammer)
        
        الشروط:
        - جسم صغير في الجزء السفلي
        - ظل علوي طويل (ضعفي الجسم)
        - ظل سفلي صغير
        """
        if candle.body_to_range_ratio > 0.35:
            return None
        
        if candle.upper_shadow < candle.body * self.SHADOW_MIN_RATIO:
            return None
        
        if candle.lower_shadow > candle.body * 0.5:
            return None
        
        entry = candle.close
        stop_loss = candle.low - (candle.total_range * 0.1)
        target = entry + (entry - stop_loss) * 3
        
        return CandlestickSignal(
            pattern_type=CandleType.INVERTED_HAMMER,
            pattern_name="Inverted Hammer",
            pattern_name_ar="المطرقة المقلوبة",
            signal_direction="BULLISH",
            confidence=70.0,
            strength="MODERATE",
            entry_price=entry,
            stop_loss=stop_loss,
            target_price=target,
            description="مطرقة مقلوبة: إشارة انعكاس صاعد تحتاج تأكيد",
            confirmation_rules=[
                "الجسم صغير في الجزء السفلي",
                f"الظل العلوي طويل = {candle.upper_shadow/candle.body:.1f}x الجسم",
                "يحتاج تأكيد في الجلسة التالية"
            ],
            filter_status={},
            risk_reward_ratio=3.0
        )
    
    def _detect_morning_star(
        self,
        candle: CandleData,
        prev_candle: CandleData,
        prev2_candle: CandleData
    ) -> Optional[CandlestickSignal]:
        """
        كشف نجمة الصباح (Morning Star)
        
        النموذج المكون من 3 شمعات:
        1. شمعة سوداء طويلة (هبوط)
        2. شمعة صغيرة "نجمة" (تردد)
        3. شمعة بيضاء طويلة تغلق فوق منتصف الشمعة الأولى
        """
        # الشمعة الأولى: سوداء طويلة
        if not prev2_candle.is_bearish:
            return None
        if prev2_candle.body_to_range_ratio < 0.6:
            return None
        
        # الشمعة الثانية: صغيرة (نجمة)
        if prev_candle.body_to_range_ratio > 0.35:
            return None
        
        # فجوة بين الشمعة الأولى والثانية
        gap1 = abs(prev_candle.open - prev2_candle.close) / prev2_candle.close
        if gap1 < self.GAP_TOLERANCE:
            # نسمح بدون فجوة صريحة
            pass
        
        # الشمعة الثالثة: بيضاء طويلة
        if not candle.is_bullish:
            return None
        if candle.body_to_range_ratio < 0.5:
            return None
        
        # قاعدة الـ 50%: الإغلاق فوق منتصف الشمعة الأولى
        first_midpoint = (prev2_candle.open + prev2_candle.close) / 2
        if candle.close <= first_midpoint:
            return None
        
        entry = candle.close
        stop_loss = min(candle.low, prev_candle.low) - (candle.body * 0.1)
        target = entry + (entry - stop_loss) * 3
        
        return CandlestickSignal(
            pattern_type=CandleType.MORNING_STAR,
            pattern_name="Morning Star",
            pattern_name_ar="نجمة الصباح",
            signal_direction="BULLISH",
            confidence=85.0,
            strength="STRONG",
            entry_price=entry,
            stop_loss=stop_loss,
            target_price=target,
            description="نجمة الصباح: نموذج انعكاس صاعد قوي جداً (3 شمعات)",
            confirmation_rules=[
                "الشمعة الأولى سوداء طويلة",
                "الشمعة الثانية صغيرة (نجمة)",
                "الشمعة الثالثة بيضاء تغلق فوق منتصف الأولى",
                f"الإغلاق ({candle.close:.2f}) فوق منتصف الأولى ({first_midpoint:.2f})"
            ],
            filter_status={},
            risk_reward_ratio=3.0
        )
    
    def _detect_piercing_line(
        self,
        candle: CandleData,
        prev_candle: CandleData
    ) -> Optional[CandlestickSignal]:
        """
        كشف الخط الثاقب (Piercing Line)
        
        الشروط:
        1. شمعة سوداء طويلة
        2. شمعة بيضاء تفتح بفجوة لأسفل
        3. تغلق فوق منتصف جسم الشمعة السوداء (قاعدة الـ 50%)
        """
        # الشمعة السابقة: سوداء طويلة
        if not prev_candle.is_bearish:
            return None
        if prev_candle.body_to_range_ratio < 0.5:
            return None
        
        # الشمعة الحالية: بيضاء
        if not candle.is_bullish:
            return None
        
        # فجوة لأسفل (الافتتاح أقل من إغلاق السابقة)
        if candle.open >= prev_candle.close:
            # نسمح بدون فجوة صريحة
            pass
        
        # قاعدة الـ 50%: الإغلاق فوق منتصف الشمعة السابقة
        prev_midpoint = (prev_candle.open + prev_candle.close) / 2
        if candle.close <= prev_midpoint:
            return None
        
        # لكن لا يغلق فوق الافتتاح (ليس ابتلاع)
        if candle.close >= prev_candle.open:
            return None  # هذا ابتلاع، ليس خط ثاقب
        
        entry = candle.close
        stop_loss = candle.low - (candle.body * 0.1)
        target = entry + (entry - stop_loss) * 3
        
        return CandlestickSignal(
            pattern_type=CandleType.PIERCING_LINE,
            pattern_name="Piercing Line",
            pattern_name_ar="الخط الثاقب",
            signal_direction="BULLISH",
            confidence=80.0,
            strength="STRONG",
            entry_price=entry,
            stop_loss=stop_loss,
            target_price=target,
            description="الخط الثاقب: انعكاس صاعد مع اختراق منتصف الشمعة السابقة",
            confirmation_rules=[
                "الشمعة السابقة سوداء طويلة",
                "الشمعة الحالية بيضاء",
                f"الإغلاق ({candle.close:.2f}) فوق منتصف السابقة ({prev_midpoint:.2f})",
                "قاعدة الـ 50% محققة ✓"
            ],
            filter_status={},
            risk_reward_ratio=3.0
        )
    
    def _detect_bullish_engulfing(
        self,
        candle: CandleData,
        prev_candle: CandleData
    ) -> Optional[CandlestickSignal]:
        """كشف الابتلاع الصاعد (Bullish Engulfing)"""
        # الشمعة السابقة: سوداء صغيرة
        if not prev_candle.is_bearish:
            return None
        
        # الشمعة الحالية: بيضاء كبيرة تبتلع السابقة
        if not candle.is_bullish:
            return None
        
        # الابتلاع: الفتح أقل والإغلاق أعلى
        if candle.open > prev_candle.close or candle.close < prev_candle.open:
            return None
        
        entry = candle.close
        stop_loss = candle.low - (candle.body * 0.1)
        target = entry + (entry - stop_loss) * 3
        
        return CandlestickSignal(
            pattern_type=CandleType.BULLISH_ENGULFING,
            pattern_name="Bullish Engulfing",
            pattern_name_ar="الابتلاع الصاعد",
            signal_direction="BULLISH",
            confidence=82.0,
            strength="STRONG",
            entry_price=entry,
            stop_loss=stop_loss,
            target_price=target,
            description="الابتلاع الصاعد: إشارة انعكاس قوية جداً",
            confirmation_rules=[
                "شمعة سوداء صغيرة",
                "شمعة بيضاء كبيرة تبتلعها بالكامل",
                "الافتتاح أقل والإغلاق أعلى من السابقة"
            ],
            filter_status={},
            risk_reward_ratio=3.0
        )
    
    def _detect_bullish_harami(
        self,
        candle: CandleData,
        prev_candle: CandleData
    ) -> Optional[CandlestickSignal]:
        """كشف هارامي صاعد (Bullish Harami)"""
        # الشمعة السابقة: سوداء كبيرة
        if not prev_candle.is_bearish or prev_candle.body_to_range_ratio < 0.5:
            return None
        
        # الشمعة الحالية: بيضاء صغيرة داخل السابقة
        if not candle.is_bullish or candle.body_to_range_ratio > 0.35:
            return None
        
        # داخل السابقة
        if candle.open < prev_candle.close or candle.close > prev_candle.open:
            return None
        
        entry = candle.close
        stop_loss = prev_candle.low - (prev_candle.body * 0.1)
        target = entry + (entry - stop_loss) * 2.5
        
        return CandlestickSignal(
            pattern_type=CandleType.BULLISH_HARAMI,
            pattern_name="Bullish Harami",
            pattern_name_ar="هارامي صاعد",
            signal_direction="BULLISH",
            confidence=65.0,
            strength="MODERATE",
            entry_price=entry,
            stop_loss=stop_loss,
            target_price=target,
            description="هارامي صاعد: إشارة انعكاس تحتاج تأكيد",
            confirmation_rules=[
                "شمعة سوداء كبيرة",
                "شمعة بيضاء صغيرة داخلها",
                "يحتاج تأكيد في الجلسة التالية"
            ],
            filter_status={},
            risk_reward_ratio=2.5
        )
    
    # ========== كاشفات النماذج الهابطة ==========
    
    def _detect_shooting_star(self, candle: CandleData, trend: str) -> Optional[CandlestickSignal]:
        """
        كشف الشهاب (Shooting Star)
        
        الشروط:
        - جسم صغير في الجزء السفلي
        - ظل علوي طويل (ضعفي الجسم)
        - ظل سفلي صغير أو معدوم
        - تظهر عند قمة
        """
        if candle.body_to_range_ratio > 0.35:
            return None
        
        if candle.upper_shadow < candle.body * self.SHADOW_MIN_RATIO:
            return None
        
        if candle.lower_shadow > candle.body * 0.5:
            return None
        
        entry = candle.close
        stop_loss = candle.high + (candle.total_range * 0.1)
        target = entry - (stop_loss - entry) * 3
        
        return CandlestickSignal(
            pattern_type=CandleType.SHOOTING_STAR,
            pattern_name="Shooting Star",
            pattern_name_ar="الشهاب",
            signal_direction="BEARISH",
            confidence=75.0,
            strength="MODERATE",
            entry_price=entry,
            stop_loss=stop_loss,
            target_price=target,
            description="الشهاب: إشارة انعكاس هابط عند القمة",
            confirmation_rules=[
                "الجسم صغير في الجزء السفلي",
                f"الظل العلوي طويل = {candle.upper_shadow/candle.body:.1f}x الجسم",
                "الظل السفلي صغير أو معدوم"
            ],
            filter_status={},
            risk_reward_ratio=3.0
        )
    
    def _detect_evening_star(
        self,
        candle: CandleData,
        prev_candle: CandleData,
        prev2_candle: CandleData
    ) -> Optional[CandlestickSignal]:
        """
        كشف نجمة المساء (Evening Star)
        
        عكس نجمة الصباح:
        1. شمعة بيضاء طويلة
        2. شمعة صغيرة "نجمة"
        3. شمعة سوداء تغلق تحت منتصف الشمعة الأولى
        """
        # الشمعة الأولى: بيضاء طويلة
        if not prev2_candle.is_bullish:
            return None
        if prev2_candle.body_to_range_ratio < 0.6:
            return None
        
        # الشمعة الثانية: صغيرة
        if prev_candle.body_to_range_ratio > 0.35:
            return None
        
        # الشمعة الثالثة: سوداء طويلة
        if not candle.is_bearish:
            return None
        if candle.body_to_range_ratio < 0.5:
            return None
        
        # قاعدة الـ 50%: الإغلاق تحت منتصف الشمعة الأولى
        first_midpoint = (prev2_candle.open + prev2_candle.close) / 2
        if candle.close >= first_midpoint:
            return None
        
        entry = candle.close
        stop_loss = max(candle.high, prev_candle.high) + (candle.body * 0.1)
        target = entry - (stop_loss - entry) * 3
        
        return CandlestickSignal(
            pattern_type=CandleType.EVENING_STAR,
            pattern_name="Evening Star",
            pattern_name_ar="نجمة المساء",
            signal_direction="BEARISH",
            confidence=85.0,
            strength="STRONG",
            entry_price=entry,
            stop_loss=stop_loss,
            target_price=target,
            description="نجمة المساء: نموذج انعكاس هابط قوي جداً (3 شمعات)",
            confirmation_rules=[
                "الشمعة الأولى بيضاء طويلة",
                "الشمعة الثانية صغيرة (نجمة)",
                "الشمعة الثالثة سوداء تغلق تحت منتصف الأولى",
                f"الإغلاق ({candle.close:.2f}) تحت منتصف الأولى ({first_midpoint:.2f})"
            ],
            filter_status={},
            risk_reward_ratio=3.0
        )
    
    def _detect_dark_cloud_cover(
        self,
        candle: CandleData,
        prev_candle: CandleData
    ) -> Optional[CandlestickSignal]:
        """
        كشف سحابة الظلام (Dark Cloud Cover)
        
        الشروط:
        1. شمعة بيضاء طويلة
        2. شمعة سوداء تفتح بفجوة لأعلى
        3. تغلق تحت منتصف جسم الشمعة البيضاء (قاعدة الـ 50%)
        """
        # الشمعة السابقة: بيضاء طويلة
        if not prev_candle.is_bullish:
            return None
        if prev_candle.body_to_range_ratio < 0.5:
            return None
        
        # الشمعة الحالية: سوداء
        if not candle.is_bearish:
            return None
        
        # فجوة لأعلى (الافتتاح أعلى من إغلاق السابقة)
        if candle.open <= prev_candle.close:
            # نسمح بدون فجوة صريحة
            pass
        
        # قاعدة الـ 50%: الإغلاق تحت منتصف الشمعة السابقة
        prev_midpoint = (prev_candle.open + prev_candle.close) / 2
        if candle.close >= prev_midpoint:
            return None
        
        # لكن لا يغلق تحت الافتتاح (ليس ابتلاع)
        if candle.close <= prev_candle.open:
            return None  # هذا ابتلاع
        
        entry = candle.close
        stop_loss = candle.high + (candle.body * 0.1)
        target = entry - (stop_loss - entry) * 3
        
        return CandlestickSignal(
            pattern_type=CandleType.DARK_CLOUD_COVER,
            pattern_name="Dark Cloud Cover",
            pattern_name_ar="سحابة الظلام",
            signal_direction="BEARISH",
            confidence=80.0,
            strength="STRONG",
            entry_price=entry,
            stop_loss=stop_loss,
            target_price=target,
            description="سحابة الظلام: انعكاس هابط مع اختراق منتصف الشمعة السابقة",
            confirmation_rules=[
                "الشمعة السابقة بيضاء طويلة",
                "الشمعة الحالية سوداء",
                f"الإغلاق ({candle.close:.2f}) تحت منتصف السابقة ({prev_midpoint:.2f})",
                "قاعدة الـ 50% محققة ✓"
            ],
            filter_status={},
            risk_reward_ratio=3.0
        )
    
    def _detect_bearish_engulfing(
        self,
        candle: CandleData,
        prev_candle: CandleData
    ) -> Optional[CandlestickSignal]:
        """كشف الابتلاع الهابط (Bearish Engulfing)"""
        if not prev_candle.is_bullish:
            return None
        
        if not candle.is_bearish:
            return None
        
        if candle.open < prev_candle.close or candle.close > prev_candle.open:
            return None
        
        entry = candle.close
        stop_loss = candle.high + (candle.body * 0.1)
        target = entry - (stop_loss - entry) * 3
        
        return CandlestickSignal(
            pattern_type=CandleType.BEARISH_ENGULFING,
            pattern_name="Bearish Engulfing",
            pattern_name_ar="الابتلاع الهابط",
            signal_direction="BEARISH",
            confidence=82.0,
            strength="STRONG",
            entry_price=entry,
            stop_loss=stop_loss,
            target_price=target,
            description="الابتلاع الهابط: إشارة انعكاس قوية جداً",
            confirmation_rules=[
                "شمعة بيضاء صغيرة",
                "شمعة سوداء كبيرة تبتلعها بالكامل",
                "الافتتاح أعلى والإغلاق أقل من السابقة"
            ],
            filter_status={},
            risk_reward_ratio=3.0
        )
    
    def _detect_bearish_harami(
        self,
        candle: CandleData,
        prev_candle: CandleData
    ) -> Optional[CandlestickSignal]:
        """كشف هارامي هابط (Bearish Harami)"""
        if not prev_candle.is_bullish or prev_candle.body_to_range_ratio < 0.5:
            return None
        
        if not candle.is_bearish or candle.body_to_range_ratio > 0.35:
            return None
        
        if candle.open > prev_candle.close or candle.close < prev_candle.open:
            return None
        
        entry = candle.close
        stop_loss = prev_candle.high + (prev_candle.body * 0.1)
        target = entry - (stop_loss - entry) * 2.5
        
        return CandlestickSignal(
            pattern_type=CandleType.BEARISH_HARAMI,
            pattern_name="Bearish Harami",
            pattern_name_ar="هارامي هابط",
            signal_direction="BEARISH",
            confidence=65.0,
            strength="MODERATE",
            entry_price=entry,
            stop_loss=stop_loss,
            target_price=target,
            description="هارامي هابط: إشارة انعكاس تحتاج تأكيد",
            confirmation_rules=[
                "شمعة بيضاء كبيرة",
                "شمعة سوداء صغيرة داخلها",
                "يحتاج تأكيد في الجلسة التالية"
            ],
            filter_status={},
            risk_reward_ratio=2.5
        )
    
    # ========== نماذج أخرى ==========
    
    def _handle_doji(self, candle: CandleData, prev_candle: Optional[CandleData]) -> List[CandlestickSignal]:
        """
        معالجة الدوجي (تردد السوق)
        
        الدوجي يعكس تساوي قوى المشترين والبائعين
        لا نعطي إشارة اتجاهية صريحة
        """
        return [CandlestickSignal(
            pattern_type=CandleType.DOJI,
            pattern_name="Doji",
            pattern_name_ar="دوجي",
            signal_direction="NEUTRAL",
            confidence=50.0,
            strength="WEAK",
            entry_price=candle.close,
            stop_loss=candle.low - (candle.total_range * 0.1),
            target_price=candle.close,
            description="دوجي: تردد السوق - تساوي قوى المشترين والبائعين - لا إشارة اتجاهية",
            confirmation_rules=[
                "فتح ≈ إغلاق (تردد)",
                "لا إشارة صريحة",
                "انتظر الجلسة التالية للتأكيد"
            ],
            filter_status={"note": "الدوجي لا يعطي إشارة تداول"},
            risk_reward_ratio=0
        )]
    
    def _detect_spinning_top(self, candle: CandleData) -> Optional[CandlestickSignal]:
        """كشف القمة المغزلية (Spinning Top) - حيرة وتردد"""
        if candle.body_to_range_ratio > 0.35:
            return None
        
        # ظلين متقاربين
        if abs(candle.upper_shadow - candle.lower_shadow) / candle.total_range > 0.3:
            return None
        
        return CandlestickSignal(
            pattern_type=CandleType.SPINNING_TOP,
            pattern_name="Spinning Top",
            pattern_name_ar="القمة المغزلية",
            signal_direction="NEUTRAL",
            confidence=45.0,
            strength="WEAK",
            entry_price=candle.close,
            stop_loss=candle.low,
            target_price=candle.high,
            description="قمة مغزلية: حيرة وتردد - لا اتجاه واضح",
            confirmation_rules=[
                "جسم صغير",
                "ظلين متقاربين",
                "انتظر التأكيد"
            ],
            filter_status={},
            risk_reward_ratio=1.0
        )
    
    def _detect_marubozu(self, candle: CandleData) -> Optional[CandlestickSignal]:
        """كشف الماروبوزو (شمعة كاملة بدون ظلال)"""
        # لا ظلال أو ظلال صغيرة جداً
        if candle.upper_shadow > candle.body * 0.1:
            return None
        if candle.lower_shadow > candle.body * 0.1:
            return None
        
        # جسم كبير
        if candle.body_to_range_ratio < 0.9:
            return None
        
        direction = "BULLISH" if candle.is_bullish else "BEARISH"
        strength = "STRONG"
        confidence = 80.0
        
        if candle.is_bullish:
            stop_loss = candle.low
            target = candle.close + (candle.body * 2)
        else:
            stop_loss = candle.high
            target = candle.close - (candle.body * 2)
        
        return CandlestickSignal(
            pattern_type=CandleType.MARUBOZU,
            pattern_name="Marubozu",
            pattern_name_ar="ماروبوزو",
            signal_direction=direction,
            confidence=confidence,
            strength=strength,
            entry_price=candle.close,
            stop_loss=stop_loss,
            target_price=target,
            description=f"ماروبوزو {'صاعد' if candle.is_bullish else 'هابط'}: قوة اتجاهية واضحة",
            confirmation_rules=[
                "شمعة كاملة بدون ظلال",
                "قوة المشترين" if candle.is_bullish else "قوة البائعين",
                "استمرار الاتجاه متوقع"
            ],
            filter_status={},
            risk_reward_ratio=2.0
        )
    
    # ========== الفلترة المزدوجة ==========
    
    def _apply_dual_filter(
        self,
        signal: CandlestickSignal,
        candle: CandleData
    ) -> Optional[CandlestickSignal]:
        """
        تطبيق الفلترة المزدوجة
        
        1. منطقة الإشارة: Stochastics %D < 20 أو > 80
        2. التلاقي مع المستويات: فيبوناتشي 61.8% أو مناطق الكلستر
        
        إذا لم تتحقق أي فلترة، يتم تقليل الثقة بنسبة 50%
        """
        filter_results = {
            "stochastic_filter": None,
            "fibonacci_filter": None,
            "cluster_filter": None,
            "overall_filter_passed": False,
            "confidence_adjustment": 0
        }
        
        confidence_boost = 0
        filters_passed = 0
        
        # ========== الفلتر 1: Stochastics ==========
        if self.stochastic_d is not None:
            if signal.signal_direction == "BULLISH":
                # للشراء: نريد ذروة بيع (D < 20)
                if self.stochastic_d < self.OVERSOLD_THRESHOLD:
                    filter_results["stochastic_filter"] = {
                        "passed": True,
                        "reason": f"Stochastics في ذروة البيع ({self.stochastic_d:.1f} < 20)",
                        "value": self.stochastic_d
                    }
                    confidence_boost += 10
                    filters_passed += 1
                else:
                    filter_results["stochastic_filter"] = {
                        "passed": False,
                        "reason": f"Stochastics ليس في ذروة البيع ({self.stochastic_d:.1f})",
                        "value": self.stochastic_d
                    }
            
            elif signal.signal_direction == "BEARISH":
                # للبيع: نريد ذروة شراء (D > 80)
                if self.stochastic_d > self.OVERBOUGHT_THRESHOLD:
                    filter_results["stochastic_filter"] = {
                        "passed": True,
                        "reason": f"Stochastics في ذروة الشراء ({self.stochastic_d:.1f} > 80)",
                        "value": self.stochastic_d
                    }
                    confidence_boost += 10
                    filters_passed += 1
                else:
                    filter_results["stochastic_filter"] = {
                        "passed": False,
                        "reason": f"Stochastics ليس في ذروة الشراء ({self.stochastic_d:.1f})",
                        "value": self.stochastic_d
                    }
        else:
            filter_results["stochastic_filter"] = {
                "passed": None,
                "reason": "Stochastics غير متوفر",
                "value": None
            }
        
        # ========== الفلتر 2: Fibonacci ==========
        if self.fibonacci_analyzer:
            golden_check = self.fibonacci_analyzer.check_price_at_golden_level(candle.close)
            
            if golden_check["is_at_golden_level"]:
                filter_results["fibonacci_filter"] = {
                    "passed": True,
                    "reason": f"السعر عند مستوى فيبوناتشي ذهبي: {golden_check['golden_levels'][0]['level']}",
                    "levels": golden_check["golden_levels"]
                }
                confidence_boost += 15
                filters_passed += 1
            else:
                filter_results["fibonacci_filter"] = {
                    "passed": False,
                    "reason": "السعر ليس عند مستوى فيبوناتشي ذهبي",
                    "levels": []
                }
            
            # ========== الفلتر 3: Cluster Zones ==========
            if self.fibonacci_analyzer.clusters:
                in_cluster = False
                for cluster in self.fibonacci_analyzer.clusters:
                    if cluster.price_zone_start <= candle.close <= cluster.price_zone_end:
                        in_cluster = True
                        filter_results["cluster_filter"] = {
                            "passed": True,
                            "reason": cluster.description,
                            "cluster_strength": cluster.strength
                        }
                        confidence_boost += cluster.confidence_boost
                        filters_passed += 1
                        break
                
                if not in_cluster:
                    filter_results["cluster_filter"] = {
                        "passed": False,
                        "reason": "السعر ليس في منطقة كلستر",
                        "cluster_strength": None
                    }
        else:
            filter_results["fibonacci_filter"] = {
                "passed": None,
                "reason": "محلل فيبوناتشي غير متوفر",
                "levels": []
            }
            filter_results["cluster_filter"] = {
                "passed": None,
                "reason": "محلل فيبوناتشي غير متوفر",
                "cluster_strength": None
            }
        
        # ========== تقييم الفلاتر ==========
        if filters_passed >= 1:
            filter_results["overall_filter_passed"] = True
            filter_results["confidence_adjustment"] = confidence_boost
            signal.confidence = min(signal.confidence + confidence_boost, 95)
            signal.strength = "STRONG" if filters_passed >= 2 else signal.strength
        else:
            # لا فلاتر محققة - تقليل الثقة
            filter_results["overall_filter_passed"] = False
            filter_results["confidence_adjustment"] = -signal.confidence * 0.5
            signal.confidence *= 0.5
            signal.strength = "WEAK"
        
        signal.filter_status = filter_results
        return signal
    
    def analyze_candles_batch(
        self,
        candles: List[CandleData],
        trend: str = "NEUTRAL"
    ) -> List[CandlestickSignal]:
        """
        تحليل مجموعة شمعات
        
        Args:
            candles: قائمة الشمعات (من الأقدم للأحدث)
            trend: الاتجاه العام
        """
        all_signals = []
        
        for i in range(len(candles)):
            candle = candles[i]
            prev_candle = candles[i-1] if i > 0 else None
            prev2_candle = candles[i-2] if i > 1 else None
            
            signals = self.analyze_candle(
                candle=candle,
                prev_candle=prev_candle,
                prev2_candle=prev2_candle,
                trend=trend
            )
            
            for signal in signals:
                signal.filter_status["candle_index"] = i
                all_signals.append(signal)
        
        self.signals = all_signals
        return all_signals
    
    def get_best_signal(self) -> Optional[CandlestickSignal]:
        """الحصول على أفضل إشارة"""
        if not self.signals:
            return None
        
        # ترتيب حسب الثقة
        sorted_signals = sorted(
            self.signals,
            key=lambda x: x.confidence,
            reverse=True
        )
        
        # استبعاد الإشارات المحايدة
        for signal in sorted_signals:
            if signal.signal_direction != "NEUTRAL" and signal.filter_status.get("overall_filter_passed", False):
                return signal
        
        return sorted_signals[0] if sorted_signals else None
    
    def to_dict(self) -> Dict:
        """تحويل النتائج لقاموس"""
        return {
            "signals": [
                {
                    "pattern": signal.pattern_name,
                    "pattern_ar": signal.pattern_name_ar,
                    "direction": signal.signal_direction,
                    "confidence": signal.confidence,
                    "strength": signal.strength,
                    "entry": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "target": signal.target_price,
                    "description": signal.description,
                    "filter_status": signal.filter_status,
                    "risk_reward": signal.risk_reward_ratio
                }
                for signal in self.signals
            ],
            "best_signal": {
                "pattern": self.get_best_signal().pattern_name,
                "direction": self.get_best_signal().signal_direction,
                "confidence": self.get_best_signal().confidence
            } if self.get_best_signal() else None,
            "total_patterns_found": len(self.signals)
        }


# ============================================================================
# CLI INTERFACE
# ============================================================================

def print_analysis(result: UnifiedAnalysisResult):
    """Print analysis result"""
    print(f"\n{'='*70}")
    print(f" 📊 تحليل: {result.symbol} - {result.name}")
    print(f"{'='*70}")
    
    print(f"\n 💰 السعر الحالي: {result.current_price:.2f}")
    print(f" 📈 الإشارة: {result.overall_signal}")
    print(f" 🎯 الثقة: {result.confidence:.1f}%")
    print(f" ⭐ النقاط: {result.overall_score}")
    
    if result.entry_price:
        print(f"\n 🎯 الأهداف:")
        print(f"    - الدخول: {result.entry_price:.2f}")
        if result.target_price:
            print(f"    - الهدف: {result.target_price:.2f}")
        if result.stop_loss:
            print(f"    - الاستوب: {result.stop_loss:.2f}")
    
    if result.buy_reasons:
        print(f"\n 🟢 أسباب الشراء:")
        for reason in result.buy_reasons:
            print(f"    + {reason}")
    
    if result.sell_reasons:
        print(f"\n 🔴 أسباب البيع:")
        for reason in result.sell_reasons:
            print(f"    - {reason}")
    
    if result.warnings:
        print(f"\n ⚠️ تحذيرات:")
        for warning in result.warnings:
            print(f"    ! {warning}")
    
    if result.technical:
        tech = result.technical
        print(f"\n 📉 المؤشرات الفنية:")
        if tech.rsi:
            print(f"    RSI: {tech.rsi:.1f} ({tech.rsi_signal})")
        if tech.macd_trend:
            print(f"    MACD: {tech.macd_trend}")
        if tech.sma_20 and tech.sma_50:
            print(f"    SMA20: {tech.sma_20:.2f} | SMA50: {tech.sma_50:.2f}")
    
    if result.timing:
        print(f"\n ⏰ التوقيت:")
        print(f"    الجلسة: {result.timing.current_session}")
        print(f"    التوصية: {result.timing.timing_recommendation}")
    
    print(f"\n{'='*70}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="نظام التحليل المالي الموحد")
    parser.add_argument("--symbol", type=str, help="رمز السهم")
    parser.add_argument("--type", type=str, default="STOCK", help="نوع الأصل (STOCK/CRYPTO)")
    parser.add_argument("--top", type=int, help="أفضل التوصيات")
    parser.add_argument("--filter", type=str, help="فلترة (buy/sell)")
    
    args = parser.parse_args()
    
    # Find database
    db_paths = [
        '/root/egxpy_service/data/egx_investment.db',
        'db/egx_investment.db',
        '../db/egx_investment.db'
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    analyzer = UnifiedAnalyzer(db_path)
    
    try:
        if args.symbol:
            result = analyzer.analyze(args.symbol, args.type)
            if result:
                print_analysis(result)
            else:
                print(f"لم يتم العثور على السهم {args.symbol}")
        
        elif args.top:
            print(f"\n{'='*70}")
            print(f" 🏆 أفضل {args.top} توصيات")
            print(f"{'='*70}")
            
            results = analyzer.get_top_recommendations(args.top, args.filter)
            
            for i, result in enumerate(results, 1):
                signal_emoji = "🟢" if "BUY" in result.overall_signal else "🔴" if "SELL" in result.overall_signal else "🟡"
                print(f"\n{i}. {result.symbol} - {result.name}")
                print(f"   السعر: {result.current_price:.2f} | {signal_emoji} {result.overall_signal} | الثقة: {result.confidence:.1f}%")
                if result.buy_reasons:
                    print(f"   الأسباب: {', '.join(result.buy_reasons[:2])}")
        
        else:
            parser.print_help()
    
    finally:
        analyzer.close()

if __name__ == "__main__":
    main()
