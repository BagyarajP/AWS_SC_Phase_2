"""
Property Test 4: High-risk decision routing

**Property**: For any purchase order with value exceeding £10,000 OR confidence 
score below 0.7, the decision should be routed to the Human_Approval_Queue.

**Validates: Requirements 1.4, 2.4**
"""

import pytest
from hypothesis import given, strategies as st, settings
from lambda_function import check_approval_required


# Feature: supply-chain-ai-platform, Property 4: High-risk decision routing
@given(
    po_value=st.floats(min_value=0, max_value=50000, allow_nan=False, allow_infinity=False),
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100)
def test_property_high_risk_routing(po_value, confidence):
    """
    Property 4: High-risk decisions must be routed to approval queue
    
    This test verifies that decisions with high value (>£10,000) or
    low confidence (<0.7) are correctly identified as requiring approval.
    """
    decision = {
        'po_value': po_value,
        'confidence_score': confidence
    }
    
    requires_approval = check_approval_required(decision)
    
    # Check the routing logic
    if po_value > 10000 or confidence < 0.7:
        assert requires_approval is True, \
            f"Decision with PO value £{po_value:.2f} and confidence {confidence:.2f} should require approval"
    else:
        assert requires_approval is False, \
            f"Decision with PO value £{po_value:.2f} and confidence {confidence:.2f} should not require approval"


@given(
    po_value=st.floats(min_value=10001, max_value=50000),
    confidence=st.floats(min_value=0.7, max_value=1.0)
)
@settings(max_examples=100)
def test_property_high_value_requires_approval(po_value, confidence):
    """
    Property 4: High-value POs require approval regardless of confidence
    
    Even with high confidence, POs over £10,000 must be approved.
    """
    decision = {
        'po_value': po_value,
        'confidence_score': confidence
    }
    
    requires_approval = check_approval_required(decision)
    
    assert requires_approval is True, \
        f"PO with value £{po_value:.2f} should require approval even with confidence {confidence:.2f}"


@given(
    po_value=st.floats(min_value=0, max_value=10000),
    confidence=st.floats(min_value=0.0, max_value=0.69)
)
@settings(max_examples=100)
def test_property_low_confidence_requires_approval(po_value, confidence):
    """
    Property 4: Low-confidence decisions require approval regardless of value
    
    Even with low value, decisions with confidence <0.7 must be approved.
    """
    decision = {
        'po_value': po_value,
        'confidence_score': confidence
    }
    
    requires_approval = check_approval_required(decision)
    
    assert requires_approval is True, \
        f"Decision with confidence {confidence:.2f} should require approval even with PO value £{po_value:.2f}"


@given(
    po_value=st.floats(min_value=0, max_value=10000),
    confidence=st.floats(min_value=0.7, max_value=1.0)
)
@settings(max_examples=100)
def test_property_low_risk_auto_approved(po_value, confidence):
    """
    Property 4: Low-risk decisions should not require approval
    
    Decisions with value <=£10,000 and confidence >=0.7 should be auto-approved.
    """
    decision = {
        'po_value': po_value,
        'confidence_score': confidence
    }
    
    requires_approval = check_approval_required(decision)
    
    assert requires_approval is False, \
        f"Decision with PO value £{po_value:.2f} and confidence {confidence:.2f} should be auto-approved"


def test_boundary_value_exactly_10000():
    """
    Edge case: PO value exactly £10,000 should not require approval
    """
    decision = {
        'po_value': 10000.0,
        'confidence_score': 0.8
    }
    
    requires_approval = check_approval_required(decision)
    
    assert requires_approval is False, \
        "PO value of exactly £10,000 should not require approval (threshold is >10000)"


def test_boundary_value_exactly_0_7_confidence():
    """
    Edge case: Confidence exactly 0.7 should not require approval
    """
    decision = {
        'po_value': 5000.0,
        'confidence_score': 0.7
    }
    
    requires_approval = check_approval_required(decision)
    
    assert requires_approval is False, \
        "Confidence of exactly 0.7 should not require approval (threshold is <0.7)"


def test_both_thresholds_exceeded():
    """
    Test case where both thresholds are exceeded
    """
    decision = {
        'po_value': 15000.0,
        'confidence_score': 0.65
    }
    
    requires_approval = check_approval_required(decision)
    
    assert requires_approval is True, \
        "Decision exceeding both thresholds should require approval"


def test_minimal_values():
    """
    Test with minimal values (zero PO value, zero confidence)
    """
    decision = {
        'po_value': 0.0,
        'confidence_score': 0.0
    }
    
    requires_approval = check_approval_required(decision)
    
    assert requires_approval is True, \
        "Decision with zero confidence should require approval"


def test_maximum_safe_values():
    """
    Test with maximum values that don't require approval
    """
    decision = {
        'po_value': 9999.99,
        'confidence_score': 0.999
    }
    
    requires_approval = check_approval_required(decision)
    
    assert requires_approval is False, \
        "Decision just below thresholds should not require approval"
