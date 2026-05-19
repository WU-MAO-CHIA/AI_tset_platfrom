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
      <button :disabled="!urlInput" @click="addUrl">加入網址</button>
    </div>

    <ul v-if="attachments.length" class="attachment-list">
      <li v-for="(att, idx) in attachments" :key="idx">
        <span>{{ att.filename || att.url }}</span>
        <button @click="remove(idx)">移除</button>
      </li>
    </ul>

    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { caseApi } from '../../services/caseApi'

const props = defineProps<{ caseId?: string }>()
const emit = defineEmits<{ (e: 'uploaded', att: object): void }>()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const urlInput = ref('')
const errorMsg = ref('')
const attachments = ref<Array<{ filename?: string; url?: string }>>([])

const IMAGE_MAX = 10 * 1024 * 1024
const VIDEO_MAX = 100 * 1024 * 1024

function validateFile(file: File): string | null {
  if (file.type.startsWith('image/') && file.size > IMAGE_MAX) return '圖片不得超過 10MB'
  if (file.type.startsWith('video/') && file.size > VIDEO_MAX) return '影片不得超過 100MB'
  if (!file.type.startsWith('image/') && !file.type.startsWith('video/')) return '不支援的檔案類型'
  return null
}

async function uploadFile(file: File) {
  const error = validateFile(file)
  if (error) { errorMsg.value = error; return }
  if (!props.caseId) {
    attachments.value.push({ filename: file.name })
    return
  }
  try {
    const res = await caseApi.uploadAttachment(props.caseId, file)
    attachments.value.push({ filename: res.data.filename })
    emit('uploaded', res.data)
    errorMsg.value = ''
  } catch (e: any) {
    errorMsg.value = e.message
  }
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.[0]) uploadFile(input.files[0])
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  const file = event.dataTransfer?.files[0]
  if (file) uploadFile(file)
}

async function addUrl() {
  if (!urlInput.value) return
  if (props.caseId) {
    try {
      await caseApi.uploadAttachmentUrl(props.caseId, urlInput.value)
    } catch {}
  }
  attachments.value.push({ url: urlInput.value })
  urlInput.value = ''
}

function remove(idx: number) {
  attachments.value.splice(idx, 1)
}
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
.error { color: red; font-size: 13px; }
</style>
