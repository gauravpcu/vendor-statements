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

# Download environment file from deployment
# Note: The environment file will be uploaded during deployment

# Set environment file permissions
chown ec2-user:ec2-user /opt/app/.env
chmod 600 /opt/app/.env

# Login to ECR
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

# Create a simple health check script
cat > /opt/app/health-check.sh << 'EOF'
#!/bin/bash
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ $response -eq 200 ]; then
    echo "$(date): Health check passed"
    exit 0
else
    echo "$(date): Health check failed with status $response"
    exit 1
fi
EOF

chmod +x /opt/app/health-check.sh

# Set up cron job for health monitoring
echo "*/5 * * * * /opt/app/health-check.sh >> /var/log/health-check.log 2>&1" | crontab -

# Create update script for easy deployments
cat > /opt/app/update-app.sh << 'EOF'
#!/bin/bash
echo "Updating vendor statements processor..."

# Pull latest image
docker pull 533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest

# Stop and remove current container
docker stop vendor-statements-app
docker rm vendor-statements-app

# Start new container
docker run -d \
    --name vendor-statements-app \
    --restart unless-stopped \
    -p 8000:8000 \
    -v /opt/app-data/uploads:/app/uploads \
    -v /opt/app-data/templates:/app/templates_storage \
    -v /opt/app-data/preferences:/app/learned_preferences_storage \
    --env-file /opt/app/.env \
    533267165065.dkr.ecr.us-east-1.amazonaws.com/vendor-statements-processor:latest

echo "Update complete!"
EOF

chmod +x /opt/app/update-app.sh
chown ec2-user:ec2-user /opt/app/update-app.sh

# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent

# Create CloudWatch config
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/health-check.log",
                        "log_group_name": "/aws/ec2/vendor-statements/health",
                        "log_stream_name": "{instance_id}"
                    }
                ]
            }
        }
    },
    "metrics": {
        "namespace": "VendorStatements/EC2",
        "metrics_collected": {
            "cpu": {
                "measurement": [
                    "cpu_usage_idle",
                    "cpu_usage_iowait",
                    "cpu_usage_user",
                    "cpu_usage_system"
                ],
                "metrics_collection_interval": 60
            },
            "disk": {
                "measurement": [
                    "used_percent"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "mem": {
                "measurement": [
                    "mem_used_percent"
                ],
                "metrics_collection_interval": 60
            }
        }
    }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
    -s

echo "EC2 setup complete! Application should be running on port 8000."