#!/bin/bash
# EGX Unified Data Service - Local Test Script
# Tests the service locally without VPS

echo "=========================================="
echo "EGX Unified Data Service - Local Test"
echo "=========================================="

# Set local database path
export DATABASE_PATH="./test_data/egx_test.db"
export PORT=8010

# Create test directory
mkdir -p ./test_data

# Install minimal dependencies
echo "Installing dependencies..."
pip3 install -q flask flask-cors tradingview-ta numpy 2>/dev/null

# Initialize database
echo "Initializing database..."
python3 egx_unified_service.py --init-db

# Start service in background
echo "Starting service on port $PORT..."
python3 egx_unified_service.py --port $PORT &
SERVICE_PID=$!

# Wait for service to start
sleep 3

# Test endpoints
echo ""
echo "Testing endpoints..."
echo ""

# Health check
echo "1. Health Check:"
curl -s http://localhost:$PORT/health | python3 -m json.tool

# Get stocks
echo ""
echo "2. Get Stocks:"
curl -s "http://localhost:$PORT/api/stocks?limit=5" | python3 -m json.tool

# Market overview
echo ""
echo "3. Market Overview:"
curl -s http://localhost:$PORT/api/market/overview | python3 -m json.tool

# Sync test (popular stocks only)
echo ""
echo "4. Sync Test (5 stocks):"
curl -s -X POST -H "Content-Type: application/json" \
    -d '{"symbols": ["COMI", "HRHO", "ETEL", "SWDY", "TMGH"]}' \
    http://localhost:$PORT/api/sync | python3 -m json.tool

# Export data
echo ""
echo "5. Export Data:"
curl -s http://localhost:$PORT/api/data/export | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Success: {d[\"success\"]}, Stocks: {d[\"counts\"][\"stocks\"]}')"

# Cleanup
echo ""
echo "Stopping service..."
kill $SERVICE_PID 2>/dev/null

echo ""
echo "Test completed!"
echo "Test database: $DATABASE_PATH"
