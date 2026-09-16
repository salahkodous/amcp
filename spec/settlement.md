# Settlement

Money moves on x402 v2 rails. AMCP defines only the economic state machine around them. Shapes: `../schemas/contract.schema.json`, `../schemas/receipt.schema.json`.

## Primitives used (referenced, not redefined)

- `exact`: fixed price, verify → execute → settle.
- `upto`: authorize ceiling, settle actual. **The session-budget primitive.**
- `escrow`: settle(deposit) → execute → settle(final). **The per-task deposit primitive.**
- `batch-settlement`: escrow + offchain vouchers, periodic redemption. **Mandatory for `per_task` pricing under $1.00.**
- Headers `PAYMENT-REQUIRED` / `PAYMENT-SIGNATURE` / `PAYMENT-RESPONSE`; facilitator `/verify` + `/settle`.

## Flow

1. **Budget:** principal authorizes a session ceiling (`upto`). Spend meters task settlements + data egress against it. Breach pauses the session (`budget_exceeded`).
2. **Contract:** negotiation accept mints the signed contract (terms hash pinned). No paid work without one.
3. **Deposit (optional):** for untrusted counterparties, escrow deposit settles first.
4. **Execute:** task runs under §7 task states; artifact delivered content-addressed.
5. **Acceptance:** principal (or designated approver role) validates artifact against `acceptance_criteria_schema` → `accepted | rejected(reason)`.
6. **Settle:** acceptance triggers facilitator `/settle` for the exact amount and mints the **receipt** — signed by payer + platform/host. Only this event creates reputation.
7. **Dispute:** `DISPUTED` freezes funds; both timelines are evidence; arbitrator decides `release | refund | split`. Lost disputes weigh more than completions. Refunds/splits travel the settle path with receipt-level semantics — never off-ledger adjustments.

## Custody (v0.1)

Agents hold **budgets**, not wallets. Escrow and settlement execute host/platform-side against delegated caps. External agents holding real x402 wallets is a defined Phase-2 extension (same receipt format, `platform` signature becomes the wallet owner's).
