<template>
  <div class="app-layout">
    <nav class="app-nav">
      <RouterLink class="nav-brand" to="/">AutoTest</RouterLink>
      <div class="nav-links">
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
import { RouterView, RouterLink } from 'vue-router'
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
</style>
