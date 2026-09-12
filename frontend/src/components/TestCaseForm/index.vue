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

    <!-- RF 程式碼上傳與預覽區塊：上傳控制永遠顯示（支援覆寫既有程式碼），有內容即顯示預覽 -->
    <div class="field">
      <label>RF 程式碼</label>
      <RFCodeUpload
        :case-id="caseId"
        @file-loaded="onRfFileLoaded"
        @file-cleared="onRfFileCleared"
        data-testid="rf-upload"
      />
      <RFCodePreview
        v-if="rfCode"
        :main-steps="effectiveMainSteps"
        :selected-model="selectedModel"
        :rf-code-override="rfCode"
        :case-id="caseId"
        :chat-mode="false"
        data-testid="rf-preview"
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
import RFCodeUpload from '../RFCodeUpload/index.vue'
import RFCodePreview from '../RFCodePreview/index.vue'
import { caseApi } from '../../services/caseApi'

const props = defineProps<{
  caseId?: string
  initialData?: Record<string, any>
  mainSteps?: string
  selectedModel?: string
}>()

const emit = defineEmits<{
  (e: 'saved', id: string): void
  (e: 'trial-run', executionId: string): void
  (e: 'update:main-steps', value: string): void
  (e: 'rf-buffered', content: string | null): void
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

/** Buffer for uploaded RF file content before case is created. */
const pendingRfContent = ref<string | null>(null)
/** RF code to display in preview (from upload or existing case). */
const rfCode = ref<string | null>(null)
/** Whether RF code has been saved to backend (persisted). */
const savedRfCode = ref(false)
const selectedModel = ref(props.selectedModel || '')

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
  // Load existing RF script if editing
  if (props.caseId) {
    try {
      const res = await caseApi.getRobotScript(props.caseId)
      rfCode.value = res.data.rf_code
      savedRfCode.value = true
    } catch {
      // no saved script yet
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
      // If there's pending RF content, upload it
      if (pendingRfContent.value) {
        await uploadPendingRfCode(props.caseId)
      }
      emit('saved', props.caseId)
    } else {
      const res = await caseApi.createCase(payload)
      // 建立案例前暫存的媒體附件／網址，於此一併上傳到新案例
      await mediaUploaderRef.value?.flushPending(res.data.id)
      // RF 程式碼由父層（CaseCreatePage.onSaved）統一持久化：
      // Tab1 上傳檔優先，其次 Tab2 AI 生成碼。不可在此直接上傳，
      // 否則 AI 生成碼會被無聲丟棄。
      emit('saved', res.data.id)
    }
  } catch (e: any) {
    saveError.value = e.message
  } finally {
    saving.value = false
  }
}

async function uploadPendingRfCode(caseId: string) {
  if (!pendingRfContent.value) return
  try {
    // Create a File object from the buffered content
    const file = new File([pendingRfContent.value], 'upload.robot', { type: 'text/plain' })
    const res = await caseApi.uploadRobotScript(caseId, file)
    rfCode.value = res.data.rf_code
    savedRfCode.value = true
    pendingRfContent.value = null
  } catch (e: any) {
    saveError.value = `RF 程式碼上傳失敗：${e.message}`
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

function onRfFileLoaded(content: string) {
  pendingRfContent.value = content
  rfCode.value = content
  savedRfCode.value = false
  // Let the creation page forward the buffered code to AI chat as context
  emit('rf-buffered', content)
}

function onRfFileCleared() {
  pendingRfContent.value = null
  rfCode.value = null
  savedRfCode.value = false
  emit('rf-buffered', null)
}

/** 取出暫存的上傳內容並清空（供建立頁在案例建立後統一儲存）。 */
function takePendingRfCode(): string | null {
  const content = pendingRfContent.value
  pendingRfContent.value = null
  return content
}

defineExpose({ takePendingRfCode })
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
