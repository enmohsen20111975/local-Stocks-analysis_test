# -*- coding: utf-8 -*-
"""
Auto Sync Scheduler - جدولة التحديث التلقائي
=================================================
بشكل ساعي:
  1. سحب بيانات MubasherTrade (لو متوفرة)
  2. إعادة حساب المؤشرات
  3. رفع التوصيات للموقع الحي
"""

import os
import sys
import time
import schedule
import requests
import json
from datetime import datetime
from loguru import logger

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_engine import data_engine
from mubasher_sync import mubasher_sync

# Config
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://invist.m2y.net")
API_KEY = os.getenv("WEBSITE_API_KEY", "")
PUSH_ENABLED = os.getenv("AUTO_PUSH_ENABLED", "true").lower() == "true"
SYNC_ENABLED = os.getenv("AUTO_SYNC_ENABLED", "true").lower() == "true"


def run_full_pipeline():
    """تشغيل الـ pipeline كامل: sync → compute → push"""
    logger.info("=" * 60)
    logger.info(f"[AutoSync] Starting full pipeline at {datetime.now()}")
    logger.info("=" * 60)
    
    results = {"sync": None, "compute": None, "push": None}
    
    # Step 1: Sync from MubasherTrade
    if SYNC_ENABLED:
        try:
            logger.info("[AutoSync] Step 1: Syncing from MubasherTrade...")
            sync_result = mubasher_sync.full_sync()
            results["sync"] = sync_result
            logger.info(f"[AutoSync] Sync complete: {sync_result}")
        except Exception as e:
            logger.error(f"[AutoSync] Sync failed: {e}")
            results["sync"] = {"error": str(e)}
    
    # Step 2: Recompute indicators
    try:
        logger.info("[AutoSync] Step 2: Recomputing indicators...")
        compute_result = data_engine.compute_all_indicators(asset_type="stock")
        data_engine.compute_crypto_indicators()
        data_engine.compute_gold_indicators()
        results["compute"] = compute_result
        logger.info(f"[AutoSync] Compute complete: {compute_result}")
    except Exception as e:
        logger.error(f"[AutoSync] Compute failed: {e}")
        results["compute"] = {"error": str(e)}
    
    # Step 3: Push to website
    if PUSH_ENABLED:
        try:
            logger.info("[AutoSync] Step 3: Pushing to website...")
            push_result = push_to_website("stock")
            results["push"] = push_result
            logger.info(f"[AutoSync] Push complete: {push_result}")
        except Exception as e:
            logger.error(f"[AutoSync] Push failed: {e}")
            results["push"] = {"error": str(e)}
    
    logger.info("[AutoSync] Full pipeline completed")
    return results


def push_to_website(asset_type: str) -> dict:
    """Push signals to live website via API"""
    signals = data_engine.get_all_signals(asset_type=asset_type)
    if not signals:
        return {"error": f"No {asset_type} signals found"}
    
    payload = []
    for sig in signals:
        payload.append({
            "ticker": sig.get("ticker"),
            "action": sig.get("action", "HOLD"),
            "confidence": sig.get("confidence", 50),
            "current_price": sig.get("current_price"),
            "entry_zone_low": sig.get("entry_zone_low"),
            "entry_zone_high": sig.get("entry_zone_high"),
            "entry_trigger": sig.get("entry_trigger"),
            "support_level": sig.get("support_level"),
            "target_1": sig.get("target_1"),
            "target_2": sig.get("target_2"),
            "investment_target": sig.get("investment_target"),
            "stop_loss": sig.get("stop_loss"),
            "expected_return_pct": sig.get("expected_return_pct"),
            "reasons": sig.get("reasons", []),
            "trend": sig.get("trend"),
            "asset_type": asset_type,
            "timestamp": datetime.now().isoformat()
        })
    
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    
    pushed = 0
    failed = 0
    batch_size = 100
    
    for i in range(0, len(payload), batch_size):
        batch = payload[i:i+batch_size]
        for attempt in range(3):
            try:
                resp = requests.post(
                    f"{WEBSITE_URL}/api/recommendations/batch",
                    json={"signals": batch, "asset_type": asset_type},
                    headers=headers,
                    timeout=30
                )
                if resp.status_code in (200, 201):
                    pushed += len(batch)
                    break
                else:
                    if attempt == 2:
                        failed += len(batch)
            except Exception:
                if attempt == 2:
                    failed += len(batch)
                else:
                    time.sleep(2 ** attempt)
    
    return {
        "success": True,
        "pushed": pushed,
        "failed": failed,
        "total": len(signals)
    }


def generate_and_push_morning_report():
    """توليد التقرير الصباحي ورفعه للموقع"""
    logger.info("[AutoSync] Generating morning report...")
    
    try:
        signals = data_engine.get_all_signals(action="BUY", min_confidence=60, asset_type="stock")
        signals.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        signals = signals[:10]
        
        today_str = datetime.now().strftime("%A %d-%m-%Y")
        header = f"*التحليل اليومي*\nمتابعة فنية لجلسة {today_str} — للأغراض التعليمية فقط"
        
        recommendations = []
        for idx, sig in enumerate(signals, 1):
            lines = []
            conf = sig.get('confidence', 0)
            lines.append(f"{idx}- *{sig.get('ticker')} | الثقة: {conf}% | اخر سعر {sig.get('current_price')}*")
            if sig.get('entry_zone_low') and sig.get('entry_zone_high'):
                lines.append(f"نطاق سعري محتمل: من {sig['entry_zone_low']} الي {sig['entry_zone_high']} جنية")
            if sig.get('entry_trigger'):
                lines.append(f"او الاستقرار والثبات اعلاه {sig['entry_trigger']}")
            if sig.get('support_level'):
                lines.append(f"دعم مهم في {sig['support_level']}")
            if sig.get('target_1') and sig.get('target_2'):
                lines.append(f"*مستوى ربح متوقع {sig['target_1']} ثم {sig['target_2']} جنية*")
            if sig.get('investment_target'):
                lines.append(f"*تارجت بعيد المدى {sig['investment_target']}*")
            if sig.get('expected_return_pct'):
                lines.append(f"نسبة ربح متوقع من {round(sig['expected_return_pct'] * 0.7, 1)}% الي {sig['expected_return_pct']}%")
            if sig.get('stop_loss'):
                lines.append(f"مستوى دعم/مخاطر: {sig['stop_loss']}")
            recommendations.append("\n".join(lines))
        
        footer = "⚠️ هذا التحليل للأغراض التعليمية والتثقيفية فقط.\nلا يُعد توصية استثمارية ولا يعتمد عليه لاتخاذ قرارات مالية.\nيُرجى استشارة مستشار مالي مرخص قبل أي قرار استثماري."
        
        full_text = header + "\n\n" + "\n\n".join(recommendations) + "\n\n" + footer
        
        # Push report to website
        if PUSH_ENABLED:
            headers = {"Content-Type": "application/json"}
            if API_KEY:
                headers["X-API-Key"] = API_KEY
            
            for attempt in range(3):
                try:
                    resp = requests.post(
                        f"{WEBSITE_URL}/api/reports/morning",
                        json={
                            "header": header,
                            "recommendations": recommendations,
                            "footer": footer,
                            "full_text": full_text,
                            "date": datetime.now().isoformat()
                        },
                        headers=headers,
                        timeout=30
                    )
                    if resp.status_code in (200, 201):
                        logger.info(f"[AutoSync] Morning report pushed successfully ({len(recommendations)} recs)")
                        return {"success": True, "recommendations_count": len(recommendations)}
                except Exception as e:
                    logger.warning(f"[AutoSync] Morning report push attempt {attempt+1} failed: {e}")
                    time.sleep(2 ** attempt)
        
        return {"success": True, "recommendations_count": len(recommendations), "pushed": False}
    
    except Exception as e:
        logger.error(f"[AutoSync] Morning report generation failed: {e}")
        return {"error": str(e)}


# Schedule
schedule.every().hour.at(":00").do(run_full_pipeline)
schedule.every().day.at("08:30").do(generate_and_push_morning_report)

logger.info("[AutoSync] Scheduler started")
logger.info("[AutoSync] Jobs:")
logger.info("  - Full pipeline every hour")
logger.info("  - Morning report at 08:30 daily")

if __name__ == "__main__":
    # Run once immediately
    run_full_pipeline()
    
    while True:
        schedule.run_pending()
        time.sleep(60)
