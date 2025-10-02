#!/bin/sh

# Run aggregator in a loop
while true; do 
    python aggregator.py && sleep $UPDATE_INTERVAL
done &

# Only start Python HTTP server if not using nginx
if [ "$USE_NGINX" != "true" ]; then
    echo "Starting Python HTTP server on port 8080..."
    python -m http.server 8080 --directory /app
else
    echo "Using external nginx server, keeping container alive..."
    # Keep container running without the Python server
    tail -f /dev/null
fi