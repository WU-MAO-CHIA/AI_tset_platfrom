<template>
  <div class="run-strip" role="img" :aria-label="summary">
    <span class="cells">
      <i v-for="(cell, idx) in cells" :key="idx" :class="cell.tone" :title="cell.title" />
    </span>
    <span v-if="runs.length" class="rate">{{ rateText }}</span>
    <span v-else class="rate">還沒執行過</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RecentRun } from '../../services/checklistApi'
import { formatDateTime } from '../../utils/format'

const props = withDefaults(defineProps<{ runs: RecentRun[]; limit?: number }>(), { limit: 10 })

type Tone = 'pass' | 'fail' | 'running' | 'queued' | 'neutral' | 'empty'

const ACTIVE = ['running', 'pending']
const FAILED = ['failed', 'error', 'interrupted']

function toneOf(run: RecentRun): Tone {
  if (run.status === 'running') return 'running'
  if (run.status === 'pending') return 'queued'
  if (run.status === 'cancelled') return 'neutral'
  if (FAILED.includes(run.status) || run.failed_count > 0) return 'fail'
  return 'pass'
}

const LABEL: Record<Tone, string> = {
  pass: '全部通過',
  fail: '有失敗',
  running: '執行中',
  queued: '排隊中',
  neutral: '已取消',
  empty: '',
}

// API 回傳新到舊；條狀圖由左（舊）到右（新），不足的格數補在左邊
const cells = computed(() => {
  const runs = props.runs.slice(0, props.limit).reverse()
  const filled = runs.map((run) => {
    const tone = toneOf(run)
    const detail = run.total_count ? `，${run.passed_count}/${run.total_count} 通過` : ''
    return { tone, title: `${formatDateTime(run.started_at ?? run.finished_at)}：${LABEL[tone]}${detail}` }
  })
  const padding = Array.from({ length: props.limit - filled.length }, () => ({ tone: 'empty' as Tone, title: '' }))
  return [...padding, ...filled]
})

const finished = computed(() => props.runs.slice(0, props.limit).filter((r) => !ACTIVE.includes(r.status)))
const passed = computed(() => finished.value.filter((r) => toneOf(r) === 'pass').length)

const rateText = computed(() => {
  if (props.runs[0] && ACTIVE.includes(props.runs[0].status)) return LABEL[toneOf(props.runs[0])]
  return `${passed.value}/${finished.value.length}`
})

const summary = computed(() =>
  props.runs.length
    ? `最近完成的 ${finished.value.length} 次執行中，${passed.value} 次全部通過`
    : '還沒執行過',
)
</script>

<style scoped>
.run-strip { display: inline-flex; align-items: center; gap: 10px; }
.cells { display: inline-flex; gap: 3px; }
.cells i { width: 8px; height: 20px; border-radius: 2px; background: var(--pass); }
.cells i.fail { background: var(--fail); }
.cells i.running { background: repeating-linear-gradient(135deg, var(--running) 0 3px, #a08ceb 3px 6px); }
.cells i.queued { background: var(--queued); }
.cells i.neutral { background: var(--ink-faint); }
.cells i.empty { background: var(--line); }
.rate { font-size: var(--fs-12); color: var(--ink-muted); white-space: nowrap; }
</style>
