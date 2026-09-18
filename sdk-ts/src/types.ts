/** AMCP wire types. Hand-written to mirror schemas/*.json 1:1.
 * Drift tripwire: test/schema-drift.test.ts asserts every `required` field
 * of every schema exists here. Wire shape is proven by fixture replay. */

export type AmcpVersion = "0.1";
export type PartClass = "instruction" | "content" | "evidence";
export type PricingScheme = "exact" | "upto" | "escrow";
export type SessionState = "active" | "paused" | "completed" | "cancelled";
export type ConflictPolicy = "coordinator_arbitrates" | "human_escalation" | "first_claim_wins";
export type ReceiptOutcome = "accepted" | "refunded" | "split" | "disputed_lost" | "disputed_won";

export interface SignatureEnvelope {
  key_id: string;
  alg: string;
  sig: string;
}

export interface AdvertisedKey {
  id: string;
  alg: string;
  pub: string | null;
  note?: string;
}

export interface Capability {
  name: string;
  kind: string;
  description: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  authorization: string;
  pricing?: { model: string; amount_usdc: string; scheme: PricingScheme };
  [k: string]: unknown;
}

export interface Descriptor {
  amcp_version: AmcpVersion;
  id: string;
  name: string;
  description: string;
  version: string;
  capabilities: Capability[];
  public_key?: string;
  keys?: AdvertisedKey[];
  settlement?: SettlementInfo;
  reputation?: ReputationInfo;
  registrations?: Registration[];
  key_history?: KeyRotation[];
  signature?: SignatureEnvelope;
  [k: string]: unknown;
}

export interface SettlementInfo {
  pay_to: string;
  networks: string[];
  schemes: string[];
}

export interface ReputationInfo {
  receipts_uri: string;
  completed_tasks: number;
  acceptance_rate: number;
}

export interface Registration {
  system: string;
  ref: string;
}

export interface KeyRotation {
  public_key: string;
  rotated_at: string;
}

export interface Receipt {
  amcp_version: AmcpVersion;
  receipt_id: string;
  contract_id: string;
  session_id?: string | null;
  payer: string;
  payee: string;
  amount_usdc: string;
  task_ref: string;
  artifact_hash: string;
  settlement_proof: string;
  outcome: ReceiptOutcome;
  trial?: boolean;
  decided_at?: string;
  signatures: { payer: string; platform: SignatureEnvelope };
}

export interface Page<T> {
  data: T[];
  pagination: { next_cursor: string | null; has_more: boolean };
}

export interface MatchExplanation {
  matched_capabilities: string[];
  similarity_band: "high" | "medium" | "low";
  reputation: Record<string, unknown>;
}

export interface DirectoryHit {
  descriptor: Descriptor;
  verification: string;
  match_explanation: MatchExplanation;
}

export interface NegotiationTerms {
  price_usdc: string;
  scheme: PricingScheme;
  deliverable: string;
}

export type DisputeKind = "non_delivery" | "partial_delivery" | "wrong_output"
  | "late_delivery" | "unauthorized_delegation" | "evidence_forged" | "double_commit";
export type DisputeRemedy = "refund_full" | "refund_partial" | "redo" | "split"
  | "concede" | "escalate";
export type DisputeState = "filed" | "evidenced" | "adjudicating" | "decided"
  | "resolved" | "withdrawn";
export type DisputeTier = "respondent" | "arbiter" | "principal";
export type DisputeOutcome = "conceded" | "upheld" | "rejected" | "split";

export interface DisputeSubject {
  kind: "receipt" | "session";
  ref: string;
}

export interface DisputeEvidenceRef {
  ref: string;
  hash?: string;
  uri?: string;
  kind?: string;
}

export interface DisputeDecision {
  outcome: "upheld" | "rejected" | "split";
  remedy: DisputeRemedy;
  amount_usdc?: string | null;
  rationale?: string;
  arbiter: string;
  signature_valid?: boolean;
  signatures: Record<string, unknown>;
}

export interface DisputeEnforcement {
  remedy: string;
  amount_usdc?: string | null;
  executed_at: string;
  source_key: string;
}

export interface Dispute {
  amcp_version: AmcpVersion;
  dispute_id: string;
  claimant: string;
  respondent: string;
  subject: DisputeSubject;
  kind: DisputeKind;
  remedy: DisputeRemedy;
  detail?: string;
  state: DisputeState;
  tier: DisputeTier;
  appeals?: number;
  evidence?: DisputeEvidenceRef[];
  decision?: DisputeDecision | null;
  outcome?: DisputeOutcome | null;
  enforcement?: DisputeEnforcement | null;
}

export interface SessionMember {
  actor: { type: "agent" | "human"; id: string };
  role: string;
  joined_at: string;
  presence: "active" | "away" | "offline";
}

export interface SessionBudget {
  ceiling_usdc: string;
  spent_usdc: string;
  scheme: PricingScheme;
}

export interface EscalationRule {
  trigger: string;
  action: "require_approval" | "pause" | "notify";
  role: string;
  timeout_seconds?: number;
  default: "deny" | "allow";
}

export interface Session {
  amcp_version: AmcpVersion;
  id: string;
  members: SessionMember[];
  roles: Record<string, {
    read: string[]; write: string[]; message: string[];
    delegate: boolean; approve: boolean;
  }>;
  blackboard: Record<string, unknown>;
  budget: SessionBudget;
  conflict_policy: ConflictPolicy | string;
  state: SessionState;
  escalation?: EscalationRule[];
  contract_id?: string;
}

export interface Contract {
  amcp_version: AmcpVersion;
  contract_id: string;
  parties: { principal: string; counterparty: string };
  capability: string;
  terms_hash: string;
  price: { amount_usdc: string; scheme: PricingScheme };
  acceptance_criteria_schema: Record<string, unknown>;
  signatures: { principal: SignatureEnvelope; counterparty: SignatureEnvelope };
}

export interface Part {
  kind: string;
  class: PartClass;
  provenance?: Provenance;
  [k: string]: unknown;
}

export interface Provenance {
  producer: string;
  task_ref?: string;
  derived_from?: string[];
}
