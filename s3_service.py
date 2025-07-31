"""
AWS S3 Service for handling file and template storage
"""
import os
import boto3
import logging
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, List, Dict, Any
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        """Initialize S3 service with configuration from environment variables"""
        self.bucket_name = os.getenv('AWS_S3_BUCKET_NAME')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.templates_prefix = os.getenv('S3_TEMPLATES_PREFIX', 'templates/')
        self.uploads_prefix = os.getenv('S3_UPLOADS_PREFIX', 'uploads/')
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            
            # Test connection if bucket is configured
            if self.bucket_name:
                self._test_connection()
                logger.info(f"S3 service initialized successfully for bucket: {self.bucket_name}")
            else:
                logger.warning("S3_BUCKET_NAME not configured. S3 functionality will be disabled.")
                
        except NoCredentialsError:
            logger.error("AWS credentials not found. S3 functionality will be disabled.")
            self.s3_client = None
        except Exception as e:
            logger.error(f"Error initializing S3 service: {e}")
            self.s3_client = None
    
    def _test_connection(self):
        """Test S3 connection and bucket access"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Successfully connected to S3 bucket: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f"S3 bucket '{self.bucket_name}' does not exist")
            elif error_code == '403':
                logger.error(f"Access denied to S3 bucket '{self.bucket_name}'")
            else:
                logger.error(f"Error accessing S3 bucket '{self.bucket_name}': {e}")
            raise
    
    def is_enabled(self) -> bool:
        """Check if S3 service is properly configured and enabled"""
        return self.s3_client is not None and self.bucket_name is not None
    
    # Template Management Methods
    def upload_template(self, template_name: str, template_data: Dict[str, Any]) -> bool:
        """Upload a template to S3"""
        if not self.is_enabled():
            logger.warning("S3 service not enabled. Cannot upload template.")
            return False
        
        try:
            key = f"{self.templates_prefix}{template_name}.json"
            template_json = json.dumps(template_data, indent=2)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=template_json,
                ContentType='application/json',
                Metadata={
                    'uploaded_at': datetime.utcnow().isoformat(),
                    'template_name': template_data.get('template_name', template_name)
                }
            )
            
            logger.info(f"Successfully uploaded template '{template_name}' to S3")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading template '{template_name}' to S3: {e}")
            return False
    
    def download_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Download a template from S3"""
        if not self.is_enabled():
            logger.warning("S3 service not enabled. Cannot download template.")
            return None
        
        try:
            key = f"{self.templates_prefix}{template_name}.json"
            
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            template_data = json.loads(response['Body'].read().decode('utf-8'))
            
            logger.info(f"Successfully downloaded template '{template_name}' from S3")
            return template_data
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.info(f"Template '{template_name}' not found in S3")
            else:
                logger.error(f"Error downloading template '{template_name}' from S3: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading template '{template_name}' from S3: {e}")
            return None
    
    def list_templates(self) -> List[str]:
        """List all templates in S3"""
        if not self.is_enabled():
            logger.warning("S3 service not enabled. Cannot list templates.")
            return []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.templates_prefix
            )
            
            templates = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Extract template name from key (remove prefix and .json extension)
                    key = obj['Key']
                    if key.endswith('.json'):
                        template_name = key[len(self.templates_prefix):-5]  # Remove prefix and .json
                        templates.append(template_name)
            
            logger.info(f"Found {len(templates)} templates in S3")
            return templates
            
        except Exception as e:
            logger.error(f"Error listing templates from S3: {e}")
            return []
    
    def delete_template(self, template_name: str) -> bool:
        """Delete a template from S3"""
        if not self.is_enabled():
            logger.warning("S3 service not enabled. Cannot delete template.")
            return False
        
        try:
            key = f"{self.templates_prefix}{template_name}.json"
            
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            
            logger.info(f"Successfully deleted template '{template_name}' from S3")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting template '{template_name}' from S3: {e}")
            return False
    
    # File Management Methods
    def upload_file(self, file_path: str, s3_key: str = None) -> Optional[str]:
        """Upload a file to S3"""
        if not self.is_enabled():
            logger.warning("S3 service not enabled. Cannot upload file.")
            return None
        
        try:
            if s3_key is None:
                filename = os.path.basename(file_path)
                s3_key = f"{self.uploads_prefix}{filename}"
            
            # Determine content type based on file extension
            content_type = self._get_content_type(file_path)
            
            with open(file_path, 'rb') as file_data:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=file_data,
                    ContentType=content_type,
                    Metadata={
                        'uploaded_at': datetime.utcnow().isoformat(),
                        'original_filename': os.path.basename(file_path)
                    }
                )
            
            logger.info(f"Successfully uploaded file '{file_path}' to S3 as '{s3_key}'")
            return s3_key
            
        except Exception as e:
            logger.error(f"Error uploading file '{file_path}' to S3: {e}")
            return None
    
    def download_file(self, s3_key: str, local_path: str) -> bool:
        """Download a file from S3"""
        if not self.is_enabled():
            logger.warning("S3 service not enabled. Cannot download file.")
            return False
        
        try:
            # Ensure local directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            
            logger.info(f"Successfully downloaded file '{s3_key}' from S3 to '{local_path}'")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading file '{s3_key}' from S3: {e}")
            return False
    
    def delete_file(self, s3_key: str) -> bool:
        """Delete a file from S3"""
        if not self.is_enabled():
            logger.warning("S3 service not enabled. Cannot delete file.")
            return False
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            
            logger.info(f"Successfully deleted file '{s3_key}' from S3")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file '{s3_key}' from S3: {e}")
            return False
    
    def list_files(self, prefix: str = None) -> List[Dict[str, Any]]:
        """List files in S3 with optional prefix filter"""
        if not self.is_enabled():
            logger.warning("S3 service not enabled. Cannot list files.")
            return []
        
        try:
            list_prefix = prefix or self.uploads_prefix
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=list_prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'filename': os.path.basename(obj['Key'])
                    })
            
            logger.info(f"Found {len(files)} files in S3 with prefix '{list_prefix}'")
            return files
            
        except Exception as e:
            logger.error(f"Error listing files from S3: {e}")
            return []
    
    def get_file_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for file access"""
        if not self.is_enabled():
            logger.warning("S3 service not enabled. Cannot generate file URL.")
            return None
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned URL for '{s3_key}' (expires in {expiration}s)")
            return url
            
        except Exception as e:
            logger.error(f"Error generating presigned URL for '{s3_key}': {e}")
            return None
    
    def _get_content_type(self, file_path: str) -> str:
        """Determine content type based on file extension"""
        extension = os.path.splitext(file_path)[1].lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.csv': 'text/csv',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
            '.json': 'application/json',
            '.txt': 'text/plain'
        }
        return content_types.get(extension, 'application/octet-stream')

# Global S3 service instance
s3_service = S3Service()