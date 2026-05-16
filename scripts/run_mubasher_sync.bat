@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [%date% %time%] Starting Mubasher Sync...

.venv\Scripts\python.exe -c "
import requests
import sys

API = 'http://localhost:8010'

try:
    r = requests.post(f'{API}/api/sync/mubasher', timeout=120)
    data = r.json()
    if data.get('success'):
        print(f'[OK] Synced: {data.get(\"stocks_synced\", 0)} stocks')
        print(f'[OK] Failed: {data.get(\"stocks_failed\", 0)} stocks')
    else:
        print(f'[ERROR] {data.get(\"error\", \"unknown\")}')
except Exception as e:
    print(f'[ERROR] {e}')
    sys.exit(1)
"

echo [%date% %time%] Mubasher Sync completed.
