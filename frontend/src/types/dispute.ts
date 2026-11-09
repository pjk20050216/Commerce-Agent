/**
 * Description: 售后纠纷仲裁庭类型定义。
 * @author 23372
 * @version 1.0.0
 * 2026-11-09
 */

export type Responsibility = 'merchant' | 'consumer' | 'platform' | 'shared' | 'undetermined'

export type DraftTone = 'complaint' | 'appeal' | 'negotiation'

export type DisputeClaim =
  | 'refund_only'
  | 'refund_with_return'
  | 'return_repair'
  | 'exchange'
  | 'compensation'
  | 'apology'
  | 'undetermined'

export type Speaker = 'consumer' | 'merchant' | 'platform' | 'system'

/** 聊天记录 */
export interface ChatMessageInput {
  speaker: Speaker
  content: string
  sent_at?: string | null
}

/** 物流轨迹 */
export interface LogisticsEventInput {
  status: string
  description?: string | null
  occurred_at?: string | null
  location?: string | null
}

/** 开箱凭证 */
export interface UnboxingEvidence {
  image_url: string
  description?: string
  captured_at?: string | null
}

/** 争议订单 */
export interface DisputeOrderInput {
  order_id: string
  platform: string
  category?: string | null
  amount: number
  product_title: string
  paid_at?: string | null
  shipped_at?: string | null
  received_at?: string | null
  is_custom_made?: boolean
  is_fresh?: boolean
  is_digital?: boolean
}

/** 归一化证据 */
export interface EvidenceItem {
  evidence_id: string
  type: string
  title: string
  content: string
  occurred_at: string | null
  weight: number
}

/** 时间线节点 */
export interface TimelineNode {
  occurred_at: string | null
  phase: string
  title: string
  detail: string
  source: string | null
}

/** 关键事实 */
export interface KeyFact {
  statement: string
  evidence_ids: string[]
  confidence: number
  favorable_to: string
}

/** 事实还原结果 */
export interface FactSheet {
  order: DisputeOrderInput
  evidence: EvidenceItem[]
  timeline: TimelineNode[]
  key_facts: KeyFact[]
  evidence_gaps: string[]
  complete: boolean
  summary: string
}

/** 命中规则 */
export interface MatchedRule {
  rule_id: string
  name: string
  category: string
  legal_basis: string
  conclusion: string
  weight: number
  matched_because: string
  favors: Responsibility
}

/** 裁决 */
export interface ArbitrationVerdict {
  case_id: string
  responsibility: Responsibility
  confidence: number
  claim: DisputeClaim
  matched_rules: MatchedRule[]
  legal_basis: string[]
  reasoning: string
  suggested_compensation: string
  deadline_advice: string
}

/** 话术草稿 */
export interface ComplaintDraft {
  tone: DraftTone
  title: string
  body: string
  cited_clauses: string[]
  next_actions: string[]
}

/** 案件结果 */
export interface DisputeCaseResult {
  case_id: string
  order_id: string
  verdict: ArbitrationVerdict
  fact_sheet: FactSheet
  drafts: ComplaintDraft[]
  disclaimer: string
  generated_at: string
}

/** 案件列表项 */
export interface DisputeCaseSummary {
  case_id: string
  order_id: string
  platform: string
  responsibility: Responsibility
  confidence: number
  created_at: string | null
}

/** 提交仲裁请求 */
export interface DisputeCaseRequest {
  order: DisputeOrderInput
  claim_text: string
  chat_log: ChatMessageInput[]
  logistics: LogisticsEventInput[]
  unboxing: UnboxingEvidence[]
  persist?: boolean
}
