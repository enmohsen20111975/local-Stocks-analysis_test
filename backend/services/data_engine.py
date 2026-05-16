# -*- coding: utf-8 -*-
"""
Real Data Engine - Uses technical_analysis.py to pre-compute ALL indicators
============================================================================
No dependencies on broken modules. Direct SQL with correct column names.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

from technical_analysis import TechnicalAnalysis, analyze_stock

DB_PATH = Path(os.path.join(os.path.dirname(__file__), "data", "egx_investment.db"))


def ensure_tables():
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS precomputed_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                asset_type TEXT DEFAULT 'stock',
                rsi REAL, macd REAL, macd_signal REAL,
                bb_upper REAL, bb_lower REAL,
                sma_20 REAL, sma_50 REAL, sma_200 REAL,
                ema_12 REAL, ema_26 REAL,
                current_price REAL,
                atr REAL, atr_percent REAL,
                stoch_k REAL, adx REAL,
                obv_trend TEXT,
                action TEXT, confidence INTEGER,
                bullish_count INTEGER, bearish_count INTEGER,
                score INTEGER,
                trend TEXT, volatility TEXT,
                reasons TEXT,
                entry_zone_low REAL, entry_zone_high REAL, entry_trigger REAL,
                support_level REAL,
                target_1 REAL, target_2 REAL, investment_target REAL,
                stop_loss REAL, expected_return_pct REAL,
                computed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sector_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sector TEXT NOT NULL,
                avg_change_percent REAL,
                stock_count INTEGER,
                top_performer TEXT,
                worst_performer TEXT,
                computed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                summary_type TEXT,
                summary TEXT,
                top_gainers TEXT,
                top_losers TEXT,
                sentiment TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Add new columns if they don't exist (for trade plan fields)
        new_columns = [
            ('current_price', 'REAL'),
            ('entry_zone_low', 'REAL'), ('entry_zone_high', 'REAL'), ('entry_trigger', 'REAL'),
            ('support_level', 'REAL'),
            ('target_1', 'REAL'), ('target_2', 'REAL'), ('investment_target', 'REAL'),
            ('stop_loss', 'REAL'), ('expected_return_pct', 'REAL')
        ]
        for col_name, col_type in new_columns:
            try:
                conn.execute(f"ALTER TABLE precomputed_indicators ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass  # Column already exists
        
        conn.commit()
    finally:
        conn.close()


class DataEngine:
    def __init__(self):
        ensure_tables()
        logger.info("[DataEngine] Ready")

    def _get_tickers(self) -> List[str]:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("SELECT ticker FROM stocks WHERE is_active=1 ORDER BY ticker").fetchall()
            return [r['ticker'] for r in rows]
        finally:
            conn.close()

    def _get_price_df(self, ticker: str) -> Optional[pd.DataFrame]:
        """Fetch price history using CORRECT column names"""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            # Try stock_price_history (has stock_id, not ticker directly)
            rows = conn.execute("""
                SELECT sph.date, sph.open_price as open, sph.high_price as high,
                       sph.low_price as low, sph.close_price as close, sph.volume
                FROM stock_price_history sph
                JOIN stocks s ON s.id = sph.stock_id
                WHERE s.ticker = ?
                ORDER BY sph.date ASC
            """, (ticker,)).fetchall()
            
            if not rows or len(rows) < 50:
                # Fallback to price_history table (for crypto)
                rows = conn.execute("""
                    SELECT date, open, high, low, close, volume
                    FROM price_history WHERE ticker = ? ORDER BY date ASC
                """, (ticker,)).fetchall()
            
            if not rows or len(rows) < 50:
                return None
            
            df = pd.DataFrame([dict(r) for r in rows])
            df['date'] = pd.to_datetime(df['date'], format='mixed', dayfirst=True)
            df = df.set_index('date')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df.dropna()
        finally:
            conn.close()

    def _get_crypto_df(self, coin_id: str) -> Optional[pd.DataFrame]:
        """Fetch crypto price history from price_history"""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT date, open, high, low, close, volume
                FROM price_history WHERE ticker = ? ORDER BY date ASC
            """, (coin_id,)).fetchall()
            if not rows or len(rows) < 20:
                return None
            df = pd.DataFrame([dict(r) for r in rows])
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df.dropna()
        finally:
            conn.close()

    def _get_gold_df(self, karat: str = "24") -> Optional[pd.DataFrame]:
        """Fetch gold price history and synthesize OHLCV"""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT recorded_at as date, price_per_gram as close, change
                FROM gold_price_history
                WHERE karat = ? ORDER BY date ASC
            """, (karat,)).fetchall()
            if not rows or len(rows) < 5:
                return None
            df = pd.DataFrame([dict(r) for r in rows])
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['open'] = df['close'].shift(1).fillna(df['close'])
            df['high'] = df[['open', 'close']].max(axis=1) * 1.002
            df['low'] = df[['open', 'close']].min(axis=1) * 0.998
            df['volume'] = 1000
            return df[['open', 'high', 'low', 'close', 'volume']].dropna()
        finally:
            conn.close()

    def compute_all_indicators(self, limit: Optional[int] = None, asset_type: str = "stock") -> Dict:
        tickers = self._get_tickers()
        if limit:
            tickers = tickers[:limit]
        
        logger.info(f"[DataEngine] Computing indicators for {len(tickers)} stocks (asset_type={asset_type})")
        processed = 0
        failed = 0
        
        conn = sqlite3.connect(str(DB_PATH))
        try:
            for ticker in tickers:
                try:
                    df = self._get_price_df(ticker)
                    if df is None or len(df) < 50:
                        failed += 1
                        continue
                    
                    result = analyze_stock(df)
                    if 'error' in result:
                        failed += 1
                        continue
                    
                    ind = result['indicators']
                    sig = result['signals']
                    
                    tp = result.get('trade_plan', {})
                    conn.execute("""
                        INSERT OR REPLACE INTO precomputed_indicators
                        (ticker, asset_type, current_price, rsi, macd, macd_signal, bb_upper, bb_lower,
                         sma_20, sma_50, sma_200, ema_12, ema_26,
                         atr, atr_percent, stoch_k, adx, obv_trend,
                         action, confidence, bullish_count, bearish_count, score,
                         trend, volatility, reasons,
                         entry_zone_low, entry_zone_high, entry_trigger, support_level,
                         target_1, target_2, investment_target, stop_loss, expected_return_pct,
                         computed_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        ticker, asset_type, result.get('current_price'),
                        ind.get('rsi'), ind.get('macd'), ind.get('macd_signal'),
                        ind.get('bb_upper'), ind.get('bb_lower'),
                        ind.get('sma_20'), ind.get('sma_50'), ind.get('sma_200'),
                        ind.get('ema_12'), ind.get('ema_26'),
                        ind.get('atr'), ind.get('atr_percent'),
                        ind.get('stoch_k'), ind.get('adx'), ind.get('obv_trend'),
                        sig.get('action'), sig.get('confidence'),
                        sig.get('bullish_count'), sig.get('bearish_count'), sig.get('score'),
                        result.get('trend'), result.get('volatility'),
                        json.dumps(sig.get('reasons', [])),
                        tp.get('entry_zone_low'), tp.get('entry_zone_high'), tp.get('entry_trigger'), tp.get('support_level'),
                        tp.get('target_1'), tp.get('target_2'), tp.get('investment_target'), tp.get('stop_loss'), tp.get('expected_return_pct'),
                        datetime.now().isoformat()
                    ))
                    processed += 1
                    
                    if processed % 50 == 0:
                        conn.commit()
                        logger.info(f"[DataEngine] {processed}/{len(tickers)} done")
                        
                except Exception as e:
                    logger.warning(f"[DataEngine] Failed {ticker}: {e}")
                    failed += 1
            
            conn.commit()
        finally:
            conn.close()
        
        logger.info(f"[DataEngine] Done: {processed} ok, {failed} failed")
        return {"processed": processed, "failed": failed}

    def compute_crypto_indicators(self) -> Dict:
        """Compute indicators for all crypto in price_history"""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("SELECT DISTINCT ticker FROM price_history ORDER BY ticker").fetchall()
            tickers = [r['ticker'] for r in rows]
        finally:
            conn.close()
        
        logger.info(f"[DataEngine] Computing crypto indicators for {len(tickers)} coins")
        processed = 0
        failed = 0
        
        conn = sqlite3.connect(str(DB_PATH))
        try:
            for ticker in tickers:
                try:
                    df = self._get_crypto_df(ticker)
                    if df is None or len(df) < 20:
                        failed += 1
                        continue
                    
                    result = analyze_stock(df)
                    if 'error' in result:
                        failed += 1
                        continue
                    
                    ind = result['indicators']
                    sig = result['signals']
                    tp = result.get('trade_plan', {})
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO precomputed_indicators
                        (ticker, asset_type, current_price, rsi, macd, macd_signal, bb_upper, bb_lower,
                         sma_20, sma_50, sma_200, ema_12, ema_26,
                         atr, atr_percent, stoch_k, adx, obv_trend,
                         action, confidence, bullish_count, bearish_count, score,
                         trend, volatility, reasons,
                         entry_zone_low, entry_zone_high, entry_trigger, support_level,
                         target_1, target_2, investment_target, stop_loss, expected_return_pct,
                         computed_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        ticker, 'crypto', result.get('current_price'),
                        ind.get('rsi'), ind.get('macd'), ind.get('macd_signal'),
                        ind.get('bb_upper'), ind.get('bb_lower'),
                        ind.get('sma_20'), ind.get('sma_50'), ind.get('sma_200'),
                        ind.get('ema_12'), ind.get('ema_26'),
                        ind.get('atr'), ind.get('atr_percent'),
                        ind.get('stoch_k'), ind.get('adx'), ind.get('obv_trend'),
                        sig.get('action'), sig.get('confidence'),
                        sig.get('bullish_count'), sig.get('bearish_count'), sig.get('score'),
                        result.get('trend'), result.get('volatility'),
                        json.dumps(sig.get('reasons', [])),
                        tp.get('entry_zone_low'), tp.get('entry_zone_high'), tp.get('entry_trigger'), tp.get('support_level'),
                        tp.get('target_1'), tp.get('target_2'), tp.get('investment_target'), tp.get('stop_loss'), tp.get('expected_return_pct'),
                        datetime.now().isoformat()
                    ))
                    processed += 1
                    
                except Exception as e:
                    logger.warning(f"[DataEngine] Crypto failed {ticker}: {e}")
                    failed += 1
            
            conn.commit()
        finally:
            conn.close()
        
        logger.info(f"[DataEngine] Crypto done: {processed} ok, {failed} failed")
        return {"processed": processed, "failed": failed}

    def _analyze_short(self, df: pd.DataFrame) -> Dict:
        """Simplified analysis for short datasets (< 50 rows)"""
        close = df['close']
        high = df['high']
        low = df['low']
        current_price = close.iloc[-1]
        prev_price = close.iloc[-2] if len(close) > 1 else current_price
        change_pct = ((current_price - prev_price) / prev_price * 100) if prev_price else 0
        
        # Simple trend
        if len(close) >= 3:
            trend = 'bullish' if close.iloc[-1] > close.iloc[-3] else 'bearish' if close.iloc[-1] < close.iloc[-3] else 'neutral'
        else:
            trend = 'neutral'
        
        action = 'BUY' if change_pct < -2 else 'SELL' if change_pct > 2 else 'HOLD'
        confidence = 50 + abs(change_pct) * 2 if abs(change_pct) < 25 else 95
        
        # Simple trade plan for short datasets
        cp = current_price
        atr_est = cp * abs(change_pct) / 100 if abs(change_pct) > 0 else cp * 0.01
        
        if action == 'BUY':
            entry_low = round(cp * 0.99, 2)
            entry_high = round(cp, 2)
            entry_trigger = round(cp * 1.01, 2)
            support = round(cp * 0.97, 2)
            target_1 = round(cp * 1.04, 2)
            target_2 = round(cp * 1.07, 2)
            inv_target = round(cp * 1.12, 2)
            stop_loss = round(cp * 0.96, 2)
            exp_return = round(6.0, 1)
        elif action == 'SELL':
            entry_low = round(cp, 2)
            entry_high = round(cp * 1.01, 2)
            entry_trigger = round(cp * 0.99, 2)
            support = round(cp * 0.97, 2)
            target_1 = round(cp * 0.96, 2)
            target_2 = round(cp * 0.93, 2)
            inv_target = round(cp * 0.88, 2)
            stop_loss = round(cp * 1.04, 2)
            exp_return = round(6.0, 1)
        else:
            entry_low = round(cp * 0.995, 2)
            entry_high = round(cp * 1.005, 2)
            entry_trigger = round(cp * 1.01, 2)
            support = round(cp * 0.97, 2)
            target_1 = round(cp * 1.03, 2)
            target_2 = round(cp * 1.06, 2)
            inv_target = round(cp * 1.10, 2)
            stop_loss = round(cp * 0.96, 2)
            exp_return = round(4.0, 1)
        
        return {
            'current_price': round(current_price, 2),
            'indicators': {
                'rsi': None, 'macd': None, 'macd_signal': None,
                'bb_upper': None, 'bb_lower': None,
                'sma_20': None, 'sma_50': None, 'sma_200': None,
                'ema_12': None, 'ema_26': None,
                'atr': None, 'atr_percent': round(abs(change_pct), 2),
                'stoch_k': None, 'adx': None, 'obv_trend': None
            },
            'signals': {
                'action': action, 'confidence': min(100, int(confidence)),
                'bullish_count': 1 if action == 'BUY' else 0,
                'bearish_count': 1 if action == 'SELL' else 0,
                'score': 50 + int(change_pct),
                'reasons': [f"تغير السعر: {change_pct:+.2f}%", f"الاتجاه: {trend}"]
            },
            'trade_plan': {
                'entry_zone_low': entry_low,
                'entry_zone_high': entry_high,
                'entry_trigger': entry_trigger,
                'support_level': support,
                'target_1': target_1,
                'target_2': target_2,
                'investment_target': inv_target,
                'stop_loss': stop_loss,
                'expected_return_pct': exp_return,
                'risk_reward_ratio': round(exp_return / 3.0, 2)
            },
            'trend': trend,
            'volatility': 'high' if abs(change_pct) > 3 else 'medium' if abs(change_pct) > 1 else 'low'
        }

    def compute_gold_indicators(self) -> Dict:
        """Compute indicators for gold"""
        logger.info("[DataEngine] Computing gold indicators")
        processed = 0
        failed = 0
        
        conn = sqlite3.connect(str(DB_PATH))
        try:
            for karat in ['24', '21', '18']:
                try:
                    df = self._get_gold_df(karat)
                    if df is None or len(df) < 5:
                        failed += 1
                        continue
                    
                    if len(df) >= 50:
                        result = analyze_stock(df)
                    else:
                        result = self._analyze_short(df)
                    
                    if 'error' in result:
                        failed += 1
                        continue
                    
                    ind = result['indicators']
                    sig = result['signals']
                    tp = result.get('trade_plan', {})
                    ticker = f'GOLD_{karat}K'
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO precomputed_indicators
                        (ticker, asset_type, current_price, rsi, macd, macd_signal, bb_upper, bb_lower,
                         sma_20, sma_50, sma_200, ema_12, ema_26,
                         atr, atr_percent, stoch_k, adx, obv_trend,
                         action, confidence, bullish_count, bearish_count, score,
                         trend, volatility, reasons,
                         entry_zone_low, entry_zone_high, entry_trigger, support_level,
                         target_1, target_2, investment_target, stop_loss, expected_return_pct,
                         computed_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        ticker, 'gold', result.get('current_price'),
                        ind.get('rsi'), ind.get('macd'), ind.get('macd_signal'),
                        ind.get('bb_upper'), ind.get('bb_lower'),
                        ind.get('sma_20'), ind.get('sma_50'), ind.get('sma_200'),
                        ind.get('ema_12'), ind.get('ema_26'),
                        ind.get('atr'), ind.get('atr_percent'),
                        ind.get('stoch_k'), ind.get('adx'), ind.get('obv_trend'),
                        sig.get('action'), sig.get('confidence'),
                        sig.get('bullish_count'), sig.get('bearish_count'), sig.get('score'),
                        result.get('trend'), result.get('volatility'),
                        json.dumps(sig.get('reasons', [])),
                        tp.get('entry_zone_low'), tp.get('entry_zone_high'), tp.get('entry_trigger'), tp.get('support_level'),
                        tp.get('target_1'), tp.get('target_2'), tp.get('investment_target'), tp.get('stop_loss'), tp.get('expected_return_pct'),
                        datetime.now().isoformat()
                    ))
                    processed += 1
                    
                except Exception as e:
                    logger.warning(f"[DataEngine] Gold failed {karat}: {e}")
                    failed += 1
            
            conn.commit()
        finally:
            conn.close()
        
        logger.info(f"[DataEngine] Gold done: {processed} ok, {failed} failed")
        return {"processed": processed, "failed": failed}

    def compute_sectors(self) -> Dict:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT ticker, sector, current_price, previous_close
                FROM stocks WHERE is_active=1 AND sector IS NOT NULL
            """).fetchall()
            
            df = pd.DataFrame([dict(r) for r in rows])
            if df.empty:
                return {"sectors": 0}
            
            df['change_percent'] = ((df['current_price'] - df['previous_close']) / df['previous_close'] * 100).fillna(0)
            
            sectors = df.groupby('sector').agg({
                'change_percent': 'mean',
                'ticker': 'count'
            }).reset_index()
            
            for _, row in sectors.iterrows():
                sec = row['sector']
                sec_df = df[df['sector'] == sec]
                top = sec_df.loc[sec_df['change_percent'].idxmax()]['ticker']
                worst = sec_df.loc[sec_df['change_percent'].idxmin()]['ticker']
                
                conn.execute("""
                    INSERT INTO sector_performance
                    (sector, avg_change_percent, stock_count, top_performer, worst_performer, computed_at)
                    VALUES (?,?,?,?,?,?)
                """, (sec, round(row['change_percent'], 2), int(row['ticker']), top, worst, datetime.now().isoformat()))
            
            conn.commit()
            return {"sectors": len(sectors)}
        finally:
            conn.close()

    def generate_market_summary(self) -> Dict:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT ticker, action, confidence, trend, score
                FROM precomputed_indicators
                ORDER BY score DESC
            """).fetchall()
            
            if not rows:
                return {"error": "No indicators. Run compute_all_indicators first."}
            
            df = pd.DataFrame([dict(r) for r in rows])
            buy = len(df[df['action'] == 'BUY'])
            sell = len(df[df['action'] == 'SELL'])
            hold = len(df[df['action'] == 'HOLD'])
            
            top_buy = df[df['action'] == 'BUY'].head(5).to_dict('records') if buy > 0 else []
            top_sell = df[df['action'] == 'SELL'].head(5).to_dict('records') if sell > 0 else []
            
            summary = f"BUY: {buy}, SELL: {sell}, HOLD: {hold}. Market: {'Bullish' if buy > sell else 'Bearish' if sell > buy else 'Neutral'}."
            
            conn.execute("""
                INSERT INTO market_summaries (summary_type, summary, top_gainers, top_losers, sentiment, created_at)
                VALUES (?,?,?,?,?,?)
            """, ('daily', summary, json.dumps(top_buy), json.dumps(top_sell),
                  'bullish' if buy > sell else 'bearish' if sell > buy else 'neutral',
                  datetime.now().isoformat()))
            conn.commit()
            
            return {"buy": buy, "sell": sell, "hold": hold, "summary": summary}
        finally:
            conn.close()

    def run_full_pipeline(self, stock_limit: Optional[int] = None) -> Dict:
        logger.info("=" * 50)
        logger.info("[DataEngine] FULL PIPELINE STARTING")
        logger.info("=" * 50)
        
        r1 = self.compute_all_indicators(stock_limit)
        r2 = self.compute_crypto_indicators()
        r3 = self.compute_gold_indicators()
        r4 = self.compute_sectors()
        r5 = self.generate_market_summary()
        
        logger.info("[DataEngine] PIPELINE COMPLETE")
        return {"indicators": r1, "crypto": r2, "gold": r3, "sectors": r4, "market_summary": r5}

    # Fast query APIs
    def get_stock_signals(self, ticker: str) -> Optional[Dict]:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT * FROM precomputed_indicators WHERE ticker=? ORDER BY computed_at DESC LIMIT 1", (ticker,)).fetchone()
            if row:
                d = dict(row)
                try:
                    d['reasons'] = json.loads(d['reasons']) if d.get('reasons') else []
                except:
                    d['reasons'] = []
                return d
        finally:
            conn.close()
        return None

    def get_all_signals(self, action: Optional[str] = None, min_confidence: int = 0, asset_type: Optional[str] = None) -> List[Dict]:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            # Get latest row per ticker only (avoid duplicates from old computations)
            query = """
                SELECT * FROM precomputed_indicators
                WHERE id IN (
                    SELECT MAX(id) FROM precomputed_indicators GROUP BY ticker
                )
            """
            params = []
            if asset_type:
                query += " AND asset_type = ?"
                params.append(asset_type.lower())
            if action:
                query += " AND action = ?"
                params.append(action.upper())
            if min_confidence > 0:
                query += " AND confidence >= ?"
                params.append(min_confidence)
            query += " ORDER BY confidence DESC, computed_at DESC"
            
            rows = conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                try:
                    d['reasons'] = json.loads(d['reasons']) if d.get('reasons') else []
                except:
                    d['reasons'] = []
                results.append(d)
            return results
        finally:
            conn.close()

    def get_sectors(self) -> List[Dict]:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("SELECT * FROM sector_performance ORDER BY avg_change_percent DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_market_summary(self) -> Optional[Dict]:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT * FROM market_summaries ORDER BY created_at DESC LIMIT 1").fetchone()
            if row:
                d = dict(row)
                for k in ['top_gainers', 'top_losers']:
                    try:
                        d[k] = json.loads(d[k]) if d.get(k) else []
                    except:
                        d[k] = []
                return d
        finally:
            conn.close()
        return None


# Singleton instance
data_engine = DataEngine()
