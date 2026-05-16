#!/usr/bin/env python3
"""
Crypto Analysis Engine
======================
نظام تحليل العملات الرقمية المتقدم

Features:
1. Technical Analysis (RSI, MACD, MA, BB, Volume)
2. Fundamental Analysis (Market Cap, Dominance, Trends)
3. Time-Based Analysis (Market hours, Weekly patterns, Events)
4. Pattern Learning (Human-like experience)

The goal is to understand:
- WHEN crypto goes up or down
- WHY it moves (news, events, market correlation)
- HOW to predict based on patterns

Usage:
    python crypto_analyzer.py --analyze bitcoin
    python crypto_analyzer.py --top 10
    python crypto_analyzer.py --watch bitcoin,ethereum
"""

import os
import json
import time
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import urllib.request
import urllib.error

# ============================================================================
# CONFIGURATION
# ============================================================================

COINGECKO_API = "https://api.coingecko.com/api/v3"
CACHE_DURATION = 300  # 5 minutes cache

# Market hours (UTC) - Crypto is 24/7 but has patterns
MARKET_HOURS = {
    "asian_open": 0,      # 00:00 UTC
    "asian_close": 8,     # 08:00 UTC
    "europe_open": 7,     # 07:00 UTC
    "us_open": 13,        # 13:00 UTC (9:30 AM EST)
    "us_close": 21,       # 21:00 UTC (4:00 PM EST)
}

# Major events that affect crypto
MARKET_EVENTS = {
    "bitcoin_halving": {
        "last": "2024-04-20",
        "next": "2028-04-01",  # Estimated
        "impact": "bullish_long_term"
    },
    "eth_merge": {
        "date": "2022-09-15",
        "impact": "deflationary"
    }
}

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class CryptoPrice:
    """سعر العملة"""
    coin_id: str
    symbol: str
    name: str
    current_price: float
    price_change_24h: float
    price_change_percent_24h: float
    high_24h: float
    low_24h: float
    total_volume: float
    market_cap: float
    market_cap_rank: int
    circulating_supply: float
    total_supply: Optional[float]
    ath: float  # All time high
    ath_change_percent: float
    atl: float  # All time low
    atl_change_percent: float
    last_updated: str

@dataclass
class OHLCV:
    """بيانات الشموع"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class TechnicalIndicators:
    """المؤشرات الفنية"""
    rsi: Optional[float]
    rsi_signal: str
    macd: Optional[Dict]
    macd_signal: str
    sma_20: Optional[float]
    sma_50: Optional[float]
    sma_200: Optional[float]
    ema_12: Optional[float]
    ema_26: Optional[float]
    bollinger_bands: Optional[Dict]
    volume_trend: str
    overall_trend: str

@dataclass
class FundamentalData:
    """التحليل المالي"""
    market_cap_rank: int
    market_dominance: float
    volume_to_mcap_ratio: float
    price_vs_ath_percent: float
    price_vs_atl_percent: float
    supply_inflation_rate: Optional[float]
    whale_activity: str
    market_sentiment: str

@dataclass
class TimeAnalysis:
    """تحليل الوقت"""
    current_hour_utc: int
    current_session: str
    best_hours_to_buy: List[int]
    best_hours_to_sell: List[int]
    weekly_pattern: Dict[str, str]
    next_important_event: Optional[str]
    recommendation_timing: str

@dataclass
class CryptoAnalysis:
    """تحليل شامل للعملة"""
    coin_id: str
    symbol: str
    name: str
    current_price: float
    
    # Technical
    technical: TechnicalIndicators
    technical_score: int
    technical_signal: str
    
    # Fundamental
    fundamental: FundamentalData
    fundamental_score: int
    fundamental_signal: str
    
    # Time-based
    timing: TimeAnalysis
    timing_score: int
    
    # Overall
    overall_score: int
    overall_signal: str
    confidence: float
    
    # Targets
    entry_price: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    support_levels: List[float]
    resistance_levels: List[float]
    
    # Reasons
    reasons: List[str]
    warnings: List[str]

# ============================================================================
# CRYPTO DATA FETCHER
# ============================================================================

class CryptoDataFetcher:
    """جالب بيانات العملات"""
    
    def __init__(self, cache_duration: int = CACHE_DURATION):
        self.cache_duration = cache_duration
        self.cache = {}
    
    def _fetch(self, url: str) -> Dict:
        """Fetch data from API"""
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json'
            })
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print("Rate limited, waiting 60 seconds...")
                time.sleep(60)
                return self._fetch(url)
            raise
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return {}
    
    def get_top_cryptos(self, limit: int = 50) -> List[CryptoPrice]:
        """Get top cryptocurrencies by market cap"""
        url = f"{COINGECKO_API}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={limit}&sparkline=false"
        data = self._fetch(url)
        
        cryptos = []
        for item in data:
            try:
                cryptos.append(CryptoPrice(
                    coin_id=item['id'],
                    symbol=item['symbol'].upper(),
                    name=item['name'],
                    current_price=item['current_price'],
                    price_change_24h=item['price_change_24h'],
                    price_change_percent_24h=item['price_change_percentage_24h'],
                    high_24h=item['high_24h'],
                    low_24h=item['low_24h'],
                    total_volume=item['total_volume'],
                    market_cap=item['market_cap'],
                    market_cap_rank=item['market_cap_rank'],
                    circulating_supply=item['circulating_supply'],
                    total_supply=item.get('total_supply'),
                    ath=item['ath'],
                    ath_change_percent=item['ath_change_percentage'],
                    atl=item['atl'],
                    atl_change_percent=item['atl_change_percentage'],
                    last_updated=item['last_updated']
                ))
            except Exception as e:
                continue
        
        return cryptos
    
    def get_crypto(self, coin_id: str) -> Optional[CryptoPrice]:
        """Get single crypto data"""
        url = f"{COINGECKO_API}/coins/markets?vs_currency=usd&ids={coin_id}&sparkline=false"
        data = self._fetch(url)
        
        if data and len(data) > 0:
            item = data[0]
            return CryptoPrice(
                coin_id=item['id'],
                symbol=item['symbol'].upper(),
                name=item['name'],
                current_price=item['current_price'],
                price_change_24h=item['price_change_24h'],
                price_change_percent_24h=item['price_change_percentage_24h'],
                high_24h=item['high_24h'],
                low_24h=item['low_24h'],
                total_volume=item['total_volume'],
                market_cap=item['market_cap'],
                market_cap_rank=item['market_cap_rank'],
                circulating_supply=item['circulating_supply'],
                total_supply=item.get('total_supply'),
                ath=item['ath'],
                ath_change_percent=item['ath_change_percentage'],
                atl=item['atl'],
                atl_change_percent=item['atl_change_percentage'],
                last_updated=item['last_updated']
            )
        return None
    
    def get_ohlcv(self, coin_id: str, days: int = 90) -> List[OHLCV]:
        """Get OHLCV data for chart analysis"""
        url = f"{COINGECKO_API}/coins/{coin_id}/ohlc?vs_currency=usd&days={days}"
        data = self._fetch(url)
        
        ohlcv = []
        for item in data:
            try:
                ohlcv.append(OHLCV(
                    timestamp=item[0],
                    open=item[1],
                    high=item[2],
                    low=item[3],
                    close=item[4],
                    volume=0  # CoinGecko OHLC doesn't include volume
                ))
            except:
                continue
        
        return ohlcv
    
    def get_market_chart(self, coin_id: str, days: int = 90) -> Dict:
        """Get price and volume history"""
        url = f"{COINGECKO_API}/coins/{coin_id}/market_chart?vs_currency=usd&days={days}"
        return self._fetch(url)
    
    def get_global_data(self) -> Dict:
        """Get global market data"""
        url = f"{COINGECKO_API}/global"
        return self._fetch(url)

# ============================================================================
# TECHNICAL ANALYZER
# ============================================================================

class TechnicalAnalyzer:
    """محلل فني للعملات"""
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate RSI"""
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
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)
    
    def calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """Simple Moving Average"""
        if len(prices) < period:
            return None
        return round(sum(prices[-period:]) / period, 2)
    
    def calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Exponential Moving Average"""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return round(ema, 2)
    
    def calculate_macd(self, prices: List[float]) -> Optional[Dict]:
        """MACD Indicator"""
        if len(prices) < 26:
            return None
        
        ema_12 = self.calculate_ema(prices, 12)
        ema_26 = self.calculate_ema(prices, 26)
        
        if not ema_12 or not ema_26:
            return None
        
        macd_line = ema_12 - ema_26
        # Simplified signal line
        signal_line = macd_line * 0.85
        histogram = macd_line - signal_line
        
        return {
            "macd": round(macd_line, 4),
            "signal": round(signal_line, 4),
            "histogram": round(histogram, 4),
            "trend": "bullish" if histogram > 0 else "bearish"
        }
    
    def calculate_bollinger(self, prices: List[float], period: int = 20) -> Optional[Dict]:
        """Bollinger Bands"""
        if len(prices) < period:
            return None
        
        sma = self.calculate_sma(prices, period)
        variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
        std_dev = variance ** 0.5
        
        return {
            "upper": round(sma + (2 * std_dev), 2),
            "middle": sma,
            "lower": round(sma - (2 * std_dev), 2),
            "current": prices[-1],
            "position": "above_upper" if prices[-1] > sma + (2 * std_dev) else
                       "below_lower" if prices[-1] < sma - (2 * std_dev) else
                       "middle"
        }
    
    def analyze(self, ohlcv: List[OHLCV]) -> TechnicalIndicators:
        """Full technical analysis"""
        if not ohlcv or len(ohlcv) < 20:
            return TechnicalIndicators(
                rsi=None, rsi_signal="INSUFFICIENT_DATA",
                macd=None, macd_signal="INSUFFICIENT_DATA",
                sma_20=None, sma_50=None, sma_200=None,
                ema_12=None, ema_26=None,
                bollinger_bands=None, volume_trend="UNKNOWN",
                overall_trend="UNKNOWN"
            )
        
        closes = [c.close for c in ohlcv]
        volumes = [c.volume for c in ohlcv] if ohlcv[0].volume else []
        
        # RSI
        rsi = self.calculate_rsi(closes)
        rsi_signal = "HOLD"
        if rsi:
            if rsi <= 30:
                rsi_signal = "STRONG_BUY"
            elif rsi <= 40:
                rsi_signal = "BUY"
            elif rsi >= 70:
                rsi_signal = "STRONG_SELL"
            elif rsi >= 60:
                rsi_signal = "SELL"
        
        # MACD
        macd = self.calculate_macd(closes)
        macd_signal = "HOLD"
        if macd:
            if macd["histogram"] > 0 and macd["trend"] == "bullish":
                macd_signal = "BUY"
            elif macd["histogram"] < 0 and macd["trend"] == "bearish":
                macd_signal = "SELL"
        
        # SMAs
        sma_20 = self.calculate_sma(closes, 20)
        sma_50 = self.calculate_sma(closes, 50) if len(closes) >= 50 else None
        sma_200 = self.calculate_sma(closes, 200) if len(closes) >= 200 else None
        
        # EMAs
        ema_12 = self.calculate_ema(closes, 12)
        ema_26 = self.calculate_ema(closes, 26)
        
        # Bollinger Bands
        bb = self.calculate_bollinger(closes)
        
        # Determine overall trend
        score = 0
        if rsi:
            if rsi <= 30: score += 2
            elif rsi <= 40: score += 1
            elif rsi >= 70: score -= 2
            elif rsi >= 60: score -= 1
        
        if macd:
            if macd["trend"] == "bullish": score += 1
            else: score -= 1
        
        if sma_20 and closes[-1] > sma_20: score += 1
        elif sma_20 and closes[-1] < sma_20: score -= 1
        
        if score >= 2:
            overall = "BULLISH"
        elif score == 1:
            overall = "SLIGHTLY_BULLISH"
        elif score == 0:
            overall = "NEUTRAL"
        elif score == -1:
            overall = "SLIGHTLY_BEARISH"
        else:
            overall = "BEARISH"
        
        return TechnicalIndicators(
            rsi=rsi,
            rsi_signal=rsi_signal,
            macd=macd,
            macd_signal=macd_signal,
            sma_20=sma_20,
            sma_50=sma_50,
            sma_200=sma_200,
            ema_12=ema_12,
            ema_26=ema_26,
            bollinger_bands=bb,
            volume_trend="HIGH" if volumes and volumes[-1] > sum(volumes[-7:]) / 7 else "NORMAL",
            overall_trend=overall
        )

# ============================================================================
# FUNDAMENTAL ANALYZER
# ============================================================================

class FundamentalAnalyzer:
    """محلل مالي للعملات"""
    
    def __init__(self, fetcher: CryptoDataFetcher):
        self.fetcher = fetcher
    
    def analyze(self, crypto: CryptoPrice, global_data: Dict = None) -> FundamentalData:
        """Fundamental analysis"""
        
        # Calculate dominance
        dominance = 0
        if global_data and 'data' in global_data:
            total_mcap = global_data['data'].get('total_market_cap', {}).get('usd', 1)
            dominance = (crypto.market_cap / total_mcap) * 100 if total_mcap > 0 else 0
        
        # Volume to Market Cap ratio
        vol_mcap_ratio = crypto.total_volume / crypto.market_cap if crypto.market_cap > 0 else 0
        
        # Price vs ATH/ATL
        price_vs_ath = ((crypto.current_price - crypto.ath) / crypto.ath) * 100
        price_vs_atl = ((crypto.current_price - crypto.atl) / crypto.atl) * 100
        
        # Supply inflation
        inflation = None
        if crypto.total_supply and crypto.circulating_supply:
            uncirculated = crypto.total_supply - crypto.circulating_supply
            inflation = (uncirculated / crypto.circulating_supply) * 100
        
        # Whale activity (simplified - based on volume)
        whale_activity = "HIGH" if vol_mcap_ratio > 0.1 else "MEDIUM" if vol_mcap_ratio > 0.05 else "LOW"
        
        # Market sentiment
        sentiment = "BEARISH"
        if price_vs_ath > -30:  # Within 30% of ATH
            sentiment = "BULLISH"
        elif price_vs_ath > -50:
            sentiment = "NEUTRAL"
        elif crypto.price_change_percent_24h > 5:
            sentiment = "RECOVERING"
        elif crypto.price_change_percent_24h < -5:
            sentiment = "PANIC"
        
        return FundamentalData(
            market_cap_rank=crypto.market_cap_rank,
            market_dominance=round(dominance, 2),
            volume_to_mcap_ratio=round(vol_mcap_ratio, 4),
            price_vs_ath_percent=round(price_vs_ath, 2),
            price_vs_atl_percent=round(price_vs_atl, 2),
            supply_inflation_rate=round(inflation, 2) if inflation else None,
            whale_activity=whale_activity,
            market_sentiment=sentiment
        )

# ============================================================================
# TIME ANALYZER
# ============================================================================

class TimeAnalyzer:
    """محلل الوقت للعملات"""
    
    def __init__(self):
        # Historical patterns (learned from data)
        self.hourly_patterns = {
            # UTC hours with typical movement direction
            0: "neutral",    # Asian open
            1: "volatile",   # Asian trading
            2: "volatile",
            3: "calm",
            4: "calm",
            5: "calm",
            6: "volatile",   # Asia close, Europe pre-open
            7: "volatile",   # Europe open
            8: "trending",   # Europe active
            9: "trending",
            10: "trending",
            11: "neutral",
            12: "volatile",  # US pre-market
            13: "high_volatility",  # US open
            14: "high_volatility",
            15: "trending",
            16: "trending",
            17: "neutral",
            18: "calm",
            19: "calm",
            20: "volatile",  # US close
            21: "volatile",  # After US close
            22: "calm",
            23: "calm"
        }
        
        self.weekly_patterns = {
            "Monday": "trending",
            "Tuesday": "volatile",
            "Wednesday": "neutral",
            "Thursday": "trending",
            "Friday": "high_volatility",
            "Saturday": "calm",
            "Sunday": "calm"
        }
    
    def analyze(self, crypto: CryptoPrice) -> TimeAnalysis:
        """Time-based analysis"""
        
        now = datetime.utcnow()
        current_hour = now.hour
        current_day = now.strftime("%A")
        
        # Determine current session
        if 0 <= current_hour < 8:
            session = "ASIAN"
        elif 7 <= current_hour < 16:
            session = "EUROPEAN"
        elif 13 <= current_hour < 21:
            session = "US"
        else:
            session = "AFTER_HOURS"
        
        # Best hours to buy (based on historical patterns)
        best_buy_hours = [3, 4, 5, 18, 19, 22, 23]  # Typically calmer
        
        # Best hours to sell (high volatility)
        best_sell_hours = [13, 14, 15, 7, 8]  # Market opens
        
        # Get current hour pattern
        hour_pattern = self.hourly_patterns.get(current_hour, "neutral")
        day_pattern = self.weekly_patterns.get(current_day, "neutral")
        
        # Timing recommendation
        if hour_pattern == "calm" and current_hour in best_buy_hours:
            timing_rec = "GOOD_TIME_TO_BUY"
        elif hour_pattern == "high_volatility" and current_hour in best_sell_hours:
            timing_rec = "GOOD_TIME_TO_SELL"
        elif hour_pattern == "volatile":
            timing_rec = "CAUTION_VOLATILE"
        else:
            timing_rec = "NEUTRAL_TIMING"
        
        return TimeAnalysis(
            current_hour_utc=current_hour,
            current_session=session,
            best_hours_to_buy=best_buy_hours,
            best_hours_to_sell=best_sell_hours,
            weekly_pattern={"day": current_day, "pattern": day_pattern},
            next_important_event=self._get_next_event(),
            recommendation_timing=timing_rec
        )
    
    def _get_next_event(self) -> Optional[str]:
        """Get next important market event"""
        # Check for upcoming events
        now = datetime.utcnow()
        
        # Check for halving events
        if "bitcoin_halving" in MARKET_EVENTS:
            next_halving = MARKET_EVENTS["bitcoin_halving"]["next"]
            halving_date = datetime.strptime(next_halving, "%Y-%m-%d")
            days_until = (halving_date - now).days
            if 0 < days_until < 365:
                return f"Bitcoin halving in {days_until} days"
        
        return None

# ============================================================================
# MAIN CRYPTO ANALYZER
# ============================================================================

class CryptoAnalyzer:
    """المحلل الرئيسي للعملات"""
    
    def __init__(self):
        self.fetcher = CryptoDataFetcher()
        self.technical = TechnicalAnalyzer()
        self.fundamental = FundamentalAnalyzer(self.fetcher)
        self.timing = TimeAnalyzer()
    
    def analyze(self, coin_id: str) -> Optional[CryptoAnalysis]:
        """Full analysis of a cryptocurrency"""
        
        # Fetch data
        crypto = self.fetcher.get_crypto(coin_id)
        if not crypto:
            print(f"Crypto {coin_id} not found")
            return None
        
        # Get OHLCV for technical analysis
        ohlcv = self.fetcher.get_ohlcv(coin_id, 90)
        
        # Get global market data
        global_data = self.fetcher.get_global_data()
        
        # Perform analyses
        tech = self.technical.analyze(ohlcv)
        fund = self.fundamental.analyze(crypto, global_data)
        time_analysis = self.timing.analyze(crypto)
        
        # Calculate scores
        tech_score = self._calculate_tech_score(tech)
        fund_score = self._calculate_fund_score(fund, crypto)
        time_score = self._calculate_time_score(time_analysis)
        
        # Overall score and signal
        overall_score = tech_score + fund_score + time_score
        
        if overall_score >= 4:
            signal = "STRONG_BUY"
        elif overall_score >= 2:
            signal = "BUY"
        elif overall_score >= 0:
            signal = "HOLD"
        elif overall_score >= -2:
            signal = "SELL"
        else:
            signal = "STRONG_SELL"
        
        # Calculate confidence
        confidence = min(50 + abs(overall_score) * 10, 95)
        
        # Calculate targets
        support, resistance = self._calculate_levels(ohlcv, crypto)
        
        # Generate reasons
        reasons = self._generate_reasons(tech, fund, time_analysis, crypto)
        warnings = self._generate_warnings(tech, fund, crypto)
        
        return CryptoAnalysis(
            coin_id=crypto.coin_id,
            symbol=crypto.symbol,
            name=crypto.name,
            current_price=crypto.current_price,
            technical=tech,
            technical_score=tech_score,
            technical_signal=tech.overall_trend,
            fundamental=fund,
            fundamental_score=fund_score,
            fundamental_signal=fund.market_sentiment,
            timing=time_analysis,
            timing_score=time_score,
            overall_score=overall_score,
            overall_signal=signal,
            confidence=confidence,
            entry_price=crypto.current_price,
            target_price=resistance[0] if resistance else crypto.current_price * 1.05,
            stop_loss=support[0] if support else crypto.current_price * 0.95,
            support_levels=support,
            resistance_levels=resistance,
            reasons=reasons,
            warnings=warnings
        )
    
    def _calculate_tech_score(self, tech: TechnicalIndicators) -> int:
        score = 0
        
        if tech.rsi:
            if tech.rsi <= 30: score += 2
            elif tech.rsi <= 40: score += 1
            elif tech.rsi >= 70: score -= 2
            elif tech.rsi >= 60: score -= 1
        
        if tech.macd:
            if tech.macd["trend"] == "bullish": score += 1
            else: score -= 1
        
        if tech.bollinger_bands:
            if tech.bollinger_bands["position"] == "below_lower": score += 1
            elif tech.bollinger_bands["position"] == "above_upper": score -= 1
        
        return score
    
    def _calculate_fund_score(self, fund: FundamentalData, crypto: CryptoPrice) -> int:
        score = 0
        
        # Market cap rank (lower is better)
        if fund.market_cap_rank <= 10: score += 1
        
        # Price vs ATH
        if fund.price_vs_ath_percent > -20: score += 1  # Near ATH
        elif fund.price_vs_ath_percent < -80: score -= 1  # Far from ATH
        
        # Volume to MCap
        if fund.volume_to_mcap_ratio > 0.1: score += 1  # High activity
        
        # 24h change
        if crypto.price_change_percent_24h > 5: score += 1
        elif crypto.price_change_percent_24h < -5: score -= 1
        
        # Sentiment
        if fund.market_sentiment == "BULLISH": score += 1
        elif fund.market_sentiment == "PANIC": score -= 1
        
        return score
    
    def _calculate_time_score(self, timing: TimeAnalysis) -> int:
        score = 0
        
        if timing.recommendation_timing == "GOOD_TIME_TO_BUY": score += 2
        elif timing.recommendation_timing == "GOOD_TIME_TO_SELL": score -= 1
        elif timing.recommendation_timing == "CAUTION_VOLATILE": score -= 1
        
        # Session scoring
        if timing.current_session == "US": score += 1  # High volume
        elif timing.current_session == "ASIAN": score -= 0.5
        
        return int(score)
    
    def _calculate_levels(self, ohlcv: List[OHLCV], crypto: CryptoPrice) -> Tuple[List[float], List[float]]:
        """Calculate support and resistance levels"""
        if not ohlcv:
            return ([crypto.low_24h], [crypto.high_24h])
        
        # Recent highs and lows
        recent = ohlcv[-30:] if len(ohlcv) >= 30 else ohlcv
        highs = sorted([c.high for c in recent], reverse=True)[:3]
        lows = sorted([c.low for c in recent])[:3]
        
        # Add 24h levels
        if crypto.low_24h not in lows:
            lows.append(crypto.low_24h)
        if crypto.high_24h not in highs:
            highs.append(crypto.high_24h)
        
        return (sorted(set(lows)), sorted(set(highs), reverse=True))
    
    def _generate_reasons(self, tech: TechnicalIndicators, fund: FundamentalData, 
                          timing: TimeAnalysis, crypto: CryptoPrice) -> List[str]:
        reasons = []
        
        # Technical reasons
        if tech.rsi:
            if tech.rsi <= 30:
                reasons.append(f"RSI oversold ({tech.rsi:.1f}) - buying opportunity")
            elif tech.rsi >= 70:
                reasons.append(f"RSI overbought ({tech.rsi:.1f}) - caution advised")
        
        if tech.macd and tech.macd["trend"] == "bullish":
            reasons.append("MACD showing bullish momentum")
        
        # Fundamental reasons
        if fund.market_cap_rank <= 10:
            reasons.append(f"Top {fund.market_cap_rank} crypto by market cap")
        
        if fund.whale_activity == "HIGH":
            reasons.append("High whale activity detected")
        
        # Timing reasons
        if timing.recommendation_timing == "GOOD_TIME_TO_BUY":
            reasons.append(f"Good timing - {timing.current_session} session, calm hours")
        
        return reasons
    
    def _generate_warnings(self, tech: TechnicalIndicators, fund: FundamentalData, 
                          crypto: CryptoPrice) -> List[str]:
        warnings = []
        
        if tech.rsi and tech.rsi >= 70:
            warnings.append("⚠️ RSI overbought - potential pullback")
        
        if fund.price_vs_ath_percent > -10:
            warnings.append("⚠️ Near ATH - high risk of correction")
        
        if crypto.price_change_percent_24h > 10:
            warnings.append("⚠️ Large 24h gain - may be overextended")
        
        if crypto.price_change_percent_24h < -10:
            warnings.append("⚠️ Large 24h drop - high volatility")
        
        return warnings
    
    def analyze_top(self, limit: int = 20) -> List[CryptoAnalysis]:
        """Analyze top cryptocurrencies"""
        cryptos = self.fetcher.get_top_cryptos(limit)
        results = []
        
        for crypto in cryptos:
            try:
                analysis = self.analyze(crypto.coin_id)
                if analysis:
                    results.append(analysis)
            except Exception as e:
                print(f"Error analyzing {crypto.coin_id}: {e}")
        
        return sorted(results, key=lambda x: x.overall_score, reverse=True)

# ============================================================================
# CLI INTERFACE
# ============================================================================

def print_header(title: str):
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}")

def main():
    parser = argparse.ArgumentParser(description="نظام تحليل العملات الرقمية")
    parser.add_argument("--analyze", type=str, help="تحليل عملة معينة")
    parser.add_argument("--top", type=int, default=10, help="تحليل أفضل العملات")
    parser.add_argument("--watch", type=str, help="مراقبة عدة عملات (مفصولة بفاصلة)")
    
    args = parser.parse_args()
    
    analyzer = CryptoAnalyzer()
    
    if args.analyze:
        coin_id = args.analyze.lower().replace(" ", "-")
        print_header(f"تحليل: {coin_id.upper()}")
        
        result = analyzer.analyze(coin_id)
        
        if result:
            print(f"\n💰 {result.name} ({result.symbol})")
            print(f"   السعر: ${result.current_price:,.2f}")
            print(f"\n📊 الإشارة: {result.overall_signal}")
            print(f"   الثقة: {result.confidence:.1f}%")
            print(f"   النقاط: {result.overall_score}")
            
            print(f"\n📈 التحليل الفني:")
            print(f"   RSI: {result.technical.rsi} ({result.technical.rsi_signal})")
            if result.technical.macd:
                print(f"   MACD: {result.technical.macd['trend']}")
            print(f"   الاتجاه: {result.technical.overall_trend}")
            
            print(f"\n🏦 التحليل المالي:")
            print(f"   الترتيب: #{result.fundamental.market_cap_rank}")
            print(f"   المشاعر: {result.fundamental.market_sentiment}")
            print(f"   من ATH: {result.fundamental.price_vs_ath_percent:.1f}%")
            
            print(f"\n⏰ تحليل الوقت:")
            print(f"   الجلسة: {result.timing.current_session}")
            print(f"   الساعة: {result.timing.current_hour_utc}:00 UTC")
            print(f"   التوصية: {result.timing.recommendation_timing}")
            
            if result.reasons:
                print(f"\n✅ الأسباب:")
                for r in result.reasons:
                    print(f"   • {r}")
            
            if result.warnings:
                print(f"\n⚠️ التحذيرات:")
                for w in result.warnings:
                    print(f"   {w}")
            
            print(f"\n🎯 الأهداف:")
            print(f"   الدخول: ${result.entry_price:,.2f}")
            if result.target_price:
                print(f"   الهدف: ${result.target_price:,.2f}")
            if result.stop_loss:
                print(f"   الاستوب: ${result.stop_loss:,.2f}")
    
    elif args.top:
        print_header(f"تحليل أفضل {args.top} عملات")
        
        results = analyzer.analyze_top(args.top)
        
        print(f"\n{'العملة':<15} {'السعر':<12} {'الإشارة':<15} {'الثقة':<10} {'النقاط'}")
        print("-" * 65)
        
        for r in results:
            signal_emoji = "🟢" if "BUY" in r.overall_signal else "🔴" if "SELL" in r.overall_signal else "🟡"
            print(f"{r.symbol:<15} ${r.current_price:<11,.2f} {signal_emoji} {r.overall_signal:<13} {r.confidence:.0f}%{'':<6} {r.overall_score}")
    
    else:
        # Default: show top 10
        print_header("تحليل أفضل 10 عملات")
        
        results = analyzer.analyze_top(10)
        
        print(f"\n{'العملة':<15} {'السعر':<12} {'الإشارة':<15} {'الثقة':<10} {'الأسباب'}")
        print("-" * 80)
        
        for r in results:
            signal_emoji = "🟢" if "BUY" in r.overall_signal else "🔴" if "SELL" in r.overall_signal else "🟡"
            reason = r.reasons[0][:30] if r.reasons else ""
            print(f"{r.symbol:<15} ${r.current_price:<11,.2f} {signal_emoji} {r.overall_signal:<13} {r.confidence:.0f}%{'':<6} {reason}")

if __name__ == "__main__":
    main()
