"""
Lambda Tool: get_inventory_levels
Query Redshift for current inventory levels and reorder points
"""

import json
import logging
import os
import boto3
import time
from typing import Dict, Any, List, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Redshift Data API client
redshift_data = boto3.client('redshift-data', region_name='us-east-1')

# Configuration from environment variables
WORKGROUP_NAME = os.environ.get('REDSHIFT_WORKGROUP', 'supply-chain-workgroup')
DATABASE_NAME = os.environ.get('REDSHIFT_DATABASE', 'supply_chain_db')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Get current inventory levels from Redshift
    
    Args:
        event: Input parameters
            - warehouse_id (optional): Filter by warehouse
            - below_reorder_point_only (optional): Only return items below reorder point
            
    Returns:
        List of inventory records with current levels and reorder points
    """
    logger.info(f"get_inventory_levels invoked with event: {json.dumps(event)}")
    
    try:
        # Extract parameters
        warehouse_id = event.get('warehouse_id')
        below_reorder_point_only = event.get('below_reorder_point_only', False)
        
        # Build SQL query
        sql = """
            SELECT 
                i.inventory_id,
                i.product_id,
                p.product_name,
                p.category,
                i.warehouse_id,
                w.warehouse_name,
                i.quantity_on_hand,
                i.reorder_point,
                i.reorder_quantity,
                i.last_updated,
                (i.quantity_on_hand - i.reorder_point) as quantity_above_reorder
            FROM inventory i
            JOIN product p ON i.product_id = p.product_id
            JOIN warehouse w ON i.warehouse_id = w.warehouse_id
            WHERE 1=1
        """
        
        # Add filters
        if warehouse_id:
            sql += f" AND i.warehouse_id = {warehouse_id}"
        
        if below_reorder_point_only:
            sql += " AND i.quantity_on_hand < i.reorder_point"
        
        sql += " ORDER BY (i.quantity_on_hand - i.reorder_point) ASC LIMIT 100"
        
        logger.info(f"Executing SQL: {sql}")
        
        # Execute query using Redshift Data API
        response = redshift_data.execute_statement(
            WorkgroupName=WORKGROUP_NAME,
            Database=DATABASE_NAME,
            Sql=sql
        )
        
        query_id = response['Id']
        logger.info(f"Query ID: {query_id}")
        
        # Wait for query to complete
        status = wait_for_query_completion(query_id)
        
        if status != 'FINISHED':
            raise Exception(f"Query failed with status: {status}")
        
        # Get query results
        result = redshift_data.get_statement_result(Id=query_id)
        
        # Parse results
        inventory_records = parse_query_results(result)
        
        logger.info(f"Retrieved {len(inventory_records)} inventory records")
        
        return {
            'inventory_records': inventory_records,
            'total_count': len(inventory_records),
            'filters_applied': {
                'warehouse_id': warehouse_id,
                'below_reorder_point_only': below_reorder_point_only
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting inventory levels: {str(e)}", exc_info=True)
        raise


def wait_for_query_completion(query_id: str, max_wait_seconds: int = 60) -> str:
    """
    Wait for Redshift query to complete
    
    Args:
        query_id: Query ID from execute_statement
        max_wait_seconds: Maximum time to wait
        
    Returns:
        Final query status
    """
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
    """
    Parse Redshift Data API query results
    
    Args:
        result: Result from get_statement_result
        
    Returns:
        List of inventory records
    """
    records = []
    
    if 'Records' not in result:
        return records
    
    column_metadata = result.get('ColumnMetadata', [])
    column_names = [col['name'] for col in column_metadata]
    
    for row in result['Records']:
        record = {}
        for i, col_name in enumerate(column_names):
            value = row[i]
            
            # Extract value based on type
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
