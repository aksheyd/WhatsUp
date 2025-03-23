# Use the official Python image
FROM python:3.10-slim

# Install dependencies
RUN apt-get update -y && apt-get install -y gunicorn ca-certificates fuse3 sqlite3 && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Copy litefs
COPY --from=flyio/litefs:0.5 /usr/local/bin/litefs /usr/local/bin/litefs

# Expose the application port
EXPOSE 8501

# Make start script executable
COPY start.sh .
RUN chmod +x start.sh

ENTRYPOINT litefs mount

# Use the start script instead
CMD ["./start.sh"]