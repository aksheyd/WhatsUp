# Use the official Python image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Copy the data file into the image
COPY web_scraper/state_urls.csv /app/web_scraper/state_urls.csv

# Run migrations and populate the database during deployment
CMD ["sh", "-c", "python manage.py migrate && python manage.py import_data && gunicorn myproject.wsgi:application --bind 0.0.0.0:8000"]