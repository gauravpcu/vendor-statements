#!/bin/bash
# Create IAM role for EC2 to access ECR

ROLE_NAME="VendorStatementsEC2Role"
POLICY_NAME="VendorStatementsECRPolicy"
INSTANCE_ID="i-0a164611259120944"

echo "🔐 Creating IAM role for EC2 ECR access..."

# Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create ECR access policy
cat > ecr-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create IAM role
echo "Creating IAM role..."
aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://trust-policy.json || echo "Role may already exist"

# Create and attach policy
echo "Creating and attaching policy..."
aws iam put-role-policy --role-name $ROLE_NAME --policy-name $POLICY_NAME --policy-document file://ecr-policy.json

# Create instance profile
echo "Creating instance profile..."
aws iam create-instance-profile --instance-profile-name $ROLE_NAME || echo "Instance profile may already exist"

# Add role to instance profile
echo "Adding role to instance profile..."
aws iam add-role-to-instance-profile --instance-profile-name $ROLE_NAME --role-name $ROLE_NAME || echo "Role may already be added"

# Wait for role to be ready
echo "Waiting for role to be ready..."
sleep 10

# Attach instance profile to EC2 instance
echo "Attaching instance profile to EC2 instance..."
aws ec2 associate-iam-instance-profile --instance-id $INSTANCE_ID --iam-instance-profile Name=$ROLE_NAME

echo "✅ IAM role setup complete!"

# Cleanup
rm -f trust-policy.json ecr-policy.json