"""
Ghent University styling utilities for Streamlit dashboard
"""

UGENT_COLORS = {
    "blue": "#1E64C8",
    "yellow": "#FFD200",
    "salmon_pink": "#E85E71",
    "white": "#FFFFFF",
    "background": "#F8F9FA",
    "text_dark": "#212529",
    "text_secondary": "#6C757D",
    "border": "#DEE2E6",
    "alert_critical": "#DC3545",
    "alert_warning": "#FFD200",
    "alert_success": "#28A745"
}

def get_ugent_css():
    """Returns CSS stylesheet for Ghent University branding"""
    return f"""
    <style>
        /* Main styling */
        .stApp {{
            background-color: {UGENT_COLORS['background']};
        }}
        
        /* Headers */
        h1 {{
            color: {UGENT_COLORS['blue']};
            font-family: 'Segoe UI', Arial, Helvetica, sans-serif;
            font-weight: bold;
            border-bottom: 3px solid {UGENT_COLORS['blue']};
            padding-bottom: 10px;
        }}
        
        h2 {{
            color: {UGENT_COLORS['blue']};
            font-family: 'Segoe UI', Arial, Helvetica, sans-serif;
            font-weight: bold;
        }}
        
        h3 {{
            color: {UGENT_COLORS['text_dark']};
            font-family: 'Segoe UI', Arial, Helvetica, sans-serif;
            font-weight: bold;
        }}
        
        /* Buttons */
        .stButton > button {{
            background-color: {UGENT_COLORS['blue']};
            color: white;
            border-radius: 5px;
            font-weight: bold;
            border: none;
        }}
        
        .stButton > button:hover {{
            background-color: #1554a0;
        }}
        
        /* Cards/Containers */
        .ugent-card {{
            background-color: {UGENT_COLORS['white']};
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 5px solid {UGENT_COLORS['blue']};
            margin: 10px 0;
        }}
        
        /* Alert boxes */
        .alert-critical {{
            background-color: {UGENT_COLORS['alert_critical']};
            color: white;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
            font-weight: bold;
        }}
        
        .alert-warning {{
            background-color: {UGENT_COLORS['alert_warning']};
            color: {UGENT_COLORS['text_dark']};
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
            font-weight: bold;
        }}
        
        .alert-success {{
            background-color: {UGENT_COLORS['alert_success']};
            color: white;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
            font-weight: bold;
        }}
        
        /* Progress indicators */
        .progress-step {{
            display: flex;
            align-items: center;
            margin: 10px 0;
        }}
        
        .progress-step-icon {{
            font-size: 24px;
            margin-right: 10px;
        }}
        
        /* Tables */
        .stDataFrame {{
            border: 1px solid {UGENT_COLORS['border']};
            border-radius: 5px;
        }}
        
        /* Sidebar */
        .css-1d391kg {{
            background-color: {UGENT_COLORS['white']};
        }}
        
        /* Paper-like report container */
        .report-container {{
            background-color: {UGENT_COLORS['white']};
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            max-width: 8.5in;
            margin: 0 auto;
            border: 1px solid {UGENT_COLORS['border']};
        }}
    </style>
    """

def inject_css():
    """Inject Ghent University CSS into Streamlit"""
    import streamlit as st
    st.markdown(get_ugent_css(), unsafe_allow_html=True)

