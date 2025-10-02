FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY aggregator.py .

# Create output directory
RUN mkdir -p /app/output

# Set a default value for UPDATE_INTERVAL (can be overridden at runtime)
ENV UPDATE_INTERVAL=3600
ENV USE_NGINX=false

# Create an entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]