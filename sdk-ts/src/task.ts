/** Task execution client (L2): idempotent task calls + receipt listing. */

import { AmcpClient } from "./client.js";
import type { Page, Receipt } from "./types.js";

export interface TaskResult {
  task: { task_id: string; capability: string; state: string };
  artifact: Record<string, unknown>;
  receipt: Receipt;
  replayed: boolean;
}

export class TaskClient extends AmcpClient {
  async run(capability: string, inputs: Record<string, unknown>, opts?: {
    idempotencyKey?: string; trial?: boolean; price_usdc?: string;
    contract_id?: string; session_id?: string; payer?: string;
  }): Promise<TaskResult> {
    const headers = opts?.idempotencyKey ? { "Idempotency-Key": opts.idempotencyKey } : undefined;
    const { body, headers: rh } = await this.req<TaskResult>("POST", "/amcp/task", {
      capability, inputs,
      ...(opts?.trial !== undefined ? { trial: opts.trial } : {}),
      ...(opts?.price_usdc !== undefined ? { price_usdc: opts.price_usdc } : {}),
      ...(opts?.contract_id !== undefined ? { contract_id: opts.contract_id } : {}),
      ...(opts?.session_id !== undefined ? { session_id: opts.session_id } : {}),
      ...(opts?.payer !== undefined ? { payer: opts.payer } : {}),
    }, headers);
    return { ...body, replayed: rh.get("X-Idempotent-Replayed") === "true" };
  }

  receipts(limit = 20): Promise<Page<Receipt>> {
    return this.get<Page<Receipt>>(`/amcp/receipts?limit=${limit}`);
  }
}
