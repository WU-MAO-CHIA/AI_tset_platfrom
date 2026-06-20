<template>
  <div class="result-page">
    <div v-if="loading" class="loading">載入中...</div>

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

      <div class="main-tabs">
        <button
          v-for="tab in mainTabs"
          :key="tab.id"
          class="main-tab-btn"
          :class="{ active: activeMainTab === tab.id }"
          @click="activeMainTab = tab.id"
        >{{ tab.label }}</button>
      </div>

      <div v-show="activeMainTab === 'results'" class="tab-content">
        <ResultViewer :results="caseResults" />
      </div>

      <div v-show="activeMainTab === 'rf-report'" class="tab-content rf-report-tab">
        <template v-if="execution && (execution.status === 'completed' || execution.status === 'failed')">
          <div class="rf-sub-tabs">
            <button
              class="sub-tab-btn"
              :class="{ active: activeRfSubTab === 'log' }"
              @click="activeRfSubTab = 'log'"
            >執行日誌 (log.html)</button>
            <button
              class="sub-tab-btn"
              :class="{ active: activeRfSubTab === 'report' }"
              @click="activeRfSubTab = 'report'"
            >測試報告 (report.html)</button>
          </div>
          <iframe
            v-if="activeRfSubTab === 'log'"
            :src="`/api/v1/executions/${executionId}/rf-report/log.html`"
            class="rf-iframe"
            title="RF 執行日誌"
          />
          <iframe
            v-if="activeRfSubTab === 'report'"
            :src="`/api/v1/executions/${executionId}/rf-report/report.html`"
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
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getExecution, getExecutionResults, exportReport, type ExecutionRecord, type CaseResultItem } from '../services/executionApi'
import ResultViewer from '../components/ResultViewer/index.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const execution = ref<ExecutionRecord | null>(null)
const caseResults = ref<CaseResultItem[]>([])
const activeMainTab = ref<'results' | 'rf-report'>('results')
const activeRfSubTab = ref<'log' | 'report'>('log')

const executionId = computed(() => route.params.id as string)

const mainTabs = [
  { id: 'results' as const, label: '執行結果' },
  { id: 'rf-report' as const, label: 'RF 報告' },
]

async function fetchResults() {
  loading.value = true
  try {
    execution.value = await getExecution(executionId.value)
    const data = await getExecutionResults(executionId.value)
    caseResults.value = data.items
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
.main-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 2px solid #e0e0e0;
  margin-bottom: 16px;
}
.main-tab-btn {
  padding: 8px 20px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}
.main-tab-btn.active {
  color: #1976d2;
  border-bottom-color: #1976d2;
  font-weight: 600;
}
.tab-content {
  min-height: 200px;
}
.rf-report-tab {
  display: flex;
  flex-direction: column;
}
.rf-sub-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
}
.sub-tab-btn {
  padding: 6px 16px;
  border: 1px solid #ccc;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  color: #555;
}
.sub-tab-btn.active {
  background: #1976d2;
  color: #fff;
  border-color: #1976d2;
}
.rf-iframe {
  width: 100%;
  height: 80vh;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
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
.btn-secondary {
  padding: 8px 16px;
  background: #fff;
  color: #555;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
}
</style>
