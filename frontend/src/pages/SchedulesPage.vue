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
.page { max-width: 1200px; margin: 0 auto; padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
h1 { font-size: 22px; margin-bottom: 4px; }
.subtitle { font-size: 13px; color: #6b7280; }
</style>
