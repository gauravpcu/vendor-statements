#!/bin/bash

# Test the Lambda function locally
# This script helps test the Lambda function before deploying to AWS

echo "Testing Lambda function locally..."

# Create a test event file if it doesn't exist
cat > test_event.json << 'EOF'
{
  "version": "2.0",
  "routeKey": "ANY /",
  "rawPath": "/",
  "rawQueryString": "",
  "headers": {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "host": "localhost:3000",
    "user-agent": "Mozilla/5.0"
  },
  "requestContext": {
    "http": {
      "method": "GET",
      "path": "/",
      "protocol": "HTTP/1.1",
      "sourceIp": "127.0.0.1",
      "userAgent": "Mozilla/5.0"
    }
  },
  "isBase64Encoded": false
}
EOF

echo "Created test_event.json with a sample API Gateway event"

# Run the function
echo "Running Lambda function with test event..."
python -c "import lambda_function; import json; event = json.load(open('test_event.json')); response = lambda_function.lambda_handler(event, None); print(f'Status code: {response[\"statusCode\"]}')"

echo "If no errors appeared, your Lambda function should work in AWS"
