"""
Async Job Monitor (GridMarkets API Wrapper)

This snippet demonstrates the asynchronous polling mechanism used to check and report
the condition of remote GPU tasks sent to GridMarkets. 

Usage: Triggers immediately after jobs are submitted to the farm.
"""

import time
import json
import urllib.request
from datetime import datetime

ENVOY_API_URL = "http://localhost:8090"

def get_job_batch(submission_id: str) -> list[dict] | None:
    """Fetch the status of our submitted job batch from the local API gateway."""
    try:
        req = urllib.request.urlopen(f"{ENVOY_API_URL}/submissions", timeout=5)
        data = json.loads(req.read().decode())
        
        for sub in data.get("data", []):
            if sub.get("submission_id") == submission_id:
                return sub.get("jobs", [])
    except Exception:
        pass
    return None

def wait_for_project(submission_id: str, poll_interval: int = 30):
    """
    Continuous loop that evaluates the Cloud farm's progress and detects state changes.
    Waits intelligently until the Dependency chain (Renders -> Comps) completes.
    """
    last_status_cache = ""

    print(f"Polling GridMarkets for Job: {submission_id} (Every {poll_interval}s)")

    while True:
        jobs = get_job_batch(submission_id)
        
        if jobs:
            status_lines = []
            all_complete = True
            
            for job in jobs:
                name = job.get("name", "unknown")
                status = job.get("status", "unknown")
                prog = job.get("progress_percentage", 0)
                tasks = f"{job.get('tasks_completed', 0)}/{job.get('tasks_total', 0)}"
                
                status_lines.append(f"  {name}: {status} ({prog}%) [{tasks} tasks]")
                
                if status != "Completed":
                    all_complete = False
                if status in ["Failed", "Suspended"]:
                    raise RuntimeError(f"Cloud Architecture failure: Job {name} failed.")

            # Formatting logic to only spam the terminal if the state updates
            computed_status = "\\n".join(status_lines)
            if computed_status != last_status_cache:
                print(f"\\n[{datetime.now().strftime('%H:%M:%S')}]")
                print(computed_status)
                last_status_cache = computed_status

            if all_complete:
                print("\\nCloud Renders finished successfully! Triggering local downloads...")
                break
                
        time.sleep(poll_interval)
