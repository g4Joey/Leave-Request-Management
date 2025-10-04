#!/bin/sh
set -e

# Run migrations and collect static files at container start
echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn leave_management.wsgi:application --bind 0.0.0.0:${PORT:-8000}