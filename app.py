"""Fintel — premium financial intelligence dashboard (Streamlit UI)."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any

import streamlit as st

from orchestrator import DEMO_USERS, analyze_market_event, get_live_market_data

INVESTORS = {uid: profile["name"] for uid, profile in DEMO_USERS.items()}
STOCKS = ["TCS", "INFY", "RELIANCE"]

# ---------------------------------------------------------------------------
# Theme & helpers
# ---------------------------------------------------------------------------

STATUS_STYLES = {
    "LIVE": ("live", "#3fb950", "Live market data"),
    "CACHED": ("cached", "#d29922", "Cached market data"),
    "SIMULATED": ("simulated", "#8b949e", "Simulated fallback data"),
    "UNAVAILABLE": ("unavailable", "#f85149", "Data unavailable"),
}

SIGNAL_POSITIVE = {"BULLISH", "POSITIVE", "STRONG"}
SIGNAL_NEGATIVE = {"BEARISH", "NEGATIVE", "CONFLICTED"}
IMPACT_COLORS = {"HIGH": "#f85149", "MODERATE": "#d29922", "LOW": "#3fb950"}


def inject_global_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        .stApp {
            background: linear-gradient(180deg, #080a0d 0%, #0d1017 40%, #0b0d10 100%);
            color: #e8eaed;
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }

        div[data-testid="stVerticalBlock"] > div:has(> div.fintel-card) {
            gap: 0.75rem;
        }

        .fintel-card {
            background: #12161e;
            border: 1px solid #252d3a;
            border-radius: 14px;
            padding: 1.25rem 1.35rem;
            margin-bottom: 0.75rem;
        }

        .fintel-card-hero {
            background: linear-gradient(135deg, #141a24 0%, #10141c 100%);
            border: 1px solid #2d3748;
            border-radius: 16px;
            padding: 1.5rem 1.75rem;
        }

        .fintel-section-title {
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #8b949e;
            margin: 0 0 0.35rem 0;
        }

        .fintel-section-heading {
            font-size: 1.35rem;
            font-weight: 700;
            color: #f0f3f6;
            margin: 0 0 0.25rem 0;
            letter-spacing: -0.02em;
        }

        .fintel-section-sub {
            font-size: 0.88rem;
            color: #8b949e;
            margin: 0 0 1rem 0;
        }

        .fintel-brand {
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: 0.22em;
            color: #f0f3f6;
            margin: 0;
        }

        .fintel-tagline {
            font-size: 0.95rem;
            color: #c9d1d9;
            margin: 0.2rem 0 0 0;
            font-weight: 500;
        }

        .fintel-subline {
            font-size: 0.78rem;
            color: #6e7681;
            margin: 0.35rem 0 0 0;
        }

        .fintel-badge {
            display: inline-block;
            padding: 0.3rem 0.75rem;
            border-radius: 999px;
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }

        .fintel-badge-live { background: rgba(63,185,80,0.15); color: #3fb950; border: 1px solid rgba(63,185,80,0.35); }
        .fintel-badge-cached { background: rgba(210,153,34,0.15); color: #d29922; border: 1px solid rgba(210,153,34,0.35); }
        .fintel-badge-simulated { background: rgba(139,148,158,0.12); color: #8b949e; border: 1px solid rgba(139,148,158,0.3); }
        .fintel-badge-unavailable { background: rgba(248,81,73,0.12); color: #f85149; border: 1px solid rgba(248,81,73,0.3); }

        .fintel-signal-badge {
            display: inline-block;
            padding: 0.35rem 0.85rem;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.06em;
        }

        .signal-pos { background: rgba(63,185,80,0.14); color: #3fb950; border: 1px solid rgba(63,185,80,0.3); }
        .signal-neg { background: rgba(248,81,73,0.14); color: #f85149; border: 1px solid rgba(248,81,73,0.3); }
        .signal-neu { background: rgba(139,148,158,0.12); color: #8b949e; border: 1px solid rgba(139,148,158,0.28); }
        .signal-warn { background: rgba(210,153,34,0.14); color: #d29922; border: 1px solid rgba(210,153,34,0.3); }

        .fintel-metric-label {
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: #6e7681;
            margin-bottom: 0.25rem;
        }

        .fintel-metric-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #f0f3f6;
            line-height: 1.2;
        }

        .fintel-metric-value-sm {
            font-size: 1.1rem;
            font-weight: 600;
            color: #e8eaed;
        }

        .fintel-price {
            font-size: 2.4rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            color: #f0f3f6;
            margin: 0.15rem 0;
        }

        .fintel-change-pos { color: #3fb950; font-weight: 600; font-size: 1.1rem; }
        .fintel-change-neg { color: #f85149; font-weight: 600; font-size: 1.1rem; }
        .fintel-change-neu { color: #8b949e; font-weight: 600; font-size: 1.1rem; }

        .fintel-agent-card {
            background: #0f1319;
            border: 1px solid #232b36;
            border-radius: 12px;
            padding: 1.1rem 1.2rem;
            height: 100%;
        }

        .fintel-agent-name {
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #6e7681;
            margin-bottom: 0.5rem;
        }

        .fintel-timeline-step {
            border-left: 2px solid #2d3748;
            padding: 0 0 1.1rem 1.1rem;
            margin-left: 0.4rem;
            position: relative;
        }

        .fintel-timeline-step::before {
            content: '';
            position: absolute;
            left: -6px;
            top: 0.15rem;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #58a6ff;
            border: 2px solid #0d1017;
        }

        .fintel-timeline-step:last-child { border-left-color: transparent; padding-bottom: 0; }

        .fintel-timeline-label {
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #58a6ff;
            margin-bottom: 0.3rem;
        }

        .fintel-timeline-body {
            font-size: 0.9rem;
            color: #c9d1d9;
            line-height: 1.55;
            word-wrap: break-word;
            overflow-wrap: anywhere;
        }

        .fintel-allocation-bar {
            background: #1c2330;
            border-radius: 6px;
            height: 8px;
            overflow: hidden;
            margin-top: 0.35rem;
        }

        .fintel-allocation-fill {
            height: 100%;
            border-radius: 6px;
            background: linear-gradient(90deg, #388bfd 0%, #58a6ff 100%);
        }

        .fintel-news-card {
            background: #0f1319;
            border: 1px solid #232b36;
            border-radius: 10px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.6rem;
        }

        .fintel-confidence-ring {
            font-size: 2.5rem;
            font-weight: 700;
            color: #58a6ff;
            line-height: 1;
        }

        .fintel-footer {
            font-size: 0.75rem;
            color: #6e7681;
            text-align: center;
            padding: 1.5rem 0 0.5rem;
            border-top: 1px solid #1c2330;
            margin-top: 2rem;
        }

        .fintel-consensus-row {
            display: flex;
            justify-content: space-between;
            padding: 0.4rem 0;
            border-bottom: 1px solid #1c2330;
            font-size: 0.88rem;
        }

        .fintel-consensus-row:last-child { border-bottom: none; }

        div[data-testid="stExpander"] {
            background: #12161e;
            border: 1px solid #252d3a;
            border-radius: 10px;
        }

        .stButton > button[kind="primary"] {
            background: linear-gradient(180deg, #388bfd 0%, #1f6feb 100%);
            border: 1px solid #388bfd;
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        .stButton > button[kind="secondary"] {
            background: #1c2330;
            border: 1px solid #30363d;
            color: #c9d1d9;
            font-weight: 500;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_timestamp(ts: str | None, prefix: str = "Last updated") -> str:
    if not ts:
        return f"{prefix}: —"
    try:
        normalized = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        formatted = dt.astimezone(timezone.utc).strftime("%b %d, %Y · %H:%M UTC")
        return f"{prefix}: {formatted}"
    except (ValueError, TypeError):
        return f"{prefix}: {ts[:19]}"


def signal_css_class(signal: str) -> str:
    upper = (signal or "").upper()
    if upper in SIGNAL_POSITIVE:
        return "signal-pos"
    if upper in SIGNAL_NEGATIVE or upper == "INSUFFICIENT_EVIDENCE":
        return "signal-neg"
    if upper in ("MIXED", "CONFLICTED", "ANOMALY", "ELEVATED"):
        return "signal-warn"
    return "signal-neu"


def normalize_agent_signal(agent: dict[str, Any]) -> str | None:
    signal = (agent.get("signal") or "").upper()
    if signal in ("BULLISH", "BEARISH", "NEUTRAL"):
        return signal
    if signal == "POSITIVE":
        return "BULLISH"
    if signal == "NEGATIVE":
        return "BEARISH"
    if signal == "INSUFFICIENT_EVIDENCE":
        return None
    return None


def compute_consensus(agents: dict[str, Any]) -> tuple[str, bool, str]:
    """Return (consensus_label, has_conflict, explanation)."""
    agent_labels = {
        "technical": "Technical",
        "fundamental": "Fundamental",
        "sentiment": "Sentiment",
    }
    normalized: dict[str, str] = {}
    raw_signals: dict[str, str] = {}

    for key in ("technical", "fundamental", "sentiment"):
        raw_signals[key] = agents.get(key, {}).get("signal", "—")
        norm = normalize_agent_signal(agents.get(key, {}))
        if norm:
            normalized[key] = norm

    if not normalized:
        return "Unavailable", False, ""

    unique = set(normalized.values())
    if len(unique) == 1:
        return "Strong", False, "All agents align on the same directional signal."

    bullish = [agent_labels[k] for k, v in normalized.items() if v == "BULLISH"]
    bearish = [agent_labels[k] for k, v in normalized.items() if v == "BEARISH"]
    neutral = [agent_labels[k] for k, v in normalized.items() if v == "NEUTRAL"]

    if "BULLISH" in unique and "BEARISH" in unique:
        return "Conflicted", True, "Signal conflict detected — confidence reduced."

    if len(unique) == 2 and "NEUTRAL" in unique:
        if len(bearish) == 2 and len(neutral) == 1:
            return "Mixed", False, f"Two agents are bearish while {neutral[0].lower()} is neutral."
        if len(bullish) == 2 and len(neutral) == 1:
            return "Mixed", False, f"Two agents are bullish while {neutral[0].lower()} is neutral."
        return "Mixed", False, "Agents show mixed directional signals with a neutral contributor."

    return "Mixed", False, "Agents show partially aligned signals."


def parse_reasoning_step(step: str) -> tuple[str, str]:
    if step.startswith("[") and "]" in step:
        label, _, body = step[1:].partition("]")
        return label.strip(), body.strip()
    return "ANALYSIS", step


def render_status_badge(status: str) -> str:
    css_key, _, _ = STATUS_STYLES.get(status, STATUS_STYLES["SIMULATED"])
    return f'<span class="fintel-badge fintel-badge-{css_key}">{status}</span>'


def render_signal_badge(signal: str) -> str:
    css = signal_css_class(signal)
    return f'<span class="fintel-signal-badge {css}">{signal or "—"}</span>'


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def render_header(market_data: dict[str, Any] | None) -> None:
    status = (market_data or {}).get("data_status", "—")
    timestamp = (market_data or {}).get("data_timestamp")
    ts_label = format_timestamp(timestamp, "Latest available quote")

    col_brand, col_status = st.columns([2.2, 1])
    with col_brand:
        st.markdown(
            """
            <div>
                <p class="fintel-brand">FINTEL</p>
                <p class="fintel-tagline">Personalized Financial Intelligence</p>
                <p class="fintel-subline">Live market signals · Multi-agent reasoning · Evidence-backed insights</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_status:
        st.markdown(
            f"""
            <div style="text-align: right; padding-top: 0.25rem;">
                {render_status_badge(status) if status != "—" else '<span class="fintel-badge fintel-badge-simulated">AWAITING DATA</span>'}
                <p class="fintel-subline" style="margin-top: 0.65rem; text-align: right;">{ts_label}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_control_bar(
    investor_id: str,
    symbol: str,
) -> tuple[bool, bool, bool, bool]:
    st.markdown('<p class="fintel-section-title">Control Panel</p>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1.4, 1.2, 1, 1.2])
    with c1:
        investor_id = st.selectbox(
            "Investor",
            options=list(INVESTORS.keys()),
            format_func=lambda uid: INVESTORS[uid],
            key="investor_select",
        )
    with c2:
        symbol = st.selectbox("Stock", options=STOCKS, key="stock_select")
    with c3:
        st.markdown("<div style='margin-top: 1.6rem;'></div>", unsafe_allow_html=True)
        analyze_clicked = st.button("Analyze", type="primary", use_container_width=True)
    with c4:
        st.markdown("<div style='margin-top: 1.6rem;'></div>", unsafe_allow_html=True)
        refresh_clicked = st.button("Refresh Market Data", use_container_width=True)

    simulate_missing_filing = False
    simulate_agent_conflict = False
    with st.expander("Demo / Reliability Tests", expanded=False):
        st.caption("Simulate degraded data paths for demonstration purposes.")
        d1, d2 = st.columns(2)
        with d1:
            simulate_missing_filing = st.checkbox("Simulate missing filing")
        with d2:
            simulate_agent_conflict = st.checkbox("Simulate agent conflict")

    return analyze_clicked, refresh_clicked, simulate_missing_filing, simulate_agent_conflict


def render_degraded_alerts(result: dict[str, Any]) -> None:
    md = result.get("market_data", {})
    status = md.get("data_status", "")
    agents = result.get("agents", {})
    sentiment = agents.get("sentiment", {})

    if status == "CACHED":
        st.warning("**LIVE DATA UNAVAILABLE** — Using cached market data (not realtime).")
    elif status == "SIMULATED":
        st.info("**SIMULATED MARKET DATA** — Offline deterministic fallback is active.")

    if agents.get("fundamental", {}).get("signal") == "INSUFFICIENT_EVIDENCE":
        st.warning("**FINANCIAL EVIDENCE UNAVAILABLE** — Fundamental confidence reduced.")

    if sentiment.get("sentiment_source") == "DEMO_FALLBACK":
        st.info("**LIVE NEWS UNAVAILABLE** — Deterministic sentiment fallback active.")

    if result.get("status") == "degraded" and status not in ("CACHED", "SIMULATED"):
        st.warning("Analysis completed in degraded mode — some data sources were partial or unavailable.")


def render_market_overview(result: dict[str, Any]) -> None:
    md = result["market_data"]
    agents = result["agents"]
    sentiment_score = agents.get("sentiment", {}).get("score", 0.0)
    symbol = md.get("symbol", "—")
    price = md.get("price")
    change = md.get("change_pct")
    volume = md.get("volume")
    vr = md.get("volume_ratio")
    provider = md.get("provider") or "—"
    data_status = md.get("data_status", "SIMULATED")

    change_class = "fintel-change-neu"
    if change is not None:
        change_class = "fintel-change-pos" if change > 0 else "fintel-change-neg" if change < 0 else "fintel-change-neu"

    st.markdown('<p class="fintel-section-title">Market Overview</p>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="fintel-card-hero">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1rem;">
                <div>
                    <p class="fintel-section-title" style="margin-bottom: 0.2rem;">Selected Symbol</p>
                    <p style="font-size: 1.6rem; font-weight: 700; margin: 0; color: #f0f3f6;">{symbol}</p>
                    <p class="fintel-price">{'₹' + f'{price:,.2f}' if price is not None else '—'}</p>
                    <p class="{change_class}">{f'{change:+.2f}%' if change is not None else '—'}</p>
                </div>
                <div style="text-align: right;">
                    {render_status_badge(data_status)}
                    <p class="fintel-subline" style="margin-top: 0.5rem;">Provider: <strong>{provider}</strong></p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4 = st.columns(4)
    metrics = [
        ("Volume", f"{volume:,}" if volume is not None else "—"),
        ("Volume Ratio", f"{vr:.1f}x" if vr is not None else "Unavailable"),
        ("Sentiment Score", f"{sentiment_score:+.2f}"),
        ("Overall Signal", result.get("overall_signal", "—")),
    ]
    for col, (label, value) in zip([m1, m2, m3, m4], metrics):
        with col:
            st.markdown(
                f"""
                <div class="fintel-card">
                    <p class="fintel-metric-label">{label}</p>
                    <p class="fintel-metric-value-sm">{value}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_signal_intelligence(result: dict[str, Any]) -> None:
    dims = result.get("signal_dimensions", {})
    agents = result.get("agents", {})
    md = result.get("market_data", {})
    vr = md.get("volume_ratio")

    st.markdown('<p class="fintel-section-title">Signal Intelligence</p>', unsafe_allow_html=True)
    st.markdown('<p class="fintel-section-heading">Market Signal Dimensions</p>', unsafe_allow_html=True)

    cards = [
        ("Momentum", dims.get("momentum", "—"), agents.get("technical", {}).get("confidence"), "Price trend classification"),
        ("Volume", dims.get("volume", "—"), None, f"{vr:.1f}x avg" if vr is not None else "Ratio unavailable"),
        ("Sentiment", dims.get("sentiment", "—"), agents.get("sentiment", {}).get("confidence"), "News & sentiment signal"),
    ]

    c1, c2, c3 = st.columns(3)
    for col, (label, classification, confidence, note) in zip([c1, c2, c3], cards):
        conf_text = f"{confidence:.0%} confidence" if confidence is not None else note
        with col:
            st.markdown(
                f"""
                <div class="fintel-card" style="text-align: center;">
                    <p class="fintel-metric-label">{label}</p>
                    <div style="margin: 0.6rem 0;">{render_signal_badge(str(classification))}</div>
                    <p class="fintel-subline">{conf_text}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_agent_card(agent_key: str, agent: dict[str, Any]) -> None:
    title = f"{agent_key.title()} Agent"
    signal = agent.get("signal", "—")
    confidence = agent.get("confidence", 0)
    status = agent.get("status", "—")
    reasoning = agent.get("reasoning", "")

    st.markdown(
        f"""
        <div class="fintel-agent-card">
            <p class="fintel-agent-name">{title}</p>
            <div style="margin-bottom: 0.5rem;">{render_signal_badge(signal)}</div>
            <p class="fintel-metric-value-sm" style="margin: 0.25rem 0;">{confidence:.0%} confidence</p>
            <p class="fintel-subline">Status: <strong>{status}</strong></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("View reasoning", expanded=False):
        st.write(reasoning)


def render_agent_council(result: dict[str, Any], simulate_conflict: bool) -> None:
    agents = result.get("agents", {})
    consensus, has_conflict, explanation = compute_consensus(agents)
    if simulate_conflict:
        has_conflict = True
        consensus = "Conflicted"
        explanation = "Signal conflict detected — confidence reduced."

    st.markdown('<p class="fintel-section-title">Multi-Agent Council</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="fintel-section-heading">Agent Council</p>'
        '<p class="fintel-section-sub">Independent perspectives before synthesis</p>',
        unsafe_allow_html=True,
    )

    a1, a2, a3 = st.columns(3)
    for col, key in zip([a1, a2, a3], ["technical", "fundamental", "sentiment"]):
        with col:
            render_agent_card(key, agents.get(key, {}))

    st.markdown('<div style="margin-top: 0.75rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="fintel-card">', unsafe_allow_html=True)
    st.markdown('<p class="fintel-metric-label">Agent Consensus</p>', unsafe_allow_html=True)

    for label, key in [("Technical", "technical"), ("Fundamental", "fundamental"), ("Sentiment", "sentiment")]:
        signal = agents.get(key, {}).get("signal", "—")
        st.write(f"**{label}** — {signal}")

    st.write(f"**Consensus:** {consensus}")
    if explanation:
        st.caption(explanation)
    if has_conflict or simulate_conflict:
        st.warning("Signal conflict detected — confidence reduced.")
    st.markdown("</div>", unsafe_allow_html=True)


def render_sentiment_section(result: dict[str, Any]) -> None:
    sentiment = result.get("agents", {}).get("sentiment", {})
    src_type = sentiment.get("sentiment_source", "DEMO_FALLBACK")

    st.markdown('<p class="fintel-section-title">Sentiment Intelligence</p>', unsafe_allow_html=True)
    st.markdown('<p class="fintel-section-heading">Sentiment Intelligence</p>', unsafe_allow_html=True)

    if src_type == "LIVE_NEWS":
        headline_count = sentiment.get("news_headlines_retrieved", 0)
        st.caption(
            f"Source: LIVE NEWS · {headline_count} relevant headline(s) · "
            f"Aggregate score: {sentiment.get('score', 0):+.2f}"
        )
        for headline in sentiment.get("news_headlines", [])[:5]:
            publisher = html.escape(headline.get("source", "Unknown"))
            title = html.escape(headline.get("title", ""))
            published = headline.get("published_at", "")
            url = headline.get("url", "")
            contribution = headline.get("sentiment_contribution")
            pub_display = html.escape(format_timestamp(published, "Published")) if published else ""

            contribution_line = ""
            if contribution is not None:
                contribution_line = (
                    f'<p class="fintel-subline">Sentiment contribution: {contribution:+.2f}</p>'
                )

            link_line = ""
            if url:
                safe_url = html.escape(url)
                link_line = (
                    f'<p class="fintel-subline" style="margin-top: 0.35rem;">'
                    f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">Source link</a></p>'
                )

            st.markdown(
                f"""
                <div class="fintel-news-card">
                    <p class="fintel-metric-label">{publisher}</p>
                    <p style="font-size: 0.95rem; font-weight: 600; color: #e8eaed; margin: 0.35rem 0;">{title}</p>
                    <p class="fintel-subline">{pub_display}</p>
                    {contribution_line}
                    {link_line}
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.caption("Source: DETERMINISTIC DEMO FALLBACK")
        st.info("Live news unavailable — deterministic fallback active.")
        st.caption(f"Fallback score: {sentiment.get('score', 0):+.2f}")


def render_portfolio_impact(result: dict[str, Any], investor_id: str) -> None:
    pi = result.get("portfolio_impact", {})
    profile = DEMO_USERS.get(investor_id, {})
    portfolio = profile.get("portfolio", {})
    symbol = pi.get("symbol") or result.get("market_data", {}).get("symbol", "")
    impact_level = pi.get("classification", "—")
    impact_color = IMPACT_COLORS.get(impact_level, "#8b949e")

    st.markdown('<p class="fintel-section-title">Portfolio Impact</p>', unsafe_allow_html=True)
    st.markdown('<p class="fintel-section-heading">Your Portfolio Impact</p>', unsafe_allow_html=True)
    st.caption("Market events are weighted against your portfolio exposure.")

    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown(
            f"""
            <div class="fintel-card">
                <p class="fintel-metric-label">Investor</p>
                <p class="fintel-metric-value-sm">{pi.get('user', '—')}</p>
                <p class="fintel-subline">{pi.get('risk_tolerance', '—')} risk profile</p>
                <div style="margin-top: 1rem;">
                    <p class="fintel-metric-label">{symbol} Exposure</p>
                    <p class="fintel-metric-value">{pi.get('exposure', 0):.0%}</p>
                </div>
                <div style="margin-top: 1rem;">
                    <p class="fintel-metric-label">Estimated Direct Impact</p>
                    <p class="fintel-metric-value">{pi.get('direct_impact_pct', 0):+.2f}%</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="fintel-card" style="text-align: center; border-color: {impact_color}55;">
                <p class="fintel-metric-label">Impact Level</p>
                <p style="font-size: 2.2rem; font-weight: 800; color: {impact_color}; margin: 0.5rem 0;">{impact_level}</p>
                <p class="fintel-subline">Exposure-weighted signal impact</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<p class="fintel-section-sub" style="margin-top: 1rem;">Portfolio Composition</p>', unsafe_allow_html=True)
    for holding, weight in sorted(portfolio.items(), key=lambda x: -x[1]):
        if holding == "CASH":
            label = "Cash"
        else:
            label = holding
        pct = int(weight * 100)
        st.markdown(
            f"""
            <div style="margin-bottom: 0.65rem;">
                <div style="display: flex; justify-content: space-between; font-size: 0.88rem;">
                    <span style="color: #c9d1d9;">{label}</span>
                    <span style="color: #8b949e;">{pct}%</span>
                </div>
                <div class="fintel-allocation-bar">
                    <div class="fintel-allocation-fill" style="width: {pct}%;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_confidence(result: dict[str, Any], simulate_conflict: bool) -> None:
    confidence = result.get("confidence", 0)
    agents = result.get("agents", {})
    consensus, has_conflict, explanation = compute_consensus(agents)
    if simulate_conflict:
        has_conflict = True
        consensus = "Conflicted"
        explanation = "Signal conflict detected — confidence reduced."

    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.markdown(
            f"""
            <div class="fintel-card" style="text-align: center;">
                <p class="fintel-metric-label">Overall Confidence</p>
                <p class="fintel-confidence-ring">{confidence:.0%}</p>
                <p class="fintel-subline">Illustrative signal confidence</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown('<div class="fintel-card">', unsafe_allow_html=True)
        st.markdown('<p class="fintel-metric-label">Agent Agreement</p>', unsafe_allow_html=True)
        st.markdown(
            f'<p class="fintel-metric-value-sm">{html.escape(consensus)}</p>',
            unsafe_allow_html=True,
        )
        if explanation:
            st.caption(explanation)
        st.caption(f"Overall signal: {result.get('overall_signal', '—')}")
        if has_conflict:
            st.warning("Confidence reduced due to agent disagreement.")
        summary = result.get("summary", "")
        if summary:
            st.caption(summary)
        st.markdown("</div>", unsafe_allow_html=True)


def render_reasoning_chain(result: dict[str, Any]) -> None:
    chain = result.get("reasoning_chain", [])

    with st.expander("Why did Fintel reach this conclusion?", expanded=True):
        st.caption("Step-by-step reasoning from market data to portfolio impact.")
        for step in chain:
            label, body = parse_reasoning_step(step)
            st.markdown(
                f"""
                <div class="fintel-timeline-step">
                    <p class="fintel-timeline-label">{html.escape(label)}</p>
                    <p class="fintel-timeline-body">{html.escape(body)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_evidence(result: dict[str, Any]) -> None:
    md = result.get("market_data", {})
    sources = result.get("sources", [])
    documents = result.get("retrieved_evidence", [])
    sentiment = result.get("agents", {}).get("sentiment", {})

    st.markdown('<p class="fintel-section-title">Evidence</p>', unsafe_allow_html=True)
    st.markdown('<p class="fintel-section-heading">Evidence & Sources</p>', unsafe_allow_html=True)

    st.markdown("**Market Data**")
    market_sources = [s for s in sources if s.get("type") == "market_data"]
    if market_sources:
        for src in market_sources:
            st.write(f"- {src.get('label', '')}")
    else:
        provider = md.get("provider", "—")
        status = md.get("data_status", "—")
        st.write(f"- {status} quote via {provider}")

    st.markdown("**Financial Evidence**")
    if documents:
        for doc in documents:
            with st.expander(f"{doc.get('title', 'Document')} — relevance {doc.get('score', 0):.0%}"):
                st.caption(f"Source: {doc.get('source', doc.get('title', ''))}")
                st.write(doc.get("text", ""))
    else:
        st.write("- No financial filings retrieved.")

    st.markdown("**News**")
    if sentiment.get("sentiment_source") == "LIVE_NEWS":
        count = sentiment.get("news_headlines_retrieved", 0)
        st.write(f"- {count} company-relevant headline(s) shown in Sentiment Intelligence above.")
    else:
        st.write("- Live news unavailable — deterministic sentiment fallback in use.")


def render_metrics(result: dict[str, Any]) -> None:
    metrics = result.get("metrics", {})
    sentiment = result.get("agents", {}).get("sentiment", {})

    st.markdown('<p class="fintel-section-title">Session</p>', unsafe_allow_html=True)
    st.markdown('<p class="fintel-section-heading">Session Metrics</p>', unsafe_allow_html=True)

    items = [
        ("Latency", f"{metrics.get('latency_seconds', 0):.3f}s"),
        ("Signal Confidence", f"{metrics.get('signal_confidence', 0):.0%}"),
        ("Portfolio Concentration", f"{metrics.get('portfolio_concentration', 0):.0%}"),
        ("Agents Completed", str(metrics.get("agents_completed", 0))),
        ("Sources Retrieved", str(metrics.get("sources_retrieved", 0))),
        ("Market Data Source", metrics.get("market_data_source", "—")),
        ("Data Freshness", format_timestamp(metrics.get("data_freshness"), "Quote").replace("Quote: ", "")),
        ("Sentiment Source", metrics.get("sentiment_source", "DEMO_FALLBACK")),
        ("News Headlines", str(metrics.get("news_headlines_retrieved", 0))),
        ("Sentiment Score", f"{sentiment.get('score', 0):+.2f}"),
    ]

    cols = st.columns(5)
    for idx, (label, value) in enumerate(items):
        with cols[idx % 5]:
            st.markdown(
                f"""
                <div class="fintel-card" style="padding: 0.85rem;">
                    <p class="fintel-metric-label">{label}</p>
                    <p style="font-size: 0.95rem; font-weight: 600; color: #e8eaed; margin: 0;">{value}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_footer() -> None:
    st.markdown(
        """
        <div class="fintel-footer">
            Fintel provides illustrative financial intelligence and evidence-backed analysis
            for research purposes. It is not investment advice or a guarantee of future performance.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_analysis_dashboard(result: dict[str, Any], investor_id: str, simulate_conflict: bool) -> None:
    render_degraded_alerts(result)
    render_market_overview(result)
    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
    render_signal_intelligence(result)
    render_agent_council(result, simulate_conflict)
    render_sentiment_section(result)
    render_portfolio_impact(result, investor_id)
    render_confidence(result, simulate_conflict)
    render_reasoning_chain(result)
    render_evidence(result)
    render_metrics(result)


def render_refresh_preview(market_data: dict[str, Any]) -> None:
    if market_data.get("price") is None:
        return
    st.markdown('<p class="fintel-section-title">Market Preview</p>', unsafe_allow_html=True)
    preview_result = {
        "market_data": market_data,
        "agents": {"sentiment": {"score": 0.0}},
        "overall_signal": "—",
        "signal_dimensions": {},
    }
    render_market_overview(preview_result)


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Fintel",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_global_styles()

if "last_market_data" not in st.session_state:
    st.session_state.last_market_data = None
if "last_market_symbol" not in st.session_state:
    st.session_state.last_market_symbol = None
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "analysis_meta" not in st.session_state:
    st.session_state.analysis_meta = {}

header_data = None
if st.session_state.analysis_result:
    header_data = st.session_state.analysis_result.get("market_data")
elif st.session_state.last_market_data and st.session_state.last_market_symbol:
    header_data = st.session_state.last_market_data

render_header(header_data)

analyze_clicked, refresh_clicked, simulate_missing_filing, simulate_agent_conflict = render_control_bar(
    st.session_state.get("investor_select", "rahul"),
    st.session_state.get("stock_select", "TCS"),
)

investor_id = st.session_state.get("investor_select", "rahul")
symbol = st.session_state.get("stock_select", "TCS")

if refresh_clicked:
    with st.spinner("Refreshing live market data..."):
        refreshed = get_live_market_data(symbol, force_refresh=True)
    st.session_state.last_market_data = refreshed
    st.session_state.last_market_symbol = symbol
    if refreshed.get("error"):
        st.error(refreshed["error"])
    else:
        st.success(f"Market data refreshed for {symbol}.")

if analyze_clicked:
    with st.status("Analyzing market event...", expanded=True) as status:
        st.write("Running independent agent analysis...")
        result = analyze_market_event(
            symbol=symbol,
            user_id=investor_id,
            simulate_missing_filing=simulate_missing_filing,
            simulate_agent_conflict=simulate_agent_conflict,
            force_market_refresh=False,
        )
        st.write("Synthesizing personalized intelligence...")
        if result.get("status") == "error":
            status.update(label="Analysis failed", state="error")
        else:
            status.update(label="Analysis complete", state="complete")

    if result.get("status") == "error":
        st.error(result.get("summary", "Analysis failed."))
    else:
        st.session_state.analysis_result = result
        st.session_state.analysis_meta = {
            "investor_id": investor_id,
            "symbol": symbol,
            "simulate_conflict": simulate_agent_conflict,
        }

if (
    st.session_state.last_market_symbol == symbol
    and st.session_state.last_market_data
    and not st.session_state.analysis_result
):
    render_refresh_preview(st.session_state.last_market_data)

if st.session_state.analysis_result:
    meta = st.session_state.analysis_meta
    render_analysis_dashboard(
        st.session_state.analysis_result,
        meta.get("investor_id", investor_id),
        meta.get("simulate_conflict", False),
    )

render_footer()
