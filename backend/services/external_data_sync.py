# -*- coding: utf-8 -*-
"""
External Data Sync — مصادر بيانات خارجية
================================================
✅ Crypto: CoinGecko (free, hourly) + Binance (1-min candles, free)
✅ Gold: Binance PAXG + USD/EGP rate → calculate Egyptian prices
✅ Currency: exchangerate-api.com (free, daily)
⚠️  EGX Stocks: MubasherTrade (primary) — scrape EGX as fallback

All APIs are FREE and do NOT require API keys for basic usage.
"""

import os
import sys
import json
import sqlite3
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import pandas as pd
from loguru import logger

# ============================================================
# Configuration
# ============================================================
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "egx_investment.db")

# Egyptian gold calculation constants
GOLD_PREMIUM_21K = 0.875
GOLD_PREMIUM_18K = 0.75
EGYPTIAN_WORKMANSHIP = 25.0

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


# ============================================================
# Helper Functions
# ============================================================
def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


async def fetch_json(url: str, method: str = "GET", json_payload: dict = None, timeout: int = 30) -> Optional[dict]:
    """Generic async JSON fetcher with retry"""
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as session:
                kwargs = {"timeout": aiohttp.ClientTimeout(total=timeout)}
                if method.upper() == "POST" and json_payload:
                    kwargs["json"] = json_payload
                async with session.request(method, url, **kwargs) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 429:
                        wait = 2 ** attempt
                        logger.warning(f"Rate limited on {url}, waiting {wait}s")
                        await asyncio.sleep(wait)
                    else:
                        text = await resp.text()
                        logger.error(f"HTTP {resp.status} from {url}: {text[:200]}")
                        return None
        except Exception as e:
            logger.error(f"Fetch error ({url}): {e}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
    return None


# ============================================================
# 1. CRYPTO — CoinGecko (prices) + Binance (1-min history)
# ============================================================
class CryptoSync:
    """Crypto data: CoinGecko for current prices, Binance for 1-minute candles"""

    COINGECKO_URL = "https://api.coingecko.com/api/v3"
    BINANCE_URL = "https://api.binance.com"
    
    TOP_COINS = [
        "bitcoin", "ethereum", "binancecoin", "solana", "ripple",
        "dogecoin", "cardano", "avalanche-2", "polkadot", "chainlink",
        "matic-network", "litecoin", "uniswap", "cosmos", "ethereum-classic"
    ]
    TOP_SYMBOLS = [
        "BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT", "LINK",
        "MATIC", "LTC", "UNI", "ATOM", "ETC"
    ]

    async def sync_coingecko_prices(self) -> Dict:
        """Fetch current prices from CoinGecko (updates crypto_prices table)"""
        logger.info("[CryptoSync] Fetching CoinGecko prices...")
        ids = ",".join(self.TOP_COINS)
        url = f"{self.COINGECKO_URL}/coins/markets?vs_currency=usd&ids={ids}&order=market_cap_desc&sparkline=false&price_change_percentage=24h"
        
        data = await fetch_json(url, timeout=15)
        if not data:
            return {"inserted": 0, "error": "CoinGecko API failed"}
        
        conn = sqlite3.connect(str(DB_PATH))
        try:
            cursor = conn.cursor()
            inserted = 0
            for coin in data:
                symbol = coin.get("symbol", "").upper()
                if not symbol:
                    continue
                cursor.execute("""
                    INSERT OR REPLACE INTO crypto_prices
                    (coin_id, name, symbol, current_price, market_cap, price_change_24h,
                     price_change_percentage_24h, high_24h, low_24h, volume_24h, ath, atl, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    coin.get("id"), coin.get("name"), symbol,
                    coin.get("current_price"), coin.get("market_cap"),
                    coin.get("price_change_24h"), coin.get("price_change_percentage_24h"),
                    coin.get("high_24h"), coin.get("low_24h"), coin.get("total_volume"),
                    coin.get("ath"), coin.get("atl")
                ))
                inserted += 1
                
                # Also update stocks table for analysis engine
                cursor.execute("""
                    INSERT OR IGNORE INTO stocks (ticker, name, current_price, sector)
                    VALUES (?, ?, ?, 'Crypto')
                """, (symbol, coin.get("name"), coin.get("current_price")))
                cursor.execute("""
                    UPDATE stocks SET current_price = ?, last_update = datetime('now') WHERE ticker = ?
                """, (coin.get("current_price"), symbol))
            
            conn.commit()
            logger.info(f"[CryptoSync] Updated {inserted} crypto prices from CoinGecko")
            return {"inserted": inserted}
        finally:
            conn.close()

    async def sync_binance_history(self, limit: int = 60) -> Dict:
        """Fetch 1-minute candles from Binance (stores in price_history table)"""
        logger.info("[CryptoSync] Fetching Binance 1-min history...")
        results = {"inserted": 0, "errors": []}
        
        conn = sqlite3.connect(str(DB_PATH))
        try:
            cursor = conn.cursor()
            for symbol in self.TOP_SYMBOLS[:10]:  # Top 10 only to avoid rate limits
                try:
                    url = f"{self.BINANCE_URL}/api/v3/klines?symbol={symbol}USDT&interval=1m&limit={limit}"
                    klines = await fetch_json(url, timeout=10)
                    if not klines:
                        continue
                    
                    for k in klines:
                        ts = datetime.fromtimestamp(k[0] / 1000).strftime("%Y-%m-%d %H:%M:%S")
                        cursor.execute("""
                            INSERT OR IGNORE INTO price_history (ticker, exchange, date, open, high, low, close, volume)
                            VALUES (?, 'BINANCE', ?, ?, ?, ?, ?, ?)
                        """, (symbol, ts, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])))
                        results["inserted"] += 1
                    
                    conn.commit()
                except Exception as e:
                    results["errors"].append(f"{symbol}: {str(e)}")
            
            logger.info(f"[CryptoSync] Inserted {results['inserted']} 1-min candles from Binance")
        finally:
            conn.close()
        
        return results

    async def sync_all(self) -> Dict:
        """Run both CoinGecko + Binance syncs"""
        cg = await self.sync_coingecko_prices()
        bn = await self.sync_binance_history()
        return {"coingecko": cg, "binance": bn}


# ============================================================
# 2. GOLD — Binance PAXG + USD/EGP calculation
# ============================================================
class GoldSync:
    """Gold: International from Binance PAXG, Egyptian calculated via USD/EGP"""

    async def fetch_usd_egp(self) -> Optional[float]:
        """Get USD/EGP rate"""
        try:
            data = await fetch_json("https://api.exchangerate-api.com/v4/latest/USD", timeout=10)
            if data and "rates" in data:
                rate = data["rates"].get("EGP")
                if rate:
                    return rate
        except Exception as e:
            logger.warning(f"exchangerate-api failed: {e}")
        
        # Fallback to cached
        conn = sqlite3.connect(str(DB_PATH))
        try:
            row = conn.execute("SELECT buy_rate FROM currency_rates WHERE code='USD' ORDER BY updated_at DESC LIMIT 1").fetchone()
            if row and row[0]:
                return row[0]
        finally:
            conn.close()
        
        return 50.0  # Hardcoded fallback

    async def fetch_paxg_price(self) -> Optional[float]:
        """Fetch PAXG (tokenized gold) price from Binance in USDT"""
        try:
            data = await fetch_json("https://api.binance.com/api/v3/ticker/price?symbol=PAXGUSDT", timeout=10)
            if data and "price" in data:
                return float(data["price"])
        except Exception as e:
            logger.warning(f"Binance PAXG failed: {e}")
        return None

    def calculate_egyptian_prices(self, usd_per_oz: float, usd_egp: float) -> Dict[str, float]:
        """Calculate Egyptian gold prices per gram"""
        grams_per_oz = 31.1034768
        usd_per_gram = usd_per_oz / grams_per_oz
        egp_per_gram_24k = usd_per_gram * usd_egp
        
        return {
            "24": round(egp_per_gram_24k + EGYPTIAN_WORKMANSHIP, 2),
            "21": round(egp_per_gram_24k * GOLD_PREMIUM_21K + EGYPTIAN_WORKMANSHIP, 2),
            "18": round(egp_per_gram_24k * GOLD_PREMIUM_18K + EGYPTIAN_WORKMANSHIP, 2),
        }

    async def sync(self) -> Dict:
        """Sync gold prices"""
        logger.info("[GoldSync] Starting sync...")
        
        usd_egp = await self.fetch_usd_egp()
        paxg = await self.fetch_paxg_price()
        
        if not paxg:
            return {"error": "Failed to fetch PAXG price"}
        
        prices = self.calculate_egyptian_prices(paxg, usd_egp)
        now = datetime.now().isoformat()
        today = datetime.now().strftime("%Y-%m-%d")
        
        conn = sqlite3.connect(str(DB_PATH))
        try:
            cursor = conn.cursor()
            
            for karat, price in prices.items():
                name_map = {"24": "ذهب عيار 24", "21": "ذهب عيار 21", "18": "ذهب عيار 18"}
                # Update gold_prices
                cursor.execute("""
                    INSERT OR REPLACE INTO gold_prices (karat, name_ar, price_per_gram, change, currency, updated_at, updated_by)
                    VALUES (?, ?, ?, 0, 'EGP', ?, 'external_data_sync')
                """, (karat, name_map[karat], price, now))
                
                # Insert into gold_price_history
                cursor.execute("""
                    INSERT INTO gold_price_history (karat, price_per_gram, change, currency, recorded_at, source)
                    VALUES (?, ?, 0, 'EGP', ?, 'Binance PAXG')
                """, (karat, price, now))
                
                # Update stocks table
                ticker = f"GOLD_{karat}K"
                cursor.execute("""
                    INSERT OR IGNORE INTO stocks (ticker, name, current_price, sector)
                    VALUES (?, ?, ?, 'Gold')
                """, (ticker, name_map[karat], price))
                cursor.execute("""
                    UPDATE stocks SET current_price = ?, last_update = datetime('now') WHERE ticker = ?
                """, (price, ticker))
            
            # Also store international reference
            cursor.execute("""
                INSERT OR REPLACE INTO gold_prices (karat, name_ar, price_per_gram, change, currency, updated_at, updated_by)
                VALUES ('24_INTL', 'ذهب عيار 24 دولي', ?, 0, 'USD', ?, 'external_data_sync')
            """, (paxg, now))
            
            conn.commit()
            logger.info(f"[GoldSync] 24K={prices['24']} EGP, 21K={prices['21']} EGP, USD/EGP={usd_egp}")
            return {"prices": prices, "usd_egp": usd_egp, "intl_usd": paxg}
        finally:
            conn.close()


# ============================================================
# 3. CURRENCY — exchangerate-api.com
# ============================================================
class CurrencySync:
    """Currency rates from exchangerate-api.com"""

    CODES = ["USD", "EUR", "GBP", "SAR", "AED", "KWD", "JPY", "CNY"]

    async def sync(self) -> Dict:
        """Sync all currency rates against EGP"""
        logger.info("[CurrencySync] Starting sync...")
        
        data = await fetch_json("https://api.exchangerate-api.com/v4/latest/USD", timeout=15)
        if not data or "rates" not in data:
            return {"error": "Failed to fetch rates"}
        
        rates = data["rates"]
        usd_egp = rates.get("EGP", 50.0)
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(str(DB_PATH))
        try:
            cursor = conn.cursor()
            inserted = 0
            
            for code in self.CODES:
                try:
                    if code == "USD":
                        buy = sell = usd_egp
                    else:
                        usd_rate = rates.get(code, 0)
                        if usd_rate:
                            buy = sell = round(usd_egp / usd_rate, 4)
                        else:
                            continue
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO currency_rates 
                        (code, name_ar, buy_rate, sell_rate, change, is_major, updated_at, updated_by)
                        VALUES (?, ?, ?, ?, 0, 1, ?, 'external_data_sync')
                    """, (code, code, buy, sell, now))
                    inserted += 1
                except Exception as e:
                    logger.warning(f"Currency {code}: {e}")
            
            conn.commit()
            logger.info(f"[CurrencySync] Updated {inserted} currencies")
            return {"inserted": inserted, "usd_egp": usd_egp}
        finally:
            conn.close()


# ============================================================
# 4. EGX STOCKS — EGX website scraping fallback
# ============================================================
class EGXScraperSync:
    """Fallback: scrape EGX website when Mubasher is stale."""
    
    async def sync(self) -> Dict:
        logger.warning("[EGXScraper] EGX scraping not yet implemented. "
                       "MubasherTrade desktop app is still the primary source.")
        return {"success": False, "note": "MubasherTrade is primary source", "stocks": []}


# ============================================================
# Unified Runner
# ============================================================
async def sync_all_external_data() -> Dict:
    """Run all external syncs"""
    logger.info("=" * 60)
    logger.info("[ExternalDataSync] Starting ALL syncs...")
    logger.info("=" * 60)
    
    crypto = CryptoSync()
    gold = GoldSync()
    currency = CurrencySync()
    egx = EGXScraperSync()
    
    results = await asyncio.gather(
        crypto.sync_all(),
        gold.sync(),
        currency.sync(),
        egx.sync(),
        return_exceptions=True
    )
    
    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "crypto": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
        "gold": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
        "currency": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
        "egx": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
    }


def sync_all_external_data_sync() -> Dict:
    """Synchronous wrapper"""
    return asyncio.run(sync_all_external_data())


if __name__ == "__main__":
    result = sync_all_external_data_sync()
    print(json.dumps(result, indent=2, ensure_ascii=False))
