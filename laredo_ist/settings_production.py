"""
laredo_ist/settings_production.py
==================================
Production overrides for the Railway deployment.
Set DJANGO_SETTINGS_MODULE=laredo_ist.settings_production in Railway Variables.
"""

from .settings import *   # noqa
import os
import dj_database_url

# --- Security -------------------------------------------------------------
SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG      = False

_raw_hosts = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(",") if h.strip()]
ALLOWED_HOSTS += [".railway.app", ".up.railway.app"]

SESSION_COOKIE_SECURE       = True
CSRF_COOKIE_SECURE          = True
SECURE_PROXY_SSL_HEADER     = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Database -------------------------------------------------------------
# DATABASE_URL is injected by Railway at RUNTIME (not during build).
# During collectstatic (build phase) this block is skipped safely because
# Django doesn't need a database to collect static files.
_database_url = os.environ.get("DATABASE_URL")

if _database_url:
    DATABASES = {
        "default": dj_database_url.config(
            default=_database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
# If DATABASE_URL is absent (build phase), Django falls back to the
# SQLite default from settings.py — collectstatic succeeds, then
# the Procfile "release:" step runs migrate with the real DB.

# --- Logging --------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
