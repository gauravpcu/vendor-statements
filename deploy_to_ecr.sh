#!/bin/bash

# Deploy to ECR script
set -e

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="533267165065"
ECR_REPOSITORY="vendor-statements-processor"
IMAGE_TAG="latest"

echo "🚀 Deploying to ECR..."
echo "Region: $AWS_REGION"
echo "Account: $AWS_ACCOUNT_ID"
echo "Repository: $ECR_REPOSITORY"
echo "Tag: $IMAGE_TAG"
echo

# Build the image
echo "🔨 Building Docker image..."
docker build -t $ECR_REPOSITORY:$IMAGE_TAG .

# Tag for ECR
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"
echo "🏷️  Tagging image for ECR: $ECR_URI"
docker tag $ECR_REPOSITORY:$IMAGE_TAG $ECR_URI

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Push to ECR
echo "📤 Pushing to ECR..."
docker push $ECR_URI

echo "✅ Successfully pushed to ECR!"
echo "Image URI: $ECR_URI"
echo
echo "🔄 Now update your App Runner service to use this image URI."
echo "Go to: https://console.aws.amazon.com/apprunner/"
echo "1. Select your service"
echo "2. Click 'Deploy' or 'Edit configuration'"
echo "3. Update the image URI to: $ECR_URI"