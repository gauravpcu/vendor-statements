# AWS Lambda Deployment Instructions

This document provides instructions for deploying the Vendor Statements application to AWS Lambda.

## Prerequisites

- AWS CLI installed and configured with appropriate credentials
- Python 3.9 or 3.10 (same version as your Lambda runtime)
- pip (Python package installer)
- Basic understanding of AWS Lambda, API Gateway, and related services
- AWS S3 bucket (for deploying packages larger than 50MB)

## Deployment Steps

### Step 1: Build the Lambda package

1. Run the build script to create the deployment packages:

```bash
chmod +x build_lambda.sh
./build_lambda.sh
```

This script will:
- Create a Lambda layer with all required dependencies
- Create a Lambda function package with the application code
- Optimize both packages to reduce size
- Provide information about package sizes and deployment methods

2. Check the output of the build script for size warnings:
   - If any package exceeds 50MB, you will need to use the S3 deployment method
   - If the total unzipped size exceeds 250MB, you may need further optimization

### Step 2: Create a Lambda Layer

1. In the AWS Lambda Console, navigate to "Layers" and click "Create layer"
2. Name it "vendor-statements-dependencies"
3. Upload the generated `vendor-statements-layer.zip` file
4. Select the compatible runtimes (Python 3.9, 3.10)
5. Click "Create"

### Step 3: Create the Lambda Function

1. In the AWS Lambda Console, click "Create function"
2. Choose "Author from scratch"
3. Name it "vendor-statements-processor"
4. Select the appropriate runtime (Python 3.9 or 3.10)
5. Choose or create an execution role with appropriate permissions
6. Click "Create function"
7. In the function configuration page, upload the generated `vendor-statements-lambda.zip`
8. Under "Layers", click "Add a layer"
9. Select "Custom layers", choose "vendor-statements-dependencies" and the appropriate version, then click "Add"

### Step 4: Configure the Lambda Function

1. Set the handler to `lambda_function.lambda_handler`
2. Configure environment variables:
   - AZURE_OAI_ENDPOINT
   - AZURE_OAI_KEY
   - AZURE_OAI_DEPLOYMENT_NAME
   - AZURE_OAI_API_VERSION
   - Add any other environment variables needed by your application

3. Increase the timeout to at least 30 seconds
4. Adjust memory allocation to at least 512MB (recommended: 1024MB)

### Step 5: Set up API Gateway

1. In the Lambda function's "Function overview", click "Add trigger"
2. Select "API Gateway" as the source
3. Create a new API or use an existing one
4. Configure the API as needed (HTTP API is recommended for simplicity)
5. Click "Add"

### Step 6: Test the Deployment

1. Once the API Gateway is deployed, get the invoke URL
2. Test the API to ensure it's working correctly

## Deploying Large Packages via S3

If your Lambda function package exceeds the 50MB direct upload limit, follow these steps to deploy through S3:

1. Create an S3 bucket or use an existing one:
```bash
aws s3 mb s3://your-lambda-deployment-bucket --region us-east-1
```

2. Upload your Lambda deployment package to S3:
```bash
aws s3 cp vendor-statements-lambda.zip s3://your-lambda-deployment-bucket/
```

3. Create the Lambda function using the S3 object:
```bash
aws lambda create-function \
  --function-name vendor-statements-processor \
  --runtime python3.10 \
  --handler lambda_function.lambda_handler \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --code S3Bucket=your-lambda-deployment-bucket,S3Key=vendor-statements-lambda.zip \
  --timeout 30 \
  --memory-size 1024
```

4. Similarly, for the Lambda layer:
```bash
aws s3 cp vendor-statements-layer.zip s3://your-lambda-deployment-bucket/

aws lambda publish-layer-version \
  --layer-name vendor-statements-dependencies \
  --description "Dependencies for Vendor Statements application" \
  --content S3Bucket=your-lambda-deployment-bucket,S3Key=vendor-statements-layer.zip \
  --compatible-runtimes python3.9 python3.10
```

5. Attach the layer to your function:
```bash
aws lambda update-function-configuration \
  --function-name vendor-statements-processor \
  --layers arn:aws:lambda:REGION:ACCOUNT_ID:layer:vendor-statements-dependencies:VERSION
```

Replace `REGION`, `ACCOUNT_ID`, and `VERSION` with your specific values.

## Testing Locally

Before deploying to AWS, you can test your Lambda function locally to verify it works correctly:

1. Install the required packages:
```bash
pip install -r requirements-lambda.txt
```

2. Create a test event JSON file (test_event.json):
```json
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
```

3. Run the function locally:
```bash
python -c "import lambda_function; import json; event = json.load(open('test_event.json')); print(lambda_function.lambda_handler(event, None))"
```

If this executes successfully, your Lambda function should work in the AWS environment. If you encounter errors, they will be displayed in your terminal.

## Troubleshooting

### Common Issues

1. **Package Size Too Large**: If your deployment package exceeds 50MB (uncompressed) or 250MB (with layers):
   - Consider moving more dependencies to the layer
   - Remove unnecessary files (use the cleanup.sh script)
   - Skip optional dependencies like docling when building

2. **Timeout Issues**: If your function times out:
   - Increase the Lambda timeout setting
   - Optimize your code for better performance
   - Consider splitting the functionality into multiple functions

3. **Memory Issues**: If your function runs out of memory:
   - Increase the allocated memory
   - Optimize your code to use less memory

4. **Import Errors**: If you see errors like `No module named 'flask.json.tag'`:
   - Make sure you're not removing essential Flask modules during the build process
   - The build script has been updated to retain these modules
   - If you still encounter this issue, modify build_lambda.sh to keep additional modules

5. **libmagic Missing Error**: If you see an error like `failed to find libmagic`:
   - We've implemented multiple fallback strategies for the libmagic dependency:
     1. Try to use python-magic-bin-linux which is designed for AWS Lambda
     2. Look for magic files in multiple possible locations
     3. Use a custom fallback implementation that detects file types by extension
   - The solution is designed to gracefully degrade, maintaining functionality even if libmagic isn't available
   - For better MIME type detection, you can create a custom Lambda layer with libmagic binaries

6. **Numpy Import Error**: If you see an error like `Error importing numpy: you should not try to import numpy from its source directory`:
   - The build script now uses a clean virtual environment to install dependencies
   - This prevents package path issues when importing libraries like numpy
   - If you still encounter this issue, try cleaning up completely with `./cleanup.sh` before rebuilding

## Size Optimization

The `build_lambda.sh` script implements several optimization strategies:

1. Splits dependencies between the layer and function package
2. Makes heavy dependencies optional (docling, pytesseract, pdf2image)
3. Removes unnecessary files (tests, docs, examples)
4. Uses maximum compression for the ZIP files

If you need further optimization, you can:

1. Move more code to external services
2. Implement a serverless framework like SAM or Serverless Framework
3. Consider using Amazon ECS or EKS for more complex workloads

## Updating the Deployment

To update your deployment:

1. Make your changes to the code
2. Run `./cleanup.sh` to remove unnecessary files
3. Run `./build_lambda.sh` to rebuild the packages
4. Upload the new packages to AWS
   - For the layer: Create a new layer version
   - For the function: Upload the new code
