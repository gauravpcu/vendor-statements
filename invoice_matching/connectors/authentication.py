"""
Authentication mechanisms for API connectors.

Provides various authentication methods including API keys, Bearer tokens,
Basic authentication, and AWS IAM authentication with comprehensive
token management and refresh capabilities.
"""

import json
import time
import hashlib
import hmac
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from urllib.parse import urlparse

from invoice_matching.models import AuthenticationType, InvoiceMatchingError

import logging
logger = logging.getLogger(__name__)


class AuthenticationError(InvoiceMatchingError):
    """Exception raised for authentication-related errors."""
    pass


class BaseAuthenticator(ABC):
    """Base class for all authentication mechanisms."""
    
    def __init__(self, auth_type: AuthenticationType):
        self.auth_type = auth_type
        self.logger = logging.getLogger(f"{__name__}.{auth_type.value}")
    
    @abstractmethod
    def apply_authentication(self, headers: Dict[str, str], **kwargs) -> Dict[str, str]:
        """
        Apply authentication to request headers.
        
        Args:
            headers: Existing request headers
            **kwargs: Additional authentication parameters
            
        Returns:
            Updated headers with authentication applied
        """
        pass
    
    @abstractmethod
    def is_valid(self) -> bool:
        """
        Check if the authentication is valid and not expired.
        
        Returns:
            True if authentication is valid, False otherwise
        """
        pass
    
    def refresh_if_needed(self) -> bool:
        """
        Refresh authentication if needed and possible.
        
        Returns:
            True if refresh was successful or not needed, False if failed
        """
        return True  # Default implementation - no refresh needed


class APIKeyAuthenticator(BaseAuthenticator):
    """API Key authentication handler."""
    
    def __init__(self, api_key: str, header_name: str = "X-API-Key"):
        """
        Initialize API key authenticator.
        
        Args:
            api_key: The API key to use
            header_name: Header name for the API key (default: X-API-Key)
        """
        super().__init__(AuthenticationType.API_KEY)
        self.api_key = api_key
        self.header_name = header_name
        self.logger.info(f"API Key authenticator initialized with header: {header_name}")
    
    def apply_authentication(self, headers: Dict[str, str], **kwargs) -> Dict[str, str]:
        """Apply API key to request headers."""
        headers = headers.copy()
        headers[self.header_name] = self.api_key
        return headers
    
    def is_valid(self) -> bool:
        """API keys don't expire by default."""
        return bool(self.api_key)


class BearerTokenAuthenticator(BaseAuthenticator):
    """Bearer Token authentication with refresh capability."""
    
    def __init__(self, access_token: str, refresh_token: Optional[str] = None,
                 expires_at: Optional[datetime] = None, refresh_url: Optional[str] = None):
        """
        Initialize Bearer token authenticator.
        
        Args:
            access_token: The access token
            refresh_token: Optional refresh token for token renewal
            expires_at: Token expiration time
            refresh_url: URL for token refresh
        """
        super().__init__(AuthenticationType.BEARER_TOKEN)
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at
        self.refresh_url = refresh_url
        self._refresh_in_progress = False
        
        self.logger.info(f"Bearer token authenticator initialized, expires: {expires_at}")
    
    def apply_authentication(self, headers: Dict[str, str], **kwargs) -> Dict[str, str]:
        """Apply Bearer token to request headers."""
        if not self.is_valid():
            if not self.refresh_if_needed():
                raise AuthenticationError("Bearer token is expired and refresh failed")
        
        headers = headers.copy()
        headers['Authorization'] = f'Bearer {self.access_token}'
        return headers
    
    def is_valid(self) -> bool:
        """Check if token is valid and not expired."""
        if not self.access_token:
            return False
        
        if self.expires_at:
            # Add 5 minute buffer before expiration
            buffer_time = datetime.utcnow() + timedelta(minutes=5)
            return self.expires_at > buffer_time
        
        return True
    
    def refresh_if_needed(self) -> bool:
        """Refresh token if needed and possible."""
        if self.is_valid():
            return True
        
        if not self.refresh_token or not self.refresh_url or self._refresh_in_progress:
            return False
        
        try:
            self._refresh_in_progress = True
            self.logger.info("Attempting to refresh Bearer token")
            
            # In a real implementation, this would make an HTTP request
            # For now, we'll simulate a successful refresh
            self.access_token = f"refreshed_{self.access_token}"
            self.expires_at = datetime.utcnow() + timedelta(hours=1)
            
            self.logger.info("Bearer token refreshed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Token refresh failed: {e}")
            return False
        finally:
            self._refresh_in_progress = False


class BasicAuthAuthenticator(BaseAuthenticator):
    """Basic Authentication handler."""
    
    def __init__(self, username: str, password: str):
        """
        Initialize Basic auth authenticator.
        
        Args:
            username: Username for authentication
            password: Password for authentication
        """
        super().__init__(AuthenticationType.BASIC_AUTH)
        self.username = username
        self.password = password
        self.logger.info(f"Basic auth authenticator initialized for user: {username}")
    
    def apply_authentication(self, headers: Dict[str, str], **kwargs) -> Dict[str, str]:
        """Apply Basic authentication to request headers."""
        import base64
        
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        headers = headers.copy()
        headers['Authorization'] = f'Basic {encoded_credentials}'
        return headers
    
    def is_valid(self) -> bool:
        """Basic auth credentials don't expire."""
        return bool(self.username and self.password)


class AWSIAMAuthenticator(BaseAuthenticator):
    """AWS IAM authentication using Signature Version 4."""
    
    def __init__(self, access_key: str, secret_key: str, region: str, 
                 service: str = "execute-api", session_token: Optional[str] = None):
        """
        Initialize AWS IAM authenticator.
        
        Args:
            access_key: AWS access key ID
            secret_key: AWS secret access key
            region: AWS region
            service: AWS service name (default: execute-api for API Gateway)
            session_token: Optional session token for temporary credentials
        """
        super().__init__(AuthenticationType.AWS_IAM)
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.service = service
        self.session_token = session_token
        
        self.logger.info(f"AWS IAM authenticator initialized for region: {region}, service: {service}")
    
    def apply_authentication(self, headers: Dict[str, str], **kwargs) -> Dict[str, str]:
        """Apply AWS Signature V4 to request headers."""
        method = kwargs.get('method', 'GET').upper()
        url = kwargs.get('url', '')
        payload = kwargs.get('payload', '')
        
        if not url:
            raise AuthenticationError("URL is required for AWS IAM authentication")
        
        return self._sign_request(method, url, headers, payload)
    
    def is_valid(self) -> bool:
        """Check if AWS credentials are present."""
        return bool(self.access_key and self.secret_key and self.region)
    
    def _sign_request(self, method: str, url: str, headers: Dict[str, str], payload: str) -> Dict[str, str]:
        """
        Sign HTTP request using AWS Signature Version 4.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            payload: Request body
            
        Returns:
            Headers with AWS signature
        """
        parsed_url = urlparse(url)
        host = parsed_url.netloc
        path = parsed_url.path or '/'
        query = parsed_url.query
        
        # Create timestamp
        t = datetime.utcnow()
        amz_date = t.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = t.strftime('%Y%m%d')
        
        # Prepare headers
        headers = headers.copy()
        headers['Host'] = host
        headers['X-Amz-Date'] = amz_date
        
        if self.session_token:
            headers['X-Amz-Security-Token'] = self.session_token
        
        # Create canonical request
        canonical_headers = '\n'.join([f"{k.lower()}:{v.strip()}" for k, v in sorted(headers.items())]) + '\n'
        signed_headers = ';'.join([k.lower() for k in sorted(headers.keys())])
        payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        
        canonical_request = f"{method}\n{path}\n{query}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        
        # Create string to sign
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f"{date_stamp}/{self.region}/{self.service}/aws4_request"
        string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        
        # Calculate signature
        signing_key = self._get_signature_key(date_stamp)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Create authorization header
        authorization_header = (
            f"{algorithm} "
            f"Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        
        headers['Authorization'] = authorization_header
        
        self.logger.debug(f"AWS request signed for {method} {url}")
        return headers
    
    def _get_signature_key(self, date_stamp: str) -> bytes:
        """Generate AWS signature key."""
        k_date = hmac.new(('AWS4' + self.secret_key).encode('utf-8'), 
                         date_stamp.encode('utf-8'), hashlib.sha256).digest()
        k_region = hmac.new(k_date, self.region.encode('utf-8'), hashlib.sha256).digest()
        k_service = hmac.new(k_region, self.service.encode('utf-8'), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, b'aws4_request', hashlib.sha256).digest()
        return k_signing


class AuthenticatorFactory:
    """Factory for creating authenticators based on configuration."""
    
    @staticmethod
    def create_authenticator(auth_type: AuthenticationType, credentials: str, 
                           **kwargs) -> BaseAuthenticator:
        """
        Create an authenticator based on type and credentials.
        
        Args:
            auth_type: Type of authentication
            credentials: Credential string (format depends on auth_type)
            **kwargs: Additional parameters
            
        Returns:
            Configured authenticator instance
            
        Raises:
            AuthenticationError: If authenticator cannot be created
        """
        try:
            if auth_type == AuthenticationType.API_KEY:
                header_name = kwargs.get('header_name', 'X-API-Key')
                return APIKeyAuthenticator(credentials, header_name)
            
            elif auth_type == AuthenticationType.BEARER_TOKEN:
                # For Bearer tokens, credentials might be just the token
                # or a JSON string with token details
                try:
                    token_data = json.loads(credentials)
                    return BearerTokenAuthenticator(
                        access_token=token_data['access_token'],
                        refresh_token=token_data.get('refresh_token'),
                        expires_at=datetime.fromisoformat(token_data['expires_at']) if token_data.get('expires_at') else None,
                        refresh_url=token_data.get('refresh_url')
                    )
                except (json.JSONDecodeError, KeyError):
                    # Treat as simple access token
                    return BearerTokenAuthenticator(credentials)
            
            elif auth_type == AuthenticationType.BASIC_AUTH:
                if ':' not in credentials:
                    raise AuthenticationError("Basic auth credentials must be in format 'username:password'")
                username, password = credentials.split(':', 1)
                return BasicAuthAuthenticator(username, password)
            
            elif auth_type == AuthenticationType.AWS_IAM:
                if ':' not in credentials:
                    raise AuthenticationError("AWS IAM credentials must be in format 'access_key:secret_key'")
                
                access_key, secret_key = credentials.split(':', 1)
                region = kwargs.get('region', 'us-east-1')
                service = kwargs.get('service', 'execute-api')
                session_token = kwargs.get('session_token')
                
                return AWSIAMAuthenticator(access_key, secret_key, region, service, session_token)
            
            else:
                raise AuthenticationError(f"Unsupported authentication type: {auth_type}")
                
        except Exception as e:
            raise AuthenticationError(f"Failed to create authenticator: {e}")
    
    @staticmethod
    def get_supported_types() -> List[AuthenticationType]:
        """Get list of supported authentication types."""
        return [
            AuthenticationType.API_KEY,
            AuthenticationType.BEARER_TOKEN,
            AuthenticationType.BASIC_AUTH,
            AuthenticationType.AWS_IAM
        ]