#!/bin/bash
set -e

echo "Starting vendor-statements application..."

# Set default ports if not specified
: "${PORT:=8080}"
: "${HEALTH_PORT:=8081}"

echo "Main app will run on port: $PORT"
echo "Health check server will run on port: $HEALTH_PORT"

# Start health check server in the background
echo "Starting health check server..."
python health.py &
HEALTH_PID=$!
echo "Health check server started with PID: $HEALTH_PID"

# Give the health check server a moment to start
sleep 2

# Start main application
echo "Starting main application..."
exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 60 app:app
