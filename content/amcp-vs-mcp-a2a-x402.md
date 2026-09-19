# AMCP vs MCP vs A2A vs x402 vs ERC-8004

Short version: **AMCP composes them; it competes with none of them.** If
you're choosing one, you're probably misunderstanding at least one.

## One-line each

| Standard | Answers | Does NOT answer |
|---|---|---|
| **MCP** | How does a model use tools/context? | Who authorized it, with whose money, with what proof |
| **A2A** | How do agents message and collaborate? | Budgets, settlement, receipts, failure recourse |
| **x402** | How does payment move between machines? | Whether the payment was authorized by the principal |
| **ERC-8004** | Who is this agent, onchain? What's its raw feedback? | Ranking policy, dispute process, session semantics |
| **AMCP** | How do autonomous participants transact — authorize, commit, prove, resolve — across boundaries? | Tool execution, message transport, money movement, identity issuance |

## The composition (how they stack)

```text
                    AMCP — economic transaction lifecycle
  Identity · Capability · Intent · Authorization · Commitment ·
  Receipt · Evidence · Dispute (+ Consent as control plane)
         ┌──────────────┼──────────────┐
         ↓              ↓              ↓
        A2A            MCP            x402
   agent↔agent    agent↔tools       payment
   messages       execution         movement
         └──────────────┼──────────────┘
                        ↓
              ERC-8004 (anchors) · HTTP/APIs · humans
```

Concrete example — an agent hiring another agent for $40 of research:

- **A2A**: the two agents exchange messages and task updates.
- **MCP**: the hired agent uses tools (search APIs, browsers) internally.
- **x402**: $40 moves machine-to-machine on settlement rails.
- **ERC-8004**: both agents hold onchain identities; feedback is anchored.
- **AMCP**: the directory match, the negotiated quote, the spending
  authorization chain, the bilateral contract, the settlement-bound receipt,
  the reputation evidence, and — if delivery fails — the dispute with
  escrow enforcement. Remove AMCP and you have messages, tool calls, and a
  payment with no shared record of what was agreed, authorized, or proven.

## Frequently confused points

**"Isn't this just A2A + MCP + x402 bundled?"**
No — that's the wrapper test, and AMCP passes it. Source-keyed idempotent
evidence, scale-parity money, 202-pending decision receipts,
absent-excluded reputation, L0-vs-ranked lifecycle, monotone delegation
evaluation: none of these come from the underlying protocols. AMCP defines
the economic state and evidence that *survives across* them.

**"Why not an A2A extension?"**
Scope. A2A's job is communication between opaque agents; loading it with
budgets, escrow hooks, and reputation math would bloat its contract and
split its community. Composition beats absorption.

**"Does AMCP compete with ERC-8004 reputation?"**
No — it consumes it. Raw chain feedback stays auditable; only explicit
categorical tags enter ranking, under a versioned policy anyone can
recompute. The directory is portable infrastructure, not a moat.

**"Which do I adopt first?"**
Tools → MCP. Agent messaging → A2A. Machine payments → x402. Onchain agent
identity → ERC-8004. Transacting with strangers with proof → AMCP. Most
serious agent systems will run all five within two years.
