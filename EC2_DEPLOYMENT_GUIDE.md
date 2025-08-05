# EC2 Deployment Guide

This document provides a step-by-step guide for deploying and updating the vendor-statements application on an EC2 instance.

## Prerequisites

- AWS CLI configured with appropriate permissions
- SSH access to EC2 instance (vendor-statements-key.pem)
- Docker installed on local machine

## Commands for Deployment Process

### 1. Check EC2 Instance Status

```bash
./ec2-management.sh status
```

This command shows:
- Instance ID, state, and type
- Public and private IP addresses
- Application URLs
- Connectivity status

### 2. Build and Push Docker Image to ECR

```bash
./deploy_to_ecr.sh
```

This command:
- Builds the Docker image for the AMD64 platform (compatible with EC2)
- Tags the image for Amazon ECR
- Authenticates to the ECR repository
- Pushes the image to ECR

### 3. Resize EC2 Disk (if needed)

If you encounter "no space left on device" errors:

```bash
# Run the resize script to increase the EBS volume size
./resize_ec2_disk.sh

# SSH into the instance and complete the resize process
ssh -i ~/.ssh/vendor-statements-key.pem ec2-user@<EC2_IP_ADDRESS>
sudo growpart /dev/nvme0n1 1
sudo xfs_growfs -d /  # For XFS filesystem (Amazon Linux 2 default)
```

Verify the resize worked:
```bash
df -h  # Check that / filesystem now shows the new size
```

### 4. Update the Application on EC2

```bash
./ec2-management.sh update
```

This command:
- Re-runs the deploy_to_ecr.sh script
- SSH's into the EC2 instance
- Authenticates with ECR
- Pulls the latest Docker image
- Stops and removes the existing container
- Starts a new container with the latest image
- Maps volumes for persistent storage

### 5. Manual Update (if automated update fails)

If the automated update fails, you can perform these steps manually:

```bash
# 1. Push the image to ECR
./deploy_to_ecr.sh

# 2. Login to ECR from the EC2 instance
aws ecr get-login-password --region us-east-1 | ssh -i ~/.ssh/vendor-statements-key.pem ec2-user@<EC2_IP_ADDRESS> 'sudo docker login --username AWS --password-stdin 533267165065.dkr.ecr.us-east-1.amazonaws.com'

# 3. SSH into the instance and perform the update
ssh -i ~/.ssh/vendor-statements-key.pem ec2-user@<EC2_IP_ADDRESS>

# 4. Once inside the EC2 instance
sudo docker pull 533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest
sudo docker stop vendor-statements-app
sudo docker rm vendor-statements-app
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

### Disk Space Issues

If you encounter disk space errors:
1. Check current disk usage: `df -h`
2. Clean up Docker resources: `sudo docker system prune -af`
3. Follow the disk resize instructions in section 3

### ECR Authentication Issues

If you see "no basic auth credentials" error:
1. Manually authenticate with ECR on the EC2 instance:
   ```bash
   aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin 533267165065.dkr.ecr.us-east-1.amazonaws.com
   ```

### Container Won't Start

If the container doesn't start correctly:
1. Check Docker logs: `sudo docker logs vendor-statements-app`
2. Verify environment variables: `sudo cat /opt/app/.env`
3. Ensure volumes exist: `ls -la /opt/app-data/`

## Maintenance

### Viewing Logs

```bash
./ec2-management.sh logs
```

### SSH Access

```bash
./ec2-management.sh ssh
```

### Restart Application

```bash
./ec2-management.sh restart
```

## Architecture Notes

- The application runs in a Docker container named `vendor-statements-app`
- Persistent data is stored in mapped volumes:
  - `/opt/app-data/uploads`: Uploaded files
  - `/opt/app-data/templates`: Saved templates
  - `/opt/app-data/preferences`: Learned preferences
- Environment variables are stored in `/opt/app/.env`
- The application runs on port 8000
