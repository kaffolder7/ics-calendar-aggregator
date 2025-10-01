FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY aggregator.py .

# Create output directory
RUN mkdir -p /app/output

# Run aggregator periodically and serve via simple HTTP
CMD ["sh", "-c", "while true; do python aggregator.py && sleep 3600; done & python -m http.server 8080 --directory /app"]