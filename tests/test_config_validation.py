"""
Unit tests for configuration validation and testing utilities.

Tests validation logic, connection testing, and configuration templates.
"""

from invoice_matching.models import (
    SQLConnectionConfig, APIConnectionConfig, ConnectionType, AuthenticationType
)
from invoice_matching.config.validation import (
    ConfigurationValidator, ConnectionTester, ConfigurationTemplates, ValidationResult
)


class TestConfigurationValidator:
    """Test cases for configuration validation."""
    
    def test_valid_sql_config(self):
        """Test validation of valid SQL configuration."""
        config = SQLConnectionConfig(
            connection_id="valid-sql",
            database_type=ConnectionType.MYSQL,
            host="mysql.example.com",
            port=3306,
            database="test_db",
            username="test_user",
            password="secure_password123"
        )
        
        validator = ConfigurationValidator()
        result = validator.validate_sql_config(config)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_invalid_sql_config(self):
        """Test validation of invalid SQL configuration."""
        config = SQLConnectionConfig(
            connection_id="",  # Invalid: empty
            database_type=ConnectionType.MYSQL,
            host="",  # Invalid: empty
            port=70000,  # Invalid: out of range
            database="test_db",
            username="",  # Invalid: empty
            password="short"  # Warning: too short
        )
        
        validator = ConfigurationValidator()
        result = validator.validate_sql_config(config)
        
        assert result.is_valid is False
        assert len(result.errors) >= 3  # connection_id, host, port, username
        assert len(result.warnings) >= 1  # password length
    
    def test_aws_rds_sql_config(self):
        """Test validation of AWS RDS SQL configuration."""
        config = SQLConnectionConfig(
            connection_id="aws-rds-test",
            database_type=ConnectionType.SQL_SERVER,
            host="mydb.cluster-xyz.us-east-1.rds.amazonaws.com",
            port=1433,
            database="invoices",
            username="dbuser",
            password="secure_password",
            use_ssl=True,
            aws_region="us-east-1"
        )
        
        validator = ConfigurationValidator()
        result = validator.validate_sql_config(config)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert any("AWS RDS endpoint detected" in s for s in result.suggestions)
    
    def test_valid_api_config(self):
        """Test validation of valid API configuration."""
        config = APIConnectionConfig(
            connection_id="valid-api",
            base_url="https://api.example.com/v1",
            api_key="secure_api_key_123",
            authentication_type=AuthenticationType.API_KEY,
            timeout=30,
            rate_limit=100
        )
        
        validator = ConfigurationValidator()
        result = validator.validate_api_config(config)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_invalid_api_config(self):
        """Test validation of invalid API configuration."""
        config = APIConnectionConfig(
            connection_id="invalid@id",  # Invalid: special characters
            base_url="not-a-url",  # Invalid: no protocol
            api_key="",  # Invalid: empty
            authentication_type=AuthenticationType.API_KEY,
            timeout=-5,  # Invalid: negative
            rate_limit=0  # Invalid: zero
        )
        
        validator = ConfigurationValidator()
        result = validator.validate_api_config(config)
        
        assert result.is_valid is False
        assert len(result.errors) >= 4  # connection_id, base_url, api_key, timeout, rate_limit
    
    def test_aws_api_gateway_config(self):
        """Test validation of AWS API Gateway configuration."""
        config = APIConnectionConfig(
            connection_id="aws-api-gateway",
            base_url="https://abc123.execute-api.us-east-1.amazonaws.com/prod",
            api_key="AKIAIOSFODNN7EXAMPLE:wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            authentication_type=AuthenticationType.AWS_IAM,
            aws_region="us-east-1"
        )
        
        validator = ConfigurationValidator()
        result = validator.validate_api_config(config)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert any("AWS API Gateway detected" in s for s in result.suggestions)
    
    def test_basic_auth_validation(self):
        """Test validation of Basic authentication configuration."""
        # Valid basic auth
        valid_config = APIConnectionConfig(
            connection_id="basic-auth-valid",
            base_url="https://api.example.com",
            api_key="username:password",
            authentication_type=AuthenticationType.BASIC_AUTH
        )
        
        validator = ConfigurationValidator()
        result = validator.validate_api_config(valid_config)
        
        assert result.is_valid is True
        
        # Invalid basic auth (missing colon)
        invalid_config = APIConnectionConfig(
            connection_id="basic-auth-invalid",
            base_url="https://api.example.com",
            api_key="usernamepassword",  # Missing colon
            authentication_type=AuthenticationType.BASIC_AUTH
        )
        
        result = validator.validate_api_config(invalid_config)
        
        assert result.is_valid is False
        assert any("username:password" in error for error in result.errors)


class TestConnectionTester:
    """Test cases for connection testing."""
    
    def test_sql_connection_test_valid_config(self):
        """Test SQL connection testing with valid configuration."""
        config = SQLConnectionConfig(
            connection_id="test-sql-connection",
            database_type=ConnectionType.MYSQL,
            host="localhost",
            port=3306,
            database="test_db",
            username="test_user",
            password="test_password"
        )
        
        tester = ConnectionTester()
        result = tester.test_sql_connection(config)
        
        # Note: This is a simulated test, so it should succeed
        assert result.connection_id == "test-sql-connection"
        assert result.connection_type in [ConnectionType.MYSQL, ConnectionType.SQL_SERVER]
        assert result.response_time > 0
        assert result.additional_info is not None
        assert result.additional_info.get('simulated') is True
    
    def test_sql_connection_test_invalid_config(self):
        """Test SQL connection testing with invalid configuration."""
        config = SQLConnectionConfig(
            connection_id="",  # Invalid
            database_type=ConnectionType.MYSQL,
            host="",  # Invalid
            port=3306,
            database="test_db",
            username="test_user",
            password="test_password"
        )
        
        tester = ConnectionTester()
        result = tester.test_sql_connection(config)
        
        assert result.success is False
        assert "Configuration validation failed" in result.error_message
        assert 'validation_errors' in result.additional_info
    
    def test_api_connection_test_valid_config(self):
        """Test API connection testing with valid configuration."""
        config = APIConnectionConfig(
            connection_id="test-api-connection",
            base_url="https://httpbin.org/get",  # Public test API
            api_key="test_api_key",
            authentication_type=AuthenticationType.API_KEY
        )
        
        tester = ConnectionTester()
        result = tester.test_api_connection(config)
        
        # Note: This is a simulated test
        assert result.connection_id == "test-api-connection"
        assert result.connection_type == ConnectionType.REST_API
        assert result.response_time > 0
        assert result.additional_info is not None
        assert result.additional_info.get('simulated') is True
    
    def test_api_connection_test_invalid_config(self):
        """Test API connection testing with invalid configuration."""
        config = APIConnectionConfig(
            connection_id="test-invalid-api",
            base_url="not-a-valid-url",  # Invalid URL
            api_key="",  # Invalid: empty
            authentication_type=AuthenticationType.API_KEY
        )
        
        tester = ConnectionTester()
        result = tester.test_api_connection(config)
        
        assert result.success is False
        assert "Configuration validation failed" in result.error_message
        assert 'validation_errors' in result.additional_info


class TestConfigurationTemplates:
    """Test cases for configuration templates."""
    
    def test_aws_rds_sql_server_template(self):
        """Test AWS RDS SQL Server template."""
        template = ConfigurationTemplates.get_aws_rds_sql_server_template()
        
        assert template['name'] == 'AWS RDS SQL Server'
        assert template['config_type'] == 'sql'
        assert template['template']['database_type'] == 'sql_server'
        assert template['template']['port'] == 1433
        assert template['template']['use_ssl'] is True
        assert 'connection_id' in template['required_fields']
        assert 'example' in template
    
    def test_aws_rds_mysql_template(self):
        """Test AWS RDS MySQL template."""
        template = ConfigurationTemplates.get_aws_rds_mysql_template()
        
        assert template['name'] == 'AWS RDS MySQL'
        assert template['config_type'] == 'sql'
        assert template['template']['database_type'] == 'mysql'
        assert template['template']['port'] == 3306
        assert template['template']['use_ssl'] is True
    
    def test_api_gateway_template(self):
        """Test AWS API Gateway template."""
        template = ConfigurationTemplates.get_api_gateway_template()
        
        assert template['name'] == 'AWS API Gateway'
        assert template['config_type'] == 'api'
        assert template['template']['authentication_type'] == 'aws_iam'
        assert 'aws_region' in template['required_fields']
    
    def test_rest_api_template(self):
        """Test generic REST API template."""
        template = ConfigurationTemplates.get_rest_api_template()
        
        assert template['name'] == 'Generic REST API'
        assert template['config_type'] == 'api'
        assert template['template']['authentication_type'] == 'api_key'
        assert 'base_url' in template['required_fields']
    
    def test_list_templates(self):
        """Test listing all templates."""
        templates = ConfigurationTemplates.list_templates()
        
        assert len(templates) == 4
        assert all('name' in template for template in templates)
        assert all('config_type' in template for template in templates)
        assert all('template' in template for template in templates)
        
        # Check we have both SQL and API templates
        sql_templates = [t for t in templates if t['config_type'] == 'sql']
        api_templates = [t for t in templates if t['config_type'] == 'api']
        
        assert len(sql_templates) == 2
        assert len(api_templates) == 2


class TestValidationResult:
    """Test cases for ValidationResult class."""
    
    def test_validation_result_creation(self):
        """Test creating ValidationResult."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert len(result.suggestions) == 0
    
    def test_add_error(self):
        """Test adding error to ValidationResult."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])
        
        result.add_error("Test error")
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0] == "Test error"
    
    def test_add_warning(self):
        """Test adding warning to ValidationResult."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])
        
        result.add_warning("Test warning")
        
        assert result.is_valid is True  # Warnings don't affect validity
        assert len(result.warnings) == 1
        assert result.warnings[0] == "Test warning"
    
    def test_add_suggestion(self):
        """Test adding suggestion to ValidationResult."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])
        
        result.add_suggestion("Test suggestion")
        
        assert result.is_valid is True
        assert len(result.suggestions) == 1
        assert result.suggestions[0] == "Test suggestion"
    
    def test_to_dict(self):
        """Test converting ValidationResult to dictionary."""
        result = ValidationResult(is_valid=False, errors=["Error 1"], warnings=["Warning 1"], suggestions=["Suggestion 1"])
        
        result_dict = result.to_dict()
        
        assert result_dict['is_valid'] is False
        assert result_dict['errors'] == ["Error 1"]
        assert result_dict['warnings'] == ["Warning 1"]
        assert result_dict['suggestions'] == ["Suggestion 1"]


def run_basic_validation_test():
    """Run basic validation functionality test."""
    print("Testing configuration validation...")
    
    # Test SQL config validation
    sql_config = SQLConnectionConfig(
        connection_id="test-sql",
        database_type=ConnectionType.MYSQL,
        host="test.db.com",
        port=3306,
        database="testdb",
        username="testuser",
        password="testpass"
    )
    
    validator = ConfigurationValidator()
    sql_result = validator.validate_sql_config(sql_config)
    print(f"✓ SQL validation: {sql_result.is_valid} ({len(sql_result.errors)} errors)")
    
    # Test API config validation
    api_config = APIConnectionConfig(
        connection_id="test-api",
        base_url="https://api.test.com",
        api_key="test_key",
        authentication_type=AuthenticationType.API_KEY
    )
    
    api_result = validator.validate_api_config(api_config)
    print(f"✓ API validation: {api_result.is_valid} ({len(api_result.errors)} errors)")
    
    # Test connection testing
    tester = ConnectionTester()
    sql_test = tester.test_sql_connection(sql_config)
    print(f"✓ SQL connection test: {sql_test.success} ({sql_test.response_time:.3f}s)")
    
    api_test = tester.test_api_connection(api_config)
    print(f"✓ API connection test: {api_test.success} ({api_test.response_time:.3f}s)")
    
    # Test templates
    templates = ConfigurationTemplates.list_templates()
    print(f"✓ Configuration templates: {len(templates)} available")
    
    print("🎉 Configuration validation working!")


if __name__ == "__main__":
    run_basic_validation_test()