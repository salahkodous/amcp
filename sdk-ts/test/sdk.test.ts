/** SDK behavior beyond fixtures: Ed25519 vector, offline receipt verify,
 * canonical-JSON parity with the reference, SSE stream resume. */
import { spawn, ChildProcess } from "node:child_process";
import { beforeAll, afterAll, describe, it, expect } from "vitest";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { canonicalJson, verifyEd25519, TEST_VECTOR } from "../src/envelope.js";
import { IdentityClient } from "../src/descriptor.js";
import { TaskClient } from "../src/task.js";
import { DisputeClient } from "../src/dispute.js";
import { SessionClient } from "../src/session.js";
import { AmcpError } from "../src/errors.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const PORT = 8489;
const BASE = `http://127.0.0.1:${PORT}`;
let server: ChildProcess;

beforeAll(async () => {
  server = spawn("python", ["-m", "reference.agent", "--port", String(PORT)], { cwd: ROOT, stdio: "ignore" });
  const t0 = Date.now();
  for (;;) {
    try {
      if (await fetch(`${BASE}/amcp/health`).then((r) => r.ok).catch(() => false)) return;
    } catch { /* retry */ }
    if (Date.now() - t0 > 10000) throw new Error("server never came up");
    await new Promise((r) => setTimeout(r, 200));
  }
}, 30000);

afterAll(() => { server?.kill(); });

describe("crypto", () => {
  it("fixed vector verifies", async () => {
    expect(await verifyEd25519(TEST_VECTOR.pubHex, TEST_VECTOR.message, TEST_VECTOR.sig)).toBe(true);
  });
  it("tampered message fails", async () => {
    expect(await verifyEd25519(TEST_VECTOR.pubHex, { test: "evil" }, TEST_VECTOR.sig)).toBe(false);
  });
  it("canonical JSON matches reference (sorted, tight)", () => {
    expect(canonicalJson({ b: 1, a: [3, 2], c: { z: null, y: "x" } }))
      .toBe('{"a":[3,2],"b":1,"c":{"y":"x","z":null}}');
  });
  it("live receipt verifies via advertised key", async () => {
    const id = new IdentityClient({ baseUrl: BASE });
    const tasks = new TaskClient({ baseUrl: BASE });
    const r = await tasks.run("echo", { text: "sdk" }, { idempotencyKey: "sdk-keys-001" });
    expect(await id.verifyReceiptViaDirectory(r.receipt)).toBe(true);
  });
});

describe("errors", () => {
  it("typed wire errors with codes", async () => {
    const tasks = new TaskClient({ baseUrl: BASE });
    const err = await tasks.run("nope", {}).catch((e) => e);
    expect(err).toBeInstanceOf(AmcpError);
    expect((err as AmcpError).code).toBe("unknown_capability");
    expect((err as AmcpError).is("unknown_capability")).toBe(true);
  });
});

describe("disputes", () => {
  it("file → respond → concede roundtrip through the client", async () => {
    const tasks = new TaskClient({ baseUrl: BASE });
    const disputes = new DisputeClient({ baseUrl: BASE });
    const ran = await tasks.run("echo", { text: "sdk dispute" }, { idempotencyKey: "sdk-dispute-001" });
    const filed = await disputes.file({
      claimant: "sdk:buyer", respondent: "sdk:seller",
      subject: { kind: "receipt", ref: ran.receipt.receipt_id },
      kind: "wrong_output", remedy: "redo",
    });
    expect(filed.state).toBe("filed");
    const done = await disputes.respond(filed.dispute_id, "sdk:seller", "concede");
    expect(done.state).toBe("resolved");
    const record = await disputes.read(filed.dispute_id);
    expect(record.dispute.outcome).toBe("conceded");
  });
});

describe("sessions + stream", () => {
  it("room message arrives on the stream", async () => {
    const s = new SessionClient({ baseUrl: BASE });
    const roles = {
      coordinator: { read: ["*"], write: ["plan"], message: ["*"], delegate: true, approve: false },
      worker: { read: ["brief"], write: ["findings"], message: ["room"], delegate: false, approve: false },
    };
    const { id } = await s.create({
      members: [
        { actor: { type: "agent", id: "sdk:a" }, role: "coordinator" },
        { actor: { type: "agent", id: "sdk:b" }, role: "worker" }],
      roles,
    });
    const seen: string[] = [];
    const streamP = (async () => {
      for await (const ev of s.stream(id, "sdk:b", { wait: 8 })) {
        seen.push(ev.kind);
        if (ev.kind === "message") break;
      }
    })();
    await new Promise((r) => setTimeout(r, 500));
    await s.message(id, "sdk:a", "room", [{ kind: "text", class: "content", text: "hi sdk" }]);
    await streamP;
    expect(seen).toContain("session_created");
    expect(seen).toContain("message");
  });
});
