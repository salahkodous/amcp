# Fixture format (portable conformance)

Python scripts can't be replayed by a Rust or TypeScript implementation. Fixtures can. Any AMCP implementation proves compatibility by replaying `conformance/fixtures/*.json` and passing every item — same assertions, every language.

## File shape

```json
{
  "version": "0.1",
  "fixtures": [
    {
      "name": "echo-executes",
      "request": {"method": "POST", "path": "/amcp/task",
                  "headers": {"Idempotency-Key": "k1"},
                  "body": {"capability": "echo", "inputs": {"text": "hello"}}},
      "capture": {"task": "task.task_id"},
      "save_as": "echo1",
      "expect": {"status": 200,
                 "where": {"artifact.data.echo": "hello"},
                 "has": ["task", "artifact", "receipt"]}
    }
  ]
}
```

- `request`: `method`, `path` (with `{var}` substitution), optional `headers`, `body`.
- `capture`: `{var: dotted.path}` from the response body for later steps (stateful flows: session ids, cursors).
- `save_as` / `identical_to`: name a response, then assert a later response is byte-identical (idempotency).
- `expect`: `status` (required), `where` (dotted path → exact value; `{var}` allowed), `has` (top-level keys), `absent` (dotted paths that MUST be missing — redaction), `headers` (response header values).
- Dotted paths walk nested objects and numeric list indices (`data.0.descriptor.id`) — no wildcards, no expressions. If an assertion needs logic, it doesn't belong in fixtures; it belongs in the implementation's own tests.

## Coverage (70 fixtures, all green vs the reference)

`l0-l2` · `sessions` · `directory` · `negotiation` · `escalation` · `keys-wire` (shape only; crypto vectors stay in `reference/test_keys.py` — library-level, not wire). Streaming (SSE) is intentionally not fixture-expressible yet; it needs a streaming-aware replayer, defined later. Everything else wire-visible is covered.

## Runners

- `conformance/replay.py` — boots the Python reference in-process, replays a fixture file. CI runs every file in `fixtures/`.
- Ports (TS SDK, Rust runtime) MUST ship an equivalent replayer against the same files before claiming any level.
