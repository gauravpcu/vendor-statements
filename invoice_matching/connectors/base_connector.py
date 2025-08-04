"""
Base connector interface for invoice matching data sources.

Provides common functionality and interface for all connector types
including error handling, logging, and connection management.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from invoice_matching.models import ConnectionTestResult, InvoiceMatchingError

logger = logging.getLogger(__name__)


class ConnectorError(InvoiceMatchingError):
    """Base exception for connector-related errors."""
    pass


class BaseConnector(ABC):
    """
    Abstract base class for all invoice matching connectors.
    
    Provides common functionality for database and API connectors
    including connection testing, error handling, and logging.
    """
    
    def __init__(self, connection_id: str):
        """
        Initialize base connector.
        
        Args:
            connection_id: Unique identifier for this connection
        """
        self.connection_id = connection_id
        self.logger = logging.getLogger(f"{__name__}.{connection_id}")
        self._last_connection_test: Optional[ConnectionTestResult] = None
        self._connection_healthy = True
    
    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """
        Test the connection to the data source.
        
        Returns:
            ConnectionTestResult with success status and details
        """
        pass
    
    @abstractmethod
    def search_invoices(self, search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for invoices matching the given criteria.
        
        Args:
            search_criteria: Dictionary containing search parameters
            
        Returns:
            List of matching invoice records
            
        Raises:
            ConnectorError: If search operation fails
        """
        pass
    
    @abstractmethod
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get information about the current connection.
        
        Returns:
            Dictionary containing connection metadata
        """
        pass
    
    def is_healthy(self) -> bool:
        """
        Check if the connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        return self._connection_healthy
    
    def get_last_test_result(self) -> Optional[ConnectionTestResult]:
        """
        Get the result of the last connection test.
        
        Returns:
            Last ConnectionTestResult or None if never tested
        """
        return self._last_connection_test
    
    def _log_operation(self, operation: str, duration: float, success: bool, 
                      details: Optional[str] = None):
        """
        Log connector operation with timing and status.
        
        Args:
            operation: Name of the operation
            duration: Time taken in seconds
            success: Whether operation succeeded
            details: Additional details to log
        """
        status = "SUCCESS" if success else "FAILED"
        message = f"{operation} {status} in {duration:.3f}s"
        
        if details:
            message += f" - {details}"
        
        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)
    
    def _handle_error(self, operation: str, error: Exception) -> ConnectorError:
        """
        Handle and log connector errors consistently.
        
        Args:
            operation: Name of the operation that failed
            error: The original exception
            
        Returns:
            ConnectorError with appropriate message
        """
        error_msg = f"{operation} failed for connection '{self.connection_id}': {str(error)}"
        self.logger.error(error_msg, exc_info=True)
        self._connection_healthy = False
        return ConnectorError(error_msg)
    
    def _measure_time(self, func, *args, **kwargs):
        """
        Measure execution time of a function.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Tuple of (result, duration_in_seconds)
        """
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            return result, duration
        except Exception as e:
            duration = time.time() - start_time
            raise e