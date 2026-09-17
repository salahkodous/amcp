/** Shared HTTP core: one fetch wrapper, typed errors, no retries-by-default
 * (retries key off `retryable`, decided by callers, never sniffed). */

import { AmcpError } from "./errors.js";

export interface ClientOptions {
  baseUrl: string;
  fetchFn?: typeof fetch;
  headers?: Record<string, string>;
}

export class AmcpClient {
  protected baseUrl: string;
  protected fetchFn: typeof fetch;
  protected headers: Record<string, string>;

  constructor(opts: ClientOptions) {
    this.baseUrl = opts.baseUrl.replace(/\/$/, "");
    this.fetchFn = opts.fetchFn ?? fetch;
    this.headers = opts.headers ?? {};
  }

  protected url(path: string): string {
    return this.baseUrl + path;
  }

  protected async req<T>(method: string, path: string, body?: unknown, extraHeaders?: Record<string, string>): Promise<{ body: T; headers: Headers }> {
    // Never call fetch as a method (this.fetchFn(...)): the Workers runtime
    // brand-checks fetch and throws "Illegal invocation" — green in Node,
    // dead at the edge. Destructure first so the receiver is undefined.
    const { fetchFn } = this;
    const resp = await fetchFn(this.url(path), {
      method,
      headers: { "Content-Type": "application/json", ...this.headers, ...extraHeaders },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const text = await resp.text();
    const parsed = text ? (JSON.parse(text) as T) : ({} as T);
    if (!resp.ok) {
      const err = parsed as unknown as { error?: { code: string; message: string; retryable: boolean; doc: string } };
      if (err?.error) throw new AmcpError(resp.status, { error: err.error });
      throw new AmcpError(resp.status, {
        error: { code: "transport_error", message: `HTTP ${resp.status}`, retryable: resp.status >= 500, doc: "" },
      });
    }
    return { body: parsed, headers: resp.headers };
  }

  protected async get<T>(path: string, headers?: Record<string, string>): Promise<T> {
    return (await this.req<T>("GET", path, undefined, headers)).body;
  }

  protected async post<T>(path: string, body?: unknown, headers?: Record<string, string>): Promise<T> {
    return (await this.req<T>("POST", path, body, headers)).body;
  }
}
