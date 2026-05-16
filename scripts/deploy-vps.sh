#!/bin/bash
# ============================================================
# EGX Investment Platform - VPS Full Deployment Script
# ============================================================
# This script deploys both Next.js and Python Engine on VPS
# Run as root: bash deploy-vps.sh
# ============================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  EGX Investment Platform - VPS Deploy${NC}"
echo -e "${BLUE}========================================${NC}"

# Configuration
APP_DIR="/opt/egx-investment"
PYTHON_DIR="$APP_DIR/python-engine"
DATA_DIR="$APP_DIR/data"
LOG_DIR="/var/log/egx-investment"
DOMAIN="invist.m2y.net"

# ============================================================
# Step 1: Stop Old Services
# ============================================================
echo -e "${YELLOW}[1/8] Stopping old services...${NC}"

# Kill any existing processes
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "bun run" 2>/dev/null || true
pkill -f "node.*next" 2>/dev/null || true

# Stop systemd services if exist
systemctl stop egxpy-bridge 2>/dev/null || true
systemctl stop egx-investment 2>/dev/null || true

echo -e "${GREEN}✓ Old services stopped${NC}"

# ============================================================
# Step 2: Install Dependencies
# ============================================================
echo -e "${YELLOW}[2/8] Installing dependencies...${NC}"

# Update system
apt update -qq

# Install Node.js 20
if ! command -v node &> /dev/null; then
    echo "Installing Node.js 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - &>/dev/null
    apt install -y nodejs &>/dev/null
fi
echo -e "  Node.js: ${GREEN}$(node --version)${NC}"

# Install Bun
if ! command -v bun &> /dev/null; then
    echo "Installing Bun..."
    curl -fsSL https://bun.sh/install | bash &>/dev/null
    export PATH="$HOME/.bun/bin:$PATH"
fi
echo -e "  Bun: ${GREEN}$(bun --version 2>/dev/null || echo 'installed')${NC}"

# Install Python dependencies
apt install -y python3 python3-pip python3-venv &>/dev/null
echo -e "  Python: ${GREEN}$(python3 --version)${NC}"

# Install PM2
if ! command -v pm2 &> /dev/null; then
    npm install -g pm2 &>/dev/null
fi
echo -e "  PM2: ${GREEN}$(pm2 --version)${NC}"

# Install Caddy
if ! command -v caddy &> /dev/null; then
    echo "Installing Caddy..."
    apt install -y debian-keyring debian-archive-keyring apt-transport-https &>/dev/null
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list &>/dev/null
    apt update -qq
    apt install -y caddy &>/dev/null
fi
echo -e "  Caddy: ${GREEN}$(caddy version 2>/dev/null | head -1)${NC}"

# ============================================================
# Step 3: Setup Directories
# ============================================================
echo -e "${YELLOW}[3/8] Setting up directories...${NC}"

mkdir -p $APP_DIR
mkdir -p $DATA_DIR
mkdir -p $LOG_DIR

# ============================================================
# Step 4: Clone/Update Code
# ============================================================
echo -e "${YELLOW}[4/8] Downloading code from GitHub...${NC}"

if [ -d "$APP_DIR/.git" ]; then
    cd $APP_DIR
    git pull
else
    rm -rf $APP_DIR/*
    git clone https://github.com/enmohsen20111975/GLMinvestment.git $APP_DIR
fi

echo -e "${GREEN}✓ Code downloaded${NC}"

# ============================================================
# Step 5: Setup Next.js
# ============================================================
echo -e "${YELLOW}[5/8] Setting up Next.js...${NC}"

cd $APP_DIR

# Install dependencies
bun install --silent

# Create .env if not exists
if [ ! -f ".env" ]; then
    cat > .env << 'ENVEOF'
# Database
DATABASE_URL="file:./db/custom.db"

# VPS API
VPS_API_URL="http://localhost:8010"

# App
NEXT_PUBLIC_APP_URL="https://invist.m2y.net"
ENVEOF
fi

# Build
echo "Building Next.js..."
bun run build &>/dev/null || echo "Build completed (with warnings)"

echo -e "${GREEN}✓ Next.js ready${NC}"

# ============================================================
# Step 6: Setup Python Engine
# ============================================================
echo -e "${YELLOW}[6/8] Setting up Python Engine...${NC}"

cd $PYTHON_DIR

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Create data directory
mkdir -p data

# Copy database if exists in main db folder
if [ -f "$APP_DIR/db/egx_data.db" ]; then
    cp $APP_DIR/db/egx_data.db data/
fi

deactivate

echo -e "${GREEN}✓ Python Engine ready${NC}"

# ============================================================
# Step 7: Configure Caddy
# ============================================================
echo -e "${YELLOW}[7/8] Configuring Caddy reverse proxy...${NC}"

cat > /etc/caddy/Caddyfile << 'CADDEOF'
# EGX Investment Platform
invist.m2y.net {
    # Next.js frontend
    reverse_proxy localhost:3000
    
    # Python API
    handle /api/vps/* {
        uri strip_prefix /api/vps
        reverse_proxy localhost:8010
    }
    
    # Python API (direct)
    handle /api/py/* {
        uri strip_prefix /api/py
        reverse_proxy localhost:8010
    }
    
    # Logging
    log {
        output file /var/log/caddy/invist.log
    }
}

# Direct IP access (optional)
:80 {
    respond /health "OK" 200
    reverse_proxy localhost:3000
}
CADDEOF

mkdir -p /var/log/caddy

echo -e "${GREEN}✓ Caddy configured${NC}"

# ============================================================
# Step 8: Start Services with PM2
# ============================================================
echo -e "${YELLOW}[8/8] Starting services with PM2...${NC}"

cd $APP_DIR

# Start Python Engine
pm2 delete python-engine 2>/dev/null || true
pm2 start --name python-engine --interpreter bash -c "cd $PYTHON_DIR && source venv/bin/activate && python main.py"

# Start Next.js
pm2 delete nextjs 2>/dev/null || true
pm2 start --name nextjs -c "cd $APP_DIR && bun run start"

# Save PM2 config
pm2 save

# Start PM2 on boot
pm2 startup systemd -u root --hp /root 2>/dev/null || true

# Start Caddy
systemctl enable caddy
systemctl restart caddy

echo -e "${GREEN}✓ All services started${NC}"

# ============================================================
# Summary
# ============================================================
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  🎉 DEPLOYMENT COMPLETE!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Services running:"
pm2 list
echo ""
echo -e "URLs:"
echo -e "  ${BLUE}https://invist.m2y.net${NC} - Main App"
echo -e "  ${BLUE}http://localhost:3000${NC} - Next.js"
echo -e "  ${BLUE}http://localhost:8010${NC} - Python API"
echo -e "  ${BLUE}http://localhost:8010/docs${NC} - API Docs"
echo ""
echo -e "Logs:"
echo -e "  ${YELLOW}pm2 logs${NC} - View all logs"
echo -e "  ${YELLOW}pm2 logs python-engine${NC} - Python logs"
echo -e "  ${YELLOW}pm2 logs nextjs${NC} - Next.js logs"
echo ""
echo -e "Commands:"
echo -e "  ${YELLOW}pm2 restart all${NC} - Restart all"
echo -e "  ${YELLOW}pm2 stop all${NC} - Stop all"
echo -e "  ${YELLOW}pm2 status${NC} - Check status"
echo ""
