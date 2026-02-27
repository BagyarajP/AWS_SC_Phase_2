"""
Unit Tests for Task 4.7: Store forecasts in Redshift and calculate accuracy

These are unit tests using mocks - no database connection required.

Tests verify:
1. store_forecast function creates correct SQL statements
2. calculate_forecast_accuracy function logic
3. MAPE calculation correctness
"""

import pytest
from unittest.mock import Mock, MagicMock, call
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lambda_function import store_forecast, calculate_forecast_accuracy


class TestStoreForecast:
    """Test forecast storage functionality"""
    
    def test_store_forecast_creates_two_records(self):
        """Test that store_forecast creates records for both 80% and 95% confidence levels"""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        product_id = 'PROD-001'
        horizon = 7
        forecast = 150
        intervals_80 = {'lower': 120, 'upper': 180}
        intervals_95 = {'lower': 100, 'upper': 200}
        
        # Act
        forecast_id = store_forecast(
            conn=mock_conn,
            product_id=product_id,
            horizon=horizon,
            forecast=forecast,
            intervals_80=intervals_80,
            intervals_95=intervals_95
        )
        
        # Assert
        assert forecast_id is not None
        assert forecast_id.startswith('FC-')
        
        # Verify cursor.execute was called twice (once for 80%, once for 95%)
        assert mock_cursor.execute.call_count == 2
        
        # Verify commit was called
        mock_conn.commit.assert_called_once()
        
        # Verify cursor was closed
        mock_cursor.close.assert_called_once()
    
    def test_store_forecast_sql_parameters(self):
        """Test that store_forecast passes correct parameters to SQL"""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        product_id = 'PROD-123'
        horizon = 30
        forecast = 500
        intervals_80 = {'lower': 400, 'upper': 600}
        intervals_95 = {'lower': 350, 'upper': 650}
        
        # Act
        forecast_id = store_forecast(
            conn=mock_conn,
            product_id=product_id,
            horizon=horizon,
            forecast=forecast,
            intervals_80=intervals_80,
            intervals_95=intervals_95
        )
        
        # Assert - Check the parameters passed to execute
        calls = mock_cursor.execute.call_args_list
        
        # First call (80% confidence)
        first_call_params = calls[0][0][1]
        assert first_call_params[1] == product_id
        assert first_call_params[4] == horizon
        assert first_call_params[5] == forecast
        assert first_call_params[6] == intervals_80['lower']
        assert first_call_params[7] == intervals_80['upper']
        assert first_call_params[8] == 0.80
        
        # Second call (95% confidence)
        second_call_params = calls[1][0][1]
        assert second_call_params[1] == product_id
        assert second_call_params[4] == horizon
        assert second_call_params[5] == forecast
        assert second_call_params[6] == intervals_95['lower']
        assert second_call_params[7] == intervals_95['upper']
        assert second_call_params[8] == 0.95


class TestCalculateForecastAccuracy:
    """Test forecast accuracy calculation functionality"""
    
    def test_mape_calculation_logic(self):
        """Test MAPE calculation formula"""
        # Test cases: (actual, predicted, expected_mape)
        test_cases = [
            (100, 120, 20.0),   # 20% over-prediction
            (100, 80, 20.0),    # 20% under-prediction
            (200, 200, 0.0),    # Perfect prediction
            (150, 100, 33.33),  # 33.33% under-prediction
            (0, 100, 100.0),    # Zero actual, non-zero predicted
            (0, 0, 0.0),        # Both zero
        ]
        
        for actual, predicted, expected_mape in test_cases:
            if actual > 0:
                mape = abs(actual - predicted) / actual * 100
            else:
                mape = 0 if predicted == 0 else 100
            
            assert abs(mape - expected_mape) < 0.01, \
                f"MAPE calculation failed for actual={actual}, predicted={predicted}"
    
    def test_calculate_forecast_accuracy_queries_old_forecasts(self):
        """Test that calculate_forecast_accuracy queries for forecasts to evaluate"""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock empty result (no forecasts to evaluate)
        mock_cursor.fetchall.return_value = []
        mock_cursor.__iter__ = Mock(return_value=iter([]))
        
        # Act
        result = calculate_forecast_accuracy(mock_conn)
        
        # Assert
        assert result['successful'] == 0
        assert result['failed'] == 0
        
        # Verify query was executed
        mock_cursor.execute.assert_called()
        
        # Verify cursor was closed
        mock_cursor.close.assert_called()
    
    def test_calculate_forecast_accuracy_with_mock_data(self):
        """Test accuracy calculation with mocked forecast and sales data"""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock forecast to evaluate
        forecast_date = datetime.now().date() - timedelta(days=30)
        mock_forecasts = [
            {
                'forecast_id': 'FC-TEST-001',
                'product_id': 'PROD-001',
                'forecast_date': forecast_date,
                'forecast_horizon_days': 7,
                'predicted_demand': 100,
                'confidence_level': 0.80
            }
        ]
        
        # Mock the query results
        # First call: get forecasts to evaluate
        # Second call: get actual demand
        # Third call: insert accuracy record
        mock_cursor.fetchall.side_effect = [
            # Forecasts to evaluate (converted to tuples as DB would return)
            [(f['forecast_id'], f['product_id'], f['forecast_date'], 
              f['forecast_horizon_days'], f['predicted_demand'], f['confidence_level']) 
             for f in mock_forecasts],
        ]
        
        mock_cursor.fetchone.return_value = (120,)  # Actual demand = 120
        
        # Mock description for column names
        mock_cursor.description = [
            ('forecast_id',), ('product_id',), ('forecast_date',),
            ('forecast_horizon_days',), ('predicted_demand',), ('confidence_level',)
        ]
        
        # Act
        result = calculate_forecast_accuracy(mock_conn)
        
        # Assert
        assert result['successful'] == 1
        assert result['failed'] == 0
        
        # Verify INSERT was called for accuracy record
        insert_calls = [call for call in mock_cursor.execute.call_args_list 
                       if 'INSERT INTO forecast_accuracy' in str(call)]
        assert len(insert_calls) == 1
        
        # Verify MAPE calculation in the INSERT
        # Expected MAPE = |120 - 100| / 120 * 100 = 16.67%
        insert_params = insert_calls[0][0][1]
        mape_value = insert_params[5]
        expected_mape = abs(120 - 100) / 120 * 100
        assert abs(mape_value - expected_mape) < 0.1
    
    def test_calculate_forecast_accuracy_handles_errors(self):
        """Test that calculate_forecast_accuracy handles errors gracefully"""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock an error during query
        mock_cursor.execute.side_effect = Exception("Database error")
        
        # Act
        result = calculate_forecast_accuracy(mock_conn)
        
        # Assert
        assert result['successful'] == 0
        assert len(result['errors']) > 0
        assert 'Database error' in str(result['errors'][0])


class TestMAPECalculation:
    """Test MAPE calculation edge cases"""
    
    def test_mape_with_positive_actual(self):
        """Test MAPE when actual demand is positive"""
        actual = 100
        predicted = 120
        
        mape = abs(actual - predicted) / actual * 100
        
        assert mape == 20.0
    
    def test_mape_with_zero_actual_and_zero_predicted(self):
        """Test MAPE when both actual and predicted are zero"""
        actual = 0
        predicted = 0
        
        mape = 0 if predicted == 0 else 100
        
        assert mape == 0.0
    
    def test_mape_with_zero_actual_and_positive_predicted(self):
        """Test MAPE when actual is zero but predicted is positive"""
        actual = 0
        predicted = 50
        
        mape = 0 if predicted == 0 else 100
        
        assert mape == 100.0
    
    def test_mape_perfect_prediction(self):
        """Test MAPE with perfect prediction"""
        actual = 150
        predicted = 150
        
        mape = abs(actual - predicted) / actual * 100
        
        assert mape == 0.0
    
    def test_mape_over_prediction(self):
        """Test MAPE with over-prediction"""
        actual = 100
        predicted = 150
        
        mape = abs(actual - predicted) / actual * 100
        
        assert mape == 50.0
    
    def test_mape_under_prediction(self):
        """Test MAPE with under-prediction"""
        actual = 200
        predicted = 150
        
        mape = abs(actual - predicted) / actual * 100
        
        assert mape == 25.0


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '-s'])
