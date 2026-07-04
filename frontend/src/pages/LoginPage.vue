<template>
  <div class="login-container">
    <div class="login-card">
      <h1>自動化測試平台</h1>
      <p class="subtitle">登入以繼續</p>

      <form @submit.prevent="handleLogin">
        <div class="field">
          <label>帳號</label>
          <input v-model="form.username" type="text" placeholder="輸入帳號" autocomplete="username" required />
        </div>
        <div class="field">
          <label>密碼</label>
          <input v-model="form.password" type="password" placeholder="輸入密碼" autocomplete="current-password" required />
        </div>

        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

        <button type="submit" class="login-btn" :disabled="loading">
          {{ loading ? '登入中...' : '登入' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const router = useRouter()
const authStore = useAuthStore()

const form = ref({ username: '', password: '' })
const loading = ref(false)
const errorMsg = ref('')

async function handleLogin() {
  errorMsg.value = ''
  loading.value = true
  try {
    await authStore.login(form.value.username, form.value.password)
    router.push('/')
  } catch {
    errorMsg.value = '帳號或密碼錯誤，請重試'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #f5f5f5;
}

.login-card {
  background: white;
  border-radius: 8px;
  padding: 40px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

h1 {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0 0 4px;
  color: #111;
}

.subtitle {
  color: #666;
  font-size: 0.9rem;
  margin: 0 0 28px;
}

.field {
  margin-bottom: 16px;
}

.field label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  margin-bottom: 6px;
  color: #374151;
}

.field input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.9rem;
  box-sizing: border-box;
  outline: none;
  transition: border-color 0.15s;
}

.field input:focus {
  border-color: #4f46e5;
}

.error-msg {
  color: #dc2626;
  font-size: 0.875rem;
  margin-bottom: 12px;
}

.login-btn {
  width: 100%;
  padding: 10px;
  background: #4f46e5;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.95rem;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.15s;
}

.login-btn:hover:not(:disabled) {
  background: #4338ca;
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
