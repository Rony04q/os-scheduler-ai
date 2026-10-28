"""workloads.py - Preset and random process workloads for the dashboard."""
import random

import pandas as pd

COLUMNS = ["Process", "Arrival", "Burst", "Priority"]

PRESETS = {
    "Default demo": [("P1", 0, 6, 2), ("P2", 1, 4, 1), ("P3", 2, 8, 3)],
    "Starvation demo (use Priority)": [
        ("P1", 0, 4, 1), ("P2", 3, 4, 1), ("P3", 6, 4, 1), ("P4", 9, 4, 1),
        ("P5", 12, 4, 1), ("P6", 15, 4, 1), ("P7", 1, 3, 5),
    ],
    "Convoy effect (use FCFS)": [
        ("P1", 0, 20, 1), ("P2", 1, 2, 1), ("P3", 2, 3, 1), ("P4", 3, 2, 1),
    ],
    "CPU-heavy vs interactive (use RR)": [
        ("Batch", 0, 24, 3), ("Edit", 1, 3, 1), ("Shell", 2, 2, 1), ("Web", 3, 4, 2),
    ],
    "Idle gap in the middle": [("P1", 0, 3, 1), ("P2", 10, 4, 2), ("P3", 11, 2, 1)],
}


def preset_df(name):
    return pd.DataFrame(PRESETS[name], columns=COLUMNS)


def random_workload(n=5, seed=None, max_arrival=8, burst_min=2, burst_max=12, max_priority=5):
    rng = random.Random(seed)
    rows = [(f"P{i + 1}", rng.randint(0, max_arrival), rng.randint(burst_min, burst_max),
             rng.randint(1, max_priority)) for i in range(n)]
    return pd.DataFrame(rows, columns=COLUMNS)
