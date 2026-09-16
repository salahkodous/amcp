/** Fixture conformance: replays every conformance/fixtures/*.json against a
 * live Python reference (spawned here). Any failure = wire drift. */
import { spawn, ChildProcess } from "node:child_process";
import { readdirSync, readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { beforeAll, afterAll, describe, it, expect } from "vitest";
import { replayFile } from "../src/replay.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const PORT = 8488;
const BASE = `http://127.0.0.1:${PORT}`;
let server: ChildProcess;

const waitFor = async (fn: () => Promise<boolean>, ms = 10000) => {
  const t0 = Date.now();
  for (;;) {
    try { if (await fn()) return; } catch { /* retry */ }
    if (Date.now() - t0 > ms) throw new Error("server never came up");
    await new Promise((r) => setTimeout(r, 200));
  }
};

beforeAll(async () => {
  server = spawn("python", ["-m", "reference.agent", "--port", String(PORT)], {
    cwd: ROOT, stdio: "ignore",
  });
  await waitFor(async () => (await fetch(`${BASE}/amcp/health`).then((r) => r.ok).catch(() => false)));
}, 30000);

afterAll(() => { server?.kill(); });

const files = readdirSync(join(ROOT, "conformance", "fixtures")).filter((f) => f.endsWith(".json"));

describe.each(files)("%s", (file) => {
  it("replays green", async () => {
    const spec = JSON.parse(readFileSync(join(ROOT, "conformance", "fixtures", file), "utf8"));
    const results = await replayFile(BASE, spec);
    const bad = results.filter((r) => !r.ok);
    expect(bad.map((r) => `${r.name}: ${r.fails.join("; ")}`)).toEqual([]);
    expect(results.length).toBeGreaterThan(0);
  });
});
