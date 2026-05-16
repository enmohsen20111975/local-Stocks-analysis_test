"""
Hourly AI Scheduler
جدولة التحليل كل ساعة

يتم تشغيل هذا الموديول كـ background process
"""

import asyncio
import schedule
import time
import threading
import logging
from datetime import datetime
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_investment_analyzer import InvestmentAIAnalyzer, HourlyAnalysisScheduler
from ai_news_agent import AINewsAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class HourlyAIWorker:
    """عامل التحليل الساعي"""
    
    def __init__(self):
        self.analyzer = InvestmentAIAnalyzer()
        self.news_agent = AINewsAgent()
        self.scheduler = HourlyAnalysisScheduler(self.analyzer)
        self.running = False
        self.last_run = None
        
    def run_hourly_task(self):
        """تنفيذ المهمة الساعية"""
        logger.info("="*60)
        logger.info(f"Starting hourly AI analysis at {datetime.now()}")
        logger.info("="*60)
        
        try:
            # 1. Run stock analysis
            logger.info("Step 1: Analyzing stocks...")
            recommendations = self.scheduler.run_analysis()
            logger.info(f"Analyzed {len(recommendations)} stocks")
            
            # 2. Get market news
            logger.info("Step 2: Fetching market news...")
            news = self.news_agent.search_news_via_ai("البورصة المصرية EGX")
            logger.info(f"Found {len(news)} news items")
            
            # 3. Generate daily brief
            logger.info("Step 3: Generating market brief...")
            brief = self.news_agent.get_egx_daily_brief()
            logger.info(f"Market status: {brief.get('market_status', 'unknown')}")
            
            # 4. Save results
            self._save_hourly_report(recommendations, news, brief)
            
            self.last_run = datetime.now()
            logger.info("Hourly analysis completed successfully!")
            
        except Exception as e:
            logger.error(f"Error in hourly task: {e}")
    
    def _save_hourly_report(self, recommendations, news, brief):
        """حفظ التقرير الساعي"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "recommendations": recommendations,
            "news": news,
            "brief": brief
        }
        
        # Save to file
        report_dir = os.path.join(os.path.dirname(__file__), '..', 'ai_reports')
        os.makedirs(report_dir, exist_ok=True)
        
        filename = f"hourly_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        filepath = os.path.join(report_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Report saved to {filepath}")
    
    def start(self):
        """بدء الجدولة"""
        self.running = True
        logger.info("Starting hourly AI scheduler...")
        
        # Schedule every hour at minute 0
        schedule.every().hour.at(":00").do(self.run_hourly_task)
        
        # Run first task immediately
        logger.info("Running initial analysis...")
        self.run_hourly_task()
        
        # Start scheduler loop
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def stop(self):
        """إيقاف الجدولة"""
        self.running = False
        logger.info("Stopping hourly AI scheduler...")


def run_in_background():
    """تشغيل في الخلفية"""
    worker = HourlyAIWorker()
    
    try:
        worker.start()
    except KeyboardInterrupt:
        worker.stop()
        logger.info("Scheduler stopped by user")


if __name__ == "__main__":
    print("="*60)
    print("AI Investment Analysis - Hourly Scheduler")
    print("="*60)
    print("\nThis will run analysis every hour at minute 0.")
    print("Press Ctrl+C to stop.\n")
    
    run_in_background()
