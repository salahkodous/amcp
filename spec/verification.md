# Verification: executed acceptance, not schemad wishes (verify-v1)

Reputation weights third-party verdicts at 0.15 (`validation` input), and
contracts carry `acceptance_criteria_schema` — but until verdicts are
*executed*, both are decoration. This doc defines the checkable form:
what a verification run is, what a verdict contains, and how verdicts bind
into evidence, disputes, and reputation.

## 1. What verification is (and isn't)

Verification answers: **does this artifact satisfy the agreed criteria,
as executed?** Methods, in ascending strength:

- **schema** — artifact validates against the capability output schema.
  Catches shape drift; proves nothing about correctness.
- **criteria** — artifact validates against the commitment's acceptance
  criteria (a JSON-Schema subset both sides agreed at commit time).
- **re-run** — the verifier re-executes deterministic work from inputs and
  compares canonical hashes. Strongest portable check; only possible where
  execution is deterministic (reference capabilities are, by design).
- **third-party / human** — external verdicts (re-run services, zkML, TEE,
  human review) arrive as `validation` evidence, not through this endpoint.
  This doc standardizes what they must contain (§3), not how they run.

What verification never is: a re-litigation of price, scope, or intent
(that's negotiation and disputes), or execution itself (that's sessions).

## 2. Verdict object

```text
verdict         accepted | rejected
checks[]        {name, pass, detail} — schema, re_execution, acceptance_criteria
artifact_hash   canonical hash of the verified data (binds, not embeds)
criteria_hash   canonical hash of the criteria run (null when absent)
verifier        agent id (key-bound in production)
verified_at     timestamp
signatures      platform envelope + signature_valid self-check (reference)
```

Rules: checks run in fixed order (schema → re-run → criteria); the first
failure still runs the rest (a verdict explains fully, not just first-fault);
verdict is `accepted` iff every check passes. Verdicts are deterministic
given (capability, inputs, artifact, criteria) — same inputs, same verdict,
on every implementation. Vectors prove it.

## 3. Binding rules

- A verdict references `artifact_hash` (+ `criteria_hash`); it never embeds
  the artifact. Verification composes with evidence by reference.
- One verdict per (artifact_hash, criteria_hash, verifier): re-verification
  is idempotent, not a new opinion. (Reference is stateless here; hosts
  enforce the key.)
- A `rejected` verdict is valid dispute evidence (kind `validation`,
  outcome `rejected`) and a valid `feedback` input to reputation — the
  trust→transaction→evidence loop consumes verification output, not just
  settlement.
- Acceptance criteria SHOULD be committed (in the contract) before execution;
  post-hoc criteria are admissible but marked `criteria_committed: false` —
  moving goalposts are visible as such.

## 4. The subset schema (portable core)

Full JSON Schema is not portable across runtimes without dependencies the
SDK refuses (zero-dep) and the reference refuses (stdlib-only). verify-v1
standardizes a subset both implement identically, proven by shared vectors:

```text
type: object | array | string | number | integer | boolean | null
required, properties (recursive), items, enum,
minimum, maximum, minLength, maxLength
```

Unknown keywords are IGNORED (not errors) — forward-compatible schemas keep
verifying on old runtimes; strictness lives in `required` + `enum`, never in
keyword coverage. Anything beyond the subset (formats, refs, conditionals)
belongs in third-party verifiers, whose verdicts enter as evidence.

## 5. Endpoint shape (reference)

```text
POST /amcp/verify  {capability, inputs, artifact: {data}, criteria?}
  -> 200 {verdict, checks[], artifact_hash, criteria_hash, verifier, ...}
  -> 404 unknown_capability
  -> 422 bad_request (missing artifact.data and friends)
```

No auth in the reference (demo); production binds verifier identity to keys
and rate-limits like other write endpoints.

## 6. What this doc does NOT do

- No verdict aggregation policy (mean/median/quorum of verifiers is a
  directory/ranker concern, versioned with reputation — not here).
- No execution sandboxing (that's runtime-rs territory).
- No new money movement (verification may *trigger* escrow release via
  existing dispute/commitment hooks, never directly).
