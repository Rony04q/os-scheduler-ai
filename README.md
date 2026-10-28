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
pytest -q tests                 # run the tests
```

## Demo script (for your viva / presentation)

1. Load preset **"Starvation demo (use Priority)"**, choose *Priority (Non-Preemptive)* → P7 is flagged as starved.
2. AI tab → *"Why is P7 starved?"* → **Analyze**: explains who held the CPU.
3. **Suggest tuning parameters** → see the what-if preview (aging interval) → **Apply suggestion**.
4. Starvation warning disappears; open **Compare Algorithms** to justify the choice; download the **report**.
5. Load **"Convoy effect"** with FCFS, then **"CPU-heavy vs interactive"** with Round-Robin and raise the context-switch cost to show the quantum trade-off.

## Conventions

* Time unit is 1 ms ticks. Lower priority number = higher priority.
* Aging: every *N* ms a process waits, its priority improves by 1 (the boost sticks once it runs).
* Context switch: charged whenever the CPU moves to a different process (not after idle).
