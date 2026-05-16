#!/usr/bin/env python3
"""
Iterative Learning Engine with Simulated Trades
================================================
نظام التعلم التكراري مع الصفقات الوهمية

Features:
1. إنشاء صفقات وهمية على البيانات التاريخية
2. تتبع أداء الصفقات وتحليل النتائج
3. تحسين معاملات التوقع بناءً على النتائج
4. لا ينتظر العميل - يتعلم من البيانات التاريخية

Usage:
    python3 iterative_learning_engine.py --learn-all
    python3 iterative_learning_engine.py --stock COMI --iterations 100
    python3 iterative_learning_engine.py --status
"""

import os
import sys
import json
import sqlite3
import random
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
import statistics

# Database path
DB_PATH = os.environ.get('DATABASE_PATH', '/home/z/my-project/GLMinvestment/db/custom.db')

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class SimulatedTrade:
    """صفقة وهمية للتدريب"""
    id: str
    symbol: str
    entry_date: str
    entry_price: float
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    signal: str = "BUY"  # BUY or SELL
    confidence: float = 0.0
    
    # Strategy parameters
    strategy: str = "technical"  # technical, momentum, mean_reversion
    target_percent: float = 5.0
    stop_loss_percent: float = 3.0
    holding_days: int = 0
    
    # Results
    status: str = "OPEN"  # OPEN, TARGET_HIT, STOP_HIT, TIME_EXIT, CLOSED
    profit_loss: float = 0.0
    profit_loss_percent: float = 0.0
    
    # Learning metrics
    market_condition: str = "neutral"  # bullish, bearish, neutral, volatile
    indicators_snapshot: Dict = field(default_factory=dict)
    
    def to_dict(self):
        return asdict(self)


@dataclass
class LearningSession:
    """جلسة تعلم"""
    id: str
    start_time: str
    end_time: Optional[str] = None
    
    # Session stats
    stocks_processed: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Performance metrics
    win_rate: float = 0.0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Learning outcomes
    best_strategies: List[Dict] = field(default_factory=list)
    parameter_adjustments: Dict = field(default_factory=dict)
    
    def to_dict(self):
        return {
            "id": self.id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "stocks_processed": self.stocks_processed,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 2),
            "avg_profit": round(self.avg_profit, 4),
            "avg_loss": round(self.avg_loss, 4),
            "profit_factor": round(self.profit_factor, 2),
            "best_strategies": self.best_strategies,
            "parameter_adjustments": self.parameter_adjustments
        }


@dataclass
class StrategyParameters:
    """معاملات الاستراتيجية"""
    name: str
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    ma_short: int = 20
    ma_long: int = 50
    target_percent: float = 5.0
    stop_loss_percent: float = 3.0
    min_confidence: float = 60.0
    max_holding_days: int = 30
    
    # Performance tracking
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    total_profit: float = 0.0


# ============================================================================
# ITERATIVE LEARNING ENGINE
# ============================================================================

class IterativeLearningEngine:
    """محرك التعلم التكراري"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self.conn = None
        
        # Strategy parameters to optimize
        self.strategies = [
            StrategyParameters(name="conservative", target_percent=3.0, stop_loss_percent=2.0, min_confidence=70.0),
            StrategyParameters(name="moderate", target_percent=5.0, stop_loss_percent=3.0, min_confidence=60.0),
            StrategyParameters(name="aggressive", target_percent=8.0, stop_loss_percent=5.0, min_confidence=50.0),
            StrategyParameters(name="momentum", target_percent=6.0, stop_loss_percent=4.0, min_confidence=65.0),
            StrategyParameters(name="mean_reversion", target_percent=4.0, stop_loss_percent=2.5, min_confidence=55.0),
        ]
        
        # Learning parameters
        self.learning_rate = 0.1
        self.min_trades_for_learning = 100
        
        self._connect_db()
    
    def _connect_db(self):
        """Connect to database"""
        if os.path.exists(self.db_path):
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self._ensure_tables()
    
    def _ensure_tables(self):
        """Ensure required tables exist"""
        cursor = self.conn.cursor()
        
        # Simulated trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS simulated_trades (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_date TEXT,
                exit_price REAL,
                signal TEXT DEFAULT 'BUY',
                confidence REAL DEFAULT 0,
                strategy TEXT DEFAULT 'technical',
                target_percent REAL DEFAULT 5.0,
                stop_loss_percent REAL DEFAULT 3.0,
                holding_days INTEGER DEFAULT 0,
                status TEXT DEFAULT 'OPEN',
                profit_loss REAL DEFAULT 0,
                profit_loss_percent REAL DEFAULT 0,
                market_condition TEXT DEFAULT 'neutral',
                indicators_snapshot TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Learning sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_sessions (
                id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                stocks_processed INTEGER DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                avg_profit REAL DEFAULT 0,
                avg_loss REAL DEFAULT 0,
                profit_factor REAL DEFAULT 0,
                best_strategies TEXT,
                parameter_adjustments TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Optimized parameters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimized_parameters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                strategy TEXT NOT NULL,
                optimal_target REAL,
                optimal_stop_loss REAL,
                optimal_confidence REAL,
                win_rate REAL,
                total_trades INTEGER,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, strategy)
            )
        ''')
        
        self.conn.commit()
    
    def get_price_history(self, symbol: str, days: int = 365) -> List[Dict]:
        """Get historical prices for a symbol"""
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT date, open, high, low, close, volume
            FROM DailyPrice
            WHERE symbol = ?
            ORDER BY date ASC
            LIMIT ?
        ''', (symbol.upper(), days))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_all_symbols(self) -> List[str]:
        """Get all symbols with historical data"""
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT symbol FROM DailyPrice ORDER BY symbol')
        return [row[0] for row in cursor.fetchall()]
    
    def calculate_indicators(self, prices: List[float]) -> Dict:
        """Calculate technical indicators"""
        if len(prices) < 50:
            return {}
        
        indicators = {}
        
        # RSI
        if len(prices) >= 15:
            deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            gains = [d if d > 0 else 0 for d in deltas[-14:]]
            losses = [-d if d < 0 else 0 for d in deltas[-14:]]
            avg_gain = sum(gains) / 14
            avg_loss = sum(losses) / 14
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                indicators['rsi'] = 100 - (100 / (1 + rs))
            else:
                indicators['rsi'] = 100
        
        # Moving Averages
        indicators['sma_20'] = sum(prices[-20:]) / 20 if len(prices) >= 20 else None
        indicators['sma_50'] = sum(prices[-50:]) / 50 if len(prices) >= 50 else None
        
        # Bollinger Bands
        if len(prices) >= 20:
            sma = indicators['sma_20']
            variance = sum((p - sma) ** 2 for p in prices[-20:]) / 20
            std = variance ** 0.5
            indicators['bb_upper'] = sma + 2 * std
            indicators['bb_lower'] = sma - 2 * std
        
        # Momentum
        if len(prices) >= 10:
            indicators['momentum'] = (prices[-1] - prices[-10]) / prices[-10] * 100
        
        # Volatility
        if len(prices) >= 20:
            returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(-20, 0)]
            indicators['volatility'] = statistics.stdev(returns) * 100 if len(returns) > 1 else 0
        
        return indicators
    
    def generate_signal(self, prices: List[float], indicators: Dict, strategy: StrategyParameters) -> Tuple[str, float, str]:
        """Generate trading signal based on strategy"""
        if len(prices) < 50 or not indicators:
            return "HOLD", 0, "insufficient_data"
        
        current_price = prices[-1]
        score = 0
        reasons = []
        
        # RSI signals
        rsi = indicators.get('rsi', 50)
        if rsi <= strategy.rsi_oversold:
            score += 2
            reasons.append("rsi_oversold")
        elif rsi >= strategy.rsi_overbought:
            score -= 2
            reasons.append("rsi_overbought")
        
        # Moving average signals
        sma_20 = indicators.get('sma_20')
        sma_50 = indicators.get('sma_50')
        if sma_20 and sma_50:
            if current_price > sma_20 > sma_50:
                score += 1
                reasons.append("bullish_ma_alignment")
            elif current_price < sma_20 < sma_50:
                score -= 1
                reasons.append("bearish_ma_alignment")
        
        # Bollinger Bands
        bb_lower = indicators.get('bb_lower')
        bb_upper = indicators.get('bb_upper')
        if bb_lower and current_price <= bb_lower:
            score += 1
            reasons.append("bb_lower_bounce")
        elif bb_upper and current_price >= bb_upper:
            score -= 1
            reasons.append("bb_upper_rejection")
        
        # Momentum
        momentum = indicators.get('momentum', 0)
        if momentum > 3:
            score += 1
            reasons.append("strong_momentum")
        elif momentum < -3:
            score -= 1
            reasons.append("weak_momentum")
        
        # Determine signal
        confidence = min(50 + abs(score) * 10, 95)
        market_condition = self._determine_market_condition(indicators)
        
        if score >= 2 and confidence >= strategy.min_confidence:
            return "BUY", confidence, ",".join(reasons)
        elif score <= -2 and confidence >= strategy.min_confidence:
            return "SELL", confidence, ",".join(reasons)
        else:
            return "HOLD", confidence, ",".join(reasons)
    
    def _determine_market_condition(self, indicators: Dict) -> str:
        """Determine market condition from indicators"""
        rsi = indicators.get('rsi', 50)
        momentum = indicators.get('momentum', 0)
        volatility = indicators.get('volatility', 0)
        
        if volatility > 3:
            return "volatile"
        elif momentum > 2 and rsi > 50:
            return "bullish"
        elif momentum < -2 and rsi < 50:
            return "bearish"
        else:
            return "neutral"
    
    def simulate_trade(self, symbol: str, history: List[Dict], strategy: StrategyParameters, 
                       start_idx: int) -> Optional[SimulatedTrade]:
        """Simulate a single trade on historical data"""
        if start_idx >= len(history) - 30:  # Need at least 30 days for holding
            return None
        
        # Get prices up to this point for signal generation
        prices = [h['close'] for h in history[:start_idx+1]]
        if len(prices) < 50:
            return None
        
        indicators = self.calculate_indicators(prices)
        signal, confidence, reasons = self.generate_signal(prices, indicators, strategy)
        
        if signal == "HOLD":
            return None
        
        # Create simulated trade
        entry_data = history[start_idx]
        entry_price = entry_data['close']
        entry_date = entry_data['date']
        
        trade_id = f"{symbol}_{entry_date}_{strategy.name}_{random.randint(1000, 9999)}"
        
        trade = SimulatedTrade(
            id=trade_id,
            symbol=symbol,
            entry_date=entry_date,
            entry_price=entry_price,
            signal=signal,
            confidence=confidence,
            strategy=strategy.name,
            target_percent=strategy.target_percent,
            stop_loss_percent=strategy.stop_loss_percent,
            market_condition=self._determine_market_condition(indicators),
            indicators_snapshot=indicators
        )
        
        # Simulate trade outcome
        if signal == "BUY":
            target_price = entry_price * (1 + strategy.target_percent / 100)
            stop_price = entry_price * (1 - strategy.stop_loss_percent / 100)
        else:  # SELL (short)
            target_price = entry_price * (1 - strategy.target_percent / 100)
            stop_price = entry_price * (1 + strategy.stop_loss_percent / 100)
        
        # Check each subsequent day
        for i in range(start_idx + 1, min(start_idx + strategy.max_holding_days + 1, len(history))):
            day_data = history[i]
            high = day_data['high']
            low = day_data['low']
            close = day_data['close']
            
            trade.holding_days = i - start_idx
            
            if signal == "BUY":
                if high >= target_price:
                    # Target hit
                    trade.exit_date = day_data['date']
                    trade.exit_price = target_price
                    trade.status = "TARGET_HIT"
                    break
                elif low <= stop_price:
                    # Stop loss hit
                    trade.exit_date = day_data['date']
                    trade.exit_price = stop_price
                    trade.status = "STOP_HIT"
                    break
            else:  # SELL
                if low <= target_price:
                    trade.exit_date = day_data['date']
                    trade.exit_price = target_price
                    trade.status = "TARGET_HIT"
                    break
                elif high >= stop_price:
                    trade.exit_date = day_data['date']
                    trade.exit_price = stop_price
                    trade.status = "STOP_HIT"
                    break
        else:
            # Time exit
            last_data = history[min(start_idx + strategy.max_holding_days, len(history) - 1)]
            trade.exit_date = last_data['date']
            trade.exit_price = last_data['close']
            trade.status = "TIME_EXIT"
        
        # Calculate profit/loss
        if trade.exit_price:
            if signal == "BUY":
                trade.profit_loss = trade.exit_price - entry_price
                trade.profit_loss_percent = (trade.profit_loss / entry_price) * 100
            else:  # SELL
                trade.profit_loss = entry_price - trade.exit_price
                trade.profit_loss_percent = (trade.profit_loss / entry_price) * 100
        
        return trade
    
    def run_learning_iteration(self, symbol: str, strategy: StrategyParameters, 
                               num_trades: int = 50) -> List[SimulatedTrade]:
        """Run learning iteration for a symbol with a strategy"""
        history = self.get_price_history(symbol, 365)
        
        if len(history) < 100:
            return []
        
        trades = []
        random.seed(42 + hash(symbol))  # Reproducible randomness
        
        # Generate trades at random points in history
        possible_starts = list(range(50, len(history) - 30))
        random.shuffle(possible_starts)
        
        for start_idx in possible_starts[:num_trades]:
            trade = self.simulate_trade(symbol, history, strategy, start_idx)
            if trade:
                trades.append(trade)
        
        return trades
    
    def save_trades(self, trades: List[SimulatedTrade]):
        """Save trades to database"""
        if not self.conn or not trades:
            return
        
        cursor = self.conn.cursor()
        
        for trade in trades:
            cursor.execute('''
                INSERT OR REPLACE INTO simulated_trades 
                (id, symbol, entry_date, entry_price, exit_date, exit_price, 
                 signal, confidence, strategy, target_percent, stop_loss_percent,
                 holding_days, status, profit_loss, profit_loss_percent,
                 market_condition, indicators_snapshot, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade.id, trade.symbol, trade.entry_date, trade.entry_price,
                trade.exit_date, trade.exit_price, trade.signal, trade.confidence,
                trade.strategy, trade.target_percent, trade.stop_loss_percent,
                trade.holding_days, trade.status, trade.profit_loss, 
                trade.profit_loss_percent, trade.market_condition,
                json.dumps(trade.indicators_snapshot), datetime.now().isoformat()
            ))
        
        self.conn.commit()
    
    def analyze_trades(self, trades: List[SimulatedTrade]) -> Dict:
        """Analyze trade performance"""
        if not trades:
            return {}
        
        wins = [t for t in trades if t.profit_loss > 0]
        losses = [t for t in trades if t.profit_loss <= 0]
        
        total_trades = len(trades)
        winning_trades = len(wins)
        losing_trades = len(losses)
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        avg_profit = statistics.mean([t.profit_loss_percent for t in wins]) if wins else 0
        avg_loss = statistics.mean([t.profit_loss_percent for t in losses]) if losses else 0
        
        total_profit = sum(t.profit_loss_percent for t in wins)
        total_loss = abs(sum(t.profit_loss_percent for t in losses))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        # Analyze by market condition
        by_condition = {}
        for trade in trades:
            cond = trade.market_condition
            if cond not in by_condition:
                by_condition[cond] = {'trades': 0, 'wins': 0, 'profit': 0}
            by_condition[cond]['trades'] += 1
            if trade.profit_loss > 0:
                by_condition[cond]['wins'] += 1
            by_condition[cond]['profit'] += trade.profit_loss_percent
        
        # Analyze by strategy
        by_strategy = {}
        for trade in trades:
            strat = trade.strategy
            if strat not in by_strategy:
                by_strategy[strat] = {'trades': 0, 'wins': 0, 'profit': 0}
            by_strategy[strat]['trades'] += 1
            if trade.profit_loss > 0:
                by_strategy[strat]['wins'] += 1
            by_strategy[strat]['profit'] += trade.profit_loss_percent
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'avg_profit': round(avg_profit, 4),
            'avg_loss': round(avg_loss, 4),
            'profit_factor': round(profit_factor, 2),
            'by_condition': by_condition,
            'by_strategy': by_strategy
        }
    
    def optimize_parameters(self, symbol: str, trades: List[SimulatedTrade]) -> Dict:
        """Optimize parameters based on trade results"""
        if not trades or len(trades) < self.min_trades_for_learning:
            return {}
        
        analysis = self.analyze_trades(trades)
        
        # Find best performing strategy
        by_strategy = analysis.get('by_strategy', {})
        best_strategy = None
        best_win_rate = 0
        
        for strat_name, strat_stats in by_strategy.items():
            strat_win_rate = strat_stats['wins'] / strat_stats['trades'] * 100 if strat_stats['trades'] > 0 else 0
            if strat_win_rate > best_win_rate:
                best_win_rate = strat_win_rate
                best_strategy = strat_name
        
        # Find best market conditions
        by_condition = analysis.get('by_condition', {})
        best_conditions = []
        for cond, stats in by_condition.items():
            cond_win_rate = stats['wins'] / stats['trades'] * 100 if stats['trades'] > 0 else 0
            if cond_win_rate > 50:
                best_conditions.append(cond)
        
        # Calculate optimal target/stop based on actual performance
        avg_win = analysis['avg_profit']
        avg_loss = abs(analysis['avg_loss'])
        
        # Kelly criterion for optimal position sizing
        if avg_loss > 0:
            win_prob = analysis['win_rate'] / 100
            kelly = (win_prob * avg_win - (1 - win_prob) * avg_loss) / avg_win
            kelly = max(0, min(kelly, 0.25))  # Cap at 25%
        else:
            kelly = 0
        
        optimizations = {
            'symbol': symbol,
            'best_strategy': best_strategy,
            'best_win_rate': round(best_win_rate, 2),
            'best_conditions': best_conditions,
            'optimal_target': round(avg_win * 1.2, 2),  # 20% above average win
            'optimal_stop_loss': round(avg_loss * 0.8, 2),  # 20% below average loss
            'kelly_fraction': round(kelly, 4),
            'total_trades_analyzed': len(trades)
        }
        
        # Save to database
        if self.conn and best_strategy:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO optimized_parameters
                (symbol, strategy, optimal_target, optimal_stop_loss, optimal_confidence, 
                 win_rate, total_trades, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, best_strategy, optimizations['optimal_target'],
                  optimizations['optimal_stop_loss'], analysis['win_rate'],
                  best_win_rate, len(trades), datetime.now().isoformat()))
            self.conn.commit()
        
        return optimizations
    
    def run_full_learning_session(self, iterations_per_stock: int = 100) -> LearningSession:
        """Run full learning session across all stocks"""
        session = LearningSession(
            id=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            start_time=datetime.now().isoformat()
        )
        
        symbols = self.get_all_symbols()
        all_trades = []
        
        print(f"\n{'='*60}")
        print(f"🎓 Starting Learning Session: {session.id}")
        print(f"{'='*60}")
        print(f"Stocks to process: {len(symbols)}")
        print(f"Iterations per stock: {iterations_per_stock}")
        print(f"Strategies: {len(self.strategies)}")
        print(f"{'='*60}\n")
        
        for i, symbol in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] Processing {symbol}...", end=" ")
            
            for strategy in self.strategies:
                trades = self.run_learning_iteration(symbol, strategy, iterations_per_stock)
                all_trades.extend(trades)
            
            session.stocks_processed += 1
            print(f"✅ Total trades: {len(all_trades)}")
        
        # Save all trades
        print(f"\n💾 Saving {len(all_trades)} trades...")
        self.save_trades(all_trades)
        
        # Analyze results
        print(f"📊 Analyzing results...")
        analysis = self.analyze_trades(all_trades)
        
        session.end_time = datetime.now().isoformat()
        session.total_trades = analysis.get('total_trades', 0)
        session.winning_trades = analysis.get('winning_trades', 0)
        session.losing_trades = analysis.get('losing_trades', 0)
        session.win_rate = analysis.get('win_rate', 0)
        session.avg_profit = analysis.get('avg_profit', 0)
        session.avg_loss = analysis.get('avg_loss', 0)
        session.profit_factor = analysis.get('profit_factor', 0)
        
        # Find best strategies
        by_strategy = analysis.get('by_strategy', {})
        strategy_rankings = []
        for strat_name, stats in by_strategy.items():
            win_rate = stats['wins'] / stats['trades'] * 100 if stats['trades'] > 0 else 0
            strategy_rankings.append({
                'strategy': strat_name,
                'win_rate': round(win_rate, 2),
                'trades': stats['trades'],
                'total_profit': round(stats['profit'], 2)
            })
        
        session.best_strategies = sorted(strategy_rankings, key=lambda x: x['win_rate'], reverse=True)
        
        # Save session
        if self.conn:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO learning_sessions
                (id, start_time, end_time, stocks_processed, total_trades,
                 winning_trades, losing_trades, win_rate, avg_profit, avg_loss,
                 profit_factor, best_strategies, parameter_adjustments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session.id, session.start_time, session.end_time,
                session.stocks_processed, session.total_trades,
                session.winning_trades, session.losing_trades,
                session.win_rate, session.avg_profit, session.avg_loss,
                session.profit_factor, json.dumps(session.best_strategies), '{}'
            ))
            self.conn.commit()
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"🎓 Learning Session Complete!")
        print(f"{'='*60}")
        print(f"Stocks processed: {session.stocks_processed}")
        print(f"Total trades: {session.total_trades}")
        print(f"Winning trades: {session.winning_trades}")
        print(f"Losing trades: {session.losing_trades}")
        print(f"Win rate: {session.win_rate}%")
        print(f"Profit factor: {session.profit_factor}")
        print(f"\n🏆 Best Strategies:")
        for strat in session.best_strategies[:3]:
            print(f"  {strat['strategy']}: {strat['win_rate']}% win rate")
        print(f"{'='*60}\n")
        
        return session
    
    def get_optimized_parameters(self, symbol: str) -> Optional[Dict]:
        """Get optimized parameters for a symbol"""
        if not self.conn:
            return None
        
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT strategy, optimal_target, optimal_stop_loss, 
                   optimal_confidence, win_rate, total_trades
            FROM optimized_parameters
            WHERE symbol = ?
            ORDER BY win_rate DESC
            LIMIT 1
        ''', (symbol.upper(),))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def get_learning_status(self) -> Dict:
        """Get current learning status"""
        if not self.conn:
            return {'error': 'No database connection'}
        
        cursor = self.conn.cursor()
        
        # Count trades
        cursor.execute('SELECT COUNT(*) FROM simulated_trades')
        total_trades = cursor.fetchone()[0]
        
        # Count winning trades
        cursor.execute('SELECT COUNT(*) FROM simulated_trades WHERE profit_loss > 0')
        winning_trades = cursor.fetchone()[0]
        
        # Count by strategy
        cursor.execute('''
            SELECT strategy, COUNT(*) as count, 
                   SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as wins
            FROM simulated_trades
            GROUP BY strategy
            ORDER BY count DESC
        ''')
        by_strategy = [dict(row) for row in cursor.fetchall()]
        
        # Get latest session
        cursor.execute('''
            SELECT * FROM learning_sessions
            ORDER BY start_time DESC
            LIMIT 1
        ''')
        latest_session = cursor.fetchone()
        
        # Get symbols with optimized parameters
        cursor.execute('SELECT COUNT(DISTINCT symbol) FROM optimized_parameters')
        optimized_symbols = cursor.fetchone()[0]
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': round(winning_trades / total_trades * 100, 2) if total_trades > 0 else 0,
            'by_strategy': by_strategy,
            'optimized_symbols': optimized_symbols,
            'latest_session': dict(latest_session) if latest_session else None
        }
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Iterative Learning Engine")
    parser.add_argument("--learn-all", action="store_true", help="Run full learning session")
    parser.add_argument("--stock", type=str, help="Learn for single stock")
    parser.add_argument("--iterations", type=int, default=100, help="Iterations per stock")
    parser.add_argument("--status", action="store_true", help="Show learning status")
    parser.add_argument("--optimize", type=str, help="Get optimized parameters for a stock")
    
    args = parser.parse_args()
    
    engine = IterativeLearningEngine()
    
    try:
        if args.status:
            status = engine.get_learning_status()
            print(json.dumps(status, indent=2))
        
        elif args.optimize:
            params = engine.get_optimized_parameters(args.optimize)
            if params:
                print(json.dumps(params, indent=2))
            else:
                print(f"No optimized parameters found for {args.optimize}")
        
        elif args.learn_all:
            session = engine.run_full_learning_session(args.iterations)
            print(f"\nSession completed: {session.id}")
        
        elif args.stock:
            print(f"Learning for {args.stock}...")
            all_trades = []
            for strategy in engine.strategies:
                trades = engine.run_learning_iteration(args.stock, strategy, args.iterations)
                all_trades.extend(trades)
            
            engine.save_trades(all_trades)
            analysis = engine.analyze_trades(all_trades)
            optimizations = engine.optimize_parameters(args.stock, all_trades)
            
            print(f"\nResults for {args.stock}:")
            print(json.dumps(analysis, indent=2))
            print(f"\nOptimizations:")
            print(json.dumps(optimizations, indent=2))
        
        else:
            parser.print_help()
    
    finally:
        engine.close()


if __name__ == "__main__":
    main()
