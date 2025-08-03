#!/bin/bash
# Script to resize EC2 instance disk

INSTANCE_ID=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=vendor-statements-processor" "Name=instance-state-name,Values=running,stopped" \
    --query 'Reservations[0].Instances[0].InstanceId' \
    --output text \
    --region us-east-1)

if [ "$INSTANCE_ID" = "None" ]; then
    echo "❌ No instance found"
    exit 1
fi

echo "🔍 Found instance: $INSTANCE_ID"

# Get the volume ID
VOLUME_ID=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region us-east-1 \
    --query 'Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId' \
    --output text)

echo "💾 Volume ID: $VOLUME_ID"

# Resize volume to 32GB
echo "📈 Resizing volume to 32GB..."
aws ec2 modify-volume --volume-id $VOLUME_ID --size 32 --region us-east-1

echo "✅ Volume resize initiated. Waiting for completion..."
aws ec2 wait volume-in-use --volume-ids $VOLUME_ID --region us-east-1

echo "🔄 Now SSH into the instance and run:"
echo "sudo growpart /dev/nvme0n1 1"
echo "sudo resize2fs /dev/nvme0n1p1"
