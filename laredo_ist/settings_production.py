"""
laredo_ist/settings_production.py
==================================
Production overrides for the Railway deployment.

Railway injects these environment variables automatically:
  DATABASE_URL  — PostgreSQL connection string (from the Postgres plugin)

You must add these manually in the Railway dashboard → Variables:
  SECRET_KEY        — generate with: python -c "import secrets; print(secrets.token_hex(50))"
  ALLOWED_HOSTS     — your Railway domain, e.g. laredo-ist.up.railway.app
  DJANGO_SETTINGS_MODULE = laredo_ist.settings_production
"""

from .settings import *   # noqa: import all base settings first
import os
import dj_database_url

# --- Security -------------------------------------------------------------
SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG      = False

# Accept the Railway-provided domain plus any custom domain you attach
_raw_hosts = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(",") if h.strip()]
ALLOWED_HOSTS += [".railway.app", ".up.railway.app"]

# Secure cookies over HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE    = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Database (Railway Postgres) ------------------------------------------
# DATABASE_URL is injected automatically by the Railway PostgreSQL plugin.
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# --- Logging --------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}
