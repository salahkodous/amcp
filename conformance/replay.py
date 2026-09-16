"""Portable conformance replayer: boots the Python reference in-process
and replays conformance/fixtures/*.json. Ports MUST reimplement this
(~80 lines) against the same fixture files.

Run:  python conformance/replay.py [fixture-file ...]  (default: all)
"""

import json
import sys
import threading
import urllib.request
import urllib.error

sys.path.insert(0, ".")
from reference.agent import ThreadingHTTPServer, Handler  # noqa: E402

PORT = 8487
BASE = f"http://127.0.0.1:{PORT}"


def get_path(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return (False, None)
        cur = cur[part]
    return (True, cur)


def sub(obj, variables):
    if isinstance(obj, str):
        for k, v in variables.items():
            obj = obj.replace("{" + k + "}", str(v))
        return obj
    if isinstance(obj, dict):
        return {k: sub(v, variables) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sub(v, variables) for v in obj]
    return obj


def run_fixture(fx, variables, saved):
    req = fx["request"]
    data = json.dumps(sub(req.get("body"), variables)).encode() if "body" in req else None
    r = urllib.request.Request(
        BASE + sub(req["path"], variables), data=data,
        headers={"Content-Type": "application/json",
                 **sub(req.get("headers", {}), variables)},
        method=req["method"])
    try:
        with urllib.request.urlopen(r) as resp:
            status, body, headers = resp.status, json.loads(resp.read() or b"{}"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        status, body, headers = e.code, json.loads(e.read() or b"{}"), dict(e.headers)
    exp = fx.get("expect", {})
    fails = []
    if "status" in exp and status != exp["status"]:
        fails.append(f"status {status} != {exp['status']} (body={str(body)[:200]})")
    for key in exp.get("has", []):
        if key not in body:
            fails.append(f"missing key {key!r}")
    for path, want in exp.get("where", {}).items():
        want = sub(want, variables)
        ok, got = get_path(body, path)
        if not ok:
            fails.append(f"missing path {path!r}")
        elif got != want:
            fails.append(f"{path}: {got!r} != {want!r}")
    for hk, hv in exp.get("headers", {}).items():
        if headers.get(hk) != hv:
            fails.append(f"header {hk}: {headers.get(hk)!r} != {hv!r}")
    if "identical_to" in exp and body != saved.get(exp["identical_to"]):
        fails.append(f"body differs from saved {exp['identical_to']!r}")
    for var, path in fx.get("capture", {}).items():
        ok, got = get_path(body, path)
        if ok:
            variables[var] = got
        else:
            fails.append(f"capture failed: {path!r}")
    if "save_as" in fx:
        saved[fx["save_as"]] = body
    return fails


def main():
    import glob
    files = sys.argv[1:] or sorted(glob.glob("conformance/fixtures/*.json"))
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    total_pass, total_fail = 0, 0
    for path in files:
        spec = json.load(open(path))
        assert spec.get("version") == "0.1", f"{path}: unsupported fixture version"
        variables, saved = {}, {}
        print(f"[{path}]")
        for fx in spec["fixtures"]:
            fails = run_fixture(fx, variables, saved)
            if fails:
                total_fail += 1
                print(f"  FAIL {fx['name']}: {'; '.join(fails)}")
            else:
                total_pass += 1
                print(f"  PASS {fx['name']}")
    srv.shutdown()
    print(f"\n{total_pass} passed, {total_fail} failed")
    sys.exit(1 if total_fail else 0)


if __name__ == "__main__":
    main()
