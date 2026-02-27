"""
Unit Tests for Forecasting Agent

This module contains unit tests to verify the forecasting logic implementation.

Testing Framework: pytest
Requirements: 3.3 - Generate forecasts using historical data and time series models
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import pandas as pd
import numpy as np
from hypothesis import given, strategies as st, settings

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))
from lambda_function import (
    get_historical_sales_data,
    generate_holtwinters_forecast,
    generate_arima_forecast,
    ensemble_forecasts,
    store_forecast,
    generate_forecast_for_product
)


class TestHistoricalDataRetrieval:
    """Test historical sales data retrieval"""
    
    def test_get_historical_sales_data_with_data(self):
        """Test retrieving historical sales data when data exists"""
        # Mock connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock query results
        mock_cursor.description = [('order_date',), ('quantity',)]
        mock_cursor.fetchall.return_value = [
            (datetime.now().date() - timedelta(days=i), 10 + i)
            for i in range(100)
        ]
        
        # Execute
        result = get_historical_sales_data(mock_conn, 'PROD-001')
        
        # Verify
        assert result is not None
        assert len(result) == 100
        assert 'order_date' in result.columns
        assert 'quantity' in result.columns
        mock_cursor.execute.assert_called_once()
    
    def test_get_historical_sales_data_no_data(self):
        """Test retrieving historical sales data when no data exists"""
        # Mock connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock empty results
        mock_cursor.description = [('order_date',), ('quantity',)]
        mock_cursor.fetchall.return_value = []
        
        # Execute
        result = get_historical_sales_data(mock_conn, 'PROD-999')
        
        # Verify
        assert result is None


class TestHoltWintersForecast:
    """Test Holt-Winters exponential smoothing forecasting"""
    
    def test_holtwinters_with_sufficient_data(self):
        """Test Holt-Winters forecast with sufficient historical data"""
        # Create synthetic time series data with trend and seasonality
        dates = pd.date_range(start='2023-01-01', periods=180, freq='D')
        # Create data with weekly seasonality
        values = [100 + i * 0.5 + 20 * np.sin(2 * np.pi * i / 7) for i in range(180)]
        ts_data = pd.Series(values, index=dates)
        
        # Generate forecast
        forecast, intervals = generate_holtwinters_forecast(ts_data, horizon=7)
        
        # Verify
        assert forecast >= 0, "Forecast should be non-negative"
        assert isinstance(forecast, int), "Forecast should be an integer"
        assert '80' in intervals, "Should have 80% confidence interval"
        assert '95' in intervals, "Should have 95% confidence interval"
        assert intervals['80']['lower'] <= forecast <= intervals['80']['upper']
        assert intervals['95']['lower'] <= forecast <= intervals['95']['upper']
        assert intervals['80']['lower'] >= 0, "Lower bound should be non-negative"
    
    def test_holtwinters_with_minimal_data(self):
        """Test Holt-Winters forecast with minimal data (fallback to simple method)"""
        # Create minimal time series data
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        values = [50 + i for i in range(10)]
        ts_data = pd.Series(values, index=dates)
        
        # Generate forecast (should use fallback)
        forecast, intervals = generate_holtwinters_forecast(ts_data, horizon=7)
        
        # Verify
        assert forecast >= 0
        assert isinstance(forecast, int)
        assert '80' in intervals
        assert '95' in intervals


class TestARIMAForecast:
    """Test ARIMA forecasting"""
    
    def test_arima_with_sufficient_data(self):
        """Test ARIMA forecast with sufficient historical data"""
        # Create synthetic time series data with trend
        dates = pd.date_range(start='2023-01-01', periods=180, freq='D')
        values = [100 + i * 0.3 + np.random.normal(0, 5) for i in range(180)]
        ts_data = pd.Series(values, index=dates)
        
        # Generate forecast
        forecast, intervals = generate_arima_forecast(ts_data, horizon=7)
        
        # Verify
        assert forecast >= 0, "Forecast should be non-negative"
        assert isinstance(forecast, int), "Forecast should be an integer"
        assert '80' in intervals, "Should have 80% confidence interval"
        assert '95' in intervals, "Should have 95% confidence interval"
        assert intervals['80']['lower'] <= forecast <= intervals['80']['upper']
        assert intervals['95']['lower'] <= forecast <= intervals['95']['upper']
        assert intervals['80']['lower'] >= 0, "Lower bound should be non-negative"
    
    def test_arima_confidence_intervals_nested(self):
        """Test that 95% CI is wider than 80% CI"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        values = [100 + i * 0.5 for i in range(100)]
        ts_data = pd.Series(values, index=dates)
        
        forecast, intervals = generate_arima_forecast(ts_data, horizon=7)
        
        # 95% CI should be wider than 80% CI
        assert intervals['95']['lower'] <= intervals['80']['lower']
        assert intervals['95']['upper'] >= intervals['80']['upper']


class TestEnsembleForecasts:
    """Test ensemble forecasting logic"""
    
    def test_ensemble_simple_average(self):
        """Test that ensemble is the average of two forecasts"""
        hw_forecast = 100
        arima_forecast = 120
        
        ensemble = ensemble_forecasts(hw_forecast, arima_forecast)
        
        assert ensemble == 110, "Ensemble should be average of two forecasts"
    
    def test_ensemble_with_equal_forecasts(self):
        """Test ensemble when both models agree"""
        hw_forecast = 100
        arima_forecast = 100
        
        ensemble = ensemble_forecasts(hw_forecast, arima_forecast)
        
        assert ensemble == 100
    
    def test_ensemble_returns_integer(self):
        """Test that ensemble returns an integer"""
        hw_forecast = 101
        arima_forecast = 100
        
        ensemble = ensemble_forecasts(hw_forecast, arima_forecast)
        
        assert isinstance(ensemble, int)


class TestStoreForecast:
    """Test forecast storage in Redshift"""
    
    def test_store_forecast_creates_records(self):
        """Test that store_forecast creates records for both confidence levels"""
        # Mock connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Execute
        forecast_id = store_forecast(
            conn=mock_conn,
            product_id='PROD-001',
            horizon=7,
            forecast=150,
            intervals_80={'lower': 130, 'upper': 170},
            intervals_95={'lower': 120, 'upper': 180}
        )
        
        # Verify
        assert forecast_id.startswith('FC-')
        assert mock_cursor.execute.call_count == 2  # Two inserts (80% and 95%)
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
    
    def test_store_forecast_with_multiple_horizons(self):
        """Test storing forecasts for different horizons"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Store 7-day forecast
        forecast_id_7 = store_forecast(
            conn=mock_conn,
            product_id='PROD-001',
            horizon=7,
            forecast=150,
            intervals_80={'lower': 130, 'upper': 170},
            intervals_95={'lower': 120, 'upper': 180}
        )
        
        # Store 30-day forecast
        forecast_id_30 = store_forecast(
            conn=mock_conn,
            product_id='PROD-001',
            horizon=30,
            forecast=600,
            intervals_80={'lower': 550, 'upper': 650},
            intervals_95={'lower': 500, 'upper': 700}
        )
        
        # Verify different IDs
        assert forecast_id_7 != forecast_id_30


class TestGenerateForecastForProduct:
    """Test end-to-end forecast generation for a product"""
    
    @patch('lambda_function.get_historical_sales_data')
    @patch('lambda_function.store_forecast')
    def test_generate_forecast_with_sufficient_data(self, mock_store, mock_get_data):
        """Test forecast generation with sufficient historical data"""
        # Mock historical data
        dates = pd.date_range(start='2023-01-01', periods=180, freq='D')
        mock_df = pd.DataFrame({
            'order_date': dates,
            'quantity': [100 + i * 0.5 for i in range(180)]
        })
        mock_get_data.return_value = mock_df
        
        # Mock store_forecast to return IDs
        mock_store.side_effect = lambda **kwargs: f"FC-{kwargs['horizon']}"
        
        # Mock connection
        mock_conn = Mock()
        
        # Set environment variable for horizons
        os.environ['FORECAST_HORIZONS'] = '7,30'
        
        # Execute
        product = {'product_id': 'PROD-001', 'sku': 'SKU-001'}
        result = generate_forecast_for_product(mock_conn, product)
        
        # Verify
        assert result is not None
        assert result['product_id'] == 'PROD-001'
        assert 'forecasts' in result
        assert len(result['forecasts']) == 2  # 7-day and 30-day
        assert mock_store.call_count == 2
    
    @patch('lambda_function.get_historical_sales_data')
    def test_generate_forecast_insufficient_data(self, mock_get_data):
        """Test forecast generation with insufficient historical data"""
        # Mock insufficient data (less than 90 days)
        dates = pd.date_range(start='2023-01-01', periods=50, freq='D')
        mock_df = pd.DataFrame({
            'order_date': dates,
            'quantity': [100 for _ in range(50)]
        })
        mock_get_data.return_value = mock_df
        
        # Mock connection
        mock_conn = Mock()
        
        # Execute
        product = {'product_id': 'PROD-001', 'sku': 'SKU-001'}
        result = generate_forecast_for_product(mock_conn, product)
        
        # Verify
        assert result is None
    
    @patch('lambda_function.get_historical_sales_data')
    def test_generate_forecast_no_data(self, mock_get_data):
        """Test forecast generation with no historical data"""
        # Mock no data
        mock_get_data.return_value = None
        
        # Mock connection
        mock_conn = Mock()
        
        # Execute
        product = {'product_id': 'PROD-999', 'sku': 'SKU-999'}
        result = generate_forecast_for_product(mock_conn, product)
        
        # Verify
        assert result is None


class TestForecastEdgeCases:
    """Test edge cases in forecasting"""
    
    def test_holtwinters_with_zero_values(self):
        """Test Holt-Winters with time series containing zeros"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        values = [0 if i % 10 == 0 else 50 for i in range(100)]
        ts_data = pd.Series(values, index=dates)
        
        forecast, intervals = generate_holtwinters_forecast(ts_data, horizon=7)
        
        assert forecast >= 0
        assert intervals['80']['lower'] >= 0
    
    def test_arima_with_constant_values(self):
        """Test ARIMA with constant time series"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        values = [100 for _ in range(100)]
        ts_data = pd.Series(values, index=dates)
        
        forecast, intervals = generate_arima_forecast(ts_data, horizon=7)
        
        # With constant values, forecast should be close to the constant
        assert 600 <= forecast <= 800  # 7 days * ~100 per day
    
    def test_ensemble_with_large_difference(self):
        """Test ensemble when models disagree significantly"""
        hw_forecast = 50
        arima_forecast = 150
        
        ensemble = ensemble_forecasts(hw_forecast, arima_forecast)
        
        # Should be the average
        assert ensemble == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestForecastingProperties:
    """Property-based tests for forecasting agent correctness properties"""
    
    # Feature: supply-chain-ai-platform, Property 9: Forecast uses historical data
    @settings(max_examples=20, deadline=None)
    @given(
        num_days=st.integers(min_value=90, max_value=365),
        base_demand=st.integers(min_value=10, max_value=500),
        horizon=st.sampled_from([7, 30])
    )
    @patch('lambda_function.store_forecast')
    def test_property_forecast_uses_historical_data(self, mock_store, num_days, base_demand, horizon):
        """
        **Validates: Requirements 3.3**
        
        Property 9: Forecast uses historical data
        For any forecast generation, the forecasting algorithm should receive and 
        process at least 90 days of historical sales data for the SKU.
        
        This test verifies that:
        1. The forecast generation function queries historical data
        2. At least 90 days of data is required for forecast generation
        3. The forecasting algorithm processes the historical data
        """
        # Mock store_forecast to track calls
        mock_store.return_value = f"FC-test-{horizon}"
        
        # Create historical sales data with at least 90 days
        dates = pd.date_range(
            start=datetime.now() - timedelta(days=num_days),
            periods=num_days,
            freq='D'
        )
        
        # Generate realistic demand data with some variation
        quantities = [
            max(0, int(base_demand + np.random.normal(0, base_demand * 0.2)))
            for _ in range(num_days)
        ]
        
        historical_data = pd.DataFrame({
            'order_date': dates,
            'quantity': quantities
        })
        
        # Mock connection
        mock_conn = Mock()
        
        # Set environment variable for horizon
        os.environ['FORECAST_HORIZONS'] = str(horizon)
        
        # Mock get_historical_sales_data to return our test data
        with patch('lambda_function.get_historical_sales_data') as mock_get_data:
            mock_get_data.return_value = historical_data
            
            # Execute forecast generation
            product = {
                'product_id': f'PROD-TEST-{num_days}',
                'sku': f'SKU-TEST-{num_days}'
            }
            result = generate_forecast_for_product(mock_conn, product)
            
            # Verify that historical data was queried
            mock_get_data.assert_called_once_with(mock_conn, product['product_id'])
            
            # Verify that forecast was generated (not None)
            assert result is not None, \
                f"Forecast should be generated when {num_days} days of historical data is available"
            
            # Verify that the forecast result contains expected structure
            assert 'product_id' in result
            assert result['product_id'] == product['product_id']
            assert 'forecasts' in result
            assert len(result['forecasts']) > 0
            
            # Verify that store_forecast was called (meaning data was processed)
            assert mock_store.called, \
                "Forecast should be stored, indicating historical data was processed"
            
            # Verify the forecast was generated using the historical data
            # by checking that store_forecast received reasonable values
            store_call_args = mock_store.call_args_list[0][1]
            assert store_call_args['product_id'] == product['product_id']
            assert store_call_args['horizon'] == horizon
            assert store_call_args['forecast'] >= 0, \
                "Forecast value should be non-negative"
    
    @settings(max_examples=10, deadline=None)
    @given(
        num_days=st.integers(min_value=1, max_value=89),
        base_demand=st.integers(min_value=10, max_value=500)
    )
    def test_property_insufficient_historical_data_rejected(self, num_days, base_demand):
        """
        **Validates: Requirements 3.3**
        
        Property 9 (negative case): Forecast requires at least 90 days
        For any forecast generation with less than 90 days of historical data,
        the forecast should not be generated (returns None).
        
        This test verifies that the 90-day minimum is enforced.
        """
        # Create historical sales data with less than 90 days
        dates = pd.date_range(
            start=datetime.now() - timedelta(days=num_days),
            periods=num_days,
            freq='D'
        )
        
        quantities = [
            max(0, int(base_demand + np.random.normal(0, base_demand * 0.2)))
            for _ in range(num_days)
        ]
        
        historical_data = pd.DataFrame({
            'order_date': dates,
            'quantity': quantities
        })
        
        # Mock connection
        mock_conn = Mock()
        
        # Mock get_historical_sales_data to return insufficient data
        with patch('lambda_function.get_historical_sales_data') as mock_get_data:
            mock_get_data.return_value = historical_data
            
            # Execute forecast generation
            product = {
                'product_id': f'PROD-INSUFFICIENT-{num_days}',
                'sku': f'SKU-INSUFFICIENT-{num_days}'
            }
            result = generate_forecast_for_product(mock_conn, product)
            
            # Verify that forecast was NOT generated due to insufficient data
            assert result is None, \
                f"Forecast should not be generated with only {num_days} days of data (minimum 90 required)"
    
    @settings(max_examples=10, deadline=None)
    @given(
        num_days=st.integers(min_value=90, max_value=365),
        base_demand=st.integers(min_value=10, max_value=500)
    )
    @patch('lambda_function.store_forecast')
    def test_property_historical_data_influences_forecast(self, mock_store, num_days, base_demand):
        """
        **Validates: Requirements 3.3**
        
        Property 9 (data usage verification): Historical data influences forecast
        For any forecast generation, the forecast value should be influenced by
        the historical sales data patterns.
        
        This test verifies that the forecast is actually using the historical data
        by checking that forecasts differ based on different historical patterns.
        """
        mock_store.return_value = "FC-test"
        
        # Create two different historical patterns
        dates = pd.date_range(
            start=datetime.now() - timedelta(days=num_days),
            periods=num_days,
            freq='D'
        )
        
        # Pattern 1: Low demand
        low_demand_data = pd.DataFrame({
            'order_date': dates,
            'quantity': [base_demand // 2 for _ in range(num_days)]
        })
        
        # Pattern 2: High demand
        high_demand_data = pd.DataFrame({
            'order_date': dates,
            'quantity': [base_demand * 2 for _ in range(num_days)]
        })
        
        mock_conn = Mock()
        os.environ['FORECAST_HORIZONS'] = '7'
        
        # Generate forecast with low demand data
        with patch('lambda_function.get_historical_sales_data') as mock_get_data:
            mock_get_data.return_value = low_demand_data
            
            product = {'product_id': 'PROD-LOW', 'sku': 'SKU-LOW'}
            result_low = generate_forecast_for_product(mock_conn, product)
            
            assert result_low is not None
            forecast_low = result_low['forecasts'][0]['predicted_demand']
        
        # Reset mock
        mock_store.reset_mock()
        
        # Generate forecast with high demand data
        with patch('lambda_function.get_historical_sales_data') as mock_get_data:
            mock_get_data.return_value = high_demand_data
            
            product = {'product_id': 'PROD-HIGH', 'sku': 'SKU-HIGH'}
            result_high = generate_forecast_for_product(mock_conn, product)
            
            assert result_high is not None
            forecast_high = result_high['forecasts'][0]['predicted_demand']
        
        # Verify that forecasts differ based on historical data
        # High demand history should produce higher forecast
        assert forecast_high > forecast_low, \
            "Forecast should be influenced by historical data patterns: " \
            f"high demand ({forecast_high}) should exceed low demand ({forecast_low})"
    
    # Feature: supply-chain-ai-platform, Property 10: Confidence interval presence
    @settings(max_examples=20, deadline=None)
    @given(
        num_days=st.integers(min_value=90, max_value=365),
        base_demand=st.integers(min_value=10, max_value=500),
        horizon=st.sampled_from([7, 30])
    )
    @patch('lambda_function.store_forecast')
    def test_property_confidence_interval_presence(self, mock_store, num_days, base_demand, horizon):
        """
        **Validates: Requirements 3.4**
        
        Property 10: Confidence interval presence
        For any demand forecast, the forecast record should include confidence 
        intervals at both 80% and 95% levels.
        
        This test verifies that:
        1. Every forecast includes 80% confidence intervals (lower and upper bounds)
        2. Every forecast includes 95% confidence intervals (lower and upper bounds)
        3. The confidence intervals are stored in the database
        4. The 95% CI is wider than the 80% CI (mathematical property)
        """
        # Track store_forecast calls to verify confidence intervals
        stored_forecasts = []
        
        def capture_store_call(**kwargs):
            stored_forecasts.append(kwargs)
            return f"FC-test-{kwargs['horizon']}"
        
        mock_store.side_effect = capture_store_call
        
        # Create historical sales data with sufficient days
        dates = pd.date_range(
            start=datetime.now() - timedelta(days=num_days),
            periods=num_days,
            freq='D'
        )
        
        # Generate realistic demand data with variation
        quantities = [
            max(0, int(base_demand + np.random.normal(0, base_demand * 0.2)))
            for _ in range(num_days)
        ]
        
        historical_data = pd.DataFrame({
            'order_date': dates,
            'quantity': quantities
        })
        
        # Mock connection
        mock_conn = Mock()
        
        # Set environment variable for horizon
        os.environ['FORECAST_HORIZONS'] = str(horizon)
        
        # Mock get_historical_sales_data to return our test data
        with patch('lambda_function.get_historical_sales_data') as mock_get_data:
            mock_get_data.return_value = historical_data
            
            # Execute forecast generation
            product = {
                'product_id': f'PROD-CI-TEST-{num_days}',
                'sku': f'SKU-CI-TEST-{num_days}'
            }
            result = generate_forecast_for_product(mock_conn, product)
            
            # Verify that forecast was generated
            assert result is not None, \
                f"Forecast should be generated with {num_days} days of historical data"
            
            # Verify that store_forecast was called
            assert len(stored_forecasts) > 0, \
                "store_forecast should be called to persist forecast data"
            
            # Verify confidence intervals for each stored forecast
            for stored_forecast in stored_forecasts:
                # Check that 80% confidence interval is present
                assert 'intervals_80' in stored_forecast, \
                    "Forecast must include 80% confidence interval"
                
                intervals_80 = stored_forecast['intervals_80']
                assert 'lower' in intervals_80, \
                    "80% confidence interval must have lower bound"
                assert 'upper' in intervals_80, \
                    "80% confidence interval must have upper bound"
                
                # Check that 95% confidence interval is present
                assert 'intervals_95' in stored_forecast, \
                    "Forecast must include 95% confidence interval"
                
                intervals_95 = stored_forecast['intervals_95']
                assert 'lower' in intervals_95, \
                    "95% confidence interval must have lower bound"
                assert 'upper' in intervals_95, \
                    "95% confidence interval must have upper bound"
                
                # Verify confidence interval values are non-negative
                assert intervals_80['lower'] >= 0, \
                    "80% CI lower bound must be non-negative"
                assert intervals_80['upper'] >= 0, \
                    "80% CI upper bound must be non-negative"
                assert intervals_95['lower'] >= 0, \
                    "95% CI lower bound must be non-negative"
                assert intervals_95['upper'] >= 0, \
                    "95% CI upper bound must be non-negative"
                
                # Verify confidence interval ordering (lower <= upper)
                assert intervals_80['lower'] <= intervals_80['upper'], \
                    f"80% CI lower bound ({intervals_80['lower']}) must be <= upper bound ({intervals_80['upper']})"
                assert intervals_95['lower'] <= intervals_95['upper'], \
                    f"95% CI lower bound ({intervals_95['lower']}) must be <= upper bound ({intervals_95['upper']})"
                
                # Verify mathematical property: 95% CI should be wider than 80% CI
                # (95% CI has lower lower-bound and higher upper-bound)
                assert intervals_95['lower'] <= intervals_80['lower'], \
                    f"95% CI lower bound ({intervals_95['lower']}) should be <= 80% CI lower bound ({intervals_80['lower']})"
                assert intervals_95['upper'] >= intervals_80['upper'], \
                    f"95% CI upper bound ({intervals_95['upper']}) should be >= 80% CI upper bound ({intervals_80['upper']})"
                
                # Verify forecast value is within confidence intervals
                forecast_value = stored_forecast['forecast']
                assert intervals_80['lower'] <= forecast_value <= intervals_80['upper'], \
                    f"Forecast value ({forecast_value}) should be within 80% CI [{intervals_80['lower']}, {intervals_80['upper']}]"
                assert intervals_95['lower'] <= forecast_value <= intervals_95['upper'], \
                    f"Forecast value ({forecast_value}) should be within 95% CI [{intervals_95['lower']}, {intervals_95['upper']}]"
