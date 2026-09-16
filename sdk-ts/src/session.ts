/** Session client (L3): lifecycle, messaging, claims, budgets, negotiation,
 * escalation, and resumable SSE streams. */

import { AmcpClient } from "./client.js";
import type { NegotiationTerms, SessionMember } from "./types.js";

export interface RoleDef {
  read: string[];
  write: string[];
  message: string[];
  delegate: boolean;
  approve: boolean;
}

export interface SessionEvent {
  seq: number;
  ts: string;
  kind: string;
  visibility?: string[];
  [k: string]: unknown;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export class SessionClient extends AmcpClient {
  create(args: {    members: { actor: { type: string; id: string }; role: string }[];
    roles: Record<string, RoleDef>;
    blackboard?: Record<string, unknown>;
    budget?: { ceiling_usdc: string; scheme?: string };
    conflict_policy?: string;
  }): Promise<{ id: string; state: string; join: Record<string, { role: string; snapshot: Record<string, unknown> }> }> {
    return this.post("/amcp/session", args);
  }

  join(sessionId: string, actor: { type?: string; id: string }, role: string): Promise<{
    role: string; snapshot: Record<string, unknown>;
  }> {
    return this.act(sessionId, "join", { actor, role });
  }

  view(sessionId: string, actor: string): Promise<{    id: string; state: string; role: string;
    blackboard: Record<string, unknown>; budget: Record<string, string>;
    timeline: SessionEvent[];
  }> {
    return this.get(`/amcp/session/${sessionId}?actor=${encodeURIComponent(actor)}`);
  }

  private act<T>(sessionId: string, action: string, body: Record<string, unknown>): Promise<T> {
    return this.post<T>(`/amcp/session/${sessionId}/${action}`, body);
  }

  message(sessionId: string, actor: string, to: string, parts: Record<string, unknown>[]): Promise<{ delivered_to: string[] }> {
    return this.act(sessionId, "message", { actor: { id: actor }, to, parts });
  }

  claim(sessionId: string, actor: string, subtask: string): Promise<{ subtask: string; claimed_by: string }> {
    return this.act(sessionId, "claim", { actor: { id: actor }, subtask });
  }

  spend(sessionId: string, actor: string, amount_usdc: string, task_ref?: string): Promise<{ spent_usdc: string; ceiling_usdc: string }> {
    return this.act(sessionId, "spend", { actor: { id: actor }, amount_usdc, ...(task_ref ? { task_ref } : {}) });
  }

  pause(sessionId: string, actor: string) { return this.act(sessionId, "pause", { actor: { id: actor } }); }
  complete(sessionId: string, actor: string) { return this.act(sessionId, "complete", { actor: { id: actor } }); }

  negotiate(sessionId: string, body: Record<string, unknown>): Promise<Record<string, unknown> & { id: string; status: string }> {
    return this.act(sessionId, "negotiate", body);
  }

  offer(sessionId: string, actor: string, terms: NegotiationTerms, task_ref?: string) {
    return this.negotiate(sessionId, { actor: { id: actor }, op: "offer", terms, ...(task_ref ? { task_ref } : {}) });
  }

  escalate(sessionId: string, actor: string, kind: string, refs: string[] = [], timeout_seconds?: number) {
    return this.act(sessionId, "escalate", {
      actor: { id: actor }, kind, refs,
      ...(timeout_seconds !== undefined ? { timeout_seconds } : {}),
    });
  }

  decide(sessionId: string, body: Record<string, unknown>) {
    return this.act(sessionId, "decide", body);
  }

  /** Resumable event stream. Persists nothing itself — pass lastSeq back in
   * to resume; generator ends when the server closes the bounded hold. */
  async *stream(sessionId: string, actor: string, opts?: { cursor?: number; wait?: number }): AsyncGenerator<SessionEvent> {
    let cursor = opts?.cursor ?? 0;
    const wait = opts?.wait ?? 25;
    while (true) {
      const resp = await this.fetchFn(
        this.url(`/amcp/session/${sessionId}/events?actor=${encodeURIComponent(actor)}&cursor=${cursor}&wait=${wait}`),
        { headers: { Accept: "text/event-stream" } });
      if (!resp.ok || !resp.body) return;
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "", frames = 0;
      try {
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          let idx: number;
          while ((idx = buf.indexOf("\n\n")) >= 0) {
            const frame = buf.slice(0, idx);
            buf = buf.slice(idx + 2);
            const data = frame.split("\n").filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trim()).join("\n");
            if (!data || data.startsWith(":")) continue;
            const ev = JSON.parse(data) as SessionEvent;
            cursor = Math.max(cursor, ev.seq);
            frames++;
            yield ev;
          }
        }
      } finally {
        reader.releaseLock();
      }
      if (frames === 0) return; // quiet hold expired — caller resumes if needed
      await sleep(250);
    }
  }
}

export type { SessionMember };
