/**
 * Description: 售后纠纷仲裁庭 API 函数封装。
 * @author 23372
 * @version 1.0.0
 * 2026-11-09
 */

import http from '@/api'
import type {
  ComplaintDraft,
  DisputeCaseRequest,
  DisputeCaseResult,
  DisputeCaseSummary,
  DraftTone,
  Responsibility,
} from '@/types/dispute'
import type { ApiResponse } from '@/types/api'

/** 提交纠纷仲裁 */
export function createCase(data: DisputeCaseRequest) {
  return http.post<ApiResponse<DisputeCaseResult>>('/dispute/cases', data)
}

/** 案件历史 */
export function listCases(params?: {
  responsibility?: Responsibility
  limit?: number
}) {
  return http.get<ApiResponse<DisputeCaseSummary[]>>('/dispute/cases', { params })
}

/** 案件详情 */
export function getCase(caseId: string) {
  return http.get<ApiResponse<DisputeCaseResult>>(`/dispute/cases/${caseId}`)
}

/** 重新生成指定语气的话术 */
export function regenerateDraft(caseId: string, tone: DraftTone) {
  return http.post<ApiResponse<ComplaintDraft>>(`/dispute/cases/${caseId}/draft`, { tone })
}
