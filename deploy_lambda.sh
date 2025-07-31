#!/bin/bash

# Setup and deployment script for AWS Lambda

set -e  # Exit on any command failure

# Check required tools
command -v aws >/dev/null 2>&1 || { echo "AWS CLI is required but not installed. Aborting." >&2; exit 1; }
command -v sam >/dev/null 2>&1 || { echo "AWS SAM CLI is required but not installed. Aborting." >&2; exit 1; }

# Default values
STACK_NAME="vendor-statements-api"
STAGE_NAME="dev"
S3_BUCKET_NAME="vendor-statements-storage-$(openssl rand -hex 4)"
AWS_REGION="us-east-1"
LAMBDA_MEMORY="1024"

echo "===== AWS Lambda Deployment - Vendor Statements API ====="
echo ""
echo "This script will deploy your FastAPI application to AWS Lambda."
echo ""

# Ask for configuration values
read -p "Stack name [$STACK_NAME]: " input
STACK_NAME=${input:-$STACK_NAME}

read -p "Stage name [$STAGE_NAME]: " input
STAGE_NAME=${input:-$STAGE_NAME}

read -p "S3 bucket name [$S3_BUCKET_NAME]: " input
S3_BUCKET_NAME=${input:-$S3_BUCKET_NAME}

read -p "AWS region [$AWS_REGION]: " input
AWS_REGION=${input:-$AWS_REGION}

read -p "Lambda memory (MB) [$LAMBDA_MEMORY]: " input
LAMBDA_MEMORY=${input:-$LAMBDA_MEMORY}

echo ""
echo "Creating deployment package..."

# Install deployment dependencies - using Lambda-specific requirements file
pip install --upgrade pip
pip install -r requirements-lambda.txt

# Create build directory if it doesn't exist
mkdir -p .aws-sam/build

echo "Building SAM application..."
sam build --template template.yaml --use-container

echo "Deploying application..."
sam deploy \
  --stack-name $STACK_NAME \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    StageName=$STAGE_NAME \
    BucketName=$S3_BUCKET_NAME \
    LambdaMemory=$LAMBDA_MEMORY \
  --region $AWS_REGION \
  --guided

# Get deployed API URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text \
  --region $AWS_REGION)

echo ""
echo "===== Deployment Complete ====="
echo ""
echo "API URL: $API_URL"
echo "API Documentation: ${API_URL}docs"
echo ""
echo "To update the frontend to use this API:"
echo "1. Change API_BASE_URL in frontend/.env to: $API_URL"
echo "2. Restart your frontend application"
echo ""
