"""
Exact matching algorithms for invoice data.

Provides precise matching for invoice numbers, dates, amounts, and other
fields with support for case-insensitive matching and timezone handling.
"""

import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from invoice_matching.models import InvoiceData, MatchingError

import logging
logger = logging.getLogger(__name__)


@dataclass
class ExactMatchResult:
    """Result of an exact match operation."""
    field_name: str
    matches: bool
    expected_value: Any
    actual_value: Any
    match_type: str  # 'exact', 'case_insensitive', 'normalized', etc.
    confidence: float = 1.0  # Exact matches have 100% confidence
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'field_name': self.field_name,
            'matches': self.matches,
            'expected_value': str(self.expected_value),
            'actual_value': str(self.actual_value),
            'match_type': self.match_type,
            'confidence': self.confidence
        }


class ExactMatcher:
    """
    Performs exact matching operations on invoice data fields.
    
    Supports various types of exact matching including case-insensitive
    string matching, date matching with tolerance, and amount matching
    with precision handling.
    """
    
    def __init__(self):
        """Initialize exact matcher."""
        self.logger = logging.getLogger(f"{__name__}.ExactMatcher")
    
    def match_invoice_number(self, expected: str, actual: str, 
                           case_sensitive: bool = False) -> ExactMatchResult:
        """
        Match invoice numbers with optional case sensitivity.
        
        Args:
            expected: Expected invoice number
            actual: Actual invoice number from database
            case_sensitive: Whether to perform case-sensitive matching
            
        Returns:
            ExactMatchResult with match details
        """
        if not expected or not actual:
            return ExactMatchResult(
                field_name='invoice_number',
                matches=False,
                expected_value=expected,
                actual_value=actual,
                match_type='exact',
                confidence=0.0
            )
        
        # Normalize values for comparison
        expected_normalized = str(expected).strip()
        actual_normalized = str(actual).strip()
        
        if case_sensitive:
            matches = expected_normalized == actual_normalized
            match_type = 'exact'
        else:
            matches = expected_normalized.lower() == actual_normalized.lower()
            match_type = 'case_insensitive'
        
        result = ExactMatchResult(
            field_name='invoice_number',
            matches=matches,
            expected_value=expected,
            actual_value=actual,
            match_type=match_type,
            confidence=1.0 if matches else 0.0
        )
        
        self.logger.debug(f"Invoice number match: {expected} vs {actual} = {matches}")
        return result
    
    def match_vendor_name(self, expected: str, actual: str,
                         case_sensitive: bool = False,
                         normalize_whitespace: bool = True) -> ExactMatchResult:
        """
        Match vendor names with normalization options.
        
        Args:
            expected: Expected vendor name
            actual: Actual vendor name from database
            case_sensitive: Whether to perform case-sensitive matching
            normalize_whitespace: Whether to normalize whitespace
            
        Returns:
            ExactMatchResult with match details
        """
        if not expected or not actual:
            return ExactMatchResult(
                field_name='vendor_name',
                matches=False,
                expected_value=expected,
                actual_value=actual,
                match_type='exact',
                confidence=0.0
            )
        
        # Normalize values
        expected_normalized = str(expected).strip()
        actual_normalized = str(actual).strip()
        
        if normalize_whitespace:
            # Normalize multiple spaces to single space
            expected_normalized = re.sub(r'\s+', ' ', expected_normalized)
            actual_normalized = re.sub(r'\s+', ' ', actual_normalized)
        
        if case_sensitive:
            matches = expected_normalized == actual_normalized
            match_type = 'exact'
        else:
            matches = expected_normalized.lower() == actual_normalized.lower()
            match_type = 'case_insensitive'
        
        if normalize_whitespace and match_type == 'case_insensitive':
            match_type = 'normalized_case_insensitive'
        elif normalize_whitespace:
            match_type = 'normalized'
        
        result = ExactMatchResult(
            field_name='vendor_name',
            matches=matches,
            expected_value=expected,
            actual_value=actual,
            match_type=match_type,
            confidence=1.0 if matches else 0.0
        )
        
        self.logger.debug(f"Vendor name match: '{expected}' vs '{actual}' = {matches}")
        return result
    
    def match_customer_name(self, expected: str, actual: str,
                          case_sensitive: bool = False,
                          normalize_whitespace: bool = True) -> ExactMatchResult:
        """
        Match customer names with normalization options.
        
        Args:
            expected: Expected customer name
            actual: Actual customer name from database
            case_sensitive: Whether to perform case-sensitive matching
            normalize_whitespace: Whether to normalize whitespace
            
        Returns:
            ExactMatchResult with match details
        """
        # Customer name matching uses same logic as vendor name matching
        result = self.match_vendor_name(expected, actual, case_sensitive, normalize_whitespace)
        result.field_name = 'customer_name'
        
        self.logger.debug(f"Customer name match: '{expected}' vs '{actual}' = {result.matches}")
        return result
    
    def match_date(self, expected: datetime, actual: datetime,
                  tolerance_days: int = 0) -> ExactMatchResult:
        """
        Match dates with optional tolerance.
        
        Args:
            expected: Expected date
            actual: Actual date from database
            tolerance_days: Number of days tolerance (0 for exact match)
            
        Returns:
            ExactMatchResult with match details
        """
        if not expected or not actual:
            return ExactMatchResult(
                field_name='invoice_date',
                matches=False,
                expected_value=expected,
                actual_value=actual,
                match_type='exact',
                confidence=0.0
            )
        
        # Convert to date objects if they're datetime objects
        if isinstance(expected, datetime):
            expected_date = expected.date()
        else:
            expected_date = expected
            
        if isinstance(actual, datetime):
            actual_date = actual.date()
        else:
            actual_date = actual
        
        if tolerance_days == 0:
            # Exact date match
            matches = expected_date == actual_date
            match_type = 'exact'
            confidence = 1.0 if matches else 0.0
        else:
            # Date match with tolerance
            date_diff = abs((expected_date - actual_date).days)
            matches = date_diff <= tolerance_days
            match_type = f'tolerance_{tolerance_days}_days'
            
            # Calculate confidence based on how close the dates are
            if matches:
                if date_diff == 0:
                    confidence = 1.0
                else:
                    # Linear decrease in confidence based on days difference
                    confidence = max(0.5, 1.0 - (date_diff / tolerance_days) * 0.5)
            else:
                confidence = 0.0
        
        result = ExactMatchResult(
            field_name='invoice_date',
            matches=matches,
            expected_value=expected,
            actual_value=actual,
            match_type=match_type,
            confidence=confidence
        )
        
        self.logger.debug(f"Date match: {expected_date} vs {actual_date} (tolerance: {tolerance_days}) = {matches}")
        return result
    
    def match_amount(self, expected: Union[Decimal, float, str], 
                    actual: Union[Decimal, float, str],
                    precision: int = 2) -> ExactMatchResult:
        """
        Match monetary amounts with precision handling.
        
        Args:
            expected: Expected amount
            actual: Actual amount from database
            precision: Number of decimal places for comparison
            
        Returns:
            ExactMatchResult with match details
        """
        try:
            # Convert to Decimal for precise comparison
            if isinstance(expected, str):
                # Clean string: remove currency symbols and commas
                cleaned_expected = expected.replace('$', '').replace(',', '').strip()
                expected_decimal = Decimal(cleaned_expected)
            elif isinstance(expected, float):
                expected_decimal = Decimal(str(expected))
            else:
                expected_decimal = Decimal(expected)
            
            if isinstance(actual, str):
                # Clean string: remove currency symbols and commas
                cleaned_actual = actual.replace('$', '').replace(',', '').strip()
                actual_decimal = Decimal(cleaned_actual)
            elif isinstance(actual, float):
                actual_decimal = Decimal(str(actual))
            else:
                actual_decimal = Decimal(actual)
            
            # Round to specified precision for comparison
            expected_rounded = expected_decimal.quantize(Decimal('0.' + '0' * precision))
            actual_rounded = actual_decimal.quantize(Decimal('0.' + '0' * precision))
            
            matches = expected_rounded == actual_rounded
            
            result = ExactMatchResult(
                field_name='total_amount',
                matches=matches,
                expected_value=expected,
                actual_value=actual,
                match_type=f'exact_precision_{precision}',
                confidence=1.0 if matches else 0.0
            )
            
            self.logger.debug(f"Amount match: {expected_rounded} vs {actual_rounded} = {matches}")
            return result
            
        except (ValueError, TypeError, ArithmeticError) as e:
            self.logger.error(f"Error comparing amounts {expected} vs {actual}: {e}")
            return ExactMatchResult(
                field_name='total_amount',
                matches=False,
                expected_value=expected,
                actual_value=actual,
                match_type='error',
                confidence=0.0
            )
    
    def match_field(self, field_name: str, expected: Any, actual: Any,
                   **kwargs) -> ExactMatchResult:
        """
        Generic field matching with field-specific logic.
        
        Args:
            field_name: Name of the field to match
            expected: Expected value
            actual: Actual value from database
            **kwargs: Field-specific matching options
            
        Returns:
            ExactMatchResult with match details
        """
        # Route to specific matching methods based on field name
        if field_name.lower() in ['invoice_number', 'invoice_id', 'invoiceid']:
            return self.match_invoice_number(
                expected, actual, 
                case_sensitive=kwargs.get('case_sensitive', False)
            )
        
        elif field_name.lower() in ['vendor_name', 'vendorname', 'supplier_name']:
            return self.match_vendor_name(
                expected, actual,
                case_sensitive=kwargs.get('case_sensitive', False),
                normalize_whitespace=kwargs.get('normalize_whitespace', True)
            )
        
        elif field_name.lower() in ['customer_name', 'customername', 'facility_name']:
            return self.match_customer_name(
                expected, actual,
                case_sensitive=kwargs.get('case_sensitive', False),
                normalize_whitespace=kwargs.get('normalize_whitespace', True)
            )
        
        elif field_name.lower() in ['invoice_date', 'invoicedate', 'date']:
            return self.match_date(
                expected, actual,
                tolerance_days=kwargs.get('tolerance_days', 0)
            )
        
        elif field_name.lower() in ['total_amount', 'totalamount', 'amount']:
            return self.match_amount(
                expected, actual,
                precision=kwargs.get('precision', 2)
            )
        
        else:
            # Generic string matching for other fields
            return self._match_generic_string(field_name, expected, actual, **kwargs)
    
    def _match_generic_string(self, field_name: str, expected: Any, actual: Any,
                            case_sensitive: bool = False) -> ExactMatchResult:
        """
        Generic string matching for unspecified fields.
        
        Args:
            field_name: Name of the field
            expected: Expected value
            actual: Actual value
            case_sensitive: Whether to perform case-sensitive matching
            
        Returns:
            ExactMatchResult with match details
        """
        if expected is None and actual is None:
            matches = True
        elif expected is None or actual is None:
            matches = False
        else:
            expected_str = str(expected).strip()
            actual_str = str(actual).strip()
            
            if case_sensitive:
                matches = expected_str == actual_str
                match_type = 'exact'
            else:
                matches = expected_str.lower() == actual_str.lower()
                match_type = 'case_insensitive'
        
        return ExactMatchResult(
            field_name=field_name,
            matches=matches,
            expected_value=expected,
            actual_value=actual,
            match_type=match_type if 'match_type' in locals() else 'exact',
            confidence=1.0 if matches else 0.0
        )
    
    def match_invoice_data(self, invoice_data: InvoiceData, 
                          candidate_data: Dict[str, Any],
                          matching_options: Optional[Dict[str, Any]] = None) -> List[ExactMatchResult]:
        """
        Match complete invoice data against candidate record.
        
        Args:
            invoice_data: Invoice data to match
            candidate_data: Candidate record from database
            matching_options: Options for matching behavior
            
        Returns:
            List of ExactMatchResult for each field
        """
        if matching_options is None:
            matching_options = {}
        
        results = []
        
        # Define field mappings and their matching options
        field_mappings = [
            ('invoice_number', 'invoice_number', {'case_sensitive': False}),
            ('vendor_name', 'vendor_name', {'case_sensitive': False, 'normalize_whitespace': True}),
            ('customer_name', 'customer_name', {'case_sensitive': False, 'normalize_whitespace': True}),
            ('invoice_date', 'invoice_date', {'tolerance_days': matching_options.get('date_tolerance_days', 0)}),
            ('total_amount', 'total_amount', {'precision': 2}),
        ]
        
        # Optional fields
        optional_mappings = [
            ('facility_name', 'facility_name', {'case_sensitive': False}),
            ('po_number', 'po_number', {'case_sensitive': False}),
            ('currency', 'currency', {'case_sensitive': False}),
        ]
        
        # Match required fields
        for invoice_field, candidate_field, options in field_mappings:
            invoice_value = getattr(invoice_data, invoice_field, None)
            candidate_value = candidate_data.get(candidate_field)
            
            # Merge with global matching options
            merged_options = {**options, **matching_options.get(invoice_field, {})}
            
            result = self.match_field(invoice_field, invoice_value, candidate_value, **merged_options)
            results.append(result)
        
        # Match optional fields if present
        for invoice_field, candidate_field, options in optional_mappings:
            invoice_value = getattr(invoice_data, invoice_field, None)
            candidate_value = candidate_data.get(candidate_field)
            
            # Only match if both values are present
            if invoice_value is not None and candidate_value is not None:
                merged_options = {**options, **matching_options.get(invoice_field, {})}
                result = self.match_field(invoice_field, invoice_value, candidate_value, **merged_options)
                results.append(result)
        
        self.logger.info(f"Matched invoice {invoice_data.invoice_number}: {sum(1 for r in results if r.matches)}/{len(results)} fields matched")
        return results