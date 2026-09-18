"""Authorization-chain evaluator, authz-v1 (spec/authorization.md).
Pure function: chain + request + now -> decision. Identical in reference
and production; hosts compose key-active checks conjunctively outside it.
"""

from decimal import Decimal

VERSION = "authz-v1"

DECISIONS = ("allow", "escalate", "deny")


def _parse_amount(raw) -> Decimal | None:
    """Wire-format amounts only (same pattern as reference _amt)."""
    import re
    if not isinstance(raw, str) or not re.match(r"^[0-9]+(?:\.[0-9]{1,6})?$", raw):
        return None
    v = Decimal(raw)
    if not v.is_finite() or v < 0:
        return None
    return v


def _parse_ts(raw) -> float | None:
    if not isinstance(raw, str):
        return None
    try:
        from datetime import datetime, timezone
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()
    except ValueError:
        return None


def _limit(raw) -> Decimal | None:
    """Absent limit = +infinity (unbounded link). Returns None for absent;
    raises ValueError for present-but-malformed (never silently unbounded)."""
    if raw is None:
        return None
    v = _parse_amount(raw) if isinstance(raw, str) else None
    if v is None:
        raise ValueError(f"malformed limit: {raw!r}")
    return v


def _allows_scope(scope, operation) -> bool:
    if not isinstance(scope, str) or not scope or not isinstance(operation, str):
        return False
    return operation == scope or operation.startswith(scope + ":")


def _subset(child, parent) -> bool:
    if parent is None:
        return True
    if child is None:
        return False
    try:
        return set(child) <= set(parent)
    except TypeError:
        return False


def _shape_ok(link: dict) -> bool:
    """Link values must be well-typed. Malformed authority is unusable —
    never silently unbounded, never silently unconstrained."""
    for key in ("max_spend_usdc", "require_approval_above_usdc"):
        if link.get(key) is not None:
            try:
                _limit(link[key])
            except ValueError:
                return False
    for key in ("categories", "regions"):
        if link.get(key) is not None and not isinstance(link[key], list):
            return False
    if link.get("expires_at") is not None and _parse_ts(link["expires_at"]) is None:
        return False
    return True


def monotone(parent: dict, child: dict) -> bool:
    """Authority may only shrink down a chain. Absent parent bound means
    unbounded, so any child bound still shrinks (or ties)."""
    p_max, c_max = _limit(parent.get("max_spend_usdc")), _limit(child.get("max_spend_usdc"))
    if c_max is not None and p_max is not None and c_max > p_max:
        return False
    p_thr, c_thr = _limit(parent.get("require_approval_above_usdc")), _limit(child.get("require_approval_above_usdc"))
    if c_thr is not None and p_thr is not None and c_thr > p_thr:
        return False
    if not _subset(child.get("categories"), parent.get("categories")):
        return False
    if not _subset(child.get("regions"), parent.get("regions")):
        return False
    return True


def evaluate(chain: list, request: dict, now: float) -> dict:
    """Full algorithm per spec/authorization.md §3. Never raises on shape
    variance — malformed input denies with a reason, it doesn't crash."""
    if not isinstance(chain, list) or not chain or not isinstance(request, dict):
        return {"decision": "deny", "reason": "chain_broken", "authority": -1}
    actor, op = request.get("actor"), request.get("operation")
    # 0. contiguity
    ok = True
    for i, link in enumerate(chain):
        if not isinstance(link, dict):
            ok = False
            break
        want_delegator = chain[i - 1].get("delegate") if (i > 0 and isinstance(chain[i - 1], dict)) else None
        if i > 0 and link.get("delegator") != want_delegator:
            ok = False
            break
    if not ok or not actor or chain[-1].get("delegate") != actor:
        return {"decision": "deny", "reason": "chain_broken", "authority": -1}
    # 0b. link shape: malformed values deny, never silently unbounded
    for link in chain:
        if not _shape_ok(link):
            return {"decision": "deny", "reason": "malformed_link", "authority": -1}
    # 1. liveness
    for link in chain:
        if link.get("revoked") is True:
            return {"decision": "deny", "reason": "link_revoked", "authority": -1}
        exp = _parse_ts(link["expires_at"]) if link.get("expires_at") is not None else None
        if exp is not None and now >= exp:
            return {"decision": "deny", "reason": "link_expired", "authority": -1}
    # 2. monotonicity
    try:
        for i in range(1, len(chain)):
            if not monotone(chain[i - 1], chain[i]):
                return {"decision": "deny", "reason": "monotone_violation", "authority": -1}
    except ValueError:
        return {"decision": "deny", "reason": "malformed_link", "authority": -1}
    # 3. scope, every link
    for link in chain:
        if not _allows_scope(link.get("scope"), op):
            return {"decision": "deny", "reason": "scope_mismatch", "authority": -1}
    # 4. category / region
    for link in chain:
        cats, regs = link.get("categories"), link.get("regions")
        if request.get("category") is not None and cats is not None \
                and request["category"] not in cats:
            return {"decision": "deny", "reason": "category_denied", "authority": -1}
        if request.get("region") is not None and regs is not None \
                and request["region"] not in regs:
            return {"decision": "deny", "reason": "region_denied", "authority": -1}
    # 5. amount (spend ops only)
    amount = None
    if request.get("amount_usdc") is not None:
        amount = _parse_amount(request["amount_usdc"])
        if amount is None:
            return {"decision": "deny", "reason": "invalid_amount", "authority": -1}
        for link in chain:
            cap = _limit(link.get("max_spend_usdc"))
            if cap is not None and amount > cap:
                return {"decision": "deny", "reason": "over_limit", "authority": -1}
    # 6. escalation
    if amount is not None:
        for link in chain:
            thr = _limit(link.get("require_approval_above_usdc"))
            if thr is not None and amount > thr:
                return {"decision": "escalate", "reason": "approval_required",
                        "authority": len(chain) - 1}
    return {"decision": "allow", "reason": "allow", "authority": len(chain) - 1}
