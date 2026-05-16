# -*- coding: utf-8 -*-
"""
Market Hours Scheduler — جدولة تحديثات البيانات في ساعات السوق
================================================================
يعمل من 9:30 صباحاً حتى 2:30 مساءً كل يوم (أيام العمل فقط)

Schedule (كل ساعة):
- 09:30: Pipeline كامل + تقرير صباحي
- 10:30: سحب بيانات + تحديث
- 11:30: سحب بيانات + تحديث
- 12:30: سحب بيانات + تحديث
- 13:30: سحب بيانات + تحديث
- 14:30: Pipeline كامل + تقرير نهائي

كل الـ APIs مجانية 100%:
- Crypto: CoinGecko + Binance
- Gold: Binance PAXG + USD/EGP calculation
- Currency: exchangerate-api.com
- EGX: MubasherTrade local DB (primary) + TradingView (VPS fallback)
"""

import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Optional
from loguru import logger

# ============================================================
# Configuration
# ============================================================
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 14
MARKET_CLOSE_MINUTE = 30
SYNC_INTERVAL_MINUTES = 60  # Every hour
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8011")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("logs/market_scheduler.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)


# ============================================================
# Helper Functions
# ============================================================
def is_market_day() -> bool:
    """Check if today is a trading day (Sun-Thu, not Fri/Sat)"""
    weekday = datetime.now().weekday()
    # Python weekday: Monday=0, Sunday=6
    # EGX trading days: Sunday=6, Monday=0, Tuesday=1, Wednesday=2, Thursday=3
    return weekday in [0, 1, 2, 3, 6]  # Sun-Thu


def is_market_hours() -> bool:
    """Check if current time is within market hours (9:30 - 14:30)"""
    now = datetime.now()
    market_open = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)
    market_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)
    return market_open <= now <= market_close


def get_next_run_time() -> Optional[datetime]:
    """Calculate next scheduled run time"""
    now = datetime.now()
    
    # If before market open, next run is at market open
    market_open = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)
    if now < market_open:
        return market_open
    
    # If after market close, next run is tomorrow at market open
    market_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)
    if now > market_close:
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)
    
    # During market hours, next run is at the next hour mark
    next_hour = now.replace(minute=30, second=0, microsecond=0)
    if now.minute >= 30:
        next_hour = next_hour + timedelta(hours=1)
    
    # Don't schedule past market close
    if next_hour > market_close:
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)
    
    return next_hour


def call_api(endpoint: str, method: str = "POST") -> Dict:
    """Call local API endpoint"""
    import urllib.request
    url = f"{API_BASE_URL}{endpoint}"
    try:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        logger.error(f"API call failed: {url} - {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# Sync Jobs
# ============================================================
def job_external_data() -> Dict:
    """Sync Crypto + Gold + Currency (FREE APIs)"""
    logger.info("=" * 60)
    logger.info("[JOB] External Data Sync (Crypto + Gold + Currency)")
    logger.info("=" * 60)
    result = call_api("/api/sync/external-data")
    logger.info(f"External data result: {json.dumps(result, ensure_ascii=False)[:500]}")
    return result


def job_mubasher_sync() -> Dict:
    """Sync from MubasherTrade local DB"""
    logger.info("=" * 60)
    logger.info("[JOB] MubasherTrade Local DB Sync")
    logger.info("=" * 60)
    result = call_api("/api/sync/mubasher")
    logger.info(f"Mubasher result: {json.dumps(result, ensure_ascii=False)[:500]}")
    return result


def job_compute_indicators(asset_type: str = "stock") -> Dict:
    """Compute technical indicators"""
    logger.info(f"[JOB] Compute Indicators for {asset_type}")
    # Compute is a background task, we trigger it via the pipeline or direct
    from data_engine import data_engine
    try:
        data_engine.compute_all_indicators(asset_type=asset_type)
        return {"success": True, "message": f"Computed {asset_type} indicators"}
    except Exception as e:
        logger.error(f"Compute error: {e}")
        return {"success": False, "error": str(e)}


def job_push_to_website() -> Dict:
    """Push all signals to live website"""
    logger.info("[JOB] Push to Website")
    results = {}
    for asset_type in ["stock", "crypto", "gold"]:
        result = call_api(f"/api/sync/push-asset?asset_type={asset_type}")
        results[asset_type] = result
        logger.info(f"Push {asset_type}: {result.get('message', 'N/A')}")
    return results


def job_morning_report() -> Dict:
    """Generate and push morning report"""
    logger.info("=" * 60)
    logger.info("[JOB] Morning Report")
    logger.info("=" * 60)
    result = call_api("/api/sync/push-morning-report")
    logger.info(f"Morning report result: {json.dumps(result, ensure_ascii=False)[:500]}")
    return result


# ============================================================
# Pipeline Runners
# ============================================================
def run_full_pipeline() -> Dict:
    """Run complete pipeline: External → Mubasher → Compute → Push → Report"""
    logger.info("\n" + "=" * 70)
    logger.info("🚀 FULL PIPELINE STARTING")
    logger.info("=" * 70)
    
    start = datetime.now()
    results = {}
    
    # Step 1: External data
    results["external"] = job_external_data()
    
    # Step 2: Mubasher sync
    results["mubasher"] = job_mubasher_sync()
    
    # Step 3: Compute all indicators
    for asset_type in ["stock", "crypto", "gold"]:
        results[f"compute_{asset_type}"] = job_compute_indicators(asset_type)
    
    # Step 4: Push to website
    results["push"] = job_push_to_website()
    
    # Step 5: Morning report
    results["morning_report"] = job_morning_report()
    
    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"\n✅ Full pipeline completed in {elapsed:.1f}s")
    
    return {"success": True, "elapsed_seconds": elapsed, "results": results}


def run_hourly_update() -> Dict:
    """Run hourly update: External → Mubasher → Compute → Push (no report)"""
    logger.info("\n" + "=" * 70)
    logger.info("🔄 HOURLY UPDATE STARTING")
    logger.info("=" * 70)
    
    start = datetime.now()
    results = {}
    
    # Step 1: External data
    results["external"] = job_external_data()
    
    # Step 2: Mubasher sync (if app is open)
    results["mubasher"] = job_mubasher_sync()
    
    # Step 3: Compute
    for asset_type in ["stock", "crypto", "gold"]:
        results[f"compute_{asset_type}"] = job_compute_indicators(asset_type)
    
    # Step 4: Push
    results["push"] = job_push_to_website()
    
    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"\n✅ Hourly update completed in {elapsed:.1f}s")
    
    return {"success": True, "elapsed_seconds": elapsed, "results": results}


# ============================================================
# Main Scheduler Loop
# ============================================================
def run_scheduler():
    """Main scheduler loop — runs indefinitely"""
    logger.info("=" * 70)
    logger.info("📅 MARKET HOURS SCHEDULER STARTED")
    logger.info("   Market Hours: 9:30 AM - 2:30 PM (Sun-Thu)")
    logger.info("   Sync Interval: Every hour")
    logger.info("   APIs: ALL FREE (CoinGecko, Binance, exchangerate-api)")
    logger.info("=" * 70)
    
    while True:
        try:
            now = datetime.now()
            
            # Skip weekends
            if not is_market_day():
                next_run = now + timedelta(days=1)
                next_run = next_run.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)
                wait_seconds = (next_run - now).total_seconds()
                logger.info(f"Weekend/holiday. Sleeping until {next_run.strftime('%Y-%m-%d %H:%M')}")
                time.sleep(min(wait_seconds, 3600))  # Sleep max 1 hour at a time
                continue
            
            # Calculate next run
            next_run = get_next_run_time()
            wait_seconds = (next_run - now).total_seconds()
            
            if wait_seconds > 0:
                logger.info(f"Next run at {next_run.strftime('%H:%M')} (waiting {wait_seconds/60:.0f} minutes)")
                time.sleep(wait_seconds)
            
            # Determine what to run based on time
            current_hour = datetime.now().hour
            current_minute = datetime.now().minute
            
            if (current_hour == MARKET_OPEN_HOUR and current_minute == MARKET_OPEN_MINUTE):
                # 9:30 AM — Full pipeline with morning report
                run_full_pipeline()
            elif (current_hour == MARKET_CLOSE_HOUR and current_minute == MARKET_CLOSE_MINUTE):
                # 2:30 PM — Full pipeline with final report
                run_full_pipeline()
            else:
                # Hourly update
                run_hourly_update()
            
            # Small delay to prevent double-running
            time.sleep(60)
            
        except KeyboardInterrupt:
            logger.info("\nScheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time.sleep(300)  # Wait 5 minutes on error


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Market Hours Scheduler")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon (waits for scheduled times)")
    parser.add_argument("--now", action="store_true", help="Run full pipeline immediately")
    parser.add_argument("--hourly", action="store_true", help="Run hourly update immediately")
    
    args = parser.parse_args()
    
    if args.now:
        result = run_full_pipeline()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.hourly:
        result = run_hourly_update()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Default: run as daemon
        run_scheduler()
