@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [%date% %time%] Starting Market Data Update...

.venv\Scripts\python.exe -c "
import requests
import sys

API = 'http://localhost:8010'
endpoints = [
    ('Gold', '/api/gold'),
    ('Crypto', '/api/crypto?limit=50'),
    ('Market Overview', '/api/market/overview'),
    ('Top Gainers', '/api/market/top-gainers?limit=10'),
    ('Top Losers', '/api/market/top-losers?limit=10'),
]

try:
    for name, path in endpoints:
        r = requests.get(f'{API}{path}', timeout=30)
        if r.status_code == 200:
            print(f'[OK] {name} updated')
        else:
            print(f'[WARN] {name}: {r.status_code}')
except Exception as e:
    print(f'[ERROR] {e}')
    sys.exit(1)
"

echo [%date% %time%] Market Data Update completed.
