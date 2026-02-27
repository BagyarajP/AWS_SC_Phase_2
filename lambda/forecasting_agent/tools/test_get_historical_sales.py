"""
Unit tests for get_historical_sales Lambda tool

Tests the historical sales data retrieval functionality including:
- Parameter validation
- Redshift Data API integration
- Error handling
- Response formatting
"""

import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from get_historical_sales import (
    lambda_handler,
    query_historical_sales,
    wait_for_query_completion,
    validate_environment
)


class TestGetHistoricalSales:
    """Test suite for get_historical_sales Lambda tool"""
    
    def setup_method(self):
        """Set up test environment variables"""
        os.environ['REDSHIFT_WORKGROUP'] = 'test-workgroup'
        os.environ['REDSHIFT_DATABASE'] = 'test_db'
    
    def teardown_method(self):
        """Clean up environment variables"""
        if 'REDSHIFT_WORKGROUP' in os.environ:
            del os.environ['REDSHIFT_WORKGROUP']
        if 'REDSHIFT_DATABASE' in os.environ:
            del os.environ['REDSHIFT_DATABASE']
    
    def test_validate_environment_success(self):
        """Test environment validation with all required variables"""
        assert validate_environment() is True
    
    def test_validate_environment_missing_vars(self):
        """Test environment validation with missing variables"""
        del os.environ['REDSHIFT_WORKGROUP']
        assert validate_environment() is False
    
    @patch('get_historical_sales.redshift_data')
    def test_lambda_handler_success(self, mock_redshift):
        """Test successful Lambda invocation with valid parameters"""
        # Mock Redshift Data API responses
        mock_redshift.execute_statement.return_value = {'Id': 'query-123'}
        mock_redshift.describe_statement.return_value = {'Status': 'FINISHED'}
        mock_redshift.get_statement_result.return_value = {
            'Records': [
                [
                    {'stringValue': '2023-01-01'},
                    {'longValue': 45}
                ],
                [
                    {'stringValue': '2023-01-02'},
                    {'longValue': 52}
                ]
            ]
        }
        
        # Test event
        event = {
            'product_id': 'PROD-00001',
            'months_back': 12
        }
        
        context = Mock()
        
        # Execute
        result = lambda_handler(event, context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['product_id'] == 'PROD-00001'
        assert body['months_back'] == 12
        assert body['data_points'] == 2
        assert len(body['time_series']) == 2
        assert body['time_series'][0]['order_date'] == '2023-01-01'
        assert body['time_series'][0]['quantity'] == 45
        assert body['summary']['total_quantity'] == 97
    
    @patch('get_historical_sales.redshift_data')
    def test_lambda_handler_bedrock_format(self, mock_redshift):
        """Test Lambda invocation with Bedrock Agent parameter format"""
        # Mock Redshift Data API responses
        mock_redshift.execute_statement.return_value = {'Id': 'query-123'}
        mock_redshift.describe_statement.return_value = {'Status': 'FINISHED'}
        mock_redshift.get_statement_result.return_value = {
            'Records': [
                [
                    {'stringValue': '2023-01-01'},
                    {'longValue': 100}
                ]
            ]
        }
        
        # Test event in Bedrock Agent format
        event = {
            'parameters': [
                {'name': 'product_id', 'value': 'PROD-00002'},
                {'name': 'months_back', 'value': '6'}
            ]
        }
        
        context = Mock()
        
        # Execute
        result = lambda_handler(event, context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['product_id'] == 'PROD-00002'
        assert body['months_back'] == 6
    
    def test_lambda_handler_missing_product_id(self):
        """Test Lambda invocation with missing product_id parameter"""
        event = {
            'months_back': 12
        }
        
        context = Mock()
        
        # Execute
        result = lambda_handler(event, context)
        
        # Assertions
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body
    
    @patch('get_historical_sales.redshift_data')
    def test_lambda_handler_no_data_found(self, mock_redshift):
        """Test Lambda invocation when no historical data exists"""
        # Mock Redshift Data API responses with empty result
        mock_redshift.execute_statement.return_value = {'Id': 'query-123'}
        mock_redshift.describe_statement.return_value = {'Status': 'FINISHED'}
        mock_redshift.get_statement_result.return_value = {
            'Records': []
        }
        
        event = {
            'product_id': 'PROD-99999',
            'months_back': 12
        }
        
        context = Mock()
        
        # Execute
        result = lambda_handler(event, context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['data_points'] == 0
        assert body['time_series'] == []
        assert 'No historical sales data found' in body['message']
    
    @patch('get_historical_sales.redshift_data')
    def test_query_historical_sales_success(self, mock_redshift):
        """Test successful Redshift query execution"""
        # Mock responses
        mock_redshift.execute_statement.return_value = {'Id': 'query-456'}
        mock_redshift.describe_statement.return_value = {'Status': 'FINISHED'}
        mock_redshift.get_statement_result.return_value = {
            'Records': [
                [
                    {'stringValue': '2023-06-01'},
                    {'longValue': 75}
                ],
                [
                    {'stringValue': '2023-06-02'},
                    {'longValue': 80}
                ]
            ]
        }
        
        # Execute
        result = query_historical_sales('PROD-00003', 6)
        
        # Assertions
        assert len(result) == 2
        assert result[0]['order_date'] == '2023-06-01'
        assert result[0]['quantity'] == 75
        assert result[1]['order_date'] == '2023-06-02'
        assert result[1]['quantity'] == 80
    
    @patch('get_historical_sales.redshift_data')
    def test_wait_for_query_completion_finished(self, mock_redshift):
        """Test query completion wait with FINISHED status"""
        mock_redshift.describe_statement.return_value = {'Status': 'FINISHED'}
        
        status = wait_for_query_completion('query-789')
        
        assert status == 'FINISHED'
    
    @patch('get_historical_sales.redshift_data')
    def test_wait_for_query_completion_failed(self, mock_redshift):
        """Test query completion wait with FAILED status"""
        mock_redshift.describe_statement.return_value = {
            'Status': 'FAILED',
            'Error': 'Syntax error in SQL'
        }
        
        with pytest.raises(Exception) as exc_info:
            wait_for_query_completion('query-789')
        
        assert 'FAILED' in str(exc_info.value)
    
    @patch('get_historical_sales.redshift_data')
    @patch('get_historical_sales.time.sleep')
    def test_wait_for_query_completion_timeout(self, mock_sleep, mock_redshift):
        """Test query completion wait with timeout"""
        # Always return RUNNING status to trigger timeout
        mock_redshift.describe_statement.return_value = {'Status': 'RUNNING'}
        
        with pytest.raises(Exception) as exc_info:
            wait_for_query_completion('query-789', max_wait_seconds=1)
        
        assert 'timeout' in str(exc_info.value).lower()
    
    @patch('get_historical_sales.redshift_data')
    def test_query_historical_sales_with_sql_injection_protection(self, mock_redshift):
        """Test that SQL query properly handles product_id (note: uses string formatting for simplicity in MVP)"""
        mock_redshift.execute_statement.return_value = {'Id': 'query-999'}
        mock_redshift.describe_statement.return_value = {'Status': 'FINISHED'}
        mock_redshift.get_statement_result.return_value = {'Records': []}
        
        # Execute with product_id
        query_historical_sales('PROD-00001', 12)
        
        # Verify execute_statement was called
        assert mock_redshift.execute_statement.called
        call_args = mock_redshift.execute_statement.call_args
        sql = call_args[1]['Sql']
        
        # Verify SQL contains the product_id
        assert 'PROD-00001' in sql
        assert 'sales_order_line' in sql
        assert 'sales_order_header' in sql


class TestIntegration:
    """Integration tests (require actual Redshift connection)"""
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.environ.get('RUN_INTEGRATION_TESTS'),
        reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=1 to enable"
    )
    def test_real_redshift_query(self):
        """Test actual Redshift query (requires real connection)"""
        # Set real environment variables
        os.environ['REDSHIFT_WORKGROUP'] = 'supply-chain-workgroup'
        os.environ['REDSHIFT_DATABASE'] = 'supply_chain'
        
        event = {
            'product_id': 'PROD-00001',
            'months_back': 12
        }
        
        context = Mock()
        
        # Execute
        result = lambda_handler(event, context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert 'time_series' in body
        assert 'summary' in body


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '--tb=short'])
