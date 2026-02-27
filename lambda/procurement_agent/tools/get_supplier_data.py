"""
Lambda Tool: get_supplier_data
Query supplier table for specified product with performance metrics
"""

import json
import logging
import os
import boto3
import time
from typing import Dict, Any, List

logger = logging.getLogger()
logger.setLevel(logging.INFO)

redshift_data = boto3.client('redshift-data', region_name='us-east-1')

WORKGROUP_NAME = os.environ.get('REDSHIFT_WORKGROUP', 'supply-chain-workgroup')
DATABASE_NAME = os.environ.get('REDSHIFT_DATABASE', 'supply_chain_db')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Get supplier data with performance metrics
    
    Args:
        event: Input parameters
            - product_id: Product ID to get suppliers for
            
    Returns:
        List of suppliers with pricing and performance metrics
    """
    logger.info(f"get_supplier_data invoked with event: {json.dumps(event)}")
    
    try:
        product_id = event.get('product_id')
        
        if not product_id:
            raise ValueError("product_id is required")
        
        sql = f"""
            SELECT 
                s.supplier_id,
                s.supplier_name,
                s.contact_email,
                s.lead_time_days,
                s.reliability_score,
                s.defect_rate,
                s.unit_price,
                s.minimum_order_quantity
            FROM supplier s
            WHERE s.product_id = {product_id}
            ORDER BY s.reliability_score DESC, s.unit_price ASC
        """
        
        logger.info(f"Executing SQL: {sql}")
        
        response = redshift_data.execute_statement(
            WorkgroupName=WORKGROUP_NAME,
            Database=DATABASE_NAME,
            Sql=sql
        )
        
        query_id = response['Id']
        status = wait_for_query_completion(query_id)
        
        if status != 'FINISHED':
            raise Exception(f"Query failed with status: {status}")
        
        result = redshift_data.get_statement_result(Id=query_id)
        suppliers = parse_query_results(result)
        
        logger.info(f"Retrieved {len(suppliers)} suppliers")
        
        return {
            'product_id': product_id,
            'suppliers': suppliers,
            'supplier_count': len(suppliers)
        }
        
    except Exception as e:
        logger.error(f"Error getting supplier data: {str(e)}", exc_info=True)
        raise


def wait_for_query_completion(query_id: str, max_wait_seconds: int = 60) -> str:
    start_time = time.time()
    while True:
        response = redshift_data.describe_statement(Id=query_id)
        status = response['Status']
        if status in ['FINISHED', 'FAILED', 'ABORTED']:
            return status
        if time.time() - start_time > max_wait_seconds:
            raise Exception(f"Query timeout")
        time.sleep(1)


def parse_query_results(result: Dict[str, Any]) -> List[Dict[str, Any]]:
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
