<template>
  <div class="rf-preview">
    <div class="rf-header">
      <span class="rf-title">Robot Framework 程式碼預覽</span>
      <div class="rf-actions">
        <button
          v-if="!chatMode"
          type="button"
          data-testid="rf-translate-btn"
          :disabled="!mainSteps.trim() || loading"
          @click="onTranslate"
        >
          {{ loading ? '翻譯中...' : '翻譯為 Robot Framework' }}
        </button>
        <button
          v-if="caseId && rfCode"
          type="button"
          class="btn-save"
          data-testid="rf-save-btn"
          :disabled="saving"
          @click="onSave"
        >
          {{ saving ? '儲存中...' : (saved ? '✓ 已儲存' : '儲存 RF 程式碼') }}
        </button>
        <!-- Phase 27: Trial run button -->
        <button
          v-if="caseId && chatMode"
          type="button"
          class="btn-trial-run"
          data-testid="rf-trial-run-btn"
          :disabled="!rfCode || trialRunning"
          :title="!rfCode ? 'RF 程式碼為空，請先透過 Chat 生成程式碼' : ''"
          @click="onTrialRun"
        >
          {{ trialRunning ? '試跑中...' : '立即試跑' }}
        </button>
      </div>
    </div>
    <p v-if="error && !chatMode" data-testid="rf-error" class="error">{{ error }}</p>
    <p v-if="saveError" class="error">{{ saveError }}</p>
    <div v-if="rfCode" class="code-block">
      <pre><code>{{ rfCode }}</code></pre>
    </div>
    <div v-else class="placeholder">
      <span v-if="chatMode">向 AI 描述測試功能，每次 AI 回應後 RF 腳本將自動更新。</span>
      <span v-else>點擊「翻譯為 Robot Framework」按鈕，AI 將自動將測試步驟轉換為可執行的 Robot Framework 腳本。</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { caseApi } from '../../services/caseApi'

const props = defineProps<{
  mainSteps: string
  selectedModel: string
  rfCodeOverride?: string
  chatMode?: boolean
  caseId?: string
}>()

const emit = defineEmits<{ (e: 'trial-started', executionId: string): void }>()

const loading = ref(false)
const translatedCode = ref('')
const error = ref('')
const saving = ref(false)
const saved = ref(false)
const saveError = ref('')
const trialRunning = ref(false)

const rfCode = computed(() => props.rfCodeOverride || translatedCode.value)

watch(() => props.rfCodeOverride, (val) => {
  if (val) {
    error.value = ''
    saved.value = false
  }
})

onMounted(async () => {
  if (props.caseId && !props.rfCodeOverride) {
    try {
      const res = await caseApi.getRobotScript(props.caseId)
      translatedCode.value = res.data.rf_code
    } catch {
      // no saved script yet — that's fine
    }
  }
})

async function onTranslate() {
  if (!props.mainSteps.trim()) return
  loading.value = true
  error.value = ''
  saved.value = false
  try {
    const res = await caseApi.previewRfCode({
      main_steps: props.mainSteps,
      llm_model: props.selectedModel,
    })
    translatedCode.value = res.data.rf_code
  } catch {
    error.value = '翻譯失敗，請稍後重試'
  } finally {
    loading.value = false
  }
}

async function onSave() {
  if (!props.caseId || !rfCode.value) return
  saving.value = true
  saveError.value = ''
  try {
    await caseApi.saveRobotScript(props.caseId, rfCode.value)
    saved.value = true
  } catch {
    saveError.value = '儲存失敗，請稍後重試'
  } finally {
    saving.value = false
  }
}

// Phase 27: Trial run from RF code preview
async function onTrialRun() {
  if (!props.caseId || !rfCode.value) return
  trialRunning.value = true
  const startTime = Date.now()
  try {
    const res = await caseApi.runTrialFromCode(props.caseId, rfCode.value)
    emit('trial-started', res.data.execution_id)
  } catch (err) {
    console.error('Trial run failed:', err)
  } finally {
    trialRunning.value = false
    const elapsed = Date.now() - startTime
    // SC-011: Verify execution within 60 seconds
    if (elapsed > 60000) {
      console.warn(`Trial run took ${elapsed}ms, exceeds 60s SLA`)
    }
  }
}
</script>

<style scoped>
.rf-preview { display: flex; flex-direction: column; gap: 10px; }
.rf-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.rf-title { font-weight: 600; font-size: 14px; }
.rf-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.rf-header button { padding: 6px 14px; border: none; border-radius: 4px; cursor: pointer; background: #0f766e; color: white; font-size: 13px; }
.rf-header button:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-save { background: #4f46e5 !important; }
.btn-trial-run { background: #a855f7 !important; }
.code-block { background: #1e1e2e; border-radius: 6px; padding: 12px; overflow-x: auto; }
pre { margin: 0; }
code { font-family: 'Courier New', monospace; font-size: 13px; color: #cdd6f4; white-space: pre; }
.placeholder { font-size: 13px; color: #888; padding: 12px; background: #f8f8f8; border-radius: 6px; border: 1px dashed #ccc; }
.error { color: red; font-size: 13px; margin: 0; }
</style>
