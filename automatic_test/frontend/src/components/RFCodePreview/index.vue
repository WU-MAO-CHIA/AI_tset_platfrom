<template>
  <div class="rf-preview">
    <div class="rf-header">
      <span class="rf-title">Robot Framework 程式碼預覽</span>
      <button
        type="button"
        data-testid="rf-translate-btn"
        :disabled="!mainSteps.trim() || loading"
        @click="onTranslate"
      >
        {{ loading ? '翻譯中...' : '翻譯為 Robot Framework' }}
      </button>
    </div>
    <p v-if="error" data-testid="rf-error" class="error">{{ error }}</p>
    <div v-if="rfCode" class="code-block">
      <pre><code>{{ rfCode }}</code></pre>
    </div>
    <div v-else-if="!error" class="placeholder">
      點擊「翻譯為 Robot Framework」按鈕，AI 將自動將測試步驟轉換為可執行的 Robot Framework 腳本。
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { caseApi } from '../../services/caseApi'

const props = defineProps<{
  mainSteps: string
  selectedModel: string
  rfCodeOverride?: string
}>()

const loading = ref(false)
const translatedCode = ref('')
const error = ref('')

// AI Chat override takes precedence over manually translated code
const rfCode = computed(() => props.rfCodeOverride || translatedCode.value)

watch(() => props.rfCodeOverride, (val) => {
  if (val) error.value = ''
})

async function onTranslate() {
  if (!props.mainSteps.trim()) return
  loading.value = true
  error.value = ''
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
</script>

<style scoped>
.rf-preview { display: flex; flex-direction: column; gap: 10px; }
.rf-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.rf-title { font-weight: 600; font-size: 14px; }
.rf-header button { padding: 6px 14px; border: none; border-radius: 4px; cursor: pointer; background: #0f766e; color: white; font-size: 13px; }
.rf-header button:disabled { opacity: 0.5; cursor: not-allowed; }
.code-block { background: #1e1e2e; border-radius: 6px; padding: 12px; overflow-x: auto; }
pre { margin: 0; }
code { font-family: 'Courier New', monospace; font-size: 13px; color: #cdd6f4; white-space: pre; }
.placeholder { font-size: 13px; color: #888; padding: 12px; background: #f8f8f8; border-radius: 6px; border: 1px dashed #ccc; }
.error { color: red; font-size: 13px; margin: 0; }
</style>
