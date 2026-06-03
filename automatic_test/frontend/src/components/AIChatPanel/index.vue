<template>
  <div class="ai-chat-panel">
    <div class="chat-messages" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-hint">
        <p>向 AI 描述你想測試的功能，AI 將協助你產生測試步驟與 Robot Framework 腳本。</p>
      </div>
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="chat-bubble"
        :class="msg.role === 'user' ? 'bubble-user' : 'bubble-assistant'"
      >
        <div class="bubble-content">{{ msg.content }}</div>
      </div>
      <div v-if="loading" class="chat-bubble bubble-assistant loading-bubble">
        <div class="bubble-content">AI 思考中...</div>
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
import { ref, onMounted, nextTick } from 'vue'
import { caseApi } from '../../services/caseApi'
import type { ChatMessage } from '../../services/caseApi'

const props = defineProps<{
  caseId?: string
  selectedModel: string
}>()

const emit = defineEmits<{
  (e: 'rf-updated', rfCode: string): void
}>()

const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const loading = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)

onMounted(async () => {
  if (props.caseId) {
    try {
      const res = await caseApi.getChatHistory(props.caseId)
      messages.value = res.data.messages
      scrollToBottom()
    } catch {
      // no history yet
    }
  }
})

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text, created_at: new Date().toISOString() })
  inputText.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const res = await caseApi.chatWithAI(props.caseId ?? '', text, props.selectedModel)
    const { assistant_message, rf_code } = res.data
    messages.value.push({ role: 'assistant', content: assistant_message, created_at: new Date().toISOString() })
    if (rf_code) {
      emit('rf-updated', rf_code)
    }
  } catch {
    messages.value.push({ role: 'assistant', content: '發生錯誤，請稍後再試。', created_at: new Date().toISOString() })
  } finally {
    loading.value = false
    scrollToBottom()
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
</style>
