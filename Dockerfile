# Use the official Python image
FROM python:3.10-slim

# Install dependencies (removed fuse3 since we don't need LiteFS)
RUN apt-get update -y && apt-get install -y ca-certificates sqlite3 && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright and its dependencies
RUN pip install playwright
RUN playwright install --with-deps

# Copy the application code
COPY . .

# Create database directory with proper permissions
RUN mkdir -p /data && chmod 777 /data

# Make start script executable
COPY start.sh .
RUN chmod +x start.sh

# Expose the application port
EXPOSE 8000

# Run the start script
CMD ["./start.sh"]