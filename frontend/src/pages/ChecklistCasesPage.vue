<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1>管理案例</h1>
        <span class="subtitle" v-if="checklistName">{{ checklistName }}</span>
      </div>
      <div class="actions">
        <button class="btn-secondary" @click="$router.push(`/checklists/${checklistId}`)">返回清單</button>
      </div>
    </div>

    <div v-if="errorMsg" class="error-banner">{{ errorMsg }}</div>

    <!-- 已加入案例列表 -->
    <div class="section">
      <h2>已加入案例（{{ items.length }} 筆）</h2>
      <div v-if="items.length === 0" class="empty">尚無案例{{ authStore.isEditor ? '，請從下方搜尋加入' : '' }}</div>
      <table v-else class="data-table responsive-table case-table">
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
            <td data-label="順序" class="idx">{{ item.position + 1 }}</td>
            <td data-label="案例編號" class="muted">{{ item.case_number ?? '-' }}</td>
            <td class="cell-title">{{ item.name ?? '-' }}</td>
            <td data-label="備註">
              <input
                v-if="authStore.isEditor"
                class="notes-input"
                :value="item.notes ?? ''"
                placeholder="加入備註..."
                @blur="onNotesBlur(item, ($event.target as HTMLInputElement).value)"
              />
              <span v-else>{{ item.notes || '-' }}</span>
            </td>
            <td v-if="authStore.isEditor" class="cell-actions row-actions">
              <button class="btn-secondary btn-sm btn-up" aria-label="上移" @click="moveUp(idx)" :disabled="idx === 0">↑</button>
              <button class="btn-secondary btn-sm btn-down" aria-label="下移" @click="moveDown(idx)" :disabled="idx === items.length - 1">↓</button>
              <button class="btn-danger btn-sm btn-danger-sm" @click="onRemove(item.test_case_id)">移除</button>
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
        <table class="data-table responsive-table case-table">
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
              <td data-label="案例編號" class="muted">{{ c.case_number }}</td>
              <td class="cell-title">{{ c.name }}</td>
              <td data-label="系統別">{{ c.system_category ?? '-' }}</td>
              <td class="cell-actions row-actions">
                <button
                  class="btn-secondary btn-sm btn-add"
                  :disabled="isAlreadyAdded(c.id)"
                  @click="onAdd(c.id)"
                >
                  {{ isAlreadyAdded(c.id) ? '已加入' : '加入清單' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="searchKeyword" class="empty">沒有符合「{{ searchKeyword }}」的案例。</div>
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
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 24px; }
.subtitle { color: var(--ink-muted); }
.actions { display: flex; gap: 8px; }

.section { margin-bottom: 32px; }
.section h2 { margin-bottom: 12px; }

.idx { color: var(--ink-faint); width: 48px; }
.notes-input { width: 100%; min-width: 160px; padding: 5px 8px; }
.row-actions { white-space: nowrap; text-align: right; }
.row-actions button + button { margin-left: 6px; }

.search-row { margin-bottom: 12px; }
.search-input { width: 320px; max-width: 100%; }

.empty { color: var(--ink-muted); padding: 16px 0; }
.error-banner { background: var(--fail-bg); color: var(--fail); padding: 10px 16px; border-radius: var(--radius); margin-bottom: 16px; }

.save-order-btn { margin-top: 12px; }
</style>
