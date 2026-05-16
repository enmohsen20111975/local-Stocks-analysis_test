#!/bin/bash
# EGX Unified Data Service - Start Script
# Usage: ./start_service.sh

# Configuration
PORT=${PORT:-8010}
DATABASE_PATH=${DATABASE_PATH:-"/opt/egx-api/data/egx_unified.db"}
LOG_FILE="/var/log/egx-service.log"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}EGX Unified Data Service${NC}"
echo "================================"
echo "Port: $PORT"
echo "Database: $DATABASE_PATH"
echo ""

# Create data directory if not exists
mkdir -p $(dirname $DATABASE_PATH)

# Activate virtual environment if exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python3 not found${NC}"
    exit 1
fi

# Install dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"
pip3 install -q flask flask-cors tradingview-ta numpy 2>/dev/null

# Initialize database
echo -e "${YELLOW}Initializing database...${NC}"
python3 egx_unified_service.py --init-db

# Start service
echo -e "${GREEN}Starting service on port $PORT...${NC}"
echo ""

if [ "$1" = "--daemon" ]; then
    # Run as daemon with gunicorn
    gunicorn --bind 0.0.0.0:$PORT --workers 2 --daemon --access-logfile $LOG_FILE --error-logfile $LOG_FILE egx_unified_service:app
    echo -e "${GREEN}Service started as daemon${NC}"
    echo "Logs: $LOG_FILE"
else
    # Run in foreground
    python3 egx_unified_service.py --port $PORT
fi
