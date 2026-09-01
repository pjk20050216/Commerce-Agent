import type { AxiosResponse } from 'axios'
import request from './index'

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
  display_name?: string
  workspace_name: string
}

export interface UserInfo {
  id: number
  username: string
  display_name: string | null
  tenant_id: string
  tenant_name: string
}

export interface TokenData {
  access_token: string
  token_type: string
  expires_in: number
  user: UserInfo
}

export interface MeData {
  user: UserInfo
  tenant: {
    tenant_id: string
    name: string
    is_active: boolean
  }
}

const BASE_URL = '/auth'

/** 用户注册 */
export function register(data: RegisterRequest): Promise<AxiosResponse<TokenData>> {
  return request.post(`${BASE_URL}/register`, data)
}

/** 用户登录 */
export function login(data: LoginRequest): Promise<AxiosResponse<TokenData>> {
  return request.post(`${BASE_URL}/login`, data)
}

/** 获取当前用户信息 */
export function getMe(): Promise<AxiosResponse<MeData>> {
  return request.get(`${BASE_URL}/me`)
}
