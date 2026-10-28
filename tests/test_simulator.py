import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from simulator import Process, simulate, compare_algorithms, run_round_robin, ALGORITHMS
from analysis import detect_starvation, heuristic_recommendation


def base():
    return [Process("P1", 0, 6, 2), Process("P2", 1, 4, 1), Process("P3", 2, 8, 3)]


def fin(r):
    return dict(zip(r.metrics["Process"], r.metrics["Finish"]))


def test_round_robin_hand_computed():
    r = simulate(base(), "Round-Robin", 2)
    assert fin(r) == {"P1": 14, "P2": 10, "P3": 18}
    assert r.summary["Avg Waiting"] == round((8 + 5 + 8) / 3, 2)
    assert r.summary["CPU Utilization %"] == 100.0


def test_fcfs():
    r = simulate(base(), "FCFS")
    assert fin(r) == {"P1": 6, "P2": 10, "P3": 18}
    assert r.summary["Context Switches"] == 2


def test_sjf_and_srtf():
    assert fin(simulate(base(), "SJF (Non-Preemptive)")) == {"P1": 6, "P2": 10, "P3": 18}
    assert fin(simulate(base(), "SRTF (Preemptive)")) == {"P1": 10, "P2": 5, "P3": 18}


def test_priority_preemptive_vs_non():
    ps = [Process("A", 0, 5, 3), Process("B", 1, 2, 1)]
    assert fin(simulate(ps, "Priority (Non-Preemptive)")) == {"A": 5, "B": 7}
    r = simulate(ps, "Priority (Preemptive)")
    assert fin(r) == {"A": 7, "B": 3}
    assert r.metrics.set_index("Process").loc["A", "Preemptions"] == 1


def starve_set():
    from workloads import preset_df
    return [Process(r.Process, r.Arrival, r.Burst, r.Priority)
            for r in preset_df("Starvation demo (use Priority)").itertuples()]


def test_starvation_and_aging_fix():
    r = simulate(starve_set(), "Priority (Non-Preemptive)")
    m = r.metrics.set_index("Process")
    assert m.loc["P7", "Max Wait Gap"] >= 20
    flagged = detect_starvation(r.metrics, 10)
    assert flagged[0]["pid"] == "P7"
    rec = heuristic_recommendation(r, flagged)
    assert rec["aging_interval"] > 0
    r2 = simulate(starve_set(), "Priority (Non-Preemptive)", aging_interval=rec["aging_interval"])
    assert r2.metrics.set_index("Process").loc["P7", "Finish"] < m.loc["P7", "Finish"]


def test_context_switch_cost_and_idle():
    r = simulate(base(), "Round-Robin", 2, context_switch=1)
    assert r.summary["Switch Overhead ms"] == r.summary["Context Switches"]
    assert r.summary["Total Time"] == 18 + r.summary["Switch Overhead ms"]
    idle = simulate([Process("A", 0, 2), Process("B", 5, 2)], "FCFS")
    assert idle.summary["Idle ms"] == 3 and idle.summary["Total Time"] == 7


def test_conservation_all_algorithms():
    for algo in ALGORITHMS:
        r = simulate(base(), algo, 3, 1)
        exec_time = r.logs[r.logs["Type"] == "Execution"].groupby("Process")["Duration"].sum().to_dict()
        assert exec_time == {"P1": 6, "P2": 4, "P3": 8}, algo
        assert (r.metrics["Waiting"] >= 0).all()


def test_compare_and_legacy_wrapper():
    assert len(compare_algorithms(base(), 2)) == len(ALGORITHMS)
    assert list(run_round_robin(base(), 2).columns) == ["Process", "Start", "End"]
