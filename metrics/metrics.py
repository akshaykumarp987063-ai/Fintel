"""
UI-side session metrics for Fintel.

Stores analysis counts, per-run durations, and error counts in Streamlit
session state. Callers (dashboard/orchestrator wiring) own when to start,
finish, or fail a run. This module has no UI and no mock_data dependency.
"""

from __future__ import annotations

import time
from typing import Any

import streamlit as st

_METRICS_KEY = "_fintel_session_metrics"
_START_KEY = "_fintel_analysis_started_at"


def initialize_metrics() -> None:
    """Create session metric buckets once; later calls are no-ops."""
    if _METRICS_KEY not in st.session_state:
        st.session_state[_METRICS_KEY] = {
            "analysis_count": 0,
            "analysis_durations": [],
            "error_count": 0,
        }
    if _START_KEY not in st.session_state:
        st.session_state[_START_KEY] = None


def _store() -> dict[str, Any]:
    initialize_metrics()
    return st.session_state[_METRICS_KEY]


def record_analysis_start() -> None:
    """Mark the start of an analysis so duration can be measured."""
    initialize_metrics()
    st.session_state[_START_KEY] = time.perf_counter()


def record_analysis_end() -> None:
    """Record a successful analysis: duration (if started) and increment count."""
    metrics = _store()
    started_at = st.session_state.get(_START_KEY)
    if started_at is not None:
        duration_seconds = max(0.0, time.perf_counter() - float(started_at))
        metrics["analysis_durations"].append(duration_seconds)
    st.session_state[_START_KEY] = None
    metrics["analysis_count"] = int(metrics.get("analysis_count", 0)) + 1


def record_error() -> None:
    """Increment error_count for a failed analysis and clear any open timer."""
    metrics = _store()
    metrics["error_count"] = int(metrics.get("error_count", 0)) + 1
    st.session_state[_START_KEY] = None


def get_metrics_summary() -> dict[str, Any]:
    """Return a read-only snapshot of session metrics, including average duration."""
    metrics = _store()
    durations = [float(item) for item in list(metrics.get("analysis_durations") or [])]
    average = sum(durations) / len(durations) if durations else 0.0
    return {
        "analysis_count": int(metrics.get("analysis_count", 0)),
        "analysis_durations": durations,
        "average_analysis_time": average,
        "error_count": int(metrics.get("error_count", 0)),
    }
