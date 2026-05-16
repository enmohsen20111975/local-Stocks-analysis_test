"""
AI News Agent - وكيل الأخبار بالذكاء الاصطناعي

يقوم بالبحث عن الأخبار المتعلقة بالسوق المصري وتحليلها
"""

import json
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging
import re

logger = logging.getLogger(__name__)

@dataclass
class NewsAnalysis:
    """تحليل خبر"""
    title: str
    url: str
    source: str
    date: str
    summary: str
    sentiment: str  # positive, negative, neutral
    impact: str  # high, medium, low
    affected_sectors: List[str]
    affected_stocks: List[str]
    recommendation: str


class AINewsAgent:
    """وكيل الأخبار بالذكاء الاصطناعي"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "glm-4-flash"):
        self.ollama_url = ollama_url
        self.model = model
        self.ollama_available = self._check_ollama()
        
        # Egyptian market keywords
        self.egx_keywords = [
            "البورصة المصرية", "EGX", "سوق المال", "الأسهم المصرية",
            "EGX30", "EGX70", "EGX100", "بورصة القاهرة",
            "البنك المركزي", "الجنيه المصري", "احتياطي النقد الأجنبي",
            "صندوق النقد الدولي", "البترول", "الذهب"
        ]
        
        # Sector mapping
        self.sector_keywords = {
            "Financials": ["بنك", "مصرف", "مالية", "استثمار", "تأمين", "bank", "financial"],
            "Basic Materials": ["أسمدة", "بترول", "غاز", "تعدين", "كيماوي", "petroleum", "fertilizers"],
            "Real Estate": ["عقارات", "تطوير عقاري", "إنشاءات", "real estate", "construction"],
            "Consumer Goods": ["مستهلك", "غذائي", "مشروبات", "consumer", "food"],
            "Industrials": ["صناعة", "صناعات", "مصانع", "industrial", "manufacturing"],
            "Telecommunications": ["اتصالات", "موبايل", "إنترنت", "telecom", "mobile"],
            "Healthcare": ["صحة", "طبية", "أدوية", "pharmaceutical", "healthcare"],
            "Energy": ["طاقة", "كهرباء", "energy", "power"]
        }
    
    def _check_ollama(self) -> bool:
        """التحقق من توفر Ollama"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def search_news_via_ai(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        البحث عن الأخبار باستخدام AI
        هذا يستخدم AI للبحث عن الأخبار المتعلقة بالسوق
        """
        # Create search prompt for AI
        search_prompt = f"""
أنت وكيل أخبار متخصص في الأسواق المالية المصرية.
المطلوب: البحث عن أخبار مهمة متعلقة بـ: {query}

قواعد البحث:
1. ركز على الأخبار المالية والاقتصادية المصرية
2. ابحث عن أخبار تؤثر على البورصة المصرية
3. ركز على الأخبار الحديثة (آخر 24 ساعة)

قدم النتائج في صيغة JSON:
{{
    "news_found": true/false,
    "headlines": [
        {{
            "title": "عنوان الخبر",
            "source": "المصدر",
            "relevance": "عالي/متوسط/منخفض",
            "sentiment": "إيجابي/سلبي/محايد",
            "affected_sectors": ["قطاع 1", "قطاع 2"],
            "summary": "ملخص قصير"
        }}
    ],
    "market_outlook": "نظرة عامة على السوق"
}}

إذا لم تجد أخبار محددة، قدم تحليل عام للسوق بناءً على المعرفة المتاحة.
"""
        
        if self.ollama_available:
            try:
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": search_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.5,
                            "num_predict": 2000
                        }
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    ai_response = response.json().get('response', '')
                    return self._parse_news_response(ai_response)
            except Exception as e:
                logger.error(f"AI news search error: {e}")
        
        # Fallback: return general market news
        return self._get_fallback_news(query)
    
    def _parse_news_response(self, response: str) -> List[Dict]:
        """تحليل رد البحث"""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                return data.get('headlines', [])
        except:
            pass
        return []
    
    def _get_fallback_news(self, query: str) -> List[Dict]:
        """أخبار بديلة"""
        return [
            {
                "title": "تحديث السوق المصري",
                "source": "نظام التحليل",
                "relevance": "متوسط",
                "sentiment": "محايد",
                "affected_sectors": ["عام"],
                "summary": "لم يتم العثور على أخبار محددة. يرجى التحقق من الاتصال."
            }
        ]
    
    def analyze_news_impact(self, news_title: str, news_content: str = "") -> NewsAnalysis:
        """تحليل تأثير خبر معين"""
        analysis_prompt = f"""
أنت محلل مالي متخصص. قم بتحليل الخبر التالي وتحديد تأثيره على السوق المصري:

العنوان: {news_title}
المحتوى: {news_content if news_content else "غير متاح"}

قدم التحليل في صيغة JSON:
{{
    "sentiment": "positive/negative/neutral",
    "impact": "high/medium/low",
    "affected_sectors": ["قطاع 1", "قطاع 2"],
    "affected_stocks": ["رمز السهم 1", "رمز السهم 2"],
    "recommendation": "توصية للمستثمرين",
    "summary": "ملخص التأثير"
}}
"""
        
        if self.ollama_available:
            try:
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": analysis_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 1000
                        }
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    ai_response = response.json().get('response', '')
                    data = self._parse_analysis_response(ai_response)
                    
                    return NewsAnalysis(
                        title=news_title,
                        url="",
                        source="AI Analysis",
                        date=datetime.now().isoformat(),
                        summary=data.get('summary', ''),
                        sentiment=data.get('sentiment', 'neutral'),
                        impact=data.get('impact', 'medium'),
                        affected_sectors=data.get('affected_sectors', []),
                        affected_stocks=data.get('affected_stocks', []),
                        recommendation=data.get('recommendation', '')
                    )
            except Exception as e:
                logger.error(f"News analysis error: {e}")
        
        return NewsAnalysis(
            title=news_title,
            url="",
            source="System",
            date=datetime.now().isoformat(),
            summary="تعذر تحليل الخبر",
            sentiment="neutral",
            impact="low",
            affected_sectors=[],
            affected_stocks=[],
            recommendation="انتظار مزيد من المعلومات"
        )
    
    def _parse_analysis_response(self, response: str) -> Dict:
        """تحليل رد التحليل"""
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
        return {}
    
    def get_egx_daily_brief(self) -> Dict[str, Any]:
        """ملخص يومي للبورصة المصرية"""
        brief_prompt = f"""
أنت محلل مالي مصري خبير. قدم ملخص يومي للبورصة المصرية يتضمن:

1. نظرة عامة على أداء السوق
2. أهم الأخبار والأحداث
3. القطاعات الأكثر نشاطاً
4. توقعات قصيرة المدى

قدم الملخص في صيغة JSON:
{{
    "market_status": "إيجابي/سلبي/محايد",
    "summary": "ملخص عام",
    "key_events": ["حدث 1", "حدث 2"],
    "active_sectors": ["قطاع 1", "قطاع 2"],
    "recommendations": ["توصية 1", "توصية 2"],
    "outlook": "نظرة مستقبلية قصيرة"
}}
"""
        
        if self.ollama_available:
            try:
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": brief_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.6,
                            "num_predict": 1500
                        }
                    },
                    timeout=45
                )
                
                if response.status_code == 200:
                    ai_response = response.json().get('response', '')
                    return self._parse_analysis_response(ai_response)
            except Exception as e:
                logger.error(f"Daily brief error: {e}")
        
        return {
            "market_status": "محايد",
            "summary": "تعذر إنشاء الملخص اليومي",
            "key_events": [],
            "active_sectors": [],
            "recommendations": [],
            "outlook": "انتظار تحديث البيانات"
        }
    
    def search_stock_news(self, ticker: str, stock_name: str = "") -> List[Dict]:
        """البحث عن أخبار سهم معين"""
        query = f"أخبار {stock_name} {ticker} البورصة المصرية"
        return self.search_news_via_ai(query)
    
    def get_sector_news(self, sector: str) -> List[Dict]:
        """البحث عن أخبار قطاع معين"""
        query = f"أخبار قطاع {sector} مصر اقتصاد"
        return self.search_news_via_ai(query)


# Integration with main analyzer
def integrate_news_with_analysis(analyzer, news_agent: AINewsAgent):
    """دمج الأخبار مع التحليل"""
    
    def enhanced_analyze_stock(ticker: str):
        # Get basic analysis
        recommendation = analyzer.analyze_stock(ticker)
        if not recommendation:
            return None
        
        # Get stock name for news search
        stock = analyzer.get_stock_data(ticker)
        if stock:
            # Search for stock news
            news = news_agent.search_stock_news(ticker, stock.name)
            
            # Analyze news impact
            if news:
                news_analysis = news_agent.analyze_news_impact(
                    news[0].get('title', ''),
                    news[0].get('summary', '')
                )
                recommendation.news_impact = f"{news_analysis.sentiment}: {news_analysis.summary}"
        
        return recommendation
    
    return enhanced_analyze_stock


if __name__ == "__main__":
    # Test the news agent
    agent = AINewsAgent()
    
    print("Testing AI News Agent...")
    print(f"Ollama available: {agent.ollama_available}")
    
    # Test news search
    print("\nSearching for EGX news...")
    news = agent.search_news_via_ai("البورصة المصرية EGX30")
    print(json.dumps(news, ensure_ascii=False, indent=2))
    
    # Test daily brief
    print("\nGetting daily brief...")
    brief = agent.get_egx_daily_brief()
    print(json.dumps(brief, ensure_ascii=False, indent=2))
