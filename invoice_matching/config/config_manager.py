"""
Configuration manager for invoice matching system.

Handles secure storage and retrieval of database and API connection
configurations with encryption for sensitive credentials.
"""

import os
import json
import time
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

from invoice_matching.models import (
    SQLConnectionConfig, APIConnectionConfig, ConnectionTestResult,
    MatchingSettings, ConnectionType, ConfigurationError
)
from .encryption import CredentialEncryption, EncryptionError

import logging
logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages configuration storage and retrieval for invoice matching system.
    
    Provides secure storage of connection configurations with credential encryption,
    validation, and backup/restore capabilities.
    """
    
    def __init__(self, config_dir: Optional[str] = None, encryption_key: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory to store configuration files. If None, uses default.
            encryption_key: Optional encryption key for credentials.
        """
        self.logger = logging.getLogger(f"{__name__}.ConfigManager")
        
        # Setup configuration directory
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / '.invoice_matching' / 'config'
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup encryption
        self.encryption = CredentialEncryption(encryption_key)
        
        # Configuration file paths
        self.connections_file = self.config_dir / 'connections.json'
        self.settings_file = self.config_dir / 'settings.json'
        self.backup_dir = self.config_dir / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"Configuration manager initialized with directory: {self.config_dir}")
    
    def save_connection_config(self, config: Union[SQLConnectionConfig, APIConnectionConfig]) -> bool:
        """
        Save a connection configuration with encrypted credentials.
        
        Args:
            config: Connection configuration to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Load existing connections
            connections = self._load_connections_file()
            
            # Prepare configuration data
            if isinstance(config, SQLConnectionConfig):
                config_data = config.to_dict(include_password=True)
                config_data['config_type'] = 'sql'
                
                # Encrypt password
                if config_data['password']:
                    config_data['password'] = self.encryption.encrypt(config_data['password'])
                    config_data['password_encrypted'] = True
                
            elif isinstance(config, APIConnectionConfig):
                config_data = config.to_dict(include_api_key=True)
                config_data['config_type'] = 'api'
                
                # Encrypt API key
                if config_data['api_key']:
                    config_data['api_key'] = self.encryption.encrypt(config_data['api_key'])
                    config_data['api_key_encrypted'] = True
            
            else:
                raise ConfigurationError(f"Unsupported configuration type: {type(config)}")
            
            # Add metadata
            config_data['created_at'] = time.time()
            config_data['updated_at'] = time.time()
            
            # Update connections dictionary
            connections[config.connection_id] = config_data
            
            # Save to file
            self._save_connections_file(connections)
            
            self.logger.info(f"Saved connection configuration: {config.connection_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save connection config '{config.connection_id}': {e}")
            return False
    
    def load_connection_config(self, connection_id: str) -> Optional[Union[SQLConnectionConfig, APIConnectionConfig]]:
        """
        Load a connection configuration and decrypt credentials.
        
        Args:
            connection_id: ID of the connection to load
            
        Returns:
            Connection configuration or None if not found
        """
        try:
            connections = self._load_connections_file()
            
            if connection_id not in connections:
                self.logger.warning(f"Connection configuration not found: {connection_id}")
                return None
            
            config_data = connections[connection_id].copy()
            config_type = config_data.pop('config_type', 'unknown')
            
            # Remove metadata
            config_data.pop('created_at', None)
            config_data.pop('updated_at', None)
            
            if config_type == 'sql':
                # Decrypt password if encrypted
                if config_data.get('password_encrypted', False):
                    config_data['password'] = self.encryption.decrypt(config_data['password'])
                config_data.pop('password_encrypted', None)
                
                # Create SQL configuration
                return SQLConnectionConfig(
                    connection_id=config_data['connection_id'],
                    database_type=ConnectionType(config_data['database_type']),
                    host=config_data['host'],
                    port=config_data['port'],
                    database=config_data['database'],
                    username=config_data['username'],
                    password=config_data['password'],
                    connection_timeout=config_data.get('connection_timeout', 30),
                    query_timeout=config_data.get('query_timeout', 60),
                    max_connections=config_data.get('max_connections', 5),
                    use_ssl=config_data.get('use_ssl', True),
                    aws_region=config_data.get('aws_region'),
                    use_iam_auth=config_data.get('use_iam_auth', False)
                )
            
            elif config_type == 'api':
                # Decrypt API key if encrypted
                if config_data.get('api_key_encrypted', False):
                    config_data['api_key'] = self.encryption.decrypt(config_data['api_key'])
                config_data.pop('api_key_encrypted', None)
                
                # Create API configuration
                from invoice_matching.models import AuthenticationType
                return APIConnectionConfig(
                    connection_id=config_data['connection_id'],
                    base_url=config_data['base_url'],
                    api_key=config_data['api_key'],
                    authentication_type=AuthenticationType(config_data['authentication_type']),
                    timeout=config_data.get('timeout', 30),
                    rate_limit=config_data.get('rate_limit', 100),
                    retry_attempts=config_data.get('retry_attempts', 3),
                    aws_region=config_data.get('aws_region'),
                    additional_headers=config_data.get('additional_headers', {})
                )
            
            else:
                raise ConfigurationError(f"Unknown configuration type: {config_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to load connection config '{connection_id}': {e}")
            return None
    
    def list_connections(self) -> List[Dict[str, Any]]:
        """
        List all connection configurations (without sensitive data).
        
        Returns:
            List of connection information dictionaries
        """
        try:
            connections = self._load_connections_file()
            
            connection_list = []
            for connection_id, config_data in connections.items():
                info = {
                    'connection_id': connection_id,
                    'config_type': config_data.get('config_type', 'unknown'),
                    'created_at': config_data.get('created_at'),
                    'updated_at': config_data.get('updated_at')
                }
                
                # Add type-specific info without sensitive data
                if config_data.get('config_type') == 'sql':
                    info.update({
                        'database_type': config_data.get('database_type'),
                        'host': config_data.get('host'),
                        'database': config_data.get('database'),
                        'username': config_data.get('username')
                    })
                elif config_data.get('config_type') == 'api':
                    info.update({
                        'base_url': config_data.get('base_url'),
                        'authentication_type': config_data.get('authentication_type'),
                        'rate_limit': config_data.get('rate_limit')
                    })
                
                connection_list.append(info)
            
            return connection_list
            
        except Exception as e:
            self.logger.error(f"Failed to list connections: {e}")
            return []
    
    def delete_connection_config(self, connection_id: str) -> bool:
        """
        Delete a connection configuration.
        
        Args:
            connection_id: ID of the connection to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            connections = self._load_connections_file()
            
            if connection_id not in connections:
                self.logger.warning(f"Connection configuration not found for deletion: {connection_id}")
                return False
            
            # Create backup before deletion
            self._create_backup("before_delete_" + connection_id)
            
            # Remove connection
            del connections[connection_id]
            
            # Save updated connections
            self._save_connections_file(connections)
            
            self.logger.info(f"Deleted connection configuration: {connection_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete connection config '{connection_id}': {e}")
            return False
    
    def connection_exists(self, connection_id: str) -> bool:
        """
        Check if a connection configuration exists.
        
        Args:
            connection_id: ID of the connection to check
            
        Returns:
            True if connection exists, False otherwise
        """
        try:
            connections = self._load_connections_file()
            return connection_id in connections
        except Exception as e:
            self.logger.error(f"Failed to check connection existence '{connection_id}': {e}")
            return False
    
    def save_matching_settings(self, settings: MatchingSettings) -> bool:
        """
        Save matching algorithm settings.
        
        Args:
            settings: Matching settings to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            settings_data = settings.to_dict()
            settings_data['updated_at'] = time.time()
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings_data, f, indent=2)
            
            self.logger.info("Saved matching settings")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save matching settings: {e}")
            return False
    
    def load_matching_settings(self) -> MatchingSettings:
        """
        Load matching algorithm settings.
        
        Returns:
            MatchingSettings instance (default if not found)
        """
        try:
            if not self.settings_file.exists():
                self.logger.info("No matching settings file found, using defaults")
                return MatchingSettings()
            
            with open(self.settings_file, 'r') as f:
                settings_data = json.load(f)
            
            # Remove metadata
            settings_data.pop('updated_at', None)
            
            return MatchingSettings.from_dict(settings_data)
            
        except Exception as e:
            self.logger.error(f"Failed to load matching settings: {e}")
            return MatchingSettings()
    
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """
        Create a backup of all configuration files.
        
        Args:
            backup_name: Optional name for the backup. If None, uses timestamp.
            
        Returns:
            Path to the created backup file
        """
        return self._create_backup(backup_name)
    
    def restore_backup(self, backup_path: str) -> bool:
        """
        Restore configuration from a backup file.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            True if restored successfully, False otherwise
        """
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                raise ConfigurationError(f"Backup file not found: {backup_path}")
            
            # Create backup of current state before restore
            self._create_backup("before_restore")
            
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            # Restore connections
            if 'connections' in backup_data:
                self._save_connections_file(backup_data['connections'])
            
            # Restore settings
            if 'settings' in backup_data:
                with open(self.settings_file, 'w') as f:
                    json.dump(backup_data['settings'], f, indent=2)
            
            self.logger.info(f"Restored configuration from backup: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup '{backup_path}': {e}")
            return False
    
    def get_config_info(self) -> Dict[str, Any]:
        """
        Get information about the configuration manager.
        
        Returns:
            Dictionary with configuration manager information
        """
        try:
            connections = self._load_connections_file()
            
            return {
                'config_directory': str(self.config_dir),
                'connections_count': len(connections),
                'connections_file_exists': self.connections_file.exists(),
                'settings_file_exists': self.settings_file.exists(),
                'encryption_info': self.encryption.get_key_info(),
                'backup_directory': str(self.backup_dir),
                'backup_count': len(list(self.backup_dir.glob('*.json')))
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get config info: {e}")
            return {'error': str(e)}
    
    def _load_connections_file(self) -> Dict[str, Any]:
        """Load connections from file."""
        try:
            if not self.connections_file.exists():
                return {}
            
            with open(self.connections_file, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"Failed to load connections file: {e}")
            return {}
    
    def _save_connections_file(self, connections: Dict[str, Any]):
        """Save connections to file."""
        with open(self.connections_file, 'w') as f:
            json.dump(connections, f, indent=2)
    
    def _create_backup(self, backup_name: Optional[str] = None) -> str:
        """Create a backup of current configuration."""
        try:
            if backup_name is None:
                backup_name = f"backup_{int(time.time())}"
            
            backup_file = self.backup_dir / f"{backup_name}.json"
            
            backup_data = {
                'created_at': time.time(),
                'connections': self._load_connections_file(),
                'settings': {}
            }
            
            # Include settings if they exist
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    backup_data['settings'] = json.load(f)
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            self.logger.info(f"Created backup: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise ConfigurationError(f"Backup creation failed: {e}")


# Global configuration manager instance
_global_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    Get the global configuration manager instance.
    
    Returns:
        Global ConfigManager instance
    """
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
    return _global_config_manager