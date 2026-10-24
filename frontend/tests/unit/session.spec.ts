import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { cancelSessionExpiry, scheduleSessionExpiry, storeRenewedToken } from '../../src/services/session'

function tokenExpiringIn(seconds: number): string {
  const payload = { sub: 'admin', exp: Math.floor(Date.now() / 1000) + seconds }
  const encoded = btoa(JSON.stringify(payload)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  return `header.${encoded}.signature`
}

describe('session expiry', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    localStorage.clear()
    // 停在 /login：到期時只清狀態，不觸發 jsdom 未實作的頁面導向
    window.history.replaceState({}, '', '/login')
  })

  afterEach(() => {
    cancelSessionExpiry()
    vi.useRealTimers()
  })

  it('clears the session when the token expires without activity', () => {
    localStorage.setItem('access_token', tokenExpiringIn(600))
    localStorage.setItem('username', 'admin')
    scheduleSessionExpiry()

    vi.advanceTimersByTime(599_000)
    expect(localStorage.getItem('access_token')).not.toBeNull()

    vi.advanceTimersByTime(2_000)
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('username')).toBeNull()
  })

  it('a renewed token pushes the expiry back', () => {
    localStorage.setItem('access_token', tokenExpiringIn(600))
    scheduleSessionExpiry()

    vi.advanceTimersByTime(500_000)
    storeRenewedToken(tokenExpiringIn(600))
    vi.advanceTimersByTime(500_000)

    expect(localStorage.getItem('access_token')).not.toBeNull()
  })

  it('keeps the session when another tab already renewed the token', () => {
    localStorage.setItem('access_token', tokenExpiringIn(600))
    scheduleSessionExpiry()

    vi.advanceTimersByTime(500_000)
    localStorage.setItem('access_token', tokenExpiringIn(600))
    vi.advanceTimersByTime(200_000)

    expect(localStorage.getItem('access_token')).not.toBeNull()
  })

  it('ignores a renewed token after logout', () => {
    storeRenewedToken(tokenExpiringIn(600))
    expect(localStorage.getItem('access_token')).toBeNull()
  })
})
