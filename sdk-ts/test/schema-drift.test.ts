/** Schema drift tripwire: every `required` field of every normative schema
 * must exist in src/types.ts. Catches SDK/schema drift without dependencies. */
import { readdirSync, readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it, expect } from "vitest";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const typesSrc = readFileSync(join(ROOT, "sdk-ts", "src", "types.ts"), "utf8");

function requiredFields(schema: unknown, path = ""): string[] {
  if (Array.isArray(schema)) return schema.flatMap((s) => requiredFields(s, path));
  if (schema === null || typeof schema !== "object") return [];
  const s = schema as Record<string, any>;
  const own: string[] = Array.isArray(s.required) ? s.required : [];
  const nested = Object.entries(s.properties ?? {}).flatMap(([k, v]) => requiredFields(v, `${path}.${k}`));
  const items = s.items ? requiredFields(s.items, `${path}[]`) : [];
  return [...own.map((f) => `${path}.${f}`), ...nested, ...items];
}

describe("schema/type drift", () => {
  const files = readdirSync(join(ROOT, "schemas")).filter((f) => f.endsWith(".json"));
  it("schemas exist", () => expect(files.length).toBeGreaterThan(0));
  for (const file of files) {
    it(`${file}: required fields present in types.ts`, () => {
      const schema = JSON.parse(readFileSync(join(ROOT, "schemas", file), "utf8"));
      const missing = requiredFields(schema).filter((f) => {
        const leaf = f.split(".").pop()!;
        // snake_case wire names map to identical TS keys (SDK uses wire naming)
        return !typesSrc.includes(`${leaf}?:`) && !typesSrc.includes(`${leaf}:`);
      });
      expect(missing).toEqual([]);
    });
  }
});
