#!/bin/bash
# Deploy Vendor Statements Processor to EC2

set -e

# Configuration
REGION="us-east-1"
INSTANCE_TYPE="t3.large"
KEY_NAME="vendor-statements-key"
SECURITY_GROUP_NAME="vendor-statements-sg"
INSTANCE_NAME="vendor-statements-processor"
VPC_ID="vpc-0bb57f378b6451edf"
SUBNET_ID="subnet-00bdabade76398df2"  # US-East-Public-1a

echo "🚀 Starting EC2 deployment for Vendor Statements Processor..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

echo "✅ AWS CLI configured"

# Get the latest Amazon Linux 2 AMI
echo "🔍 Finding latest Amazon Linux 2 AMI..."
AMI_ID=$(aws ec2 describe-images \
    --owners amazon \
    --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" \
    --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
    --output text \
    --region $REGION)

echo "📦 Using AMI: $AMI_ID"

# Create security group if it doesn't exist
echo "🔒 Setting up security group..."
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" "Name=vpc-id,Values=$VPC_ID" \
    --region $REGION \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "None")

if [ "$SECURITY_GROUP_ID" = "None" ] || [ -z "$SECURITY_GROUP_ID" ]; then
    echo "Creating security group: $SECURITY_GROUP_NAME"
    SECURITY_GROUP_ID=$(aws ec2 create-security-group \
        --group-name $SECURITY_GROUP_NAME \
        --description "Security group for vendor statements processor" \
        --vpc-id $VPC_ID \
        --region $REGION \
        --query 'GroupId' \
        --output text)
    
    # Add inbound rules
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 8000 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    echo "✅ Security group created: $SECURITY_GROUP_ID"
else
    echo "✅ Using existing security group: $SECURITY_GROUP_ID"
fi

# Build and push Docker image to ECR
echo "🐳 Building and pushing Docker image..."
if [ -f "./deploy_to_ecr.sh" ]; then
    ./deploy_to_ecr.sh
else
    echo "⚠️  deploy_to_ecr.sh not found. Building and pushing manually..."
    
    # Login to ECR
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin 533267165065.dkr.ecr.$REGION.amazonaws.com
    
    # Build and push
    docker build -t vendor-statements-processor .
    docker tag vendor-statements-processor:latest 533267165065.dkr.ecr.$REGION.amazonaws.com/vendor-statements-processor:latest
    docker push 533267165065.dkr.ecr.$REGION.amazonaws.com/vendor-statements-processor:latest
fi

# Launch EC2 instance
echo "🖥️  Launching EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --count 1 \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SECURITY_GROUP_ID \
    --subnet-id $SUBNET_ID \
    --associate-public-ip-address \
    --user-data file://user-data.sh \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --region $REGION \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "✅ Instance launched: $INSTANCE_ID"

# Wait for instance to be running
echo "⏳ Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

# Get instance details
INSTANCE_INFO=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region $REGION \
    --query 'Reservations[0].Instances[0]')

PUBLIC_IP=$(echo $INSTANCE_INFO | jq -r '.PublicIpAddress')
PRIVATE_IP=$(echo $INSTANCE_INFO | jq -r '.PrivateIpAddress')

echo "🎉 Instance is running!"
echo "📍 Instance ID: $INSTANCE_ID"
echo "🌐 Public IP: $PUBLIC_IP"
echo "🏠 Private IP: $PRIVATE_IP"

# Wait for instance to be accessible
echo "⏳ Waiting for instance to be accessible..."
sleep 60

# Upload environment file
echo "📄 Uploading environment configuration..."
if [ -f ".env.ec2" ]; then
    scp -o StrictHostKeyChecking=no -i ~/.ssh/$KEY_NAME.pem .env.ec2 ec2-user@$PUBLIC_IP:/tmp/.env
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/$KEY_NAME.pem ec2-user@$PUBLIC_IP 'sudo mv /tmp/.env /opt/app/.env && sudo chown ec2-user:ec2-user /opt/app/.env && sudo chmod 600 /opt/app/.env'
    echo "✅ Environment file uploaded"
else
    echo "⚠️  .env.ec2 file not found. Using default configuration."
fi

# Wait for user-data script to complete
echo "⏳ Waiting for application to start (this may take 2-3 more minutes)..."
sleep 120

# Test health endpoint
echo "🔍 Testing health endpoint..."
for i in {1..10}; do
    if curl -f -s "http://$PUBLIC_IP:8000/health" > /dev/null; then
        echo "✅ Application is healthy!"
        break
    else
        echo "⏳ Attempt $i/10: Application not ready yet, waiting 30 seconds..."
        sleep 30
    fi
done

echo ""
echo "🚀 Deployment Summary:"
echo "===================="
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo "Application URL: http://$PUBLIC_IP:8000"
echo "Health Check: http://$PUBLIC_IP:8000/health"
echo "Detailed Health: http://$PUBLIC_IP:8000/healthz"
echo ""
echo "📝 Next Steps:"
echo "1. Update /opt/app/.env on the instance with your API keys"
echo "2. Test file upload functionality"
echo "3. Configure domain name and SSL if needed"
echo "4. Set up monitoring and backups"
echo ""
echo "🔧 SSH Access:"
echo "ssh -i $KEY_NAME.pem ec2-user@$PUBLIC_IP"
echo ""
echo "📊 View logs:"
echo "ssh -i $KEY_NAME.pem ec2-user@$PUBLIC_IP 'sudo docker logs vendor-statements-app'"