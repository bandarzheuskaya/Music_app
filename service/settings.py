from pathlib import Path
import json
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
CONFIG_PATH = BASE_DIR / "config.json"

load_dotenv(ENV_PATH)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

HOST = CONFIG["host"]
PORT = CONFIG["port"]
BUFFER_SIZE = CONFIG["buffer_size"]

UPLOAD_DIR = str(BASE_DIR / CONFIG["upload_dir"])
EXTERNAL_CACHE_DIR = str(BASE_DIR / CONFIG["external_cache_dir"])
COVER_DIR = str(BASE_DIR / CONFIG["cover_dir"])

DEFAULT_THEME = CONFIG["default_theme"]

DB_HOST = CONFIG["db"]["host"]
DB_PORT = CONFIG["db"]["port"]
DB_NAME = CONFIG["db"]["name"]
DB_USER = CONFIG["db"]["user"]
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

CORS_ALLOWED_ORIGIN = CONFIG["cors"]["allowed_origin"]

MAX_AUDIO_SIZE = CONFIG.get("max_audio_size", 100 * 1024 * 1024)
MAX_COVER_SIZE = CONFIG.get("max_cover_size", 5 * 1024 * 1024)
SESSION_LIFETIME_DAYS = CONFIG.get("session_lifetime_days", 7)

LOG_FILE = str(BASE_DIR / CONFIG.get("log_file", "app.log"))