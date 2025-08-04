"""
Unit tests for authentication mechanisms.

Tests various authentication methods including API keys, Bearer tokens,
Basic authentication, and AWS IAM authentication.
"""

import json
import base64
from datetime import datetime, timedelta
from invoice_matching.models import AuthenticationType
from invoice_matching.connectors.authentication import (
    APIKeyAuthenticator, BearerTokenAuthenticator, BasicAuthAuthenticator,
    AWSIAMAuthenticator, AuthenticatorFactory, AuthenticationError
)


class TestAPIKeyAuthenticator:
    """Test cases for API Key authentication."""
    
    def test_api_key_creation(self):
        """Test creating API key authenticator."""
        auth = APIKeyAuthenticator("test-api-key")
        
        assert auth.auth_type == AuthenticationType.API_KEY
        assert auth.api_key == "test-api-key"
        assert auth.header_name == "X-API-Key"
        assert auth.is_valid() is True
    
    def test_api_key_custom_header(self):
        """Test API key with custom header name."""
        auth = APIKeyAuthenticator("custom-key", "Authorization")
        
        assert auth.header_name == "Authorization"
    
    def test_api_key_apply_authentication(self):
        """Test applying API key to headers."""
        auth = APIKeyAuthenticator("secret-key", "X-Custom-Key")
        headers = {"Content-Type": "application/json"}
        
        result = auth.apply_authentication(headers)
        
        assert result["X-Custom-Key"] == "secret-key"
        assert result["Content-Type"] == "application/json"
        assert len(result) == 2
    
    def test_api_key_invalid(self):
        """Test invalid API key."""
        auth = APIKeyAuthenticator("")
        
        assert auth.is_valid() is False


class TestBearerTokenAuthenticator:
    """Test cases for Bearer Token authentication."""
    
    def test_bearer_token_creation(self):
        """Test creating Bearer token authenticator."""
        auth = BearerTokenAuthenticator("access-token-123")
        
        assert auth.auth_type == AuthenticationType.BEARER_TOKEN
        assert auth.access_token == "access-token-123"
        assert auth.refresh_token is None
        assert auth.expires_at is None
        assert auth.is_valid() is True
    
    def test_bearer_token_with_expiration(self):
        """Test Bearer token with expiration."""
        future_time = datetime.utcnow() + timedelta(hours=1)
        auth = BearerTokenAuthenticator("token", expires_at=future_time)
        
        assert auth.is_valid() is True
        assert auth.expires_at == future_time
    
    def test_bearer_token_expired(self):
        """Test expired Bearer token."""
        past_time = datetime.utcnow() - timedelta(hours=1)
        auth = BearerTokenAuthenticator("token", expires_at=past_time)
        
        assert auth.is_valid() is False
    
    def test_bearer_token_near_expiration(self):
        """Test Bearer token near expiration (within 5 minute buffer)."""
        near_future = datetime.utcnow() + timedelta(minutes=3)
        auth = BearerTokenAuthenticator("token", expires_at=near_future)
        
        # Should be considered invalid due to 5-minute buffer
        assert auth.is_valid() is False
    
    def test_bearer_token_apply_authentication(self):
        """Test applying Bearer token to headers."""
        auth = BearerTokenAuthenticator("bearer-token-456")
        headers = {"Accept": "application/json"}
        
        result = auth.apply_authentication(headers)
        
        assert result["Authorization"] == "Bearer bearer-token-456"
        assert result["Accept"] == "application/json"
    
    def test_bearer_token_refresh_simulation(self):
        """Test Bearer token refresh simulation."""
        past_time = datetime.utcnow() - timedelta(hours=1)
        auth = BearerTokenAuthenticator(
            "old-token",
            refresh_token="refresh-123",
            expires_at=past_time,
            refresh_url="https://api.example.com/refresh"
        )
        
        # Token should be expired
        assert auth.is_valid() is False
        
        # Refresh should work (simulated)
        assert auth.refresh_if_needed() is True
        
        # Token should now be valid
        assert auth.is_valid() is True
        assert auth.access_token.startswith("refreshed_")


class TestBasicAuthAuthenticator:
    """Test cases for Basic Authentication."""
    
    def test_basic_auth_creation(self):
        """Test creating Basic auth authenticator."""
        auth = BasicAuthAuthenticator("username", "password")
        
        assert auth.auth_type == AuthenticationType.BASIC_AUTH
        assert auth.username == "username"
        assert auth.password == "password"
        assert auth.is_valid() is True
    
    def test_basic_auth_apply_authentication(self):
        """Test applying Basic auth to headers."""
        auth = BasicAuthAuthenticator("testuser", "testpass")
        headers = {"User-Agent": "test-client"}
        
        result = auth.apply_authentication(headers)
        
        assert "Authorization" in result
        assert result["Authorization"].startswith("Basic ")
        assert result["User-Agent"] == "test-client"
        
        # Decode and verify credentials
        encoded_creds = result["Authorization"].split(" ")[1]
        decoded_creds = base64.b64decode(encoded_creds).decode('utf-8')
        assert decoded_creds == "testuser:testpass"
    
    def test_basic_auth_invalid(self):
        """Test invalid Basic auth credentials."""
        auth1 = BasicAuthAuthenticator("", "password")
        auth2 = BasicAuthAuthenticator("username", "")
        
        assert auth1.is_valid() is False
        assert auth2.is_valid() is False


class TestAWSIAMAuthenticator:
    """Test cases for AWS IAM authentication."""
    
    def test_aws_iam_creation(self):
        """Test creating AWS IAM authenticator."""
        auth = AWSIAMAuthenticator(
            "AKIAIOSFODNN7EXAMPLE",
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "us-east-1"
        )
        
        assert auth.auth_type == AuthenticationType.AWS_IAM
        assert auth.access_key == "AKIAIOSFODNN7EXAMPLE"
        assert auth.region == "us-east-1"
        assert auth.service == "execute-api"
        assert auth.is_valid() is True
    
    def test_aws_iam_with_session_token(self):
        """Test AWS IAM with session token."""
        auth = AWSIAMAuthenticator(
            "AKIAIOSFODNN7EXAMPLE",
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "us-west-2",
            "execute-api",
            "session-token-123"
        )
        
        assert auth.session_token == "session-token-123"
        assert auth.region == "us-west-2"
    
    def test_aws_iam_apply_authentication(self):
        """Test applying AWS IAM signature to headers."""
        auth = AWSIAMAuthenticator(
            "AKIAIOSFODNN7EXAMPLE",
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "us-east-1"
        )
        
        headers = {"Content-Type": "application/json"}
        
        result = auth.apply_authentication(
            headers,
            method="POST",
            url="https://api.example.com/invoices/search",
            payload='{"test": "data"}'
        )
        
        assert "Authorization" in result
        assert result["Authorization"].startswith("AWS4-HMAC-SHA256")
        assert "X-Amz-Date" in result
        assert "Host" in result
        assert result["Host"] == "api.example.com"
        assert result["Content-Type"] == "application/json"
    
    def test_aws_iam_with_session_token_headers(self):
        """Test AWS IAM signature with session token in headers."""
        auth = AWSIAMAuthenticator(
            "AKIAIOSFODNN7EXAMPLE",
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "us-east-1",
            session_token="temp-session-token"
        )
        
        result = auth.apply_authentication(
            {},
            method="GET",
            url="https://api.example.com/health"
        )
        
        assert "X-Amz-Security-Token" in result
        assert result["X-Amz-Security-Token"] == "temp-session-token"
    
    def test_aws_iam_invalid_credentials(self):
        """Test invalid AWS IAM credentials."""
        auth1 = AWSIAMAuthenticator("", "secret", "us-east-1")
        auth2 = AWSIAMAuthenticator("access", "", "us-east-1")
        auth3 = AWSIAMAuthenticator("access", "secret", "")
        
        assert auth1.is_valid() is False
        assert auth2.is_valid() is False
        assert auth3.is_valid() is False
    
    def test_aws_iam_missing_url_error(self):
        """Test AWS IAM authentication without URL."""
        auth = AWSIAMAuthenticator(
            "AKIAIOSFODNN7EXAMPLE",
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "us-east-1"
        )
        
        try:
            auth.apply_authentication({})
            assert False, "Should have raised AuthenticationError"
        except Exception as e:
            assert "URL is required" in str(e)


class TestAuthenticatorFactory:
    """Test cases for AuthenticatorFactory."""
    
    def test_create_api_key_authenticator(self):
        """Test creating API key authenticator via factory."""
        auth = AuthenticatorFactory.create_authenticator(
            AuthenticationType.API_KEY,
            "factory-api-key"
        )
        
        assert isinstance(auth, APIKeyAuthenticator)
        assert auth.api_key == "factory-api-key"
        assert auth.header_name == "X-API-Key"
    
    def test_create_api_key_with_custom_header(self):
        """Test creating API key authenticator with custom header."""
        auth = AuthenticatorFactory.create_authenticator(
            AuthenticationType.API_KEY,
            "custom-key",
            header_name="Authorization"
        )
        
        assert isinstance(auth, APIKeyAuthenticator)
        assert auth.header_name == "Authorization"
    
    def test_create_bearer_token_simple(self):
        """Test creating Bearer token authenticator with simple token."""
        auth = AuthenticatorFactory.create_authenticator(
            AuthenticationType.BEARER_TOKEN,
            "simple-bearer-token"
        )
        
        assert isinstance(auth, BearerTokenAuthenticator)
        assert auth.access_token == "simple-bearer-token"
        assert auth.refresh_token is None
    
    def test_create_bearer_token_complex(self):
        """Test creating Bearer token authenticator with JSON credentials."""
        token_data = {
            "access_token": "complex-token",
            "refresh_token": "refresh-token",
            "expires_at": "2024-12-31T23:59:59",
            "refresh_url": "https://api.example.com/refresh"
        }
        
        auth = AuthenticatorFactory.create_authenticator(
            AuthenticationType.BEARER_TOKEN,
            json.dumps(token_data)
        )
        
        assert isinstance(auth, BearerTokenAuthenticator)
        assert auth.access_token == "complex-token"
        assert auth.refresh_token == "refresh-token"
        assert auth.refresh_url == "https://api.example.com/refresh"
        assert auth.expires_at is not None
    
    def test_create_basic_auth_authenticator(self):
        """Test creating Basic auth authenticator via factory."""
        auth = AuthenticatorFactory.create_authenticator(
            AuthenticationType.BASIC_AUTH,
            "testuser:testpass"
        )
        
        assert isinstance(auth, BasicAuthAuthenticator)
        assert auth.username == "testuser"
        assert auth.password == "testpass"
    
    def test_create_basic_auth_invalid_format(self):
        """Test creating Basic auth with invalid format."""
        try:
            AuthenticatorFactory.create_authenticator(
                AuthenticationType.BASIC_AUTH,
                "invalid-format"
            )
            assert False, "Should have raised AuthenticationError"
        except Exception as e:
            assert "username:password" in str(e)
    
    def test_create_aws_iam_authenticator(self):
        """Test creating AWS IAM authenticator via factory."""
        auth = AuthenticatorFactory.create_authenticator(
            AuthenticationType.AWS_IAM,
            "AKIAIOSFODNN7EXAMPLE:wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-west-2",
            service="lambda"
        )
        
        assert isinstance(auth, AWSIAMAuthenticator)
        assert auth.access_key == "AKIAIOSFODNN7EXAMPLE"
        assert auth.secret_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert auth.region == "us-west-2"
        assert auth.service == "lambda"
    
    def test_create_aws_iam_invalid_format(self):
        """Test creating AWS IAM with invalid format."""
        try:
            AuthenticatorFactory.create_authenticator(
                AuthenticationType.AWS_IAM,
                "invalid-format"
            )
            assert False, "Should have raised AuthenticationError"
        except Exception as e:
            assert "access_key:secret_key" in str(e)
    
    def test_get_supported_types(self):
        """Test getting supported authentication types."""
        supported = AuthenticatorFactory.get_supported_types()
        
        assert AuthenticationType.API_KEY in supported
        assert AuthenticationType.BEARER_TOKEN in supported
        assert AuthenticationType.BASIC_AUTH in supported
        assert AuthenticationType.AWS_IAM in supported
        assert len(supported) == 4


def run_basic_authentication_test():
    """Run basic authentication functionality test."""
    print("Testing authentication mechanisms...")
    
    # Test API Key
    api_auth = APIKeyAuthenticator("test-key")
    headers = api_auth.apply_authentication({"Content-Type": "application/json"})
    print(f"✓ API Key auth: {headers.get('X-API-Key')}")
    
    # Test Bearer Token
    bearer_auth = BearerTokenAuthenticator("bearer-token")
    headers = bearer_auth.apply_authentication({})
    print(f"✓ Bearer Token auth: {headers.get('Authorization')}")
    
    # Test Basic Auth
    basic_auth = BasicAuthAuthenticator("user", "pass")
    headers = basic_auth.apply_authentication({})
    print(f"✓ Basic auth: {headers.get('Authorization')[:20]}...")
    
    # Test AWS IAM
    aws_auth = AWSIAMAuthenticator("AKIATEST", "secretkey", "us-east-1")
    headers = aws_auth.apply_authentication(
        {},
        method="GET",
        url="https://api.example.com/test"
    )
    print(f"✓ AWS IAM auth: {headers.get('Authorization')[:30]}...")
    
    # Test Factory
    factory_auth = AuthenticatorFactory.create_authenticator(
        AuthenticationType.API_KEY,
        "factory-key"
    )
    print(f"✓ Factory created: {type(factory_auth).__name__}")
    
    print("✅ Authentication mechanisms working!")


if __name__ == "__main__":
    run_basic_authentication_test()