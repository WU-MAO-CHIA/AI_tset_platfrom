<template>
  <div class="app-layout">
    <nav class="app-nav">
      <RouterLink class="nav-brand" to="/">AutoTest</RouterLink>
      <button class="hamburger" @click="menuOpen = !menuOpen" aria-label="選單">
        {{ menuOpen ? '✕' : '☰' }}
      </button>
      <div class="nav-links" :class="{ open: menuOpen }" @click="menuOpen = false">
        <RouterLink to="/cases" active-class="active">測試案例管理</RouterLink>
        <RouterLink to="/checklists" active-class="active">測試清單</RouterLink>
        <RouterLink to="/db-connections" active-class="active">資料庫連線</RouterLink>
      </div>
    </nav>
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterView, RouterLink } from 'vue-router'

const menuOpen = ref(false)
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
  }

  .nav-links.open { display: flex; }

  .nav-links a { padding: 10px 14px; font-size: 15px; }
}
</style>
