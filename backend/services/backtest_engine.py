# -*- coding: utf-8 -*-
"""
Backtest Engine - Block Testing for ALL assets
===============================================
Tests trading strategies on groups of assets and stores results.
No individual stock view - block analysis only.
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

DB_PATH = Path(os.path.join(os.path.dirname(__file__), "data", "egx_investment.db"))

# Strategy definitions
STRATEGIES = {
    "rsi_oversold": {
        "name": "RSI Oversold Reversal",
        "params": {"rsi_buy": 30, "rsi_sell": 70},
        "description": "Buy when RSI < 30, Sell when RSI > 70"
    },
    "macd_crossover": {
        "name": "MACD Crossover",
        "params": {"macd_threshold": 0},
        "description": "Buy when MACD histogram turns positive, Sell when negative"
    },
    "ma_crossover": {
        "name": "MA Crossover",
        "params": {"fast_ma": 20, "slow_ma": 50},
        "description": "Buy when SMA20 > SMA50, Sell when SMA20 < SMA50"
    },
    "bollinger_reversal": {
        "name": "Bollinger Bands Reversal",
        "params": {"bb_deviation": 2},
        "description": "Buy when price hits lower band, Sell when hits upper band"
    },
    "combined_signal": {
        "name": "Combined Multi-Indicator",
        "params": {"min_signals": 2},
        "description": "Buy when 2+ indicators agree bullish, Sell when 2+ agree bearish"
    }
}


@dataclass
class BacktestResult:
    strategy: str
    ticker: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return_pct: float
    avg_return_per_trade: float
    max_drawdown_pct: float
    sharpe_ratio: float
    start_price: float
    end_price: float
    parameter_set: str


def ensure_backtest_tables():
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_type TEXT NOT NULL,
                strategy TEXT NOT NULL,
                ticker TEXT NOT NULL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                win_rate REAL,
                total_return_pct REAL,
                avg_return_per_trade REAL,
                max_drawdown_pct REAL,
                sharpe_ratio REAL,
                start_price REAL,
                end_price REAL,
                parameter_set TEXT,
                computed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backtest_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_type TEXT NOT NULL,
                strategy TEXT NOT NULL,
                assets_tested INTEGER,
                avg_win_rate REAL,
                avg_return_pct REAL,
                best_ticker TEXT,
                worst_ticker TEXT,
                profitable_count INTEGER,
                losing_count INTEGER,
                parameter_set TEXT,
                computed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()


def get_price_df(ticker: str, table: str = "stock_price_history") -> Optional[pd.DataFrame]:
    """Fetch price history from DB"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        if table == "stock_price_history":
            rows = conn.execute("""
                SELECT sph.date, sph.open_price as open, sph.high_price as high,
                       sph.low_price as low, sph.close_price as close, sph.volume
                FROM stock_price_history sph
                JOIN stocks s ON s.id = sph.stock_id
                WHERE s.ticker = ? ORDER BY sph.date ASC
            """, (ticker,)).fetchall()
        elif table == "price_history":
            rows = conn.execute("""
                SELECT date, open, high, low, close, volume
                FROM price_history WHERE ticker = ? ORDER BY date ASC
            """, (ticker,)).fetchall()
        else:
            return None

        if not rows or len(rows) < 50:
            return None

        df = pd.DataFrame([dict(r) for r in rows])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df.dropna()
    finally:
        conn.close()


def get_gold_price_df(karat: str = "24") -> Optional[pd.DataFrame]:
    """Fetch gold price history and synthesize OHLCV from price_per_gram"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT recorded_at as date, price_per_gram as close, change
            FROM gold_price_history
            WHERE karat = ? ORDER BY date ASC
        """, (karat,)).fetchall()

        if not rows or len(rows) < 20:
            return None

        df = pd.DataFrame([dict(r) for r in rows])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        # Synthesize OHLC from close price
        df['open'] = df['close'].shift(1).fillna(df['close'])
        df['high'] = df[['open', 'close']].max(axis=1) * 1.002
        df['low'] = df[['open', 'close']].min(axis=1) * 0.998
        df['volume'] = 1000  # Dummy volume
        return df[['open', 'high', 'low', 'close', 'volume']].dropna()
    finally:
        conn.close()


def run_strategy_backtest(df: pd.DataFrame, strategy: str, params: Dict) -> Optional[Dict]:
    """Run a single strategy backtest on one asset's price data"""
    if len(df) < 50:
        return None

    close = df['close']
    high = df['high']
    low = df['low']

    # Pre-calculate indicators
    sma_20 = close.rolling(20).mean()
    sma_50 = close.rolling(50).mean()

    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=26, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - signal_line

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + (bb_std * 2)
    bb_lower = bb_mid - (bb_std * 2)

    trades = []
    position = 0  # 0 = no position, 1 = long
    entry_price = 0
    equity = [1.0]  # normalized equity curve

    for i in range(50, len(df)):
        price = close.iloc[i]
        
        # Generate signal
        buy_signal = False
        sell_signal = False

        if strategy == "rsi_oversold":
            if rsi.iloc[i] < params.get("rsi_buy", 30) and position == 0:
                buy_signal = True
            elif rsi.iloc[i] > params.get("rsi_sell", 70) and position == 1:
                sell_signal = True

        elif strategy == "macd_crossover":
            if macd_hist.iloc[i] > 0 and macd_hist.iloc[i-1] <= 0 and position == 0:
                buy_signal = True
            elif macd_hist.iloc[i] < 0 and macd_hist.iloc[i-1] >= 0 and position == 1:
                sell_signal = True

        elif strategy == "ma_crossover":
            if sma_20.iloc[i] > sma_50.iloc[i] and sma_20.iloc[i-1] <= sma_50.iloc[i-1] and position == 0:
                buy_signal = True
            elif sma_20.iloc[i] < sma_50.iloc[i] and sma_20.iloc[i-1] >= sma_50.iloc[i-1] and position == 1:
                sell_signal = True

        elif strategy == "bollinger_reversal":
            if price < bb_lower.iloc[i] and position == 0:
                buy_signal = True
            elif price > bb_upper.iloc[i] and position == 1:
                sell_signal = True

        elif strategy == "combined_signal":
            bullish = 0
            bearish = 0
            if rsi.iloc[i] < 35: bullish += 1
            if rsi.iloc[i] > 65: bearish += 1
            if macd_hist.iloc[i] > 0: bullish += 1
            if macd_hist.iloc[i] < 0: bearish += 1
            if sma_20.iloc[i] > sma_50.iloc[i]: bullish += 1
            if sma_20.iloc[i] < sma_50.iloc[i]: bearish += 1
            if price < bb_lower.iloc[i]: bullish += 1
            if price > bb_upper.iloc[i]: bearish += 1

            if bullish >= params.get("min_signals", 2) and position == 0:
                buy_signal = True
            elif bearish >= params.get("min_signals", 2) and position == 1:
                sell_signal = True

        # Execute
        if buy_signal:
            position = 1
            entry_price = price
        elif sell_signal and position == 1:
            pnl = (price - entry_price) / entry_price
            trades.append(pnl)
            position = 0

        # Equity tracking
        if trades:
            equity.append(1.0 + sum(trades))
        else:
            equity.append(equity[-1])

    # Close any open position at end
    if position == 1:
        pnl = (close.iloc[-1] - entry_price) / entry_price
        trades.append(pnl)

    if not trades:
        return None

    trades = np.array(trades)
    wins = trades > 0
    losses = trades <= 0

    equity_arr = np.array(equity)
    peak = np.maximum.accumulate(equity_arr)
    drawdown = (peak - equity_arr) / peak

    returns_std = np.std(trades) if len(trades) > 1 else 0.001
    sharpe = (np.mean(trades) / returns_std) * np.sqrt(252) if returns_std > 0 else 0

    return {
        "total_trades": len(trades),
        "winning_trades": int(np.sum(wins)),
        "losing_trades": int(np.sum(losses)),
        "win_rate": float(np.mean(wins) * 100),
        "total_return_pct": float((equity_arr[-1] - 1.0) * 100),
        "avg_return_per_trade": float(np.mean(trades) * 100),
        "max_drawdown_pct": float(np.max(drawdown) * 100),
        "sharpe_ratio": float(sharpe),
        "start_price": float(close.iloc[50]),
        "end_price": float(close.iloc[-1]),
    }


class BacktestEngine:
    def __init__(self):
        ensure_backtest_tables()
        logger.info("[BacktestEngine] Ready")

    def run_block_backtest(self, asset_type: str, tickers: List[str], strategies: Optional[List[str]] = None) -> Dict:
        """
        Run backtest block for ALL assets of a given type
        asset_type: 'stocks' | 'crypto' | 'gold'
        """
        if strategies is None:
            strategies = list(STRATEGIES.keys())

        logger.info(f"[BacktestEngine] Running block backtest for {asset_type}: {len(tickers)} assets x {len(strategies)} strategies")

        conn = sqlite3.connect(str(DB_PATH))
        try:
            all_results = []
            summary_by_strategy = {}

            for strategy_key in strategies:
                strategy_info = STRATEGIES[strategy_key]
                params = strategy_info["params"]

                strategy_results = []
                profitable = 0
                losing = 0
                best_return = -999
                worst_return = 999
                best_ticker = ""
                worst_ticker = ""

                for ticker in tickers:
                    try:
                        if asset_type == "crypto":
                            df = get_price_df(ticker, "price_history")
                        elif asset_type == "gold":
                            df = get_gold_price_df(ticker)
                        else:
                            df = get_price_df(ticker, "stock_price_history")

                        if df is None or len(df) < 50:
                            continue

                        result = run_strategy_backtest(df, strategy_key, params)
                        if result:
                            result["ticker"] = ticker
                            result["strategy"] = strategy_key
                            result["asset_type"] = asset_type
                            result["parameter_set"] = json.dumps(params)
                            strategy_results.append(result)
                            all_results.append(result)

                            # Store individual result
                            conn.execute("""
                                INSERT INTO backtest_results
                                (asset_type, strategy, ticker, total_trades, winning_trades, losing_trades,
                                 win_rate, total_return_pct, avg_return_per_trade, max_drawdown_pct,
                                 sharpe_ratio, start_price, end_price, parameter_set)
                                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                            """, (
                                asset_type, strategy_key, ticker,
                                result["total_trades"], result["winning_trades"], result["losing_trades"],
                                result["win_rate"], result["total_return_pct"], result["avg_return_per_trade"],
                                result["max_drawdown_pct"], result["sharpe_ratio"],
                                result["start_price"], result["end_price"], json.dumps(params)
                            ))

                            if result["total_return_pct"] > 0:
                                profitable += 1
                            else:
                                losing += 1

                            if result["total_return_pct"] > best_return:
                                best_return = result["total_return_pct"]
                                best_ticker = ticker
                            if result["total_return_pct"] < worst_return:
                                worst_return = result["total_return_pct"]
                                worst_ticker = ticker
                    except Exception as e:
                        logger.warning(f"[BacktestEngine] Failed {ticker}/{strategy_key}: {e}")

                if strategy_results:
                    avg_win = np.mean([r["win_rate"] for r in strategy_results])
                    avg_ret = np.mean([r["total_return_pct"] for r in strategy_results])

                    summary_by_strategy[strategy_key] = {
                        "strategy_name": strategy_info["name"],
                        "assets_tested": len(strategy_results),
                        "avg_win_rate": round(avg_win, 2),
                        "avg_return_pct": round(avg_ret, 2),
                        "best_ticker": best_ticker,
                        "worst_ticker": worst_ticker,
                        "profitable_count": profitable,
                        "losing_count": losing,
                        "parameter_set": json.dumps(params)
                    }

                    conn.execute("""
                        INSERT INTO backtest_summaries
                        (asset_type, strategy, assets_tested, avg_win_rate, avg_return_pct,
                         best_ticker, worst_ticker, profitable_count, losing_count, parameter_set)
                        VALUES (?,?,?,?,?,?,?,?,?,?)
                    """, (
                        asset_type, strategy_key, len(strategy_results), avg_win, avg_ret,
                        best_ticker, worst_ticker, profitable, losing, json.dumps(params)
                    ))

                logger.info(f"[BacktestEngine] {asset_type}/{strategy_key}: {len(strategy_results)} assets tested")

            conn.commit()
            logger.info(f"[BacktestEngine] Block backtest complete for {asset_type}")
            return {
                "asset_type": asset_type,
                "assets_tested": len(tickers),
                "strategies_tested": len(strategies),
                "total_results": len(all_results),
                "summaries": summary_by_strategy
            }
        finally:
            conn.close()

    def run_stocks_backtest(self, limit: Optional[int] = None) -> Dict:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("SELECT ticker FROM stocks WHERE is_active=1 ORDER BY ticker").fetchall()
            tickers = [r['ticker'] for r in rows]
            if limit:
                tickers = tickers[:limit]
            return self.run_block_backtest("stocks", tickers)
        finally:
            conn.close()

    def run_crypto_backtest(self, limit: Optional[int] = None) -> Dict:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            try:
                rows = conn.execute("SELECT coin_id as ticker FROM crypto_prices WHERE current_price > 0 ORDER BY market_cap DESC").fetchall()
            except sqlite3.OperationalError:
                return {"error": "No crypto data. Sync crypto first."}
            tickers = [r['ticker'] for r in rows]
            if limit:
                tickers = tickers[:limit]
            if not tickers:
                return {"error": "No crypto data. Sync crypto first."}
            return self.run_block_backtest("crypto", tickers)
        finally:
            conn.close()

    def run_gold_backtest(self) -> Dict:
        # Gold is single asset, backtest on gold price history
        tickers = ["GOLD"]
        return self.run_block_backtest("gold", tickers)

    # Fast query APIs
    def get_backtest_summaries(self, asset_type: Optional[str] = None) -> List[Dict]:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            query = "SELECT * FROM backtest_summaries"
            params = []
            if asset_type:
                query += " WHERE asset_type = ?"
                params.append(asset_type)
            query += " ORDER BY computed_at DESC"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_backtest_results(self, strategy: Optional[str] = None, asset_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            query = "SELECT * FROM backtest_results WHERE 1=1"
            params = []
            if strategy:
                query += " AND strategy = ?"
                params.append(strategy)
            if asset_type:
                query += " AND asset_type = ?"
                params.append(asset_type)
            query += " ORDER BY total_return_pct DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_best_strategies(self, asset_type: str) -> List[Dict]:
        """Get best performing strategies for an asset type"""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("""
                SELECT strategy, AVG(avg_return_pct) as avg_return, AVG(avg_win_rate) as avg_win,
                       SUM(profitable_count) as total_profitable, SUM(losing_count) as total_losing
                FROM backtest_summaries
                WHERE asset_type = ?
                GROUP BY strategy
                ORDER BY avg_return DESC
            """, (asset_type,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


# Singleton
backtest_engine = BacktestEngine()
