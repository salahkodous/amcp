"""Escalation conformance subset: raise/decide/appeal/final, role guards,
human_escalation pause/resume, first_claim_wins auto-resolve, lazy timeout,
signed decisions.

Run:  python reference/test_escalation.py  (spawns server in-process)
"""

import json
import sys
import threading
import urllib.request
import urllib.error

sys.path.insert(0, ".")
from reference.agent import ThreadingHTTPServer, Handler, verify_envelope  # noqa: E402

BASE = "http://127.0.0.1:8485"
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


ROLES = {
    "coordinator": {"read": ["*"], "write": ["plan"], "message": ["*"], "delegate": True, "approve": False},
    "worker": {"read": ["brief"], "write": ["findings"], "message": ["room"], "delegate": False, "approve": False},
    "approver": {"read": ["*"], "write": [], "message": ["room"], "delegate": False, "approve": True},
}
MEMBERS = [{"actor": {"type": "agent", "id": "amcp:t:coord"}, "role": "coordinator"},
           {"actor": {"type": "agent", "id": "amcp:t:work"}, "role": "worker"},
           {"actor": {"type": "human", "id": "user:t"}, "role": "approver"}]


def make_session(policy):
    s, sess, _ = call("POST", "/amcp/session",
                      {"members": MEMBERS, "roles": ROLES, "conflict_policy": policy})
    assert s == 201, sess
    return sess["id"]


def esc(sid, **kw):
    return call("POST", f"/amcp/session/{sid}/escalate", kw)


def decide(sid, **kw):
    return call("POST", f"/amcp/session/{sid}/decide", kw)


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 8485), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    print("[ESC] coordinator_arbitrates + appeal")
    sid = make_session("coordinator_arbitrates")
    s, e, _ = esc(sid, actor={"id": "amcp:t:work"}, kind="flag", refs=["msg:12"])
    check("raise creates open escalation", s == 201 and e["state"] == "open", (s, e))
    eid = e["id"]
    check("policy frozen at raise", e["policy"] == "coordinator_arbitrates", e)
    s, err, _ = decide(sid, actor={"id": "amcp:t:work"}, escalation_id=eid,
                       decision="remove", rationale="spam")
    check("worker cannot decide", s == 403, s)
    s, d, _ = decide(sid, actor={"id": "amcp:t:coord"}, escalation_id=eid,
                     decision="remove", rationale="off-brief")
    check("coordinator decides", s == 200 and d["state"] == "decided", (s, d))
    dec = d["decision"]
    check("decision signed + verifies",
          verify_envelope({k: v for k, v in dec.items() if k != "signatures"},
                          dec["signatures"]["decider"]))
    s, a, _ = decide(sid, actor={"id": "amcp:t:work"}, escalation_id=eid, appeal=True)
    check("appeal reopens to approver", s == 200 and a["state"] == "appealed", (s, a))
    s, f, _ = decide(sid, actor={"id": "user:t"}, escalation_id=eid,
                     decision="keep", rationale="context matters")
    check("approver final", s == 200 and f["state"] == "final", (s, f))
    s, err, _ = decide(sid, actor={"id": "amcp:t:work"}, escalation_id=eid, appeal=True)
    check("second appeal refused", s == 409, s)

    print("[ESC] human_escalation freezes + resumes")
    sid2 = make_session("human_escalation")
    s, e, _ = esc(sid2, actor={"id": "amcp:t:work"}, kind="budget", refs=["spend:3"])
    check("raise pauses session", s == 201, s)
    s, view, _ = call("GET", f"/amcp/session/{sid2}?actor=amcp:t:coord")
    check("session paused while escalated", view["state"] == "paused", view)
    s, err, _ = decide(sid2, actor={"id": "amcp:t:coord"}, escalation_id=e["id"],
                       decision="allow")
    check("coordinator cannot decide human escalation", s == 403, s)
    s, d, _ = decide(sid2, actor={"id": "user:t"}, escalation_id=e["id"],
                     decision="deny", rationale="over budget")
    s, view, _ = call("GET", f"/amcp/session/{sid2}?actor=amcp:t:coord")
    check("decision resumes session", d["state"] == "decided" and view["state"] == "active",
          (d["state"], view["state"]))

    print("[ESC] first_claim_wins auto-resolves")
    sid3 = make_session("first_claim_wins")
    call("POST", f"/amcp/session/{sid3}/claim",
         {"actor": {"id": "amcp:t:work"}, "subtask": "batch-9"})
    s, e, _ = esc(sid3, actor={"id": "amcp:t:coord"}, kind="claim", refs=["batch-9"])
    check("auto-resolved with cited winner",
          s == 201 and e["state"] == "decided"
          and e["decision"].get("winner") == "amcp:t:work", (s, e))

    print("[ESC] timeout + guards")
    sid4 = make_session("coordinator_arbitrates")
    s, e, _ = esc(sid4, actor={"id": "amcp:t:work"}, kind="flag", timeout_seconds=0)
    s, t, _ = decide(sid4, actor={"id": "amcp:t:coord"}, escalation_id=e["id"],
                     decision="late")
    check("expired escalation hits safe default",
          s == 200 and t["state"] == "timed_out"
          and t["decision"]["outcome"] == "default_deny", (s, t))
    s, err, _ = esc(sid4, actor={"id": "amcp:t:ghost"}, kind="flag")
    check("non-member cannot raise", s == 403, s)

    srv.shutdown()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
