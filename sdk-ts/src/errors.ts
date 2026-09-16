/** Wire error taxonomy — one shape for every code in spec/wire.md. */

export interface WireErrorBody {
  error: { code: string; message: string; retryable: boolean; doc: string };
}

export class AmcpError extends Error {
  readonly code: string;
  readonly status: number;
  readonly retryable: boolean;
  readonly doc: string;

  constructor(status: number, body: WireErrorBody) {
    super(`[${status}/${body.error.code}] ${body.error.message}`);
    this.name = "AmcpError";
    this.code = body.error.code;
    this.status = status;
    this.retryable = body.error.retryable;
    this.doc = body.error.doc;
  }

  is(code: string): boolean {
    return this.code === code;
  }
}
