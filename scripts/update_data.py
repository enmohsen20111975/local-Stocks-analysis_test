#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت تحديث البيانات
Run: python3 update_data.py
"""

import sys
sys.path.insert(0, '.')

import sqlite3
import requests
from datetime import datetime
from data_engine import DataEngine

DB_PATH = 'data/egx_investment.db'
WEBSITE_URL = 'https://invist.m2y.net/api'

def sync_stocks():
    """مزامنة الأسهم من الموقع"""
    print("=" * 60)
    print("📊 تحديث الأسهم من الموقع الحي")
    print("=" * 60)
    
    try:
        resp = requests.get(f'{WEBSITE_URL}/stocks', timeout=30)
        stocks = resp.json().get('stocks', [])
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        updated = 0
        for s in stocks:
            ticker = s.get('ticker', s.get('symbol', '')).upper()
            price = s.get('current_price') or s.get('price')
            
            if ticker and price:
                cursor.execute("""
                    UPDATE stocks 
                    SET current_price = ?, 
                        previous_close = COALESCE(previous_close, current_price),
                        last_update = ?
                    WHERE ticker = ?
                """, (float(price), datetime.now().isoformat(), ticker))
                
                if cursor.rowcount > 0:
                    updated += 1
        
        conn.commit()
        conn.close()
        
        print(f"✅ تم تحديث {updated} سهم")
        return True
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return False

def compute_indicators():
    """حساب التحليلات الفنية"""
    print("\n" + "=" * 60)
    print("📊 حساب التحليلات الفنية")
    print("=" * 60)
    
    engine = DataEngine()
    
    # الأسهم
    result = engine.compute_all_indicators()
    print(f"✅ الأسهم: {result['processed']} تم، {result['failed']} فشل")
    
    # الذهب
    gold = engine.compute_gold_indicators()
    print(f"✅ الذهب: {gold['processed']}")
    
    # القطاعات
    sectors = engine.compute_sectors()
    print(f"✅ القطاعات: {sectors['sectors']}")
    
    # ملخص السوق
    summary = engine.generate_market_summary()
    print(f"✅ السوق: BUY={summary.get('buy', 0)}, SELL={summary.get('sell', 0)}, HOLD={summary.get('hold', 0)}")
    
    return True

def sync_crypto():
    """مزامنة العملات الرقمية"""
    print("\n" + "=" * 60)
    print("🪙 تحديث العملات الرقمية")
    print("=" * 60)
    
    coins = ['bitcoin', 'ethereum', 'binancecoin', 'ripple', 'cardano', 'solana']
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total = 0
    for coin_id in coins:
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            resp = requests.get(url, timeout=15)
            data = resp.json()
            
            price = data['market_data']['current_price']['usd']
            
            cursor.execute("""
                INSERT OR REPLACE INTO price_history (ticker, date, close, open, high, low, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (coin_id, datetime.now().strftime("%Y-%m-%d"), price, price, price, price, 0))
            
            total += 1
            print(f"  ✅ {coin_id}: ${price:,.2f}")
            
        except Exception as e:
            print(f"  ❌ {coin_id}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"✅ تم تحديث {total} عملة")
    return True

def show_stats():
    """عرض الإحصائيات"""
    print("\n" + "=" * 60)
    print("📊 الإحصائيات")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM stocks WHERE is_active = 1")
    stocks = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM stock_price_history")
    history = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM precomputed_indicators WHERE action = 'BUY'")
    buy = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM precomputed_indicators WHERE action = 'SELL'")
    sell = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM precomputed_indicators WHERE action = 'HOLD'")
    hold = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"📈 الأسهم: {stocks}")
    print(f"📊 السجلات: {history:,}")
    print(f"🟢 BUY: {buy}")
    print(f"🔴 SELL: {sell}")
    print(f"🟡 HOLD: {hold}")

def show_top_recommendations():
    """عرض أفضل التوصيات"""
    print("\n" + "=" * 60)
    print("📈 أفضل التوصيات")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # BUY
    cursor.execute("""
        SELECT ticker, current_price, target_1, stop_loss, confidence, trend
        FROM precomputed_indicators
        WHERE action = 'BUY'
        ORDER BY confidence DESC
        LIMIT 10
    """)
    
    print("\n🟢 شراء:")
    print(f"{'السهم':<10} {'السعر':<12} {'الهدف':<12} {'الثقة':<8}")
    print("-" * 50)
    for r in cursor.fetchall():
        print(f"{r['ticker']:<10} {r['current_price']:<12.2f} {r['target_1']:<12.2f} {r['confidence']:<8}%")
    
    # SELL
    cursor.execute("""
        SELECT ticker, current_price, confidence, trend
        FROM precomputed_indicators
        WHERE action = 'SELL'
        ORDER BY confidence DESC
        LIMIT 10
    """)
    
    print("\n🔴 بيع:")
    print(f"{'السهم':<10} {'السعر':<12} {'الثقة':<8}")
    print("-" * 50)
    for r in cursor.fetchall():
        print(f"{r['ticker']:<10} {r['current_price']:<12.2f} {r['confidence']:<8}%")
    
    conn.close()

def main():
    """القائمة الرئيسية"""
    print("\n" + "=" * 60)
    print("🚀 EGX Data Engine - محرك البيانات")
    print("=" * 60)
    
    print("""
    1. 📊 تحديث الأسهم من الموقع
    2. 📈 حساب التحليلات الفنية
    3. 🪙 تحديث العملات الرقمية
    4. 📋 عرض الإحصائيات
    5. 📈 عرض التوصيات
    6. ✅ تحديث كل شيء
    0. 🚪 خروج
    """)
    
    choice = input("اختر رقم: ").strip()
    
    if choice == '1':
        sync_stocks()
    elif choice == '2':
        compute_indicators()
    elif choice == '3':
        sync_crypto()
    elif choice == '4':
        show_stats()
    elif choice == '5':
        show_top_recommendations()
    elif choice == '6':
        sync_stocks()
        compute_indicators()
        sync_crypto()
        show_stats()
        show_top_recommendations()
    elif choice == '0':
        print("👋 مع السلامة!")
        return
    else:
        print("❌ اختيار غير صحيح")
    
    main()

if __name__ == "__main__":
    main()
