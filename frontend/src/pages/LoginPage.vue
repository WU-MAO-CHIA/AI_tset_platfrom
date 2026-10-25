<template>
  <div class="login-container">
    <aside class="login-side">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        自動化測試平台
      </div>
      <div class="pitch">
        <p class="headline">寫下測試步驟，<br />每天自動驗證一次。</p>
        <p class="lead">管理測試案例與清單，用 Robot Framework 自動執行，結果一眼看清。</p>
      </div>
      <div class="run-wall" aria-hidden="true">
        <i v-for="(cell, idx) in wall" :key="idx" :class="cell" />
      </div>
    </aside>

    <main class="login-main">
      <form class="login-form" @submit.prevent="handleLogin">
        <h1>登入</h1>
        <p class="subtitle">使用管理員提供的帳號</p>

        <div class="field">
          <label for="login-username">帳號</label>
          <input id="login-username" v-model="form.username" type="text" placeholder="輸入帳號" autocomplete="username" required />
        </div>
        <div class="field">
          <label for="login-password">密碼</label>
          <input id="login-password" v-model="form.password" type="password" placeholder="輸入密碼" autocomplete="current-password" required />
        </div>

        <p v-if="errorMsg" class="error-msg" role="alert">{{ errorMsg }}</p>

        <button type="submit" class="btn-primary login-btn" :disabled="loading">
          {{ loading ? '登入中...' : '登入' }}
        </button>
      </form>
    </main>
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

// 裝飾用的執行結果牆：大多數通過，零星失敗
const wall = Array.from({ length: 100 }, (_, i) => (i % 23 === 6 || i % 37 === 11 ? 'fail' : i % 41 === 18 ? 'idle' : ''))

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
.login-container { display: grid; grid-template-columns: 1fr 1fr; min-height: 100vh; }

.login-side {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 48px;
  padding: 64px;
  background: var(--brand-soft);
  border-right: 1px solid var(--brand-line);
  color: var(--brand-ink);
}

.brand { display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 600; }
.brand-mark { width: 22px; height: 22px; display: grid; grid-template-columns: 1fr 1fr; gap: 2px; }
.brand-mark i { border-radius: 2px; background: var(--pass); }
.brand-mark i:first-child { background: var(--brand); }
.brand-mark i:last-child { background: var(--fail); }

.headline { font-size: 32px; font-weight: 600; line-height: 1.35; }
.lead { margin-top: 16px; max-width: 420px; font-size: var(--fs-16); color: var(--brand-ink-muted); }

.run-wall { display: grid; grid-template-columns: repeat(20, 1fr); gap: 4px; max-width: 520px; }
.run-wall i { aspect-ratio: 1; border-radius: 2px; background: #3bb273; }
.run-wall i.fail { background: #e0574b; }
.run-wall i.idle { background: var(--brand-line); }

.login-main { display: grid; place-items: center; padding: 32px 24px; background: var(--paper); }
.login-form { width: 100%; max-width: 360px; }
.subtitle { color: var(--ink-muted); margin: 4px 0 24px; }

.field { margin-bottom: 16px; }
.field label { display: block; font-size: var(--fs-12); color: var(--ink-muted); margin-bottom: 6px; }
.field input { width: 100%; height: 42px; }

.error-msg { color: var(--fail); margin-bottom: 12px; }

.login-btn { width: 100%; height: 42px; margin-top: 8px; }

@media (max-width: 767px) {
  .login-container { grid-template-columns: 1fr; grid-template-rows: auto 1fr; }
  .login-side { padding: 24px 16px; gap: 0; border-right: 0; border-bottom: 1px solid var(--brand-line); }
  .pitch, .run-wall { display: none; }
  .login-main { place-items: start center; padding-top: 40px; }
}
</style>
