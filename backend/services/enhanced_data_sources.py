#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مصادر البيانات المحسنة
Enhanced Data Sources with Multiple APIs
"""

import os
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "egx_investment.db")

# API Keys
API_KEYS = {
    "twelvedata": "821e4b4a88874941af581ad4d3141d93",
    "eodhd": "6990ef9ee966c5.41761316",
    "alphavantage": "UOTWJFFUX1SLZ63W",  # Free: 25 calls/day
    "marketstack": "49e316b2786f93cb87c674bdcf6a595d",  # Free: 100 calls/month
    "fcsapi": "n6RbYitzjnw0xx32h0IlgP",  # Free: 100 calls/month
    # مصادر مجانية إضافية (بدون مفتاح أو بمفتاح مجاني)
    "polygon": "demo",  # Free: 5 calls/min
    "fmp": "demo",  # Financial Modeling Prep - Free tier
    "iex": "pk_demo",  # IEX Cloud - Free sandbox
    "binance": "",  # No key needed for public endpoints
    "coincap": "",  # No key needed
}

class EnhancedDataSources:
    """مصادر البيانات المحسنة"""
    
    def __init__(self):
        self.sources = {
            "website": {
                "name": "الموقع الحي",
                "url": "https://invist.m2y.net/api",
                "type": "stocks",
                "free_limit": "غير محدود"
            },
            "twelvedata": {
                "name": "Twelve Data",
                "url": "https://api.twelvedata.com",
                "type": "stocks/crypto/forex",
                "free_limit": "800 calls/day",
                "api_key": API_KEYS["twelvedata"]
            },
            "eodhd": {
                "name": "EODHD",
                "url": "https://eodhistoricaldata.com/api",
                "type": "stocks/etf/indices",
                "free_limit": "20 calls/day",
                "api_key": API_KEYS["eodhd"]
            },
            "alphavantage": {
                "name": "Alpha Vantage",
                "url": "https://www.alphavantage.co/query",
                "type": "stocks/crypto/forex",
                "free_limit": "25 calls/day",
                "api_key": API_KEYS["alphavantage"]
            },
            "coingecko": {
                "name": "CoinGecko",
                "url": "https://api.coingecko.com/api/v3",
                "type": "crypto",
                "free_limit": "10-50 calls/min"
            },
            "yahoo_finance": {
                "name": "Yahoo Finance (yfinance)",
                "url": "https://query1.finance.yahoo.com/v8/finance",
                "type": "stocks/crypto/etf",
                "free_limit": "غير محدود (تقريباً)"
            },
            "finnhub": {
                "name": "Finnhub",
                "url": "https://finnhub.io/api/v1",
                "type": "stocks/crypto/forex",
                "free_limit": "60 calls/min",
                "api_key": "demo"  # Free demo
            },
            # مصادر مجانية إضافية
            "polygon": {
                "name": "Polygon.io",
                "url": "https://api.polygon.io/v2",
                "type": "stocks/crypto/forex",
                "free_limit": "5 calls/min (100,000/month)",
                "api_key": API_KEYS["polygon"]
            },
            "fmp": {
                "name": "Financial Modeling Prep",
                "url": "https://financialmodelingprep.com/api/v3",
                "type": "stocks/etf/crypto",
                "free_limit": "250 calls/day",
                "api_key": API_KEYS["fmp"]
            },
            "coincap": {
                "name": "CoinCap",
                "url": "https://api.coincap.io/v2",
                "type": "crypto",
                "free_limit": "غير محدود"
            },
            "binance": {
                "name": "Binance API",
                "url": "https://api.binance.com/api/v3",
                "type": "crypto",
                "free_limit": "غير محدود"
            },
            "marketstack": {
                "name": "MarketStack",
                "url": "http://api.marketstack.com/v1",
                "type": "stocks/etf/indices",
                "free_limit": "100 calls/month",
                "api_key": API_KEYS["marketstack"]
            },
            "fcsapi": {
                "name": "FCS API",
                "url": "https://fcsapi.com/api-v3",
                "type": "forex/stocks/crypto",
                "free_limit": "100 calls/month",
                "api_key": API_KEYS["fcsapi"]
            }
        }
        self.usage = {k: {"calls": 0, "last_call": None} for k in self.sources}
    
    def test_source(self, source_id: str) -> Dict:
        """اختبار مصدر بيانات"""
        source = self.sources.get(source_id)
        if not source:
            return {"success": False, "error": "Source not found"}
        
        try:
            if source_id == "website":
                resp = requests.get(f"{source['url']}/stocks", timeout=10)
                return {"success": resp.ok, "stocks": resp.json().get("total", 0)}
            
            elif source_id == "twelvedata":
                resp = requests.get(
                    f"{source['url']}/quote",
                    params={"symbol": "AAPL", "apikey": source["api_key"]},
                    timeout=10
                )
                return {"success": resp.ok, "status": "Working" if resp.ok else "Error"}
            
            elif source_id == "eodhd":
                resp = requests.get(
                    f"{source['url']}/EOD/AAPL.US",
                    params={"api_token": source["api_key"], "fmt": "json"},
                    timeout=10
                )
                return {"success": resp.ok, "status": "Working" if resp.ok else "Error"}
            
            elif source_id == "alphavantage":
                resp = requests.get(
                    source["url"],
                    params={"function": "GLOBAL_QUOTE", "symbol": "IBM", "apikey": source["api_key"]},
                    timeout=10
                )
                return {"success": resp.ok, "status": "Working" if resp.ok else "Error"}
            
            elif source_id == "coingecko":
                resp = requests.get(f"{source['url']}/ping", timeout=10)
                return {"success": resp.ok, "status": resp.json()}
            
            elif source_id == "yahoo_finance":
                resp = requests.get(
                    f"{source['url']}/chart/AAPL",
                    timeout=10
                )
                return {"success": resp.ok, "status": "Working" if resp.ok else "Error"}
            
            elif source_id == "finnhub":
                resp = requests.get(
                    f"{source['url']}/quote",
                    params={"symbol": "AAPL", "token": source["api_key"]},
                    timeout=10
                )
                return {"success": resp.ok, "status": "Working" if resp.ok else "Error"}
            
            # مصادر مجانية إضافية
            elif source_id == "polygon":
                # Polygon.io test
                resp = requests.get(
                    f"{source['url']}/aggs/ticker/AAPL/prev",
                    params={"apiKey": source["api_key"]},
                    timeout=10
                )
                return {"success": resp.ok, "status": "Working" if resp.ok else "Error"}
            
            elif source_id == "fmp":
                # Financial Modeling Prep test
                resp = requests.get(
                    f"{source['url']}/quote/AAPL",
                    params={"apikey": source["api_key"]},
                    timeout=10
                )
                return {"success": resp.ok, "status": "Working" if resp.ok else "Error"}
            
            elif source_id == "coincap":
                # CoinCap test (no key needed)
                resp = requests.get(f"{source['url']}/assets?limit=1", timeout=10)
                return {"success": resp.ok, "status": "Working" if resp.ok else "Error"}
            
            elif source_id == "binance":
                # Binance test (no key needed)
                resp = requests.get(f"{source['url']}/ticker/price?symbol=BTCUSDT", timeout=10)
                return {"success": resp.ok, "status": "Working" if resp.ok else "Error"}
            
            elif source_id == "marketstack":
                # MarketStack test
                resp = requests.get(
                    f"{source['url']}/eod",
                    params={"access_key": source["api_key"], "symbols": "AAPL", "limit": 1},
                    timeout=10
                )
                return {"success": resp.ok, "status": "Working" if resp.ok else "Error"}
            
            elif source_id == "fcsapi":
                # FCS API test
                resp = requests.get(
                    f"{source['url']}/stock/latest",
                    params={"symbol": "AAPL", "access_key": source["api_key"]},
                    timeout=10
                )
                return {"success": resp.ok, "status": "Working" if resp.ok else "Error"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Unknown"}
    
    def test_all(self) -> Dict:
        """اختبار كل المصادر"""
        results = {}
        for source_id in self.sources:
            result = self.test_source(source_id)
            results[source_id] = {
                "name": self.sources[source_id]["name"],
                "status": "🟢 Online" if result["success"] else "🔴 Offline",
                "details": result
            }
        return results
    
    # ==================== Twelve Data ====================
    
    def fetch_from_twelvedata(self, symbol: str, exchange: str = "EGX") -> Optional[Dict]:
        """جلب بيانات من Twelve Data"""
        try:
            # Quote
            quote_url = f"{self.sources['twelvedata']['url']}/quote"
            params = {
                "symbol": symbol,
                "exchange": exchange,
                "apikey": self.sources['twelvedata']['api_key']
            }
            
            resp = requests.get(quote_url, params=params, timeout=15)
            
            if resp.ok:
                data = resp.json()
                if "symbol" in data:
                    return {
                        "ticker": symbol.upper(),
                        "current_price": float(data.get("close", 0)),
                        "open": float(data.get("open", 0)),
                        "high": float(data.get("high", 0)),
                        "low": float(data.get("low", 0)),
                        "volume": int(data.get("volume", 0)),
                        "previous_close": float(data.get("previous_close", 0)),
                        "change": float(data.get("change", 0)),
                        "change_percent": float(data.get("percent_change", 0)),
                        "source": "twelvedata"
                    }
        except Exception as e:
            print(f"Twelve Data Error: {e}")
        return None
    
    def fetch_history_twelvedata(self, symbol: str, interval: str = "1day", 
                                  outputsize: int = 100, exchange: str = "EGX") -> List[Dict]:
        """جلب بيانات تاريخية من Twelve Data"""
        try:
            url = f"{self.sources['twelvedata']['url']}/time_series"
            params = {
                "symbol": symbol,
                "interval": interval,
                "outputsize": outputsize,
                "exchange": exchange,
                "apikey": self.sources['twelvedata']['api_key']
            }
            
            resp = requests.get(url, params=params, timeout=30)
            
            if resp.ok:
                data = resp.json()
                values = data.get("values", [])
                
                return [{
                    "date": v["datetime"],
                    "open": float(v["open"]),
                    "high": float(v["high"]),
                    "low": float(v["low"]),
                    "close": float(v["close"]),
                    "volume": int(v.get("volume", 0))
                } for v in values]
        except Exception as e:
            print(f"Twelve Data History Error: {e}")
        return []
    
    # ==================== EODHD ====================
    
    def fetch_from_eodhd(self, symbol: str, exchange: str = "EGX") -> Optional[Dict]:
        """جلب بيانات من EODHD"""
        try:
            url = f"{self.sources['eodhd']['url']}/real-time/{symbol}.{exchange}"
            params = {
                "api_token": self.sources['eodhd']['api_key'],
                "fmt": "json"
            }
            
            resp = requests.get(url, params=params, timeout=15)
            
            if resp.ok:
                data = resp.json()
                if isinstance(data, list):
                    data = data[0]
                
                return {
                    "ticker": symbol.upper(),
                    "current_price": float(data.get("close", 0)),
                    "open": float(data.get("open", 0)),
                    "high": float(data.get("high", 0)),
                    "low": float(data.get("low", 0)),
                    "volume": int(data.get("volume", 0)),
                    "previous_close": float(data.get("previousClose", 0)),
                    "source": "eodhd"
                }
        except Exception as e:
            print(f"EODHD Error: {e}")
        return None
    
    def fetch_history_eodhd(self, symbol: str, days: int = 100, exchange: str = "EGX") -> List[Dict]:
        """جلب بيانات تاريخية من EODHD"""
        try:
            url = f"{self.sources['eodhd']['url']}/eod/{symbol}.{exchange}"
            params = {
                "api_token": self.sources['eodhd']['api_key'],
                "fmt": "json",
                "period": "d"
            }
            
            resp = requests.get(url, params=params, timeout=30)
            
            if resp.ok:
                data = resp.json()
                
                return [{
                    "date": v["date"],
                    "open": float(v["open"]),
                    "high": float(v["high"]),
                    "low": float(v["low"]),
                    "close": float(v["close"]),
                    "volume": int(v.get("volume", 0))
                } for v in data[:days]]
        except Exception as e:
            print(f"EODHD History Error: {e}")
        return []
    
    # ==================== Alpha Vantage ====================
    
    def fetch_from_alphavantage(self, symbol: str) -> Optional[Dict]:
        """جلب بيانات من Alpha Vantage"""
        try:
            url = self.sources['alphavantage']['url']
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.sources['alphavantage']['api_key']
            }
            
            resp = requests.get(url, params=params, timeout=15)
            
            if resp.ok:
                data = resp.json()
                quote = data.get("Global Quote", {})
                
                if quote:
                    return {
                        "ticker": symbol.upper(),
                        "current_price": float(quote.get("05. price", 0)),
                        "open": float(quote.get("02. open", 0)),
                        "high": float(quote.get("03. high", 0)),
                        "low": float(quote.get("04. low", 0)),
                        "volume": int(quote.get("06. volume", 0)),
                        "previous_close": float(quote.get("08. previous close", 0)),
                        "change": float(quote.get("09. change", 0)),
                        "change_percent": float(quote.get("10. change percent", "0%").replace("%", "")),
                        "source": "alphavantage"
                    }
        except Exception as e:
            print(f"Alpha Vantage Error: {e}")
        return None
    
    # ==================== CoinGecko ====================
    
    def fetch_crypto_from_coingecko(self, limit: int = 50) -> List[Dict]:
        """جلب بيانات العملات الرقمية من CoinGecko"""
        try:
            url = f"{self.sources['coingecko']['url']}/coins/markets"
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": "false"
            }
            
            resp = requests.get(url, params=params, timeout=30)
            
            if resp.ok:
                coins = resp.json()
                return [{
                    "id": c["id"],
                    "symbol": c["symbol"].upper(),
                    "name": c["name"],
                    "current_price": c["current_price"],
                    "market_cap": c["market_cap"],
                    "market_cap_rank": c["market_cap_rank"],
                    "price_change_24h": c.get("price_change_percentage_24h"),
                    "total_volume": c.get("total_volume"),
                    "high_24h": c.get("high_24h"),
                    "low_24h": c.get("low_24h"),
                    "source": "coingecko"
                } for c in coins]
        except Exception as e:
            print(f"CoinGecko Error: {e}")
        return []
    
    # ==================== Yahoo Finance ====================
    
    def fetch_from_yahoo(self, symbol: str) -> Optional[Dict]:
        """جلب بيانات من Yahoo Finance (بدون مكتبة)"""
        try:
            url = f"{self.sources['yahoo_finance']['url']}/finance/chart/{symbol}"
            params = {"interval": "1d", "range": "1d"}
            
            resp = requests.get(url, params=params, timeout=15)
            
            if resp.ok:
                data = resp.json()
                result = data.get("chart", {}).get("result", [{}])[0]
                meta = result.get("meta", {})
                
                return {
                    "ticker": symbol.upper(),
                    "current_price": meta.get("regularMarketPrice"),
                    "previous_close": meta.get("previousClose"),
                    "open": meta.get("regularMarketPrice"),
                    "currency": meta.get("currency"),
                    "exchange": meta.get("exchangeName"),
                    "source": "yahoo_finance"
                }
        except Exception as e:
            print(f"Yahoo Finance Error: {e}")
        return None
    
    # ==================== Finnhub ====================
    
    def fetch_from_finnhub(self, symbol: str) -> Optional[Dict]:
        """جلب بيانات من Finnhub"""
        try:
            url = f"{self.sources['finnhub']['url']}/quote"
            params = {
                "symbol": symbol,
                "token": self.sources['finnhub']['api_key']
            }
            
            resp = requests.get(url, params=params, timeout=15)
            
            if resp.ok:
                data = resp.json()
                
                if data.get("c"):  # current price
                    return {
                        "ticker": symbol.upper(),
                        "current_price": float(data["c"]),
                        "high": float(data.get("h", 0)),
                        "low": float(data.get("l", 0)),
                        "open": float(data.get("o", 0)),
                        "previous_close": float(data.get("pc", 0)),
                        "change": float(data.get("d", 0)),
                        "change_percent": float(data.get("dp", 0)),
                        "source": "finnhub"
                    }
        except Exception as e:
            print(f"Finnhub Error: {e}")
        return None
    
    # ==================== CoinCap (مجاني - بدون مفتاح) ====================
    
    def fetch_crypto_from_coincap(self, limit: int = 50) -> List[Dict]:
        """جلب بيانات العملات الرقمية من CoinCap (مجاني تماماً)"""
        try:
            url = f"{self.sources['coincap']['url']}/assets"
            params = {"limit": limit}
            
            resp = requests.get(url, params=params, timeout=30)
            
            if resp.ok:
                data = resp.json()
                coins = data.get("data", [])
                
                return [{
                    "id": c["id"],
                    "symbol": c["symbol"].upper(),
                    "name": c["name"],
                    "current_price": float(c.get("priceUsd", 0)),
                    "market_cap": float(c.get("marketCapUsd", 0)),
                    "market_cap_rank": c.get("rank"),
                    "price_change_24h": float(c.get("changePercent24Hr", 0)),
                    "volume": float(c.get("volumeUsd24Hr", 0)),
                    "source": "coincap"
                } for c in coins]
        except Exception as e:
            print(f"CoinCap Error: {e}")
        return []
    
    # ==================== Binance API (مجاني - بدون مفتاح) ====================
    
    def fetch_crypto_from_binance(self, symbols: List[str] = None) -> List[Dict]:
        """جلب أسعار العملات من Binance (مجاني تماماً)"""
        try:
            # جلب كل الأسعار
            url = f"{self.sources['binance']['url']}/ticker/24hr"
            resp = requests.get(url, timeout=30)
            
            if resp.ok:
                data = resp.json()
                
                # فلترة العملات مقابل USDT فقط
                usdt_pairs = [d for d in data if d["symbol"].endswith("USDT")]
                
                # ترتيب حسب الحجم
                usdt_pairs.sort(key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)
                
                return [{
                    "symbol": d["symbol"].replace("USDT", ""),
                    "current_price": float(d.get("lastPrice", 0)),
                    "price_change_24h": float(d.get("priceChangePercent", 0)),
                    "high_24h": float(d.get("highPrice", 0)),
                    "low_24h": float(d.get("lowPrice", 0)),
                    "volume": float(d.get("volume", 0)),
                    "quote_volume": float(d.get("quoteVolume", 0)),
                    "source": "binance"
                } for d in usdt_pairs[:100]]  # أعلى 100 عملة
        except Exception as e:
            print(f"Binance Error: {e}")
        return []
    
    # ==================== Polygon.io ====================
    
    def fetch_from_polygon(self, symbol: str) -> Optional[Dict]:
        """جلب بيانات من Polygon.io"""
        try:
            url = f"{self.sources['polygon']['url']}/aggs/ticker/{symbol}/prev"
            params = {"apiKey": self.sources['polygon']['api_key']}
            
            resp = requests.get(url, params=params, timeout=15)
            
            if resp.ok:
                data = resp.json()
                results = data.get("results", [])
                
                if results:
                    r = results[0]
                    return {
                        "ticker": symbol.upper(),
                        "current_price": float(r.get("c", 0)),
                        "open": float(r.get("o", 0)),
                        "high": float(r.get("h", 0)),
                        "low": float(r.get("l", 0)),
                        "volume": int(r.get("v", 0)),
                        "source": "polygon"
                    }
        except Exception as e:
            print(f"Polygon Error: {e}")
        return None
    
    # ==================== Financial Modeling Prep ====================
    
    def fetch_from_fmp(self, symbol: str) -> Optional[Dict]:
        """جلب بيانات من Financial Modeling Prep"""
        try:
            url = f"{self.sources['fmp']['url']}/quote/{symbol}"
            params = {"apikey": self.sources['fmp']['api_key']}
            
            resp = requests.get(url, params=params, timeout=15)
            
            if resp.ok:
                data = resp.json()
                
                if data and isinstance(data, list) and len(data) > 0:
                    q = data[0]
                    return {
                        "ticker": symbol.upper(),
                        "current_price": float(q.get("price", 0)),
                        "open": float(q.get("open", 0)),
                        "high": float(q.get("dayHigh", 0)),
                        "low": float(q.get("dayLow", 0)),
                        "volume": int(q.get("volume", 0)),
                        "market_cap": float(q.get("marketCap", 0)),
                        "pe_ratio": q.get("pe"),
                        "source": "fmp"
                    }
        except Exception as e:
            print(f"FMP Error: {e}")
        return None
    
    # ==================== MarketStack ====================
    
    def fetch_from_marketstack(self, symbol: str) -> Optional[Dict]:
        """جلب بيانات من MarketStack"""
        try:
            url = f"{self.sources['marketstack']['url']}/eod/latest"
            params = {
                "access_key": self.sources['marketstack']['api_key'],
                "symbols": symbol
            }
            
            resp = requests.get(url, params=params, timeout=15)
            
            if resp.ok:
                data = resp.json()
                results = data.get("data", [])
                
                if results:
                    r = results[0]
                    return {
                        "ticker": symbol.upper(),
                        "current_price": float(r.get("close", 0)),
                        "open": float(r.get("open", 0)),
                        "high": float(r.get("high", 0)),
                        "low": float(r.get("low", 0)),
                        "volume": int(r.get("volume", 0)),
                        "date": r.get("date"),
                        "source": "marketstack"
                    }
        except Exception as e:
            print(f"MarketStack Error: {e}")
        return None
    
    # ==================== Multi-Source Fetch ====================
    
    def fetch_stock_data(self, symbol: str, exchange: str = "EGX") -> Dict:
        """جلب بيانات السهم من أفضل مصدر متاح"""
        
        # ترتيب الأولويات
        sources_priority = [
            ("website", lambda: self._fetch_from_website(symbol)),
            ("twelvedata", lambda: self.fetch_from_twelvedata(symbol, exchange)),
            ("eodhd", lambda: self.fetch_from_eodhd(symbol, exchange)),
            ("finnhub", lambda: self.fetch_from_finnhub(symbol)),
            ("alphavantage", lambda: self.fetch_from_alphavantage(symbol)),
            ("yahoo_finance", lambda: self.fetch_from_yahoo(symbol))
        ]
        
        for source_name, fetch_func in sources_priority:
            try:
                data = fetch_func()
                if data and data.get("current_price"):
                    data["source"] = source_name
                    return data
            except Exception as e:
                print(f"{source_name} failed: {e}")
                continue
        
        return {"success": False, "error": "All sources failed"}
    
    def _fetch_from_website(self, symbol: str) -> Optional[Dict]:
        """جلب من الموقع الحي"""
        try:
            url = f"{self.sources['website']['url']}/stocks/{symbol}"
            resp = requests.get(url, timeout=10)
            
            if resp.ok:
                data = resp.json()
                return {
                    "ticker": symbol.upper(),
                    "current_price": data.get("current_price"),
                    "name": data.get("name"),
                    "sector": data.get("sector"),
                    "source": "website"
                }
        except:
            pass
        return None
    
    def save_to_db(self, data: Dict) -> bool:
        """حفظ البيانات في قاعدة البيانات"""
        if not data or not data.get("ticker"):
            return False
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            ticker = data["ticker"]
            
            # تحديث السهم
            if data.get("current_price"):
                cursor.execute("""
                    UPDATE stocks 
                    SET current_price = ?,
                        previous_close = COALESCE(?, previous_close),
                        open_price = COALESCE(?, open_price),
                        high_price = COALESCE(?, high_price),
                        low_price = COALESCE(?, low_price),
                        volume = COALESCE(?, volume),
                        last_update = ?
                    WHERE ticker = ?
                """, (
                    data["current_price"],
                    data.get("previous_close"),
                    data.get("open"),
                    data.get("high"),
                    data.get("low"),
                    data.get("volume"),
                    datetime.now().isoformat(),
                    ticker
                ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"DB Error: {e}")
            return False


def test_all_sources():
    """اختبار كل المصادر"""
    ds = EnhancedDataSources()
    
    print("=" * 60)
    print("🔍 اختبار مصادر البيانات")
    print("=" * 60)
    
    results = ds.test_all()
    
    print("\n📊 النتائج:")
    for source_id, info in results.items():
        print(f"  {info['status']} {info['name']}")
    
    # اختبار جلب بيانات الأسهم
    print("\n🔄 اختبار جلب بيانات الأسهم (AAPL):")
    data = ds.fetch_from_twelvedata("AAPL", "NASDAQ")
    if data:
        print(f"  ✅ Twelve Data: ${data['current_price']}")
    
    data = ds.fetch_from_finnhub("AAPL")
    if data:
        print(f"  ✅ Finnhub: ${data['current_price']}")
    
    # اختبار جلب العملات الرقمية
    print("\n💰 اختبار جلب العملات الرقمية:")
    
    # CoinGecko
    coins = ds.fetch_crypto_from_coingecko(5)
    if coins:
        print(f"  ✅ CoinGecko: {len(coins)} عملة - BTC: ${coins[0]['current_price']}")
    
    # CoinCap
    coins = ds.fetch_crypto_from_coincap(5)
    if coins:
        print(f"  ✅ CoinCap: {len(coins)} عملة - BTC: ${coins[0]['current_price']:.2f}")
    
    # Binance
    coins = ds.fetch_crypto_from_binance()
    if coins:
        btc = next((c for c in coins if c['symbol'] == 'BTC'), None)
        if btc:
            print(f"  ✅ Binance: {len(coins)} عملة - BTC: ${btc['current_price']}")
    
    print("\n" + "=" * 60)
    print("✅ انتهى الاختبار")
    print("=" * 60)


if __name__ == "__main__":
    test_all_sources()
