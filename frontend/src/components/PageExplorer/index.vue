<template>
  <div class="page-explorer">
    <div class="explorer-form">
      <div class="field">
        <label>目標網址 *</label>
        <input
          v-model="url"
          type="url"
          placeholder="https://example.com/login"
          :disabled="running"
          data-testid="explore-url"
        />
      </div>
      <div class="field">
        <label>目標元素 *（每行一個，例如：帳號輸入框、登入按鈕）</label>
        <textarea
          v-model="goalsText"
          rows="3"
          :disabled="running"
          placeholder="帳號輸入框&#10;密碼輸入框&#10;登入按鈕"
          data-testid="explore-goals"
        />
      </div>
      <div class="field">
        <label>登入變數（選填，逗號分隔；值取自測試資料，絕不會顯示）</label>
        <input
          v-model="variablesText"
          placeholder="${USERNAME}, ${PASSWORD}"
          :disabled="running"
          data-testid="explore-variables"
        />
      </div>
      <div class="actions">
        <button
          type="button"
          :disabled="running || !canLaunch"
          @click="launch"
          data-testid="explore-launch-btn"
        >
          {{ running ? `探索中…（第 ${steps} 步）` : '開始探索' }}
        </button>
        <span v-if="status" class="status" :data-testid="'explore-status-' + status">
          狀態：{{ statusLabel }}
        </span>
      </div>
      <p v-if="error" class="error" data-testid="explore-error">{{ error }}</p>
      <p v-if="note" class="note">{{ note }}</p>
    </div>

    <div v-if="log.length" class="explore-log" data-testid="explore-log">
      <div class="log-title">探索過程</div>
      <ul>
        <li v-for="(entry, idx) in log" :key="idx">
          <span class="log-step">#{{ entry.step }}</span>
          <span class="log-action">{{ entry.action }}</span>
          <span v-if="entry.narrative" class="log-narrative">{{ entry.narrative }}</span>
        </li>
      </ul>
    </div>

    <div v-if="catalog.length" class="catalog">
      <div class="catalog-header">
        <span class="catalog-title">元素目錄（{{ foundCount }}/{{ catalog.length }} 找到）</span>
        <button type="button" class="btn-apply" :disabled="!foundCount" @click="applyCatalog" data-testid="explore-apply-btn">
          帶入 AI 對話
        </button>
      </div>
      <table class="catalog-table" data-testid="explore-catalog">
        <thead>
          <tr><th>目標</th><th>狀態</th><th>建議 locator</th><th>XPath</th><th>CSS</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="(el, idx) in catalog" :key="idx" :class="{ missing: el.status !== 'found' }">
            <td>{{ el.goal }}</td>
            <td>{{ el.status === 'found' ? '✓' : '✗' }}{{ el.note ? `（${el.note}）` : '' }}</td>
            <td><code>{{ el.recommended }}</code></td>
            <td><code>{{ el.xpath }}</code></td>
            <td><code>{{ el.css }}</code></td>
            <td>
              <button v-if="el.status === 'found'" type="button" class="btn-copy" @click="copy(el.xpath, idx)">
                {{ copiedIdx === idx ? '已複製' : '複製 XPath' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { caseApi, type ExploreElement } from '../../services/caseApi'

const props = defineProps<{ caseId: string }>()

const emit = defineEmits<{
  (e: 'catalog-ready', catalog: ExploreElement[]): void
}>()

const url = ref('')
const goalsText = ref('')
const variablesText = ref('')
const running = ref(false)
const status = ref('')
const steps = ref(0)
const log = ref<Array<{ step: number; action: string; narrative?: string }>>([])
const catalog = ref<ExploreElement[]>([])
const note = ref('')
const error = ref('')
const copiedIdx = ref<number | null>(null)

let pollTimer: ReturnType<typeof setInterval> | null = null

const canLaunch = computed(() => url.value.trim() !== '' && goalsText.value.trim() !== '')

const statusLabel = computed(() => {
  switch (status.value) {
    case 'running': return '探索中'
    case 'done': return '完成'
    case 'partial': return '部分完成（達步數上限）'
    case 'empty': return '未找到目標'
    case 'error': return '失敗'
    default: return status.value
  }
})

const foundCount = computed(() => catalog.value.filter((el) => el.status === 'found').length)

function parseVariables(): string[] {
  return variablesText.value.split(/[,，]/).map((v) => v.trim()).filter(Boolean)
}

async function launch() {
  if (!canLaunch.value || running.value) return
  running.value = true
  error.value = ''
  note.value = ''
  catalog.value = []
  log.value = []
  steps.value = 0
  status.value = 'running'
  try {
    const goals = goalsText.value.split('\n').map((g) => g.trim()).filter(Boolean)
    const res = await caseApi.explorePage(props.caseId, {
      url: url.value.trim(),
      goals,
      variables: parseVariables(),
    })
    poll(res.data.session_id)
  } catch (e: any) {
    error.value = e?.message || '啟動探索失敗'
    running.value = false
    status.value = ''
  }
}

function poll(sessionId: string) {
  stopPolling()
  // setTimeout chain (not setInterval): polls never overlap, and the first
  // poll fires immediately instead of after a full interval.
  const tick = async () => {
    let done = false
    try {
      const res = await caseApi.getExploreSession(props.caseId, sessionId)
      const s = res.data
      status.value = s.status
      steps.value = s.steps
      log.value = s.log ?? []
      if (['done', 'partial', 'empty', 'error'].includes(s.status)) {
        done = true
        running.value = false
        catalog.value = s.catalog ?? []
        note.value = s.note ?? ''
        if (s.status === 'error' && !s.note) error.value = '探索失敗，請稍後再試'
      }
    } catch (e: any) {
      done = true
      running.value = false
      error.value = e?.message || '查詢探索進度失敗'
    }
    if (!done) {
      pollTimer = setTimeout(tick, 2000)
    } else {
      pollTimer = null
    }
  }
  void tick()
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function copy(text: string, idx: number) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
  copiedIdx.value = idx
  setTimeout(() => { if (copiedIdx.value === idx) copiedIdx.value = null }, 1500)
}

function applyCatalog() {
  emit('catalog-ready', catalog.value.filter((el) => el.status === 'found'))
}

onUnmounted(stopPolling)
</script>

<style scoped>
.page-explorer { display: flex; flex-direction: column; gap: 16px; }
.explorer-form { display: flex; flex-direction: column; gap: 10px; }
.field { display: flex; flex-direction: column; gap: 4px; }
.field label { font-weight: 600; font-size: 14px; }
.field input, .field textarea { padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
.actions { display: flex; align-items: center; gap: 12px; }
.actions button { padding: 8px 20px; border: none; border-radius: 4px; cursor: pointer; background: #0f766e; color: white; }
.actions button:disabled { opacity: 0.6; cursor: not-allowed; }
.status { font-size: 13px; color: #374151; }
.error { color: red; font-size: 13px; }
.note { color: #374151; font-size: 13px; }
.explore-log { background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 6px; padding: 10px 14px; }
.log-title { font-size: 13px; font-weight: 600; margin-bottom: 6px; }
.explore-log ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; font-size: 13px; }
.log-step { color: #6b7280; margin-right: 6px; }
.log-action { font-family: monospace; background: #eef2ff; padding: 1px 6px; border-radius: 4px; margin-right: 6px; }
.log-narrative { color: #374151; }
.catalog-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.catalog-title { font-weight: 600; font-size: 14px; }
.btn-apply { padding: 6px 14px; border: none; border-radius: 4px; background: #4f46e5; color: white; cursor: pointer; }
.btn-apply:disabled { opacity: 0.6; cursor: not-allowed; }
.catalog-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.catalog-table th, .catalog-table td { padding: 6px 8px; border-bottom: 1px solid #eee; text-align: left; vertical-align: top; }
.catalog-table code { font-family: monospace; font-size: 12px; word-break: break-all; }
.catalog-table tr.missing { color: #9ca3af; }
.btn-copy { padding: 4px 10px; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; font-size: 12px; white-space: nowrap; }
</style>
