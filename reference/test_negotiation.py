"""Negotiation conformance subset: offer/counter/accept/decline,
no-self-dealing, closed-negotiation guard, pause freeze.

Run:  python reference/test_negotiation.py  (spawns server in-process)
"""

import json
import sys
import threading
import urllib.request
import urllib.error

sys.path.insert(0, ".")
from reference.agent import ThreadingHTTPServer, Handler  # noqa: E402

BASE = "http://127.0.0.1:8483"
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
}
MEMBERS = [{"actor": {"type": "agent", "id": "amcp:t:buyer"}, "role": "coordinator"},
           {"actor": {"type": "agent", "id": "amcp:t:seller"}, "role": "worker"}]


def nego(sid, **kw):
    return call("POST", f"/amcp/session/{sid}/negotiate", kw)


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 8483), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    s, sess, _ = call("POST", "/amcp/session", {"members": MEMBERS, "roles": ROLES})
    assert s == 201, sess
    sid = sess["id"]
    terms = {"price_usdc": "1.50", "scheme": "escrow", "deliverable": "qualified-lead-batch"}

    print("[NEGO] happy path")
    s, n, _ = nego(sid, actor={"id": "amcp:t:buyer"}, op="offer", terms=terms)
    check("offer creates open negotiation", s == 201 and n["status"] == "open", (s, n))
    nid = n["id"]
    s, e, _ = nego(sid, actor={"id": "amcp:t:buyer"}, op="accept", negotiation_id=nid)
    check("no self-accept", s == 403, s)
    s, n, _ = nego(sid, actor={"id": "amcp:t:seller"}, op="counter",
                   negotiation_id=nid,
                   terms={"price_usdc": "2.00", "scheme": "escrow", "deliverable": "qualified-lead-batch"})
    check("counter supersedes terms", s == 200 and n["terms"]["price_usdc"] == "2.00", (s, n))
    check("history records both rounds", len(n["history"]) == 2, n)
    s, n, _ = nego(sid, actor={"id": "amcp:t:buyer"}, op="accept", negotiation_id=nid)
    check("other party accepts", s == 200 and n["status"] == "accepted", (s, n))
    s, e, _ = nego(sid, actor={"id": "amcp:t:seller"}, op="counter",
                   negotiation_id=nid, terms=terms)
    check("closed negotiation rejects counter", s == 409, s)

    print("[NEGO] guards")
    s, n, _ = nego(sid, actor={"id": "amcp:t:buyer"}, op="offer", terms=terms)
    s, d, _ = nego(sid, actor={"id": "amcp:t:seller"}, op="decline", negotiation_id=n["id"])
    check("decline closes", s == 200 and d["status"] == "declined", (s, d))
    s, e, _ = nego(sid, actor={"id": "amcp:t:buyer"}, op="offer", terms={"price_usdc": "1"})
    check("terms without deliverable rejected", s == 422, s)
    s, e, _ = nego(sid, actor={"id": "amcp:t:stranger"}, op="offer", terms=terms)
    check("non-member cannot offer", s == 403, s)
    call("POST", f"/amcp/session/{sid}/pause", {"actor": {"id": "amcp:t:buyer"}})
    s, e, _ = nego(sid, actor={"id": "amcp:t:buyer"}, op="offer", terms=terms)
    check("negotiation frozen while paused", s == 409, s)

    srv.shutdown()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
