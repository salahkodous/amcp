"""Dispute lifecycle evaluator (spec/disputes.md §5).
Pure helpers over dispute dicts — identical in reference and production.
Storage, clocks (lazy: evaluated on touch, no background timers), and
enforcement hooks live with the caller. Escalation uses the same lazy
pattern as reference/escalation.py.
"""

ANSWER_DEFAULT_SECONDS = 72 * 3600
APPEAL_DEFAULT_SECONDS = 168 * 3600

KINDS = ("non_delivery", "partial_delivery", "wrong_output", "late_delivery",
         "unauthorized_delegation", "evidence_forged", "double_commit")
REMEDIES = ("refund_full", "refund_partial", "redo", "split",
            "concede", "escalate")
TIERS = ("respondent", "arbiter", "principal")
TERMINAL = ("resolved", "withdrawn")
OUTCOMES = ("conceded", "upheld", "rejected", "split")


def open_key(subject: dict, kind: str) -> tuple:
    return (subject.get("kind"), subject.get("ref"), kind)


def touch(d: dict, now: float, now_iso: str):
    """Lazy clock: expiry escalates, appeal windows close. Idempotent —
    calling twice changes nothing the second time."""
    if d["state"] == "filed" and now >= d["answer_by"]:
        d["state"] = "adjudicating"
        d["tier"] = "arbiter"
        d["history"].append({"at": now_iso, "kind": "expired_to_adjudication",
                             "detail": "respondent silent past answer_by"})
    if d["state"] == "decided" and d.get("appeal_until") is not None \
            and now >= d["appeal_until"]:
        d["state"] = "resolved"
        d["history"].append({"at": now_iso, "kind": "finalized",
                             "detail": "appeal window lapsed"})


def can_respond(d: dict) -> tuple:
    if d["state"] in TERMINAL:
        return False, "dispute is closed"
    if d["state"] == "decided":
        return False, "dispute is decided; appeal instead"
    return True, ""


def can_adjudicate(d: dict) -> tuple:
    if d["state"] in TERMINAL:
        return False, "dispute is closed"
    if d["state"] == "decided":
        return False, "already decided; appeal instead"
    return True, ""


def can_appeal(d: dict, now: float) -> tuple:
    if d["state"] != "decided":
        return False, "only decided disputes can be appealed"
    if d.get("appeals", 0) >= 1:
        return False, "one appeal only; decision is final"
    if d.get("appeal_until") is not None and now >= d["appeal_until"]:
        return False, "appeal window lapsed"
    return True, ""
