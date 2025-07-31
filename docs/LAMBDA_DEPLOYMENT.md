# AWS Lambda Deployment Guide

This guide walks you through deploying the Vendor Statements application to AWS Lambda using AWS SAM (Serverless Application Model).

## 🚀 Quick Start

### Prerequisites

1. **AWS CLI** - [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
2. **AWS SAM CLI** - [Install SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
3. **Docker** - [Install Docker](https://docs.docker.com/get-docker/) (for building Lambda packages)
4. **AWS Account** with appropriate permissions

### One-Command Deployment

```bash
chmod +x deploy_lambda.sh
./deploy_lambda.sh
```

The script will guide you through the configuration and deploy everything automatically.

## 📋 Manual Deployment Steps

### 1. Configure AWS Credentials

```bash
aws configure
```

Provide your AWS Access Key ID, Secret Access Key, and default region.

### 2. Set Environment Variables

Create a `.env` file or set these environment variables:

```bash
# Required for deployment
AWS_REGION=us-east-1
AZURE_OAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OAI_KEY=your-azure-openai-key
AZURE_OAI_DEPLOYMENT_NAME=gpt-4o
```

### 3. Build the Application

```bash
sam build --template template.yaml --use-container
```

### 4. Deploy to AWS

```bash
sam deploy --guided
```

Follow the prompts to configure:
- Stack name: `vendor-statements-app`
- AWS Region: `us-east-1`
- Stage name: `prod`
- S3 bucket name: `vendor-statements-your-company-prod`

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway   │────│  Lambda Function │────│   S3 Storage    │
│                 │    │                  │    │                 │
│ • HTTP Routing  │    │ • Flask App      │    │ • Templates     │
│ • CORS Support  │    │ • File Processing│    │ • Uploaded Files│
│ • Binary Data   │    │ • AI Mapping     │    │ • Processed Data│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                       ┌──────────────────┐
                       │  Azure OpenAI    │
                       │                  │
                       │ • Header Mapping │
                       │ • AI Suggestions │
                       └──────────────────┘
```

## 📦 What Gets Deployed

### AWS Resources Created:

1. **Lambda Function**
   - Runtime: Python 3.11
   - Memory: 2048 MB
   - Timeout: 5 minutes
   - Environment variables for configuration

2. **API Gateway**
   - REST API with CORS enabled
   - Binary media type support for file uploads
   - Custom domain support (optional)

3. **S3 Bucket**
   - Versioning enabled
   - CORS configuration
   - Lifecycle policies for cost optimization
   - Organized folder structure

4. **IAM Roles & Policies**
   - Lambda execution role
   - S3 read/write permissions
   - CloudWatch logging permissions

5. **CloudWatch Log Group**
   - 14-day retention policy
   - Structured logging

## 🔧 Configuration

### Environment Variables

The Lambda function is configured with these environment variables:

```yaml
AWS_S3_BUCKET_NAME: your-bucket-name
AWS_REGION: us-east-1
STORAGE_MODE: s3
S3_TEMPLATES_PREFIX: templates/
S3_UPLOADS_PREFIX: uploads/
S3_PROCESSED_PREFIX: processed/
S3_CACHE_PREFIX: cache/
MAX_FILE_SIZE: 50
PRESIGNED_URL_EXPIRATION: 3600
AZURE_OAI_ENDPOINT: https://your-endpoint.openai.azure.com/
AZURE_OAI_KEY: your-api-key
AZURE_OAI_DEPLOYMENT_NAME: gpt-4o
AZURE_OAI_API_VERSION: 2024-12-01-preview
LAMBDA_ENVIRONMENT: true
```

### Lambda Optimizations

The application includes Lambda-specific optimizations:

- **Temporary Storage**: Uses `/tmp` for file processing
- **Memory Management**: Optimized garbage collection
- **Reduced Limits**: Smaller file sizes and upload limits
- **S3 Integration**: Automatic S3 storage configuration
- **Logging**: Structured logging for CloudWatch

## 🧪 Testing the Deployment

### 1. Health Check

```bash
curl https://your-api-url/health
```

Expected response: `200 OK`

### 2. Storage Status

```bash
curl https://your-api-url/storage_status
```

Should show S3 backend configuration.

### 3. Upload Test

Visit the web application URL and try uploading a test file to verify:
- File upload works
- AI header mapping functions
- Template saving works
- S3 storage is operational

## 📊 Monitoring & Debugging

### CloudWatch Logs

View logs in AWS Console:
```
/aws/lambda/vendor-statements-app-VendorStatementsFunction-*
```

### Common Issues & Solutions

#### 1. **Cold Start Timeouts**
- **Issue**: First request takes too long
- **Solution**: Consider provisioned concurrency for production

#### 2. **File Upload Failures**
- **Issue**: Large files fail to upload
- **Solution**: Check API Gateway limits (10MB max)

#### 3. **S3 Permission Errors**
- **Issue**: Cannot read/write to S3
- **Solution**: Verify IAM permissions in template.yaml

#### 4. **Azure OpenAI Errors**
- **Issue**: AI mapping not working
- **Solution**: Check Azure OpenAI credentials and endpoint

### Performance Monitoring

Key metrics to monitor:
- **Duration**: Function execution time
- **Memory Usage**: Peak memory consumption
- **Error Rate**: Failed invocations
- **Cold Starts**: Initialization time

## 🔄 Updates & Maintenance

### Updating the Application

1. Make changes to your code
2. Run the deployment script again:
   ```bash
   ./deploy_lambda.sh
   ```

### Rolling Back

```bash
aws cloudformation delete-stack --stack-name vendor-statements-app
```

### Scaling Considerations

- **Concurrent Executions**: Default limit is 1000
- **Memory**: Increase for better performance
- **Timeout**: Adjust based on file processing needs
- **Storage**: S3 scales automatically

## 💰 Cost Optimization

### Lambda Costs
- **Requests**: $0.20 per 1M requests
- **Duration**: $0.0000166667 per GB-second
- **Typical cost**: ~$5-20/month for moderate usage

### S3 Costs
- **Storage**: ~$0.023 per GB/month
- **Requests**: Minimal for typical usage
- **Data Transfer**: Free within same region

### Cost Reduction Tips
1. Use S3 lifecycle policies (already configured)
2. Monitor and adjust Lambda memory allocation
3. Implement request caching where appropriate
4. Use S3 Intelligent Tiering for long-term storage

## 🔒 Security Best Practices

### Implemented Security Features
- ✅ IAM roles with least privilege
- ✅ S3 bucket encryption
- ✅ CORS properly configured
- ✅ No hardcoded secrets
- ✅ CloudWatch logging enabled

### Additional Security Recommendations
- Use AWS Secrets Manager for sensitive data
- Implement API authentication (API Keys/Cognito)
- Enable AWS CloudTrail for audit logging
- Set up AWS Config for compliance monitoring
- Use VPC endpoints for private S3 access

## 🆘 Support & Troubleshooting

### Getting Help

1. **Check CloudWatch Logs** for detailed error messages
2. **Review SAM deployment logs** for infrastructure issues
3. **Test individual components** (S3, Lambda, API Gateway)
4. **Verify environment variables** are set correctly

### Common Commands

```bash
# View stack status
aws cloudformation describe-stacks --stack-name vendor-statements-app

# View Lambda function
aws lambda get-function --function-name vendor-statements-app-VendorStatementsFunction-*

# View S3 bucket
aws s3 ls s3://your-bucket-name --recursive

# Tail logs
sam logs --stack-name vendor-statements-app --tail
```

## 🎯 Production Readiness Checklist

- [ ] Custom domain configured
- [ ] SSL certificate installed
- [ ] Monitoring and alerting set up
- [ ] Backup strategy implemented
- [ ] Security review completed
- [ ] Performance testing done
- [ ] Documentation updated
- [ ] Team training completed

---

Your Vendor Statements application is now ready for production deployment on AWS Lambda! 🚀