"""
Inventory Rebalancing Agent Lambda Function

This agent automatically rebalances stock across warehouses based on regional demand patterns.
Implements Requirements 2.1-2.7 from the supply chain AI platform specification.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
REDSHIFT_HOST = os.environ.get('REDSHIFT_HOST', 'localhost')
REDSHIFT_PORT = int(os.environ.get('REDSHIFT_PORT', '5439'))
REDSHIFT_DATABASE = os.environ.get('REDSHIFT_DATABASE', 'supply_chain')
REDSHIFT_USER = os.environ.get('REDSHIFT_USER', 'admin')
REDSHIFT_PASSWORD = os.environ.get('REDSHIFT_PASSWORD', '')
LARGE_TRANSFER_THRESHOLD = int(os.environ.get('LARGE_TRANSFER_THRESHOLD', '100'))
LOW_CONFIDENCE_THRESHOLD = float(os.environ.get('LOW_CONFIDENCE_THRESHOLD', '0.75'))


def get_redshift_connection(max_retries=3):
    """
    Create connection to Redshift with retry logic.
    
    Args:
        max_retries: Maximum number of connection attempts
        
    Returns:
        psycopg2 connection object
    """
    import time
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=REDSHIFT_HOST,
                port=REDSHIFT_PORT,
                database=REDSHIFT_DATABASE,
                user=REDSHIFT_USER,
                password=REDSHIFT_PASSWORD,
                connect_timeout=10
            )
            logger.info("Successfully connected to Redshift")
            return conn
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to connect to Redshift after {max_retries} attempts: {str(e)}")
                raise
            wait_time = 2 ** attempt
            logger.warning(f"Connection attempt {attempt + 1} failed, retrying in {wait_time}s...")
            time.sleep(wait_time)


def fetch_inventory_levels(conn) -> List[Dict]:
    """
    Query current inventory levels across all warehouses.
    
    Returns:
        List of inventory records with product and warehouse details
    """
    query = """
        SELECT 
            i.inventory_id,
            i.product_id,
            i.warehouse_id,
            i.quantity_on_hand,
            p.sku,
            p.product_name,
            p.category,
            w.warehouse_name,
            w.location,
            w.capacity
        FROM inventory i
        JOIN product p ON i.product_id = p.product_id
        JOIN warehouse w ON i.warehouse_id = w.warehouse_id
        WHERE i.quantity_on_hand > 0
        ORDER BY p.product_id, w.warehouse_id
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query)
        results = cursor.fetchall()
        logger.info(f"Fetched {len(results)} inventory records")
        return [dict(row) for row in results]


def fetch_demand_forecasts(conn, horizon_days=7) -> Dict[Tuple[str, str], int]:
    """
    Query demand forecasts by warehouse and product.
    
    Args:
        conn: Database connection
        horizon_days: Forecast horizon in days
        
    Returns:
        Dictionary mapping (product_id, warehouse_id) to forecasted demand
    """
    query = """
        SELECT 
            product_id,
            warehouse_id,
            predicted_demand
        FROM demand_forecast
        WHERE forecast_horizon_days = %s
        AND forecast_date = CURRENT_DATE
    """
    
    forecasts = {}
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, (horizon_days,))
        for row in cursor.fetchall():
            key = (row['product_id'], row['warehouse_id'])
            forecasts[key] = row['predicted_demand']
    
    logger.info(f"Fetched {len(forecasts)} demand forecasts")
    return forecasts


def calculate_imbalance_score(inventory_by_warehouse: Dict[str, int], 
                              demand_by_warehouse: Dict[str, int]) -> float:
    """
    Calculate inventory imbalance score across warehouses for a product.
    
    Score ranges from 0 (perfectly balanced) to 1 (severely imbalanced).
    
    Args:
        inventory_by_warehouse: Current inventory levels by warehouse
        demand_by_warehouse: Forecasted demand by warehouse
        
    Returns:
        Imbalance score (0-1)
    """
    if not inventory_by_warehouse or not demand_by_warehouse:
        return 0.0
    
    # Calculate inventory-to-demand ratios
    ratios = []
    for wh_id in inventory_by_warehouse.keys():
        inventory = inventory_by_warehouse.get(wh_id, 0)
        demand = demand_by_warehouse.get(wh_id, 1)  # Avoid division by zero
        ratio = inventory / demand if demand > 0 else inventory
        ratios.append(ratio)
    
    if not ratios:
        return 0.0
    
    # Calculate coefficient of variation as imbalance measure
    import statistics
    if len(ratios) < 2:
        return 0.0
    
    mean_ratio = statistics.mean(ratios)
    if mean_ratio == 0:
        return 0.0
    
    std_ratio = statistics.stdev(ratios)
    cv = std_ratio / mean_ratio
    
    # Normalize to 0-1 range (CV > 1 indicates high imbalance)
    imbalance_score = min(cv, 1.0)
    
    return round(imbalance_score, 2)


def detect_inventory_imbalances(inventory_levels: List[Dict], 
                                demand_forecasts: Dict[Tuple[str, str], int]) -> List[Dict]:
    """
    Detect inventory imbalances across warehouses for each product.
    
    Args:
        inventory_levels: Current inventory records
        demand_forecasts: Forecasted demand by (product_id, warehouse_id)
        
    Returns:
        List of imbalance records with product and warehouse details
    """
    # Group inventory by product
    inventory_by_product = {}
    for inv in inventory_levels:
        product_id = inv['product_id']
        if product_id not in inventory_by_product:
            inventory_by_product[product_id] = {
                'sku': inv['sku'],
                'product_name': inv['product_name'],
                'warehouses': {}
            }
        inventory_by_product[product_id]['warehouses'][inv['warehouse_id']] = {
            'inventory': inv['quantity_on_hand'],
            'warehouse_name': inv['warehouse_name'],
            'capacity': inv['capacity']
        }
    
    imbalances = []
    for product_id, data in inventory_by_product.items():
        warehouses = data['warehouses']
        
        # Get demand forecasts for this product
        demand_by_warehouse = {}
        for wh_id in warehouses.keys():
            demand_by_warehouse[wh_id] = demand_forecasts.get((product_id, wh_id), 0)
        
        # Calculate inventory levels
        inventory_by_warehouse = {wh_id: wh['inventory'] for wh_id, wh in warehouses.items()}
        
        # Calculate imbalance score
        imbalance_score = calculate_imbalance_score(inventory_by_warehouse, demand_by_warehouse)
        
        # Only consider significant imbalances (score > 0.3)
        if imbalance_score > 0.3:
            imbalances.append({
                'product_id': product_id,
                'sku': data['sku'],
                'product_name': data['product_name'],
                'imbalance_score': imbalance_score,
                'warehouses': warehouses,
                'demand_forecasts': demand_by_warehouse
            })
    
    logger.info(f"Detected {len(imbalances)} inventory imbalances")
    return imbalances


def generate_transfer_recommendation(imbalance: Dict) -> Optional[Dict]:
    """
    Generate optimal transfer recommendation for an imbalanced product.
    
    Args:
        imbalance: Imbalance record with product and warehouse details
        
    Returns:
        Transfer recommendation or None if no transfer needed
    """
    warehouses = imbalance['warehouses']
    demand_forecasts = imbalance['demand_forecasts']
    
    # Calculate inventory-to-demand ratios
    ratios = {}
    for wh_id, wh_data in warehouses.items():
        inventory = wh_data['inventory']
        demand = demand_forecasts.get(wh_id, 1)
        ratios[wh_id] = inventory / demand if demand > 0 else inventory
    
    # Find source (excess) and destination (shortage) warehouses
    sorted_warehouses = sorted(ratios.items(), key=lambda x: x[1], reverse=True)
    
    if len(sorted_warehouses) < 2:
        return None
    
    source_wh_id = sorted_warehouses[0][0]
    dest_wh_id = sorted_warehouses[-1][0]
    
    source_inventory = warehouses[source_wh_id]['inventory']
    source_demand = demand_forecasts.get(source_wh_id, 0)
    dest_inventory = warehouses[dest_wh_id]['inventory']
    dest_demand = demand_forecasts.get(dest_wh_id, 0)
    dest_capacity = warehouses[dest_wh_id]['capacity']
    
    # Calculate optimal transfer quantity
    # Transfer enough to balance the ratios while respecting constraints
    source_excess = max(0, source_inventory - source_demand)
    dest_shortage = max(0, dest_demand - dest_inventory)
    available_capacity = dest_capacity - dest_inventory
    
    transfer_qty = min(source_excess, dest_shortage, available_capacity)
    transfer_qty = int(transfer_qty * 0.5)  # Transfer 50% of calculated amount for safety
    
    if transfer_qty < 10:  # Minimum transfer threshold
        return None
    
    # Generate rationale
    rationale = (
        f"{imbalance['sku']} has inventory imbalance (score: {imbalance['imbalance_score']}). "
        f"{warehouses[dest_wh_id]['warehouse_name']} has {dest_inventory} units with forecasted demand of {dest_demand} units, "
        f"creating potential stockout risk. {warehouses[source_wh_id]['warehouse_name']} has excess inventory "
        f"({source_inventory} units) relative to demand ({source_demand} units). "
        f"Transferring {transfer_qty} units will balance inventory to match regional demand patterns."
    )
    
    # Calculate confidence score based on forecast accuracy and imbalance severity
    # Higher imbalance = higher confidence in need for transfer
    # For MVP, use simplified confidence calculation
    base_confidence = 0.6 + (imbalance['imbalance_score'] * 0.3)
    confidence_score = min(0.95, base_confidence)
    
    return {
        'product_id': imbalance['product_id'],
        'sku': imbalance['sku'],
        'product_name': imbalance['product_name'],
        'quantity': transfer_qty,
        'source_warehouse_id': source_wh_id,
        'source_warehouse_name': warehouses[source_wh_id]['warehouse_name'],
        'dest_warehouse_id': dest_wh_id,
        'dest_warehouse_name': warehouses[dest_wh_id]['warehouse_name'],
        'rationale': rationale,
        'confidence_score': round(confidence_score, 2),
        'imbalance_score': imbalance['imbalance_score'],
        'factors': {
            'source_inventory': source_inventory,
            'source_forecasted_demand_7d': source_demand,
            'dest_inventory': dest_inventory,
            'dest_forecasted_demand_7d': dest_demand,
            'imbalance_score': imbalance['imbalance_score']
        }
    }


def check_approval_required(transfer: Dict) -> bool:
    """
    Determine if transfer requires human approval.
    
    Args:
        transfer: Transfer recommendation
        
    Returns:
        True if approval required, False otherwise
    """
    return (
        transfer['quantity'] > LARGE_TRANSFER_THRESHOLD or
        transfer['confidence_score'] < LOW_CONFIDENCE_THRESHOLD
    )


def create_agent_decision(conn, transfer: Dict, requires_approval: bool) -> str:
    """
    Create agent decision record in database.
    
    Args:
        conn: Database connection
        transfer: Transfer recommendation
        requires_approval: Whether approval is required
        
    Returns:
        Decision ID
    """
    decision_id = f"IT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
    
    decision_data = {
        'product_id': transfer['product_id'],
        'sku': transfer['sku'],
        'quantity': transfer['quantity'],
        'source_warehouse_id': transfer['source_warehouse_id'],
        'dest_warehouse_id': transfer['dest_warehouse_id'],
        'factors': transfer['factors']
    }
    
    query = """
        INSERT INTO agent_decision (
            decision_id, agent_name, decision_type, decision_data,
            rationale, confidence_score, status, requires_approval, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    status = 'PENDING_APPROVAL' if requires_approval else 'APPROVED'
    
    with conn.cursor() as cursor:
        cursor.execute(query, (
            decision_id,
            'Inventory_Agent',
            'TRANSFER_INVENTORY',
            json.dumps(decision_data),
            transfer['rationale'],
            transfer['confidence_score'],
            status,
            requires_approval,
            datetime.now()
        ))
    
    conn.commit()
    logger.info(f"Created agent decision: {decision_id} (requires_approval={requires_approval})")
    
    return decision_id


def create_approval_queue_entry(conn, decision_id: str):
    """
    Create approval queue entry for high-risk transfer.
    
    Args:
        conn: Database connection
        decision_id: Decision ID to queue for approval
    """
    approval_id = f"APR-{uuid.uuid4().hex[:12]}"
    
    query = """
        INSERT INTO approval_queue (
            approval_id, decision_id, assigned_role, status, created_at
        ) VALUES (%s, %s, %s, %s, %s)
    """
    
    with conn.cursor() as cursor:
        cursor.execute(query, (
            approval_id,
            decision_id,
            'Inventory_Manager',
            'pending',
            datetime.now()
        ))
    
    conn.commit()
    logger.info(f"Created approval queue entry: {approval_id}")


def execute_transfer(conn, transfer: Dict, decision_id: str):
    """
    Execute approved inventory transfer by updating inventory records.
    
    Args:
        conn: Database connection
        transfer: Transfer details
        decision_id: Associated decision ID
    """
    # Update source warehouse inventory
    update_source = """
        UPDATE inventory
        SET quantity_on_hand = quantity_on_hand - %s,
            last_updated = %s
        WHERE product_id = %s AND warehouse_id = %s
    """
    
    # Update destination warehouse inventory
    update_dest = """
        UPDATE inventory
        SET quantity_on_hand = quantity_on_hand + %s,
            last_updated = %s
        WHERE product_id = %s AND warehouse_id = %s
    """
    
    now = datetime.now()
    
    with conn.cursor() as cursor:
        cursor.execute(update_source, (
            transfer['quantity'],
            now,
            transfer['product_id'],
            transfer['source_warehouse_id']
        ))
        
        cursor.execute(update_dest, (
            transfer['quantity'],
            now,
            transfer['product_id'],
            transfer['dest_warehouse_id']
        ))
    
    conn.commit()
    logger.info(f"Executed transfer for decision {decision_id}: {transfer['quantity']} units of {transfer['sku']}")


def log_to_audit(conn, decision_id: str, transfer: Dict, action_type: str):
    """
    Log transfer decision to audit log.
    
    Args:
        conn: Database connection
        decision_id: Decision ID
        transfer: Transfer details
        action_type: Type of action (e.g., 'TRANSFER_RECOMMENDED', 'TRANSFER_EXECUTED')
    """
    event_id = f"AUD-{uuid.uuid4().hex[:12]}"
    
    metadata = {
        'decision_id': decision_id,
        'source_warehouse': transfer['source_warehouse_name'],
        'dest_warehouse': transfer['dest_warehouse_name'],
        'quantity': transfer['quantity']
    }
    
    query = """
        INSERT INTO audit_log (
            event_id, timestamp, agent_name, action_type,
            entity_type, entity_id, rationale, confidence_score, metadata
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    with conn.cursor() as cursor:
        cursor.execute(query, (
            event_id,
            datetime.now(),
            'Inventory_Agent',
            action_type,
            'inventory_transfer',
            decision_id,
            transfer['rationale'],
            transfer['confidence_score'],
            json.dumps(metadata)
        ))
    
    conn.commit()
    logger.info(f"Logged audit entry: {event_id}")


def lambda_handler(event, context):
    """
    Inventory Rebalancing Agent Lambda handler.
    
    Triggered daily by EventBridge to analyze inventory distribution
    and generate transfer recommendations.
    
    Args:
        event: EventBridge scheduled event
        context: Lambda context object
        
    Returns:
        dict: Execution summary with transfers recommended
    """
    logger.info("Starting Inventory Rebalancing Agent execution")
    
    results = {
        'successful_transfers': [],
        'pending_approvals': [],
        'failed': []
    }
    
    try:
        # Connect to Redshift
        conn = get_redshift_connection()
        
        # Fetch current inventory levels
        inventory_levels = fetch_inventory_levels(conn)
        
        # Fetch demand forecasts
        demand_forecasts = fetch_demand_forecasts(conn, horizon_days=7)
        
        # Detect inventory imbalances
        imbalances = detect_inventory_imbalances(inventory_levels, demand_forecasts)
        
        # Generate transfer recommendations
        for imbalance in imbalances:
            try:
                transfer = generate_transfer_recommendation(imbalance)
                
                if transfer is None:
                    continue
                
                # Check if approval required
                requires_approval = check_approval_required(transfer)
                
                # Create agent decision record
                decision_id = create_agent_decision(conn, transfer, requires_approval)
                transfer['decision_id'] = decision_id
                
                if requires_approval:
                    # Route to approval queue
                    create_approval_queue_entry(conn, decision_id)
                    results['pending_approvals'].append(decision_id)
                    logger.info(f"Transfer requires approval: {decision_id}")
                else:
                    # Execute transfer automatically
                    execute_transfer(conn, transfer, decision_id)
                    results['successful_transfers'].append(decision_id)
                    logger.info(f"Transfer executed automatically: {decision_id}")
                
                # Log to audit
                action_type = 'TRANSFER_RECOMMENDED' if requires_approval else 'TRANSFER_EXECUTED'
                log_to_audit(conn, decision_id, transfer, action_type)
                
            except Exception as e:
                logger.error(f"Error processing transfer for {imbalance['sku']}: {str(e)}", exc_info=True)
                results['failed'].append({
                    'sku': imbalance['sku'],
                    'error': str(e)
                })
        
        conn.close()
        
        logger.info(f"Inventory Rebalancing Agent completed: {len(results['successful_transfers'])} executed, "
                   f"{len(results['pending_approvals'])} pending approval, {len(results['failed'])} failed")
        
        return {
            'statusCode': 200,
            'body': results
        }
        
    except Exception as e:
        logger.error(f"Fatal error in Inventory Rebalancing Agent: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }
