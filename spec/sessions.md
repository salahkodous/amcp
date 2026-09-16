# Sessions (ALL IN THE LOOP)

A session is a bounded multi-party collaboration: N agents + M humans, roles, scoped shared state, one timeline. Shape: `../schemas/session.schema.json`.

## Lifecycle

```text
proposed → active → paused → completed | cancelled
```

- `propose`: creator declares members (invited), roles, policy, budget ceiling, conflict policy.
- `active`: invites accepted (explicit accept; silence ≠ consent). Spend and delegation enabled.
- `paused`: spend + delegation frozen immediately; blackboard stays readable per roles. Triggered by coordinator, approver, escalation rule, or schema/pin drift.
- `completed | cancelled`: terminal. Retention policy executes (`purge | archive | handoff`); purge is a timeline event, not silent deletion.

## Roles

- Permissions are `read[] / write[] / message[] / delegate / approve` over named blackboard keys and channels (`room`, `direct`, named role-channels). `*` = all (coordinator conventionally).
- Join delivers the **role-scoped snapshot only**. Hosts MUST NOT leak unreadable slices; coordinators relaying across roles MUST NOT forward unreadable content (conformance-tested with canary keys).
- Humans join identically (`actor.type: human`) with `presence: active|away|offline`. Approvals and typed inputs are inline timeline events.

## Routing

- `room`: broadcast, filtered by each recipient's role readability.
- `direct`: member→member, always logged to the timeline (no side channels inside a session).
- `role-channel`: all holders of a role.
- Every message records `{actor, role, authority, ts}` — authority names the permission exercised.

## Claims and conflicts

- Subtasks are atomically claimable: `claim → claimed_by | already_claimed`. Double-work is a protocol failure.
- Concurrent blackboard writes resolve per `conflict_policy`: `coordinator_arbitrates` (default), `human_decides`, `last_write_wins` (commutative-declared fields only).

## Escalation

Session `escalation[]` rules evaluate on every state-changing event: `{trigger, action: require_approval|pause|notify, role, timeout_seconds, default: deny}`. Timeouts resolve to `default` (SHOULD be `deny` for spend/irreversible effects). All evaluations are timeline events.

## Collapse rule

A 2-member session with default roles MUST behave as a plain conversation. Ceremony scales with membership, never below it.
