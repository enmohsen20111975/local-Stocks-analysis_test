#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مصادر البيانات المتعددة
Multiple Data Sources for EGX Investment Platform
"""

import os
import json
import sqlite3
import requests
from datetime import datetime
from typing import Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "egx_investment.db")

class DataSources:
    """مصادر البيانات المتعددة"""
    
    def __init__(self):
        self.sources = {
            "website": {
                "name": "الموقع الحي",
                "url": "https://invist.m2y.net/api",
                "type": "stocks",
                "status": "unknown"
            },
            "vps_egx": {
                "name": "VPS - EGX",
                "url": "http://72.61.137.86:8010",
                "type": "stocks",
                "status": "unknown"
            },
            "vps_crypto": {
                "name": "VPS - Crypto",
                "url": "http://72.61.137.86:8012",
                "type": "crypto",
                "status": "unknown"
            },
            "coingecko": {
                "name": "CoinGecko",
                "url": "https://api.coingecko.com/api/v3",
                "type": "crypto",
                "status": "unknown"
            },
            "twelvedata": {
                "name": "Twelve Data",
                "url": "https://api.twelvedata.com",
                "type": "stocks",
                "api_key": "821e4b4a88874941af581ad4d3141d93",
                "status": "unknown"
            }
        }
    
    def test_source(self, source_id: str) -> Dict:
        """اختبار مصدر بيانات"""
        source = self.sources.get(source_id)
        if not source:
            return {"success": False, "error": "Source not found"}
        
        try:
            if source_id == "website":
                resp = requests.get(f"{source['url']}/stocks", timeout=10)
                data = resp.json()
                count = len(data.get("stocks", []))
                return {"success": True, "stocks": count}
                
            elif source_id == "vps_egx":
                resp = requests.get(f"{source['url']}/health", timeout=10)
                return {"success": resp.ok, "status": resp.json() if resp.ok else None}
                
            elif source_id == "vps_crypto":
                resp = requests.get(f"{source['url']}/health", timeout=10)
                return {"success": resp.ok, "status": resp.json() if resp.ok else None}
                
            elif source_id == "coingecko":
                resp = requests.get(f"{source['url']}/ping", timeout=10)
                return {"success": resp.ok, "status": resp.json()}
                
            elif source_id == "twelvedata":
                resp = requests.get(
                    f"{source['url']}/usage",
                    params={"apikey": source["api_key"]},
                    timeout=10
                )
                return {"success": resp.ok, "status": resp.json() if resp.ok else None}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Unknown source"}
    
    def test_all_sources(self) -> Dict:
        """اختبار كل المصادر"""
        results = {}
        for source_id in self.sources:
            result = self.test_source(source_id)
            self.sources[source_id]["status"] = "online" if result["success"] else "offline"
            results[source_id] = {
                "name": self.sources[source_id]["name"],
                "status": self.sources[source_id]["status"],
                "details": result
            }
        return results
    
    def fetch_crypto_from_coingecko(self, limit: int = 50) -> List[Dict]:
        """جلب بيانات العملات الرقمية من CoinGecko"""
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": "false"
            }
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            
            coins = resp.json()
            return [{
                "id": c["id"],
                "symbol": c["symbol"].upper(),
                "name": c["name"],
                "current_price": c["current_price"],
                "market_cap": c["market_cap"],
                "market_cap_rank": c["market_cap_rank"],
                "price_change_24h": c["price_change_percentage_24h"],
                "total_volume": c["total_volume"],
                "high_24h": c["high_24h"],
                "low_24h": c["low_24h"],
                "source": "coingecko"
            } for c in coins]
        except Exception as e:
            print(f"خطأ في CoinGecko: {e}")
            return []
    
    def fetch_crypto_from_vps(self) -> List[Dict]:
        """جلب بيانات العملات الرقمية من VPS"""
        try:
            url = "http://72.61.137.86:8012/api/crypto/top/50"
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json().get("coins", [])
        except Exception as e:
            print(f"خطأ في VPS Crypto: {e}")
            return []
    
    def save_crypto_to_db(self, coins: List[Dict]) -> Dict:
        """حفظ العملات الرقمية في قاعدة البيانات"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        inserted = 0
        updated = 0
        
        for coin in coins:
            coin_id = coin.get("id") or coin.get("symbol", "").lower()
            
            try:
                # Check if exists
                cursor.execute("SELECT id FROM price_history WHERE ticker = ?", (coin_id,))
                exists = cursor.fetchone()
                
                # Insert price record
                cursor.execute("""
                    INSERT INTO price_history (ticker, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    coin_id,
                    datetime.now().strftime("%Y-%m-%d"),
                    coin.get("low_24h") or coin.get("current_price"),
                    coin.get("high_24h") or coin.get("current_price"),
                    coin.get("low_24h") or coin.get("current_price"),
                    coin.get("current_price"),
                    coin.get("total_volume", 0)
                ))
                
                if exists:
                    updated += 1
                else:
                    inserted += 1
                    
            except Exception as e:
                print(f"خطأ في حفظ {coin_id}: {e}")
        
        conn.commit()
        conn.close()
        
        return {"inserted": inserted, "updated": updated}
    
    def sync_crypto(self) -> Dict:
        """مزامنة العملات الرقمية من كل المصادر"""
        print("🔄 مزامنة العملات الرقمية...")
        
        # Try VPS first
        coins = self.fetch_crypto_from_vps()
        source = "VPS"
        
        if not coins:
            # Fallback to CoinGecko
            coins = self.fetch_crypto_from_coingecko()
            source = "CoinGecko"
        
        if not coins:
            return {"success": False, "error": "فشل في جلب البيانات"}
        
        print(f"✅ تم جلب {len(coins)} عملة من {source}")
        
        # Save to database
        result = self.save_crypto_to_db(coins)
        
        return {
            "success": True,
            "source": source,
            "coins": len(coins),
            "saved": result
        }


def main():
    """اختبار مصادر البيانات"""
    ds = DataSources()
    
    print("=" * 60)
    print("🔍 اختبار مصادر البيانات")
    print("=" * 60)
    
    # اختبار كل المصادر
    results = ds.test_all_sources()
    
    print("\n📊 نتائج الاختبار:")
    for source_id, info in results.items():
        status = "🟢" if info["status"] == "online" else "🔴"
        print(f"  {status} {info['name']}: {info['status']}")
    
    # مزامنة العملات الرقمية
    print("\n" + "=" * 60)
    crypto_result = ds.sync_crypto()
    print(f"\n{'✅' if crypto_result.get('success') else '❌'} {crypto_result}")


if __name__ == "__main__":
    main()
