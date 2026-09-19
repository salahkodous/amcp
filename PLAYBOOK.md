# AMCP Playbook — the any-agent-to-any-agent economy in practice

> **Status:** `amcp/0.1` public draft. This playbook teaches the protocol as it
> runs today: every flow below replays green against the reference
> implementation. Versioned experiments are marked as such.
>
> **One line:** MCP gives agents tools. A2A gives agents communication. AMCP
> gives agentic work a shared context of authority, commitment,
> accountability, and economic settlement.

## Who this is for

- **Agent developers** wiring paid collaboration between agents (and humans).
- **Platform teams** adding settlement, reputation, or dispute handling.
- **Evaluators** deciding whether AMCP fits: start at §2, then §15.

## 1. The economic loop

Every AMCP transaction moves through the same lifecycle. Not every
transaction needs every stage — but all parties name the same stages:

```text
               ┌──────────────────────────────────────────────┐
               │                 DISCOVER                     │
               │  directory search · intents (demand) · cards │
               └──────────────────────┬───────────────────────┘
                                      ▼
               ┌──────────────────────────────────────────────┐
               │         IDENTIFY · UNDERSTAND · TRUST        │
               │  keys · capabilities+pricing · reputation    │
               │  receipts · evidence (never self-scores)     │
               └──────────────────────┬───────────────────────┘
                                      ▼
               ┌──────────────────────────────────────────────┐
               │        NEGOTIATE · AUTHORIZE · COMMIT        │
               │  quotes · delegation chains · consent policy │
               │  202-pend approvals · bilateral contracts    │
               └──────────────────────┬───────────────────────┘
                                      ▼
               ┌──────────────────────────────────────────────┐
               │         PAY · EXECUTE · VERIFY · PROVE       │
               │  x402 movement · sessions · re-run verdicts  │
               │  settlement-bound receipts                   │
               └──────────────────────┬───────────────────────┘
                                      ▼
               ┌──────────────────────────────────────────────┐
               │      SETTLE · REPUTATION · (DISPUTE)         │
               │  escrow ledger · evidence projection · v1    │
               │  scores · claim/adjudicate/enforce on failure│
               └──────────────────────────────────────────────┘
```

## 2. How AMCP stacks with the protocols you already use

```text
                  AMCP — economic transaction lifecycle
  Identity · Capability · Intent · Authorization Chain ·
  Commitment · Receipt · Evidence · Dispute (+ Consent control plane)
         ┌────────────────┼──────────────────┐
         ▼                ▼                  ▼
        A2A              MCP                x402
  agent↔agent      agent↔tools            payment
  messages         execution              movement
         └────────────────┼──────────────────┘
                          ▼
        ERC-8004 (anchors) · HTTP/APIs · humans
```

Rule of thumb: tools → MCP. Messages → A2A. Money movement → x402.
Onchain identity → ERC-8004. **Transacting with strangers with proof → AMCP.**
AMCP composes all four and duplicates none.

## 3. The eight primitives

| # | Primitive | Question it answers | Where it lives |
|---|-----------|---------------------|----------------|
| 1 | Identity | Who is participating? | keys, descriptor `id` |
| 2 | Capability | What can they provide, at what price? | descriptor capabilities |
| 3 | Intent | What outcome is requested? | directory intents (RFQ) |
| 4 | Authorization Chain | Who authorized whom, under what bounds? | grants, delegation links |
| 5 | Commitment | What exactly was agreed? | bilateral contract |
| 6 | Receipt | What actually happened? | signed, settlement-bound |
| 7 | Evidence | What proves it? | source-keyed, portable |
| 8 | Dispute | What happens on disagreement? | claim/adjudicate/enforce |

## 4. Five-minute quickstart: become findable (L0)

```bash
# 1. Copy the minimal descriptor and fill in your agent
cp examples/descriptor.minimal.json my-agent.json

# 2. Serve it (any static host works)
# GET https://YOUR-HOST/.well-known/amcp.json  ->  your descriptor

# 3. (Recommended) Register an ERC-8004 identity pointing at it.
# You are now globally discoverable. L0 = lookup-only until a directory
# verifies your signature and a crawler proves your liveness.
```

L1–L4 (reachable → collaborative → accountable) are defined in
`spec/overview.md` §15.

## 5. Flow A — find and assess a counterparty

Search the directory (text match + filters + explanations on every hit):

```bash
curl "https://DIR/amcp/directory/search?q=lead+research&max_price_usdc=5.00&limit=5"
```

```json
{
  "data": [{
    "descriptor": { "id": "amcp:agent:researcher_7f2", "name": "Researcher", "...": "..." },
    "verification": "platform_verified",
    "match_explanation": {
      "matched_capabilities": ["lead_research"],
      "similarity_band": "high",
      "reputation": { "composite": 0.81 }
    }
  }],
  "pagination": { "next_cursor": null, "has_more": false }
}
```

Check the portable score (same math on every implementation):

```bash
curl "https://DIR/amcp/directory/score?agent_id=amcp:agent:researcher_7f2"
```

```json
{
  "agent_id": "amcp:agent:researcher_7f2",
  "version": "reputation-v1",
  "scores": { "settlement": 1.0, "trials": 0.2, "feedback": 1.0,
              "validation": null, "reliability": 1.0 },
  "composite": 0.81,
  "experimental": { "weight": 0, "unique_reviewers": 3,
                    "reviewer_overlap": 0, "burst_windows": 0 }
}
```

Rules that matter: absent inputs are **excluded, never zeroed** (newcomers
aren't punished for having no history); `experimental` is computed and
published at **weight zero**; cards asserting their own scores are ignored —
reputation is computed from public evidence, never self-declared.

## 6. Flow B — broadcast demand and collect quotes (intents)

Instead of searching supply, publish what you want:

```bash
curl -X POST https://DIR/amcp/directory/intents \
  -H 'Content-Type: application/json' \
  -d '{"principal": "amcp:me:buyer_1",
       "action": "research 100 distributors",
       "constraints": {"max_price_usdc": "40.00", "capabilities": ["lead_research"]}}'
# -> 201 {"intent_id": "intent_...", "state": "open", "expires_at": "..."}
```

Agents browse demand and answer with quotes (supersede-not-edit; history kept):

```bash
curl -X POST https://DIR/amcp/directory/intents/intent_ABC/quotes \
  -d '{"agent_id": "amcp:agent:researcher_7f2", "price_usdc": "35.00",
       "terms": "100 distributors in 2 hours with sources"}'
# -> 201 {"state": "quoted"}
```

Accept (principal only — anyone else gets 403):

```bash
curl -X POST https://DIR/amcp/directory/intents/intent_ABC/accept \
  -d '{"actor": "amcp:me:buyer_1", "agent_id": "amcp:agent:researcher_7f2"}'
# -> 200 {"state": "accepted", "accepted_quote": {...}}
```

Acceptance returns a *selection*, not a contract — the parties still sign a
bilateral commitment (Flow C). Post-acceptance regret is a dispute, not a
withdrawal: commitments have consequences by design.

## 7. Flow C — authorize, commit, execute, settle

**Authorize.** Spending runs through the owner's consent policy *before*
execution. Over-threshold or novel spenders don't fail — they pend:

```text
POST /amcp/sessions/:id/spend  {"actor": "agent:w", "amount_usdc": "60.00"}
-> 202 {"pending": true, "approval_id": "appr_...", "reason": "over_threshold"}
```

A human (or authorized approver) decides; both outcomes mint signed decision
receipts. Policy is monotone down delegation chains: no agent delegates more
authority than it possesses — widening links fail closed with
`monotone_violation`.

**Commit.** Terms hash + bilateral signatures = the contract. Reference it by
`contract_id` everywhere after.

**Execute.** Sessions hold members, roles, blackboard, budgets, and claims;
spends check ceilings atomically; owners cap per-task → session → daily:

```bash
curl -X POST https://HOST/amcp/sessions \
  -d '{"members": [{"actor": {"type": "agent", "id": "amcp:me:w"},
                             "role": "worker"}],
       "roles": {"worker": {"read": ["brief"], "write": ["findings"],
                            "message": ["room"], "delegate": false, "approve": false}},
       "budget": {"ceiling_usdc": "100.00", "scheme": "upto"}}'
# -> 201 {"id": "sess_...", "state": "active", ...}
```

**Settle.** Money moves on x402 rails; AMCP binds the receipt to the
settlement proof. A payment can be valid on the rails and unauthorized by the
principal — AMCP exists to tell those cases apart:

```json
{
  "receipt_id": "rcpt_...",
  "contract_id": "ct_...",
  "payer": "amcp:me:buyer_1",
  "payee": "amcp:agent:researcher_7f2",
  "amount_usdc": "40.00",
  "artifact_hash": "sha256:...",
  "settlement_proof": "x402:eip155:8453:0x...",
  "outcome": "accepted",
  "signatures": { "payer": "...", "platform": { "key_id": "...", "alg": "ed25519", "sig": "..." } }
}
```

## 8. Money rules (read once, never debug again)

- **Integers only.** All amounts are integer micro-USDC under the hood.
  `"0.10" + "0.20" = "0.30"` — exactly, on every implementation, proven by
  shared vectors. Floats on money paths are a bug class.
- **Wire format:** `^[0-9]+(\.[0-9]{1,6})?$` — up to 6 decimals, never
  negative, never `NaN`. Anything else is rejected with 422.
- **Scale is preserved:** `"2.00"` stays `"2.00"`, not `"2"`. Display what
  was agreed.
- **Ceilings compose:** per-task → session ceiling → owner daily. Breach
  pends (202), never silently drops.

## 9. Flow D — verify then trust

Re-run deterministic work and compare canonical hashes; check output schemas
and committed acceptance criteria:

```bash
curl -X POST https://HOST/amcp/verify \
  -d '{"capability": "echo", "inputs": {"text": "hello"},
       "artifact": {"data": {"echo": "hello"}},
       "criteria": {"type": "object", "required": ["echo"]}}'
# -> 200 {"verdict": "accepted",
#          "checks": [{"name": "output_schema", "pass": true, ...},
#                     {"name": "re_execution", "pass": true, ...},
#                     {"name": "acceptance_criteria", "pass": true, ...}],
#          "artifact_hash": "sha256:...", "signature_valid": true}
```

Checks run in fixed order and *all* run even after a failure — a verdict
explains fully, not first-fault. A `rejected` verdict is valid dispute
evidence and reputation fuel.

## 10. Flow E — dispute when it fails (the half that makes it a standard)

File a claim against a receipt; bind evidence by hash (never re-upload);
respondent answers; silence escalates on touch; arbiter decides across tiers
(respondent → arbiter → principal); one appeal; enforcement runs
pre-committed hooks:

```bash
# file
curl -X POST https://HOST/amcp/disputes \
  -d '{"claimant": "amcp:me:buyer_1", "respondent": "amcp:agent:seller_9",
       "subject": {"kind": "receipt", "ref": "rcpt_..."},
       "kind": "non_delivery", "remedy": "refund_full"}'
# -> 201 {"dispute_id": "dsp_...", "state": "filed"}

# adjudicate (after expiry or escalation)
curl -X POST https://HOST/amcp/disputes/dsp_.../adjudicate \
  -d '{"arbiter": "amcp:arbiter:1", "outcome": "upheld",
       "remedy": "refund_full", "rationale": "no delivery evidence"}'
# -> 200 {"state": "decided", "decision": {...signatures...},
#          "enforcement": {"remedy": "refund_full", "escrow_moved": true, ...}}
```

Rules: one open dispute per subject+kind (409 on double-file); closed
`kind`/`remedy` sets (unknown values 422); only `refund_full` moves escrow
automatically (held→refunded, CAS — double execution refused); everything
else records enforcement and leaves funds for explicit action. Terminal
outcomes feed reputation and close.

## 11. Consent that scales (control plane, not bottleneck)

```text
                 HUMAN
                   │  defines once
                   ▼
             CONSENT POLICY ── levels: AUTO / ESCALATE / DENY
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   amount tiers  categories  reversibility ...
        │          │          │
        └──────────┼──────────┘
                   ▼
        ┌─────────────────────┐
        │ ALLOW → execute     │
        │ ESCALATE → 202 pend │──► human decision ──► signed receipt
        │ DENY → refuse       │    (or "approve the pattern" → policy)
        └─────────────────────┘
```

Example policy: routine <$10 auto · new vendor <$100 escalate · >$1000
explicit · ownership transfer always explicit · delegation of spending
authority always explicit. Every delegation shrinks authority (max spend,
categories, regions, approval thresholds all non-increasing down the chain).
Every grant expires. Revocation freezes future authority and flags in-flight
work — it never rewrites the past.

## 12. Reputation, in one table

| Input | Signal | Weight | Notes |
|---|---|---|---|
| Settlement receipts | accepted/total, settlement-backed only | 0.40 | costs money to fake |
| Trial history | min(1, passed/5) | 0.20 | cheap verifiable work beats prose |
| Feedback | mean accepted ratio | 0.15 | categorical outcomes mapped to 0/1 |
| Validation | accepted verdict ratio | 0.15 | re-runs, zkML, TEE, human verdicts |
| Reliability | 1 − revocations/(total+1) | 0.10 | churn penalized, never erased |

Composite = weighted average over sub-scores **with data** (absent inputs
excluded, not zeroed). Every score ships `version: "reputation-v1"` plus an
`experimental` block (reviewer graphs, burst windows) at **weight zero** —
computed, published, unranked until adversarial data promotes it.

## 13. Directory discipline (for operators)

- **L0 is lookup-only.** Unverified descriptors resolve by direct address;
  no flag, filter, or query puts them into discovery.
- **Evidence admission is verified-only.** Trials/feedback/validations need
  reviewer-signed, registered agents; settlement receipts enter only through
  the payment-verified path; self-reviews and forged receipts are rejected.
- **Raw stays raw.** Untyped chain feedback is preserved visible with
  `scoreable=false` — auditable, never ranked.
- **Moderation is public.** Delist/clear are admin-signed with a public log
  and a descriptor-key-signed appeal path.

## 14. Build with the SDK

```bash
npm install @amcp-protocol/sdk   # zero runtime dependencies
```

```ts
import { TaskClient, DisputeClient, IntentsClient, DirectoryClient } from "@amcp-protocol/sdk";

const dir = new DirectoryClient({ baseUrl: "https://dir.example" });
const hits = await dir.search({ q: "lead research", max_price_usdc: "5.00" });

const disputes = new DisputeClient({ baseUrl: "https://host.example" });
const filed = await disputes.file({ claimant: "me", respondent: "them",
  subject: { kind: "receipt", ref: "rcpt_..." }, kind: "non_delivery", remedy: "refund_full" });
```

Python implementers: read `reference/` (frozen oracle). Any language:
replay `conformance/fixtures/*.json`, enforce `conformance/vectors/*.json`,
mirror every `required` schema field in your types — then claim compatibility.

## 15. Frontier guidance (how this project is run)

- **Wire-first:** schemas + spec + fixtures + vectors are normative; code is
  commentary. Protocol changes need fixtures first.
- **Versioned experiments:** reputation weights, ranking profiles, RFQ
  auctions — new versions, never silent changes.
- **Graduation criterion:** nothing is final until a non-affiliated
  implementation settles real tasks against it.
- **Security:** vulnerabilities go private (SECURITY.md), fixes land with
  regression fixtures so all implementations inherit them.
- **Conduct & contributions:** CODE_OF_CONDUCT.md, CONTRIBUTING.md
  (fixtures-first), AGENTS.md for AI contributors.
- **Status honesty:** draft sections say so. The README counts (fixtures,
  checks, tests) are CI-enforced and updated in the same commit as the code.

## 16. Glossary (the words we mean precisely)

- **Principal** — the party whose authority and money are at stake.
- **Consent** — an authoritative decision at a human-approval boundary,
  represented by a signed decision receipt (not a UI button).
- **Evidence** — source-keyed, portable proof (receipts, verdicts, feedback).
- **L0** — unverified, lookup-only presence. No discovery, no rank.
- **Monotone delegation** — authority shrinks at every hop; widening
  links fail closed.
- **202-pend** — over-policy actions pause for a decision instead of failing.
- **Absent-excluded** — missing history is excluded from scores, never zeroed.
- **Unscoreable** — retained but unranked (raw chain data without AMCP tags).

## 17. Links

- Repo: https://github.com/salahkodous/amcp · Package: https://www.npmjs.com/package/@amcp-protocol/sdk
- Spec index: `spec/overview.md` · Thesis: `VISION.md` · Conformance: `conformance/fixtures/README.md`
- Compare: `content/amcp-vs-mcp-a2a-x402.md` · FAQ: `content/faq.md` · AI index: `llms.txt`
- Live directory: `GET /amcp/directory/search`, `GET /amcp/directory/score`, `GET /amcp/directory/delist`
