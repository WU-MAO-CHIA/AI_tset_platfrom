<template>
  <div class="page" v-if="caseData">
    <div class="page-header">
      <h1>{{ caseData.case_number }} — {{ caseData.name }}</h1>
      <div class="actions">
        <RouterLink :to="`/cases/${caseData.id}`">
          <button>編輯</button>
        </RouterLink>
        <button @click="onTrialRun" :disabled="trialRunning">
          {{ trialRunning ? '試跑中...' : '立即試跑' }}
        </button>
      </div>
    </div>

    <div class="section">
      <h2>基本資訊</h2>
      <dl>
        <dt>系統別</dt><dd>{{ caseData.system_category || '-' }}</dd>
        <dt>版本</dt><dd>v{{ caseData.version }}</dd>
        <dt>建立者</dt><dd>{{ caseData.created_by }}</dd>
        <dt>更新時間</dt><dd>{{ caseData.updated_at }}</dd>
      </dl>
    </div>

    <div class="section">
      <h2>前置條件</h2>
      <pre>{{ caseData.precondition_steps || '（無）' }}</pre>
    </div>

    <div class="section">
      <h2>主要步驟</h2>
      <pre>{{ caseData.main_steps }}</pre>
    </div>

    <div class="section">
      <h2>測試資料匯入</h2>
      <FileImporter :case-id="caseData.id" />
    </div>

    <div class="section">
      <h2>執行歷史</h2>
      <button @click="loadHistory">載入執行歷史</button>
      <table v-if="history.length" class="history-table">
        <thead><tr><th>執行 ID</th><th>狀態</th><th>開始時間</th><th>通過</th><th>失敗</th></tr></thead>
        <tbody>
          <tr v-for="h in history" :key="h.execution_id" class="clickable" @click="$router.push(`/results/${h.execution_id}`)">
            <td>{{ h.execution_id.slice(0, 8) }}...</td>
            <td>{{ h.status }}</td>
            <td>{{ h.started_at }}</td>
            <td>{{ h.passed_count }}</td>
            <td>{{ h.failed_count }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else-if="historyLoaded" class="empty">尚無執行紀錄</p>
    </div>
  </div>
  <p v-else>載入中...</p>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { caseApi, type TestCaseDetail } from '../services/caseApi'
import FileImporter from '../components/FileImporter/index.vue'

const route = useRoute()
const router = useRouter()
const caseId = route.params.id as string

const caseData = ref<TestCaseDetail | null>(null)
const history = ref<any[]>([])
const historyLoaded = ref(false)
const trialRunning = ref(false)

onMounted(async () => {
  const res = await caseApi.getCase(caseId)
  caseData.value = res.data
})

async function loadHistory() {
  const res = await caseApi.getExecutionHistory(caseId)
  history.value = res.data.items
  historyLoaded.value = true
}

async function onTrialRun() {
  trialRunning.value = true
  try {
    const res = await caseApi.trialRun(caseId)
    router.push(`/executions/${res.data.execution_id}`)
  } finally {
    trialRunning.value = false
  }
}
</script>

<style scoped>
.page { max-width: 900px; margin: 0 auto; padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
h1 { font-size: 20px; }
.actions { display: flex; gap: 8px; }
.section { margin-bottom: 32px; }
.section h2 { font-size: 16px; font-weight: 600; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 4px; }
dl { display: grid; grid-template-columns: 100px 1fr; gap: 4px 16px; }
dt { font-weight: 600; color: #555; }
pre { white-space: pre-wrap; background: #f9f9f9; padding: 12px; border-radius: 4px; font-size: 14px; }
.history-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.history-table th, .history-table td { padding: 8px; border-bottom: 1px solid #eee; }
.clickable { cursor: pointer; }
.clickable:hover { background: #f0f4ff; }
.empty { color: #888; }
</style>
