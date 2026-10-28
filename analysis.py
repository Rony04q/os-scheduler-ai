"""
analysis.py - Rule-based diagnostics (no LLM needed).

Used (a) to show instant diagnostics in the dashboard, (b) to give the LLM hard facts,
(c) as the offline fallback when no API key / quota is available.
"""
import re

import pandas as pd

from simulator import ALGORITHMS, PRIORITY_ALGOS


def detect_starvation(metrics: pd.DataFrame, threshold: int):
    """A process is flagged as starved if it waited >= threshold ms in one continuous stretch."""
    out = []
    for _, r in metrics.iterrows():
        if r["Max Wait Gap"] >= threshold:
            out.append({"pid": r["Process"], "max_gap": int(r["Max Wait Gap"]),
                        "waiting": int(r["Waiting"]), "burst": int(r["Burst"]),
                        "priority": int(r["Priority"])})
    return sorted(out, key=lambda d: -d["max_gap"])


def who_blocked(logs: pd.DataFrame, metrics: pd.DataFrame, pid: str):
    """CPU time consumed by other processes while `pid` was in the system (arrival -> finish)."""
    row = metrics[metrics["Process"] == pid].iloc[0]
    lo, hi = int(row["Arrival"]), int(row["Finish"])
    blockers = {}
    for _, seg in logs[logs["Type"] == "Execution"].iterrows():
        if seg["Process"] == pid:
            continue
        overlap = min(hi, seg["End"]) - max(lo, seg["Start"])
        if overlap > 0:
            blockers[seg["Process"]] = blockers.get(seg["Process"], 0) + int(overlap)
    return dict(sorted(blockers.items(), key=lambda kv: -kv[1]))


def find_bottlenecks(result, starved):
    """Return a list of (severity, text). severity in {'warning','info','success'}."""
    s, cfg, m = result.summary, result.config, result.metrics
    algo = cfg["algorithm"]
    out = []
    if starved:
        names = ", ".join(f"{d['pid']} (waited {d['max_gap']} ms in a row)" for d in starved)
        out.append(("warning", f"Starvation risk: {names}."))
    if s["Total Time"] and s["Switch Overhead ms"] / s["Total Time"] >= 0.15:
        pct = 100 * s["Switch Overhead ms"] / s["Total Time"]
        out.append(("warning", f"Context-switch overhead is high: {pct:.0f}% of total time "
                               f"({s['Context Switches']} switches x {cfg['context_switch']} ms)."))
    if algo == "Round-Robin":
        if cfg["quantum"] >= m["Burst"].max() and len(m) > 1:
            out.append(("info", f"Quantum ({cfg['quantum']}) >= longest burst ({m['Burst'].max()}): "
                                "Round-Robin degenerates into FCFS."))
        elif cfg["quantum"] == 1 and len(m) > 1:
            out.append(("info", "Quantum = 1 gives the best response time but the most context switches."))
    if algo == "FCFS" and (m["Waiting"] > 3 * m["Burst"]).any():
        slow = ", ".join(m.loc[m["Waiting"] > 3 * m["Burst"], "Process"])
        out.append(("warning", f"Convoy effect: short jobs ({slow}) are stuck behind a long job."))
    if s["Fairness"] < 0.6:
        out.append(("warning", f"Low fairness index ({s['Fairness']}): some processes are slowed far more than others."))
    if s["Idle ms"] > 0:
        out.append(("info", f"CPU was idle for {s['Idle ms']} ms (no process was ready)."))
    peak = int(result.queue["Ready Queue Length"].max()) if len(result.queue) else 0
    if peak >= 4:
        out.append(("info", f"Ready queue peaked at {peak} processes: the CPU is the bottleneck."))
    if not out:
        out.append(("success", "No bottlenecks detected for this workload and configuration."))
    return out


def heuristic_recommendation(result, starved):
    """Deterministic tuning suggestion. Also the fallback if the LLM's JSON is unusable."""
    cfg, s, m = result.config, result.summary, result.metrics
    algo, q, aging = cfg["algorithm"], cfg["quantum"], cfg["aging_interval"]
    avg_burst = float(m["Burst"].mean())
    rec = {"algorithm": algo, "quantum": q, "aging_interval": aging, "reason": ""}

    if algo in PRIORITY_ALGOS and starved and aging == 0:
        # choose an interval so the starved job climbs to the top priority in about half its observed wait
        diff = max(1, starved[0]["priority"] - int(m["Priority"].min()))
        rec["aging_interval"] = max(1, int(starved[0]["max_gap"] // 2) // diff)
        rec["reason"] = (f"{starved[0]['pid']} starves behind higher-priority work. Enabling aging "
                         f"(+1 priority every {rec['aging_interval']} ms of waiting) guarantees it eventually runs.")
    elif algo in PRIORITY_ALGOS and starved:
        rec["aging_interval"] = max(1, aging // 2)
        rec["reason"] = "Aging is on but too slow; halving the interval promotes waiting jobs sooner."
    elif algo == "Round-Robin" and s["Total Time"] and s["Switch Overhead ms"] / s["Total Time"] >= 0.15:
        rec["quantum"] = min(10, q * 2)
        rec["reason"] = "Too much time is lost switching; a larger quantum means fewer switches."
    elif algo == "Round-Robin" and q >= m["Burst"].max() and len(m) > 1:
        rec["quantum"] = max(1, round(avg_burst / 2))
        rec["reason"] = "The quantum is so large that RR behaves like FCFS; about half the average burst restores time-slicing."
    elif algo == "Round-Robin" and starved:
        rec["quantum"] = max(1, q // 2)
        rec["reason"] = "A smaller quantum rotates the CPU faster, cutting the longest wait."
    elif algo == "FCFS" and (m["Waiting"] > 3 * m["Burst"]).any():
        rec["algorithm"] = "SRTF (Preemptive)"
        rec["reason"] = "Short jobs are stuck behind a long one (convoy effect); SRTF minimises average waiting time."
    elif algo in ("SJF (Non-Preemptive)", "SRTF (Preemptive)") and starved:
        rec["algorithm"] = "Round-Robin"
        rec["quantum"] = max(2, round(avg_burst / 2))
        rec["reason"] = "Shortest-first postpones long jobs while short ones keep arriving; Round-Robin guarantees everyone a turn."
    else:
        rec["reason"] = "The current configuration already looks healthy; no change recommended."
    rec["quantum"] = int(min(10, max(1, rec["quantum"])))
    rec["aging_interval"] = int(min(30, max(0, rec["aging_interval"])))
    return rec


def _md_table(df: pd.DataFrame):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


_CAUSE = {
    "FCFS": "FCFS never preempts, so a process must wait for every job that arrived before it (convoy effect).",
    "SJF (Non-Preemptive)": "SJF always picks the shortest job, so long jobs are postponed while shorter ones are available.",
    "SRTF (Preemptive)": "SRTF preempts for any job with less remaining time, so long jobs keep getting pushed back.",
    "Priority (Non-Preemptive)": "Lower-priority jobs only run when no higher-priority job is ready; without aging they can wait indefinitely.",
    "Priority (Preemptive)": "A higher-priority arrival immediately preempts the CPU; without aging, low-priority jobs can starve.",
    "Round-Robin": "In Round-Robin each process waits roughly (n-1) x quantum between turns.",
}


def rule_based_answer(query, result, starved, findings, rec):
    m, logs, cfg = result.metrics, result.logs, result.config
    mentioned = [p for p in m["Process"] if re.search(rf"(?<!\w){re.escape(p)}(?!\w)", query, re.I)]
    lines = []
    for pid in mentioned:
        r = m[m["Process"] == pid].iloc[0]
        blockers = who_blocked(logs, m, pid)
        b = ", ".join(f"{k}: {v} ms" for k, v in blockers.items()) or "none"
        lines.append(
            f"**{pid}** arrived at t={r['Arrival']} (priority {r['Priority']}, burst {r['Burst']} ms). "
            f"It first got the CPU at t={r['First Start']}, waited {r['Waiting']} ms in total "
            f"(longest unbroken wait: {r['Max Wait Gap']} ms) and finished at t={r['Finish']}. "
            f"While it was in the system the CPU time went to: {b}.\n\n"
            f"*Why:* {_CAUSE[cfg['algorithm']]}")
    if not mentioned:
        s = result.summary
        lines.append(
            f"Under **{cfg['algorithm']}** the average waiting time is {s['Avg Waiting']} ms, average turnaround "
            f"{s['Avg Turnaround']} ms, with {s['Context Switches']} context switches and "
            f"{s['CPU Utilization %']}% CPU utilization (fairness {s['Fairness']}).")
    if starved:
        lines.append("**Starvation flagged for:** " + ", ".join(d["pid"] for d in starved) + ".")
    lines.append("**Findings:** " + " ".join(t for _, t in findings))
    lines.append(f"**Suggested tweak:** algorithm = {rec['algorithm']}, quantum = {rec['quantum']}, "
                 f"aging interval = {rec['aging_interval']} ms. {rec['reason']}")
    return "\n\n".join(lines)


def rule_based_report(result, starved, findings, rec, threshold):
    cfg, s = result.config, result.summary
    parts = [
        "# CPU Scheduling Report",
        "## Configuration",
        f"- Algorithm: **{cfg['algorithm']}**\n- Quantum: {cfg['quantum']} ms\n"
        f"- Context-switch cost: {cfg['context_switch']} ms\n- Aging interval: {cfg['aging_interval']} ms (0 = off)\n"
        f"- Starvation threshold: {threshold} ms",
        "## System Metrics",
        "\n".join(f"- {k}: {v}" for k, v in s.items()),
        "## Per-Process Metrics",
        _md_table(result.metrics[["Process", "Arrival", "Burst", "Priority", "Waiting", "Turnaround",
                                  "Response", "Max Wait Gap", "Preemptions"]]),
        "## Findings",
        "\n".join(f"- {t}" for _, t in findings),
        "## Recommendation",
        f"Set algorithm to **{rec['algorithm']}**, quantum **{rec['quantum']} ms**, aging interval "
        f"**{rec['aging_interval']} ms**. {rec['reason']}",
    ]
    if starved:
        parts.insert(-2, "## Starvation\n" + "\n".join(
            f"- {d['pid']}: longest continuous wait {d['max_gap']} ms (priority {d['priority']}, burst {d['burst']} ms)"
            for d in starved))
    return "\n\n".join(parts)
