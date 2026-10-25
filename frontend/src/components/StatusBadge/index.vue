<template>
  <span class="badge" :class="tone">{{ text }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

// 執行狀態對應的顏色與中文；顏色只在這裡決定，頁面不再各自定義
const STATUS: Record<string, { tone: string; label: string }> = {
  passed: { tone: 'badge-pass', label: '通過' },
  completed: { tone: 'badge-pass', label: '完成' },
  failed: { tone: 'badge-fail', label: '失敗' },
  error: { tone: 'badge-fail', label: '錯誤' },
  running: { tone: 'badge-running', label: '執行中' },
  pending: { tone: 'badge-queued', label: '排隊中' },
  queued: { tone: 'badge-queued', label: '排隊中' },
  cancelled: { tone: '', label: '已取消' },
  interrupted: { tone: 'badge-fail', label: '已中斷' },
}

const props = defineProps<{ status: string | null | undefined; label?: string }>()

const tone = computed(() => (props.status ? STATUS[props.status]?.tone ?? '' : ''))
const text = computed(() => props.label ?? (props.status ? STATUS[props.status]?.label ?? props.status : '未執行'))
</script>
