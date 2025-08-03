#!/bin/bash
# Quick setup script for EC2 deployment

set -e

echo "🚀 Setting up EC2 deployment for Vendor Statements Processor"
echo "============================================================"

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first:"
    echo "   https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Check jq
if ! command -v jq &> /dev/null; then
    echo "⚠️  jq not found. Installing via brew (macOS)..."
    if command -v brew &> /dev/null; then
        brew install jq
    else
        echo "❌ Please install jq manually: https://stedolan.github.io/jq/download/"
        exit 1
    fi
fi

echo "✅ All prerequisites met!"

# Get user input for configuration
echo ""
echo "📝 Configuration Setup"
echo "====================="

# Get AWS region
read -p "AWS Region (default: us-east-1): " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

# Get key pair name
echo ""
echo "🔑 SSH Key Pair Setup"
echo "You need an EC2 key pair for SSH access."
aws ec2 describe-key-pairs --region $AWS_REGION --query 'KeyPairs[].KeyName' --output table

read -p "Enter your EC2 key pair name: " KEY_NAME

if [ -z "$KEY_NAME" ]; then
    echo "❌ Key pair name is required"
    exit 1
fi

# Verify key pair exists
if ! aws ec2 describe-key-pairs --key-names $KEY_NAME --region $AWS_REGION > /dev/null 2>&1; then
    echo "❌ Key pair '$KEY_NAME' not found in region $AWS_REGION"
    echo "💡 Create one in the AWS Console or use aws ec2 create-key-pair"
    exit 1
fi

# Update deployment script with user's configuration
echo ""
echo "🔧 Updating deployment scripts..."

# Update deploy-ec2.sh
sed -i.bak "s/REGION=\"us-east-1\"/REGION=\"$AWS_REGION\"/" deploy-ec2.sh
sed -i.bak "s/KEY_NAME=\"your-key-pair\"/KEY_NAME=\"$KEY_NAME\"/" deploy-ec2.sh

# Update ec2-management.sh
sed -i.bak "s/REGION=\"us-east-1\"/REGION=\"$AWS_REGION\"/" ec2-management.sh

# Update deploy_to_ecr.sh if it exists
if [ -f "deploy_to_ecr.sh" ]; then
    sed -i.bak "s/us-east-1/$AWS_REGION/g" deploy_to_ecr.sh
fi

echo "✅ Scripts updated with your configuration"

# Test Docker build
echo ""
echo "🐳 Testing Docker build..."
if docker build -t vendor-statements-test . > /dev/null 2>&1; then
    echo "✅ Docker build successful"
    docker rmi vendor-statements-test > /dev/null 2>&1
else
    echo "❌ Docker build failed. Please check your Dockerfile and dependencies."
    exit 1
fi

# Create environment file template
echo ""
echo "📄 Creating environment configuration..."

cat > .env.ec2.template << 'EOF'
# Flask Configuration
FLASK_ENV=production
FLASK_APP=app.py
PYTHONPATH=/app

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name

# AWS Configuration
AWS_DEFAULT_REGION=us-east-1

# S3 Configuration (optional)
S3_BUCKET_NAME=your-s3-bucket-name

# External API Configuration (optional)
INVOICE_VALIDATION_API_URL=your-validation-api-url
INVOICE_VALIDATION_API_KEY=your-validation-api-key
EOF

echo "✅ Environment template created: .env.ec2.template"

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "📋 Next Steps:"
echo "1. Edit .env.ec2.template with your actual API keys and configuration"
echo "2. Run './deploy-ec2.sh' to deploy your application"
echo "3. Use './ec2-management.sh status' to check deployment status"
echo ""
echo "🔧 Available Commands:"
echo "./deploy-ec2.sh          - Deploy application to EC2"
echo "./ec2-management.sh      - Manage your EC2 instance"
echo ""
echo "📚 Documentation:"
echo "See ec2-deployment-guide.md for detailed instructions"
echo ""
echo "⚠️  Important Notes:"
echo "- Make sure your SSH key file is in ~/.ssh/$KEY_NAME.pem"
echo "- Update the SSH key path in ec2-management.sh if different"
echo "- Your application will be available on port 8000"
echo "- Remember to configure your environment variables after deployment"