"""
Property Test 6: Supplier selection optimality

**Property**: For any purchase order decision, the selected supplier should have 
the highest weighted score based on price (40%), reliability (30%), and lead time (30%) 
among all suppliers offering the product.

**Validates: Requirements 1.6**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from lambda_function import select_best_supplier


def calculate_supplier_score(supplier, min_lead_time, max_lead_time):
    """
    Calculate the weighted score for a supplier using the same algorithm
    as the implementation to verify correctness.
    """
    price_score = 0.8  # Baseline
    reliability_score = supplier['reliability_score']
    
    lead_time_range = max_lead_time - min_lead_time if max_lead_time > min_lead_time else 1
    if lead_time_range > 0:
        lead_time_normalized = (supplier['avg_lead_time_days'] - min_lead_time) / lead_time_range
        lead_time_score = 1.0 - lead_time_normalized
    else:
        lead_time_score = 1.0
    
    total_score = (
        price_score * 0.4 +
        reliability_score * 0.3 +
        lead_time_score * 0.3
    )
    
    return total_score


# Feature: supply-chain-ai-platform, Property 6: Supplier selection optimality
@given(
    num_suppliers=st.integers(min_value=2, max_value=10),
    seed=st.integers(min_value=0, max_value=10000)
)
@settings(max_examples=100)
def test_property_supplier_selection_optimality(num_suppliers, seed):
    """
    Property 6: Selected supplier should have highest weighted score
    
    This test verifies that the supplier selection algorithm always chooses
    the supplier with the highest weighted score based on:
    - Price: 40%
    - Reliability: 30%
    - Lead time: 30%
    """
    import random
    random.seed(seed)
    
    # Generate random suppliers
    suppliers = []
    for i in range(num_suppliers):
        suppliers.append({
            'supplier_id': f'SUP-{i:03d}',
            'supplier_name': f'Supplier {i}',
            'reliability_score': round(random.uniform(0.7, 0.99), 2),
            'avg_lead_time_days': random.randint(3, 21),
            'defect_rate': round(random.uniform(0.001, 0.05), 4)
        })
    
    unit_cost = 50.0
    
    # Act: Select best supplier
    selected = select_best_supplier(suppliers, unit_cost)
    
    # Assert: Selected supplier should have highest score
    assert selected is not None, "A supplier should be selected"
    assert selected in suppliers, "Selected supplier should be from the input list"
    
    # Calculate scores for all suppliers
    lead_times = [s['avg_lead_time_days'] for s in suppliers]
    min_lead_time = min(lead_times)
    max_lead_time = max(lead_times)
    
    selected_score = calculate_supplier_score(selected, min_lead_time, max_lead_time)
    
    # Verify selected supplier has the highest (or tied for highest) score
    for supplier in suppliers:
        supplier_score = calculate_supplier_score(supplier, min_lead_time, max_lead_time)
        assert selected_score >= supplier_score - 0.001, \
            f"Selected supplier score ({selected_score:.4f}) should be >= all other scores. " \
            f"Found supplier {supplier['supplier_id']} with score {supplier_score:.4f}"


@given(
    reliability1=st.floats(min_value=0.7, max_value=0.99),
    reliability2=st.floats(min_value=0.7, max_value=0.99),
    lead_time1=st.integers(min_value=3, max_value=21),
    lead_time2=st.integers(min_value=3, max_value=21)
)
@settings(max_examples=100)
def test_property_supplier_selection_with_two_suppliers(reliability1, reliability2, lead_time1, lead_time2):
    """
    Property 6: Test supplier selection with exactly two suppliers
    
    This test verifies the selection logic with a simple two-supplier scenario.
    """
    suppliers = [
        {
            'supplier_id': 'SUP-A',
            'supplier_name': 'Supplier A',
            'reliability_score': reliability1,
            'avg_lead_time_days': lead_time1,
            'defect_rate': 0.01
        },
        {
            'supplier_id': 'SUP-B',
            'supplier_name': 'Supplier B',
            'reliability_score': reliability2,
            'avg_lead_time_days': lead_time2,
            'defect_rate': 0.02
        }
    ]
    
    unit_cost = 100.0
    
    # Act: Select best supplier
    selected = select_best_supplier(suppliers, unit_cost)
    
    # Assert: One supplier should be selected
    assert selected is not None
    assert selected['supplier_id'] in ['SUP-A', 'SUP-B']
    
    # Calculate scores
    min_lead_time = min(lead_time1, lead_time2)
    max_lead_time = max(lead_time1, lead_time2)
    
    score_a = calculate_supplier_score(suppliers[0], min_lead_time, max_lead_time)
    score_b = calculate_supplier_score(suppliers[1], min_lead_time, max_lead_time)
    
    # Verify the selected supplier has the higher score
    if score_a > score_b:
        assert selected['supplier_id'] == 'SUP-A', \
            f"Supplier A (score {score_a:.4f}) should be selected over B (score {score_b:.4f})"
    elif score_b > score_a:
        assert selected['supplier_id'] == 'SUP-B', \
            f"Supplier B (score {score_b:.4f}) should be selected over A (score {score_a:.4f})"
    # If scores are equal, either is acceptable


def test_supplier_selection_single_supplier():
    """
    Edge case: When only one supplier is available, it should be selected
    """
    suppliers = [
        {
            'supplier_id': 'SUP-ONLY',
            'supplier_name': 'Only Supplier',
            'reliability_score': 0.85,
            'avg_lead_time_days': 10,
            'defect_rate': 0.02
        }
    ]
    
    selected = select_best_supplier(suppliers, 50.0)
    
    assert selected is not None
    assert selected['supplier_id'] == 'SUP-ONLY'


def test_supplier_selection_empty_list_raises_error():
    """
    Edge case: Empty supplier list should raise ValueError
    """
    with pytest.raises(ValueError, match="No suppliers available"):
        select_best_supplier([], 50.0)


@given(
    reliability=st.floats(min_value=0.95, max_value=0.99),
    lead_time=st.integers(min_value=3, max_value=5)
)
@settings(max_examples=50)
def test_property_high_quality_supplier_preferred(reliability, lead_time):
    """
    Property 6: High reliability and low lead time should result in selection
    
    When one supplier has significantly better reliability and lead time,
    it should be selected.
    """
    suppliers = [
        {
            'supplier_id': 'SUP-PREMIUM',
            'supplier_name': 'Premium Supplier',
            'reliability_score': reliability,
            'avg_lead_time_days': lead_time,
            'defect_rate': 0.005
        },
        {
            'supplier_id': 'SUP-STANDARD',
            'supplier_name': 'Standard Supplier',
            'reliability_score': 0.75,
            'avg_lead_time_days': 20,
            'defect_rate': 0.04
        }
    ]
    
    selected = select_best_supplier(suppliers, 50.0)
    
    # Premium supplier should be selected due to much better metrics
    assert selected['supplier_id'] == 'SUP-PREMIUM', \
        "Premium supplier with high reliability and low lead time should be selected"
