"""
Property Test 32: Explanation persistence

**Property**: For any agent decision, the natural language explanation should be 
stored in the rationale field of the audit_log table.

**Validates: Requirements 12.3**
"""

import pytest
from hypothesis import given, strategies as st, settings
from lambda_function import generate_purchase_order_decision


# Feature: supply-chain-ai-platform, Property 32: Explanation persistence
@given(
    quantity=st.integers(min_value=0, max_value=99),
    reorder_point=st.integers(min_value=100, max_value=200)
)
@settings(max_examples=100)
def test_property_explanation_in_rationale(quantity, reorder_point):
    """
    Property 32: Decision rationale should contain the explanation
    
    This test verifies that the rationale field contains a natural
    language explanation that would be stored in the audit log.
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
    assert 'rationale' in decision, "Decision must have rationale field"
    
    rationale = decision['rationale']
    assert isinstance(rationale, str), "Rationale must be a string"
    assert len(rationale) > 50, "Rationale should be substantial (>50 chars)"
    
    # Rationale should mention key decision factors
    assert 'inventory' in rationale.lower() or str(quantity) in rationale, \
        "Rationale should mention inventory level"
    assert 'reorder' in rationale.lower() or str(reorder_point) in rationale, \
        "Rationale should mention reorder point"


def test_rationale_is_natural_language():
    """
    Test that rationale is human-readable natural language
    """
    inventory_item = {
        'product_id': 'PROD-TEST',
        'sku': 'SKU-ABC-123',
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
        forecast_accuracy=0.10
    )
    
    assert decision is not None
    rationale = decision['rationale']
    
    # Check for natural language indicators
    assert any(word in rationale.lower() for word in ['is', 'are', 'will', 'should']), \
        "Rationale should use natural language verbs"
    
    # Should mention the SKU
    assert 'SKU-ABC-123' in rationale, "Rationale should mention the SKU"
    
    # Should mention the supplier
    assert 'Acme Supplies' in rationale, "Rationale should mention the supplier name"
