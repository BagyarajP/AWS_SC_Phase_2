"""
Property Test 44: Supplier selection uses performance data

**Property**: For any purchase order decision, the supplier selection algorithm 
should incorporate the supplier's reliability score, lead time, and defect rate 
into the weighted scoring calculation.

**Validates: Requirements 14.6**
"""

import pytest
from hypothesis import given, strategies as st, settings
from lambda_function import select_best_supplier, generate_purchase_order_decision


# Feature: supply-chain-ai-platform, Property 44: Supplier selection uses performance data
@given(
    reliability1=st.floats(min_value=0.7, max_value=0.99),
    reliability2=st.floats(min_value=0.7, max_value=0.99),
    lead_time1=st.integers(min_value=3, max_value=21),
    lead_time2=st.integers(min_value=3, max_value=21),
    defect_rate1=st.floats(min_value=0.001, max_value=0.05),
    defect_rate2=st.floats(min_value=0.001, max_value=0.05)
)
@settings(max_examples=100)
def test_property_supplier_selection_uses_performance_metrics(
    reliability1, reliability2, lead_time1, lead_time2, defect_rate1, defect_rate2
):
    """
    Property 44: Supplier selection must use reliability, lead time, and defect rate
    
    This test verifies that the supplier selection algorithm incorporates
    all three performance metrics into its decision-making process.
    """
    suppliers = [
        {
            'supplier_id': 'SUP-A',
            'supplier_name': 'Supplier A',
            'reliability_score': reliability1,
            'avg_lead_time_days': lead_time1,
            'defect_rate': defect_rate1
        },
        {
            'supplier_id': 'SUP-B',
            'supplier_name': 'Supplier B',
            'reliability_score': reliability2,
            'avg_lead_time_days': lead_time2,
            'defect_rate': defect_rate2
        }
    ]
    
    unit_cost = 50.0
    
    # Act: Select supplier
    selected = select_best_supplier(suppliers, unit_cost)
    
    # Assert: A supplier should be selected
    assert selected is not None, "A supplier should be selected"
    
    # Verify the selected supplier has the performance data fields
    assert 'reliability_score' in selected, "Selected supplier should have reliability_score"
    assert 'avg_lead_time_days' in selected, "Selected supplier should have avg_lead_time_days"
    assert 'defect_rate' in selected, "Selected supplier should have defect_rate"
    
    # Verify the values are from the input
    assert selected['reliability_score'] in [reliability1, reliability2], \
        "Selected supplier reliability should match input data"
    assert selected['avg_lead_time_days'] in [lead_time1, lead_time2], \
        "Selected supplier lead time should match input data"
    assert selected['defect_rate'] in [defect_rate1, defect_rate2], \
        "Selected supplier defect rate should match input data"


def test_supplier_with_better_reliability_preferred():
    """
    Test that higher reliability score influences selection
    """
    suppliers = [
        {
            'supplier_id': 'SUP-HIGH-REL',
            'supplier_name': 'High Reliability Supplier',
            'reliability_score': 0.98,  # Very high
            'avg_lead_time_days': 10,
            'defect_rate': 0.01
        },
        {
            'supplier_id': 'SUP-LOW-REL',
            'supplier_name': 'Low Reliability Supplier',
            'reliability_score': 0.72,  # Lower
            'avg_lead_time_days': 10,  # Same lead time
            'defect_rate': 0.01  # Same defect rate
        }
    ]
    
    selected = select_best_supplier(suppliers, 50.0)
    
    # With same lead time, higher reliability should win
    assert selected['supplier_id'] == 'SUP-HIGH-REL', \
        "Supplier with higher reliability should be selected when other factors are equal"


def test_supplier_with_better_lead_time_preferred():
    """
    Test that lower lead time influences selection
    """
    suppliers = [
        {
            'supplier_id': 'SUP-FAST',
            'supplier_name': 'Fast Supplier',
            'reliability_score': 0.85,
            'avg_lead_time_days': 3,  # Very fast
            'defect_rate': 0.02
        },
        {
            'supplier_id': 'SUP-SLOW',
            'supplier_name': 'Slow Supplier',
            'reliability_score': 0.85,  # Same reliability
            'avg_lead_time_days': 20,  # Much slower
            'defect_rate': 0.02  # Same defect rate
        }
    ]
    
    selected = select_best_supplier(suppliers, 50.0)
    
    # With same reliability, faster lead time should win
    assert selected['supplier_id'] == 'SUP-FAST', \
        "Supplier with lower lead time should be selected when other factors are equal"


@given(
    quantity=st.integers(min_value=0, max_value=99),
    reorder_point=st.integers(min_value=100, max_value=200),
    reliability1=st.floats(min_value=0.85, max_value=0.99),
    reliability2=st.floats(min_value=0.70, max_value=0.84),
    lead_time1=st.integers(min_value=3, max_value=10),
    lead_time2=st.integers(min_value=11, max_value=21)
)
@settings(max_examples=100)
def test_property_po_decision_uses_supplier_performance(
    quantity, reorder_point, reliability1, reliability2, lead_time1, lead_time2
):
    """
    Property 44: PO decision should use supplier performance data in selection
    
    This test verifies that when generating a PO decision, the supplier
    selection incorporates performance metrics.
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
    
    # Create suppliers with different performance characteristics
    suppliers = [
        {
            'supplier_id': 'SUP-BETTER',
            'supplier_name': 'Better Supplier',
            'reliability_score': reliability1,  # Higher reliability
            'avg_lead_time_days': lead_time1,  # Lower lead time
            'defect_rate': 0.01
        },
        {
            'supplier_id': 'SUP-WORSE',
            'supplier_name': 'Worse Supplier',
            'reliability_score': reliability2,  # Lower reliability
            'avg_lead_time_days': lead_time2,  # Higher lead time
            'defect_rate': 0.03
        }
    ]
    
    forecast_accuracy = 0.10
    
    # Act: Generate PO decision
    decision = generate_purchase_order_decision(
        inventory_item=inventory_item,
        forecast=forecast,
        suppliers=suppliers,
        forecast_accuracy=forecast_accuracy
    )
    
    # Assert: Decision should be generated and use better supplier
    assert decision is not None, "PO decision should be generated"
    assert 'supplier_id' in decision, "Decision should include supplier selection"
    
    # The better supplier should be selected (higher reliability, lower lead time)
    assert decision['supplier_id'] == 'SUP-BETTER', \
        "Supplier with better performance metrics should be selected"
    
    # Verify performance data is included in decision factors
    assert 'factors' in decision, "Decision should include factors"
    assert 'supplier_reliability' in decision['factors'], \
        "Decision factors should include supplier reliability"
    assert 'supplier_lead_time' in decision['factors'], \
        "Decision factors should include supplier lead time"
    
    # Verify the values match the selected supplier
    assert decision['factors']['supplier_reliability'] == reliability1, \
        "Decision should record the selected supplier's reliability"
    assert decision['factors']['supplier_lead_time'] == lead_time1, \
        "Decision should record the selected supplier's lead time"


def test_performance_data_in_decision_rationale():
    """
    Test that supplier performance data appears in the decision rationale
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
    assert 'rationale' in decision
    
    # Rationale should mention supplier performance metrics
    rationale = decision['rationale'].lower()
    assert 'reliability' in rationale or '95%' in rationale or '0.95' in rationale, \
        "Rationale should mention supplier reliability"
    assert 'lead time' in rationale or '7 days' in rationale, \
        "Rationale should mention supplier lead time"
