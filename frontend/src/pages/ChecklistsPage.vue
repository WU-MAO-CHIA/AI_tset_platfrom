<template>
  <div class="page">
    <div class="page-header">
      <h1>測試清單</h1>
      <button v-if="authStore.isEditor" class="btn-primary" @click="showCreate = true">建立清單</button>
    </div>

    <!-- 搜尋欄 -->
    <div class="search-bar">
      <input
        v-model="keyword"
        data-testid="search-input"
        placeholder="搜尋清單名稱..."
        @input="onSearch"
      />
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <div v-else-if="checklists.length === 0" class="empty-state">
      <p>{{ keyword ? '沒有符合搜尋的清單。' : '還沒有測試清單，按「建立清單」把案例組成一份可執行的清單。' }}</p>
    </div>

    <!-- 條列式清單表格（比照 CasesPage） -->
    <table v-else class="data-table responsive-table checklist-table">
      <thead>
        <tr>
          <th class="sortable" @click="toggleSort('name')">
            清單名稱 <span class="sort-indicator">{{ sortIndicator('name') }}</span>
          </th>
          <th class="num">案例數</th>
          <th>最近 10 次</th>
          <th>上次執行</th>
          <th class="sortable" @click="toggleSort('created_at')">
            建立時間 <span class="sort-indicator">{{ sortIndicator('created_at') }}</span>
          </th>
          <th class="sortable" @click="toggleSort('status')">
            狀態 <span class="sort-indicator">{{ sortIndicator('status') }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="cl in checklists"
          :key="cl.id"
          data-testid="checklist-row"
          class="clickable"
          @click="$router.push(`/checklists/${cl.id}`)"
        >
          <td class="cl-name cell-title">
            {{ cl.name }}
            <span class="created-by">{{ cl.created_by }} 建立</span>
          </td>
          <td data-label="案例數" class="num">{{ cl.case_count ?? '-' }}</td>
          <td data-label="最近 10 次"><RunStrip :runs="cl.recent_runs ?? []" /></td>
          <td data-label="上次執行" class="muted">{{ lastRunText(cl) }}</td>
          <td data-label="建立時間" class="muted">{{ formatDate(cl.created_at) }}</td>
          <td data-label="狀態">
            <StatusBadge v-bind="latestBadge(cl)" />
          </td>
        </tr>
      </tbody>
    </table>

    <div class="pagination" v-if="total > pageSize">
      <button :disabled="page <= 1" @click="page--">上一頁</button>
      <span>第 {{ page }} 頁 / 共 {{ Math.ceil(total / pageSize) }} 頁</span>
      <button :disabled="page * pageSize >= total" @click="page++">下一頁</button>
    </div>

    <!-- 建立清單 Modal -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal" role="dialog" aria-modal="true">
        <h2>建立測試清單</h2>
        <label for="new-checklist-name">清單名稱</label>
        <input id="new-checklist-name" v-model="newName" placeholder="例如：每日冒煙測試" />
        <div class="modal-actions">
          <button class="btn-secondary" @click="showCreate = false">取消</button>
          <button class="btn-primary" :disabled="!newName" @click="handleCreate">建立</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { listChecklists, createChecklist, type Checklist } from '../services/checklistApi'
import { useAuthStore } from '../stores/authStore'
import StatusBadge from '../components/StatusBadge/index.vue'
import RunStrip from '../components/RunStrip/index.vue'
import { formatDate, formatDateTime } from '../utils/format'

const authStore = useAuthStore()

const checklists = ref<Checklist[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const keyword = ref('')
const sortBy = ref('created_at')
const sortOrder = ref<'asc' | 'desc'>('desc')

const showCreate = ref(false)
const newName = ref('')

let searchTimer: ReturnType<typeof setTimeout> | null = null

function onSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    fetchChecklists()
  }, 300)
}

function toggleSort(col: string) {
  if (sortBy.value === col) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortBy.value = col
    sortOrder.value = 'asc'
  }
  page.value = 1
  fetchChecklists()
}

function sortIndicator(col: string): string {
  if (sortBy.value !== col) return ''
  return sortOrder.value === 'asc' ? '↑' : '↓'
}

async function fetchChecklists() {
  loading.value = true
  try {
    const data = await listChecklists(page.value, pageSize, keyword.value || undefined, sortBy.value, sortOrder.value)
    checklists.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!newName.value) return
  await createChecklist({ name: newName.value, created_by: authStore.username ?? '', case_ids: [] })
  newName.value = ''
  showCreate.value = false
  await fetchChecklists()
}

// 「完成」不代表全部通過：有失敗案例時直接顯示失敗數
function latestBadge(cl: Checklist): { status: string | null | undefined; label?: string } {
  const last = cl.recent_runs?.[0]
  if (last?.status === 'completed') {
    return last.failed_count > 0
      ? { status: 'failed', label: `${last.failed_count} 個失敗` }
      : { status: 'passed' }
  }
  return { status: cl.status }
}

function lastRunText(cl: Checklist): string {
  const last = cl.recent_runs?.[0]
  if (!last) return '-'
  return formatDateTime(last.started_at ?? last.finished_at)
}

watch(page, fetchChecklists)
onMounted(fetchChecklists)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 24px; }

.search-bar { margin-bottom: 16px; }
.search-bar input { width: 100%; max-width: 400px; }

.sortable { cursor: pointer; user-select: none; white-space: nowrap; }
.sortable:hover { color: var(--ink); }
.sort-indicator { display: inline-block; width: 12px; color: var(--brand-strong); font-weight: 700; }
.num { text-align: right; }
.clickable { cursor: pointer; }
.clickable:hover td { background: var(--brand-soft); }
.cl-name { font-weight: 600; }
.created-by { display: block; font-weight: 400; font-size: var(--fs-12); color: var(--ink-muted); }

.loading { padding: 40px; text-align: center; color: var(--ink-muted); }
.empty-state { padding: 48px 0; text-align: center; }

.pagination { display: flex; align-items: center; gap: 12px; margin-top: 16px; justify-content: center; color: var(--ink-muted); }

.modal label { font-size: var(--fs-12); color: var(--ink-muted); }
</style>
