# Deployment - النشر

## 🖥️ متطلبات السيرفر

### الحد الأدنى
- **CPU**: 1 core
- **RAM**: 512 MB
- **Storage**: 1 GB
- **Python**: 3.8+

### الموصى به
- **CPU**: 2+ cores
- **RAM**: 2 GB
- **Storage**: 5 GB
- **Python**: 3.10+

---

## 📦 التثبيت

### 1. تحضير السيرفر

```bash
# تحديث النظام
sudo apt update && sudo apt upgrade -y

# تثبيت Python
sudo apt install python3 python3-pip python3-venv -y

# تثبيت Git
sudo apt install git -y
```

### 2. استنساخ المشروع

```bash
# استنساخ
git clone https://github.com/enmohsen20111975/local-Stocks-analysis_test.git
cd local-Stocks-analysis_test

# إنشاء بيئة افتراضية
python3 -m venv venv
source venv/bin/activate

# تثبيت المتطلبات
pip install -r requirements.txt
```

### 3. التكوين

```bash
# نسخ ملف البيئة
cp .env.example .env

# تعديل الإعدادات
nano .env
```

---

## 🚀 التشغيل

### التشغيل المباشر

```bash
python backend/server.py
```

### باستخدام Systemd (Linux)

```bash
# إنشاء ملف الخدمة
sudo nano /etc/systemd/system/egx-data.service
```

**المحتوى:**
```ini
[Unit]
Description=EGX Data Engine
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/local-Stocks-analysis_test
ExecStart=/path/to/local-Stocks-analysis_test/venv/bin/python backend/server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# تفعيل الخدمة
sudo systemctl daemon-reload
sudo systemctl enable egx-data
sudo systemctl start egx-data
```

### باستخدام PM2 (Node.js Process Manager)

```bash
# تثبيت PM2
npm install -g pm2

# تشغيل
pm2 start backend/server.py --name egx-data --interpreter python3

# حفظ
pm2 save
pm2 startup
```

---

## 🔄 التحديث التلقائي

### باستخدام Cron

```bash
# فتح جدولة Cron
crontab -e

# إضافة مهمة تحديث يومية (الساعة 6 صباحاً)
0 6 * * * cd /path/to/project && source venv/bin/activate && python scripts/update_data.py
```

### باستخدام Scheduler

```python
# backend/scheduler.py
import schedule
import time
from backend.services.data_engine import DataEngine

def update_job():
    engine = DataEngine()
    engine.compute_all_indicators()
    print("Data updated!")

schedule.every().day.at("06:00").do(update_job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 🌐 Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8020;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## 🔒 الأمان

### 1. Firewall

```bash
# تثبيت UFW
sudo apt install ufw

# السماح بالمنافذ المطلوبة
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443

# تفعيل
sudo ufw enable
```

### 2. HTTPS (Let's Encrypt)

```bash
# تثبيت Certbot
sudo apt install certbot python3-certbot-nginx

# الحصول على شهادة
sudo certbot --nginx -d your-domain.com
```

---

## 📊 المراقبة

### السجلات

```bash
# عرض السجلات
tail -f logs/app.log

# أو عبر Systemd
journalctl -u egx-data -f
```

### Health Check

```bash
# فحص الحالة
curl http://localhost:8020/api/health
```

---

## 🔧 استكشاف الأخطاء

### المشكلة: السيرفر لا يعمل

```bash
# التحقق من المنفذ
lsof -i :8020

# التحقق من السجلات
tail -f logs/app.log
```

### المشكلة: قاعدة البيانات مقفلة

```bash
# إصلاح قاعدة البيانات
sqlite3 data/egx_investment.db "PRAGMA integrity_check;"
```

---

## 📈 الأداء

### تحسين الأداء

1. **استخدام Gunicorn** للإنتاج:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8020 backend.server:app
```

2. **تفعيل Cache**:
```python
# إضافة cache للبيانات المتكررة
from functools import lru_cache

@lru_cache(maxsize=100)
def get_stock_data(symbol):
    # ...
```

3. **تحسين قاعدة البيانات**:
```sql
-- إضافة فهارس
CREATE INDEX idx_stocks_ticker ON stocks(ticker);
CREATE INDEX idx_history_date ON stock_price_history(date);
```
