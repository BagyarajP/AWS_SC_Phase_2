"""
Lambda Tool: store_forecast

This tool stores forecast records into the demand_forecast table in Redshift
Serverless via Data API. It's designed to be called by the Forecasting Bedrock
Agent after generating demand forecasts.

Requirements: 3.6
"""

import os
import json
import logging
import time
import uuid
from typing import Dict, Any, List
from datetime import datetime
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Redshift Data API client
redshift_data = boto3.client('redshift-data', region_name='us-east-1')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for store_forecast tool
    
    This function is invoked by Bedrock Agent to store forecast results in
    Redshift Serverless.
    
    Args:
        event: Input from Bedrock Agent with parameters:
            - product_id (required): Product identifier
            - warehouse_id (required): Warehouse identifier
            - forecast_data (required): List of forecast records with dates and values
            - horizon_days (required): Forecast horizon (7 or 30 days)
        context: Lambda context object
        
    Returns:
        dict: Response with forecast IDs and storage confirmation
    """
    logger.info(f"store_forecast invoked with event keys: {list(event.keys())}")
    
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
        warehouse_id = params.get('warehouse_id')
        forecast_data = params.get('forecast_data')
        horizon_days = int(params.get('horizon_days', 7))
        
        # Validate parameters
        if not product_id:
            raise ValueError("Missing required parameter: product_id")
        if not warehouse_id:
            raise ValueError("Missing required parameter: warehouse_id")
        if forecast_data is None:
            raise ValueError("Missing required parameter: forecast_data")
        
        # Parse forecast data if it's a JSON string
        if isinstance(forecast_data, str):
            forecast_data = json.loads(forecast_data)
        
        logger.info(f"Storing {len(forecast_data)} forecast records for product: {product_id}, warehouse: {warehouse_id}")
        
        # Validate environment variables
        if not validate_environment():
            raise Exception("Missing required environment variables")
        
        # Store forecast records in Redshift Serverless
        forecast_ids = store_forecast_records(
            product_id, 
            warehouse_id, 
            forecast_data, 
            horizon_days
        )
        
        response = {
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'horizon_days': horizon_days,
            'records_stored': len(forecast_ids),
            'forecast_ids': forecast_ids,
            'stored_at': datetime.now().isoformat(),
            'message': f'Successfully stored {len(forecast_ids)} forecast records'
        }
        
        logger.info(f"Successfully stored {len(forecast_ids)} forecast records")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
        
    except Exception as e:
        logger.error(f"Error in store_forecast: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to store forecast data'
            })
        }


def store_forecast_records(
    product_id: str,
    warehouse_id: str,
    forecast_data: List[Dict[str, Any]],
    horizon_days: int
) -> List[str]:
    """
    Store forecast records in Redshift Serverless demand_forecast table
    
    Args:
        product_id: Product identifier
        warehouse_id: Warehouse identifier
        forecast_data: List of forecast records with dates, predictions, and confidence intervals
        horizon_days: Forecast horizon (7 or 30 days)
        
    Returns:
        List of forecast IDs for stored records
    """
    try:
        forecast_ids = []
        
        # Build batch insert SQL
        values_list = []
        for record in forecast_data:
            forecast_id = f"FCST-{uuid.uuid4().hex[:12].upper()}"
            forecast_ids.append(forecast_id)
            
            # Extract confidence intervals
            ci_80_lower = record.get('confidence_80_lower', 0)
            ci_80_upper = record.get('confidence_80_upper', 0)
            ci_95_lower = record.get('confidence_95_lower', 0)
            ci_95_upper = record.get('confidence_95_upper', 0)
            
            # Determine confidence level (use 80% as default)
            confidence_level = 0.80
            confidence_interval_lower = int(ci_80_lower)
            confidence_interval_upper = int(ci_80_upper)
            
            values = f"""(
                '{forecast_id}',
                '{product_id}',
                '{warehouse_id}',
                '{record['forecast_date']}',
                {horizon_days},
                {int(record['predicted_demand'])},
                {confidence_interval_lower},
                {confidence_interval_upper},
                {confidence_level},
                CURRENT_TIMESTAMP
            )"""
            values_list.append(values)
        
        # Build complete SQL statement
        sql = f"""
            INSERT INTO demand_forecast (
                forecast_id,
                product_id,
                warehouse_id,
                forecast_date,
                forecast_horizon_days,
                predicted_demand,
                confidence_interval_lower,
                confidence_interval_upper,
                confidence_level,
                created_at
            ) VALUES {','.join(values_list)}
        """
        
        logger.info(f"Executing batch insert for {len(forecast_ids)} records")
        
        # Execute insert using Redshift Data API
        response = redshift_data.execute_statement(
            WorkgroupName=os.environ['REDSHIFT_WORKGROUP'],
            Database=os.environ['REDSHIFT_DATABASE'],
            Sql=sql
        )
        
        query_id = response['Id']
        logger.info(f"Insert query submitted with ID: {query_id}")
        
        # Wait for query to complete
        status = wait_for_query_completion(query_id)
        
        if status != 'FINISHED':
            raise Exception(f"Insert query failed with status: {status}")
        
        logger.info(f"Successfully inserted {len(forecast_ids)} forecast records")
        return forecast_ids
        
    except Exception as e:
        logger.error(f"Error storing forecast records: {str(e)}", exc_info=True)
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
    
    # Test forecast data
    test_forecast_data = [
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
    
    # Test event
    test_event = {
        'product_id': 'PROD-00001',
        'warehouse_id': 'WH-SOUTH',
        'forecast_data': test_forecast_data,
        'horizon_days': 7
    }
    
    # Mock context
    class MockContext:
        function_name = 'store-forecast-test'
        memory_limit_in_mb = 256
        invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:store-forecast-test'
        aws_request_id = 'test-request-id'
    
    # Execute
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(json.loads(result['body']), indent=2))
