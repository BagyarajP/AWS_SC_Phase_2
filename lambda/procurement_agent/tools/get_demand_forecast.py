"""
Lambda Tool: get_demand_forecast
Query demand_forecast table for specified SKUs and horizon
"""

import json
import logging
import os
import boto3
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Redshift Data API client
redshift_data = boto3.client('redshift-data', region_name='us-east-1')

# Configuration
WORKGROUP_NAME = os.environ.get('REDSHIFT_WORKGROUP', 'supply-chain-workgroup')
DATABASE_NAME = os.environ.get('REDSHIFT_DATABASE', 'supply_chain_db')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Get demand forecasts from Redshift
    
    Args:
        event: Input parameters
            - product_id: Product ID to get forecast for
            - horizon_days: Forecast horizon (7 or 30)
            - start_date (optional): Start date for forecast (default: today)
            
    Returns:
        Forecast data with confidence intervals
    """
    logger.info(f"get_demand_forecast invoked with event: {json.dumps(event)}")
    
    try:
        # Extract parameters
        product_id = event.get('product_id')
        horizon_days = event.get('horizon_days', 7)
        start_date = event.get('start_date', datetime.now().strftime('%Y-%m-%d'))
        
        if not product_id:
            raise ValueError("product_id is required")
        
        if horizon_days not in [7, 30]:
            raise ValueError("horizon_days must be 7 or 30")
        
        # Calculate end date
        end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=horizon_days)).strftime('%Y-%m-%d')
        
        # Build SQL query
        sql = f"""
            SELECT 
                df.forecast_id,
                df.product_id,
                p.product_name,
                df.forecast_date,
                df.forecast_value,
                df.confidence_80_lower,
                df.confidence_80_upper,
                df.confidence_95_lower,
                df.confidence_95_upper,
                df.horizon_days,
                df.created_at
            FROM demand_forecast df
            JOIN product p ON df.product_id = p.product_id
            WHERE df.product_id = {product_id}
              AND df.forecast_date >= '{start_date}'
              AND df.forecast_date < '{end_date}'
              AND df.horizon_days = {horizon_days}
            ORDER BY df.forecast_date ASC
        """
        
        logger.info(f"Executing SQL: {sql}")
        
        # Execute query
        response = redshift_data.execute_statement(
            WorkgroupName=WORKGROUP_NAME,
            Database=DATABASE_NAME,
            Sql=sql
        )
        
        query_id = response['Id']
        logger.info(f"Query ID: {query_id}")
        
        # Wait for completion
        status = wait_for_query_completion(query_id)
        
        if status != 'FINISHED':
            raise Exception(f"Query failed with status: {status}")
        
        # Get results
        result = redshift_data.get_statement_result(Id=query_id)
        
        # Parse results
        forecast_records = parse_query_results(result)
        
        logger.info(f"Retrieved {len(forecast_records)} forecast records")
        
        # Calculate summary statistics
        if forecast_records:
            total_forecast = sum(r['forecast_value'] for r in forecast_records)
            avg_forecast = total_forecast / len(forecast_records)
        else:
            total_forecast = 0
            avg_forecast = 0
        
        return {
            'product_id': product_id,
            'horizon_days': horizon_days,
            'start_date': start_date,
            'end_date': end_date,
            'forecast_records': forecast_records,
            'summary': {
                'total_forecast_demand': round(total_forecast, 2),
                'average_daily_demand': round(avg_forecast, 2),
                'forecast_count': len(forecast_records)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting demand forecast: {str(e)}", exc_info=True)
        raise


def wait_for_query_completion(query_id: str, max_wait_seconds: int = 60) -> str:
    """Wait for Redshift query to complete"""
    start_time = time.time()
    
    while True:
        response = redshift_data.describe_statement(Id=query_id)
        status = response['Status']
        
        if status in ['FINISHED', 'FAILED', 'ABORTED']:
            return status
        
        if time.time() - start_time > max_wait_seconds:
            raise Exception(f"Query timeout after {max_wait_seconds} seconds")
        
        time.sleep(1)


def parse_query_results(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Redshift Data API query results"""
    records = []
    
    if 'Records' not in result:
        return records
    
    column_metadata = result.get('ColumnMetadata', [])
    column_names = [col['name'] for col in column_metadata]
    
    for row in result['Records']:
        record = {}
        for i, col_name in enumerate(column_names):
            value = row[i]
            
            if 'longValue' in value:
                record[col_name] = value['longValue']
            elif 'stringValue' in value:
                record[col_name] = value['stringValue']
            elif 'doubleValue' in value:
                record[col_name] = value['doubleValue']
            elif 'isNull' in value and value['isNull']:
                record[col_name] = None
            else:
                record[col_name] = str(value)
        
        records.append(record)
    
    return records
