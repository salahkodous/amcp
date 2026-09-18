"""Verification runner, verify-v1 (spec/verification.md).
Deterministic verdicts over (capability, inputs, artifact, criteria):
schema -> re-execution -> acceptance criteria. Pure logic; the agent owns
routes. Subset-schema validator shared by cross-implementation vectors.
"""

VERSION = "verify-v1"

METHODS = ("schema", "re_execution", "acceptance_criteria")


def check_schema(schema: dict, value, path="$") -> list:
    """Subset validator (spec/verification.md §4). Unknown keywords ignored.
    Returns error strings; empty means valid."""
    if not isinstance(schema, dict):
        return []
    errors = []
    want = schema.get("type")
    if want is not None and not _type_ok(want, value):
        errors.append(f"{path}: expected {want}")
        return errors  # shape wrong; deeper checks would noise
    if isinstance(value, dict):
        for field in schema.get("required", []) or []:
            if field not in value:
                errors.append(f"{path}: missing required field {field!r}")
        for key, subschema in (schema.get("properties") or {}).items():
            if key in value:
                errors.extend(check_schema(subschema, value[key], f"{path}.{key}"))
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for i, item in enumerate(value):
            errors.extend(check_schema(schema["items"], item, f"{path}[{i}]"))
    if "enum" in schema and isinstance(schema["enum"], list):
        if value not in schema["enum"]:
            errors.append(f"{path}: not in enum")
    if isinstance(value, bool):
        pass
    elif isinstance(value, (int, float)):
        if schema.get("minimum") is not None and value < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if schema.get("maximum") is not None and value > schema["maximum"]:
            errors.append(f"{path}: above maximum")
    if isinstance(value, str):
        if schema.get("minLength") is not None and len(value) < schema["minLength"]:
            errors.append(f"{path}: too short")
        if schema.get("maxLength") is not None and len(value) > schema["maxLength"]:
            errors.append(f"{path}: too long")
    return errors


def _type_ok(want: str, value) -> bool:
    if want == "object":
        return isinstance(value, dict)
    if want == "array":
        return isinstance(value, list)
    if want == "string":
        return isinstance(value, str)
    if want == "boolean":
        return isinstance(value, bool)
    if want == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if want == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if want == "null":
        return value is None
    return True  # unknown type keyword: ignore per §4


def verify(capability: str, inputs: dict, data, criteria, criteria_committed: bool,
           execute, output_schema: dict,
           artifact_hash: str, criteria_hash, verifier: str, verified_at: str) -> dict:
    """Assemble the verdict. `execute`/`output_schema` injected so the
    reference agent.py stays the only place capabilities live."""
    checks = []
    schema_errors = check_schema(output_schema or {}, data)
    checks.append({"name": "output_schema", "pass": not schema_errors,
                   "detail": "; ".join(schema_errors)[:200] or "matches capability output schema"})
    rerun_detail, rerun_pass = "capability not re-executable", True
    try:
        expected = execute(capability, inputs)
        rerun_pass = expected == data
        rerun_detail = "re-execution matches" if rerun_pass else "re-execution differs"
    except Exception as e:  # noqa: BLE001 — unknown capability surfaces as 404 upstream; anything else fails the check
        rerun_pass, rerun_detail = False, f"re-execution failed: {e}"[:200]
    checks.append({"name": "re_execution", "pass": rerun_pass, "detail": rerun_detail})
    if criteria is not None:
        crit_errors = check_schema(criteria, data)
        checks.append({"name": "acceptance_criteria", "pass": not crit_errors,
                       "detail": "; ".join(crit_errors)[:200] or "meets acceptance criteria"})
    verdict = "accepted" if all(c["pass"] for c in checks) else "rejected"
    return {"verdict": verdict, "checks": checks, "artifact_hash": artifact_hash,
            "criteria_hash": criteria_hash, "criteria_committed": bool(criteria_committed),
            "verifier": verifier, "verified_at": verified_at}
