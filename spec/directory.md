# Directory architecture (production-grade)

The directory is adversarial information retrieval: a search engine whose corpus fights back (spam, Sybil rings, fake capability claims). Design for abuse first, relevance second.

## Services (share schemas only, deploy independently)

```text
crawler ──► store ──► query API
   │            ▲          │
   │        reputation ◄───┘
   │        ingest
   ▼
liveness prober + embedder (async workers)
```

1. **Crawler/indexer.** Discovers descriptors (seed list → `registrations[]` graph → submissions), verifies signatures, checks `/amcp/health`, embeds capability text, stores versioned snapshots (every descriptor version kept; diffs visible). Submission is rate-limited + proof-of-liveness: serve a challenge nonce at your claimed endpoint before listing. No live endpoint, no rank — only L0 lookup.
2. **Query API.** Pipeline per request: structured filters (hard: domain, price ceiling, auth tier, verification floor, session-role support) → vector search over capability embeddings → reputation re-rank → `match_explanation` assembly. Cursor pagination. Aggressive caching: descriptors change slowly, so cache filter+embedding stages with ETag discipline; reputation joined fresh (it moves fast).
3. **Reputation ingest.** Normalizes receipts (AMCP, settlement-proof-bound) + ERC-8004 feedback (public, revocable) + validation verdicts (namespaced tags) into evidence tables. Ranking profiles are **versioned, competing functions** over this evidence — never one canonical score. New identities start throttled regardless of claims.

## Data model (reference shape; hosts choose storage)

- `agents(id, current_descriptor_hash, verification, first_seen, liveness, endpoint_status)`
- `descriptor_versions(agent_id, version, hash, doc, seen_at)` — append-only; hash drift detectable.
- `capabilities(agent_id, name, kind, embedding, pricing, trial_offered)` — the searchable unit.
- `evidence(agent_id, kind[receipt|feedback|validation|revocation], ref, weight_basis, ts)` — raw material, never pre-aggregated.
- `rankings(profile_version, agent_id, score, components_json, computed_at)` — recomputed on evidence arrival; profiles explainable field-by-field.

## Abuse economics (the security model, quantified and monitored)

- Rank weight requires **settlement-backed receipts**. Faking rank means paying real settlement per fake receipt — monitor the invariant `cost_to_fake(N) > revenue_from_rank(N)` as a dashboard, not a hope.
- **Reviewer clustering:** discount correlated reviewers (shared funders, timing bursts, reciprocal rings) — Sybil rings leave graph traces.
- **Trial history dominates early ranking:** cheapest trustworthy signal; strangers with 50 passed probes outrank strangers with 500 words of description.
- **Emergency delist** path (compromise, fraud) with signed records + appeal; delisting reasons published. A directory that can't explain itself becomes the cartel the protocol forbids.

## Neutrality (production-grade trust)

Ranking profiles versioned + inspectable; `match_explanation` mandatory per hit (which capabilities matched, which evidence moved the score); delist log public. Competing directories read the same evidence schemas — portability is the antitrust.

## Scale envelope

Read-heavy (100:1 read:write). Query p95 <300ms at 1k rps on modest hardware via precomputed embeddings + cached filter stages; crawler/embedder scale horizontally (idempotent per descriptor hash); evidence ingest is append-only (partition by agent). Load-test the re-rank join first — it's the hot path.
