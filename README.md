# EGX Data Engine 📊

محرك بيانات وتحليلات البورصة المصرية

## 🚀 نظرة عامة

EGX Data Engine هو نظام متكامل لتحليل أسهم البورصة المصرية مع واجهة ويب بسيطة وسريعة.

### الميزات الرئيسية

- **📈 تحليل فني شامل** - RSI, MACD, Moving Averages, Bollinger Bands
- **🎯 توصيات ذكية** - BUY / SELL / HOLD مع مستوى ثقة
- **🔌 مصادر بيانات متعددة** - Twelve Data, EODHD, CoinGecko, وأكثر
- **🪙 عملات رقمية** - Bitcoin, Ethereum, وأكثر من 50 عملة
- **💰 الذهب** - أسعار 3 عيارات (18, 21, 24)
- **⚡ سريع وخفيف** - بدون Node.js، فقط Python و Vanilla JS

## 📁 هيكل المشروع

```
egx-data-engine/
├── backend/
│   ├── server.py           # السيرفر الرئيسي
│   ├── services/
│   │   ├── data_engine.py  # محرك البيانات
│   │   ├── enhanced_data_sources.py
│   │   └── technical_analysis.py
│   └── models/
├── frontend/
│   ├── index.html          # الصفحة الرئيسية
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── data/
│   └── egx_investment.db   # قاعدة البيانات
├── scripts/
│   └── update_data.py      # سكريبت التحديث
├── docs/
│   ├── API.md
│   ├── DATA_SOURCES.md
│   └── DEPLOYMENT.md
├── logs/
├── requirements.txt
└── README.md
```

## ⚡ التشغيل السريع

### 1. التثبيت

```bash
# استنساخ المشروع
git clone https://github.com/enmohsen20111975/local-Stocks-analysis_test.git
cd local-Stocks-analysis_test

# إنشاء بيئة افتراضية
python -m venv venv
source venv/bin/activate  # Linux/Mac
# أو
venv\Scripts\activate     # Windows

# تثبيت المتطلبات
pip install -r requirements.txt
```

### 2. التشغيل

```bash
# تشغيل السيرفر
python backend/server.py

# أو استخدام السكريبت
python scripts/update_data.py
```

### 3. الوصول

افتح المتصفح على: `http://localhost:8020`

## 📊 قاعدة البيانات

- **عدد الأسهم**: 295+
- **السجلات التاريخية**: 108,333+
- **القطاعات**: 11
- **العملات الرقمية**: 50+

## 🔌 مصادر البيانات

| المصدر | النوع | الحد المجاني |
|--------|-------|--------------|
| الموقع الحي | أسهم EGX | غير محدود |
| Twelve Data | أسهم/عملات | 800/يوم |
| EODHD | أسهم | 20/يوم |
| CoinGecko | عملات | 50/دقيقة |
| Alpha Vantage | أسهم | 25/يوم |

## 🎯 التحليلات

### المؤشرات الفنية

| المؤشر | الوصف |
|--------|-------|
| RSI | مؤشر القوة النسبية |
| MACD | تقارب وتباعد المتوسطات |
| SMA | المتوسط البسيط (20, 50, 200) |
| EMA | المتوسط الأسي (12, 26) |
| BB | نطاقات بولينجر |
| ADX | مؤشر الاتجاه |

### التوصيات

- **BUY** 🟢 - توصية شراء
- **SELL** 🔴 - توصية بيع
- **HOLD** 🟡 - توصية انتظار

## 📝 API

### Endpoints

```
GET /api/health          - فحص الحالة
GET /api/stats           - الإحصائيات
GET /api/stocks          - قائمة الأسهم
GET /api/stocks/{symbol} - معلومات سهم
GET /api/recommendations - التوصيات
GET /api/crypto          - العملات الرقمية
GET /api/gold            - أسعار الذهب
GET /api/sources         - مصادر البيانات
POST /api/sync/stocks    - مزامنة الأسهم
```

## 🔧 التكوين

### متغيرات البيئة

```env
TWELVE_DATA_API_KEY=your_key
EODHD_API_KEY=your_key
ALPHA_VANTAGE_API_KEY=your_key
PORT=8020
```

## 📖 التوثيق

- [API Reference](docs/API.md)
- [Data Sources](docs/DATA_SOURCES.md)
- [Deployment](docs/DEPLOYMENT.md)

## 📄 الترخيص

MIT License

## 👨‍💻 المساهمة

نرحب بالمساهمات! يرجى قراءة دليل المساهمة قبل إرسال Pull Request.
