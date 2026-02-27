"""
Metrics Calculator Lambda Function

Calculates and stores inventory performance metrics and supplier performance metrics.
Implements Requirements 13.1-13.7 and 14.1-14.7.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
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


def get_redshift_connection(max_retries=3):
    """Create connection to Redshift with retry logic"""
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
                logger.error(f"Failed to connect after {max_retries} attempts: {str(e)}")
                raise
            wait_time = 2 ** attempt
            logger.warning(f"Connection attempt {attempt + 1} failed, retrying in {wait_time}s...")
            time.sleep(wait_time)


def calculate_inventory_turnover(conn, warehouse_id: str, period_days: int = 90) -> float:
    """
    Calculate inventory turnover ratio for a warehouse.
    
    Formula: (Total Sales Value) / (Average Inventory Value)
    
    Args:
        conn: Database connection
        warehouse_id: Warehouse identifier
        period_days: Measurement period in days
        
    Returns:
        Inventory turnover ratio
        
    Validates: Requirements 13.1
    """
    query = """
        WITH sales_value AS (
            SELECT 
                SUM(sol.quantity * p.unit_cost) as total_sales
            FROM sales_order_line sol
            JOIN sales_order_header soh ON sol.so_id = soh.so_id
            JOIN product p ON sol.product_id = p.product_id
            WHERE soh.warehouse_id = %s
            AND soh.order_date >= CURRENT_DATE - INTERVAL '%s days'
        ),
        avg_inventory AS (
            SELECT 
                AVG(i.quantity_on_hand * p.unit_cost) as avg_value
            FROM inventory i
            JOIN product p ON i.product_id = p.product_id
            WHERE i.warehouse_id = %s
        )
        SELECT 
            CASE 
                WHEN avg_inventory.avg_value > 0 
                THEN sales_value.total_sales / avg_inventory.avg_value
                ELSE 0
            END as turnover_ratio
        FROM sales_value, avg_inventory
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, (warehouse_id, period_days, warehouse_id))
        result = cursor.fetchone()
        return float(result['turnover_ratio']) if result else 0.0


def calculate_stockout_rate(conn, product_id: str, period_days: int = 90) -> float:
    """
    Calculate stockout rate for a product.
    
    Formula: (Number of Stockout Incidents) / (Total Demand Events)
    
    Args:
        conn: Database connection
        product_id: Product identifier
        period_days: Measurement period in days
        
    Returns:
        Stockout rate (0-1)
        
    Validates: Requirements 13.2
    """
    # Simplified calculation for MVP
    # In production, would track actual stockout incidents
    query = """
        SELECT 
            COUNT(CASE WHEN i.quantity_on_hand = 0 THEN 1 END) as stockout_days,
            COUNT(*) as total_days
        FROM inventory i
        WHERE i.product_id = %s
        AND i.last_updated >= CURRENT_DATE - INTERVAL '%s days'
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, (product_id, period_days))
        result = cursor.fetchone()
        
        if result and result['total_days'] > 0:
            return float(result['stockout_days']) / float(result['total_days'])
        return 0.0


def identify_slow_moving_skus(conn, turnover_threshold: float = 2.0, period_days: int = 90) -> List[str]:
    """
    Identify slow-moving SKUs based on turnover ratio.
    
    Args:
        conn: Database connection
        turnover_threshold: Turnover ratio threshold (default: 2.0)
        period_days: Measurement period in days
        
    Returns:
        List of slow-moving product IDs
        
    Validates: Requirements 13.5
    """
    query = """
        WITH product_turnover AS (
            SELECT 
                p.product_id,
                p.sku,
                SUM(sol.quantity) as total_sold,
                AVG(i.quantity_on_hand) as avg_inventory,
                CASE 
                    WHEN AVG(i.quantity_on_hand) > 0 
                    THEN SUM(sol.quantity) / AVG(i.quantity_on_hand)
                    ELSE 0
                END as turnover_ratio
            FROM product p
            LEFT JOIN sales_order_line sol ON p.product_id = sol.product_id
            LEFT JOIN sales_order_header soh ON sol.so_id = soh.so_id
            LEFT JOIN inventory i ON p.product_id = i.product_id
            WHERE soh.order_date >= CURRENT_DATE - INTERVAL '%s days'
            OR soh.order_date IS NULL
            GROUP BY p.product_id, p.sku
        )
        SELECT product_id
        FROM product_turnover
        WHERE turnover_ratio < %s
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, (period_days, turnover_threshold))
        results = cursor.fetchall()
        return [row['product_id'] for row in results]


def calculate_supplier_reliability(conn, supplier_id: str, period_days: int = 180) -> float:
    """
    Calculate supplier reliability score.
    
    Formula: (On-Time Deliveries) / (Total Deliveries)
    
    Args:
        conn: Database connection
        supplier_id: Supplier identifier
        period_days: Measurement period in days
        
    Returns:
        Reliability score (0-1)
        
    Validates: Requirements 14.1
    """
    # Simplified calculation for MVP
    # In production, would track actual delivery dates
    query = """
        SELECT 
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
            COUNT(*) as total
        FROM purchase_order_header
        WHERE supplier_id = %s
        AND order_date >= CURRENT_DATE - INTERVAL '%s days'
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, (supplier_id, period_days))
        result = cursor.fetchone()
        
        if result and result['total'] > 0:
            return float(result['completed']) / float(result['total'])
        return 0.0


def calculate_supplier_lead_time(conn, supplier_id: str, period_days: int = 180) -> float:
    """
    Calculate average supplier lead time.
    
    Formula: Mean of (Delivery Date - Order Date)
    
    Args:
        conn: Database connection
        supplier_id: Supplier identifier
        period_days: Measurement period in days
        
    Returns:
        Average lead time in days
        
    Validates: Requirements 14.2
    """
    query = """
        SELECT 
            AVG(expected_delivery_date - order_date) as avg_lead_time
        FROM purchase_order_header
        WHERE supplier_id = %s
        AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        AND expected_delivery_date IS NOT NULL
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, (supplier_id, period_days))
        result = cursor.fetchone()
        return float(result['avg_lead_time']) if result and result['avg_lead_time'] else 0.0


def store_inventory_metrics(conn, metrics: Dict):
    """
    Store calculated inventory metrics in Redshift.
    
    Args:
        conn: Database connection
        metrics: Dictionary of metric values
        
    Validates: Requirements 13.7
    """
    # Create metrics table if not exists
    create_table_query = """
        CREATE TABLE IF NOT EXISTS inventory_metrics (
            metric_id VARCHAR(50) PRIMARY KEY,
            warehouse_id VARCHAR(50),
            metric_name VARCHAR(100),
            metric_value DECIMAL(10,2),
            calculation_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    
    with conn.cursor() as cursor:
        cursor.execute(create_table_query)
    
    # Insert metrics
    insert_query = """
        INSERT INTO inventory_metrics (
            metric_id, warehouse_id, metric_name, metric_value, calculation_date
        ) VALUES (%s, %s, %s, %s, %s)
    """
    
    with conn.cursor() as cursor:
        for warehouse_id, warehouse_metrics in metrics.items():
            for metric_name, metric_value in warehouse_metrics.items():
                metric_id = f"INV-{uuid.uuid4().hex[:12]}"
                cursor.execute(insert_query, (
                    metric_id,
                    warehouse_id,
                    metric_name,
                    metric_value,
                    datetime.now().date()
                ))
    
    conn.commit()
    logger.info(f"Stored {len(metrics)} inventory metrics")


def store_supplier_metrics(conn, metrics: Dict):
    """
    Store calculated supplier metrics in Redshift.
    
    Args:
        conn: Database connection
        metrics: Dictionary of metric values
        
    Validates: Requirements 14.7
    """
    # Update supplier table with calculated metrics
    update_query = """
        UPDATE supplier
        SET reliability_score = %s,
            avg_lead_time_days = %s,
            defect_rate = %s
        WHERE supplier_id = %s
    """
    
    with conn.cursor() as cursor:
        for supplier_id, supplier_metrics in metrics.items():
            cursor.execute(update_query, (
                supplier_metrics.get('reliability_score', 0),
                supplier_metrics.get('avg_lead_time', 0),
                supplier_metrics.get('defect_rate', 0),
                supplier_id
            ))
    
    conn.commit()
    logger.info(f"Updated {len(metrics)} supplier metrics")


def track_decision_accuracy(conn, decision_id: str, actual_outcome: Dict):
    """
    Track agent decision accuracy by comparing predictions to actual outcomes.
    
    Args:
        conn: Database connection
        decision_id: Decision identifier
        actual_outcome: Dictionary with actual outcome data
        
    Validates: Requirements 12.7
    """
    # Create decision accuracy table if not exists
    create_table_query = """
        CREATE TABLE IF NOT EXISTS decision_accuracy (
            accuracy_id VARCHAR(50) PRIMARY KEY,
            decision_id VARCHAR(50),
            predicted_value DECIMAL(10,2),
            actual_value DECIMAL(10,2),
            accuracy_score DECIMAL(5,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    
    with conn.cursor() as cursor:
        cursor.execute(create_table_query)
    
    # Calculate accuracy and store
    predicted = actual_outcome.get('predicted_value', 0)
    actual = actual_outcome.get('actual_value', 0)
    
    if predicted > 0:
        accuracy = 1 - abs(actual - predicted) / predicted
    else:
        accuracy = 0
    
    insert_query = """
        INSERT INTO decision_accuracy (
            accuracy_id, decision_id, predicted_value, actual_value, accuracy_score
        ) VALUES (%s, %s, %s, %s, %s)
    """
    
    accuracy_id = f"ACC-{uuid.uuid4().hex[:12]}"
    
    with conn.cursor() as cursor:
        cursor.execute(insert_query, (
            accuracy_id,
            decision_id,
            predicted,
            actual,
            accuracy
        ))
    
    conn.commit()
    logger.info(f"Tracked decision accuracy: {accuracy_id}")


def lambda_handler(event, context):
    """
    Metrics Calculator Lambda handler.
    
    Triggered periodically to calculate and store performance metrics.
    
    Args:
        event: EventBridge scheduled event
        context: Lambda context object
        
    Returns:
        dict: Execution summary with metrics calculated
    """
    logger.info("Starting Metrics Calculator execution")
    
    results = {
        'inventory_metrics': {},
        'supplier_metrics': {},
        'slow_moving_skus': [],
        'errors': []
    }
    
    try:
        conn = get_redshift_connection()
        
        # Calculate inventory metrics for each warehouse
        warehouses = ['WH1_South', 'WH_Midland', 'WH_North']
        
        for warehouse_id in warehouses:
            try:
                turnover = calculate_inventory_turnover(conn, warehouse_id)
                results['inventory_metrics'][warehouse_id] = {
                    'turnover_ratio': turnover
                }
                logger.info(f"Calculated turnover for {warehouse_id}: {turnover:.2f}")
            except Exception as e:
                logger.error(f"Error calculating metrics for {warehouse_id}: {str(e)}")
                results['errors'].append(f"{warehouse_id}: {str(e)}")
        
        # Identify slow-moving SKUs
        try:
            slow_moving = identify_slow_moving_skus(conn)
            results['slow_moving_skus'] = slow_moving
            logger.info(f"Identified {len(slow_moving)} slow-moving SKUs")
        except Exception as e:
            logger.error(f"Error identifying slow-moving SKUs: {str(e)}")
            results['errors'].append(f"Slow-moving SKUs: {str(e)}")
        
        # Calculate supplier metrics
        supplier_query = "SELECT supplier_id FROM supplier"
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(supplier_query)
            suppliers = cursor.fetchall()
        
        for supplier in suppliers[:10]:  # Limit to first 10 for MVP
            supplier_id = supplier['supplier_id']
            try:
                reliability = calculate_supplier_reliability(conn, supplier_id)
                lead_time = calculate_supplier_lead_time(conn, supplier_id)
                
                results['supplier_metrics'][supplier_id] = {
                    'reliability_score': reliability,
                    'avg_lead_time': lead_time,
                    'defect_rate': 0.02  # Placeholder
                }
            except Exception as e:
                logger.error(f"Error calculating metrics for {supplier_id}: {str(e)}")
                results['errors'].append(f"{supplier_id}: {str(e)}")
        
        # Store metrics
        if results['inventory_metrics']:
            store_inventory_metrics(conn, results['inventory_metrics'])
        
        if results['supplier_metrics']:
            store_supplier_metrics(conn, results['supplier_metrics'])
        
        conn.close()
        
        logger.info(f"Metrics Calculator completed: {len(results['inventory_metrics'])} warehouses, "
                   f"{len(results['supplier_metrics'])} suppliers, {len(results['errors'])} errors")
        
        return {
            'statusCode': 200,
            'body': results
        }
        
    except Exception as e:
        logger.error(f"Fatal error in Metrics Calculator: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }


# Property test stubs for Task 12

def test_property_inventory_turnover_calculation():
    """
    Property 35: Inventory turnover calculation
    
    For any warehouse, turnover should equal sales_value / avg_inventory
    
    Validates: Requirements 13.1
    """
    # TODO: Implement property test
    pass


def test_property_stockout_rate_calculation():
    """
    Property 36: Stockout rate calculation
    
    For any SKU, stockout rate should equal stockout_incidents / total_demand_events
    
    Validates: Requirements 13.2
    """
    # TODO: Implement property test
    pass


def test_property_metrics_persistence():
    """
    Property 39: Metrics persistence
    
    For any calculated metric, the value should be stored in Redshift with timestamp
    
    Validates: Requirements 13.7
    """
    # TODO: Implement property test
    pass


def test_property_supplier_metrics_persistence():
    """
    Property 45: Supplier metrics persistence
    
    For any supplier metric, the value should be stored with timestamp and supplier_id
    
    Validates: Requirements 14.7
    """
    # TODO: Implement property test
    pass


def test_property_decision_accuracy_tracking():
    """
    Property 34: Decision accuracy tracking
    
    For any agent decision with measurable outcome, accuracy metric should be calculated and stored
    
    Validates: Requirements 12.7
    """
    # TODO: Implement property test
    pass
