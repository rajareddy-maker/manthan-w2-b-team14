"""Superset configuration for GridPulse. All secrets come from environment variables (.env)."""

import os

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg2://superset:{os.environ['SUPERSET_DB_PASSWORD']}"
    f"@{os.environ.get('WAREHOUSE_HOST', 'postgres')}:5432/superset"
)

# Single-node dev: simple in-process caches, no Celery/Redis.
CACHE_CONFIG = {"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300}
DATA_CACHE_CONFIG = CACHE_CONFIG
RATELIMIT_STORAGE_URI = "memory://"

FEATURE_FLAGS = {
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_RBAC": False,
}

# Local dev only — the UI is bound to 127.0.0.1 by docker-compose.
WTF_CSRF_ENABLED = True
TALISMAN_ENABLED = False
SQLLAB_TIMEOUT = 120
ROW_LIMIT = 50000
DEFAULT_TIMEZONE = "Asia/Kolkata"
