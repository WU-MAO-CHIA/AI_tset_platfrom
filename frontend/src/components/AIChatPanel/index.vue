<template>
  <div class="ai-chat-panel">
    <div class="chat-header">
      <div class="rf-context-indicator" v-if="hasRfCode">
        <span class="indicator-dot" :class="contextMode"></span>
        <span class="indicator-text">RF 程式碼：{{ contextModeLabel }}</span>
        <select
          v-model="contextMode"
          class="context-mode-select"
          data-testid="rf-context-mode-select"
        >
          <option value="full">完整</option>
          <option value="summary">摘要</option>
          <option value="none">無</option>
        </select>
      </div>
      <div v-else class="rf-context-indicator no-rf">
        <span class="indicator-text">無 RF 程式碼上下文</span>
      </div>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-hint">
        <p>向 AI 描述你想測試的功能，AI 將協助你產生測試步驟與 Robot Framework 腳本。</p>
      </div>
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="chat-bubble"
        :class="[
          msg.role === 'user' ? 'bubble-user' : 'bubble-assistant',
          msg.type === 'trial_run_result' ? 'bubble-trial-result' : ''
        ]"
      >
        <!-- Phase 27: Trial run result rendering -->
        <div v-if="msg.type === 'trial_run_result'" class="bubble-content trial-result">
          <TrialRunResult :result="parseTrialResult(msg.content)" />
        </div>
        <div v-else class="bubble-content">{{ displayContent(msg) }}</div>
      </div>
      <div v-if="loading" class="chat-bubble bubble-assistant loading-bubble">
        <div class="bubble-content">AI 思考中...</div>
      </div>
      <div v-if="trialInProgress" class="chat-bubble bubble-assistant loading-bubble">
        <div class="bubble-content">試跑執行中，完成後將自動顯示結果...</div>
      </div>
    </div>

    <div class="chat-input-area">
      <textarea
        v-model="inputText"
        placeholder="描述你想測試的功能..."
        rows="3"
        @keydown.ctrl.enter.prevent="sendMessage"
      />
      <button
        data-testid="send-btn"
        :disabled="!inputText.trim() || loading"
        @click="sendMessage"
      >
        送出
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import { caseApi } from '../../services/caseApi'
import { streamExecution } from '../../services/executionApi'
import type { ChatMessage } from '../../services/caseApi'
import TrialRunResult from './TrialRunResult.vue'

const props = defineProps<{
  caseId?: string
  selectedModel: string
  watchExecutionId?: string
  elementCatalog?: Array<Record<string, any>>
  rfCodeContext?: string | null
}>()

const emit = defineEmits<{
  (e: 'rf-updated', rfCode: string): void
}>()

const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const loading = ref(false)
const trialInProgress = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)

/** RF context mode: full, summary, none */
const contextMode = ref<'full' | 'summary' | 'none'>('full')

/** Check if case has RF code available */
const hasRfCode = ref(false)

const contextModeLabel = computed(() => {
  switch (contextMode.value) {
    case 'full': return '完整模式'
    case 'summary': return '摘要模式'
    case 'none': return '無上下文'
  }
})

let evtSource: EventSource | null = null

async function loadHistory() {
  if (!props.caseId) return
  try {
    const res = await caseApi.getChatHistory(props.caseId)
    messages.value = res.data.messages
    scrollToBottom()
  } catch {
    // no history yet
  }
}

async function checkRfCodeAvailability() {
  if (!props.caseId) return
  try {
    const res = await caseApi.getRobotScript(props.caseId)
    hasRfCode.value = !!res.data.rf_code
  } catch {
    hasRfCode.value = false
  }
}

onMounted(async () => {
  await loadHistory()
  await checkRfCodeAvailability()
})

watch(() => props.watchExecutionId, (executionId) => {
  if (!executionId) return
  evtSource?.close()
  trialInProgress.value = true
  evtSource = streamExecution(executionId, (data) => {
    const event = data as { event?: string }
    if (event.event === 'execution_completed' || event.event === 'execution_error') {
      evtSource = null
      trialInProgress.value = false
      loadHistory()
    }
  })
})

onUnmounted(() => evtSource?.close())

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  // Build stateless history BEFORE pushing: backend already appends the
  // current message, so including it here would duplicate the turn.
  const history = messages.value
    .filter((m) => (m.role === 'user' || m.role === 'assistant') && m.type !== 'trial_run_result')
    .map((m) => ({ role: m.role as string, content: m.content }))
  messages.value.push({ role: 'user', content: text, created_at: new Date().toISOString() })
  inputText.value = ''
  loading.value = true
  scrollToBottom()

  try {
    let assistant_message: string
    let rf_code: string
    if (props.caseId) {
      const res = await caseApi.chatWithAI(props.caseId, text, props.selectedModel, contextMode.value, props.elementCatalog)
      ;({ assistant_message, rf_code } = res.data)
    } else {
      // Case-creation page: stateless chat, history kept locally, nothing persisted
      const res = await caseApi.chatPreview({
        message: text,
        llm_model: props.selectedModel,
        rf_context_mode: contextMode.value,
        history,
        catalog: props.elementCatalog ?? null,
        rf_code: props.rfCodeContext ?? null,
      })
      ;({ assistant_message, rf_code } = res.data)
    }
    messages.value.push({ role: 'assistant', content: assistant_message, created_at: new Date().toISOString() })
    if (rf_code) {
      emit('rf-updated', rf_code)
    }
  } catch (e: any) {
    const detail = e?.message ? `：${e.message}` : ''
    messages.value.push({ role: 'assistant', content: `發生錯誤${detail}，請稍後再試。`, created_at: new Date().toISOString() })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function displayContent(msg: ChatMessage): string {
  if (msg.role !== 'assistant') return msg.content
  const rfIdx = msg.content.indexOf('---RF_CODE---')
  return rfIdx !== -1 ? msg.content.slice(0, rfIdx).trim() : msg.content
}

// Phase 27: Parse trial run result from JSON content
function parseTrialResult(content: string): any {
  try {
    return JSON.parse(content)
  } catch {
    return { status: 'error', error_message: 'Failed to parse trial result' }
  }
}

async function scrollToBottom() {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}
</script>

<style scoped>
.ai-chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 8px 8px 0 0;
  border-bottom: 1px solid #e9ecef;
}

.rf-context-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #495057;
}

.rf-context-indicator.no-rf {
  color: #adb5bd;
}

.indicator-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.indicator-dot.full { background: #28a745; }
.indicator-dot.summary { background: #ffc107; }
.indicator-dot.none { background: #dc3545; }

.context-mode-select {
  padding: 2px 8px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  background: white;
  font-size: 12px;
  color: #495057;
  cursor: pointer;
}

.context-mode-select:focus {
  outline: none;
  border-color: #80bdff;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 12px;
}

.empty-hint {
  color: #6c757d;
  text-align: center;
  padding: 32px 16px;
  font-size: 14px;
}

.chat-bubble {
  display: flex;
  max-width: 85%;
}

.bubble-user {
  align-self: flex-end;
}

.bubble-assistant {
  align-self: flex-start;
}

.bubble-content {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.bubble-user .bubble-content {
  background: #3b82f6;
  color: white;
  border-bottom-right-radius: 4px;
}

.bubble-assistant .bubble-content {
  background: #e9ecef;
  color: #212529;
  border-bottom-left-radius: 4px;
}

.loading-bubble .bubble-content {
  color: #6c757d;
  font-style: italic;
}

.chat-input-area {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.chat-input-area textarea {
  flex: 1;
  resize: none;
  padding: 10px;
  border: 1px solid #ced4da;
  border-radius: 8px;
  font-size: 14px;
}

.chat-input-area button {
  padding: 10px 20px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  white-space: nowrap;
}

.chat-input-area button:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

/* 滾動條樣式 */
.chat-messages::-webkit-scrollbar {
  width: 8px;
}

.chat-messages::-webkit-scrollbar-track {
  background: #f8f9fa;
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}
</style>
