<template>
  <div class="file-importer">
    <div
      class="drop-zone"
      :class="{ active: isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
      @click="fileInput?.click()"
    >
      <input ref="fileInput" type="file" accept=".xlsx,.xls,.csv,.txt,.tsv" class="hidden" @change="onFileChange" />
      <p>拖曳或點擊上傳 Excel / CSV / 文字檔</p>
    </div>

    <div v-if="preview.length" class="preview">
      <h3>預覽（前 {{ preview.length }} 筆，共 {{ totalRows }} 筆）</h3>
      <table class="preview-table">
        <thead>
          <tr><th v-for="col in columns" :key="col">{{ col }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in preview" :key="i">
            <td v-for="col in columns" :key="col">{{ row[col] }}</td>
          </tr>
        </tbody>
      </table>
      <p v-for="w in warnings" :key="w" class="warning">⚠ {{ w }}</p>
      <button @click="confirmImport" :disabled="importing">{{ importing ? '匯入中...' : `確認匯入 ${totalRows} 筆` }}</button>
      <button @click="reset" style="margin-left:8px">取消</button>
    </div>

    <p v-if="importedCount !== null" class="success">✓ 成功匯入 {{ importedCount }} 筆測試資料</p>
    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { caseApi } from '../../services/caseApi'

const props = defineProps<{ caseId: string }>()
const emit = defineEmits<{ (e: 'imported', count: number): void }>()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const preview = ref<Record<string, string>[]>([])
const columns = ref<string[]>([])
const totalRows = ref(0)
const warnings = ref<string[]>([])
const importToken = ref('')
const importing = ref(false)
const importedCount = ref<number | null>(null)
const errorMsg = ref('')

async function processFile(file: File) {
  errorMsg.value = ''
  importedCount.value = null
  try {
    const res = await caseApi.importTestData(props.caseId, file)
    const data = res.data as any
    preview.value = data.preview
    columns.value = data.columns
    totalRows.value = data.total_rows
    warnings.value = data.warnings || []
    importToken.value = data.import_token
  } catch (e: any) {
    errorMsg.value = e.message
  }
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.[0]) processFile(input.files[0])
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  const file = event.dataTransfer?.files[0]
  if (file) processFile(file)
}

async function confirmImport() {
  importing.value = true
  try {
    const res = await caseApi.confirmImportTestData(props.caseId, importToken.value)
    const data = res.data as any
    importedCount.value = data.imported_count
    emit('imported', data.imported_count)
    reset()
  } catch (e: any) {
    errorMsg.value = e.message
  } finally {
    importing.value = false
  }
}

function reset() {
  preview.value = []
  columns.value = []
  totalRows.value = 0
  warnings.value = []
  importToken.value = ''
}
</script>

<style scoped>
.drop-zone { border: 2px dashed #ccc; padding: 20px; text-align: center; cursor: pointer; border-radius: 4px; }
.drop-zone.active { border-color: #4f46e5; background: #f0f0ff; }
.hidden { display: none; }
.preview { margin-top: 12px; }
.preview h3 { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
.preview-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.preview-table th, .preview-table td { padding: 6px 8px; border: 1px solid #eee; }
.preview-table th { background: #f9f9f9; }
.warning { color: #d97706; font-size: 13px; }
.error { color: red; font-size: 13px; }
.success { color: green; font-size: 13px; }
button { margin-top: 8px; padding: 6px 14px; cursor: pointer; }
</style>
