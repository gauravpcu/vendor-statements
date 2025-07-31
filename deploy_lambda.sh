#!/bin/bash

# Enhanced deployment script for Vendor Statements Flask App on AWS Lambda

set -e  # Exit on any command failure

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check required tools
echo -e "${BLUE}🔍 Checking required tools...${NC}"
command -v aws >/dev/null 2>&1 || { echo -e "${RED}❌ AWS CLI is required but not installed. Please install it first.${NC}" >&2; exit 1; }
command -v sam >/dev/null 2>&1 || { echo -e "${RED}❌ AWS SAM CLI is required but not installed. Please install it first.${NC}" >&2; exit 1; }

# Check AWS credentials
aws sts get-caller-identity >/dev/null 2>&1 || { echo -e "${RED}❌ AWS credentials not configured. Run 'aws configure' first.${NC}" >&2; exit 1; }

echo -e "${GREEN}✅ All required tools are available${NC}"

# Default values
STACK_NAME="vendor-statements-app"
STAGE_NAME="prod"
S3_BUCKET_NAME="vendor-statements-procurementiq-$(date +%Y%m%d)"
AWS_REGION="us-east-1"

echo ""
echo -e "${BLUE}🚀 AWS Lambda Deployment - Vendor Statements Flask Application${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""
echo "This script will deploy your enhanced Vendor Statements application to AWS Lambda with:"
echo "• 🤖 Azure OpenAI intelligent header mapping"
echo "• 📁 S3 storage for templates and files"
echo "• 🔄 Template management system"
echo "• 📊 File processing and preview"
echo ""

# Get configuration values
echo -e "${YELLOW}📝 Configuration Setup${NC}"
echo "Please provide the following configuration values:"
echo ""

read -p "Stack name [$STACK_NAME]: " input
STACK_NAME=${input:-$STACK_NAME}

read -p "Stage name [$STAGE_NAME]: " input
STAGE_NAME=${input:-$STAGE_NAME}

read -p "S3 bucket name [$S3_BUCKET_NAME]: " input
S3_BUCKET_NAME=${input:-$S3_BUCKET_NAME}

read -p "AWS region [$AWS_REGION]: " input
AWS_REGION=${input:-$AWS_REGION}

# Azure OpenAI Configuration
echo ""
echo -e "${YELLOW}🤖 Azure OpenAI Configuration${NC}"
echo "The application requires Azure OpenAI for intelligent header mapping."
echo ""

read -p "Azure OpenAI Endpoint [https://procurementiq.openai.azure.com/]: " AZURE_ENDPOINT
AZURE_ENDPOINT=${AZURE_ENDPOINT:-https://procurementiq.openai.azure.com/}

read -s -p "Azure OpenAI API Key: " AZURE_KEY
echo ""

read -p "Azure OpenAI Deployment Name [gpt-4o]: " AZURE_DEPLOYMENT
AZURE_DEPLOYMENT=${AZURE_DEPLOYMENT:-gpt-4o}

echo ""
echo -e "${BLUE}📦 Building deployment package...${NC}"

# Validate configuration
if [ -z "$AZURE_KEY" ]; then
    echo -e "${RED}❌ Azure OpenAI API Key is required${NC}"
    exit 1
fi

# Create build directory if it doesn't exist
mkdir -p .aws-sam/build

echo -e "${BLUE}🔨 Building SAM application...${NC}"
sam build --template template.yaml --use-container

echo ""
echo -e "${BLUE}🚀 Deploying application to AWS...${NC}"
echo "Stack: $STACK_NAME"
echo "Region: $AWS_REGION"
echo "Stage: $STAGE_NAME"
echo "S3 Bucket: $S3_BUCKET_NAME"
echo ""

sam deploy \
  --stack-name $STACK_NAME \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    StageName=$STAGE_NAME \
    BucketName=$S3_BUCKET_NAME \
    AzureOpenAIEndpoint=$AZURE_ENDPOINT \
    AzureOpenAIKey=$AZURE_KEY \
    AzureOpenAIDeployment=$AZURE_DEPLOYMENT \
  --region $AWS_REGION \
  --no-confirm-changeset

# Get deployment outputs
echo ""
echo -e "${BLUE}📊 Retrieving deployment information...${NC}"

API_URL=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text \
  --region $AWS_REGION 2>/dev/null || echo "Not available")

S3_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query "Stacks[0].Outputs[?OutputKey=='S3BucketName'].OutputValue" \
  --output text \
  --region $AWS_REGION 2>/dev/null || echo "Not available")

LAMBDA_ARN=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query "Stacks[0].Outputs[?OutputKey=='LambdaFunctionArn'].OutputValue" \
  --output text \
  --region $AWS_REGION 2>/dev/null || echo "Not available")

echo ""
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${GREEN}========================${NC}"
echo ""
echo -e "${BLUE}📍 Application URLs:${NC}"
echo "   Web Application: $API_URL"
echo "   Storage Status:  ${API_URL}storage_status"
echo "   Health Check:    ${API_URL}health"
echo ""
echo -e "${BLUE}☁️  AWS Resources:${NC}"
echo "   S3 Bucket:       $S3_BUCKET"
echo "   Lambda Function: $LAMBDA_ARN"
echo "   Stack Name:      $STACK_NAME"
echo "   Region:          $AWS_REGION"
echo ""
echo -e "${BLUE}🔧 Next Steps:${NC}"
echo "1. Visit the web application URL to test functionality"
echo "2. Check storage status to verify S3 integration"
echo "3. Upload a test file to verify AI mapping works"
echo "4. Create templates and test the full workflow"
echo ""
echo -e "${YELLOW}💡 Monitoring:${NC}"
echo "   CloudWatch Logs: /aws/lambda/${STACK_NAME}-VendorStatementsFunction-*"
echo "   AWS Console:     https://console.aws.amazon.com/lambda/home?region=${AWS_REGION}"
echo ""
echo -e "${GREEN}✅ Your Vendor Statements application is now live on AWS Lambda!${NC}"
