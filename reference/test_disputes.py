"""Dispute lifecycle behavior: file/respond/concede, expiry escalation,
adjudication with signed decisions, single appeal, lazy finality, withdraw
guards, enforcement idempotency key shape. Wire contract proven by
conformance/fixtures/dispute*.json; this file pins behavior details.

Run:  python reference/test_disputes.py  (spawns server in-process)
"""

import json
import sys
import threading
import urllib.request
import urllib.error

sys.path.insert(0, ".")
from reference.agent import ThreadingHTTPServer, Handler, store  # noqa: E402
from reference import disputes as dsp  # noqa: E402

BASE = "http://127.0.0.1:8486"
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


def run_task(key="dispute-behavior-001"):
    s, r, _ = call("POST", "/amcp/task", {"capability": "echo", "inputs": {"text": "x"}})
    assert s == 200, r
    return r["receipt"]["receipt_id"]


def file_claim(rid, kind="wrong_output", remedy="redo", **kw):
    body = {"claimant": "amcp:t:buyer", "respondent": "amcp:t:seller",
            "subject": {"kind": "receipt", "ref": rid},
            "kind": kind, "remedy": remedy}
    body.update(kw)
    return call("POST", "/amcp/disputes", body)


srv = ThreadingHTTPServer(("127.0.0.1", 8486), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
try:
    # lazy clock is idempotent and ordered: expiry before finality
    d = {"state": "filed", "tier": "respondent", "answer_by": 100.0,
         "appeal_until": None, "history": []}
    dsp.touch(d, 50.0, "t0")
    check("no premature expiry", d["state"] == "filed" and d["tier"] == "respondent")
    dsp.touch(d, 100.0, "t1")
    check("expiry escalates tier", d["state"] == "adjudicating" and d["tier"] == "arbiter")
    n = len(d["history"])
    dsp.touch(d, 1e9, "t2")
    check("touch idempotent", len(d["history"]) == n and d["state"] == "adjudicating")

    ok, _ = dsp.can_respond({"state": "resolved"})
    check("closed disputes reject respond", not ok)
    ok, _ = dsp.can_adjudicate({"state": "decided"})
    check("decided disputes reject re-decide", not ok)
    ok, _ = dsp.can_appeal({"state": "decided", "appeals": 0, "appeal_until": 1e9}, 0)
    check("appeal allowed in window", ok)
    ok, _ = dsp.can_appeal({"state": "decided", "appeals": 1, "appeal_until": 1e9}, 0)
    check("second appeal refused", not ok)

    rid = run_task()
    s, r, _ = file_claim(rid)
    check("file 201", s == 201 and r["state"] == "filed", (s, r))
    did = r["dispute_id"]

    s, r, _ = call("POST", f"/amcp/disputes/{did}/respond",
                   {"actor": "amcp:t:buyer", "verdict": "concede"})
    check("non-respondent cannot answer", s == 403, (s, r))

    s, r, _ = call("POST", f"/amcp/disputes/{did}/respond",
                   {"actor": "amcp:t:seller", "verdict": "maybe"})
    check("bad verdict rejected", s == 422, (s, r))

    s, r, _ = call("POST", f"/amcp/disputes/{did}/respond",
                   {"actor": "amcp:t:seller", "verdict": "deny"})
    check("deny keeps open", s == 200 and r["state"] == "filed", (s, r))

    s, r, _ = call("POST", f"/amcp/disputes/{did}/adjudicate",
                   {"arbiter": "amcp:t:arbiter", "outcome": "upheld",
                    "remedy": "refund_partial", "amount_usdc": "abc"})
    check("bad refund amount rejected", s == 422, (s, r))

    s, r, _ = call("POST", f"/amcp/disputes/{did}/adjudicate",
                   {"arbiter": "amcp:t:arbiter", "outcome": "upheld",
                    "remedy": "refund_partial", "amount_usdc": "1.25"})
    check("adjudicate with amount", s == 200 and r["decision"]["amount_usdc"] == "1.25"
          and r["enforcement"]["source_key"].endswith(":decision"), (s, r))

    s, r, _ = call("POST", f"/amcp/disputes/{did}/appeal",
                   {"actor": "amcp:t:ghost", "grounds": "x"})
    check("stranger cannot appeal", s == 403, (s, r))

    # enforcement source keys are unique per dispute decision
    keys = [x["enforcement"]["source_key"] for x in store.disputes.values() if x["enforcement"]]
    check("enforcement keys unique", len(keys) == len(set(keys)), keys)
finally:
    srv.shutdown()

print(f"{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
