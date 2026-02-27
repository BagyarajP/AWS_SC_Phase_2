"""
Property Test 1: Purchase order generation for low inventory

**Property**: For any SKU with inventory level below its reorder point, when the 
Procurement Agent executes, a purchase order recommendation should be generated 
with a supplier selection.

**Validates: Requirements 1.1**
"""

import pytest
from hypothesis import given, strategies as st, settings
from lambda_function import generate_purchase_order_decision


# Feature: supply-chain-ai-platform, Property 1: Purchase order generation for low inventory
@given(
    quantity=st.integers(min_value=0, max_value=199),
    reorder_point=st.integers(min_value=200, max_value=500),
    demand_30d=st.integers(min_value=1, max_value=2000),
    unit_cost=st.floats(min_value=1.0, max_value=500.0),
    reorder_quantity=st.integers(min_value=100, max_value=1000)
)
@settings(max_examples=100)
def test_property_po_generation_for_low_inventory(quantity, reorder_point, demand_30d, unit_cost, reorder_quantity):
    """
    Property 1: For any SKU with inventory below reorder point, a PO should be generated
    
    This test verifies that whenever inventory is below the reorder point,
    the system generates a purchase order recommendation with supplier selection.
    """
    # Arrange: Create inventory item below reorder point
    inventory_item = {
        'product_id': 'PROD-TEST-001',
        'sku': 'SKU-TEST-001',
        'product_name': 'Test Product',
        'category': 'Test',
        'unit_cost': unit_cost,
        'reorder_point': reorder_point,
        'reorder_quantity': reorder_quantity,
        'inventory_id': 'INV-TEST-001',
        'warehouse_id': 'WH1_South',
        'warehouse_name': 'South Warehouse',
        'quantity_on_hand': quantity
    }
    
    forecast = {
        'product_id': 'PROD-TEST-001',
        'warehouse_id': 'WH1_South',
        'forecast_horizon_days': 30,
        'predicted_demand': demand_30d,
        'confidence_interval_lower': int(demand_30d * 0.8),
        'confidence_interval_upper': int(demand_30d * 1.2),
        'confidence_level': 0.95
    }
    
    suppliers = [
        {
            'supplier_id': 'SUP-001',
            'supplier_name': 'Supplier A',
            'reliability_score': 0.95,
            'avg_lead_time_days': 7,
            'defect_rate': 0.01
        },
        {
            'supplier_id': 'SUP-002',
            'supplier_name': 'Supplier B',
            'reliability_score': 0.90,
            'avg_lead_time_days': 5,
            'defect_rate': 0.02
        }
    ]
    
    forecast_accuracy = 0.12  # 12% MAPE
    
    # Act: Generate purchase order decision
    decision = generate_purchase_order_decision(
        inventory_item=inventory_item,
        forecast=forecast,
        suppliers=suppliers,
        forecast_accuracy=forecast_accuracy
    )
    
    # Assert: PO should be generated since inventory < reorder point
    assert decision is not None, \
        f"PO should be generated when inventory ({quantity}) < reorder point ({reorder_point})"
    
    assert 'decision_id' in decision, "Decision should have a decision_id"
    assert 'product_id' in decision, "Decision should include product_id"
    assert decision['product_id'] == 'PROD-TEST-001', "Decision should reference correct product"
    
    assert 'supplier_id' in decision, "Decision should include supplier selection"
    assert decision['supplier_id'] in ['SUP-001', 'SUP-002'], "Selected supplier should be from available suppliers"
    
    assert 'quantity' in decision, "Decision should specify order quantity"
    assert decision['quantity'] > 0, "Order quantity should be positive"
    
    assert 'rationale' in decision, "Decision should include rationale"
    assert len(decision['rationale']) > 0, "Rationale should not be empty"
    
    assert 'confidence_score' in decision, "Decision should include confidence score"


@given(
    quantity=st.integers(min_value=500, max_value=10000),
    reorder_point=st.integers(min_value=100, max_value=499)
)
@settings(max_examples=100)
def test_property_no_po_when_inventory_sufficient(quantity, reorder_point):
    """
    Property 1 (inverse): When inventory is above reorder point, no PO should be generated
    
    This test verifies the inverse property - when inventory is sufficient,
    no purchase order should be generated.
    """
    # Arrange: Create inventory item above reorder point
    inventory_item = {
        'product_id': 'PROD-TEST-002',
        'sku': 'SKU-TEST-002',
        'product_name': 'Test Product 2',
        'category': 'Test',
        'unit_cost': 50.0,
        'reorder_point': reorder_point,
        'reorder_quantity': 200,
        'inventory_id': 'INV-TEST-002',
        'warehouse_id': 'WH1_South',
        'warehouse_name': 'South Warehouse',
        'quantity_on_hand': quantity
    }
    
    forecast = {
        'product_id': 'PROD-TEST-002',
        'warehouse_id': 'WH1_South',
        'forecast_horizon_days': 30,
        'predicted_demand': 100,
        'confidence_interval_lower': 80,
        'confidence_interval_upper': 120,
        'confidence_level': 0.95
    }
    
    suppliers = [
        {
            'supplier_id': 'SUP-001',
            'supplier_name': 'Supplier A',
            'reliability_score': 0.95,
            'avg_lead_time_days': 7,
            'defect_rate': 0.01
        }
    ]
    
    forecast_accuracy = 0.10
    
    # Act: Attempt to generate purchase order decision
    decision = generate_purchase_order_decision(
        inventory_item=inventory_item,
        forecast=forecast,
        suppliers=suppliers,
        forecast_accuracy=forecast_accuracy
    )
    
    # Assert: No PO should be generated since inventory >= reorder point
    assert decision is None, \
        f"No PO should be generated when inventory ({quantity}) >= reorder point ({reorder_point})"
