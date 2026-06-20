<template>
  <div class="case-list">
    <div class="filters">
      <input v-model="filters.keyword" placeholder="搜尋名稱..." @input="onFilterChange" />
      <select v-model="filters.system_category" @change="onFilterChange">
        <option value="">全部系統別</option>
        <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
      </select>
    </div>

    <table v-if="!loading && cases.length" class="case-table">
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
          <th>版本</th>
          <th class="sortable" @click="toggleSort('updated_at')">
            更新時間 <span class="sort-indicator">{{ sortIndicator('updated_at') }}</span>
          </th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in cases" :key="c.id" @click="$emit('select', c)" class="clickable">
          <td>{{ c.case_number }}</td>
          <td>{{ c.name }}</td>
          <td>{{ c.system_category || '-' }}</td>
          <td>v{{ c.version }}</td>
          <td>{{ formatDate(c.updated_at) }}</td>
          <td>
            <button @click.stop="$emit('edit', c)">編輯</button>
            <button @click.stop="$emit('delete', c)" class="danger">刪除</button>
          </td>
        </tr>
      </tbody>
    </table>

    <p v-else-if="!loading && !cases.length" class="empty">無符合條件的測試案例</p>
    <p v-if="loading">載入中...</p>

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
const categories = ref<string[]>(['auth', 'order', 'product', 'payment'])

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

function formatDate(iso: string | null) {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString('zh-TW')
}

onMounted(load)

defineExpose({ load })
</script>

<style scoped>
.case-list { display: flex; flex-direction: column; gap: 16px; }
.filters { display: flex; gap: 12px; }
.filters input, .filters select { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
.case-table { width: 100%; border-collapse: collapse; }
.case-table th, .case-table td { padding: 10px; border-bottom: 1px solid #eee; text-align: left; font-size: 14px; }
.case-table thead { background: #f9f9f9; }
.sortable { cursor: pointer; user-select: none; }
.sortable:hover { background: #f0f0f0; }
.sort-indicator { display: inline-block; width: 12px; color: #4f46e5; font-weight: 700; }
.clickable { cursor: pointer; }
.clickable:hover { background: #f0f4ff; }
button { padding: 4px 10px; cursor: pointer; }
.danger { color: red; }
.pagination { display: flex; align-items: center; gap: 12px; }
.empty { color: #888; text-align: center; }
</style>
