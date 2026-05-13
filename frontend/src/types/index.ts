// ─── GET /commerce/sessions ──────────────────────────────────────────────────

export interface SessionSummary {
  session_id: string
  item: string
  status: 'pending' | 'settled' | 'revoked' | 'failed'
  listed_price: number
  final_price: number | null
  buyer_agent_id: string
  created_at: string  // ISO 8601
}

// ─── GET /commerce/session/:id ───────────────────────────────────────────────

// One auction round stored in negotiation_sessions.rounds JSON column
export interface NegotiationRound {
  round: number
  type: string
  quotes: Record<string, unknown>[]
  winner: Record<string, unknown> | null
  timestamp: string
}

// The core session object returned nested inside SessionDetailResponse
export interface SessionDetail {
  id: string
  item: string
  status: 'pending' | 'settled' | 'revoked' | 'failed'
  listed_price: number
  final_price: number | null
  rounds: NegotiationRound[]
  created_at: string
  settled_at: string | null
  policy_id: string | null
  buyer_agent_id: string
  merchant_agent_id: string | null
  product_id: string | null
}

// Signed receipt attached after settlement — Ed25519 signature over payload_json
export interface SignedReceipt {
  receipt_id: string
  policy_id: string
  buyer_agent_id: string
  merchant_agent_id: string
  amount_inr: number
  payload_json: string
  signature_b64: string
  signed_payload_b64: string
  razorpay_order_id: string | null
  razorpay_payment_id: string | null
  created_at: string
}

// One row in the audit trail — every state mutation writes one of these
export interface AuditLogEntry {
  event: string
  payload: Record<string, unknown> | null
  timestamp: string
}

// Full response shape for GET /commerce/session/:id
export interface SessionDetailResponse {
  session: SessionDetail
  audit_log: AuditLogEntry[]
  signed_receipt: SignedReceipt | null
  winner_skill_id: string | null
  llm_seed: number | null
  replay_data: unknown  // opaque until replay feature (3.6) types it fully
}

// ─── Identity / pubkey endpoints ─────────────────────────────────────────────

// GET /agents/:id/pubkey
export interface AgentPubkeyResponse {
  agent_id: string
  public_key_b64: string
}

// GET /.well-known/platform-pubkey
export interface PlatformPubkeyResponse {
  public_key_b64: string
  algorithm: string
}
