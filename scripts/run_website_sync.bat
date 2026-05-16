@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [%date% %time%] Starting Website Sync...

.venv\Scripts\python.exe -c "
import requests
import sys

API = 'http://localhost:8010'

try:
    # Sync stocks
    r1 = requests.post(f'{API}/api/sync/stocks', timeout=60)
    d1 = r1.json()
    print(f'[Stocks] {d1.get(\"stats\", {})}')
    
    # Sync history (50 stocks)
    r2 = requests.post(f'{API}/api/sync/history?max_stocks=50', timeout=120)
    d2 = r2.json()
    print(f'[History] {d2.get(\"stats\", {})}')
    
except Exception as e:
    print(f'[ERROR] {e}')
    sys.exit(1)
"

echo [%date% %time%] Website Sync completed.
