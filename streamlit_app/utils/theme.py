"""
Glassy Theme Implementation

Provides custom CSS for a modern glassy UI theme with backdrop blur effects.
"""

import streamlit as st


def apply_glassy_theme():
    """Apply glassy theme CSS to the Streamlit app"""
    
    st.markdown("""
    <style>
        /* Main background gradient */
        .main {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        /* App container with glass effect */
        .stApp {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
        }
        
        /* Card/container styling */
        .css-1d391kg, .css-12oz5g7 {
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 20px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }
        
        /* Metric styling */
        .stMetric {
            background: rgba(255, 255, 255, 0.2);
            padding: 15px;
            border-radius: 10px;
            backdrop-filter: blur(5px);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            background: rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            backdrop-filter: blur(5px);
        }
        
        /* Button styling */
        .stButton > button {
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 8px;
            backdrop-filter: blur(5px);
            color: white;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            background: rgba(255, 255, 255, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.5);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }
        
        /* Sidebar styling */
        .css-1d391kg {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
        }
        
        /* Table styling */
        .dataframe {
            background: rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            backdrop-filter: blur(5px);
        }
        
        /* Header styling */
        h1, h2, h3 {
            color: white;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        /* Info/warning/error boxes */
        .stAlert {
            background: rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(10px);
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
    </style>
    """, unsafe_allow_html=True)
