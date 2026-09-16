"""Signing interface. Production MUST use Ed25519 (see Ed25519Signer, requires
`pynacl`). DevSigner (HMAC-SHA256) exists only so the reference runs on stdlib;
receipts it mints verify offline ONLY with the shared dev secret and MUST be
rejected by conformance L4 checks against real agents."""

import hashlib
import hmac
import json


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


class DevSigner:
    """DEV ONLY. Symmetric stand-in for Ed25519. Never accept in production."""

    alg = "hmac-sha256-dev"

    def __init__(self, secret: bytes, key_id: str = "dev-hmac"):
        self._secret = secret
        self.key_id = key_id
        self.pub_hex = None  # symmetric: no public half; undiscoverable by design

    def sign(self, obj) -> dict:
        return {"key_id": self.key_id, "alg": self.alg,
                "sig": "hmac-dev:" + hmac.new(self._secret, canonical(obj), hashlib.sha256).hexdigest()}

    def verify(self, obj, envelope: dict) -> bool:
        if not isinstance(envelope, dict) or envelope.get("alg") != self.alg:
            return False
        want = self.sign(obj)["sig"]
        got = envelope.get("sig", "")
        if len(want) != len(got):
            return False
        return hmac.compare_digest(want, got)


class Ed25519Signer:
    """Production signer. Requires `pip install pynacl`."""

    alg = "ed25519"

    def __init__(self, seed: bytes):
        try:
            from nacl.signing import SigningKey
        except ImportError as e:
            raise RuntimeError("Ed25519Signer needs pynacl: pip install pynacl") from e
        if len(seed) != 32:
            raise ValueError("Ed25519 seed must be 32 bytes")
        self._key = SigningKey(seed)
        self.pub_hex = self._key.verify_key.encode().hex()
        self.key_id = "ed25519:" + self.pub_hex[:16]

    def sign(self, obj) -> dict:
        return {"key_id": self.key_id, "alg": self.alg,
                "sig": "ed25519:" + self._key.sign(canonical(obj)).signature.hex()}

    def verify(self, obj, envelope: dict) -> bool:
        if not isinstance(envelope, dict) or envelope.get("alg") != self.alg:
            return False
        return verify_ed25519(self.pub_hex, obj, envelope.get("sig", ""))


def verify_ed25519(pub_hex: str, obj, sig: str) -> bool:
    """Verify a detached Ed25519 signature over canonical JSON. Unknown
    shapes fail closed (False, never raise on attacker input)."""
    try:
        from nacl.signing import VerifyKey
        from nacl.exceptions import BadSignatureError
    except ImportError:
        return False
    try:
        if not sig.startswith("ed25519:"):
            return False
        VerifyKey(bytes.fromhex(pub_hex)).verify(
            canonical(obj), bytes.fromhex(sig[len("ed25519:"):]))
        return True
    except Exception:  # noqa: BLE001 — any failure is "invalid"
        return False


# Fixed conformance vector: seed = sha256("amcp-test-vector-1"),
# message = {"test": "vector"}. Pins the canonicalization + signature bytes.
TEST_VECTOR = {
    "seed_hex": "cd193366b40bf529dab4a29ceb2db2d4d536ab0027e6ded8b9ae409ad15b614e",
    "pub_hex": "31ecd65016de3153d691f9bf59ef7fbc28dd62766288739e87593a2a0ab14795",
    "message": {"test": "vector"},
    "sig": "ed25519:2151eb4dd48ab817ae7cf3960bf43b5646a704819ced3c7f609caa1584c1107c7dd89a9b9a7caa9f55c123b795168d6176dce9b45191a756fab75899b5932f05",
}
