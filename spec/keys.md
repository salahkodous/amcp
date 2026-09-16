# Key lifecycle: state machine, API contract, test matrix (Gate 4a)

Keys are deterministic engineering: no open questions, only a checklist. This doc is the contract; the adapter implements it; the matrix gates it.

## 1. Key states

```text
active ──rotate──► retired ──purge────► gone (history verifies until purge)
  │                  │         (retention policy, e.g. 2 rotations or 90d)
  └────revoke──► revoked
                     │
                     ▼
              rejected for all NEW authorization;
              historical signatures still verify
              (attribution survives revocation)
```

- Exactly one `active` key per identity. Rotation issues the replacement first, then retires the old — no signing gap.
- `retired` verifies history, never authorizes.
- `revoked` authorizes nothing; history still verifies (revocation must not rewrite the past).
- Historical verification and active authorization are different code paths with different key sets. Confusing them is the classic bug; the matrix tests it explicitly.

## 2. Grants (scoped, expiring)

```text
principal   actor the grant is for (agent id / user id)
key_id      issuing key (must be active at issue time)
scope       capability-specific: agent:read | agent:execute |
            payment:create | payment:approve | receipt:sign |
            session:spend:<session_id> | session:decide:<session_id>
resource    optional resource binding (session, budget line, subtask)
issued_at / expires_at   short-lived for sensitive scopes (minutes–hours)
status      valid | expired | revoked
```

Rules: least privilege (narrowest scope that works); sensitive scopes short-lived; every privileged step checks grant validity (scope match + unexpired + key active + principal match). Fail closed on any mismatch.

## 3. API contract (adapter)

```text
GET  /amcp/keys                 active + retired keys (pub only, never secrets)
POST /amcp/keys/rotate          { } -> { active, retired }          [admin]
POST /amcp/keys/revoke          { key_id } -> { revoked }           [admin]
POST /amcp/grants               { principal, scope, resource?, ttl_seconds } [admin]
GET  /amcp/grants?principal=    list live grants                    [admin]
POST /amcp/grants/revoke        { grant_id } -> { revoked }         [admin]
```

All mutating routes admin-gated (Clerk JWT; tests prove the 401). Revocation path:

```text
revoke member/grant/key
      ↓
grants -> revoked (immediate, same transaction as status flip)
      ↓
delist intent recorded (directory delist when directory exists)
      ↓
new authorization with revoked material rejected (max window: 0 —
no caches in the auth path; tests assert immediate)
```

## 4. Secret isolation invariant

> Private key material never appears in Durable Object storage, application logs, envelopes, error messages, or telemetry.

Enforcement: derivation + signing happen in the worker (env-only secret); the DO receives public keys and signature envelopes only. Automated tests serialize every emitted artifact (descriptors, keys responses, errors, DO-saved state) and assert no secret-shaped material.

## 5. Test matrix (gates Gate 4a)

| # | Assertion | Type |
|---|---|---|
| K1 | Rotate: new key active, old retired, no gap (sign before+after both verify) | logic |
| K2 | Pre-rotation signatures verify under retired key | logic |
| K3 | Revoked key authorizes nothing new | logic |
| K4 | Revoked key still verifies history | logic |
| K5 | Expired grant denies; valid grant allows (scope/resource/principal match) | logic |
| K6 | Wrong-scope / wrong-principal grant denies | logic |
| K7 | Rotation/revocation/grant endpoints 401 without admin | route |
| K8 | Revocation effective immediately (no cache window) | route |
| K9 | No secret material in any emitted artifact (descriptors, keys, errors, DO state) | isolation |
| K10 | Exactly one active key invariant holds across rotate/revoke sequences | logic |
