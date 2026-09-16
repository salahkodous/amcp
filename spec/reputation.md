# Reputation v1: formalized inputs, instrumented graphs, experimental clustering

Status: **instrumentation phase**. v1 scores from the inputs below; reviewer graphs are logged from day one; clustering signals are computed, reported, and given **weight zero** until they meet real adversarial data. No load-bearing Sybil judgment without evidence.

## Inputs (all from public evidence — receipts, feedback, validation, trials)

| Input | Signal | Weight | Notes |
|---|---|---|---|
| Settlement receipts | accepted/total, settlement-backed only | 0.40 | Costs money to fake; highest weight by design |
| Trial history | min(1, passed/5) | 0.20 | Cheap verifiable work beats prose |
| Feedback | mean accepted ratio | 0.15 | Categorical outcomes mapped to 0/1 |
| Validation | accepted verdict ratio | 0.15 | Third-party verdicts (re-run, zkML, TEE, human) |
| Reliability | 1 − revocations/(total+1) | 0.10 | Retraction churn penalized, never silently dropped |

Composite `reputation-v1` = weighted average over sub-scores **with data** (absent inputs excluded, not zeroed — newcomers aren't punished for having no history, they just rank on trials). Version string pinned in every score response; weight changes ship as `reputation-v2`, never silently.

## Reviewer graph (logged, not judged)

Evidence carries optional `reviewer` (wallet/address, ERC-8004 clientAddress convention). From it:

- `unique_reviewers`: distinct reviewers per agent (Sybil cost proxy).
- `reviewer_overlap`: Σ over reviewers of (agents-they-reviewed − 1) — shared-reviewer density.
- `burst_windows`: 1-hour windows with ≥3 evidence items from one reviewer.

These ship inside `experimental:` in every score response. Ranking MUST NOT consume them until the clustering study (gate 5+) promotes one with adversarial data.

## Anti-Sybil posture (explicit)

1. Faking rank costs real settlement per fake receipt (economic invariant, monitored).
2. Newcomers earn via trials, not claims (built into ranking).
3. Revocations are public and penalize reliability (churn ≠ clean slate).
4. Reviewer-clustering stays experimental until it has met abuse. Anyone claiming otherwise is selling something.

## Adapter instrumentation

Every minted receipt emits an evidence row `{reviewer: payer, agent: payee, kind: receipt, ref}` into `amcp_evidence` — the reviewer-graph seed. Scoring runs in the directory (reference now, general directory gate 5); the adapter's job is complete, timestamped fuel.
