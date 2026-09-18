"""Money vectors: conformance/vectors/money.json enforced on the reference.
Run:  python reference/test_vectors.py
"""

import json
import sys
from decimal import Decimal

sys.path.insert(0, ".")
from reference.agent import _amt  # noqa: E402
from reference.directory import Directory  # noqa: E402
from reference import authorization as authz  # noqa: E402
from reference import verification as vfy  # noqa: E402

PASS, FAIL = 0, 0
vec = json.load(open("conformance/vectors/money.json"))
rep = json.load(open("conformance/vectors/reputation.json"))
dlg = json.load(open("conformance/vectors/delegation.json"))


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL {name} {detail}")


def dec_scale(d: Decimal) -> int:
    return max(0, -d.as_tuple().exponent)


for c in vec["cases"]:
    try:
        v = _amt(c["amount"])
        assert v == Decimal(c["micro"]) / 1_000_000, (v, c)
        assert dec_scale(v) == c["scale"], (dec_scale(v), c)
        assert str(v) == c["print"], (str(v), c)
        PASS += 1
    except AssertionError as e:
        check(f"case {c['amount']}", False, str(e)[:120])

for s in vec["sequences"]:
    total = Decimal(s["start"])
    for a in s["adds"]:
        total += Decimal(a)
    if str(total) == s["spent"]:
        PASS += 1
    else:
        check(f"sequence {s}", False, f"{total} != {s['spent']}")

for bad in vec["invalid"]:
    try:
        _amt(bad)
        check(f"invalid {bad!r}", False, "accepted")
    except ValueError:
        PASS += 1

assert rep["version"] == Directory.SCORE_VERSION, "vector/scorer version drift"
assert rep["weights"] == Directory.SCORE_WEIGHTS, "vector/weight drift"

DESC = {"amcp_version": "0.1", "id": "amcp:t:v", "name": "V", "description": "vector agent",
        "version": "1.0.0", "capabilities": []}

for case in rep["cases"]:
    d = Directory()
    d.submit(DESC)
    for e in case["evidence"]:
        d.record_evidence("amcp:t:v", e["kind"], e["ref"], e["outcome"],
                          weight_basis=e.get("weight_basis", "settlement"),
                          reviewer=e.get("reviewer", ""), ts=e.get("ts", ""))
    got = d.score("amcp:t:v")
    exp = case["expected"]
    ok = got["version"] == "reputation-v1" and got["scores"] == exp["scores"]
    for k in ("composite",):
        g, w = got[k], exp[k]
        ok = ok and ((g is None and w is None) or (g is not None and w is not None and abs(g - w) < 1e-9))
    ok = ok and got["experimental"] == exp["experimental"]
    check(f"reputation {case['name']}", ok, f"{got} != {exp}" if not ok else "")

assert dlg["version"] == authz.VERSION, "vector/evaluator version drift"
from datetime import datetime, timezone
_NOW = datetime.fromisoformat(dlg["now"].replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()
for case in dlg["cases"]:
    got = authz.evaluate(case["chain"], case["request"], _NOW)
    check(f"delegation {case['name']}", got == case["expected"], f"{got} != {case['expected']}" if got != case["expected"] else "")

ver = json.load(open("conformance/vectors/verification.json"))
assert ver["version"] == vfy.VERSION, "vector/verifier version drift"
for case in ver["cases"]:
    errs = vfy.check_schema(case["schema"], case["instance"])
    check(f"verification {case['name']}", (not errs) == case["valid"], f"{errs} != valid={case['valid']}")

print(f"{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
