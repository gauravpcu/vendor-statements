#!/bin/bash

# Cleanup script for AWS Lambda deployment
# This script removes unnecessary files and directories to reduce package size

echo "Running cleanup for AWS Lambda deployment..."

# Remove Python cache files
echo "Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type f -name "*.pyd" -delete

# Remove temporary folders
echo "Removing temporary folders..."
rm -rf .pytest_cache
rm -rf .coverage
rm -rf htmlcov
rm -rf temp_packages
rm -rf lambda_package
rm -rf lambda_layer

# Remove deployment artifacts if they exist
echo "Removing old deployment artifacts..."
rm -f vendor-statements-layer.zip
rm -f vendor-statements-lambda.zip

# Remove logs
echo "Removing log files..."
find . -type f -name "*.log" -delete
rm -f upload_history.log

# Remove test data if it exists
echo "Removing test data..."
find ./uploads -type f -not -name ".gitkeep" -delete 2>/dev/null || true

echo "Cleanup completed successfully!"
