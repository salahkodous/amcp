/** Dispute client: file, evidence, respond, adjudicate, appeal, withdraw, read.
 * Thin transport only — the state machine lives in spec/disputes.md and is
 * proven by conformance/fixtures/dispute*.json. */

import { AmcpClient } from "./client.js";
import type { Dispute } from "./types.js";

export interface FileClaimInput {
  claimant: string;
  respondent: string;
  subject: { kind: "receipt" | "session"; ref: string };
  kind: string;
  remedy: string;
  detail?: string;
  timeout_seconds?: number;
}

export class DisputeClient extends AmcpClient {
  file(input: FileClaimInput): Promise<{ dispute_id: string; state: string; tier: string; answer_by: string }> {
    return this.post("/amcp/disputes", input);
  }

  read(id: string): Promise<{ dispute_id: string; state: string; dispute: Dispute }> {
    return this.get(`/amcp/disputes/${encodeURIComponent(id)}`);
  }

  evidence(id: string, ref: string, opts: { hash?: string; uri?: string; kind?: string; actor?: string } = {}): Promise<{ state: string; evidence: number }> {
    return this.post(`/amcp/disputes/${encodeURIComponent(id)}/evidence`, { ref, ...opts });
  }

  respond(id: string, actor: string, verdict: string, note?: string): Promise<{ state: string; outcome: string | null }> {
    return this.post(`/amcp/disputes/${encodeURIComponent(id)}/respond`, { actor, verdict, note });
  }

  adjudicate(id: string, arbiter: string, outcome: string, remedy: string,
    opts: { rationale?: string; amount_usdc?: string; appeal_seconds?: number } = {},
  ): Promise<{ state: string }> {
    return this.post(`/amcp/disputes/${encodeURIComponent(id)}/adjudicate`, { arbiter, outcome, remedy, ...opts });
  }

  appeal(id: string, actor: string, grounds?: string): Promise<{ state: string; tier: string }> {
    return this.post(`/amcp/disputes/${encodeURIComponent(id)}/appeal`, { actor, grounds });
  }

  withdraw(id: string, actor: string): Promise<{ state: string }> {
    return this.post(`/amcp/disputes/${encodeURIComponent(id)}/withdraw`, { actor });
  }
}
