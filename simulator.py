"""
simulator.py - Discrete-event CPU scheduling engine.

Supports: FCFS, SJF, SRTF, Priority (non-preemptive / preemptive), Round-Robin.
Features: context-switch cost, idle tracking, aging (starvation prevention),
          per-process metrics, system-level metrics, ready-queue history.

Convention: a LOWER priority number means HIGHER priority (like Unix nice values).
The simulation advances in 1 ms ticks, which keeps every rule easy to reason about.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

ALGORITHMS = [
    "FCFS",
    "SJF (Non-Preemptive)",
    "SRTF (Preemptive)",
    "Priority (Non-Preemptive)",
    "Priority (Preemptive)",
    "Round-Robin",
]
PRIORITY_ALGOS = ("Priority (Non-Preemptive)", "Priority (Preemptive)")
PREEMPTIVE_ALGOS = ("SRTF (Preemptive)", "Priority (Preemptive)")

CS_LABEL = "Context Switch"
IDLE_LABEL = "Idle"
RESERVED_NAMES = {CS_LABEL, IDLE_LABEL}


class Process:
    def __init__(self, pid, arrival, burst, priority=0):
        self.pid = str(pid)
        self.arrival = int(arrival)
        self.burst = int(burst)
        self.priority = int(priority)
        # runtime state
        self.remaining = self.burst
        self.dyn_priority = self.priority  # priority after aging boosts
        self.ready_since = None
        self.first_start = None
        self.finish = None
        self.max_gap = 0  # longest continuous time spent waiting in the ready queue
        self.preemptions = 0
        # kept for backward compatibility with the first version
        self.wait_time = 0
        self.turnaround_time = 0

    def clone(self):
        return Process(self.pid, self.arrival, self.burst, self.priority)


@dataclass
class SimResult:
    logs: pd.DataFrame
    metrics: pd.DataFrame
    summary: dict
    queue: pd.DataFrame
    config: dict = field(default_factory=dict)


def simulate(processes, algorithm="Round-Robin", quantum=2, context_switch=0, aging_interval=0) -> SimResult:
    """
    Run one scheduling simulation.

    quantum         - time slice (Round-Robin only)
    context_switch  - ms of CPU time wasted whenever the CPU switches to a different process
    aging_interval  - Priority algorithms only: every `aging_interval` ms a process waits in the
                      ready queue its priority improves by 1 (0 disables aging)
    """
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm: {algorithm}")
    if quantum < 1:
        raise ValueError("quantum must be >= 1")
    config = dict(algorithm=algorithm, quantum=int(quantum),
                  context_switch=int(context_switch), aging_interval=int(aging_interval))

    procs = sorted((p.clone() for p in processes), key=lambda p: p.arrival)  # stable sort
    n = len(procs)
    if n == 0:
        return _empty_result(config)

    order = {p.pid: i for i, p in enumerate(procs)}
    use_priority = algorithm in PRIORITY_ALGOS

    time = 0
    idx = 0
    ready: list[Process] = []
    current = None
    slice_used = 0
    last_pid = None
    completed = 0
    switches = 0
    ticks: list[str] = []
    queue_hist: list[tuple[int, int]] = []

    def admit():
        nonlocal idx
        while idx < n and procs[idx].arrival <= time:
            p = procs[idx]
            p.ready_since = p.arrival
            ready.append(p)
            idx += 1

    def eff_priority(p):
        if aging_interval > 0 and p.ready_since is not None:
            return p.dyn_priority - (time - p.ready_since) // aging_interval
        return p.dyn_priority

    def key(p, running=False):
        if algorithm == "FCFS":
            return (p.arrival, order[p.pid])
        if algorithm == "SJF (Non-Preemptive)":
            return (p.burst, p.arrival, order[p.pid])
        if algorithm == "SRTF (Preemptive)":
            return (p.remaining, p.arrival, order[p.pid])
        if use_priority:
            pr = p.dyn_priority if running else eff_priority(p)
            return (pr, p.arrival, order[p.pid])
        return (order[p.pid],)

    def pick():
        if algorithm == "Round-Robin":
            return ready[0]  # FIFO queue
        return min(ready, key=key)

    while completed < n:
        admit()

        # ---- preemption decisions -------------------------------------------------
        if current is not None:
            preempt = False
            if algorithm in PREEMPTIVE_ALGOS and ready:
                if key(pick())[0] < key(current, running=True)[0]:
                    preempt = True
            elif algorithm == "Round-Robin" and slice_used >= quantum:
                if ready:
                    preempt = True
                else:
                    slice_used = 0  # nobody else waiting: keep running, fresh slice
            if preempt:
                current.preemptions += 1
                current.ready_since = time
                ready.append(current)
                current = None

        # ---- dispatch -------------------------------------------------------------
        if current is None and ready:
            p = pick()
            gap = time - p.ready_since
            p.max_gap = max(p.max_gap, gap)
            if use_priority:
                p.dyn_priority = eff_priority(p)  # aging boost sticks once the process runs
            ready.remove(p)
            if last_pid is not None and last_pid != p.pid:
                switches += 1
                for _ in range(context_switch):
                    ticks.append(CS_LABEL)
                    queue_hist.append((time, len(ready)))
                    time += 1
                    admit()
            current = p
            slice_used = 0
            if p.first_start is None:
                p.first_start = time

        # ---- idle -----------------------------------------------------------------
        if current is None:
            ticks.append(IDLE_LABEL)
            queue_hist.append((time, 0))
            time += 1
            last_pid = None
            continue

        # ---- run for one tick -----------------------------------------------------
        ticks.append(current.pid)
        queue_hist.append((time, len(ready)))
        time += 1
        current.remaining -= 1
        slice_used += 1
        last_pid = current.pid
        if current.remaining == 0:
            current.finish = time
            current.turnaround_time = time - current.arrival
            current.wait_time = current.turnaround_time - current.burst
            completed += 1
            current = None
            slice_used = 0

    logs = _ticks_to_segments(ticks)
    metrics = _build_metrics(procs)
    summary = _build_summary(logs, metrics, time, switches, n)
    queue = pd.DataFrame(queue_hist, columns=["Time", "Ready Queue Length"])
    return SimResult(logs, metrics, summary, queue, config)


# ----------------------------------------------------------------------------------------
def _ticks_to_segments(ticks):
    rows = []
    start = 0
    for i in range(1, len(ticks) + 1):
        if i == len(ticks) or ticks[i] != ticks[start]:
            label = ticks[start]
            kind = label if label in RESERVED_NAMES else "Execution"
            rows.append({"Process": label, "Start": start, "End": i, "Duration": i - start, "Type": kind})
            start = i
    return pd.DataFrame(rows, columns=["Process", "Start", "End", "Duration", "Type"])


def _build_metrics(procs):
    rows = []
    for p in sorted(procs, key=lambda x: x.pid):
        tat = p.finish - p.arrival
        wait = tat - p.burst
        rows.append({
            "Process": p.pid, "Arrival": p.arrival, "Burst": p.burst, "Priority": p.priority,
            "First Start": p.first_start, "Finish": p.finish,
            "Waiting": wait, "Turnaround": tat, "Response": p.first_start - p.arrival,
            "Max Wait Gap": p.max_gap, "Preemptions": p.preemptions,
            "Slowdown": round(tat / p.burst, 2),
        })
    return pd.DataFrame(rows)


def _build_summary(logs, metrics, total_time, switches, n):
    busy = int(logs.loc[logs["Type"] == "Execution", "Duration"].sum())
    cs_time = int(logs.loc[logs["Type"] == CS_LABEL, "Duration"].sum())
    idle = int(logs.loc[logs["Type"] == IDLE_LABEL, "Duration"].sum())
    x = metrics["Slowdown"].astype(float)
    fairness = float(x.sum() ** 2 / (len(x) * (x ** 2).sum())) if len(x) else 1.0
    return {
        "Total Time": int(total_time),
        "Avg Waiting": round(float(metrics["Waiting"].mean()), 2),
        "Avg Turnaround": round(float(metrics["Turnaround"].mean()), 2),
        "Avg Response": round(float(metrics["Response"].mean()), 2),
        "Max Waiting": int(metrics["Waiting"].max()),
        "CPU Utilization %": round(100 * busy / total_time, 1) if total_time else 0.0,
        "Throughput": round(n / total_time, 3) if total_time else 0.0,
        "Context Switches": int(switches),
        "Switch Overhead ms": cs_time,
        "Idle ms": idle,
        "Fairness": round(fairness, 3),
    }


def _empty_result(config):
    logs = pd.DataFrame(columns=["Process", "Start", "End", "Duration", "Type"])
    return SimResult(logs, pd.DataFrame(), {}, pd.DataFrame(columns=["Time", "Ready Queue Length"]), config)


def compare_algorithms(processes, quantum=2, context_switch=0, aging_interval=0) -> pd.DataFrame:
    """Run the same workload through every algorithm and tabulate the results."""
    rows = []
    for algo in ALGORITHMS:
        r = simulate(processes, algo, quantum, context_switch, aging_interval)
        s = r.summary
        rows.append({
            "Algorithm": algo,
            "Avg Waiting": s["Avg Waiting"], "Avg Turnaround": s["Avg Turnaround"],
            "Avg Response": s["Avg Response"], "Max Waiting": s["Max Waiting"],
            "CPU Util %": s["CPU Utilization %"], "Context Switches": s["Context Switches"],
            "Fairness": s["Fairness"], "Total Time": s["Total Time"],
        })
    return pd.DataFrame(rows)


def run_round_robin(processes, quantum):
    """Backward-compatible wrapper from version 1 (returns only the execution log)."""
    logs = simulate(processes, "Round-Robin", quantum).logs
    return logs[logs["Type"] == "Execution"][["Process", "Start", "End"]].reset_index(drop=True)
