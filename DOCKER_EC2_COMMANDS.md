# Docker Build and EC2 Deployment Commands

Quick reference guide for building a new Docker image, pushing it to ECR, and deploying to EC2.

## One-Line Commands

```bash
# 1. Build and push Docker image to ECR
./deploy_to_ecr.sh

# 2. Deploy latest image to EC2
./ec2-management.sh update

# 3. Verify the deployment
./ec2-management.sh status
```

## Step-by-Step Commands

### 1. Build and Push Docker Image to ECR

```bash
# Login to Amazon ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 533267165065.dkr.ecr.us-east-1.amazonaws.com

# Build the image (targeting AMD64 platform for EC2 compatibility)
docker build --platform linux/amd64 -t vendor-statements-processor:latest .

# Tag the image for ECR
docker tag vendor-statements-processor:latest 533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest

# Push the image to ECR
docker push 533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest
```

### 2. Check EC2 Status and Space

```bash
# Check instance status
./ec2-management.sh status

# Check available disk space
./ec2-management.sh ssh "df -h"

# If disk space is low, clean Docker resources
./ec2-management.sh ssh "sudo docker system prune -af"
```

### 3. Resize EC2 Disk (if needed)

```bash
# Resize the EBS volume
./resize_ec2_disk.sh

# SSH into EC2 to extend the filesystem
./ec2-management.sh ssh

# Once connected to EC2, run:
sudo growpart /dev/nvme0n1 1
sudo xfs_growfs -d /
df -h  # Verify new size
exit
```

### 4. Deploy to EC2

```bash
# Deploy the latest image to EC2
./ec2-management.sh update
```

### 5. Verify Deployment

```bash
# Check if application is running
./ec2-management.sh status

# View application logs
./ec2-management.sh logs
```

## Manual Deployment Commands

If the automated scripts fail, you can deploy manually:

```bash
# SSH into the EC2 instance
ssh -i ~/.ssh/vendor-statements-key.pem ec2-user@<EC2_IP_ADDRESS>

# Login to ECR
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
```

## Troubleshooting

### No space left on device

If you see "no space left on device" error, follow the resize steps above.

### Authentication Issues

If ECR authentication fails:

```bash
# On EC2 instance
aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin 533267165065.dkr.ecr.us-east-1.amazonaws.com
```

### Container Issues

To check logs if the container isn't working properly:

```bash
# On EC2 instance
sudo docker logs vendor-statements-app
```
