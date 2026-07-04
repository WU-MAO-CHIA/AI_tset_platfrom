import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios from 'axios'
import router from './router'
import App from './App.vue'
import { useAuthStore } from './stores/authStore'

async function initApp() {
  const app = createApp(App)
  const pinia = createPinia()
  app.use(pinia)
  app.use(router)

  const authStore = useAuthStore()

  // 驗證 localStorage token 有效性；過期或無效(401)則先清除，避免 API 401 cascade
  const storedToken = localStorage.getItem('access_token')
  if (storedToken) {
    try {
      await axios.get('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${storedToken}` },
      })
      // token 有效，載入 authStore
      authStore.initFromStorage()
    } catch (err: any) {
      if (err?.response?.status === 401 || err?.response?.status === 403) {
        // token 過期或無效，清除讓路由守衛導向 /login
        localStorage.removeItem('access_token')
        localStorage.removeItem('user_role')
        localStorage.removeItem('username')
      } else {
        // 網路錯誤等非 auth 問題，仍保留 token（可能 backend 暫時不可用）
        authStore.initFromStorage()
      }
    }
  }

  app.mount('#app')
}

initApp()
