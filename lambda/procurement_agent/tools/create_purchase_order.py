"""
Lambda Tool: create_purchase_order
Create purchase order with approval routing logic
"""

import json
import logging
import os
import boto3
import time
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

redshift_data = boto3.client('redshift-data', region_name='us-east-1')

WORKGROUP_NAME = os.environ.get('REDSHIFT_WORKGROUP', 'supply-chain-workgroup')
DATABASE_NAME = os.environ.get('REDSHIFT_DATABASE', 'supply_chain_db')

# Approval thresholds
VALUE_THRESHOLD = 10000  # £10k
CONFIDENCE_THRESHOLD = 0.7


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Create purchase order with approval routing
    
    Args:
        event: Input parameters
            - product_id: Product ID
            - supplier_id: Supplier ID
            - quantity: Order quantity
            - unit_price: Price per unit
            - rationale: LLM-generated rationale
            - confidence_score: Confidence score (0-1)
            
    Returns:
        PO creation result with approval status
    """
    logger.info(f"create_purchase_order invoked with event: {json.dumps(event)}")
    
    try:
        product_id = event.get('product_id')
        supplier_id = event.get('supplier_id')
        quantity = float(event.get('quantity', 0))
        unit_price = float(event.get('unit_price', 0))
        rationale = event.get('rationale', '')
        confidence_score = float(event.get('confidence_score', 0))
        
        if not all([product_id, supplier_id, quantity > 0, unit_price > 0]):
            raise ValueError("Missing required parameters")
        
        # Calculate total value
        total_value = quantity * unit_price
        
        # Determine if approval is needed
        needs_approval = (total_value > VALUE_THRESHOLD) or (confidence_score < CONFIDENCE_THRESHOLD)
        
        if needs_approval:
            # Route to approval queue
            result = route_to_approval_queue(
                product_id, supplier_id, quantity, unit_price, 
                total_value, rationale, confidence_score
            )
            status = 'pending_approval'
        else:
            # Create PO directly
            result = create_po_directly(
                product_id, supplier_id, quantity, unit_price, 
                total_value, rationale, confidence_score
            )
            status = 'approved'
        
        # Log to audit_log
        log_to_audit(
            agent_name='Procurement',
            decision_type='purchase_order',
            details=json.dumps({
                'product_id': product_id,
                'supplier_id': supplier_id,
                'quantity': quantity,
                'total_value': total_value,
                'status': status
            }),
            rationale=rationale,
            confidence_score=confidence_score
        )
        
        return {
            'success': True,
            'status': status,
            'total_value': round(total_value, 2),
            'needs_approval': needs_approval,
            'approval_reason': get_approval_reason(total_value, confidence_score),
            **result
        }
        
    except Exception as e:
        logger.error(f"Error creating purchase order: {str(e)}", exc_info=True)
        raise


def route_to_approval_queue(product_id, supplier_id, quantity, unit_price, 
                            total_value, rationale, confidence_score) -> Dict[str, Any]:
    """Route high-risk PO to approval queue"""
    sql = f"""
        INSERT INTO approval_queue (
            decision_type, product_id, supplier_id, quantity, 
            unit_price, total_value, rationale, confidence_score,
            status, role_required, created_at
        ) VALUES (
            'purchase_order', {product_id}, {supplier_id}, {quantity},
            {unit_price}, {total_value}, '{rationale.replace("'", "''")}', {confidence_score},
            'pending', 'Procurement_Manager', CURRENT_TIMESTAMP
        )
    """
    
    execute_sql(sql)
    
    return {
        'approval_queue_id': 'generated_by_db',
        'message': 'Purchase order routed to approval queue'
    }


def create_po_directly(product_id, supplier_id, quantity, unit_price,
                      total_value, rationale, confidence_score) -> Dict[str, Any]:
    """Create PO directly without approval"""
    # Insert into purchase_order_header
    sql_header = f"""
        INSERT INTO purchase_order_header (
            supplier_id, order_date, expected_delivery_date, 
            status, total_amount, created_at
        ) VALUES (
            {supplier_id}, CURRENT_DATE, CURRENT_DATE + INTERVAL '14 days',
            'approved', {total_value}, CURRENT_TIMESTAMP
        )
    """
    
    execute_sql(sql_header)
    
    # Note: In production, get the generated PO ID and insert line items
    
    return {
        'po_id': 'generated_by_db',
        'message': 'Purchase order created successfully'
    }


def log_to_audit(agent_name, decision_type, details, rationale, confidence_score):
    """Log decision to audit_log"""
    sql = f"""
        INSERT INTO audit_log (
            agent_name, decision_type, decision_details, 
            rationale, confidence_score, timestamp
        ) VALUES (
            '{agent_name}', '{decision_type}', '{details.replace("'", "''")}',
            '{rationale.replace("'", "''")}', {confidence_score}, CURRENT_TIMESTAMP
        )
    """
    
    execute_sql(sql)


def get_approval_reason(total_value, confidence_score) -> str:
    """Get human-readable approval reason"""
    reasons = []
    if total_value > VALUE_THRESHOLD:
        reasons.append(f"Total value £{total_value:,.2f} exceeds threshold of £{VALUE_THRESHOLD:,.2f}")
    if confidence_score < CONFIDENCE_THRESHOLD:
        reasons.append(f"Confidence score {confidence_score:.2f} below threshold of {CONFIDENCE_THRESHOLD}")
    return "; ".join(reasons) if reasons else "No approval needed"


def execute_sql(sql: str):
    """Execute SQL via Redshift Data API"""
    response = redshift_data.execute_statement(
        WorkgroupName=WORKGROUP_NAME,
        Database=DATABASE_NAME,
        Sql=sql
    )
    
    query_id = response['Id']
    
    # Wait for completion
    start_time = time.time()
    while True:
        response = redshift_data.describe_statement(Id=query_id)
        status = response['Status']
        
        if status in ['FINISHED', 'FAILED', 'ABORTED']:
            if status != 'FINISHED':
                raise Exception(f"Query failed with status: {status}")
            return
        
        if time.time() - start_time > 60:
            raise Exception("Query timeout")
        
        time.sleep(1)
