"""
Property Test 31: Decision factor display

**Property**: For any agent decision, the explanation should include exactly 3 factors 
that influenced the decision, each with a relative importance weight.

**Validates: Requirements 12.2**
"""

import pytest
from hypothesis import given, strategies as st, settings
from lambda_function import generate_purchase_order_decision


# Feature: supply-chain-ai-platform, Property 31: Decision factor display
@given(
    quantity=st.integers(min_value=0, max_value=99),
    reorder_point=st.integers(min_value=100, max_value=200),
    demand=st.integers(min_value=100, max_value=1000)
)
@settings(max_examples=100)
def test_property_decision_has_three_factors(quantity, reorder_point, demand):
    """
    Property 31: Every decision must include exactly 3 top factors with importance weights
    """
    inventory_item = {
        'product_id': 'PROD-TEST',
        'sku': 'SKU-TEST',
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
        'predicted_demand': demand,
        'confidence_interval_lower': int(demand * 0.8),
        'confidence_interval_upper': int(demand * 1.2),
        'confidence_level': 0.95
    }
    
    suppliers = [
        {
            'supplier_id': 'SUP-001',
            'supplier_name': 'Test Supplier',
            'reliability_score': 0.90,
            'avg_lead_time_days': 7,
            'defect_rate': 0.01
        }
    ]
    
    decision = generate_purchase_order_decision(
        inventory_item=inventory_item,
        forecast=forecast,
        suppliers=suppliers,
        forecast_accuracy=0.10
    )
    
    assert decision is not None
    assert 'top_factors' in decision, "Decision must include top_factors"
    
    top_factors = decision['top_factors']
    assert isinstance(top_factors, list), "top_factors must be a list"
    assert len(top_factors) == 3, f"Must have exactly 3 factors, got {len(top_factors)}"
    
    # Verify each factor has required fields
    for i, factor in enumerate(top_factors):
        assert 'factor' in factor, f"Factor {i} must have 'factor' field"
        assert 'value' in factor, f"Factor {i} must have 'value' field"
        assert 'importance' in factor, f"Factor {i} must have 'importance' field"
        
        # Verify importance is a number between 0 and 1
        importance = factor['importance']
        assert isinstance(importance, (int, float)), f"Importance must be numeric, got {type(importance)}"
        assert 0 <= importance <= 1, f"Importance must be between 0 and 1, got {importance}"


def test_importance_weights_sum_to_one():
    """
    Test that importance weights sum to approximately 1.0
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
        'predicted_demand': 300,
        'confidence_interval_lower': 240,
        'confidence_interval_upper': 360,
        'confidence_level': 0.95
    }
    
    suppliers = [
        {
            'supplier_id': 'SUP-001',
            'supplier_name': 'Test Supplier',
            'reliability_score': 0.90,
            'avg_lead_time_days': 7,
            'defect_rate': 0.01
        }
    ]
    
    decision = generate_purchase_order_decision(
        inventory_item=inventory_item,
        forecast=forecast,
        suppliers=suppliers,
        forecast_accuracy=0.10
    )
    
    assert decision is not None
    top_factors = decision['top_factors']
    
    total_importance = sum(f['importance'] for f in top_factors)
    assert abs(total_importance - 1.0) < 0.01, \
        f"Importance weights should sum to ~1.0, got {total_importance}"


def test_factors_have_meaningful_names():
    """
    Test that factors have descriptive names
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
        'predicted_demand': 300,
        'confidence_interval_lower': 240,
        'confidence_interval_upper': 360,
        'confidence_level': 0.95
    }
    
    suppliers = [
        {
            'supplier_id': 'SUP-001',
            'supplier_name': 'Test Supplier',
            'reliability_score': 0.90,
            'avg_lead_time_days': 7,
            'defect_rate': 0.01
        }
    ]
    
    decision = generate_purchase_order_decision(
        inventory_item=inventory_item,
        forecast=forecast,
        suppliers=suppliers,
        forecast_accuracy=0.10
    )
    
    assert decision is not None
    top_factors = decision['top_factors']
    
    # Check that factor names are not empty
    for factor in top_factors:
        assert len(factor['factor']) > 0, "Factor name must not be empty"
        assert len(factor['value']) > 0, "Factor value must not be empty"
