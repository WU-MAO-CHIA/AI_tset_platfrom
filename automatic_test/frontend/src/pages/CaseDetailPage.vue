<template>
  <div class="page" v-if="caseData">
    <div class="page-header">
      <h1>{{ caseData.case_number }} — {{ caseData.name }}</h1>
      <div class="actions">
        <button v-if="!editing" @click="startEdit">編輯</button>
        <template v-else>
          <button class="btn-save-edit" @click="saveFromPageHeader">儲存案例</button>
          <button class="btn-cancel" @click="cancelEdit">取消</button>
        </template>
        <button v-if="!editing" @click="onTrialRun" :disabled="trialRunning">
          {{ trialRunning ? '試跑中...' : '立即試跑' }}
        </button>
      </div>
    </div>

    <!-- 編輯模式：Tab 分頁結構（與 CaseCreatePage 相同） -->
    <template v-if="editing">
      <div class="tabs">
        <button
          class="tab-btn"
          :class="{ active: editTab === 'basic' }"
          @click="editTab = 'basic'"
        >
          基本資訊
        </button>
        <button
          class="tab-btn"
          :class="{ active: editTab === 'steps' }"
          @click="editTab = 'steps'"
        >
          測試步驟
        </button>
      </div>

      <!-- Tab 1：基本資訊 -->
      <div v-show="editTab === 'basic'" class="tab-content">
        <TestCaseForm
          :case-id="caseData.id"
          :initial-data="editInitialData"
          :main-steps="mainSteps"
          :selected-model="selectedModel"
          @update:main-steps="mainSteps = $event"
          @saved="onSaved"
          @trial-run="onTrialRunFromForm"
        />
      </div>

      <!-- Tab 2：測試步驟（左：AI Chat，右：RF 預覽） -->
      <div v-show="editTab === 'steps'" class="tab-content split-layout">
        <section class="left-col">
          <AIChatPanel
            :case-id="caseData.id"
            :selected-model="selectedModel"
            @rf-updated="rfCode = $event"
          />
        </section>
        <section class="right-col">
          <RFCodePreview
            :main-steps="mainSteps"
            :selected-model="selectedModel"
            :rf-code-override="rfCode"
            :chat-mode="true"
          />
        </section>
      </div>
    </template>

    <!-- 檢視模式：Tab 分頁結構 -->
    <template v-else>
      <div class="tabs">
        <button
          class="tab-btn"
          :class="{ active: viewTab === 'basic' }"
          @click="viewTab = 'basic'"
        >
          基本資訊
        </button>
        <button
          class="tab-btn"
          :class="{ active: viewTab === 'steps' }"
          @click="viewTab = 'steps'"
        >
          測試步驟
        </button>
      </div>

      <!-- Tab 1：基本資訊（唯讀） -->
      <div v-show="viewTab === 'basic'" class="tab-content">
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
      </div>

      <!-- Tab 2：測試步驟（唯讀：AI 對話歷史 + RF 程式碼預覽） -->
      <div v-show="viewTab === 'steps'" class="tab-content split-layout">
        <section class="left-col">
          <h2 style="font-size:16px;font-weight:600;margin-bottom:12px;">AI 對話歷史</h2>
          <div v-if="chatMessages.length === 0" class="empty-chat">尚無對話紀錄</div>
          <div v-else class="chat-history">
            <div
              v-for="(msg, idx) in chatMessages"
              :key="idx"
              class="chat-bubble"
              :class="msg.role"
            >
              <span class="bubble-role">{{ msg.role === 'user' ? '使用者' : 'AI' }}</span>
              <p>{{ chatDisplayText(msg) }}</p>
            </div>
          </div>
        </section>
        <section class="right-col">
          <h2 style="font-size:16px;font-weight:600;margin-bottom:12px;">最新 RF 程式碼（唯讀）</h2>
          <div v-if="rfCode" class="rf-readonly">
            <pre class="rf-code">{{ rfCode }}</pre>
          </div>
          <div v-else class="empty-chat">尚無 RF 程式碼（請先透過 AI 對話生成）</div>
        </section>
      </div>
    </template>

    <div class="section" v-show="!editing">
      <h2>測試資料匯入</h2>
      <FileImporter :case-id="caseData.id" />
    </div>

    <div class="section" v-show="!editing">
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
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { caseApi, type TestCaseDetail } from '../services/caseApi'
import FileImporter from '../components/FileImporter/index.vue'
import TestCaseForm from '../components/TestCaseForm/index.vue'
import AIChatPanel from '../components/AIChatPanel/index.vue'
import RFCodePreview from '../components/RFCodePreview/index.vue'

const route = useRoute()
const router = useRouter()
const caseId = route.params.id as string

const caseData = ref<TestCaseDetail | null>(null)
const history = ref<any[]>([])
const historyLoaded = ref(false)
const trialRunning = ref(false)
const editing = ref(false)
const editTab = ref<'basic' | 'steps'>('basic')
const viewTab = ref<'basic' | 'steps'>('basic')
const mainSteps = ref('')
const selectedModel = ref('claude-sonnet-4-6')
const rfCode = ref('')
const chatMessages = ref<Array<{ role: string; content: string; created_at: string }>>([])

const editInitialData = computed(() => caseData.value ? { ...caseData.value } : undefined)

onMounted(async () => {
  const res = await caseApi.getCase(caseId)
  caseData.value = res.data

  // Restore chat history and last RF code on page load
  try {
    const histRes = await caseApi.getChatHistory(caseId)
    chatMessages.value = histRes.data.messages ?? []
    if (histRes.data.messages.length > 0) {
      const lastMessage = histRes.data.messages[histRes.data.messages.length - 1]
      if (lastMessage.role === 'assistant' && lastMessage.content.includes('---RF_CODE---')) {
        const rfIdx = lastMessage.content.indexOf('---RF_CODE---')
        const endIdx = lastMessage.content.indexOf('---END---')
        if (rfIdx !== -1 && endIdx !== -1) {
          rfCode.value = lastMessage.content.slice(rfIdx + 13, endIdx).trim()
        }
      }
    }
  } catch {
    // Silently fail; rfCode remains empty if no chat history
  }
})

function startEdit() {
  mainSteps.value = caseData.value?.main_steps ?? ''
  editTab.value = 'basic'
  editing.value = true
  // rfCode was already restored from chat history in onMounted; keep it.
}

function cancelEdit() {
  editing.value = false
}

async function onSaved(_id: string) {
  const res = await caseApi.getCase(caseId)
  caseData.value = res.data
  editing.value = false
}

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

function onTrialRunFromForm(executionId: string) {
  router.push(`/executions/${executionId}`)
}

function chatDisplayText(msg: { role: string; content: string }) {
  if (msg.role !== 'assistant') return msg.content
  const rfIdx = msg.content.indexOf('---RF_CODE---')
  return rfIdx !== -1 ? msg.content.slice(0, rfIdx).trim() : msg.content
}

function saveFromPageHeader() {
  const submitBtn = document.querySelector('.case-form button[type="submit"]') as HTMLButtonElement
  if (submitBtn && !submitBtn.disabled) {
    submitBtn.click()
  }
}
</script>

<style scoped>
.page { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
h1 { font-size: 20px; }
.actions { display: flex; gap: 8px; }
.btn-cancel { background: #e2e8f0; color: #475569; }

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  border-bottom: 2px solid #e5e7eb;
}

.tab-btn {
  padding: 10px 20px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  color: #6b7280;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.15s;
}

.tab-btn.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
  font-weight: 600;
}

.tab-content { min-height: 400px; }

.split-layout {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 24px;
  align-items: start;
  height: calc(100vh - 220px);
}

.left-col, .right-col {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.btn-save-edit {
  background: #4f46e5;
  color: white;
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
}

.btn-save-edit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 767px) {
  .split-layout { grid-template-columns: 1fr; height: auto; }
}

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

.chat-history { display: flex; flex-direction: column; gap: 12px; overflow-y: auto; max-height: calc(100vh - 300px); }
.chat-bubble { padding: 10px 14px; border-radius: 8px; max-width: 90%; font-size: 14px; }
.chat-bubble.user { background: #eff6ff; align-self: flex-end; }
.chat-bubble.assistant { background: #f9fafb; border: 1px solid #e5e7eb; align-self: flex-start; }
.bubble-role { font-size: 11px; font-weight: 600; color: #6b7280; display: block; margin-bottom: 4px; }
.empty-chat { color: #9ca3af; font-size: 14px; padding: 24px 0; }
.rf-readonly { background: #1e1e1e; border-radius: 6px; padding: 16px; overflow: auto; max-height: calc(100vh - 300px); }
.rf-code { color: #d4d4d4; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; white-space: pre-wrap; margin: 0; }
</style>
