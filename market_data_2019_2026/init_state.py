import os
import json

base_dir = r"C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest"
runlog_dir = os.path.join(base_dir, "launch", "runlog")
os.makedirs(runlog_dir, exist_ok=True)

state_path = os.path.join(runlog_dir, "B.state.json")
initial_state = {
    "status": "running",
    "attempts": 1,
    "lastError": None,
    "fundsDeep": 0,
    "universeQuarters": 0,
    "artifacts": [],
    "notes": ["Started 13F universe and flagship funds harvest."]
}
with open(state_path, "w", encoding="utf-8") as f:
    json.dump(initial_state, f, indent=2)

print("Initial B.state.json written.")
