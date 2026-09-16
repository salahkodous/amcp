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

    def __init__(self, secret: bytes, key_id: str = "dev-hmac"):
        self._secret = secret
        self.key_id = key_id

    def sign(self, obj) -> str:
        return "hmac:" + hmac.new(self._secret, canonical(obj), hashlib.sha256).hexdigest()

    def verify(self, obj, signature: str) -> bool:
        want = self.sign(obj)
        if len(want) != len(signature):
            return False
        return hmac.compare_digest(want, signature)


class Ed25519Signer:
    """Production signer. Requires `pip install pynacl`."""

    def __init__(self, seed: bytes):
        try:
            from nacl.signing import SigningKey
        except ImportError as e:
            raise RuntimeError("Ed25519Signer needs pynacl: pip install pynacl") from e
        self._key = SigningKey(seed)
        self.key_id = "ed25519:" + self._key.verify_key.encode().hex()[:16]

    def sign(self, obj) -> str:
        return "ed25519:" + self._key.sign(canonical(obj)).signature.hex()
