"""
Unit tests for calculate_forecast Lambda tool

Tests the demand forecasting functionality including:
- Holt-Winters exponential smoothing
- ARIMA forecasting
- Ensemble forecasting
- Confidence interval calculation
- Parameter validation
- Error handling
"""

import json
import pytest
import numpy as np
from unittest.mock import Mock
from calculate_forecast import (
    lambda_handler,
    holt_winters_forecast,
    arima_forecast_simple,
    calculate_confidence_intervals
)


class TestCalculateForecast:
    """Test suite for calculate_forecast Lambda tool"""
    
    def create_test_data(self, days: int = 90, base_value: int = 50) -> list:
        """Helper to create test historical data"""
        from datetime import datetime, timedelta
        start_date = datetime(2023, 1, 1)
        return [
            {
                'order_date': (start_date + timedelta(days=i)).strftime('%Y-%m-%d'),
                'quantity': base_value + (i % 7) * 5  # Weekly pattern
            }
            for i in range(days)
        ]
    
    def test_lambda_handler_success_7_day(self):
        """Test successful 7-day forecast generation"""
        historical_data = self.create_test_data(90)
        
        event = {
            'product_id': 'PROD-00001',
            'historical_data': historical_data,
            'horizon_days': 7
        }
        
        context = Mock()
        
        # Execute
        result = lambda_handler(event, context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['product_id'] == 'PROD-00001'
        assert body['horizon_days'] == 7
        assert len(body['forecast_data']) == 7
        
        # Check first forecast point structure
        first_forecast = body['forecast_data'][0]
        assert 'forecast_date' in first_forecast
        assert 'predicted_demand' in first_forecast
        assert 'confidence_80_lower' in first_forecast
        assert 'confidence_80_upper' in first_forecast
        assert 'confidence_95_lower' in first_forecast
        assert 'confidence_95_upper' in first_forecast
        assert 'model_components' in first_forecast
        assert 'holt_winters' in first_forecast['model_components']
        assert 'arima' in first_forecast['model_components']
        
        # Check summary
        assert 'summary' in body
        assert 'total_predicted_demand' in body['summary']
        assert 'average_daily_demand' in body['summary']
        assert 'historical_average' in body['summary']
    
    def test_lambda_handler_success_30_day(self):
        """Test successful 30-day forecast generation"""
        historical_data = self.create_test_data(180)
        
        event = {
            'product_id': 'PROD-00002',
            'historical_data': historical_data,
            'horizon_days': 30
        }
        
        context = Mock()
        
        # Execute
        result = lambda_handler(event, context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['horizon_days'] == 30
        assert len(body['forecast_data']) == 30
    
    def test_lambda_handler_bedrock_format(self):
        """Test Lambda invocation with Bedrock Agent parameter format"""
        historical_data = self.create_test_data(60)
        
        event = {
            'parameters': [
                {'name': 'product_id', 'value': 'PROD-00003'},
                {'name': 'historical_data', 'value': json.dumps(historical_data)},
                {'name': 'horizon_days', 'value': '7'}
            ]
        }
        
        context = Mock()
        
        # Execute
        result = lambda_handler(event, context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['product_id'] == 'PROD-00003'
    
    def test_lambda_handler_missing_product_id(self):
        """Test error handling for missing product_id"""
        event = {
            'historical_data': self.create_test_data(60),
            'horizon_days': 7
        }
        
        context = Mock()
        
        # Execute
        result = lambda_handler(event, context)
        
        # Assertions
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body
    
    def test_lambda_handler_missing_historical_data(self):
        """Test error handling for missing historical_data"""
        event = {
            'product_id': 'PROD-00001',
            'horizon_days': 7
        }
        
        context = Mock()
        
        # Execute
        result = lambda_handler(event, context)
        
        # Assertions
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body
        assert 'historical_data' in body['error']
    
    def test_lambda_handler_invalid_horizon(self):
        """Test error handling for invalid horizon_days"""
        event = {
            'product_id': 'PROD-00001',
            'historical_data': self.create_test_data(60),
            'horizon_days': 15  # Invalid: must be 7 or 30
        }
        
        context = Mock()
        
        # Execute
        result = lambda_handler(event, context)
        
        # Assertions
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body
        assert 'horizon_days' in body['error']
    
    def test_lambda_handler_insufficient_data(self):
        """Test error handling for insufficient historical data"""
        event = {
            'product_id': 'PROD-00001',
            'historical_data': self.create_test_data(10),  # Too few data points
            'horizon_days': 7
        }
        
        context = Mock()
        
        # Execute
        result = lambda_handler(event, context)
        
        # Assertions
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body
        assert 'Insufficient' in body['error']
    
    def test_forecast_dates_sequential(self):
        """Test that forecast dates are sequential and start after last historical date"""
        historical_data = self.create_test_data(60)
        
        event = {
            'product_id': 'PROD-00001',
            'historical_data': historical_data,
            'horizon_days': 7
        }
        
        context = Mock()
        
        # Execute
        result = lambda_handler(event, context)
        body = json.loads(result['body'])
        
        # Check dates are sequential
        forecast_dates = [f['forecast_date'] for f in body['forecast_data']]
        assert len(forecast_dates) == 7
        
        # Verify dates are in order
        for i in range(len(forecast_dates) - 1):
            assert forecast_dates[i] < forecast_dates[i + 1]
    
    def test_confidence_intervals_ordering(self):
        """Test that confidence intervals are properly ordered (95% wider than 80%)"""
        historical_data = self.create_test_data(90)
        
        event = {
            'product_id': 'PROD-00001',
            'historical_data': historical_data,
            'horizon_days': 7
        }
        
        context = Mock()
        
        # Execute
        result = lambda_handler(event, context)
        body = json.loads(result['body'])
        
        # Check each forecast point
        for forecast_point in body['forecast_data']:
            predicted = forecast_point['predicted_demand']
            ci_80_lower = forecast_point['confidence_80_lower']
            ci_80_upper = forecast_point['confidence_80_upper']
            ci_95_lower = forecast_point['confidence_95_lower']
            ci_95_upper = forecast_point['confidence_95_upper']
            
            # 95% CI should be wider than 80% CI
            assert ci_95_lower <= ci_80_lower
            assert ci_95_upper >= ci_80_upper
            
            # Lower bounds should be less than predicted
            assert ci_80_lower <= predicted
            assert ci_95_lower <= predicted
            
            # Upper bounds should be greater than predicted
            assert ci_80_upper >= predicted
            assert ci_95_upper >= predicted
            
            # All values should be non-negative
            assert ci_80_lower >= 0
            assert ci_95_lower >= 0


class TestHoltWintersForecast:
    """Test suite for Holt-Winters exponential smoothing"""
    
    def test_holt_winters_basic(self):
        """Test basic Holt-Winters forecast"""
        data = [50, 52, 48, 55, 53, 49, 56] * 10  # Weekly pattern
        horizon = 7
        
        forecast = holt_winters_forecast(data, horizon)
        
        # Assertions
        assert len(forecast) == horizon
        assert all(f >= 0 for f in forecast)  # Non-negative
        assert all(isinstance(f, (int, float)) for f in forecast)
    
    def test_holt_winters_captures_trend(self):
        """Test that Holt-Winters captures upward trend"""
        data = [50 + i for i in range(60)]  # Clear upward trend
        horizon = 7
        
        forecast = holt_winters_forecast(data, horizon)
        
        # Forecast should continue upward trend
        assert forecast[-1] > forecast[0]
    
    def test_holt_winters_handles_seasonality(self):
        """Test that Holt-Winters handles seasonal patterns"""
        # Create data with weekly seasonality
        data = [50 + (i % 7) * 10 for i in range(70)]
        horizon = 7
        
        forecast = holt_winters_forecast(data, horizon)
        
        # Should produce reasonable forecasts
        assert len(forecast) == horizon
        assert all(f > 0 for f in forecast)
    
    def test_holt_winters_non_negative(self):
        """Test that Holt-Winters never produces negative forecasts"""
        data = [10, 8, 5, 3, 2, 1, 0.5] * 5  # Declining trend
        horizon = 7
        
        forecast = holt_winters_forecast(data, horizon)
        
        # All forecasts should be non-negative
        assert all(f >= 0 for f in forecast)


class TestARIMAForecast:
    """Test suite for ARIMA forecasting"""
    
    def test_arima_basic(self):
        """Test basic ARIMA forecast"""
        data = [50, 52, 48, 55, 53, 49, 56] * 10
        horizon = 7
        
        forecast = arima_forecast_simple(data, horizon)
        
        # Assertions
        assert len(forecast) == horizon
        assert all(f >= 0 for f in forecast)  # Non-negative
        assert all(isinstance(f, (int, float)) for f in forecast)
    
    def test_arima_stable_series(self):
        """Test ARIMA on stable time series"""
        data = [50] * 60  # Constant series
        horizon = 7
        
        forecast = arima_forecast_simple(data, horizon)
        
        # Forecast should be close to historical mean
        assert all(40 <= f <= 60 for f in forecast)
    
    def test_arima_trending_series(self):
        """Test ARIMA on trending time series"""
        data = [50 + i * 0.5 for i in range(60)]  # Upward trend
        horizon = 7
        
        forecast = arima_forecast_simple(data, horizon)
        
        # Should produce reasonable forecasts
        assert len(forecast) == horizon
        assert all(f > 0 for f in forecast)
    
    def test_arima_non_negative(self):
        """Test that ARIMA never produces negative forecasts"""
        data = [10, 8, 5, 3, 2, 1, 0.5] * 5
        horizon = 7
        
        forecast = arima_forecast_simple(data, horizon)
        
        # All forecasts should be non-negative
        assert all(f >= 0 for f in forecast)


class TestConfidenceIntervals:
    """Test suite for confidence interval calculation"""
    
    def test_confidence_intervals_basic(self):
        """Test basic confidence interval calculation"""
        historical = [50, 52, 48, 55, 53, 49, 56] * 10
        forecast = [54, 55, 56, 57, 58, 59, 60]
        
        lower_80, upper_80 = calculate_confidence_intervals(historical, forecast, 0.80)
        lower_95, upper_95 = calculate_confidence_intervals(historical, forecast, 0.95)
        
        # Assertions
        assert len(lower_80) == len(forecast)
        assert len(upper_80) == len(forecast)
        assert len(lower_95) == len(forecast)
        assert len(upper_95) == len(forecast)
        
        # 95% should be wider than 80%
        for i in range(len(forecast)):
            assert lower_95[i] <= lower_80[i]
            assert upper_95[i] >= upper_80[i]
    
    def test_confidence_intervals_contain_forecast(self):
        """Test that confidence intervals contain the forecast values"""
        historical = [50] * 60
        forecast = [52, 53, 54, 55, 56, 57, 58]
        
        lower_80, upper_80 = calculate_confidence_intervals(historical, forecast, 0.80)
        
        # Forecast should be within intervals
        for i in range(len(forecast)):
            assert lower_80[i] <= forecast[i] <= upper_80[i]
    
    def test_confidence_intervals_widen_with_horizon(self):
        """Test that confidence intervals widen as forecast horizon increases"""
        historical = [50, 52, 48, 55, 53, 49, 56] * 10
        forecast = [54] * 30
        
        lower_80, upper_80 = calculate_confidence_intervals(historical, forecast, 0.80)
        
        # Width should increase with horizon
        width_early = upper_80[0] - lower_80[0]
        width_late = upper_80[-1] - lower_80[-1]
        
        assert width_late > width_early
    
    def test_confidence_intervals_non_negative(self):
        """Test that confidence intervals never go negative"""
        historical = [10, 12, 8, 15, 13, 9, 16]
        forecast = [5, 4, 3, 2, 1, 0.5, 0.1]
        
        lower_80, upper_80 = calculate_confidence_intervals(historical, forecast, 0.80)
        
        # All lower bounds should be non-negative
        assert all(l >= 0 for l in lower_80)


class TestEnsembleForecasting:
    """Test suite for ensemble forecasting logic"""
    
    def test_ensemble_combines_models(self):
        """Test that ensemble properly combines HW and ARIMA forecasts"""
        from datetime import datetime, timedelta
        start_date = datetime(2023, 1, 1)
        historical_data = [
            {'order_date': (start_date + timedelta(days=i)).strftime('%Y-%m-%d'), 
             'quantity': 50 + (i % 7) * 5}
            for i in range(90)
        ]
        
        event = {
            'product_id': 'PROD-00001',
            'historical_data': historical_data,
            'horizon_days': 7
        }
        
        context = Mock()
        
        # Execute
        result = lambda_handler(event, context)
        body = json.loads(result['body'])
        
        # Check that model components are present and ensemble is average
        for forecast_point in body['forecast_data']:
            hw = forecast_point['model_components']['holt_winters']
            arima = forecast_point['model_components']['arima']
            predicted = forecast_point['predicted_demand']
            
            # Ensemble should be average of both models
            expected_ensemble = (hw + arima) / 2
            assert abs(predicted - expected_ensemble) < 0.01  # Allow small rounding error


class TestEdgeCases:
    """Test suite for edge cases and error conditions"""
    
    def test_zero_values_in_data(self):
        """Test handling of zero values in historical data"""
        from datetime import datetime, timedelta
        start_date = datetime(2023, 1, 1)
        historical_data = [
            {'order_date': (start_date + timedelta(days=i)).strftime('%Y-%m-%d'), 
             'quantity': 0 if i % 5 == 0 else 50}
            for i in range(30)
        ]
        
        event = {
            'product_id': 'PROD-00001',
            'historical_data': historical_data,
            'horizon_days': 7
        }
        
        context = Mock()
        
        # Should not crash
        result = lambda_handler(event, context)
        assert result['statusCode'] == 200
    
    def test_high_variance_data(self):
        """Test handling of high variance data"""
        from datetime import datetime, timedelta
        start_date = datetime(2023, 1, 1)
        historical_data = [
            {'order_date': (start_date + timedelta(days=i)).strftime('%Y-%m-%d'), 
             'quantity': 50 + np.random.randint(-40, 40)}
            for i in range(90)
        ]
        
        event = {
            'product_id': 'PROD-00001',
            'historical_data': historical_data,
            'horizon_days': 7
        }
        
        context = Mock()
        
        # Should handle high variance
        result = lambda_handler(event, context)
        assert result['statusCode'] == 200
        
        body = json.loads(result['body'])
        # Confidence intervals should be wider for high variance
        first_point = body['forecast_data'][0]
        ci_width = first_point['confidence_95_upper'] - first_point['confidence_95_lower']
        assert ci_width > 0


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '--tb=short'])
