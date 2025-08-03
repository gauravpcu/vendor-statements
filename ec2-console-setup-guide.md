# EC2 Console Setup Guide

## 🖥️ Setting up Vendor Statements Processor via EC2 Console

Since you're logged into the EC2 console, here's how to deploy your application step by step:

## 📋 Step 1: Launch EC2 Instance

### 1.1 Navigate to EC2 Dashboard
- Go to **EC2 Dashboard** in AWS Console
- Click **"Launch Instance"**

### 1.2 Configure Instance
**Name:** `vendor-statements-processor`

**Application and OS Images:**
- **Amazon Machine Image (AMI):** Amazon Linux 2 AMI (HVM) - Kernel 5.10, SSD Volume Type
- **Architecture:** 64-bit (x86)

**Instance Type:**
- **Recommended:** `t3.medium` (2 vCPU, 4 GB RAM) - $30/month
- **Budget option:** `t3.small` (2 vCPU, 2 GB RAM) - $15/month
- **High performance:** `t3.large` (2 vCPU, 8 GB RAM) - $60/month

**Key Pair:**
- Select your existing key pair OR create a new one
- **Important:** Download the .pem file if creating new

### 1.3 Network Settings
**Security Group:** Create new security group with these rules:

| Type | Protocol | Port Range | Source | Description |
|------|----------|------------|---------|-------------|
| SSH | TCP | 22 | 0.0.0.0/0 | SSH access |
| HTTP | TCP | 80 | 0.0.0.0/0 | HTTP access |
| HTTPS | TCP | 443 | 0.0.0.0/0 | HTTPS access |
| Custom TCP | TCP | 8000 | 0.0.0.0/0 | Application port |

### 1.4 Configure Storage
- **Size:** 20 GB (minimum) - 30 GB recommended
- **Volume Type:** gp3 (better performance/cost)
- **Delete on Termination:** ✅ (checked)

### 1.5 Advanced Details - User Data
Copy and paste this script in the **User Data** section:

```bash
#!/bin/bash
# EC2 User Data Script for Vendor Statements Processor

# Update system
yum update -y

# Install Docker
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Create application directories
mkdir -p /opt/app-data/{uploads,templates,preferences}
mkdir -p /opt/app

# Set permissions
chown -R ec2-user:ec2-user /opt/app-data
chmod -R 755 /opt/app-data

# Create environment file template
cat > /opt/app/.env << 'EOF'
# Flask Configuration
FLASK_ENV=production
FLASK_APP=app.py
PYTHONPATH=/app

# Azure OpenAI Configuration (REPLACE WITH YOUR VALUES)
AZURE_OAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OAI_KEY=your-azure-openai-api-key-here
AZURE_OAI_DEPLOYMENT_NAME=your-gpt-deployment-name
AZURE_OAI_API_VERSION=2024-02-15-preview

# AWS Configuration
AWS_DEFAULT_REGION=us-east-1

# S3 Configuration (optional)
S3_BUCKET_NAME=your-s3-bucket-name

# External API Configuration (optional)
INVOICE_VALIDATION_API_URL=your-validation-api-url
INVOICE_VALIDATION_API_KEY=your-validation-api-key
EOF

# Set environment file permissions
chown ec2-user:ec2-user /opt/app/.env
chmod 600 /opt/app/.env

# Login to ECR and run the application
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 533267165065.dkr.ecr.us-east-1.amazonaws.com

# Pull and run the application
docker pull 533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest

# Run the container
docker run -d \
    --name vendor-statements-app \
    --restart unless-stopped \
    -p 8000:8000 \
    -v /opt/app-data/uploads:/app/uploads \
    -v /opt/app-data/templates:/app/templates_storage \
    -v /opt/app-data/preferences:/app/learned_preferences_storage \
    --env-file /opt/app/.env \
    533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest

echo "EC2 setup complete! Application should be running on port 8000."
```

### 1.6 Launch Instance
- Review all settings
- Click **"Launch Instance"**
- Wait for instance to be in **"Running"** state (2-3 minutes)

## 🔧 Step 2: Configure Environment Variables

### 2.1 Connect to Your Instance
1. Select your instance in EC2 console
2. Click **"Connect"**
3. Choose **"EC2 Instance Connect"** (browser-based SSH)
4. Click **"Connect"**

### 2.2 Edit Environment File
Once connected to your instance:

```bash
# Edit the environment file
sudo nano /opt/app/.env
```

**Replace these placeholders with your actual values:**

```bash
# Azure OpenAI Configuration (REQUIRED)
AZURE_OAI_ENDPOINT=https://YOUR-RESOURCE-NAME.openai.azure.com/
AZURE_OAI_KEY=YOUR-ACTUAL-API-KEY
AZURE_OAI_DEPLOYMENT_NAME=YOUR-GPT-DEPLOYMENT-NAME
AZURE_OAI_API_VERSION=2024-02-15-preview

# S3 Configuration (Optional)
S3_BUCKET_NAME=your-actual-s3-bucket-name

# External APIs (Optional)
INVOICE_VALIDATION_API_URL=your-actual-validation-api-url
INVOICE_VALIDATION_API_KEY=your-actual-validation-api-key
```

**Save and exit:** Press `Ctrl+X`, then `Y`, then `Enter`

### 2.3 Restart Application
```bash
# Restart the Docker container to pick up new environment variables
sudo docker restart vendor-statements-app
```

## 🧪 Step 3: Test Your Application

### 3.1 Get Your Instance IP
1. Go back to EC2 console
2. Select your instance
3. Copy the **"Public IPv4 address"**

### 3.2 Test Health Endpoints
Open these URLs in your browser:

- **Main App:** `http://YOUR-INSTANCE-IP:8000`
- **Health Check:** `http://YOUR-INSTANCE-IP:8000/health`
- **Detailed Health:** `http://YOUR-INSTANCE-IP:8000/healthz`

### 3.3 Test File Upload
1. Go to `http://YOUR-INSTANCE-IP:8000`
2. Try uploading a CSV or Excel file
3. Check if AI field mapping works

## 🔍 Step 4: Troubleshooting

### 4.1 Check Application Logs
```bash
# View application logs
sudo docker logs vendor-statements-app

# Follow logs in real-time
sudo docker logs -f vendor-statements-app
```

### 4.2 Check Container Status
```bash
# Check if container is running
sudo docker ps

# If container is not running, check what happened
sudo docker ps -a
```

### 4.3 Restart Application
```bash
# Stop container
sudo docker stop vendor-statements-app

# Remove container
sudo docker rm vendor-statements-app

# Run new container
sudo docker run -d \
    --name vendor-statements-app \
    --restart unless-stopped \
    -p 8000:8000 \
    -v /opt/app-data/uploads:/app/uploads \
    -v /opt/app-data/templates:/app/templates_storage \
    -v /opt/app-data/preferences:/app/learned_preferences_storage \
    --env-file /opt/app/.env \
    533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest
```

## 🔐 Step 5: Security Best Practices

### 5.1 Restrict Security Group (Optional)
- Edit security group to allow SSH only from your IP
- Keep ports 80, 443, 8000 open for application access

### 5.2 Set up SSL (Optional)
- Use AWS Certificate Manager for SSL certificate
- Set up Application Load Balancer for HTTPS

## 💰 Step 6: Cost Management

### 6.1 Monitor Costs
- Check AWS Billing Dashboard regularly
- Set up billing alerts

### 6.2 Stop Instance When Not Needed
- **Stop** (not terminate) instance to save costs
- **Start** when you need to use it
- You only pay for running time

## 🔄 Step 7: Updates and Maintenance

### 7.1 Update Application
```bash
# Pull latest image
sudo docker pull 533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest

# Restart with new image
sudo docker stop vendor-statements-app
sudo docker rm vendor-statements-app
# Run the docker run command from Step 4.3
```

### 7.2 Backup Data
- Your uploaded files are in `/opt/app-data/uploads`
- Templates are in `/opt/app-data/templates`
- Consider setting up S3 backup

## 🎉 Success Indicators

✅ **Instance is running** in EC2 console  
✅ **Health check returns 200** at `http://YOUR-IP:8000/health`  
✅ **Main page loads** at `http://YOUR-IP:8000`  
✅ **File upload works** and shows field mappings  
✅ **AI features work** (if Azure OpenAI is configured)  

## 📞 Need Help?

If you encounter issues:
1. Check the application logs first
2. Verify environment variables are set correctly
3. Ensure security group allows traffic on port 8000
4. Check if Docker container is running