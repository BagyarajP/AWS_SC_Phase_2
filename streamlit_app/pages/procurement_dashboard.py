"""
Procurement Manager Dashboard

Displays pending approvals, recent purchase orders, and supplier performance
for Procurement Managers.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

from utils.db_connection import (
    fetch_pending_approvals,
    approve_decision,
    reject_decision,
    fetch_recent_purchase_orders,
    fetch_supplier_performance
)


def show():
    """Display Procurement Manager dashboard"""
    
    st.title("📋 Procurement Manager Dashboard")
    st.markdown("---")
    
    # Pending Approvals Section
    show_pending_approvals()
    
    st.markdown("---")
    
    # Recent Purchase Orders Section
    show_recent_purchase_orders()
    
    st.markdown("---")
    
    # Supplier Performance Section
    show_supplier_performance()


def show_pending_approvals():
    """Display pending approval requests"""
    
    st.header("⚠️ Pending Approvals")
    
    approvals_df = fetch_pending_approvals('Procurement_Manager')
    
    if approvals_df is None or len(approvals_df) == 0:
        st.success("✅ No pending approvals. All decisions are up to date!")
        return
    
    st.info(f"You have **{len(approvals_df)}** pending approval(s)")
    
    for idx, approval in approvals_df.iterrows():
        decision_data = json.loads(approval['decision_data']) if isinstance(approval['decision_data'], str) else approval['decision_data']
        
        with st.expander(
            f"🔔 {approval['decision_type']} - Decision {approval['decision_id'][:12]}... "
            f"(Confidence: {approval['confidence_score']:.2f})",
            expanded=(idx == 0)  # Expand first item
        ):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Confidence Score", f"{approval['confidence_score']:.2f}")
                if 'po_value' in decision_data:
                    st.metric("PO Value", f"£{decision_data.get('po_value', 0):,.2f}")
            
            with col2:
                st.write("**Agent:**", approval['agent_name'])
                st.write("**Created:**", approval['created_at'].strftime('%Y-%m-%d %H:%M'))
            
            with col3:
                if 'supplier_name' in decision_data:
                    st.write("**Supplier:**", decision_data['supplier_name'])
                if 'quantity' in decision_data:
                    st.write("**Quantity:**", decision_data['quantity'])
            
            st.markdown("**Rationale:**")
            st.write(approval['rationale'])
            
            # Decision factors
            if 'factors' in decision_data:
                st.markdown("**Key Factors:**")
                factors = decision_data['factors']
                factor_cols = st.columns(len(factors))
                for i, (key, value) in enumerate(factors.items()):
                    with factor_cols[i]:
                        st.metric(key.replace('_', ' ').title(), value)
            
            # Action buttons
            st.markdown("---")
            col_a, col_b, col_c = st.columns([1, 1, 3])
            
            with col_a:
                if st.button("✅ Approve", key=f"approve_{approval['approval_id']}", type="primary"):
                    if approve_decision(approval['approval_id'], "current_user"):
                        st.success("Decision approved!")
                        st.rerun()
                    else:
                        st.error("Failed to approve decision")
            
            with col_b:
                if st.button("❌ Reject", key=f"reject_{approval['approval_id']}"):
                    rejection_reason = st.text_input(
                        "Rejection reason:",
                        key=f"reason_{approval['approval_id']}"
                    )
                    if rejection_reason:
                        if reject_decision(approval['approval_id'], "current_user", rejection_reason):
                            st.success("Decision rejected!")
                            st.rerun()
                        else:
                            st.error("Failed to reject decision")


def show_recent_purchase_orders():
    """Display recent purchase orders"""
    
    st.header("📦 Recent Purchase Orders")
    
    # Date range filter
    col1, col2 = st.columns([1, 3])
    with col1:
        days = st.selectbox("Time Period", [7, 14, 30, 60, 90], index=2)
    
    po_df = fetch_recent_purchase_orders(days)
    
    if po_df is None or len(po_df) == 0:
        st.warning("No purchase orders found for the selected period")
        return
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Orders", len(po_df))
    
    with col2:
        total_spend = po_df['total_amount'].sum()
        st.metric("Total Spend", f"£{total_spend:,.2f}")
    
    with col3:
        avg_po_value = po_df['total_amount'].mean()
        st.metric("Avg PO Value", f"£{avg_po_value:,.2f}")
    
    with col4:
        unique_suppliers = po_df['supplier_name'].nunique()
        st.metric("Suppliers", unique_suppliers)
    
    # Purchase orders table
    st.dataframe(
        po_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Spend by supplier chart
    if len(po_df) > 0:
        supplier_spend = po_df.groupby('supplier_name')['total_amount'].sum().sort_values(ascending=False).head(10)
        
        fig = px.bar(
            x=supplier_spend.values,
            y=supplier_spend.index,
            orientation='h',
            title="Top 10 Suppliers by Spend",
            labels={'x': 'Total Spend (£)', 'y': 'Supplier'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)


def show_supplier_performance():
    """Display supplier performance scorecards"""
    
    st.header("🏆 Supplier Performance")
    
    supplier_df = fetch_supplier_performance()
    
    if supplier_df is None or len(supplier_df) == 0:
        st.warning("No supplier data available")
        return
    
    # Filter by performance status
    col1, col2 = st.columns([1, 3])
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Good", "Alert"]
        )
    
    if status_filter != "All":
        supplier_df = supplier_df[supplier_df['performance_status'] == status_filter]
    
    # Display supplier cards
    for idx, supplier in supplier_df.iterrows():
        with st.container():
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"**{supplier['supplier_name']}**")
                if supplier['performance_status'] == 'Alert':
                    st.error("⚠️ Performance Alert")
                else:
                    st.success("✅ Good Performance")
            
            with col2:
                st.metric("Reliability", f"{supplier['reliability_score']:.2%}")
            
            with col3:
                st.metric("Avg Lead Time", f"{supplier['avg_lead_time_days']} days")
            
            with col4:
                st.metric("Defect Rate", f"{supplier['defect_rate']:.2%}")
        
        st.markdown("---")
    
    # Reliability distribution chart
    if len(supplier_df) > 0:
        fig = px.histogram(
            supplier_df,
            x='reliability_score',
            nbins=20,
            title="Supplier Reliability Distribution",
            labels={'reliability_score': 'Reliability Score', 'count': 'Number of Suppliers'}
        )
        st.plotly_chart(fig, use_container_width=True)
