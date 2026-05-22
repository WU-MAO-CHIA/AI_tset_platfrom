<template>
  <form class="case-form" @submit.prevent="onSubmit">
    <div class="field">
      <label>案例編號 *</label>
      <input v-model="form.case_number" :disabled="!!caseId" required placeholder="TC-001" />
    </div>

    <div class="field">
      <label>名稱 *</label>
      <input v-model="form.name" required placeholder="測試案例名稱" />
    </div>

    <div class="field">
      <label>系統別</label>
      <input v-model="form.system_category" placeholder="auth, order, ..." />
    </div>

    <div class="field">
      <label>前置條件</label>
      <textarea v-model="form.precondition_steps" rows="2" placeholder="（選填）" />
    </div>

    <div class="field">
      <label>主要步驟 *</label>
      <textarea v-model="form.main_steps" rows="6" required placeholder="1. 開啟登入頁面&#10;2. 輸入帳號密碼" />
      <div class="ai-bar">
        <LLMModelSelector v-model="selectedModel" />
        <button type="button" :disabled="aiLoading || !form.main_steps" @click="onAiComplete">
          {{ aiLoading ? 'AI 補齊中...' : 'AI 補齊步驟' }}
        </button>
      </div>
      <p v-if="aiError" class="error">{{ aiError }}</p>
    </div>

    <div class="field">
      <label>描述</label>
      <input v-model="form.description" placeholder="（選填）測試目的說明" />
    </div>

    <div class="field">
      <label>媒體附件</label>
      <MediaUploader :case-id="caseId" @uploaded="onAttachmentUploaded" />
    </div>

    <div class="actions">
      <button type="submit" :disabled="saving">{{ saving ? '儲存中...' : '儲存案例' }}</button>
      <button v-if="caseId" type="button" :disabled="trialRunning" @click="onTrialRun">
        {{ trialRunning ? '試跑中...' : '立即試跑' }}
      </button>
    </div>
    <p v-if="saveError" class="error">{{ saveError }}</p>
  </form>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import MediaUploader from '../MediaUploader/index.vue'
import LLMModelSelector from '../LLMModelSelector/index.vue'
import { caseApi } from '../../services/caseApi'

const props = defineProps<{
  caseId?: string
  initialData?: Record<string, any>
}>()
const emit = defineEmits<{
  (e: 'saved', id: string): void
  (e: 'trial-run', executionId: string): void
}>()

const selectedModel = ref('claude-3-5-sonnet-20241022')

const form = reactive({
  case_number: '',
  name: '',
  main_steps: '',
  description: '',
  precondition_steps: '',
  system_category: '',
  tags: [] as string[],
})

const saving = ref(false)
const saveError = ref('')
const aiLoading = ref(false)
const aiError = ref('')
const trialRunning = ref(false)

onMounted(() => {
  if (props.initialData) Object.assign(form, props.initialData)
})

async function onSubmit() {
  saving.value = true
  saveError.value = ''
  try {
    if (props.caseId) {
      await caseApi.updateCase(props.caseId, { ...form, created_by: 'current_user' })
      emit('saved', props.caseId)
    } else {
      const res = await caseApi.createCase({ ...form, created_by: 'current_user' })
      emit('saved', res.data.id)
    }
  } catch (e: any) {
    saveError.value = e.message
  } finally {
    saving.value = false
  }
}

async function onAiComplete() {
  if (!form.main_steps) return
  aiLoading.value = true
  aiError.value = ''
  try {
    const payload = {
      partial_steps: form.main_steps,
      llm_model: selectedModel.value,
      description: form.description,
    }
    const res = props.caseId
      ? await caseApi.aiComplete(props.caseId, payload)
      : await caseApi.aiCompletePreview(payload)
    form.main_steps = res.data.completed_steps
  } catch (e: any) {
    aiError.value = e.message
  } finally {
    aiLoading.value = false
  }
}

async function onTrialRun() {
  if (!props.caseId) return
  trialRunning.value = true
  try {
    const res = await caseApi.trialRun(props.caseId)
    emit('trial-run', res.data.execution_id)
  } catch (e: any) {
    saveError.value = e.message
  } finally {
    trialRunning.value = false
  }
}

function onAttachmentUploaded(att: object) {
  // attachment added — no local state needed
}
</script>

<style scoped>
.case-form { display: flex; flex-direction: column; gap: 16px; max-width: 700px; }
.field { display: flex; flex-direction: column; gap: 4px; }
.field label { font-weight: 600; font-size: 14px; }
.field input, .field textarea, .field select { padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
.ai-bar { display: flex; gap: 8px; margin-top: 4px; }
.model-select { flex: 1; }
.actions { display: flex; gap: 12px; }
.actions button { padding: 8px 20px; border: none; border-radius: 4px; cursor: pointer; }
.actions button[type="submit"] { background: #4f46e5; color: white; }
.actions button:disabled { opacity: 0.6; cursor: not-allowed; }
.error { color: red; font-size: 13px; }
</style>
