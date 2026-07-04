<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1>管理案例</h1>
        <span class="subtitle" v-if="checklistName">{{ checklistName }}</span>
      </div>
      <div class="actions">
        <button class="btn-secondary" @click="$router.push(`/checklists/${checklistId}`)">← 返回清單</button>
      </div>
    </div>

    <div v-if="errorMsg" class="error-banner">{{ errorMsg }}</div>

    <!-- 已加入案例列表 -->
    <div class="section">
      <h2>已加入案例（{{ items.length }} 筆）</h2>
      <div v-if="items.length === 0" class="empty">尚無案例{{ authStore.isEditor ? '，請從下方搜尋加入' : '' }}</div>
      <table v-else class="case-table">
        <thead>
          <tr>
            <th>#</th>
            <th>案例編號</th>
            <th>名稱</th>
            <th>備註</th>
            <th v-if="authStore.isEditor">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, idx) in items" :key="item.item_id">
            <td>{{ item.position + 1 }}</td>
            <td>{{ item.case_number ?? '-' }}</td>
            <td>{{ item.name ?? '-' }}</td>
            <td>
              <input
                v-if="authStore.isEditor"
                class="notes-input"
                :value="item.notes ?? ''"
                placeholder="加入備註..."
                @blur="onNotesBlur(item, ($event.target as HTMLInputElement).value)"
              />
              <span v-else>{{ item.notes || '-' }}</span>
            </td>
            <td v-if="authStore.isEditor">
              <button class="btn-up" @click="moveUp(idx)" :disabled="idx === 0">↑</button>
              <button class="btn-down" @click="moveDown(idx)" :disabled="idx === items.length - 1">↓</button>
              <button class="btn-danger-sm" @click="onRemove(item.test_case_id)">移除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <button v-if="reorderDirty && authStore.isEditor" class="btn-primary save-order-btn" @click="saveOrder">
        儲存排序
      </button>
    </div>

    <!-- 搜尋並加入案例（僅 editor 以上） -->
    <div v-if="authStore.isEditor" class="section">
      <h2>搜尋案例</h2>
      <div class="search-row">
        <input v-model="searchKeyword" class="search-input" placeholder="輸入案例名稱或編號..." @input="onSearch" />
      </div>
      <div v-if="searchResults.length > 0" class="search-results">
        <table class="case-table">
          <thead>
            <tr>
              <th>案例編號</th>
              <th>名稱</th>
              <th>系統別</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in searchResults" :key="c.id">
              <td>{{ c.case_number }}</td>
              <td>{{ c.name }}</td>
              <td>{{ c.system_category ?? '-' }}</td>
              <td>
                <button
                  class="btn-add"
                  :disabled="isAlreadyAdded(c.id)"
                  @click="onAdd(c.id)"
                >
                  {{ isAlreadyAdded(c.id) ? '已加入' : '+ 加入' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="searchKeyword" class="empty">無符合結果</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import {
  getChecklistCases,
  addCaseToChecklist,
  removeCaseFromChecklist,
  patchChecklistCaseItem,
  reorderChecklistCases,
  getChecklist,
  type ChecklistCaseItem,
} from '../services/checklistApi'
import { caseApi } from '../services/caseApi'

const authStore = useAuthStore()
const route = useRoute()
const checklistId = route.params.id as string

const items = ref<ChecklistCaseItem[]>([])
const checklistName = ref('')
const errorMsg = ref('')
const searchKeyword = ref('')
const searchResults = ref<any[]>([])
const reorderDirty = ref(false)
let searchTimeout: ReturnType<typeof setTimeout> | null = null

onMounted(async () => {
  try {
    const [casesData, clData] = await Promise.all([
      getChecklistCases(checklistId),
      getChecklist(checklistId),
    ])
    items.value = [...casesData.items].sort((a, b) => a.position - b.position)
    checklistName.value = clData.name
  } catch {
    errorMsg.value = '載入失敗'
  }
})

function isAlreadyAdded(caseId: string) {
  return items.value.some((item) => item.test_case_id === caseId)
}

function onSearch() {
  if (searchTimeout) clearTimeout(searchTimeout)
  if (!searchKeyword.value.trim()) {
    searchResults.value = []
    return
  }
  searchTimeout = setTimeout(async () => {
    try {
      const res = await caseApi.listCases({ keyword: searchKeyword.value, page_size: 20 })
      searchResults.value = res.data.items
    } catch {
      searchResults.value = []
    }
  }, 300)
}

async function onAdd(caseId: string) {
  errorMsg.value = ''
  try {
    await addCaseToChecklist(checklistId, caseId)
    const casesData = await getChecklistCases(checklistId)
    items.value = [...casesData.items].sort((a, b) => a.position - b.position)
  } catch (err: any) {
    errorMsg.value = err?.response?.data?.error === 'case_already_in_checklist'
      ? '案例已在清單中'
      : '加入失敗'
  }
}

async function onRemove(caseId: string) {
  errorMsg.value = ''
  try {
    await removeCaseFromChecklist(checklistId, caseId)
    items.value = items.value.filter((item) => item.test_case_id !== caseId)
  } catch {
    errorMsg.value = '移除失敗'
  }
}

async function onNotesBlur(item: ChecklistCaseItem, newNotes: string) {
  if (newNotes === (item.notes ?? '')) return
  try {
    await patchChecklistCaseItem(checklistId, item.test_case_id, { notes: newNotes })
    item.notes = newNotes
  } catch {
    errorMsg.value = '備註儲存失敗'
  }
}

function moveUp(idx: number) {
  if (idx === 0) return
  const arr = [...items.value]
  ;[arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]]
  items.value = arr
  reorderDirty.value = true
}

function moveDown(idx: number) {
  if (idx === items.value.length - 1) return
  const arr = [...items.value]
  ;[arr[idx], arr[idx + 1]] = [arr[idx + 1], arr[idx]]
  items.value = arr
  reorderDirty.value = true
}

async function saveOrder() {
  errorMsg.value = ''
  try {
    await reorderChecklistCases(checklistId, items.value.map((i) => i.test_case_id))
    reorderDirty.value = false
    // Refresh to get updated positions
    const casesData = await getChecklistCases(checklistId)
    items.value = [...casesData.items].sort((a, b) => a.position - b.position)
  } catch {
    errorMsg.value = '排序儲存失敗'
  }
}
</script>

<style scoped>
.page { max-width: 1200px; margin: 0 auto; padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
h1 { font-size: 22px; margin-bottom: 4px; }
.subtitle { font-size: 13px; color: #6b7280; }
.actions { display: flex; gap: 8px; }

.section { margin-bottom: 32px; }
.section h2 { font-size: 16px; font-weight: 600; margin-bottom: 12px; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }

.case-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.case-table th, .case-table td { padding: 10px 12px; border-bottom: 1px solid #e5e7eb; text-align: left; }
.case-table th { background: #f9fafb; font-weight: 600; color: #374151; }

.notes-input { width: 100%; border: 1px solid #e5e7eb; border-radius: 4px; padding: 4px 8px; font-size: 13px; }
.notes-input:focus { outline: none; border-color: #6366f1; }

.search-row { margin-bottom: 12px; }
.search-input { width: 320px; border: 1px solid #d1d5db; border-radius: 6px; padding: 8px 12px; font-size: 14px; }
.search-input:focus { outline: none; border-color: #6366f1; }

.empty { color: #9ca3af; font-size: 14px; padding: 16px 0; }
.error-banner { background: #fee2e2; color: #991b1b; padding: 10px 16px; border-radius: 6px; margin-bottom: 16px; }

.btn-primary { background: #4f46e5; color: white; padding: 8px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
.btn-secondary { background: #e5e7eb; color: #374151; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
.btn-danger-sm { background: #fee2e2; color: #dc2626; padding: 4px 10px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; margin-left: 4px; }
.btn-danger-sm:hover { background: #fecaca; }
.btn-add { background: #d1fae5; color: #065f46; padding: 4px 10px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }
.btn-add:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-up, .btn-down { background: #f3f4f6; color: #374151; padding: 4px 8px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; margin-right: 2px; }
.btn-up:disabled, .btn-down:disabled { opacity: 0.4; cursor: not-allowed; }
.save-order-btn { margin-top: 12px; }
</style>
