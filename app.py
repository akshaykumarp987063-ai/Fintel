"""
Fintel — Person 5 entry point.

Owns Streamlit UI, dashboard, UX, explainability display, and session metrics.
Does not own backend, AI agents, RAG, or portfolio logic (other teammates).

Until integration, this app renders against mock_data only.
"""

import streamlit as st

from metrics.metrics import initialize_metrics
from ui.dashboard import render_dashboard


def main() -> None:
    st.set_page_config(page_title="Fintel", layout="wide")
    initialize_metrics()
    render_dashboard()


if __name__ == "__main__":
    main()
