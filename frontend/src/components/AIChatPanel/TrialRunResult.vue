<template>
  <div class="trial-result-container">
    <!-- Status Badge -->
    <div class="status-badge" :class="`status-${result.status}`">
      {{ statusLabel() }}
    </div>

    <!-- Elapsed Time -->
    <div class="elapsed-time">
      執行時間：{{ (result.elapsed_ms / 1000).toFixed(2) }}s
    </div>

    <!-- RF Report Link -->
    <a v-if="result.execution_id" class="report-link" :href="`/executions/${result.execution_id}`" target="_blank">
      查看完整測試報告 →
    </a>

    <!-- Error Message -->
    <div v-if="result.status !== 'passed' && result.error_message" class="error-message">
      <strong>失敗訊息：</strong>
      <p>{{ result.error_message }}</p>
    </div>

    <!-- Screenshots -->
    <div v-if="result.screenshot_paths && result.screenshot_paths.length > 0" class="screenshots">
      <strong>截圖：</strong>
      <div class="screenshot-gallery">
        <div v-for="(path, idx) in result.screenshot_paths" :key="idx" class="screenshot-item">
          <img
            :src="`/api/v1/media/${path}`"
            :alt="`Screenshot ${idx + 1}`"
            class="screenshot-thumb"
            @click="showFullImage(path)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface TrialResult {
  execution_id?: string
  status: 'passed' | 'failed' | 'timeout' | 'error'
  elapsed_ms: number
  error_message?: string
  screenshot_paths?: string[]
}

const props = defineProps<{
  result: TrialResult
}>()

const statusLabel = () => {
  switch (props.result.status) {
    case 'passed':
      return '✓ 通過'
    case 'failed':
      return '✗ 失敗'
    case 'timeout':
      return '⏱ 逾時'
    case 'error':
      return '⚠ 錯誤'
    default:
      return props.result.status
  }
}

function showFullImage(path: string) {
  window.open(`/api/v1/media/${path}`, '_blank')
}
</script>

<style scoped>
.trial-result-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 6px;
}

.status-badge {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 14px;
  width: fit-content;
}

.status-passed {
  background: #dcfce7;
  color: #166534;
}

.status-failed {
  background: #fee2e2;
  color: #991b1b;
}

.status-timeout {
  background: #fef3c7;
  color: #92400e;
}

.status-error {
  background: #fca5a5;
  color: #7f1d1d;
}

.elapsed-time {
  font-size: 13px;
  color: #666;
}

.report-link {
  font-size: 13px;
  color: #3b82f6;
  text-decoration: none;
  width: fit-content;
}

.report-link:hover {
  text-decoration: underline;
}

.error-message {
  padding: 8px;
  background: #fff3cd;
  border-left: 3px solid #ff9800;
  border-radius: 4px;
  font-size: 13px;
}

.error-message p {
  margin: 4px 0 0 0;
}

.screenshots {
  font-size: 13px;
}

.screenshot-gallery {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.screenshot-item {
  flex-shrink: 0;
}

.screenshot-thumb {
  max-width: 120px;
  max-height: 80px;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid #ddd;
  transition: transform 0.2s;
}

.screenshot-thumb:hover {
  transform: scale(1.05);
}
</style>
