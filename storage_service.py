"""
Hybrid Storage Service - supports both local and S3 storage
"""
import os
import json
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import shutil

from s3_service import s3_service
from config.s3_config import S3Config

logger = logging.getLogger(__name__)

class StorageService:
    """Hybrid storage service that can use either local filesystem or S3"""
    
    def __init__(self):
        self.config = S3Config()
        self.use_s3 = self.config.is_s3_enabled()
        
        if self.use_s3:
            logger.info("Storage service initialized with S3 backend")
        else:
            logger.info("Storage service initialized with local filesystem backend")
            # Ensure local directories exist
            os.makedirs(self.config.LOCAL_TEMPLATES_DIR, exist_ok=True)
            os.makedirs(self.config.LOCAL_UPLOADS_DIR, exist_ok=True)
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get current storage configuration info"""
        return {
            'backend': 's3' if self.use_s3 else 'local',
            'config': self.config.get_storage_config(),
            's3_available': s3_service.is_enabled() if self.use_s3 else False
        }
    
    # Template Management Methods
    def save_template(self, template_name: str, template_data: Dict[str, Any]) -> bool:
        """Save a template to storage"""
        try:
            if self.use_s3:
                return s3_service.upload_template(template_name, template_data)
            else:
                return self._save_template_local(template_name, template_data)
        except Exception as e:
            logger.error(f"Error saving template '{template_name}': {e}")
            return False
    
    def load_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Load a template from storage"""
        try:
            if self.use_s3:
                return s3_service.download_template(template_name)
            else:
                return self._load_template_local(template_name)
        except Exception as e:
            logger.error(f"Error loading template '{template_name}': {e}")
            return None
    
    def list_templates(self) -> List[str]:
        """List all available templates"""
        try:
            if self.use_s3:
                return s3_service.list_templates()
            else:
                return self._list_templates_local()
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            return []
    
    def delete_template(self, template_name: str) -> bool:
        """Delete a template from storage"""
        try:
            if self.use_s3:
                return s3_service.delete_template(template_name)
            else:
                return self._delete_template_local(template_name)
        except Exception as e:
            logger.error(f"Error deleting template '{template_name}': {e}")
            return False
    
    def template_exists(self, template_name: str) -> bool:
        """Check if a template exists"""
        if self.use_s3:
            template_data = s3_service.download_template(template_name)
            return template_data is not None
        else:
            template_path = os.path.join(self.config.LOCAL_TEMPLATES_DIR, f"{template_name}.json")
            return os.path.exists(template_path)
    
    # File Management Methods
    def save_file(self, file_path: str, storage_key: str = None) -> Optional[str]:
        """Save a file to storage"""
        try:
            if self.use_s3:
                return s3_service.upload_file(file_path, storage_key)
            else:
                return self._save_file_local(file_path, storage_key)
        except Exception as e:
            logger.error(f"Error saving file '{file_path}': {e}")
            return None
    
    def load_file(self, storage_key: str, local_path: str = None) -> Optional[str]:
        """Load a file from storage to local path"""
        try:
            if self.use_s3:
                if local_path is None:
                    local_path = os.path.join(self.config.LOCAL_UPLOADS_DIR, os.path.basename(storage_key))
                
                if s3_service.download_file(storage_key, local_path):
                    return local_path
                return None
            else:
                # For local storage, storage_key is the file path
                if os.path.exists(storage_key):
                    return storage_key
                return None
        except Exception as e:
            logger.error(f"Error loading file '{storage_key}': {e}")
            return None
    
    def delete_file(self, storage_key: str) -> bool:
        """Delete a file from storage"""
        try:
            if self.use_s3:
                return s3_service.delete_file(storage_key)
            else:
                return self._delete_file_local(storage_key)
        except Exception as e:
            logger.error(f"Error deleting file '{storage_key}': {e}")
            return False
    
    def list_files(self, prefix: str = None) -> List[Dict[str, Any]]:
        """List files in storage"""
        try:
            if self.use_s3:
                return s3_service.list_files(prefix)
            else:
                return self._list_files_local(prefix)
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def get_file_url(self, storage_key: str, expiration: int = None) -> Optional[str]:
        """Get a URL for file access"""
        try:
            if self.use_s3:
                exp = expiration or self.config.PRESIGNED_URL_EXPIRATION
                return s3_service.get_file_url(storage_key, exp)
            else:
                # For local files, return the file path (in production, this would be a web URL)
                return storage_key
        except Exception as e:
            logger.error(f"Error getting file URL for '{storage_key}': {e}")
            return None
    
    def file_exists(self, storage_key: str) -> bool:
        """Check if a file exists in storage"""
        try:
            if self.use_s3:
                # Try to get object metadata
                try:
                    s3_service.s3_client.head_object(Bucket=s3_service.bucket_name, Key=storage_key)
                    return True
                except:
                    return False
            else:
                return os.path.exists(storage_key)
        except Exception as e:
            logger.error(f"Error checking file existence '{storage_key}': {e}")
            return False
    
    # Local Storage Implementation Methods
    def _save_template_local(self, template_name: str, template_data: Dict[str, Any]) -> bool:
        """Save template to local filesystem"""
        template_path = os.path.join(self.config.LOCAL_TEMPLATES_DIR, f"{template_name}.json")
        
        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=2)
            
            logger.info(f"Successfully saved template '{template_name}' locally")
            return True
            
        except Exception as e:
            logger.error(f"Error saving template '{template_name}' locally: {e}")
            return False
    
    def _load_template_local(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Load template from local filesystem"""
        template_path = os.path.join(self.config.LOCAL_TEMPLATES_DIR, f"{template_name}.json")
        
        try:
            if not os.path.exists(template_path):
                return None
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
            
            logger.info(f"Successfully loaded template '{template_name}' locally")
            return template_data
            
        except Exception as e:
            logger.error(f"Error loading template '{template_name}' locally: {e}")
            return None
    
    def _list_templates_local(self) -> List[str]:
        """List templates from local filesystem"""
        try:
            if not os.path.exists(self.config.LOCAL_TEMPLATES_DIR):
                return []
            
            templates = []
            for filename in os.listdir(self.config.LOCAL_TEMPLATES_DIR):
                if filename.endswith('.json'):
                    template_name = filename[:-5]  # Remove .json extension
                    templates.append(template_name)
            
            logger.info(f"Found {len(templates)} templates locally")
            return templates
            
        except Exception as e:
            logger.error(f"Error listing templates locally: {e}")
            return []
    
    def _delete_template_local(self, template_name: str) -> bool:
        """Delete template from local filesystem"""
        template_path = os.path.join(self.config.LOCAL_TEMPLATES_DIR, f"{template_name}.json")
        
        try:
            if os.path.exists(template_path):
                os.remove(template_path)
                logger.info(f"Successfully deleted template '{template_name}' locally")
                return True
            else:
                logger.warning(f"Template '{template_name}' not found locally")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting template '{template_name}' locally: {e}")
            return False
    
    def _save_file_local(self, file_path: str, storage_key: str = None) -> Optional[str]:
        """Save file to local filesystem"""
        try:
            if storage_key is None:
                filename = os.path.basename(file_path)
                storage_key = os.path.join(self.config.LOCAL_UPLOADS_DIR, filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(storage_key), exist_ok=True)
            
            # Copy file if it's not already in the target location
            if os.path.abspath(file_path) != os.path.abspath(storage_key):
                shutil.copy2(file_path, storage_key)
            
            logger.info(f"Successfully saved file locally: {storage_key}")
            return storage_key
            
        except Exception as e:
            logger.error(f"Error saving file '{file_path}' locally: {e}")
            return None
    
    def _delete_file_local(self, storage_key: str) -> bool:
        """Delete file from local filesystem"""
        try:
            if os.path.exists(storage_key):
                os.remove(storage_key)
                logger.info(f"Successfully deleted file locally: {storage_key}")
                return True
            else:
                logger.warning(f"File not found locally: {storage_key}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting file '{storage_key}' locally: {e}")
            return False
    
    def _list_files_local(self, prefix: str = None) -> List[Dict[str, Any]]:
        """List files from local filesystem"""
        try:
            search_dir = prefix or self.config.LOCAL_UPLOADS_DIR
            
            if not os.path.exists(search_dir):
                return []
            
            files = []
            for filename in os.listdir(search_dir):
                file_path = os.path.join(search_dir, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    files.append({
                        'key': file_path,
                        'size': stat.st_size,
                        'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'filename': filename
                    })
            
            logger.info(f"Found {len(files)} files locally in '{search_dir}'")
            return files
            
        except Exception as e:
            logger.error(f"Error listing files locally: {e}")
            return []

# Global storage service instance
storage_service = StorageService()