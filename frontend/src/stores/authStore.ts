import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const role = ref<string | null>(null)
  const username = ref<string | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => role.value === 'admin')
  const isEditor = computed(() => role.value === 'editor' || role.value === 'admin')

  async function login(user: string, password: string) {
    const res = await axios.post('/api/v1/auth/login', { username: user, password })
    const data = res.data
    token.value = data.access_token
    role.value = data.role
    username.value = data.username
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('user_role', data.role)
    localStorage.setItem('username', data.username)
  }

  function logout() {
    token.value = null
    role.value = null
    username.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    localStorage.removeItem('username')
    window.location.href = '/login'
  }

  function initFromStorage() {
    const storedToken = localStorage.getItem('access_token')
    const storedRole = localStorage.getItem('user_role')
    const storedUsername = localStorage.getItem('username')
    if (storedToken) {
      token.value = storedToken
      role.value = storedRole
      username.value = storedUsername
    }
  }

  return { token, role, username, isLoggedIn, isAdmin, isEditor, login, logout, initFromStorage }
})
