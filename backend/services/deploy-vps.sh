#!/bin/bash
#
# Deploy EGX Investment App to Hostinger VPS (KVM 2)
# ================================================
# This script sets up the complete environment for:
# - Next.js app (production build)
# - Python data fetcher (background service)
#
# Prerequisites:
# - Ubuntu 22.04 or similar
# - Root or sudo access
# - Domain pointing to VPS IP (optional)
#
# Usage:
#   chmod +x deploy-vps.sh
#   ./deploy-vps.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}EGX Investment App - VPS Deploy${NC}"
echo -e "${GREEN}================================${NC}"

# Configuration
APP_DIR="/home/z/invest/app"
DB_DIR="$APP_DIR/db"
LOG_DIR="/var/log/egx-invest"
DOMAIN="${DOMAIN:-invest.example.com}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Please run as root or with sudo${NC}"
    exit 1
fi

# Step 1: Install dependencies
echo -e "\n${YELLOW}[1/8] Installing system dependencies...${NC}"
apt-get update
apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    certbot \
    python3-certbot-nginx \
    sqlite3

# Step 2: Install Node.js
echo -e "\n${YELLOW}[2/8] Installing Node.js 20...${NC}"
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi
node --version
npm --version

# Step 3: Install Bun
echo -e "\n${YELLOW}[3/8] Installing Bun...${NC}"
if ! command -v bun &> /dev/null; then
    curl -fsSL https://bun.sh/install | bash
    export PATH="$HOME/.bun/bin:$PATH"
fi
bun --version

# Step 4: Create app directory
echo -e "\n${YELLOW}[4/8] Creating app directory...${NC}"
mkdir -p "$APP_DIR"
mkdir -p "$DB_DIR"
mkdir -p "$LOG_DIR"

# Step 5: Setup Python virtual environment
echo -e "\n${YELLOW}[5/8] Setting up Python environment...${NC}"
python3 -m venv "$APP_DIR/venv"
source "$APP_DIR/venv/bin/activate"
pip install --upgrade pip
pip install tradingview-ta flask flask-cors schedule pandas numpy
deactivate

# Step 6: Copy application files (if present)
echo -e "\n${YELLOW}[6/8] Copying application files...${NC}"
# This assumes you've uploaded the app files to /tmp/egx-invest
if [ -d "/tmp/egx-invest" ]; then
    cp -r /tmp/egx-invest/* "$APP_DIR/"
    echo "Application files copied"
else
    echo -e "${YELLOW}Warning: /tmp/egx-invest not found. Please copy files manually.${NC}"
fi

# Step 7: Setup systemd services
echo -e "\n${YELLOW}[7/8] Setting up systemd services...${NC}"

# Create Next.js service
cat > /etc/systemd/system/egx-nextjs.service << 'EOF'
[Unit]
Description=EGX Investment App - Next.js
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/z/invest/app
ExecStart=/usr/bin/bun run start
Restart=always
RestartSec=10
Environment=NODE_ENV=production
Environment=PORT=3000

[Install]
WantedBy=multi-user.target
EOF

# Create Python data fetcher service
cat > /etc/systemd/system/egx-fetcher.service << 'EOF'
[Unit]
Description=EGX Investment App - Data Fetcher
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/z/invest/app/vps-service
ExecStart=/home/z/invest/app/venv/bin/python3 egx_data_fetcher_unified.py --daemon
Restart=always
RestartSec=30
Environment=DATABASE_PATH=/home/z/invest/app/db/egx_investment.db

[Install]
WantedBy=multi-user.target
EOF

# Enable services
systemctl daemon-reload
systemctl enable egx-nextjs
systemctl enable egx-fetcher

# Step 8: Setup Nginx reverse proxy
echo -e "\n${YELLOW}[8/8] Setting up Nginx...${NC}"
cat > /etc/nginx/sites-available/egx-invest << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/egx-invest /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# Setup SSL (optional)
echo -e "\n${YELLOW}Setup SSL with: certbot --nginx -d $DOMAIN${NC}"

# Print summary
echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "App directory: $APP_DIR"
echo "Database directory: $DB_DIR"
echo "Logs directory: $LOG_DIR"
echo ""
echo "Services:"
echo "  - egx-nextjs (Next.js app on port 3000)"
echo "  - egx-fetcher (Python data fetcher)"
echo ""
echo "Commands:"
echo "  Start:   systemctl start egx-nextjs egx-fetcher"
echo "  Stop:    systemctl stop egx-nextjs egx-fetcher"
echo "  Status:  systemctl status egx-nextjs egx-fetcher"
echo "  Logs:    journalctl -u egx-nextjs -f"
echo "           journalctl -u egx-fetcher -f"
echo ""
echo "Nginx: http://$DOMAIN"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Upload your app files to $APP_DIR"
echo "2. Copy database to $DB_DIR/egx_investment.db"
echo "3. Run: cd $APP_DIR && bun install && bun run build"
echo "4. Start services: systemctl start egx-nextjs egx-fetcher"
echo "5. Setup SSL: certbot --nginx -d $DOMAIN"
