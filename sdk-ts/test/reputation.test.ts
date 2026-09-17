/** Reputation-v1 parity: every shared vector must score identically in the SDK. */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  SCORE_VERSION,
  SCORE_WEIGHTS,
  scoreAgent,
  type ReputationEvidence,
} from "../src/reputation.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const vectors = JSON.parse(
  readFileSync(join(ROOT, "conformance", "vectors", "reputation.json"), "utf8"),
);

describe("reputation vectors", () => {
  it("pins the scoring version and weights", () => {
    expect(vectors.version).toBe(SCORE_VERSION);
    expect(vectors.weights).toEqual({ ...SCORE_WEIGHTS });
  });

  for (const testCase of vectors.cases) {
    it(testCase.name, () => {
      const evidence = testCase.evidence as ReputationEvidence[];
      const score = scoreAgent("amcp:t:v", evidence, { "amcp:t:v": evidence });

      expect(score.version).toBe("reputation-v1");
      expect(score.scores).toEqual(testCase.expected.scores);
      if (testCase.expected.composite === null) {
        expect(score.composite).toBeNull();
      } else {
        expect(Math.abs((score.composite as number) - testCase.expected.composite)).toBeLessThan(1e-9);
      }
      expect(score.experimental).toEqual(testCase.expected.experimental);
    });
  }

  it("keeps retained-but-unscoreable evidence out of scoring and signals", () => {
    const evidence: ReputationEvidence[] = [{
      kind: "feedback",
      ref: "raw-chain-feedback",
      outcome: "accepted",
      reviewer: "0xreviewer",
      ts: "2026-09-01T10:00:00Z",
      scoreable: false,
    }];
    const score = scoreAgent("amcp:t:raw", evidence, { "amcp:t:raw": evidence });

    expect(score.scores).toEqual({
      settlement: null,
      trials: null,
      feedback: null,
      validation: null,
      reliability: null,
    });
    expect(score.composite).toBeNull();
    expect(score.experimental).toEqual({
      weight: 0,
      unique_reviewers: 0,
      reviewer_overlap: 0,
      burst_windows: 0,
    });
  });
});
