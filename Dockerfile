# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Set the working directory in the container
WORKDIR /app

# Install system dependencies first to leverage Docker cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    libmagic1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# Copy the application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p /app/uploads /app/templates_storage /app/learned_preferences_storage

# Expose the port App Runner will use
EXPOSE 8080

# Start command for App Runner
CMD gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 60 app:app
