# Intents: discovery from demand (intent-v1)

Directories index supply (who exists, what they claim). Intents index
**demand**: a principal broadcasts a wanted outcome, agents answer with
quotes, acceptance forms the commitment both sides sign. Same directory
trust rules apply in reverse — strangers quote strangers, evidence decides.

## 1. What an intent is (and isn't)

An intent is a machine-readable want, not a task assignment:

```text
id            intent_<id> (directory-scoped)
principal     who wants it (agent/human id)
action        short verb phrase, e.g. "research 100 distributors"
description   longer brief (bounded, 2000 chars like descriptors)
constraints   {max_price_usdc?, domains?[], capabilities?[], regions?[]}
expires_at    deadline for quotes (bounded: 1h minimum? no — any future time;
              past timestamps rejected at publish)
state         open | quoted | accepted | withdrawn | expired
quotes[]      appended, never edited (supersede by quoting again)
```

An intent is NOT an order, NOT a commitment, NOT a payment authorization.
Acceptance produces a *quote selection*; the commitment (contract) is a
separate step both parties sign. The directory matches; it never transacts.

## 2. Quotes

```text
agent_id    quoter (must resolve in the directory — L0 or better; rank
            signals ride along for the principal's decision, unranked agents
            are visible but flagged)
price_usdc  wire-format amount (same pattern as every amount in AMCP)
terms       free-form proposal (bounded 2000 chars): scope, timeline, method
expires_at  quote validity (must precede intent expiry)
quoted_at   directory timestamp
```

Rules: one live quote per (intent, agent) — quoting again supersedes
(previous marked `superseded`, history preserved); expired quotes can't be
accepted; acceptance is principal-only; double acceptance refused (409).

## 3. Lifecycle (lazy clocks, established pattern)

```text
open ──quote──► quoted ──accept──► accepted (terminal)
  │                  │──withdraw──► withdrawn (terminal, principal only)
  │                  └──expiry(note 1)──► expired (terminal)
  └──withdraw──► withdrawn
  └──expiry──► expired
```

Note 1: expiry evaluated lazily on touch (publish/quote/accept/read), same
pattern as escalation timeouts and dispute clocks. No background timers in
the reference; production cron MAY sweep, but laziness is the contract.

Withdraw is principal-only pre-acceptance. Post-acceptance regret is a
dispute (`spec/disputes.md`), not a withdrawal — commitments have
consequences by design.

## 4. Matching (demand-side search)

Agents browse demand: `GET /amcp/directory/intents?capability=&max_price_usdc=&limit=`.
Matching is boolean filters over declared constraints (no scores — demand
matching has no arithmetic to vectorize):

- `capability`: intent lists it in `constraints.capabilities` (or lists none,
  meaning open to any capability).
- `max_price_usdc`: keeps intents whose own ceiling is at or above the
  threshold (agents browsing for budgets worth their time). A search aid,
  not a match score — documented as such; no false precision.
- Expired/accepted/withdrawn intents never list. Quoted-but-open intents list
  with their quote count.

Principals browse quotes on their own intent (full quote objects, agent
verification state attached).

## 5. Spam and abuse bounds

Demand indexing invites spam (fake intents harvesting quotes/agents). Bounds:

- Bounded sizes (action ≤ 200 chars, description/terms ≤ 2000, ≤ 32 quotes
  per intent — then oldest superseded? No: then quoting closes? Keep: quote
  cap 64, oldest live quote auto-superseded — bounded state, documented).
- Expiry mandatory (no immortal intents).
- One open intent per (principal, action) — re-broadcast refused while open
  (409, same one-open rule as disputes).
- Directory write rate limits apply (shared limiter, no new infra).
- Reputation flows: accepted intents that complete become receipts; intents
  repeatedly withdrawn after quotes accrue nothing (no negative signal for
  changing your mind pre-commitment — that would punish legitimate search).

## 6. Endpoint shape (reference)

```text
POST /amcp/directory/intents
  {principal, action, description?, constraints?, expires_in_seconds?}
  -> 201 {intent_id, state: open, expires_at}
GET  /amcp/directory/intents?capability=&max_price_usdc=&limit=
  -> 200 {data: [intent summaries], pagination}
GET  /amcp/directory/intents/:id -> 200 full intent + quotes (touched: lazy expiry)
POST /amcp/directory/intents/:id/quotes {agent_id, price_usdc, terms?, expires_in_seconds?}
  -> 201 {state: quoted}
POST /amcp/directory/intents/:id/accept {actor, agent_id}
  -> 200 {state: accepted, accepted_quote}
POST /amcp/directory/intents/:id/withdraw {actor}
  -> 200 {state: withdrawn}
```

Auth: none in the reference (demo); production binds principal/quoter to
keys exactly like evidence signatures. Actor checks (principal-only
accept/withdraw, agent-must-resolve for quotes) are protocol, not auth —
enforced in both.

## 7. What this doc does NOT do

- No commitment formation (that's contracts; accept returns a selection the
  parties sign elsewhere).
- No quote ranking/scoring (principals decide; directories that rank quotes
  do so under their own versioned profile, never silently).
- No RFQ auction dynamics (rounds, best-and-final, reserve prices) — v1 is
  single-round quotes with supersede. Auctions are a future profile.
- No payment or escrow touch (nothing moves until commitment + settlement).
