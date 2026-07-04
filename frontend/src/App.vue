<template>
  <div class="app-layout">
    <nav class="app-nav" v-if="!isLoginPage">
      <RouterLink class="nav-brand" to="/">AutoTest</RouterLink>
      <button class="hamburger" @click="menuOpen = !menuOpen" aria-label="選單">
        {{ menuOpen ? '✕' : '☰' }}
      </button>
      <div class="nav-links" :class="{ open: menuOpen }" @click="menuOpen = false">
        <RouterLink to="/cases" active-class="active">測試案例管理</RouterLink>
        <RouterLink to="/checklists" active-class="active">測試清單</RouterLink>
        <RouterLink to="/db-connections" active-class="active">資料庫連線</RouterLink>
        <RouterLink v-if="authStore.isAdmin" to="/admin" active-class="active">管理後台</RouterLink>
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
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; font-family: inherit; }
body { font-family: 'Noto Sans TC', system-ui, -apple-system, sans-serif; background: #f8fafc; color: #1e293b; }
</style>

<style scoped>
.app-layout { min-height: 100vh; display: flex; flex-direction: column; }

.app-nav {
  display: flex;
  align-items: center;
  gap: 32px;
  padding: 0 24px;
  height: 52px;
  background: #1e293b;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-brand {
  font-weight: 700;
  font-size: 16px;
  color: #f1f5f9;
  text-decoration: none;
  letter-spacing: 0.5px;
}

.hamburger {
  display: none;
  background: none;
  border: none;
  color: #f1f5f9;
  font-size: 20px;
  cursor: pointer;
  margin-left: auto;
  padding: 4px 8px;
}

.nav-links {
  display: flex;
  gap: 4px;
  flex: 1;
}

.nav-links a {
  padding: 6px 14px;
  border-radius: 6px;
  color: #94a3b8;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
}

.nav-links a:hover { background: #334155; color: #e2e8f0; }
.nav-links a.active { background: #4f46e5; color: white; }

.nav-user {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
  white-space: nowrap;
}

.username {
  font-size: 0.875rem;
  color: #94a3b8;
}

.logout-btn {
  background: none;
  border: 1px solid #475569;
  color: #94a3b8;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: background 0.15s, color 0.15s;
}

.logout-btn:hover {
  background: #334155;
  color: #e2e8f0;
}

.app-main { flex: 1; }

@media (max-width: 767px) {
  .hamburger { display: block; }

  .nav-links {
    display: none;
    position: absolute;
    top: 52px;
    left: 0;
    right: 0;
    background: #1e293b;
    flex-direction: column;
    padding: 8px 16px 16px;
    gap: 4px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    flex: none;
  }

  .nav-links.open { display: flex; }

  .nav-links a { padding: 10px 14px; font-size: 15px; }

  .nav-user { margin-left: 0; }
}
</style>
