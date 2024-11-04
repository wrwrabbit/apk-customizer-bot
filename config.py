import os

from dotenv import load_dotenv

load_dotenv()
if os.path.isfile(".env.postgres"):
    load_dotenv(".env.postgres")


NAME_LENGTH_LIMIT = 50
FILE_SIZE_LIMIT = 20 * 1024 * 1024
APP_ID_DOCS_URL = "https://developer.android.com/build/configure-app-module#set-application-id"
APP_ID_EXAMPLE = "org.some.app"
APP_NAME_REPLACEMENT_FOR_NOT_NORMALIZED = "app"

# Telegram
if os.environ.get("DOCKER"):
    TELEGRAM_HOST = "tg_bot_api"
else:
    TELEGRAM_HOST = "127.0.0.1"
TOKEN = os.environ.get("TOKEN", "0000000000:asdasdasdasdadsasdadsasd")
SKIP_UPDATES = os.environ.get("SKIP_UPDATES", "False").lower() in ("true", "1", "t")
DELETE_MESSAGES_AFTER_SEC = int(os.environ.get("DELETE_MESSAGES_AFTER_SEC", "3600"))
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))
CONSIDER_WORKER_OFFLINE_AFTER_SEC = int(os.environ.get("CONSIDER_WORKER_OFFLINE_AFTER_SEC", "1800"))
# If not defined, the seed will not depend on the user id.
SALT_FOR_DERIVATION_RANDOM_SEED_FROM_USER_ID = os.environ.get("SALT_FOR_DERIVATION_RANDOM_SEED_FROM_USER_ID", None)
USER_ID_HASH_SALT = os.environ.get("USER_ID_HASH_SALT", None)
FAILED_BUILD_COUNT_ALLOWED = int(os.environ.get("FAILED_BUILD_COUNT_ALLOWED", "1"))
FLOOD_WAIT_INTERVALS_SEC = [int(interval) for interval in os.environ.get("FLOOD_WAIT_INTERVALS_SEC", "1").split(",")]
DELETE_USER_BUILD_STATS_AFTER_SEC = int(os.environ.get("RESET_USER_BUILD_STATS_AFTER_SEC", "1"))

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
PROJECT_ROOT_ABSPATH_ON_HOST = os.environ.get("PROJECT_ROOT_ABSPATH_ON_HOST", None)
MOCK_BUILD = os.environ.get("MOCK_BUILD", "False").lower() in ("true", "1", "t")
WORKER_CONTROLLER_HOST = os.environ.get("WORKER_CONTROLLER_HOST", "localhost")
WORKER_CHECK_INTERVAL_SEC = int(os.environ.get("WORKER_CHECK_INTERVAL_SEC", "1"))
WORKER_JWT = os.environ.get("WORKER_JWT", "")
KEYSTORE_PASSWORD = os.environ.get("KEYSTORE_PASSWORD", "")
BUILD_DOCKER_IMAGE_NAME = os.environ.get("BUILD_DOCKER_IMAGE_NAME", "masked-partisan-telegram-build")

# Workers Controller
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "")
