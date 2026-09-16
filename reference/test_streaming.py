"""Streaming conformance subset: SSE replay, live tail, resume cursors,
monotonic seq, member-only access, bounded hold.

Run:  python reference/test_streaming.py  (spawns server in-process)
"""

import http.client
import json
import sys
import threading
import urllib.request
import urllib.error

sys.path.insert(0, ".")
from reference.agent import ThreadingHTTPServer, Handler  # noqa: E402

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


def read_events(path, want_kinds, timeout=12):
    """Open the SSE stream, collect events until all want_kinds seen."""
    conn = http.client.HTTPConnection("127.0.0.1", 8486, timeout=timeout)
    conn.request("GET", path)
    resp = conn.getresponse()
    if resp.status != 200:
        return resp.status, []
    got, buf = [], b""
    try:
        while not all(k in [e.get("kind") for e in got] for k in want_kinds):
            chunk = resp.read(1)
            if not chunk:
                break
            buf += chunk
            while b"\n\n" in buf:
                frame, buf = buf.split(b"\n\n", 1)
                data = [l[5:].strip() for l in frame.decode().split("\n")
                        if l.startswith("data:")]
                if data:
                    got.append(json.loads(data[0]))
    finally:
        conn.close()
    return 200, got


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 8486), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    ROLES = {
        "coordinator": {"read": ["*"], "write": ["plan"], "message": ["*"], "delegate": True, "approve": False},
        "worker": {"read": ["brief"], "write": ["findings"], "message": ["room"], "delegate": False, "approve": False},
    }
    s, sess, _ = call("POST", "/amcp/session", {
        "members": [{"actor": {"type": "agent", "id": "amcp:t:a"}, "role": "coordinator"},
                    {"actor": {"type": "agent", "id": "amcp:t:b"}, "role": "worker"}],
        "roles": ROLES, "blackboard": {"brief": "x"}})
    assert s == 201, sess
    sid = sess["id"]

    print("[SSE] replay + live tail")
    out = {}
    t = threading.Thread(
        target=lambda: out.update(
            {"r": read_events(f"/amcp/session/{sid}/events?actor=amcp:t:b&wait=10",
                              ["session_created", "message"])}),
        daemon=True)
    t.start()
    __import__("time").sleep(0.5)  # let the tail attach
    call("POST", f"/amcp/session/{sid}/message",
         {"actor": {"id": "amcp:t:a"}, "to": "room",
          "parts": [{"kind": "text", "class": "content", "text": "hello stream"}]})
    t.join(timeout=15)
    status, events = out.get("r", (None, []))
    check("replay delivers history + live message",
          status == 200 and "session_created" in [e["kind"] for e in events]
          and "message" in [e["kind"] for e in events], (status, [e["kind"] for e in events]))
    seqs = [e["seq"] for e in events]
    check("seq monotonic increasing", seqs == sorted(seqs) and len(set(seqs)) == len(seqs), seqs)

    print("[SSE] resume cursor")
    last = max(seqs)
    status, events2 = read_events(
        f"/amcp/session/{sid}/events?actor=amcp:t:b&cursor={last}&wait=2", [])
    check("cursor past tip returns nothing new", status == 200 and events2 == [], (status, events2))
    status, events3 = read_events(
        f"/amcp/session/{sid}/events?actor=amcp:t:b&cursor=0&wait=2", ["session_created"])
    check("cursor=0 replays from start",
          status == 200 and events3 and events3[0]["kind"] == "session_created", status)

    print("[SSE] guards")
    conn = http.client.HTTPConnection("127.0.0.1", 8486, timeout=5)
    conn.request("GET", f"/amcp/session/{sid}/events?actor=amcp:t:ghost&wait=1")
    check("non-member stream denied", conn.getresponse().status == 403)
    conn.close()
    conn = http.client.HTTPConnection("127.0.0.1", 8486, timeout=5)
    conn.request("GET", f"/amcp/session/{sid}/events?actor=amcp:t:b&cursor=bogus&wait=1")
    check("bad cursor rejected", conn.getresponse().status == 422)
    conn.close()

    srv.shutdown()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
