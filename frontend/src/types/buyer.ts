/**
 * Description: 虚拟买手团类型定义。
 * @author 23372
 * @version 1.0.0
 * 2026-11-09
 */

export type Recommendation = 'strong_buy' | 'buy' | 'consider' | 'avoid'

export type RiskLevel = 'low' | 'medium' | 'high'

export type PriceVerdict = 'great_deal' | 'fair' | 'wait' | 'overpriced'

export type BrowsingAction = 'view' | 'favorite' | 'cart' | 'purchase'

/** 单个风格维度的偏好强度 */
export interface StyleDimension {
  name: string
  weight: number
  evidence: string[]
}

/** 用户价格带画像 */
export interface PriceBand {
  min_price: number | null
  max_price: number | null
  avg_price: number | null
  preferred_price: number | null
}

/** 风格画像 */
export interface StyleProfile {
  user_id: string
  dominant_styles: StyleDimension[]
  price_band: PriceBand
  preferred_categories: string[]
  brand_affinity: string[]
  confidence: number
  based_on_records: number
  summary: string
}

/** 候选商品 */
export interface CandidateProduct {
  title: string
  price: number
  category?: string | null
  brand?: string | null
  platform?: string | null
  url?: string | null
  specs?: Record<string, string>
  tags?: string[]
  reviews?: string[]
  return_rate?: number | null
  total_reviews?: number | null
}

/** 用户行为记录 */
export interface BrowsingRecord {
  item_id: string
  title: string
  category?: string | null
  brand?: string | null
  tags?: string[]
  price?: number | null
  action?: BrowsingAction
  occurred_at?: string | null
}

/** 单条全网报价 */
export interface PriceQuote {
  platform: string
  title: string
  price: number
  currency: string
  seller: string | null
  url: string | null
  is_mock: boolean
  fetched_at: string | null
}

/** 历史价格点 */
export interface PriceHistoryPoint {
  date: string
  price: number
}

/** 比价结果 */
export interface PriceComparison {
  query: string
  quotes: PriceQuote[]
  lowest: PriceQuote | null
  highest: PriceQuote | null
  average_price: number | null
  current_price: number | null
  vs_lowest_pct: number | null
  vs_average_pct: number | null
  history: PriceHistoryPoint[]
  historical_low: number | null
  historical_high: number | null
  historical_avg: number | null
  verdict: PriceVerdict
  advice: string
  source: string
  is_mock: boolean
}

/** 差评缺陷关键词 */
export interface DefectKeyword {
  keyword: string
  category: string
  count: number
  severity: number
  quotes: string[]
}

/** 差评与退货风险 */
export interface ReviewInsight {
  total_reviews: number
  negative_count: number
  negative_ratio: number
  defect_keywords: DefectKeyword[]
  return_rate: number | null
  category_return_rate: number | null
  risk_level: RiskLevel
  evidence_quotes: string[]
  summary: string
}

/** 质量评估 */
export interface QualityAssessment {
  score: number
  risk_level: RiskLevel
  insight: ReviewInsight
  warnings: string[]
}

/** 加权评分明细 */
export interface WeightedScore {
  style_fit: number
  value_score: number
  quality_score: number
  weights: Record<string, number>
  overall: number
}

/** 风险预警 */
export interface DecisionWarning {
  kind: string
  severity: RiskLevel
  message: string
  evidence: string | null
}

/** Agent 执行痕迹 */
export interface AgentTraceItem {
  agent: string
  status: string
  detail: string
}

/** 买手决策卡 */
export interface BuyerDecisionCard {
  card_id: string
  user_id: string
  candidate: CandidateProduct
  style_profile: StyleProfile
  price_comparison: PriceComparison
  quality: QualityAssessment
  score: WeightedScore
  recommendation: Recommendation
  reasons: string[]
  warnings: DecisionWarning[]
  buy_advice: string
  is_mock_data: boolean
  generated_at: string
  agent_trace: AgentTraceItem[]
}

/** 决策卡列表项 */
export interface BuyerDecisionSummary {
  card_id: string
  user_id: string
  title: string
  overall_score: number
  recommendation: Recommendation
  is_mock_data: boolean
  created_at: string | null
}

/** 生成决策卡请求 */
export interface BuyerDecisionRequest {
  user_id: string
  candidate: CandidateProduct
  history: BrowsingRecord[]
  persist?: boolean
}
