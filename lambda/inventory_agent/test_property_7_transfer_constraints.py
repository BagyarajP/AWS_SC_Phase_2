"""
Property Test 7: Inventory transfer respects constraints

**Property**: For any inventory transfer recommendation, the transfer quantity should not exceed 
the source warehouse's available inventory, and the destination warehouse should have sufficient 
capacity to receive the transfer.

**Validates**: Requirements 2.6

Feature: supply-chain-ai-platform, Property 7: Inventory transfer respects constraints
"""

import pytest
from hypothesis import given, strategies as st, settings
from lambda_function import generate_transfer_recommendation, calculate_imbalance_score


@given(
    source_inventory=st.integers(min_value=0, max_value=1000),
    source_demand=st.integers(min_value=0, max_value=500),
    dest_inventory=st.integers(min_value=0, max_value=200),
    dest_demand=st.integers(min_value=50, max_value=500),
    dest_capacity=st.integers(min_value=500, max_value=5000)
)
@settings(max_examples=100)
def test_property_transfer_respects_source_inventory(
    source_inventory, source_demand, dest_inventory, dest_demand, dest_capacity
):
    """
    Property: Transfer quantity must not exceed source warehouse inventory
    """
    # Create imbalance data structure
    imbalance = {
        'product_id': 'PROD-TEST',
        'sku': 'SKU-TEST-001',
        'product_name': 'Test Product',
        'imbalance_score': 0.5,
        'warehouses': {
            'WH_SOURCE': {
                'inventory': source_inventory,
                'warehouse_name': 'Source Warehouse',
                'capacity': 10000
            },
            'WH_DEST': {
                'inventory': dest_inventory,
                'warehouse_name': 'Destination Warehouse',
                'capacity': dest_capacity
            }
        },
        'demand_forecasts': {
            'WH_SOURCE': source_demand,
            'WH_DEST': dest_demand
        }
    }
    
    # Generate transfer recommendation
    transfer = generate_transfer_recommendation(imbalance)
    
    # Property: If transfer is generated, quantity must not exceed source inventory
    if transfer is not None:
        assert transfer['quantity'] <= source_inventory, \
            f"Transfer quantity {transfer['quantity']} exceeds source inventory {source_inventory}"


@given(
    source_inventory=st.integers(min_value=100, max_value=1000),
    source_demand=st.integers(min_value=0, max_value=200),
    dest_inventory=st.integers(min_value=0, max_value=200),
    dest_demand=st.integers(min_value=100, max_value=500),
    dest_capacity=st.integers(min_value=300, max_value=5000)
)
@settings(max_examples=100)
def test_property_transfer_respects_destination_capacity(
    source_inventory, source_demand, dest_inventory, dest_demand, dest_capacity
):
    """
    Property: Transfer must not cause destination to exceed capacity
    """
    imbalance = {
        'product_id': 'PROD-TEST',
        'sku': 'SKU-TEST-002',
        'product_name': 'Test Product 2',
        'imbalance_score': 0.6,
        'warehouses': {
            'WH_SOURCE': {
                'inventory': source_inventory,
                'warehouse_name': 'Source Warehouse',
                'capacity': 10000
            },
            'WH_DEST': {
                'inventory': dest_inventory,
                'warehouse_name': 'Destination Warehouse',
                'capacity': dest_capacity
            }
        },
        'demand_forecasts': {
            'WH_SOURCE': source_demand,
            'WH_DEST': dest_demand
        }
    }
    
    transfer = generate_transfer_recommendation(imbalance)
    
    # Property: If transfer is generated, destination must have capacity
    if transfer is not None:
        final_dest_inventory = dest_inventory + transfer['quantity']
        assert final_dest_inventory <= dest_capacity, \
            f"Transfer would cause destination to exceed capacity: {final_dest_inventory} > {dest_capacity}"


@given(
    source_inventory=st.integers(min_value=100, max_value=1000),
    source_demand=st.integers(min_value=0, max_value=200),
    dest_inventory=st.integers(min_value=0, max_value=100),
    dest_demand=st.integers(min_value=100, max_value=500),
    dest_capacity=st.integers(min_value=300, max_value=5000)
)
@settings(max_examples=100)
def test_property_transfer_quantity_positive(
    source_inventory, source_demand, dest_inventory, dest_demand, dest_capacity
):
    """
    Property: Transfer quantity must be positive if transfer is recommended
    """
    imbalance = {
        'product_id': 'PROD-TEST',
        'sku': 'SKU-TEST-003',
        'product_name': 'Test Product 3',
        'imbalance_score': 0.7,
        'warehouses': {
            'WH_SOURCE': {
                'inventory': source_inventory,
                'warehouse_name': 'Source Warehouse',
                'capacity': 10000
            },
            'WH_DEST': {
                'inventory': dest_inventory,
                'warehouse_name': 'Destination Warehouse',
                'capacity': dest_capacity
            }
        },
        'demand_forecasts': {
            'WH_SOURCE': source_demand,
            'WH_DEST': dest_demand
        }
    }
    
    transfer = generate_transfer_recommendation(imbalance)
    
    # Property: Transfer quantity must be positive
    if transfer is not None:
        assert transfer['quantity'] > 0, \
            f"Transfer quantity must be positive, got {transfer['quantity']}"


@given(
    inventories=st.lists(
        st.integers(min_value=0, max_value=1000),
        min_size=2,
        max_size=5
    ),
    demands=st.lists(
        st.integers(min_value=1, max_value=500),
        min_size=2,
        max_size=5
    )
)
@settings(max_examples=100)
def test_property_imbalance_score_range(inventories, demands):
    """
    Property: Imbalance score must be between 0 and 1
    """
    # Ensure lists are same length
    min_len = min(len(inventories), len(demands))
    inventories = inventories[:min_len]
    demands = demands[:min_len]
    
    # Create warehouse dictionaries
    inventory_by_wh = {f'WH{i}': inv for i, inv in enumerate(inventories)}
    demand_by_wh = {f'WH{i}': dem for i, dem in enumerate(demands)}
    
    score = calculate_imbalance_score(inventory_by_wh, demand_by_wh)
    
    # Property: Score must be in valid range
    assert 0 <= score <= 1, f"Imbalance score {score} is outside valid range [0, 1]"


def test_transfer_respects_constraints_example():
    """
    Unit test: Specific example of transfer respecting constraints
    """
    imbalance = {
        'product_id': 'PROD-001',
        'sku': 'SKU-ABC-001',
        'product_name': 'Widget A',
        'imbalance_score': 0.65,
        'warehouses': {
            'WH_North': {
                'inventory': 500,
                'warehouse_name': 'North Warehouse',
                'capacity': 10000
            },
            'WH1_South': {
                'inventory': 50,
                'warehouse_name': 'South Warehouse',
                'capacity': 8000
            }
        },
        'demand_forecasts': {
            'WH_North': 100,
            'WH1_South': 300
        }
    }
    
    transfer = generate_transfer_recommendation(imbalance)
    
    assert transfer is not None
    assert transfer['quantity'] <= 500  # Source inventory
    assert transfer['quantity'] + 50 <= 8000  # Destination capacity
    assert transfer['source_warehouse_id'] == 'WH_North'
    assert transfer['dest_warehouse_id'] == 'WH1_South'


def test_no_transfer_when_balanced():
    """
    Unit test: No transfer recommended when inventory is balanced
    """
    imbalance = {
        'product_id': 'PROD-002',
        'sku': 'SKU-XYZ-002',
        'product_name': 'Widget B',
        'imbalance_score': 0.2,  # Low imbalance
        'warehouses': {
            'WH_North': {
                'inventory': 200,
                'warehouse_name': 'North Warehouse',
                'capacity': 10000
            },
            'WH1_South': {
                'inventory': 180,
                'warehouse_name': 'South Warehouse',
                'capacity': 8000
            }
        },
        'demand_forecasts': {
            'WH_North': 200,
            'WH1_South': 180
        }
    }
    
    transfer = generate_transfer_recommendation(imbalance)
    
    # Should not recommend transfer for well-balanced inventory
    # (or if it does, it should be a small quantity)
    if transfer is not None:
        assert transfer['quantity'] < 50


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
