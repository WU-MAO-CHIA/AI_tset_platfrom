<template>
  <div class="checklist-view">
    <div class="checklist-header">
      <h2>{{ checklist.name }}</h2>
      <p v-if="checklist.description" class="description">{{ checklist.description }}</p>
      <div class="execute-controls">
        <label>
          <input type="checkbox" v-model="parallelMode" />
          平行執行
        </label>
        <label v-if="parallelMode">
          並行數：
          <input type="number" v-model.number="maxWorkers" min="1" max="10" style="width: 60px" />
        </label>
        <button class="btn-primary" @click="emit('execute', { parallelMode, maxWorkers })">
          執行測試
        </button>
      </div>
    </div>

    <section class="items-section">
      <h3>測試案例（{{ checklist.items.length }} 筆）</h3>
      <ul class="items-list">
        <li v-for="item in checklist.items" :key="item.id" class="item-row">
          <span>{{ item.test_case_id }}</span>
          <button class="btn-remove" @click="emit('removeCase', item.test_case_id)">移除</button>
        </li>
        <li v-if="checklist.items.length === 0" class="empty-items">尚無案例</li>
      </ul>
    </section>

    <section class="history-section">
      <h3>執行歷史</h3>
      <table v-if="executions.length > 0" class="history-table">
        <thead>
          <tr>
            <th>執行 ID</th>
            <th>狀態</th>
            <th>通過</th>
            <th>失敗</th>
            <th>建立時間</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="exec in executions" :key="exec.id">
            <td>{{ exec.id.slice(0, 8) }}</td>
            <td>{{ exec.status }}</td>
            <td>{{ exec.passed_count }}</td>
            <td>{{ exec.failed_count }}</td>
            <td>{{ exec.created_at }}</td>
            <td>
              <button class="btn-link" @click="emit('viewExecution', exec.id)">詳情</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty-history">尚無執行記錄</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { ChecklistDetail } from '../../services/checklistApi'

const parallelMode = ref(false)
const maxWorkers = ref(3)

interface Execution {
  id: string
  status: string
  passed_count: number
  failed_count: number
  created_at: string
}

defineProps<{
  checklist: ChecklistDetail
  executions?: Execution[]
}>()

const emit = defineEmits<{
  (e: 'removeCase', caseId: string): void
  (e: 'viewExecution', executionId: string): void
  (e: 'execute', options: { parallelMode: boolean; maxWorkers: number }): void
}>()
</script>
