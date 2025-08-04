"""
Invoice matching engine for comparing extracted invoice data against databases.

Provides exact matching, fuzzy matching, and scoring algorithms for
invoice verification and duplicate detection.
"""

from .exact_matcher import ExactMatcher
from .fuzzy_matcher import FuzzyMatcher
from .tolerance_matcher import ToleranceMatcher

__all__ = [
    "ExactMatcher",
    "FuzzyMatcher", 
    "ToleranceMatcher"
]