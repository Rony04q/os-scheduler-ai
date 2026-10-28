# ⚡ AI-Powered CPU Job Scheduler Dashboard

An interactive Operating System scheduling simulator paired with an LLM diagnostic engine. It simulates six
CPU-scheduling algorithms, visualizes bursts / waiting / context switches, detects starvation automatically,
and lets an AI explain **"Why is process X starved?"** and recommend (and one-click apply) parameter tweaks.

## Features

| Area | What you get |
|---|---|
| **Schedulers** | FCFS, SJF, SRTF, Priority (non-preemptive & preemptive), Round-Robin |
| **OS concepts** | Context-switch cost, idle time, preemption counts, priority **aging** (starvation prevention) |
| **Metrics** | Waiting, turnaround, response, longest wait gap, CPU utilization, throughput, Jain fairness index |
| **Workloads** | Editable process table, 5 presets (starvation, convoy effect, ...), random generator |
| **Visuals** | Gantt chart (with context-switch/idle blocks and arrival markers), waiting-vs-burst, ready-queue length, algorithm comparison |
| **Diagnostics** | Rule-based starvation / convoy / overhead / fairness detection with adjustable threshold |
| **AI** | Q&A about the schedule, structured tuning suggestions with what-if preview + **Apply** button, downloadable Markdown report |
| **Resilience** | Gemini → OpenRouter → offline rule-based analyzer (works with no API keys) |
| **Export / Tests** | CSV export of logs and metrics; pytest suite for the scheduling math |

## Project layout

```text
os-scheduler-ai/
├── app.py            # Streamlit dashboard (tabs: timeline, charts, compare, AI, logs)
├── simulator.py      # Scheduling engine: 6 algorithms, metrics, comparison
├── analysis.py       # Rule-based starvation/bottleneck detection + offline analyzer
├── ai_agent.py       # LLM layer (Gemini -> OpenRouter -> offline) : Q&A, JSON tuning, report
├── workloads.py      # Presets and random workload generator
├── tests/test_simulator.py
├── requirements.txt
├── .env.example      # copy to .env
└── .devcontainer/devcontainer.json
```

## Quickstart

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # optional: add API keys
streamlit run app.py

```

---

## 💡 Contribution & Expansion Ideas

Want to take this project further? Here are high-impact features you can build:

* **Algorithm Expansion:** Add Preemptive Priority Scheduling, Shortest Remaining Time First (SRTF), or Multi-Level Feedback Queues (MLFQ).
* **Context Switch Penalty:** Introduce a configurable 1–2 ms idle CPU penalty on each swap to visualize real-world overhead.
* **Aging Mechanism:** Implement dynamic priority escalation for waiting tasks to demonstrate starvation prevention.
* **Closed-Loop Auto-Tuning:** Configure the AI agent to return structured JSON recommendations (e.g., `{"quantum": 4}`) and add an "Apply Suggestion" button that updates the scheduler in one click.
* **I/O Bursts:** Simulate mixed CPU-burst and I/O-wait cycles to model real database and network tasks.

```

### Next Steps for Git

Now that `requirements.txt` was created[cite: 7] and the README is formatted:

```bash
git add .
git commit -m "Add documentation and project requirements"
git push -u origin main

```
