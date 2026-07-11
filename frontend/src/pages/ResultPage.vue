<template>
  <div class="result-page">
    <div v-if="loading" class="loading">載入中...</div>

    <div v-else-if="fetchError" class="fetch-error">
      <p>{{ fetchError }}</p>
      <button class="btn-secondary" @click="fetchResults">重試</button>
    </div>

    <template v-else>
      <div class="page-header">
        <h1>執行結果</h1>
        <div class="header-actions">
          <button class="btn-secondary" @click="goBack">返回</button>
          <button class="btn-primary" @click="handleExportReport">匯出報告</button>
        </div>
      </div>

      <div v-if="execution" class="execution-summary">
        <span>執行 ID：{{ execution.id }}</span>
        <span>狀態：{{ execution.status }}</span>
        <span>通過：{{ execution.passed_count }}</span>
        <span>失敗：{{ execution.failed_count }}</span>
      </div>

      <div class="rf-report-tab">
        <template v-if="execution && (execution.status === 'completed' || execution.status === 'failed')">
          <!-- checklist 多案例時顯示案例選擇器 -->
          <div v-if="!execution.source_case_id && caseResults.length > 1" class="case-selector">
            <label>選擇案例：</label>
            <select v-model="selectedReportCase">
              <option v-for="cr in caseResults" :key="cr.case_number" :value="cr.case_number">
                {{ cr.case_number }} — {{ cr.case_name }}
              </option>
            </select>
          </div>
          <iframe
            :key="`report-${rfReportPrefix}`"
            :src="`/api/v1/executions/${executionId}/rf-report/${rfReportPrefix}report.html`"
            class="rf-iframe"
            title="RF 測試報告"
          />
        </template>
        <div v-else class="rf-report-placeholder">
          執行進行中，報告生成後可查閱
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getExecution, getExecutionResults, exportReport, streamExecution, type ExecutionRecord, type CaseResultItem } from '../services/executionApi'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const fetchError = ref<string | null>(null)
const execution = ref<ExecutionRecord | null>(null)
const caseResults = ref<CaseResultItem[]>([])
const selectedReportCase = ref<string>('')

// trial run → 報告在根目錄；checklist → 報告在 {case_number}/ 子目錄
const rfReportPrefix = computed(() => {
  if (execution.value?.source_case_id) return ''
  const cn = selectedReportCase.value || caseResults.value[0]?.case_number || ''
  return cn ? `${cn}/` : ''
})

const executionId = computed(() => route.params.id as string)

let evtSource: EventSource | null = null

async function fetchResults() {
  loading.value = true
  fetchError.value = null
  try {
    execution.value = await getExecution(executionId.value)
    const data = await getExecutionResults(executionId.value)
    caseResults.value = data.items

    // 試跑／執行在背景非同步進行，剛導頁進來時通常還是 running，
    // 訂閱 SSE 等待完成後再重新抓一次以取得最終狀態與報告
    if (execution.value.status !== 'completed' && execution.value.status !== 'failed' && !evtSource) {
      evtSource = streamExecution(executionId.value, (data) => {
        const event = data as { event?: string }
        if (event.event === 'execution_completed' || event.event === 'execution_error') {
          evtSource = null
          fetchResults()
        }
      })
    }
  } catch (e: any) {
    if (e.message !== 'Unauthorized') {
      fetchError.value = e.message || '載入失敗'
    }
    // 401 由 apiClient 攔截後跳轉 /login，不需額外處理
  } finally {
    loading.value = false
  }
}

function goBack() {
  if (execution.value?.checklist_id) {
    router.push(`/checklists/${execution.value.checklist_id}`)
  } else if (execution.value?.source_case_id) {
    router.push(`/cases/${execution.value.source_case_id}`)
  } else {
    router.push('/checklists')
  }
}

async function handleExportReport() {
  if (execution.value) {
    await exportReport(execution.value.id)
  }
}

onMounted(fetchResults)
onUnmounted(() => evtSource?.close())
</script>

<style scoped>
.result-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.header-actions {
  display: flex;
  gap: 8px;
}
.execution-summary {
  display: flex;
  gap: 24px;
  padding: 12px 16px;
  background: #f5f5f5;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 14px;
  color: #555;
}
.rf-report-tab {
  display: flex;
  flex-direction: column;
}
.rf-iframe {
  width: 100%;
  height: 80vh;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
}
.case-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  color: #555;
}
.case-selector select {
  padding: 4px 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 14px;
}
.rf-report-placeholder {
  padding: 40px;
  text-align: center;
  color: #888;
  background: #fafafa;
  border: 1px dashed #ccc;
  border-radius: 6px;
}
.btn-primary {
  padding: 8px 16px;
  background: #1976d2;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.fetch-error {
  padding: 40px;
  text-align: center;
  color: #dc2626;
}
.fetch-error button {
  margin-top: 12px;
}
.btn-secondary {
  padding: 8px 16px;
  background: #fff;
  color: #555;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
}
</style>
