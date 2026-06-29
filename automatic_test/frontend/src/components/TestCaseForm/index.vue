<template>
  <form class="case-form" @submit.prevent="onSubmit">
    <!-- 編輯時顯示自動生成的案例編號（唯讀）；建立時由後端自動生成，無需輸入 -->
    <div v-if="caseId && initialData?.case_number" class="field">
      <label>案例編號</label>
      <input :value="initialData.case_number" disabled />
    </div>

    <div class="field">
      <label>名稱 *</label>
      <input v-model="form.name" required placeholder="測試案例名稱" />
    </div>

    <div class="field">
      <label>系統別</label>
      <select v-model="form.system_category">
        <option value="">（不指定）</option>
        <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
      </select>
    </div>

    <div class="field">
      <label>描述</label>
      <input v-model="form.description" placeholder="（選填）測試目的說明" />
    </div>

    <div class="field">
      <label>前置條件</label>
      <textarea v-model="form.precondition_steps" rows="2" placeholder="（選填）" />
    </div>

    <!-- 主要步驟：總是顯示，支援雙向綁定 -->
    <div class="field">
      <label>主要步驟 *</label>
      <textarea
        :value="effectiveMainSteps"
        @input="handleMainStepsInput"
        rows="6"
        required
        placeholder="1. 開啟登入頁面&#10;2. 輸入帳號密碼"
      />
    </div>

    <div class="field">
      <label>媒體附件</label>
      <MediaUploader ref="mediaUploaderRef" :case-id="caseId" @uploaded="onAttachmentUploaded" />
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
import { ref, reactive, computed, onMounted } from 'vue'
import MediaUploader from '../MediaUploader/index.vue'
import { caseApi } from '../../services/caseApi'

const props = defineProps<{
  caseId?: string
  initialData?: Record<string, any>
  mainSteps?: string
}>()

const emit = defineEmits<{
  (e: 'saved', id: string): void
  (e: 'trial-run', executionId: string): void
  (e: 'update:main-steps', value: string): void
}>()

/** True when CaseCreatePage provides mainSteps via prop (two-column layout). */
const externalSteps = computed(() => props.mainSteps !== undefined)

/** Used only when parent does NOT pass mainSteps (e.g. CaseDetailPage edit). */
const internalMainSteps = ref('')

const effectiveMainSteps = computed(() =>
  externalSteps.value ? props.mainSteps! : internalMainSteps.value
)

const form = reactive({
  name: '',
  description: '',
  precondition_steps: '',
  system_category: '',
  tags: [] as string[],
})

const saving = ref(false)
const saveError = ref('')
const trialRunning = ref(false)
const categories = ref<string[]>([])
const mediaUploaderRef = ref<InstanceType<typeof MediaUploader> | null>(null)

onMounted(async () => {
  try {
    const res = await caseApi.listCategories()
    categories.value = res.data.items
  } catch {
    // silently ignore; select will be empty
  }
  if (props.initialData) {
    Object.assign(form, props.initialData)
    if (!externalSteps.value && props.initialData.main_steps) {
      internalMainSteps.value = props.initialData.main_steps
    }
  }
})

async function onSubmit() {
  saving.value = true
  saveError.value = ''
  try {
    const payload = { ...form, main_steps: effectiveMainSteps.value, created_by: 'current_user' }
    if (props.caseId) {
      await caseApi.updateCase(props.caseId, payload)
      emit('saved', props.caseId)
    } else {
      const res = await caseApi.createCase(payload)
      // 建立案例前暫存的媒體附件／網址，於此一併上傳到新案例
      await mediaUploaderRef.value?.flushPending(res.data.id)
      emit('saved', res.data.id)
    }
  } catch (e: any) {
    saveError.value = e.message
  } finally {
    saving.value = false
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

function onAttachmentUploaded(_att: object) {}

function handleMainStepsInput(e: Event) {
  const value = (e.target as HTMLTextAreaElement).value
  internalMainSteps.value = value
  if (externalSteps.value) {
    emit('update:main-steps', value)
  }
}
</script>

<style scoped>
.case-form { display: flex; flex-direction: column; gap: 16px; }
.field { display: flex; flex-direction: column; gap: 4px; }
.field label { font-weight: 600; font-size: 14px; }
.field input, .field textarea { padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
.actions { display: flex; gap: 12px; }
.actions button { padding: 8px 20px; border: none; border-radius: 4px; cursor: pointer; }
.actions button[type="submit"] { background: #4f46e5; color: white; }
.actions button:disabled { opacity: 0.6; cursor: not-allowed; }
.error { color: red; font-size: 13px; }
</style>
