"""
Technical Analysis - التحليل الفني باستخدام pandas و numpy
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, List
from loguru import logger


class TechnicalIndicators:
    """
    حساب المؤشرات الفنية
    باستخدام pandas و numpy فقط (بدون مكتبات خارجية)
    """
    
    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index - مؤشر القوة النسبية
        """
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD - Moving Average Convergence Divergence
        Returns: (macd_line, signal_line, histogram)
        """
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Bollinger Bands - نطاقات بولينجر
        Returns: (upper, middle, lower)
        """
        middle = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower
    
    @staticmethod
    def moving_averages(close: pd.Series) -> Dict[str, pd.Series]:
        """
        Moving Averages - المتوسطات المتحركة
        """
        return {
            'sma_20': close.rolling(window=20).mean(),
            'sma_50': close.rolling(window=50).mean(),
            'sma_200': close.rolling(window=200).mean(),
            'ema_12': close.ewm(span=12, adjust=False).mean(),
            'ema_26': close.ewm(span=26, adjust=False).mean(),
        }
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Average True Range - المدى الحقيقي المتوسط
        """
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        Stochastic Oscillator - المذبذب العشوائي
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d = k.rolling(window=d_period).mean()
        return k, d
    
    @staticmethod
    def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Williams %R - مؤشر ويليامز
        """
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        wr = -100 * ((highest_high - close) / (highest_high - lowest_low))
        return wr
    
    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Average Directional Index - مؤشر الاتجاه المتوسط
        """
        plus_dm = high.diff()
        minus_dm = low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr = TechnicalIndicators.atr(high, low, close, period) * period
        
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr)
        minus_di = 100 * (abs(minus_dm).rolling(window=period).mean() / tr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        On-Balance Volume - حجم الرصيد
        """
        direction = np.where(close > close.shift(), 1, np.where(close < close.shift(), -1, 0))
        return (volume * direction).cumsum()


class TechnicalAnalysis:
    """
    تحليل فني شامل للأسهم
    """
    
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'rsi_weight': 15,
            'macd_weight': 10,
            'ma_weight': 12,
            'bollinger_weight': 8,
            'min_indicators_agree': 2
        }
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        تحليل شامل للبيانات
        
        Args:
            df: DataFrame with columns [open, high, low, close, volume]
        
        Returns:
            Dictionary with analysis results
        """
        if len(df) < 50:
            return {'error': 'Insufficient data for analysis'}
        
        # Calculate indicators
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df.get('volume', pd.Series(index=df.index, data=0))
        
        # RSI
        rsi = TechnicalIndicators.rsi(close)
        rsi_value = rsi.iloc[-1]
        
        # MACD
        macd_line, signal_line, histogram = TechnicalIndicators.macd(close)
        macd_value = macd_line.iloc[-1]
        signal_value = signal_line.iloc[-1]
        
        # Bollinger Bands
        upper, middle, lower = TechnicalIndicators.bollinger_bands(close)
        bb_upper = upper.iloc[-1]
        bb_lower = lower.iloc[-1]
        current_price = close.iloc[-1]
        
        # Moving Averages
        ma = TechnicalIndicators.moving_averages(close)
        sma_20 = ma['sma_20'].iloc[-1]
        sma_50 = ma['sma_50'].iloc[-1]
        sma_200 = ma['sma_200'].iloc[-1] if len(df) >= 200 else None
        
        # ATR
        atr = TechnicalIndicators.atr(high, low, close)
        atr_value = atr.iloc[-1]
        atr_percent = (atr_value / current_price) * 100
        
        # Stochastic
        stoch_k, stoch_d = TechnicalIndicators.stochastic(high, low, close)
        stoch_k_value = stoch_k.iloc[-1]
        
        # ADX
        adx = TechnicalIndicators.adx(high, low, close)
        adx_value = adx.iloc[-1]
        
        # OBV
        obv = TechnicalIndicators.obv(close, volume)
        obv_trend = 'up' if obv.iloc[-1] > obv.iloc[-5] else 'down'
        
        # Generate signals
        signals = self._generate_signals(
            rsi=rsi_value,
            macd=macd_value,
            signal=signal_value,
            current_price=current_price,
            bb_upper=bb_upper,
            bb_lower=bb_lower,
            sma_20=sma_20,
            sma_50=sma_50,
            sma_200=sma_200,
            stoch_k=stoch_k_value,
            adx=adx_value,
            atr_percent=atr_percent
        )
        
        # Compute professional trade plan
        trade_plan = self._compute_trade_plan(
            current_price=current_price,
            action=signals['action'],
            atr=atr_value,
            atr_percent=atr_percent,
            bb_upper=bb_upper,
            bb_lower=bb_lower,
            sma_20=sma_20,
            sma_50=sma_50,
            sma_200=sma_200,
            high=high,
            low=low
        )
        
        return {
            'current_price': round(current_price, 2),
            'indicators': {
                'rsi': round(rsi_value, 2),
                'macd': round(macd_value, 4),
                'macd_signal': round(signal_value, 4),
                'bb_upper': round(bb_upper, 2),
                'bb_lower': round(bb_lower, 2),
                'sma_20': round(sma_20, 2),
                'sma_50': round(sma_50, 2),
                'sma_200': round(sma_200, 2) if sma_200 else None,
                'atr': round(atr_value, 2),
                'atr_percent': round(atr_percent, 2),
                'stoch_k': round(stoch_k_value, 2),
                'adx': round(adx_value, 2),
                'obv_trend': obv_trend
            },
            'signals': signals,
            'trade_plan': trade_plan,
            'trend': self._determine_trend(signals),
            'volatility': 'high' if atr_percent > 4 else 'medium' if atr_percent > 2 else 'low'
        }
    
    def _generate_signals(self, **kwargs) -> Dict:
        """توليد إشارات التداول"""
        bullish_count = 0
        bearish_count = 0
        reasons = []
        
        # RSI Signal
        if kwargs['rsi'] <= self.params['rsi_oversold']:
            bullish_count += 1
            reasons.append(f"RSI تشبع بيعي ({kwargs['rsi']:.0f})")
        elif kwargs['rsi'] >= self.params['rsi_overbought']:
            bearish_count += 1
            reasons.append(f"RSI تشبع شرائي ({kwargs['rsi']:.0f})")
        
        # MACD Signal
        if kwargs['macd'] > kwargs['signal'] and kwargs['macd'] > 0:
            bullish_count += 1
            reasons.append("MACD إيجابي")
        elif kwargs['macd'] < kwargs['signal'] and kwargs['macd'] < 0:
            bearish_count += 1
            reasons.append("MACD سلبي")
        
        # Bollinger Signal
        if kwargs['current_price'] < kwargs['bb_lower']:
            bullish_count += 1
            reasons.append("تحت النطاق السفلي للبولينجر")
        elif kwargs['current_price'] > kwargs['bb_upper']:
            bearish_count += 1
            reasons.append("فوق النطاق العلوي للبولينجر")
        
        # MA Signal
        if kwargs['sma_200'] and kwargs['current_price'] > kwargs['sma_20'] and kwargs['current_price'] > kwargs['sma_50'] and kwargs['current_price'] > kwargs['sma_200']:
            bullish_count += 1
            reasons.append("فوق كل المتوسطات")
        elif kwargs['current_price'] < kwargs['sma_20'] and kwargs['current_price'] < kwargs['sma_50']:
            bearish_count += 1
            reasons.append("تحت كل المتوسطات")
        
        # Stochastic Signal
        if kwargs['stoch_k'] < 20:
            bullish_count += 1
            reasons.append("Stochastic تشبع بيعي")
        elif kwargs['stoch_k'] > 80:
            bearish_count += 1
            reasons.append("Stochastic تشبع شرائي")
        
        # Calculate score
        score = 50 + (bullish_count * 10) - (bearish_count * 10)
        
        # Determine action
        min_agree = self.params.get('min_indicators_agree', 2)
        if bullish_count >= min_agree and score >= 60:
            action = 'BUY'
            confidence = min(100, score)
        elif bearish_count >= min_agree and score <= 40:
            action = 'SELL'
            confidence = max(0, 100 - score)
        else:
            action = 'HOLD'
            confidence = 50
        
        return {
            'action': action,
            'confidence': confidence,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'score': score,
            'reasons': reasons
        }
    
    def _compute_trade_plan(self, current_price: float, action: str, atr: float,
                           atr_percent: float, bb_upper: float, bb_lower: float,
                           sma_20: float, sma_50: float, sma_200: Optional[float],
                           high: pd.Series, low: pd.Series) -> Dict:
        """
        حساب خطة التداول الاحترافية
        Entry zone, targets, stop loss, expected return
        """
        cp = current_price
        
        # Support level: lowest of recent swing low, bb_lower, sma_50
        recent_low = low.tail(20).min()
        support_candidates = [recent_low, bb_lower, sma_50]
        if sma_200:
            support_candidates.append(sma_200)
        support = min([s for s in support_candidates if s and not pd.isna(s)])
        
        # Resistance level: highest of recent swing high, bb_upper, sma_20
        recent_high = high.tail(20).max()
        resistance_candidates = [recent_high, bb_upper, sma_20]
        resistance = max([r for r in resistance_candidates if r and not pd.isna(r)])
        
        if action == 'BUY':
            # Entry zone: tight around current price (1-2% below)
            entry_low = round(max(cp * 0.985, support * 1.01), 2)
            entry_high = round(cp, 2)
            entry_trigger = round(cp * 1.01, 2)
            
            # Targets based on ATR multiples, capped by resistance
            t1_raw = cp + (atr * 2)
            t2_raw = cp + (atr * 3.5)
            target_1 = round(min(t1_raw, resistance), 2)
            target_2 = round(min(t2_raw, resistance * 1.02), 2)
            inv_target = round(max(resistance * 1.05, cp * 1.15), 2)
            
            # Stop loss: below support, max 5% from entry
            sl_atr = round(cp - (atr * 2.5), 2)
            sl_support = round(support * 0.98, 2)
            stop_loss = max(sl_atr, sl_support)
            stop_loss = max(stop_loss, round(cp * 0.95, 2))  # Don't go below 5%
            
            # Expected return from average entry to target_2
            avg_entry = (entry_low + entry_high) / 2
            expected_return = round(((target_2 - avg_entry) / avg_entry) * 100, 1)
            
        elif action == 'SELL':
            entry_low = round(cp, 2)
            entry_high = round(min(cp * 1.015, resistance * 0.99), 2)
            entry_trigger = round(cp * 0.99, 2)
            
            target_1 = round(max(cp - (atr * 2), support), 2)
            target_2 = round(max(cp - (atr * 3.5), support * 0.98), 2)
            inv_target = round(min(support * 0.95, cp * 0.85), 2)
            
            sl_atr = round(cp + (atr * 2.5), 2)
            sl_resistance = round(resistance * 1.02, 2)
            stop_loss = min(sl_atr, sl_resistance)
            stop_loss = min(stop_loss, round(cp * 1.05, 2))
            
            avg_entry = (entry_low + entry_high) / 2
            expected_return = round(((avg_entry - target_2) / avg_entry) * 100, 1)
            
        else:  # HOLD
            entry_low = round(cp * 0.99, 2)
            entry_high = round(cp * 1.01, 2)
            entry_trigger = round(cp * 1.02, 2)
            target_1 = round(resistance, 2)
            target_2 = round(resistance * 1.02, 2)
            inv_target = round(resistance * 1.05, 2)
            stop_loss = round(support * 0.98, 2)
            expected_return = round(((target_2 - cp) / cp) * 100, 1)
        
        # Clamp expected return to realistic range
        expected_return = max(3.0, min(expected_return, 50.0))
        
        risk = abs(((cp - stop_loss) / cp) * 100) if action != 'SELL' else abs(((stop_loss - cp) / cp) * 100)
        risk_reward = round(expected_return / max(risk, 0.5), 2)
        
        return {
            'entry_zone_low': round(entry_low, 2),
            'entry_zone_high': round(entry_high, 2),
            'entry_trigger': entry_trigger,
            'support_level': round(support, 2),
            'resistance_level': round(resistance, 2),
            'target_1': target_1,
            'target_2': target_2,
            'investment_target': inv_target,
            'stop_loss': round(stop_loss, 2),
            'expected_return_pct': expected_return,
            'risk_reward_ratio': risk_reward
        }
    
    def _determine_trend(self, signals: Dict) -> str:
        """تحديد الاتجاه العام"""
        if signals['bullish_count'] >= 3:
            return 'strong_bullish'
        elif signals['bullish_count'] > signals['bearish_count']:
            return 'bullish'
        elif signals['bearish_count'] >= 3:
            return 'strong_bearish'
        elif signals['bearish_count'] > signals['bullish_count']:
            return 'bearish'
        else:
            return 'neutral'


# Convenience function
def analyze_stock(df: pd.DataFrame, params: Optional[Dict] = None) -> Dict:
    """تحليل سهم واحد"""
    analyzer = TechnicalAnalysis(params)
    return analyzer.analyze(df)
