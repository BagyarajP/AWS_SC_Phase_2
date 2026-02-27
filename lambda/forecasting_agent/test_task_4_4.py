"""
Integration Test for Task 4.4: Generate forecasts for multiple horizons

This test verifies that the forecasting agent correctly:
1. Generates 7-day and 30-day forecasts
2. Calculates confidence intervals at 80% and 95% levels
3. Stores all forecast data in the database

Requirements: 3.4, 3.5
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))
from lambda_function import generate_forecast_for_product, store_forecast


class TestTask44MultiHorizonForecasts:
    """Test task 4.4: Generate forecasts for multiple horizons"""
    
    @patch('lambda_function.store_forecast')
    @patch('lambda_function.get_historical_sales_data')
    def test_generates_both_7_and_30_day_forecasts(self, mock_get_data, mock_store):
        """
        Verify that forecasts are generated for both 7-day and 30-day horizons
        
        Requirements: 3.5 - THE Forecasting_Agent SHALL support forecast horizons 
        of 7 days and 30 days
        """
        # Setup: Create 180 days of historical data
        dates = pd.date_range(start='2023-01-01', periods=180, freq='D')
        historical_data = pd.DataFrame({
            'order_date': dates,
            'quantity': [100 + i * 0.5 + 20 * np.sin(2 * np.pi * i / 7) for i in range(180)]
        })
        mock_get_data.return_value = historical_data
        
        # Mock store_forecast to track calls
        mock_store.side_effect = lambda **kwargs: f"FC-{kwargs['horizon']}"
        
        # Mock connection
        mock_conn = Mock()
        
        # Set environment variable for both horizons
        os.environ['FORECAST_HORIZONS'] = '7,30'
        
        # Execute
        product = {'product_id': 'PROD-TEST-001', 'sku': 'SKU-TEST-001'}
        result = generate_forecast_for_product(mock_conn, product)
        
        # Verify
        assert result is not None, "Forecast generation should succeed"
        assert 'forecasts' in result, "Result should contain forecasts"
        assert len(result['forecasts']) == 2, "Should generate forecasts for 2 horizons"
        
        # Verify horizons
        horizons = [f['horizon'] for f in result['forecasts']]
        assert 7 in horizons, "Should include 7-day forecast"
        assert 30 in horizons, "Should include 30-day forecast"
        
        # Verify store_forecast was called twice (once for each horizon)
        assert mock_store.call_count == 2, "Should store forecasts for both horizons"
        
        print("✓ Successfully generated forecasts for both 7-day and 30-day horizons")
    
    @patch('lambda_function.store_forecast')
    @patch('lambda_function.get_historical_sales_data')
    def test_calculates_80_and_95_percent_confidence_intervals(self, mock_get_data, mock_store):
        """
        Verify that confidence intervals are calculated at both 80% and 95% levels
        
        Requirements: 3.4 - THE Forecasting_Agent SHALL provide forecast confidence 
        intervals at 80% and 95% levels
        """
        # Setup: Create historical data
        dates = pd.date_range(start='2023-01-01', periods=180, freq='D')
        historical_data = pd.DataFrame({
            'order_date': dates,
            'quantity': [100 + i * 0.3 for i in range(180)]
        })
        mock_get_data.return_value = historical_data
        
        # Track store_forecast calls
        stored_forecasts = []
        def capture_store_call(**kwargs):
            stored_forecasts.append(kwargs)
            return f"FC-{kwargs['horizon']}"
        
        mock_store.side_effect = capture_store_call
        
        # Mock connection
        mock_conn = Mock()
        
        # Set environment variable for one horizon (to simplify verification)
        os.environ['FORECAST_HORIZONS'] = '7'
        
        # Execute
        product = {'product_id': 'PROD-TEST-002', 'sku': 'SKU-TEST-002'}
        result = generate_forecast_for_product(mock_conn, product)
        
        # Verify
        assert result is not None, "Forecast generation should succeed"
        assert len(stored_forecasts) == 1, "Should store forecast for one horizon"
        
        # Verify the stored forecast has both confidence intervals
        stored = stored_forecasts[0]
        
        # Check 80% confidence interval
        assert 'intervals_80' in stored, "Should include 80% confidence interval"
        assert 'lower' in stored['intervals_80'], "80% CI should have lower bound"
        assert 'upper' in stored['intervals_80'], "80% CI should have upper bound"
        assert stored['intervals_80']['lower'] >= 0, "Lower bound should be non-negative"
        assert stored['intervals_80']['upper'] > stored['intervals_80']['lower'], \
            "Upper bound should be greater than lower bound"
        
        # Check 95% confidence interval
        assert 'intervals_95' in stored, "Should include 95% confidence interval"
        assert 'lower' in stored['intervals_95'], "95% CI should have lower bound"
        assert 'upper' in stored['intervals_95'], "95% CI should have upper bound"
        assert stored['intervals_95']['lower'] >= 0, "Lower bound should be non-negative"
        assert stored['intervals_95']['upper'] > stored['intervals_95']['lower'], \
            "Upper bound should be greater than lower bound"
        
        # Verify 95% CI is wider than 80% CI
        assert stored['intervals_95']['lower'] <= stored['intervals_80']['lower'], \
            "95% CI lower bound should be <= 80% CI lower bound"
        assert stored['intervals_95']['upper'] >= stored['intervals_80']['upper'], \
            "95% CI upper bound should be >= 80% CI upper bound"
        
        print("✓ Successfully calculated confidence intervals at 80% and 95% levels")
        print(f"  80% CI: [{stored['intervals_80']['lower']}, {stored['intervals_80']['upper']}]")
        print(f"  95% CI: [{stored['intervals_95']['lower']}, {stored['intervals_95']['upper']}]")
    
    def test_store_forecast_creates_records_for_both_confidence_levels(self):
        """
        Verify that store_forecast creates separate records for 80% and 95% confidence levels
        
        Requirements: 3.4 - Store confidence intervals at both levels
        """
        # Mock connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Execute
        forecast_id = store_forecast(
            conn=mock_conn,
            product_id='PROD-TEST-003',
            horizon=7,
            forecast=150,
            intervals_80={'lower': 130, 'upper': 170},
            intervals_95={'lower': 120, 'upper': 180}
        )
        
        # Verify
        assert forecast_id.startswith('FC-'), "Should generate forecast ID"
        
        # Verify two INSERT statements were executed (one for each confidence level)
        assert mock_cursor.execute.call_count == 2, \
            "Should execute 2 INSERT statements (one for 80%, one for 95%)"
        
        # Verify the calls
        calls = mock_cursor.execute.call_args_list
        
        # First call should be for 80% confidence level
        first_call_args = calls[0][0]
        first_call_str = str(first_call_args)
        assert '0.8' in first_call_str or 0.8 in first_call_args or 0.80 in first_call_args, \
            "First insert should be for 80% confidence level"
        
        # Second call should be for 95% confidence level
        second_call_args = calls[1][0]
        second_call_str = str(second_call_args)
        assert '0.95' in second_call_str or 0.95 in second_call_args, \
            "Second insert should be for 95% confidence level"
        
        # Verify commit was called
        mock_conn.commit.assert_called_once()
        
        print("✓ Successfully created database records for both confidence levels")
    
    @patch('lambda_function.store_forecast')
    @patch('lambda_function.get_historical_sales_data')
    def test_forecast_values_differ_by_horizon(self, mock_get_data, mock_store):
        """
        Verify that 30-day forecasts are different from 7-day forecasts
        (typically higher due to longer time period)
        """
        # Setup: Create historical data with consistent demand
        dates = pd.date_range(start='2023-01-01', periods=180, freq='D')
        historical_data = pd.DataFrame({
            'order_date': dates,
            'quantity': [100 for _ in range(180)]  # Constant demand
        })
        mock_get_data.return_value = historical_data
        
        # Track store_forecast calls
        stored_forecasts = []
        def capture_store_call(**kwargs):
            stored_forecasts.append(kwargs)
            return f"FC-{kwargs['horizon']}"
        
        mock_store.side_effect = capture_store_call
        
        # Mock connection
        mock_conn = Mock()
        
        # Set environment variable for both horizons
        os.environ['FORECAST_HORIZONS'] = '7,30'
        
        # Execute
        product = {'product_id': 'PROD-TEST-004', 'sku': 'SKU-TEST-004'}
        result = generate_forecast_for_product(mock_conn, product)
        
        # Verify
        assert result is not None
        assert len(stored_forecasts) == 2
        
        # Get forecasts for each horizon
        forecast_7day = next(f for f in stored_forecasts if f['horizon'] == 7)
        forecast_30day = next(f for f in stored_forecasts if f['horizon'] == 30)
        
        # With constant demand of 100/day, 30-day forecast should be roughly 4x the 7-day forecast
        # (allowing for some variation due to model behavior)
        ratio = forecast_30day['forecast'] / forecast_7day['forecast']
        assert 3.0 <= ratio <= 5.0, \
            f"30-day forecast should be roughly 4x the 7-day forecast (ratio: {ratio:.2f})"
        
        print(f"✓ Forecasts correctly differ by horizon:")
        print(f"  7-day forecast: {forecast_7day['forecast']}")
        print(f"  30-day forecast: {forecast_30day['forecast']}")
        print(f"  Ratio: {ratio:.2f}x")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
