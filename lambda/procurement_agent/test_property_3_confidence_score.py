"""
Property Test 3: Confidence score validity

**Property**: For any agent decision, the confidence score should be a decimal 
value between 0 and 1 inclusive.

**Validates: Requirements 1.3, 2.3**
"""

import pytest
from hypothesis import given, strategies as st, settings
from lambda_function import generate_purchase_order_decision


# Feature: supply-chain-ai-platform, Property 3: Confidence score validity
@given(
    quantity=st.integers(min_value=0, max_value=199),
    reorder_point=st.integers(min_value=200, max_value=500),
    demand_30d=st.integers(min_value=1, max_value=2000),
    unit_cost=st.floats(min_value=1.0, max_value=500.0),
    reorder_quantity=st.integers(min_value=100, max_value=1000),
    reliability=st.floats(min_value=0.7, max_value=0.99),
    lead_time=st.integers(min_value=3, max_value=21),
    forecast_accuracy=st.one_of(
        st.none(),
        st.floats(min_value=0.01, max_value=0.50)
    )
)
@settings(max_examples=100)
def test_property_confidence_score_in_valid_range(
    quantity, reorder_point, demand_30d, unit_cost, reorder_quantity, 
    reliability, lead_time, forecast_accuracy
):
    """
    Property 3: Confidence score must be between 0 and 1 inclusive
    
    This test verifies that all procurement decisions include a confidence
    score that is a valid decimal value in the range [0, 1].
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
    
    # Act
    decision = generate_purchase_order_decision(
        inventory_item=inventory_item,
        forecast=forecast,
        suppliers=suppliers,
        forecast_accuracy=forecast_accuracy
    )
    
    # Assert
    assert decision is not None, "Decision should be generated for low inventory"
    assert 'confidence_score' in decision, "Decision must include confidence_score field"
    
    confidence = decision['confidence_score']
    
    # Check type
    assert isinstance(confidence, (int, float)), \
        f"Confidence score must be numeric, got {type(confidence)}"
    
    # Check range
    assert 0.0 <= confidence <= 1.0, \
        f"Confidence score must be between 0 and 1, got {confidence}"


@given(
    quantity=st.integers(min_value=0, max_value=50),
    reorder_point=st.integers(min_value=100, max_value=200),
    high_reliability=st.floats(min_value=0.90, max_value=0.99),
    low_mape=st.floats(min_value=0.01, max_value=0.10)
)
@settings(max_examples=100)
def test_property_high_confidence_for_good_conditions(
    quantity, reorder_point, high_reliability, low_mape
):
    """
    Property 3: High confidence when conditions are favorable
    
    When forecast accuracy is high (low MAPE) and supplier reliability is high,
    confidence score should be relatively high.
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
            'supplier_name': 'Reliable Supplier',
            'reliability_score': high_reliability,
            'avg_lead_time_days': 5,
            'defect_rate': 0.005
        }
    ]
    
    decision = generate_purchase_order_decision(
        inventory_item=inventory_item,
        forecast=forecast,
        suppliers=suppliers,
        forecast_accuracy=low_mape
    )
    
    assert decision is not None
    confidence = decision['confidence_score']
    
    # With high reliability and low MAPE, confidence should be reasonably high
    assert confidence >= 0.70, \
        f"Confidence should be high (>=0.70) with good conditions, got {confidence}"
    assert confidence <= 1.0, "Confidence must not exceed 1.0"


@given(
    quantity=st.integers(min_value=0, max_value=50),
    reorder_point=st.integers(min_value=100, max_value=200),
    low_reliability=st.floats(min_value=0.70, max_value=0.80),
    high_mape=st.floats(min_value=0.20, max_value=0.40)
)
@settings(max_examples=100)
def test_property_lower_confidence_for_poor_conditions(
    quantity, reorder_point, low_reliability, high_mape
):
    """
    Property 3: Lower confidence when conditions are less favorable
    
    When forecast accuracy is poor (high MAPE) and supplier reliability is lower,
    confidence score should be lower.
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
        'confidence_interval_lower': 150,
        'confidence_interval_upper': 450,
        'confidence_level': 0.95
    }
    
    suppliers = [
        {
            'supplier_id': 'SUP-001',
            'supplier_name': 'Less Reliable Supplier',
            'reliability_score': low_reliability,
            'avg_lead_time_days': 18,
            'defect_rate': 0.04
        }
    ]
    
    decision = generate_purchase_order_decision(
        inventory_item=inventory_item,
        forecast=forecast,
        suppliers=suppliers,
        forecast_accuracy=high_mape
    )
    
    assert decision is not None
    confidence = decision['confidence_score']
    
    # With poor conditions, confidence should be lower
    assert confidence >= 0.0, "Confidence must not be negative"
    assert confidence < 0.90, \
        f"Confidence should be lower (<0.90) with poor conditions, got {confidence}"


def test_confidence_score_without_forecast():
    """
    Test confidence score when no forecast data is available
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
            'reliability_score': 0.85,
            'avg_lead_time_days': 10,
            'defect_rate': 0.02
        }
    ]
    
    decision = generate_purchase_order_decision(
        inventory_item=inventory_item,
        forecast=None,
        suppliers=suppliers,
        forecast_accuracy=None
    )
    
    assert decision is not None
    confidence = decision['confidence_score']
    
    # Should still have valid confidence score
    assert 0.0 <= confidence <= 1.0, \
        f"Confidence must be in [0,1] even without forecast, got {confidence}"


def test_confidence_score_is_numeric():
    """
    Test that confidence score is always a numeric type
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
        forecast_accuracy=0.12
    )
    
    assert decision is not None
    confidence = decision['confidence_score']
    
    # Must be numeric (int or float)
    assert isinstance(confidence, (int, float)), \
        f"Confidence must be numeric, got type {type(confidence)}"
    
    # Should not be NaN or infinity
    import math
    assert not math.isnan(confidence), "Confidence must not be NaN"
    assert not math.isinf(confidence), "Confidence must not be infinity"
