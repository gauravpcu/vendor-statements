# EC2 Deployment Guide for Vendor Statements Processor

## 🚀 Why EC2 Over App Runner?

EC2 provides:
- Full control over the environment
- Better debugging capabilities
- More predictable networking
- Easier troubleshooting
- Support for complex dependencies (tesseract, poppler-utils, etc.)

## 📋 Prerequisites

- AWS CLI configured with appropriate permissions
- Docker installed locally (for testing)
- SSH key pair for EC2 access

## 🏗️ Architecture Overview

```
Internet → ALB → EC2 Instance → Docker Container (Flask App)
                     ↓
                 EBS Volume (persistent storage)
                     ↓
                 S3 Bucket (file storage)
```

## 🔧 Step 1: Create EC2 Infrastructure

### Launch EC2 Instance
```bash
# Create security group
aws ec2 create-security-group \
    --group-name vendor-statements-sg \
    --description "Security group for vendor statements processor"

# Add inbound rules
aws ec2 authorize-security-group-ingress \
    --group-name vendor-statements-sg \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-name vendor-statements-sg \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-name vendor-statements-sg \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-name vendor-statements-sg \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0
```

### Launch Instance
```bash
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --count 1 \
    --instance-type t3.medium \
    --key-name your-key-pair \
    --security-groups vendor-statements-sg \
    --user-data file://user-data.sh \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=vendor-statements-processor}]'
```

## 🐳 Step 2: Docker Deployment Strategy

We'll use Docker for consistent deployment and easy updates.

### Build and Push to ECR
```bash
# Build the image
docker build -t vendor-statements-processor .

# Tag for ECR
docker tag vendor-statements-processor:latest 533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest

# Push to ECR
docker push 533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest
```

## 🔨 Step 3: Server Setup Script

The user-data script will automatically configure the EC2 instance.

## 🌐 Step 4: Load Balancer Setup (Optional but Recommended)

For production, use an Application Load Balancer:

```bash
# Create ALB
aws elbv2 create-load-balancer \
    --name vendor-statements-alb \
    --subnets subnet-12345 subnet-67890 \
    --security-groups sg-12345

# Create target group
aws elbv2 create-target-group \
    --name vendor-statements-targets \
    --protocol HTTP \
    --port 8000 \
    --vpc-id vpc-12345 \
    --health-check-path /health
```

## 🔍 Step 5: Monitoring and Logging

### CloudWatch Setup
- EC2 instance metrics
- Application logs via CloudWatch agent
- Custom metrics for file processing

### Log Management
```bash
# Install CloudWatch agent on EC2
sudo yum install amazon-cloudwatch-agent
```

## 🚀 Step 6: Deployment Process

### Initial Deployment
1. Launch EC2 instance with user-data script
2. Verify Docker container is running
3. Test health endpoints
4. Configure domain/SSL if needed

### Updates
```bash
# SSH to instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Pull latest image
sudo docker pull 533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest

# Stop current container
sudo docker stop vendor-statements-app

# Remove old container
sudo docker rm vendor-statements-app

# Start new container
sudo docker run -d \
    --name vendor-statements-app \
    --restart unless-stopped \
    -p 8000:8000 \
    -v /opt/app-data:/app/uploads \
    -v /opt/app-data/templates:/app/templates_storage \
    -v /opt/app-data/preferences:/app/learned_preferences_storage \
    --env-file /opt/app/.env \
    533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest
```

## 🔐 Step 7: Security Best Practices

### IAM Role for EC2
- S3 access for file storage
- ECR access for image pulls
- CloudWatch logs access

### Environment Variables
Store sensitive data in:
- AWS Systems Manager Parameter Store
- AWS Secrets Manager
- Local .env file with restricted permissions

## 📊 Step 8: Scaling Considerations

### Vertical Scaling
- Start with t3.medium
- Monitor CPU/memory usage
- Scale up to t3.large or t3.xlarge as needed

### Horizontal Scaling
- Use Auto Scaling Groups
- Multiple instances behind ALB
- Shared storage via EFS or S3

## 🧪 Step 9: Testing

### Health Checks
```bash
# Basic health
curl http://your-instance-ip:8000/health

# Detailed health
curl http://your-instance-ip:8000/healthz

# Upload test
curl -X POST -F "files[]=@test-file.csv" http://your-instance-ip:8000/upload
```

## 🔧 Troubleshooting

### Common Issues
1. **Container won't start**: Check logs with `sudo docker logs vendor-statements-app`
2. **Port not accessible**: Verify security group rules
3. **File upload fails**: Check volume mounts and permissions
4. **AI features not working**: Verify environment variables for Azure OpenAI

### Log Locations
- Application logs: `sudo docker logs vendor-statements-app`
- System logs: `/var/log/messages`
- CloudWatch logs: AWS Console

## 💰 Cost Optimization

### Instance Types
- Development: t3.small ($15/month)
- Production: t3.medium ($30/month)
- High load: t3.large ($60/month)

### Storage
- Use gp3 EBS volumes for better cost/performance
- Lifecycle policies for S3 storage

## 🔄 Backup Strategy

### Data Backup
- EBS snapshots for instance storage
- S3 versioning for uploaded files
- Database backups if using RDS

### Configuration Backup
- Store deployment scripts in version control
- Document environment variables
- Keep AMI snapshots of configured instances

## 📈 Next Steps

1. Deploy basic EC2 setup
2. Test core functionality
3. Add monitoring and alerting
4. Implement CI/CD pipeline
5. Add SSL/domain configuration
6. Set up backup procedures