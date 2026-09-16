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
- Concurrent blackboard writes resolve per `conflict_policy`: `coordinator_arbitrates` (default), `human_escalation`, `first_claim_wins` (claim races; `last_write_wins` only for commutative-declared fields).

## Decision policy (default-deny thresholds)

Money moves on two rails: affordable-and-routine (executes) vs novel-or-large (pauses for a human). Every session carries `decision_policy`:

```text
spend_threshold_usdc    spends above this need approval (default "1.00")
new_spender_approval    first spend by an unknown actor needs approval (default false;
                        production SHOULD set true)
```

Evaluation order per spend: membership → budget → policy. A triggered policy does NOT error — it returns `202 {pending: true, approval_id}` and records a `pending_approval` plus an approval-queue effect. `approve` (approver role only) re-checks the ceiling (funds may have moved) and executes; `deny` closes it. Both produce a **signed decision receipt**: `{approval_id, session_id, inputs_hash, policy, decision, principal, decided_at, result}` — attribution without pretending attribution equals prevention. Defaults stay green for demo amounts; tightening is one field.

## Escalation design (evaluator)

Money moves on two rails: affordable-and-routine (executes) vs novel-or-large (pauses for a human). Every session carries `decision_policy`:

```text
spend_threshold_usdc    spends above this need approval (default "1.00")
new_spender_approval    first spend by an unknown actor needs approval (default false;
                        production SHOULD set true)
```

Evaluation order per spend: membership → budget → policy. A triggered policy does NOT error — it returns `202 {pending: true, approval_id}` and records a `pending_approval` plus an approval-queue effect. `approve` (approver role only) re-checks the ceiling (funds may have moved) and executes; `deny` closes it. Both produce a **signed decision receipt**: `{approval_id, session_id, inputs_hash, policy, decision, principal, decided_at, result}` — attribution without pretending attribution equals prevention. Defaults stay green for demo amounts; tightening is one field.

Conflicts arrive as: claim collisions, budget disputes, member flags. The evaluator routes them by the session's frozen `conflict_policy` — it never invents policy, only executes it.

- **Record:** `{id, session_id, kind, raised_by, refs (claims/tasks), policy_snapshot, state}`. The policy snapshot is frozen at raise-time so mid-dispute edits can't move the goalposts.
- **Policies:**
  - `coordinator_arbitrates` → coordinator decides within timeout (default 24h); silence escalates to human approver automatically. Coordinator decisions are appealable once, to a human.
  - `human_escalation` → affected scope (subtask/budget line) freezes immediately; approver decides; on timeout the **safe default** executes (refund unspent, split remainder, release claims) — money never hangs on human latency.
  - `first_claim_wins` → automatic for claim races; no human involved; decision cites the winning `claimed_at`.
- **Decision:** signed record (see `security.md` keys) appended to the timeline, affected members notified. Appeal: one round, human-only, then final.
- **Evaluator is stateless logic over session state** — same function in reference and production; only the notification transport differs.
- **Trigger rules:** session `escalation[]` entries evaluate on every state-changing event: `{trigger, action: require_approval|pause|notify, role, timeout_seconds, default: deny}`. Timeouts resolve to `default` (SHOULD be `deny` for spend/irreversible effects). All evaluations are timeline events.

## Collapse rule

A 2-member session with default roles MUST behave as a plain conversation. Ceremony scales with membership, never below it.
