#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EGX Data Engine - Backend Server
سيرفر محرك بيانات البورصة المصرية
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# مسارات
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "egx_investment.db")
FRONTEND_PATH = os.path.join(BASE_DIR, "frontend")
PORT = 8020

class EGXAPIHandler(SimpleHTTPRequestHandler):
    """معالج API للبيانات"""
    
    def do_GET(self):
        """معالجة طلبات GET"""
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        # تسجيل الطلب
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {path}")
        
        # === API Routes ===
        
        # Health Check
        if path == '/api/health' or path == '/health':
            self.json_response({"status": "healthy", "version": "2.0.0", "timestamp": datetime.now().isoformat()})
            return
        
        # إحصائيات قاعدة البيانات
        if path == '/api/stats':
            self.json_response(self.get_stats())
            return
        
        # قائمة الأسهم
        if path == '/api/stocks':
            limit = int(params.get('limit', [100])[0])
            sector = params.get('sector', [None])[0]
            self.json_response(self.get_stocks(limit, sector))
            return
        
        # معلومات سهم محدد
        if path.startswith('/api/stocks/'):
            symbol = path.split('/')[-1]
            self.json_response(self.get_stock(symbol))
            return
        
        # التوصيات
        if path == '/api/recommendations':
            action = params.get('action', [None])[0]
            limit = int(params.get('limit', [20])[0])
            self.json_response(self.get_recommendations(action, limit))
            return
        
        # أداء القطاعات
        if path == '/api/sectors':
            self.json_response(self.get_sectors())
            return
        
        # العملات الرقمية
        if path == '/api/crypto':
            self.json_response(self.get_crypto())
            return
        
        # الذهب
        if path == '/api/gold':
            self.json_response(self.get_gold())
            return
        
        # مصادر البيانات
        if path == '/api/sources':
            self.json_response(self.get_sources())
            return
        
        # ملخص السوق
        if path == '/api/market/summary':
            self.json_response(self.get_market_summary())
            return
        
        # === الملفات الثابتة ===
        
        # الصفحة الرئيسية
        if path == '/' or path == '/index.html':
            self.serve_file(os.path.join(FRONTEND_PATH, 'index.html'), 'text/html')
            return
        
        # ملفات CSS
        if path.endswith('.css'):
            self.serve_file(os.path.join(FRONTEND_PATH, path[1:]), 'text/css')
            return
        
        # ملفات JS
        if path.endswith('.js'):
            self.serve_file(os.path.join(FRONTEND_PATH, path[1:]), 'application/javascript')
            return
        
        # صفحات أخرى
        if path.endswith('.html'):
            self.serve_file(os.path.join(FRONTEND_PATH, path[1:]), 'text/html')
            return
        
        # 404
        self.send_error(404, "Not Found")
    
    def do_POST(self):
        """معالجة طلبات POST"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # تحديث الأسعار
        if path == '/api/sync/stocks':
            self.json_response(self.sync_stocks())
            return
        
        # حساب التحليلات
        if path == '/api/compute/indicators':
            self.json_response(self.compute_indicators())
            return
        
        self.send_error(404, "Not Found")
    
    # === Database Functions ===
    
    def get_db(self):
        """الحصول على اتصال قاعدة البيانات"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_stats(self):
        """إحصائيات قاعدة البيانات"""
        try:
            conn = self.get_db()
            c = conn.cursor()
            
            c.execute("SELECT COUNT(*) FROM stocks WHERE is_active = 1")
            stocks = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM stock_price_history")
            history = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM precomputed_indicators WHERE action = 'BUY'")
            buy = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM precomputed_indicators WHERE action = 'SELL'")
            sell = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM precomputed_indicators WHERE action = 'HOLD'")
            hold = c.fetchone()[0]
            
            c.execute("SELECT MAX(last_update) FROM stocks")
            last_update = c.fetchone()[0]
            
            conn.close()
            
            return {
                "success": True,
                "data": {
                    "stocks_count": stocks,
                    "history_count": history,
                    "signals": {"buy": buy, "sell": sell, "hold": hold},
                    "last_update": last_update,
                    "database": "egx_investment.db"
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_stocks(self, limit=100, sector=None):
        """قائمة الأسهم"""
        try:
            conn = self.get_db()
            c = conn.cursor()
            
            query = """
                SELECT ticker, name, name_ar, sector, current_price, 
                       previous_close, open_price, high_price, low_price, volume
                FROM stocks 
                WHERE is_active = 1
            """
            params = []
            
            if sector:
                query += " AND sector = ?"
                params.append(sector)
            
            query += f" ORDER BY ticker LIMIT ?"
            params.append(limit)
            
            c.execute(query, params)
            rows = c.fetchall()
            
            stocks = []
            for r in rows:
                change = 0
                change_pct = 0
                if r['current_price'] and r['previous_close'] and r['previous_close'] > 0:
                    change = float(r['current_price']) - float(r['previous_close'])
                    change_pct = (change / float(r['previous_close'])) * 100
                
                stocks.append({
                    "ticker": r['ticker'],
                    "name": r['name'],
                    "name_ar": r['name_ar'],
                    "sector": r['sector'],
                    "price": round(float(r['current_price']), 2) if r['current_price'] else None,
                    "change": round(change, 2),
                    "change_percent": round(change_pct, 2),
                    "open": r['open_price'],
                    "high": r['high_price'],
                    "low": r['low_price'],
                    "volume": r['volume']
                })
            
            conn.close()
            
            return {"success": True, "data": stocks, "count": len(stocks)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_stock(self, symbol):
        """معلومات سهم محدد"""
        try:
            conn = self.get_db()
            c = conn.cursor()
            
            # معلومات السهم
            c.execute("""
                SELECT * FROM stocks WHERE ticker = ?
            """, (symbol.upper(),))
            stock = c.fetchone()
            
            if not stock:
                return {"success": False, "error": f"Stock {symbol} not found"}
            
            # التحليل الفني
            c.execute("""
                SELECT * FROM precomputed_indicators WHERE ticker = ?
            """, (symbol.upper(),))
            analysis = c.fetchone()
            
            result = dict(stock)
            if analysis:
                result['analysis'] = dict(analysis)
            
            conn.close()
            
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_recommendations(self, action=None, limit=20):
        """التوصيات"""
        try:
            conn = self.get_db()
            c = conn.cursor()
            
            query = """
                SELECT ticker, action, confidence, current_price,
                       target_1, target_2, stop_loss, trend, score,
                       entry_zone_low, entry_zone_high
                FROM precomputed_indicators
                WHERE 1=1
            """
            params = []
            
            if action and action.upper() in ['BUY', 'SELL', 'HOLD']:
                query += " AND action = ?"
                params.append(action.upper())
            
            query += " ORDER BY confidence DESC, score DESC LIMIT ?"
            params.append(limit)
            
            c.execute(query, params)
            rows = c.fetchall()
            
            recommendations = []
            for r in rows:
                recommendations.append({
                    "ticker": r['ticker'],
                    "action": r['action'],
                    "confidence": r['confidence'],
                    "price": round(float(r['current_price']), 2) if r['current_price'] else None,
                    "target_1": round(float(r['target_1']), 2) if r['target_1'] else None,
                    "target_2": round(float(r['target_2']), 2) if r['target_2'] else None,
                    "stop_loss": round(float(r['stop_loss']), 2) if r['stop_loss'] else None,
                    "trend": r['trend'],
                    "score": r['score']
                })
            
            conn.close()
            
            return {"success": True, "data": recommendations, "count": len(recommendations)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_sectors(self):
        """أداء القطاعات"""
        try:
            conn = self.get_db()
            c = conn.cursor()
            
            c.execute("""
                SELECT sector, COUNT(*) as count,
                       AVG(current_price) as avg_price
                FROM stocks 
                WHERE is_active = 1 AND sector IS NOT NULL
                GROUP BY sector
                ORDER BY count DESC
            """)
            
            sectors = []
            for r in c.fetchall():
                sectors.append({
                    "sector": r['sector'],
                    "count": r['count'],
                    "avg_price": round(float(r['avg_price']), 2) if r['avg_price'] else 0
                })
            
            conn.close()
            
            return {"success": True, "data": sectors}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_crypto(self):
        """العملات الرقمية"""
        try:
            conn = self.get_db()
            c = conn.cursor()
            
            c.execute("""
                SELECT ticker, close as price, date
                FROM price_history
                WHERE ticker IN ('bitcoin', 'ethereum', 'binancecoin', 'ripple', 'cardano', 'solana')
                ORDER BY date DESC
            """)
            
            crypto = {}
            for r in c.fetchall():
                if r['ticker'] not in crypto:
                    crypto[r['ticker']] = {
                        "ticker": r['ticker'],
                        "price": round(float(r['price']), 2) if r['price'] else 0,
                        "date": r['date']
                    }
            
            conn.close()
            
            return {"success": True, "data": list(crypto.values())}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_gold(self):
        """أسعار الذهب"""
        try:
            conn = self.get_db()
            c = conn.cursor()
            
            c.execute("""
                SELECT karat, price_per_gram, change, recorded_at
                FROM gold_prices
                ORDER BY karat
            """)
            
            gold = []
            for r in c.fetchall():
                gold.append({
                    "karat": r['karat'],
                    "price": round(float(r['price_per_gram']), 2) if r['price_per_gram'] else 0,
                    "change": r['change'],
                    "date": r['recorded_at']
                })
            
            conn.close()
            
            return {"success": True, "data": gold}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_sources(self):
        """مصادر البيانات"""
        return {
            "success": True,
            "data": [
                {"name": "الموقع الحي", "url": "https://invist.m2y.net/api", "status": "online", "type": "stocks"},
                {"name": "Twelve Data", "url": "https://api.twelvedata.com", "status": "online", "type": "stocks", "limit": "800/day"},
                {"name": "EODHD", "url": "https://eodhistoricaldata.com/api", "status": "online", "type": "stocks", "limit": "20/day"},
                {"name": "CoinGecko", "url": "https://api.coingecko.com/api/v3", "status": "online", "type": "crypto", "limit": "50/min"},
                {"name": "Alpha Vantage", "url": "https://www.alphavantage.co/query", "status": "online", "type": "stocks", "limit": "25/day"}
            ]
        }
    
    def get_market_summary(self):
        """ملخص السوق"""
        try:
            conn = self.get_db()
            c = conn.cursor()
            
            # عدد التوصيات
            c.execute("SELECT COUNT(*) FROM precomputed_indicators WHERE action = 'BUY'")
            buy = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM precomputed_indicators WHERE action = 'SELL'")
            sell = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM precomputed_indicators WHERE action = 'HOLD'")
            hold = c.fetchone()[0]
            
            # أفضل 5 شراء
            c.execute("""
                SELECT ticker, current_price, confidence
                FROM precomputed_indicators
                WHERE action = 'BUY'
                ORDER BY confidence DESC
                LIMIT 5
            """)
            top_buy = [{"ticker": r[0], "price": r[1], "confidence": r[2]} for r in c.fetchall()]
            
            # أفضل 5 بيع
            c.execute("""
                SELECT ticker, current_price, confidence
                FROM precomputed_indicators
                WHERE action = 'SELL'
                ORDER BY confidence DESC
                LIMIT 5
            """)
            top_sell = [{"ticker": r[0], "price": r[1], "confidence": r[2]} for r in c.fetchall()]
            
            conn.close()
            
            sentiment = "bullish" if buy > sell else "bearish" if sell > buy else "neutral"
            
            return {
                "success": True,
                "data": {
                    "signals": {"buy": buy, "sell": sell, "hold": hold},
                    "sentiment": sentiment,
                    "top_buy": top_buy,
                    "top_sell": top_sell,
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def sync_stocks(self):
        """مزامنة الأسهم"""
        try:
            import requests
            resp = requests.get('https://invist.m2y.net/api/stocks', timeout=30)
            stocks = resp.json().get('stocks', [])
            
            conn = self.get_db()
            c = conn.cursor()
            
            updated = 0
            for s in stocks:
                ticker = s.get('ticker', s.get('symbol', '')).upper()
                price = s.get('current_price') or s.get('price')
                
                if ticker and price:
                    c.execute("""
                        UPDATE stocks 
                        SET current_price = ?, last_update = ?
                        WHERE ticker = ?
                    """, (float(price), datetime.now().isoformat(), ticker))
                    
                    if c.rowcount > 0:
                        updated += 1
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": f"Updated {updated} stocks"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def compute_indicators(self):
        """حساب التحليلات"""
        try:
            sys.path.insert(0, BASE_DIR)
            from backend.services.data_engine import DataEngine
            
            engine = DataEngine()
            result = engine.compute_all_indicators()
            
            return {"success": True, "message": f"Processed {result['processed']} stocks"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === Response Helpers ===
    
    def json_response(self, data):
        """إرسال JSON"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))
    
    def serve_file(self, filepath, content_type):
        """إرسال ملف"""
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, "File not found")
    
    def log_message(self, format, *args):
        """تسجيل مختصر"""
        pass  # suppress default logging


def main():
    """تشغيل السيرفر"""
    print("=" * 60)
    print("🚀 EGX Data Engine v2.0")
    print("=" * 60)
    print(f"📊 Database: {DB_PATH}")
    print(f"🌐 Frontend: {FRONTEND_PATH}")
    print(f"🔗 URL: http://localhost:{PORT}")
    print("=" * 60)
    print("Press Ctrl+C to stop")
    print()
    
    os.chdir(BASE_DIR)
    
    server = HTTPServer(('0.0.0.0', PORT), EGXAPIHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⛔ Stopping server...")
        server.shutdown()


if __name__ == "__main__":
    main()
