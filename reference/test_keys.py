"""Keys conformance subset: fixed Ed25519 vector, roundtrip, tamper,
fail-closed verify, advertised keys, receipt signatures verify offline.

Run:  python reference/test_keys.py  (spawns server in-process; needs pynacl
for the live-key checks — vector + fail-closed checks always run)
"""

import json
import sys
import threading
import urllib.request
import urllib.error

sys.path.insert(0, ".")
from reference.agent import ThreadingHTTPServer, Handler  # noqa: E402
from reference.signer import TEST_VECTOR, verify_ed25519, DevSigner  # noqa: E402

try:
    from reference.signer import Ed25519Signer
    from reference.agent import init_signer
    import nacl  # noqa: F401
    HAVE_NACL = True
except ImportError:
    HAVE_NACL = False

BASE = "http://127.0.0.1:8484"
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


def main():
    if HAVE_NACL:
        init_signer(b"test-secret-keys")
    srv = ThreadingHTTPServer(("127.0.0.1", 8484), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    print("[KEYS] fixed vector (pins canonicalization + sig bytes)")
    v = TEST_VECTOR
    if HAVE_NACL:
        k = Ed25519Signer(bytes.fromhex(v["seed_hex"]))
        check("vector pubkey", k.pub_hex == v["pub_hex"])
        check("vector signature", k.sign(v["message"])["sig"] == v["sig"])
    check("vector verifies via module fn",
          verify_ed25519(v["pub_hex"], v["message"], v["sig"]))

    print("[KEYS] fail-closed verification")
    check("tampered message fails",
          not verify_ed25519(v["pub_hex"], {"test": "tampered"}, v["sig"]))
    check("wrong key fails",
          not verify_ed25519("00" * 32, v["message"], v["sig"]))
    check("truncated sig fails",
          not verify_ed25519(v["pub_hex"], v["message"], v["sig"][:-4]))
    check("unknown alg prefix fails",
          not verify_ed25519(v["pub_hex"], v["message"], v["sig"].replace("ed25519:", "rsa:")))
    check("garbage never raises",
          verify_ed25519("xyz", {"a": 1}, "nope") is False)

    print("[KEYS] advertised + live receipts")
    s, keys, _ = call("GET", "/amcp/keys")
    check("keys endpoint", s == 200 and keys["active"] in [k["id"] for k in keys["keys"]], s)
    s, desc, _ = call("GET", "/amcp")
    check("descriptor advertises same active key",
          s == 200 and any(k["id"] == keys["active"] for k in desc.get("keys", [])), s)
    s, r, _ = call("POST", "/amcp/task", {"capability": "echo", "inputs": {"text": "sig"}})
    rec = r["receipt"]
    env = rec["signatures"]["platform"]
    body = {k: v for k, v in rec.items() if k != "signatures"}
    try:
        from jsonschema import Draft202012Validator  # noqa: E402
        Draft202012Validator(json.load(open("schemas/receipt.schema.json"))).validate(rec)
        check("live receipt validates against receipt schema", True)
    except Exception as e:  # noqa: BLE001
        check("live receipt validates against receipt schema", False, str(e)[:200])
    if HAVE_NACL:
        check("live receipt is ed25519", env.get("alg") == "ed25519", env)
        pub = next(k["pub"] for k in keys["keys"] if k["id"] == env["key_id"])
        check("live receipt verifies via advertised key",
              verify_ed25519(pub, body, env["sig"]))
        check("server-side keychain verifies",
              __import__("reference.agent", fromlist=["verify_envelope"]).verify_envelope(body, env))
    else:
        check("dev receipt verifies (dev secret)",
              DevSigner(b"dev-secret-change-me").verify(body, env))

    srv.shutdown()
    print(f"\n{PASS} passed, {FAIL} failed (pynacl: {'yes' if HAVE_NACL else 'no'})")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
