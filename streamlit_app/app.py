"""
Supply Chain AI Platform - Streamlit Dashboard
Main application with role-based routing and AI chat interface
"""

import streamlit as st
import os
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Supply Chain AI Platform",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for glassy theme
def load_css():
    st.markdown("""
    <style>
    /* Glassy background */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Glassy cards */
    .css-1r6slb0 {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* Metrics */
    .css-1xarl3l {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        border-radius: 8px;
        padding: 15px;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(15px);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: white;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    /* Chat interface */
    .chat-message {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'role' not in st.session_state:
    st.session_state.role = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Load CSS
load_css()

# Sidebar
with st.sidebar:
    st.title("📦 Supply Chain AI")
    st.markdown("---")
    
    # Role selection
    st.subheader("Select Role")
    role = st.selectbox(
        "Role",
        ["Select a role...", "Procurement Manager", "Inventory Manager"],
        key="role_selector"
    )
    
    if role != "Select a role...":
        st.session_state.role = role
    
    st.markdown("---")
    
    # AI Chat Interface
    st.subheader("🤖 AI Assistant")
    
    user_query = st.text_area(
        "Ask the AI assistant:",
        placeholder="e.g., What products need reordering?",
        height=100
    )
    
    if st.button("Send", use_container_width=True):
        if user_query:
            # TODO: Integrate with Bedrock Runtime API
            st.session_state.chat_history.append({
                'user': user_query,
                'ai': 'AI response will be integrated with Bedrock Agent'
            })
            st.rerun()
    
    # Display chat history
    if st.session_state.chat_history:
        st.markdown("### Recent Conversations")
        for chat in st.session_state.chat_history[-3:]:
            st.markdown(f"**You:** {chat['user']}")
            st.markdown(f"**AI:** {chat['ai']}")
            st.markdown("---")
    
    # Filters
    st.markdown("---")
    st.subheader("Filters")
    
    date_range = st.date_input(
        "Date Range",
        value=(datetime.now() - timedelta(days=30), datetime.now()),
        key="date_range"
    )
    
    warehouse_filter = st.multiselect(
        "Warehouse",
        ["All", "South", "Midland", "North"],
        default=["All"]
    )
    
    sku_search = st.text_input("Search SKU", placeholder="Enter product ID or name")

# Main content
if not st.session_state.role or st.session_state.role == "Select a role...":
    # Welcome screen
    st.title("Welcome to Supply Chain AI Platform")
    st.markdown("### Powered by AWS Bedrock & Claude 3.5 Sonnet")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 🛒 Procurement Manager
        - Monitor inventory levels
        - Review AI-generated purchase orders
        - Approve/reject procurement decisions
        - Analyze supplier performance
        """)
    
    with col2:
        st.markdown("""
        #### 📊 Inventory Manager
        - View inventory across warehouses
        - Review transfer recommendations
        - Monitor forecast accuracy
        - Track inventory metrics
        """)
    
    st.info("👈 Select your role from the sidebar to get started")

elif st.session_state.role == "Procurement Manager":
    # Procurement Manager Dashboard
    st.title("Procurement Manager Dashboard")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Pending Approvals", "12", "+3")
    with col2:
        st.metric("Total Spend (30d)", "£245,320", "+15%")
    with col3:
        st.metric("Active Suppliers", "487", "-2")
    with col4:
        st.metric("Avg PO Value", "£20,443", "+8%")
    
    st.markdown("---")
    
    # AI Insights Section
    st.subheader("🤖 AI-Powered Insights")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Generate Recommendations", use_container_width=True):
            st.info("Invoking Procurement Bedrock Agent...")
            # TODO: Integrate with Bedrock Agent
    
    with col2:
        if st.button("Explain Decisions", use_container_width=True):
            st.info("Generating AI explanations...")
            # TODO: Integrate with Bedrock Runtime API
    
    st.markdown("---")
    
    # Pending Approvals
    st.subheader("Pending Approvals")
    st.info("TODO: Query approval_queue table via Redshift Data API")
    
    # Recent Purchase Orders
    st.subheader("Recent Purchase Orders")
    st.info("TODO: Query purchase_order_header table")
    
    # Supplier Performance
    st.subheader("Supplier Performance")
    st.info("TODO: Calculate and display supplier metrics")

elif st.session_state.role == "Inventory Manager":
    # Inventory Manager Dashboard
    st.title("Inventory Manager Dashboard")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Inventory Turnover", "8.5", "+0.3")
    with col2:
        st.metric("Stockout Rate", "2.1%", "-0.5%")
    with col3:
        st.metric("Pending Transfers", "7", "+2")
    with col4:
        st.metric("Forecast MAPE", "12.3%", "-1.2%")
    
    st.markdown("---")
    
    # AI Insights Section
    st.subheader("🤖 AI-Powered Insights")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Generate Transfer Recommendations", use_container_width=True):
            st.info("Invoking Inventory Bedrock Agent...")
            # TODO: Integrate with Bedrock Agent
    
    with col2:
        if st.button("Explain Imbalances", use_container_width=True):
            st.info("Generating AI analysis...")
            # TODO: Integrate with Bedrock Runtime API
    
    st.markdown("---")
    
    # Pending Transfer Approvals
    st.subheader("Pending Transfer Approvals")
    st.info("TODO: Query approval_queue for Inventory_Manager role")
    
    # Inventory Levels
    st.subheader("Inventory Levels by Warehouse")
    st.info("TODO: Query inventory table and create heatmap")
    
    # Forecast Accuracy
    st.subheader("Forecast Accuracy")
    st.info("TODO: Query forecast_accuracy table and visualize")

# Footer
st.markdown("---")
st.markdown("Supply Chain AI Platform | Powered by AWS Bedrock (Claude 3.5 Sonnet) | Region: us-east-1")
