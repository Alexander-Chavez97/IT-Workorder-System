# Dockerfile
# ==========
# Explicit Dockerfile so Railway uses this instead of auto-generating one.
# KEY RULE: migrate is NOT run here — it has no DATABASE_URL at build time.
# migrate runs in the Procfile "release:" step where env vars are present.

FROM python:3.12-slim

# Keeps Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files — does NOT need a database
RUN DJANGO_SETTINGS_MODULE=laredo_ist.settings_production \
    SECRET_KEY=build-phase-placeholder \
    python manage.py collectstatic --noinput

# Railway injects PORT at runtime
EXPOSE 8000

# This is the runtime start command.
# The Procfile "release:" step (migrate) runs before this via Railway's
# release phase mechanism — not during the Docker build.
CMD gunicorn laredo_ist.wsgi \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 2 \
    --timeout 120 \
    --log-file -
