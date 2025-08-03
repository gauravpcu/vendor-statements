#!/bin/bash
# Check EC2 deployment status

INSTANCE_IP="44.198.169.216"
KEY_PATH="~/.ssh/vendor-statements-key.pem"

echo "🔍 Checking EC2 deployment status..."
echo "Instance IP: $INSTANCE_IP"
echo

# Test connectivity
echo "📡 Testing connectivity..."
if ping -c 1 $INSTANCE_IP > /dev/null 2>&1; then
    echo "✅ Instance is reachable"
else
    echo "❌ Instance is not reachable"
    exit 1
fi

# Test SSH connectivity
echo "🔐 Testing SSH connectivity..."
if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -i $KEY_PATH ec2-user@$INSTANCE_IP 'echo "SSH works"' > /dev/null 2>&1; then
    echo "✅ SSH connection successful"
else
    echo "❌ SSH connection failed"
    echo "💡 Make sure you have the key file at: $KEY_PATH"
    exit 1
fi

# Check Docker status
echo "🐳 Checking Docker status..."
ssh -o StrictHostKeyChecking=no -i $KEY_PATH ec2-user@$INSTANCE_IP 'sudo systemctl status docker --no-pager -l'

echo
echo "📦 Checking Docker containers..."
ssh -o StrictHostKeyChecking=no -i $KEY_PATH ec2-user@$INSTANCE_IP 'sudo docker ps -a'

echo
echo "📊 Checking application logs..."
ssh -o StrictHostKeyChecking=no -i $KEY_PATH ec2-user@$INSTANCE_IP 'sudo docker logs vendor-statements-app --tail 20'

echo
echo "🌐 Testing health endpoints..."
curl -s -w "Status: %{http_code}\n" http://$INSTANCE_IP:8000/health || echo "Health endpoint not responding"
curl -s -w "Status: %{http_code}\n" http://$INSTANCE_IP:8000/healthz || echo "Detailed health endpoint not responding"

echo
echo "💾 Checking system resources..."
ssh -o StrictHostKeyChecking=no -i $KEY_PATH ec2-user@$INSTANCE_IP 'free -h && df -h'