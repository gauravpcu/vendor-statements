# EC2 Deployment Guide - Vendor Statements Processor

## 🚀 Overview

This guide covers deploying the Vendor Statements Processor to AWS EC2 using Docker containers. This approach provides better control, easier debugging, and more reliable deployment compared to App Runner.

## 📋 Prerequisites

- AWS CLI configured with appropriate permissions
- Docker installed locally (for building images)
- SSH key pair for EC2 access
- Azure OpenAI service configured

## 🏗️ Architecture

```
Internet → Security Group → EC2 Instance → Docker Container (Flask App)
                                ↓
                           EBS Volume (persistent storage)
                                ↓
                           S3 Bucket (file storage)
```

## 🚀 Quick Start

### Option 1: Automated Deployment (Recommended)

1. **Setup and configure:**
   ```bash
   ./setup-ec2-deployment.sh
   ```

2. **Deploy to EC2:**
   ```bash
   ./deploy-ec2.sh
   ```

3. **Manage your deployment:**
   ```bash
   ./ec2-management.sh status
   ```

### Option 2: Manual Console Deployment

Follow the detailed guide in `ec2-console-setup-guide.md` for step-by-step console instructions.

## 📁 Deployment Files

| File | Purpose |
|------|---------|
| `deploy-ec2.sh` | Main deployment script |
| `ec2-management.sh` | Instance management utilities |
| `user-data.sh` | EC2 initialization script |
| `setup-ec2-deployment.sh` | Interactive setup wizard |
| `ec2-console-setup-guide.md` | Manual console deployment guide |
| `.env.template` | Environment configuration template |

## 🔧 Configuration

### 1. Environment Variables

Copy `.env.template` to `.env` and configure:

```bash
cp .env.template .env
# Edit .env with your actual values
```

**Required Variables:**
- `AZURE_OAI_ENDPOINT` - Your Azure OpenAI endpoint
- `AZURE_OAI_KEY` - Your Azure OpenAI API key
- `AZURE_OAI_DEPLOYMENT_NAME` - Your GPT model deployment name
- `AWS_S3_BUCKET_NAME` - S3 bucket for file storage

### 2. AWS Permissions

Your EC2 instance needs these IAM permissions:
- `AmazonEC2ContainerRegistryReadOnly` - For pulling Docker images
- `AmazonS3FullAccess` - For file storage
- `CloudWatchAgentServerPolicy` - For monitoring (optional)

## 🐳 Docker Image Management

### Build and Push to ECR

```bash
# Build for EC2 (AMD64 architecture)
docker build --platform linux/amd64 -t vendor-statements-processor .

# Tag and push to ECR
docker tag vendor-statements-processor:latest 533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest
docker push 533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest
```

### Update Deployed Application

```bash
# Using management script
./ec2-management.sh update

# Or manually on EC2 instance
sudo /opt/app/update-app.sh
```

## 🔍 Monitoring and Troubleshooting

### Health Checks

- **Basic Health:** `http://your-instance-ip:8000/health`
- **Detailed Health:** `http://your-instance-ip:8000/healthz`

### View Logs

```bash
# Application logs
./ec2-management.sh logs

# Or directly on instance
sudo docker logs vendor-statements-app
```

### Common Issues

1. **Container won't start:**
   - Check logs: `sudo docker logs vendor-statements-app`
   - Verify environment file: `sudo cat /opt/app/.env`

2. **S3 access issues:**
   - Verify bucket exists: `aws s3 ls s3://your-bucket-name/`
   - Check IAM permissions

3. **Azure OpenAI not working:**
   - Verify API keys in environment file
   - Check endpoint URL format

## 💰 Cost Management

### Instance Types and Costs (us-east-1)

| Instance Type | vCPU | RAM | Storage | Monthly Cost* |
|---------------|------|-----|---------|---------------|
| t3.small | 2 | 2 GB | 30 GB | ~$15 |
| t3.medium | 2 | 4 GB | 30 GB | ~$30 |
| t3.large | 2 | 8 GB | 30 GB | ~$60 |

*Approximate costs for 24/7 operation

### Cost Optimization

- **Stop instance** when not in use (you only pay for running time)
- **Use gp3 EBS volumes** for better cost/performance
- **Set up billing alerts** in AWS Console

## 🔐 Security Best Practices

1. **Use IAM roles** instead of hardcoded AWS credentials
2. **Restrict security group** to necessary ports only
3. **Keep environment files secure** (never commit to git)
4. **Regular security updates** of the base AMI
5. **Use HTTPS** in production with SSL certificates

## 🔄 Backup and Recovery

### Data Backup

- **Application data:** Stored in S3 bucket
- **Instance configuration:** Documented in deployment scripts
- **EBS snapshots:** For instance storage backup

### Disaster Recovery

1. **Launch new instance** using deployment scripts
2. **Restore from S3** (automatic with proper configuration)
3. **Update DNS** if using custom domain

## 📈 Scaling

### Vertical Scaling
- **Monitor resource usage** in CloudWatch
- **Upgrade instance type** as needed
- **Increase EBS volume size** if storage is full

### Horizontal Scaling (Future)
- **Application Load Balancer** for multiple instances
- **Auto Scaling Groups** for automatic scaling
- **Shared storage** via EFS or S3

## 🧪 Testing

### Automated Tests

```bash
# Test health endpoints
curl -f http://your-instance-ip:8000/health
curl -f http://your-instance-ip:8000/healthz

# Test file upload (with sample file)
curl -X POST -F "files[]=@sample.csv" http://your-instance-ip:8000/upload
```

### Manual Testing

1. **Upload various file types** (CSV, Excel, PDF)
2. **Test AI field mapping** functionality
3. **Save and load templates**
4. **Verify S3 storage** is working

## 📞 Support

### Getting Help

1. **Check application logs** first
2. **Verify environment configuration**
3. **Test network connectivity**
4. **Review AWS service status**

### Useful Commands

```bash
# Instance management
./ec2-management.sh status
./ec2-management.sh logs
./ec2-management.sh ssh

# Direct troubleshooting
sudo docker ps
sudo docker logs vendor-statements-app
sudo systemctl status docker
```

## 🎉 Success Indicators

Your deployment is successful when:

✅ **Instance is running** in EC2 console  
✅ **Health checks pass** (return 200 OK)  
✅ **Web interface loads** without errors  
✅ **File uploads work** and show field mappings  
✅ **AI features function** (if Azure OpenAI configured)  
✅ **Templates save/load** from S3 storage  
✅ **No critical errors** in application logs  

## 📚 Additional Resources

- [AWS EC2 Documentation](https://docs.aws.amazon.com/ec2/)
- [Docker Documentation](https://docs.docker.com/)
- [Azure OpenAI Service](https://docs.microsoft.com/en-us/azure/cognitive-services/openai/)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)

---

**Last Updated:** August 2025  
**Version:** 1.0  
**Tested On:** Amazon Linux 2, Docker 20.10+