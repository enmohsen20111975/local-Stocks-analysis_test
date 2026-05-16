# VPS Service Documentation
## وثائق خدمة السيرفر الافتراضي

---

## 📋 نظرة عامة

| العنصر | القيمة |
|--------|--------|
| **VPS URL** | `http://72.61.137.86:8010` |
| **النسخة** | 8.0.0 |
| **قاعدة البيانات** | SQLite: `/root/egxpy_service/data/egx_data.db` |
| **الحالة** | يعمل ✅ |

---

## 🔌 API Endpoints

### 1. Health Check
```
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "version": "8.0.0",
  "database": "/root/egxpy_service/data/egx_data.db",
  "stats": {
    "stocks_count": 295,
    "history_count": 0,
    "predictions_count": 0
  },
  "data_sources": {
    "numpy": true,
    "pandas": true,
    "tradingview": true
  }
}
```

### 2. قائمة الأسهم
```
GET /api/stocks?limit=100&search=COMI
```
**Response:**
```json
{
  "count": 100,
  "data": [
    {
      "symbol": "COMI",
      "current_price": 138.5,
      "previous_close": 138.0,
      "open_price": 138.11,
      "high_price": 138.7,
      "low_price": 138.0,
      "volume": 75845,
      "last_updated": "2026-05-08T15:30:00"
    }
  ]
}
```

### 3. تفاصيل سهم
```
GET /api/stocks/{ticker}
```

### 4. المؤشرات الفنية
```
GET /api/indicators/{ticker}
```
**Response:**
```json
{
  "success": true,
  "data": {
    "ticker": "COMI",
    "current_price": 138.5,
    "indicators": {
      "rsi": {"value": 55.2, "signal": "neutral"},
      "macd": {"trend": "bullish"},
      "sma_20": 137.5,
      "sma_50": 135.2,
      "bollinger": {
        "upper": 142.0,
        "middle": 137.5,
        "lower": 133.0
      },
      "overall_signal": "buy",
      "signal_strength": 0.65
    }
  }
}
```

### 5. التوقعات
```
GET /api/predict/{ticker}?days=7
```
**Response:**
```json
{
  "success": true,
  "data": {
    "ticker": "COMI",
    "current_price": 138.5,
    "prediction": {
      "predicted_price": 141.2,
      "trend": "buy",
      "confidence": 75.5,
      "prediction_date": "2026-05-15"
    }
  }
}
```

### 6. نظرة السوق
```
GET /api/market/overview
```

### 7. مزامنة TradingView
```
POST /api/sync
```
**Body:**
```json
{
  "symbols": ["COMI", "HRHO", "ETEL"]
}
```

### 8. البيانات التاريخية
```
GET /api/history/{ticker}?days=30
```

---

## 🗄️ هيكل قاعدة البيانات

### جدول stocks
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | INTEGER | المفتاح الأساسي |
| symbol | TEXT | رمز السهم |
| current_price | REAL | السعر الحالي |
| previous_close | REAL | سعر الإغلاق السابق |
| open_price | REAL | سعر الافتتاح |
| high_price | REAL | أعلى سعر |
| low_price | REAL | أدنى سعر |
| volume | REAL | حجم التداول |
| last_updated | TEXT | آخر تحديث |

### جدول technical_indicators
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | INTEGER | المفتاح الأساسي |
| ticker | TEXT | رمز السهم |
| rsi | REAL | مؤشر RSI |
| rsi_signal | TEXT | إشارة RSI |
| macd | REAL | قيمة MACD |
| macd_signal | REAL | خط الإشارة |
| macd_histogram | REAL | الهيستوجرام |
| macd_trend | TEXT | اتجاه MACD |
| sma_20 | REAL | المتوسط البسيط 20 يوم |
| sma_50 | REAL | المتوسط البسيط 50 يوم |
| ema_20 | REAL | المتوسط الأسي 20 يوم |
| bollinger_upper | REAL | النطاق العلوي |
| bollinger_middle | REAL | النطاق الأوسط |
| bollinger_lower | REAL | النطاق السفلي |
| overall_signal | TEXT | الإشارة العامة |
| signal_strength | REAL | قوة الإشارة |
| calculated_at | TEXT | وقت الحساب |

### جدول predictions
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | INTEGER | المفتاح الأساسي |
| ticker | TEXT | رمز السهم |
| prediction_date | TEXT | تاريخ التوقع |
| predicted_price | REAL | السعر المتوقع |
| current_price | REAL | السعر الحالي |
| confidence | REAL | نسبة الثقة |
| trend | TEXT | الاتجاه |
| model_type | TEXT | نوع النموذج |
| status | TEXT | الحالة |
| created_at | TEXT | تاريخ الإنشاء |

### جدول price_history
| العمود | النوع | الوصف |
|--------|-------|-------|
| id | INTEGER | المفتاح الأساسي |
| symbol | TEXT | رمز السهم |
| date | TEXT | التاريخ |
| open | REAL | الافتتاح |
| high | REAL | الأعلى |
| low | REAL | الأدنى |
| close | REAL | الإغلاق |
| volume | REAL | الحجم |

---

## ⚠️ المشاكل الحالية

### 1. البيانات التاريخية فارغة
- `price_history`: 0 سجل
- `stock_price_history`: 0 سجل

**السبب:** البيانات لم تُرفع من Mubasher بعد

**الحل:** تشغيل سكربت المزامنة:
```bash
cd /home/z/my-project/mubasher-python-app
python3 mubasher_db_sync.py
```

### 2. المؤشرات تعتمد على البيانات التاريخية
- VPS يحسب المؤشرات من `price_history`
- بما أن الجدول فارغ، لا يمكن حساب المؤشرات

### 3. API لا يدعم POST للمؤشرات
- `/api/indicators/{ticker}` لا يقبل POST
- يجب تحديث كود VPS لإضافة هذا الـ endpoint

---

## 🔧 الحلول المقترحة

### الحل 1: تحديث VPS code
إضافة endpoints جديدة:
```python
@app.route('/api/mubasher/bulk', methods=['POST'])
def bulk_sync():
    # قبول بيانات الأسهم والمؤشرات والتوقعات
    pass

@app.route('/api/indicators/<ticker>', methods=['POST'])
def upsert_indicators(ticker):
    # حفظ المؤشرات مباشرة
    pass

@app.route('/api/predict/<ticker>', methods=['POST'])
def upsert_prediction(ticker):
    # حفظ التوقعات مباشرة
    pass
```

### الحل 2: استخدام السيرفر المحلي
```bash
# تشغيل السيرفر المحلي على المنفذ 8020
python3 realtime_data_server.py
```

### الحل 3: نسخ قاعدة البيانات مباشرة
```bash
# نسخ قاعدة البيانات المحدثة إلى VPS
scp /home/z/my-project/upload/egx_data.db root@72.61.137.86:/root/egxpy_service/data/
```

---

## 📂 مصادر البيانات

### INTRADAY_MASTER.db (61MB)
- **المسار:** `/home/z/my-project/upload/INTRADAY_MASTER.db`
- **المحتوى:** بيانات لحظية من Mubasher
- **الجداول:** 267 جدول (جدول لكل سهم)
- **السجلات:** ~500,000 سجل

### egx_History_monthly.db (4.8MB)
- **المسار:** `/home/z/my-project/upload/egx_History_monthly.db`
- **المحتوى:** هيكل فقط (جداول فارغة)

### egx_data.db (160KB)
- **المسار المحلي:** `/home/z/my-project/upload/egx_data.db`
- **المسار VPS:** `/root/egxpy_service/data/egx_data.db`
- **المحتوى:** قاعدة بيانات التطبيق

---

## 🚀 خطوات التشغيل

### 1. تشغيل السيرفر المحلي
```bash
cd /home/z/my-project/mubasher-python-app
python3 realtime_data_server.py
```

### 2. تشغيل واجهة المراقبة
```bash
cd /home/z/my-project/mubasher-python-app
python3 mubasher_monitor_gui.py
```

### 3. تشغيل المزامنة
```bash
cd /home/z/my-project/mubasher-python-app
python3 mubasher_db_sync.py
```

---

## 📊 حالة البيانات الحالية

| العنصر | القيمة |
|--------|--------|
| الأسهم في VPS | 295 |
| الأسهم مع بيانات تاريخية | 0 |
| المؤشرات المحسوبة | 0 |
| التوقعات | 0 |

**بعد تشغيل المزامنة:**

| العنصر | القيمة |
|--------|--------|
| الأسهم المحدثة | 260 |
| المؤشرات المحسوبة | 187 |
| التوقعات المنشأة | 191 |

---

## 🔐 الملاحظات المهمة

1. **تحديث تلقائي:** السيرفر المحلي يتحدث كل 5 دقائق تلقائياً
2. **البيانات التاريخية:** VPS يحتاج بيانات تاريخية لحساب المؤشرات
3. **المنافذ:**
   - VPS: 8010
   - السيرفر المحلي: 8020

---

## 📞 للتواصل

- **المطور:** GLMinvestment Team
- **آخر تحديث:** 2026-05-08
