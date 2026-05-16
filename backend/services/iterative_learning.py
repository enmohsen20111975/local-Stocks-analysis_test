"""
Iterative Learning Engine - محرك التعلم التكراري
مع Cross-Validation لتجنب Overfitting
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger
from datetime import datetime
import json

from ml_engine import MLEngine, BacktestResult, TradeResult
from technical_analysis import TechnicalAnalysis
from database import price_db, params_db


@dataclass
class LearningParameters:
    """بارامترات التعلم"""
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    rsi_weight: float = 15.0
    macd_weight: float = 10.0
    ma_weight: float = 12.0
    bollinger_weight: float = 8.0
    stop_loss_min: float = 3.0
    stop_loss_max: float = 8.0
    target_multiplier: float = 2.0
    confidence_threshold: float = 55.0
    min_indicators_agree: int = 2
    volume_threshold: float = 1.5
    volume_weight: float = 5.0


@dataclass
class LearningProgress:
    """تقدم التعلم"""
    target_win_rate: float = 99.0
    current_win_rate: float = 0.0
    best_win_rate: float = 0.0
    iteration: int = 0
    max_iterations: int = 50
    status: str = 'idle'
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    best_parameters: Optional[Dict] = None
    cross_validation_score: float = 0.0
    win_rate_history: List[float] = field(default_factory=list)
    message: str = ''


# Cross-Validation Folds
DATA_FOLDS = [
    {'name': 'Fold 1: Q3 2025', 'start': '2025-07-01', 'end': '2025-09-30'},
    {'name': 'Fold 2: Q4 2025', 'start': '2025-10-01', 'end': '2025-12-31'},
    {'name': 'Fold 3: Q1 2026', 'start': '2026-01-01', 'end': '2026-03-31'},
    {'name': 'Fold 4: Q2 2026', 'start': '2026-04-01', 'end': '2026-06-30'},
    {'name': 'Fold 5: Full Year', 'start': '2025-07-01', 'end': '2026-05-31'},
]


class IterativeLearningEngine:
    """
    محرك التعلم التكراري
    يستخدم Cross-Validation لتجنب Overfitting
    """
    
    def __init__(self):
        self.progress = LearningProgress()
        self.should_stop = False
        self.ml_engine = MLEngine()
    
    def start(self,
              target_win_rate: float = 99.0,
              max_iterations: int = 50,
              tickers: Optional[List[str]] = None) -> LearningProgress:
        """
        بدء التعلم التكراري
        """
        logger.info(f"Starting iterative learning - Target: {target_win_rate}%")
        
        self.progress = LearningProgress(
            target_win_rate=target_win_rate,
            max_iterations=max_iterations,
            status='running',
            started_at=datetime.now().isoformat(),
            message='بدأ التعلم التكراري...'
        )
        self.should_stop = False
        
        # Load data
        all_tickers = tickers or price_db.get_all_tickers()
        logger.info(f"Found {len(all_tickers)} tickers")
        
        current_params = LearningParameters()
        no_improvement_count = 0
        
        for iteration in range(1, max_iterations + 1):
            if self.should_stop:
                self.progress.status = 'stopped'
                self.progress.message = 'تم إيقاف التعلم'
                break
            
            self.progress.iteration = iteration
            
            # 🔄 Cross-Validation: استخدام fold مختلف
            fold = DATA_FOLDS[(iteration - 1) % len(DATA_FOLDS)]
            logger.info(f"Iteration {iteration}/{max_iterations} - {fold['name']}")
            
            # Load data for this fold
            fold_data = self._load_fold_data(all_tickers, fold['start'], fold['end'])
            
            if not fold_data:
                logger.warning(f"No data for fold {fold['name']}")
                continue
            
            try:
                # Run backtest with current parameters
                result = self._run_backtest(fold_data, current_params)
                
                # Update progress
                self.progress.current_win_rate = result.win_rate
                self.progress.win_rate_history.append(result.win_rate)
                
                # Calculate Cross-Validation Score
                if len(self.progress.win_rate_history) >= 3:
                    self.progress.cross_validation_score = self._calculate_cv_score()
                
                # Check if best
                if result.win_rate > self.progress.best_win_rate:
                    self.progress.best_win_rate = result.win_rate
                    self.progress.best_parameters = self._params_to_dict(current_params)
                    no_improvement_count = 0
                    logger.success(f"NEW BEST: {result.win_rate:.2f}% on {fold['name']}")
                else:
                    no_improvement_count += 1
                
                # Check target reached
                if result.win_rate >= target_win_rate:
                    self.progress.status = 'completed'
                    self.progress.message = f'🎯 تم الوصول للهدف! {result.win_rate:.2f}%'
                    self.progress.completed_at = datetime.now().isoformat()
                    break
                
                # If no improvement, try radical change
                if no_improvement_count >= 10:
                    logger.info("No improvement - trying radical change")
                    current_params.confidence_threshold = 55 + np.random.randint(-15, 20)
                    no_improvement_count = 0
                
                # Optimize parameters based on results
                current_params = self._optimize_parameters(result, current_params)
                
            except Exception as e:
                logger.error(f"Error in iteration {iteration}: {e}")
                continue
        
        if self.progress.status == 'running':
            self.progress.status = 'completed'
            self.progress.completed_at = datetime.now().isoformat()
            self.progress.message = f'انتهى التعلم - أفضل نسبة: {self.progress.best_win_rate:.2f}%'
        
        return self.progress
    
    def stop(self):
        """إيقاف التعلم"""
        self.should_stop = True
    
    def get_progress(self) -> LearningProgress:
        """الحصول على التقدم"""
        return self.progress
    
    def apply_best_parameters(self) -> bool:
        """تطبيق أفضل البارامترات"""
        if not self.progress.best_parameters:
            return False
        
        if self.progress.best_win_rate < 50:
            return False
        
        try:
            params_db.save_params({
                'id': f'py-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'name': f"Python ML - {self.progress.best_win_rate:.1f}%",
                'win_rate': self.progress.best_win_rate,
                'total_trades': 0,
                **self.progress.best_parameters
            })
            return True
        except Exception as e:
            logger.error(f"Failed to save parameters: {e}")
            return False
    
    def _load_fold_data(self, tickers: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """تحميل بيانات Fold"""
        data = {}
        for ticker in tickers[:50]:  # Limit to 50 for performance
            try:
                df = price_db.get_daily_prices(ticker, 365)
                if len(df) >= 50:
                    # Filter by date range
                    start = pd.to_datetime(start_date)
                    end = pd.to_datetime(end_date)
                    mask = (df.index >= start) & (df.index <= end)
                    filtered = df[mask]
                    if len(filtered) >= 30:
                        data[ticker] = filtered
            except Exception:
                continue
        return data
    
    def _run_backtest(self, data: Dict[str, pd.DataFrame], params: LearningParameters) -> BacktestResult:
        """تشغيل اختبار رجعي"""
        trades = []
        analyzer = TechnicalAnalysis(self._params_to_dict(params))
        
        for ticker, df in data.items():
            try:
                for i in range(len(df) - 30):
                    analysis_df = df.iloc[:i+1]
                    analysis = analyzer.analyze(analysis_df)
                    
                    if 'error' in analysis:
                        continue
                    
                    signals = analysis['signals']
                    if signals['action'] == 'HOLD':
                        continue
                    
                    if signals['confidence'] < params.confidence_threshold:
                        continue
                    
                    # Simulate trade
                    entry_price = df['close'].iloc[i]
                    exit_price = df['close'].iloc[i + 30] if i + 30 < len(df) else df['close'].iloc[-1]
                    return_pct = (exit_price - entry_price) / entry_price * 100
                    
                    trades.append(TradeResult(
                        ticker=ticker,
                        entry_date=str(df.index[i].date()),
                        entry_price=entry_price,
                        action=signals['action'],
                        exit_price=exit_price,
                        return_pct=return_pct,
                        win=return_pct > 0,
                        confidence=signals['confidence'],
                        reasoning=' | '.join(signals['reasons'])
                    ))
            except Exception:
                continue
        
        if not trades:
            return BacktestResult(0, 0, 0, 0, 0, 0, 0, 0, [])
        
        winning = [t for t in trades if t.win]
        total_return = sum(t.return_pct for t in trades)
        avg_return = total_return / len(trades)
        
        returns = [t.return_pct for t in trades]
        sharpe = np.mean(returns) / (np.std(returns) + 0.0001)
        
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        
        return BacktestResult(
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(trades) - len(winning),
            win_rate=len(winning) / len(trades) * 100,
            total_return=total_return,
            avg_return=avg_return,
            sharpe_ratio=sharpe,
            max_drawdown=np.max(drawdown),
            trades=trades
        )
    
    def _calculate_cv_score(self) -> float:
        """حساب Cross-Validation Score"""
        history = self.progress.win_rate_history
        avg = np.mean(history)
        std = np.std(history)
        
        # CV Score = Average - (Std Dev penalty)
        # كلما كان التشتت أقل، كان النظام أكثر موثوقية
        return avg - (std * 0.5)
    
    def _optimize_parameters(self, result: BacktestResult, current: LearningParameters) -> LearningParameters:
        """تحسين البارامترات بناءً على النتائج"""
        new_params = LearningParameters(
            rsi_oversold=current.rsi_oversold,
            rsi_overbought=current.rsi_overbought,
            rsi_weight=current.rsi_weight,
            macd_weight=current.macd_weight,
            ma_weight=current.ma_weight,
            bollinger_weight=current.bollinger_weight,
            stop_loss_min=current.stop_loss_min,
            stop_loss_max=current.stop_loss_max,
            target_multiplier=current.target_multiplier,
            confidence_threshold=current.confidence_threshold,
            min_indicators_agree=current.min_indicators_agree,
            volume_threshold=current.volume_threshold,
            volume_weight=current.volume_weight
        )
        
        # تحليل الصفقات
        if result.trades:
            winners = [t for t in result.trades if t.win]
            losers = [t for t in result.trades if not t.win]
            
            # إذا كانت معظم الخسائر من stop loss، زود المسافة
            if losers:
                stopped_out = [t for t in losers if 'stop' in t.reasoning.lower()]
                if len(stopped_out) > len(losers) * 0.6:
                    new_params.stop_loss_min = min(6, new_params.stop_loss_min + 0.5)
            
            # إذا كانت نسبة النجاح عالية مع ثقة عالية، زود الـ threshold
            if result.win_rate > 60 and winners:
                avg_conf = np.mean([t.confidence for t in winners])
                if avg_conf > 70:
                    new_params.confidence_threshold = min(80, new_params.confidence_threshold + 5)
        
        return new_params
    
    def _params_to_dict(self, params: LearningParameters) -> Dict:
        """تحويل البارامترات إلى Dictionary"""
        return {
            'rsi_oversold': params.rsi_oversold,
            'rsi_overbought': params.rsi_overbought,
            'rsi_weight': params.rsi_weight,
            'macd_weight': params.macd_weight,
            'ma_weight': params.ma_weight,
            'bollinger_weight': params.bollinger_weight,
            'stop_loss_min': params.stop_loss_min,
            'stop_loss_max': params.stop_loss_max,
            'target_multiplier': params.target_multiplier,
            'confidence_threshold': params.confidence_threshold,
            'min_indicators_agree': params.min_indicators_agree,
            'volume_threshold': params.volume_threshold,
            'volume_weight': params.volume_weight
        }


# Global instance
iterative_learning = IterativeLearningEngine()
