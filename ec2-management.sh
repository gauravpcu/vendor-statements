#!/bin/bash
# EC2 Management Script for Vendor Statements Processor

set -e

REGION="us-east-1"
INSTANCE_NAME="vendor-statements-processor"

# Function to get instance ID by name
get_instance_id() {
    aws ec2 describe-instances \
        --filters "Name=tag:Name,Values=$INSTANCE_NAME" "Name=instance-state-name,Values=running,stopped" \
        --query 'Reservations[0].Instances[0].InstanceId' \
        --output text \
        --region $REGION 2>/dev/null || echo "None"
}

# Function to get instance info
get_instance_info() {
    local instance_id=$1
    aws ec2 describe-instances \
        --instance-ids $instance_id \
        --region $REGION \
        --query 'Reservations[0].Instances[0]' 2>/dev/null
}

# Function to show usage
show_usage() {
    echo "Usage: $0 {start|stop|restart|status|logs|ssh|update|terminate}"
    echo ""
    echo "Commands:"
    echo "  start     - Start the EC2 instance"
    echo "  stop      - Stop the EC2 instance"
    echo "  restart   - Restart the EC2 instance"
    echo "  status    - Show instance status and details"
    echo "  logs      - Show application logs"
    echo "  ssh       - SSH into the instance"
    echo "  update    - Update the application to latest version"
    echo "  terminate - Terminate the instance (DESTRUCTIVE)"
}

# Get instance ID
INSTANCE_ID=$(get_instance_id)

if [ "$INSTANCE_ID" = "None" ]; then
    echo "❌ No instance found with name: $INSTANCE_NAME"
    echo "💡 Run ./deploy-ec2.sh to create a new instance"
    exit 1
fi

case "$1" in
    start)
        echo "🚀 Starting instance $INSTANCE_ID..."
        aws ec2 start-instances --instance-ids $INSTANCE_ID --region $REGION
        echo "⏳ Waiting for instance to be running..."
        aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION
        
        # Get public IP
        PUBLIC_IP=$(aws ec2 describe-instances \
            --instance-ids $INSTANCE_ID \
            --region $REGION \
            --query 'Reservations[0].Instances[0].PublicIpAddress' \
            --output text)
        
        echo "✅ Instance started!"
        echo "🌐 Public IP: $PUBLIC_IP"
        echo "🔗 Application URL: http://$PUBLIC_IP:8000"
        ;;
    
    stop)
        echo "🛑 Stopping instance $INSTANCE_ID..."
        aws ec2 stop-instances --instance-ids $INSTANCE_ID --region $REGION
        echo "⏳ Waiting for instance to stop..."
        aws ec2 wait instance-stopped --instance-ids $INSTANCE_ID --region $REGION
        echo "✅ Instance stopped!"
        ;;
    
    restart)
        echo "🔄 Restarting instance $INSTANCE_ID..."
        aws ec2 reboot-instances --instance-ids $INSTANCE_ID --region $REGION
        echo "⏳ Waiting for instance to be running..."
        sleep 30
        aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION
        echo "✅ Instance restarted!"
        ;;
    
    status)
        echo "📊 Instance Status for $INSTANCE_NAME"
        echo "=================================="
        
        INSTANCE_INFO=$(get_instance_info $INSTANCE_ID)
        STATE=$(echo $INSTANCE_INFO | jq -r '.State.Name')
        INSTANCE_TYPE=$(echo $INSTANCE_INFO | jq -r '.InstanceType')
        PUBLIC_IP=$(echo $INSTANCE_INFO | jq -r '.PublicIpAddress // "N/A"')
        PRIVATE_IP=$(echo $INSTANCE_INFO | jq -r '.PrivateIpAddress // "N/A"')
        LAUNCH_TIME=$(echo $INSTANCE_INFO | jq -r '.LaunchTime')
        
        echo "Instance ID: $INSTANCE_ID"
        echo "State: $STATE"
        echo "Type: $INSTANCE_TYPE"
        echo "Public IP: $PUBLIC_IP"
        echo "Private IP: $PRIVATE_IP"
        echo "Launch Time: $LAUNCH_TIME"
        
        if [ "$STATE" = "running" ] && [ "$PUBLIC_IP" != "N/A" ]; then
            echo ""
            echo "🔗 Application URLs:"
            echo "Main App: http://$PUBLIC_IP:8000"
            echo "Health Check: http://$PUBLIC_IP:8000/health"
            echo "Detailed Health: http://$PUBLIC_IP:8000/healthz"
            
            echo ""
            echo "🔍 Testing connectivity..."
            if curl -f -s "http://$PUBLIC_IP:8000/health" > /dev/null; then
                echo "✅ Application is responding"
            else
                echo "❌ Application is not responding"
            fi
        fi
        ;;
    
    logs)
        INSTANCE_INFO=$(get_instance_info $INSTANCE_ID)
        STATE=$(echo $INSTANCE_INFO | jq -r '.State.Name')
        
        if [ "$STATE" != "running" ]; then
            echo "❌ Instance is not running. Current state: $STATE"
            exit 1
        fi
        
        PUBLIC_IP=$(echo $INSTANCE_INFO | jq -r '.PublicIpAddress')
        echo "📋 Fetching application logs from $PUBLIC_IP..."
        
        # You'll need to have your SSH key available
        echo "Docker container logs:"
        ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@$PUBLIC_IP \
            'sudo docker logs --tail 50 vendor-statements-app'
        ;;
    
    ssh)
        INSTANCE_INFO=$(get_instance_info $INSTANCE_ID)
        STATE=$(echo $INSTANCE_INFO | jq -r '.State.Name')
        
        if [ "$STATE" != "running" ]; then
            echo "❌ Instance is not running. Current state: $STATE"
            exit 1
        fi
        
        PUBLIC_IP=$(echo $INSTANCE_INFO | jq -r '.PublicIpAddress')
        echo "🔐 Connecting to $PUBLIC_IP..."
        
        # You'll need to have your SSH key available
        ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@$PUBLIC_IP
        ;;
    
    update)
        INSTANCE_INFO=$(get_instance_info $INSTANCE_ID)
        STATE=$(echo $INSTANCE_INFO | jq -r '.State.Name')
        
        if [ "$STATE" != "running" ]; then
            echo "❌ Instance is not running. Current state: $STATE"
            exit 1
        fi
        
        PUBLIC_IP=$(echo $INSTANCE_INFO | jq -r '.PublicIpAddress')
        echo "🔄 Updating application on $PUBLIC_IP..."
        
        # Build and push latest image
        echo "🐳 Building and pushing latest Docker image..."
        ./deploy_to_ecr.sh
        
        # Update application on EC2
        echo "📦 Updating application on EC2..."
        ssh -o StrictHostKeyChecking=no -i ~/.ssh/vendor-statements-key.pem ec2-user@$PUBLIC_IP \
            'sudo /opt/app/update-app.sh'
        
        echo "✅ Application updated!"
        echo "🔗 Application URL: http://$PUBLIC_IP:8000"
        ;;
    
    terminate)
        echo "⚠️  WARNING: This will permanently delete the instance and all data!"
        echo "Instance ID: $INSTANCE_ID"
        read -p "Are you sure you want to terminate this instance? (yes/no): " confirm
        
        if [ "$confirm" = "yes" ]; then
            echo "🗑️  Terminating instance $INSTANCE_ID..."
            aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $REGION
            echo "✅ Instance termination initiated"
        else
            echo "❌ Termination cancelled"
        fi
        ;;
    
    *)
        show_usage
        exit 1
        ;;
esac