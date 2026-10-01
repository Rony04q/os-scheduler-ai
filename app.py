import streamlit as st
import pandas as pd
import plotly.express as px
from simulator import Process, run_round_robin
from ai_agent import analyze_schedule

# 1. Page Configuration
st.set_page_config(page_title="AI CPU Scheduler", layout="wide")
st.title("Generative AI–Powered OS Scheduler")
st.markdown("Simulate CPU scheduling algorithms and use AI to analyze context switching and starvation.")

# 2. Sidebar: Configuration Controls
st.sidebar.header("Scheduler Settings")
algorithm = st.sidebar.selectbox("Algorithm", ["Round-Robin"])
quantum = st.sidebar.slider("Time Quantum (ms)", min_value=1, max_value=10, value=2)

st.sidebar.markdown("---")
st.sidebar.subheader("Processes")
st.sidebar.markdown("*P1 arrives at 0s, P2 at 1s, P3 at 2s.*")
burst_p1 = st.sidebar.number_input("P1 Burst Time", min_value=1, value=6)
burst_p2 = st.sidebar.number_input("P2 Burst Time", min_value=1, value=4)
burst_p3 = st.sidebar.number_input("P3 Burst Time", min_value=1, value=8)

# Initialize processes based on user input
processes = [
    Process("P1", arrival=0, burst=burst_p1),
    Process("P2", arrival=1, burst=burst_p2),
    Process("P3", arrival=2, burst=burst_p3)
]

# 3. Run Simulation
logs_df = run_round_robin(processes, quantum)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("CPU Execution Timeline")
    # 4. Visualize with a Gantt Chart
    if not logs_df.empty:
        # Calculate duration for the bar chart
        logs_df["Duration"] = logs_df["End"] - logs_df["Start"]
        
        # Use px.bar horizontally instead of px.timeline
        fig = px.bar(
            logs_df, 
            base="Start", 
            x="Duration", 
            y="Process", 
            color="Process",
            orientation="h",
            title=f"Round-Robin (Quantum = {quantum})"
        )
        
        fig.update_layout(xaxis_title="Time (ms)", yaxis_title="Process", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No execution logs generated.")
with col2:
    # 5. Display Raw Logs
    st.subheader("Raw Telemetry")
    st.dataframe(logs_df, use_container_width=True, hide_index=True)

st.markdown("---")

# 6. Ask the AI Debugger
st.subheader("🤖 Ask the AI Assistant")
st.markdown("Ask the AI to diagnose the scheduling state, explain why a process is delayed, or suggest optimizations.")

default_query = f"Explain the context switching overhead in this scenario where the quantum is {quantum}. Is any process waiting too long?"
user_query = st.text_area("Your Question:", value=default_query)

if st.button("Analyze Logs with AI", type="primary"):
    if logs_df.empty:
        st.error("No logs available to analyze.")
    else:
        with st.spinner("Analyzing CPU telemetry data..."):
            answer = analyze_schedule(logs_df, user_query)
            st.info(answer)