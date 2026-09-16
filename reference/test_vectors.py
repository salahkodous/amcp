"""Money vectors: conformance/vectors/money.json enforced on the reference.
Run:  python reference/test_vectors.py
"""

import json
import sys
from decimal import Decimal

sys.path.insert(0, ".")
from reference.agent import _amt  # noqa: E402

PASS, FAIL = 0, 0
vec = json.load(open("conformance/vectors/money.json"))


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL {name} {detail}")


def dec_scale(d: Decimal) -> int:
    return max(0, -d.as_tuple().exponent)


for c in vec["cases"]:
    try:
        v = _amt(c["amount"])
        assert v == Decimal(c["micro"]) / 1_000_000, (v, c)
        assert dec_scale(v) == c["scale"], (dec_scale(v), c)
        assert str(v) == c["print"], (str(v), c)
        PASS += 1
    except AssertionError as e:
        check(f"case {c['amount']}", False, str(e)[:120])

for s in vec["sequences"]:
    total = Decimal(s["start"])
    for a in s["adds"]:
        total += Decimal(a)
    if str(total) == s["spent"]:
        PASS += 1
    else:
        check(f"sequence {s}", False, f"{total} != {s['spent']}")

for bad in vec["invalid"]:
    try:
        _amt(bad)
        check(f"invalid {bad!r}", False, "accepted")
    except ValueError:
        PASS += 1

print(f"{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
