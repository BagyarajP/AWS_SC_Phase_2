"""
Audit Log and Compliance Viewer

Provides search, filter, and export capabilities for audit log records.
Implements Requirements 5.1-5.7 for compliance and audit trail.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json

from utils.db_connection import execute_query, execute_update


def show():
    """Display audit log viewer"""
    
    st.title("📋 Audit Log & Compliance")
    st.markdown("---")
    
    # Search and filter section
    show_search_filters()
    
    st.markdown("---")
    
    # Audit log table
    show_audit_log_table()
    
    st.markdown("---")
    
    # Audit statistics
    show_audit_statistics()


def show_search_filters():
    """Display search and filter controls"""
    
    st.header("🔍 Search & Filter")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=30)
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now()
        )
    
    with col3:
        agent_filter = st.multiselect(
            "Agent",
            options=['Procurement_Agent', 'Inventory_Agent', 'Forecasting_Agent', 'All'],
            default=['All']
        )
    
    with col4:
        action_filter = st.multiselect(
            "Action Type",
            options=['CREATE_PURCHASE_ORDER', 'TRANSFER_INVENTORY', 'FORECAST_GENERATED', 
                    'APPROVAL', 'REJECTION', 'All'],
            default=['All']
        )
    
    # Store filters in session state
    st.session_state['audit_filters'] = {
        'start_date': start_date,
        'end_date': end_date,
        'agents': agent_filter,
        'actions': action_filter
    }


def fetch_audit_log(filters):
    """
    Fetch audit log records with filters.
    
    Args:
        filters: Dictionary with filter criteria
        
    Returns:
        DataFrame with audit log records
    """
    query = """
        SELECT 
            event_id,
            timestamp,
            agent_name,
            user_name,
            action_type,
            entity_type,
            entity_id,
            rationale,
            confidence_score,
            metadata
        FROM audit_log
        WHERE timestamp >= %s
        AND timestamp <= %s
    """
    
    params = [filters['start_date'], filters['end_date']]
    
    # Add agent filter
    if 'All' not in filters['agents']:
        placeholders = ','.join(['%s'] * len(filters['agents']))
        query += f" AND agent_name IN ({placeholders})"
        params.extend(filters['agents'])
    
    # Add action filter
    if 'All' not in filters['actions']:
        placeholders = ','.join(['%s'] * len(filters['actions']))
        query += f" AND action_type IN ({placeholders})"
        params.extend(filters['actions'])
    
    query += " ORDER BY timestamp DESC LIMIT 1000"
    
    return execute_query(query, tuple(params))


def show_audit_log_table():
    """Display audit log records in table format"""
    
    st.header("📊 Audit Log Records")
    
    # Get filters from session state
    filters = st.session_state.get('audit_filters', {
        'start_date': datetime.now() - timedelta(days=30),
        'end_date': datetime.now(),
        'agents': ['All'],
        'actions': ['All']
    })
    
    # Fetch audit log
    audit_df = fetch_audit_log(filters)
    
    if audit_df is None or len(audit_df) == 0:
        st.warning("No audit log records found for the selected filters")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Records", len(audit_df))
    
    with col2:
        agent_actions = len(audit_df[audit_df['agent_name'].notna()])
        st.metric("Agent Actions", agent_actions)
    
    with col3:
        user_actions = len(audit_df[audit_df['user_name'].notna()])
        st.metric("User Actions", user_actions)
    
    with col4:
        unique_entities = audit_df['entity_id'].nunique()
        st.metric("Unique Entities", unique_entities)
    
    # Export button
    if st.button("📥 Export to CSV"):
        csv = audit_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Display table with expandable details
    for idx, record in audit_df.iterrows():
        with st.expander(
            f"{record['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - "
            f"{record['action_type']} by {record['agent_name'] or record['user_name']}"
        ):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Event ID:**", record['event_id'])
                st.write("**Agent:**", record['agent_name'] or 'N/A')
                st.write("**User:**", record['user_name'] or 'N/A')
                st.write("**Action Type:**", record['action_type'])
            
            with col2:
                st.write("**Entity Type:**", record['entity_type'])
                st.write("**Entity ID:**", record['entity_id'])
                if record['confidence_score']:
                    st.write("**Confidence:**", f"{record['confidence_score']:.2f}")
            
            if record['rationale']:
                st.markdown("**Rationale:**")
                st.write(record['rationale'])
            
            if record['metadata']:
                st.markdown("**Metadata:**")
                try:
                    metadata = json.loads(record['metadata']) if isinstance(record['metadata'], str) else record['metadata']
                    st.json(metadata)
                except:
                    st.write(record['metadata'])


def show_audit_statistics():
    """Display audit log statistics and visualizations"""
    
    st.header("📈 Audit Statistics")
    
    filters = st.session_state.get('audit_filters', {
        'start_date': datetime.now() - timedelta(days=30),
        'end_date': datetime.now(),
        'agents': ['All'],
        'actions': ['All']
    })
    
    audit_df = fetch_audit_log(filters)
    
    if audit_df is None or len(audit_df) == 0:
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Actions by agent
        agent_counts = audit_df[audit_df['agent_name'].notna()]['agent_name'].value_counts()
        
        fig = px.pie(
            values=agent_counts.values,
            names=agent_counts.index,
            title="Actions by Agent"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Actions by type
        action_counts = audit_df['action_type'].value_counts().head(10)
        
        fig = px.bar(
            x=action_counts.values,
            y=action_counts.index,
            orientation='h',
            title="Top 10 Action Types",
            labels={'x': 'Count', 'y': 'Action Type'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Timeline of actions
    audit_df['date'] = pd.to_datetime(audit_df['timestamp']).dt.date
    daily_counts = audit_df.groupby('date').size().reset_index(name='count')
    
    fig = px.line(
        daily_counts,
        x='date',
        y='count',
        title="Audit Log Activity Over Time",
        labels={'date': 'Date', 'count': 'Number of Actions'}
    )
    st.plotly_chart(fig, use_container_width=True)


# Property test stubs for Task 11

def test_property_audit_log_search():
    """
    Property 22: Audit log search functionality
    
    For any search query with filters (date range, agent, user),
    results should include only records matching all specified filters.
    
    Validates: Requirements 5.4
    """
    # TODO: Implement property test
    pass


def test_property_human_action_logging():
    """
    Property 20: Human action audit logging
    
    For any human approval or rejection action, an audit log entry
    should be created with timestamp, user identifier, and reason.
    
    Validates: Requirements 5.2
    """
    # TODO: Implement property test
    pass


def test_property_data_modification_audit():
    """
    Property 21: Data modification audit trail
    
    For any data modification, an audit log entry should be created
    with before and after states.
    
    Validates: Requirements 5.3
    """
    # TODO: Implement property test
    pass


def test_property_approval_queue_persistence():
    """
    Property 18: Approval queue persistence
    
    For any decision requiring approval, a corresponding record
    should exist in the approval_queue table.
    
    Validates: Requirements 4.7
    """
    # TODO: Implement property test
    pass


if __name__ == '__main__':
    show()
