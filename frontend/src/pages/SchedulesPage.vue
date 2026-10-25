<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1>排程</h1>
        <span class="subtitle">所有清單的排程執行；新增排程請到各清單頁面</span>
      </div>
    </div>
    <ScheduleList />
  </div>
</template>

<script setup lang="ts">
import ScheduleList from '../components/ScheduleList/index.vue'
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
h1 { margin-bottom: 4px; }
.subtitle { color: var(--ink-muted); }
</style>
