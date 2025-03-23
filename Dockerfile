# Use the official Python image
FROM python:3.10-slim

# Install dependencies
RUN apt-get update -y && apt-get install -y ca-certificates fuse3 sqlite3 && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Copy litefs
COPY --from=flyio/litefs:0.5 /usr/local/bin/litefs /usr/local/bin/litefs

# Create necessary directories
RUN mkdir -p /litefs /var/lib/litefs

# Copy LiteFS config
COPY litefs.yml /etc/litefs.yml

# Set permissions
RUN chmod 777 /litefs /var/lib/litefs

# Expose both the application port and LiteFS proxy port
EXPOSE 8501 8080

# Make start script executable
COPY start.sh .
RUN chmod +x start.sh

# Use litefs mount as entrypoint
ENTRYPOINT ["litefs", "mount"]