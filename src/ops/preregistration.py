import os
import json
import yaml
import hashlib
import re
import datetime
from typing import Dict, Any, Optional

def load_yaml_spec(spec_path: str) -> Dict[str, Any]:
    with open(spec_path, 'r') as f:
        return yaml.safe_load(f)

def _get_max_cycle(docs_dir: str) -> int:
    max_cycle = 0
    if os.path.exists(docs_dir):
        for f in os.listdir(docs_dir):
            match = re.match(r'cycle(\d+)_prereg_.*\.md', f)
            if match:
                max_cycle = max(max_cycle, int(match.group(1)))
    return max_cycle

def freeze_preregistration(spec_path: str, claim: str, cycle: Optional[int] = None, docs_dir: str = "docs/data") -> str:
    spec = load_yaml_spec(spec_path)
    family = spec.get('family')
    if not family:
        raise ValueError(f"Spec file {spec_path} is missing 'family' field.")

    if cycle is None:
        cycle = _get_max_cycle(docs_dir) + 1

    os.makedirs(docs_dir, exist_ok=True)
    filename = f"cycle{cycle}_prereg_{family}.md"
    filepath = os.path.join(docs_dir, filename)

    if os.path.exists(filepath):
        raise FileExistsError(f"Pre-registration doc already exists at {filepath}. Refusing to overwrite.")

    with open(spec_path, 'r') as f:
        spec_content = f.read()

    doc_content = f"""# Pre-registration: {family}
Cycle: {cycle}
Date: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Claim
{claim}

## Strategy Spec
```yaml
{spec_content}
```
"""

    with open(filepath, 'w') as f:
        f.write(doc_content)

    return filepath

def record_evaluation(spec_path: str, verdict: str, cycle: Optional[int] = None, eval_path: Optional[str] = None, registry_path: str = "strategies/registry.json", docs_dir: str = "docs/data") -> str:
    spec = load_yaml_spec(spec_path)
    family = spec.get('family')
    if not family:
        raise ValueError(f"Spec file {spec_path} is missing 'family' field.")

    if cycle is None:
        cycle = _get_max_cycle(docs_dir)
        if cycle == 0:
            raise FileNotFoundError(f"no claim registered for family {family} in cycle {cycle} — run preregister freeze first")

    prereg_filename = f"cycle{cycle}_prereg_{family}.md"
    prereg_filepath = os.path.join(docs_dir, prereg_filename)

    if not os.path.exists(prereg_filepath):
        raise FileNotFoundError(f"no claim registered for family {family} in cycle {cycle} — run preregister freeze first")

    # Read claim from prereg doc
    with open(prereg_filepath, 'r') as f:
        prereg_content = f.read()

    claim_match = re.search(r'## Claim\n(.*?)\n\n## Strategy Spec', prereg_content, re.DOTALL)
    declared_claim = claim_match.group(1).strip() if claim_match else ""

    # Generate spec fingerprint
    with open(spec_path, 'r') as f:
        spec_content = f.read()
    spec_fingerprint = hashlib.sha256(spec_content.encode('utf-8')).hexdigest()

    # Parse evaluation results
    eval_data = {
        "spec_fingerprint": spec_fingerprint,
        "declared_claim": declared_claim,
        "verdict": verdict,
        "evaluated_at": datetime.datetime.now().isoformat(),
        "gate_script": "unknown"
    }

    report_path = os.path.join(docs_dir, "backtest_report.json")
    if os.path.exists(report_path):
        with open(report_path, 'r') as f:
            try:
                report = json.load(f)
                eval_data["walk_forward"] = report.get("portfolio_summary", {})
                eval_data["permutation"] = report.get("all_strategies", [])
                eval_data["dsr"] = report.get("benchmark_comparison", {}).get("strategy_sharpe")
                eval_data["gate_script"] = "scripts/comprehensive_backtest_report.py"
            except Exception:
                pass
    elif eval_path:
        eval_data["walk_forward"] = eval_path
        eval_data["permutation"] = eval_path
        eval_data["gate_script"] = "raw_output"

    eval_filename = f"cycle{cycle}_eval_{family}.json"
    eval_filepath = os.path.join(docs_dir, eval_filename)

    with open(eval_filepath, 'w') as f:
        json.dump(eval_data, f, indent=2)

    # Update registry
    if os.path.exists(registry_path):
        with open(registry_path, 'r') as f:
            registry = json.load(f)
    else:
        registry = {"strategies": []}

    strategy_entry = next((s for s in registry.get("strategies", []) if s.get("family") == family), None)

    if strategy_entry:
        strategy_entry["verdict"] = verdict
        strategy_entry["eval_file"] = eval_filepath
        if verdict == "PASS":
            strategy_entry["status"] = "ported"
        else:
            strategy_entry["status"] = "inactive"
    else:
        new_entry = {
            "id": spec.get("id", family),
            "name": spec.get("name", family),
            "family": family,
            "venue": "alpaca",
            "spec_file": spec_path,
            "gates_passed": "5/5" if verdict == "PASS" else "0/5",
            "rank": len(registry.get("strategies", [])) + 1,
            "status": "ported" if verdict == "PASS" else "inactive",
            "verdict": verdict,
            "eval_file": eval_filepath
        }
        if "strategies" not in registry:
            registry["strategies"] = []
        registry["strategies"].append(new_entry)

    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)

    return eval_filepath
