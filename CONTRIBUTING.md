# Contributing to AMCP

## The one rule

**The wire contract owns the protocol, not any implementation.** `schemas/` + `spec/` + `conformance/fixtures/` are normative. Code is commentary.

## How to contribute

1. **Protocol changes need fixtures first.** A new endpoint, field, or behavior MUST arrive with JSON fixtures in `conformance/fixtures/` that the Python reference passes via `conformance/replay.py`. No fixtures, no merge.
2. **Run everything before pushing:**
   ```bash
   python conformance/replay.py
   python reference/test_conformance.py
   python reference/test_sessions.py
   python reference/test_directory.py
   python reference/test_negotiation.py
   python reference/test_keys.py
   python reference/test_escalation.py
   python reference/test_streaming.py
   ```
   (Use the interpreter with `pynacl` for live-key checks; without it, key tests fall back to dev-HMAC paths.)
3. **Two-track firewall.** Anakin-specific needs do NOT get private protocol fields. Propose them as RFCs against `spec/`; one private field anywhere fails review.
4. **Reference stays boring.** `reference/` is stdlib-only Python, optimized for readability. Performance work belongs in `runtime-rs/`; ergonomics in `sdk-ts/`. If your PR makes the reference harder to read, it goes elsewhere.
5. **Security issues:** T1–T8 in `spec/security.md` are the threat model. Report vulnerabilities privately to the maintainers first; do not open public issues for live exploits.

## Repo map

```text
schemas/                Normative JSON Schemas (draft 2020-12)
spec/                   Human-readable spec
examples/               Valid sample documents (validated against schemas in CI)
conformance/            CHECKLIST + portable JSON fixtures + replay.py
reference/              MIT reference agent (stdlib Python) — the spec oracle
sdk-ts/                 (planned) TypeScript SDK for agent developers
runtime-rs/             (planned) Rust production runtime for non-Workers hosting
```
