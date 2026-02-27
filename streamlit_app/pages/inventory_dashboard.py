"""
Inventory Manager Dashboard

Displays pending transfer approvals, inventory levels, metrics, and forecast accuracy
for Inventory Managers.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json

from utils.db_connection import (
    fetch_pending_approvals,
    approve_decision,
    reject_decision,
    fetch_inventory_levels,
    fetch_inventory_metrics,
    fetch_forecast_accuracy
)


def show():
    """Display Inventory Manager dashboard"""
    
    st.title("📊 Inventory Manager Dashboard")
    st.markdown("---")
    
    # Pending Transfer Approvals Section
    show_pending_transfer_approvals()
    
    st.markdown("---")
    
    # Inventory Levels Section
    show_inventory_levels()
    
    st.markdown("---")
    
    # Inventory Metrics Section
    show_inventory_metrics()
    
    st.markdown("---")
    
    # Forecast Accuracy Section
    show_forecast_accuracy()


def show_pending_transfer_approvals():
    """Display pending transfer approval requests"""
    
    st.header("⚠️ Pending Transfer Approvals")
    
    approvals_df = fetch_pending_approvals('Inventory_Manager')
    
    if approvals_df is None or len(approvals_df) == 0:
        st.success("✅ No pending transfer approvals. All decisions are up to date!")
        return
    
    st.info(f"You have **{len(approvals_df)}** pending transfer approval(s)")
    
    for idx, approval in approvals_df.iterrows():
        decision_data = json.loads(approval['decision_data']) if isinstance(approval['decision_data'], str) else approval['decision_data']
        
        with st.expander(
            f"🔔 Transfer {decision_data.get('sku', 'N/A')} - "
            f"{decision_data.get('quantity', 0)} units "
            f"(Confidence: {approval['confidence_score']:.2f})",
            expanded=(idx == 0)
        ):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Quantity", decision_data.get('quantity', 0))
                st.write(f"**From:** {decision_data.get('source_warehouse_id', 'N/A')}")
                st.write(f"**To:** {decision_data.get('dest_warehouse_id', 'N/A')}")
            
            with col2:
                st.metric("Confidence Score", f"{approval['confidence_score']:.2f}")
                st.write("**SKU:**", decision_data.get('sku', 'N/A'))
            
            with col3:
                st.write("**Created:**", approval['created_at'].strftime('%Y-%m-%d %H:%M'))
                st.write("**Agent:**", approval['agent_name'])
            
            st.markdown("**Rationale:**")
            st.write(approval['rationale'])
            
            # Transfer factors
            if 'factors' in decision_data:
                st.markdown("**Transfer Factors:**")
                factors = decision_data['factors']
                factor_cols = st.columns(min(len(factors), 4))
                for i, (key, value) in enumerate(list(factors.items())[:4]):
                    with factor_cols[i]:
                        st.metric(key.replace('_', ' ').title(), value)
            
            # Action buttons
            st.markdown("---")
            col_a, col_b = st.columns(2)
            
            with col_a:
                if st.button("✅ Approve Transfer", key=f"approve_{approval['approval_id']}", type="primary"):
                    if approve_decision(approval['approval_id'], "current_user"):
                        st.success("Transfer approved!")
                        st.rerun()
                    else:
                        st.error("Failed to approve transfer")
            
            with col_b:
                if st.button("❌ Reject Transfer", key=f"reject_{approval['approval_id']}"):
                    rejection_reason = st.text_input(
                        "Rejection reason:",
                        key=f"reason_{approval['approval_id']}"
                    )
                    if rejection_reason:
                        if reject_decision(approval['approval_id'], "current_user", rejection_reason):
                            st.success("Transfer rejected!")
                            st.rerun()
                        else:
                            st.error("Failed to reject transfer")


def show_inventory_levels():
    """Display current inventory levels across warehouses"""
    
    st.header("📦 Inventory Levels by Warehouse")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    inventory_df = fetch_inventory_levels()
    
    if inventory_df is None or len(inventory_df) == 0:
        st.warning("No inventory data available")
        return
    
    with col1:
        warehouse_filter = st.multiselect(
            "Warehouse",
            options=inventory_df['warehouse_name'].unique(),
            default=inventory_df['warehouse_name'].unique()
        )
    
    with col2:
        category_filter = st.multiselect(
            "Category",
            options=inventory_df['category'].unique(),
            default=inventory_df['category'].unique()
        )
    
    with col3:
        status_filter = st.multiselect(
            "Stock Status",
            options=['Normal', 'Low', 'Critical'],
            default=['Normal', 'Low', 'Critical']
        )
    
    # Apply filters
    filtered_df = inventory_df[
        (inventory_df['warehouse_name'].isin(warehouse_filter)) &
        (inventory_df['category'].isin(category_filter)) &
        (inventory_df['stock_status'].isin(status_filter))
    ]
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_items = len(filtered_df)
        st.metric("Total SKUs", total_items)
    
    with col2:
        critical_count = len(filtered_df[filtered_df['stock_status'] == 'Critical'])
        st.metric("Critical Stock", critical_count, delta=f"-{critical_count}" if critical_count > 0 else "0")
    
    with col3:
        low_count = len(filtered_df[filtered_df['stock_status'] == 'Low'])
        st.metric("Low Stock", low_count)
    
    with col4:
        total_units = filtered_df['quantity_on_hand'].sum()
        st.metric("Total Units", f"{total_units:,}")
    
    # Inventory heatmap
    if len(filtered_df) > 0:
        # Aggregate by category and warehouse
        heatmap_data = filtered_df.groupby(['category', 'warehouse_name'])['quantity_on_hand'].sum().reset_index()
        heatmap_pivot = heatmap_data.pivot(index='category', columns='warehouse_name', values='quantity_on_hand')
        
        fig = px.imshow(
            heatmap_pivot,
            labels=dict(x="Warehouse", y="Category", color="Quantity"),
            title="Inventory Distribution Heatmap",
            aspect="auto",
            color_continuous_scale="Blues"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed inventory table
    st.subheader("Detailed Inventory")
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True
    )


def show_inventory_metrics():
    """Display inventory performance metrics"""
    
    st.header("📈 Inventory Performance Metrics")
    
    metrics = fetch_inventory_metrics()
    
    if not metrics:
        st.warning("No metrics data available")
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Inventory Turnover",
            f"{metrics.get('current_turnover', 0):.2f}",
            delta=f"+{metrics.get('improvement_pct', 0):.1f}% vs baseline"
        )
    
    with col2:
        st.metric(
            "Stockout Rate",
            f"{metrics.get('stockout_rate', 0):.2%}"
        )
    
    with col3:
        st.metric(
            "Slow-Moving SKUs",
            metrics.get('slow_moving_count', 0)
        )
    
    with col4:
        st.metric(
            "Low Stock Items",
            metrics.get('low_stock_count', 0)
        )
    
    # Trend chart (placeholder with sample data)
    st.subheader("Inventory Turnover Trend")
    
    # Sample trend data
    dates = pd.date_range(end=datetime.now(), periods=12, freq='M')
    baseline = [3.8] * 12
    current = [3.8, 3.9, 4.0, 4.0, 4.1, 4.1, 4.2, 4.2, 4.3, 4.2, 4.2, 4.2]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=baseline, name='Baseline', line=dict(dash='dash')))
    fig.add_trace(go.Scatter(x=dates, y=current, name='Current', line=dict(color='green')))
    fig.update_layout(
        title="Inventory Turnover Over Time",
        xaxis_title="Month",
        yaxis_title="Turnover Ratio",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)


def show_forecast_accuracy():
    """Display forecast accuracy metrics"""
    
    st.header("🎯 Forecast Accuracy")
    
    accuracy_df = fetch_forecast_accuracy()
    
    if accuracy_df is None or len(accuracy_df) == 0:
        st.warning("No forecast accuracy data available")
        return
    
    # MAPE by category
    st.subheader("MAPE by Category")
    
    fig = px.bar(
        accuracy_df,
        x='category',
        y='avg_mape',
        title="Mean Absolute Percentage Error by Category",
        labels={'avg_mape': 'MAPE (%)', 'category': 'Product Category'},
        color='avg_mape',
        color_continuous_scale='RdYlGn_r'
    )
    fig.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Target: 15%")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Accuracy table
    st.subheader("Forecast Accuracy Details")
    st.dataframe(
        accuracy_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Performance summary
    avg_mape = accuracy_df['avg_mape'].mean()
    categories_meeting_target = len(accuracy_df[accuracy_df['avg_mape'] < 15])
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Overall MAPE", f"{avg_mape:.2f}%")
    with col2:
        st.metric("Categories Meeting Target (<15%)", f"{categories_meeting_target}/{len(accuracy_df)}")
