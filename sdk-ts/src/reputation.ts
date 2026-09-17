/** Portable reputation-v1 scorer. Pure offline math over caller-supplied active evidence. */

export const SCORE_VERSION = "reputation-v1";
export const SCORE_WEIGHTS = {
  settlement: 0.4,
  trials: 0.2,
  feedback: 0.15,
  validation: 0.15,
  reliability: 0.1,
} as const;

export type ReputationScoreKey = keyof typeof SCORE_WEIGHTS;

export interface ReputationEvidence {
  kind: string;
  ref: string;
  outcome: string;
  weight_basis?: string;
  reviewer?: string | null;
  ts?: string;
  /**
   * Retained-but-unscoreable rows (for example, raw chain feedback without an
   * explicit AMCP categorical tag) remain auditable upstream, but must not
   * influence v1 scores or experimental reviewer signals.
   */
  scoreable?: boolean;
}

export interface ReputationExperimental {
  weight: 0;
  unique_reviewers: number;
  reviewer_overlap: number;
  burst_windows: number;
}

export interface ReputationScore {
  agent_id: string;
  version: typeof SCORE_VERSION;
  scores: Record<ReputationScoreKey, number | null>;
  composite: number | null;
  experimental: ReputationExperimental;
}

const isAccepted = (evidence: ReputationEvidence): boolean => evidence.outcome === "accepted";

function ratio(items: ReputationEvidence[]): number | null {
  if (items.length === 0) return null;
  return items.filter(isAccepted).length / items.length;
}

function scoreable(evidence: ReputationEvidence[]): ReputationEvidence[] {
  return evidence.filter((item) => item.scoreable !== false);
}

export function burstWindows(evidence: ReputationEvidence[]): number {
  const stampsByReviewer = new Map<string, number[]>();
  for (const item of evidence) {
    if (!item.reviewer || item.ts === undefined) continue;
    const timestamp = Date.parse(item.ts);
    if (Number.isNaN(timestamp)) continue;
    const stamps = stampsByReviewer.get(item.reviewer) ?? [];
    stamps.push(timestamp);
    stampsByReviewer.set(item.reviewer, stamps);
  }

  let bursts = 0;
  for (const stamps of stampsByReviewer.values()) {
    stamps.sort((a, b) => a - b);
    for (let index = 0; index < stamps.length; index += 1) {
      const window = stamps.slice(index).filter((stamp) => stamp - stamps[index] <= 3_600_000);
      if (window.length >= 3) {
        bursts += 1;
        break;
      }
    }
  }
  return bursts;
}

export function scoreAgent(
  agentId: string,
  evidence: ReputationEvidence[],
  universe: Record<string, ReputationEvidence[]> = { [agentId]: evidence },
): ReputationScore {
  const mine = scoreable(evidence);
  const activeUniverse = Object.fromEntries(
    Object.entries(universe).map(([id, items]) => [id, scoreable(items)]),
  );
  const byKind = new Map<string, ReputationEvidence[]>();
  for (const item of mine) {
    const items = byKind.get(item.kind) ?? [];
    items.push(item);
    byKind.set(item.kind, items);
  }

  const trials = byKind.get("trial") ?? [];
  const revocations = mine.filter((item) => item.kind === "revocation").length;
  const scores: Record<ReputationScoreKey, number | null> = {
    settlement: ratio((byKind.get("receipt") ?? []).filter((item) => item.weight_basis === "settlement")),
    trials: byKind.has("trial") ? Math.min(1, trials.filter(isAccepted).length / 5) : null,
    feedback: ratio(byKind.get("feedback") ?? []),
    validation: ratio(byKind.get("validation") ?? []),
    reliability: mine.length > 0 ? 1 - revocations / (mine.length + 1) : null,
  };

  const present = (Object.entries(scores) as [ReputationScoreKey, number | null][])
    .filter((entry): entry is [ReputationScoreKey, number] => entry[1] !== null);
  const composite = present.length > 0
    ? present.reduce((sum, [key, value]) => sum + value * SCORE_WEIGHTS[key], 0) /
      present.reduce((sum, [key]) => sum + SCORE_WEIGHTS[key], 0)
    : null;

  // Reviewer graph: logged, not judged.
  const agentsByReviewer = new Map<string, Set<string>>();
  for (const [id, items] of Object.entries(activeUniverse)) {
    for (const item of items) {
      if (!item.reviewer) continue;
      const agents = agentsByReviewer.get(item.reviewer) ?? new Set<string>();
      agents.add(id);
      agentsByReviewer.set(item.reviewer, agents);
    }
  }
  const myReviewers = [...agentsByReviewer.entries()]
    .filter(([, agents]) => agents.has(agentId));

  return {
    agent_id: agentId,
    version: SCORE_VERSION,
    scores,
    composite,
    experimental: {
      weight: 0,
      unique_reviewers: myReviewers.length,
      reviewer_overlap: myReviewers.reduce((sum, [, agents]) => sum + (agents.size - 1), 0),
      burst_windows: burstWindows(mine.filter((item) => item.reviewer)),
    },
  };
}
