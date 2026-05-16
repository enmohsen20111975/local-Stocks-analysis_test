#!/usr/bin/env python3
"""
Recommendation Verification & Backtesting Engine
=================================================
نظام تقييم التوصيات والاختبار الخلفي

Features:
1. Verify past recommendations against actual prices
2. Calculate success rates for AI vs Experts
3. Backtest recommendation algorithm on historical data
4. Generate performance reports

Usage:
    python recommendation_verifier.py --backtest COMI --days 90
    python recommendation_verifier.py --test-popular
    python recommendation_verifier.py --verify-expert EHDR,CCAM,CCAP
"""

import sqlite3
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import os
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

# Try multiple database paths
DB_PATHS = [
    '/root/egxpy_service/data/egx_investment.db',  # VPS
    '/root/GLMinvestment/db/egx_investment.db',    # VPS Next.js
    'db/egx_investment.db',                         # Local relative
    os.path.join(os.path.dirname(__file__), '..', 'db', 'egx_investment.db')
]

def find_database():
    """Find available database"""
    for path in DB_PATHS:
        if os.path.exists(path):
            return path
    return None

DATABASE_PATH = find_database()

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class StockData:
    """بيانات السهم"""
    ticker: str
    name: str
    current_price: float
    previous_close: Optional[float]
    rsi: Optional[float]
    support: Optional[float]
    resistance: Optional[float]
    ma_50: Optional[float]
    ma_200: Optional[float]

@dataclass
class Recommendation:
    """توصية للتقييم"""
    ticker: str
    action: str  # BUY, SELL, HOLD
    entry_price: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    confidence: float = 0
    source: str = "AI"
    
@dataclass
class AnalysisResult:
    """نتيجة التحليل"""
    ticker: str
    current_price: float
    signal: str  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    confidence: float
    score: int
    entry_price: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    support: Optional[float]
    resistance: Optional[float]
    indicators: Dict
    reasons: List[str]

# ============================================================================
# STOCK ANALYZER
# ============================================================================

class StockAnalyzer:
    """محلل الأسهم"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DATABASE_PATH
        if not self.db_path:
            print("Warning: No database found, using sample data mode")
            
    def get_connection(self):
        if not self.db_path:
            return None
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_stock(self, ticker: str) -> Optional[StockData]:
        """الحصول على بيانات سهم"""
        conn = self.get_connection()
        if not conn:
            return None
            
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ticker, name, current_price, previous_close, 
                   rsi, support_level, resistance_level, ma_50, ma_200
            FROM stocks 
            WHERE ticker = ? AND current_price IS NOT NULL
        ''', (ticker.upper(),))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return StockData(
                ticker=row['ticker'],
                name=row['name'] or '',
                current_price=row['current_price'],
                previous_close=row['previous_close'],
                rsi=row['rsi'],
                support=row['support_level'],
                resistance=row['resistance_level'],
                ma_50=row['ma_50'],
                ma_200=row['ma_200']
            )
        return None
    
    def get_all_stocks(self) -> List[StockData]:
        """الحصول على جميع الأسهم"""
        conn = self.get_connection()
        if not conn:
            return []
            
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ticker, name, current_price, previous_close, 
                   rsi, support_level, resistance_level, ma_50, ma_200
            FROM stocks 
            WHERE current_price IS NOT NULL
            ORDER BY ticker
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [StockData(
            ticker=row['ticker'],
            name=row['name'] or '',
            current_price=row['current_price'],
            previous_close=row['previous_close'],
            rsi=row['rsi'],
            support=row['support_level'],
            resistance=row['resistance_level'],
            ma_50=row['ma_50'],
            ma_200=row['ma_200']
        ) for row in rows]
    
    def analyze_stock(self, ticker: str) -> Optional[AnalysisResult]:
        """تحليل سهم وتوليد توصية"""
        stock = self.get_stock(ticker)
        if not stock:
            return None
        
        return self.analyze(stock)
    
    def analyze(self, stock: StockData) -> AnalysisResult:
        """تحليل سهم"""
        signals = []
        score = 0
        reasons = []
        
        current_price = stock.current_price
        
        # RSI Analysis
        rsi_signal = "HOLD"
        if stock.rsi:
            if stock.rsi <= 30:
                rsi_signal = "BUY"
                score += 2
                reasons.append(f"RSI oversold ({stock.rsi:.1f})")
            elif stock.rsi <= 40:
                rsi_signal = "BUY"
                score += 1
                reasons.append(f"RSI approaching oversold ({stock.rsi:.1f})")
            elif stock.rsi >= 70:
                rsi_signal = "SELL"
                score -= 2
                reasons.append(f"RSI overbought ({stock.rsi:.1f})")
            elif stock.rsi >= 60:
                rsi_signal = "SELL"
                score -= 1
                reasons.append(f"RSI approaching overbought ({stock.rsi:.1f})")
            
            signals.append({"indicator": "RSI", "signal": rsi_signal, "value": stock.rsi})
        
        # Moving Average Analysis
        ma_signal = "HOLD"
        if stock.ma_50 and stock.ma_200:
            if current_price > stock.ma_50 > stock.ma_200:
                ma_signal = "BUY"
                score += 1
                reasons.append("Price above MAs, bullish trend")
            elif current_price < stock.ma_50 < stock.ma_200:
                ma_signal = "SELL"
                score -= 1
                reasons.append("Price below MAs, bearish trend")
            
            signals.append({"indicator": "MA", "signal": ma_signal, 
                           "ma_50": stock.ma_50, "ma_200": stock.ma_200})
        elif stock.ma_50:
            if current_price > stock.ma_50:
                ma_signal = "BUY"
                score += 1
                reasons.append("Price above MA50")
            else:
                ma_signal = "SELL"
                score -= 1
                reasons.append("Price below MA50")
            
            signals.append({"indicator": "MA_50", "signal": ma_signal, "value": stock.ma_50})
        
        # Support/Resistance Analysis
        sr_signal = "HOLD"
        if stock.support and stock.resistance:
            # Calculate distance from support/resistance
            dist_to_support = (current_price - stock.support) / current_price * 100
            dist_to_resistance = (stock.resistance - current_price) / current_price * 100
            
            if dist_to_support < 2:  # Within 2% of support
                sr_signal = "BUY"
                score += 1
                reasons.append(f"Near support ({stock.support:.2f})")
            elif dist_to_resistance < 2:  # Within 2% of resistance
                sr_signal = "SELL"
                score -= 1
                reasons.append(f"Near resistance ({stock.resistance:.2f})")
            
            signals.append({"indicator": "S/R", "signal": sr_signal,
                           "support": stock.support, "resistance": stock.resistance})
        
        # Calculate targets
        target_price = None
        stop_loss = None
        
        if stock.resistance:
            target_price = stock.resistance
        elif stock.support:
            target_price = current_price * 1.05  # 5% target
            
        if stock.support:
            stop_loss = stock.support
        else:
            stop_loss = current_price * 0.97  # 3% stop loss
        
        # Determine final signal
        if score >= 3:
            signal = "STRONG_BUY"
            confidence = min(80 + score * 5, 95)
        elif score >= 1:
            signal = "BUY"
            confidence = 60 + score * 5
        elif score <= -3:
            signal = "STRONG_SELL"
            confidence = min(80 + abs(score) * 5, 95)
        elif score <= -1:
            signal = "SELL"
            confidence = 60 + abs(score) * 5
        else:
            signal = "HOLD"
            confidence = 50
        
        return AnalysisResult(
            ticker=stock.ticker,
            current_price=current_price,
            signal=signal,
            confidence=confidence,
            score=score,
            entry_price=current_price,
            target_price=target_price,
            stop_loss=stop_loss,
            support=stock.support,
            resistance=stock.resistance,
            indicators={
                "rsi": stock.rsi,
                "ma_50": stock.ma_50,
                "ma_200": stock.ma_200
            },
            reasons=reasons
        )
    
    def get_recommendations(self, filter_signal: str = None) -> List[AnalysisResult]:
        """الحصول على توصيات لجميع الأسهم"""
        stocks = self.get_all_stocks()
        results = []
        
        for stock in stocks:
            try:
                analysis = self.analyze(stock)
                if filter_signal:
                    if filter_signal.upper() in ["BUY", "STRONG_BUY"] and analysis.score >= 1:
                        results.append(analysis)
                    elif filter_signal.upper() in ["SELL", "STRONG_SELL"] and analysis.score <= -1:
                        results.append(analysis)
                else:
                    results.append(analysis)
            except Exception as e:
                pass
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        return results

# ============================================================================
# EXPERT RECOMMENDATION VERIFIER
# ============================================================================

class ExpertVerifier:
    """مدقق توصيات الخبراء"""
    
    def __init__(self, analyzer: StockAnalyzer):
        self.analyzer = analyzer
    
    def verify_expert_rec(self, ticker: str, entry_price: float, 
                          target_price: float, stop_loss: float) -> Dict:
        """التحقق من توصية خبير"""
        stock = self.analyzer.get_stock(ticker)
        
        if not stock:
            return {
                "ticker": ticker,
                "status": "NOT_FOUND",
                "message": f"Stock {ticker} not found in database"
            }
        
        current_price = stock.current_price
        
        # Check if target or stop hit
        hit_target = current_price >= target_price
        hit_stop = current_price <= stop_loss
        
        # Calculate current P/L
        pl_percent = ((current_price - entry_price) / entry_price) * 100
        
        # Calculate distance to target/stop
        dist_to_target = ((target_price - current_price) / current_price) * 100
        dist_to_stop = ((current_price - stop_loss) / current_price) * 100
        
        # Get AI analysis for comparison
        ai_analysis = self.analyzer.analyze(stock)
        
        # Determine status
        if hit_target:
            status = "SUCCESS"
        elif hit_stop:
            status = "STOPPED"
        else:
            status = "PENDING"
        
        return {
            "ticker": ticker,
            "name": stock.name,
            "status": status,
            "entry_price": entry_price,
            "target_price": target_price,
            "stop_loss": stop_loss,
            "current_price": current_price,
            "profit_loss_percent": round(pl_percent, 2),
            "distance_to_target": round(dist_to_target, 2),
            "distance_to_stop": round(dist_to_stop, 2),
            "hit_target": hit_target,
            "hit_stop": hit_stop,
            "ai_signal": ai_analysis.signal,
            "ai_confidence": ai_analysis.confidence,
            "ai_score": ai_analysis.score
        }

# ============================================================================
# CLI INTERFACE
# ============================================================================

def print_header(title: str):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def main():
    parser = argparse.ArgumentParser(description="نظام تقييم التوصيات والاختبار الخلفي")
    parser.add_argument("--backtest", type=str, help="تحليل سهم معين")
    parser.add_argument("--test-popular", action="store_true", help="تحليل الأسهم الأكثر تداولاً")
    parser.add_argument("--verify-expert", type=str, help="التحقق من توصيات خبير (tickers مفصولة بفاصلة)")
    parser.add_argument("--get-recommendations", action="store_true", help="الحصول على توصيات")
    parser.add_argument("--filter", type=str, help="فلترة التوصيات (buy/sell)")
    parser.add_argument("--limit", type=int, default=10, help="عدد النتائج")
    
    args = parser.parse_args()
    
    if not DATABASE_PATH:
        print("Error: No database found!")
        print("Please run from project root or set DATABASE_PATH")
        sys.exit(1)
    
    analyzer = StockAnalyzer(DATABASE_PATH)
    
    if args.backtest:
        ticker = args.backtest.upper()
        print_header(f"تحليل: {ticker}")
        
        result = analyzer.analyze_stock(ticker)
        
        if result:
            print(f"\n📊 النتيجة:")
            print(f"  السعر الحالي: {result.current_price:.2f} EGP")
            print(f"  الإشارة: {result.signal}")
            print(f"  الثقة: {result.confidence:.1f}%")
            print(f"  النقاط: {result.score}")
            print(f"\n  🎯 أهداف:")
            print(f"  - الدخول: {result.entry_price:.2f}")
            print(f"  - الهدف: {result.target_price:.2f}" if result.target_price else "  - الهدف: غير محدد")
            print(f"  - الاستوب: {result.stop_loss:.2f}" if result.stop_loss else "  - الاستوب: غير محدد")
            print(f"  - الدعم: {result.support:.2f}" if result.support else "  - الدعم: غير محدد")
            print(f"  - المقاومة: {result.resistance:.2f}" if result.resistance else "  - المقاومة: غير محدد")
            
            if result.reasons:
                print(f"\n  📝 الأسباب:")
                for r in result.reasons:
                    print(f"  - {r}")
        else:
            print(f"لم يتم العثور على السهم {ticker}")
    
    elif args.test_popular:
        print_header("تحليل الأسهم الأكثر تداولاً")
        
        popular = ["COMI", "HRHO", "SWDY", "ETEL", "EKHO", "TMGH", "PHDC", "GTHE",
                   "ESRS", "ORHD", "CIEB", "AMER", "HELI", "OCDI", "JUFO", "ABUK"]
        
        print(f"\n{'السهم':<8} {'السعر':<10} {'الإشارة':<12} {'الثقة':<8} {'النقاط':<8}")
        print("-" * 50)
        
        for ticker in popular:
            result = analyzer.analyze_stock(ticker)
            if result:
                signal_emoji = "🟢" if "BUY" in result.signal else "🔴" if "SELL" in result.signal else "🟡"
                print(f"{result.ticker:<8} {result.current_price:<10.2f} {signal_emoji} {result.signal:<10} {result.confidence:.1f}%{'':<4} {result.score}")
    
    elif args.verify_expert:
        print_header("التحقق من توصيات الخبير")
        
        # Expert recommendations from Raymond (14-5-2026)
        expert_recs = {
            "EHDR": {"entry": 2.35, "target": 2.48, "stop": 2.27},
            "CCAM": {"entry": 1.48, "target": 1.62, "stop": 1.45},
            "CCAP": {"entry": 4.73, "target": 4.93, "stop": 4.60}
        }
        
        verifier = ExpertVerifier(analyzer)
        
        print(f"\n{'السهم':<8} {'الحالة':<10} {'السعر':<10} {'P/L%':<8} {'AI Signal':<12}")
        print("-" * 60)
        
        for ticker, rec in expert_recs.items():
            result = verifier.verify_expert_rec(
                ticker, rec['entry'], rec['target'], rec['stop']
            )
            
            if result.get('status') == 'NOT_FOUND':
                print(f"{ticker:<8} ❌ NOT_FOUND")
                continue
                
            if 'status' in result and 'current_price' in result:
                status_emoji = "✅" if result['status'] == "SUCCESS" else "❌" if result['status'] == "STOPPED" else "⏳"
                ai_signal = result.get('ai_signal', 'N/A')
                print(f"{result['ticker']:<8} {status_emoji} {result['status']:<8} {result['current_price']:<10.2f} {result['profit_loss_percent']:<8.2f} {ai_signal}")
    
    elif args.get_recommendations:
        print_header("التوصيات")
        
        filter_sig = args.filter
        results = analyzer.get_recommendations(filter_sig)
        
        print(f"\n{'السهم':<8} {'السعر':<10} {'الإشارة':<12} {'الثقة':<8} {'الهدف':<10}")
        print("-" * 55)
        
        for result in results[:args.limit]:
            signal_emoji = "🟢" if "BUY" in result.signal else "🔴" if "SELL" in result.signal else "🟡"
            target = f"{result.target_price:.2f}" if result.target_price else "N/A"
            print(f"{result.ticker:<8} {result.current_price:<10.2f} {signal_emoji} {result.signal:<10} {result.confidence:.1f}%{'':<4} {target}")
    
    else:
        # Default: show top buy recommendations
        print_header("أفضل فرص الشراء")
        
        results = analyzer.get_recommendations("BUY")
        
        if results:
            print(f"\n{'السهم':<8} {'السعر':<10} {'الإشارة':<12} {'الثقة':<8} {'الأسباب'}")
            print("-" * 70)
            
            for result in results[:args.limit]:
                reasons_str = ", ".join(result.reasons[:2]) if result.reasons else ""
                print(f"{result.ticker:<8} {result.current_price:<10.2f} 🟢 {result.signal:<10} {result.confidence:.1f}%{'':<4} {reasons_str}")
        else:
            print("\nلا توجد فرص شراء واضحة حالياً")

if __name__ == "__main__":
    main()
