"""
Core data models for invoice matching system.

This module defines the fundamental data structures used throughout the
invoice matching process, including invoice data, match results, and
configuration models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class MatchType(Enum):
    """Types of matches that can be found during invoice matching."""
    FOUND = "found"
    NOT_FOUND = "not_found"
    PARTIAL_MATCH = "partial_match"


class VarianceType(Enum):
    """Types of variances that can occur in partial matches."""
    AMOUNT_VARIANCE = "amount_variance"
    DATE_VARIANCE = "date_variance"
    NAME_MISMATCH = "name_mismatch"
    FIELD_MISSING = "field_missing"


class ConnectionType(Enum):
    """Types of database/API connections supported."""
    SQL_SERVER = "sql_server"
    MYSQL = "mysql"
    REST_API = "rest_api"


class AuthenticationType(Enum):
    """Authentication methods for API connections."""
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    AWS_IAM = "aws_iam"


@dataclass
class InvoiceData:
    """
    Represents invoice data extracted from processed files.
    
    This is the primary data structure that contains all relevant
    invoice information used for matching against databases/APIs.
    """
    invoice_number: str
    vendor_name: str
    customer_name: str
    invoice_date: datetime
    total_amount: Decimal
    facility_name: Optional[str] = None
    facility_code: Optional[str] = None
    po_number: Optional[str] = None
    currency: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'invoice_number': self.invoice_number,
            'vendor_name': self.vendor_name,
            'customer_name': self.customer_name,
            'invoice_date': self.invoice_date.isoformat(),
            'total_amount': str(self.total_amount),
            'facility_name': self.facility_name,
            'facility_code': self.facility_code,
            'po_number': self.po_number,
            'currency': self.currency
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InvoiceData':
        """Create InvoiceData from dictionary."""
        return cls(
            invoice_number=data['invoice_number'],
            vendor_name=data['vendor_name'],
            customer_name=data['customer_name'],
            invoice_date=datetime.fromisoformat(data['invoice_date']),
            total_amount=Decimal(data['total_amount']),
            facility_name=data.get('facility_name'),
            facility_code=data.get('facility_code'),
            po_number=data.get('po_number'),
            currency=data.get('currency')
        )


@dataclass
class Discrepancy:
    """
    Represents a discrepancy found during invoice matching.
    
    Used to track differences between expected and actual values
    in partial matches.
    """
    field_name: str
    expected_value: Any
    actual_value: Any
    variance_type: VarianceType
    variance_amount: Optional[float] = None
    variance_percentage: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'field_name': self.field_name,
            'expected_value': str(self.expected_value),
            'actual_value': str(self.actual_value),
            'variance_type': self.variance_type.value,
            'variance_amount': self.variance_amount,
            'variance_percentage': self.variance_percentage
        }


@dataclass
class Match:
    """
    Represents a single match candidate found during database/API search.
    
    Contains the candidate data, confidence score, and any discrepancies
    found during comparison.
    """
    candidate_data: Dict[str, Any]
    confidence_score: float
    matched_fields: List[str]
    discrepancies: List[Discrepancy]
    match_type: MatchType
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'candidate_data': self.candidate_data,
            'confidence_score': self.confidence_score,
            'matched_fields': self.matched_fields,
            'discrepancies': [d.to_dict() for d in self.discrepancies],
            'match_type': self.match_type.value
        }


@dataclass
class MatchResult:
    """
    Complete result of an invoice matching operation.
    
    Contains the original invoice data, classification, all matches found,
    and metadata about the matching process.
    """
    invoice_data: InvoiceData
    classification: MatchType
    matches: List[Match]
    confidence_score: float
    processing_time: float
    search_criteria_used: Dict[str, Any]
    connection_used: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'invoice_data': self.invoice_data.to_dict(),
            'classification': self.classification.value,
            'matches': [m.to_dict() for m in self.matches],
            'confidence_score': self.confidence_score,
            'processing_time': self.processing_time,
            'search_criteria_used': self.search_criteria_used,
            'connection_used': self.connection_used,
            'error_message': self.error_message
        }


@dataclass
class SQLConnectionConfig:
    """Configuration for SQL database connections (AWS RDS focus)."""
    connection_id: str
    database_type: ConnectionType
    host: str
    port: int
    database: str
    username: str
    password: str  # Will be encrypted in storage
    connection_timeout: int = 30
    query_timeout: int = 60
    max_connections: int = 5
    use_ssl: bool = True
    aws_region: Optional[str] = None
    use_iam_auth: bool = False
    
    def to_dict(self, include_password: bool = False) -> Dict[str, Any]:
        """Convert to dictionary, optionally excluding password."""
        data = {
            'connection_id': self.connection_id,
            'database_type': self.database_type.value,
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'username': self.username,
            'connection_timeout': self.connection_timeout,
            'query_timeout': self.query_timeout,
            'max_connections': self.max_connections,
            'use_ssl': self.use_ssl,
            'aws_region': self.aws_region,
            'use_iam_auth': self.use_iam_auth
        }
        if include_password:
            data['password'] = self.password
        return data


@dataclass
class APIConnectionConfig:
    """Configuration for REST API connections."""
    connection_id: str
    base_url: str
    api_key: str  # Will be encrypted in storage
    authentication_type: AuthenticationType
    timeout: int = 30
    rate_limit: int = 100  # requests per minute
    retry_attempts: int = 3
    aws_region: Optional[str] = None
    additional_headers: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self, include_api_key: bool = False) -> Dict[str, Any]:
        """Convert to dictionary, optionally excluding API key."""
        data = {
            'connection_id': self.connection_id,
            'base_url': self.base_url,
            'authentication_type': self.authentication_type.value,
            'timeout': self.timeout,
            'rate_limit': self.rate_limit,
            'retry_attempts': self.retry_attempts,
            'aws_region': self.aws_region,
            'additional_headers': self.additional_headers
        }
        if include_api_key:
            data['api_key'] = self.api_key
        return data


@dataclass
class ConnectionTestResult:
    """Result of testing a database or API connection."""
    success: bool
    connection_id: str
    connection_type: ConnectionType
    response_time: float
    error_message: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'success': self.success,
            'connection_id': self.connection_id,
            'connection_type': self.connection_type.value,
            'response_time': self.response_time,
            'error_message': self.error_message,
            'additional_info': self.additional_info
        }


@dataclass
class MatchingSettings:
    """Configuration settings for matching algorithms."""
    fuzzy_match_threshold: float = 0.8  # 0.0 to 1.0
    date_tolerance_days: int = 7
    amount_variance_percentage: float = 5.0  # 5% tolerance
    enable_fuzzy_vendor_matching: bool = True
    enable_fuzzy_customer_matching: bool = True
    vendor_name_weight: float = 0.3
    customer_name_weight: float = 0.2
    invoice_number_weight: float = 0.4
    date_weight: float = 0.1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'fuzzy_match_threshold': self.fuzzy_match_threshold,
            'date_tolerance_days': self.date_tolerance_days,
            'amount_variance_percentage': self.amount_variance_percentage,
            'enable_fuzzy_vendor_matching': self.enable_fuzzy_vendor_matching,
            'enable_fuzzy_customer_matching': self.enable_fuzzy_customer_matching,
            'vendor_name_weight': self.vendor_name_weight,
            'customer_name_weight': self.customer_name_weight,
            'invoice_number_weight': self.invoice_number_weight,
            'date_weight': self.date_weight
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MatchingSettings':
        """Create MatchingSettings from dictionary."""
        return cls(**data)


# Custom exceptions for invoice matching
class InvoiceMatchingError(Exception):
    """Base exception for invoice matching operations."""
    pass


class ConnectionError(InvoiceMatchingError):
    """Raised when database or API connection fails."""
    pass


class ConfigurationError(InvoiceMatchingError):
    """Raised when configuration is invalid or missing."""
    pass


class MatchingError(InvoiceMatchingError):
    """Raised when matching operation fails."""
    pass


class ValidationError(InvoiceMatchingError):
    """Raised when data validation fails."""
    pass