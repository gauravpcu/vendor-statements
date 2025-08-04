"""
Fuzzy matching algorithms for invoice data.

Provides fuzzy string matching using various algorithms including
Levenshtein distance, Jaro-Winkler similarity, and configurable
similarity thresholds for vendor and customer name matching.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from invoice_matching.models import InvoiceData, MatchingError

import logging
logger = logging.getLogger(__name__)


@dataclass
class FuzzyMatchResult:
    """Result of a fuzzy match operation."""
    field_name: str
    matches: bool
    expected_value: Any
    actual_value: Any
    similarity_score: float  # 0.0 to 1.0
    algorithm: str  # 'levenshtein', 'jaro_winkler', etc.
    threshold: float  # Threshold used for matching
    confidence: float  # Final confidence score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'field_name': self.field_name,
            'matches': self.matches,
            'expected_value': str(self.expected_value),
            'actual_value': str(self.actual_value),
            'similarity_score': self.similarity_score,
            'algorithm': self.algorithm,
            'threshold': self.threshold,
            'confidence': self.confidence
        }


class FuzzyMatcher:
    """
    Performs fuzzy matching operations on invoice data fields.
    
    Implements various fuzzy matching algorithms with configurable
    thresholds for different types of data matching scenarios.
    """
    
    def __init__(self, default_threshold: float = 0.8):
        """
        Initialize fuzzy matcher.
        
        Args:
            default_threshold: Default similarity threshold (0.0 to 1.0)
        """
        self.logger = logging.getLogger(f"{__name__}.FuzzyMatcher")
        self.default_threshold = default_threshold
    
    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings.
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            Levenshtein distance (number of edits needed)
        """
        if not s1 and not s2:
            return 0
        if not s1:
            return len(s2)
        if not s2:
            return len(s1)
        
        # Create matrix
        rows = len(s1) + 1
        cols = len(s2) + 1
        matrix = [[0] * cols for _ in range(rows)]
        
        # Initialize first row and column
        for i in range(rows):
            matrix[i][0] = i
        for j in range(cols):
            matrix[0][j] = j
        
        # Fill matrix
        for i in range(1, rows):
            for j in range(1, cols):
                if s1[i-1] == s2[j-1]:
                    cost = 0
                else:
                    cost = 1
                
                matrix[i][j] = min(
                    matrix[i-1][j] + 1,      # deletion
                    matrix[i][j-1] + 1,      # insertion
                    matrix[i-1][j-1] + cost  # substitution
                )
        
        return matrix[rows-1][cols-1]
    
    def levenshtein_similarity(self, s1: str, s2: str) -> float:
        """
        Calculate Levenshtein similarity (0.0 to 1.0).
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            Similarity score (1.0 = identical, 0.0 = completely different)
        """
        if not s1 and not s2:
            return 1.0
        
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0
        
        distance = self.levenshtein_distance(s1, s2)
        similarity = 1.0 - (distance / max_len)
        return max(0.0, similarity)
    
    def jaro_similarity(self, s1: str, s2: str) -> float:
        """
        Calculate Jaro similarity between two strings.
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            Jaro similarity score (0.0 to 1.0)
        """
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 1.0
        
        len1, len2 = len(s1), len(s2)
        
        # Calculate matching window
        match_window = max(len1, len2) // 2 - 1
        match_window = max(0, match_window)
        
        # Initialize match arrays
        s1_matches = [False] * len1
        s2_matches = [False] * len2
        
        matches = 0
        transpositions = 0
        
        # Find matches
        for i in range(len1):
            start = max(0, i - match_window)
            end = min(i + match_window + 1, len2)
            
            for j in range(start, end):
                if s2_matches[j] or s1[i] != s2[j]:
                    continue
                s1_matches[i] = s2_matches[j] = True
                matches += 1
                break
        
        if matches == 0:
            return 0.0
        
        # Count transpositions
        k = 0
        for i in range(len1):
            if not s1_matches[i]:
                continue
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1
        
        # Calculate Jaro similarity
        jaro = (matches / len1 + matches / len2 + (matches - transpositions/2) / matches) / 3.0
        return jaro
    
    def jaro_winkler_similarity(self, s1: str, s2: str, prefix_scale: float = 0.1) -> float:
        """
        Calculate Jaro-Winkler similarity between two strings.
        
        Args:
            s1: First string
            s2: Second string
            prefix_scale: Scaling factor for common prefix (default 0.1)
            
        Returns:
            Jaro-Winkler similarity score (0.0 to 1.0)
        """
        jaro_sim = self.jaro_similarity(s1, s2)
        
        if jaro_sim < 0.7:  # Standard threshold for Jaro-Winkler
            return jaro_sim
        
        # Calculate common prefix length (up to 4 characters)
        prefix_len = 0
        for i in range(min(len(s1), len(s2), 4)):
            if s1[i] == s2[i]:
                prefix_len += 1
            else:
                break
        
        # Apply Winkler modification
        jaro_winkler = jaro_sim + (prefix_len * prefix_scale * (1 - jaro_sim))
        return min(1.0, jaro_winkler)
    
    def normalize_string(self, text: str, remove_punctuation: bool = True,
                        remove_common_words: bool = True) -> str:
        """
        Normalize string for better fuzzy matching.
        
        Args:
            text: Text to normalize
            remove_punctuation: Whether to remove punctuation
            remove_common_words: Whether to remove common business words
            
        Returns:
            Normalized string
        """
        if not text:
            return ""
        
        # Convert to lowercase and strip
        normalized = text.lower().strip()
        
        # Remove punctuation
        if remove_punctuation:
            normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        # Normalize whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove common business words
        if remove_common_words:
            common_words = {
                'inc', 'incorporated', 'corp', 'corporation', 'ltd', 'limited',
                'llc', 'company', 'co', 'enterprises', 'group', 'holdings',
                'international', 'intl', 'services', 'solutions', 'systems',
                'technologies', 'tech', 'the', 'and', 'of', 'for'
            }
            
            words = normalized.split()
            filtered_words = [word for word in words if word not in common_words]
            normalized = ' '.join(filtered_words)
        
        return normalized
    
    def fuzzy_match_string(self, expected: str, actual: str,
                          algorithm: str = 'jaro_winkler',
                          threshold: float = None,
                          normalize: bool = True) -> FuzzyMatchResult:
        """
        Perform fuzzy string matching using specified algorithm.
        
        Args:
            expected: Expected string value
            actual: Actual string value from database
            algorithm: Algorithm to use ('levenshtein', 'jaro', 'jaro_winkler')
            threshold: Similarity threshold (uses default if None)
            normalize: Whether to normalize strings before matching
            
        Returns:
            FuzzyMatchResult with match details
        """
        if threshold is None:
            threshold = self.default_threshold
        
        if not expected or not actual:
            return FuzzyMatchResult(
                field_name='string',
                matches=False,
                expected_value=expected,
                actual_value=actual,
                similarity_score=0.0,
                algorithm=algorithm,
                threshold=threshold,
                confidence=0.0
            )
        
        # Normalize strings if requested
        if normalize:
            expected_norm = self.normalize_string(expected)
            actual_norm = self.normalize_string(actual)
        else:
            expected_norm = expected.lower().strip()
            actual_norm = actual.lower().strip()
        
        # Calculate similarity based on algorithm
        if algorithm == 'levenshtein':
            similarity = self.levenshtein_similarity(expected_norm, actual_norm)
        elif algorithm == 'jaro':
            similarity = self.jaro_similarity(expected_norm, actual_norm)
        elif algorithm == 'jaro_winkler':
            similarity = self.jaro_winkler_similarity(expected_norm, actual_norm)
        else:
            raise MatchingError(f"Unknown fuzzy matching algorithm: {algorithm}")
        
        # Determine if it's a match
        matches = similarity >= threshold
        
        # Calculate confidence (similarity score adjusted for threshold)
        if matches:
            confidence = similarity
        else:
            # Partial confidence for near-misses
            confidence = similarity * 0.5
        
        result = FuzzyMatchResult(
            field_name='string',
            matches=matches,
            expected_value=expected,
            actual_value=actual,
            similarity_score=similarity,
            algorithm=algorithm,
            threshold=threshold,
            confidence=confidence
        )
        
        self.logger.debug(f"Fuzzy match ({algorithm}): '{expected}' vs '{actual}' = {similarity:.3f} (threshold: {threshold})")
        return result
    
    def match_vendor_name(self, expected: str, actual: str,
                         algorithm: str = 'jaro_winkler',
                         threshold: float = None) -> FuzzyMatchResult:
        """
        Fuzzy match vendor names with business-specific normalization.
        
        Args:
            expected: Expected vendor name
            actual: Actual vendor name from database
            algorithm: Algorithm to use
            threshold: Similarity threshold
            
        Returns:
            FuzzyMatchResult with match details
        """
        result = self.fuzzy_match_string(
            expected, actual, algorithm, threshold, normalize=True
        )
        result.field_name = 'vendor_name'
        
        self.logger.debug(f"Vendor name fuzzy match: '{expected}' vs '{actual}' = {result.similarity_score:.3f}")
        return result
    
    def match_customer_name(self, expected: str, actual: str,
                           algorithm: str = 'jaro_winkler',
                           threshold: float = None) -> FuzzyMatchResult:
        """
        Fuzzy match customer names with business-specific normalization.
        
        Args:
            expected: Expected customer name
            actual: Actual customer name from database
            algorithm: Algorithm to use
            threshold: Similarity threshold
            
        Returns:
            FuzzyMatchResult with match details
        """
        result = self.fuzzy_match_string(
            expected, actual, algorithm, threshold, normalize=True
        )
        result.field_name = 'customer_name'
        
        self.logger.debug(f"Customer name fuzzy match: '{expected}' vs '{actual}' = {result.similarity_score:.3f}")
        return result
    
    def match_field(self, field_name: str, expected: Any, actual: Any,
                   algorithm: str = 'jaro_winkler',
                   threshold: float = None,
                   **kwargs) -> FuzzyMatchResult:
        """
        Generic fuzzy field matching.
        
        Args:
            field_name: Name of the field to match
            expected: Expected value
            actual: Actual value from database
            algorithm: Algorithm to use
            threshold: Similarity threshold
            **kwargs: Additional matching options
            
        Returns:
            FuzzyMatchResult with match details
        """
        # Route to specific matching methods based on field name
        if field_name.lower() in ['vendor_name', 'vendorname', 'supplier_name']:
            return self.match_vendor_name(expected, actual, algorithm, threshold)
        
        elif field_name.lower() in ['customer_name', 'customername', 'facility_name']:
            return self.match_customer_name(expected, actual, algorithm, threshold)
        
        else:
            # Generic string fuzzy matching
            result = self.fuzzy_match_string(
                str(expected) if expected is not None else "",
                str(actual) if actual is not None else "",
                algorithm, threshold, normalize=kwargs.get('normalize', True)
            )
            result.field_name = field_name
            return result
    
    def match_invoice_data(self, invoice_data: InvoiceData,
                          candidate_data: Dict[str, Any],
                          matching_options: Optional[Dict[str, Any]] = None) -> List[FuzzyMatchResult]:
        """
        Fuzzy match invoice data against candidate record.
        
        Args:
            invoice_data: Invoice data to match
            candidate_data: Candidate record from database
            matching_options: Options for fuzzy matching behavior
            
        Returns:
            List of FuzzyMatchResult for fuzzy-matchable fields
        """
        if matching_options is None:
            matching_options = {}
        
        results = []
        
        # Define fuzzy-matchable fields and their options
        fuzzy_fields = [
            ('vendor_name', 'vendor_name', {
                'algorithm': 'jaro_winkler',
                'threshold': matching_options.get('vendor_threshold', self.default_threshold)
            }),
            ('customer_name', 'customer_name', {
                'algorithm': 'jaro_winkler', 
                'threshold': matching_options.get('customer_threshold', self.default_threshold)
            }),
        ]
        
        # Optional fuzzy fields
        optional_fuzzy_fields = [
            ('facility_name', 'facility_name', {
                'algorithm': 'jaro_winkler',
                'threshold': matching_options.get('facility_threshold', self.default_threshold)
            }),
        ]
        
        # Match required fuzzy fields
        for invoice_field, candidate_field, options in fuzzy_fields:
            invoice_value = getattr(invoice_data, invoice_field, None)
            candidate_value = candidate_data.get(candidate_field)
            
            if invoice_value and candidate_value:
                # Merge with global matching options
                merged_options = {**options, **matching_options.get(invoice_field, {})}
                
                result = self.match_field(
                    invoice_field, 
                    invoice_value, 
                    candidate_value,
                    **merged_options
                )
                results.append(result)
        
        # Match optional fuzzy fields if present
        for invoice_field, candidate_field, options in optional_fuzzy_fields:
            invoice_value = getattr(invoice_data, invoice_field, None)
            candidate_value = candidate_data.get(candidate_field)
            
            if invoice_value and candidate_value:
                merged_options = {**options, **matching_options.get(invoice_field, {})}
                result = self.match_field(
                    invoice_field,
                    invoice_value,
                    candidate_value,
                    **merged_options
                )
                results.append(result)
        
        successful_matches = sum(1 for r in results if r.matches)
        self.logger.info(f"Fuzzy matched invoice {invoice_data.invoice_number}: {successful_matches}/{len(results)} fields matched")
        return results
    
    def get_best_matches(self, results: List[FuzzyMatchResult], 
                        min_confidence: float = 0.5) -> List[FuzzyMatchResult]:
        """
        Filter and sort fuzzy match results by confidence.
        
        Args:
            results: List of fuzzy match results
            min_confidence: Minimum confidence threshold
            
        Returns:
            Filtered and sorted list of best matches
        """
        # Filter by minimum confidence
        filtered_results = [r for r in results if r.confidence >= min_confidence]
        
        # Sort by confidence (highest first)
        sorted_results = sorted(filtered_results, key=lambda r: r.confidence, reverse=True)
        
        return sorted_results