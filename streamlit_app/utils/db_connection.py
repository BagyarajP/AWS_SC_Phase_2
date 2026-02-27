"""
Database Connection Utilities

Provides Redshift connection management and query helpers for the Streamlit dashboard.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import streamlit as st
from typing import Optional, Dict, Any


# Environment variables
REDSHIFT_HOST = os.environ.get('REDSHIFT_HOST', 'localhost')
REDSHIFT_PORT = int(os.environ.get('REDSHIFT_PORT', '5439'))
REDSHIFT_DATABASE = os.environ.get('REDSHIFT_DATABASE', 'supply_chain')
REDSHIFT_USER = os.environ.get('REDSHIFT_USER', 'admin')
REDSHIFT_PASSWORD = os.environ.get('REDSHIFT_PASSWORD', '')


@st.cache_resource
def get_redshift_connection():
    """
    Create and cache Redshift connection.
    
    Returns:
        psycopg2 connection object
    """
    try:
        conn = psycopg2.connect(
            host=REDSHIFT_HOST,
            port=REDSHIFT_PORT,
            database=REDSHIFT_DATABASE,
            user=REDSHIFT_USER,
            password=REDSHIFT_PASSWORD,
            connect_timeout=10
        )
        return conn
    except Exception as e:
        st.error(f"Failed to connect to Redshift: {str(e)}")
        return None


def execute_query(query: str, params: Optional[tuple] = None) -> Optional[pd.DataFrame]:
    """
    Execute SQL query and return results as DataFrame.
    
    Args:
        query: SQL query string
        params: Query parameters (optional)
        
    Returns:
        DataFrame with query results or None on error
    """
    try:
        conn = get_redshift_connection()
        if conn is None:
            return None
        
        df = pd.read_sql(query, conn, params=params)
        return df
        
    except Exception as e:
        st.error(f"Query execution failed: {str(e)}")
        if st.button("Retry"):
            st.rerun()
        return None


def execute_update(query: str, params: Optional[tuple] = None) -> bool:
    """
    Execute UPDATE/INSERT/DELETE query.
    
    Args:
        query: SQL query string
        params: Query parameters (optional)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = get_redshift_connection()
        if conn is None:
            return False
        
        with conn.cursor() as cursor:
            cursor.execute(query, params)
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Update execution failed: {str(e)}")
        return False


def fetch_pending_approvals(role: str) -> pd.DataFrame:
    """
    Fetch pending approvals for given role.
    
    Args:
        role: User role (Procurement_Manager or Inventory_Manager)
        
    Returns:
        DataFrame with pending approval records
    """
    query = """
        SELECT 
            aq.approval_id,
            ad.decision_id,
            ad.agent_name,
            ad.decision_type,
            ad.decision_data,
            ad.rationale,
            ad.confidence_score,
            aq.created_at
        FROM approval_queue aq
        JOIN agent_decision ad ON aq.decision_id = ad.decision_id
        WHERE aq.assigned_role = %s
        AND aq.status = 'pending'
        ORDER BY aq.created_at DESC
    """
    
    return execute_query(query, (role,))


def approve_decision(approval_id: str, user_name: str) -> bool:
    """
    Approve a pending decision.
    
    Args:
        approval_id: Approval queue ID
        user_name: Name of approving user
        
    Returns:
        True if successful
    """
    query = """
        UPDATE approval_queue
        SET status = 'approved',
            approved_by = %s,
            approved_at = CURRENT_TIMESTAMP
        WHERE approval_id = %s
    """
    
    return execute_update(query, (user_name, approval_id))


def reject_decision(approval_id: str, user_name: str, reason: str) -> bool:
    """
    Reject a pending decision.
    
    Args:
        approval_id: Approval queue ID
        user_name: Name of rejecting user
        reason: Rejection reason
        
    Returns:
        True if successful
    """
    query = """
        UPDATE approval_queue
        SET status = 'rejected',
            approved_by = %s,
            approved_at = CURRENT_TIMESTAMP,
            rejection_reason = %s
        WHERE approval_id = %s
    """
    
    return execute_update(query, (user_name, reason, approval_id))


def fetch_inventory_levels() -> pd.DataFrame:
    """
    Fetch current inventory levels across all warehouses.
    
    Returns:
        DataFrame with inventory data
    """
    query = """
        SELECT 
            i.product_id,
            p.sku,
            p.product_name,
            p.category,
            i.warehouse_id,
            w.warehouse_name,
            i.quantity_on_hand,
            p.reorder_point,
            CASE 
                WHEN i.quantity_on_hand < p.reorder_point * 0.5 THEN 'Critical'
                WHEN i.quantity_on_hand < p.reorder_point THEN 'Low'
                ELSE 'Normal'
            END as stock_status
        FROM inventory i
        JOIN product p ON i.product_id = p.product_id
        JOIN warehouse w ON i.warehouse_id = w.warehouse_id
        ORDER BY p.category, p.sku
    """
    
    return execute_query(query)


def fetch_recent_purchase_orders(days: int = 30) -> pd.DataFrame:
    """
    Fetch recent purchase orders.
    
    Args:
        days: Number of days to look back
        
    Returns:
        DataFrame with purchase order data
    """
    query = """
        SELECT 
            po.po_id,
            po.order_date,
            s.supplier_name,
            po.total_amount,
            po.status,
            po.created_by,
            po.approved_by
        FROM purchase_order_header po
        JOIN supplier s ON po.supplier_id = s.supplier_id
        WHERE po.order_date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY po.order_date DESC
    """
    
    return execute_query(query, (days,))


def fetch_supplier_performance() -> pd.DataFrame:
    """
    Fetch supplier performance metrics.
    
    Returns:
        DataFrame with supplier scorecards
    """
    query = """
        SELECT 
            supplier_id,
            supplier_name,
            reliability_score,
            avg_lead_time_days,
            defect_rate,
            CASE 
                WHEN reliability_score < 0.85 OR defect_rate > 0.05 THEN 'Alert'
                ELSE 'Good'
            END as performance_status
        FROM supplier
        ORDER BY reliability_score DESC
    """
    
    return execute_query(query)


def fetch_inventory_metrics() -> Dict[str, Any]:
    """
    Calculate and fetch inventory performance metrics.
    
    Returns:
        Dictionary with metric values
    """
    # This is a simplified version - full implementation would calculate from historical data
    query = """
        SELECT 
            COUNT(DISTINCT CASE WHEN quantity_on_hand < reorder_point THEN i.product_id END) as low_stock_count,
            COUNT(DISTINCT i.product_id) as total_products
        FROM inventory i
        JOIN product p ON i.product_id = p.product_id
    """
    
    df = execute_query(query)
    
    if df is not None and len(df) > 0:
        return {
            'current_turnover': 4.2,  # Placeholder
            'baseline_turnover': 3.8,  # Placeholder
            'improvement_pct': 10.5,  # Placeholder
            'stockout_rate': 0.03,  # Placeholder
            'slow_moving_count': 45,  # Placeholder
            'low_stock_count': int(df.iloc[0]['low_stock_count'])
        }
    
    return {}


def fetch_forecast_accuracy() -> pd.DataFrame:
    """
    Fetch forecast accuracy metrics by SKU category.
    
    Returns:
        DataFrame with MAPE by category
    """
    query = """
        SELECT 
            p.category,
            AVG(fa.mape) as avg_mape,
            COUNT(*) as forecast_count
        FROM forecast_accuracy fa
        JOIN product p ON fa.product_id = p.product_id
        WHERE fa.forecast_date >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY p.category
        ORDER BY avg_mape ASC
    """
    
    return execute_query(query)
