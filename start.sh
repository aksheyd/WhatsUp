#!/bin/bash

# Set the database path for LiteFS
export DB_PATH="/litefs/db.sqlite3"
DB_DIR="/litefs"

# Ensure database directory exists
mkdir -p $DB_DIR

# Create empty database file if it doesn't exist
if [ ! -f "$DB_PATH" ]; then
    echo "Creating empty database file..."
    touch "$DB_PATH"
    chmod 666 "$DB_PATH"
fi

# Maximum number of attempts (30 seconds)
MAX_ATTEMPTS=30
ATTEMPTS=0

# Wait for LiteFS to be ready with timeout
while [ ! -w "$DB_PATH" ]; do
    ATTEMPTS=$((ATTEMPTS + 1))
    if [ $ATTEMPTS -ge $MAX_ATTEMPTS ]; then
        echo "Error: Timed out waiting for LiteFS database to become writable"
        exit 1
    fi
    echo "Waiting for LiteFS database to become writable... (Attempt $ATTEMPTS/$MAX_ATTEMPTS)"
    sleep 1
done

cd djangobase

# Run database migrations with error handling
python manage.py makemigrations || exit 1
python manage.py migrate || exit 1

# cd /app
# Import data
# python djangobase/manage.py import_data || echo "Warning: Data import failed"

# cd djangobase
python manage.py import_data_json || echo "Warning: JSON import failed"

playwright install --with-deps

# Collect static files
python manage.py collectstatic --noinput || echo "Warning: Static files collection failed"

# Start Gunicorn with proper binding and increased timeout
exec gunicorn mysite.wsgi:application \
    --bind 0.0.0.0:8501 \
    --access-logfile - \
    --error-logfile - \
    --timeout 120 \
    --workers 2
