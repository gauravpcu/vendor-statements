# AWS Lambda Deployment Instructions

This document provides instructions for deploying the Vendor Statements application to AWS Lambda.

## Prerequisites

- AWS CLI installed and configured with appropriate credentials
- Python 3.9 or 3.10 (same version as your Lambda runtime)
- pip (Python package installer)
- Basic understanding of AWS Lambda, API Gateway, and related services

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
