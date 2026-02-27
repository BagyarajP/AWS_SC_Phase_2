"""
Lambda Tool: get_historical_sales

This tool retrieves 12 months of historical sales data for a specified SKU
from Redshift Serverless via Data API. It's designed to be called by the
Forecasting Bedrock Agent as part of the demand forecasting workflow.

Requirements: 3.3, 8.4
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Redshift Data API client
redshift_data = boto3.client('redshift-data', region_name='us-east-1')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for get_historical_sales tool
    
    This function is invoked by Bedrock Agent to retrieve historical sales data.
    
    Args:
        event: Input from Bedrock Agent with parameters:
            - product_id (required): Product identifier
            - months_back (optional): Number of months of history (default: 12)
        context: Lambda context object
        
    Returns:
        dict: Response with historical sales time series data in JSON format
    """
    logger.info(f"get_historical_sales invoked with event: {json.dumps(event)}")
    
    try:
        # Extract parameters from event
        # Bedrock Agent passes parameters in different formats depending on invocation
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
            raise ValueError("Missing required parameters. Expected 'product_id' in event.")
        
        product_id = params.get('product_id')
        months_back = int(params.get('months_back', 12))
        
        if not product_id:
            raise ValueError("Missing required parameter: product_id")
        
        logger.info(f"Retrieving {months_back} months of sales data for product: {product_id}")
        
        # Validate environment variables
        if not validate_environment():
            raise Exception("Missing required environment variables")
        
        # Query historical sales data from Redshift Serverless
        sales_data = query_historical_sales(product_id, months_back)
        
        if not sales_data:
            logger.warning(f"No historical sales data found for product: {product_id}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'product_id': product_id,
                    'months_back': months_back,
                    'data_points': 0,
                    'time_series': [],
                    'message': 'No historical sales data found for this product'
                })
            }
        
        # Format response for Bedrock Agent
        response = {
            'product_id': product_id,
            'months_back': months_back,
            'data_points': len(sales_data),
            'time_series': sales_data,
            'summary': {
                'total_quantity': sum(d['quantity'] for d in sales_data),
                'average_daily_quantity': sum(d['quantity'] for d in sales_data) / len(sales_data) if sales_data else 0,
                'date_range': {
                    'start': sales_data[0]['order_date'] if sales_data else None,
                    'end': sales_data[-1]['order_date'] if sales_data else None
                }
            }
        }
        
        logger.info(f"Successfully retrieved {len(sales_data)} data points for {product_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
        
    except Exception as e:
        logger.error(f"Error in get_historical_sales: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to retrieve historical sales data'
            })
        }


def query_historical_sales(product_id: str, months_back: int) -> list:
    """
    Query Redshift Serverless for historical sales data using Data API
    
    Args:
        product_id: Product identifier
        months_back: Number of months of historical data to retrieve
        
    Returns:
        List of dictionaries with order_date and quantity
    """
    try:
        # Build SQL query
        sql = f"""
            SELECT 
                soh.order_date,
                SUM(sol.quantity) as quantity
            FROM sales_order_line sol
            JOIN sales_order_header soh ON sol.so_id = soh.so_id
            WHERE sol.product_id = '{product_id}'
            AND soh.order_date >= CURRENT_DATE - INTERVAL '{months_back} months'
            GROUP BY soh.order_date
            ORDER BY soh.order_date
        """
        
        logger.info(f"Executing Redshift query for product {product_id}")
        
        # Execute query using Redshift Data API
        response = redshift_data.execute_statement(
            WorkgroupName=os.environ['REDSHIFT_WORKGROUP'],
            Database=os.environ['REDSHIFT_DATABASE'],
            Sql=sql
        )
        
        query_id = response['Id']
        logger.info(f"Query submitted with ID: {query_id}")
        
        # Wait for query to complete
        status = wait_for_query_completion(query_id)
        
        if status != 'FINISHED':
            raise Exception(f"Query failed with status: {status}")
        
        # Retrieve results
        result = redshift_data.get_statement_result(Id=query_id)
        
        # Parse results into list of dictionaries
        sales_data = []
        for record in result['Records']:
            sales_data.append({
                'order_date': record[0]['stringValue'],
                'quantity': int(record[1]['longValue'])
            })
        
        logger.info(f"Retrieved {len(sales_data)} records from Redshift")
        return sales_data
        
    except Exception as e:
        logger.error(f"Error querying Redshift: {str(e)}", exc_info=True)
        raise


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
        'months_back': 12
    }
    
    # Mock context
    class MockContext:
        function_name = 'get-historical-sales-test'
        memory_limit_in_mb = 256
        invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:get-historical-sales-test'
        aws_request_id = 'test-request-id'
    
    # Execute
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(json.loads(result['body']), indent=2))
