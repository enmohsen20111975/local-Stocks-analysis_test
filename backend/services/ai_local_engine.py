# -*- coding: utf-8 -*-
"""
AI Local Engine - محرك الذكاء الاصطناعي المحلي
=================================================
يتصل بـ LM Studio (port 1234) أو Ollama (port 11434)
يجيب أخبار من الإنترنت ويحلل الأسهم سهم سهم
"""

import os
import json
import requests
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Database path - use same logic as unified_backend.py
_LOCAL_DB = os.path.join(os.path.dirname(__file__), "data", "egx_investment.db")
_VPS_DB = "/root/GLMinvestment/db/egx_investment.db"
DB_PATH = _VPS_DB if os.path.exists(_VPS_DB) else _LOCAL_DB

# LM Studio config
LMSTUDIO_URL = os.getenv("LMSTUDIO_URL", "http://localhost:1234/v1")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "qwen2.5-7b-instruct")

# Ollama config
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "glm-4-flash")

# Website (Next.js) config
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://invist.m2y.net")
VPS_URL = os.getenv("VPS_URL", "http://72.61.137.86:8010")


@dataclass
class AIRecommendation:
    """توصية AI معتمدة"""
    ticker: str
    action: str  # BUY, SELL, HOLD
    confidence: float
    price_target: Optional[float]
    stop_loss: Optional[float]
    reasons: List[str]
    technical_analysis: str
    fundamental_analysis: str
    news_impact: str
    risk_level: str
    time_horizon: str
    ai_approved: bool
    approval_reason: str
    timestamp: str


class AILocalEngine:
    """محرك AI محلي يتصل بـ LM Studio/Ollama + الإنترنت"""

    def __init__(self):
        self.lmstudio_available = self._check_lmstudio()
        self.ollama_available = self._check_ollama()
        self.db_path = DB_PATH
        logger.info(f"LM Studio available: {self.lmstudio_available}")
        logger.info(f"Ollama available: {self.ollama_available}")

    def _check_lmstudio(self) -> bool:
        """التحقق من توفر LM Studio"""
        try:
            resp = requests.get(f"{LMSTUDIO_URL}/models", timeout=5)
            return resp.status_code == 200
        except:
            return False

    def _check_ollama(self) -> bool:
        """التحقق من توفر Ollama"""
        try:
            resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            return resp.status_code == 200
        except:
            return False

    def _get_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _call_ai(self, prompt: str, temperature: float = 0.7) -> str:
        """استدعاء AI سواء LM Studio أو Ollama"""
        # Try LM Studio first
        if self.lmstudio_available:
            try:
                resp = requests.post(
                    f"{LMSTUDIO_URL}/chat/completions",
                    json={
                        "model": LMSTUDIO_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature,
                        "max_tokens": 4000
                    },
                    timeout=120
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"LM Studio error: {e}")

        # Fallback to Ollama
        if self.ollama_available:
            try:
                resp = requests.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": temperature, "num_predict": 4000}
                    },
                    timeout=120
                )
                if resp.status_code == 200:
                    return resp.json().get("response", "")
            except Exception as e:
                logger.warning(f"Ollama error: {e}")

        return ""

    def fetch_news_from_web(self, ticker: str, company_name: str = "") -> List[Dict]:
        """جلب أخبار من الإنترنت عن السهم"""
        query = f"{ticker} {company_name} Egyptian stock EGX news 2025 2026".strip()
        prompt = f"""
أنت وكيل أخبار مالي متخصص في البورصة المصرية.
المطلوب: ابحث عن آخر الأخبار المتعلقة بسهم {ticker} ({company_name}) في البورصة المصرية.

قدم النتائج في صيغة JSON:
{{
    "news": [
        {{
            "title": "عنوان الخبر",
            "source": "المصدر",
            "date": "YYYY-MM-DD",
            "summary": "ملخص الخبر",
            "sentiment": "positive|negative|neutral",
            "impact": "high|medium|low"
        }}
    ],
    "market_sentiment": "إيجابي|سلبي|محايد",
    "key_factors": ["عامل 1", "عامل 2"]
}}

إذا لم تتوفر أخبار حديثة محددة، قدم تحليلاً عاماً بناءً على:
1. وضع السهم في البورصة المصرية
2. القطاع الصناعي
3. الظروف الاقتصادية المصرية الحالية
4. أي أخبار قد تؤثر على السهم
"""
        response = self._call_ai(prompt, temperature=0.5)
        try:
            # Extract JSON
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(response[start:end])
                return data.get("news", [])
        except:
            pass
        return []

    def fetch_website_recommendation(self, ticker: str) -> Dict:
        """جلب التوصية الموجودة على الموقع الحي"""
        try:
            resp = requests.get(
                f"{WEBSITE_URL}/api/recommendations?ticker={ticker}",
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning(f"Could not fetch website recommendation for {ticker}: {e}")
        return {}

    def get_stock_data(self, ticker: str) -> Optional[Dict]:
        """جلب بيانات السهم من قاعدة البيانات المحلية"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[AI Engine] Getting stock data for {ticker}, DB path: {self.db_path}")
        logger.info(f"[AI Engine] DB exists: {__import__('os').path.exists(self.db_path)}")
        conn = self._get_db()
        try:
            cursor = conn.execute("""
                SELECT ticker, name, name_ar, sector, current_price, previous_close,
                       open_price, high_price, low_price, volume, market_cap,
                       pe_ratio, pb_ratio, eps, roe, rsi, ma_50, ma_200,
                       support_level, resistance_level
                FROM stocks WHERE ticker = ? AND is_active = 1
            """, (ticker,))
            row = cursor.fetchone()
            logger.info(f"[AI Engine] Query result for {ticker}: {row is not None}")
            if row:
                return dict(row)
        except Exception as e:
            logger.error(f"[AI Engine] DB error for {ticker}: {e}")
            raise
        finally:
            conn.close()
        return None

    def get_stock_history(self, ticker: str, days: int = 90) -> List[Dict]:
        """جلب البيانات التاريخية للسهم"""
        conn = self._get_db()
        try:
            rows = conn.execute("""
                SELECT sph.date, sph.open_price, sph.high_price, sph.low_price,
                       sph.close_price, sph.volume
                FROM stock_price_history sph
                JOIN stocks s ON s.id = sph.stock_id
                WHERE s.ticker = ?
                ORDER BY sph.date DESC
                LIMIT ?
            """, (ticker, days)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def analyze_stock(self, ticker: str) -> Optional[AIRecommendation]:
        """
        تحليل سهم بالكامل:
        1. جلب بيانات السهم
        2. جلب الأخبار من الإنترنت
        3. جلب التوصية من الموقع
        4. مناقشة AI للحصول على قرار نهائي
        5. الموافقة أو الرفض مع الأسباب
        """
        stock = self.get_stock_data(ticker)
        if not stock:
            logger.error(f"Stock {ticker} not found in local DB")
            return None

        # 1. Fetch news
        news = self.fetch_news_from_web(ticker, stock.get("name", ""))

        # 2. Fetch website recommendation
        website_rec = self.fetch_website_recommendation(ticker)

        # 3. Get technical data
        history = self.get_stock_history(ticker, 30)

        # Build analysis prompt
        news_text = "\n".join([
            f"- {n.get('title', '')} ({n.get('source', '')}, {n.get('date', '')}): {n.get('summary', '')} [Sentiment: {n.get('sentiment', 'neutral')}, Impact: {n.get('impact', 'medium')}]"
            for n in news[:5]
        ]) if news else "No specific news found."

        website_rec_text = ""
        if website_rec:
            website_rec_text = f"""
## التوصية الحالية على الموقع:
- التوصية: {website_rec.get('recommendation', 'N/A')}
- الثقة: {website_rec.get('confidence', 'N/A')}%
- السعر المستهدف: {website_rec.get('target_price', 'N/A')}
- وقف الخسارة: {website_rec.get('stop_loss', 'N/A')}
- الأسباب: {', '.join(website_rec.get('reasons', []))}
"""

        history_text = ""
        if history:
            latest = history[0]
            oldest = history[-1]
            change = ((latest['close_price'] - oldest['close_price']) / oldest['close_price'] * 100) if oldest['close_price'] else 0
            history_text = f"""
## أداء السهم (آخر {len(history)} يوم):
- سعر الإغلاق الأحدث: {latest['close_price']:.2f} ({latest['date']})
- سعر الإغلاق الأقدم: {oldest['close_price']:.2f} ({oldest['date']})
- التغير: {change:.2f}%
- أعلى سعر: {max(h['high_price'] for h in history):.2f}
- أقل سعر: {min(h['low_price'] for h in history):.2f}
"""

        prompt = f"""
أنت محلل مالي خبير في البورصة المصرية. مهمتك تحليل سهم وتقديم توصية استثمارية نهائية مع الموافقة أو الرفض.

## بيانات السهم:
- الرمز: {stock['ticker']}
- الاسم: {stock['name']} ({stock.get('name_ar', '')})
- القطاع: {stock.get('sector', 'N/A')}
- السعر الحالي: {stock.get('current_price') or 0:.2f} جنيه
- السعر السابق: {stock.get('previous_close') or 0:.2f} جنيه
- التغير: {(( (stock.get('current_price') or 0) - (stock.get('previous_close') or 0) ) / (stock.get('previous_close') or 1) * 100):.2f}%
- حجم التداول: {stock.get('volume') or 0:,}
- القيمة السوقية: {stock.get('market_cap') or 0:,.0f}

## المؤشرات الفنية:
- RSI: {stock.get('rsi', 'N/A')}
- MA50: {stock.get('ma_50', 'N/A')}
- MA200: {stock.get('ma_200', 'N/A')}
- مستوى الدعم: {stock.get('support_level', 'N/A')}
- مستوى المقاومة: {stock.get('resistance_level', 'N/A')}

## المؤشرات الأساسية:
- P/E: {stock.get('pe_ratio', 'N/A')}
- P/B: {stock.get('pb_ratio', 'N/A')}
- EPS: {stock.get('eps', 'N/A')}
- ROE: {stock.get('roe', 'N/A')}

{history_text}

## آخر الأخبار:
{news_text}

{website_rec_text}

## المطلوب:
قدم تحليلك في صيغة JSON صالحة فقط - لا تضف أي نص خارج JSON:
{{
    "action": "BUY|SELL|HOLD",
    "confidence": 0-100,
    "price_target": رقم,
    "stop_loss": رقم,
    "reasons": ["سبب 1", "سبب 2", "سبب 3"],
    "technical_analysis": "تحليل فني مفصل بالعربي",
    "fundamental_analysis": "تحليل أساسي مفصل بالعربي",
    "news_impact": "تأثير الأخبار على السهم بالعربي",
    "risk_level": "LOW|MEDIUM|HIGH",
    "time_horizon": "SHORT|MEDIUM|LONG",
    "ai_approved": true|false,
    "approval_reason": "اكتب هنا سبب التوصية بالتفصيل: ليه اخترت action ده؟ شوفت إيه في المؤشرات والأخبار؟"
}}

تعليمات حاسمة:
1. اكتب JSON صالح فقط - لا markdown ولا كلام خارج JSON
2. approval_reason لازم يكون مفصل: ليه الشراء/البيع؟ شوفت إيه في RSI و MACD؟
3. reasons لازم تكون list من 3-5 أسباب واضحة
4. technical_analysis يشرح كل المؤشرات الفنية
5. fundamental_analysis يشرح النسب المالية
6. news_impact يشرح تأثير الأخبار
"""

        ai_response = self._call_ai(prompt, temperature=0.3)

        # Parse JSON response with multiple fallback strategies
        data = self._parse_ai_json(ai_response, ticker)
        if not data:
            return self._fallback_recommendation(ticker, stock)

        return AIRecommendation(
            ticker=ticker,
            action=data.get("action", "HOLD"),
            confidence=float(data.get("confidence", 50)),
            price_target=data.get("price_target"),
            stop_loss=data.get("stop_loss"),
            reasons=data.get("reasons", []),
            technical_analysis=data.get("technical_analysis", ""),
            fundamental_analysis=data.get("fundamental_analysis", ""),
            news_impact=data.get("news_impact", ""),
            risk_level=data.get("risk_level", "MEDIUM"),
            time_horizon=data.get("time_horizon", "MEDIUM"),
            ai_approved=data.get("ai_approved", False),
            approval_reason=data.get("approval_reason", ""),
            timestamp=datetime.now().isoformat()
        )

    def _parse_ai_json(self, response: str, ticker: str) -> Optional[Dict]:
        """Parse JSON from AI response with multiple strategies"""
        import re
        try:
            return json.loads(response)
        except:
            pass
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
        except:
            pass
        try:
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if match:
                return json.loads(match.group(1))
        except:
            pass
        try:
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                return json.loads(match.group(0))
        except:
            pass
        logger.error(f"Could not parse AI response for {ticker}. Response: {response[:200]}...")
        return None

    def _fallback_recommendation(self, ticker: str, stock: Dict) -> AIRecommendation:
        """Generate fallback recommendation when AI fails"""
        reasons = []
        action = "HOLD"
        confidence = 50
        curr = stock.get('current_price', 0)
        prev = stock.get('previous_close', 0)
        
        rsi = stock.get('rsi')
        if rsi is not None:
            if rsi < 30:
                action = "BUY"
                confidence = 65
                reasons.append(f"RSI = {rsi:.1f} (oversold - ذروة بيع)")
            elif rsi > 70:
                action = "SELL"
                confidence = 65
                reasons.append(f"RSI = {rsi:.1f} (overbought - ذروة شراء)")
            else:
                reasons.append(f"RSI = {rsi:.1f} (محايد)")
        
        if prev and curr:
            change = (curr - prev) / prev * 100
            if abs(change) > 0:
                reasons.append(f"التغير: {change:+.2f}%")
        
        if not reasons:
            reasons.append("البيانات غير كافية للتحليل")
        
        return AIRecommendation(
            ticker=ticker,
            action=action,
            confidence=confidence,
            price_target=round(curr * 1.1, 2) if curr else None,
            stop_loss=round(curr * 0.95, 2) if curr else None,
            reasons=reasons,
            technical_analysis="لم يتمكن AI من إنتاج تحليل. يتم الاعتماد على المؤشرات الفنية فقط.",
            fundamental_analysis="",
            news_impact="",
            risk_level="MEDIUM",
            time_horizon="MEDIUM",
            ai_approved=False,
            approval_reason="فشل AI في التحليل. يتم الاعتماد على المؤشرات الفنية كاحتياطي.",
            timestamp=datetime.now().isoformat()
        )

    def analyze_batch(self, tickers: List[str]) -> List[AIRecommendation]:
        """تحليل مجموعة أسهم"""
        results = []
        for ticker in tickers:
            try:
                rec = self.analyze_stock(ticker)
                if rec:
                    results.append(rec)
            except Exception as e:
                logger.error(f"Error analyzing {ticker}: {e}")
        return results

    # ============================================================
    # تحليل العملات الرقمية
    # ============================================================

    def get_crypto_data(self, coin_id: str) -> Optional[Dict]:
        """جلب بيانات عملة رقمية من قاعدة البيانات"""
        conn = self._get_db()
        try:
            row = conn.execute("""
                SELECT coin_id, name, symbol, current_price, market_cap,
                       price_change_24h, price_change_percentage_24h,
                       high_24h, low_24h, volume_24h, ath, atl,
                       last_updated
                FROM crypto_prices WHERE coin_id = ?
            """, (coin_id,)).fetchone()
            if row:
                return dict(row)
        finally:
            conn.close()
        return None

    def get_crypto_history(self, coin_id: str, days: int = 30) -> List[Dict]:
        """جلب البيانات التاريخية للعملة الرقمية"""
        conn = self._get_db()
        try:
            rows = conn.execute("""
                SELECT date, price, market_cap, volume
                FROM crypto_price_history
                WHERE coin_id = ?
                ORDER BY date DESC LIMIT ?
            """, (coin_id, days)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def analyze_crypto(self, coin_id: str) -> Optional[AIRecommendation]:
        """تحليل عملة رقمية بالكامل"""
        coin = self.get_crypto_data(coin_id)
        if not coin:
            logger.warning(f"Crypto {coin_id} not found in DB")
            return None

        history = self.get_crypto_history(coin_id, 30)

        history_text = ""
        if history:
            latest = history[0]
            oldest = history[-1]
            change = ((latest['price'] - oldest['price']) / oldest['price'] * 100) if oldest['price'] else 0
            history_text = f"""
## أداء العملة (آخر {len(history)} يوم):
- السعر الأحدث: {latest['price']:,.2f} USD ({latest['date']})
- السعر الأقدم: {oldest['price']:,.2f} USD ({oldest['date']})
- التغير: {change:.2f}%
"""

        prompt = f"""
أنت محلل أسواق مالي متخصص في العملات الرقمية. مهمتك تحليل عملة رقمية وتقديم توصية استثمارية.

## بيانات العملة:
- الاسم: {coin['name']} ({coin['symbol'].upper()})
- السعر الحالي: {coin.get('current_price') or 0:,.2f} USD
- التغير 24 ساعة: {coin.get('price_change_percentage_24h') or 0:.2f}%
- أعلى سعر 24 ساعة: {coin.get('high_24h') or 0:,.2f} USD
- أقل سعر 24 ساعة: {coin.get('low_24h') or 0:,.2f} USD
- حجم التداول 24 ساعة: {coin.get('volume_24h') or 0:,.0f} USD
- القيمة السوقية: {coin.get('market_cap') or 0:,.0f} USD
- ATH (أعلى سعر تاريخي): {coin.get('ath') or 0:,.2f} USD
- ATL (أقل سعر تاريخي): {coin.get('atl') or 0:,.2f} USD

{history_text}

## المطلوب:
قدم تحليلك في صيغة JSON صالحة فقط - لا تضف أي نص خارج JSON:
{{
    "action": "BUY|SELL|HOLD",
    "confidence": 0-100,
    "price_target": رقم,
    "stop_loss": رقم,
    "reasons": ["سبب 1", "سبب 2", "سبب 3"],
    "technical_analysis": "تحليل فني مفصل بالعربي",
    "fundamental_analysis": "تحليل أساسي مفصل بالعربي",
    "news_impact": "تأثير الأخبار على العملة بالعربي",
    "risk_level": "LOW|MEDIUM|HIGH",
    "time_horizon": "SHORT|MEDIUM|LONG",
    "ai_approved": true|false,
    "approval_reason": "اكتب هنا سبب التوصية بالتفصيل: ليه اخترت action ده؟ شوفت إيه في البيانات؟"
}}

تعليمات حاسمة:
1. اكتب JSON صالح فقط
2. approval_reason لازم يكون مفصل
3. reasons لازم تكون list من 3-5 أسباب واضحة
"""

        ai_response = self._call_ai(prompt, temperature=0.3)
        data = self._parse_ai_json(ai_response, coin_id)
        if not data:
            # Fallback based on 24h change
            change = coin.get('price_change_percentage_24h') or 0
            action = "BUY" if change < -10 else "SELL" if change > 20 else "HOLD"
            conf = 60 if abs(change) > 10 else 50
            return AIRecommendation(
                ticker=coin_id.upper(), action=action, confidence=conf,
                price_target=round((coin.get('current_price') or 0) * 1.2, 2) if action == "BUY" else None,
                stop_loss=round((coin.get('current_price') or 0) * 0.85, 2) if action == "BUY" else None,
                reasons=[f"التغير 24h: {change:.2f}%", "تحليل AI غير متاح"],
                technical_analysis=f"التغير 24 ساعة: {change:.2f}%", fundamental_analysis="",
                news_impact="", risk_level="HIGH", time_horizon="MEDIUM",
                ai_approved=False, approval_reason="فشل AI، يتم الاعتماد على التغير 24 ساعة",
                timestamp=datetime.now().isoformat()
            )

        return AIRecommendation(
            ticker=coin_id.upper(),
            action=data.get("action", "HOLD"),
            confidence=float(data.get("confidence", 50)),
            price_target=data.get("price_target"),
            stop_loss=data.get("stop_loss"),
            reasons=data.get("reasons", []),
            technical_analysis=data.get("technical_analysis", ""),
            fundamental_analysis=data.get("fundamental_analysis", ""),
            news_impact=data.get("news_impact", ""),
            risk_level=data.get("risk_level", "MEDIUM"),
            time_horizon=data.get("time_horizon", "MEDIUM"),
            ai_approved=data.get("ai_approved", False),
            approval_reason=data.get("approval_reason", ""),
            timestamp=datetime.now().isoformat()
        )

    # ============================================================
    # تحليل الذهب
    # ============================================================

    def get_gold_data(self) -> Optional[Dict]:
        """جلب بيانات الذهب من قاعدة البيانات"""
        conn = self._get_db()
        try:
            row = conn.execute("""
                SELECT price_24k, price_21k, price_18k, change_24k,
                       source, last_updated
                FROM gold_prices ORDER BY last_updated DESC LIMIT 1
            """).fetchone()
            if row:
                return dict(row)
        finally:
            conn.close()
        return None

    def get_gold_history(self, days: int = 30) -> List[Dict]:
        """جلب البيانات التاريخية للذهب"""
        conn = self._get_db()
        try:
            rows = conn.execute("""
                SELECT date, price_24k, price_21k, price_18k, change_24k
                FROM gold_price_history
                ORDER BY date DESC LIMIT ?
            """, (days,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def analyze_gold(self) -> Optional[AIRecommendation]:
        """تحليل الذهب بالكامل"""
        gold = self.get_gold_data()
        if not gold:
            logger.warning("Gold data not found in DB")
            return None

        history = self.get_gold_history(30)

        history_text = ""
        if history:
            latest = history[0]
            oldest = history[-1]
            change = ((latest['price_24k'] - oldest['price_24k']) / oldest['price_24k'] * 100) if oldest['price_24k'] else 0
            history_text = f"""
## أداء الذهب (آخر {len(history)} يوم):
- عيار 24 أحدث: {latest['price_24k']:,.0f} EGP ({latest['date']})
- عيار 24 أقدم: {oldest['price_24k']:,.0f} EGP ({oldest['date']})
- التغير: {change:.2f}%
"""

        prompt = f"""
أنت محلل مالي متخصص في أسواق الذهب والمعادن النفيسة. مهمتك تحليل سعر الذهب في مصر وتقديم توصية استثمارية.

## بيانات الذهب:
- عيار 24: {gold.get('price_24k') or 0:,.0f} جنيه مصري
- عيار 21: {gold.get('price_21k') or 0:,.0f} جنيه مصري
- عيار 18: {gold.get('price_18k') or 0:,.0f} جنيه مصري
- التغير: {gold.get('change_24k') or 0:+.2f}%
- المصدر: {gold.get('source', 'N/A')}

{history_text}

## المطلوب:
قدم تحليلك في صيغة JSON صالحة فقط:
{{
    "action": "BUY|SELL|HOLD",
    "confidence": 0-100,
    "price_target": رقم,
    "stop_loss": رقم,
    "reasons": ["سبب 1", "سبب 2", "سبب 3"],
    "technical_analysis": "تحليل فني مفصل بالعربي",
    "fundamental_analysis": "تحليل أساسي مفصل بالعربي",
    "news_impact": "تأثير الأخبار على الذهب بالعربي",
    "risk_level": "LOW|MEDIUM|HIGH",
    "time_horizon": "SHORT|MEDIUM|LONG",
    "ai_approved": true|false,
    "approval_reason": "اكتب هنا سبب التوصية بالتفصيل"
}}

تعليمات حاسمة:
1. اكتب JSON صالح فقط
2. approval_reason لازم يكون مفصل
3. reasons لازم تكون list من 3-5 أسباب واضحة
"""

        ai_response = self._call_ai(prompt, temperature=0.3)
        data = self._parse_ai_json(ai_response, "GOLD")
        if not data:
            change = gold.get('change_24k') or 0
            action = "BUY" if change < -2 else "SELL" if change > 5 else "HOLD"
            conf = 60 if abs(change) > 3 else 50
            return AIRecommendation(
                ticker="GOLD", action=action, confidence=conf,
                price_target=round((gold.get('price_24k') or 0) * 1.05, 0) if action == "BUY" else None,
                stop_loss=round((gold.get('price_24k') or 0) * 0.97, 0) if action == "BUY" else None,
                reasons=[f"التغير: {change:.2f}%", "تحليل AI غير متاح"],
                technical_analysis=f"التغير الحالي: {change:.2f}%", fundamental_analysis="",
                news_impact="", risk_level="MEDIUM", time_horizon="MEDIUM",
                ai_approved=False, approval_reason="فشل AI، يتم الاعتماد على التغير الحالي",
                timestamp=datetime.now().isoformat()
            )

        return AIRecommendation(
            ticker="GOLD", action=data.get("action", "HOLD"),
            confidence=float(data.get("confidence", 50)),
            price_target=data.get("price_target"),
            stop_loss=data.get("stop_loss"),
            reasons=data.get("reasons", []),
            technical_analysis=data.get("technical_analysis", ""),
            fundamental_analysis=data.get("fundamental_analysis", ""),
            news_impact=data.get("news_impact", ""),
            risk_level=data.get("risk_level", "MEDIUM"),
            time_horizon=data.get("time_horizon", "MEDIUM"),
            ai_approved=data.get("ai_approved", False),
            approval_reason=data.get("approval_reason", ""),
            timestamp=datetime.now().isoformat()
        )

    def push_recommendation_to_website(self, rec: AIRecommendation) -> bool:
        """إرسال التوصية المعتمدة للموقع الحي"""
        try:
            payload = {
                "ticker": rec.ticker,
                "recommendation": rec.action,
                "confidence": rec.confidence,
                "target_price": rec.price_target,
                "stop_loss": rec.stop_loss,
                "reasons": rec.reasons,
                "technical_analysis": rec.technical_analysis,
                "fundamental_analysis": rec.fundamental_analysis,
                "news_impact": rec.news_impact,
                "risk_level": rec.risk_level,
                "time_horizon": rec.time_horizon,
                "ai_approved": rec.ai_approved,
                "approval_reason": rec.approval_reason,
                "source": "local_ai_engine",
                "timestamp": rec.timestamp
            }
            resp = requests.post(
                f"{WEBSITE_URL}/api/recommendations",
                json=payload,
                timeout=15
            )
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.error(f"Failed to push recommendation: {e}")
            return False


# Singleton instance
ai_engine = AILocalEngine()
