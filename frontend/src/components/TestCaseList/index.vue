<template>
  <div class="case-list">
    <div class="filters">
      <input v-model="filters.keyword" placeholder="搜尋名稱..." @input="onFilterChange" />
      <select v-model="filters.system_category" @change="onFilterChange">
        <option value="">全部系統別</option>
        <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
      </select>
    </div>

    <table v-if="!loading && cases.length" class="data-table responsive-table case-table">
      <thead>
        <tr>
          <th class="sortable" @click="toggleSort('case_number')">
            編號 <span class="sort-indicator">{{ sortIndicator('case_number') }}</span>
          </th>
          <th class="sortable" @click="toggleSort('name')">
            名稱 <span class="sort-indicator">{{ sortIndicator('name') }}</span>
          </th>
          <th class="sortable" @click="toggleSort('system_category')">
            系統別 <span class="sort-indicator">{{ sortIndicator('system_category') }}</span>
          </th>
          <th class="sortable" @click="toggleSort('version')">
            版本 <span class="sort-indicator">{{ sortIndicator('version') }}</span>
          </th>
          <th class="sortable" @click="toggleSort('updated_at')">
            更新時間 <span class="sort-indicator">{{ sortIndicator('updated_at') }}</span>
          </th>
          <th v-if="authStore.isEditor">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in cases" :key="c.id" @click="$emit('select', c)" class="clickable">
          <td data-label="編號" class="case-number">{{ c.case_number }}</td>
          <td class="cell-title">{{ c.name }}</td>
          <td data-label="系統別">{{ c.system_category || '-' }}</td>
          <td data-label="版本">v{{ c.version }}</td>
          <td data-label="更新時間">{{ formatDate(c.updated_at) }}</td>
          <td v-if="authStore.isEditor" class="cell-actions row-actions">
            <button class="btn-secondary" @click.stop="$emit('edit', c)">編輯</button>
            <button class="btn-danger" @click.stop="$emit('delete', c)">刪除</button>
          </td>
        </tr>
      </tbody>
    </table>

    <p v-else-if="!loading && !cases.length" class="empty-state">沒有符合條件的測試案例，試著調整搜尋或系統別。</p>
    <p v-if="loading" class="empty-state">載入中...</p>

    <div class="pagination" v-if="total > pageSize">
      <button :disabled="page <= 1" @click="page--; load()">上一頁</button>
      <span>第 {{ page }} 頁 / 共 {{ Math.ceil(total / pageSize) }} 頁（{{ total }} 筆）</span>
      <button :disabled="page * pageSize >= total" @click="page++; load()">下一頁</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { caseApi, type TestCaseSummary } from '../../services/caseApi'
import { formatDate } from '../../utils/format'
import { useAuthStore } from '../../stores/authStore'

const authStore = useAuthStore()

defineEmits<{
  (e: 'select', c: TestCaseSummary): void
  (e: 'edit', c: TestCaseSummary): void
  (e: 'delete', c: TestCaseSummary): void
}>()

const cases = ref<TestCaseSummary[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const categories = ref<string[]>([])

const filters = reactive({ keyword: '', system_category: '' })
const sortBy = ref('created_at')
const sortOrder = ref<'asc' | 'desc'>('desc')

let debounceTimer: ReturnType<typeof setTimeout>
function onFilterChange() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => { page.value = 1; load() }, 300)
}

function toggleSort(col: string) {
  if (sortBy.value === col) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortBy.value = col
    sortOrder.value = 'asc'
  }
  page.value = 1
  load()
}

function sortIndicator(col: string): string {
  if (sortBy.value !== col) return ''
  return sortOrder.value === 'asc' ? '↑' : '↓'
}

async function load() {
  loading.value = true
  try {
    const res = await caseApi.listCases({
      keyword: filters.keyword || undefined,
      system_category: filters.system_category || undefined,
      page: page.value,
      page_size: pageSize.value,
      sort_by: sortBy.value,
      order: sortOrder.value,
    })
    cases.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}


onMounted(async () => {
  try {
    const res = await caseApi.listCategories()
    categories.value = res.data.items
  } catch {
    // silently ignore; filter will have no categories
  }
  load()
})

defineExpose({ load })
</script>

<style scoped>
.case-list { display: flex; flex-direction: column; gap: 16px; }
.filters { display: flex; flex-wrap: wrap; gap: 12px; }
.filters input { width: 320px; max-width: 100%; }
.sortable { cursor: pointer; user-select: none; white-space: nowrap; }
.sortable:hover { color: var(--ink); }
.sort-indicator { display: inline-block; width: 12px; color: var(--brand-strong); font-weight: 700; }
.case-number { color: var(--ink-muted); white-space: nowrap; }
.clickable { cursor: pointer; }
.clickable:hover td { background: var(--brand-soft); }
.row-actions { white-space: nowrap; text-align: right; }
.row-actions button { min-height: 30px; padding: 0 12px; }
.row-actions button + button { margin-left: 8px; }
.pagination { display: flex; align-items: center; justify-content: center; gap: 12px; color: var(--ink-muted); }
</style>
