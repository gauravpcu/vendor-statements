"""
Database and API connectors for invoice matching.

This package provides connectors for various data sources including:
- REST API connectors with AWS integration
- SQL database connectors for AWS RDS
- Connection management and pooling
- Authentication and security handling
"""

from .api_connector import APIConnector, APIResponse
from .base_connector import BaseConnector, ConnectorError
from .authentication import (
    AuthenticatorFactory, BaseAuthenticator, APIKeyAuthenticator,
    BearerTokenAuthenticator, BasicAuthAuthenticator, AWSIAMAuthenticator,
    AuthenticationError
)

__all__ = [
    "APIConnector",
    "APIResponse", 
    "BaseConnector",
    "ConnectorError",
    "AuthenticatorFactory",
    "BaseAuthenticator",
    "APIKeyAuthenticator",
    "BearerTokenAuthenticator", 
    "BasicAuthAuthenticator",
    "AWSIAMAuthenticator",
    "AuthenticationError"
]