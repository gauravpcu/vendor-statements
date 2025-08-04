"""
Invoice Matching System

A comprehensive system for matching extracted invoice data against
internal and external databases and APIs to verify invoice authenticity,
detect duplicates, and identify discrepancies.

This package provides:
- Core data models for invoice matching
- Database and API connectors
- Fuzzy matching algorithms
- Result classification system
- Configuration management
- Audit and logging capabilities
"""

from .models import (
    # Core data models
    InvoiceData,
    Match,
    MatchResult,
    Discrepancy,
    
    # Configuration models
    SQLConnectionConfig,
    APIConnectionConfig,
    ConnectionTestResult,
    MatchingSettings,
    
    # Enums
    MatchType,
    VarianceType,
    ConnectionType,
    AuthenticationType,
    
    # Exceptions
    InvoiceMatchingError,
    ConnectionError,
    ConfigurationError,
    MatchingError,
    ValidationError
)

__version__ = "1.0.0"
__author__ = "Invoice Processing System"

__all__ = [
    # Core data models
    "InvoiceData",
    "Match", 
    "MatchResult",
    "Discrepancy",
    
    # Configuration models
    "SQLConnectionConfig",
    "APIConnectionConfig", 
    "ConnectionTestResult",
    "MatchingSettings",
    
    # Enums
    "MatchType",
    "VarianceType",
    "ConnectionType",
    "AuthenticationType",
    
    # Exceptions
    "InvoiceMatchingError",
    "ConnectionError",
    "ConfigurationError", 
    "MatchingError",
    "ValidationError"
]