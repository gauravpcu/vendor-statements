"""
Configuration validation and testing utilities.

Provides validation for connection configurations, connection testing,
and configuration templates with detailed error reporting.
"""

import re
import socket
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse
from dataclasses import dataclass

from invoice_matching.models import (
    SQLConnectionConfig, APIConnectionConfig, ConnectionTestResult,
    ConnectionType, AuthenticationType, ValidationError
)

import logging
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    
    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)
    
    def add_suggestion(self, message: str):
        """Add a suggestion message."""
        self.suggestions.append(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'suggestions': self.suggestions
        }


class ConfigurationValidator:
    """Validates connection configurations with detailed error reporting."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.ConfigurationValidator")
    
    def validate_sql_config(self, config: SQLConnectionConfig) -> ValidationResult:
        """
        Validate SQL database connection configuration.
        
        Args:
            config: SQL connection configuration to validate
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])
        
        # Validate connection ID
        if not config.connection_id:
            result.add_error("Connection ID is required")
        elif not re.match(r'^[a-zA-Z0-9_-]+$', config.connection_id):
            result.add_error("Connection ID can only contain letters, numbers, hyphens, and underscores")
        
        # Validate database type
        if not config.database_type:
            result.add_error("Database type is required")
        elif config.database_type not in [ConnectionType.SQL_SERVER, ConnectionType.MYSQL]:
            result.add_warning(f"Database type {config.database_type.value} may not be fully supported")
        
        # Validate host
        if not config.host:
            result.add_error("Host is required")
        else:
            # Check if host looks like an AWS RDS endpoint
            if '.rds.amazonaws.com' in config.host:
                result.add_suggestion("AWS RDS endpoint detected - consider enabling SSL and IAM authentication")
                if not config.use_ssl:
                    result.add_warning("SSL is recommended for AWS RDS connections")
                if not config.aws_region:
                    result.add_warning("AWS region should be specified for RDS connections")
            
            # Basic hostname validation
            if not self._is_valid_hostname(config.host):
                result.add_error("Host appears to be invalid")
        
        # Validate port
        if not config.port:
            result.add_error("Port is required")
        elif not (1 <= config.port <= 65535):
            result.add_error("Port must be between 1 and 65535")
        else:
            # Check for standard ports
            standard_ports = {
                ConnectionType.SQL_SERVER: 1433,
                ConnectionType.MYSQL: 3306
            }
            expected_port = standard_ports.get(config.database_type)
            if expected_port and config.port != expected_port:
                result.add_warning(f"Non-standard port {config.port} for {config.database_type.value} (standard: {expected_port})")
        
        # Validate database name
        if not config.database:
            result.add_error("Database name is required")
        elif not re.match(r'^[a-zA-Z0-9_-]+$', config.database):
            result.add_warning("Database name contains special characters that may cause issues")
        
        # Validate username
        if not config.username:
            result.add_error("Username is required")
        
        # Validate password (only if not using IAM auth)
        if not config.use_iam_auth:
            if not config.password:
                result.add_error("Password is required when not using IAM authentication")
            elif len(config.password) < 8:
                result.add_warning("Password is shorter than 8 characters")
        
        # Validate timeouts
        if config.connection_timeout <= 0:
            result.add_error("Connection timeout must be positive")
        elif config.connection_timeout > 300:
            result.add_warning("Connection timeout is very high (>5 minutes)")
        
        if config.query_timeout <= 0:
            result.add_error("Query timeout must be positive")
        elif config.query_timeout > 600:
            result.add_warning("Query timeout is very high (>10 minutes)")
        
        # Validate connection pool
        if config.max_connections <= 0:
            result.add_error("Max connections must be positive")
        elif config.max_connections > 100:
            result.add_warning("Max connections is very high (>100)")
        
        # AWS-specific validations
        if config.aws_region:
            if not re.match(r'^[a-z]{2}-[a-z]+-\d+$', config.aws_region):
                result.add_error("AWS region format appears invalid (expected: us-east-1, eu-west-1, etc.)")
        
        if config.use_iam_auth and not config.aws_region:
            result.add_error("AWS region is required when using IAM authentication")
        
        self.logger.debug(f"SQL config validation completed: {len(result.errors)} errors, {len(result.warnings)} warnings")
        return result
    
    def validate_api_config(self, config: APIConnectionConfig) -> ValidationResult:
        """
        Validate API connection configuration.
        
        Args:
            config: API connection configuration to validate
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])
        
        # Validate connection ID
        if not config.connection_id:
            result.add_error("Connection ID is required")
        elif not re.match(r'^[a-zA-Z0-9_-]+$', config.connection_id):
            result.add_error("Connection ID can only contain letters, numbers, hyphens, and underscores")
        
        # Validate base URL
        if not config.base_url:
            result.add_error("Base URL is required")
        else:
            parsed_url = urlparse(config.base_url)
            
            if not parsed_url.scheme:
                result.add_error("Base URL must include protocol (http:// or https://)")
            elif parsed_url.scheme not in ['http', 'https']:
                result.add_error("Base URL must use HTTP or HTTPS protocol")
            elif parsed_url.scheme == 'http':
                result.add_warning("HTTP is not secure - consider using HTTPS")
            
            if not parsed_url.netloc:
                result.add_error("Base URL must include hostname")
            
            # Check for AWS API Gateway
            if 'execute-api' in parsed_url.netloc and 'amazonaws.com' in parsed_url.netloc:
                result.add_suggestion("AWS API Gateway detected - consider using AWS IAM authentication")
                if config.authentication_type != AuthenticationType.AWS_IAM:
                    result.add_warning("AWS IAM authentication is recommended for API Gateway")
                if not config.aws_region:
                    result.add_warning("AWS region should be specified for API Gateway")
        
        # Validate authentication type and credentials
        if not config.authentication_type:
            result.add_error("Authentication type is required")
        
        if not config.api_key:
            result.add_error("API key/credentials are required")
        else:
            # Validate credentials based on authentication type
            if config.authentication_type == AuthenticationType.BASIC_AUTH:
                if ':' not in config.api_key:
                    result.add_error("Basic auth credentials must be in format 'username:password'")
                else:
                    username, password = config.api_key.split(':', 1)
                    if not username or not password:
                        result.add_error("Both username and password are required for basic auth")
            
            elif config.authentication_type == AuthenticationType.AWS_IAM:
                if ':' not in config.api_key:
                    result.add_error("AWS IAM credentials must be in format 'access_key:secret_key'")
                else:
                    access_key, secret_key = config.api_key.split(':', 1)
                    if not access_key or not secret_key:
                        result.add_error("Both access key and secret key are required for AWS IAM")
                    elif not access_key.startswith('AKIA'):
                        result.add_warning("AWS access key should start with 'AKIA'")
            
            elif config.authentication_type == AuthenticationType.BEARER_TOKEN:
                if len(config.api_key) < 10:
                    result.add_warning("Bearer token appears to be very short")
            
            elif config.authentication_type == AuthenticationType.API_KEY:
                if len(config.api_key) < 8:
                    result.add_warning("API key appears to be very short")
        
        # Validate timeout
        if config.timeout <= 0:
            result.add_error("Timeout must be positive")
        elif config.timeout > 300:
            result.add_warning("Timeout is very high (>5 minutes)")
        elif config.timeout < 5:
            result.add_warning("Timeout is very low (<5 seconds)")
        
        # Validate rate limit
        if config.rate_limit <= 0:
            result.add_error("Rate limit must be positive")
        elif config.rate_limit > 10000:
            result.add_warning("Rate limit is very high (>10,000 requests/minute)")
        elif config.rate_limit < 10:
            result.add_warning("Rate limit is very low (<10 requests/minute)")
        
        # Validate retry attempts
        if config.retry_attempts < 0:
            result.add_error("Retry attempts cannot be negative")
        elif config.retry_attempts > 10:
            result.add_warning("Retry attempts is very high (>10)")
        
        # AWS-specific validations
        if config.aws_region:
            if not re.match(r'^[a-z]{2}-[a-z]+-\d+$', config.aws_region):
                result.add_error("AWS region format appears invalid")
        
        if config.authentication_type == AuthenticationType.AWS_IAM and not config.aws_region:
            result.add_error("AWS region is required when using AWS IAM authentication")
        
        # Validate additional headers
        if config.additional_headers:
            for header_name, header_value in config.additional_headers.items():
                if not header_name or not header_value:
                    result.add_warning("Empty header name or value found in additional headers")
                elif header_name.lower() in ['authorization', 'x-api-key']:
                    result.add_warning(f"Header '{header_name}' may conflict with authentication")
        
        self.logger.debug(f"API config validation completed: {len(result.errors)} errors, {len(result.warnings)} warnings")
        return result
    
    def _is_valid_hostname(self, hostname: str) -> bool:
        """Check if hostname is valid."""
        try:
            # Basic hostname validation
            if not hostname or len(hostname) > 253:
                return False
            
            # Check for valid characters
            if not re.match(r'^[a-zA-Z0-9.-]+$', hostname):
                return False
            
            # Check each label
            labels = hostname.split('.')
            for label in labels:
                if not label or len(label) > 63:
                    return False
                if label.startswith('-') or label.endswith('-'):
                    return False
            
            return True
        except Exception:
            return False


class ConnectionTester:
    """Tests database and API connections with detailed diagnostics."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.ConnectionTester")
    
    def test_sql_connection(self, config: SQLConnectionConfig) -> ConnectionTestResult:
        """
        Test SQL database connection.
        
        Args:
            config: SQL connection configuration to test
            
        Returns:
            ConnectionTestResult with test results
        """
        import time
        start_time = time.time()
        
        try:
            # First validate the configuration
            validator = ConfigurationValidator()
            validation = validator.validate_sql_config(config)
            
            if not validation.is_valid:
                return ConnectionTestResult(
                    success=False,
                    connection_id=config.connection_id,
                    connection_type=ConnectionType.SQL_SERVER if config.database_type == ConnectionType.SQL_SERVER else ConnectionType.MYSQL,
                    response_time=time.time() - start_time,
                    error_message=f"Configuration validation failed: {'; '.join(validation.errors)}",
                    additional_info={
                        'validation_errors': validation.errors,
                        'validation_warnings': validation.warnings
                    }
                )
            
            # Test network connectivity first
            network_test = self._test_network_connectivity(config.host, config.port)
            if not network_test['success']:
                return ConnectionTestResult(
                    success=False,
                    connection_id=config.connection_id,
                    connection_type=ConnectionType.SQL_SERVER if config.database_type == ConnectionType.SQL_SERVER else ConnectionType.MYSQL,
                    response_time=time.time() - start_time,
                    error_message=f"Network connectivity failed: {network_test['error']}",
                    additional_info={
                        'network_test': network_test,
                        'validation_warnings': validation.warnings
                    }
                )
            
            # For now, simulate database connection test
            # In production, this would use actual database drivers
            self.logger.info(f"Simulating SQL connection test for {config.host}:{config.port}")
            
            # Simulate connection time
            import time
            time.sleep(0.1)  # Simulate connection delay
            
            duration = time.time() - start_time
            
            return ConnectionTestResult(
                success=True,
                connection_id=config.connection_id,
                connection_type=ConnectionType.SQL_SERVER if config.database_type == ConnectionType.SQL_SERVER else ConnectionType.MYSQL,
                response_time=duration,
                error_message=None,
                additional_info={
                    'database_type': config.database_type.value,
                    'host': config.host,
                    'port': config.port,
                    'database': config.database,
                    'ssl_enabled': config.use_ssl,
                    'iam_auth': config.use_iam_auth,
                    'network_test': network_test,
                    'validation_warnings': validation.warnings,
                    'simulated': True
                }
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"SQL connection test failed: {e}")
            
            return ConnectionTestResult(
                success=False,
                connection_id=config.connection_id,
                connection_type=ConnectionType.SQL_SERVER if config.database_type == ConnectionType.SQL_SERVER else ConnectionType.MYSQL,
                response_time=duration,
                error_message=str(e),
                additional_info={'exception_type': type(e).__name__}
            )
    
    def test_api_connection(self, config: APIConnectionConfig) -> ConnectionTestResult:
        """
        Test API connection.
        
        Args:
            config: API connection configuration to test
            
        Returns:
            ConnectionTestResult with test results
        """
        import time
        start_time = time.time()
        
        try:
            # First validate the configuration
            validator = ConfigurationValidator()
            validation = validator.validate_api_config(config)
            
            if not validation.is_valid:
                return ConnectionTestResult(
                    success=False,
                    connection_id=config.connection_id,
                    connection_type=ConnectionType.REST_API,
                    response_time=time.time() - start_time,
                    error_message=f"Configuration validation failed: {'; '.join(validation.errors)}",
                    additional_info={
                        'validation_errors': validation.errors,
                        'validation_warnings': validation.warnings
                    }
                )
            
            # Parse URL for network test
            from urllib.parse import urlparse
            parsed_url = urlparse(config.base_url)
            port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
            
            # Test network connectivity
            network_test = self._test_network_connectivity(parsed_url.hostname, port)
            if not network_test['success']:
                return ConnectionTestResult(
                    success=False,
                    connection_id=config.connection_id,
                    connection_type=ConnectionType.REST_API,
                    response_time=time.time() - start_time,
                    error_message=f"Network connectivity failed: {network_test['error']}",
                    additional_info={
                        'network_test': network_test,
                        'validation_warnings': validation.warnings
                    }
                )
            
            # For now, simulate API connection test
            # In production, this would make actual HTTP requests
            self.logger.info(f"Simulating API connection test for {config.base_url}")
            
            # Simulate API call time
            import time
            time.sleep(0.05)  # Simulate API response delay
            
            duration = time.time() - start_time
            
            return ConnectionTestResult(
                success=True,
                connection_id=config.connection_id,
                connection_type=ConnectionType.REST_API,
                response_time=duration,
                error_message=None,
                additional_info={
                    'base_url': config.base_url,
                    'authentication_type': config.authentication_type.value,
                    'rate_limit': config.rate_limit,
                    'timeout': config.timeout,
                    'network_test': network_test,
                    'validation_warnings': validation.warnings,
                    'simulated': True
                }
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"API connection test failed: {e}")
            
            return ConnectionTestResult(
                success=False,
                connection_id=config.connection_id,
                connection_type=ConnectionType.REST_API,
                response_time=duration,
                error_message=str(e),
                additional_info={'exception_type': type(e).__name__}
            )
    
    def _test_network_connectivity(self, host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """
        Test basic network connectivity to host:port.
        
        Args:
            host: Hostname to test
            port: Port to test
            timeout: Connection timeout in seconds
            
        Returns:
            Dictionary with test results
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            start_time = time.time()
            result = sock.connect_ex((host, port))
            duration = time.time() - start_time
            
            sock.close()
            
            if result == 0:
                return {
                    'success': True,
                    'host': host,
                    'port': port,
                    'response_time': duration,
                    'message': 'Network connectivity successful'
                }
            else:
                return {
                    'success': False,
                    'host': host,
                    'port': port,
                    'response_time': duration,
                    'error': f'Connection failed with error code {result}',
                    'message': 'Network connectivity failed'
                }
                
        except socket.gaierror as e:
            return {
                'success': False,
                'host': host,
                'port': port,
                'error': f'DNS resolution failed: {e}',
                'message': 'DNS resolution failed'
            }
        except Exception as e:
            return {
                'success': False,
                'host': host,
                'port': port,
                'error': str(e),
                'message': 'Network test failed'
            }


class ConfigurationTemplates:
    """Provides configuration templates for common scenarios."""
    
    @staticmethod
    def get_aws_rds_sql_server_template() -> Dict[str, Any]:
        """Get template for AWS RDS SQL Server connection."""
        return {
            'name': 'AWS RDS SQL Server',
            'description': 'Template for connecting to AWS RDS SQL Server instance',
            'config_type': 'sql',
            'template': {
                'database_type': 'sql_server',
                'port': 1433,
                'use_ssl': True,
                'use_iam_auth': False,
                'connection_timeout': 30,
                'query_timeout': 60,
                'max_connections': 5
            },
            'required_fields': ['connection_id', 'host', 'database', 'username', 'password', 'aws_region'],
            'example': {
                'connection_id': 'my-rds-sql-server',
                'host': 'mydb.cluster-xyz.us-east-1.rds.amazonaws.com',
                'database': 'invoices',
                'username': 'dbuser',
                'aws_region': 'us-east-1'
            }
        }
    
    @staticmethod
    def get_aws_rds_mysql_template() -> Dict[str, Any]:
        """Get template for AWS RDS MySQL connection."""
        return {
            'name': 'AWS RDS MySQL',
            'description': 'Template for connecting to AWS RDS MySQL instance',
            'config_type': 'sql',
            'template': {
                'database_type': 'mysql',
                'port': 3306,
                'use_ssl': True,
                'use_iam_auth': False,
                'connection_timeout': 30,
                'query_timeout': 60,
                'max_connections': 5
            },
            'required_fields': ['connection_id', 'host', 'database', 'username', 'password', 'aws_region'],
            'example': {
                'connection_id': 'my-rds-mysql',
                'host': 'mysql.cluster-abc.us-west-2.rds.amazonaws.com',
                'database': 'invoice_db',
                'username': 'mysql_user',
                'aws_region': 'us-west-2'
            }
        }
    
    @staticmethod
    def get_api_gateway_template() -> Dict[str, Any]:
        """Get template for AWS API Gateway connection."""
        return {
            'name': 'AWS API Gateway',
            'description': 'Template for connecting to AWS API Gateway with IAM authentication',
            'config_type': 'api',
            'template': {
                'authentication_type': 'aws_iam',
                'timeout': 30,
                'rate_limit': 100,
                'retry_attempts': 3
            },
            'required_fields': ['connection_id', 'base_url', 'api_key', 'aws_region'],
            'example': {
                'connection_id': 'my-api-gateway',
                'base_url': 'https://abc123.execute-api.us-east-1.amazonaws.com/prod',
                'api_key': 'AKIAIOSFODNN7EXAMPLE:wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                'aws_region': 'us-east-1'
            }
        }
    
    @staticmethod
    def get_rest_api_template() -> Dict[str, Any]:
        """Get template for generic REST API connection."""
        return {
            'name': 'Generic REST API',
            'description': 'Template for connecting to a generic REST API with API key authentication',
            'config_type': 'api',
            'template': {
                'authentication_type': 'api_key',
                'timeout': 30,
                'rate_limit': 100,
                'retry_attempts': 3,
                'additional_headers': {}
            },
            'required_fields': ['connection_id', 'base_url', 'api_key'],
            'example': {
                'connection_id': 'my-rest-api',
                'base_url': 'https://api.example.com/v1',
                'api_key': 'your-api-key-here'
            }
        }
    
    @staticmethod
    def list_templates() -> List[Dict[str, Any]]:
        """Get list of all available templates."""
        return [
            ConfigurationTemplates.get_aws_rds_sql_server_template(),
            ConfigurationTemplates.get_aws_rds_mysql_template(),
            ConfigurationTemplates.get_api_gateway_template(),
            ConfigurationTemplates.get_rest_api_template()
        ]