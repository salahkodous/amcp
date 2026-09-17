/** Edge-runtime fetch semantics: the Workers runtime brand-checks fetch and
 * throws "Illegal invocation" when it is called as a method. Node allows
 * method calls, so without this test the SDK is green locally and dead at
 * the edge. No server needed — pure client behavior. */
import { describe, expect, it } from "vitest";
import { AmcpClient } from "../src/client.js";

function strictFetch(this: unknown): Promise<Response> {
  if (this !== undefined) throw new TypeError("Illegal invocation");
  return Promise.resolve(new Response(JSON.stringify({ ok: true }), {
    status: 200, headers: { "content-type": "application/json" },
  }));
}

class ProbeClient extends AmcpClient {
  probe(): Promise<{ ok: boolean }> {
    return this.get("/probe");
  }
}

describe("edge fetch receiver rule", () => {
  it("never method-calls the injected fetch", async () => {
    const client = new ProbeClient({
      baseUrl: "https://edge.test",
      fetchFn: strictFetch as typeof fetch,
    });
    await expect(client.probe()).resolves.toEqual({ ok: true });
  });
});
