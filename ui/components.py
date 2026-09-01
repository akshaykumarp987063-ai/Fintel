"""Reusable Streamlit presentation components for the Fintel dashboard."""

from __future__ import annotations

from html import escape
from typing import Any, Mapping, Sequence

import streamlit as st

_UNAVAILABLE = "—"

_REC_COLORS = {
    "buy": ("#065f46", "#d1fae5"),
    "hold": ("#92400e", "#fef3c7"),
    "sell": ("#991b1b", "#fee2e2"),
}


def _text(value: Any, fallback: str = _UNAVAILABLE) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return escape(text) if text else fallback


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _format_confidence(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _UNAVAILABLE
    if 0.0 <= number <= 1.0:
        number *= 100.0
    return f"{number:.0f}%"


def _format_money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return _text(value)


def _format_exposure(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _text(value)
    if abs(number) <= 1.0:
        number *= 100.0
    return f"{number:.1f}%"


def _recommendation_style(label: str) -> tuple[str, str]:
    return _REC_COLORS.get(label.strip().lower(), ("#1e3a5f", "#e8eef5"))


def _inject_styles() -> None:
    if st.session_state.get("_fintel_component_styles"):
        return
    st.session_state["_fintel_component_styles"] = True
    st.markdown(
        """
        <style>
          .fintel-header { padding: 0.2rem 0 1rem 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 1.25rem; }
          .fintel-kicker { font-size: 0.72rem; letter-spacing: 0.16em; text-transform: uppercase; color: #64748b; margin: 0; }
          .fintel-title { font-size: 2rem; font-weight: 650; color: #0f172a; margin: 0.15rem 0 0.25rem 0; }
          .fintel-subtitle { color: #475569; margin: 0; font-size: 0.98rem; }
          .fintel-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1rem 1.1rem; margin-bottom: 0.75rem; }
          .fintel-label { font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase; color: #64748b; margin: 0 0 0.35rem 0; }
          .fintel-value { font-size: 1.25rem; font-weight: 650; color: #0f172a; margin: 0; }
          .fintel-desc { color: #64748b; font-size: 0.85rem; margin: 0.4rem 0 0 0; }
          .fintel-agent-name { font-weight: 650; color: #0f172a; margin: 0 0 0.5rem 0; }
          .fintel-summary { color: #334155; font-size: 0.92rem; line-height: 1.45; margin: 0.65rem 0 0 0; }
          .fintel-badge { display: inline-block; padding: 0.2rem 0.65rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.04em; }
          .fintel-final { border: 1px solid #cbd5e1; border-left: 6px solid #1e3a5f; background: #ffffff; border-radius: 12px; padding: 1.15rem 1.25rem; margin-bottom: 0.75rem; }
          .fintel-final-rec { font-size: 1.75rem; font-weight: 750; letter-spacing: 0.04em; margin: 0.2rem 0; }
          .fintel-evidence-title { font-weight: 650; color: #0f172a; margin: 0; }
          .fintel-source { color: #64748b; font-size: 0.8rem; margin: 0.15rem 0 0.45rem 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(
    title: str = "Fintel",
    subtitle: str = "Portfolio insight, market signals, and explainable recommendations",
) -> None:
    """Display the dashboard title and subtitle."""
    _inject_styles()
    st.markdown(
        f"""
        <div class="fintel-header">
          <p class="fintel-kicker">Investment workstation</p>
          <h1 class="fintel-title">{_text(title, "Fintel")}</h1>
          <p class="fintel-subtitle">{_text(subtitle, "")}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_signal_card(title: str, value: Any, description: str = "") -> None:
    """Display one market signal such as momentum, volume, or sentiment."""
    _inject_styles()
    extra = ""
    if description:
        extra = f'<p class="fintel-desc">{_text(description)}</p>'
    st.markdown(
        f"""
        <div class="fintel-card">
          <p class="fintel-label">{_text(title)}</p>
          <p class="fintel-value">{_text(value)}</p>
          {extra}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_agent_card(agent: Mapping[str, Any] | None) -> None:
    """Display one AI agent result: name, recommendation, confidence, and summary."""
    _inject_styles()
    data = _mapping(agent)
    recommendation = _text(data.get("recommendation"), "Unavailable")
    fg, bg = _recommendation_style(recommendation)
    st.markdown(
        f"""
        <div class="fintel-card">
          <p class="fintel-agent-name">{_text(data.get("name"), "Unnamed agent")}</p>
          <span class="fintel-badge" style="color:{fg};background:{bg};">{recommendation.upper()}</span>
          <p class="fintel-desc">Confidence {_format_confidence(data.get("confidence"))}</p>
          <p class="fintel-summary">{_text(data.get("summary"), "No summary provided.")}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_portfolio_summary(portfolio: Mapping[str, Any] | None) -> None:
    """Safely display portfolio holdings, risk, and stock exposure."""
    _inject_styles()
    data = _mapping(portfolio)
    st.subheader("Portfolio summary")
    col_holdings, col_risk, col_exposure = st.columns(3)
    with col_holdings:
        st.markdown(
            f"""
            <div class="fintel-card">
              <p class="fintel-label">Total holdings</p>
              <p class="fintel-value">{_format_money(data.get("total_holdings"))}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_risk:
        st.markdown(
            f"""
            <div class="fintel-card">
              <p class="fintel-label">Portfolio risk</p>
              <p class="fintel-value">{_text(data.get("portfolio_risk"))}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_exposure:
        st.markdown(
            f"""
            <div class="fintel-card">
              <p class="fintel-label">Stock exposure</p>
              <p class="fintel-value">{_format_exposure(data.get("stock_exposure"))}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_evidence(evidence_list: Sequence[Any] | None) -> None:
    """Display supporting evidence items, or an empty-state message if none exist."""
    _inject_styles()
    st.subheader("Supporting evidence")
    items = list(evidence_list) if isinstance(evidence_list, Sequence) and not isinstance(evidence_list, (str, bytes)) else []
    if not items:
        st.info("No supporting evidence is available for this analysis.")
        return
    for raw in items:
        item = _mapping(raw)
        st.markdown(
            f"""
            <div class="fintel-card">
              <p class="fintel-evidence-title">{_text(item.get("title"), "Untitled source")}</p>
              <p class="fintel-source">{_text(item.get("source"), "Unknown source")}</p>
              <p class="fintel-summary">{_text(item.get("summary"), "No summary provided.")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_final_recommendation(final_result: Mapping[str, Any] | None) -> None:
    """Show the final BUY/HOLD/SELL call with confidence and explanation."""
    _inject_styles()
    data = _mapping(final_result)
    recommendation = _text(data.get("recommendation"), "Unavailable")
    fg, bg = _recommendation_style(recommendation)
    st.subheader("Final recommendation")
    st.markdown(
        f"""
        <div class="fintel-final">
          <p class="fintel-label">Consensus action</p>
          <p class="fintel-final-rec" style="color:{fg};">{recommendation.upper()}</p>
          <span class="fintel-badge" style="color:{fg};background:{bg};">
            Confidence {_format_confidence(data.get("confidence"))}
          </span>
          <p class="fintel-summary">{_text(data.get("explanation"), "No explanation provided.")}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_reasoning(reasoning_steps: Sequence[Any] | None) -> None:
    """Show explainability steps inside a Streamlit expander."""
    _inject_styles()
    steps = list(reasoning_steps) if isinstance(reasoning_steps, Sequence) and not isinstance(reasoning_steps, (str, bytes)) else []
    with st.expander("Why this recommendation", expanded=False):
        if not steps:
            st.caption("No reasoning steps were provided.")
            return
        for index, step in enumerate(steps, start=1):
            st.markdown(f"**{index}.** {_text(step, "Step unavailable.")}")


def _format_duration(value: Any) -> str:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return _UNAVAILABLE
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    return f"{seconds:.2f} s"


def render_session_metrics(summary: Mapping[str, Any] | None) -> None:
    """Display session analysis count, average duration, and error count."""
    _inject_styles()
    data = _mapping(summary)
    col_runs, col_avg, col_errors = st.columns(3)
    with col_runs:
        st.markdown(
            f"""
            <div class="fintel-card">
              <p class="fintel-label">Analyses</p>
              <p class="fintel-value">{_text(data.get("analysis_count"), "0")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_avg:
        st.markdown(
            f"""
            <div class="fintel-card">
              <p class="fintel-label">Avg. analysis time</p>
              <p class="fintel-value">{_format_duration(data.get("average_analysis_time"))}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_errors:
        st.markdown(
            f"""
            <div class="fintel-card">
              <p class="fintel-label">Errors</p>
              <p class="fintel-value">{_text(data.get("error_count"), "0")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
