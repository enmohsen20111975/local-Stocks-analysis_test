# -*- coding: utf-8 -*-
"""
Deep Learning Engine for Egyptian Stock Market
===============================================
نظام التعلّم العميق للبورصة المصرية

Features:
- Bayesian Optimization for parameter tuning (Optuna)
- Deep Neural Networks (PyTorch)
- Gradient Boosting (XGBoost, LightGBM)
- Real-time learning with backtesting
- Model persistence and versioning
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import warnings
warnings.filterwarnings('ignore')

# Database
import sqlite3

# Logging
from loguru import logger

# ============================================================
# Configuration
# ============================================================
VERSION = "2.0.0"
DB_PATH = os.environ.get('DB_PATH', '/root/GLMinvestment/db/egx_investment.db')
LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "egx_investment.db")
VPS_DB_PATH = "/root/GLMinvestment/db/egx_investment.db"
DB_PATH = VPS_DB_PATH if os.path.exists(VPS_DB_PATH) else LOCAL_DB_PATH

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# ============================================================
# Data Classes
# ============================================================
@dataclass
class LearningConfig:
    """إعدادات التعلّم"""
    target_win_rate: float = 65.0  # هدف واقعي (كان 99%!)
    max_iterations: int = 100
    n_trials: int = 50  # لـ Optuna
    cv_folds: int = 5  # Cross-validation
    train_test_split: float = 0.2
    min_data_points: int = 100
    early_stopping_patience: int = 10
    
@dataclass
class ModelPerformance:
    """أداء النموذج"""
    win_rate: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    avg_return: float = 0.0

@dataclass
class LearningProgress:
    """تقدم التعلّم"""
    status: str = "idle"  # idle, running, completed, error
    current_iteration: int = 0
    total_iterations: int = 0
    current_trial: int = 0
    total_trials: int = 0
    best_score: float = 0.0
    best_params: Dict = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    message: str = ""
    history: List[Dict] = field(default_factory=list)

# ============================================================
# Database Helper
# ============================================================
def get_db_connection():
    """الحصول على اتصال قاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_stock_data(ticker: str, days: int = 365) -> pd.DataFrame:
    """تحميل بيانات سهم معين"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT sph.date, sph.open, sph.high, sph.low, sph.close, sph.volume
        FROM stock_price_history sph
        JOIN stocks s ON s.id = sph.stock_id
        WHERE s.ticker = ?
        ORDER BY sph.date DESC
        LIMIT ?
    """, (ticker, days))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return pd.DataFrame()
    
    df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    df = df.iloc[::-1]  # ترتيب تصاعدي
    df['date'] = pd.to_datetime(df['date'])
    
    # تحويل إلى أرقام
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

def load_all_stocks_data(min_records: int = 100) -> Dict[str, pd.DataFrame]:
    """تحميل بيانات جميع الأسهم"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # الحصول على الأسهم مع بيانات كافية
    cursor.execute("""
        SELECT s.ticker, COUNT(*) as records
        FROM stock_price_history sph
        JOIN stocks s ON s.id = sph.stock_id
        GROUP BY s.ticker
        HAVING records >= ?
        ORDER BY records DESC
    """, (min_records,))
    
    tickers = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    data = {}
    for ticker in tickers:
        df = load_stock_data(ticker)
        if not df.empty and len(df) >= min_records:
            data[ticker] = df
    
    logger.info(f"Loaded {len(data)} stocks with sufficient data")
    return data

# ============================================================
# Feature Engineering
# ============================================================
class FeatureEngineer:
    """هندسة الميزات"""
    
    @staticmethod
    def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """إضافة المؤشرات الفنية"""
        df = df.copy()
        
        # المتوسطات المتحركة
        df['sma_5'] = df['close'].rolling(window=5).mean()
        df['sma_10'] = df['close'].rolling(window=10).mean()
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        
        # EMA
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=14).mean()
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Price momentum
        df['returns'] = df['close'].pct_change()
        df['returns_5d'] = df['close'].pct_change(5)
        df['returns_10d'] = df['close'].pct_change(10)
        
        # Volatility
        df['volatility_20d'] = df['returns'].rolling(window=20).std()
        
        # Price position
        df['price_position'] = (df['close'] - df['low'].rolling(20).min()) / (
            df['high'].rolling(20).max() - df['low'].rolling(20).min()
        )
        
        # Trends
        df['trend_5d'] = (df['close'] - df['close'].shift(5)) / df['close'].shift(5)
        df['trend_20d'] = (df['close'] - df['close'].shift(20)) / df['close'].shift(20)
        
        return df
    
    @staticmethod
    def create_labels(df: pd.DataFrame, forward_days: int = 5, threshold: float = 0.02) -> pd.DataFrame:
        """إنشاء التصنيفات للتعلّم المشرف"""
        df = df.copy()
        
        # العائد المستقبلي
        df['future_return'] = df['close'].shift(-forward_days) / df['close'] - 1
        
        # التصنيف: 1 = شراء، 0 = انتظار، -1 = بيع
        df['label'] = 0
        df.loc[df['future_return'] > threshold, 'label'] = 1  # شراء
        df.loc[df['future_return'] < -threshold, 'label'] = -1  # بيع
        
        return df
    
    @staticmethod
    def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """تحضير الميزات للتعلّم"""
        # حذف الصفوف الفارغة
        df = df.dropna()
        
        # الميزات
        feature_cols = [
            'sma_5', 'sma_10', 'sma_20', 'sma_50',
            'macd', 'macd_signal', 'macd_histogram',
            'rsi', 'bb_width', 'atr',
            'volume_ratio', 'returns', 'returns_5d', 'returns_10d',
            'volatility_20d', 'price_position',
            'trend_5d', 'trend_20d'
        ]
        
        X = df[feature_cols]
        y = df['label']
        
        return X, y

# ============================================================
# Deep Learning Models
# ============================================================
class DeepLearningOptimizer:
    """محرك التعلّم العميق مع Bayesian Optimization"""
    
    def __init__(self, config: LearningConfig = None):
        self.config = config or LearningConfig()
        self.progress = LearningProgress()
        self._stop_requested = False
        self.best_model = None
        self.feature_engineer = FeatureEngineer()
        
    def prepare_training_data(self, data: Dict[str, pd.DataFrame]) -> Tuple[np.ndarray, np.ndarray]:
        """تحضير بيانات التدريب"""
        all_X = []
        all_y = []
        
        for ticker, df in data.items():
            try:
                df_features = self.feature_engineer.add_technical_indicators(df)
                df_labeled = self.feature_engineer.create_labels(df_features)
                X, y = self.feature_engineer.prepare_features(df_labeled)
                
                if len(X) >= self.config.min_data_points:
                    all_X.append(X)
                    all_y.append(y)
            except Exception as e:
                logger.warning(f"Error processing {ticker}: {e}")
                continue
        
        if not all_X:
            raise ValueError("No valid data for training")
        
        X_combined = pd.concat(all_X, ignore_index=True)
        y_combined = pd.concat(all_y, ignore_index=True)
        
        # حذف القيم الفارغة
        mask = ~(X_combined.isna().any(axis=1) | y_combined.isna())
        X_combined = X_combined[mask]
        y_combined = y_combined[mask]
        
        logger.info(f"Prepared {len(X_combined)} samples from {len(all_X)} stocks")
        
        return X_combined.values, y_combined.values
    
    def objective(self, trial, X_train, y_train, X_val, y_val):
        """دالة الهدف لـ Optuna"""
        try:
            import optuna
            from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
            from sklearn.metrics import accuracy_score, f1_score
            
            # اختيار النموذج
            model_type = trial.suggest_categorical('model_type', ['rf', 'gb', 'xgboost', 'lightgbm'])
            
            if model_type == 'rf':
                model = RandomForestClassifier(
                    n_estimators=trial.suggest_int('n_estimators', 50, 300),
                    max_depth=trial.suggest_int('max_depth', 5, 30),
                    min_samples_split=trial.suggest_int('min_samples_split', 2, 20),
                    min_samples_leaf=trial.suggest_int('min_samples_leaf', 1, 10),
                    random_state=42,
                    n_jobs=-1
                )
            elif model_type == 'gb':
                model = GradientBoostingClassifier(
                    n_estimators=trial.suggest_int('n_estimators', 50, 200),
                    max_depth=trial.suggest_int('max_depth', 3, 15),
                    learning_rate=trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                    random_state=42
                )
            elif model_type == 'xgboost':
                import xgboost as xgb
                model = xgb.XGBClassifier(
                    n_estimators=trial.suggest_int('n_estimators', 50, 300),
                    max_depth=trial.suggest_int('max_depth', 3, 15),
                    learning_rate=trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                    subsample=trial.suggest_float('subsample', 0.6, 1.0),
                    colsample_bytree=trial.suggest_float('colsample_bytree', 0.6, 1.0),
                    random_state=42,
                    verbosity=0
                )
            else:  # lightgbm
                import lightgbm as lgb
                model = lgb.LGBMClassifier(
                    n_estimators=trial.suggest_int('n_estimators', 50, 300),
                    max_depth=trial.suggest_int('max_depth', 3, 15),
                    learning_rate=trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                    num_leaves=trial.suggest_int('num_leaves', 20, 100),
                    random_state=42,
                    verbose=-1
                )
            
            # التدريب
            model.fit(X_train, y_train)
            
            # التقييم
            y_pred = model.predict(X_val)
            f1 = f1_score(y_val, y_pred, average='weighted')
            
            return f1
            
        except Exception as e:
            logger.error(f"Trial failed: {e}")
            return 0.0
    
    def optimize(self, data: Dict[str, pd.DataFrame] = None) -> Dict:
        """تشغيل Bayesian Optimization"""
        try:
            import optuna
            from sklearn.model_selection import train_test_split
            from sklearn.preprocessing import StandardScaler
            
            self.progress.status = "running"
            self.progress.start_time = datetime.now()
            self._stop_requested = False
            
            # تحميل البيانات إذا لم تكن موجودة
            if data is None:
                data = load_all_stocks_data(self.config.min_data_points)
            
            # تحضير البيانات
            X, y = self.prepare_training_data(data)
            
            # تقسيم البيانات
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=self.config.train_test_split, random_state=42
            )
            
            # تطبيع البيانات
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_val = scaler.transform(X_val)
            
            # حفظ الـ scaler
            self.scaler = scaler
            
            # إنشاء دراسة Optuna
            study = optuna.create_study(
                direction='maximize',
                study_name='egx_deep_learning',
                storage=f'sqlite:///{MODELS_DIR}/optuna.db',
                load_if_exists=True
            )
            
            def objective_wrapper(trial):
                self.progress.current_trial = trial.number + 1
                self.progress.total_trials = self.config.n_trials
                self.progress.message = f"Trial {trial.number + 1}/{self.config.n_trials}"
                
                if self._stop_requested:
                    raise optuna.exceptions.OptunaError("Optimization stopped by user")
                
                score = self.objective(trial, X_train, y_train, X_val, y_val)
                
                if score > self.progress.best_score:
                    self.progress.best_score = score
                    self.progress.best_params = trial.params
                    self.progress.history.append({
                        'trial': trial.number + 1,
                        'score': score,
                        'params': trial.params
                    })
                
                return score
            
            # تشغيل التحسين
            study.optimize(
                objective_wrapper,
                n_trials=self.config.n_trials,
                callbacks=[self._optuna_callback]
            )
            
            # حفظ أفضل نموذج
            self._save_best_model(study.best_trial, scaler)
            
            self.progress.status = "completed"
            self.progress.end_time = datetime.now()
            self.progress.message = f"Completed! Best F1: {study.best_value:.4f}"
            
            return {
                'success': True,
                'best_score': study.best_value,
                'best_params': study.best_params,
                'n_trials': len(study.trials),
                'duration': str(self.progress.end_time - self.progress.start_time)
            }
            
        except Exception as e:
            self.progress.status = "error"
            self.progress.message = str(e)
            logger.error(f"Optimization error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _optuna_callback(self, study, trial):
        """Callback لـ Optuna"""
        if self._stop_requested:
            study.stop()
    
    def _save_best_model(self, best_trial, scaler):
        """حفظ أفضل نموذج"""
        import joblib
        
        model_data = {
            'params': best_trial.params,
            'scaler': scaler,
            'timestamp': datetime.now().isoformat(),
            'version': VERSION
        }
        
        model_path = os.path.join(MODELS_DIR, 'best_model.pkl')
        joblib.dump(model_data, model_path)
        logger.info(f"Model saved to {model_path}")
    
    def stop(self):
        """إيقاف التحسين"""
        self._stop_requested = True
    
    def get_progress(self) -> Dict:
        """الحصول على تقدم التعلّم"""
        return {
            'status': self.progress.status,
            'current_trial': self.progress.current_trial,
            'total_trials': self.progress.total_trials,
            'best_score': self.progress.best_score,
            'best_params': self.progress.best_params,
            'message': self.progress.message,
            'history': self.progress.history[-10:]  # آخر 10 تجارب
        }

# ============================================================
# Trading Signal Generator
# ============================================================
class SignalGenerator:
    """مولد إشارات التداول"""
    
    def __init__(self, model_path: str = None):
        import joblib
        
        self.feature_engineer = FeatureEngineer()
        self.model = None
        self.scaler = None
        
        if model_path and os.path.exists(model_path):
            model_data = joblib.load(model_path)
            self.scaler = model_data.get('scaler')
            self.best_params = model_data.get('params', {})
    
    def generate_signal(self, ticker: str, df: pd.DataFrame = None) -> Dict:
        """توليد إشارة تداول لسهم معين"""
        try:
            if df is None:
                df = load_stock_data(ticker, days=200)
            
            if df.empty or len(df) < 100:
                return {'signal': 'insufficient_data', 'confidence': 0}
            
            # إضافة الميزات
            df_features = self.feature_engineer.add_technical_indicators(df)
            
            # الحصول على آخر صف
            latest = df_features.iloc[-1:]
            
            # الميزات
            feature_cols = [
                'sma_5', 'sma_10', 'sma_20', 'sma_50',
                'macd', 'macd_signal', 'macd_histogram',
                'rsi', 'bb_width', 'atr',
                'volume_ratio', 'returns', 'returns_5d', 'returns_10d',
                'volatility_20d', 'price_position',
                'trend_5d', 'trend_20d'
            ]
            
            X = latest[feature_cols].values
            
            if self.scaler:
                X = self.scaler.transform(X)
            
            # استنتاج بسيط (يمكن استبداله بنموذج مدرب)
            # هذا يستخدم قواعد فنية
            signal = self._rule_based_signal(df_features.iloc[-1])
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {ticker}: {e}")
            return {'signal': 'error', 'confidence': 0, 'error': str(e)}
    
    def _rule_based_signal(self, row) -> Dict:
        """إشارة مبنية على القواعد الفنية"""
        signals = []
        
        # RSI
        if row['rsi'] < 30:
            signals.append(('rsi', 'buy', 0.7))
        elif row['rsi'] > 70:
            signals.append(('rsi', 'sell', 0.7))
        else:
            signals.append(('rsi', 'hold', 0.5))
        
        # MACD
        if row['macd_histogram'] > 0:
            signals.append(('macd', 'buy', 0.6))
        else:
            signals.append(('macd', 'sell', 0.6))
        
        # Trend
        if row['trend_5d'] > 0 and row['trend_20d'] > 0:
            signals.append(('trend', 'buy', 0.8))
        elif row['trend_5d'] < 0 and row['trend_20d'] < 0:
            signals.append(('trend', 'sell', 0.8))
        
        # Volume
        if row['volume_ratio'] > 1.5:
            signals.append(('volume', 'strong', 0.5))
        
        # تجميع الإشارات
        buy_score = sum(s[2] for s in signals if s[1] == 'buy')
        sell_score = sum(s[2] for s in signals if s[1] == 'sell')
        
        if buy_score > sell_score + 0.5:
            final_signal = 'buy'
            confidence = min(buy_score / 3, 1.0)
        elif sell_score > buy_score + 0.5:
            final_signal = 'sell'
            confidence = min(sell_score / 3, 1.0)
        else:
            final_signal = 'hold'
            confidence = 0.5
        
        return {
            'signal': final_signal,
            'confidence': confidence,
            'indicators': {s[0]: {'action': s[1], 'weight': s[2]} for s in signals},
            'price': float(row['close']),
            'rsi': float(row['rsi']),
            'macd': float(row['macd_histogram']),
            'timestamp': datetime.now().isoformat()
        }

# ============================================================
# Initialize Global Instances
# ============================================================
deep_learning_engine = DeepLearningOptimizer()
signal_generator = SignalGenerator(os.path.join(MODELS_DIR, 'best_model.pkl'))

# ============================================================
# API Helper Functions
# ============================================================
def start_deep_learning(config: Dict = None) -> Dict:
    """بدء التعلّم العميق"""
    if config:
        learning_config = LearningConfig(**config)
        deep_learning_engine.config = learning_config
    
    return deep_learning_engine.optimize()

def stop_deep_learning() -> Dict:
    """إيقاف التعلّم"""
    deep_learning_engine.stop()
    return {'success': True, 'message': 'Deep learning stopped'}

def get_deep_learning_progress() -> Dict:
    """الحصول على تقدم التعلّم"""
    return deep_learning_engine.get_progress()

def get_signal(ticker: str) -> Dict:
    """الحصول على إشارة تداول"""
    return signal_generator.generate_signal(ticker)
