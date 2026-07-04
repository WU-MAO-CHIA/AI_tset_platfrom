<template>
  <div class="page" v-if="caseData">
    <div class="page-header">
      <h1>{{ caseData.case_number }} — {{ caseData.name }}</h1>
      <div class="actions">
        <button v-if="!editing && authStore.isEditor" @click="startEdit">編輯</button>
        <template v-else-if="editing">
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

        <!-- 測試資料區塊（編輯模式） -->
        <div class="section test-data-section">
          <h2>測試資料</h2>
          <table class="test-data-table" v-if="editTestData.length > 0">
            <thead>
              <tr>
                <th>易讀名稱</th>
                <th>RF 變數</th>
                <th>預設值</th>
                <th>說明</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in editTestData" :key="idx">
                <td>
                  <input
                    v-model="row.field_name"
                    class="td-input"
                    placeholder="易讀名稱"
                    @input="onFieldNameInput(idx)"
                  />
                </td>
                <td>
                  <input
                    v-model="row.rf_variable"
                    class="td-input"
                    placeholder="${易讀名稱}"
                    @input="row._rf_auto = false"
                  />
                </td>
                <td>
                  <input
                    v-model="row.field_value"
                    class="td-input"
                    placeholder="預設值"
                  />
                </td>
                <td>
                  <input
                    v-model="row.description"
                    class="td-input"
                    placeholder="說明"
                  />
                </td>
                <td>
                  <button class="btn-del-row" @click="deleteTestDataRow(idx)" title="刪除此列">✕</button>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty td-empty">（無測試資料）</div>
          <button class="btn-add-row" @click="addTestDataRow">＋ 新增列</button>
        </div>
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
            :case-id="caseData.id"
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

        <!-- 測試資料區塊（唯讀） -->
        <div class="section">
          <h2>測試資料</h2>
          <div v-if="!caseData.test_data || caseData.test_data.length === 0" class="empty">（無測試資料）</div>
          <table v-else class="test-data-table">
            <thead>
              <tr>
                <th>易讀名稱</th>
                <th>RF 變數</th>
                <th>預設值</th>
                <th>說明</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="td in caseData.test_data" :key="td.id">
                <td>{{ td.field_name }}</td>
                <td>{{ td.rf_variable ?? '' }}</td>
                <td>{{ td.field_value ?? '' }}</td>
                <td>{{ td.description ?? '' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="section">
          <h2>媒體附件</h2>
          <ul v-if="attachments.length" class="attachment-list">
            <li v-for="att in attachments" :key="att.id">
              <a v-if="att.attachment_type === 'url'" :href="att.url ?? undefined" target="_blank" rel="noopener">
                🔗 {{ att.url }}
              </a>
              <a
                v-else-if="att.file_path"
                :href="`/api/v1/media/attachments/${caseId}/${attachmentFilename(att.file_path)}`"
                target="_blank"
                rel="noopener"
                :download="att.filename ?? undefined"
              >
                {{ att.attachment_type === 'video' ? '🎬' : '📷' }} {{ att.filename }}
              </a>
              <span v-else>📎 {{ att.filename }}</span>
            </li>
          </ul>
          <p v-else class="empty">（無）</p>
        </div>
      </div>

      <!-- Tab 2：測試步驟（唯讀）：左右分欄，各自有滾輪 -->
      <div v-show="viewTab === 'steps'" class="tab-content steps-split">
        <!-- 左：AI 對話歷史 -->
        <div class="steps-left">
          <div class="steps-panel-header">AI 對話歷史</div>
          <div class="steps-panel-body">
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
          </div>
        </div>

        <!-- 右：RF 程式碼 -->
        <div class="steps-right rf-panel">
          <div class="rf-panel-header">最新 RF 程式碼（唯讀）</div>
          <div class="steps-panel-body">
            <div v-if="rfCode" class="rf-readonly">
              <pre class="rf-code">{{ rfCode }}</pre>
            </div>
            <div v-else class="rf-empty">尚無 RF 程式碼（請先透過 AI 對話生成）</div>
          </div>
        </div>
      </div>
    </template>

    <div class="section" v-show="!editing">
      <h2>測試資料匯入</h2>
      <FileImporter :case-id="caseData.id" @imported="reloadTestData" />
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
import { caseApi, type TestCaseDetail, type AttachmentRecord, type TestDataItem } from '../services/caseApi'
import FileImporter from '../components/FileImporter/index.vue'
import TestCaseForm from '../components/TestCaseForm/index.vue'
import AIChatPanel from '../components/AIChatPanel/index.vue'
import RFCodePreview from '../components/RFCodePreview/index.vue'
import { useAuthStore } from '../stores/authStore'

const authStore = useAuthStore()

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
const attachments = ref<AttachmentRecord[]>([])

interface EditTestDataRow {
  id?: string
  field_name: string
  rf_variable: string
  field_value: string
  description: string
  _rf_auto: boolean
}

const editTestData = ref<EditTestDataRow[]>([])

function initEditTestData(testData: TestDataItem[]) {
  editTestData.value = testData.map(td => ({
    id: td.id,
    field_name: td.field_name,
    rf_variable: td.rf_variable ?? '',
    field_value: td.field_value ?? '',
    description: td.description ?? '',
    _rf_auto: false,
  }))
}

function onFieldNameInput(idx: number) {
  const row = editTestData.value[idx]
  if (row._rf_auto || !row.rf_variable) {
    row.rf_variable = row.field_name ? `\${${row.field_name}}` : ''
    row._rf_auto = true
  }
}

function addTestDataRow() {
  editTestData.value.push({
    field_name: '',
    rf_variable: '',
    field_value: '',
    description: '',
    _rf_auto: true,
  })
}

function deleteTestDataRow(idx: number) {
  editTestData.value.splice(idx, 1)
}

async function loadAttachments() {
  try {
    const res = await caseApi.listAttachments(caseId)
    attachments.value = res.data.items
  } catch {
    attachments.value = []
  }
}

async function reloadTestData() {
  const res = await caseApi.getCase(caseId)
  caseData.value = res.data
}

const editInitialData = computed(() => caseData.value ? { ...caseData.value } : undefined)

onMounted(async () => {
  const res = await caseApi.getCase(caseId)
  caseData.value = res.data
  await loadAttachments()

  try {
    const scriptRes = await caseApi.getRobotScript(caseId)
    rfCode.value = scriptRes.data.rf_code
  } catch {
    // 404 = no script saved yet
  }

  try {
    const histRes = await caseApi.getChatHistory(caseId)
    chatMessages.value = histRes.data.messages ?? []
    if (!rfCode.value && histRes.data.messages.length > 0) {
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
    // Silently fail
  }
})

const RF_BUILTINS = new Set([
  'CURDIR', 'EXECDIR', 'TEMPDIR', 'OUTPUT_DIR', 'OUTPUT_FILE',
  'LOG_FILE', 'REPORT_FILE', 'DEBUG_FILE', 'SUITE_NAME', 'SUITE_SOURCE',
  'SUITE_DOCUMENTATION', 'SUITE_STATUS', 'SUITE_MESSAGE', 'TEST_NAME',
  'TEST_DOCUMENTATION', 'TEST_STATUS', 'TEST_MESSAGE', 'PREV_TEST_NAME',
  'PREV_TEST_STATUS', 'PREV_TEST_MESSAGE', 'LOG_LEVEL',
  'True', 'False', 'None', 'null', 'EMPTY', 'SPACE',
])

function extractRFVariables(rfCode: string): string[] {
  const seen = new Set<string>()
  const result: string[] = []
  for (const m of rfCode.matchAll(/\$\{([^}]+)\}/g)) {
    const name = m[1]
    if (!RF_BUILTINS.has(name) && !seen.has(name.toUpperCase())) {
      seen.add(name.toUpperCase())
      result.push(name)
    }
  }
  return result
}

async function startEdit() {
  mainSteps.value = caseData.value?.main_steps ?? ''
  initEditTestData(caseData.value?.test_data ?? [])
  editTab.value = 'basic'
  editing.value = true

  try {
    const scriptRes = await caseApi.getRobotScript(caseId)
    const vars = extractRFVariables(scriptRes.data.rf_code)
    const existingKeys = new Set(
      editTestData.value.map(r => (r.rf_variable || `\${${r.field_name}}`).toUpperCase())
    )
    for (const name of vars) {
      const rfVar = `\${${name}}`
      if (!existingKeys.has(rfVar.toUpperCase())) {
        editTestData.value.push({
          field_name: name,
          rf_variable: rfVar,
          field_value: '',
          description: '',
          _rf_auto: false,
        })
        existingKeys.add(rfVar.toUpperCase())
      }
    }
  } catch {
    // 404 or no RF script yet: silently skip
  }
}

function cancelEdit() {
  editing.value = false
}

async function onSaved(_id: string) {
  // save test_data changes (full replace)
  await caseApi.updateCase(caseId, {
    created_by: 'current_user',
    test_data: editTestData.value.map((row, idx) => ({
      field_name: row.field_name,
      rf_variable: row.rf_variable || null,
      field_value: row.field_value || null,
      description: row.description || null,
      row_index: idx,
    })),
  })
  const res = await caseApi.getCase(caseId)
  caseData.value = res.data
  await loadAttachments()
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

function attachmentFilename(filePath: string): string {
  return filePath.replace(/\\/g, '/').split('/').pop() ?? filePath
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

/* 編輯模式：測試步驟 split */
.split-layout {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 24px;
  height: calc(100vh - 220px);
  overflow: hidden;
}

.left-col, .right-col {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.right-col {
  overflow-y: auto;
}

/* 檢視模式：測試步驟 split（各自獨立滾輪） */
.steps-split {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 24px;
  height: calc(100vh - 220px);
}

.steps-left,
.steps-right {
  display: flex;
  flex-direction: column;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  min-height: 0;
}

.steps-right.rf-panel {
  border-color: transparent;
}

.steps-panel-header {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  padding: 10px 16px;
  background: #f3f4f6;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.steps-panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
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

.btn-save-edit:disabled { opacity: 0.6; cursor: not-allowed; }

@media (max-width: 767px) {
  .split-layout, .steps-split { grid-template-columns: 1fr; height: auto; }
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
.attachment-list { list-style: none; padding: 0; margin: 0; }
.attachment-list li { padding: 4px 0; font-size: 14px; }
.attachment-list a { color: #4f46e5; text-decoration: none; }
.attachment-list a:hover { text-decoration: underline; }

.chat-history { display: flex; flex-direction: column; gap: 12px; }
.chat-bubble { padding: 10px 14px; border-radius: 8px; max-width: 90%; font-size: 14px; }
.chat-bubble.user { background: #eff6ff; align-self: flex-end; }
.chat-bubble.assistant { background: #f9fafb; border: 1px solid #e5e7eb; align-self: flex-start; }
.bubble-role { font-size: 11px; font-weight: 600; color: #6b7280; display: block; margin-bottom: 4px; }
.empty-chat { color: #9ca3af; font-size: 14px; }

.rf-panel { background: #1e1e2e; }
.rf-panel-header { background: rgba(0,0,0,0.25); color: #7c8097; font-size: 12px; font-weight: 600; letter-spacing: 0.5px; padding: 10px 16px; border-bottom: 1px solid rgba(255,255,255,0.06); flex-shrink: 0; }
.rf-panel .steps-panel-body { background: #1e1e2e; }
.rf-readonly { }
.rf-code { color: #cdd6f4; background: transparent; font-family: 'Courier New', monospace; font-size: 13px; white-space: pre-wrap; margin: 0; line-height: 1.6; }
.rf-empty { color: #7c8097; font-size: 13px; }

/* 測試資料表格 */
.test-data-section { margin-top: 24px; }

.test-data-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.test-data-table th {
  background: #f3f4f6;
  font-weight: 600;
  color: #374151;
  padding: 8px 10px;
  text-align: left;
  border-bottom: 2px solid #e5e7eb;
}
.test-data-table td {
  padding: 4px 6px;
  border-bottom: 1px solid #e5e7eb;
}

.td-input {
  width: 100%;
  padding: 5px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
  box-sizing: border-box;
}
.td-input:focus { outline: none; border-color: #6366f1; }

.btn-del-row {
  background: none;
  border: none;
  color: #dc2626;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 6px;
  border-radius: 3px;
}
.btn-del-row:hover { background: #fee2e2; }

.btn-add-row {
  margin-top: 8px;
  background: none;
  border: 1px dashed #9ca3af;
  color: #6b7280;
  cursor: pointer;
  font-size: 13px;
  padding: 5px 14px;
  border-radius: 4px;
}
.btn-add-row:hover { border-color: #4f46e5; color: #4f46e5; }

.td-empty { font-size: 13px; margin-bottom: 8px; }
</style>
