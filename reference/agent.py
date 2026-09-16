"""AMCP reference agent (MIT). Stdlib-only: serves a signed /amcp descriptor,
executes demo capabilities (echo, score_lead incl. trial probes), mints signed
receipts, honors Idempotency-Key, speaks wire.md errors.

Run:  python -m reference.agent [--port 8471] [--secret dev-secret]
Test: python reference/test_conformance.py  (spawns this server in-process)
"""

import argparse
import hashlib
import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from .signer import DevSigner, canonical

AMCP_VERSION = "0.1"
AGENT_ID = "amcp:reference:demo_001"
MAX_INLINE = 256 * 1024

ERROR_DOCS = "https://amcp.dev/spec/wire#error-codes"


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Store:
    """In-memory state. Production hosts persist: idempotency (24h),
    receipts (permanent), tasks, rate windows."""

    def __init__(self):
        self.idempotency = {}  # (key, path) -> (status, body)
        self.receipts = []     # receipt dicts, newest last
        self.tasks = {}        # task_id -> task dict
        self.hits = {}         # window_start -> count (single global bucket, demo)


store = Store()
signer = DevSigner(b"dev-secret-change-me")


CAPABILITIES = {
    "echo": {
        "name": "echo",
        "kind": "operation",
        "description": "Returns the input text verbatim. Demo capability.",
        "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
        "output_schema": {"type": "object", "properties": {"echo": {"type": "string"}}, "required": ["echo"]},
        "authorization": "public",
        "pricing": {"model": "free"},
        "rate_limit": {"per_minute": 60},
    },
    "score_lead": {
        "name": "score_lead",
        "kind": "operation",
        "description": "Deterministic toy lead score 0-100 (demo of a priced capability).",
        "input_schema": {"type": "object", "properties": {"lead": {"type": "object"}}, "required": ["lead"]},
        "output_schema": {
            "type": "object",
            "properties": {"score": {"type": "number"}, "rationale": {"type": "string"}},
            "required": ["score", "rationale"],
        },
        "authorization": "authenticated",
        "pricing": {"model": "per_task", "amount_usdc": "0.05", "scheme": "exact"},
        "rate_limit": {"per_minute": 60},
        "sla": {"p50_seconds": 1, "timeout_seconds": 30},
        "trial": {"offered": True, "price_usdc": "0.01", "scope": "3 sample leads"},
    },
}


def descriptor(host: str) -> dict:
    doc = {
        "amcp_version": AMCP_VERSION,
        "id": AGENT_ID,
        "name": "AMCP Reference Agent",
        "description": "Minimal conformance demonstration: echo + toy lead scoring with trials and receipts.",
        "organization": "AMCP",
        "version": "0.1.0",
        "public_key": "dev-hmac-only-see-signer.py",
        "domain": ["demo"],
        "languages": ["en"],
        "capabilities": list(CAPABILITIES.values()),
        "session_roles": ["worker"],
        "settlement": {"pay_to": "0x0000000000000000000000000000000000000000",
                        "networks": ["eip155:8453"], "schemes": ["exact", "upto", "escrow"]},
        "reputation": {"receipts_uri": f"{host}/amcp/receipts", "completed_tasks": 0, "acceptance_rate": 1.0},
        "verification": "self_asserted",
    }
    doc["signature"] = signer.sign({k: v for k, v in doc.items() if k != "signature"})
    return doc


def check_required(schema: dict, inputs: dict):
    """Minimal required-field validation (hosts SHOULD use full JSON Schema)."""
    missing = [f for f in schema.get("required", []) if f not in inputs]
    if missing:
        return f"missing required fields: {', '.join(missing)}"
    return None


def execute(capability: str, inputs: dict):
    if capability == "echo":
        return {"echo": str(inputs["text"])}
    if capability == "score_lead":
        lead = inputs["lead"] if isinstance(inputs.get("lead"), dict) else {}
        blob = json.dumps(lead, sort_keys=True)
        score = int(sha256_hex(blob.encode())[:4], 16) % 101
        return {"score": score,
                "rationale": f"demo deterministic score from {len(blob)} input chars; fields seen: {sorted(lead)[:5]}"}
    raise KeyError(capability)


class Handler(BaseHTTPRequestHandler):
    server_version = "AMCP-Reference/0.1"

    def log_message(self, *a):
        pass

    # -- helpers ------------------------------------------------------
    def _send(self, status: int, body: dict, extra: dict | None = None):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-AMCP-Version", AMCP_VERSION)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _error(self, status: int, code: str, message: str, retryable=False):
        self._send(status, {"error": {"code": code, "message": message,
                                      "retryable": retryable, "doc": ERROR_DOCS}})

    def _read_json(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = 0
        if n > MAX_INLINE:
            return None, "body exceeds 256KB inline limit; use by-reference transfer"
        try:
            return (json.loads(self.rfile.read(n) or b"{}"), None) if n else ({}, None)
        except json.JSONDecodeError:
            return None, "malformed JSON"

    def _rate_ok(self) -> bool:
        window = int(time.time() // 60)
        store.hits[window] = store.hits.get(window, 0) + 1
        for w in [w for w in store.hits if w < window]:
            del store.hits[w]
        return store.hits[window] <= 600

    # -- routes -------------------------------------------------------
    def do_GET(self):
        url = urlparse(self.path)
        host = f"http://{self.headers.get('Host', 'localhost')}"
        if url.path in ("/amcp", "/.well-known/amcp.json"):
            self._send(200, descriptor(host))
        elif url.path == "/amcp/health":
            self._send(200, {"amcp_version": AMCP_VERSION, "checks": {
                "descriptor_valid": True, "a2a_card": False, "x402_live": False,
                "sessions": False, "escrow": False,
                "note": "L0+L2-task demo. See README for the road to L4."}})
        elif url.path == "/amcp/receipts":
            qs = parse_qs(url.query)
            limit = max(1, min(100, int(qs.get("limit", ["20"])[0])))
            items = store.receipts[-limit:][::-1]
            self._send(200, {"data": items,
                             "pagination": {"next_cursor": None, "has_more": False}})
        else:
            self._error(404, "unknown_method", f"no such endpoint: {url.path}")

    def do_POST(self):
        url = urlparse(self.path)
        if url.path != "/amcp/task":
            return self._error(404, "unknown_method", f"no such endpoint: {url.path}")
        if not self._rate_ok():
            self.send_header("Retry-After", "60")
            return self._error(429, "rate_limited", "demo global budget 600/min exceeded", True)
        body, err = self._read_json()
        if err:
            return self._error(400, "bad_request", err)
        capability = body.get("capability")
        inputs = body.get("inputs", {})
        idem = (self.headers.get("Idempotency-Key") or "").strip() or None
        if idem and (len(idem) < 8 or len(idem) > 128):
            return self._error(400, "bad_request", "Idempotency-Key must be 8..128 chars")
        if idem and (idem, url.path) in store.idempotency:
            status, saved, saved_hash = store.idempotency[(idem, url.path)]
            req_hash = sha256_hex(canonical({"capability": capability, "inputs": inputs}))
            if saved_hash != req_hash:
                return self._error(422, "idempotency_key_in_use",
                                   "Idempotency-Key already used with a different payload")
            return self._send(status, saved, {"X-Idempotent-Replayed": "true"})
        if capability not in CAPABILITIES:
            return self._error(404, "unknown_capability", f"unknown capability: {capability!r}")
        bad = check_required(CAPABILITIES[capability]["input_schema"], inputs if isinstance(inputs, dict) else {})
        if bad or not isinstance(inputs, dict):
            return self._error(422, "artifact_rejected", bad or "inputs must be an object")
        try:
            output = execute(capability, inputs)
        except Exception as e:  # noqa: BLE001 — demo surface, errors are enveloped
            return self._error(500, "execution_failed", str(e)[:300])

        task_id = "task_" + uuid.uuid4().hex[:16]
        artifact = {"kind": "data", "class": "content",
                    "schema": "amcp:reference:" + capability + "/v1",
                    "data": output, "mime_type": "application/json",
                    "content_hash": "sha256:" + sha256_hex(canonical(output)),
                    "provenance": {"producer": AGENT_ID, "task_ref": task_id, "derived_from": []}}
        receipt_body = {"amcp_version": AMCP_VERSION,
                        "receipt_id": "rcpt_" + uuid.uuid4().hex[:16],
                        "contract_id": body.get("contract_id") or "ct_trial_implicit",
                        "session_id": body.get("session_id"),
                        "payer": body.get("payer", "amcp:unknown:anonymous"),
                        "payee": AGENT_ID, "amount_usdc": body.get("price_usdc", "0.00"),
                        "task_ref": task_id, "artifact_hash": artifact["content_hash"],
                        "settlement_proof": "dev:unsigned-demo-proof",
                        "outcome": "accepted", "trial": bool(body.get("trial", False)),
                        "decided_at": now_iso()}
        receipt_body["signatures"] = {"payer": "dev:implicit",
                                      "platform": signer.sign({k: v for k, v in receipt_body.items() if k != "signatures"})}
        store.tasks[task_id] = {"task_id": task_id, "capability": capability, "state": "COMPLETED"}
        store.receipts.append(receipt_body)
        resp = {"task": store.tasks[task_id], "artifact": artifact, "receipt": receipt_body}
        if idem:
            req_hash = sha256_hex(canonical({"capability": capability, "inputs": inputs}))
            store.idempotency[(idem, url.path)] = (200, resp, req_hash)
        self._send(200, resp)


def serve(port: int = 8471):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"AMCP reference agent on http://127.0.0.1:{port}  (GET /amcp to start)")
    httpd.serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8471)
    ap.add_argument("--secret", default="dev-secret-change-me")
    args = ap.parse_args()
    signer = DevSigner(args.secret.encode())
    serve(args.port)
