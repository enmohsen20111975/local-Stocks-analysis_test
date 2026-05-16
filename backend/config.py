"""
Configuration - إعدادات النظام
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
PROJECT_DIR = BASE_DIR.parent
DB_PATH = PROJECT_DIR / "db" / "egx_investment.db"  # قاعدة البيانات الرئيسية

# VPS API
VPS_API_URL = os.getenv("VPS_API_URL", "http://72.61.137.86:8010")

# Server
HOST = os.getenv("PYTHON_ENGINE_HOST", "0.0.0.0")
PORT = int(os.getenv("PYTHON_ENGINE_PORT", "8020"))

# Learning Settings
DEFAULT_TARGET_WIN_RATE = 99.0
MAX_ITERATIONS = 100
MIN_CONFIDENCE_THRESHOLD = 50

# GPU Settings (for PyTorch/TensorFlow)
USE_GPU = os.getenv("USE_GPU", "auto")  # auto, true, false

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = BASE_DIR / "logs" / "engine.log"

# Database Settings
DB_POOL_SIZE = 5

# Model Storage
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

# Cache
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
