import axios, { type AxiosError } from 'axios'

const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ error: string; message: string }>) => {
    const message = error.response?.data?.message ?? error.message
    return Promise.reject(new Error(message))
  }
)

export default apiClient
