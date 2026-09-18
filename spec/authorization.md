# Authorization chains: delegatable, bounded authority (authz-v1)

Consent scales through bounded authority, not repeated approval (VISION.md
§8). This doc is the checkable form: link shapes, the monotone rule,
evaluation algorithm, revocation semantics. Single-hop grants live in
`keys.md`; this doc covers multi-hop delegation.

## 1. Authority link

```text
delegator     who grants (agent id / user id; link[0].delegator = principal)
delegate      who receives
scope         hierarchical capability prefix, e.g. procurement:research
resource      optional binding (session, budget line, subtask)
max_spend_usdc        optional ceiling this link conveys (absent = unbounded)
categories / regions  optional allowlists (absent = unconstrained)
require_approval_above_usdc   optional escalation threshold (absent = never)
issued_at / expires_at        bounds in time (expires_at optional, prefer short)
revoked         boolean, default false
signature       envelope binding the link (host-verified; evaluator assumes verified input)
```

## 2. The monotone rule (load-bearing)

Authority can only shrink down a chain. For every adjacent pair, the child
link must satisfy ALL of:

- `max_spend(child) <= max_spend(parent)` (absent = +infinity)
- `categories(child) ⊆ categories(parent)` (absent parent = universe)
- `regions(child) ⊆ regions(parent)`
- `require_approval_above(child) <= require_approval_above(parent)`

A chain violating monotonicity is **malformed authority and unusable** —
evaluation denies even requests that fit every link. Rationale: a widening
link is either a bug or an attack, and neither should execute while someone
figures out which. Fail closed, loudly (`monotone_violation`).

## 3. Evaluation algorithm (pure: chain + request + now → decision)

Request: `{actor, operation, amount_usdc?, category?, region?}`.
Steps run in fixed order; the first failure decides (deterministic):

0. **Contiguity.** `link[0].delegator` is the principal; each
   `link[i].delegate == link[i+1].delegator`; last `delegate == actor`
   (empty chain always fails here). Else deny `chain_broken`.
0b. **Link shape.** Every link's values must be well-typed: numeric fields
   parse as wire amounts, `categories`/`regions` are lists-or-absent,
   `expires_at` parses if present. Malformed authority denies with
   `malformed_link` — never silently unbounded, never silently
   unconstrained.
1. **Liveness, every link.** `revoked` → deny `link_revoked`. Past
   `expires_at` → deny `link_expired`. (Key-active checks are host-side and
   compose conjunctively; the pure evaluator assumes verified signatures.)
2. **Monotonicity.** Any widening adjacent pair → deny
   `monotone_violation`, even if the request fits every link.
3. **Scope.** The request `operation` must equal or extend some link's scope
   (`op == scope` or `op` starts with `scope + ":"`) — required at **every**
   link, since each hop re-constrains. Else deny `scope_mismatch`.
4. **Category/region.** If the request carries them, each link's allowlist
   (when present) must contain the value. Else deny `category_denied` /
   `region_denied`.
5. **Amount.** Only when the request carries `amount_usdc` (spend ops):
   invalid format → deny `invalid_amount`; amount above any link's
   `max_spend` → deny `over_limit`.
6. **Escalation.** If amount exceeds any link's `require_approval_above` →
   `escalate` with `approval_required` (maps to the 202-pend path, never a
   drop). Otherwise `allow`.

Decision shape: `{decision: allow|escalate|deny, reason: <code>,
authority: <deepest satisfied link index>, chain_valid: bool}`.
Reasons are machine-readable and stable — they are the contract, not prose.

## 4. Revocation propagation

Revocation is forward-looking and audit-preserving (same philosophy as key
revocation and reputation revocation):

- A revoked link breaks the chain for NEW evaluations immediately (no cache
  window in the auth path).
- Historical decisions made while the chain was valid stand; their receipts
  still verify.
- Downstream links are not rewritten — they dangle, and dangling denies.
- Already-executed spends are not un-happened; the dispute lifecycle
  (`spec/disputes.md`) is the remedy path, not retroactive revocation.

## 5. Escalation mapping

`escalate` feeds the existing 202-pend machinery: the pending record carries
the chain evaluation (links, matched authority, reason), the human decides,
and the decision receipt cites the chain. "Approve the pattern" writes back
as policy (wider scope, higher thresholds), never as a broader link —
links stay monotone; policy is where patterns live.

## 6. What this doc does NOT do

- No new authentication (keys.md + existing mechanisms).
- No counterparty reputation in the decision (reputation gates discovery,
  not authorization — different control planes).
- No risk dimensions beyond amount/scope/category/region/expiry/revocation.
  A policy engine nobody can audit is worse than a strict one; dimensions
  grow by spec version with vectors.
