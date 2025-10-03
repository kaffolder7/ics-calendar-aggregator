#!/bin/sh

# Ensure output directory exists and has proper permissions
mkdir -p /app/output
chmod 755 /app/output

# Check if we should run once or loop
if [ "$RUN_ONCE" = "true" ]; then
    echo "Running calendar aggregator once..."
    python aggregator.py
    exit 0
fi

# Run aggregator in a loop
while true; do 
    echo "Running calendar aggregator..."
    python aggregator.py
    echo "Waiting $UPDATE_INTERVAL seconds before next run..."
    sleep $UPDATE_INTERVAL
done &

# Only start Python HTTP server if not using nginx
if [ "$USE_NGINX" != "true" ]; then
    echo "Starting Python HTTP server on port 8080..."
    cd /app/output
    python -m http.server 8080
else
    echo "Using external nginx server, keeping container alive..."
    # Keep container running without the Python server
    tail -f /dev/null
fi