/**
 * Description: 直播购物分身类型定义。
 * @author 23372
 * @version 1.0.0
 * 2026-11-09
 */

import type { PriceComparison } from '@/types/buyer'

export type KeyPointKind = 'price' | 'limit' | 'gift' | 'deadline' | 'spec' | 'promise' | 'other'

/** 字幕片段 */
export interface TranscriptSegment {
  start_seconds: number
  end_seconds: number
  text: string
  speaker?: string
}

/** 弹幕 */
export interface DanmakuItem {
  text: string
  sent_at?: string | null
  user?: string | null
  likes?: number
}

/** 关键信息 */
export interface LiveKeyPoint {
  kind: KeyPointKind
  text: string
  quote: string
  confidence: number
  at_seconds: number | null
}

/** 弹幕情感 */
export interface SentimentBreakdown {
  total: number
  positive: number
  negative: number
  neutral: number
  score: number
  heat_per_minute: number
  top_positive_phrases: string[]
  top_negative_phrases: string[]
  tags: string[]
  summary: string
}

/** 报价触发点 */
export interface PriceTrigger {
  price: number
  quote: string
  at_seconds: number | null
  product_hint: string | null
}

/** 比价提醒 */
export interface LivePriceAlert {
  trigger: PriceTrigger
  comparison: PriceComparison
  advice: string
  is_mock: boolean
}

/** 直播快照 */
export interface LiveSnapshot {
  session_id: string
  room_id: string
  title: string
  status: string
  key_points: LiveKeyPoint[]
  sentiment: SentimentBreakdown
  price_alert: LivePriceAlert | null
  summary: string
  processed_segments: number
  processed_danmaku: number
  updated_at: string
}

/** 直播会话列表项 */
export interface LiveSessionSummary {
  session_id: string
  room_id: string
  title: string
  status: string
  updated_at: string | null
}

/** 创建会话请求 */
export interface CreateLiveSessionRequest {
  room_id: string
  title: string
  platform?: string
}

/** 推入事件请求 */
export interface LiveIngestRequest {
  segments: TranscriptSegment[]
  danmaku: DanmakuItem[]
  current_product?: string | null
}
