import pandas as pd
import plotly.express as px
import streamlit as st

from ai_agent import analyze_schedule, generate_report, get_recommendation, provider_status
from analysis import detect_starvation, find_bottlenecks, heuristic_recommendation
from simulator import (ALGORITHMS, CS_LABEL, IDLE_LABEL, PRIORITY_ALGOS, RESERVED_NAMES,
                       Process, compare_algorithms, simulate)
from workloads import COLUMNS, PRESETS, preset_df, random_workload

st.set_page_config(page_title="AI CPU Scheduler", layout="wide")
st.title("⚡ Generative AI–Powered OS Scheduler")
st.markdown("Simulate CPU scheduling algorithms, spot starvation and context-switch overhead, "
            "and let an AI explain *why* and tune the scheduler for you.")

# ---------------------------------------------------------------- session defaults
defaults = {"algorithm": "Round-Robin", "quantum": 2, "cs_cost": 0, "aging": 0, "thr": 10,
            "wl_version": 0, "ai_query": "", "ai_answer": None, "ai_reco": None, "ai_report": None}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)
if "workload" not in st.session_state:
    st.session_state.workload = preset_df("Default demo")


def apply_reco():
    r = st.session_state.ai_reco
    st.session_state.algorithm = r["algorithm"]
    st.session_state.quantum = int(r["quantum"])
    st.session_state.aging = int(r["aging_interval"])
    st.session_state.ai_reco = None


def load_preset():
    st.session_state.workload = preset_df(st.session_state.preset_choice)
    st.session_state.wl_version += 1


def load_random():
    st.session_state.workload = random_workload(st.session_state.rand_n, st.session_state.rand_seed)
    st.session_state.wl_version += 1


# ---------------------------------------------------------------- sidebar
st.sidebar.header("Scheduler Settings")
algorithm = st.sidebar.selectbox("Algorithm", ALGORITHMS, key="algorithm")
quantum = st.sidebar.slider("Time Quantum (ms) — Round-Robin", 1, 10, key="quantum",
                            disabled=algorithm != "Round-Robin")
cs_cost = st.sidebar.slider("Context-switch cost (ms)", 0, 3, key="cs_cost")
aging = st.sidebar.slider("Aging interval (ms, 0 = off) — Priority", 0, 30, key="aging",
                          disabled=algorithm not in PRIORITY_ALGOS,
                          help="Every N ms of waiting, a process's priority improves by 1. Prevents starvation.")
threshold = st.sidebar.slider("Starvation threshold (ms)", 2, 40, key="thr",
                              help="A process is flagged if it waits this long in one unbroken stretch.")
st.sidebar.caption("Priority: **lower number = higher priority**.")
st.sidebar.markdown("---")
status = provider_status()
st.sidebar.subheader("AI providers")
st.sidebar.write(f"{'🟢' if status['gemini'] else '⚪'} Gemini  \n"
                 f"{'🟢' if status['openrouter'] else '⚪'} OpenRouter  \n"
                 "🟢 Offline analyzer (always on)")

# ---------------------------------------------------------------- workload
with st.expander("🧮 Process workload (edit the table, or load a preset)", expanded=True):
    c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
    c1.selectbox("Preset scenario", list(PRESETS), key="preset_choice")
    c2.button("Load preset", on_click=load_preset)
    c3.number_input("# random", 2, 12, 5, key="rand_n")
    c4.number_input("Seed", 0, 9999, 1, key="rand_seed")
    c5.button("🎲 Random", on_click=load_random)
    edited = st.data_editor(
        st.session_state.workload, num_rows="dynamic", hide_index=True, width="stretch",
        key=f"editor_{st.session_state.wl_version}",
        column_config={
            "Process": st.column_config.TextColumn("Process", required=True),
            "Arrival": st.column_config.NumberColumn("Arrival", min_value=0, step=1, default=0),
            "Burst": st.column_config.NumberColumn("Burst", min_value=1, step=1, default=1),
            "Priority": st.column_config.NumberColumn("Priority", min_value=0, step=1, default=1),
        })

# ---------------------------------------------------------------- validate
df = edited.dropna(subset=["Process"]).copy()
df["Process"] = df["Process"].astype(str).str.strip()
df = df[df["Process"] != ""]
errors = []
if df.empty:
    errors.append("Add at least one process.")
else:
    if df[["Arrival", "Burst", "Priority"]].isna().any().any():
        errors.append("Every process needs Arrival, Burst and Priority values.")
    if df["Process"].duplicated().any():
        errors.append("Process names must be unique.")
    if df["Process"].isin(RESERVED_NAMES).any():
        errors.append(f"Names '{CS_LABEL}' and '{IDLE_LABEL}' are reserved.")
    if (df["Burst"] < 1).any() or (df["Arrival"] < 0).any():
        errors.append("Burst must be >= 1 and Arrival >= 0.")
if errors:
    for e in errors:
        st.error(e)
    st.stop()

processes = [Process(r.Process, r.Arrival, r.Burst, r.Priority) for r in df.itertuples()]

# ---------------------------------------------------------------- simulate
result = simulate(processes, algorithm, quantum, cs_cost, aging)
logs, metrics, summary = result.logs, result.metrics, result.summary
starved = detect_starvation(metrics, threshold)
findings = find_bottlenecks(result, starved)

k = st.columns(6)
k[0].metric("Avg Waiting", f"{summary['Avg Waiting']} ms")
k[1].metric("Avg Turnaround", f"{summary['Avg Turnaround']} ms")
k[2].metric("Avg Response", f"{summary['Avg Response']} ms")
k[3].metric("CPU Utilization", f"{summary['CPU Utilization %']}%")
k[4].metric("Context Switches", summary["Context Switches"])
k[5].metric("Fairness (Jain)", summary["Fairness"])

tab_time, tab_charts, tab_cmp, tab_ai, tab_logs = st.tabs(
    ["📊 Timeline & Diagnostics", "📈 Wait & Queue Charts", "⚖️ Compare Algorithms",
     "🤖 AI Assistant", "🧾 Raw Logs & Export"])

# ---------------------------------------------------------------- tab 1
with tab_time:
    pids = sorted(metrics["Process"])
    rows = pids + [x for x in (CS_LABEL, IDLE_LABEL) if x in set(logs["Process"])]
    cmap = {CS_LABEL: "#8d8d8d", IDLE_LABEL: "#d9d9d9"}
    fig = px.bar(logs, base="Start", x="Duration", y="Process", color="Process", orientation="h",
                 color_discrete_map=cmap, hover_data={"Start": True, "End": True, "Duration": True},
                 category_orders={"Process": rows, "Duration": []},
                 title=f"{algorithm}" + (f" (Quantum = {quantum})" if algorithm == "Round-Robin" else ""))
    fig.update_yaxes(categoryorder="array", categoryarray=rows[::-1])
    if len(metrics) <= 12:
        for _, r in metrics.iterrows():
            fig.add_vline(x=r["Arrival"], line_dash="dot", line_color="rgba(120,120,120,0.5)",
                          annotation_text=f"{r['Process']}↓", annotation_position="top")
    fig.update_layout(xaxis_title="Time (ms)", yaxis_title="", showlegend=False, height=380)
    st.plotly_chart(fig, width="stretch")
    st.caption("Grey blocks = context-switch overhead, light-grey = CPU idle, dotted lines = arrivals.")

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Per-process metrics")
        st.dataframe(metrics.drop(columns=["First Start"]), hide_index=True, width="stretch")
    with right:
        st.subheader("Diagnostics")
        for sev, text in findings:
            {"warning": st.warning, "info": st.info, "success": st.success}[sev](text)

# ---------------------------------------------------------------- tab 2
with tab_charts:
    a, b = st.columns(2)
    with a:
        long = metrics.melt(id_vars="Process", value_vars=["Waiting", "Burst"], var_name="Kind", value_name="ms")
        f2 = px.bar(long, x="Process", y="ms", color="Kind", barmode="stack",
                    color_discrete_map={"Waiting": "#ef553b", "Burst": "#636efa"},
                    title="Waiting time vs. CPU burst per process")
        st.plotly_chart(f2, width="stretch")
    with b:
        f3 = px.bar(metrics, x="Process", y="Max Wait Gap", title="Longest continuous wait (starvation indicator)",
                    color="Max Wait Gap", color_continuous_scale="Reds")
        f3.add_hline(y=threshold, line_dash="dash", annotation_text=f"threshold = {threshold} ms")
        st.plotly_chart(f3, width="stretch")
    f4 = px.line(result.queue, x="Time", y="Ready Queue Length", line_shape="hv",
                 title="Ready-queue length over time")
    f4.update_traces(fill="tozeroy")
    st.plotly_chart(f4, width="stretch")

# ---------------------------------------------------------------- tab 3
with tab_cmp:
    st.markdown("The **same workload** run through every algorithm (using your quantum, switch cost and aging settings).")
    cmp = compare_algorithms(processes, quantum, cs_cost, aging)
    st.dataframe(cmp, hide_index=True, width="stretch")
    best = cmp.loc[cmp["Avg Waiting"].idxmin(), "Algorithm"]
    fairest = cmp.loc[cmp["Fairness"].idxmax(), "Algorithm"]
    st.success(f"Lowest average waiting time: **{best}**  |  Fairest: **{fairest}**")
    a, b = st.columns(2)
    a.plotly_chart(px.bar(cmp, x="Algorithm", y=["Avg Waiting", "Avg Turnaround", "Avg Response"],
                          barmode="group", title="Time metrics (lower is better)"), width="stretch")
    b.plotly_chart(px.bar(cmp, x="Algorithm", y="Context Switches", title="Context switches",
                          color="Context Switches", color_continuous_scale="Blues"), width="stretch")

# ---------------------------------------------------------------- tab 4
with tab_ai:
    st.markdown("Ask the AI to diagnose the schedule, explain why a process is delayed, or tune the scheduler. "
                "Works even without API keys (offline analyzer).")
    templates = ["Custom question…"]
    templates += [f"Why is {d['pid']} starved? Explain and recommend a parameter tweak." for d in starved]
    templates += [f"Why does {pid} wait so long?" for pid in metrics.sort_values("Waiting", ascending=False)["Process"].head(2)]
    templates += [f"Explain the context switching overhead with {algorithm}. Is any process waiting too long?",
                  "Predict the bottleneck if 3 more CPU-heavy processes arrive."]

    def fill_query():
        if st.session_state.quick != templates[0]:
            st.session_state.ai_query = st.session_state.quick

    st.selectbox("Quick questions", templates, key="quick", on_change=fill_query)
    if not st.session_state.ai_query:
        st.session_state.ai_query = templates[1] if len(templates) > 1 else ""
    st.text_area("Your question:", key="ai_query", height=80)

    b1, b2, b3 = st.columns(3)
    if b1.button("🔍 Analyze with AI", type="primary"):
        with st.spinner("Analyzing CPU telemetry…"):
            st.session_state.ai_answer = analyze_schedule(result, st.session_state.ai_query, threshold)
    if b2.button("🎛️ Suggest tuning parameters"):
        with st.spinner("Searching for better parameters…"):
            st.session_state.ai_reco = get_recommendation(result, threshold)
    if b3.button("📝 Generate report"):
        with st.spinner("Writing report…"):
            st.session_state.ai_report = generate_report(result, threshold)

    if st.session_state.ai_answer:
        st.markdown("#### Answer")
        st.info(st.session_state.ai_answer)

    reco = st.session_state.ai_reco
    if reco:
        st.markdown(f"#### Suggested tuning  <small>(source: {reco['source']})</small>", unsafe_allow_html=True)
        st.write(reco["reason"])
        what_if = simulate(processes, reco["algorithm"], reco["quantum"], cs_cost, reco["aging_interval"])
        w = what_if.summary
        cols = st.columns(4)
        for col, key in zip(cols, ["Avg Waiting", "Avg Turnaround", "Max Waiting", "Context Switches"]):
            col.metric(key, w[key], delta=round(w[key] - summary[key], 2), delta_color="inverse")
        st.caption(f"What-if preview → {reco['algorithm']}, quantum {reco['quantum']}, "
                   f"aging {reco['aging_interval']} ms (delta vs. current).")
        st.button("✅ Apply suggestion", on_click=apply_reco)

    if st.session_state.ai_report:
        st.markdown("#### Report")
        st.markdown(st.session_state.ai_report)
        st.download_button("⬇️ Download report (.md)", st.session_state.ai_report,
                           file_name="scheduler_report.md", mime="text/markdown")

# ---------------------------------------------------------------- tab 5
with tab_logs:
    st.subheader("Execution log")
    st.dataframe(logs, hide_index=True, width="stretch")
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Execution log (CSV)", logs.to_csv(index=False), "execution_log.csv", "text/csv")
    c2.download_button("⬇️ Process metrics (CSV)", metrics.to_csv(index=False), "process_metrics.csv", "text/csv")
    st.subheader("System summary")
    st.json(summary)
