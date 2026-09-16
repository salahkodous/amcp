/** Directory client: submit, evidence, typed search. */

import { AmcpClient } from "./client.js";
import type { Descriptor, DirectoryHit, Page } from "./types.js";

export interface SearchFilters {
  q?: string;
  domain?: string;
  capability?: string;
  max_price_usdc?: string;
  min_acceptance?: string;
  limit?: number;
  cursor?: string;
}

export class DirectoryClient extends AmcpClient {
  submit(descriptor: Descriptor, check_liveness = false): Promise<{ listed: string; verification: string; doc_hash: string }> {
    return this.post("/amcp/directory/submit", { descriptor, check_liveness });
  }

  evidence(agent_id: string, kind: string, ref: string, outcome: string): Promise<{ recorded: boolean }> {
    return this.post("/amcp/directory/evidence", { agent_id, kind, ref, outcome });
  }

  search(f: SearchFilters = {}): Promise<Page<DirectoryHit>> {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(f)) if (v !== undefined) q.set(k, String(v));
    return this.get<Page<DirectoryHit>>(`/amcp/directory/search?${q}`);
  }
}
