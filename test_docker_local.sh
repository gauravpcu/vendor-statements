#!/bin/bash
# Test Docker locally with EC2-like configuration

set -e

echo "🐳 Testing Docker setup locally (EC2-like configuration)"
echo "=========================================================="

# Step 1: Build the Docker image
echo "1. Building Docker image..."
docker build -t vendor-statements-local .

# Step 2: Stop any existing container
echo "2. Stopping existing container..."
docker stop vendor-statements-local-test 2>/dev/null || true
docker rm vendor-statements-local-test 2>/dev/null || true

# Step 3: Create local directories (like EC2)
echo "3. Creating local directories..."
mkdir -p ./local-test-data/{uploads,templates,preferences}

# Step 4: Run container with EC2-like settings
echo "4. Running container with EC2-like settings..."
docker run -d \
    --name vendor-statements-local-test \
    -p 8000:8000 \
    -v $(pwd)/local-test-data/uploads:/app/uploads \
    -v $(pwd)/local-test-data/templates:/app/templates_storage \
    -v $(pwd)/local-test-data/preferences:/app/learned_preferences_storage \
    --memory="4g" \
    --memory-swap="6g" \
    --cpus="2.0" \
    --env-file .env \
    vendor-statements-local

# Step 5: Wait for container to start
echo "5. Waiting for container to start..."
sleep 10

# Step 6: Check container status
echo "6. Checking container status..."
docker ps | grep vendor-statements-local-test

# Step 7: Check logs
echo "7. Checking container logs..."
docker logs vendor-statements-local-test

# Step 8: Test health endpoint
echo "8. Testing health endpoint..."
sleep 5
curl -f http://localhost:8000/health && echo "✅ Health check passed!" || echo "❌ Health check failed!"

echo ""
echo "🎉 Local Docker test completed!"
echo "Container is running at: http://localhost:8000"
echo ""
echo "Useful commands:"
echo "- View logs: docker logs -f vendor-statements-local-test"
echo "- Stop container: docker stop vendor-statements-local-test"
echo "- Remove container: docker rm vendor-statements-local-test"
echo "- Test detailed health: curl http://localhost:8000/healthz"