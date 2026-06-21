import axios, { type AxiosError } from 'axios'

const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ error: string; message: string }>) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_role')
      localStorage.removeItem('username')
      window.location.href = '/login'
      return Promise.reject(new Error('Unauthorized'))
    }
    const message = error.response?.data?.message ?? error.message
    return Promise.reject(new Error(message))
  }
)

export default apiClient
