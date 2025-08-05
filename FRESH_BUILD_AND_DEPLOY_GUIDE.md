# Fresh Docker Build and EC2 Deployment Guide

This document provides a step-by-step guide for building a fresh Docker image of the vendor-statements application and deploying it to an EC2 instance.

## Prerequisites

- AWS CLI installed and configured with appropriate permissions
- Docker installed and running on your local machine
- SSH key pair for EC2 access (vendor-statements-key.pem)
- Git repository cloned and up-to-date

## Step 1: Prepare Your Local Environment

```bash
# Navigate to the project directory
cd /Users/gaurav/Desktop/Code/vendor-statements

# Make sure you're on the correct branch
git checkout feature/file-upload-handling

# Pull latest changes
git pull origin feature/file-upload-handling

# Review the Dockerfile to ensure it's configured correctly
cat Dockerfile
```

## Step 2: Build and Push Docker Image to ECR

```bash
# Make the deployment script executable (if needed)
chmod +x deploy_to_ecr.sh

# Build the Docker image and push to ECR
./deploy_to_ecr.sh
```

The `deploy_to_ecr.sh` script performs these operations:
- Builds the Docker image with the `--platform linux/amd64` flag (ensuring EC2 compatibility)
- Tags the image with the appropriate ECR repository name
- Authenticates with AWS ECR
- Pushes the image to the ECR repository

**Note:** If the script fails, you can perform the steps manually:

```bash
# Login to Amazon ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 533267165065.dkr.ecr.us-east-1.amazonaws.com

# Build the image (targeting the correct platform for EC2)
docker build --platform linux/amd64 -t vendor-statements-processor:latest .

# Tag the image for ECR
docker tag vendor-statements-processor:latest 533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest

# Push the image to ECR
docker push 533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest
```

## Step 3: Check EC2 Instance Status and Space

Before deploying, check the status and available space on your EC2 instance:

```bash
# Check EC2 instance status
./ec2-management.sh status

# Check available disk space on EC2
./ec2-management.sh ssh "df -h"
```

If disk space is low (below 20% available), clean up or resize:

```bash
# Clean Docker resources on EC2
./ec2-management.sh ssh "sudo docker system prune -af"

# If space is still low, resize the disk
./resize_ec2_disk.sh

# SSH into the instance to complete filesystem resize
./ec2-management.sh ssh
```

Inside the EC2 instance:
```bash
sudo growpart /dev/nvme0n1 1
sudo xfs_growfs -d /
df -h  # Verify the resize was successful
exit   # Return to your local machine
```

## Step 4: Deploy the Fresh Image to EC2

```bash
# Deploy the latest image to EC2
./ec2-management.sh update
```

The update script will:
- SSH into the EC2 instance
- Authenticate with ECR from the EC2 instance
- Pull the latest image
- Stop and remove the existing container
- Start a new container with the latest image

## Step 5: Verify Deployment

```bash
# Check if the application is running correctly
./ec2-management.sh status

# View application logs for any errors
./ec2-management.sh logs
```

## Step 6: Test the Application

1. Open the application URL in a browser: http://<EC2_PUBLIC_IP>:8000
2. Test key functionality to ensure everything is working properly

## Troubleshooting

### Image Won't Build Locally

- Check Docker daemon is running: `docker info`
- Ensure sufficient disk space: `df -h`
- Review build errors in the console output

### ECR Push Fails

- Verify AWS credentials: `aws sts get-caller-identity`
- Check ECR repository exists: `aws ecr describe-repositories`
- Try manual authentication: `aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 533267165065.dkr.ecr.us-east-1.amazonaws.com`

### EC2 Deployment Issues

- Check EC2 connectivity: `./ec2-management.sh ssh "echo 'Connection successful'"`
- Verify ECR authentication on EC2: `./ec2-management.sh ssh "aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin 533267165065.dkr.ecr.us-east-1.amazonaws.com"`
- Check container logs: `./ec2-management.sh ssh "sudo docker logs vendor-statements-app"`

## Manual Deployment Commands

If you need to manually deploy to EC2, use these commands:

```bash
# SSH into the EC2 instance
ssh -i ~/.ssh/vendor-statements-key.pem ec2-user@<EC2_IP_ADDRESS>

# Authenticate with ECR
aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin 533267165065.dkr.ecr.us-east-1.amazonaws.com

# Pull the latest image
sudo docker pull 533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest

# Stop and remove the existing container
sudo docker stop vendor-statements-app
sudo docker rm vendor-statements-app

# Run the new container
sudo docker run -d \
    --name vendor-statements-app \
    --restart unless-stopped \
    -p 8000:8000 \
    -v /opt/app-data/uploads:/app/uploads \
    -v /opt/app-data/templates:/app/templates_storage \
    -v /opt/app-data/preferences:/app/learned_preferences_storage \
    --memory="6g" \
    --memory-swap="8g" \
    --cpus="2.0" \
    --env-file /opt/app/.env \
    533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest

# Verify the container is running
sudo docker ps

# Check the logs
sudo docker logs vendor-statements-app
```

## Summary Checklist

- [ ] Repository is up-to-date
- [ ] Docker image built for linux/amd64 platform
- [ ] Image pushed to ECR successfully
- [ ] EC2 has sufficient disk space
- [ ] Latest image deployed to EC2
- [ ] Application running correctly
- [ ] Functionality tested
