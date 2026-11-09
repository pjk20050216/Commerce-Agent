/**
 * Description: 虚拟买手团 API 函数封装。
 * @author 23372
 * @version 1.0.0
 * 2026-11-09
 */

import http from '@/api'
import type {
  BuyerDecisionCard,
  BuyerDecisionRequest,
  BuyerDecisionSummary,
  PriceComparison,
} from '@/types/buyer'
import type { ApiResponse } from '@/types/api'

/** 生成买手决策卡 */
export function createDecision(data: BuyerDecisionRequest) {
  return http.post<ApiResponse<BuyerDecisionCard>>('/buyer/decisions', data)
}

/** 决策卡历史 */
export function listDecisions(params?: { user_id?: string; limit?: number }) {
  return http.get<ApiResponse<BuyerDecisionSummary[]>>('/buyer/decisions', { params })
}

/** 决策卡详情 */
export function getDecision(cardId: string) {
  return http.get<ApiResponse<BuyerDecisionCard>>(`/buyer/decisions/${cardId}`)
}

/** 全网比价 */
export function comparePrice(data: {
  title: string
  current_price?: number | null
  history_days?: number | null
}) {
  return http.post<ApiResponse<PriceComparison>>('/buyer/compare', data)
}
