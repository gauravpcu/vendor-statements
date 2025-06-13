#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
  source venv/bin/activate
fi

# Install dependencies
if [ -f "requirements.txt" ]; then
  pip install -r requirements.txt
fi

# Run the Flask application
# Use Flask's built-in server for development
# You can specify host and port if needed, e.g., python app.py --host=0.0.0.0 --port=8000
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --port=5001
