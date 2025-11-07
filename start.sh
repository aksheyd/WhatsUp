#!/bin/bash
set -e  # Exit on error

echo "Starting WhatsUp application..."

# Navigate to Django project directory
cd djangobase

# Run database migrations
echo "Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Import initial data if needed
echo "Importing initial data..."
python manage.py import_data_json || echo "Warning: JSON import failed or no data to import"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Gunicorn
echo "Starting Gunicorn server..."
exec gunicorn mysite.wsgi:application \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    --timeout 120 \
    --workers 2
