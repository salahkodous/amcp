"""Directory conformance subset: submit, search ranking, filters,
evidence-weighted re-rank, explanations, pagination.

Run:  python reference/test_directory.py  (spawns server in-process)
"""

import json
import sys
import threading
import urllib.request
import urllib.error
import urllib.parse

sys.path.insert(0, ".")
from reference.agent import ThreadingHTTPServer, Handler  # noqa: E402

BASE = "http://127.0.0.1:8482"
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


LEAD_AGENT = {
    "amcp_version": "0.1", "id": "amcp:t:leadpro", "name": "LeadPro",
    "description": "Qualifies sales leads and scores intent for B2B pipelines.",
    "version": "1.0.0",
    "capabilities": [{
        "name": "qualify_lead", "kind": "operation",
        "description": "Score a sales lead 0-100 with rationale.",
        "input_schema": {"type": "object"}, "output_schema": {"type": "object"},
        "authorization": "authenticated",
        "pricing": {"model": "per_task", "amount_usdc": "0.05", "scheme": "exact"}}],
    "domain": ["sales"],
}
LEGAL_AGENT = {
    "amcp_version": "0.1", "id": "amcp:t:lexbot", "name": "LexBot",
    "description": "Reviews contractor agreements for enforceability issues.",
    "version": "1.0.0",
    "capabilities": [{
        "name": "review_contract", "kind": "operation",
        "description": "Review a contract and flag risky clauses.",
        "input_schema": {"type": "object"}, "output_schema": {"type": "object"},
        "authorization": "authenticated",
        "pricing": {"model": "per_task", "amount_usdc": "0.40", "scheme": "escrow"}}],
    "domain": ["legal"],
}


def search(**kw):
    return call("GET", "/amcp/directory/search?" + urllib.parse.urlencode(kw))


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 8482), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    print("[DIR] submit")
    s, r, _ = call("POST", "/amcp/directory/submit", {"descriptor": LEAD_AGENT})
    check("lead agent listed", s == 201 and r["listed"] == "amcp:t:leadpro", (s, r))
    s, r, _ = call("POST", "/amcp/directory/submit", {"descriptor": LEGAL_AGENT})
    check("legal agent listed", s == 201, (s, r))
    s, e, _ = call("POST", "/amcp/directory/submit", {"descriptor": {"id": "x"}})
    check("malformed descriptor rejected", s == 422, s)

    print("[DIR] search + ranking")
    s, r, _ = search(q="qualify sales lead score")
    check("lead query finds LeadPro first",
          s == 200 and r["data"] and r["data"][0]["descriptor"]["id"] == "amcp:t:leadpro", s)
    check("explanation present",
          "match_explanation" in r["data"][0]
          and "qualify_lead" in r["data"][0]["match_explanation"]["matched_capabilities"])
    s, r, _ = search(q="contract review enforceability")
    check("legal query finds LexBot first",
          s == 200 and r["data"][0]["descriptor"]["id"] == "amcp:t:lexbot", s)

    print("[DIR] filters")
    s, r, _ = search(q="agent", domain="legal")
    check("domain filter", s == 200 and all("legal" in d["descriptor"].get("domain", []) for d in r["data"]), s)
    s, r, _ = search(q="agent", max_price_usdc="0.10")
    check("price filter drops $0.40 agent",
          s == 200 and all(d["descriptor"]["id"] != "amcp:t:lexbot" for d in r["data"]), s)
    s, r, _ = search(q="agent", capability="review_contract")
    check("capability filter",
          s == 200 and [d["descriptor"]["id"] for d in r["data"]] == ["amcp:t:lexbot"], s)

    print("[DIR] evidence re-rank (trials beat prose)")
    # A prose-similar newcomer with no history should lose to trial-backed LeadPro.
    newcomer = dict(LEAD_AGENT, id="amcp:t:leadcopy", name="LeadCopy")
    call("POST", "/amcp/directory/submit", {"descriptor": newcomer})
    for i in range(4):
        call("POST", "/amcp/directory/evidence",
             {"agent_id": "amcp:t:leadpro", "kind": "trial",
              "ref": f"trial-{i}", "outcome": "accepted"})
    s, r, _ = search(q="qualify sales lead score")
    ids = [d["descriptor"]["id"] for d in r["data"]]
    check("trial-backed agent outranks copy",
          s == 200 and ids.index("amcp:t:leadpro") < ids.index("amcp:t:leadcopy"), ids)
    s, r, _ = search(q="agent", min_acceptance="0.9")
    check("min_acceptance filters agents without receipts", s == 200 and r["data"] == [], s)

    print("[DIR] reputation v1 + experimental signals")
    for i in range(3):
        call("POST", "/amcp/directory/evidence",
             {"agent_id": "amcp:t:leadpro", "kind": "receipt", "ref": f"rcpt-{i}",
              "outcome": "accepted", "reviewer": f"0xbuyer{i}"})
    call("POST", "/amcp/directory/evidence",
         {"agent_id": "amcp:t:leadpro", "kind": "feedback", "ref": "fb-1",
          "outcome": "accepted", "reviewer": "0xbuyer0"})
    s, sc, _ = call("GET", "/amcp/directory/score?agent_id=amcp:t:leadpro")
    check("score version pinned", s == 200 and sc["version"] == "reputation-v1", s)
    check("settlement sub-score perfect",
          sc["scores"]["settlement"] == 1.0, sc["scores"])
    check("composite blends present inputs only",
          sc["composite"] is not None and 0.0 <= sc["composite"] <= 1.0, sc["composite"])
    check("experimental weight zero (not load-bearing)",
          sc["experimental"]["weight"] == 0, sc["experimental"])
    check("reviewer graph logged",
          sc["experimental"]["unique_reviewers"] == 3, sc["experimental"])
    # Sybil ring: 10 fake feedbacks from one reviewer on the copy.
    for i in range(10):
        call("POST", "/amcp/directory/evidence",
             {"agent_id": "amcp:t:leadcopy", "kind": "feedback", "ref": f"fake-{i}",
              "outcome": "accepted", "reviewer": "0xsybil"})
    s, sc2, _ = call("GET", "/amcp/directory/score?agent_id=amcp:t:leadcopy")
    check("ring shows burst + single reviewer",
          sc2["experimental"]["unique_reviewers"] == 1
          and sc2["experimental"]["burst_windows"] >= 1, sc2["experimental"])
    s, r, _ = search(q="qualify sales lead score")
    ids = [d["descriptor"]["id"] for d in r["data"]]
    check("ring does not outrank settlement-backed agent",
          ids.index("amcp:t:leadpro") < ids.index("amcp:t:leadcopy"), ids)
    # Revocation churn penalizes reliability, never silently drops.
    call("POST", "/amcp/directory/evidence",
         {"agent_id": "amcp:t:leadpro", "kind": "revocation", "ref": "fb-1",
          "outcome": "revoked", "reviewer": "0xbuyer0"})
    s, sc3, _ = call("GET", "/amcp/directory/score?agent_id=amcp:t:leadpro")
    check("revocation lowers reliability",
          sc3["scores"]["reliability"] < (sc["scores"]["reliability"] or 1.0),
          (sc["scores"]["reliability"], sc3["scores"]["reliability"]))
    s, e, _ = call("GET", "/amcp/directory/score?agent_id=amcp:t:ghost")
    check("unknown agent scores 404", s == 404, s)

    print("[DIR] pagination")
    s, r, _ = search(q="agent", limit=1)
    check("limit + has_more",
          s == 200 and len(r["data"]) == 1 and r["pagination"]["has_more"] is True, s)
    s, r2, _ = search(q="agent", limit=1, cursor=r["pagination"]["next_cursor"])
    check("cursor advances",
          s == 200 and r2["data"] and r2["data"][0] != r["data"][0], s)

    srv.shutdown()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
