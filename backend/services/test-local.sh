#!/bin/bash
#
# Test EGX Data Fetcher Locally
# =============================
# Run this script to test the data fetcher before deploying to VPS
#

set -e

echo "================================"
echo "EGX Data Fetcher - Local Test"
echo "================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found"
    exit 1
fi

# Check if tradingview-ta is installed
if ! python3 -c "import tradingview_ta" 2>/dev/null; then
    echo "Installing tradingview-ta..."
    pip install tradingview-ta
fi

# Get database path
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DB_PATH="$PROJECT_DIR/db/egx_investment.db"

if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database not found at $DB_PATH"
    exit 1
fi

echo "Database: $DB_PATH"
echo ""

# Run the fetcher
echo "Running data fetcher..."
cd "$SCRIPT_DIR"
python3 egx_data_fetcher_unified.py --once --db "$DB_PATH"

echo ""
echo "Test complete!"
