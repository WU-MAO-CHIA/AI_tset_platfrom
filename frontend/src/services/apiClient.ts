import axios, { type AxiosError } from 'axios'

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
  (response) => response,
  (error: AxiosError<{ error: string; message: string }>) => {
    if (error.response?.status === 401) {
      if (!_redirectingToLogin) {
        _redirectingToLogin = true
        localStorage.removeItem('access_token')
        localStorage.removeItem('user_role')
        localStorage.removeItem('username')
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
