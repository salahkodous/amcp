/** Verification client: run acceptance against the reference verifier.
 * Thin transport only — verdict semantics live in spec/verification.md and
 * are proven by conformance/fixtures/verification.json. */

import { AmcpClient } from "./client.js";

export interface VerifyInput {
  capability: string;
  inputs: Record<string, unknown>;
  artifact: { data: unknown };
  criteria?: Record<string, unknown>;
  criteria_committed?: boolean;
}

export interface VerifyCheck {
  name: string;
  pass: boolean;
  detail: string;
}

export interface Verdict {
  verdict: "accepted" | "rejected";
  checks: VerifyCheck[];
  artifact_hash: string;
  criteria_hash: string | null;
  criteria_committed: boolean;
  verifier: string;
  verified_at: string;
}

export class VerifyClient extends AmcpClient {
  run(input: VerifyInput): Promise<Verdict> {
    return this.post("/amcp/verify", input);
  }
}
