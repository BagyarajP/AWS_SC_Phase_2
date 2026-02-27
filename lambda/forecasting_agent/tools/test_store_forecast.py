"""
Unit tests for store_forecast Lambda tool

Tests the forecast storage functionality including parameter validation,
database writes, and error handling.
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from store_forecast import (
    lambda_handler,
    store_forecast_records,
    validate_environment
)


@pytest.fixture
def mock_context():
    """Mock Lambda context"""
    context = Mock()
    context.function_name = 'store-forecast-test'
    context.memory_limit_in_mb = 256
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:store-forecast-test'
    context.aws_request_id = 'test-request-id'
    return context


@pytest.fixture
def sample_forecast_data():
    """Sample forecast data for testing"""
    return [
        {
            'forecast_date': '2024-01-15',
            'predicted_demand': 45.5,
            'confidence_80_lower': 38.2,
            'confidence_80_upper': 52.8,
            'confidence_95_lower': 34.1,
            'confidence_95_upper': 56.9
        },
        {
            'forecast_date': '2024-01-16',
            'predicted_demand': 47.2,
            'confidence_80_lower': 39.8,
            'confidence_80_upper': 54.6,
            'confidence_95_lower': 35.5,
            'confidence_95_upper': 58.9
        }
    ]


@pytest.fixture
def valid_event(sample_forecast_data):
    """Valid Lambda event"""
    return {
        'product_id': 'PROD-00001',
        'warehouse_id': 'WH-SOUTH',
        'forecast_data': sample_forecast_data,
        'horizon_days': 7
    }


@pytest.fixture
def setup_env():
    """Setup environment variables for tests"""
    os.environ['REDSHIFT_WORKGROUP'] = 'test-workgroup'
    os.environ['REDSHIFT_DATABASE'] = 'test_db'
    yield
    # Cleanup
    if 'REDSHIFT_WORKGROUP' in os.environ:
        del os.environ['REDSHIFT_WORKGROUP']
    if 'REDSHIFT_DATABASE' in os.environ:
        del os.environ['REDSHIFT_DATABASE']


class TestLambdaHandler:
    """Tests for lambda_handler function"""
    
    @patch('store_forecast.store_forecast_records')
    @patch('store_forecast.validate_environment')
    def test_successful_storage(self, mock_validate, mock_store, valid_event, mock_context, setup_env):
        """Test successful forecast storage"""
        mock_validate.return_value = True
        mock_store.return_value = ['FCST-001', 'FCST-002']
        
        result = lambda_handler(valid_event, mock_context)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['product_id'] == 'PROD-00001'
        assert body['warehouse_id'] == 'WH-SOUTH'
        assert body['records_stored'] == 2
        assert len(body['forecast_ids']) == 2
        
    def test_missing_product_id(self, mock_context, setup_env):
        """Test error handling for missing product_id"""
        event = {
            'warehouse_id': 'WH-SOUTH',
            'forecast_data': [],
            'horizon_days': 7
        }
        
        result = lambda_handler(event, mock_context)
        
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body
        
    def test_missing_warehouse_id(self, mock_context, setup_env):
        """Test error handling for missing warehouse_id"""
        event = {
            'product_id': 'PROD-00001',
            'forecast_data': [],
            'horizon_days': 7
        }
        
        result = lambda_handler(event, mock_context)
        
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body
        
    def test_missing_forecast_data(self, mock_context, setup_env):
        """Test error handling for missing forecast_data"""
        event = {
            'product_id': 'PROD-00001',
            'warehouse_id': 'WH-SOUTH',
            'horizon_days': 7
        }
        
        result = lambda_handler(event, mock_context)
        
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body
        
    @patch('store_forecast.validate_environment')
    def test_environment_validation_failure(self, mock_validate, valid_event, mock_context):
        """Test handling of environment validation failure"""
        mock_validate.return_value = False
        
        result = lambda_handler(valid_event, mock_context)
        
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body
        
    @patch('store_forecast.store_forecast_records')
    @patch('store_forecast.validate_environment')
    def test_bedrock_agent_parameter_format(self, mock_validate, mock_store, sample_forecast_data, mock_context, setup_env):
        """Test handling of Bedrock Agent parameter format"""
        mock_validate.return_value = True
        mock_store.return_value = ['FCST-001']
        
        # Bedrock Agent format with parameters list
        event = {
            'parameters': [
                {'name': 'product_id', 'value': 'PROD-00001'},
                {'name': 'warehouse_id', 'value': 'WH-SOUTH'},
                {'name': 'forecast_data', 'value': json.dumps(sample_forecast_data)},
                {'name': 'horizon_days', 'value': '7'}
            ]
        }
        
        result = lambda_handler(event, mock_context)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['product_id'] == 'PROD-00001'


class TestStoreForecastRecords:
    """Tests for store_forecast_records function"""
    
    @patch('store_forecast.redshift_data')
    @patch('store_forecast.wait_for_query_completion')
    def test_successful_batch_insert(self, mock_wait, mock_redshift, sample_forecast_data, setup_env):
        """Test successful batch insert of forecast records"""
        mock_redshift.execute_statement.return_value = {'Id': 'query-123'}
        mock_wait.return_value = 'FINISHED'
        
        forecast_ids = store_forecast_records(
            'PROD-00001',
            'WH-SOUTH',
            sample_forecast_data,
            7
        )
        
        assert len(forecast_ids) == 2
        assert all(fid.startswith('FCST-') for fid in forecast_ids)
        mock_redshift.execute_statement.assert_called_once()
        
    @patch('store_forecast.redshift_data')
    @patch('store_forecast.wait_for_query_completion')
    def test_query_failure(self, mock_wait, mock_redshift, sample_forecast_data, setup_env):
        """Test handling of query failure"""
        mock_redshift.execute_statement.return_value = {'Id': 'query-123'}
        mock_wait.return_value = 'FAILED'
        
        with pytest.raises(Exception) as exc_info:
            store_forecast_records(
                'PROD-00001',
                'WH-SOUTH',
                sample_forecast_data,
                7
            )
        
        assert 'failed' in str(exc_info.value).lower()
        
    @patch('store_forecast.redshift_data')
    @patch('store_forecast.wait_for_query_completion')
    def test_single_record_storage(self, mock_wait, mock_redshift, setup_env):
        """Test storage of single forecast record"""
        mock_redshift.execute_statement.return_value = {'Id': 'query-123'}
        mock_wait.return_value = 'FINISHED'
        
        single_record = [{
            'forecast_date': '2024-01-15',
            'predicted_demand': 45.5,
            'confidence_80_lower': 38.2,
            'confidence_80_upper': 52.8,
            'confidence_95_lower': 34.1,
            'confidence_95_upper': 56.9
        }]
        
        forecast_ids = store_forecast_records(
            'PROD-00001',
            'WH-SOUTH',
            single_record,
            7
        )
        
        assert len(forecast_ids) == 1


class TestValidateEnvironment:
    """Tests for validate_environment function"""
    
    def test_valid_environment(self, setup_env):
        """Test validation with all required variables"""
        assert validate_environment() is True
        
    def test_missing_workgroup(self):
        """Test validation with missing REDSHIFT_WORKGROUP"""
        if 'REDSHIFT_WORKGROUP' in os.environ:
            del os.environ['REDSHIFT_WORKGROUP']
        os.environ['REDSHIFT_DATABASE'] = 'test_db'
        
        assert validate_environment() is False
        
    def test_missing_database(self):
        """Test validation with missing REDSHIFT_DATABASE"""
        os.environ['REDSHIFT_WORKGROUP'] = 'test-workgroup'
        if 'REDSHIFT_DATABASE' in os.environ:
            del os.environ['REDSHIFT_DATABASE']
        
        assert validate_environment() is False
        
    def test_missing_all_variables(self):
        """Test validation with all variables missing"""
        if 'REDSHIFT_WORKGROUP' in os.environ:
            del os.environ['REDSHIFT_WORKGROUP']
        if 'REDSHIFT_DATABASE' in os.environ:
            del os.environ['REDSHIFT_DATABASE']
        
        assert validate_environment() is False


class TestEdgeCases:
    """Tests for edge cases and error conditions"""
    
    @patch('store_forecast.store_forecast_records')
    @patch('store_forecast.validate_environment')
    def test_empty_forecast_data(self, mock_validate, mock_store, mock_context, setup_env):
        """Test handling of empty forecast data list"""
        mock_validate.return_value = True
        mock_store.return_value = []
        
        event = {
            'product_id': 'PROD-00001',
            'warehouse_id': 'WH-SOUTH',
            'forecast_data': [],
            'horizon_days': 7
        }
        
        result = lambda_handler(event, mock_context)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['records_stored'] == 0
        
    @patch('store_forecast.store_forecast_records')
    @patch('store_forecast.validate_environment')
    def test_large_forecast_data(self, mock_validate, mock_store, mock_context, setup_env):
        """Test handling of large forecast data (30-day horizon)"""
        mock_validate.return_value = True
        mock_store.return_value = [f'FCST-{i:03d}' for i in range(30)]
        
        large_forecast_data = [
            {
                'forecast_date': f'2024-01-{i+1:02d}',
                'predicted_demand': 45.0 + i,
                'confidence_80_lower': 38.0,
                'confidence_80_upper': 52.0,
                'confidence_95_lower': 34.0,
                'confidence_95_upper': 56.0
            }
            for i in range(30)
        ]
        
        event = {
            'product_id': 'PROD-00001',
            'warehouse_id': 'WH-SOUTH',
            'forecast_data': large_forecast_data,
            'horizon_days': 30
        }
        
        result = lambda_handler(event, mock_context)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['records_stored'] == 30


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
