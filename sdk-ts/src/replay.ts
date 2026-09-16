/** Portable fixture replayer (mirrors conformance/replay.py). Any implementation
 * proves wire compatibility by replaying conformance/fixtures/*.json. */

export interface FixtureResult { name: string; ok: boolean; fails: string[] }

function getPath(obj: unknown, dotted: string): [boolean, unknown] {
  let cur: unknown = obj;
  for (const part of dotted.split(".")) {
    if (Array.isArray(cur) && /^\d+$/.test(part)) {
      const i = Number(part);
      if (i >= cur.length) return [false, undefined];
      cur = cur[i];
    } else if (cur !== null && typeof cur === "object" && part in (cur as Record<string, unknown>)) {
      cur = (cur as Record<string, unknown>)[part];
    } else return [false, undefined];
  }
  return [true, cur];
}

function sub<T>(obj: T, vars: Record<string, unknown>): T {
  if (typeof obj === "string") {
    let s: string = obj;
    for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
    return s as unknown as T;
  }
  if (Array.isArray(obj)) return obj.map((v) => sub(v, vars)) as T;
  if (obj !== null && typeof obj === "object") {
    return Object.fromEntries(Object.entries(obj).map(([k, v]) => [k, sub(v, vars)])) as T;
  }
  return obj;
}

const deepEqual = (a: unknown, b: unknown): boolean => JSON.stringify(a) === JSON.stringify(b);

export async function replayFile(baseUrl: string, spec: { version: string; fixtures: unknown[] }): Promise<FixtureResult[]> {
  if (spec.version !== "0.1") throw new Error(`unsupported fixture version ${spec.version}`);
  const vars: Record<string, unknown> = {};
  const saved: Record<string, unknown> = {};
  const out: FixtureResult[] = [];
  for (const fx of spec.fixtures as Array<Record<string, any>>) {
    const fails: string[] = [];
    try {
      const req = fx.request;
      const resp = await fetch(baseUrl + sub(req.path, vars), {
        method: req.method,
        headers: { "Content-Type": "application/json", ...sub(req.headers ?? {}, vars) },
        body: req.body === undefined ? undefined : JSON.stringify(sub(req.body, vars)),
      });
      const body: unknown = await resp.json().catch(() => ({}));
      const headers: Record<string, string | null> = {};
      resp.headers.forEach((v, k) => { headers[k] = v; });
      const exp = fx.expect ?? {};
      if (exp.status !== undefined && resp.status !== exp.status) {
        fails.push(`status ${resp.status} != ${exp.status} (body=${JSON.stringify(body).slice(0, 200)})`);
      }
      for (const key of exp.has ?? []) {
        if (body === null || typeof body !== "object" || !(key in (body as Record<string, unknown>))) {
          fails.push(`missing key '${key}'`);
        }
      }
      for (const path of exp.absent ?? []) {
        if (getPath(body, path)[0]) fails.push(`forbidden path present: '${path}'`);
      }
      for (const [path, wantRaw] of Object.entries(exp.where ?? {})) {
        const want = sub(wantRaw, vars);
        const [ok, got] = getPath(body, path);
        if (!ok) fails.push(`missing path '${path}'`);
        else if (!deepEqual(got, want)) fails.push(`${path}: ${JSON.stringify(got)} != ${JSON.stringify(want)}`);
      }
      for (const [hk, hv] of Object.entries(exp.headers ?? {})) {
        if ((headers[hk.toLowerCase()] ?? null) !== hv) fails.push(`header ${hk} != ${hv}`);
      }
      if (exp.identical_to !== undefined && !deepEqual(body, saved[exp.identical_to])) {
        fails.push(`body differs from saved '${exp.identical_to}'`);
      }
      for (const [v, path] of Object.entries(fx.capture ?? {})) {
        const [ok, got] = getPath(body, path as string);
        if (ok) vars[v] = got; else fails.push(`capture failed: '${path}'`);
      }
      if (fx.save_as) saved[fx.save_as] = body;
    } catch (e) {
      fails.push(`transport: ${(e as Error).message}`);
    }
    out.push({ name: fx.name, ok: fails.length === 0, fails });
  }
  return out;
}
