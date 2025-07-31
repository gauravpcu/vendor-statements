# Quick S3 Setup Guide

## 🚀 Quick Start

### Option 1: Interactive Configuration (Recommended)
```bash
python configure_s3.py
```
This script will guide you through the entire setup process.

### Option 2: Manual Configuration

1. **Get AWS Credentials**:
   - Go to AWS Console → IAM → Users → Your User → Security Credentials
   - Create Access Key if you don't have one
   - Note down Access Key ID and Secret Access Key

2. **Create S3 Bucket**:
   ```bash
   aws s3 mb s3://your-unique-bucket-name --region us-east-1
   ```

3. **Update .env file**:
   ```bash
   # Replace these values in your .env file
   AWS_S3_BUCKET_NAME=your-unique-bucket-name
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=AKIA...
   AWS_SECRET_ACCESS_KEY=your-secret-key
   STORAGE_MODE=s3
   ```

## 📋 Configuration Values

### Bucket Name Suggestions:
- `vendor-statements-[company-name]`
- `procurement-docs-[environment]`
- `invoice-processing-[team]`

**Rules for bucket names**:
- 3-63 characters long
- Only lowercase letters, numbers, hyphens, and periods
- Must start and end with letter or number
- Must be globally unique across all AWS accounts

### Recommended Regions:
- `us-east-1` (N. Virginia) - Default, lowest cost
- `us-west-2` (Oregon) - West Coast
- `eu-west-1` (Ireland) - Europe
- `ap-southeast-1` (Singapore) - Asia Pacific

### Example Configuration:
```bash
# Production Example
AWS_S3_BUCKET_NAME=vendor-statements-prod-acme
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
STORAGE_MODE=s3

# Development Example
AWS_S3_BUCKET_NAME=vendor-statements-dev-acme
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
STORAGE_MODE=local  # Use local for development, s3 for production
```

## 🔧 Testing Your Configuration

1. **Test S3 Setup**:
   ```bash
   python setup_s3.py
   ```

2. **Check Storage Status**:
   ```bash
   curl http://localhost:5000/storage_status
   ```

3. **Test Template Operations**:
   - Upload a file through the web interface
   - Create a template
   - Verify it appears in S3 console

## 🔒 Security Best Practices

### For Development:
- Use IAM user with limited S3 permissions
- Store credentials in .env file (never commit to git)
- Use separate bucket for development

### For Production:
- Use IAM roles instead of access keys
- Enable S3 bucket versioning
- Configure bucket encryption
- Set up CloudTrail logging
- Use VPC endpoints for private access

### Minimum IAM Permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/*"
      ]
    }
  ]
}
```

## 🐛 Troubleshooting

### Common Issues:

1. **"Bucket name already exists"**:
   - S3 bucket names are globally unique
   - Try adding your company name or random suffix
   - Example: `vendor-statements-acme-2024`

2. **"Access Denied"**:
   - Check IAM permissions
   - Verify bucket policy
   - Ensure credentials are correct

3. **"Region mismatch"**:
   - Ensure AWS_REGION matches bucket region
   - Some operations require specific regions

4. **"Storage service not enabled"**:
   - Set `STORAGE_MODE=s3` in .env file
   - Restart the application
   - Check /storage_status endpoint

### Debug Commands:
```bash
# Test AWS CLI access
aws s3 ls

# Test specific bucket
aws s3 ls s3://your-bucket-name

# Check bucket region
aws s3api get-bucket-location --bucket your-bucket-name

# Test credentials
aws sts get-caller-identity
```

## 📊 Monitoring

### Key Metrics to Monitor:
- Storage usage and costs
- API request rates and errors
- Upload/download success rates
- Template operation latency

### AWS CloudWatch Metrics:
- `BucketSizeBytes`
- `NumberOfObjects`
- `AllRequests`
- `4xxErrors`
- `5xxErrors`

## 💰 Cost Optimization

### Storage Classes:
- **Standard**: Frequently accessed files (uploads, active templates)
- **Standard-IA**: Infrequently accessed (archived templates)
- **Glacier**: Long-term archive (old processed files)

### Lifecycle Policies:
```json
{
  "Rules": [
    {
      "Id": "ArchiveOldUploads",
      "Status": "Enabled",
      "Filter": {"Prefix": "uploads/"},
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```

## 🔄 Migration

### From Local to S3:
1. Keep `STORAGE_MODE=local` initially
2. Configure S3 settings
3. Run migration script (if available)
4. Test S3 operations
5. Switch to `STORAGE_MODE=s3`

### Backup Strategy:
- Enable S3 versioning
- Set up cross-region replication
- Regular exports to different storage class
- Monitor backup integrity

## 📞 Support

If you encounter issues:
1. Check the application logs
2. Verify AWS credentials and permissions
3. Test S3 connectivity with AWS CLI
4. Review the troubleshooting section above
5. Check AWS Service Health Dashboard