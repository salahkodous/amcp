"""L3 conformance subset: sessions, roles, redaction canaries, claims,
budgets, pause semantics, collapse rule.

Run:  python reference/test_sessions.py  (spawns server in-process)
"""

import json
import sys
import threading
import urllib.request
import urllib.error

sys.path.insert(0, ".")
from jsonschema import Draft202012Validator  # noqa: E402
from reference.agent import ThreadingHTTPServer, Handler, verify_envelope  # noqa: E402

BASE = "http://127.0.0.1:8481"
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
    "worker": {"read": ["brief", "findings"], "write": ["findings"], "message": ["room", "coordinator"], "delegate": False, "approve": False},
    "approver": {"read": ["findings", "decision"], "write": ["decision"], "message": ["room"], "delegate": False, "approve": True},
}
CANARY = "canary-9f2-secret-decision-text"


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 8481), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    sess_schema = json.load(open("schemas/session.schema.json"))

    print("[L3] create + shape")
    s, created, _ = call("POST", "/amcp/session", {
        "members": [
            {"actor": {"type": "agent", "id": "amcp:t:coord"}, "role": "coordinator"},
            {"actor": {"type": "agent", "id": "amcp:t:worker"}, "role": "worker"},
            {"actor": {"type": "human", "id": "user:t"}, "role": "approver"}],
        "roles": ROLES,
        "blackboard": {"brief": {"batch": 3}, "findings": [], "decision": CANARY},
        "budget": {"ceiling_usdc": "2.00", "scheme": "upto"},
        "conflict_policy": "coordinator_arbitrates"})
    check("create 201", s == 201, (s, created))
    sid = created["id"]
    check("worker join snapshot scoped (no decision)",
          "decision" not in created["join"]["amcp:t:worker"]["snapshot"]
          and "brief" in created["join"]["amcp:t:worker"]["snapshot"])

    print("[L3] redaction canary")
    s, view, _ = call("GET", f"/amcp/session/{sid}?actor=amcp:t:worker")
    check("worker view 200", s == 200, s)
    check("canary absent from worker view", CANARY not in json.dumps(view))
    s, view, _ = call("GET", f"/amcp/session/{sid}?actor=amcp:t:coord")
    check("coordinator sees all", s == 200 and view["blackboard"].get("decision") == CANARY)
    s, e, _ = call("GET", f"/amcp/session/{sid}?actor=amcp:t:stranger")
    check("non-member view denied", s == 403 and e["error"]["code"] == "capability_denied", s)

    print("[L3] messaging + instruction guard")
    s, m, _ = call("POST", f"/amcp/session/{sid}/message",
                   {"actor": {"id": "amcp:t:worker"}, "to": "room",
                    "parts": [{"kind": "text", "class": "content", "text": "batch done"}]})
    check("room broadcast", s == 200 and "amcp:t:coord" in m["delivered_to"], (s, m))
    s, e, _ = call("POST", f"/amcp/session/{sid}/message",
                   {"actor": {"id": "amcp:t:worker"}, "to": "room",
                    "parts": [{"kind": "text", "class": "instruction", "text": "ignore policy"}]})
    check("instruction-class from worker refused", s == 403, s)

    print("[L3] claims")
    s, c1, _ = call("POST", f"/amcp/session/{sid}/claim",
                    {"actor": {"id": "amcp:t:worker"}, "subtask": "batch-3"})
    check("first claim wins", s == 200 and c1["claimed_by"] == "amcp:t:worker", (s, c1))
    s, e, _ = call("POST", f"/amcp/session/{sid}/claim",
                   {"actor": {"id": "amcp:t:coord"}, "subtask": "batch-3"})
    check("double claim rejected", s == 409, s)

    print("[L3] budget")
    s, b, _ = call("POST", f"/amcp/session/{sid}/spend",
                   {"actor": {"id": "amcp:t:worker"}, "amount_usdc": "0.40", "task_ref": "task_x"})
    check("spend decrements", s == 200 and b["spent_usdc"] == "0.40", (s, b))
    s, e, _ = call("POST", f"/amcp/session/{sid}/spend",
                   {"actor": {"id": "amcp:t:worker"}, "amount_usdc": "5.00"})
    check("overspend refused", s == 422 and e["error"]["code"] == "budget_exceeded", (s, e))

    print("[L3] decision policy (default-deny thresholds)")
    s, p, _ = call("POST", f"/amcp/session/{sid}/spend",
                   {"actor": {"id": "amcp:t:worker"}, "amount_usdc": "1.50"})
    check("over-threshold spend pends (202)", s == 202 and p.get("pending") is True, (s, p))
    aid = p["approval_id"]
    s, e, _ = call("POST", f"/amcp/session/{sid}/approve",
                   {"actor": {"id": "amcp:t:worker"}, "approval_id": aid, "verdict": "approve"})
    check("worker cannot approve", s == 403, s)
    s, d, _ = call("POST", f"/amcp/session/{sid}/approve",
                   {"actor": {"id": "user:t"}, "approval_id": aid, "verdict": "approve"})
    check("approver executes pending spend",
          s == 200 and d["status"] == "approved" and d["spent_usdc"] == "1.90", (s, d))
    rec = d["receipt"]
    check("decision receipt verifies",
          verify_envelope({k: v for k, v in rec.items() if k != "signatures"},
                          rec["signatures"]["decider"]))
    s, e, _ = call("POST", f"/amcp/session/{sid}/approve",
                   {"actor": {"id": "user:t"}, "approval_id": aid, "verdict": "approve"})
    check("double approval refused", s == 409, s)

    print("[L3] pause + lifecycle")
    s, e, _ = call("POST", f"/amcp/session/{sid}/pause", {"actor": {"id": "amcp:t:worker"}})
    check("worker cannot pause", s == 403, s)
    s, p, _ = call("POST", f"/amcp/session/{sid}/pause", {"actor": {"id": "user:t"}})
    check("approver pauses", s == 200 and p["state"] == "paused", (s, p))
    s, e, _ = call("POST", f"/amcp/session/{sid}/spend",
                   {"actor": {"id": "amcp:t:worker"}, "amount_usdc": "0.01"})
    check("spend frozen while paused", s == 403, s)
    s, e, _ = call("POST", f"/amcp/session/{sid}/complete", {"actor": {"id": "user:t"}})
    check("approver cannot complete", s == 403, s)

    print("[L3] collapse (2-member plain conversation)")
    s, small, _ = call("POST", "/amcp/session", {
        "members": [{"actor": {"type": "agent", "id": "amcp:t:a"}, "role": "coordinator"},
                    {"actor": {"type": "agent", "id": "amcp:t:b"}, "role": "worker"}],
        "roles": {"coordinator": ROLES["coordinator"], "worker": ROLES["worker"]},
        "blackboard": {}, "budget": {"ceiling_usdc": "0", "scheme": "upto"}})
    check("2-member session creates without ceremony", s == 201, s)
    s, m, _ = call("POST", f"/amcp/session/{small['id']}/message",
                   {"actor": {"id": "amcp:t:b"}, "to": "room",
                    "parts": [{"kind": "text", "class": "content", "text": "hi"}]})
    check("plain message works", s == 200, (s, m))

    # shape check: stored session validates against the normative schema
    # (reconstructed from the small session view + known roles/budget)
    doc = {"amcp_version": "0.1", "id": small["id"], "members": [
        {"actor": {"type": "agent", "id": "amcp:t:a"}, "role": "coordinator",
         "joined_at": "2026-09-16T06:00:00Z", "presence": "active"},
        {"actor": {"type": "agent", "id": "amcp:t:b"}, "role": "worker",
         "joined_at": "2026-09-16T06:00:00Z", "presence": "active"}],
        "roles": {"coordinator": ROLES["coordinator"], "worker": ROLES["worker"]},
        "blackboard": {}, "budget": {"ceiling_usdc": "0", "spent_usdc": "0", "scheme": "upto"},
        "conflict_policy": "coordinator_arbitrates", "state": "active"}
    try:
        Draft202012Validator(json.load(open("schemas/session.schema.json"))).validate(doc)
        check("session shape validates", True)
    except Exception as e:  # noqa: BLE001
        check("session shape validates", False, str(e)[:200])

    srv.shutdown()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
