<template>
  <div class="app-layout">
    <nav class="app-nav" v-if="!isLoginPage">
      <RouterLink class="nav-brand" to="/">
        <span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        自動化測試平台
      </RouterLink>
      <button class="hamburger" @click="menuOpen = !menuOpen" aria-label="選單">
        {{ menuOpen ? '✕' : '☰' }}
      </button>
      <div class="nav-links" :class="{ open: menuOpen }" @click="menuOpen = false">
        <RouterLink to="/cases" :class="{ active: isSection('/cases') }">測試案例</RouterLink>
        <RouterLink to="/checklists" :class="{ active: isSection('/checklists') }">測試清單</RouterLink>
        <RouterLink to="/schedules" :class="{ active: isSection('/schedules') }">排程</RouterLink>
        <RouterLink to="/db-connections" :class="{ active: isSection('/db-connections') }">資料庫連線</RouterLink>
        <RouterLink v-if="authStore.isAdmin" to="/dashboard" :class="{ active: isSection('/dashboard') }">監控</RouterLink>
        <RouterLink v-if="authStore.isAdmin" to="/admin" :class="{ active: isSection('/admin') }">管理後台</RouterLink>
      </div>
      <div class="nav-user" v-if="authStore.isLoggedIn">
        <span class="username">{{ authStore.username }}</span>
        <button class="logout-btn" @click="authStore.logout()">登出</button>
      </div>
    </nav>
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { RouterView, RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from './stores/authStore'

const menuOpen = ref(false)
const authStore = useAuthStore()
const route = useRoute()
const isLoginPage = computed(() => route.path === '/login')

// 詳情頁（/cases/:id 等）不是巢狀路由，RouterLink 的 active-class 不會套用，改以路徑前綴判斷
function isSection(prefix: string): boolean {
  return route.path === prefix || route.path.startsWith(`${prefix}/`)
}
</script>

<style scoped>
.app-layout { min-height: 100vh; display: flex; flex-direction: column; }

.app-nav {
  display: flex;
  align-items: center;
  gap: 40px;
  padding: 0 32px;
  height: var(--nav-h);
  background: var(--brand-soft);
  border-bottom: 1px solid var(--brand-line);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: var(--fs-16);
  color: var(--brand-ink);
  text-decoration: none;
  white-space: nowrap;
}

.brand-mark { width: 20px; height: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 2px; }
.brand-mark i { border-radius: 2px; background: var(--pass); }
.brand-mark i:first-child { background: var(--brand); }
.brand-mark i:last-child { background: var(--fail); }

.hamburger {
  display: none;
  background: none;
  border: none;
  color: var(--brand-ink);
  font-size: 20px;
  margin-left: auto;
  padding: 4px 8px;
}
.hamburger:hover:not(:disabled) { background: none; }

.nav-links { display: flex; gap: 28px; flex: 1; height: 100%; }

.nav-links a {
  display: flex;
  align-items: center;
  height: 100%;
  color: var(--brand-ink-muted);
  text-decoration: none;
  font-size: var(--fs-14);
  border-bottom: 2px solid transparent;
  padding-top: 2px;
}

.nav-links a:hover { color: var(--brand-ink); }
.nav-links a.active { color: var(--brand-ink); font-weight: 600; border-bottom-color: var(--brand); }

.nav-user { display: flex; align-items: center; gap: 12px; margin-left: auto; white-space: nowrap; }
.username { color: var(--brand-ink-muted); }

.logout-btn {
  background: transparent;
  border: 1px solid var(--brand-line);
  color: var(--brand-ink-muted);
  min-height: 28px;
  padding: 0 12px;
  font-size: var(--fs-12);
}
.logout-btn:hover:not(:disabled) { background: var(--paper); color: var(--brand-ink); }

.app-main { flex: 1; }

@media (max-width: 767px) {
  .app-nav { padding: 0 16px; gap: 12px; }
  .hamburger { display: block; }

  .nav-links {
    display: none;
    position: absolute;
    top: var(--nav-h);
    left: 0;
    right: 0;
    height: auto;
    background: var(--brand-soft);
    border-bottom: 1px solid var(--brand-line);
    flex-direction: column;
    padding: 8px 16px 16px;
    gap: 0;
    flex: none;
  }

  .nav-links.open { display: flex; }
  .nav-links a { padding: 12px 0; border-bottom: 0; font-size: var(--fs-16); }
  .nav-links a.active { border-bottom: 0; box-shadow: inset 3px 0 0 var(--brand); padding-left: 12px; }

  .nav-user { margin-left: 0; }
  .username { display: none; }
}
</style>
