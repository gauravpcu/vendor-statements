"""
Unit tests for fuzzy matching algorithms.

Tests fuzzy matching functionality including Levenshtein distance,
Jaro-Winkler similarity, and business name normalization.
"""

from datetime import datetime
from decimal import Decimal

from invoice_matching.models import InvoiceData
from invoice_matching.matching.fuzzy_matcher import FuzzyMatcher, FuzzyMatchResult


class TestFuzzyMatcher:
    """Test cases for FuzzyMatcher class."""
    
    def setup_method(self):
        """Setup test environment."""
        self.matcher = FuzzyMatcher(default_threshold=0.8)
    
    def test_levenshtein_distance_identical(self):
        """Test Levenshtein distance for identical strings."""
        distance = self.matcher.levenshtein_distance("hello", "hello")
        assert distance == 0
    
    def test_levenshtein_distance_different(self):
        """Test Levenshtein distance for different strings."""
        distance = self.matcher.levenshtein_distance("hello", "world")
        assert distance == 4  # 4 substitutions needed
    
    def test_levenshtein_distance_insertion(self):
        """Test Levenshtein distance with insertion."""
        distance = self.matcher.levenshtein_distance("cat", "cats")
        assert distance == 1  # 1 insertion needed
    
    def test_levenshtein_distance_deletion(self):
        """Test Levenshtein distance with deletion."""
        distance = self.matcher.levenshtein_distance("cats", "cat")
        assert distance == 1  # 1 deletion needed
    
    def test_levenshtein_distance_empty(self):
        """Test Levenshtein distance with empty strings."""
        assert self.matcher.levenshtein_distance("", "") == 0
        assert self.matcher.levenshtein_distance("hello", "") == 5
        assert self.matcher.levenshtein_distance("", "world") == 5
    
    def test_levenshtein_similarity_identical(self):
        """Test Levenshtein similarity for identical strings."""
        similarity = self.matcher.levenshtein_similarity("hello", "hello")
        assert similarity == 1.0
    
    def test_levenshtein_similarity_different(self):
        """Test Levenshtein similarity for different strings."""
        similarity = self.matcher.levenshtein_similarity("hello", "hallo")
        assert similarity == 0.8  # 1 edit out of 5 characters = 0.8
    
    def test_levenshtein_similarity_completely_different(self):
        """Test Levenshtein similarity for completely different strings."""
        similarity = self.matcher.levenshtein_similarity("abc", "xyz")
        assert similarity == 0.0
    
    def test_jaro_similarity_identical(self):
        """Test Jaro similarity for identical strings."""
        similarity = self.matcher.jaro_similarity("hello", "hello")
        assert similarity == 1.0
    
    def test_jaro_similarity_similar(self):
        """Test Jaro similarity for similar strings."""
        similarity = self.matcher.jaro_similarity("martha", "marhta")
        # This is a classic Jaro test case
        assert 0.9 < similarity < 1.0
    
    def test_jaro_similarity_different(self):
        """Test Jaro similarity for different strings."""
        similarity = self.matcher.jaro_similarity("abc", "xyz")
        assert similarity == 0.0
    
    def test_jaro_similarity_empty(self):
        """Test Jaro similarity with empty strings."""
        assert self.matcher.jaro_similarity("", "") == 1.0
        assert self.matcher.jaro_similarity("hello", "") == 0.0
        assert self.matcher.jaro_similarity("", "world") == 0.0
    
    def test_jaro_winkler_similarity_identical(self):
        """Test Jaro-Winkler similarity for identical strings."""
        similarity = self.matcher.jaro_winkler_similarity("hello", "hello")
        assert similarity == 1.0
    
    def test_jaro_winkler_similarity_common_prefix(self):
        """Test Jaro-Winkler similarity with common prefix."""
        # Jaro-Winkler gives bonus for common prefix
        jaro_sim = self.matcher.jaro_similarity("martha", "marhta")
        jw_sim = self.matcher.jaro_winkler_similarity("martha", "marhta")
        
        # Jaro-Winkler should be higher due to common prefix "mar"
        assert jw_sim > jaro_sim
    
    def test_normalize_string_basic(self):
        """Test basic string normalization."""
        normalized = self.matcher.normalize_string("  Hello World!  ")
        assert normalized == "hello world"
    
    def test_normalize_string_punctuation(self):
        """Test string normalization with punctuation."""
        normalized = self.matcher.normalize_string("ABC Corp., Inc.")
        assert normalized == "abc"  # Corp and Inc removed as common words
    
    def test_normalize_string_common_words(self):
        """Test string normalization removing common business words."""
        normalized = self.matcher.normalize_string("ABC Corporation International Ltd")
        assert normalized == "abc"
    
    def test_normalize_string_no_common_words(self):
        """Test string normalization without removing common words."""
        normalized = self.matcher.normalize_string(
            "ABC Corporation", 
            remove_common_words=False
        )
        assert normalized == "abc corporation"
    
    def test_fuzzy_match_string_identical(self):
        """Test fuzzy string matching for identical strings."""
        result = self.matcher.fuzzy_match_string("ABC Corp", "ABC Corp")
        
        assert result.matches is True
        assert result.similarity_score == 1.0
        assert result.confidence == 1.0
        assert result.algorithm == 'jaro_winkler'
    
    def test_fuzzy_match_string_similar(self):
        """Test fuzzy string matching for similar strings."""
        result = self.matcher.fuzzy_match_string(
            "ABC Corporation", 
            "ABC Corp", 
            threshold=0.7
        )
        
        assert result.matches is True
        assert result.similarity_score > 0.7
        assert result.confidence > 0.7
    
    def test_fuzzy_match_string_different(self):
        """Test fuzzy string matching for different strings."""
        result = self.matcher.fuzzy_match_string(
            "ABC Corporation", 
            "XYZ Company", 
            threshold=0.8
        )
        
        assert result.matches is False
        assert result.similarity_score < 0.8
        assert result.confidence < 0.8
    
    def test_fuzzy_match_string_levenshtein(self):
        """Test fuzzy string matching with Levenshtein algorithm."""
        result = self.matcher.fuzzy_match_string(
            "hello", 
            "hallo", 
            algorithm='levenshtein',
            threshold=0.7
        )
        
        assert result.matches is True
        assert result.algorithm == 'levenshtein'
        assert result.similarity_score == 0.8
    
    def test_fuzzy_match_string_jaro(self):
        """Test fuzzy string matching with Jaro algorithm."""
        result = self.matcher.fuzzy_match_string(
            "martha", 
            "marhta", 
            algorithm='jaro',
            threshold=0.8
        )
        
        assert result.matches is True
        assert result.algorithm == 'jaro'
        assert result.similarity_score > 0.8
    
    def test_fuzzy_match_string_empty(self):
        """Test fuzzy string matching with empty strings."""
        result = self.matcher.fuzzy_match_string("", "ABC Corp")
        
        assert result.matches is False
        assert result.similarity_score == 0.0
        assert result.confidence == 0.0
    
    def test_match_vendor_name(self):
        """Test vendor name fuzzy matching."""
        result = self.matcher.match_vendor_name(
            "ABC Corporation Inc", 
            "ABC Corp"
        )
        
        assert result.field_name == 'vendor_name'
        assert result.matches is True  # Should match after normalization
        assert result.similarity_score > 0.8
    
    def test_match_customer_name(self):
        """Test customer name fuzzy matching."""
        result = self.matcher.match_customer_name(
            "XYZ Company Ltd", 
            "XYZ Co"
        )
        
        assert result.field_name == 'customer_name'
        assert result.matches is True  # Should match after normalization
        assert result.similarity_score > 0.8
    
    def test_match_field_vendor_name(self):
        """Test generic field matching for vendor name."""
        result = self.matcher.match_field(
            'vendor_name', 
            'ABC Corporation', 
            'ABC Corp'
        )
        
        assert result.field_name == 'vendor_name'
        assert result.matches is True
    
    def test_match_field_customer_name(self):
        """Test generic field matching for customer name."""
        result = self.matcher.match_field(
            'customer_name', 
            'XYZ Company', 
            'XYZ Co'
        )
        
        assert result.field_name == 'customer_name'
        assert result.matches is True
    
    def test_match_field_generic(self):
        """Test generic field matching for unknown field."""
        result = self.matcher.match_field(
            'custom_field', 
            'similar text', 
            'similar txt',
            threshold=0.7
        )
        
        assert result.field_name == 'custom_field'
        assert result.matches is True
        assert result.similarity_score > 0.7
    
    def test_match_invoice_data_fuzzy_fields(self):
        """Test fuzzy matching of invoice data."""
        invoice_data = InvoiceData(
            invoice_number="INV-001",
            vendor_name="ABC Corporation Inc",
            customer_name="XYZ Company Ltd",
            invoice_date=datetime(2024, 1, 15),
            total_amount=Decimal('1500.00'),
            facility_name="Main Office Building"
        )
        
        candidate_data = {
            'invoice_number': 'INV-001',
            'vendor_name': 'ABC Corp',  # Similar but not exact
            'customer_name': 'XYZ Co',  # Similar but not exact
            'invoice_date': datetime(2024, 1, 15),
            'total_amount': Decimal('1500.00'),
            'facility_name': 'Main Office'  # Similar but not exact
        }
        
        results = self.matcher.match_invoice_data(invoice_data, candidate_data)
        
        # Should have fuzzy results for vendor_name, customer_name, and facility_name
        assert len(results) >= 2  # At least vendor and customer
        
        # Check vendor name fuzzy match
        vendor_result = next((r for r in results if r.field_name == 'vendor_name'), None)
        assert vendor_result is not None
        assert vendor_result.matches is True
        assert vendor_result.similarity_score > 0.8
        
        # Check customer name fuzzy match
        customer_result = next((r for r in results if r.field_name == 'customer_name'), None)
        assert customer_result is not None
        assert customer_result.matches is True
        assert customer_result.similarity_score > 0.8
    
    def test_match_invoice_data_with_options(self):
        """Test fuzzy matching with custom options."""
        invoice_data = InvoiceData(
            invoice_number="INV-001",
            vendor_name="ABC Corporation",
            customer_name="XYZ Company",
            invoice_date=datetime(2024, 1, 15),
            total_amount=Decimal('1500.00')
        )
        
        candidate_data = {
            'vendor_name': 'ABC Corp',
            'customer_name': 'XYZ Co'
        }
        
        # Use custom thresholds
        matching_options = {
            'vendor_threshold': 0.9,  # High threshold
            'customer_threshold': 0.6  # Low threshold
        }
        
        results = self.matcher.match_invoice_data(
            invoice_data, 
            candidate_data, 
            matching_options
        )
        
        # Check that thresholds were applied
        for result in results:
            if result.field_name == 'vendor_name':
                assert result.threshold == 0.9
            elif result.field_name == 'customer_name':
                assert result.threshold == 0.6
    
    def test_get_best_matches(self):
        """Test filtering and sorting of fuzzy match results."""
        # Create mock results with different confidence scores
        results = [
            FuzzyMatchResult(
                field_name='field1',
                matches=True,
                expected_value='test1',
                actual_value='test1',
                similarity_score=0.9,
                algorithm='jaro_winkler',
                threshold=0.8,
                confidence=0.9
            ),
            FuzzyMatchResult(
                field_name='field2',
                matches=True,
                expected_value='test2',
                actual_value='test2',
                similarity_score=0.7,
                algorithm='jaro_winkler',
                threshold=0.8,
                confidence=0.7
            ),
            FuzzyMatchResult(
                field_name='field3',
                matches=False,
                expected_value='test3',
                actual_value='test3',
                similarity_score=0.4,
                algorithm='jaro_winkler',
                threshold=0.8,
                confidence=0.2
            )
        ]
        
        best_matches = self.matcher.get_best_matches(results, min_confidence=0.6)
        
        # Should filter out the low confidence result and sort by confidence
        assert len(best_matches) == 2
        assert best_matches[0].confidence == 0.9  # Highest first
        assert best_matches[1].confidence == 0.7


class TestFuzzyMatchResult:
    """Test cases for FuzzyMatchResult class."""
    
    def test_fuzzy_match_result_creation(self):
        """Test creating FuzzyMatchResult."""
        result = FuzzyMatchResult(
            field_name='test_field',
            matches=True,
            expected_value='expected',
            actual_value='actual',
            similarity_score=0.85,
            algorithm='jaro_winkler',
            threshold=0.8,
            confidence=0.85
        )
        
        assert result.field_name == 'test_field'
        assert result.matches is True
        assert result.expected_value == 'expected'
        assert result.actual_value == 'actual'
        assert result.similarity_score == 0.85
        assert result.algorithm == 'jaro_winkler'
        assert result.threshold == 0.8
        assert result.confidence == 0.85
    
    def test_fuzzy_match_result_to_dict(self):
        """Test converting FuzzyMatchResult to dictionary."""
        result = FuzzyMatchResult(
            field_name='vendor_name',
            matches=False,
            expected_value='ABC Corp',
            actual_value='XYZ Corp',
            similarity_score=0.3,
            algorithm='levenshtein',
            threshold=0.8,
            confidence=0.15
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['field_name'] == 'vendor_name'
        assert result_dict['matches'] is False
        assert result_dict['expected_value'] == 'ABC Corp'
        assert result_dict['actual_value'] == 'XYZ Corp'
        assert result_dict['similarity_score'] == 0.3
        assert result_dict['algorithm'] == 'levenshtein'
        assert result_dict['threshold'] == 0.8
        assert result_dict['confidence'] == 0.15


def run_basic_fuzzy_matcher_test():
    """Run basic fuzzy matcher functionality test."""
    print("Testing fuzzy matcher...")
    
    matcher = FuzzyMatcher(default_threshold=0.8)
    
    # Test Levenshtein distance
    distance = matcher.levenshtein_distance("hello", "hallo")
    print(f"✓ Levenshtein distance: {distance}")
    
    # Test Levenshtein similarity
    similarity = matcher.levenshtein_similarity("hello", "hallo")
    print(f"✓ Levenshtein similarity: {similarity:.3f}")
    
    # Test Jaro similarity
    jaro_sim = matcher.jaro_similarity("martha", "marhta")
    print(f"✓ Jaro similarity: {jaro_sim:.3f}")
    
    # Test Jaro-Winkler similarity
    jw_sim = matcher.jaro_winkler_similarity("martha", "marhta")
    print(f"✓ Jaro-Winkler similarity: {jw_sim:.3f}")
    
    # Test string normalization
    normalized = matcher.normalize_string("ABC Corporation Inc.")
    print(f"✓ String normalization: '{normalized}'")
    
    # Test fuzzy string matching
    result = matcher.fuzzy_match_string("ABC Corporation", "ABC Corp")
    print(f"✓ Fuzzy string match: {result.matches} (score: {result.similarity_score:.3f})")
    
    # Test vendor name matching
    vendor_result = matcher.match_vendor_name("ABC Corporation Inc", "ABC Corp")
    print(f"✓ Vendor name match: {vendor_result.matches} (score: {vendor_result.similarity_score:.3f})")
    
    print("🎉 Fuzzy matcher working!")


if __name__ == "__main__":
    run_basic_fuzzy_matcher_test()