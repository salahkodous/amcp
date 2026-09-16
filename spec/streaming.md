# Streaming design (fan-out)

Rooms are poll-only today. The fix is small because the event log already exists: the session **timeline is the stream** — SSE is just a cursor over it.

## Transport

- `GET /amcp/session/{id}/events?actor=<member>&cursor=<seq>` → `text/event-stream`.
- Reference implements **SSE only**. Production MAY upgrade to WebSocket (DO-native) behind the same event shapes; clients MUST handle both.
- Reconnect: client sends last seen `seq` (or `Last-Event-ID`); server replays missed events, then live-tails. Heartbeat comment every 15s; client backoff with jitter.

## Event shape

Every timeline entry gains `seq` (per-session monotonic). Event = `{seq, ts, kind, visibility, ...kind-fields}`. Redaction is enforced **at serve time** per the reader's role (roles can change mid-session; publish-time filtering would leak to later-demoted members on replay).

## Backpressure (the only hard part, kept simple)

- Per-consumer bounded buffer (e.g. 512 events). Slow consumer → server drops the connection with `retry` + last-delivered `seq`; client resumes. **The writer never blocks.**
- Presence (`member_joined/left`, idle timeout) rides the same stream — no second channel.

## Ordering guarantee

Single-writer per session (DO in production, the existing lock in reference) assigns `seq`. Consumers treat `seq` as the truth; gaps mean "reconnect and replay", never "guess".

## What we are NOT building

No global bus, no cross-session topics, no exactly-once (idempotent consumers via `seq` dedupe). Collapse rule applies: 2-member sessions MAY poll; streaming becomes REQUIRED at 3+ members or any human member.
