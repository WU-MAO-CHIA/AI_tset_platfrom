<template>
  <div class="page">
    <div class="page-header">
      <h1>測試清單</h1>
      <button v-if="authStore.isEditor" class="btn-primary" @click="showCreate = true">+ 建立清單</button>
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
      <p>尚無測試清單</p>
    </div>

    <!-- 條列式清單表格（比照 CasesPage） -->
    <table v-else class="checklist-table">
      <thead>
        <tr>
          <th class="sortable" @click="toggleSort('name')">
            清單名稱 <span class="sort-indicator">{{ sortIndicator('name') }}</span>
          </th>
          <th class="sortable" @click="toggleSort('created_by')">
            建立人員 <span class="sort-indicator">{{ sortIndicator('created_by') }}</span>
          </th>
          <th>案例數</th>
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
          <td class="cl-name">{{ cl.name }}</td>
          <td>{{ cl.created_by }}</td>
          <td>{{ cl.case_count ?? '-' }}</td>
          <td>{{ cl.created_at ? new Date(cl.created_at).toLocaleDateString('zh-TW') : '-' }}</td>
          <td>
            <span v-if="cl.status" class="status-badge" :class="`status-${cl.status}`">
              {{ cl.status }}
            </span>
            <span v-else class="status-badge status-none">-</span>
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
      <div class="modal">
        <h2>建立測試清單</h2>
        <label>清單名稱</label>
        <input v-model="newName" placeholder="Sprint 1 Tests" />
        <label>建立者</label>
        <input v-model="newCreatedBy" placeholder="tester" />
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
import { useRouter } from 'vue-router'
import { listChecklists, createChecklist, type Checklist } from '../services/checklistApi'
import { useAuthStore } from '../stores/authStore'

const authStore = useAuthStore()

const router = useRouter()

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
const newCreatedBy = ref('')

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
  await createChecklist({ name: newName.value, created_by: newCreatedBy.value, case_ids: [] })
  newName.value = ''
  newCreatedBy.value = ''
  showCreate.value = false
  await fetchChecklists()
}

watch(page, fetchChecklists)
onMounted(fetchChecklists)
</script>

<style scoped>
.page { max-width: 1200px; margin: 0 auto; padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
h1 { font-size: 22px; }

.search-bar { margin-bottom: 16px; }
.search-bar input {
  width: 100%;
  max-width: 400px;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.checklist-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.checklist-table th {
  text-align: left;
  padding: 10px 12px;
  background: #f3f4f6;
  border-bottom: 2px solid #e5e7eb;
  font-weight: 600;
  color: #374151;
}
.sortable { cursor: pointer; user-select: none; }
.sortable:hover { background: #e9eaf0; }
.sort-indicator { display: inline-block; width: 12px; color: #4f46e5; font-weight: 700; }
.checklist-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #e5e7eb;
}
.clickable { cursor: pointer; }
.clickable:hover { background: #f0f4ff; }
.cl-name { font-weight: 500; }

.status-badge {
  padding: 2px 8px;
  border-radius: 9999px;
  font-size: 12px;
}
.status-passed, .status-completed { background: #dcfce7; color: #166534; }
.status-failed, .status-error { background: #fee2e2; color: #991b1b; }
.status-running { background: #dbeafe; color: #1e40af; }
.status-pending { background: #fef3c7; color: #92400e; }
.status-none { background: #f3f4f6; color: #6b7280; }

.loading { padding: 40px; text-align: center; color: #6b7280; }
.empty-state { padding: 60px; text-align: center; color: #9ca3af; }

.pagination { display: flex; align-items: center; gap: 12px; margin-top: 16px; justify-content: center; }

.btn-primary { background: #4f46e5; color: white; padding: 8px 20px; border: none; border-radius: 4px; cursor: pointer; }
.btn-secondary { background: #e5e7eb; color: #374151; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: white; padding: 24px; border-radius: 8px; min-width: 360px; display: flex; flex-direction: column; gap: 12px; }
.modal h2 { font-size: 18px; margin-bottom: 4px; }
.modal label { font-size: 14px; font-weight: 500; }
.modal input { padding: 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 14px; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 4px; }
</style>
