#!/bin/bash

# EGX Python Engine - Run Script
# ================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}   EGX Python Analysis Engine${NC}"
echo -e "${BLUE}       Version 1.3.0${NC}"
echo -e "${BLUE}=======================================${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python found: $(python3 --version)${NC}"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create necessary directories
mkdir -p data/models logs

# Set environment variables
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

# Default port
PORT=${PORT:-8010}
HOST=${HOST:-0.0.0.0}

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}No .env file found, creating default...${NC}"
    cat > .env << EOF
# EGX Python Engine Configuration
APP_NAME=EGX Analysis Engine
APP_VERSION=1.3.0
DEBUG=false
HOST=0.0.0.0
PORT=8010
REQUIRE_API_KEY=false
API_KEY=
EOF
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Starting EGX Unified Backend Server${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "  Host: ${BLUE}${HOST}${NC}"
echo -e "  Port: ${BLUE}${PORT}${NC}"
echo -e "  API Docs: ${BLUE}http://localhost:${PORT}/docs${NC}"
echo -e "  ReDoc: ${BLUE}http://localhost:${PORT}/redoc${NC}"
echo ""

# Run the server
python unified_backend.py
