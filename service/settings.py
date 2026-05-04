import json
import os
from dotenv import load_dotenv

load_dotenv()

with open("../config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

HOST = CONFIG["host"]
PORT = CONFIG["port"]
BUFFER_SIZE = CONFIG["buffer_size"]

UPLOAD_DIR = CONFIG["upload_dir"]
EXTERNAL_CACHE_DIR = CONFIG["external_cache_dir"]

DEFAULT_THEME = CONFIG["default_theme"]

DB_HOST = CONFIG["db"]["host"]
DB_PORT = CONFIG["db"]["port"]
DB_NAME = CONFIG["db"]["name"]
DB_USER = CONFIG["db"]["user"]
DB_PASSWORD = os.getenv("DB_PASSWORD", "")