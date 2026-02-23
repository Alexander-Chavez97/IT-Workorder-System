release: python manage.py migrate --noinput
web: gunicorn laredo_ist.wsgi --workers 2 --timeout 120 --log-file -
