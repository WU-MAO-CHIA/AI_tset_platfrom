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

      <div v-if="caseResults.length" class="case-results" data-testid="case-results">
        <h2>案例結果</h2>
        <table class="results-table">
          <thead><tr><th>案例編號</th><th>名稱</th><th>狀態</th><th>耗時(ms)</th><th>失敗訊息</th></tr></thead>
          <tbody>
            <tr v-for="cr in caseResults" :key="cr.id" :class="`row-${cr.status}`">
              <td>{{ cr.case_number }}</td>
              <td>{{ cr.case_name }}</td>
              <td>{{ statusLabel(cr.status) }}</td>
              <td>{{ cr.elapsed_ms ?? '-' }}</td>
              <td class="failure-msg">{{ cr.failure_message || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="rf-report-tab">
        <template v-if="execution && (execution.status === 'completed' || execution.status === 'failed')">
          <!-- checklist 多案例時顯示案例選擇器 -->
          <div v-if="!execution.source_case_id && caseResults.length > 1" class="case-selector">
            <label>選擇案例：</label>
            <select v-model="selectedReportCase" @change="checkReportAvailable">
              <option v-for="cr in caseResults" :key="cr.case_number" :value="cr.case_number">
                {{ cr.case_number }} — {{ cr.case_name }}
              </option>
            </select>
          </div>
          <iframe
            v-if="reportAvailable"
            :key="`report-${rfReportPrefix}`"
            :src="`/api/v1/executions/${executionId}/rf-report/${rfReportPrefix}report.html`"
            class="rf-iframe"
            title="RF 測試報告"
          />
          <div v-else class="rf-report-placeholder" data-testid="rf-report-missing">
            尚無 RF 測試報告{{ missingReason ? `：${missingReason}` : '' }}
          </div>
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
import { getExecution, getExecutionResults, exportReport, getRfReportStatus, streamExecution, type ExecutionRecord, type CaseResultItem } from '../services/executionApi'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const fetchError = ref<string | null>(null)
const execution = ref<ExecutionRecord | null>(null)
const caseResults = ref<CaseResultItem[]>([])
const selectedReportCase = ref<string>('')
const reportAvailable = ref(false)
const missingReason = ref('')

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
    } else if (execution.value.status === 'completed' || execution.value.status === 'failed') {
      // 終態才查報告是否存在，避免 iframe 直接渲染 404 JSON
      await checkReportAvailable()
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

function statusLabel(status: string): string {
  switch (status) {
    case 'passed': return '通過'
    case 'failed': return '失敗'
    case 'skipped': return '略過（無 RF 程式碼）'
    case 'error': return '錯誤'
    case 'timeout': return '逾時'
    default: return status
  }
}

async function checkReportAvailable() {
  reportAvailable.value = false
  missingReason.value = ''
  try {
    const res = await getRfReportStatus(executionId.value, `${rfReportPrefix.value}report.html`)
    reportAvailable.value = res.available
  } catch {
    reportAvailable.value = false
  }
  if (!reportAvailable.value) {
    // 優先顯示第一個失敗案例的原因，否則給通用說明
    const failed = caseResults.value.find((cr) => cr.failure_message)
    missingReason.value = failed?.failure_message || '報告尚未生成'
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
.case-results { margin-bottom: 16px; }
.case-results h2 { font-size: 16px; margin-bottom: 8px; }
.results-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.results-table th, .results-table td { padding: 8px; border-bottom: 1px solid #eee; text-align: left; }
.results-table th { background: #f5f5f5; }
.row-failed td, .row-error td { color: #b91c1c; }
.row-passed td:first-child { color: #047857; }
.failure-msg { max-width: 420px; word-break: break-word; white-space: pre-wrap; }
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
