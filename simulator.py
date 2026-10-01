import pandas as pd

class Process:
    def __init__(self, pid, arrival, burst, priority=0):
        self.pid = pid
        self.arrival = arrival
        self.burst = burst
        self.remaining = burst
        self.priority = priority
        self.wait_time = 0
        self.turnaround_time = 0

def run_round_robin(processes, quantum):
    """
    Simulates a Round-Robin CPU scheduler.
    Returns a Pandas DataFrame containing the execution logs.
    """
    time = 0
    # Sort processes initially by arrival time
    processes = sorted(processes, key=lambda x: x.arrival)
    ready_queue = []
    logs = []
    
    completed = 0
    n = len(processes)
    index = 0
    
    # Push all processes that have arrived at time 0 to the ready queue
    while index < n and processes[index].arrival <= time:
        ready_queue.append(processes[index])
        index += 1
        
    while completed < n:
        # If queue is empty but processes are pending, the CPU sits idle
        if not ready_queue:
            time = processes[index].arrival
            while index < n and processes[index].arrival <= time:
                ready_queue.append(processes[index])
                index += 1
            continue
            
        current = ready_queue.pop(0)
        
        # CPU executes the process for either the full quantum or its remaining time
        execute_time = min(current.remaining, quantum)
        start_time = time
        time += execute_time
        current.remaining -= execute_time
        
        # Log the micro-execution block
        logs.append({
            "Process": current.pid,
            "Start": start_time,
            "End": time
        })
        
        # Check for newly arrived processes while this one was running
        while index < n and processes[index].arrival <= time:
            ready_queue.append(processes[index])
            index += 1
            
        # If the process isn't done, it goes back to the end of the line
        if current.remaining > 0:
            ready_queue.append(current)
        else:
            # Process finished tracking metrics
            completed += 1
            current.turnaround_time = time - current.arrival
            current.wait_time = current.turnaround_time - current.burst
            
    return pd.DataFrame(logs)