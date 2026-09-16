# AMCP reference agent (MIT)

Minimal, stdlib-only implementation of the AMCP serving side (L0 + task subset of L2).
Its job is to prove the spec is implementable — not to be production software.

## Run

```bash
python -m reference.agent [--port 8471] [--secret YOUR_DEV_SECRET]
curl localhost:8471/amcp | python -m json.tool
```

## Try it

```bash
# trial probe (score_lead, $0.01 demo)
curl -X POST localhost:8471/amcp/task -H 'Content-Type: application/json' -d '{
  "capability": "score_lead",
  "inputs": {"lead": {"budget": 500000, "city": "Dubai"}},
  "trial": true, "price_usdc": "0.01",
  "Idempotency-Key": "demo-1"
}' | python -m json.tool

# receipts (the portable trust atoms)
curl 'localhost:8471/amcp/receipts?limit=5' | python -m json.tool
```

## Test

```bash
python reference/test_conformance.py   # L0–L2 subset: 11 checks
python reference/test_sessions.py      # L3 subset: 19 checks (roles, canaries, claims, budgets, lifecycle)
```

## What's real vs stubbed

| Real | Stubbed (documented in code) |
|---|---|
| Descriptor serving + well-known mirror | A2A card link (serves without one) |
| Required-field input validation | Full JSON Schema validation (hosts SHOULD) |
| Idempotency with key-reuse guard | 24h persistent store (in-memory, process life) |
| Sessions: roles, scoped snapshots, canary-tested redaction, atomic claims, budgets with floor, pause/complete/cancel, instruction-class guard | Negotiation envelope, escalation evaluator, SSE fan-out, persistent session store (single-writer in-memory) |
| Signed receipts (dev HMAC) | Ed25519 (`signer.Ed25519Signer`, needs `pynacl`); x402 settlement proofs (`dev:unsigned-demo-proof`) |
| Global demo rate bucket | Per-capability windows, persistent |

## Signing

`signer.DevSigner` is HMAC-SHA256 so the reference runs dependency-free. It is
**explicitly dev-only**: receipts it mints verify only with the shared secret and
MUST be rejected by L4 conformance against real agents. Production: `Ed25519Signer`.
