"""
laredo_ist/settings.py
======================
Base settings shared by local development and production.
Environment-specific overrides live in settings_production.py.

Railway sets DJANGO_SETTINGS_MODULE=laredo_ist.settings_production automatically
via the environment variable you add in the Railway dashboard.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Security (overridden in production via env var) ----------------------
SECRET_KEY = 'django-insecure-dev-key-replace-in-production'
DEBUG      = True
ALLOWED_HOSTS = ['*']

# --- Applications ---------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tickets',
    'axes',
]

# --- Middleware ------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # serves static files in prod
    'django.contrib.sessions.middleware.SessionMiddleware',
    'axes.middleware.AxesMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'laredo_ist.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'laredo_ist.wsgi.application'

# --- Database (SQLite for local dev; overridden in production) ------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# --- Password validation --------------------------------------------------
# ── Authentication backends (axes needs its own backend) ──────────────────
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Internationalisation --------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'America/Chicago'   # Laredo, TX
USE_I18N = True
USE_TZ   = True

# --- Static files ---------------------------------------------------------
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'   # collectstatic target

# WhiteNoise compression + caching for production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Media files (user uploads) -------------------------------------------
MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Allowed attachment types and max size (5MB)
ATTACHMENT_ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
ATTACHMENT_MAX_SIZE_MB    = 5

# --- Session --------------------------------------------------------------
SESSION_COOKIE_AGE    = 28800   # 8 hours
SESSION_COOKIE_SECURE = False   # set True in production (HTTPS only)


# ── SECURITY HARDENING ────────────────────────────────────────────────────

# Prevent browsers from sniffing content types
SECURE_CONTENT_TYPE_NOSNIFF = True

# Enable browser XSS filter (legacy browsers)
SECURE_BROWSER_XSS_FILTER = True

# Prevent the site from being embedded in iframes (clickjacking)
X_FRAME_OPTIONS = "DENY"

# Session cookie hardening
SESSION_COOKIE_HTTPONLY = True    # JS cannot read the session cookie
SESSION_COOKIE_SAMESITE = "Lax"  # Prevents CSRF via cross-site requests

# ── DJANGO-AXES (login rate limiting) ─────────────────────────────────────
AXES_FAILURE_LIMIT       = 5      # lock after 5 failed attempts
AXES_COOLOFF_TIME        = 1      # locked for 1 hour
AXES_LOCKOUT_PARAMETERS  = ["username", "ip_address"]  # lock by ID + IP
AXES_RESET_ON_SUCCESS    = True   # clear failure count on successful login
AXES_LOCKOUT_TEMPLATE    = None   # use our own error message in login view
AXES_USERNAME_FORM_FIELD = "employee_id"  # our field name
AXES_ENABLED             = True