"""
Lambda Tool: calculate_accuracy

This tool calculates Mean Absolute Percentage Error (MAPE) for previous forecasts
compared to actual demand. It stores accuracy metrics in the forecast_accuracy
table and returns a summary for LLM analysis.

Requirements: 3.2
"""

import os
import json
import logging
import time
import uuid
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Redshift Data API client
redshift_data = boto3.client('redshift-data', region_name='us-east-1')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for calculate_accuracy tool
    
    This function is invoked by Bedrock Agent to calculate forecast accuracy
    by comparing previous predictions to actual demand.
    
    Args:
        event: Input from Bedrock Agent with parameters:
            - product_id (required): Product identifier
            - forecast_date (required): Date when forecast was made (YYYY-MM-DD)
        context: Lambda context object
        
    Returns:
        dict: Response with MAPE and accuracy metrics for LLM analysis
    """
    logger.info(f"calculate_accuracy invoked with event keys: {list(event.keys())}")
    
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
        forecast_date = params.get('forecast_date')
        
        # Validate parameters
        if not product_id:
            raise ValueError("Missing required parameter: product_id")
        if not forecast_date:
            raise ValueError("Missing required parameter: forecast_date")
        
        logger.info(f"Calculating accuracy for product: {product_id}, forecast date: {forecast_date}")
        
        # Validate environment variables
        if not validate_environment():
            raise Exception("Missing required environment variables")
        
        # Get forecast and actual data
        forecast_data, actual_data = get_forecast_and_actual_data(product_id, forecast_date)
        
        if not forecast_data:
            logger.warning(f"No forecast data found for product {product_id} on {forecast_date}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'product_id': product_id,
                    'forecast_date': forecast_date,
                    'message': 'No forecast data found for the specified date',
                    'accuracy_calculated': False
                })
            }
        
        if not actual_data:
            logger.warning(f"No actual sales data found for product {product_id}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'product_id': product_id,
                    'forecast_date': forecast_date,
                    'message': 'No actual sales data available yet for accuracy calculation',
                    'accuracy_calculated': False
                })
            }
        
        # Calculate MAPE and other accuracy metrics
        accuracy_metrics = calculate_mape(forecast_data, actual_data)
        
        # Store accuracy metrics in Redshift Serverless
        accuracy_ids = store_accuracy_metrics(
            product_id,
            forecast_date,
            forecast_data,
            actual_data,
            accuracy_metrics
        )
        
        # Generate summary for LLM analysis
        response = {
            'product_id': product_id,
            'forecast_date': forecast_date,
            'accuracy_calculated': True,
            'mape': accuracy_metrics['mape'],
            'mae': accuracy_metrics['mae'],
            'rmse': accuracy_metrics['rmse'],
            'bias': accuracy_metrics['bias'],
            'data_points_compared': accuracy_metrics['data_points'],
            'accuracy_records_stored': len(accuracy_ids),
            'accuracy_ids': accuracy_ids,
            'summary': generate_accuracy_summary(accuracy_metrics),
            'calculated_at': datetime.now().isoformat()
        }
        
        logger.info(f"Successfully calculated accuracy: MAPE={accuracy_metrics['mape']:.2f}%")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
        
    except Exception as e:
        logger.error(f"Error in calculate_accuracy: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to calculate forecast accuracy'
            })
        }


def get_forecast_and_actual_data(
    product_id: str,
    forecast_date: str
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Retrieve forecast predictions and actual sales data from Redshift Serverless
    
    Args:
        product_id: Product identifier
        forecast_date: Date when forecast was made
        
    Returns:
        Tuple of (forecast_data, actual_data) as lists of dictionaries
    """
    try:
        # Query forecast data
        forecast_sql = f"""
            SELECT 
                forecast_date,
                predicted_demand
            FROM demand_forecast
            WHERE product_id = '{product_id}'
            AND DATE(created_at) = '{forecast_date}'
            ORDER BY forecast_date
        """
        
        logger.info(f"Querying forecast data for {product_id}")
        
        forecast_response = redshift_data.execute_statement(
            WorkgroupName=os.environ['REDSHIFT_WORKGROUP'],
            Database=os.environ['REDSHIFT_DATABASE'],
            Sql=forecast_sql
        )
        
        forecast_query_id = forecast_response['Id']
        status = wait_for_query_completion(forecast_query_id)
        
        if status != 'FINISHED':
            raise Exception(f"Forecast query failed with status: {status}")
        
        forecast_result = redshift_data.get_statement_result(Id=forecast_query_id)
        
        forecast_data = []
        for record in forecast_result['Records']:
            forecast_data.append({
                'date': record[0]['stringValue'],
                'predicted': float(record[1]['longValue'])
            })
        
        if not forecast_data:
            return [], []
        
        # Get date range for actual data
        start_date = forecast_data[0]['date']
        end_date = forecast_data[-1]['date']
        
        # Query actual sales data
        actual_sql = f"""
            SELECT 
                soh.order_date,
                SUM(sol.quantity) as actual_demand
            FROM sales_order_line sol
            JOIN sales_order_header soh ON sol.so_id = soh.so_id
            WHERE sol.product_id = '{product_id}'
            AND soh.order_date >= '{start_date}'
            AND soh.order_date <= '{end_date}'
            GROUP BY soh.order_date
            ORDER BY soh.order_date
        """
        
        logger.info(f"Querying actual sales data for {product_id}")
        
        actual_response = redshift_data.execute_statement(
            WorkgroupName=os.environ['REDSHIFT_WORKGROUP'],
            Database=os.environ['REDSHIFT_DATABASE'],
            Sql=actual_sql
        )
        
        actual_query_id = actual_response['Id']
        status = wait_for_query_completion(actual_query_id)
        
        if status != 'FINISHED':
            raise Exception(f"Actual data query failed with status: {status}")
        
        actual_result = redshift_data.get_statement_result(Id=actual_query_id)
        
        actual_data = []
        for record in actual_result['Records']:
            actual_data.append({
                'date': record[0]['stringValue'],
                'actual': float(record[1]['longValue'])
            })
        
        logger.info(f"Retrieved {len(forecast_data)} forecast records and {len(actual_data)} actual records")
        
        return forecast_data, actual_data
        
    except Exception as e:
        logger.error(f"Error retrieving forecast and actual data: {str(e)}", exc_info=True)
        raise


def calculate_mape(
    forecast_data: List[Dict[str, Any]],
    actual_data: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Calculate Mean Absolute Percentage Error and other accuracy metrics
    
    Args:
        forecast_data: List of forecast records with date and predicted values
        actual_data: List of actual sales records with date and actual values
        
    Returns:
        Dictionary with MAPE, MAE, RMSE, bias, and data point count
    """
    try:
        # Create lookup dictionary for actual data
        actual_lookup = {d['date']: d['actual'] for d in actual_data}
        
        # Match forecast to actual
        errors = []
        absolute_errors = []
        percentage_errors = []
        squared_errors = []
        
        for forecast in forecast_data:
            date = forecast['date']
            predicted = forecast['predicted']
            
            if date in actual_lookup:
                actual = actual_lookup[date]
                
                # Skip if actual is zero (to avoid division by zero)
                if actual == 0:
                    continue
                
                error = predicted - actual
                abs_error = abs(error)
                pct_error = abs(error / actual) * 100
                sq_error = error ** 2
                
                errors.append(error)
                absolute_errors.append(abs_error)
                percentage_errors.append(pct_error)
                squared_errors.append(sq_error)
        
        if not percentage_errors:
            raise ValueError("No matching data points found for accuracy calculation")
        
        # Calculate metrics
        mape = sum(percentage_errors) / len(percentage_errors)
        mae = sum(absolute_errors) / len(absolute_errors)
        rmse = (sum(squared_errors) / len(squared_errors)) ** 0.5
        bias = sum(errors) / len(errors)
        
        metrics = {
            'mape': round(mape, 2),
            'mae': round(mae, 2),
            'rmse': round(rmse, 2),
            'bias': round(bias, 2),
            'data_points': len(percentage_errors)
        }
        
        logger.info(f"Calculated accuracy metrics: MAPE={mape:.2f}%, MAE={mae:.2f}, RMSE={rmse:.2f}")
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating MAPE: {str(e)}", exc_info=True)
        raise


def store_accuracy_metrics(
    product_id: str,
    forecast_date: str,
    forecast_data: List[Dict[str, Any]],
    actual_data: List[Dict[str, Any]],
    accuracy_metrics: Dict[str, float]
) -> List[str]:
    """
    Store accuracy metrics in Redshift Serverless forecast_accuracy table
    
    Args:
        product_id: Product identifier
        forecast_date: Date when forecast was made
        forecast_data: List of forecast records
        actual_data: List of actual sales records
        accuracy_metrics: Calculated accuracy metrics
        
    Returns:
        List of accuracy record IDs
    """
    try:
        # Create lookup dictionary for actual data
        actual_lookup = {d['date']: d['actual'] for d in actual_data}
        
        accuracy_ids = []
        values_list = []
        
        # Store individual accuracy records for each date
        for forecast in forecast_data:
            date = forecast['date']
            predicted = forecast['predicted']
            
            if date in actual_lookup:
                actual = actual_lookup[date]
                
                # Calculate MAPE for this specific data point
                if actual > 0:
                    mape = abs((predicted - actual) / actual) * 100
                else:
                    continue
                
                accuracy_id = f"ACC-{uuid.uuid4().hex[:12].upper()}"
                accuracy_ids.append(accuracy_id)
                
                values = f"""(
                    '{accuracy_id}',
                    '{product_id}',
                    '{date}',
                    {int(actual)},
                    {int(predicted)},
                    {mape:.2f},
                    CURRENT_TIMESTAMP
                )"""
                values_list.append(values)
        
        if not values_list:
            logger.warning("No accuracy records to store")
            return []
        
        # Build complete SQL statement
        sql = f"""
            INSERT INTO forecast_accuracy (
                accuracy_id,
                product_id,
                forecast_date,
                actual_demand,
                predicted_demand,
                mape,
                created_at
            ) VALUES {','.join(values_list)}
        """
        
        logger.info(f"Storing {len(accuracy_ids)} accuracy records")
        
        # Execute insert using Redshift Data API
        response = redshift_data.execute_statement(
            WorkgroupName=os.environ['REDSHIFT_WORKGROUP'],
            Database=os.environ['REDSHIFT_DATABASE'],
            Sql=sql
        )
        
        query_id = response['Id']
        status = wait_for_query_completion(query_id)
        
        if status != 'FINISHED':
            raise Exception(f"Insert query failed with status: {status}")
        
        logger.info(f"Successfully stored {len(accuracy_ids)} accuracy records")
        return accuracy_ids
        
    except Exception as e:
        logger.error(f"Error storing accuracy metrics: {str(e)}", exc_info=True)
        raise


def generate_accuracy_summary(metrics: Dict[str, float]) -> str:
    """
    Generate human-readable summary of accuracy metrics for LLM analysis
    
    Args:
        metrics: Dictionary with MAPE, MAE, RMSE, bias values
        
    Returns:
        String summary for LLM interpretation
    """
    mape = metrics['mape']
    
    # Determine accuracy quality
    if mape < 10:
        quality = "excellent"
    elif mape < 15:
        quality = "good"
    elif mape < 25:
        quality = "acceptable"
    else:
        quality = "poor"
    
    # Determine bias direction
    bias = metrics['bias']
    if abs(bias) < 1:
        bias_desc = "minimal bias"
    elif bias > 0:
        bias_desc = f"over-forecasting by {abs(bias):.1f} units on average"
    else:
        bias_desc = f"under-forecasting by {abs(bias):.1f} units on average"
    
    summary = (
        f"Forecast accuracy is {quality} with MAPE of {mape:.2f}%. "
        f"The forecast shows {bias_desc}. "
        f"Mean Absolute Error is {metrics['mae']:.2f} units. "
        f"Based on {metrics['data_points']} data points."
    )
    
    return summary


def wait_for_query_completion(query_id: str, max_wait_seconds: int = 60) -> str:
    """
    Wait for Redshift Data API query to complete
    
    Args:
        query_id: Query execution ID
        max_wait_seconds: Maximum time to wait for query completion
        
    Returns:
        Final query status (FINISHED, FAILED, ABORTED)
    """
    start_time = time.time()
    
    while True:
        # Check if we've exceeded max wait time
        if time.time() - start_time > max_wait_seconds:
            logger.error(f"Query {query_id} exceeded max wait time of {max_wait_seconds}s")
            raise Exception(f"Query timeout after {max_wait_seconds} seconds")
        
        # Get query status
        status_response = redshift_data.describe_statement(Id=query_id)
        status = status_response['Status']
        
        logger.debug(f"Query {query_id} status: {status}")
        
        if status == 'FINISHED':
            return status
        elif status in ['FAILED', 'ABORTED']:
            error_msg = status_response.get('Error', 'Unknown error')
            logger.error(f"Query {query_id} failed: {error_msg}")
            raise Exception(f"Query {status}: {error_msg}")
        
        # Query still running, wait before checking again
        time.sleep(0.5)


def validate_environment() -> bool:
    """
    Validate that all required environment variables are set
    
    Returns:
        True if all required variables are present, False otherwise
    """
    required_vars = [
        'REDSHIFT_WORKGROUP',
        'REDSHIFT_DATABASE'
    ]
    
    missing_vars = []
    for var in required_vars:
        if var not in os.environ:
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    return True


# For local testing
if __name__ == '__main__':
    # Set test environment variables
    os.environ['REDSHIFT_WORKGROUP'] = 'supply-chain-workgroup'
    os.environ['REDSHIFT_DATABASE'] = 'supply_chain'
    
    # Test event
    test_event = {
        'product_id': 'PROD-00001',
        'forecast_date': '2024-01-01'
    }
    
    # Mock context
    class MockContext:
        function_name = 'calculate-accuracy-test'
        memory_limit_in_mb = 256
        invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:calculate-accuracy-test'
        aws_request_id = 'test-request-id'
    
    # Execute
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(json.loads(result['body']), indent=2))
