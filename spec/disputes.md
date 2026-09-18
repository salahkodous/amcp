# Disputes + transaction anchor: design (frontier piece)

Status: **design**. No code lands until the fixtures in §9 exist. This is the
piece that turns AMCP from a recorder of successful activity into the venue
where strangers resolve failure — the missing half of any economic standard.

## 1. Why disputes define the standard

Payments prove money moved. Receipts prove work was claimed. Neither answers:

```text
paid → failed · paid → partial · paid → wrong output · paid → late
unauthorized delegation · double-commit · evidence forged
```

A protocol without a failure vocabulary outsources every conflict to private
support tickets and platform courts. A world standard defines the vocabulary,
the process, and the enforcement hooks — portably, so a claim filed against
an agent on one implementation is adjudicable on another.

Design rule carried over from reputation: **no private justice**. Every step
is evidenced, every decision receipted, every outcome replayable from public
inputs. Adjudicators compete; the process doesn't belong to anyone.

## 2. Non-goals

- Not a court system. No legal standing, no identity-of-last-resort, no asset
  seizure beyond what escrow already holds.
- Not arbitration-as-a-service. AMCP defines the claim/adjudication/
  enforcement *shapes*; who adjudicates is a market (counterparty, mutual,
  third-party arbiter, human principal — §4).
- Not chargebacks. Payment rails keep their own reversal semantics; AMCP
  records the dispute outcome and triggers only the hooks both parties
  pre-committed to (escrow terms, reputation inputs).

## 3. Primitives (three, reusing five)

New:

- **DisputeClaim** — a signed statement: which transaction, which obligation
  failed, what remedy is sought, what evidence supports it, by when the
  respondent must answer.
- **Adjudication** — a signed decision by an authorized adjudicator:
  findings (per-leaf: which claims hold), remedy, rationale hash, appeal
  window. *This is a decision receipt* — the same object as consent
  decisions, not a parallel invention.
- **Enforcement** — the execution of the remedy through pre-committed hooks
  (escrow release/refund/split, reputation `disputed_*` outcomes, delist
  referral for fraud). Enforcement never invents new powers; it runs what the
  commitment already allowed.

Reused: identity (claimant/respondent/arbiter keys), evidence (source-keyed,
by hash — a dispute references evidence, never re-uploads it), receipts (the
disputed artifact), reputation inputs (`disputes_lost` already exists).

## 4. Adjudication tiers (escalating, never skipping entry)

```text
T0  respondent answers (auto-resolve: refund, redo, concede)
T1  mutual agreement (both parties sign the outcome)
T2  designated arbiter (named in the commitment; e.g. platform, insurer)
T3  human principal (final authority where policy requires it)
```

Entry is always T0 with a bounded clock. Silence escalates, never stalls:
respondent silence past the deadline counts as concession on unanswered
leaves (bounded — see §6). Each tier's output is a signed adjudication the
next tier can consume or overturn within its appeal window. Finality is
explicit: after the window, the outcome is `resolved` and evidence-grade.

## 5. State machine (the testable core)

```text
filed → evidenced → adjudicating → decided → enforcing → resolved
  │          │             │            │           │           │
  │          │             │            │           │           └─ terminal: feeds reputation, closes
  │          │             │            │           └─ escrow/reputation hooks run (idempotent by source key)
  │          │             │            └─ appeal window opens (bounded, one level up, never down)
  │          │             └─ arbiter assigned/answer deadline passes
  │          └─ evidence bound by hash (claimant's packet + respondent's answer)
  └─ claim validated (shape, signatures, transaction exists, remedy in scope)

  withdrawn (claimant, before decided) · rejected malformed (never a state)
```

Invariants: one open dispute per (transaction, obligation-leaf); every
transition appends a signed record; enforcement is idempotent (same source
keys as evidence); a decided outcome is itself evidence for future trust.

## 6. Kinds (closed set, versioned)

`non_delivery · partial_delivery · wrong_output · late_delivery ·
unauthorized_delegation · evidence_forged · double_commit`. Unknown kinds are
rejected at file time — the set grows by spec version, not by free text.
Each kind declares its remedy space: `refund_full · refund_partial · redo ·
split · concede · escalate`. Remedies outside the commitment's pre-agreed
space are unenforceable (recorded as opinion, not outcome).

## 7. The transaction anchor

`amcp-transaction.schema.json` binds the eight primitives into one
interoperable object — the checkable form of the lifecycle:

```json
{
  "id": "...",
  "identity": {}, "capability": {}, "intent": {},
  "authorization_chain": [], "consent": {}, "commitment": {},
  "payment": {}, "execution": {}, "receipt": {},
  "evidence": [], "verification": {}, "settlement": {},
  "reputation": {}, "dispute": {}
}
```

Rules: every section is optional except `id`; sections reference each other
by id/hash, never by embedding (a receipt is not pasted into a dispute — it
is pointed at); the object is append-only in time (later sections never edit
earlier ones — disputes annotate, appeals supersede by reference). The
fixture suite proves the happy path
(request→authorize→consent→commit→pay→execute→receipt→evidence→settle→repute)
and then the failure paths (→dispute→adjudicate→enforce).

## 8. API surface (shape, not final)

```text
POST /amcp/disputes                 file claim -> 201 {dispute_id, state: filed, answer_by}
POST /amcp/disputes/:id/evidence    bind evidence hashes (either party, pre-decided)
POST /amcp/disputes/:id/respond     respondent answer (concede / counter / escalate)
POST /amcp/disputes/:id/adjudicate  arbiter decision -> 202 {state: decided, appeal_until}
POST /amcp/disputes/:id/appeal      one level up, within window
POST /amcp/disputes/:id/withdraw    claimant, pre-decided
GET  /amcp/disputes/:id             full record: states + signatures + evidence refs
```

Auth: claimant/respondent prove by key; arbiter must match the commitment's
designated arbiter (or principal policy); all bodies signature-enveloped.
Rate limits match other write endpoints; delist-grade admin auth is NOT
required (disputes are bilateral, moderation is platform).

## 9. Fixture-first build order

1. `conformance/fixtures/dispute.json` — file→respond→concede (T0 happy path), malformed claims rejected, double-file refused.
2. `conformance/fixtures/dispute-adjudication.json` — silence→escalation, arbiter decision, appeal window, finality, enforcement idempotency (same source keys twice).
3. `conformance/vectors/dispute.json` (if numeric edge cases emerge: remedy math, deadline arithmetic).
4. `schemas/amcp-transaction.schema.json` + `schemas/dispute.schema.json` (+ adjudication/enforcement shapes), examples validated in CI.
5. Reference → SDK → adapter, in that order, each replay-green before the next.

## 10. What "world standard" demands of this piece

- **Portable**: a claim filed on implementation A is readable, answerable,
  and adjudicable on implementation B. Evidence by hash/URI; no local ids.
- **Time-bounded**: every state has a clock; silence has a defined meaning.
  A dispute that can stall forever is a denial-of-service primitive.
- **Final**: appeal windows close. Terminal states feed reputation and close.
- **Enforceable-without-trust**: remedies execute through pre-committed
  hooks only. No hook, no enforcement — recorded as opinion.
- **Minimal**: three new shapes, one state machine, one closed kind-set.
  Anything else is composition.

## 11. Open questions (for fixtures to settle, not meetings)

- Exact default clocks (answer window, appeal window) — propose 72h/168h in
  fixtures, tune with operator data.
- Arbiter compensation: who pays the adjudicator, and is the fee itself
  escrowed? (Candidate: loser-pays capped, pre-committed in `commitment`.)
- Cross-implementation evidence fetch: content-addressed minimum (hash +
  fetchable URI) vs. hash-only with out-of-band delivery?
- Fraud referral threshold: when does an outcome auto-refer to delist flows?
