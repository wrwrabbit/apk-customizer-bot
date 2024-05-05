import os

from dotenv import load_dotenv

load_dotenv()


BUILD_SCRIPT = "scripts"
NAME_LENGTH_LIMIT = 50
FILE_SIZE_LIMIT = 20 * 1024 * 1024
APPID_DOCS_URL = "https://developer.android.com/build/configure-app-module#set-application-id"
APPID_EXAMPLE = "org.some.app"
APP_NAME_REPLACEMENT_FOR_NOT_NORMALIZED = "app"

# Telegram
if os.environ.get("DOCKER"):
    TELEGRAM_HOST = "tg_bot_api"
else:
    TELEGRAM_HOST = "127.0.0.1"
TOKEN = os.environ.get("TOKEN", "0000000000:asdasdasdasdadsasdadsasd")
SKIP_UPDATES = os.environ.get("SKIP_UPDATES", "False").lower() in ("true", "1", "t")
DELETE_MESSAGES_AFTER_SEC = int(os.environ.get("DELETE_MESSAGES_AFTER_SEC", "3600"))

# Database
if os.environ.get("DOCKER"):
    DATABASE_HOST = "postgres"
else:
    DATABASE_HOST = "127.0.0.1"
DATABASE_PORT = 5432
DATABASE_DB = "postgres"
DATABASE_USER = os.environ.get("POSTGRES_USER", "user")
DATABASE_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "password")

# Build data path
DATA_DIR = os.environ.get("DATA_DIR", "data")
TMP_DIR = os.environ.get("TMP_DIR", os.path.join(DATA_DIR, "tmp"))
MOCK_BUILD = os.environ.get("MOCK_BUILD", "False").lower() in ("true", "1", "t")
