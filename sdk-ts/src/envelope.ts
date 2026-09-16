/** Canonical JSON + Ed25519 verification. WebCrypto-only: runs on Node 20+
 * and Cloudflare Workers with zero dependencies. */

export function canonicalJson(obj: unknown): string {
  // JSON.stringify with sorted keys and no whitespace — byte-identical to
  // the Python reference canonical() for JSON-native values.
  if (obj === null || typeof obj !== "object") return JSON.stringify(obj);
  if (Array.isArray(obj)) return `[${obj.map(canonicalJson).join(",")}]`;
  const keys = Object.keys(obj).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${canonicalJson((obj as Record<string, unknown>)[k])}`).join(",")}}`;
}

function hexToBytes(hex: string): Uint8Array {
  if (!/^[0-9a-fA-F]*$/.test(hex) || hex.length % 2 !== 0) throw new Error("bad hex");
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  return out;
}

const subtle = (): SubtleCrypto => {
  const s = globalThis.crypto?.subtle;
  if (!s) throw new Error("WebCrypto unavailable — needs Node 20+ or Workers runtime");
  return s;
};

/** Verify a detached Ed25519 signature over canonical JSON. Fail closed. */
export async function verifyEd25519(pubHex: string, obj: unknown, sig: string): Promise<boolean> {
  try {
    if (!sig.startsWith("ed25519:")) return false;
    const key = await subtle().importKey(
      "raw", hexToBytes(pubHex).buffer as ArrayBuffer, { name: "Ed25519" }, false, ["verify"]);
    return await subtle().verify(
      { name: "Ed25519" }, key,
      hexToBytes(sig.slice("ed25519:".length)).buffer as ArrayBuffer,
      new TextEncoder().encode(canonicalJson(obj)));
  } catch {
    return false;
  }
}

/** Fixed conformance vector (mirrors reference/signer.py TEST_VECTOR). */
export const TEST_VECTOR = {
  pubHex: "31ecd65016de3153d691f9bf59ef7fbc28dd62766288739e87593a2a0ab14795",
  message: { test: "vector" },
  sig: "ed25519:2151eb4dd48ab817ae7cf3960bf43b5646a704819ced3c7f609caa1584c1107c7dd89a9b9a7caa9f55c123b795168d6176dce9b45191a756fab75899b5932f05",
};
