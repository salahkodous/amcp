"""Verification behavior: verdict determinism, criteria_committed default,
tamper detection, check ordering. Wire contract proven by
conformance/fixtures/verification.json; subset semantics proven by
conformance/vectors/verification.json.

Run:  python reference/test_verification.py  (spawns server in-process)
"""

import json
import sys
import threading
import urllib.request
import urllib.error

sys.path.insert(0, ".")
from reference.agent import ThreadingHTTPServer, Handler, execute, CAPABILITIES  # noqa: E402
from reference import verification as vfy  # noqa: E402

BASE = "http://127.0.0.1:8487"
PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {detail}")


def call(method, path, body=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), dict(e.headers)


srv = ThreadingHTTPServer(("127.0.0.1", 8487), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
try:
    good = {"capability": "echo", "inputs": {"text": "hi"},
            "artifact": {"data": {"echo": "hi"}}}
    s, v1, _ = call("POST", "/amcp/verify", good)
    s, v2, _ = call("POST", "/amcp/verify", good)
    check("verdict deterministic", s == 200 and v1["verdict"] == "accepted"
          and v1["artifact_hash"] == v2["artifact_hash"], (s, v1))
    check("checks ordered schema, re-run", [c["name"] for c in v1["checks"]][:2]
          == ["output_schema", "re_execution"], v1["checks"])
    check("criteria_committed defaults false", v1["criteria_committed"] is False, v1)
    check("self-verified signature", v1.get("signature_valid") is True, v1)

    bad = {"capability": "echo", "inputs": {"text": "hi"},
           "artifact": {"data": {"echo": "hi", "extra": "smuggled"}}}
    s, v3, _ = call("POST", "/amcp/verify", bad)
    check("extra fields fail re-run but pass schema", s == 200 and v3["verdict"] == "rejected"
          and v3["checks"][0]["pass"] is True and v3["checks"][1]["pass"] is False, v3)

    # score_lead is deterministic: re-execution must accept honest output
    out = execute("score_lead", {"lead": {"budget": 1}})
    s, v4, _ = call("POST", "/amcp/verify",
                    {"capability": "score_lead", "inputs": {"lead": {"budget": 1}},
                     "artifact": {"data": out}})
    check("deterministic capability re-verifies", s == 200 and v4["verdict"] == "accepted", (s, v4))

    # subset validator edge cases (unit-level, no server roundtrip needed)
    check("unknown keywords ignored",
          vfy.check_schema({"type": "object", "format": "x", "properties": {}}, {}) == [])
    check("bool distinct from integer",
          vfy.check_schema({"type": "integer"}, False) != [])
    check("null type",
          vfy.check_schema({"type": "null"}, None) == []
          and vfy.check_schema({"type": "null"}, 0) != [])
    check("non-dict schema is vacuous",
          vfy.check_schema("nonsense", {"a": 1}) == [])
finally:
    srv.shutdown()

print(f"{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
