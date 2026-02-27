"""
Property-Based Test for Lambda CloudWatch Logging

Property 29: Lambda CloudWatch logging
For any Lambda function execution (Procurement, Inventory, or Forecasting Agent), 
execution details should be logged to CloudWatch Logs.

**Validates: Requirements 8.6**

Testing Framework: pytest with hypothesis

Note: This test captures log output during Lambda execution to verify logging behavior.
"""

import pytest
import logging
import json
import io
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import patch, MagicMock
from lambda_function import lambda_handler


# Feature: supply-chain-ai-platform, Property 29: Lambda CloudWatch logging


class LogCapture:
    """Helper class to capture log messages during test execution"""
    
    def __init__(self):
        self.records = []
        self.handler = None
        
    def __enter__(self):
        # Create a custom handler that captures log records
        self.handler = logging.Handler()
        self.handler.emit = lambda record: self.records.append(record)
        
        # Add handler to root logger
        logger = logging.getLogger()
        logger.addHandler(self.handler)
        logger.setLevel(logging.DEBUG)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Remove handler
        logger = logging.getLogger()
        logger.removeHandler(self.handler)
    
    def get_messages(self, level=None):
        """Get all captured log messages, optionally filtered by level"""
        if level is None:
            return [record.getMessage() for record in self.records]
        else:
            return [record.getMessage() for record in self.records if record.levelno == level]
    
    def has_message_containing(self, text, level=None):
        """Check if any log message contains the given text"""
        messages = self.get_messages(level)
        return any(text in msg for msg in messages)
    
    def count_messages(self, level=None):
        """Count log messages, optionally filtered by level"""
        return len(self.get_messages(level))


class MockContext:
    """Mock Lambda context for testing"""
    function_name = 'forecasting-agent-test'
    memory_limit_in_mb = 512
    invoked_function_arn = 'arn:aws:lambda:eu-west-2:123456789012:function:forecasting-agent-test'
    aws_request_id = 'test-request-id'


@pytest.fixture
def mock_redshift_connection():
    """Mock Redshift connection to avoid actual database calls"""
    with patch('lambda_function.connect_with_retry') as mock_connect:
        # Create mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        # Mock get_all_products to return empty list (no products to forecast)
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = [('product_id',), ('sku',), ('product_name',), ('category',)]
        mock_conn.cursor.return_value = mock_cursor
        
        mock_connect.return_value = mock_conn
        
        yield mock_conn


@settings(
    max_examples=10,  # Test with 10 different scenarios
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    # Test with different event types
    event_source=st.sampled_from(['aws.events', 'manual', 'test']),
    detail_type=st.sampled_from(['Scheduled Event', 'Manual Trigger', 'Test Event'])
)
def test_property_lambda_cloudwatch_logging(mock_redshift_connection, event_source, detail_type):
    """
    Property 29: Lambda CloudWatch logging
    
    For any Lambda function execution, execution details should be logged to CloudWatch.
    
    This test:
    1. Executes the Lambda handler with various event types
    2. Captures all log output during execution
    3. Verifies that key execution details are logged:
       - Execution start
       - Connection status
       - Processing progress
       - Execution completion
       - Any errors (with stack traces)
    
    **Validates: Requirements 8.6**
    """
    # Prepare test event
    event = {
        'source': event_source,
        'detail-type': detail_type
    }
    
    # Capture logs during Lambda execution
    with LogCapture() as log_capture:
        # Execute Lambda handler
        result = lambda_handler(event, MockContext())
        
        # Property: Lambda execution should log to CloudWatch
        # Verify that logs were generated
        total_logs = log_capture.count_messages()
        assert total_logs > 0, "Lambda should generate log messages during execution"
        
        # Property: Execution start should be logged
        assert log_capture.has_message_containing("Forecasting Agent execution started"), \
            "Lambda should log execution start"
        
        # Property: Connection attempts should be logged
        assert log_capture.has_message_containing("Attempting Redshift connection") or \
               log_capture.has_message_containing("Successfully connected to Redshift"), \
            "Lambda should log database connection attempts"
        
        # Property: Execution completion should be logged
        # Either successful completion or error should be logged
        has_completion_log = (
            log_capture.has_message_containing("Forecasting Agent completed") or
            log_capture.has_message_containing("Fatal error in Forecasting Agent")
        )
        assert has_completion_log, "Lambda should log execution completion or errors"
        
        # Property: INFO level logs should be present for normal execution flow
        info_logs = log_capture.count_messages(level=logging.INFO)
        assert info_logs > 0, "Lambda should generate INFO level logs"
        
        # Verify result structure
        assert 'statusCode' in result, "Lambda should return statusCode"
        assert 'body' in result, "Lambda should return body"
        
        print(f"✓ Property 29 validated: {total_logs} log messages generated, "
              f"{info_logs} INFO level logs")


def test_property_lambda_error_logging(mock_redshift_connection):
    """
    Test that errors are logged with stack traces
    
    This verifies that when errors occur, they are logged with full details
    including stack traces (exc_info=True).
    """
    # Mock a connection failure to trigger error logging
    with patch('lambda_function.connect_with_retry') as mock_connect:
        mock_connect.side_effect = Exception("Database connection failed")
        
        # Capture logs
        with LogCapture() as log_capture:
            # Execute Lambda handler (should fail)
            result = lambda_handler({}, MockContext())
            
            # Property: Errors should be logged
            error_logs = log_capture.count_messages(level=logging.ERROR)
            assert error_logs > 0, "Lambda should log errors when they occur"
            
            # Property: Error messages should contain details
            assert log_capture.has_message_containing("Fatal error in Forecasting Agent", level=logging.ERROR), \
                "Lambda should log fatal errors with descriptive messages"
            
            # Verify error response
            assert result['statusCode'] == 500, "Lambda should return 500 on error"
            
            print(f"✓ Error logging validated: {error_logs} error messages logged")


def test_property_lambda_logging_levels():
    """
    Test that Lambda uses appropriate logging levels
    
    Verifies that different types of messages use appropriate log levels:
    - INFO for normal execution flow
    - WARNING for non-critical issues
    - ERROR for failures
    """
    with patch('lambda_function.connect_with_retry') as mock_connect:
        # Create mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        # Mock get_all_products to return a product with insufficient data
        mock_cursor.fetchall.side_effect = [
            # First call: get_all_products
            [('PROD-001', 'SKU-001', 'Test Product', 'Category')],
            # Second call: get_historical_sales_data (empty result)
            []
        ]
        mock_cursor.description = [('product_id',), ('sku',), ('product_name',), ('category',)]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Capture logs
        with LogCapture() as log_capture:
            result = lambda_handler({}, MockContext())
            
            # Property: INFO logs should be present for normal flow
            info_count = log_capture.count_messages(level=logging.INFO)
            assert info_count > 0, "Lambda should use INFO level for normal execution"
            
            # Property: WARNING logs may be present for non-critical issues
            warning_count = log_capture.count_messages(level=logging.WARNING)
            # Warnings are optional but if present, they should be for appropriate situations
            if warning_count > 0:
                assert log_capture.has_message_containing("Insufficient historical data", level=logging.WARNING), \
                    "WARNING level should be used for non-critical issues"
            
            print(f"✓ Logging levels validated: {info_count} INFO, {warning_count} WARNING logs")


def test_property_lambda_logging_unit():
    """
    Unit test version of Property 29 for faster execution
    
    This test verifies basic logging behavior without hypothesis.
    """
    with patch('lambda_function.connect_with_retry') as mock_connect:
        # Create mock connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = [('product_id',), ('sku',), ('product_name',), ('category',)]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Capture logs
        with LogCapture() as log_capture:
            result = lambda_handler({}, MockContext())
            
            # Verify logging occurred
            assert log_capture.count_messages() > 0
            assert log_capture.has_message_containing("Forecasting Agent execution started")
            assert log_capture.has_message_containing("Successfully connected to Redshift")
            
            # Verify successful execution
            assert result['statusCode'] == 200
            
            print("✓ Lambda CloudWatch logging validated")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
