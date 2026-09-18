/** Intents client: publish demand, browse, quote, accept, withdraw.
 * Thin transport only — lifecycle lives in spec/intents.md and is proven
 * by conformance/fixtures/intents.json. The directory matches; it never
 * transacts (acceptance returns a selection the parties sign elsewhere). */

import { AmcpClient } from "./client.js";

export interface PublishIntentInput {
  principal: string;
  action: string;
  description?: string;
  constraints?: {
    max_price_usdc?: string;
    capabilities?: string[];
    domains?: string[];
    regions?: string[];
  };
  expires_in_seconds?: number;
}

export interface IntentSummary {
  intent_id: string;
  principal: string;
  action: string;
  state: string;
  quote_count: number;
  max_price_usdc: string | null;
  expires_at: string;
}

export class IntentsClient extends AmcpClient {
  publish(input: PublishIntentInput): Promise<{ intent_id: string; state: string; expires_at: string }> {
    return this.post("/amcp/directory/intents", input);
  }

  list(filters: { capability?: string; max_price_usdc?: string; limit?: number } = {}): Promise<{
    data: IntentSummary[]; pagination: { next_cursor: string | null; has_more: boolean };
  }> {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(filters)) if (v !== undefined) q.set(k, String(v));
    return this.get(`/amcp/directory/intents?${q}`);
  }

  read(id: string): Promise<{ intent_id: string; state: string }> {
    return this.get(`/amcp/directory/intents/${encodeURIComponent(id)}`);
  }

  quote(id: string, agent_id: string, price_usdc: string,
    opts: { terms?: string; expires_in_seconds?: number } = {},
  ): Promise<{ state: string; quote_count: number }> {
    return this.post(`/amcp/directory/intents/${encodeURIComponent(id)}/quotes`,
      { agent_id, price_usdc, ...opts });
  }

  accept(id: string, actor: string, agent_id: string): Promise<{ state: string }> {
    return this.post(`/amcp/directory/intents/${encodeURIComponent(id)}/accept`, { actor, agent_id });
  }

  withdraw(id: string, actor: string): Promise<{ state: string }> {
    return this.post(`/amcp/directory/intents/${encodeURIComponent(id)}/withdraw`, { actor });
  }
}
