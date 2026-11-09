/**
 * Description: 直播购物分身 API 函数封装。
 * @author 23372
 * @version 1.0.0
 * 2026-11-09
 */

import http from '@/api'
import type {
  CreateLiveSessionRequest,
  LiveIngestRequest,
  LivePriceAlert,
  LiveSessionSummary,
  LiveSnapshot,
} from '@/types/live'
import type { ApiResponse } from '@/types/api'

/** 创建直播会话 */
export function createSession(data: CreateLiveSessionRequest) {
  return http.post<ApiResponse<LiveSnapshot>>('/live/sessions', data)
}

/** 直播会话列表 */
export function listSessions(params?: { status?: string; limit?: number }) {
  return http.get<ApiResponse<LiveSessionSummary[]>>('/live/sessions', { params })
}

/** 获取最新快照 */
export function getSnapshot(sessionId: string) {
  return http.get<ApiResponse<LiveSnapshot>>(`/live/sessions/${sessionId}/snapshot`)
}

/** 推入一批字幕/弹幕 */
export function ingestEvents(sessionId: string, data: LiveIngestRequest) {
  return http.post<ApiResponse<LiveSnapshot>>(`/live/sessions/${sessionId}/ingest`, data)
}

/** 结束会话 */
export function endSession(sessionId: string) {
  return http.post<ApiResponse<LiveSnapshot>>(`/live/sessions/${sessionId}/end`)
}

/** 一键比价 */
export function priceCheck(data: { title: string; price: number }) {
  return http.post<ApiResponse<LivePriceAlert>>('/live/price-check', data)
}
