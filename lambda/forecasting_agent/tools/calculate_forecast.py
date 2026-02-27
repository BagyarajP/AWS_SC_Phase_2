"""
Lambda Tool: calculate_forecast

This tool generates demand forecasts using ensemble of Holt-Winters exponential
smoothing and ARIMA models. It calculates confidence intervals at 80% and 95%
levels and supports 7-day and 30-day forecast horizons.

Requirements: 3.3, 3.4, 3.5
"""

import os
import json
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
import numpy as np

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for calculate_forecast tool
    
    This function is invoked by Bedrock Agent to generate demand forecasts
    using ensemble of Holt-Winters and ARIMA models.
    
    Args:
        event: Input from Bedrock Agent with parameters:
            - product_id (required): Product identifier
            - historical_data (required): Time series data as list of dicts with 'order_date' and 'quantity'
            - horizon_days (required): Forecast horizon (7 or 30 days)
        context: Lambda context object
        
    Returns:
        dict: Response with forecast values and confidence intervals
    """
    logger.info(f"calculate_forecast invoked with event keys: {list(event.keys())}")
    
    try:
        # Extract parameters from event
        if 'parameters' in event:
            # Direct Bedrock Agent invocation
            params = event['parameters']
            if isinstance(params, list):
                # Convert list of parameter objects to dict
                params = {p['name']: p['value'] for p in params}
        elif 'product_id' in event:
            # Direct Lambda invocation (for testing)
            params = event
        else:
            raise ValueError("Missing required parameters")
        
        product_id = params.get('product_id')
        historical_data = params.get('historical_data')
        horizon_days = int(params.get('horizon_days', 7))
        
        # Validate parameters
        if not product_id:
            raise ValueError("Missing required parameter: product_id")
        if not historical_data:
            raise ValueError("Missing required parameter: historical_data")
        if horizon_days not in [7, 30]:
            raise ValueError(f"Invalid horizon_days: {horizon_days}. Must be 7 or 30")
        
        # Parse historical data if it's a JSON string
        if isinstance(historical_data, str):
            historical_data = json.loads(historical_data)
        
        logger.info(f"Generating {horizon_days}-day forecast for product: {product_id}")
        logger.info(f"Historical data points: {len(historical_data)}")
        
        # Validate minimum data requirements
        if len(historical_data) < 14:
            raise ValueError(f"Insufficient historical data. Need at least 14 days, got {len(historical_data)}")
        
        # Extract time series values
        quantities = [float(d['quantity']) for d in historical_data]
        
        # Generate forecasts using both models
        hw_forecast = holt_winters_forecast(quantities, horizon_days)
        arima_forecast = arima_forecast_simple(quantities, horizon_days)
        
        # Ensemble: average of both models
        ensemble_forecast = [(hw + ar) / 2 for hw, ar in zip(hw_forecast, arima_forecast)]
        
        # Calculate confidence intervals
        ci_80_lower, ci_80_upper = calculate_confidence_intervals(
            quantities, ensemble_forecast, confidence_level=0.80
        )
        ci_95_lower, ci_95_upper = calculate_confidence_intervals(
            quantities, ensemble_forecast, confidence_level=0.95
        )
        
        # Generate forecast dates
        last_date = datetime.strptime(historical_data[-1]['order_date'], '%Y-%m-%d')
        forecast_dates = [(last_date + timedelta(days=i+1)).strftime('%Y-%m-%d') 
                         for i in range(horizon_days)]
        
        # Format response
        forecast_data = []
        for i in range(horizon_days):
            forecast_data.append({
                'forecast_date': forecast_dates[i],
                'predicted_demand': round(ensemble_forecast[i], 2),
                'confidence_80_lower': round(ci_80_lower[i], 2),
                'confidence_80_upper': round(ci_80_upper[i], 2),
                'confidence_95_lower': round(ci_95_lower[i], 2),
                'confidence_95_upper': round(ci_95_upper[i], 2),
                'model_components': {
                    'holt_winters': round(hw_forecast[i], 2),
                    'arima': round(arima_forecast[i], 2)
                }
            })
        
        response = {
            'product_id': product_id,
            'horizon_days': horizon_days,
            'forecast_generated_at': datetime.now().isoformat(),
            'forecast_data': forecast_data,
            'summary': {
                'total_predicted_demand': round(sum(ensemble_forecast), 2),
                'average_daily_demand': round(sum(ensemble_forecast) / horizon_days, 2),
                'historical_average': round(sum(quantities) / len(quantities), 2)
            }
        }
        
        logger.info(f"Successfully generated {horizon_days}-day forecast for {product_id}")
        logger.info(f"Total predicted demand: {response['summary']['total_predicted_demand']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
        
    except Exception as e:
        logger.error(f"Error in calculate_forecast: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to generate forecast'
            })
        }


def holt_winters_forecast(data: List[float], horizon: int) -> List[float]:
    """
    Generate forecast using Holt-Winters exponential smoothing
    
    This implementation uses triple exponential smoothing with additive seasonality.
    
    Args:
        data: Historical time series data
        horizon: Number of periods to forecast
        
    Returns:
        List of forecasted values
    """
    try:
        # Holt-Winters parameters
        alpha = 0.3  # Level smoothing
        beta = 0.1   # Trend smoothing
        gamma = 0.2  # Seasonality smoothing
        season_length = 7  # Weekly seasonality
        
        n = len(data)
        
        # Initialize components
        level = np.mean(data[:season_length])
        trend = (np.mean(data[season_length:2*season_length]) - np.mean(data[:season_length])) / season_length
        
        # Initialize seasonal components
        seasonal = []
        for i in range(season_length):
            seasonal.append(data[i] - level)
        
        # Fit the model
        for i in range(n):
            last_level = level
            last_trend = trend
            
            level = alpha * (data[i] - seasonal[i % season_length]) + (1 - alpha) * (last_level + last_trend)
            trend = beta * (level - last_level) + (1 - beta) * last_trend
            seasonal[i % season_length] = gamma * (data[i] - level) + (1 - gamma) * seasonal[i % season_length]
        
        # Generate forecast
        forecast = []
        for i in range(horizon):
            forecast_value = level + (i + 1) * trend + seasonal[i % season_length]
            # Ensure non-negative forecasts
            forecast.append(max(0, forecast_value))
        
        return forecast
        
    except Exception as e:
        logger.error(f"Error in Holt-Winters forecast: {str(e)}")
        # Fallback to simple moving average
        return [np.mean(data)] * horizon


def arima_forecast_simple(data: List[float], horizon: int) -> List[float]:
    """
    Generate forecast using simplified ARIMA model
    
    This implementation uses a simple ARIMA(1,1,1) approach with differencing
    and autoregressive components.
    
    Args:
        data: Historical time series data
        horizon: Number of periods to forecast
        
    Returns:
        List of forecasted values
    """
    try:
        # Convert to numpy array
        series = np.array(data)
        
        # First-order differencing to make series stationary
        diff = np.diff(series)
        
        # Calculate AR(1) coefficient
        if len(diff) > 1:
            ar_coef = np.corrcoef(diff[:-1], diff[1:])[0, 1]
            ar_coef = max(-0.9, min(0.9, ar_coef))  # Bound coefficient
        else:
            ar_coef = 0.5
        
        # Calculate MA(1) coefficient (simplified)
        ma_coef = 0.3
        
        # Last value and last difference
        last_value = series[-1]
        last_diff = diff[-1] if len(diff) > 0 else 0
        
        # Generate forecast
        forecast = []
        current_value = last_value
        current_diff = last_diff
        
        for i in range(horizon):
            # ARIMA forecast: current + AR component + MA component
            next_diff = ar_coef * current_diff + ma_coef * (current_diff - ar_coef * current_diff)
            next_value = current_value + next_diff
            
            # Ensure non-negative
            next_value = max(0, next_value)
            
            forecast.append(next_value)
            current_value = next_value
            current_diff = next_diff
        
        return forecast
        
    except Exception as e:
        logger.error(f"Error in ARIMA forecast: {str(e)}")
        # Fallback to simple moving average
        return [np.mean(data)] * horizon


def calculate_confidence_intervals(
    historical: List[float], 
    forecast: List[float], 
    confidence_level: float
) -> Tuple[List[float], List[float]]:
    """
    Calculate confidence intervals for forecast
    
    Uses historical forecast error variance to estimate prediction intervals.
    
    Args:
        historical: Historical time series data
        forecast: Forecasted values
        confidence_level: Confidence level (e.g., 0.80 or 0.95)
        
    Returns:
        Tuple of (lower_bounds, upper_bounds)
    """
    try:
        # Calculate historical standard deviation as proxy for forecast error
        hist_std = np.std(historical)
        
        # Z-scores for confidence levels
        z_scores = {
            0.80: 1.28,
            0.95: 1.96
        }
        
        z = z_scores.get(confidence_level, 1.96)
        
        # Calculate intervals (widening with forecast horizon)
        lower_bounds = []
        upper_bounds = []
        
        for i, f in enumerate(forecast):
            # Increase uncertainty with forecast horizon
            horizon_factor = np.sqrt(1 + i * 0.1)
            margin = z * hist_std * horizon_factor
            
            lower_bounds.append(max(0, f - margin))
            upper_bounds.append(f + margin)
        
        return lower_bounds, upper_bounds
        
    except Exception as e:
        logger.error(f"Error calculating confidence intervals: {str(e)}")
        # Fallback to ±20% intervals
        lower = [max(0, f * 0.8) for f in forecast]
        upper = [f * 1.2 for f in forecast]
        return lower, upper


# For local testing
if __name__ == '__main__':
    # Test data
    test_historical_data = [
        {'order_date': f'2023-{i//30+1:02d}-{i%30+1:02d}', 'quantity': 50 + np.random.randint(-10, 10)}
        for i in range(90)
    ]
    
    # Test event
    test_event = {
        'product_id': 'PROD-00001',
        'historical_data': test_historical_data,
        'horizon_days': 7
    }
    
    # Mock context
    class MockContext:
        function_name = 'calculate-forecast-test'
        memory_limit_in_mb = 256
        invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:calculate-forecast-test'
        aws_request_id = 'test-request-id'
    
    # Execute
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(json.loads(result['body']), indent=2))
