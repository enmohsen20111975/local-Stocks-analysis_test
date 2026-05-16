#!/bin/bash
# EGX API Service - Deployment Script
# Run this on your VPS to deploy the service

set -e

echo "=============================================="
echo "EGX Data API Service - Deployment"
echo "=============================================="

# Configuration
SERVICE_DIR="/opt/egx-api"
SERVICE_USER="root"
PORT="${PORT:-5000}"

# Create service directory
echo "Creating service directory..."
mkdir -p $SERVICE_DIR

# Copy files
echo "Copying service files..."
cp egx_api_service.py $SERVICE_DIR/
cp requirements.txt $SERVICE_DIR/

# Install dependencies
echo "Installing Python dependencies..."
cd $SERVICE_DIR
pip3 install -r requirements.txt

# Also try to install egxpy if available
pip3 install egxpy 2>/dev/null || echo "egxpy not on PyPI, using local if available"

# Create systemd service
echo "Creating systemd service..."
cat > /etc/systemd/system/egx-api.service << EOF
[Unit]
Description=EGX Data API Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$SERVICE_DIR
ExecStart=/usr/bin/python3 $SERVICE_DIR/egx_api_service.py
Restart=always
RestartSec=10
Environment=PORT=$PORT

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
echo "Enabling and starting service..."
systemctl daemon-reload
systemctl enable egx-api.service
systemctl restart egx-api.service

# Check status
echo ""
echo "=============================================="
echo "Service Status:"
echo "=============================================="
systemctl status egx-api.service --no-pager

echo ""
echo "=============================================="
echo "Deployment Complete!"
echo "=============================================="
echo "API Endpoints:"
echo "  Health:  http://YOUR_VPS_IP:$PORT/health"
echo "  Stocks:  http://YOUR_VPS_IP:$PORT/api/stocks"
echo "  Indices: http://YOUR_VPS_IP:$PORT/api/indices"
echo "  Gold:    http://YOUR_VPS_IP:$PORT/api/gold"
echo "  Sync:    POST http://YOUR_VPS_IP:$PORT/api/sync"
echo ""
echo "To check logs: journalctl -u egx-api -f"
echo "To restart:    systemctl restart egx-api"
echo "=============================================="
