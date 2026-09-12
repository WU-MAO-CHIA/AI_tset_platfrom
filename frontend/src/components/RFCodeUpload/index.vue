<template>
  <div class="rf-upload">
    <label class="upload-label">
      <input
        type="file"
        ref="fileInput"
        accept=".robot"
        @change="onFileSelected"
        class="file-input"
        data-testid="rf-upload-input"
      />
      <span class="upload-text">
        <svg v-if="!file" class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        <span v-if="file">{{ file.name }} ({{ formatSize(file.size) }})</span>
        <span v-else>點擊或拖曳上傳 .robot 檔案</span>
      </span>
    </label>

    <p v-if="error" class="error" data-testid="rf-upload-error">{{ error }}</p>

    <div v-if="file" class="upload-actions">
      <button
        type="button"
        class="btn-clear"
        @click="clearFile"
        data-testid="rf-upload-clear"
      >
        清除
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, defineEmits } from 'vue'
import { validateFileExtension, validateFileSize, decodeFileContent, getFileValidationError } from '../../utils/rfUpload'

const props = defineProps<{
  caseId?: string
}>()

const emit = defineEmits<{
  (e: 'file-loaded', content: string): void
  (e: 'file-cleared'): void
}>()

const file = ref<File | null>(null)
const error = ref('')

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  return `${(bytes / 1024).toFixed(1)} KB`
}

async function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const selectedFile = input.files?.[0]
  if (!selectedFile) return

  // Client-side validation
  const validationError = getFileValidationError(selectedFile)
  if (validationError) {
    error.value = validationError
    file.value = null
    input.value = ''
    return
  }

  try {
    const content = await decodeFileContent(selectedFile)
    file.value = selectedFile
    error.value = ''
    emit('file-loaded', content)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '讀取檔案失敗'
    file.value = null
  }
}

function clearFile() {
  file.value = null
  error.value = ''
  emit('file-cleared')
}
</script>

<style scoped>
.rf-upload { display: flex; flex-direction: column; gap: 8px; }
.upload-label {
  display: flex; align-items: center; gap: 12px;
  padding: 16px; border: 2px dashed #ccc; border-radius: 8px;
  cursor: pointer; transition: border-color 0.2s, background 0.2s;
}
.upload-label:hover { border-color: #4f46e5; background: #f8fafc; }
.upload-label.dragover { border-color: #4f46e5; background: #eef2ff; }
.file-input { display: none; }
.upload-text { font-size: 14px; color: #666; flex: 1; }
.upload-icon { width: 24px; height: 24px; color: #999; flex-shrink: 0; }
.error { color: #dc2626; font-size: 13px; margin: 0; }
.upload-actions { display: flex; justify-content: flex-end; }
.btn-clear {
  padding: 6px 14px; border: none; border-radius: 4px;
  background: #ef4444; color: white; font-size: 13px; cursor: pointer;
}
.btn-clear:hover { background: #dc2626; }
</style>