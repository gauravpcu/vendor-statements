"""
Unit tests for tolerance-based matching algorithms.

Tests date and amount tolerance matching with various tolerance settings
and confidence scoring.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from invoice_matching.models import InvoiceData
from invoice_matching.matching.tolerance_matcher import ToleranceMatcher, ToleranceMatchResult


class TestToleranceMatcher:
    """Test cases for ToleranceMatcher class."""
    
    def setup_method(self):
        """Setup test environment."""
        self.matcher = ToleranceMatcher()
    
    def test_match_date_exact(self):
        """Test exact date matching with tolerance."""
        date1 = datetime(2024, 1, 15)
        date2 = datetime(2024, 1, 15)
        
        result = self.matcher.match_date_with_tolerance(date1, date2, tolerance_days=7)
        
        assert result.matches is True
        assert result.field_name == 'invoice_date'
        assert result.tolerance_type == 'date_days'
        assert result.tolerance_value == 7
        assert result.actual_variance == 0
        assert result.confidence == 1.0
    
    def test_match_date_within_tolerance(self):
        """Test date matching within tolerance range."""
        date1 = datetime(2024, 1, 15)
        date2 = datetime(2024, 1, 18)  # 3 days difference
        
        result = self.matcher.match_date_with_tolerance(date1, date2, tolerance_days=5)
        
        assert result.matches is True
        assert result.actual_variance == 3
        assert result.confidence > 0.5  # Should have reduced confidence
        assert result.confidence < 1.0
    
    def test_match_date_outside_tolerance(self):
        """Test date matching outside tolerance range."""
        date1 = datetime(2024, 1, 15)
        date2 = datetime(2024, 1, 25)  # 10 days difference
        
        result = self.matcher.match_date_with_tolerance(date1, date2, tolerance_days=5)
        
        assert result.matches is False
        assert result.actual_variance == 10
        assert result.confidence < 0.5
    
    def test_match_date_zero_tolerance(self):
        """Test date matching with zero tolerance (exact match required)."""
        date1 = datetime(2024, 1, 15)
        date2 = datetime(2024, 1, 16)  # 1 day difference
        
        result = self.matcher.match_date_with_tolerance(date1, date2, tolerance_days=0)
        
        assert result.matches is False
        assert result.actual_variance == 1
        assert result.confidence == 0.0
    
    def test_match_date_empty(self):
        """Test date matching with empty values."""
        result = self.matcher.match_date_with_tolerance(None, datetime(2024, 1, 15))
        
        assert result.matches is False
        assert result.confidence == 0.0
    
    def test_match_amount_percentage_exact(self):
        """Test exact amount matching with percentage tolerance."""
        result = self.matcher.match_amount_with_percentage_tolerance(
            Decimal('1000.00'), 
            Decimal('1000.00'), 
            tolerance_percentage=5.0
        )
        
        assert result.matches is True
        assert result.field_name == 'total_amount'
        assert result.tolerance_type == 'amount_percentage'
        assert result.tolerance_value == 5.0
        assert result.actual_variance == 0.0
        assert result.variance_percentage == 0.0
        assert result.confidence == 1.0
    
    def test_match_amount_percentage_within_tolerance(self):
        """Test amount matching within percentage tolerance."""
        result = self.matcher.match_amount_with_percentage_tolerance(
            Decimal('1000.00'), 
            Decimal('1030.00'),  # 3% difference
            tolerance_percentage=5.0
        )
        
        assert result.matches is True
        assert result.actual_variance == 30.0
        assert result.variance_percentage == 3.0
        assert result.confidence > 0.5
        assert result.confidence < 1.0
    
    def test_match_amount_percentage_outside_tolerance(self):
        """Test amount matching outside percentage tolerance."""
        result = self.matcher.match_amount_with_percentage_tolerance(
            Decimal('1000.00'), 
            Decimal('1080.00'),  # 8% difference
            tolerance_percentage=5.0
        )
        
        assert result.matches is False
        assert result.actual_variance == 80.0
        assert result.variance_percentage == 8.0
        assert result.confidence < 0.5
    
    def test_match_amount_percentage_zero_expected(self):
        """Test amount matching with zero expected amount."""
        result = self.matcher.match_amount_with_percentage_tolerance(
            Decimal('0.00'), 
            Decimal('0.00'), 
            tolerance_percentage=5.0
        )
        
        assert result.matches is True
        assert result.variance_percentage == 0.0
        assert result.confidence == 1.0
    
    def test_match_amount_percentage_string_input(self):
        """Test amount matching with string inputs."""
        result = self.matcher.match_amount_with_percentage_tolerance(
            "$1,000.00", 
            "1,050.00",  # 5% difference
            tolerance_percentage=5.0
        )
        
        assert result.matches is True
        assert result.variance_percentage == 5.0
    
    def test_match_amount_absolute_exact(self):
        """Test exact amount matching with absolute tolerance."""
        result = self.matcher.match_amount_with_absolute_tolerance(
            Decimal('1000.00'), 
            Decimal('1000.00'), 
            tolerance_amount=Decimal('50.00')
        )
        
        assert result.matches is True
        assert result.field_name == 'total_amount'
        assert result.tolerance_type == 'amount_absolute'
        assert result.tolerance_value == 50.0
        assert result.actual_variance == 0.0
        assert result.confidence == 1.0
    
    def test_match_amount_absolute_within_tolerance(self):
        """Test amount matching within absolute tolerance."""
        result = self.matcher.match_amount_with_absolute_tolerance(
            Decimal('1000.00'), 
            Decimal('1030.00'),  # $30 difference
            tolerance_amount=Decimal('50.00')
        )
        
        assert result.matches is True
        assert result.actual_variance == 30.0
        assert result.confidence > 0.5
        assert result.confidence < 1.0
    
    def test_match_amount_absolute_outside_tolerance(self):
        """Test amount matching outside absolute tolerance."""
        result = self.matcher.match_amount_with_absolute_tolerance(
            Decimal('1000.00'), 
            Decimal('1080.00'),  # $80 difference
            tolerance_amount=Decimal('50.00')
        )
        
        assert result.matches is False
        assert result.actual_variance == 80.0
        assert result.confidence < 0.5
    
    def test_match_amount_absolute_string_tolerance(self):
        """Test amount matching with string tolerance amount."""
        result = self.matcher.match_amount_with_absolute_tolerance(
            "1000.00", 
            "1025.00",  # $25 difference
            tolerance_amount="30.00"
        )
        
        assert result.matches is True
        assert result.actual_variance == 25.0
        assert result.tolerance_value == 30.0
    
    def test_match_field_with_tolerance_date(self):
        """Test generic field matching for date with tolerance."""
        date1 = datetime(2024, 1, 15)
        date2 = datetime(2024, 1, 18)
        
        result = self.matcher.match_field_with_tolerance(
            'invoice_date', 
            date1, 
            date2, 
            tolerance_days=5
        )
        
        assert result.field_name == 'invoice_date'
        assert result.matches is True
        assert result.tolerance_type == 'date_days'
    
    def test_match_field_with_tolerance_amount_percentage(self):
        """Test generic field matching for amount with percentage tolerance."""
        result = self.matcher.match_field_with_tolerance(
            'total_amount', 
            '1000.00', 
            '1030.00', 
            tolerance_percentage=5.0
        )
        
        assert result.field_name == 'total_amount'
        assert result.matches is True
        assert result.tolerance_type == 'amount_percentage'
    
    def test_match_field_with_tolerance_amount_absolute(self):
        """Test generic field matching for amount with absolute tolerance."""
        result = self.matcher.match_field_with_tolerance(
            'total_amount', 
            '1000.00', 
            '1030.00', 
            tolerance_amount='50.00'
        )
        
        assert result.field_name == 'total_amount'
        assert result.matches is True
        assert result.tolerance_type == 'amount_absolute'
    
    def test_match_field_with_tolerance_non_tolerance_field(self):
        """Test generic field matching for non-tolerance field."""
        result = self.matcher.match_field_with_tolerance(
            'invoice_number', 
            'INV-001', 
            'INV-001'
        )
        
        assert result.field_name == 'invoice_number'
        assert result.matches is True
        assert result.tolerance_type == 'exact'
        assert result.confidence == 1.0
    
    def test_match_invoice_data_with_tolerance(self):
        """Test tolerance matching of complete invoice data."""
        invoice_data = InvoiceData(
            invoice_number="INV-001",
            vendor_name="ABC Corporation",
            customer_name="XYZ Company",
            invoice_date=datetime(2024, 1, 15),
            total_amount=Decimal('1000.00')
        )
        
        candidate_data = {
            'invoice_number': 'INV-001',
            'vendor_name': 'ABC Corporation',
            'customer_name': 'XYZ Company',
            'invoice_date': datetime(2024, 1, 18),  # 3 days difference
            'total_amount': Decimal('1030.00')  # 3% difference
        }
        
        tolerance_options = {
            'date_tolerance_days': 5,
            'amount_variance_percentage': 5.0
        }
        
        results = self.matcher.match_invoice_data_with_tolerance(
            invoice_data, 
            candidate_data, 
            tolerance_options
        )
        
        # Should have results for date and amount
        assert len(results) == 2
        
        # Check date tolerance match
        date_result = next(r for r in results if r.field_name == 'invoice_date')
        assert date_result.matches is True
        assert date_result.actual_variance == 3
        
        # Check amount tolerance match
        amount_result = next(r for r in results if r.field_name == 'total_amount')
        assert amount_result.matches is True
        assert amount_result.variance_percentage == 3.0
    
    def test_calculate_weighted_confidence(self):
        """Test weighted confidence calculation."""
        results = [
            ToleranceMatchResult(
                field_name='invoice_date',
                matches=True,
                expected_value=datetime(2024, 1, 15),
                actual_value=datetime(2024, 1, 18),
                tolerance_type='date_days',
                tolerance_value=5,
                actual_variance=3,
                confidence=0.7
            ),
            ToleranceMatchResult(
                field_name='total_amount',
                matches=True,
                expected_value=1000.00,
                actual_value=1030.00,
                tolerance_type='amount_percentage',
                tolerance_value=5.0,
                actual_variance=30.0,
                variance_percentage=3.0,
                confidence=0.8
            )
        ]
        
        # Test equal weights
        weighted_confidence = self.matcher.calculate_weighted_confidence(results)
        expected_confidence = (0.7 + 0.8) / 2
        assert abs(weighted_confidence - expected_confidence) < 0.001
        
        # Test custom weights
        field_weights = {'invoice_date': 0.3, 'total_amount': 0.7}
        weighted_confidence = self.matcher.calculate_weighted_confidence(results, field_weights)
        expected_confidence = (0.7 * 0.3 + 0.8 * 0.7) / (0.3 + 0.7)
        assert abs(weighted_confidence - expected_confidence) < 0.001
    
    def test_get_tolerance_summary(self):
        """Test tolerance matching summary generation."""
        results = [
            ToleranceMatchResult(
                field_name='invoice_date',
                matches=True,
                expected_value=datetime(2024, 1, 15),
                actual_value=datetime(2024, 1, 18),
                tolerance_type='date_days',
                tolerance_value=5,
                actual_variance=3,
                confidence=0.7
            ),
            ToleranceMatchResult(
                field_name='total_amount',
                matches=False,
                expected_value=1000.00,
                actual_value=1100.00,
                tolerance_type='amount_percentage',
                tolerance_value=5.0,
                actual_variance=100.0,
                variance_percentage=10.0,
                confidence=0.2
            )
        ]
        
        summary = self.matcher.get_tolerance_summary(results)
        
        assert summary['total_fields'] == 2
        assert summary['matched_fields'] == 1
        assert summary['match_rate'] == 0.5
        assert summary['average_confidence'] == 0.45
        assert 'date_days' in summary['tolerance_types']
        assert 'amount_percentage' in summary['tolerance_types']
        assert len(summary['field_details']) == 2
    
    def test_get_tolerance_summary_empty(self):
        """Test tolerance summary with empty results."""
        summary = self.matcher.get_tolerance_summary([])
        
        assert summary['total_fields'] == 0
        assert summary['matched_fields'] == 0
        assert summary['match_rate'] == 0.0
        assert summary['average_confidence'] == 0.0
        assert summary['tolerance_types'] == []


class TestToleranceMatchResult:
    """Test cases for ToleranceMatchResult class."""
    
    def test_tolerance_match_result_creation(self):
        """Test creating ToleranceMatchResult."""
        result = ToleranceMatchResult(
            field_name='test_field',
            matches=True,
            expected_value='expected',
            actual_value='actual',
            tolerance_type='date_days',
            tolerance_value=7.0,
            actual_variance=3.0,
            variance_percentage=5.0,
            confidence=0.8
        )
        
        assert result.field_name == 'test_field'
        assert result.matches is True
        assert result.expected_value == 'expected'
        assert result.actual_value == 'actual'
        assert result.tolerance_type == 'date_days'
        assert result.tolerance_value == 7.0
        assert result.actual_variance == 3.0
        assert result.variance_percentage == 5.0
        assert result.confidence == 0.8
    
    def test_tolerance_match_result_to_dict(self):
        """Test converting ToleranceMatchResult to dictionary."""
        result = ToleranceMatchResult(
            field_name='total_amount',
            matches=False,
            expected_value=1000.00,
            actual_value=1100.00,
            tolerance_type='amount_percentage',
            tolerance_value=5.0,
            actual_variance=100.0,
            variance_percentage=10.0,
            confidence=0.2
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['field_name'] == 'total_amount'
        assert result_dict['matches'] is False
        assert result_dict['expected_value'] == '1000.0'
        assert result_dict['actual_value'] == '1100.0'
        assert result_dict['tolerance_type'] == 'amount_percentage'
        assert result_dict['tolerance_value'] == 5.0
        assert result_dict['actual_variance'] == 100.0
        assert result_dict['variance_percentage'] == 10.0
        assert result_dict['confidence'] == 0.2


def run_basic_tolerance_matcher_test():
    """Run basic tolerance matcher functionality test."""
    print("Testing tolerance matcher...")
    
    matcher = ToleranceMatcher()
    
    # Test date tolerance matching
    date1 = datetime(2024, 1, 15)
    date2 = datetime(2024, 1, 18)  # 3 days difference
    date_result = matcher.match_date_with_tolerance(date1, date2, tolerance_days=5)
    print(f"✓ Date tolerance match: {date_result.matches} (variance: {date_result.actual_variance} days, confidence: {date_result.confidence:.2f})")
    
    # Test amount percentage tolerance matching
    amount_result = matcher.match_amount_with_percentage_tolerance(
        Decimal('1000.00'), 
        Decimal('1030.00'), 
        tolerance_percentage=5.0
    )
    print(f"✓ Amount percentage match: {amount_result.matches} (variance: {amount_result.variance_percentage:.1f}%, confidence: {amount_result.confidence:.2f})")
    
    # Test amount absolute tolerance matching
    abs_result = matcher.match_amount_with_absolute_tolerance(
        "1000.00", 
        "1025.00", 
        tolerance_amount="30.00"
    )
    print(f"✓ Amount absolute match: {abs_result.matches} (variance: ${abs_result.actual_variance:.2f}, confidence: {abs_result.confidence:.2f})")
    
    # Test complete invoice tolerance matching
    invoice_data = InvoiceData(
        invoice_number="INV-001",
        vendor_name="Test Vendor",
        customer_name="Test Customer",
        invoice_date=datetime(2024, 1, 15),
        total_amount=Decimal('1000.00')
    )
    
    candidate_data = {
        'invoice_date': datetime(2024, 1, 17),  # 2 days difference
        'total_amount': Decimal('1020.00')  # 2% difference
    }
    
    results = matcher.match_invoice_data_with_tolerance(invoice_data, candidate_data)
    matches = sum(1 for r in results if r.matches)
    print(f"✓ Complete tolerance match: {matches}/{len(results)} fields matched")
    
    # Test weighted confidence
    weighted_confidence = matcher.calculate_weighted_confidence(results)
    print(f"✓ Weighted confidence: {weighted_confidence:.2f}")
    
    print("🎉 Tolerance matcher working!")


if __name__ == "__main__":
    run_basic_tolerance_matcher_test()