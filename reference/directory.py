"""Reference directory: submit → verify → index → search.

Stdlib-only. Semantic matching is TF-IDF + cosine over capability text
(production: embeddings + LLM re-rank; same API, same explanation shape).
Reputation consumes settlement-backed receipts + trial history; strangers
with probes outrank strangers with prose.

Endpoints (mounted under the same demo server):
  POST /amcp/directory/submit   {descriptor} -> {listed, verification}
  POST /amcp/directory/evidence {agent_id, kind, ref, outcome} -> {recorded}
  GET  /amcp/directory/search?q=&domain=&capability=&max_price_usdc=
       &min_acceptance=&limit=&cursor= -> {data[{descriptor, match_explanation}], pagination}
"""

import hashlib
import json
import math
import re
import time
import urllib.request
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9]{2,}")


def tokenize(text: str):
    return TOKEN_RE.findall(str(text).lower())


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Directory:
    def __init__(self):
        self.agents = {}    # agent_id -> record
        self.evidence = {}  # agent_id -> [evidence dicts]

    # -- submit ------------------------------------------------------
    def submit(self, descriptor: dict, check_liveness: bool = False):
        errs = self._validate_shape(descriptor)
        if errs:
            return 422, {"error": {"code": "artifact_rejected", "message": "; ".join(errs),
                                   "retryable": False, "doc": "https://amcp.dev/spec/wire#error-codes"}}
        aid = descriptor["id"]
        if check_liveness:
            if not self._liveness_probe(descriptor):
                return 422, {"error": {"code": "artifact_rejected",
                                       "message": "liveness probe failed: descriptor endpoint unreachable",
                                       "retryable": True, "doc": "https://amcp.dev/spec/wire#error-codes"}}
            verification = "platform_verified"
        else:
            verification = descriptor.get("verification", "self_asserted")
        doc_hash = sha256_hex(json.dumps(descriptor, sort_keys=True).encode())
        self.agents[aid] = {"descriptor": descriptor, "doc_hash": doc_hash,
                            "verification": verification, "indexed_at": now_iso()}
        self._reindex()
        return 201, {"listed": aid, "verification": verification, "doc_hash": doc_hash}

    def _validate_shape(self, d: dict):
        errs = []
        for f in ("amcp_version", "id", "name", "description", "version", "capabilities"):
            if f not in d:
                errs.append(f"missing {f}")
        for c in d.get("capabilities", []) if isinstance(d.get("capabilities"), list) else []:
            for f in ("name", "kind", "description", "input_schema", "output_schema", "authorization"):
                if f not in c:
                    errs.append(f"capability missing {f}")
        return errs

    def _liveness_probe(self, descriptor: dict, timeout: int = 5) -> bool:
        """Fetch the descriptor's own id-derived health endpoint. Demo: the
        agent must serve GET /amcp and return the same id (challenge-response
        against impersonation-by-copy)."""
        for uri in (descriptor.get("agent_card_uri"),):
            _ = uri  # reserved: well-known cross-checks
        base = (descriptor.get("reputation") or {}).get("receipts_uri", "")
        root = base.split("/amcp/")[0] if "/amcp/" in base else ""
        if not root:
            return False
        try:
            with urllib.request.urlopen(root + "/amcp", timeout=timeout) as r:
                doc = json.loads(r.read() or b"{}")
            return doc.get("id") == descriptor["id"]
        except Exception:  # noqa: BLE001 — any failure = not live
            return False

    # -- evidence ----------------------------------------------------
    def record_evidence(self, agent_id: str, kind: str, ref: str, outcome: str,
                          weight_basis: str = "settlement", reviewer: str = ""):
        if agent_id not in self.agents:
            return 404, {"error": {"code": "unknown_agent", "message": agent_id,
                                   "retryable": False, "doc": "https://amcp.dev/spec/wire#error-codes"}}
        if kind not in ("receipt", "feedback", "validation", "revocation", "trial"):
            return 422, {"error": {"code": "bad_request", "message": f"unknown evidence kind: {kind}",
                                   "retryable": False, "doc": "https://amcp.dev/spec/wire#error-codes"}}
        ev = {"kind": kind, "ref": ref, "outcome": outcome,
              "weight_basis": weight_basis, "reviewer": reviewer or None,
              "ts": now_iso()}
        self.evidence.setdefault(agent_id, []).append(ev)
        return 201, {"recorded": True, "evidence": ev}

    def reputation(self, agent_id: str):
        evs = self.evidence.get(agent_id, [])
        receipts = [e for e in evs if e["kind"] == "receipt" and e["weight_basis"] == "settlement"]
        trials = [e for e in evs if e["kind"] == "trial"]
        accepted = sum(1 for e in receipts if e["outcome"] == "accepted")
        total = len(receipts)
        return {"receipts": total,
                "acceptance": (accepted / total) if total else None,
                "trials_passed": sum(1 for e in trials if e["outcome"] == "accepted"),
                "disputes_lost": sum(1 for e in evs if e["outcome"] in ("disputed_lost",))}

    # -- reputation v1 (spec/reputation.md) ------------------------------
    # Formalized inputs with pinned weights; reviewer graphs logged;
    # clustering signals computed, reported, weight ZERO.
    SCORE_VERSION = "reputation-v1"
    SCORE_WEIGHTS = {"settlement": 0.40, "trials": 0.20, "feedback": 0.15,
                     "validation": 0.15, "reliability": 0.10}

    @staticmethod
    def _ratio(items, pred):
        items = list(items)
        if not items:
            return None
        return sum(1 for e in items if pred(e)) / len(items)

    def score(self, agent_id: str):
        if agent_id not in self.agents:
            return None
        evs = self.evidence.get(agent_id, [])
        by_kind = {}
        for e in evs:
            by_kind.setdefault(e["kind"], []).append(e)
        accepted = lambda e: e["outcome"] == "accepted"  # noqa: E731
        scores = {
            "settlement": self._ratio(
                [e for e in by_kind.get("receipt", []) if e["weight_basis"] == "settlement"], accepted),
            "trials": (lambda n: min(1.0, n / 5) if evs else None)(
                sum(1 for e in by_kind.get("trial", []) if e["outcome"] == "accepted")),
            "feedback": self._ratio(by_kind.get("feedback", []), accepted),
            "validation": self._ratio(by_kind.get("validation", []), accepted),
            "reliability": (lambda r, t: 1 - r / (t + 1) if evs else None)(
                sum(1 for e in evs if e["kind"] == "revocation"), len(evs)),
        }
        present = {k: v for k, v in scores.items() if v is not None}
        composite = (sum(v * self.SCORE_WEIGHTS[k] for k, v in present.items())
                     / sum(self.SCORE_WEIGHTS[k] for k in present)) if present else None
        # Reviewer graph: logged, not judged. reviewer -> agents reviewed.
        reviewers: dict = {}
        for aid, items in self.evidence.items():
            for e in items:
                if e.get("reviewer"):
                    reviewers.setdefault(e["reviewer"], set()).add(aid)
        mine = {r for r, agents in reviewers.items() if agent_id in agents}
        overlap = sum(len(reviewers[r]) - 1 for r in mine)
        experimental = {
            "weight": 0,
            "unique_reviewers": len(mine),
            "reviewer_overlap": overlap,
            "burst_windows": self._burst_windows(
                [e for e in evs if e.get("reviewer")]),
        }
        return {"agent_id": agent_id, "version": self.SCORE_VERSION,
                "scores": scores, "composite": composite,
                "experimental": experimental}

    @staticmethod
    def _burst_windows(evs):
        # 1-hour windows with >=3 items from one reviewer.
        from datetime import datetime, timedelta, timezone
        by_reviewer: dict = {}
        for e in evs:
            try:
                ts = datetime.fromisoformat(e["ts"].replace("Z", "+00:00"))
            except (ValueError, KeyError):
                continue
            by_reviewer.setdefault(e["reviewer"], []).append(ts)
        bursts = 0
        for stamps in by_reviewer.values():
            stamps.sort()
            for i, t0 in enumerate(stamps):
                if sum(1 for t in stamps[i:] if t - t0 <= timedelta(hours=1)) >= 3:
                    bursts += 1
                    break
        return bursts

    # -- index + search ----------------------------------------------
    def _reindex(self):
        docs = {}
        for aid, rec in self.agents.items():
            text = " ".join([rec["descriptor"].get("description", "")]
                            + [c.get("name", "") + " " + c.get("description", "")
                               for c in rec["descriptor"].get("capabilities", [])])
            docs[aid] = Counter(tokenize(text))
        df = Counter()
        for terms in docs.values():
            for t in terms:
                df[t] += 1
        n = max(1, len(docs))
        self._tfidf = {aid: {t: (1 + math.log(c)) * math.log(n / df[t])
                             for t, c in terms.items()} for aid, terms in docs.items()}

    @staticmethod
    def _cosine(a: dict, b: dict) -> float:
        dot = sum(a.get(t, 0.0) * w for t, w in b.items())
        na = math.sqrt(sum(v * v for v in a.values())) or 1.0
        nb = math.sqrt(sum(v * v for v in b.values())) or 1.0
        return dot / (na * nb)

    def search(self, q="", domain=None, capability=None, max_price_usdc=None,
               min_acceptance=None, limit=20, cursor=None):
        limit = max(1, min(100, limit))
        qvec = Counter(tokenize(q)) if q else {}
        qtfidf = ({t: (1 + math.log(c)) for t, c in qvec.items()}) if qvec else {}
        hits = []
        for aid, rec in self.agents.items():
            d = rec["descriptor"]
            if domain and domain not in d.get("domain", []):
                continue
            caps = d.get("capabilities", [])
            if capability and not any(c.get("name") == capability for c in caps):
                continue
            prices = [float(c["pricing"]["amount_usdc"]) for c in caps
                      if c.get("pricing", {}).get("amount_usdc")]
            if max_price_usdc is not None and prices and min(prices) > float(max_price_usdc):
                continue
            rep = self.reputation(aid)
            if min_acceptance is not None and (rep["acceptance"] is None or rep["acceptance"] < float(min_acceptance)):
                continue
            qtokens = set(tokenize(q)) if q else set()
            matched = [c["name"] for c in caps
                       if not q or qtokens & set(tokenize(c.get("name", "") + " " + c.get("description", "")))] or ([] if q else [c["name"] for c in caps])
            sim = self._cosine(qtfidf, self._tfidf.get(aid, {})) if qvec else 0.0
            # Trial history outranks prose for strangers: cheap trustworthy signal.
            trust_boost = min(0.3, 0.05 * rep["trials_passed"]) + (0.1 if rep["receipts"] else 0.0)
            score = (0.7 * sim if qvec else 0.0) + trust_boost
            hits.append((score, sim, aid, matched, rep))
        hits.sort(reverse=True)
        if cursor:
            try:
                off = int(cursor)
            except ValueError:
                off = 0
        else:
            off = 0
        page = hits[off:off + limit]
        data = [{"descriptor": self.agents[aid]["descriptor"],
                 "verification": self.agents[aid]["verification"],
                 "match_explanation": {
                     "matched_capabilities": matched,
                     "similarity_band": ("high" if sim >= 0.5 else "medium" if sim >= 0.15 else "low"),
                     "reputation": rep}}
                for score, sim, aid, matched, rep in page]
        nxt = str(off + limit) if off + limit < len(hits) else None
        return {"data": data, "pagination": {"next_cursor": nxt, "has_more": nxt is not None}}
