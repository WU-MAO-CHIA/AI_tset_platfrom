<template>
  <div class="result-page">
    <div v-if="loading" class="loading">載入中...</div>

    <template v-else>
      <div class="page-header">
        <h1>執行結果</h1>
        <div class="header-actions">
          <button class="btn-secondary" @click="$router.back()">返回</button>
          <button class="btn-primary" @click="handleExportReport">匯出報告</button>
        </div>
      </div>

      <div v-if="execution" class="execution-summary">
        <span>執行 ID：{{ execution.id }}</span>
        <span>狀態：{{ execution.status }}</span>
        <span>通過：{{ execution.passed_count }}</span>
        <span>失敗：{{ execution.failed_count }}</span>
      </div>

      <ResultViewer :results="caseResults" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getExecution, getExecutionResults, exportReport, type ExecutionRecord, type CaseResultItem } from '../services/executionApi'
import ResultViewer from '../components/ResultViewer/index.vue'

const route = useRoute()

const loading = ref(true)
const execution = ref<ExecutionRecord | null>(null)
const caseResults = ref<CaseResultItem[]>([])

async function fetchResults() {
  const id = route.params.id as string
  loading.value = true
  try {
    execution.value = await getExecution(id)
    const data = await getExecutionResults(id)
    caseResults.value = data.items
  } finally {
    loading.value = false
  }
}

async function handleExportReport() {
  if (execution.value) {
    await exportReport(execution.value.id)
  }
}

onMounted(fetchResults)
</script>
