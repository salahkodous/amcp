# Security

Threats T1–T8 with mandated mitigations. "SHOULD" items are conformance-checked; "MUST" items gate level claims.

| # | Threat | Mitigation |
|---|---|---|
| T1 | Cross-agent confused deputy (compromised A steers privileged B) | No implicit authority inheritance. Delegation = explicit signed grant scoped to capability + purpose + session + expiry. Receivers verify the authority chain per privileged step against session policy. |
| T2 | Synthetic identity injection ("Admin Helper" with no keys) | Unsigned descriptors are discovery-only: ineligible for paid work, delegation, or roles above observer. Session join requires key-bound identity; mismatches rejected. |
| T3 | Prompt injection across the boundary (artifacts/tool outputs/peer messages) | Envelope classes (`../schemas/part.schema.json`): `instruction` from authorized+signed actors only; `content` untrusted by default; `evidence` immutable. Promotion of content→instruction without signature is a conformance failure. |
| T4 | TOCTOU / stale authority | Task-scoped, intent-bound tokens (subject+audience+purpose+session+expiry). Re-check per privileged step; fail closed; revocation propagates within a bounded window. |
| T5 | Memory/state bleed across sessions | Per-session sandboxed context; role-slice redaction (canary-tested); re-scope or wipe between sessions. |
| T6 | Malicious capability / tool poisoning | Fully-qualified names + version pins; hash drift pauses tasks; artifact scope enforcement; sandbox + egress allowlists for untrusted counterparties. |
| T7 | Economic attacks (fake work, inflated subtasks, Sybil reviewers) | Escrow + acceptance-gated settlement; proof-bound receipts (settlement proofs, not self-scores); competing aggregators over public evidence — no canonical score in-protocol. |
| T8 | Rogue participant at runtime | Kill switch: instant grant revocation session-wide; emergency directory delisting; revocations as signed timeline events. |

Posture: zero-trust between members, least-privilege roles, human approval for irreversible/high-value effects enforced at runtime. The session timeline plus signed receipts **is** the audit trail.
