"""L0–L2 conformance subset against the in-process reference agent.

Run:  python reference/test_conformance.py
Covers: descriptor validity (repo schema), task execution, trial probe,
idempotent replay identical, unknown capability code, schema-violation code,
receipt offline verification (dev HMAC), receipts listing + pagination shape.
"""

import json
import sys
import threading
import urllib.request

sys.path.insert(0, ".")
from jsonschema import Draft202012Validator  # noqa: E402
from reference.agent import ThreadingHTTPServer, Handler  # noqa: E402
from reference.signer import DevSigner  # noqa: E402

BASE = "http://127.0.0.1:8479"
PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {detail}")


def call(method, path, body=None, headers=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", **(headers or {})},
        method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), dict(e.headers)


def main():
    global BASE
    srv = ThreadingHTTPServer(("127.0.0.1", 8479), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    schema = json.load(open("schemas/descriptor.schema.json"))

    print("[L0] descriptor")
    s, desc, _ = call("GET", "/amcp")
    check("GET /amcp 200", s == 200, s)
    try:
        Draft202012Validator(schema).validate(desc)
        check("descriptor validates", True)
    except Exception as e:  # noqa: BLE001
        check("descriptor validates", False, str(e)[:200])
    s2, desc2, _ = call("GET", "/.well-known/amcp.json")
    check("well-known mirrors /amcp", s2 == 200 and desc2["id"] == desc["id"])

    print("[L2] tasks")
    s, r, _ = call("POST", "/amcp/task",
                   {"capability": "echo", "inputs": {"text": "hello"}},
                   {"Idempotency-Key": "test-key-001"})
    check("echo executes", s == 200 and r["artifact"]["data"] == {"echo": "hello"}, s)
    s, r2, h2 = call("POST", "/amcp/task",
                     {"capability": "echo", "inputs": {"text": "hello"}},
                     {"Idempotency-Key": "test-key-001"})
    check("idempotent replay identical + flagged",
          s == 200 and r2 == r and h2.get("X-Idempotent-Replayed") == "true")
    s, r3, _ = call("POST", "/amcp/task",
                    {"capability": "echo", "inputs": {"text": "other"}},
                    {"Idempotency-Key": "test-key-001"})
    check("same key + different payload rejected",
          s == 422 and r3["error"]["code"] == "idempotency_key_in_use", (s, r3))
    s, e, _ = call("POST", "/amcp/task", {"capability": "nope", "inputs": {}})
    check("unknown capability code", s == 404 and e["error"]["code"] == "unknown_capability", s)
    s, e, _ = call("POST", "/amcp/task", {"capability": "echo", "inputs": {}})
    check("schema violation code", s == 422 and e["error"]["code"] == "artifact_rejected", s)

    print("[L2] trial + receipts")
    s, r, _ = call("POST", "/amcp/task",
                   {"capability": "score_lead", "inputs": {"lead": {"budget": 500000}},
                    "trial": True, "price_usdc": "0.01"})
    check("trial executes", s == 200 and r["receipt"]["trial"] is True, s)
    rec = r["receipt"]
    v = DevSigner(b"dev-secret-change-me").verify(
        {k: v for k, v in rec.items() if k != "signatures"}, rec["signatures"]["platform"])
    check("receipt verifies offline (dev secret)", v)
    s, listing, _ = call("GET", "/amcp/receipts?limit=5")
    check("receipts list + pagination shape",
          s == 200 and isinstance(listing["data"], list) and "pagination" in listing, s)

    srv.shutdown()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    import urllib.error
    main()
