#!/usr/bin/env python3
"""
Backtesting Engine
==================
نظام الاختبار الخلفي لتقييم التوصيات

Features:
1. اختبار التوصيات على البيانات التاريخية
2. حساب نسبة النجاح
3. مقارنة أداء AI مقابل الخبراء
4. تحسين المعاملات بناءً على النتائج
5. تقارير أداء مفصلة

Usage:
    python backtest_engine.py --stock COMI --days 90
    python backtest_engine.py --all-popular --days 180
    python backtest_engine.py --compare-expert EHDR,CCAM,CCAP
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
import statistics

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class BacktestTrade:
    """صفقة في الاختبار الخلفي"""
    entry_date: str
    entry_price: float
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    signal: str = "BUY"
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    
    # Results
    status: str = "OPEN"  # OPEN, TARGET_HIT, STOP_HIT, TIME_EXIT
    profit_loss: float = 0.0
    profit_loss_percent: float = 0.0
    holding_days: int = 0
    
@dataclass
class BacktestResult:
    """نتيجة الاختبار الخلفي"""
    symbol: str
    start_date: str
    end_date: str
    
    # Trades
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Performance
    total_return: float = 0.0
    average_return: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    
    # Risk
    max_drawdown: float = 0.0
    average_holding_days: float = 0.0
    sharpe_ratio: Optional[float] = None
    
    # Trades list
    trades: List[BacktestTrade] = field(default_factory=list)
    
    def to_dict(self):
        return {
            "symbol": self.symbol,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_return": round(self.total_return, 2),
            "average_return": round(self.average_return, 2),
            "win_rate": round(self.win_rate, 2),
            "profit_factor": round(self.profit_factor, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "average_holding_days": round(self.average_holding_days, 1),
            "sharpe_ratio": round(self.sharpe_ratio, 2) if self.sharpe_ratio else None
        }

@dataclass
class ExpertRecommendation:
    """توصية خبير"""
    symbol: str
    expert_name: str
    recommendation_date: str
    action: str  # BUY, SELL
    entry_price: float
    target_price: float
    stop_loss: float
    timeframe_days: int = 30
    notes: str = ""

@dataclass
class ExpertVerification:
    """نتيجة التحقق من توصية خبير"""
    symbol: str
    expert_name: str
    recommendation: ExpertRecommendation
    
    # Current status
    current_price: float
    status: str  # SUCCESS, STOPPED, PENDING, TIME_EXPIRED
    
    # Performance
    profit_loss_percent: float
    days_elapsed: int
    max_profit_reached: float
    max_loss_reached: float
    
    # AI comparison
    ai_signal: str
    ai_confidence: float
    ai_agreement: bool  # True if AI agreed with expert

# ============================================================================
# BACKTEST ENGINE
# ============================================================================

class BacktestEngine:
    """محرك الاختبار الخلفي"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.conn = None
        
        if db_path and os.path.exists(db_path):
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
    
    def run_backtest(self, symbol: str, days: int = 180, 
                     initial_capital: float = 10000) -> Optional[BacktestResult]:
        """تشغيل الاختبار الخلفي"""
        
        if not self.conn:
            return None
        
        # Get price history
        cursor = self.conn.cursor()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        cursor.execute('''
            SELECT sph.date, sph.open_price, sph.high_price, sph.low_price, sph.close_price, sph.volume
            FROM stock_price_history sph
            JOIN stocks s ON sph.stock_id = s.id
            WHERE s.ticker = ? AND sph.date >= ?
            ORDER BY sph.date ASC
        ''', (symbol.upper(), start_date.strftime('%Y-%m-%d')))
        
        rows = cursor.fetchall()
        
        if len(rows) < 50:
            return None
        
        # Convert to list of dicts
        history = [dict(row) for row in rows]
        
        result = BacktestResult(
            symbol=symbol,
            start_date=history[0]['date'],
            end_date=history[-1]['date']
        )
        
        # Simulate trading
        capital = initial_capital
        trades = []
        current_trade = None
        equity_curve = [capital]
        
        for i in range(50, len(history)):
            current_data = history[i]
            current_price = current_data['close_price']
            current_date = current_data['date']
            
            # Get historical prices up to this point
            prices = [h['close_price'] for h in history[:i]]
            
            # Generate signal
            signal = self._generate_signal(prices)
            
            # If we have an open trade, check for exit
            if current_trade:
                # Check target
                if current_trade.signal == "BUY":
                    if current_price >= current_trade.target_price:
                        current_trade.exit_date = current_date
                        current_trade.exit_price = current_price
                        current_trade.status = "TARGET_HIT"
                        current_trade.profit_loss = current_trade.exit_price - current_trade.entry_price
                        current_trade.profit_loss_percent = (current_trade.profit_loss / current_trade.entry_price) * 100
                        trades.append(current_trade)
                        current_trade = None
                    elif current_price <= current_trade.stop_loss:
                        current_trade.exit_date = current_date
                        current_trade.exit_price = current_price
                        current_trade.status = "STOP_HIT"
                        current_trade.profit_loss = current_trade.exit_price - current_trade.entry_price
                        current_trade.profit_loss_percent = (current_trade.profit_loss / current_trade.entry_price) * 100
                        trades.append(current_trade)
                        current_trade = None
                    elif (datetime.strptime(current_date, '%Y-%m-%d') - 
                          datetime.strptime(current_trade.entry_date, '%Y-%m-%d')).days > 30:
                        current_trade.exit_date = current_date
                        current_trade.exit_price = current_price
                        current_trade.status = "TIME_EXIT"
                        current_trade.profit_loss = current_trade.exit_price - current_trade.entry_price
                        current_trade.profit_loss_percent = (current_trade.profit_loss / current_trade.entry_price) * 100
                        trades.append(current_trade)
                        current_trade = None
            
            # Open new trade if no current trade
            if not current_trade and signal['action'] == "BUY":
                support = min(prices[-20:])
                resistance = max(prices[-20:])
                
                current_trade = BacktestTrade(
                    entry_date=current_date,
                    entry_price=current_price,
                    signal="BUY",
                    target_price=resistance,
                    stop_loss=support * 0.98
                )
            
            # Update equity curve
            if current_trade:
                unrealized_pl = (current_price - current_trade.entry_price) / current_trade.entry_price * capital
                equity_curve.append(capital + unrealized_pl)
            else:
                equity_curve.append(capital)
        
        # Close any remaining trade
        if current_trade:
            current_trade.exit_date = history[-1]['date']
            current_trade.exit_price = history[-1]['close_price']
            current_trade.status = "TIME_EXIT"
            current_trade.profit_loss = current_trade.exit_price - current_trade.entry_price
            current_trade.profit_loss_percent = (current_trade.profit_loss / current_trade.entry_price) * 100
            trades.append(current_trade)
        
        # Calculate statistics
        result.trades = trades
        result.total_trades = len(trades)
        
        if trades:
            result.winning_trades = len([t for t in trades if t.profit_loss > 0])
            result.losing_trades = len([t for t in trades if t.profit_loss <= 0])
            result.win_rate = (result.winning_trades / result.total_trades) * 100
            
            returns = [t.profit_loss_percent for t in trades]
            result.total_return = sum(returns)
            result.average_return = statistics.mean(returns) if returns else 0
            
            # Calculate profit factor
            profits = [t.profit_loss_percent for t in trades if t.profit_loss_percent > 0]
            losses = [abs(t.profit_loss_percent) for t in trades if t.profit_loss_percent < 0]
            
            if losses:
                result.profit_factor = sum(profits) / sum(losses) if sum(losses) > 0 else 0
            else:
                result.profit_factor = sum(profits) if profits else 0
            
            # Calculate max drawdown
            peak = equity_curve[0]
            max_dd = 0
            for eq in equity_curve:
                if eq > peak:
                    peak = eq
                dd = (peak - eq) / peak * 100
                if dd > max_dd:
                    max_dd = dd
            result.max_drawdown = max_dd
            
            # Average holding days
            holding_days = []
            for t in trades:
                if t.entry_date and t.exit_date:
                    days = (datetime.strptime(t.exit_date, '%Y-%m-%d') - 
                            datetime.strptime(t.entry_date, '%Y-%m-%d')).days
                    holding_days.append(days)
            result.average_holding_days = statistics.mean(holding_days) if holding_days else 0
        
        return result
    
    def _generate_signal(self, prices: List[float]) -> Dict:
        """Generate trading signal from prices"""
        if len(prices) < 50:
            return {"action": "HOLD", "confidence": 0}
        
        score = 0
        
        # RSI
        rsi = self._calculate_rsi(prices, 14)
        if rsi:
            if rsi <= 30:
                score += 2
            elif rsi <= 40:
                score += 1
            elif rsi >= 70:
                score -= 2
            elif rsi >= 60:
                score -= 1
        
        # Moving Averages
        sma_20 = sum(prices[-20:]) / 20
        sma_50 = sum(prices[-50:]) / 50
        current_price = prices[-1]
        
        if current_price > sma_20 > sma_50:
            score += 1
        elif current_price < sma_20 < sma_50:
            score -= 1
        
        # Bollinger Bands position
        sma = sum(prices[-20:]) / 20
        variance = sum((p - sma) ** 2 for p in prices[-20:]) / 20
        std = variance ** 0.5
        lower = sma - 2 * std
        
        if current_price <= lower:
            score += 1
        
        # Determine action
        if score >= 2:
            return {"action": "BUY", "confidence": min(70 + score * 5, 95)}
        elif score <= -2:
            return {"action": "SELL", "confidence": min(70 + abs(score) * 5, 95)}
        else:
            return {"action": "HOLD", "confidence": 50}
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
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
        return 100 - (100 / (1 + rs))
    
    def verify_expert_recommendation(self, rec: ExpertRecommendation) -> Optional[ExpertVerification]:
        """التحقق من توصية خبير"""
        if not self.conn:
            return None
        
        cursor = self.conn.cursor()
        
        # Get current price
        cursor.execute('''
            SELECT current_price FROM stocks WHERE ticker = ?
        ''', (rec.symbol.upper(),))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        current_price = row['current_price']
        
        # Get price history since recommendation
        cursor.execute('''
            SELECT sph.date, sph.high_price, sph.low_price, sph.close_price
            FROM stock_price_history sph
            JOIN stocks s ON sph.stock_id = s.id
            WHERE s.ticker = ? AND sph.date >= ?
            ORDER BY sph.date ASC
        ''', (rec.symbol.upper(), rec.recommendation_date))
        
        history = [dict(r) for r in cursor.fetchall()]
        
        # Calculate performance
        profit_loss_percent = ((current_price - rec.entry_price) / rec.entry_price) * 100
        
        # Check max profit/loss reached
        max_profit = 0
        max_loss = 0
        
        for h in history:
            profit_pct = ((h['high_price'] - rec.entry_price) / rec.entry_price) * 100
            loss_pct = ((rec.entry_price - h['low_price']) / rec.entry_price) * 100
            
            if profit_pct > max_profit:
                max_profit = profit_pct
            if loss_pct > max_loss:
                max_loss = loss_pct
        
        # Determine status
        if current_price >= rec.target_price:
            status = "SUCCESS"
        elif current_price <= rec.stop_loss:
            status = "STOPPED"
        else:
            days_elapsed = (datetime.now() - datetime.strptime(rec.recommendation_date, '%Y-%m-%d')).days
            if days_elapsed > rec.timeframe_days:
                status = "TIME_EXPIRED"
            else:
                status = "PENDING"
        
        # Get AI signal for comparison
        prices = [h['close_price'] for h in history] if history else []
        ai_signal_data = self._generate_signal(prices) if len(prices) >= 50 else {"action": "HOLD", "confidence": 0}
        
        return ExpertVerification(
            symbol=rec.symbol,
            expert_name=rec.expert_name,
            recommendation=rec,
            current_price=current_price,
            status=status,
            profit_loss_percent=profit_loss_percent,
            days_elapsed=(datetime.now() - datetime.strptime(rec.recommendation_date, '%Y-%m-%d')).days,
            max_profit_reached=max_profit,
            max_loss_reached=max_loss,
            ai_signal=ai_signal_data['action'],
            ai_confidence=ai_signal_data['confidence'],
            ai_agreement=(ai_signal_data['action'] == rec.action)
        )
    
    def compare_strategies(self, symbol: str, days: int = 180) -> Dict:
        """مقارنة استراتيجيات مختلفة"""
        results = {}
        
        # Run backtest
        backtest_result = self.run_backtest(symbol, days)
        if backtest_result:
            results['backtest'] = backtest_result.to_dict()
        
        # Buy and hold comparison
        if self.conn:
            cursor = self.conn.cursor()
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            cursor.execute('''
                SELECT sph.close_price 
                FROM stock_price_history sph
                JOIN stocks s ON sph.stock_id = s.id
                WHERE s.ticker = ? AND sph.date >= ?
                ORDER BY sph.date ASC
            ''', (symbol.upper(), start_date.strftime('%Y-%m-%d')))
            
            rows = cursor.fetchall()
            if len(rows) >= 2:
                start_price = rows[0]['close_price']
                end_price = rows[-1]['close_price']
                buy_hold_return = ((end_price - start_price) / start_price) * 100
                
                results['buy_and_hold'] = {
                    'return': round(buy_hold_return, 2),
                    'start_price': start_price,
                    'end_price': end_price
                }
        
        return results
    
    def batch_backtest(self, symbols: List[str], days: int = 180) -> List[BacktestResult]:
        """اختبار مجموعة من الأسهم"""
        results = []
        
        for symbol in symbols:
            try:
                result = self.run_backtest(symbol, days)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"Error backtesting {symbol}: {e}")
        
        return results
    
    def generate_performance_report(self, results: List[BacktestResult]) -> Dict:
        """توليد تقرير أداء"""
        if not results:
            return {"error": "No results to analyze"}
        
        total_trades = sum(r.total_trades for r in results)
        total_winning = sum(r.winning_trades for r in results)
        total_losing = sum(r.losing_trades for r in results)
        
        returns = [r.total_return for r in results]
        win_rates = [r.win_rate for r in results if r.total_trades > 0]
        
        return {
            "summary": {
                "stocks_tested": len(results),
                "total_trades": total_trades,
                "total_winning": total_winning,
                "total_losing": total_losing,
                "overall_win_rate": round((total_winning / total_trades * 100) if total_trades > 0 else 0, 2),
                "average_return": round(statistics.mean(returns), 2) if returns else 0,
                "median_return": round(statistics.median(returns), 2) if returns else 0,
                "best_return": round(max(returns), 2) if returns else 0,
                "worst_return": round(min(returns), 2) if returns else 0,
                "average_win_rate": round(statistics.mean(win_rates), 2) if win_rates else 0
            },
            "top_performers": [
                {"symbol": r.symbol, "return": round(r.total_return, 2), "win_rate": round(r.win_rate, 2)}
                for r in sorted(results, key=lambda x: x.total_return, reverse=True)[:5]
            ],
            "worst_performers": [
                {"symbol": r.symbol, "return": round(r.total_return, 2), "win_rate": round(r.win_rate, 2)}
                for r in sorted(results, key=lambda x: x.total_return)[:5]
            ]
        }

# ============================================================================
# CLI
# ============================================================================

def print_backtest_result(result: BacktestResult):
    """Print backtest result"""
    print(f"\n{'='*60}")
    print(f" 📊 نتيجة الاختبار الخلفي: {result.symbol}")
    print(f"{'='*60}")
    
    print(f"\n 📅 الفترة: {result.start_date} إلى {result.end_date}")
    
    print(f"\n 📈 إحصائيات التداول:")
    print(f"    إجمالي الصفقات: {result.total_trades}")
    print(f"    صفقات رابحة: {result.winning_trades}")
    print(f"    صفقات خاسرة: {result.losing_trades}")
    print(f"    نسبة النجاح: {result.win_rate:.1f}%")
    
    print(f"\n 💰 الأداء:")
    print(f"    العائد الكلي: {result.total_return:.2f}%")
    print(f"    متوسط العائد: {result.average_return:.2f}%")
    print(f"    معامل الربح: {result.profit_factor:.2f}")
    
    print(f"\n ⚠️ المخاطر:")
    print(f"    أقصى خسارة: {result.max_drawdown:.2f}%")
    print(f"    متوسط أيام الاحتفاظ: {result.average_holding_days:.1f}")
    
    if result.trades:
        print(f"\n 📋 آخر 5 صفقات:")
        for trade in result.trades[-5:]:
            status_emoji = "✅" if trade.status == "TARGET_HIT" else "❌" if trade.status == "STOP_HIT" else "⏳"
            pl_emoji = "📈" if trade.profit_loss_percent > 0 else "📉"
            print(f"    {status_emoji} {trade.entry_date}: {trade.entry_price:.2f} → {trade.exit_price:.2f} ({pl_emoji} {trade.profit_loss_percent:.2f}%)")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="نظام الاختبار الخلفي")
    parser.add_argument("--stock", type=str, help="رمز السهم")
    parser.add_argument("--days", type=int, default=180, help="عدد الأيام")
    parser.add_argument("--all-popular", action="store_true", help="اختبار الأسهم الشائعة")
    parser.add_argument("--compare-expert", type=str, help="مقارنة مع توصيات خبير")
    
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
    
    engine = BacktestEngine(db_path)
    
    try:
        if args.stock:
            result = engine.run_backtest(args.stock, args.days)
            if result:
                print_backtest_result(result)
            else:
                print(f"لا توجد بيانات كافية لـ {args.stock}")
        
        elif args.all_popular:
            popular = ["COMI", "HRHO", "SWDY", "ETEL", "EKHO", "TMGH", "PHDC", "GTHE",
                       "ESRS", "ORHD", "CIEB", "AMER", "HELI", "OCDI", "JUFO", "ABUK"]
            
            print(f"\n{'='*60}")
            print(f" 🏆 اختبار {len(popular)} سهم شائع")
            print(f"{'='*60}")
            
            results = engine.batch_backtest(popular, args.days)
            report = engine.generate_performance_report(results)
            
            print(f"\n📊 ملخص الأداء:")
            summary = report['summary']
            print(f"    الأسهم المختبرة: {summary['stocks_tested']}")
            print(f"    إجمالي الصفقات: {summary['total_trades']}")
            print(f"    نسبة النجاح الكلية: {summary['overall_win_rate']}%")
            print(f"    متوسط العائد: {summary['average_return']}%")
            
            print(f"\n🏆 أفضل 5 أسهم:")
            for p in report['top_performers']:
                print(f"    {p['symbol']}: {p['return']}% (نسبة نجاح: {p['win_rate']}%)")
            
            print(f"\n📉 أسوأ 5 أسهم:")
            for p in report['worst_performers']:
                print(f"    {p['symbol']}: {p['return']}% (نسبة نجاح: {p['win_rate']}%)")
        
        elif args.compare_expert:
            # Raymond's recommendations
            expert_recs = {
                "EHDR": {"entry": 2.35, "target": 2.48, "stop": 2.27},
                "CCAM": {"entry": 1.48, "target": 1.62, "stop": 1.45},
                "CCAP": {"entry": 4.73, "target": 4.93, "stop": 4.60}
            }
            
            print(f"\n{'='*60}")
            print(f" 🔍 التحقق من توصيات الخبير")
            print(f"{'='*60}")
            
            for symbol, rec_data in expert_recs.items():
                rec = ExpertRecommendation(
                    symbol=symbol,
                    expert_name="Raymond",
                    recommendation_date="2025-05-14",  # Example date
                    action="BUY",
                    entry_price=rec_data['entry'],
                    target_price=rec_data['target'],
                    stop_loss=rec_data['stop']
                )
                
                verification = engine.verify_expert_recommendation(rec)
                
                if verification:
                    status_emoji = "✅" if verification.status == "SUCCESS" else "❌" if verification.status == "STOPPED" else "⏳"
                    pl_emoji = "📈" if verification.profit_loss_percent > 0 else "📉"
                    
                    print(f"\n{symbol}:")
                    print(f"  الحالة: {status_emoji} {verification.status}")
                    print(f"  السعر الحالي: {verification.current_price:.2f}")
                    print(f"  الربح/الخسارة: {pl_emoji} {verification.profit_loss_percent:.2f}%")
                    print(f"  أقصى ربح وصل له: {verification.max_profit_reached:.2f}%")
                    print(f"  أقصى خسارة وصل لها: {verification.max_loss_reached:.2f}%")
                    print(f"  إشارة AI: {verification.ai_signal} ({verification.ai_confidence:.0f}% ثقة)")
                    print(f"  AI موافق: {'نعم' if verification.ai_agreement else 'لا'}")
                else:
                    print(f"\n{symbol}: غير موجود في قاعدة البيانات")
        
        else:
            parser.print_help()
    
    finally:
        if engine.conn:
            engine.conn.close()

if __name__ == "__main__":
    main()
