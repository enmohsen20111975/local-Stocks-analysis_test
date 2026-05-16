"""
AI Investment Analyzer - نظام تحليل الاستثمار بالذكاء الاصطناعي

هذا الموديول يقوم بـ:
1. جمع البيانات من قاعدة البيانات
2. البحث عن الأخبار المتعلقة بالسوق
3. تحليل الأسهم باستخدام AI
4. إنشاء توصيات مدعومة بالأسباب
"""

import sqlite3
import json
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
_LOCAL_DB = os.path.join(os.path.dirname(__file__), 'data', 'egx_investment.db')
_VPS_DB = "/root/GLMinvestment/db/egx_investment.db"
DB_PATH = _VPS_DB if os.path.exists(_VPS_DB) else _LOCAL_DB
CUSTOM_DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'custom.db')

@dataclass
class StockData:
    """بيانات السهم"""
    ticker: str
    name: str
    sector: str
    current_price: float
    previous_close: float
    change_percent: float
    volume: int
    market_cap: float
    pe_ratio: float
    pb_ratio: float
    rsi: float
    ma_50: float
    ma_200: float
    support_level: float
    resistance_level: float

@dataclass
class NewsItem:
    """خبر"""
    title: str
    url: str
    source: str
    date: str
    snippet: str
    relevance_score: float = 0.0
    sentiment: str = "neutral"
    impact: str = "neutral"

@dataclass
class AIRecommendation:
    """توصية AI"""
    ticker: str
    action: str  # BUY, SELL, HOLD
    confidence: float  # 0-100
    price_target: Optional[float]
    stop_loss: Optional[float]
    reasons: List[str]
    technical_analysis: str
    fundamental_analysis: str
    news_impact: str
    risk_level: str  # LOW, MEDIUM, HIGH
    time_horizon: str  # SHORT, MEDIUM, LONG
    timestamp: str


class InvestmentAIAnalyzer:
    """محلل الاستثمار بالذكاء الاصطناعي"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "glm-4-flash"):
        """
        تهيئة المحلل
        
        Args:
            ollama_url: رابط Ollama server
            model: اسم الموديل (glm-4-flash, llama3.1, etc.)
        """
        self.ollama_url = ollama_url
        self.model = model
        self.db_path = DB_PATH
        self.custom_db_path = CUSTOM_DB_PATH
        
        # Check if Ollama is available
        self.ollama_available = self._check_ollama()
        logger.info(f"Ollama available: {self.ollama_available}")
        
    def _check_ollama(self) -> bool:
        """التحقق من توفر Ollama"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _get_db_connection(self) -> sqlite3.Connection:
        """إنشاء اتصال بقاعدة البيانات"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_stock_data(self, ticker: str) -> Optional[StockData]:
        """جلب بيانات سهم معين"""
        conn = self._get_db_connection()
        try:
            cursor = conn.execute("""
                SELECT ticker, name, sector, current_price, previous_close,
                       volume, market_cap, pe_ratio, pb_ratio, rsi,
                       ma_50, ma_200, support_level, resistance_level
                FROM stocks 
                WHERE ticker = ?
            """, (ticker,))
            row = cursor.fetchone()
            if row:
                change_percent = 0
                if row['previous_close'] and row['previous_close'] > 0:
                    change_percent = ((row['current_price'] - row['previous_close']) / row['previous_close']) * 100
                
                return StockData(
                    ticker=row['ticker'],
                    name=row['name'],
                    sector=row['sector'],
                    current_price=row['current_price'] or 0,
                    previous_close=row['previous_close'] or 0,
                    change_percent=change_percent,
                    volume=row['volume'] or 0,
                    market_cap=row['market_cap'] or 0,
                    pe_ratio=row['pe_ratio'] or 0,
                    pb_ratio=row['pb_ratio'] or 0,
                    rsi=row['rsi'] or 50,
                    ma_50=row['ma_50'] or 0,
                    ma_200=row['ma_200'] or 0,
                    support_level=row['support_level'] or 0,
                    resistance_level=row['resistance_level'] or 0
                )
            return None
        finally:
            conn.close()
    
    def get_top_movers(self, limit: int = 10) -> Dict[str, List[StockData]]:
        """جلب أكثر الأسهم تحركاً"""
        conn = self._get_db_connection()
        try:
            gainers = []
            losers = []
            
            cursor = conn.execute("""
                SELECT ticker, name, sector, current_price, previous_close,
                       volume, market_cap, pe_ratio, pb_ratio, rsi,
                       ma_50, ma_200, support_level, resistance_level
                FROM stocks 
                WHERE is_active = 1 AND previous_close > 0
                ORDER BY (current_price - previous_close) / previous_close DESC
                LIMIT ?
            """, (limit,))
            
            for row in cursor.fetchall():
                change_percent = ((row['current_price'] - row['previous_close']) / row['previous_close']) * 100
                stock = StockData(
                    ticker=row['ticker'],
                    name=row['name'],
                    sector=row['sector'],
                    current_price=row['current_price'],
                    previous_close=row['previous_close'],
                    change_percent=change_percent,
                    volume=row['volume'] or 0,
                    market_cap=row['market_cap'] or 0,
                    pe_ratio=row['pe_ratio'] or 0,
                    pb_ratio=row['pb_ratio'] or 0,
                    rsi=row['rsi'] or 50,
                    ma_50=row['ma_50'] or 0,
                    ma_200=row['ma_200'] or 0,
                    support_level=row['support_level'] or 0,
                    resistance_level=row['resistance_level'] or 0
                )
                if change_percent > 0:
                    gainers.append(stock)
                else:
                    losers.append(stock)
            
            return {"gainers": gainers, "losers": losers}
        finally:
            conn.close()
    
    def analyze_with_ai(self, prompt: str) -> str:
        """إرسال طلب للـ AI"""
        if not self.ollama_available:
            return self._fallback_analysis(prompt)
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 2000
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return self._fallback_analysis(prompt)
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return self._fallback_analysis(prompt)
    
    def _fallback_analysis(self, prompt: str) -> str:
        """تحليل بديل لو AI مش متاح"""
        return json.dumps({
            "action": "HOLD",
            "confidence": 50,
            "reasons": ["تحليل AI غير متاح حالياً"],
            "note": "يرجى التحقق من اتصال Ollama"
        })
    
    def analyze_stock(self, ticker: str) -> Optional[AIRecommendation]:
        """تحليل سهم معين"""
        stock = self.get_stock_data(ticker)
        if not stock:
            logger.error(f"Stock {ticker} not found")
            return None
        
        # Create analysis prompt
        prompt = self._create_analysis_prompt(stock)
        
        # Get AI response
        ai_response = self.analyze_with_ai(prompt)
        
        # Parse response
        recommendation = self._parse_ai_response(ticker, ai_response, stock)
        
        return recommendation
    
    def _create_analysis_prompt(self, stock: StockData) -> str:
        """إنشاء prompt للتحليل"""
        prompt = f"""
أنت محلل مالي خبير في البورصة المصرية. قم بتحليل السهم التالي وقدم توصية استثمارية:

## بيانات السهم:
- الرمز: {stock.ticker}
- الاسم: {stock.name}
- القطاع: {stock.sector}
- السعر الحالي: {stock.current_price:.2f} جنيه
- السعر السابق: {stock.previous_close:.2f} جنيه
- التغير: {stock.change_percent:.2f}%
- حجم التداول: {stock.volume:,}
- القيمة السوقية: {stock.market_cap:,.0f}

## المؤشرات الفنية:
- RSI: {stock.rsi:.1f}
- MA50: {stock.ma_50:.2f}
- MA200: {stock.ma_200:.2f}
- مستوى الدعم: {stock.support_level:.2f}
- مستوى المقاومة: {stock.resistance_level:.2f}

## المؤشرات الأساسية:
- P/E Ratio: {stock.pe_ratio:.2f}
- P/B Ratio: {stock.pb_ratio:.2f}

## المطلوب:
قدم تحليلك في صيغة JSON كالتالي:
{{
    "action": "BUY|SELL|HOLD",
    "confidence": 0-100,
    "price_target": سعر مستهدف,
    "stop_loss": سعر وقف الخسارة,
    "reasons": ["سبب 1", "سبب 2"],
    "technical_analysis": "تحليل فني مفصل",
    "fundamental_analysis": "تحليل أساسي مفصل",
    "risk_level": "LOW|MEDIUM|HIGH",
    "time_horizon": "SHORT|MEDIUM|LONG"
}}

قدم التحليل باللغة العربية.
"""
        return prompt
    
    def _parse_ai_response(self, ticker: str, response: str, stock: StockData) -> AIRecommendation:
        """تحليل رد AI"""
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
            else:
                data = json.loads(response)
            
            return AIRecommendation(
                ticker=ticker,
                action=data.get('action', 'HOLD'),
                confidence=float(data.get('confidence', 50)),
                price_target=data.get('price_target'),
                stop_loss=data.get('stop_loss'),
                reasons=data.get('reasons', []),
                technical_analysis=data.get('technical_analysis', ''),
                fundamental_analysis=data.get('fundamental_analysis', ''),
                news_impact='',
                risk_level=data.get('risk_level', 'MEDIUM'),
                time_horizon=data.get('time_horizon', 'MEDIUM'),
                timestamp=datetime.now().isoformat()
            )
        except json.JSONDecodeError:
            # Fallback parsing
            return AIRecommendation(
                ticker=ticker,
                action='HOLD',
                confidence=50,
                price_target=None,
                stop_loss=None,
                reasons=['تعذر تحليل رد AI'],
                technical_analysis=response[:500],
                fundamental_analysis='',
                news_impact='',
                risk_level='MEDIUM',
                time_horizon='MEDIUM',
                timestamp=datetime.now().isoformat()
            )
    
    def generate_market_summary(self) -> Dict[str, Any]:
        """إنشاء ملخص السوق"""
        movers = self.get_top_movers(5)
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "market_overview": {
                "top_gainers": [{"ticker": s.ticker, "name": s.name, "change": f"{s.change_percent:.2f}%"} for s in movers["gainers"][:5]],
                "top_losers": [{"ticker": s.ticker, "name": s.name, "change": f"{s.change_percent:.2f}%"} for s in movers["losers"][:5]]
            },
            "recommendations": [],
            "ai_summary": ""
        }
        
        # Analyze top movers
        for stock in movers["gainers"][:3] + movers["losers"][:3]:
            rec = self.analyze_stock(stock.ticker)
            if rec:
                summary["recommendations"].append(asdict(rec))
        
        # Generate AI summary
        if summary["recommendations"]:
            summary_prompt = f"""
بناءً على التحليلات التالية، قدم ملخص قصير للسوق المصري:

{json.dumps(summary["recommendations"], ensure_ascii=False, indent=2)}

قدم ملخصاً من 3-4 جمل يوضح وضع السوق وأهم التوصيات.
"""
            summary["ai_summary"] = self.analyze_with_ai(summary_prompt)
        
        return summary


class HourlyAnalysisScheduler:
    """جدولة التحليل كل ساعة"""
    
    def __init__(self, analyzer: InvestmentAIAnalyzer):
        self.analyzer = analyzer
        self.last_run = None
        self.results = []
    
    def run_analysis(self, tickers: List[str] = None):
        """تشغيل التحليل"""
        logger.info("Starting hourly analysis...")
        
        if tickers is None:
            # Get top movers
            movers = self.analyzer.get_top_movers(10)
            tickers = [s.ticker for s in movers["gainers"][:5] + movers["losers"][:5]]
        
        results = []
        for ticker in tickers:
            try:
                recommendation = self.analyzer.analyze_stock(ticker)
                if recommendation:
                    results.append(asdict(recommendation))
                    logger.info(f"Analyzed {ticker}: {recommendation.action} ({recommendation.confidence}%)")
            except Exception as e:
                logger.error(f"Error analyzing {ticker}: {e}")
        
        self.last_run = datetime.now()
        self.results = results
        
        # Save to database
        self._save_results(results)
        
        return results
    
    def _save_results(self, results: List[Dict]):
        """حفظ النتائج في قاعدة البيانات"""
        conn = sqlite3.connect(self.analyzer.custom_db_path)
        try:
            # Create table if not exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    action TEXT NOT NULL,
                    confidence REAL,
                    price_target REAL,
                    stop_loss REAL,
                    reasons TEXT,
                    technical_analysis TEXT,
                    fundamental_analysis TEXT,
                    news_impact TEXT,
                    risk_level TEXT,
                    time_horizon TEXT,
                    timestamp TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert results
            for rec in results:
                conn.execute("""
                    INSERT INTO ai_recommendations 
                    (ticker, action, confidence, price_target, stop_loss, reasons, 
                     technical_analysis, fundamental_analysis, news_impact, 
                     risk_level, time_horizon, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rec['ticker'],
                    rec['action'],
                    rec['confidence'],
                    rec.get('price_target'),
                    rec.get('stop_loss'),
                    json.dumps(rec.get('reasons', []), ensure_ascii=False),
                    rec.get('technical_analysis', ''),
                    rec.get('fundamental_analysis', ''),
                    rec.get('news_impact', ''),
                    rec.get('risk_level', 'MEDIUM'),
                    rec.get('time_horizon', 'MEDIUM'),
                    rec['timestamp']
                ))
            
            conn.commit()
            logger.info(f"Saved {len(results)} recommendations to database")
        finally:
            conn.close()


# API Endpoints for FastAPI integration
def create_ai_analyzer_router(app):
    """إنشاء router للـ API"""
    from fastapi import HTTPException
    
    analyzer = InvestmentAIAnalyzer()
    scheduler = HourlyAnalysisScheduler(analyzer)
    
    @app.get("/api/ai/health")
    async def ai_health():
        """التحقق من حالة الـ AI"""
        return {
            "status": "healthy",
            "ollama_available": analyzer.ollama_available,
            "model": analyzer.model,
            "last_analysis": scheduler.last_run.isoformat() if scheduler.last_run else None
        }
    
    @app.get("/api/ai/analyze/{ticker}")
    async def analyze_ticker(ticker: str):
        """تحليل سهم معين"""
        recommendation = analyzer.analyze_stock(ticker)
        if not recommendation:
            raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")
        return asdict(recommendation)
    
    @app.post("/api/ai/run-hourly")
    async def run_hourly_analysis(tickers: List[str] = None):
        """تشغيل التحليل الساعي"""
        results = scheduler.run_analysis(tickers)
        return {
            "success": True,
            "analyzed_count": len(results),
            "results": results
        }
    
    @app.get("/api/ai/recommendations")
    async def get_recommendations(limit: int = 20):
        """جلب التوصيات المحفوظة"""
        conn = sqlite3.connect(analyzer.custom_db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute("""
                SELECT * FROM ai_recommendations 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            results = [dict(row) for row in cursor.fetchall()]
            return {"success": True, "count": len(results), "results": results}
        finally:
            conn.close()
    
    @app.get("/api/ai/market-summary")
    async def get_market_summary():
        """ملخص السوق"""
        summary = analyzer.generate_market_summary()
        return summary


if __name__ == "__main__":
    # Test the analyzer
    analyzer = InvestmentAIAnalyzer()
    
    print("Testing AI Investment Analyzer...")
    print(f"Ollama available: {analyzer.ollama_available}")
    
    # Test stock analysis
    print("\nAnalyzing COMI...")
    rec = analyzer.analyze_stock("COMI")
    if rec:
        print(f"Action: {rec.action}")
        print(f"Confidence: {rec.confidence}%")
        print(f"Reasons: {rec.reasons}")
    
    # Test market summary
    print("\nGenerating market summary...")
    summary = analyzer.generate_market_summary()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
