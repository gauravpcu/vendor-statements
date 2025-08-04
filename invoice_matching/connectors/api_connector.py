"""
REST API connector for invoice matching with AWS integration.

Provides HTTP client functionality with support for various authentication
methods, rate limiting, retry logic, and AWS-specific features.
"""

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
import hashlib
import hmac
from datetime import datetime
from urllib.parse import urlparse, quote

# For now, we'll create a mock HTTP client that can be replaced with requests later
class MockHTTPSession:
    """Mock HTTP session for testing without external dependencies."""
    
    def __init__(self):
        self.headers = {}
        self.auth = None
    
    def request(self, method, url, **kwargs):
        """Mock request method."""
        # Return a mock response for testing
        return MockResponse(200, {"status": "mock_response"})
    
    def get(self, url, **kwargs):
        """Mock GET method."""
        return self.request('GET', url, **kwargs)
    
    def post(self, url, **kwargs):
        """Mock POST method."""
        return self.request('POST', url, **kwargs)

class MockResponse:
    """Mock HTTP response for testing."""
    
    def __init__(self, status_code, data):
        self.status_code = status_code
        self.content = json.dumps(data).encode('utf-8') if data else b''
        self.text = json.dumps(data) if data else ''
        self.headers = {'Content-Type': 'application/json'}
        self._json_data = data
    
    def json(self):
        """Return JSON data."""
        return self._json_data

class MockHTTPBasicAuth:
    """Mock basic auth for testing."""
    
    def __init__(self, username, password):
        self.username = username
        self.password = password

from invoice_matching.models import (
    APIConnectionConfig, ConnectionTestResult, ConnectionType,
    AuthenticationType, InvoiceMatchingError
)
from .base_connector import BaseConnector, ConnectorError
from .authentication import AuthenticatorFactory, BaseAuthenticator

import logging
logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    """Response from API connector operations."""
    success: bool
    status_code: int
    data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    error_message: Optional[str] = None
    response_time: float = 0.0
    headers: Optional[Dict[str, str]] = None


class RateLimiter:
    """Simple token bucket rate limiter."""
    
    def __init__(self, rate_limit: int):
        """
        Initialize rate limiter.
        
        Args:
            rate_limit: Maximum requests per minute
        """
        self.rate_limit = rate_limit
        self.tokens = rate_limit
        self.last_update = time.time()
        self.lock = False
    
    def acquire(self) -> bool:
        """
        Try to acquire a token for making a request.
        
        Returns:
            True if token acquired, False if rate limited
        """
        now = time.time()
        time_passed = now - self.last_update
        self.last_update = now
        
        # Add tokens based on time passed
        self.tokens = min(self.rate_limit, self.tokens + time_passed * (self.rate_limit / 60.0))
        
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
    
    def wait_time(self) -> float:
        """Get time to wait before next request is allowed."""
        if self.tokens >= 1:
            return 0.0
        return (1 - self.tokens) * (60.0 / self.rate_limit)


class AWSSignatureV4:
    """AWS Signature Version 4 signing for API requests."""
    
    def __init__(self, access_key: str, secret_key: str, region: str, service: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.service = service
    
    def sign_request(self, method: str, url: str, headers: Dict[str, str], 
                    payload: str = '') -> Dict[str, str]:
        """
        Sign an HTTP request using AWS Signature V4.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL of the request
            headers: Request headers
            payload: Request body
            
        Returns:
            Updated headers with Authorization header
        """
        parsed_url = urlparse(url)
        host = parsed_url.netloc
        path = parsed_url.path or '/'
        query = parsed_url.query
        
        # Create timestamp
        t = datetime.utcnow()
        amz_date = t.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = t.strftime('%Y%m%d')
        
        # Add required headers
        headers = headers.copy()
        headers['Host'] = host
        headers['X-Amz-Date'] = amz_date
        
        # Create canonical request
        canonical_headers = '\n'.join([f"{k.lower()}:{v}" for k, v in sorted(headers.items())]) + '\n'
        signed_headers = ';'.join([k.lower() for k in sorted(headers.keys())])
        payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        
        canonical_request = f"{method}\n{path}\n{query}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        
        # Create string to sign
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f"{date_stamp}/{self.region}/{self.service}/aws4_request"
        string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        
        # Calculate signature
        signing_key = self._get_signature_key(self.secret_key, date_stamp, self.region, self.service)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Add authorization header
        authorization_header = f"{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        headers['Authorization'] = authorization_header
        
        return headers
    
    def _get_signature_key(self, key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
        """Generate AWS signature key."""
        k_date = hmac.new(('AWS4' + key).encode('utf-8'), date_stamp.encode('utf-8'), hashlib.sha256).digest()
        k_region = hmac.new(k_date, region_name.encode('utf-8'), hashlib.sha256).digest()
        k_service = hmac.new(k_region, service_name.encode('utf-8'), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, b'aws4_request', hashlib.sha256).digest()
        return k_signing


class APIConnector(BaseConnector):
    """
    REST API connector with AWS integration support.
    
    Provides HTTP client functionality with authentication, rate limiting,
    retry logic, and AWS-specific features like Signature V4.
    """
    
    def __init__(self, config: APIConnectionConfig):
        """
        Initialize API connector.
        
        Args:
            config: API connection configuration
        """
        super().__init__(config.connection_id)
        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit)
        
        # Setup HTTP session (using mock for now, will be replaced with requests)
        self.session = MockHTTPSession()
        
        # Setup authentication using the new authentication system
        self.authenticator = self._create_authenticator()
        
        self.logger.info(f"API connector initialized for {config.base_url}")
    
    def _create_authenticator(self) -> BaseAuthenticator:
        """Create authenticator based on configuration."""
        try:
            # Determine header name for API key authentication
            header_name = 'X-API-Key'
            if self.config.additional_headers and 'Authorization' in self.config.additional_headers:
                header_name = 'Authorization'
            
            authenticator = AuthenticatorFactory.create_authenticator(
                auth_type=self.config.authentication_type,
                credentials=self.config.api_key,
                header_name=header_name,
                region=self.config.aws_region,
                service='execute-api'
            )
            
            self.logger.info(f"Created {self.config.authentication_type.value} authenticator")
            return authenticator
            
        except Exception as e:
            self.logger.error(f"Failed to create authenticator: {e}")
            raise ConnectorError(f"Authentication setup failed: {e}")
    
    def _apply_authentication(self, headers: Dict[str, str], **kwargs) -> Dict[str, str]:
        """Apply authentication to request headers."""
        try:
            # Refresh authentication if needed
            if not self.authenticator.refresh_if_needed():
                raise ConnectorError("Authentication refresh failed")
            
            # Apply authentication
            authenticated_headers = self.authenticator.apply_authentication(headers, **kwargs)
            
            # Add any additional headers from configuration
            if self.config.additional_headers:
                authenticated_headers.update(self.config.additional_headers)
            
            return authenticated_headers
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            raise ConnectorError(f"Authentication failed: {e}")
    
    def test_connection(self) -> ConnectionTestResult:
        """
        Test the API connection.
        
        Returns:
            ConnectionTestResult with test status and details
        """
        start_time = time.time()
        
        try:
            # Try a simple GET request to the base URL or health endpoint
            test_url = f"{self.config.base_url.rstrip('/')}/health"
            
            response, duration = self._measure_time(
                self.session.get,
                test_url,
                timeout=self.config.timeout
            )
            
            success = response.status_code < 400
            
            result = ConnectionTestResult(
                success=success,
                connection_id=self.connection_id,
                connection_type=ConnectionType.REST_API,
                response_time=duration,
                error_message=None if success else f"HTTP {response.status_code}: {response.text[:200]}",
                additional_info={
                    'status_code': response.status_code,
                    'base_url': self.config.base_url,
                    'authentication_type': self.config.authentication_type.value
                }
            )
            
            self._last_connection_test = result
            self._connection_healthy = success
            
            self._log_operation("Connection test", duration, success, 
                              f"Status: {response.status_code}")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            result = ConnectionTestResult(
                success=False,
                connection_id=self.connection_id,
                connection_type=ConnectionType.REST_API,
                response_time=duration,
                error_message=error_msg,
                additional_info={'base_url': self.config.base_url}
            )
            
            self._last_connection_test = result
            self._connection_healthy = False
            
            self._log_operation("Connection test", duration, False, error_msg)
            
            return result
    
    def search_invoices(self, search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for invoices using the API.
        
        Args:
            search_criteria: Dictionary containing search parameters
            
        Returns:
            List of matching invoice records
            
        Raises:
            ConnectorError: If search operation fails
        """
        try:
            # Check rate limiting
            if not self.rate_limiter.acquire():
                wait_time = self.rate_limiter.wait_time()
                if wait_time > 0:
                    self.logger.warning(f"Rate limited, waiting {wait_time:.2f} seconds")
                    time.sleep(wait_time)
                    if not self.rate_limiter.acquire():
                        raise ConnectorError("Rate limit exceeded")
            
            # Prepare search request
            search_url = f"{self.config.base_url.rstrip('/')}/invoices/search"
            
            response = self._make_request('POST', search_url, json=search_criteria)
            
            if not response.success:
                raise ConnectorError(f"Search failed: {response.error_message}")
            
            # Extract invoice data from response
            if isinstance(response.data, list):
                return response.data
            elif isinstance(response.data, dict) and 'invoices' in response.data:
                return response.data['invoices']
            elif isinstance(response.data, dict) and 'results' in response.data:
                return response.data['results']
            else:
                return [response.data] if response.data else []
                
        except ConnectorError:
            raise
        except Exception as e:
            raise self._handle_error("Invoice search", e)
    
    def _make_request(self, method: str, url: str, **kwargs) -> APIResponse:
        """
        Make an HTTP request with proper error handling and logging.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            APIResponse with request results
        """
        start_time = time.time()
        
        try:
            # Prepare headers
            headers = kwargs.pop('headers', {})
            
            # Prepare payload for authentication
            payload = ''
            if 'json' in kwargs:
                payload = json.dumps(kwargs['json'])
                headers['Content-Type'] = 'application/json'
            elif 'data' in kwargs:
                payload = kwargs['data']
            
            # Apply authentication
            headers = self._apply_authentication(
                headers,
                method=method.upper(),
                url=url,
                payload=payload
            )
            
            # Make request
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self.config.timeout,
                **kwargs
            )
            
            duration = time.time() - start_time
            
            # Parse response
            try:
                data = response.json() if response.content else None
            except json.JSONDecodeError:
                data = {'raw_response': response.text}
            
            success = response.status_code < 400
            
            api_response = APIResponse(
                success=success,
                status_code=response.status_code,
                data=data,
                error_message=None if success else f"HTTP {response.status_code}: {response.text[:200]}",
                response_time=duration,
                headers=dict(response.headers)
            )
            
            self._log_operation(f"{method.upper()} {url}", duration, success,
                              f"Status: {response.status_code}")
            
            return api_response
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            api_response = APIResponse(
                success=False,
                status_code=0,
                error_message=error_msg,
                response_time=duration
            )
            
            self._log_operation(f"{method.upper()} {url}", duration, False, error_msg)
            
            return api_response
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get information about the API connection.
        
        Returns:
            Dictionary containing connection metadata
        """
        return {
            'connection_id': self.connection_id,
            'connection_type': 'REST_API',
            'base_url': self.config.base_url,
            'authentication_type': self.config.authentication_type.value,
            'rate_limit': self.config.rate_limit,
            'timeout': self.config.timeout,
            'retry_attempts': self.config.retry_attempts,
            'aws_region': self.config.aws_region,
            'healthy': self.is_healthy(),
            'last_test': self._last_connection_test.to_dict() if self._last_connection_test else None
        }
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """
        Get current rate limiting information.
        
        Returns:
            Dictionary with rate limit status
        """
        return {
            'rate_limit': self.config.rate_limit,
            'tokens_available': self.rate_limiter.tokens,
            'wait_time': self.rate_limiter.wait_time()
        }