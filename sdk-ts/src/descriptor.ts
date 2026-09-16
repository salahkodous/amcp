/** Descriptor serving + offline receipt verification. */

import { AmcpClient } from "./client.js";
import { verifyEd25519 } from "./envelope.js";
import type { AdvertisedKey, AmcpVersion, Descriptor, Receipt } from "./types.js";

export class IdentityClient extends AmcpClient {
  descriptor(): Promise<Descriptor> {
    return this.get<Descriptor>("/amcp");
  }

  keys(): Promise<{ keys: AdvertisedKey[]; active: string }> {
    return this.get("/amcp/keys");
  }

  /** Verify a receipt's platform signature against an advertised key.
   * Fully offline — no host callback. Unknown alg fails closed. */
  async verifyReceipt(receipt: Receipt, pubHex: string): Promise<boolean> {
    const env = receipt.signatures?.platform;
    if (!env || env.alg !== "ed25519") return false;
    const { signatures: _drop, ...body } = receipt;
    return verifyEd25519(pubHex, body, env.sig);
  }

  /** Convenience: fetch keys, verify receipt against the matching key id. */
  async verifyReceiptViaDirectory(receipt: Receipt): Promise<boolean> {
    const env = receipt.signatures?.platform;
    if (!env) return false;
    const { keys } = await this.keys();
    const key = keys.find((k) => k.id === env.key_id);
    if (!key?.pub) return false; // dev keys are undiscoverable by design
    return this.verifyReceipt(receipt, key.pub);
  }
}

/** Minimal descriptor builder — fills protocol defaults, callers own content. */
export function defineDescriptor(
  input: Omit<Descriptor, "amcp_version"> & { amcp_version?: AmcpVersion },
): Descriptor {
  // Cast: Omit<> collapses over Descriptor's index signature, but the
  // runtime shape is exactly Descriptor (callers supply every required key).
  return { ...input, amcp_version: input.amcp_version ?? "0.1" } as Descriptor;
}
