"""
laredo_ist/settings_production.py
==================================
Production overrides for Render deployment.
Set DJANGO_SETTINGS_MODULE=laredo_ist.settings_production in environment variables.
"""

from .settings import *   # noqa
import os
import dj_database_url

# --- Security -------------------------------------------------------------
SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG      = False

_raw_hosts = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(",") if h.strip()]
ALLOWED_HOSTS += [".onrender.com"]   # Render's domain

SESSION_COOKIE_SECURE   = True
CSRF_COOKIE_SECURE      = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Database (Render PostgreSQL) -----------------------------------------
_database_url = os.environ.get("DATABASE_URL")

if _database_url:
    DATABASES = {
        "default": dj_database_url.config(
            default=_database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }

# --- Logging --------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}