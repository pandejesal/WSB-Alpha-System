import json
import os
import yaml
from typing import List, Dict, Any, Tuple

class MalformedSpecError(Exception):
    pass

def load_yaml(filepath: str) -> Dict[str, Any]:
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)

def validate_spec(spec: Dict[str, Any], filepath: str) -> bool:
    """
    Validates the structure of a loaded strategy YAML spec.
    Raises MalformedSpecError with a clear error message if validation fails.
    """
    required_fields = ["id", "name", "family", "universe"]

    spec_id = spec.get("id", "UNKNOWN_ID")

    for field in required_fields:
        if field not in spec:
            raise MalformedSpecError(f"Spec {spec_id} at {filepath} missing required field: {field}")

    # Some older specs use "parameters", some use "params". One must be present.
    if "parameters" not in spec and "params" not in spec:
        raise MalformedSpecError(f"Spec {spec_id} at {filepath} missing required field: parameters (or params)")

    # Allow either `signal` or both `entry_rules` and `exit_rules`
    has_signal = "signal" in spec
    has_rules = "entry_rules" in spec and "exit_rules" in spec

    if not has_signal and not has_rules:
         raise MalformedSpecError(f"Spec {spec_id} at {filepath} missing required rule definition: must have either 'signal' or both 'entry_rules' and 'exit_rules'")

    # Check that required fields are of expected types
    if not isinstance(spec["id"], str):
        raise MalformedSpecError(f"Spec {spec_id} at {filepath} has invalid type for id: expected str, got {type(spec['id']).__name__}")
    if not isinstance(spec["name"], str):
        raise MalformedSpecError(f"Spec {spec_id} at {filepath} has invalid type for name: expected str, got {type(spec['name']).__name__}")
    if not isinstance(spec["family"], str):
        raise MalformedSpecError(f"Spec {spec_id} at {filepath} has invalid type for family: expected str, got {type(spec['family']).__name__}")
    if not isinstance(spec["universe"], (str, list)):
        raise MalformedSpecError(f"Spec {spec_id} at {filepath} has invalid type for universe: expected str or list, got {type(spec['universe']).__name__}")
    if "parameters" in spec and not isinstance(spec["parameters"], dict):
        raise MalformedSpecError(f"Spec {spec_id} at {filepath} has invalid type for parameters: expected dict, got {type(spec['parameters']).__name__}")
    if "params" in spec and not isinstance(spec["params"], dict):
        raise MalformedSpecError(f"Spec {spec_id} at {filepath} has invalid type for params: expected dict, got {type(spec['params']).__name__}")

    # Validate HUNT protocol fields if they exist (they might not exist for legacy specs,
    # but new ones should have them. We will enforce that any provided have correct types).
    optional_type_checks = {
        "venue": str,
        "pre_registration_ref": str,
        "gates_passed": str,
        "verdict": str,
        "eval_records": str,
        "version": int,
        "status": str
    }

    for field, expected_type in optional_type_checks.items():
        if field in spec and not isinstance(spec[field], expected_type):
            raise MalformedSpecError(f"Spec {spec_id} at {filepath} has invalid type for {field}: expected {expected_type.__name__}, got {type(spec[field]).__name__}")

    return True

def load_registry(registry_path: str = "strategies/registry.json") -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Loads the registry.json, resolves each spec_file, validates it, and returns the list of active registry entries
    along with their loaded specs.

    Returns:
       active_entries: List of dicts, each containing the registry entry and a 'spec' key with the loaded YAML dict.
       portfolio: The portfolio dict from the registry.
    """
    if not os.path.exists(registry_path):
        raise FileNotFoundError(f"Registry file not found: {registry_path}")

    with open(registry_path, 'r') as f:
        registry_data = json.load(f)

    entries = registry_data.get("strategies", [])
    portfolio = registry_data.get("portfolio", {})

    loaded_entries = []

    # Track which specs we've seen
    seen_specs = set()

    # Add portfolio spec to seen if it exists
    if "spec_file" in portfolio:
        p_path = portfolio["spec_file"]
        if not os.path.exists(p_path):
             p_path = os.path.join(os.path.dirname(registry_path), os.path.basename(portfolio["spec_file"]))
        if os.path.exists(p_path):
            seen_specs.add(os.path.abspath(p_path))


    # We validate each entry has a spec_file and the spec_file exists
    for entry in entries:
        if "spec_file" not in entry:
            raise MalformedSpecError(f"Registry entry for {entry.get('id', 'UNKNOWN')} missing 'spec_file'")

        # Try relative to registry path's directory, or just directly if absolute/cwd
        spec_path = entry["spec_file"]
        if not os.path.exists(spec_path):
             # Try relative to the directory containing registry.json
             spec_path = os.path.join(os.path.dirname(registry_path), os.path.basename(entry["spec_file"]))
             if not os.path.exists(spec_path):
                 raise MalformedSpecError(f"Registry entry {entry.get('id', 'UNKNOWN')} points to non-existent spec_file: {entry['spec_file']}")

        # Load and validate
        spec = load_yaml(spec_path)
        validate_spec(spec, spec_path)

        # Verify that the id in the registry matches the id in the spec
        if entry.get("id") != spec.get("id"):
            raise MalformedSpecError(f"Registry entry id '{entry.get('id')}' does not match spec id '{spec.get('id')}' in {spec_path}")

        # Add the loaded spec into the entry dict for easy access
        entry_with_spec = entry.copy()
        entry_with_spec["spec"] = spec
        loaded_entries.append(entry_with_spec)
        seen_specs.add(os.path.abspath(spec_path))


    # Check for orphaned yaml specs in the same directory as the registry
    registry_dir = os.path.dirname(registry_path)
    if os.path.exists(registry_dir):
        for fname in os.listdir(registry_dir):
            if fname.endswith('.yaml') and not fname.startswith('_'):
                full_path = os.path.abspath(os.path.join(registry_dir, fname))
                if full_path not in seen_specs:
                    # Found a spec without a registry entry
                    print(f"WARNING: Found strategy spec without registry entry: {full_path}")

    return loaded_entries, portfolio
