
import pandas as pd
import plotly.express as px
import streamlit as st

from ai_agent import (
    analyze_schedule,
    generate_report,
    get_recommendation,
    provider_status,
)
from analysis import (
    detect_starvation,
    find_bottlenecks,
    heuristic_recommendation,
)
from simulator import (
    ALGORITHMS,
    CS_LABEL,
    IDLE_LABEL,
    PRIORITY_ALGOS,
    RESERVED_NAMES,
    Process,
    compare_algorithms,
    simulate,
)
from workloads import PRESETS, preset_df, random_workload


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="OS Scheduler Studio",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------
# THEME
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --accent: #2563eb;
        --accent-hover: #1d4ed8;
        --accent-soft: #eaf1ff;
        --ink: #0f1f3d;
        --text: #334155;
        --muted: #64748b;
        --line: #e6ebf3;
        --surface: #ffffff;
        --canvas: #f6f9fd;
        --good: #16a34a;
        --bad: #dc2626;
        --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                Roboto, 'Helvetica Neue', Arial, sans-serif;
    }

    /* ---------- Base ---------- */
    html, body, .stApp, button, input, textarea {
        font-family: var(--font);
    }
    
    /* Restore Streamlit's native UI icons */
    .stIconMaterial, .material-symbols-rounded, [data-testid="stIconMaterial"] {
        font-family: "Material Symbols Rounded" !important;
    }

    .stApp {
        background: var(--canvas);
        color: var(--text);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    #MainMenu, footer {
        visibility: hidden;
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 4rem;
        max-width: 1600px;
    }

    h1, h2, h3, h4 {
        color: var(--ink);
        font-family: var(--font);
        letter-spacing: -0.01em;
    }

    h1 {
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        padding: 0 0 0.25rem 0 !important;
    }

    h3 {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        margin-top: 0.5rem;
    }

    p, label, li {
        color: var(--text);
    }

    hr {
        border-color: var(--line) !important;
        margin: 1.5rem 0 !important;
    }

    /* ---------- Top bar ---------- */
    .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 12px 22px;
        margin-bottom: 18px;
        box-shadow: 0 1px 2px rgba(15, 31, 61, 0.04);
    }

    .brand {
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .brand-title {
        color: var(--ink);
        font-size: 1.5rem;
        font-weight: 700;
        line-height: 1.15;
        letter-spacing: -0.01em;
    }

    .brand-sub {
        color: var(--muted);
        font-size: 0.8rem;
        letter-spacing: 0.02em;
    }

    .ai-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #e8f7ee;
        color: #166534;
        font-size: 0.8rem;
        font-weight: 500;
        padding: 6px 14px;
        border-radius: 999px;
    }

    .ai-pill::before {
        content: "";
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--good);
    }

    .ai-pill.off {
        background: #f1f5f9;
        color: var(--muted);
    }

    .ai-pill.off::before {
        background: #94a3b8;
    }

    .welcome {
        display: flex;
        align-items: center;
        gap: 14px;
        margin: 4px 0 16px 0;
    }

    .welcome .wave {
        font-size: 2rem;
        line-height: 1;
    }

    .welcome .w-title {
        color: var(--ink);
        font-size: 1.35rem;
        font-weight: 700;
    }

    .welcome .w-sub {
        color: var(--muted);
        font-size: 0.9rem;
    }

    /* ---------- Cards ---------- */
    [class*="st-key-card_"] {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 1px 2px rgba(15, 31, 61, 0.04);
    }

    .card-title {
        display: flex;
        align-items: center;
        gap: 10px;
        color: var(--ink);
        font-size: 1.05rem;
        font-weight: 600;
        margin-bottom: 4px;
    }

    .card-title svg {
        flex: none;
    }

    .card-sub {
        color: var(--muted);
        font-size: 0.8rem;
        margin: 0 0 10px 0;
    }

    /* ---------- KPI tiles ---------- */
    .kpi {
        display: flex;
        align-items: center;
        gap: 16px;
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 1px 2px rgba(15, 31, 61, 0.04);
        height: 100%;
    }

    .kpi-icon {
        flex: none;
        width: 52px;
        height: 52px;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .kpi-label {
        color: var(--text);
        font-size: 0.85rem;
        font-weight: 500;
    }

    .kpi-value {
        color: var(--ink);
        font-size: 1.9rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }

    .kpi-delta {
        font-size: 0.78rem;
        color: var(--muted);
    }

    .kpi-delta b {
        font-weight: 600;
    }

    .kpi-delta .good {
        color: var(--good);
    }

    .kpi-delta .bad {
        color: var(--bad);
    }

    /* ---------- Summary list ---------- */
    .sum-row {
        display: flex;
        justify-content: space-between;
        padding: 9px 0;
        font-size: 0.875rem;
        color: var(--text);
    }

    .sum-row b {
        color: var(--ink);
        font-weight: 600;
    }

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] {
        background: var(--surface);
        border-right: 1px solid var(--line);
    }

    [data-testid="stSidebar"] h1 {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }

    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
    }

    .status-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 7px 0;
        border-bottom: 1px solid var(--line);
        font-size: 0.875rem;
        color: var(--text);
    }

    .status-row:last-of-type {
        border-bottom: none;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--muted);
    }

    .status-pill::before {
        content: "";
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #9ca3af;
    }

    .status-pill.on {
        color: #166534;
    }

    .status-pill.on::before {
        background: #16a34a;
    }

    .cfg-card {
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 14px 16px;
        margin-top: 8px;
    }

    .cfg-card .cfg-title {
        color: var(--ink);
        font-weight: 600;
        font-size: 0.9rem;
        margin-bottom: 8px;
    }

    .cfg-card .cfg-k {
        color: var(--muted);
        font-size: 0.78rem;
        margin-top: 8px;
    }

    .cfg-card .cfg-v {
        color: var(--ink);
        font-size: 0.875rem;
        font-weight: 500;
    }

    .promo {
        margin-top: 18px;
        border-radius: 14px;
        padding: 26px 16px 70px 16px;
        text-align: center;
        background: linear-gradient(180deg, #eef4ff 0%, #dfeaff 100%);
    }

    .promo .p-title {
        color: var(--ink);
        font-size: 1.05rem;
        font-weight: 700;
        line-height: 1.3;
        margin-top: 8px;
    }

    .promo .p-sub {
        color: var(--muted);
        font-size: 0.8rem;
        margin-top: 8px;
    }

    /* ---------- KPI cards (native metrics used in other tabs) ---------- */
    [data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: none;
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted);
        font-size: 0.75rem;
        font-weight: 500;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    [data-testid="stMetricLabel"] p {
        color: var(--muted);
        font-size: 0.75rem;
    }

    [data-testid="stMetricValue"] {
        color: var(--ink);
        font-size: 1.6rem;
        font-weight: 600;
        letter-spacing: -0.01em;
    }

    /* ---------- Tabs ---------- */
    [data-testid="stTabs"] [role="tablist"] {
        gap: 4px;
        border-bottom: 1px solid var(--line);
    }

    [data-testid="stTabs"] button[role="tab"] {
        padding: 10px 14px;
        font-size: 0.9rem;
        font-weight: 500;
        color: var(--muted);
        border-radius: 0;
    }

    [data-testid="stTabs"] button[role="tab"]:hover {
        color: var(--ink);
        background: transparent;
    }

    [data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--accent);
        font-weight: 600;
    }

    [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        background-color: var(--accent);
        height: 2px;
    }

    [data-testid="stTabs"] [data-baseweb="tab-border"] {
        background-color: var(--line);
    }

    /* ---------- Containers ---------- */
    [data-testid="stExpander"] {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 12px;
        box-shadow: none;
    }

    [data-testid="stExpander"] summary {
        font-weight: 600;
        color: var(--ink);
    }

    [data-testid="stDataFrame"],
    [data-testid="stDataEditor"] {
        border: 1px solid var(--line);
        border-radius: 10px;
        overflow: hidden;
    }

    [data-testid="stPlotlyChart"] {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 6px;
    }

    [class*="st-key-card_"] [data-testid="stPlotlyChart"] {
        border: none;
        padding: 0;
    }

    /* ---------- Buttons ---------- */
    .stButton > button,
    .stDownloadButton > button {
        border-radius: 8px;
        font-weight: 500;
        font-size: 0.875rem;
        background: var(--surface);
        color: var(--ink);
        border: 1px solid #d5deec;
        box-shadow: none;
        transition: background 0.12s ease, border-color 0.12s ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background: var(--accent-soft);
        border-color: var(--accent);
        color: var(--accent);
    }

    .stButton > button[kind="primary"] {
        background: var(--accent);
        border-color: var(--accent);
        color: #ffffff;
    }

    .stButton > button[kind="primary"]:hover {
        background: var(--accent-hover);
        border-color: var(--accent-hover);
        color: #ffffff;
    }

    /* quick-question chips */
    [class*="st-key-chip_"] button {
        border-radius: 999px;
        font-size: 0.78rem;
        padding: 2px 12px;
        min-height: 32px;
        background: #f3f7ff;
        border-color: #d9e4fb;
        color: var(--text);
        justify-content: flex-start;
    }

    /* ---------- Inputs ---------- */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] {
        border-radius: 8px;
        border-color: #d5deec;
        background: var(--surface);
    }

    [data-testid="stWidgetLabel"] p {
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--text);
    }

    /* ---------- Alerts ---------- */
    [data-testid="stAlert"] {
        border-radius: 10px;
        border: 1px solid var(--line);
        box-shadow: none;
    }

    /* ---------- Captions ---------- */
    [data-testid="stCaptionContainer"] {
        color: var(--muted);
        font-size: 0.8125rem;
    }

    @media (max-width: 768px) {
        [data-testid="stMetric"] {
            padding: 12px;
        }

        .block-container {
            padding-top: 1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# REUSABLE CHART STYLE
# ---------------------------------------------------------
CHART_FONT = (
    "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', "
    "Roboto, Arial, sans-serif"
)


def style_chart(fig, height=360):
    fig.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(
            family=CHART_FONT,
            size=12,
            color="#4b5563",
        ),
        title=dict(
            font=dict(size=14, color="#111827"),
            x=0,
            xanchor="left",
        ),
        margin=dict(l=16, r=16, t=56, b=32),
        hoverlabel=dict(
            bgcolor="#ffffff",
            bordercolor="#d1d5db",
            font_color="#111827",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            title_text="",
            bgcolor="rgba(255,255,255,0)",
            borderwidth=0,
        ),
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor="#d1d5db",
        ticks="outside",
        tickcolor="#d1d5db",
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="#f0f1f3",
        zeroline=False,
        linecolor="rgba(0,0,0,0)",
    )

    return fig


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------
CHIP_SVG = (
    '<svg width="44" height="44" viewBox="0 0 48 48" fill="none" '
    'stroke="#1e3a8a" stroke-width="2.6" stroke-linecap="round">'
    '<rect x="11" y="11" width="26" height="26" rx="4"/>'
    '<rect x="19" y="19" width="10" height="10" rx="2" fill="#2563eb" stroke="none"/>'
    '<path d="M17 4v7M24 4v7M31 4v7M17 37v7M24 37v7M31 37v7'
    'M4 17h7M4 24h7M4 31h7M37 17h7M37 24h7M37 31h7"/></svg>'
)

_header_status = provider_status()
_ai_online = _header_status["gemini"] or _header_status["openrouter"]

st.markdown(
    f"""
    <div class="topbar">
        <div class="brand">
            {CHIP_SVG}
            <div>
                <div class="brand-title">OS Scheduler Studio</div>
                <div class="brand-sub">Simulate &nbsp;•&nbsp; Analyze &nbsp;•&nbsp; Optimize</div>
            </div>
        </div>
        <span class="ai-pill {'' if _ai_online else 'off'}">
            {'AI Ready' if _ai_online else 'Offline analyzer'}
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# SESSION DEFAULTS
# ---------------------------------------------------------
defaults = {
    "algorithm": "Round-Robin",
    "quantum": 2,
    "cs_cost": 0,
    "aging": 0,
    "thr": 10,
    "wl_version": 0,
    "ai_query": "",
    "ai_answer": None,
    "ai_reco": None,
    "ai_report": None,
}

for key, value in defaults.items():
    st.session_state.setdefault(key, value)

if "workload" not in st.session_state:
    st.session_state.workload = preset_df("Default demo")


# ---------------------------------------------------------
# CALLBACKS
# ---------------------------------------------------------
def apply_reco():
    recommendation = st.session_state.ai_reco

    if recommendation:
        st.session_state.algorithm = recommendation["algorithm"]
        st.session_state.quantum = int(recommendation["quantum"])
        st.session_state.aging = int(
            recommendation["aging_interval"]
        )
        st.session_state.ai_reco = None


def load_preset():
    st.session_state.workload = preset_df(
        st.session_state.preset_choice
    )
    st.session_state.wl_version += 1


def load_random():
    st.session_state.workload = random_workload(
        st.session_state.rand_n,
        st.session_state.rand_seed,
    )
    st.session_state.wl_version += 1


# ---------------------------------------------------------
# SIDEBAR: SCHEDULER SETTINGS
# ---------------------------------------------------------
st.sidebar.title("Scheduler Settings")
st.sidebar.caption("Configure the simulation parameters.")

algorithm = st.sidebar.selectbox(
    "Scheduling algorithm",
    ALGORITHMS,
    key="algorithm",
)

quantum = st.sidebar.slider(
    "Time quantum (ms)",
    1,
    10,
    key="quantum",
    disabled=algorithm != "Round-Robin",
)

cs_cost = st.sidebar.slider(
    "Context-switch cost (ms)",
    0,
    3,
    key="cs_cost",
)

aging = st.sidebar.slider(
    "Priority aging interval (ms)",
    0,
    30,
    key="aging",
    disabled=algorithm not in PRIORITY_ALGOS,
    help=(
        "Every N ms of waiting, a process's priority improves "
        "by 1. Set to 0 to disable aging."
    ),
)

threshold = st.sidebar.slider(
    "Starvation threshold (ms)",
    2,
    40,
    key="thr",
    help="Flags processes that wait too long in one unbroken stretch.",
)

st.sidebar.caption(
    "Priority rule: lower number means higher priority."
)

st.sidebar.divider()

status = provider_status()

st.sidebar.subheader("AI services")


def status_row(label, active, on_text="Connected", off_text="Not configured"):
    css = "on" if active else ""
    text = on_text if active else off_text
    return (
        f'<div class="status-row"><span>{label}</span>'
        f'<span class="status-pill {css}">{text}</span></div>'
    )


st.sidebar.markdown(
    status_row("Gemini", status["gemini"])
    + status_row("OpenRouter", status["openrouter"])
    + status_row("Offline analyzer", True, on_text="Available"),
    unsafe_allow_html=True,
)

st.sidebar.caption(
    "The offline analyzer remains available without API keys."
)

# Current configuration + tagline cards (display only)
st.sidebar.markdown(
    f"""
    <div class="cfg-card">
        <div class="cfg-title">Current Configuration</div>
        <div class="cfg-k">Algorithm</div><div class="cfg-v">{algorithm}</div>
        <div class="cfg-k">Time Quantum</div><div class="cfg-v">{quantum}</div>
        <div class="cfg-k">Context Switch Cost</div><div class="cfg-v">{cs_cost}</div>
        <div class="cfg-k">Priority Aging Interval</div><div class="cfg-v">{aging}</div>
    </div>
    <div class="promo">
        <svg width="56" height="56" viewBox="0 0 48 48" fill="none"
             stroke="#1e3a8a" stroke-width="2.6" stroke-linecap="round">
            <rect x="11" y="11" width="26" height="26" rx="4"/>
            <rect x="19" y="19" width="10" height="10" rx="2" fill="#2563eb" stroke="none"/>
            <path d="M17 4v7M24 4v7M31 4v7M17 37v7M24 37v7M31 37v7M4 17h7M4 24h7M4 31h7M37 17h7M37 24h7M37 31h7"/>
        </svg>
        <div class="p-title">Better Scheduling<br>for a Smarter CPU</div>
        <div class="p-sub">Understand. Optimize.<br>Build better systems.</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# WORKLOAD EDITOR
# ---------------------------------------------------------
with st.expander(
    "Process Workload",
    expanded=False,
):
    st.caption(
        "Edit the process values or load a prepared scenario."
    )

    c1, c2, c3, c4, c5 = st.columns(
        [3, 1, 1, 1, 1]
    )

    c1.selectbox(
        "Preset scenario",
        list(PRESETS),
        key="preset_choice",
    )

    c2.button(
        "Load preset",
        on_click=load_preset,
        use_container_width=True,
    )

    c3.number_input(
        "Random processes",
        2,
        12,
        5,
        key="rand_n",
    )

    c4.number_input(
        "Random seed",
        0,
        9999,
        1,
        key="rand_seed",
    )

    c5.button(
        "Generate",
        on_click=load_random,
        use_container_width=True,
    )

    edited = st.data_editor(
        st.session_state.workload,
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        key=f"editor_{st.session_state.wl_version}",
        column_config={
            "Process": st.column_config.TextColumn(
                "Process",
                required=True,
            ),
            "Arrival": st.column_config.NumberColumn(
                "Arrival time",
                min_value=0,
                step=1,
                default=0,
            ),
            "Burst": st.column_config.NumberColumn(
                "Burst time",
                min_value=1,
                step=1,
                default=1,
            ),
            "Priority": st.column_config.NumberColumn(
                "Priority",
                min_value=0,
                step=1,
                default=1,
            ),
        },
    )


# ---------------------------------------------------------
# INPUT VALIDATION
# ---------------------------------------------------------
df = edited.dropna(subset=["Process"]).copy()
df["Process"] = df["Process"].astype(str).str.strip()
df = df[df["Process"] != ""]

errors = []

if df.empty:
    errors.append("Add at least one process.")
else:
    if df[
        ["Arrival", "Burst", "Priority"]
    ].isna().any().any():
        errors.append(
            "Every process needs Arrival, Burst and Priority values."
        )

    if df["Process"].duplicated().any():
        errors.append("Process names must be unique.")

    if df["Process"].isin(RESERVED_NAMES).any():
        errors.append(
            f"Names '{CS_LABEL}' and '{IDLE_LABEL}' are reserved."
        )

    if (df["Burst"] < 1).any() or (df["Arrival"] < 0).any():
        errors.append(
            "Burst must be at least 1 and Arrival cannot be negative."
        )

if errors:
    for error in errors:
        st.error(error)
    st.stop()


processes = [
    Process(
        row.Process,
        row.Arrival,
        row.Burst,
        row.Priority,
    )
    for row in df.itertuples()
]


# ---------------------------------------------------------
# SIMULATION
# ---------------------------------------------------------
result = simulate(
    processes,
    algorithm,
    quantum,
    cs_cost,
    aging,
)

logs = result.logs
metrics = result.metrics
summary = result.summary

starved = detect_starvation(metrics, threshold)
findings = find_bottlenecks(result, starved)


# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------
DASH_COLORS = [
    "#3b82f6",
    "#fb923c",
    "#22c55e",
    "#8b5cf6",
    "#ef4444",
    "#06b6d4",
    "#eab308",
    "#ec4899",
    "#14b8a6",
    "#6366f1",
    "#84cc16",
    "#f97316",
]


def icon(path, color, size=20):
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round">{path}</svg>'
    )


ICON_CLOCK = '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'
ICON_REFRESH = '<path d="M20 11a8 8 0 0 0-14-4M4 13a8 8 0 0 0 14 4"/><path d="M6 3v4h4M18 21v-4h-4"/>'
ICON_BOLT = '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>'
ICON_SWAP = '<path d="M4 8h14l-3-3M20 16H6l3 3"/>'
ICON_BARS = '<path d="M5 21V10M12 21V4M19 21v-8"/>'
ICON_CLIP = '<rect x="6" y="4" width="12" height="17" rx="2"/><path d="M9 4h6v3H9zM9 12h6M9 16h6"/>'
ICON_TREND = '<path d="M3 3v18h18"/><path d="m7 14 4-4 3 3 5-6"/>'
ICON_SPARK = '<path d="M12 2l2.4 6.6L21 11l-6.6 2.4L12 20l-2.4-6.6L3 11l6.6-2.4z"/>'
ICON_BULB = '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0 0 12 3z"/>'
ICON_DOWN = '<path d="M12 3v12m0 0-4-4m4 4 4-4M5 21h14"/>'


def card_title(path, color, text, sub=None):
    html = f'<div class="card-title">{icon(path, color, 22)}<span>{text}</span></div>'
    if sub:
        html += f'<div class="card-sub">{sub}</div>'
    return html


# --- previous-run tracking for the "vs. previous" deltas ---
_current = {
    "wait": summary["Avg Waiting"],
    "tat": summary["Avg Turnaround"],
    "cpu": summary["CPU Utilization %"],
    "cs": summary["Context Switches"],
}
_sig = repr(
    (algorithm, quantum, cs_cost, aging, df.values.tolist())
)

if st.session_state.get("_run_sig") != _sig:
    st.session_state["_prev_run"] = st.session_state.get("_cur_run")
    st.session_state["_cur_run"] = _current
    st.session_state["_run_sig"] = _sig

_previous = st.session_state.get("_prev_run")


def kpi_tile(key, label, value_text, path, color, bg, lower_is_better):
    cur = _current[key]
    delta_html = "No previous run yet"

    if _previous is not None:
        old = _previous[key]
        pct = 0.0 if old == 0 else (cur - old) / abs(old) * 100
        arrow = "↓" if pct < 0 else "↑"
        improved = (pct < 0) if lower_is_better else (pct > 0)
        cls = "good" if (improved or pct == 0) else "bad"
        delta_html = (
            f'<b class="{cls}">{arrow} {abs(pct):.0f}%</b> vs. previous'
        )

    return (
        '<div class="kpi">'
        f'<div class="kpi-icon" style="background:{bg}">{icon(path, color, 26)}</div>'
        "<div>"
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value_text}</div>'
        f'<div class="kpi-delta">{delta_html}</div>'
        "</div></div>"
    )


main_col, side_col = st.columns([3.1, 1.15], gap="medium")


# ======================= RIGHT COLUMN =======================
with side_col:
    with st.container(key="card_ai"):
        st.markdown(
            card_title(
                ICON_SPARK,
                "#7c3aed",
                "AI Assistant",
                "Ask questions, get insights and recommendations.",
            ),
            unsafe_allow_html=True,
        )

        st.text_area(
            "Ask the AI assistant",
            key="dash_q",
            height=90,
            placeholder="e.g. Why is a process waiting so long?",
            label_visibility="collapsed",
        )

        def run_dash_ai(question):
            if not question.strip():
                return
            with st.spinner("Analyzing schedule..."):
                st.session_state.dash_answer = analyze_schedule(
                    result,
                    question,
                    threshold,
                )

        if st.button(
            "Ask  ➤",
            key="dash_send",
            type="primary",
            use_container_width=True,
        ):
            run_dash_ai(st.session_state.dash_q)

        st.markdown(
            '<div class="card-title" style="font-size:0.9rem;margin-top:14px">'
            "Quick Questions</div>",
            unsafe_allow_html=True,
        )

        for i, q_text in enumerate(
            [
                "Why is a process waiting so long?",
                "Are there any bottlenecks?",
                "Which algorithm performs best?",
                "How can I improve CPU utilization?",
            ]
        ):
            if st.button(q_text, key=f"chip_{i}"):
                run_dash_ai(q_text)

        if st.session_state.get("dash_answer"):
            st.markdown("---")
            st.markdown(st.session_state.dash_answer)

    with st.container(key="card_reco"):
        _reco = heuristic_recommendation(result, starved)
        st.markdown(
            card_title(ICON_BULB, "#f59e0b", "Recommendation"),
            unsafe_allow_html=True,
        )
        st.write(
            _reco.get("reason")
            or "The current configuration looks balanced for this workload."
        )

        if st.button("Get Full Report  →", key="dash_report"):
            with st.spinner("Generating report..."):
                st.session_state.ai_report = generate_report(
                    result,
                    threshold,
                )

        if st.session_state.ai_report:
            with st.expander("Full report", expanded=True):
                st.markdown(st.session_state.ai_report)

    with st.container(key="card_dl_side"):
        st.markdown(
            card_title(
                ICON_DOWN,
                "#1e3a8a",
                "Download Results",
                "Export your simulation data",
            ),
            unsafe_allow_html=True,
        )

        st.download_button(
            "Process Metrics (CSV)",
            data=metrics.to_csv(index=False),
            file_name="process_metrics.csv",
            mime="text/csv",
            key="dl_side_metrics",
            use_container_width=True,
        )

        st.download_button(
            "Scheduling Logs (CSV)",
            data=logs.to_csv(index=False),
            file_name="execution_log.csv",
            mime="text/csv",
            key="dl_side_logs",
            use_container_width=True,
        )

        st.download_button(
            "Summary Report (CSV)",
            data=pd.DataFrame(
                list(summary.items()),
                columns=["Metric", "Value"],
            ).to_csv(index=False),
            file_name="summary_report.csv",
            mime="text/csv",
            key="dl_side_summary",
            use_container_width=True,
        )


# ======================= MAIN COLUMN =======================
with main_col:
    st.markdown(
        """
        <div class="welcome">
            <div class="wave">👋</div>
            <div>
                <div class="w-title">Welcome to OS Scheduler Studio</div>
                <div class="w-sub">Visualize process scheduling, analyze performance and get AI-powered insights.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- KPI row ----
    k1, k2, k3, k4 = st.columns(4, gap="small")

    k1.markdown(
        kpi_tile(
            "wait",
            "Average Waiting Time",
            f"{summary['Avg Waiting']}",
            ICON_CLOCK,
            "#2563eb",
            "#e3edff",
            True,
        ),
        unsafe_allow_html=True,
    )
    k2.markdown(
        kpi_tile(
            "tat",
            "Average Turnaround Time",
            f"{summary['Avg Turnaround']}",
            ICON_REFRESH,
            "#7c3aed",
            "#efe7ff",
            True,
        ),
        unsafe_allow_html=True,
    )
    k3.markdown(
        kpi_tile(
            "cpu",
            "CPU Utilization",
            f"{summary['CPU Utilization %']:g}%",
            ICON_BOLT,
            "#16a34a",
            "#e0f7e9",
            False,
        ),
        unsafe_allow_html=True,
    )
    k4.markdown(
        kpi_tile(
            "cs",
            "Context Switches",
            f"{summary['Context Switches']}",
            ICON_SWAP,
            "#ea580c",
            "#ffecdd",
            True,
        ),
        unsafe_allow_html=True,
    )

    st.write("")

    # ---- Timeline + scheduling summary ----
    t_col, s_col = st.columns([2.2, 1], gap="medium")

    with t_col:
        with st.container(key="card_timeline"):
            st.markdown(
                card_title(ICON_BARS, "#2563eb", "CPU Execution Timeline"),
                unsafe_allow_html=True,
            )

            _pids = sorted(metrics["Process"])
            _rows = _pids + [
                name
                for name in (CS_LABEL, IDLE_LABEL)
                if name in set(logs["Process"])
            ]
            _cmap = {
                pid: DASH_COLORS[i % len(DASH_COLORS)]
                for i, pid in enumerate(_pids)
            }
            _cmap[CS_LABEL] = "#9ca3af"
            _cmap[IDLE_LABEL] = "#e5e7eb"

            gfig = px.bar(
                logs,
                base="Start",
                x="Duration",
                y="Process",
                color="Process",
                orientation="h",
                color_discrete_map=_cmap,
                category_orders={"Process": _rows},
                hover_data={"Start": True, "End": True, "Duration": True},
            )
            gfig.update_yaxes(
                categoryorder="array",
                categoryarray=_rows[::-1],
                title="",
            )
            gfig.update_xaxes(title="Time")
            gfig.update_layout(barcornerradius=4)
            gfig = style_chart(gfig, height=330)
            gfig.update_layout(
                title=None,
                margin=dict(l=8, r=8, t=8, b=32),
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.01,
                ),
            )
            gfig.update_xaxes(showgrid=True, gridcolor="#eef2f8")

            st.plotly_chart(
                gfig,
                width="stretch",
                config={"displaylogo": False},
                key="dash_gantt",
            )

    with s_col:
        with st.container(key="card_summary"):
            st.markdown(
                card_title(ICON_CLIP, "#2563eb", "Scheduling Summary"),
                unsafe_allow_html=True,
            )

            _sim_time = int(logs["End"].max()) if len(logs) else 0

            st.markdown(
                "".join(
                    f'<div class="sum-row"><span>{k}</span><b>{v}</b></div>'
                    for k, v in [
                        ("Algorithm", algorithm),
                        ("Time Quantum", quantum),
                        ("Context Switch Cost", cs_cost),
                        ("Priority Aging Interval", aging),
                        ("Total Processes", len(metrics)),
                        ("Simulation Time", _sim_time),
                    ]
                ),
                unsafe_allow_html=True,
            )

    # ---- Process performance + queue length ----
    p_col, q_col = st.columns(2, gap="medium")

    with p_col:
        with st.container(key="card_perf"):
            st.markdown(
                card_title(ICON_BARS, "#2563eb", "Process Performance"),
                unsafe_allow_html=True,
            )

            _perf = metrics.melt(
                id_vars="Process",
                value_vars=["Waiting", "Turnaround", "Response"],
                var_name="Metric",
                value_name="ms",
            )
            pfig = px.bar(
                _perf,
                x="Process",
                y="ms",
                color="Metric",
                barmode="group",
                color_discrete_map={
                    "Waiting": "#3b82f6",
                    "Turnaround": "#8b5cf6",
                    "Response": "#22c55e",
                },
                labels={"ms": "Time"},
            )
            pfig.update_layout(barcornerradius=3)
            pfig = style_chart(pfig, height=300)
            pfig.update_layout(
                title=None,
                margin=dict(l=8, r=8, t=36, b=32),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.0,
                    xanchor="center",
                    x=0.5,
                    title_text="",
                ),
            )
            pfig.update_xaxes(title="")

            st.plotly_chart(
                pfig,
                width="stretch",
                config={"displaylogo": False},
                key="dash_perf",
            )

    with q_col:
        with st.container(key="card_queue"):
            st.markdown(
                card_title(ICON_TREND, "#2563eb", "Queue Length Over Time"),
                unsafe_allow_html=True,
            )

            qfig = px.line(
                result.queue,
                x="Time",
                y="Ready Queue Length",
                line_shape="hv",
                markers=True,
            )
            qfig.update_traces(
                line_color="#2563eb",
                name="Ready Queue",
                showlegend=True,
            )
            qfig = style_chart(qfig, height=300)
            qfig.update_layout(
                title=None,
                margin=dict(l=8, r=8, t=36, b=32),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.0,
                    xanchor="center",
                    x=0.5,
                ),
            )
            qfig.update_yaxes(title="")

            st.plotly_chart(
                qfig,
                width="stretch",
                config={"displaylogo": False},
                key="dash_queue",
            )

    # ---- Data tabs + downloads ----
    d_col, dl_col = st.columns([2.2, 1], gap="medium")

    with d_col:
        with st.container(key="card_data"):
            t_proc, t_queue, t_logs = st.tabs(
                ["Process Table", "Queue Data", "Logs"]
            )

            with t_proc:
                _cols = [
                    c
                    for c in [
                        "Process",
                        "Arrival",
                        "Burst",
                        "Waiting",
                        "Turnaround",
                        "Response",
                        "Priority",
                    ]
                    if c in metrics.columns
                ]
                st.dataframe(
                    metrics[_cols],
                    hide_index=True,
                    width="stretch",
                )

            with t_queue:
                st.dataframe(
                    result.queue,
                    hide_index=True,
                    width="stretch",
                )

            with t_logs:
                st.dataframe(
                    logs,
                    hide_index=True,
                    width="stretch",
                )

    with dl_col:
        with st.container(key="card_dl_main"):
            st.markdown(
                card_title(
                    ICON_DOWN,
                    "#1e3a8a",
                    "Download Results",
                    "Export your simulation data",
                ),
                unsafe_allow_html=True,
            )

            st.download_button(
                "Process Metrics (CSV)",
                data=metrics.to_csv(index=False),
                file_name="process_metrics.csv",
                mime="text/csv",
                key="dl_main_metrics",
                use_container_width=True,
            )

            st.download_button(
                "Scheduling Logs (CSV)",
                data=logs.to_csv(index=False),
                file_name="execution_log.csv",
                mime="text/csv",
                key="dl_main_logs",
                use_container_width=True,
            )

            st.download_button(
                "Summary Report (CSV)",
                data=pd.DataFrame(
                    list(summary.items()),
                    columns=["Metric", "Value"],
                ).to_csv(index=False),
                file_name="summary_report.csv",
                mime="text/csv",
                key="dl_main_summary",
                use_container_width=True,
            )

st.divider()

# ---------------------------------------------------------
# KPI METRICS
# ---------------------------------------------------------
st.subheader("Performance Overview")

st.caption(
    f"Current algorithm: {algorithm}"
    + (
        f" • Time quantum: {quantum} ms"
        if algorithm == "Round-Robin"
        else ""
    )
)

k = st.columns(3)

k[0].metric(
    "Average Waiting",
    f"{summary['Avg Waiting']} ms",
)

k[1].metric(
    "Average Turnaround",
    f"{summary['Avg Turnaround']} ms",
)

k[2].metric(
    "Average Response",
    f"{summary['Avg Response']} ms",
)

k = st.columns(3)

k[0].metric(
    "CPU Utilization",
    f"{summary['CPU Utilization %']}%",
)

k[1].metric(
    "Context Switches",
    summary["Context Switches"],
)

k[2].metric(
    "Jain's Fairness Index",
    summary["Fairness"],
)

st.divider()


# ---------------------------------------------------------
# MAIN NAVIGATION
# ---------------------------------------------------------
tab_time, tab_charts, tab_cmp, tab_ai, tab_logs = st.tabs(
    [
        "Timeline & Diagnostics",
        "Wait & Queue Charts",
        "Compare Algorithms",
        "AI Assistant",
        "Logs & Export",
    ]
)


# ---------------------------------------------------------
# TAB 1: TIMELINE AND DIAGNOSTICS
# ---------------------------------------------------------
with tab_time:
    st.subheader("CPU Execution Timeline")

    pids = sorted(metrics["Process"])

    rows = pids + [
        name
        for name in (CS_LABEL, IDLE_LABEL)
        if name in set(logs["Process"])
    ]

    palette = [
        "#1f4e79",
        "#2a7f8e",
        "#b7791f",
        "#6b5b95",
        "#a23b5a",
        "#3d7ea6",
        "#5f8a3c",
        "#c05621",
        "#4a5aa8",
        "#5b6770",
        "#2f855a",
        "#8b5fbf",
    ]

    color_map = {
        pid: palette[index % len(palette)]
        for index, pid in enumerate(pids)
    }

    color_map[CS_LABEL] = "#9ca3af"
    color_map[IDLE_LABEL] = "#e5e7eb"

    fig = px.bar(
        logs,
        base="Start",
        x="Duration",
        y="Process",
        color="Process",
        orientation="h",
        color_discrete_map=color_map,
        hover_data={
            "Start": True,
            "End": True,
            "Duration": True,
        },
        category_orders={
            "Process": rows,
        },
        title=(
            f"Execution Timeline — {algorithm}"
            + (
                f" (Quantum = {quantum} ms)"
                if algorithm == "Round-Robin"
                else ""
            )
        ),
    )

    fig.update_yaxes(
        categoryorder="array",
        categoryarray=rows[::-1],
        title="",
    )

    if len(metrics) <= 12:
        for _, row in metrics.iterrows():
            fig.add_vline(
                x=row["Arrival"],
                line_dash="dot",
                line_color="rgba(107,114,128,0.45)",
                annotation_text=f"{row['Process']} arrival",
                annotation_position="top",
            )

    fig.update_xaxes(title="Time (ms)")
    fig.update_layout(showlegend=False)

    fig = style_chart(fig, height=400)

    st.plotly_chart(
        fig,
        width="stretch",
        config={"displaylogo": False},
    )

    st.caption(
        "Grey blocks indicate context-switch overhead; "
        "light grey indicates CPU idle time. "
        "Dotted lines mark process arrivals."
    )

    left, right = st.columns(
        [3, 2],
        gap="large",
    )

    with left:
        st.subheader("Per-process Metrics")

        st.dataframe(
            metrics.drop(
                columns=["First Start"],
                errors="ignore",
            ),
            hide_index=True,
            width="stretch",
        )

    with right:
        st.subheader("Schedule Diagnostics")

        if not findings:
            st.success(
                "No issues were detected by the current diagnostics."
            )

        for severity, message in findings:
            if severity == "warning":
                st.warning(message)
            elif severity == "info":
                st.info(message)
            else:
                st.success(message)


# ---------------------------------------------------------
# TAB 2: WAITING AND QUEUE CHARTS
# ---------------------------------------------------------
with tab_charts:
    st.subheader("Process Performance Analysis")

    a, b = st.columns(2, gap="large")

    with a:
        long = metrics.melt(
            id_vars="Process",
            value_vars=["Waiting", "Burst"],
            var_name="Kind",
            value_name="ms",
        )

        fig2 = px.bar(
            long,
            x="Process",
            y="ms",
            color="Kind",
            barmode="group",
            color_discrete_map={
                "Waiting": "#1f4e79",
                "Burst": "#9fb3c8",
            },
            title="Waiting Time vs CPU Burst",
            labels={
                "ms": "Time (ms)",
                "Kind": "Metric",
            },
        )

        st.plotly_chart(
            style_chart(fig2),
            width="stretch",
            config={"displaylogo": False},
        )

    with b:
        fig3 = px.bar(
            metrics,
            x="Process",
            y="Max Wait Gap",
            title="Longest Continuous Waiting Time",
            color="Max Wait Gap",
            color_continuous_scale=[
                "#dbe5f0",
                "#7fa3c8",
                "#1f4e79",
            ],
            labels={
                "Max Wait Gap": "Waiting time (ms)",
            },
        )

        fig3.add_hline(
            y=threshold,
            line_dash="dash",
            line_color="#b42318",
            annotation_text=f"Threshold: {threshold} ms",
        )

        st.plotly_chart(
            style_chart(fig3),
            width="stretch",
            config={"displaylogo": False},
        )

    st.subheader("Ready Queue Analysis")

    fig4 = px.line(
        result.queue,
        x="Time",
        y="Ready Queue Length",
        line_shape="hv",
        title="Ready Queue Length Over Time",
        markers=True,
        labels={
            "Time": "Time (ms)",
            "Ready Queue Length": "Processes waiting",
        },
    )

    fig4.update_traces(
        line_color="#1f4e79",
        fill="tozeroy",
        fillcolor="rgba(31,78,121,0.08)",
    )

    st.plotly_chart(
        style_chart(fig4),
        width="stretch",
        config={"displaylogo": False},
    )


# ---------------------------------------------------------
# TAB 3: ALGORITHM COMPARISON
# ---------------------------------------------------------
with tab_cmp:
    st.subheader("Algorithm Comparison")

    st.caption(
        "The same workload is run through every scheduling "
        "algorithm using the current quantum, switch cost, "
        "and aging settings."
    )

    cmp = compare_algorithms(
        processes,
        quantum,
        cs_cost,
        aging,
    )

    st.dataframe(
        cmp,
        hide_index=True,
        width="stretch",
    )

    best = cmp.loc[
        cmp["Avg Waiting"].idxmin(),
        "Algorithm",
    ]

    fairest = cmp.loc[
        cmp["Fairness"].idxmax(),
        "Algorithm",
    ]

    a, b = st.columns(2)

    with a:
        st.info(
            f"Lowest average waiting time: **{best}**"
        )

    with b:
        st.info(
            f"Highest fairness score: **{fairest}**"
        )

    st.subheader("Comparison Charts")

    a, b = st.columns(2, gap="large")

    with a:
        fig5 = px.bar(
            cmp,
            x="Algorithm",
            y=[
                "Avg Waiting",
                "Avg Turnaround",
                "Avg Response",
            ],
            barmode="group",
            title="Time Metrics",
            labels={
                "value": "Time (ms)",
                "variable": "Metric",
            },
            color_discrete_sequence=[
                "#1f4e79",
                "#5b8db8",
                "#b7c9dc",
            ],
        )

        st.plotly_chart(
            style_chart(fig5, height=400),
            width="stretch",
            config={"displaylogo": False},
        )

    with b:
        fig6 = px.bar(
            cmp,
            x="Algorithm",
            y="Context Switches",
            title="Context Switches by Algorithm",
            color="Context Switches",
            color_continuous_scale=[
                "#dbe5f0",
                "#7fa3c8",
                "#1f4e79",
            ],
        )

        st.plotly_chart(
            style_chart(fig6, height=400),
            width="stretch",
            config={"displaylogo": False},
        )


# ---------------------------------------------------------
# TAB 4: AI ASSISTANT
# ---------------------------------------------------------
with tab_ai:
    st.subheader("AI Scheduling Assistant")

    st.caption(
        "Ask questions about delays, starvation, context-switch "
        "overhead, or possible scheduling improvements."
    )

    templates = ["Custom question…"]

    templates += [
        f"Why is {item['pid']} starved? Explain and recommend a parameter tweak."
        for item in starved
    ]

    templates += [
        f"Why does {pid} wait so long?"
        for pid in metrics.sort_values(
            "Waiting",
            ascending=False,
        )["Process"].head(2)
    ]

    templates += [
        (
            f"Explain the context-switching overhead with "
            f"{algorithm}. Is any process waiting too long?"
        ),
        (
            "Predict the bottleneck if 3 more CPU-heavy "
            "processes arrive."
        ),
    ]

    def fill_query():
        if st.session_state.quick != templates[0]:
            st.session_state.ai_query = st.session_state.quick

    st.selectbox(
        "Suggested questions",
        templates,
        key="quick",
        on_change=fill_query,
    )

    if not st.session_state.ai_query:
        st.session_state.ai_query = (
            templates[1] if len(templates) > 1 else ""
        )

    st.text_area(
        "Your question",
        key="ai_query",
        height=100,
        placeholder="Ask a question about your CPU schedule...",
    )

    b1, b2, b3 = st.columns(3)

    if b1.button(
        "Analyze Schedule",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("Analyzing schedule..."):
            st.session_state.ai_answer = analyze_schedule(
                result,
                st.session_state.ai_query,
                threshold,
            )

    if b2.button(
        "Suggest Improvements",
        use_container_width=True,
    ):
        with st.spinner("Finding possible improvements..."):
            st.session_state.ai_reco = get_recommendation(
                result,
                threshold,
            )

    if b3.button(
        "Generate Report",
        use_container_width=True,
    ):
        with st.spinner("Generating report..."):
            st.session_state.ai_report = generate_report(
                result,
                threshold,
            )

    if st.session_state.ai_answer:
        st.subheader("Analysis Result")
        st.info(st.session_state.ai_answer)

    recommendation = st.session_state.ai_reco

    if recommendation:
        st.subheader(
            f"Suggested Tuning — {recommendation['source']}"
        )

        st.write(recommendation["reason"])

        what_if = simulate(
            processes,
            recommendation["algorithm"],
            recommendation["quantum"],
            cs_cost,
            recommendation["aging_interval"],
        )

        what_if_summary = what_if.summary

        cols = st.columns(4)

        for col, key in zip(
            cols,
            [
                "Avg Waiting",
                "Avg Turnaround",
                "Max Waiting",
                "Context Switches",
            ],
        ):
            col.metric(
                key,
                what_if_summary[key],
                delta=round(
                    what_if_summary[key] - summary[key],
                    2,
                ),
                delta_color="inverse",
            )

        st.caption(
            f"What-if preview: {recommendation['algorithm']}, "
            f"quantum {recommendation['quantum']}, "
            f"aging {recommendation['aging_interval']} ms."
        )

        st.button(
            "Apply Suggested Settings",
            on_click=apply_reco,
        )

    if st.session_state.ai_report:
        st.subheader("Generated Report")

        st.markdown(st.session_state.ai_report)

        st.download_button(
            "Download Report (.md)",
            data=st.session_state.ai_report,
            file_name="scheduler_report.md",
            mime="text/markdown",
        )


# ---------------------------------------------------------
# TAB 5: LOGS AND EXPORT
# ---------------------------------------------------------
with tab_logs:
    st.subheader("Execution Log")

    st.caption(
        "Detailed CPU execution intervals for the current simulation."
    )

    st.dataframe(
        logs,
        hide_index=True,
        width="stretch",
    )

    c1, c2 = st.columns(2, gap="medium")

    with c1:
        st.download_button(
            "Download Execution Log (CSV)",
            data=logs.to_csv(index=False),
            file_name="execution_log.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with c2:
        st.download_button(
            "Download Process Metrics (CSV)",
            data=metrics.to_csv(index=False),
            file_name="process_metrics.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.subheader("System Summary")

    st.json(summary)
