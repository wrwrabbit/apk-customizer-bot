import os

from dotenv import load_dotenv

load_dotenv()
if os.path.isfile(".env.postgres"):
    load_dotenv(".env.postgres")


def _env(name: str, default=None):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


NAME_LENGTH_LIMIT = 50
FILE_SIZE_LIMIT = 5 * 1024 * 1024
APP_ID_DOCS_URL = "https://developer.android.com/build/configure-app-module#set-application-id"
APP_ID_EXAMPLE = "org.some.app"
APP_NAME_REPLACEMENT_FOR_NOT_NORMALIZED = "app"
MAX_VERSION_CODE = 1000_000_000
APK_SEND_MAX_RETRY_COUNT = 5
APK_SEND_TIMEOUT_SEC = 600

# Telegram
if _env("DOCKER"):
    TELEGRAM_HOST = "tg_bot_api"
else:
    TELEGRAM_HOST = "127.0.0.1"
TOKEN = _env("TOKEN", "0000000000:asdasdasdasdadsasdadsasd")
SKIP_UPDATES = _env("SKIP_UPDATES", "False").lower() in ("true", "1", "t")
DELETE_MESSAGES_AFTER_SEC = int(_env("DELETE_MESSAGES_AFTER_SEC", "3600"))
DELETE_MESSAGES_WITHOUT_ORDERS_AFTER_SEC = int(_env("DELETE_MESSAGES_WITHOUT_ORDERS_AFTER_SEC", str(DELETE_MESSAGES_AFTER_SEC)))
DELETE_MESSAGES_WITH_FINISHED_ORDERS_AFTER_SEC = int(_env("DELETE_MESSAGES_WITH_FINISHED_ORDERS_AFTER_SEC", str(DELETE_MESSAGES_AFTER_SEC)))
ADMIN_CHAT_ID = int(_env("ADMIN_CHAT_ID", "0"))
ERROR_LOGS_CHAT_ID = int(_env("ERROR_LOGS_CHAT_ID", str(ADMIN_CHAT_ID)))
STATS_CHAT_ID = int(_env("STATS_CHAT_ID", str(ADMIN_CHAT_ID)))
STATS_PERIOD = int(_env("STATS_PERIOD", "86400"))
CONSIDER_WORKER_OFFLINE_AFTER_SEC = int(_env("CONSIDER_WORKER_OFFLINE_AFTER_SEC", "1800"))
MAX_QUEUE_LENGTH = int(_env("MAX_QUEUE_LENGTH", "5"))
CONSIDER_BUILD_STUCK_AFTER_SEC = int(_env("CONSIDER_BUILD_STUCK_AFTER_SEC", str(5 * 3600)))
# If not defined, the seed will not depend on the user id.
SALT_FOR_DERIVATION_RANDOM_SEED_FROM_USER_ID = _env("SALT_FOR_DERIVATION_RANDOM_SEED_FROM_USER_ID", None)
USER_ID_HASH_SALT = _env("USER_ID_HASH_SALT", None)
FAILED_BUILD_COUNT_ALLOWED = int(_env("FAILED_BUILD_COUNT_ALLOWED", "1"))
DELETE_USER_BUILD_STATS_AFTER_SEC = int(_env("DELETE_USER_BUILD_STATS_AFTER_SEC", "1"))
UPDATES_ALLOWED = _env("UPDATES_ALLOWED", "True").lower() in ("true", "1", "t")
SET_BOT_NAME_AND_DESCRIPTION = _env("SET_BOT_NAME_AND_DESCRIPTION", "True").lower() in ("true", "1", "t")
DELAY_BEFORE_UPDATE_ORDER_BUILD_SEC = int(_env("DELAY_BEFORE_UPDATE_ORDER_BUILD_SEC", "60"))

# Database
if _env("DOCKER"):
    DATABASE_HOST = "postgres"
else:
    DATABASE_HOST = "127.0.0.1"
DATABASE_PORT = 5432
DATABASE_DB = "postgres"
DATABASE_USER = _env("POSTGRES_USER", "user")
DATABASE_PASSWORD = _env("POSTGRES_PASSWORD", "password")

# Build data path
DATA_DIR = _env("DATA_DIR", "data")
TMP_DIR = _env("TMP_DIR", os.path.join(DATA_DIR, "tmp"))
MOCK_BUILD = _env("MOCK_BUILD", "False").lower() in ("true", "1", "t")
WORKER_CONTROLLER_HOST = _env("WORKER_CONTROLLER_HOST", "localhost")
WORKER_CHECK_INTERVAL_SEC = int(_env("WORKER_CHECK_INTERVAL_SEC", "1"))
MAX_CONSECUTIVE_BUILD_FAILURES = int(_env("MAX_CONSECUTIVE_BUILD_FAILURES", "3"))
WORKER_JWT = _env("WORKER_JWT", "")
KEYSTORE_PASSWORD = _env("KEYSTORE_PASSWORD", "")
BUILD_DOCKER_IMAGE_NAME = _env("BUILD_DOCKER_IMAGE_NAME", "masked-partisan-telegram-build")
ALLOW_BUILD_SOURCES_ONLY = _env("ALLOW_BUILD_SOURCES_ONLY", "True").lower() in ("true", "1", "t")
REPO_URL = _env("REPO_URL", "https://github.com/wrwrabbit/Partisan-Telegram-Android.git")
REPO_BRANCH = _env("REPO_BRANCH", "masking")
GITHUB_TOKEN = _env("GITHUB_TOKEN", "")

# Workers Controller
JWT_SECRET_KEY = _env("JWT_SECRET_KEY")
