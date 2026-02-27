"""
Unit tests for calculate_accuracy Lambda tool

Tests the forecast accuracy calculation functionality including MAPE calculation,
data retrieval, and metrics storage.
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from calculate_accuracy import (
    lambda_handler,
    calculate_mape,
    generate_accuracy_summary,
    validate_environment
)


@pytest.fixture
def mock_context():
    """Mock Lambda context"""
    context = Mock()
    context.function_name = 'calculate-accuracy-test'
    context.memory_limit_in_mb = 256
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:calculate-accuracy-test'
    context.aws_request_id = 'test-request-id'
    return context


@pytest.fixture
def sample_forecast_data():
    """Sample forecast data for testing"""
    return [
        {'date': '2024-01-15', 'predicted': 45.0},
        {'date': '2024-01-16', 'predicted': 47.0},
        {'date': '2024-01-17', 'predicted': 50.0}
    ]


@pytest.fixture
def sample_actual_data():
    """Sample actual sales data for testing"""
    return [
        {'date': '2024-01-15', 'actual': 42.0},
        {'date': '2024-01-16', 'actual': 48.0},
        {'date': '2024-01-17', 'actual': 49.0}
    ]


@pytest.fixture
def valid_event():
    """Valid Lambda event"""
    return {
        'product_id': 'PROD-00001',
        'forecast_date': '2024-01-01'
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
    
    @patch('calculate_accuracy.store_accuracy_metrics')
    @patch('calculate_accuracy.calculate_mape')
    @patch('calculate_accuracy.get_forecast_and_actual_data')
    @patch('calculate_accuracy.validate_environment')
    def test_successful_accuracy_calculation(
        self, mock_validate, mock_get_data, mock_calc_mape, mock_store,
        valid_event, mock_context, sample_forecast_data, sample_actual_data, setup_env
    ):
        """Test successful accuracy calculation"""
        mock_validate.return_value = True
        mock_get_data.return_value = (sample_forecast_data, sample_actual_data)
        mock_calc_mape.return_value = {
            'mape': 5.5,
            'mae': 2.3,
            'rmse': 2.8,
            'bias': -0.3,
            'data_points': 3
        }
        mock_store.return_value = ['ACC-001', 'ACC-002', 'ACC-003']
        
        result = lambda_handler(valid_event, mock_context)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['accuracy_calculated'] is True
        assert body['mape'] == 5.5
        assert body['data_points_compared'] == 3
        assert len(body['accuracy_ids']) == 3
        
    @patch('calculate_accuracy.get_forecast_and_actual_data')
    @patch('calculate_accuracy.validate_environment')
    def test_no_forecast_data(self, mock_validate, mock_get_data, valid_event, mock_context, setup_env):
        """Test handling when no forecast data is found"""
        mock_validate.return_value = True
        mock_get_data.return_value = ([], [])
        
        result = lambda_handler(valid_event, mock_context)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['accuracy_calculated'] is False
        assert 'No forecast data found' in body['message']
        
    @patch('calculate_accuracy.get_forecast_and_actual_data')
    @patch('calculate_accuracy.validate_environment')
    def test_no_actual_data(
        self, mock_validate, mock_get_data, valid_event, mock_context,
        sample_forecast_data, setup_env
    ):
        """Test handling when no actual sales data is available"""
        mock_validate.return_value = True
        mock_get_data.return_value = (sample_forecast_data, [])
        
        result = lambda_handler(valid_event, mock_context)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['accuracy_calculated'] is False
        assert 'No actual sales data' in body['message']
        
    def test_missing_product_id(self, mock_context, setup_env):
        """Test error handling for missing product_id"""
        event = {'forecast_date': '2024-01-01'}
        
        result = lambda_handler(event, mock_context)
        
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body
        
    def test_missing_forecast_date(self, mock_context, setup_env):
        """Test error handling for missing forecast_date"""
        event = {'product_id': 'PROD-00001'}
        
        result = lambda_handler(event, mock_context)
        
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body
        
    @patch('calculate_accuracy.validate_environment')
    def test_environment_validation_failure(self, mock_validate, valid_event, mock_context):
        """Test handling of environment validation failure"""
        mock_validate.return_value = False
        
        result = lambda_handler(valid_event, mock_context)
        
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body


class TestCalculateMAPE:
    """Tests for calculate_mape function"""
    
    def test_perfect_forecast(self):
        """Test MAPE calculation with perfect forecast"""
        forecast_data = [
            {'date': '2024-01-15', 'predicted': 50.0},
            {'date': '2024-01-16', 'predicted': 60.0}
        ]
        actual_data = [
            {'date': '2024-01-15', 'actual': 50.0},
            {'date': '2024-01-16', 'actual': 60.0}
        ]
        
        metrics = calculate_mape(forecast_data, actual_data)
        
        assert metrics['mape'] == 0.0
        assert metrics['mae'] == 0.0
        assert metrics['bias'] == 0.0
        assert metrics['data_points'] == 2
        
    def test_over_forecast(self):
        """Test MAPE calculation with over-forecasting"""
        forecast_data = [
            {'date': '2024-01-15', 'predicted': 55.0},
            {'date': '2024-01-16', 'predicted': 66.0}
        ]
        actual_data = [
            {'date': '2024-01-15', 'actual': 50.0},
            {'date': '2024-01-16', 'actual': 60.0}
        ]
        
        metrics = calculate_mape(forecast_data, actual_data)
        
        assert metrics['mape'] == 10.0  # (10% + 10%) / 2
        assert metrics['mae'] == 5.5  # (5 + 6) / 2
        assert metrics['bias'] == 5.5  # Positive bias indicates over-forecasting
        assert metrics['data_points'] == 2
        
    def test_under_forecast(self):
        """Test MAPE calculation with under-forecasting"""
        forecast_data = [
            {'date': '2024-01-15', 'predicted': 45.0},
            {'date': '2024-01-16', 'predicted': 54.0}
        ]
        actual_data = [
            {'date': '2024-01-15', 'actual': 50.0},
            {'date': '2024-01-16', 'actual': 60.0}
        ]
        
        metrics = calculate_mape(forecast_data, actual_data)
        
        assert metrics['mape'] == 10.0  # (10% + 10%) / 2
        assert metrics['mae'] == 5.5  # (5 + 6) / 2
        assert metrics['bias'] == -5.5  # Negative bias indicates under-forecasting
        assert metrics['data_points'] == 2
        
    def test_partial_data_match(self):
        """Test MAPE calculation with partial date matches"""
        forecast_data = [
            {'date': '2024-01-15', 'predicted': 50.0},
            {'date': '2024-01-16', 'predicted': 60.0},
            {'date': '2024-01-17', 'predicted': 70.0}
        ]
        actual_data = [
            {'date': '2024-01-15', 'actual': 50.0},
            {'date': '2024-01-17', 'actual': 70.0}
        ]
        
        metrics = calculate_mape(forecast_data, actual_data)
        
        assert metrics['data_points'] == 2  # Only 2 matching dates
        assert metrics['mape'] == 0.0
        
    def test_zero_actual_values_skipped(self):
        """Test that zero actual values are skipped to avoid division by zero"""
        forecast_data = [
            {'date': '2024-01-15', 'predicted': 50.0},
            {'date': '2024-01-16', 'predicted': 60.0}
        ]
        actual_data = [
            {'date': '2024-01-15', 'actual': 0.0},  # Should be skipped
            {'date': '2024-01-16', 'actual': 60.0}
        ]
        
        metrics = calculate_mape(forecast_data, actual_data)
        
        assert metrics['data_points'] == 1  # Only 1 valid data point
        assert metrics['mape'] == 0.0
        
    def test_no_matching_dates(self):
        """Test error handling when no dates match"""
        forecast_data = [
            {'date': '2024-01-15', 'predicted': 50.0}
        ]
        actual_data = [
            {'date': '2024-01-20', 'actual': 60.0}
        ]
        
        with pytest.raises(ValueError) as exc_info:
            calculate_mape(forecast_data, actual_data)
        
        assert 'No matching data points' in str(exc_info.value)


class TestGenerateAccuracySummary:
    """Tests for generate_accuracy_summary function"""
    
    def test_excellent_accuracy(self):
        """Test summary generation for excellent accuracy (MAPE < 10%)"""
        metrics = {
            'mape': 5.5,
            'mae': 2.3,
            'rmse': 2.8,
            'bias': 0.5,
            'data_points': 10
        }
        
        summary = generate_accuracy_summary(metrics)
        
        assert 'excellent' in summary.lower()
        assert '5.5' in summary
        assert '10 data points' in summary
        
    def test_good_accuracy(self):
        """Test summary generation for good accuracy (10% <= MAPE < 15%)"""
        metrics = {
            'mape': 12.0,
            'mae': 5.0,
            'rmse': 6.0,
            'bias': -2.0,
            'data_points': 15
        }
        
        summary = generate_accuracy_summary(metrics)
        
        assert 'good' in summary.lower()
        assert '12.0' in summary
        assert 'under-forecasting' in summary.lower()
        
    def test_acceptable_accuracy(self):
        """Test summary generation for acceptable accuracy (15% <= MAPE < 25%)"""
        metrics = {
            'mape': 18.5,
            'mae': 8.0,
            'rmse': 10.0,
            'bias': 3.5,
            'data_points': 20
        }
        
        summary = generate_accuracy_summary(metrics)
        
        assert 'acceptable' in summary.lower()
        assert '18.5' in summary
        assert 'over-forecasting' in summary.lower()
        
    def test_poor_accuracy(self):
        """Test summary generation for poor accuracy (MAPE >= 25%)"""
        metrics = {
            'mape': 30.0,
            'mae': 15.0,
            'rmse': 18.0,
            'bias': 0.2,
            'data_points': 8
        }
        
        summary = generate_accuracy_summary(metrics)
        
        assert 'poor' in summary.lower()
        assert '30.0' in summary
        assert 'minimal bias' in summary.lower()


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


class TestEdgeCases:
    """Tests for edge cases and error conditions"""
    
    @patch('calculate_accuracy.store_accuracy_metrics')
    @patch('calculate_accuracy.calculate_mape')
    @patch('calculate_accuracy.get_forecast_and_actual_data')
    @patch('calculate_accuracy.validate_environment')
    def test_bedrock_agent_parameter_format(
        self, mock_validate, mock_get_data, mock_calc_mape, mock_store,
        mock_context, sample_forecast_data, sample_actual_data, setup_env
    ):
        """Test handling of Bedrock Agent parameter format"""
        mock_validate.return_value = True
        mock_get_data.return_value = (sample_forecast_data, sample_actual_data)
        mock_calc_mape.return_value = {
            'mape': 5.5,
            'mae': 2.3,
            'rmse': 2.8,
            'bias': -0.3,
            'data_points': 3
        }
        mock_store.return_value = ['ACC-001']
        
        # Bedrock Agent format with parameters list
        event = {
            'parameters': [
                {'name': 'product_id', 'value': 'PROD-00001'},
                {'name': 'forecast_date', 'value': '2024-01-01'}
            ]
        }
        
        result = lambda_handler(event, mock_context)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['product_id'] == 'PROD-00001'
        assert body['accuracy_calculated'] is True
        
    def test_high_mape_values(self):
        """Test MAPE calculation with high error values"""
        forecast_data = [
            {'date': '2024-01-15', 'predicted': 100.0}
        ]
        actual_data = [
            {'date': '2024-01-15', 'actual': 50.0}
        ]
        
        metrics = calculate_mape(forecast_data, actual_data)
        
        assert metrics['mape'] == 100.0  # 100% error
        assert metrics['mae'] == 50.0
        assert metrics['bias'] == 50.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
