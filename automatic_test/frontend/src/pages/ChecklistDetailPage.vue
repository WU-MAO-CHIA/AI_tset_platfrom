<template>
  <div class="checklist-detail-page">
    <div v-if="loading" class="loading">載入中...</div>

    <div v-else-if="!checklist" class="not-found">
      <p>找不到清單</p>
      <button @click="$router.push('/checklists')">返回清單</button>
    </div>

    <template v-else>
      <div class="page-actions">
        <button class="btn-secondary" @click="$router.push('/checklists')">← 返回</button>
        <button class="btn-primary" @click="handleExecute">執行清單</button>
      </div>

      <ChecklistView
        :checklist="checklist"
        :executions="executions"
        @remove-case="handleRemoveCase"
        @view-execution="handleViewExecution"
      />

      <div v-if="errorMsg" class="error-banner">{{ errorMsg }}</div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getChecklist, updateChecklistItems, type ChecklistDetail } from '../services/checklistApi'
import ChecklistView from '../components/ChecklistView/index.vue'

const route = useRoute()
const router = useRouter()

const checklist = ref<ChecklistDetail | null>(null)
const executions = ref([])
const loading = ref(false)
const errorMsg = ref('')

async function fetchChecklist() {
  loading.value = true
  errorMsg.value = ''
  try {
    checklist.value = await getChecklist(route.params.id as string)
  } catch {
    checklist.value = null
  } finally {
    loading.value = false
  }
}

async function handleRemoveCase(caseId: string) {
  if (!checklist.value) return
  const newIds = checklist.value.items
    .filter((item) => item.test_case_id !== caseId)
    .map((item) => item.test_case_id)
  try {
    checklist.value = await updateChecklistItems(checklist.value.id, newIds)
  } catch {
    errorMsg.value = '移除案例失敗'
  }
}

function handleExecute() {
  // Placeholder — execution engine implemented in Phase 7
  alert('執行功能將在 Phase 7 實作')
}

function handleViewExecution(executionId: string) {
  router.push(`/executions/${executionId}`)
}

onMounted(fetchChecklist)
</script>
