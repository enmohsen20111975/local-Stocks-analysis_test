# API Reference

## Base URL

```
http://localhost:8020/api
```

## Endpoints

### Health Check

```
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2024-01-15T10:30:00"
}
```

---

### Statistics

```
GET /api/stats
```

**Response:**
```json
{
  "success": true,
  "data": {
    "stocks_count": 295,
    "history_count": 108333,
    "signals": {
      "buy": 73,
      "sell": 158,
      "hold": 77
    },
    "last_update": "2024-01-15T10:00:00"
  }
}
```

---

### Stocks List

```
GET /api/stocks
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 100 | Maximum results |
| sector | string | null | Filter by sector |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "ticker": "COMI",
      "name": "Commercial International Bank",
      "name_ar": "البنك التجاري الدولي",
      "sector": "Banks",
      "price": 46.38,
      "change": 0.50,
      "change_percent": 1.09
    }
  ],
  "count": 100
}
```

---

### Single Stock

```
GET /api/stocks/{symbol}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "ticker": "COMI",
    "name": "Commercial International Bank",
    "current_price": 46.38,
    "analysis": {
      "action": "BUY",
      "confidence": 70,
      "rsi": 45.5,
      "trend": "bullish"
    }
  }
}
```

---

### Recommendations

```
GET /api/recommendations
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| action | string | null | Filter: BUY, SELL, HOLD |
| limit | int | 20 | Maximum results |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "ticker": "SEIG",
      "action": "BUY",
      "confidence": 70,
      "price": 188.11,
      "target_1": 207.36,
      "target_2": null,
      "stop_loss": 184.24,
      "trend": "strong_bullish"
    }
  ]
}
```

---

### Crypto

```
GET /api/crypto
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "ticker": "bitcoin",
      "price": 77902.86,
      "date": "2024-01-15"
    }
  ]
}
```

---

### Gold

```
GET /api/gold
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "karat": "24",
      "price": 3850.00,
      "change": 25.00
    }
  ]
}
```

---

### Sectors

```
GET /api/sectors
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "sector": "Banks",
      "count": 25,
      "avg_price": 45.50
    }
  ]
}
```

---

### Data Sources

```
GET /api/sources
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "name": "Twelve Data",
      "url": "https://api.twelvedata.com",
      "status": "online",
      "type": "stocks",
      "limit": "800/day"
    }
  ]
}
```

---

### Market Summary

```
GET /api/market/summary
```

**Response:**
```json
{
  "success": true,
  "data": {
    "signals": {
      "buy": 73,
      "sell": 158,
      "hold": 77
    },
    "sentiment": "bearish",
    "top_buy": [...],
    "top_sell": [...]
  }
}
```

---

### Sync Stocks

```
POST /api/sync/stocks
```

**Response:**
```json
{
  "success": true,
  "message": "Updated 251 stocks"
}
```

---

### Compute Indicators

```
POST /api/compute/indicators
```

**Response:**
```json
{
  "success": true,
  "message": "Processed 295 stocks"
}
```

---

## Error Response

```json
{
  "success": false,
  "error": "Error message"
}
```

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET requests | No limit |
| POST sync/stocks | 10/minute |
| POST compute/indicators | 5/minute |
