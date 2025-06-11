#!/bin/bash

# Create build directory
mkdir -p build

# Copy static files
cp -r static build/
cp -r templates build/

# Copy Python files
cp *.py build/
cp requirements.txt build/

# Create necessary directories
mkdir -p build/uploads
mkdir -p build/templates_storage
mkdir -p build/learned_preferences_storage
mkdir -p build/files

# Copy configuration files
cp field_definitions.json build/

echo "Build completed successfully"
