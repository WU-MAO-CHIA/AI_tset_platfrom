<template>
  <div class="execution-progress">
    <div class="progress-header">
      <h3>執行進度</h3>
      <span class="status-badge" :class="store.executionStatus">{{ store.executionStatus }}</span>
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
import { computed, onMounted, onUnmounted } from 'vue'
import { useExecutionStore } from '../../stores/executionStore'
import { streamExecution } from '../../services/executionApi'

const props = defineProps<{ executionId: string }>()
const emit = defineEmits<{ (e: 'completed'): void }>()

const store = useExecutionStore()

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
    if (event.event === 'execution_completed') {
      emit('completed')
    }
  })
})

onUnmounted(() => {
  evtSource?.close()
})
</script>
