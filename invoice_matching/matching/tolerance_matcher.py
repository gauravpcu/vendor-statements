"""
Tolerance-based matching algorithms for dates and amounts.

Provides matching with configurable tolerance ranges for dates and amounts,
including percentage-based variance checking and weighted scoring systems.
"""

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from invoice_matching.models import InvoiceData, MatchingError

import logging
logger = logging.getLogger(__name__)


@dataclass
class ToleranceMatchResult:
    """Result of a tolerance-based match operation."""
    field_name: str
    matches: bool
    expected_value: Any
    actual_value: Any
    tolerance_type: str  # 'date_days', 'amount_percentage', 'amount_absolute'
    tolerance_value: float  # The tolerance threshold used
    actual_variance: float  # The actual variance found
    variance_percentage: Optional[float] = None  # For amount matching
    confidence: float = 1.0  # Confidence score based on how close to tolerance
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'field_name': self.field_name,
            'matches': self.matches,
            'expected_value': str(self.expected_value),
            'actual_value': str(self.actual_value),
            'tolerance_type': self.tolerance_type,
            'tolerance_value': self.tolerance_value,
            'actual_variance': self.actual_variance,
            'variance_percentage': self.variance_percentage,
            'confidence': self.confidence
        }


class ToleranceMatcher:
    """
    Performs tolerance-based matching for dates and amounts.
    
    Supports configurable tolerance ranges with confidence scoring
    based on how close values are to the tolerance limits.
    """
    
    def __init__(self):
        """Initialize tolerance matcher."""
        self.logger = logging.getLogger(f"{__name__}.ToleranceMatcher")
    
    def match_date_with_tolerance(self, expected: datetime, actual: datetime,
                                 tolerance_days: int = 7) -> ToleranceMatchResult:
        """
        Match dates with day-based tolerance.
        
        Args:
            expected: Expected date
            actual: Actual date from database
            tolerance_days: Number of days tolerance (±)
            
        Returns:
            ToleranceMatchResult with match details
        """
        if not expected or not actual:
            return ToleranceMatchResult(
                field_name='invoice_date',
                matches=False,
                expected_value=expected,
                actual_value=actual,
                tolerance_type='date_days',
                tolerance_value=tolerance_days,
                actual_variance=float('inf'),
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
        
        # Calculate difference in days
        date_diff = abs((expected_date - actual_date).days)
        
        # Check if within tolerance
        matches = date_diff <= tolerance_days
        
        # Calculate confidence based on how close to tolerance limit
        if matches:
            if date_diff == 0:
                confidence = 1.0  # Perfect match
            elif tolerance_days == 0:
                confidence = 0.0  # Exact match required but not met
            else:
                # Linear decrease from 1.0 to 0.5 as we approach tolerance limit
                confidence = max(0.5, 1.0 - (date_diff / tolerance_days) * 0.5)
        else:
            # Partial confidence for near-misses
            if tolerance_days > 0:
                confidence = max(0.0, 0.5 - ((date_diff - tolerance_days) / tolerance_days) * 0.5)
            else:
                confidence = 0.0
        
        result = ToleranceMatchResult(
            field_name='invoice_date',
            matches=matches,
            expected_value=expected,
            actual_value=actual,
            tolerance_type='date_days',
            tolerance_value=tolerance_days,
            actual_variance=date_diff,
            confidence=confidence
        )
        
        self.logger.debug(f"Date tolerance match: {expected_date} vs {actual_date} "
                         f"(±{tolerance_days} days) = {matches} (variance: {date_diff} days)")
        return result
    
    def match_amount_with_percentage_tolerance(self, expected: Union[Decimal, float, str],
                                             actual: Union[Decimal, float, str],
                                             tolerance_percentage: float = 5.0) -> ToleranceMatchResult:
        """
        Match amounts with percentage-based tolerance.
        
        Args:
            expected: Expected amount
            actual: Actual amount from database
            tolerance_percentage: Percentage tolerance (e.g., 5.0 for ±5%)
            
        Returns:
            ToleranceMatchResult with match details
        """
        try:
            # Convert to Decimal for precise comparison
            if isinstance(expected, str):
                expected_decimal = Decimal(expected.replace('$', '').replace(',', '').strip())
            elif isinstance(expected, float):
                expected_decimal = Decimal(str(expected))
            else:
                expected_decimal = Decimal(expected)
            
            if isinstance(actual, str):
                actual_decimal = Decimal(actual.replace('$', '').replace(',', '').strip())
            elif isinstance(actual, float):
                actual_decimal = Decimal(str(actual))
            else:
                actual_decimal = Decimal(actual)
            
            # Handle zero expected amount
            if expected_decimal == 0:
                matches = actual_decimal == 0
                variance_percentage = 0.0 if matches else float('inf')
                actual_variance = float(abs(actual_decimal))
            else:
                # Calculate percentage difference
                difference = abs(expected_decimal - actual_decimal)
                variance_percentage = float((difference / abs(expected_decimal)) * 100)
                actual_variance = float(difference)
                
                # Check if within tolerance
                matches = variance_percentage <= tolerance_percentage
            
            # Calculate confidence based on how close to tolerance limit
            if matches:
                if variance_percentage == 0.0:
                    confidence = 1.0  # Perfect match
                elif tolerance_percentage == 0.0:
                    confidence = 0.0  # Exact match required but not met
                else:
                    # Linear decrease from 1.0 to 0.5 as we approach tolerance limit
                    confidence = max(0.5, 1.0 - (variance_percentage / tolerance_percentage) * 0.5)
            else:
                # Partial confidence for near-misses
                if tolerance_percentage > 0 and variance_percentage != float('inf'):
                    excess_percentage = variance_percentage - tolerance_percentage
                    confidence = max(0.0, 0.5 - (excess_percentage / tolerance_percentage) * 0.5)
                else:
                    confidence = 0.0
            
            result = ToleranceMatchResult(
                field_name='total_amount',
                matches=matches,
                expected_value=expected,
                actual_value=actual,
                tolerance_type='amount_percentage',
                tolerance_value=tolerance_percentage,
                actual_variance=actual_variance,
                variance_percentage=variance_percentage,
                confidence=confidence
            )
            
            self.logger.debug(f"Amount percentage tolerance match: {expected_decimal} vs {actual_decimal} "
                             f"(±{tolerance_percentage}%) = {matches} (variance: {variance_percentage:.2f}%)")
            return result
            
        except (ValueError, TypeError, ArithmeticError) as e:
            self.logger.error(f"Error comparing amounts {expected} vs {actual}: {e}")
            return ToleranceMatchResult(
                field_name='total_amount',
                matches=False,
                expected_value=expected,
                actual_value=actual,
                tolerance_type='amount_percentage',
                tolerance_value=tolerance_percentage,
                actual_variance=float('inf'),
                variance_percentage=float('inf'),
                confidence=0.0
            )
    
    def match_amount_with_absolute_tolerance(self, expected: Union[Decimal, float, str],
                                           actual: Union[Decimal, float, str],
                                           tolerance_amount: Union[Decimal, float, str] = "10.00") -> ToleranceMatchResult:
        """
        Match amounts with absolute tolerance.
        
        Args:
            expected: Expected amount
            actual: Actual amount from database
            tolerance_amount: Absolute tolerance amount (e.g., ±$10.00)
            
        Returns:
            ToleranceMatchResult with match details
        """
        try:
            # Convert to Decimal for precise comparison
            if isinstance(expected, str):
                expected_decimal = Decimal(expected.replace('$', '').replace(',', '').strip())
            elif isinstance(expected, float):
                expected_decimal = Decimal(str(expected))
            else:
                expected_decimal = Decimal(expected)
            
            if isinstance(actual, str):
                actual_decimal = Decimal(actual.replace('$', '').replace(',', '').strip())
            elif isinstance(actual, float):
                actual_decimal = Decimal(str(actual))
            else:
                actual_decimal = Decimal(actual)
            
            if isinstance(tolerance_amount, str):
                tolerance_decimal = Decimal(tolerance_amount.replace('$', '').replace(',', '').strip())
            elif isinstance(tolerance_amount, float):
                tolerance_decimal = Decimal(str(tolerance_amount))
            else:
                tolerance_decimal = Decimal(tolerance_amount)
            
            # Calculate absolute difference
            difference = abs(expected_decimal - actual_decimal)
            actual_variance = float(difference)
            
            # Check if within tolerance
            matches = difference <= tolerance_decimal
            
            # Calculate variance percentage for reporting
            if expected_decimal != 0:
                variance_percentage = float((difference / abs(expected_decimal)) * 100)
            else:
                variance_percentage = 0.0 if difference == 0 else float('inf')
            
            # Calculate confidence based on how close to tolerance limit
            if matches:
                if difference == 0:
                    confidence = 1.0  # Perfect match
                elif tolerance_decimal == 0:
                    confidence = 0.0  # Exact match required but not met
                else:
                    # Linear decrease from 1.0 to 0.5 as we approach tolerance limit
                    confidence = max(0.5, 1.0 - float(difference / tolerance_decimal) * 0.5)
            else:
                # Partial confidence for near-misses
                if tolerance_decimal > 0:
                    excess_amount = difference - tolerance_decimal
                    confidence = max(0.0, 0.5 - float(excess_amount / tolerance_decimal) * 0.5)
                else:
                    confidence = 0.0
            
            result = ToleranceMatchResult(
                field_name='total_amount',
                matches=matches,
                expected_value=expected,
                actual_value=actual,
                tolerance_type='amount_absolute',
                tolerance_value=float(tolerance_decimal),
                actual_variance=actual_variance,
                variance_percentage=variance_percentage,
                confidence=confidence
            )
            
            self.logger.debug(f"Amount absolute tolerance match: {expected_decimal} vs {actual_decimal} "
                             f"(±{tolerance_decimal}) = {matches} (variance: {difference})")
            return result
            
        except (ValueError, TypeError, ArithmeticError) as e:
            self.logger.error(f"Error comparing amounts {expected} vs {actual}: {e}")
            return ToleranceMatchResult(
                field_name='total_amount',
                matches=False,
                expected_value=expected,
                actual_value=actual,
                tolerance_type='amount_absolute',
                tolerance_value=float(tolerance_amount) if isinstance(tolerance_amount, (int, float)) else 0.0,
                actual_variance=float('inf'),
                variance_percentage=float('inf'),
                confidence=0.0
            )
    
    def match_field_with_tolerance(self, field_name: str, expected: Any, actual: Any,
                                  **tolerance_options) -> ToleranceMatchResult:
        """
        Generic field matching with tolerance based on field type.
        
        Args:
            field_name: Name of the field to match
            expected: Expected value
            actual: Actual value from database
            **tolerance_options: Tolerance options specific to field type
            
        Returns:
            ToleranceMatchResult with match details
        """
        # Route to specific tolerance matching methods based on field name
        if field_name.lower() in ['invoice_date', 'invoicedate', 'date']:
            tolerance_days = tolerance_options.get('tolerance_days', 7)
            result = self.match_date_with_tolerance(expected, actual, tolerance_days)
            result.field_name = field_name
            return result
        
        elif field_name.lower() in ['total_amount', 'totalamount', 'amount']:
            # Determine which type of amount tolerance to use
            if 'tolerance_percentage' in tolerance_options:
                tolerance_percentage = tolerance_options['tolerance_percentage']
                result = self.match_amount_with_percentage_tolerance(
                    expected, actual, tolerance_percentage
                )
            elif 'tolerance_amount' in tolerance_options:
                tolerance_amount = tolerance_options['tolerance_amount']
                result = self.match_amount_with_absolute_tolerance(
                    expected, actual, tolerance_amount
                )
            else:
                # Default to percentage tolerance
                tolerance_percentage = tolerance_options.get('default_percentage_tolerance', 5.0)
                result = self.match_amount_with_percentage_tolerance(
                    expected, actual, tolerance_percentage
                )
            
            result.field_name = field_name
            return result
        
        else:
            # For non-tolerance fields, return a basic comparison
            matches = str(expected).strip().lower() == str(actual).strip().lower() if expected and actual else False
            return ToleranceMatchResult(
                field_name=field_name,
                matches=matches,
                expected_value=expected,
                actual_value=actual,
                tolerance_type='exact',
                tolerance_value=0.0,
                actual_variance=0.0 if matches else 1.0,
                confidence=1.0 if matches else 0.0
            )
    
    def match_invoice_data_with_tolerance(self, invoice_data: InvoiceData,
                                        candidate_data: Dict[str, Any],
                                        tolerance_options: Optional[Dict[str, Any]] = None) -> List[ToleranceMatchResult]:
        """
        Match invoice data with tolerance settings.
        
        Args:
            invoice_data: Invoice data to match
            candidate_data: Candidate record from database
            tolerance_options: Tolerance settings for different fields
            
        Returns:
            List of ToleranceMatchResult for tolerance-applicable fields
        """
        if tolerance_options is None:
            tolerance_options = {}
        
        results = []
        
        # Define tolerance-applicable fields and their default options
        tolerance_fields = [
            ('invoice_date', 'invoice_date', {
                'tolerance_days': tolerance_options.get('date_tolerance_days', 7)
            }),
            ('total_amount', 'total_amount', {
                'tolerance_percentage': tolerance_options.get('amount_variance_percentage', 5.0)
            }),
        ]
        
        # Match tolerance fields
        for invoice_field, candidate_field, default_options in tolerance_fields:
            invoice_value = getattr(invoice_data, invoice_field, None)
            candidate_value = candidate_data.get(candidate_field)
            
            if invoice_value is not None and candidate_value is not None:
                # Merge with field-specific options
                field_options = {**default_options, **tolerance_options.get(invoice_field, {})}
                
                result = self.match_field_with_tolerance(
                    invoice_field,
                    invoice_value,
                    candidate_value,
                    **field_options
                )
                results.append(result)
        
        successful_matches = sum(1 for r in results if r.matches)
        self.logger.info(f"Tolerance matched invoice {invoice_data.invoice_number}: "
                        f"{successful_matches}/{len(results)} fields matched")
        return results
    
    def calculate_weighted_confidence(self, results: List[ToleranceMatchResult],
                                    field_weights: Optional[Dict[str, float]] = None) -> float:
        """
        Calculate weighted confidence score from tolerance match results.
        
        Args:
            results: List of tolerance match results
            field_weights: Weights for different fields (default: equal weights)
            
        Returns:
            Weighted confidence score (0.0 to 1.0)
        """
        if not results:
            return 0.0
        
        if field_weights is None:
            # Default equal weights
            field_weights = {result.field_name: 1.0 for result in results}
        
        total_weighted_confidence = 0.0
        total_weight = 0.0
        
        for result in results:
            weight = field_weights.get(result.field_name, 1.0)
            total_weighted_confidence += result.confidence * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        weighted_confidence = total_weighted_confidence / total_weight
        return min(1.0, max(0.0, weighted_confidence))
    
    def get_tolerance_summary(self, results: List[ToleranceMatchResult]) -> Dict[str, Any]:
        """
        Generate summary statistics for tolerance matching results.
        
        Args:
            results: List of tolerance match results
            
        Returns:
            Dictionary with summary statistics
        """
        if not results:
            return {
                'total_fields': 0,
                'matched_fields': 0,
                'match_rate': 0.0,
                'average_confidence': 0.0,
                'tolerance_types': []
            }
        
        matched_count = sum(1 for r in results if r.matches)
        total_confidence = sum(r.confidence for r in results)
        tolerance_types = list(set(r.tolerance_type for r in results))
        
        return {
            'total_fields': len(results),
            'matched_fields': matched_count,
            'match_rate': matched_count / len(results),
            'average_confidence': total_confidence / len(results),
            'tolerance_types': tolerance_types,
            'field_details': [
                {
                    'field_name': r.field_name,
                    'matches': r.matches,
                    'confidence': r.confidence,
                    'tolerance_type': r.tolerance_type,
                    'actual_variance': r.actual_variance
                }
                for r in results
            ]
        }