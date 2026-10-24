// 閒置逾時：後端每次通過驗證的請求都在 X-Access-Token 換發新 token，
// 前端依 token 的 exp 計時，到期就直接回登入頁，不必等下一次 API 收到 401。

export const RENEWED_TOKEN_HEADER = 'x-access-token'

let expiryTimer: ReturnType<typeof setTimeout> | null = null

function tokenExpiryMs(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return typeof payload.exp === 'number' ? payload.exp * 1000 : null
  } catch {
    return null
  }
}

export function clearSession() {
  cancelSessionExpiry()
  localStorage.removeItem('access_token')
  localStorage.removeItem('user_role')
  localStorage.removeItem('username')
}

function expireSession() {
  clearSession()
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

export function cancelSessionExpiry() {
  if (expiryTimer !== null) {
    clearTimeout(expiryTimer)
    expiryTimer = null
  }
}

export function scheduleSessionExpiry() {
  cancelSessionExpiry()
  const token = localStorage.getItem('access_token')
  const expiresAt = token ? tokenExpiryMs(token) : null
  if (expiresAt === null) return
  expiryTimer = setTimeout(() => {
    // 其他分頁可能已換發較新的 token（共用 localStorage）：仍有效就重新計時
    const latest = localStorage.getItem('access_token')
    const latestExpiresAt = latest ? tokenExpiryMs(latest) : null
    if (latestExpiresAt !== null && latestExpiresAt > Date.now()) {
      scheduleSessionExpiry()
    } else {
      expireSession()
    }
  }, Math.max(0, expiresAt - Date.now()))
}

export function storeRenewedToken(token: string | undefined | null) {
  if (!token || !localStorage.getItem('access_token')) return
  localStorage.setItem('access_token', token)
  scheduleSessionExpiry()
}
