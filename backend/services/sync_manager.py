#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام مزامنة البيانات من الموقع الحي
Sync Manager - مع تأكيد قبل التحديث
"""

import os
import sys
import json
import sqlite3
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# إعدادات
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "egx_investment.db")
WEBSITE_URL = "https://invist.m2y.net/api"
VPS_URL = "http://72.61.137.86:8010"

class SyncManager:
    """مدير المزامنة"""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.pending_updates = []
        self.pending_inserts = []
        
    def get_local_stats(self) -> Dict:
        """إحصائيات قاعدة البيانات المحلية"""
        cursor = self.conn.cursor()
        
        # عدد الأسهم
        cursor.execute("SELECT COUNT(*) FROM stocks WHERE is_active = 1")
        stocks_count = cursor.fetchone()[0]
        
        # عدد السجلات التاريخية
        cursor.execute("SELECT COUNT(*) FROM stock_price_history")
        history_count = cursor.fetchone()[0]
        
        # آخر تحديث
        cursor.execute("SELECT MAX(last_update) FROM stocks")
        last_update = cursor.fetchone()[0]
        
        # الأسهم المحدثة اليوم
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM stocks WHERE date(last_update) = ?", (today,))
        updated_today = cursor.fetchone()[0]
        
        return {
            "stocks_count": stocks_count,
            "history_count": history_count,
            "last_update": last_update,
            "updated_today": updated_today
        }
    
    def fetch_from_source(self, source: str = "website") -> Tuple[List[Dict], str]:
        """جلب البيانات من المصدر"""
        urls = {
            "website": f"{WEBSITE_URL}/stocks",
            "vps": f"{VPS_URL}/api/stocks/all"
        }
        
        url = urls.get(source, urls["website"])
        
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            # استخراج قائمة الأسهم
            stocks = data.get("stocks", []) or data.get("data", [])
            if isinstance(stocks, dict):
                stocks = stocks.get("stocks", stocks.get("data", []))
                
            return stocks, url
        except Exception as e:
            return [], f"خطأ: {str(e)}"
    
    def compare_data(self, remote_stocks: List[Dict]) -> Dict:
        """مقارنة البيانات المحلية بالبعيدة"""
        cursor = self.conn.cursor()
        
        new_stocks = []
        updated_stocks = []
        unchanged = 0
        
        for stock in remote_stocks:
            ticker = (stock.get("symbol") or stock.get("ticker") or "").upper()
            if not ticker:
                continue
                
            # البحث عن السهم محلياً
            cursor.execute("SELECT * FROM stocks WHERE ticker = ?", (ticker,))
            local = cursor.fetchone()
            
            remote_price = stock.get("current_price") or stock.get("price") or 0
            
            if not local:
                # سهم جديد
                new_stocks.append({
                    "ticker": ticker,
                    "name": stock.get("name", ""),
                    "price": remote_price,
                    "sector": stock.get("sector", "")
                })
            else:
                # مقارنة الأسعار
                local_price = local["current_price"] or 0
                if remote_price and local_price and abs(float(remote_price) - float(local_price)) > 0.01:
                    updated_stocks.append({
                        "ticker": ticker,
                        "name": stock.get("name", local["name"]),
                        "old_price": float(local_price),
                        "new_price": float(remote_price),
                        "change_percent": ((float(remote_price) - float(local_price)) / float(local_price) * 100) if local_price else 0
                    })
                else:
                    unchanged += 1
        
        return {
            "new": new_stocks,
            "updated": updated_stocks,
            "unchanged": unchanged,
            "total_remote": len(remote_stocks)
        }
    
    def preview_sync(self, source: str = "website") -> Dict:
        """معاينة التغييرات قبل التنفيذ"""
        print(f"\n{'='*60}")
        print(f"📊 معاينة المزامنة من: {source}")
        print(f"{'='*60}")
        
        # إحصائيات محلية
        local_stats = self.get_local_stats()
        print(f"\n📦 البيانات المحلية:")
        print(f"   - عدد الأسهم: {local_stats['stocks_count']}")
        print(f"   - عدد السجلات التاريخية: {local_stats['history_count']}")
        print(f"   - آخر تحديث: {local_stats['last_update'] or 'غير محدد'}")
        print(f"   - المحدثة اليوم: {local_stats['updated_today']}")
        
        # جلب البيانات البعيدة
        print(f"\n🔄 جلب البيانات من {source}...")
        remote_stocks, source_info = self.fetch_from_source(source)
        
        if not remote_stocks:
            print(f"❌ فشل جلب البيانات: {source_info}")
            return {"success": False, "error": source_info}
        
        print(f"✅ تم جلب {len(remote_stocks)} سهم")
        
        # مقارنة البيانات
        comparison = self.compare_data(remote_stocks)
        
        print(f"\n📊 نتائج المقارنة:")
        print(f"   - أسهم جديدة: {len(comparison['new'])}")
        print(f"   - أسهم تحتاج تحديث: {len(comparison['updated'])}")
        print(f"   - أسهم بدون تغيير: {comparison['unchanged']}")
        
        # عرض الأسهم الجديدة
        if comparison['new']:
            print(f"\n🆕 الأسهم الجديدة:")
            for s in comparison['new'][:10]:
                print(f"   + {s['ticker']}: {s['name'][:30]} ({s['price']})")
            if len(comparison['new']) > 10:
                print(f"   ... و {len(comparison['new']) - 10} سهم آخر")
        
        # عرض الأسهم المحدثة
        if comparison['updated']:
            print(f"\n💰 الأسهم المحدثة:")
            for s in comparison['updated'][:10]:
                change = f"+{s['change_percent']:.2f}%" if s['change_percent'] > 0 else f"{s['change_percent']:.2f}%"
                print(f"   ↻ {s['ticker']}: {s['old_price']} → {s['new_price']} ({change})")
            if len(comparison['updated']) > 10:
                print(f"   ... و {len(comparison['updated']) - 10} سهم آخر")
        
        return {
            "success": True,
            "local_stats": local_stats,
            "comparison": comparison,
            "source": source
        }
    
    def execute_sync(self, comparison: Dict, dry_run: bool = False) -> Dict:
        """تنفيذ المزامنة"""
        if dry_run:
            print("\n⚠️ وضع التجربة - لن يتم حفظ التغييرات")
            return {"dry_run": True, "changes": len(comparison['new']) + len(comparison['updated'])}
        
        cursor = self.conn.cursor()
        inserted = 0
        updated = 0
        
        # إضافة الأسهم الجديدة
        for stock in comparison['new']:
            try:
                cursor.execute("""
                    INSERT INTO stocks (ticker, name, current_price, sector, is_active, last_update)
                    VALUES (?, ?, ?, ?, 1, ?)
                """, (
                    stock['ticker'],
                    stock['name'],
                    stock['price'],
                    stock['sector'],
                    datetime.now().isoformat()
                ))
                inserted += 1
            except Exception as e:
                print(f"خطأ في إضافة {stock['ticker']}: {e}")
        
        # تحديث الأسهم الموجودة
        for stock in comparison['updated']:
            try:
                cursor.execute("""
                    UPDATE stocks 
                    SET current_price = ?, previous_close = ?, last_update = ?
                    WHERE ticker = ?
                """, (
                    stock['new_price'],
                    stock['old_price'],
                    datetime.now().isoformat(),
                    stock['ticker']
                ))
                updated += 1
            except Exception as e:
                print(f"خطأ في تحديث {stock['ticker']}: {e}")
        
        self.conn.commit()
        
        print(f"\n✅ تمت المزامنة:")
        print(f"   - أسهم مضافة: {inserted}")
        print(f"   - أسهم محدثة: {updated}")
        
        return {
            "success": True,
            "inserted": inserted,
            "updated": updated
        }
    
    def close(self):
        """إغلاق الاتصال"""
        self.conn.close()


def main():
    """الواجهة الرئيسية"""
    manager = SyncManager()
    
    # معاينة التغييرات
    preview = manager.preview_sync("website")
    
    if not preview.get("success"):
        print("فشل في المزامنة")
        return
    
    # سؤال المستخدم
    comparison = preview['comparison']
    total_changes = len(comparison['new']) + len(comparison['updated'])
    
    if total_changes == 0:
        print("\n✅ البيانات محدثة - لا حاجة للمزامنة")
        manager.close()
        return
    
    print(f"\n{'='*60}")
    response = input(f"⚠️ هل تريد تنفيذ المزامنة؟ ({total_changes} تغيير) [y/N]: ")
    
    if response.lower() == 'y':
        manager.execute_sync(comparison)
    else:
        print("❌ تم إلغاء المزامنة")
    
    manager.close()


if __name__ == "__main__":
    main()
