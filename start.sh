#!/bin/bash
set -e

echo "Starting vendor-statements application..."

# Set default port if not specified
: "${PORT:=8080}"

echo "Main app will run on port: $PORT"

# Start main application 
echo "Starting main application with Flask development server..."
export FLASK_APP=app.py
export FLASK_ENV=development
exec python -m flask run --host=0.0.0.0 --port=${PORT}
