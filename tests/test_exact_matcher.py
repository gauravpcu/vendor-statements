"""
Unit tests for exact matching algorithms.

Tests exact matching functionality for invoice numbers, dates, amounts,
and other fields with various matching options.
"""

from datetime import datetime, date
from decimal import Decimal

from invoice_matching.models import InvoiceData
from invoice_matching.matching.exact_matcher import ExactMatcher, ExactMatchResult


class TestExactMatcher:
    """Test cases for ExactMatcher class."""
    
    def setup_method(self):
        """Setup test environment."""
        self.matcher = ExactMatcher()
    
    def test_match_invoice_number_exact(self):
        """Test exact invoice number matching."""
        result = self.matcher.match_invoice_number("INV-001", "INV-001")
        
        assert result.matches is True
        assert result.field_name == 'invoice_number'
        assert result.match_type == 'case_insensitive'
        assert result.confidence == 1.0
    
    def test_match_invoice_number_case_insensitive(self):
        """Test case-insensitive invoice number matching."""
        result = self.matcher.match_invoice_number("INV-001", "inv-001", case_sensitive=False)
        
        assert result.matches is True
        assert result.match_type == 'case_insensitive'
        assert result.confidence == 1.0
    
    def test_match_invoice_number_case_sensitive(self):
        """Test case-sensitive invoice number matching."""
        result = self.matcher.match_invoice_number("INV-001", "inv-001", case_sensitive=True)
        
        assert result.matches is False
        assert result.match_type == 'exact'
        assert result.confidence == 0.0
    
    def test_match_invoice_number_different(self):
        """Test non-matching invoice numbers."""
        result = self.matcher.match_invoice_number("INV-001", "INV-002")
        
        assert result.matches is False
        assert result.confidence == 0.0
    
    def test_match_invoice_number_empty(self):
        """Test matching with empty invoice numbers."""
        result = self.matcher.match_invoice_number("", "INV-001")
        
        assert result.matches is False
        assert result.confidence == 0.0
    
    def test_match_vendor_name_exact(self):
        """Test exact vendor name matching."""
        result = self.matcher.match_vendor_name("ABC Corporation", "ABC Corporation")
        
        assert result.matches is True
        assert result.field_name == 'vendor_name'
        assert result.confidence == 1.0
    
    def test_match_vendor_name_case_insensitive(self):
        """Test case-insensitive vendor name matching."""
        result = self.matcher.match_vendor_name("ABC Corporation", "abc corporation")
        
        assert result.matches is True
        assert result.match_type == 'normalized_case_insensitive'
        assert result.confidence == 1.0
    
    def test_match_vendor_name_whitespace_normalization(self):
        """Test vendor name matching with whitespace normalization."""
        result = self.matcher.match_vendor_name("ABC  Corporation", "ABC Corporation")
        
        assert result.matches is True
        assert result.match_type == 'normalized_case_insensitive'
        assert result.confidence == 1.0
    
    def test_match_vendor_name_no_normalization(self):
        """Test vendor name matching without normalization."""
        result = self.matcher.match_vendor_name(
            "ABC  Corporation", 
            "ABC Corporation", 
            normalize_whitespace=False
        )
        
        assert result.matches is False
        assert result.confidence == 0.0
    
    def test_match_customer_name(self):
        """Test customer name matching."""
        result = self.matcher.match_customer_name("XYZ Company", "xyz company")
        
        assert result.matches is True
        assert result.field_name == 'customer_name'
        assert result.confidence == 1.0
    
    def test_match_date_exact(self):
        """Test exact date matching."""
        date1 = datetime(2024, 1, 15)
        date2 = datetime(2024, 1, 15)
        
        result = self.matcher.match_date(date1, date2)
        
        assert result.matches is True
        assert result.field_name == 'invoice_date'
        assert result.match_type == 'exact'
        assert result.confidence == 1.0
    
    def test_match_date_different(self):
        """Test non-matching dates."""
        date1 = datetime(2024, 1, 15)
        date2 = datetime(2024, 1, 20)
        
        result = self.matcher.match_date(date1, date2)
        
        assert result.matches is False
        assert result.confidence == 0.0
    
    def test_match_date_with_tolerance(self):
        """Test date matching with tolerance."""
        date1 = datetime(2024, 1, 15)
        date2 = datetime(2024, 1, 17)  # 2 days difference
        
        result = self.matcher.match_date(date1, date2, tolerance_days=3)
        
        assert result.matches is True
        assert result.match_type == 'tolerance_3_days'
        assert result.confidence > 0.5  # Should have reduced confidence
        assert result.confidence < 1.0
    
    def test_match_date_outside_tolerance(self):
        """Test date matching outside tolerance."""
        date1 = datetime(2024, 1, 15)
        date2 = datetime(2024, 1, 25)  # 10 days difference
        
        result = self.matcher.match_date(date1, date2, tolerance_days=5)
        
        assert result.matches is False
        assert result.confidence == 0.0
    
    def test_match_amount_exact(self):
        """Test exact amount matching."""
        result = self.matcher.match_amount(Decimal('1500.00'), Decimal('1500.00'))
        
        assert result.matches is True
        assert result.field_name == 'total_amount'
        assert result.match_type == 'exact_precision_2'
        assert result.confidence == 1.0
    
    def test_match_amount_different_precision(self):
        """Test amount matching with different precision."""
        result = self.matcher.match_amount(Decimal('1500.0'), Decimal('1500.00'))
        
        assert result.matches is True
        assert result.confidence == 1.0
    
    def test_match_amount_string_input(self):
        """Test amount matching with string inputs."""
        result = self.matcher.match_amount("$1,500.00", "1500.00")
        
        assert result.matches is True
        assert result.confidence == 1.0
    
    def test_match_amount_different(self):
        """Test non-matching amounts."""
        result = self.matcher.match_amount(Decimal('1500.00'), Decimal('1600.00'))
        
        assert result.matches is False
        assert result.confidence == 0.0
    
    def test_match_amount_precision_rounding(self):
        """Test amount matching with precision rounding."""
        result = self.matcher.match_amount(
            Decimal('1500.004'), 
            Decimal('1500.006'), 
            precision=2
        )
        
        assert result.matches is True  # Both round to 1500.00
        assert result.confidence == 1.0
    
    def test_match_amount_invalid_input(self):
        """Test amount matching with invalid input."""
        result = self.matcher.match_amount("invalid", "1500.00")
        
        assert result.matches is False
        assert result.match_type == 'error'
        assert result.confidence == 0.0
    
    def test_match_field_invoice_number(self):
        """Test generic field matching for invoice number."""
        result = self.matcher.match_field('invoice_number', 'INV-001', 'inv-001')
        
        assert result.matches is True
        assert result.field_name == 'invoice_number'
    
    def test_match_field_vendor_name(self):
        """Test generic field matching for vendor name."""
        result = self.matcher.match_field('vendor_name', 'ABC Corp', 'abc corp')
        
        assert result.matches is True
        assert result.field_name == 'vendor_name'
    
    def test_match_field_date(self):
        """Test generic field matching for date."""
        date1 = datetime(2024, 1, 15)
        date2 = datetime(2024, 1, 15)
        
        result = self.matcher.match_field('invoice_date', date1, date2)
        
        assert result.matches is True
        assert result.field_name == 'invoice_date'
    
    def test_match_field_amount(self):
        """Test generic field matching for amount."""
        result = self.matcher.match_field('total_amount', '1500.00', '1500.00')
        
        assert result.matches is True
        assert result.field_name == 'total_amount'
    
    def test_match_field_generic(self):
        """Test generic field matching for unknown field."""
        result = self.matcher.match_field('custom_field', 'value1', 'value1')
        
        assert result.matches is True
        assert result.field_name == 'custom_field'
        assert result.match_type == 'case_insensitive'
    
    def test_match_invoice_data_complete(self):
        """Test matching complete invoice data."""
        invoice_data = InvoiceData(
            invoice_number="INV-001",
            vendor_name="ABC Corporation",
            customer_name="XYZ Company",
            invoice_date=datetime(2024, 1, 15),
            total_amount=Decimal('1500.00'),
            facility_name="Main Office",
            po_number="PO-12345"
        )
        
        candidate_data = {
            'invoice_number': 'INV-001',
            'vendor_name': 'ABC Corporation',
            'customer_name': 'XYZ Company',
            'invoice_date': datetime(2024, 1, 15),
            'total_amount': Decimal('1500.00'),
            'facility_name': 'Main Office',
            'po_number': 'PO-12345'
        }
        
        results = self.matcher.match_invoice_data(invoice_data, candidate_data)
        
        # Should have results for all matched fields
        assert len(results) >= 5  # At least the required fields
        
        # All matches should be successful
        successful_matches = [r for r in results if r.matches]
        assert len(successful_matches) == len(results)
        
        # Check specific field results
        invoice_number_result = next(r for r in results if r.field_name == 'invoice_number')
        assert invoice_number_result.matches is True
        
        vendor_result = next(r for r in results if r.field_name == 'vendor_name')
        assert vendor_result.matches is True
        
        amount_result = next(r for r in results if r.field_name == 'total_amount')
        assert amount_result.matches is True
    
    def test_match_invoice_data_partial(self):
        """Test matching invoice data with some mismatches."""
        invoice_data = InvoiceData(
            invoice_number="INV-001",
            vendor_name="ABC Corporation",
            customer_name="XYZ Company",
            invoice_date=datetime(2024, 1, 15),
            total_amount=Decimal('1500.00')
        )
        
        candidate_data = {
            'invoice_number': 'INV-001',  # Match
            'vendor_name': 'Different Corp',  # No match
            'customer_name': 'XYZ Company',  # Match
            'invoice_date': datetime(2024, 1, 20),  # No match (different date)
            'total_amount': Decimal('1600.00')  # No match (different amount)
        }
        
        results = self.matcher.match_invoice_data(invoice_data, candidate_data)
        
        # Should have results for all fields
        assert len(results) == 5
        
        # Check specific matches
        matches = {r.field_name: r.matches for r in results}
        assert matches['invoice_number'] is True
        assert matches['vendor_name'] is False
        assert matches['customer_name'] is True
        assert matches['invoice_date'] is False
        assert matches['total_amount'] is False
    
    def test_match_invoice_data_with_options(self):
        """Test matching invoice data with custom options."""
        invoice_data = InvoiceData(
            invoice_number="INV-001",
            vendor_name="ABC Corporation",
            customer_name="XYZ Company",
            invoice_date=datetime(2024, 1, 15),
            total_amount=Decimal('1500.00')
        )
        
        candidate_data = {
            'invoice_number': 'INV-001',
            'vendor_name': 'ABC Corporation',
            'customer_name': 'XYZ Company',
            'invoice_date': datetime(2024, 1, 18),  # 3 days difference
            'total_amount': Decimal('1500.00')
        }
        
        # Use date tolerance
        matching_options = {
            'date_tolerance_days': 5
        }
        
        results = self.matcher.match_invoice_data(invoice_data, candidate_data, matching_options)
        
        # Date should match with tolerance
        date_result = next(r for r in results if r.field_name == 'invoice_date')
        assert date_result.matches is True
        assert date_result.match_type == 'tolerance_5_days'


class TestExactMatchResult:
    """Test cases for ExactMatchResult class."""
    
    def test_exact_match_result_creation(self):
        """Test creating ExactMatchResult."""
        result = ExactMatchResult(
            field_name='test_field',
            matches=True,
            expected_value='expected',
            actual_value='actual',
            match_type='exact',
            confidence=1.0
        )
        
        assert result.field_name == 'test_field'
        assert result.matches is True
        assert result.expected_value == 'expected'
        assert result.actual_value == 'actual'
        assert result.match_type == 'exact'
        assert result.confidence == 1.0
    
    def test_exact_match_result_to_dict(self):
        """Test converting ExactMatchResult to dictionary."""
        result = ExactMatchResult(
            field_name='invoice_number',
            matches=False,
            expected_value='INV-001',
            actual_value='INV-002',
            match_type='exact',
            confidence=0.0
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['field_name'] == 'invoice_number'
        assert result_dict['matches'] is False
        assert result_dict['expected_value'] == 'INV-001'
        assert result_dict['actual_value'] == 'INV-002'
        assert result_dict['match_type'] == 'exact'
        assert result_dict['confidence'] == 0.0


def run_basic_exact_matcher_test():
    """Run basic exact matcher functionality test."""
    print("Testing exact matcher...")
    
    matcher = ExactMatcher()
    
    # Test invoice number matching
    result = matcher.match_invoice_number("INV-001", "inv-001")
    print(f"✓ Invoice number match: {result.matches} (confidence: {result.confidence})")
    
    # Test vendor name matching
    result = matcher.match_vendor_name("ABC Corp", "abc  corp")
    print(f"✓ Vendor name match: {result.matches} (type: {result.match_type})")
    
    # Test date matching
    date1 = datetime(2024, 1, 15)
    date2 = datetime(2024, 1, 17)
    result = matcher.match_date(date1, date2, tolerance_days=3)
    print(f"✓ Date match with tolerance: {result.matches} (confidence: {result.confidence:.2f})")
    
    # Test amount matching
    result = matcher.match_amount("$1,500.00", "1500.00")
    print(f"✓ Amount match: {result.matches} (type: {result.match_type})")
    
    # Test complete invoice matching
    invoice_data = InvoiceData(
        invoice_number="INV-001",
        vendor_name="Test Vendor",
        customer_name="Test Customer",
        invoice_date=datetime(2024, 1, 15),
        total_amount=Decimal('1000.00')
    )
    
    candidate_data = {
        'invoice_number': 'INV-001',
        'vendor_name': 'Test Vendor',
        'customer_name': 'Test Customer',
        'invoice_date': datetime(2024, 1, 15),
        'total_amount': Decimal('1000.00')
    }
    
    results = matcher.match_invoice_data(invoice_data, candidate_data)
    matches = sum(1 for r in results if r.matches)
    print(f"✓ Complete invoice match: {matches}/{len(results)} fields matched")
    
    print("🎉 Exact matcher working!")


if __name__ == "__main__":
    run_basic_exact_matcher_test()