"""
Unit tests for API connector with mock HTTP responses.

Tests API connector functionality including authentication, rate limiting,
retry logic, and AWS integration features.
"""

import json
import time
from unittest.mock import Mock, patch, MagicMock
from invoice_matching.models import APIConnectionConfig, AuthenticationType, ConnectionType
from invoice_matching.connectors.api_connector import APIConnector, APIResponse, RateLimiter, AWSSignatureV4


class TestRateLimiter:
    """Test cases for RateLimiter class."""
    
    def test_rate_limiter_creation(self):
        """Test creating rate limiter with specified rate."""
        limiter = RateLimiter(rate_limit=60)  # 60 requests per minute
        
        assert limiter.rate_limit == 60
        assert limiter.tokens == 60
        assert limiter.acquire() is True  # Should allow first request
    
    def test_rate_limiter_token_consumption(self):
        """Test that tokens are consumed on acquire."""
        limiter = RateLimiter(rate_limit=2)  # 2 requests per minute
        
        # Should allow first two requests
        assert limiter.acquire() is True
        assert limiter.acquire() is True
        
        # Third request should be rate limited
        assert limiter.acquire() is False
    
    def test_rate_limiter_token_replenishment(self):
        """Test that tokens are replenished over time."""
        limiter = RateLimiter(rate_limit=60)  # 1 request per second
        
        # Consume all tokens
        for _ in range(60):
            limiter.acquire()
        
        # Should be rate limited
        assert limiter.acquire() is False
        
        # Mock time passage (1 second = 1 token)
        limiter.last_update -= 1.0  # Simulate 1 second ago
        assert limiter.acquire() is True
    
    def test_wait_time_calculation(self):
        """Test wait time calculation when rate limited."""
        limiter = RateLimiter(rate_limit=60)  # 1 request per second
        
        # Consume all tokens
        for _ in range(60):
            limiter.acquire()
        
        wait_time = limiter.wait_time()
        assert wait_time > 0
        assert wait_time <= 1.0  # Should be less than 1 second


class TestAWSSignatureV4:
    """Test cases for AWS Signature V4 signing."""
    
    def test_aws_signature_creation(self):
        """Test creating AWS signature signer."""
        signer = AWSSignatureV4(
            access_key="AKIAIOSFODNN7EXAMPLE",
            secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1",
            service="execute-api"
        )
        
        assert signer.access_key == "AKIAIOSFODNN7EXAMPLE"
        assert signer.region == "us-east-1"
        assert signer.service == "execute-api"
    
    def test_request_signing(self):
        """Test signing an HTTP request."""
        signer = AWSSignatureV4(
            access_key="AKIAIOSFODNN7EXAMPLE",
            secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1",
            service="execute-api"
        )
        
        headers = {'Content-Type': 'application/json'}
        signed_headers = signer.sign_request(
            method="POST",
            url="https://api.example.com/invoices/search",
            headers=headers,
            payload='{"invoice_number": "INV-001"}'
        )
        
        assert 'Authorization' in signed_headers
        assert 'X-Amz-Date' in signed_headers
        assert 'Host' in signed_headers
        assert signed_headers['Authorization'].startswith('AWS4-HMAC-SHA256')


class TestAPIConnector:
    """Test cases for APIConnector class."""
    
    def create_test_config(self) -> APIConnectionConfig:
        """Create a test API configuration."""
        return APIConnectionConfig(
            connection_id="test-api",
            base_url="https://api.example.com/v1",
            api_key="test-api-key",
            authentication_type=AuthenticationType.API_KEY,
            timeout=30,
            rate_limit=100,
            retry_attempts=3
        )
    
    def test_api_connector_creation(self):
        """Test creating API connector with configuration."""
        config = self.create_test_config()
        connector = APIConnector(config)
        
        assert connector.connection_id == "test-api"
        assert connector.config == config
        assert connector.rate_limiter.rate_limit == 100
        assert connector.session is not None
    
    @patch('requests.Session.get')
    def test_connection_test_success(self, mock_get):
        """Test successful connection test."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_get.return_value = mock_response
        
        config = self.create_test_config()
        connector = APIConnector(config)
        
        result = connector.test_connection()
        
        assert result.success is True
        assert result.connection_id == "test-api"
        assert result.connection_type == ConnectionType.REST_API
        assert result.response_time > 0
        assert result.error_message is None
        assert result.additional_info['status_code'] == 200
    
    @patch('requests.Session.get')
    def test_connection_test_failure(self, mock_get):
        """Test failed connection test."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response
        
        config = self.create_test_config()
        connector = APIConnector(config)
        
        result = connector.test_connection()
        
        assert result.success is False
        assert result.connection_id == "test-api"
        assert result.error_message is not None
        assert "404" in result.error_message
    
    @patch('requests.Session.get')
    def test_connection_test_exception(self, mock_get):
        """Test connection test with network exception."""
        # Mock network exception
        mock_get.side_effect = Exception("Network error")
        
        config = self.create_test_config()
        connector = APIConnector(config)
        
        result = connector.test_connection()
        
        assert result.success is False
        assert result.error_message == "Network error"
        assert connector.is_healthy() is False
    
    @patch('requests.Session.request')
    def test_search_invoices_success(self, mock_request):
        """Test successful invoice search."""
        # Mock successful search response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"invoices": [{"id": "1", "invoice_number": "INV-001"}]}'
        mock_response.json.return_value = {
            "invoices": [{"id": "1", "invoice_number": "INV-001"}]
        }
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"invoices": [{"id": "1", "invoice_number": "INV-001"}]}'
        mock_request.return_value = mock_response
        
        config = self.create_test_config()
        connector = APIConnector(config)
        
        search_criteria = {"invoice_number": "INV-001"}
        results = connector.search_invoices(search_criteria)
        
        assert len(results) == 1
        assert results[0]["id"] == "1"
        assert results[0]["invoice_number"] == "INV-001"
        
        # Verify request was made correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert 'invoices/search' in call_args[1]['url']
        assert call_args[1]['json'] == search_criteria
    
    @patch('requests.Session.request')
    def test_search_invoices_with_results_key(self, mock_request):
        """Test invoice search with results in 'results' key."""
        # Mock response with 'results' key
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"results": [{"id": "2", "invoice_number": "INV-002"}]}'
        mock_response.json.return_value = {
            "results": [{"id": "2", "invoice_number": "INV-002"}]
        }
        mock_response.headers = {}
        mock_response.text = '{"results": [{"id": "2", "invoice_number": "INV-002"}]}'
        mock_request.return_value = mock_response
        
        config = self.create_test_config()
        connector = APIConnector(config)
        
        results = connector.search_invoices({"vendor_name": "Test Vendor"})
        
        assert len(results) == 1
        assert results[0]["id"] == "2"
    
    @patch('requests.Session.request')
    def test_search_invoices_direct_list(self, mock_request):
        """Test invoice search with direct list response."""
        # Mock response as direct list
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'[{"id": "3", "invoice_number": "INV-003"}]'
        mock_response.json.return_value = [{"id": "3", "invoice_number": "INV-003"}]
        mock_response.headers = {}
        mock_response.text = '[{"id": "3", "invoice_number": "INV-003"}]'
        mock_request.return_value = mock_response
        
        config = self.create_test_config()
        connector = APIConnector(config)
        
        results = connector.search_invoices({"customer_name": "Test Customer"})
        
        assert len(results) == 1
        assert results[0]["id"] == "3"
    
    @patch('requests.Session.request')
    def test_search_invoices_failure(self, mock_request):
        """Test failed invoice search."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.content = b'{"error": "Internal server error"}'
        mock_response.json.return_value = {"error": "Internal server error"}
        mock_response.headers = {}
        mock_response.text = '{"error": "Internal server error"}'
        mock_request.return_value = mock_response
        
        config = self.create_test_config()
        connector = APIConnector(config)
        
        try:
            connector.search_invoices({"invoice_number": "INV-404"})
            assert False, "Should have raised ConnectorError"
        except Exception as e:
            assert "Search failed" in str(e)
    
    def test_authentication_setup_api_key(self):
        """Test API key authentication setup."""
        config = APIConnectionConfig(
            connection_id="api-key-test",
            base_url="https://api.example.com",
            api_key="secret-key",
            authentication_type=AuthenticationType.API_KEY
        )
        
        connector = APIConnector(config)
        
        assert 'X-API-Key' in connector.session.headers
        assert connector.session.headers['X-API-Key'] == "secret-key"
    
    def test_authentication_setup_bearer_token(self):
        """Test Bearer token authentication setup."""
        config = APIConnectionConfig(
            connection_id="bearer-test",
            base_url="https://api.example.com",
            api_key="bearer-token",
            authentication_type=AuthenticationType.BEARER_TOKEN
        )
        
        connector = APIConnector(config)
        
        assert 'Authorization' in connector.session.headers
        assert connector.session.headers['Authorization'] == "Bearer bearer-token"
    
    def test_authentication_setup_basic_auth(self):
        """Test Basic authentication setup."""
        config = APIConnectionConfig(
            connection_id="basic-test",
            base_url="https://api.example.com",
            api_key="username:password",
            authentication_type=AuthenticationType.BASIC_AUTH
        )
        
        connector = APIConnector(config)
        
        assert connector.session.auth is not None
        assert connector.session.auth.username == "username"
        assert connector.session.auth.password == "password"
    
    def test_authentication_setup_aws_iam(self):
        """Test AWS IAM authentication setup."""
        config = APIConnectionConfig(
            connection_id="aws-test",
            base_url="https://api.example.com",
            api_key="access_key:secret_key",
            authentication_type=AuthenticationType.AWS_IAM,
            aws_region="us-east-1"
        )
        
        connector = APIConnector(config)
        
        assert connector.aws_signer is not None
        assert connector.aws_signer.access_key == "access_key"
        assert connector.aws_signer.secret_key == "secret_key"
        assert connector.aws_signer.region == "us-east-1"
    
    def test_get_connection_info(self):
        """Test getting connection information."""
        config = self.create_test_config()
        connector = APIConnector(config)
        
        info = connector.get_connection_info()
        
        assert info['connection_id'] == "test-api"
        assert info['connection_type'] == 'REST_API'
        assert info['base_url'] == "https://api.example.com/v1"
        assert info['authentication_type'] == 'api_key'
        assert info['rate_limit'] == 100
        assert info['timeout'] == 30
        assert 'healthy' in info
    
    def test_get_rate_limit_info(self):
        """Test getting rate limit information."""
        config = self.create_test_config()
        connector = APIConnector(config)
        
        rate_info = connector.get_rate_limit_info()
        
        assert rate_info['rate_limit'] == 100
        assert 'tokens_available' in rate_info
        assert 'wait_time' in rate_info
        assert rate_info['wait_time'] >= 0
    
    @patch('time.sleep')
    @patch('requests.Session.request')
    def test_rate_limiting_behavior(self, mock_request, mock_sleep):
        """Test rate limiting behavior during requests."""
        # Create connector with very low rate limit
        config = APIConnectionConfig(
            connection_id="rate-limit-test",
            base_url="https://api.example.com",
            api_key="test-key",
            authentication_type=AuthenticationType.API_KEY,
            rate_limit=1  # 1 request per minute
        )
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'[]'
        mock_response.json.return_value = []
        mock_response.headers = {}
        mock_response.text = '[]'
        mock_request.return_value = mock_response
        
        connector = APIConnector(config)
        
        # First request should succeed
        connector.search_invoices({"test": "1"})
        
        # Second request should trigger rate limiting
        connector.search_invoices({"test": "2"})
        
        # Should have called sleep due to rate limiting
        mock_sleep.assert_called()


def run_basic_api_connector_test():
    """Run basic API connector functionality test."""
    print("Testing API connector basic functionality...")
    
    # Test configuration creation
    config = APIConnectionConfig(
        connection_id="test-connector",
        base_url="https://httpbin.org",  # Public testing API
        api_key="test-key",
        authentication_type=AuthenticationType.API_KEY,
        timeout=10,
        rate_limit=60
    )
    
    # Test connector creation
    connector = APIConnector(config)
    print(f"✓ Created connector: {connector.connection_id}")
    
    # Test connection info
    info = connector.get_connection_info()
    print(f"✓ Connection info: {info['connection_type']}")
    
    # Test rate limiter
    rate_info = connector.get_rate_limit_info()
    print(f"✓ Rate limit info: {rate_info['rate_limit']} req/min")
    
    print("✓ API connector basic functionality test passed")


if __name__ == "__main__":
    run_basic_api_connector_test()