"""
Lambda Tool: calculate_eoq
Calculate Economic Order Quantity
"""

import json
import logging
import math
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Calculate Economic Order Quantity (EOQ)
    
    Formula: EOQ = sqrt((2 * D * S) / H)
    Where:
        D = Annual demand
        S = Order cost per order
        H = Holding cost per unit per year
    
    Args:
        event: Input parameters
            - annual_demand: Annual demand quantity
            - order_cost: Cost per order
            - holding_cost: Holding cost per unit per year
            
    Returns:
        EOQ and related metrics
    """
    logger.info(f"calculate_eoq invoked with event: {json.dumps(event)}")
    
    try:
        annual_demand = float(event.get('annual_demand', 0))
        order_cost = float(event.get('order_cost', 0))
        holding_cost = float(event.get('holding_cost', 0))
        
        if annual_demand <= 0:
            raise ValueError("annual_demand must be positive")
        if order_cost <= 0:
            raise ValueError("order_cost must be positive")
        if holding_cost <= 0:
            raise ValueError("holding_cost must be positive")
        
        # Calculate EOQ
        eoq = math.sqrt((2 * annual_demand * order_cost) / holding_cost)
        
        # Calculate number of orders per year
        orders_per_year = annual_demand / eoq
        
        # Calculate total annual cost
        ordering_cost = orders_per_year * order_cost
        holding_cost_total = (eoq / 2) * holding_cost
        total_cost = ordering_cost + holding_cost_total
        
        result = {
            'eoq': round(eoq, 2),
            'orders_per_year': round(orders_per_year, 2),
            'ordering_cost_annual': round(ordering_cost, 2),
            'holding_cost_annual': round(holding_cost_total, 2),
            'total_annual_cost': round(total_cost, 2),
            'inputs': {
                'annual_demand': annual_demand,
                'order_cost': order_cost,
                'holding_cost': holding_cost
            }
        }
        
        logger.info(f"EOQ calculation result: {json.dumps(result)}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error calculating EOQ: {str(e)}", exc_info=True)
        raise
