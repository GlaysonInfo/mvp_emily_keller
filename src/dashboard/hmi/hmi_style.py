from __future__ import annotations

import streamlit as st


def apply_hmi_style() -> None:
    st.markdown(
        """
    <style>
    section[data-testid="stSidebar"] { background: #f3f6fa; }
    section[data-testid="stSidebar"] .stButton > button {
        width: 100%;
        min-height: 44px;
        border-radius: 8px;
        font-weight: 700;
    }
    .hmi-title {
        font-size: 1.35rem;
        font-weight: 800;
        margin-bottom: 0.25rem;
    }
    .hmi-subtitle {
        color: #6b7280;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }
    .hmi-status-ok,
    .hmi-status-warning,
    .hmi-status-critical {
        padding: 0.75rem 1rem;
        border-radius: 8px;
        font-weight: 800;
    }
    .hmi-status-ok {
        background: #e8f7ef;
        color: #047857;
    }
    .hmi-status-warning {
        background: #fff7ed;
        color: #c2410c;
    }
    .hmi-status-critical {
        background: #fee2e2;
        color: #b91c1c;
        font-weight: 900;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )
