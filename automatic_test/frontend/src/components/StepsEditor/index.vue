<template>
  <div class="steps-editor">
    <label class="field-label">主要步驟 *</label>
    <textarea
      :value="mainSteps"
      rows="10"
      required
      placeholder="1. 開啟登入頁面&#10;2. 輸入帳號密碼&#10;3. 點擊登入按鈕"
      @input="$emit('update:mainSteps', ($event.target as HTMLTextAreaElement).value)"
    />
    <div class="ai-bar">
      <LLMModelSelector :model-value="selectedModel" @update:model-value="$emit('update:selectedModel', $event)" />
      <button
        type="button"
        data-testid="ai-complete-btn"
        :disabled="!mainSteps.trim() || aiLoading"
        @click="onAiComplete"
      >
        {{ aiLoading ? 'AI 補齊中...' : 'AI 補齊步驟' }}
      </button>
    </div>
    <p v-if="aiError" class="error">{{ aiError }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import LLMModelSelector from '../LLMModelSelector/index.vue'
import { caseApi } from '../../services/caseApi'

const props = defineProps<{
  mainSteps: string
  selectedModel: string
  description?: string
}>()

const emit = defineEmits<{
  (e: 'update:mainSteps', value: string): void
  (e: 'update:selectedModel', value: string): void
}>()

const aiLoading = ref(false)
const aiError = ref('')

async function onAiComplete() {
  if (!props.mainSteps.trim()) return
  aiLoading.value = true
  aiError.value = ''
  try {
    const res = await caseApi.aiCompletePreview({
      partial_steps: props.mainSteps,
      llm_model: props.selectedModel,
      description: props.description ?? '',
    })
    emit('update:mainSteps', res.data.completed_steps)
  } catch (e: any) {
    aiError.value = e.message ?? 'AI 補齊失敗，請稍後重試'
  } finally {
    aiLoading.value = false
  }
}
</script>

<style scoped>
.steps-editor { display: flex; flex-direction: column; gap: 8px; }
.field-label { font-weight: 600; font-size: 14px; }
textarea { padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; resize: vertical; }
.ai-bar { display: flex; gap: 8px; }
.ai-bar button { padding: 6px 14px; border: none; border-radius: 4px; cursor: pointer; background: #7c3aed; color: white; font-size: 13px; }
.ai-bar button:disabled { opacity: 0.5; cursor: not-allowed; }
.error { color: red; font-size: 13px; margin: 0; }
</style>
