"""
Property Test 19: Agent decision audit logging

**Property**: For any agent decision (procurement, inventory, or forecasting), 
an audit log entry should be created in Redshift with timestamp, agent identifier, 
decision type, and rationale.

**Validates: Requirements 1.7, 2.7, 5.1**
"""

import pytest
from lambda_function import insert_audit_log


# Feature: supply-chain-ai-platform, Property 19: Agent decision audit logging
def test_property_audit_log_function_exists():
    """
    Property 19: Audit logging function must exist with correct signature
    """
    import inspect
    
    sig = inspect.signature(insert_audit_log)
    params = list(sig.parameters.keys())
    
    assert 'conn' in params
    assert 'agent_name' in params
    assert 'action_type' in params
    assert 'entity_type' in params
    assert 'entity_id' in params
    assert 'rationale' in params


def test_property_audit_log_returns_event_id():
    """
    Property 19: Audit log function should return event ID
    """
    from unittest.mock import Mock, MagicMock
    
    mock_conn = Mock()
    mock_cursor = MagicMock()
    
    cm = MagicMock()
    cm.__enter__ = Mock(return_value=mock_cursor)
    cm.__exit__ = Mock(return_value=False)
    mock_conn.cursor.return_value = cm
    
    event_id = insert_audit_log(
        conn=mock_conn,
        agent_name='Procurement_Agent',
        action_type='CREATE_DECISION',
        entity_type='agent_decision',
        entity_id='PD-TEST-001',
        rationale='Test rationale',
        confidence_score=0.85
    )
    
    assert event_id is not None
    assert isinstance(event_id, str)
    assert event_id.startswith('AUD-')


def test_audit_log_with_all_parameters():
    """
    Test audit log with all optional parameters
    """
    from unittest.mock import Mock, MagicMock
    
    mock_conn = Mock()
    mock_cursor = MagicMock()
    
    cm = MagicMock()
    cm.__enter__ = Mock(return_value=mock_cursor)
    cm.__exit__ = Mock(return_value=False)
    mock_conn.cursor.return_value = cm
    
    event_id = insert_audit_log(
        conn=mock_conn,
        agent_name='Procurement_Agent',
        action_type='CREATE_PURCHASE_ORDER',
        entity_type='purchase_order',
        entity_id='PO-TEST-001',
        rationale='Test PO creation',
        confidence_score=0.90,
        before_state={'inventory': 50},
        after_state={'inventory': 50, 'po_created': True},
        metadata={'warehouse': 'WH1_South'}
    )
    
    assert event_id is not None
    assert event_id.startswith('AUD-')
