<template>
  <div class="execution-progress">
    <div class="progress-header">
      <h3>執行進度</h3>
      <span class="status-badge" :class="store.executionStatus">{{ statusLabel }}</span>
    </div>

    <div v-if="store.executionStatus === 'pending'" class="queue-notice" data-testid="queue-notice">
      <span>{{ queueText }}</span>
      <button
        v-if="auth.isEditor"
        class="btn-secondary"
        data-testid="cancel-execution"
        :disabled="cancelling"
        @click="handleCancel"
      >
        {{ cancelling ? '取消中...' : '取消排隊' }}
      </button>
    </div>

    <div class="overall-progress">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPercent + '%' }" />
      </div>
      <span class="progress-text">{{ store.completedCases }} / {{ store.totalCases }}</span>
    </div>

    <div class="stats">
      <span class="stat pass">通過 {{ store.passedCases }}</span>
      <span class="stat fail">失敗 {{ store.failedCases }}</span>
      <span v-if="store.runningCases.length > 0" class="stat running">
        執行中：{{ store.runningCases.join(', ') }}
      </span>
    </div>

    <div v-if="store.errorMessage" class="error-message">
      {{ store.errorMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useAuthStore } from '../../stores/authStore'
import { useExecutionStore } from '../../stores/executionStore'
import { cancelExecution, isTerminalEvent, streamExecution } from '../../services/executionApi'

const props = defineProps<{ executionId: string }>()
const emit = defineEmits<{ (e: 'completed'): void }>()

const store = useExecutionStore()
const auth = useAuthStore()
const cancelling = ref(false)

const STATUS_LABELS: Record<string, string> = {
  idle: '待命',
  pending: '排隊中',
  running: '執行中',
  completed: '完成',
  failed: '失敗',
  error: '錯誤',
  interrupted: '已中斷',
  cancelled: '已取消',
}

const statusLabel = computed(() => STATUS_LABELS[store.executionStatus] ?? store.executionStatus)

const queueText = computed(() => {
  if (store.queueAhead === null) return '排隊中'
  if (store.queueAhead === 0) return '排隊中（下一個就輪到）'
  return `排隊中（前面還有 ${store.queueAhead} 筆）`
})

async function handleCancel() {
  cancelling.value = true
  try {
    await cancelExecution(props.executionId)
    // 狀態由串流的 execution_cancelled 事件更新
  } catch (e: any) {
    // 409：剛好被 worker 領走開始執行，畫面會隨串流事件切成執行中
    if (e?.response?.status !== 409) {
      store.errorMessage = e?.message || '取消失敗'
    }
  } finally {
    cancelling.value = false
  }
}

const progressPercent = computed(() => {
  if (!store.totalCases) return 0
  return Math.round((store.completedCases / store.totalCases) * 100)
})

let evtSource: EventSource | null = null

onMounted(() => {
  store.startExecution(props.executionId)
  evtSource = streamExecution(props.executionId, (data) => {
    store.handleSSEEvent(data as Record<string, unknown>)
    const event = data as { event?: string }
    // 連線失敗也會送出 execution_error，那種情況留在本頁顯示錯誤
    if (isTerminalEvent(data) && event.event !== 'execution_error') {
      emit('completed')
    }
  })
})

onUnmounted(() => {
  evtSource?.close()
})
</script>

<style scoped>
.queue-notice {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0;
  padding: 10px 14px;
  border-radius: 6px;
  background: #fef3c7;
  color: #92400e;
}
.btn-secondary { background: #e5e7eb; color: #374151; padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
.btn-secondary:disabled { opacity: 0.6; cursor: default; }
</style>
