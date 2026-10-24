import axios, { type AxiosError } from 'axios'
import { RENEWED_TOKEN_HEADER, clearSession, storeRenewedToken } from './session'

const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
  withCredentials: true,
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let _redirectingToLogin = false

apiClient.interceptors.response.use(
  (response) => {
    storeRenewedToken(response.headers[RENEWED_TOKEN_HEADER])
    return response
  },
  (error: AxiosError<{ error: string; message: string }>) => {
    if (error.response?.status === 401) {
      if (!_redirectingToLogin) {
        _redirectingToLogin = true
        clearSession()
        window.location.href = '/login'
        // reset flag after navigation (2s buffer)
        setTimeout(() => { _redirectingToLogin = false }, 2000)
      }
      return Promise.reject(new Error('Unauthorized'))
    }
    const detail = (error.response?.data as any)?.detail
    const message =
      (typeof detail === 'string' ? detail : detail?.message) ??
      (error.response?.data as any)?.message ??
      error.message
    return Promise.reject(new Error(message))
  }
)

export default apiClient
