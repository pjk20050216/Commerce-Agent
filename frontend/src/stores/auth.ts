import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, register as apiRegister, getMe } from '@/api/auth'
import type { UserInfo } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref<string>(localStorage.getItem('token') || '')
  const user = ref<UserInfo | null>(null)
  const isAuthenticated = computed(() => !!token.value)

  /** 用户登录 */
  async function login(username: string, password: string) {
    const res = await apiLogin({ username, password })
    const data = res.data as any
    // Handle both wrapped and unwrapped responses
    const tokenData = data.data || data
    token.value = tokenData.access_token
    user.value = tokenData.user
    localStorage.setItem('token', tokenData.access_token)
    localStorage.setItem('tenant_id', tokenData.user?.tenant_id || 'dev')
    return tokenData
  }

  /** 用户注册 */
  async function register(
    username: string,
    password: string,
    workspaceName: string,
    displayName?: string
  ) {
    const res = await apiRegister({
      username,
      password,
      workspace_name: workspaceName,
      display_name: displayName || username,
    })
    const data = res.data as any
    const tokenData = data.data || data
    token.value = tokenData.access_token
    user.value = tokenData.user
    localStorage.setItem('token', tokenData.access_token)
    localStorage.setItem('tenant_id', tokenData.user?.tenant_id || 'dev')
    return tokenData
  }

  /** 获取当前用户信息 */
  async function fetchMe() {
    try {
      const res = await getMe()
      const data = res.data as any
      const meData = data.data || data
      if (meData?.user) {
        user.value = meData.user
        localStorage.setItem('tenant_id', meData.user.tenant_id || 'dev')
      }
    } catch {
      // Not logged in, ignore
    }
  }

  /** 退出登录 */
  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('tenant_id')
  }

  return {
    token,
    user,
    isAuthenticated,
    login,
    register,
    fetchMe,
    logout,
  }
})
