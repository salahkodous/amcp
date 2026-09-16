"""Stateless escalation evaluator (spec/sessions.md#escalation-design).

Pure logic over session state — identical in reference and production; only
the notification transport differs. The agent owns storage, timeouts (lazy:
evaluated on touch, no background timers), and pause/resume side effects.
"""

DEFAULT_TIMEOUT_SECONDS = 86400

#: policy -> role allowed to decide. None = automatic, no human decides.
DECIDER = {"coordinator_arbitrates": "coordinator",
           "human_escalation": "approver",
           "first_claim_wins": None}


def decider_for(policy: str):
    return DECIDER.get(policy)


def approvers(sess: dict) -> list:
    """Member actor ids whose role grants approval rights."""
    return [m["actor"]["id"] for m in sess["members"]
            if sess["roles"].get(m["role"], {}).get("approve")]


def can_decide(sess: dict, esc: dict, actor_id: str, role: str):
    """(ok, error) — who may decide right now."""
    policy = esc["policy"]
    if esc["state"] == "appealed":
        if actor_id not in approvers(sess):
            return False, "appeal heard by approver only"
        return True, ""
    want = decider_for(policy)
    if want is None:
        return False, "policy resolves automatically; no decision call needed"
    # The designated role decides; an approver may always step in (T8:
    # humans outrank agents on disputes). Appeal path still applies.
    if role != want and actor_id not in approvers(sess):
        return False, f"policy {policy} decides by {want}"
    return True, ""


def safe_default(esc: dict) -> dict:
    """Timeout outcome: money and claims never hang on human latency."""
    return {"outcome": "default_deny",
            "detail": f"no decision within {esc['timeout_seconds']}s; "
                      f"spend denied, claims stand, refs released: {esc['refs']}"}


def auto_resolve(sess: dict, esc: dict):
    """first_claim_wins: earliest claim timestamp wins, cites evidence."""
    if esc["kind"] != "claim" or not esc["refs"]:
        return {"outcome": "default_deny", "detail": "nothing to auto-resolve"}
    sub = esc["refs"][0]
    claim = sess.get("claims", {}).get(sub)
    if not claim:
        return {"outcome": "released", "detail": f"no live claim on {sub}"}
    by = claim["by"] if isinstance(claim, dict) else claim
    at = claim.get("at", "?") if isinstance(claim, dict) else "?"
    return {"outcome": "upheld", "winner": by,
            "detail": f"first claim wins: {by} at {at}"}
