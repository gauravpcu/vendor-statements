"""
Unit tests for configuration manager.

Tests configuration storage, encryption, and management functionality.
"""

import os
import tempfile
import shutil
from pathlib import Path

from invoice_matching.models import (
    SQLConnectionConfig, APIConnectionConfig, MatchingSettings,
    ConnectionType, AuthenticationType
)
from invoice_matching.config.config_manager import ConfigManager
from invoice_matching.config.encryption import CredentialEncryption


class TestCredentialEncryption:
    """Test cases for credential encryption."""
    
    def test_encryption_creation(self):
        """Test creating encryption instance."""
        encryption = CredentialEncryption("test_key_123")
        
        info = encryption.get_key_info()
        assert info['initialized'] is True
        assert info['key_source'] == 'provided'
        assert info['algorithm'] == 'Simple Base64 + Key Mixing'
    
    def test_encrypt_decrypt_cycle(self):
        """Test encrypting and decrypting data."""
        encryption = CredentialEncryption("secret_key")
        
        original = "my_secret_password"
        encrypted = encryption.encrypt(original)
        decrypted = encryption.decrypt(encrypted)
        
        assert encrypted != original
        assert decrypted == original
        assert len(encrypted) > len(original)
    
    def test_encrypt_empty_string(self):
        """Test encrypting empty string."""
        encryption = CredentialEncryption("test_key")
        
        encrypted = encryption.encrypt("")
        decrypted = encryption.decrypt("")
        
        assert encrypted == ""
        assert decrypted == ""
    
    def test_is_encrypted_detection(self):
        """Test detecting encrypted strings."""
        encryption = CredentialEncryption("test_key")
        
        plaintext = "plaintext_password"
        encrypted = encryption.encrypt(plaintext)
        
        assert encryption.is_encrypted(plaintext) is False
        assert encryption.is_encrypted(encrypted) is True
        assert encryption.is_encrypted("") is False
        assert encryption.is_encrypted("short") is False


class TestConfigManager:
    """Test cases for configuration manager."""
    
    def setup_method(self):
        """Setup test environment."""
        # Create temporary directory for tests
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager(
            config_dir=self.temp_dir,
            encryption_key="test_encryption_key"
        )
    
    def teardown_method(self):
        """Cleanup test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_config_manager_creation(self):
        """Test creating configuration manager."""
        assert self.config_manager.config_dir == Path(self.temp_dir)
        assert self.config_manager.connections_file.parent == Path(self.temp_dir)
        assert self.config_manager.settings_file.parent == Path(self.temp_dir)
        assert self.config_manager.backup_dir.exists()
    
    def test_save_sql_connection_config(self):
        """Test saving SQL connection configuration."""
        config = SQLConnectionConfig(
            connection_id="test-sql-1",
            database_type=ConnectionType.SQL_SERVER,
            host="test.database.com",
            port=1433,
            database="test_db",
            username="test_user",
            password="secret_password",
            aws_region="us-east-1"
        )
        
        result = self.config_manager.save_connection_config(config)
        
        assert result is True
        assert self.config_manager.connection_exists("test-sql-1")
    
    def test_save_api_connection_config(self):
        """Test saving API connection configuration."""
        config = APIConnectionConfig(
            connection_id="test-api-1",
            base_url="https://api.example.com",
            api_key="secret_api_key",
            authentication_type=AuthenticationType.API_KEY,
            rate_limit=200,
            aws_region="us-west-2"
        )
        
        result = self.config_manager.save_connection_config(config)
        
        assert result is True
        assert self.config_manager.connection_exists("test-api-1")
    
    def test_load_sql_connection_config(self):
        """Test loading SQL connection configuration."""
        # Save configuration first
        original_config = SQLConnectionConfig(
            connection_id="test-sql-load",
            database_type=ConnectionType.MYSQL,
            host="mysql.example.com",
            port=3306,
            database="invoice_db",
            username="mysql_user",
            password="mysql_password"
        )
        
        self.config_manager.save_connection_config(original_config)
        
        # Load configuration
        loaded_config = self.config_manager.load_connection_config("test-sql-load")
        
        assert loaded_config is not None
        assert isinstance(loaded_config, SQLConnectionConfig)
        assert loaded_config.connection_id == "test-sql-load"
        assert loaded_config.database_type == ConnectionType.MYSQL
        assert loaded_config.host == "mysql.example.com"
        assert loaded_config.port == 3306
        assert loaded_config.database == "invoice_db"
        assert loaded_config.username == "mysql_user"
        assert loaded_config.password == "mysql_password"  # Should be decrypted
    
    def test_load_api_connection_config(self):
        """Test loading API connection configuration."""
        # Save configuration first
        original_config = APIConnectionConfig(
            connection_id="test-api-load",
            base_url="https://api.test.com",
            api_key="test_api_key_123",
            authentication_type=AuthenticationType.BEARER_TOKEN,
            timeout=45,
            rate_limit=150
        )
        
        self.config_manager.save_connection_config(original_config)
        
        # Load configuration
        loaded_config = self.config_manager.load_connection_config("test-api-load")
        
        assert loaded_config is not None
        assert isinstance(loaded_config, APIConnectionConfig)
        assert loaded_config.connection_id == "test-api-load"
        assert loaded_config.base_url == "https://api.test.com"
        assert loaded_config.api_key == "test_api_key_123"  # Should be decrypted
        assert loaded_config.authentication_type == AuthenticationType.BEARER_TOKEN
        assert loaded_config.timeout == 45
        assert loaded_config.rate_limit == 150
    
    def test_load_nonexistent_config(self):
        """Test loading non-existent configuration."""
        loaded_config = self.config_manager.load_connection_config("nonexistent")
        
        assert loaded_config is None
    
    def test_list_connections(self):
        """Test listing connection configurations."""
        # Save multiple configurations
        sql_config = SQLConnectionConfig(
            connection_id="sql-1",
            database_type=ConnectionType.SQL_SERVER,
            host="sql.example.com",
            port=1433,
            database="db1",
            username="user1",
            password="pass1"
        )
        
        api_config = APIConnectionConfig(
            connection_id="api-1",
            base_url="https://api1.example.com",
            api_key="key1",
            authentication_type=AuthenticationType.API_KEY
        )
        
        self.config_manager.save_connection_config(sql_config)
        self.config_manager.save_connection_config(api_config)
        
        # List connections
        connections = self.config_manager.list_connections()
        
        assert len(connections) == 2
        
        # Check SQL connection info
        sql_info = next(c for c in connections if c['connection_id'] == 'sql-1')
        assert sql_info['config_type'] == 'sql'
        assert sql_info['database_type'] == 'sql_server'
        assert sql_info['host'] == 'sql.example.com'
        assert sql_info['username'] == 'user1'
        assert 'password' not in sql_info  # Should not include sensitive data
        
        # Check API connection info
        api_info = next(c for c in connections if c['connection_id'] == 'api-1')
        assert api_info['config_type'] == 'api'
        assert api_info['base_url'] == 'https://api1.example.com'
        assert api_info['authentication_type'] == 'api_key'
        assert 'api_key' not in api_info  # Should not include sensitive data
    
    def test_delete_connection_config(self):
        """Test deleting connection configuration."""
        # Save configuration first
        config = SQLConnectionConfig(
            connection_id="test-delete",
            database_type=ConnectionType.MYSQL,
            host="delete.example.com",
            port=3306,
            database="delete_db",
            username="delete_user",
            password="delete_password"
        )
        
        self.config_manager.save_connection_config(config)
        assert self.config_manager.connection_exists("test-delete")
        
        # Delete configuration
        result = self.config_manager.delete_connection_config("test-delete")
        
        assert result is True
        assert not self.config_manager.connection_exists("test-delete")
    
    def test_delete_nonexistent_config(self):
        """Test deleting non-existent configuration."""
        result = self.config_manager.delete_connection_config("nonexistent")
        
        assert result is False
    
    def test_save_load_matching_settings(self):
        """Test saving and loading matching settings."""
        # Create custom settings
        settings = MatchingSettings(
            fuzzy_match_threshold=0.9,
            date_tolerance_days=14,
            amount_variance_percentage=10.0,
            enable_fuzzy_vendor_matching=False,
            vendor_name_weight=0.4
        )
        
        # Save settings
        result = self.config_manager.save_matching_settings(settings)
        assert result is True
        
        # Load settings
        loaded_settings = self.config_manager.load_matching_settings()
        
        assert loaded_settings.fuzzy_match_threshold == 0.9
        assert loaded_settings.date_tolerance_days == 14
        assert loaded_settings.amount_variance_percentage == 10.0
        assert loaded_settings.enable_fuzzy_vendor_matching is False
        assert loaded_settings.vendor_name_weight == 0.4
    
    def test_load_default_matching_settings(self):
        """Test loading default matching settings when none exist."""
        settings = self.config_manager.load_matching_settings()
        
        # Should return default settings
        assert settings.fuzzy_match_threshold == 0.8
        assert settings.date_tolerance_days == 7
        assert settings.amount_variance_percentage == 5.0
        assert settings.enable_fuzzy_vendor_matching is True
    
    def test_create_backup(self):
        """Test creating configuration backup."""
        # Save some configurations
        sql_config = SQLConnectionConfig(
            connection_id="backup-test",
            database_type=ConnectionType.MYSQL,
            host="backup.example.com",
            port=3306,
            database="backup_db",
            username="backup_user",
            password="backup_password"
        )
        
        self.config_manager.save_connection_config(sql_config)
        
        # Create backup
        backup_path = self.config_manager.create_backup("test_backup")
        
        assert os.path.exists(backup_path)
        assert "test_backup.json" in backup_path
    
    def test_get_config_info(self):
        """Test getting configuration manager information."""
        # Save a configuration to have some data
        config = APIConnectionConfig(
            connection_id="info-test",
            base_url="https://info.example.com",
            api_key="info_key",
            authentication_type=AuthenticationType.API_KEY
        )
        
        self.config_manager.save_connection_config(config)
        
        # Get config info
        info = self.config_manager.get_config_info()
        
        assert 'config_directory' in info
        assert info['connections_count'] == 1
        assert info['connections_file_exists'] is True
        assert 'encryption_info' in info
        assert info['encryption_info']['initialized'] is True


def run_basic_config_test():
    """Run basic configuration manager test."""
    print("Testing configuration manager...")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create config manager
        config_manager = ConfigManager(temp_dir, "test_key")
        print(f"✓ Config manager created in: {temp_dir}")
        
        # Test encryption
        encryption = config_manager.encryption
        encrypted = encryption.encrypt("test_password")
        decrypted = encryption.decrypt(encrypted)
        assert decrypted == "test_password"
        print("✓ Encryption/decryption working")
        
        # Test SQL config
        sql_config = SQLConnectionConfig(
            connection_id="test-sql",
            database_type=ConnectionType.MYSQL,
            host="test.db.com",
            port=3306,
            database="testdb",
            username="testuser",
            password="testpass"
        )
        
        config_manager.save_connection_config(sql_config)
        loaded_sql = config_manager.load_connection_config("test-sql")
        assert loaded_sql.password == "testpass"
        print("✓ SQL config save/load working")
        
        # Test API config
        api_config = APIConnectionConfig(
            connection_id="test-api",
            base_url="https://api.test.com",
            api_key="test_key",
            authentication_type=AuthenticationType.API_KEY
        )
        
        config_manager.save_connection_config(api_config)
        loaded_api = config_manager.load_connection_config("test-api")
        assert loaded_api.api_key == "test_key"
        print("✓ API config save/load working")
        
        # Test listing
        connections = config_manager.list_connections()
        assert len(connections) == 2
        print(f"✓ Listed {len(connections)} connections")
        
        print("🎉 Configuration manager working!")
        
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    run_basic_config_test()