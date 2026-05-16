"""
Machine Learning Engine - محرك التعلم الآلي
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import joblib
from pathlib import Path

from sklearn.model_selection import train_test_split, cross_val_score, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.pipeline import Pipeline

from config import MODELS_DIR
from technical_analysis import TechnicalIndicators, TechnicalAnalysis


@dataclass
class TradeResult:
    """نتيجة صفقة"""
    ticker: str
    entry_date: str
    entry_price: float
    action: str
    exit_price: float
    return_pct: float
    win: bool
    confidence: float
    reasoning: str


@dataclass
class BacktestResult:
    """نتيجة اختبار رجعي"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    avg_return: float
    sharpe_ratio: float
    max_drawdown: float
    trades: List[TradeResult]


class FeatureEngineer:
    """
    هندسة الميزات - تحويل البيانات الخام إلى ميزات للتعلم
    """
    
    @staticmethod
    def create_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        إنشاء ميزات من البيانات
        """
        df = df.copy()
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df.get('volume', pd.Series(0, index=df.index))
        
        # Price features
        df['return_1d'] = close.pct_change()
        df['return_5d'] = close.pct_change(5)
        df['return_10d'] = close.pct_change(10)
        
        # Volatility
        df['volatility_10d'] = close.pct_change().rolling(10).std()
        df['volatility_20d'] = close.pct_change().rolling(20).std()
        
        # RSI
        df['rsi'] = TechnicalIndicators.rsi(close)
        
        # MACD
        macd, signal, hist = TechnicalIndicators.macd(close)
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_hist'] = hist
        
        # Bollinger Bands
        upper, middle, lower = TechnicalIndicators.bollinger_bands(close)
        df['bb_upper'] = upper
        df['bb_lower'] = lower
        df['bb_width'] = (upper - lower) / middle
        df['bb_position'] = (close - lower) / (upper - lower)  # 0-1 position
        
        # Moving Averages
        ma = TechnicalIndicators.moving_averages(close)
        df['sma_20'] = ma['sma_20']
        df['sma_50'] = ma['sma_50']
        df['sma_200'] = ma['sma_200']
        df['price_above_sma20'] = (close > ma['sma_20']).astype(int)
        df['price_above_sma50'] = (close > ma['sma_50']).astype(int)
        
        # ATR
        df['atr'] = TechnicalIndicators.atr(high, low, close)
        df['atr_pct'] = df['atr'] / close
        
        # Stochastic
        stoch_k, stoch_d = TechnicalIndicators.stochastic(high, low, close)
        df['stoch_k'] = stoch_k
        df['stoch_d'] = stoch_d
        
        # ADX
        df['adx'] = TechnicalIndicators.adx(high, low, close)
        
        # Volume
        df['volume_sma'] = volume.rolling(20).mean()
        df['volume_ratio'] = volume / df['volume_sma']
        
        # Price patterns
        df['higher_high'] = (high > high.shift(1)).astype(int)
        df['higher_low'] = (low > low.shift(1)).astype(int)
        df['lower_high'] = (high < high.shift(1)).astype(int)
        df['lower_low'] = (low < low.shift(1)).astype(int)
        
        return df
    
    @staticmethod
    def create_target(df: pd.DataFrame, holding_days: int = 30, target_return: float = 0.05) -> pd.Series:
        """
        إنشاء الهدف: هل السعر سيرتفع بنسبة X% خلال Y يوم؟
        """
        future_price = df['close'].shift(-holding_days)
        returns = (future_price - df['close']) / df['close']
        target = (returns >= target_return).astype(int)
        return target


class MLEngine:
    """
    محرك التعلم الآلي
    """
    
    def __init__(self, model_path: Optional[Path] = None):
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.model_path = model_path or MODELS_DIR / 'stock_model.pkl'
        
        if self.model_path.exists():
            self.load_model()
    
    def train(self, 
              data: Dict[str, pd.DataFrame],
              holding_days: int = 30,
              target_return: float = 0.03) -> Dict:
        """
        تدريب النموذج على بيانات متعددة الأسهم
        
        Args:
            data: Dictionary of ticker -> DataFrame
            holding_days: عدد أيام الاحتفاظ
            target_return: العائد المستهدف
        
        Returns:
            Training metrics
        """
        logger.info(f"Training ML model on {len(data)} stocks...")
        
        all_features = []
        all_targets = []
        
        for ticker, df in data.items():
            try:
                # Create features
                features_df = FeatureEngineer.create_features(df)
                target = FeatureEngineer.create_target(df, holding_days, target_return)
                
                # Remove NaN rows
                features_df = features_df.dropna()
                target = target.loc[features_df.index]
                
                # Add ticker as feature (encoded)
                # features_df['ticker_encoded'] = hash(ticker) % 1000
                
                all_features.append(features_df)
                all_targets.append(target)
                
            except Exception as e:
                logger.warning(f"Error processing {ticker}: {e}")
                continue
        
        if not all_features:
            raise ValueError("No valid data for training")
        
        # Combine all data
        X = pd.concat(all_features)
        y = pd.concat(all_targets)
        
        self.feature_names = X.columns.tolist()
        
        # Remove rows with NaN in target
        valid_mask = ~y.isna()
        X = X[valid_mask]
        y = y[valid_mask]
        
        logger.info(f"Total samples: {len(X)}, Features: {len(self.feature_names)}")
        
        # Time series split (respect chronological order)
        tscv = TimeSeriesSplit(n_splits=5)
        
        # Create pipeline
        self.model = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', GradientBoostingClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            ))
        ])
        
        # Cross-validation scores
        cv_scores = cross_val_score(self.model, X, y, cv=tscv, scoring='accuracy')
        
        # Train on full data
        self.model.fit(X, y)
        
        # Get feature importance
        classifier = self.model.named_steps['classifier']
        feature_importance = dict(zip(
            self.feature_names,
            classifier.feature_importances_
        ))
        
        # Save model
        self.save_model()
        
        return {
            'cv_accuracy_mean': cv_scores.mean(),
            'cv_accuracy_std': cv_scores.std(),
            'train_accuracy': self.model.score(X, y),
            'feature_importance': dict(sorted(feature_importance.items(), key=lambda x: -x[1])[:10]),
            'n_samples': len(X),
            'n_features': len(self.feature_names)
        }
    
    def predict(self, df: pd.DataFrame) -> Dict:
        """
        التنبؤ بسهم واحد
        """
        if self.model is None:
            raise ValueError("Model not trained")
        
        # Create features
        features_df = FeatureEngineer.create_features(df)
        features_df = features_df.dropna()
        
        if len(features_df) == 0:
            return {'error': 'Insufficient data'}
        
        # Get last row
        X = features_df[self.feature_names].iloc[[-1]]
        
        # Predict
        prediction = self.model.predict(X)[0]
        proba = self.model.predict_proba(X)[0]
        
        return {
            'prediction': 'BUY' if prediction == 1 else 'HOLD',
            'probability': float(proba[1]) if prediction == 1 else float(proba[0]),
            'confidence': float(max(proba)) * 100
        }
    
    def predict_batch(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
        """
        التنبؤ بأسهم متعددة
        """
        predictions = {}
        for ticker, df in data.items():
            try:
                pred = self.predict(df)
                predictions[ticker] = pred
            except Exception as e:
                predictions[ticker] = {'error': str(e)}
        return predictions
    
    def backtest(self,
                 data: Dict[str, pd.DataFrame],
                 holding_days: int = 30,
                 confidence_threshold: float = 0.6,
                 initial_capital: float = 100000) -> BacktestResult:
        """
        اختبار رجعي للنموذج
        """
        trades = []
        
        for ticker, df in data.items():
            try:
                # Create features
                features_df = FeatureEngineer.create_features(df)
                
                for i in range(len(features_df) - holding_days):
                    date = features_df.index[i]
                    price = features_df['close'].iloc[i]
                    
                    # Predict
                    X = features_df[self.feature_names].iloc[[i]]
                    prediction = self.model.predict(X)[0]
                    proba = self.model.predict_proba(X)[0]
                    
                    confidence = max(proba)
                    
                    if confidence < confidence_threshold:
                        continue
                    
                    if prediction == 1:  # BUY
                        exit_price = features_df['close'].iloc[i + holding_days]
                        return_pct = (exit_price - price) / price * 100
                        
                        trades.append(TradeResult(
                            ticker=ticker,
                            entry_date=str(date.date()),
                            entry_price=price,
                            action='BUY',
                            exit_price=exit_price,
                            return_pct=return_pct,
                            win=return_pct > 0,
                            confidence=confidence * 100,
                            reasoning=f"ML Prediction: {confidence*100:.1f}% confidence"
                        ))
            
            except Exception as e:
                logger.warning(f"Backtest error for {ticker}: {e}")
                continue
        
        if not trades:
            return BacktestResult(0, 0, 0, 0, 0, 0, 0, 0, [])
        
        # Calculate metrics
        winning = [t for t in trades if t.win]
        losing = [t for t in trades if not t.win]
        
        total_return = sum(t.return_pct for t in trades)
        avg_return = total_return / len(trades)
        
        # Sharpe ratio (simplified)
        returns = [t.return_pct for t in trades]
        sharpe = np.mean(returns) / (np.std(returns) + 0.0001)
        
        # Max drawdown
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        max_drawdown = np.max(drawdown)
        
        return BacktestResult(
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=len(winning) / len(trades) * 100,
            total_return=total_return,
            avg_return=avg_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            trades=trades
        )
    
    def save_model(self):
        """حفظ النموذج"""
        joblib.dump({
            'model': self.model,
            'feature_names': self.feature_names
        }, self.model_path)
        logger.info(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """تحميل النموذج"""
        data = joblib.load(self.model_path)
        self.model = data['model']
        self.feature_names = data['feature_names']
        logger.info(f"Model loaded from {self.model_path}")


# Global instance
ml_engine = MLEngine()
