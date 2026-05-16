# -*- coding: utf-8 -*-
"""
Sync from Website / VPS - مزامنة البيانات من الموقع الحي أو VPS
"""

import os
import json
import requests
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "egx_investment.db")
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://invist.m2y.net")
VPS_URL = os.getenv("VPS_URL", "http://72.61.137.86:8010")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def sync_stocks_from_website() -> Dict:
    """مزامنة قائمة الأسهم من الموقع الحي أو VPS"""
    stats = {"fetched": 0, "inserted": 0, "updated": 0, "errors": []}

    # Try website first, fallback to VPS
    urls_to_try = [
        f"{WEBSITE_URL}/api/stocks/all",
        f"{VPS_URL}/api/stocks/all",
    ]

    stocks = None
    last_error = ""

    for url in urls_to_try:
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            raw_stocks = data.get("data", []) or data.get("stocks", [])
            # Handle both list and dict-wrapped formats
            if isinstance(raw_stocks, dict) and "stocks" in raw_stocks:
                raw_stocks = raw_stocks["stocks"]
            if isinstance(raw_stocks, list) and len(raw_stocks) > 0 and isinstance(raw_stocks[0], dict):
                stocks = raw_stocks
                logger.info(f"Fetched {len(stocks)} stocks from {url}")
                break
            elif isinstance(raw_stocks, dict):
                # Might be an error response
                logger.warning(f"Unexpected response from {url}: {raw_stocks}")
                continue
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Failed to fetch from {url}: {e}")

    if not stocks:
        return {"success": False, "error": f"Could not fetch stocks from any source. Last error: {last_error}"}

    stats["fetched"] = len(stocks)
    conn = get_db()
    try:
        cursor = conn.cursor()

        for stock in stocks:
            try:
                ticker = (stock.get("symbol") or stock.get("ticker") or "").upper()
                if not ticker:
                    continue

                # Check if stock exists
                cursor.execute("SELECT id FROM stocks WHERE ticker = ?", (ticker,))
                existing = cursor.fetchone()

                # Build fields
                fields = {
                    "ticker": ticker,
                    "name": stock.get("name") or stock.get("company_name"),
                    "name_ar": stock.get("name_ar"),
                    "sector": stock.get("sector"),
                    "industry": stock.get("industry"),
                    "current_price": stock.get("current_price") or stock.get("price"),
                    "previous_close": stock.get("previous_close") or stock.get("close"),
                    "open_price": stock.get("open_price") or stock.get("open"),
                    "high_price": stock.get("high_price") or stock.get("high"),
                    "low_price": stock.get("low_price") or stock.get("low"),
                    "volume": stock.get("volume"),
                    "market_cap": stock.get("market_cap"),
                    "pe_ratio": stock.get("pe_ratio"),
                    "pb_ratio": stock.get("pb_ratio"),
                    "eps": stock.get("eps"),
                    "roe": stock.get("roe"),
                    "rsi": stock.get("rsi"),
                    "ma_50": stock.get("ma_50"),
                    "ma_200": stock.get("ma_200"),
                    "support_level": stock.get("support_level"),
                    "resistance_level": stock.get("resistance_level"),
                    "last_update": datetime.now().isoformat(),
                    "is_active": 1,
                }

                # Remove None values for update
                clean_fields = {k: v for k, v in fields.items() if v is not None}

                if existing:
                    # Update existing
                    cols = ", ".join([f"{k} = ?" for k in clean_fields.keys() if k != "ticker"])
                    values = [clean_fields[k] for k in clean_fields.keys() if k != "ticker"]
                    values.append(ticker)
                    cursor.execute(f"UPDATE stocks SET {cols} WHERE ticker = ?", values)
                    stats["updated"] += cursor.rowcount
                else:
                    # Insert new
                    cols = ", ".join(clean_fields.keys())
                    placeholders = ", ".join(["?"] * len(clean_fields))
                    cursor.execute(
                        f"INSERT INTO stocks ({cols}) VALUES ({placeholders})",
                        list(clean_fields.values())
                    )
                    stats["inserted"] += 1

            except Exception as e:
                stats["errors"].append(f"Stock {stock.get('symbol', '?')}: {str(e)}")

        conn.commit()
    finally:
        conn.close()

    return {"success": True, "stats": stats}


def sync_price_history_from_website(tickers: Optional[List[str]] = None, max_stocks: int = 50) -> Dict:
    """مزامنة البيانات التاريخية من الموقع أو VPS"""
    stats = {"fetched": 0, "records": 0, "errors": []}

    conn = get_db()
    try:
        cursor = conn.cursor()

        if not tickers:
            cursor.execute("SELECT ticker FROM stocks WHERE is_active = 1 LIMIT ?", (max_stocks,))
            tickers = [r[0] for r in cursor.fetchall()]

        for ticker in tickers:
            # Try website first, fallback to VPS
            urls_to_try = [
                f"{WEBSITE_URL}/api/stocks/{ticker}/history?days=365",
                f"{VPS_URL}/api/stocks/{ticker}/local-history?days=365",
            ]

            history = None
            for url in urls_to_try:
                try:
                    resp = requests.get(url, timeout=15)
                    if resp.ok:
                        data = resp.json()
                        history = data.get("history", []) or data.get("data", [])
                        if history:
                            break
                except Exception:
                    continue

            if not history:
                continue

            # Get stock_id
            cursor.execute("SELECT id FROM stocks WHERE ticker = ?", (ticker,))
            row = cursor.fetchone()
            if not row:
                continue
            stock_id = row[0]

            for record in history:
                try:
                    date = record.get("date")
                    if not date:
                        continue

                    cursor.execute("""
                        INSERT INTO stock_price_history (stock_id, date, open_price, high_price, low_price, close_price, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(stock_id, date) DO UPDATE SET
                            open_price = COALESCE(excluded.open_price, open_price),
                            high_price = COALESCE(excluded.high_price, high_price),
                            low_price = COALESCE(excluded.low_price, low_price),
                            close_price = COALESCE(excluded.close_price, close_price),
                            volume = COALESCE(excluded.volume, volume)
                    """, (
                        stock_id, date,
                        record.get("open") or record.get("open_price"),
                        record.get("high") or record.get("high_price"),
                        record.get("low") or record.get("low_price"),
                        record.get("close") or record.get("close_price"),
                        record.get("volume")
                    ))
                    stats["records"] += 1
                except Exception as e:
                    stats["errors"].append(f"{ticker} {date}: {str(e)}")

            stats["fetched"] += 1

        conn.commit()
        return {"success": True, "stats": stats}

    finally:
        conn.close()


def sync_all_from_website() -> Dict:
    """مزامنة كل البيانات"""
    stocks_result = sync_stocks_from_website()
    history_result = sync_price_history_from_website(max_stocks=50)

    return {
        "success": stocks_result.get("success") and history_result.get("success"),
        "stocks": stocks_result,
        "history": history_result,
        "timestamp": datetime.now().isoformat()
    }
