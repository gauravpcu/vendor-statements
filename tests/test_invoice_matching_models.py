"""
Unit tests for invoice matching data models.

Tests data model validation, serialization, and core functionality.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from invoice_matching.models import (
    InvoiceData, Match, MatchResult, Discrepancy,
    SQLConnectionConfig, APIConnectionConfig, ConnectionTestResult,
    MatchingSettings, MatchType, VarianceType, ConnectionType,
    AuthenticationType, InvoiceMatchingError, ConnectionError,
    ConfigurationError, MatchingError, ValidationError
)


class TestInvoiceData:
    """Test cases for InvoiceData model."""
    
    def test_invoice_data_creation(self):
        """Test creating InvoiceData with required fields."""
        invoice = InvoiceData(
            invoice_number="INV-001",
            vendor_name="Test Vendor",
            customer_name="Test Customer",
            invoice_date=datetime(2024, 1, 15),
            total_amount=Decimal("1500.00")
        )
        
        assert invoice.invoice_number == "INV-001"
        assert invoice.vendor_name == "Test Vendor"
        assert invoice.customer_name == "Test Customer"
        assert invoice.invoice_date == datetime(2024, 1, 15)
        assert invoice.total_amount == Decimal("1500.00")
        assert invoice.facility_name is None
        assert invoice.po_number is None
    
    def test_invoice_data_with_optional_fields(self):
        """Test creating InvoiceData with all fields."""
        invoice = InvoiceData(
            invoice_number="INV-002",
            vendor_name="Test Vendor 2",
            customer_name="Test Customer 2",
            invoice_date=datetime(2024, 2, 20),
            total_amount=Decimal("2500.50"),
            facility_name="Main Office",
            facility_code="MO-001",
            po_number="PO-12345",
            currency="USD"
        )
        
        assert invoice.facility_name == "Main Office"
        assert invoice.facility_code == "MO-001"
        assert invoice.po_number == "PO-12345"
        assert invoice.currency == "USD"
    
    def test_invoice_data_to_dict(self):
        """Test converting InvoiceData to dictionary."""
        invoice = InvoiceData(
            invoice_number="INV-003",
            vendor_name="Test Vendor 3",
            customer_name="Test Customer 3",
            invoice_date=datetime(2024, 3, 25),
            total_amount=Decimal("3000.75"),
            facility_name="Branch Office"
        )
        
        result = invoice.to_dict()
        
        assert result['invoice_number'] == "INV-003"
        assert result['vendor_name'] == "Test Vendor 3"
        assert result['customer_name'] == "Test Customer 3"
        assert result['invoice_date'] == "2024-03-25T00:00:00"
        assert result['total_amount'] == "3000.75"
        assert result['facility_name'] == "Branch Office"
        assert result['po_number'] is None
    
    def test_invoice_data_from_dict(self):
        """Test creating InvoiceData from dictionary."""
        data = {
            'invoice_number': "INV-004",
            'vendor_name': "Test Vendor 4",
            'customer_name': "Test Customer 4",
            'invoice_date': "2024-04-30T00:00:00",
            'total_amount': "4000.25",
            'facility_name': "Remote Office",
            'facility_code': "RO-001",
            'po_number': "PO-67890",
            'currency': "EUR"
        }
        
        invoice = InvoiceData.from_dict(data)
        
        assert invoice.invoice_number == "INV-004"
        assert invoice.vendor_name == "Test Vendor 4"
        assert invoice.customer_name == "Test Customer 4"
        assert invoice.invoice_date == datetime(2024, 4, 30)
        assert invoice.total_amount == Decimal("4000.25")
        assert invoice.facility_name == "Remote Office"
        assert invoice.facility_code == "RO-001"
        assert invoice.po_number == "PO-67890"
        assert invoice.currency == "EUR"


class TestDiscrepancy:
    """Test cases for Discrepancy model."""
    
    def test_discrepancy_creation(self):
        """Test creating Discrepancy with basic fields."""
        discrepancy = Discrepancy(
            field_name="total_amount",
            expected_value=Decimal("1000.00"),
            actual_value=Decimal("1050.00"),
            variance_type=VarianceType.AMOUNT_VARIANCE,
            variance_amount=50.0,
            variance_percentage=5.0
        )
        
        assert discrepancy.field_name == "total_amount"
        assert discrepancy.expected_value == Decimal("1000.00")
        assert discrepancy.actual_value == Decimal("1050.00")
        assert discrepancy.variance_type == VarianceType.AMOUNT_VARIANCE
        assert discrepancy.variance_amount == 50.0
        assert discrepancy.variance_percentage == 5.0
    
    def test_discrepancy_to_dict(self):
        """Test converting Discrepancy to dictionary."""
        discrepancy = Discrepancy(
            field_name="vendor_name",
            expected_value="ABC Corp",
            actual_value="ABC Corporation",
            variance_type=VarianceType.NAME_MISMATCH
        )
        
        result = discrepancy.to_dict()
        
        assert result['field_name'] == "vendor_name"
        assert result['expected_value'] == "ABC Corp"
        assert result['actual_value'] == "ABC Corporation"
        assert result['variance_type'] == "name_mismatch"
        assert result['variance_amount'] is None
        assert result['variance_percentage'] is None


class TestMatch:
    """Test cases for Match model."""
    
    def test_match_creation(self):
        """Test creating Match with all components."""
        discrepancy = Discrepancy(
            field_name="total_amount",
            expected_value=Decimal("1000.00"),
            actual_value=Decimal("1050.00"),
            variance_type=VarianceType.AMOUNT_VARIANCE
        )
        
        match = Match(
            candidate_data={"id": "123", "invoice_number": "INV-001"},
            confidence_score=0.85,
            matched_fields=["invoice_number", "vendor_name"],
            discrepancies=[discrepancy],
            match_type=MatchType.PARTIAL_MATCH
        )
        
        assert match.candidate_data == {"id": "123", "invoice_number": "INV-001"}
        assert match.confidence_score == 0.85
        assert match.matched_fields == ["invoice_number", "vendor_name"]
        assert len(match.discrepancies) == 1
        assert match.match_type == MatchType.PARTIAL_MATCH
    
    def test_match_to_dict(self):
        """Test converting Match to dictionary."""
        match = Match(
            candidate_data={"id": "456"},
            confidence_score=1.0,
            matched_fields=["invoice_number"],
            discrepancies=[],
            match_type=MatchType.FOUND
        )
        
        result = match.to_dict()
        
        assert result['candidate_data'] == {"id": "456"}
        assert result['confidence_score'] == 1.0
        assert result['matched_fields'] == ["invoice_number"]
        assert result['discrepancies'] == []
        assert result['match_type'] == "found"


class TestSQLConnectionConfig:
    """Test cases for SQLConnectionConfig model."""
    
    def test_sql_connection_config_creation(self):
        """Test creating SQL connection configuration."""
        config = SQLConnectionConfig(
            connection_id="rds-sql-server-1",
            database_type=ConnectionType.SQL_SERVER,
            host="mydb.cluster-xyz.us-east-1.rds.amazonaws.com",
            port=1433,
            database="invoices",
            username="dbuser",
            password="encrypted_password",
            aws_region="us-east-1",
            use_iam_auth=True
        )
        
        assert config.connection_id == "rds-sql-server-1"
        assert config.database_type == ConnectionType.SQL_SERVER
        assert config.host == "mydb.cluster-xyz.us-east-1.rds.amazonaws.com"
        assert config.port == 1433
        assert config.database == "invoices"
        assert config.username == "dbuser"
        assert config.password == "encrypted_password"
        assert config.aws_region == "us-east-1"
        assert config.use_iam_auth is True
        assert config.use_ssl is True  # Default value
    
    def test_sql_connection_config_to_dict_without_password(self):
        """Test converting SQL config to dict without password."""
        config = SQLConnectionConfig(
            connection_id="rds-mysql-1",
            database_type=ConnectionType.MYSQL,
            host="mysql.cluster-abc.us-west-2.rds.amazonaws.com",
            port=3306,
            database="invoice_db",
            username="mysql_user",
            password="secret_password"
        )
        
        result = config.to_dict(include_password=False)
        
        assert result['connection_id'] == "rds-mysql-1"
        assert result['database_type'] == "mysql"
        assert result['host'] == "mysql.cluster-abc.us-west-2.rds.amazonaws.com"
        assert result['port'] == 3306
        assert 'password' not in result
    
    def test_sql_connection_config_to_dict_with_password(self):
        """Test converting SQL config to dict with password."""
        config = SQLConnectionConfig(
            connection_id="test-db",
            database_type=ConnectionType.MYSQL,
            host="localhost",
            port=3306,
            database="test",
            username="test_user",
            password="test_password"
        )
        
        result = config.to_dict(include_password=True)
        
        assert result['password'] == "test_password"


class TestAPIConnectionConfig:
    """Test cases for APIConnectionConfig model."""
    
    def test_api_connection_config_creation(self):
        """Test creating API connection configuration."""
        config = APIConnectionConfig(
            connection_id="invoice-api-1",
            base_url="https://api.invoices.com/v1",
            api_key="encrypted_api_key",
            authentication_type=AuthenticationType.API_KEY,
            timeout=45,
            rate_limit=200,
            aws_region="us-east-1",
            additional_headers={"X-Client-Version": "1.0"}
        )
        
        assert config.connection_id == "invoice-api-1"
        assert config.base_url == "https://api.invoices.com/v1"
        assert config.api_key == "encrypted_api_key"
        assert config.authentication_type == AuthenticationType.API_KEY
        assert config.timeout == 45
        assert config.rate_limit == 200
        assert config.aws_region == "us-east-1"
        assert config.additional_headers == {"X-Client-Version": "1.0"}
    
    def test_api_connection_config_to_dict_without_api_key(self):
        """Test converting API config to dict without API key."""
        config = APIConnectionConfig(
            connection_id="test-api",
            base_url="https://test.api.com",
            api_key="secret_key",
            authentication_type=AuthenticationType.BEARER_TOKEN
        )
        
        result = config.to_dict(include_api_key=False)
        
        assert result['connection_id'] == "test-api"
        assert result['base_url'] == "https://test.api.com"
        assert result['authentication_type'] == "bearer_token"
        assert 'api_key' not in result


class TestMatchingSettings:
    """Test cases for MatchingSettings model."""
    
    def test_matching_settings_defaults(self):
        """Test MatchingSettings with default values."""
        settings = MatchingSettings()
        
        assert settings.fuzzy_match_threshold == 0.8
        assert settings.date_tolerance_days == 7
        assert settings.amount_variance_percentage == 5.0
        assert settings.enable_fuzzy_vendor_matching is True
        assert settings.enable_fuzzy_customer_matching is True
        assert settings.vendor_name_weight == 0.3
        assert settings.customer_name_weight == 0.2
        assert settings.invoice_number_weight == 0.4
        assert settings.date_weight == 0.1
    
    def test_matching_settings_custom_values(self):
        """Test MatchingSettings with custom values."""
        settings = MatchingSettings(
            fuzzy_match_threshold=0.9,
            date_tolerance_days=14,
            amount_variance_percentage=10.0,
            enable_fuzzy_vendor_matching=False
        )
        
        assert settings.fuzzy_match_threshold == 0.9
        assert settings.date_tolerance_days == 14
        assert settings.amount_variance_percentage == 10.0
        assert settings.enable_fuzzy_vendor_matching is False
    
    def test_matching_settings_to_dict(self):
        """Test converting MatchingSettings to dictionary."""
        settings = MatchingSettings(fuzzy_match_threshold=0.75)
        result = settings.to_dict()
        
        assert result['fuzzy_match_threshold'] == 0.75
        assert result['date_tolerance_days'] == 7
        assert result['amount_variance_percentage'] == 5.0
    
    def test_matching_settings_from_dict(self):
        """Test creating MatchingSettings from dictionary."""
        data = {
            'fuzzy_match_threshold': 0.85,
            'date_tolerance_days': 10,
            'amount_variance_percentage': 7.5,
            'enable_fuzzy_vendor_matching': False,
            'vendor_name_weight': 0.4
        }
        
        settings = MatchingSettings.from_dict(data)
        
        assert settings.fuzzy_match_threshold == 0.85
        assert settings.date_tolerance_days == 10
        assert settings.amount_variance_percentage == 7.5
        assert settings.enable_fuzzy_vendor_matching is False
        assert settings.vendor_name_weight == 0.4


class TestExceptions:
    """Test cases for custom exceptions."""
    
    def test_invoice_matching_error(self):
        """Test base InvoiceMatchingError exception."""
        with pytest.raises(InvoiceMatchingError):
            raise InvoiceMatchingError("Base error")
    
    def test_connection_error(self):
        """Test ConnectionError exception."""
        with pytest.raises(ConnectionError):
            raise ConnectionError("Database connection failed")
        
        # Test that ConnectionError is a subclass of InvoiceMatchingError
        with pytest.raises(InvoiceMatchingError):
            raise ConnectionError("Connection issue")
    
    def test_configuration_error(self):
        """Test ConfigurationError exception."""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Invalid configuration")
    
    def test_matching_error(self):
        """Test MatchingError exception."""
        with pytest.raises(MatchingError):
            raise MatchingError("Matching operation failed")
    
    def test_validation_error(self):
        """Test ValidationError exception."""
        with pytest.raises(ValidationError):
            raise ValidationError("Data validation failed")


class TestEnums:
    """Test cases for enum values."""
    
    def test_match_type_enum(self):
        """Test MatchType enum values."""
        assert MatchType.FOUND.value == "found"
        assert MatchType.NOT_FOUND.value == "not_found"
        assert MatchType.PARTIAL_MATCH.value == "partial_match"
    
    def test_variance_type_enum(self):
        """Test VarianceType enum values."""
        assert VarianceType.AMOUNT_VARIANCE.value == "amount_variance"
        assert VarianceType.DATE_VARIANCE.value == "date_variance"
        assert VarianceType.NAME_MISMATCH.value == "name_mismatch"
        assert VarianceType.FIELD_MISSING.value == "field_missing"
    
    def test_connection_type_enum(self):
        """Test ConnectionType enum values."""
        assert ConnectionType.SQL_SERVER.value == "sql_server"
        assert ConnectionType.MYSQL.value == "mysql"
        assert ConnectionType.REST_API.value == "rest_api"
    
    def test_authentication_type_enum(self):
        """Test AuthenticationType enum values."""
        assert AuthenticationType.API_KEY.value == "api_key"
        assert AuthenticationType.BEARER_TOKEN.value == "bearer_token"
        assert AuthenticationType.BASIC_AUTH.value == "basic_auth"
        assert AuthenticationType.AWS_IAM.value == "aws_iam"