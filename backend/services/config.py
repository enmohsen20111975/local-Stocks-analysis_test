#!/usr/bin/env python3
"""
Unified Configuration for All Python Services
==============================================

This module provides a SINGLE source of truth for all configuration
across Python backend services. All services should import from this file.

Usage:
    from config import DATABASE_PATH, API_PORT, get_db_connection

Environment Variables:
    DATABASE_PATH - Override default database path
    API_PORT - Override default API port (default: 8010)
    LOG_LEVEL - Set logging level (default: INFO)

Last Updated: 2025-05-15
"""

import os
import sys
from pathlib import Path

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Possible database locations (in order of priority)
_DB_SEARCH_PATHS = [
    # Environment variable (highest priority)
    os.environ.get('DATABASE_PATH', ''),
    # VPS - Next.js project location (PRIMARY for production)
    '/root/GLMinvestment/db/egx_investment.db',
    # Development environment
    '/home/z/my-project/GLMinvestment/db/egx_investment.db',
    # Relative path (for local development)
    os.path.join(os.path.dirname(__file__), '..', 'db', 'egx_investment.db'),
    # Old paths (deprecated - will be removed)
    '/root/egxpy_service/data/egx_investment.db',
    '/home/z/invest/app/db/egx_investment.db',
]


def find_database() -> str:
    """
    Find the database file, searching multiple possible locations.
    
    Returns:
        str: Path to the database file
        
    Raises:
        FileNotFoundError: If no database file is found
    """
    # First check environment variable
    env_path = os.environ.get('DATABASE_PATH', '')
    if env_path and os.path.exists(env_path):
        return env_path
    
    # Then search known locations
    for path in _DB_SEARCH_PATHS:
        if path and os.path.exists(path):
            print(f"[CONFIG] Found database at: {path}")
            return path
    
    # If not found, return the expected VPS path
    default_path = '/root/GLMinvestment/db/egx_investment.db'
    print(f"[CONFIG] Database not found, using default: {default_path}")
    print(f"[CONFIG] Searched paths: {[p for p in _DB_SEARCH_PATHS if p]}")
    return default_path


# Primary database path - use this everywhere
DATABASE_PATH = find_database()

# ============================================================================
# API CONFIGURATION
# ============================================================================

API_PORT = int(os.environ.get('PORT', 8010))
API_HOST = os.environ.get('API_HOST', '0.0.0.0')
DEBUG_MODE = os.environ.get('DEBUG', 'false').lower() == 'true'

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# ============================================================================
# VPS-SPECIFIC PATHS
# ============================================================================

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Database directory
DB_DIR = PROJECT_ROOT / 'db'

# Logs directory
LOGS_DIR = PROJECT_ROOT / 'logs'

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

import sqlite3
from contextlib import contextmanager
from typing import Generator


@contextmanager
def get_db_connection(db_path: str = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Get a database connection with context manager.
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM stocks")
    
    Args:
        db_path: Optional override for database path
        
    Yields:
        sqlite3.Connection: Database connection
    """
    path = db_path or DATABASE_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def verify_database() -> dict:
    """
    Verify database connection and return stats.
    
    Returns:
        dict: Database statistics and health info
    """
    result = {
        'path': DATABASE_PATH,
        'exists': os.path.exists(DATABASE_PATH),
        'connected': False,
        'stocks_count': 0,
        'history_count': 0,
        'tables': []
    }
    
    if not result['exists']:
        result['error'] = 'Database file not found'
        return result
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            result['tables'] = [row[0] for row in cursor.fetchall()]
            
            # Get stocks count
            cursor.execute("SELECT COUNT(*) FROM stocks")
            result['stocks_count'] = cursor.fetchone()[0]
            
            # Get history count
            cursor.execute("SELECT COUNT(*) FROM stock_price_history")
            result['history_count'] = cursor.fetchone()[0]
            
            result['connected'] = True
            
    except Exception as e:
        result['error'] = str(e)
    
    return result


def print_config():
    """Print current configuration."""
    print("\n" + "=" * 60)
    print("PYTHON BACKEND CONFIGURATION")
    print("=" * 60)
    print(f"Database Path:  {DATABASE_PATH}")
    print(f"Database Exists: {os.path.exists(DATABASE_PATH)}")
    print(f"API Port:       {API_PORT}")
    print(f"API Host:       {API_HOST}")
    print(f"Debug Mode:     {DEBUG_MODE}")
    print(f"Project Root:   {PROJECT_ROOT}")
    print("=" * 60 + "\n")


# Print configuration when run directly
if __name__ == '__main__':
    print_config()
    print("Database Verification:")
    stats = verify_database()
    for key, value in stats.items():
        print(f"  {key}: {value}")
