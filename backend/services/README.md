# EGX Data API Service for VPS

Python Flask API service for fetching EGX stock market data with comprehensive features.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    HOSTINGER (Shared Host)                     │
│                                                                │
│   Next.js App (https://invist.m2y.net)                        │
│   • User Interface                                             │
│   • Authentication                                             │
│   • Portfolio Management                                       │
│   • Calls VPS API for real-time data                          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP API calls
                            ▼
┌────────────────────────────────────────────────────────────────┐
│                    VPS (72.61.137.86:8010)                     │
│                                                                │
│   Python Flask API                                             │
│   • ALL 295 EGX stocks                                         │
│   • Real-time prices from TradingView                         │
│   • Historical data (yfinance)                                │
│   • Technical indicators (RSI, MACD, Bollinger)               │
│   • Price alerts system                                        │
│   • Daily market reports                                       │
│   • SQLite database (caches all data)                         │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Quick Deploy

### 1. Copy files to VPS
```bash
scp -r vps-service/* root@72.61.137.86:/opt/egx-api/
```

### 2. Install dependencies
```bash
ssh root@72.61.137.86
cd /opt/egx-api
pip3 install -r requirements.txt
```

### 3. Run the service
```bash
python3 egx_api_service.py
```

### 4. Run as systemd service (auto-start on boot)
```bash
cp egx-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable egx-api
systemctl start egx-api
```

## API Endpoints

**Base URL:** `http://72.61.137.86:8010`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/stocks/all` | **ALL 295 EGX stocks** |
| GET | `/api/stocks` | Stocks with pagination |
| GET | `/api/stock/{symbol}` | Single stock |
| GET | `/api/indices` | EGX indices (EGX30, EGX50, etc.) |
| GET | `/api/history/{symbol}` | Historical price data |
| GET | `/api/indicators/{symbol}` | Technical indicators |
| GET | `/api/alerts` | List price alerts |
| POST | `/api/alerts` | Create price alert |
| DELETE | `/api/alerts/{id}` | Delete alert |
| GET | `/api/reports/daily` | Daily market report |
| GET | `/api/search?q={query}` | Search stocks |
| GET | `/api/exchanges` | List supported exchanges |
| POST | `/api/sync` | Trigger data sync |

## Example Usage

### Get ALL Stocks (295 stocks)
```bash
curl http://72.61.137.86:8010/api/stocks/all
```

### Get Single Stock
```bash
curl http://72.61.137.86:8010/api/stock/COMI
```

### Get Indices
```bash
curl http://72.61.137.86:8010/api/indices
```

### Get Technical Indicators
```bash
curl http://72.61.137.86:8010/api/indicators/COMI
```

### Create Price Alert
```bash
curl -X POST http://72.61.137.86:8010/api/alerts \
  -H "Content-Type: application/json" \
  -d '{"symbol": "COMI", "target_price": 150.0, "condition": "above"}'
```

### Get Daily Report
```bash
curl http://72.61.137.86:8010/api/reports/daily
```

## Data Storage

The VPS stores all data locally in SQLite:
- **stocks**: All 295 EGX stocks with current prices
- **price_history**: Historical OHLCV data
- **indices**: EGX30, EGX50, EGX70, EGX100, EGX30C
- **price_alerts**: User price alerts
- **daily_reports**: Cached daily reports

## Automatic Sync

The service automatically syncs data every 5 minutes:
- Fetches prices for all 295 stocks from TradingView
- Updates indices
- Checks price alerts

## Logs

```bash
# View logs
journalctl -u egx-api -f

# Restart service
systemctl restart egx-api

# Stop service
systemctl stop egx-api
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8010` | API server port |
| `DATABASE_PATH` | `/opt/egx-api/data/egx_data.db` | SQLite database path |

## Files

```
vps-service/
├── egx_api_service.py    # Main API service (complete)
├── requirements.txt      # Python dependencies
├── egx-api.service       # Systemd service file
└── README.md             # This file
```

## Supported Exchanges

| Code | Exchange | Country |
|------|----------|---------|
| EGX | Egyptian Exchange | Egypt |
| NASDAQ | NASDAQ | USA |
| NYSE | New York Stock Exchange | USA |
| LSE | London Stock Exchange | UK |
| TSE | Tokyo Stock Exchange | Japan |
| HKG | Hong Kong Stock Exchange | Hong Kong |
| TADAWUL | Saudi Stock Exchange | Saudi Arabia |
| DFM | Dubai Financial Market | UAE |
| NSE | National Stock Exchange | India |

---

*API Documentation: See FLUTTER_MOBILE_APP_GUIDE.md for complete Flutter integration guide.*
