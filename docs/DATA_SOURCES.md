# Data Sources - مصادر البيانات

## 📊 نظرة عامة

يدعم النظام مصادر بيانات متعددة لضمان توفر البيانات بأعلى جودة ممكنة.

## 🔌 المصادر المدعومة

### 1. الموقع الحي (Primary)

| المعلومة | القيمة |
|----------|--------|
| **الاسم** | invist.m2y.net |
| **النوع** | أسهم EGX |
| **الحد** | غير محدود |
| **التحديث** | يومي |

**البيانات المتاحة:**
- أسعار الأسهم الحالية
- البيانات التاريخية
- معلومات الشركات

---

### 2. Twelve Data

| المعلومة | القيمة |
|----------|--------|
| **الاسم** | Twelve Data |
| **URL** | https://api.twelvedata.com |
| **النوع** | أسهم، عملات، فوركس |
| **الحد المجاني** | 800 طلب/يوم |
| **API Key** | مطلوب |

**الميزات:**
- بيانات لحظية
- بيانات تاريخية
- مؤشرات فنية

**الاستخدام:**
```python
from backend.services.enhanced_data_sources import EnhancedDataSources

ds = EnhancedDataSources()
data = ds.fetch_from_twelvedata("COMI", "EGX")
```

---

### 3. EODHD

| المعلومة | القيمة |
|----------|--------|
| **الاسم** | EOD Historical Data |
| **URL** | https://eodhistoricaldata.com |
| **النوع** | أسهم، ETF، مؤشرات |
| **الحد المجاني** | 20 طلب/يوم |
| **API Key** | مطلوب |

**الميزات:**
- بيانات نهاية اليوم
- بيانات فنية
- أرباح وتوزيعات

---

### 4. CoinGecko

| المعلومة | القيمة |
|----------|--------|
| **الاسم** | CoinGecko |
| **URL** | https://api.coingecko.com |
| **النوع** | عملات رقمية |
| **الحد المجاني** | 50 طلب/دقيقة |
| **API Key** | غير مطلوب |

**الميزات:**
- أكثر من 10,000 عملة
- بيانات السوق
- بيانات تاريخية

**الاستخدام:**
```python
crypto = ds.fetch_crypto_from_coingecko(50)
```

---

### 5. Alpha Vantage

| المعلومة | القيمة |
|----------|--------|
| **الاسم** | Alpha Vantage |
| **URL** | https://www.alphavantage.co |
| **النوع** | أسهم، عملات، فوركس |
| **الحد المجاني** | 25 طلب/يوم |
| **API Key** | مطلوب |

**الميزات:**
- بيانات الأسهم العالمية
- المؤشرات الفنية
- بيانات الفوركس

---

### 6. Yahoo Finance

| المعلومة | القيمة |
|----------|--------|
| **الاسم** | Yahoo Finance |
| **URL** | https://finance.yahoo.com |
| **النوع** | أسهم، عملات، ETF |
| **الحد** | تقريباً غير محدود |
| **API Key** | غير مطلوب |

---

## 🔄 ترتيب الأولوية

عند جلب البيانات، يتم المحاولة بالترتيب التالي:

1. **الموقع الحي** - الأساسي للأسهم المصرية
2. **Twelve Data** - بديل قوي
3. **EODHD** - بديل ثانوي
4. **Alpha Vantage** - بديل أخير

## 🔑 إعداد API Keys

أنشئ ملف `.env`:

```env
TWELVE_DATA_API_KEY=your_twelvedata_key
EODHD_API_KEY=your_eodhd_key
ALPHA_VANTAGE_API_KEY=your_alphavantage_key
COINGECKO_API_KEY=your_coingecko_key  # اختياري
```

## 📊 مقارنة المصادر

| المصدر | الأسهم | العملات | التاريخ | اللحظي | المجاني |
|--------|--------|---------|---------|--------|---------|
| الموقع الحي | ✅ EGX | ❌ | ✅ | ✅ | ✅ غير محدود |
| Twelve Data | ✅ عالمي | ✅ | ✅ | ✅ | 800/يوم |
| EODHD | ✅ عالمي | ❌ | ✅ | ❌ | 20/يوم |
| CoinGecko | ❌ | ✅ | ✅ | ✅ | 50/دقيقة |
| Alpha Vantage | ✅ عالمي | ✅ | ✅ | ❌ | 25/يوم |
| Yahoo Finance | ✅ عالمي | ✅ | ✅ | ✅ | تقريباً غير محدود |

## 🚀 الحصول على API Keys

### Twelve Data
1. زيارة https://twelvedata.com
2. إنشاء حساب مجاني
3. نسخ API Key من Dashboard

### EODHD
1. زيارة https://eodhistoricaldata.com
2. إنشاء حساب مجاني
3. نسخ API Token

### Alpha Vantage
1. زيارة https://www.alphavantage.co/support/#api-key
2. إدخال البريد الإلكتروني
3. استلام API Key
