"""Intent lifecycle behavior: supersede, expiry, re-broadcast after terminal,
filter directions, guards. Wire contract proven by
conformance/fixtures/intents.json.

Run:  python reference/test_intents.py  (spawns server in-process)
"""

import json
import sys
import threading
import urllib.request
import urllib.error

sys.path.insert(0, ".")
from reference.agent import ThreadingHTTPServer, Handler  # noqa: E402
from reference.directory import Directory  # noqa: E402

BASE = "http://127.0.0.1:8490"
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


DESC = {"amcp_version": "0.1", "id": "amcp:t:q", "name": "Q", "description": "quotes things",
        "version": "1.0.0", "capabilities": []}

srv = ThreadingHTTPServer(("127.0.0.1", 8490), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
try:
    s, _, _ = call("POST", "/amcp/directory/submit", {"descriptor": DESC})
    assert s == 201, s

    # unit-level: supersede keeps history, latest wins
    d = Directory()
    d.submit(DESC)
    s, r = d.publish_intent("amcp:t:p", "dig a ditch", expires_in_seconds=3600)
    assert s == 201, r
    iid = r["intent_id"]
    d.quote_intent(iid, "amcp:t:q", "10.00", terms="v1")
    d.quote_intent(iid, "amcp:t:q", "9.00", terms="v2")
    live = [q for q in d.intents[iid]["quotes"] if not q["superseded"]]
    check("re-quote supersedes, history kept",
          len(live) == 1 and live[0]["price_usdc"] == "9.00"
          and len(d.intents[iid]["quotes"]) == 2, live)
    check("quote clamped to intent expiry",
          all(q["expires_at"] <= d.intents[iid]["expires_at"] for q in d.intents[iid]["quotes"]))

    # expired quotes can't be accepted
    s, r = d.publish_intent("amcp:t:p", "mow a lawn", expires_in_seconds=3600)
    iid2 = r["intent_id"]
    d.quote_intent(iid2, "amcp:t:q", "5.00", expires_in_seconds=0)
    s, r = d.accept_quote(iid2, "amcp:t:p", "amcp:t:q")
    check("expired quote unacceptable", s == 409, (s, r))

    # server-level: re-broadcast allowed after terminal states
    s, r, _ = call("POST", "/amcp/directory/intents",
                   {"principal": "amcp:t:p2", "action": "wash a car"})
    assert s == 201, r
    wid = r["intent_id"]
    s, _, _ = call("POST", f"/amcp/directory/intents/{wid}/withdraw", {"actor": "amcp:t:p2"})
    assert s == 200, s
    s, r, _ = call("POST", "/amcp/directory/intents",
                   {"principal": "amcp:t:p2", "action": "wash a car"})
    check("re-broadcast after withdraw", s == 201, (s, r))

    s, r, _ = call("POST", "/amcp/directory/intents/{wid}/withdraw".replace("{wid}", wid),
                   {"actor": "amcp:t:stranger"})
    check("terminal withdraw refused", s == 409, (s, r))

    # filter directions
    s, _, _ = call("POST", "/amcp/directory/intents",
                   {"principal": "amcp:t:p2", "action": "cheap gig",
                    "constraints": {"max_price_usdc": "3.00"}})
    assert s == 201, s
    s, _, _ = call("POST", "/amcp/directory/intents",
                   {"principal": "amcp:t:p2", "action": "rich gig",
                    "constraints": {"max_price_usdc": "300.00"}})
    assert s == 201, s
    s, r, _ = call("GET", "/amcp/directory/intents?max_price_usdc=10.00")
    ids = [row["intent_id"] for row in r["data"]]
    check("floor keeps high budgets, drops low ones",
          any("rich gig" in row["action"] for row in r["data"])
          and not any("cheap gig" in row["action"] for row in r["data"]), ids)

    s, r, _ = call("GET", "/amcp/directory/intents?max_price_usdc=nonsense")
    check("bad floor rejected", s == 422, (s, r))

    s, r, _ = call("POST", "/amcp/directory/intents/observe-missing/quotes",
                   {"agent_id": "amcp:t:q", "price_usdc": "1.00"})
    check("quote unknown intent 404", s == 404, (s, r))
finally:
    srv.shutdown()

print(f"{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
