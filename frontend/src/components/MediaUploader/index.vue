<template>
  <div class="media-uploader">
    <div
      class="upload-area"
      :class="{ 'drag-over': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
      @click="fileInput?.click()"
    >
      <input ref="fileInput" type="file" accept="image/*,video/*" class="hidden" @change="onFileChange" />
      <p>拖曳或點擊上傳圖片/影片</p>
      <p class="hint">圖片 ≤10MB｜影片 ≤100MB</p>
    </div>

    <div class="url-input">
      <input v-model="urlInput" type="url" placeholder="或輸入網址" @keyup.enter="addUrl" />
      <button type="button" :disabled="!urlInput" @click="addUrl">加入網址</button>
    </div>

    <ul v-if="attachments.length" class="attachment-list">
      <li v-for="(att, idx) in attachments" :key="att.id ?? idx">
        <span>{{ att.filename || att.url }}<em v-if="!att.persisted" class="pending">（待儲存）</em></span>
        <button type="button" @click="remove(idx)">移除</button>
      </li>
    </ul>

    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { caseApi } from '../../services/caseApi'

const props = defineProps<{ caseId?: string }>()
const emit = defineEmits<{ (e: 'uploaded', att: object): void }>()

interface AttachmentItem {
  id?: string
  filename?: string | null
  url?: string | null
  persisted: boolean
  file?: File // 僅 pending 檔案保留，待案例建立後上傳
}

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const urlInput = ref('')
const errorMsg = ref('')
const attachments = ref<AttachmentItem[]>([])

const IMAGE_MAX = 10 * 1024 * 1024
const VIDEO_MAX = 100 * 1024 * 1024

function validateFile(file: File): string | null {
  if (file.type.startsWith('image/') && file.size > IMAGE_MAX) return '圖片不得超過 10MB'
  if (file.type.startsWith('video/') && file.size > VIDEO_MAX) return '影片不得超過 100MB'
  if (!file.type.startsWith('image/') && !file.type.startsWith('video/')) return '不支援的檔案類型'
  return null
}

async function loadExisting(caseId: string) {
  try {
    const res = await caseApi.listAttachments(caseId)
    attachments.value = res.data.items.map((a) => ({
      id: a.id,
      filename: a.filename,
      url: a.url,
      persisted: true,
    }))
  } catch {
    // 靜默忽略；清單留空
  }
}

onMounted(() => {
  if (props.caseId) loadExisting(props.caseId)
})

// 編輯頁的 caseId 可能在掛載後才到位
watch(
  () => props.caseId,
  (id, prev) => {
    if (id && id !== prev) loadExisting(id)
  },
)

async function uploadFile(file: File) {
  const error = validateFile(file)
  if (error) { errorMsg.value = error; return }
  errorMsg.value = ''
  if (!props.caseId) {
    // 尚未建立案例：暫存實際檔案，待 flushPending 後上傳
    attachments.value.push({ filename: file.name, persisted: false, file })
    return
  }
  try {
    const res = await caseApi.uploadAttachment(props.caseId, file)
    attachments.value.push({ id: res.data.id, filename: res.data.filename, persisted: true })
    emit('uploaded', res.data)
  } catch (e: any) {
    errorMsg.value = e?.message || '上傳失敗'
  }
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.[0]) uploadFile(input.files[0])
  input.value = '' // 允許重新選同一檔案
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  const file = event.dataTransfer?.files[0]
  if (file) uploadFile(file)
}

async function addUrl() {
  if (!urlInput.value) return
  errorMsg.value = ''
  const url = urlInput.value
  if (!props.caseId) {
    attachments.value.push({ url, persisted: false })
    urlInput.value = ''
    return
  }
  try {
    const res = await caseApi.uploadAttachmentUrl(props.caseId, url)
    attachments.value.push({ id: res.data.id, url, persisted: true })
    emit('uploaded', res.data)
    urlInput.value = ''
  } catch (e: any) {
    errorMsg.value = e?.message || '加入網址失敗'
  }
}

async function remove(idx: number) {
  const att = attachments.value[idx]
  if (att.persisted && att.id && props.caseId) {
    try {
      await caseApi.deleteAttachment(props.caseId, att.id)
    } catch (e: any) {
      errorMsg.value = e?.message || '移除失敗'
      return
    }
  }
  attachments.value.splice(idx, 1)
}

/** 案例建立後，將暫存（未持久化）的附件上傳到新案例。 */
async function flushPending(caseId: string) {
  const pending = attachments.value.filter((a) => !a.persisted)
  for (const att of pending) {
    try {
      if (att.file) {
        const res = await caseApi.uploadAttachment(caseId, att.file)
        att.id = res.data.id
      } else if (att.url) {
        const res = await caseApi.uploadAttachmentUrl(caseId, att.url)
        att.id = res.data.id
      }
      att.persisted = true
      att.file = undefined
    } catch (e: any) {
      errorMsg.value = e?.message || '部分附件儲存失敗'
    }
  }
}

defineExpose({ flushPending })
</script>

<style scoped>
.upload-area { border: 2px dashed #ccc; padding: 20px; text-align: center; cursor: pointer; }
.drag-over { border-color: #4f46e5; background: #f0f0ff; }
.hidden { display: none; }
.hint { font-size: 12px; color: #888; }
.url-input { display: flex; gap: 8px; margin-top: 8px; }
.url-input input { flex: 1; padding: 4px 8px; border: 1px solid #ccc; }
.attachment-list { list-style: none; padding: 0; margin-top: 8px; }
.attachment-list li { display: flex; justify-content: space-between; padding: 4px; border-bottom: 1px solid #eee; }
.pending { color: #b45309; font-style: normal; font-size: 12px; margin-left: 6px; }
.error { color: red; font-size: 13px; }
</style>
