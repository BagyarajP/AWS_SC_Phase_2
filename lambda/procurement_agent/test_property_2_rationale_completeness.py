"""
Property Test 2: Decision rationale completeness

**Property**: For any agent decision (procurement, inventory transfer, or forecast), 
the decision record should include a non-empty natural language rationale field.

**Validates: Requirements 1.2, 2.2, 12.1**
"""

import pytest
from hypothesis import given, strategies as st, settings
from lambda_function import generate_purchase_order_decision


# Feature: supply-chain-ai-platform, Property 2: Decision rationale completeness
@given(
    quantity=st.integers(min_value=0, max_value=199),
    reorder_point=st.integers(min_value=200, max_value=500),
    demand_30d=st.integers(min_value=1, max_value=2000),
    unit_cost=st.floats(min_value=1.0, max_value=500.0),
    reorder_quantity=st.integers(min_value=100, max_value=1000),
    reliability=st.floats(min_value=0.7, max_value=0.99),
    lead_time=st.integers(min_value=3, max_value=21)
)
@settings(max_examples=100)
def test_property_decision_has_non_empty_rationale(
    quantity, reorder_point, demand_30d, unit_cost, reorder_quantity, reliability, lead_time
):
    """
    Property 2: Every procurement decision must have a non-empty rationale
    
    This test verifies that all decisions include a natural language explanation
    that helps users understand why the decision was made.
    """
    # Arrange
    inventory_item = {
        'product_id': 'PROD-TEST',
        'sku': 'SKU-TEST',
        'product_name': 'Test Product',
        'category': 'Test',
        'unit_cost': unit_cost,
        'reorder_point': reorder_point,
        'reorder_quantity': reorder_quantity,
        'inventory_id': 'INV-TEST',
        'warehouse_id': 'WH1_South',
        'warehouse_name': 'South Warehouse',
        'quantity_on_hand': quantity
    }
    
    forecast = {
        'product_id': 'PROD-TEST',
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
            'supplier_name': 'Test Supplier',
            'reliability_score': reliability,
            'avg_lead_time_days': lead_time,
            'defect_rate': 0.01
        }
    ]
    
    forecast_accuracy = 0.10
    
    # Act
    decision = generate_purchase_order_decision(
        inventory_item=inventory_item,
        forecast=forecast,
        suppliers=suppliers,
        forecast_accuracy=forecast_accuracy
    )
    
    # Assert
    assert decision is not None, "Decision should be generated for low inventory"
    assert 'rationale' in decision, "Decision must include a rationale field"
    assert isinstance(decision['rationale'], str), "Rationale must be a string"
    assert len(decision['rationale']) > 0, "Rationale must not be empty"
    assert len(decision['rationale'].strip()) > 0, "Rationale must not be just whitespace"


@given(
    quantity=st.integers(min_value=0, max_value=199),
    reorder_point=st.integers(min_value=200, max_value=500),
    demand_30d=st.integers(min_value=1, max_value=2000)
)
@settings(max_examples=100)
def test_property_rationale_contains_key_information(quantity, reorder_point, demand_30d):
    """
    Property 2: Rationale should contain key decision factors
    
    This test verifies that the rationale includes important information
    about inventory levels, forecasts, and supplier selection.
    """
    inventory_item = {
        'product_id': 'PROD-TEST',
        'sku': 'SKU-ABC-123',
        'product_name': 'Test Product',
        'category': 'Test',
        'unit_cost': 50.0,
        'reorder_point': reorder_point,
        'reorder_quantity': 200,
        'inventory_id': 'INV-TEST',
        'warehouse_id': 'WH1_South',
        'warehouse_name': 'South Warehouse',
        'quantity_on_hand': quantity
    }
    
    forecast = {
        'product_id': 'PROD-TEST',
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
            'supplier_name': 'Acme Supplies',
            'reliability_score': 0.95,
            'avg_lead_time_days': 7,
            'defect_rate': 0.01
        }
    ]
    
    decision = generate_purchase_order_decision(
        inventory_item=inventory_item,
        forecast=forecast,
        suppliers=suppliers,
        forecast_accuracy=0.12
    )
    
    assert decision is not None
    rationale = decision['rationale']
    
    # Rationale should mention the SKU
    assert 'SKU-ABC-123' in rationale, "Rationale should mention the SKU"
    
    # Rationale should mention inventory levels
    assert str(quantity) in rationale or 'inventory' in rationale.lower(), \
        "Rationale should mention current inventory"
    
    # Rationale should mention reorder point
    assert str(reorder_point) in rationale or 'reorder point' in rationale.lower(), \
        "Rationale should mention reorder point"
    
    # Rationale should mention the supplier
    assert 'Acme Supplies' in rationale or 'supplier' in rationale.lower(), \
        "Rationale should mention the selected supplier"


def test_rationale_with_forecast():
    """
    Test that rationale includes forecast information when available
    """
    inventory_item = {
        'product_id': 'PROD-TEST',
        'sku': 'SKU-TEST',
        'product_name': 'Test Product',
        'category': 'Test',
        'unit_cost': 50.0,
        'reorder_point': 100,
        'reorder_quantity': 200,
        'inventory_id': 'INV-TEST',
        'warehouse_id': 'WH1_South',
        'warehouse_name': 'South Warehouse',
        'quantity_on_hand': 50
    }
    
    forecast = {
        'product_id': 'PROD-TEST',
        'warehouse_id': 'WH1_South',
        'forecast_horizon_days': 30,
        'predicted_demand': 450,
        'confidence_interval_lower': 360,
        'confidence_interval_upper': 540,
        'confidence_level': 0.95
    }
    
    suppliers = [
        {
            'supplier_id': 'SUP-001',
            'supplier_name': 'Test Supplier',
            'reliability_score': 0.90,
            'avg_lead_time_days': 10,
            'defect_rate': 0.02
        }
    ]
    
    decision = generate_purchase_order_decision(
        inventory_item=inventory_item,
        forecast=forecast,
        suppliers=suppliers,
        forecast_accuracy=0.10
    )
    
    assert decision is not None
    rationale = decision['rationale']
    
    # Should mention forecast
    assert 'forecast' in rationale.lower() or '450' in rationale, \
        "Rationale should mention forecast when available"
    
    # Should mention confidence interval
    assert 'confidence' in rationale.lower() or '360' in rationale or '540' in rationale, \
        "Rationale should mention confidence interval"


def test_rationale_without_forecast():
    """
    Test that rationale is still complete without forecast data
    """
    inventory_item = {
        'product_id': 'PROD-TEST',
        'sku': 'SKU-TEST',
        'product_name': 'Test Product',
        'category': 'Test',
        'unit_cost': 50.0,
        'reorder_point': 100,
        'reorder_quantity': 200,
        'inventory_id': 'INV-TEST',
        'warehouse_id': 'WH1_South',
        'warehouse_name': 'South Warehouse',
        'quantity_on_hand': 50
    }
    
    suppliers = [
        {
            'supplier_id': 'SUP-001',
            'supplier_name': 'Test Supplier',
            'reliability_score': 0.90,
            'avg_lead_time_days': 10,
            'defect_rate': 0.02
        }
    ]
    
    # No forecast provided
    decision = generate_purchase_order_decision(
        inventory_item=inventory_item,
        forecast=None,
        suppliers=suppliers,
        forecast_accuracy=None
    )
    
    assert decision is not None
    rationale = decision['rationale']
    
    # Should still have meaningful rationale
    assert len(rationale) > 50, "Rationale should be substantial even without forecast"
    assert 'SKU-TEST' in rationale, "Should mention SKU"
    assert 'reorder' in rationale.lower(), "Should mention reorder logic"
    assert 'Test Supplier' in rationale, "Should mention supplier"


def test_rationale_mentions_supplier_metrics():
    """
    Test that rationale includes supplier performance metrics
    """
    inventory_item = {
        'product_id': 'PROD-TEST',
        'sku': 'SKU-TEST',
        'product_name': 'Test Product',
        'category': 'Test',
        'unit_cost': 50.0,
        'reorder_point': 100,
        'reorder_quantity': 200,
        'inventory_id': 'INV-TEST',
        'warehouse_id': 'WH1_South',
        'warehouse_name': 'South Warehouse',
        'quantity_on_hand': 50
    }
    
    suppliers = [
        {
            'supplier_id': 'SUP-001',
            'supplier_name': 'Premium Supplier',
            'reliability_score': 0.98,
            'avg_lead_time_days': 5,
            'defect_rate': 0.005
        }
    ]
    
    decision = generate_purchase_order_decision(
        inventory_item=inventory_item,
        forecast=None,
        suppliers=suppliers,
        forecast_accuracy=None
    )
    
    assert decision is not None
    rationale = decision['rationale'].lower()
    
    # Should mention reliability
    assert 'reliability' in rationale or '98%' in rationale or '0.98' in rationale, \
        "Rationale should mention supplier reliability"
    
    # Should mention lead time
    assert 'lead time' in rationale or '5 days' in rationale, \
        "Rationale should mention supplier lead time"
