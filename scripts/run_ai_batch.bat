@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [%date% %time%] Starting AI Batch Analysis...

.venv\Scripts\python.exe -c "
import requests
import json
import sys

API = 'http://localhost:8010'

try:
    # Run AI batch for all stocks (limit 100 per run)
    r = requests.post(f'{API}/api/engine/run-ai-batch?limit=100', timeout=10)
    data = r.json()
    print(f'[OK] {data.get(\"message\", \"started\")}')
    
    # Check status after a while
    import time
    time.sleep(5)
    status = requests.get(f'{API}/api/engine/status', timeout=10).json()
    print(f'[Status] Analyzed: {status.get(\"ai_analyzed\", 0)} stocks')
    print(f'[Status] BUY: {status.get(\"buy_recommendations\", 0)}')
    print(f'[Status] SELL: {status.get(\"sell_recommendations\", 0)}')
    print(f'[Status] HOLD: {status.get(\"hold_recommendations\", 0)}')
    
except Exception as e:
    print(f'[ERROR] {e}')
    sys.exit(1)
"

echo [%date% %time%] AI Batch Analysis completed.
