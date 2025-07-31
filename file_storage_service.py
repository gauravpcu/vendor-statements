import os
import boto3
import logging
from botocore.exceptions import ClientError
import io
import uuid
import json

logger = logging.getLogger('upload_history')

class FileStorageService:
    """
    Service to handle file storage in either local filesystem or AWS S3.
    """
    
    def __init__(self):
        """Initialize the file storage service"""
        self.is_lambda = os.environ.get('AWS_EXECUTION_ENV') is not None
        self.s3_bucket = os.environ.get('S3_BUCKET_NAME')
        self.s3 = boto3.client('s3') if self.is_lambda else None
        
        # Local storage paths
        self.upload_folder = 'uploads'
        self.templates_dir = 'templates_storage'
        self.preferences_dir = 'learned_preferences_storage'
        
        # Create local directories if not in Lambda environment
        if not self.is_lambda:
            os.makedirs(self.upload_folder, exist_ok=True)
            os.makedirs(self.templates_dir, exist_ok=True)
            os.makedirs(self.preferences_dir, exist_ok=True)
        
    async def save_uploaded_file(self, file, filename):
        """
        Save an uploaded file to either local storage or S3.
        
        Args:
            file: UploadFile object from FastAPI
            filename: Name to save the file as
            
        Returns:
            str: The path or S3 key of the saved file
        """
        if self.is_lambda:
            # AWS Lambda - Save to S3
            try:
                file_content = await file.read()
                s3_key = f"uploads/{filename}"
                self.s3.put_object(
                    Bucket=self.s3_bucket,
                    Key=s3_key,
                    Body=file_content
                )
                return s3_key
            except ClientError as e:
                logger.error(f"Error saving file to S3: {e}")
                raise Exception(f"Error saving file to S3: {e}")
        else:
            # Local environment - Save to filesystem
            file_path = os.path.join(self.upload_folder, filename)
            with open(file_path, "wb") as f:
                f.write(await file.read())
            return file_path
    
    def get_file_content(self, file_path_or_key):
        """
        Get the content of a file from either local storage or S3.
        
        Args:
            file_path_or_key: The local path or S3 key of the file
            
        Returns:
            bytes: The content of the file
        """
        if self.is_lambda and not os.path.isfile(file_path_or_key):
            # AWS Lambda - Get from S3
            try:
                # If the full path was passed, extract just the key part
                if file_path_or_key.startswith(self.upload_folder):
                    s3_key = file_path_or_key
                else:
                    s3_key = f"uploads/{os.path.basename(file_path_or_key)}"
                
                s3_response = self.s3.get_object(
                    Bucket=self.s3_bucket,
                    Key=s3_key
                )
                return s3_response['Body'].read()
            except ClientError as e:
                logger.error(f"Error retrieving file from S3: {e}")
                raise Exception(f"Error retrieving file from S3: {e}")
        else:
            # Local environment - Read from filesystem
            with open(file_path_or_key, "rb") as f:
                return f.read()
    
    def save_template(self, template_data, template_name):
        """
        Save a template to either local storage or S3.
        
        Args:
            template_data: Dictionary containing template data
            template_name: Name of the template file
            
        Returns:
            str: The path or S3 key of the saved template
        """
        json_data = json.dumps(template_data, indent=2)
        
        if self.is_lambda:
            # AWS Lambda - Save to S3
            try:
                s3_key = f"templates_storage/{template_name}"
                self.s3.put_object(
                    Bucket=self.s3_bucket,
                    Key=s3_key,
                    Body=json_data,
                    ContentType="application/json"
                )
                return s3_key
            except ClientError as e:
                logger.error(f"Error saving template to S3: {e}")
                raise Exception(f"Error saving template to S3: {e}")
        else:
            # Local environment - Save to filesystem
            template_path = os.path.join(self.templates_dir, template_name)
            with open(template_path, "w", encoding="utf-8") as f:
                f.write(json_data)
            return template_path
    
    def list_templates(self):
        """
        List available templates from either local storage or S3.
        
        Returns:
            list: List of template filenames
        """
        if self.is_lambda:
            # AWS Lambda - List from S3
            try:
                response = self.s3.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix="templates_storage/"
                )
                templates = []
                if 'Contents' in response:
                    for item in response['Contents']:
                        key = item['Key']
                        if key.endswith('.json'):
                            templates.append(os.path.basename(key))
                return templates
            except ClientError as e:
                logger.error(f"Error listing templates from S3: {e}")
                raise Exception(f"Error listing templates from S3: {e}")
        else:
            # Local environment - List from filesystem
            try:
                return [f for f in os.listdir(self.templates_dir) if f.endswith('.json')]
            except Exception as e:
                logger.error(f"Error listing templates from local filesystem: {e}")
                return []
    
    def get_template(self, template_name):
        """
        Get a template from either local storage or S3.
        
        Args:
            template_name: Name of the template file
            
        Returns:
            dict: The template data
        """
        if self.is_lambda:
            # AWS Lambda - Get from S3
            try:
                s3_key = f"templates_storage/{template_name}"
                s3_response = self.s3.get_object(
                    Bucket=self.s3_bucket,
                    Key=s3_key
                )
                template_content = s3_response['Body'].read().decode('utf-8')
                return json.loads(template_content)
            except ClientError as e:
                logger.error(f"Error retrieving template from S3: {e}")
                raise Exception(f"Error retrieving template from S3: {e}")
        else:
            # Local environment - Get from filesystem
            template_path = os.path.join(self.templates_dir, template_name)
            try:
                with open(template_path, "r", encoding="utf-8") as f:
                    return json.loads(f.read())
            except Exception as e:
                logger.error(f"Error retrieving template from local filesystem: {e}")
                raise Exception(f"Error retrieving template from local filesystem: {e}")

# Create a global instance
file_storage = FileStorageService()
