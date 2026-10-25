<template>
  <div class="page" v-if="checklist">
    <!-- 頁首 -->
    <div class="page-header">
      <div>
        <h1>{{ checklist.name }}</h1>
        <span class="subtitle">測試清單</span>
      </div>
      <div class="actions">
        <button class="btn-secondary" @click="$router.push('/checklists')">← 返回</button>
        <button v-if="authStore.isEditor" class="btn-secondary" @click="$router.push(`/checklists/${checklist.id}/cases`)">
          管理案例
        </button>
        <button v-if="authStore.isEditor" class="btn-secondary" @click="openEditModal">編輯</button>
        <button v-if="authStore.isEditor" class="btn-danger" @click="handleDelete">刪除</button>
        <button
          data-testid="btn-execute"
          class="btn-primary"
          @click="handleExecute"
        >
          執行測試
        </button>
      </div>
    </div>

    <!-- 基本資訊區 -->
    <div class="section" data-testid="basic-info">
      <h2>基本資訊</h2>
      <dl>
        <dt>清單名稱</dt><dd>{{ checklist.name }}</dd>
        <dt>建立人員</dt><dd>{{ checklist.created_by }}</dd>
        <dt>建立時間</dt><dd>{{ formatDateTime((checklist as any).created_at) }}</dd>
        <dt>案例數</dt><dd>{{ checklist.items.length }}</dd>
      </dl>
    </div>

    <!-- 案例列表區 -->
    <div class="section" data-testid="case-list">
      <h2>所含案例</h2>
      <div v-if="checklist.items.length === 0" class="empty">
        尚無案例，點擊「管理案例」新增
      </div>
      <table v-else class="data-table case-table">
        <thead>
          <tr>
            <th class="col-expand"></th>
            <th>#</th>
            <th>案例編號</th>
            <th>名稱</th>
            <th>系統別</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(item, idx) in checklist.items" :key="item.id">
            <tr>
              <td class="col-expand">
                <button class="expand-btn" @click="toggleExpand(item.test_case_id)" :title="expandedRows.has(item.test_case_id) ? '收合' : '展開'">
                  {{ expandedRows.has(item.test_case_id) ? '▼' : '▶' }}
                </button>
              </td>
              <td>{{ idx + 1 }}</td>
              <td>{{ item.test_case?.case_number ?? item.test_case_id }}</td>
              <td>{{ item.test_case?.name ?? '-' }}</td>
              <td>{{ item.test_case?.system_category ?? '-' }}</td>
            </tr>
            <tr v-if="expandedRows.has(item.test_case_id)" class="expanded-row">
              <td colspan="5" class="expanded-cell">
                <div class="test-data-area">
                  <template v-if="itemsMap.has(item.test_case_id)">
                    <div v-if="(itemsMap.get(item.test_case_id)!.test_data ?? []).length === 0" class="no-test-data">
                      此案例無測試資料
                    </div>
                    <table v-else class="test-data-table">
                      <thead>
                        <tr>
                          <th>易讀名稱</th>
                          <th>RF 變數</th>
                          <th>預設值</th>
                          <th>說明</th>
                          <th>實際值</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="td in itemsMap.get(item.test_case_id)!.test_data" :key="td.id">
                          <td class="td-readonly">{{ td.field_name }}</td>
                          <td class="td-readonly">{{ td.rf_variable ?? '' }}</td>
                          <td class="td-readonly">{{ td.field_value ?? '' }}</td>
                          <td class="td-readonly">{{ td.description ?? '' }}</td>
                          <td>
                            <input
                              class="actual-input"
                              type="text"
                              :value="getLocalActual(item.test_case_id, td.field_name) ?? (itemsMap.get(item.test_case_id)!.actual_values[td.field_name] ?? '')"
                              @input="onActualInput(item.test_case_id, td.field_name, ($event.target as HTMLInputElement).value)"
                              @blur="saveActualValues(item.test_case_id)"
                            />
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </template>
                  <div v-else class="no-test-data">載入中...</div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- 排程區 -->
    <div class="section" data-testid="schedules">
      <h2>排程</h2>
      <ScheduleList :checklist-id="checklist.id" />
    </div>

    <!-- 執行歷史區 -->
    <div class="section" data-testid="execution-history">
      <h2>執行歷史</h2>
      <div v-if="executions.length === 0" class="empty">尚無執行紀錄</div>
      <table v-else class="data-table history-table">
        <thead>
          <tr><th>執行 ID</th><th>狀態</th><th>觸發</th><th>開始時間</th><th>通過</th><th>失敗</th></tr>
        </thead>
        <tbody>
          <tr
            v-for="ex in executions"
            :key="ex.id"
            class="clickable"
            @click="$router.push(`/results/${ex.id}`)"
          >
            <td class="mono">{{ ex.id.slice(0, 8) }}</td>
            <td><StatusBadge :status="ex.status" /></td>
            <td>{{ triggerLabel(ex) }}</td>
            <td>{{ formatDateTime(ex.started_at) }}</td>
            <td>{{ ex.passed_count }}</td>
            <td>{{ ex.failed_count }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="errorMsg" class="error-banner">{{ errorMsg }}</div>

    <!-- 編輯 Modal -->
    <div v-if="editModalOpen" class="modal-overlay" @click.self="editModalOpen = false">
      <div class="modal">
        <h3>編輯清單</h3>
        <label>清單名稱
          <input v-model="editName" class="modal-input" />
        </label>
        <label>建立人員
          <input v-model="editCreatedBy" class="modal-input" />
        </label>
        <div class="modal-actions">
          <button class="btn-secondary" @click="editModalOpen = false">取消</button>
          <button class="btn-primary" @click="saveEdit">儲存</button>
        </div>
      </div>
    </div>
  </div>

  <div v-else-if="loading" class="loading-page">載入中...</div>

  <div v-else class="not-found">
    <p>找不到清單</p>
    <button @click="$router.push('/checklists')">返回清單</button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getChecklist,
  getChecklistCases,
  updateChecklist,
  deleteChecklist,
  getChecklistExecutions,
  patchChecklistCaseItem,
  type ChecklistDetail,
  type ChecklistExecutionRecord,
  type ChecklistItemDetail,
} from '../services/checklistApi'
import { executeChecklist } from '../services/executionApi'
import { useAuthStore } from '../stores/authStore'
import ScheduleList from '../components/ScheduleList/index.vue'
import StatusBadge from '../components/StatusBadge/index.vue'
import { confirmAction } from '../composables/useConfirm'
import { triggerLabel } from '../utils/scheduleFormat'
import { formatDateTime } from '../utils/format'


const authStore = useAuthStore()

const route = useRoute()
const router = useRouter()

const checklist = ref<ChecklistDetail | null>(null)
const executions = ref<ChecklistExecutionRecord[]>([])
const loading = ref(false)
const errorMsg = ref('')
const editModalOpen = ref(false)
const editName = ref('')
const editCreatedBy = ref('')

// test_data expand/collapse state
const expandedRows = ref<Set<string>>(new Set())
const itemsMap = ref<Map<string, ChecklistItemDetail>>(new Map())
// local unsaved actual_values: Map<test_case_id, Map<field_name, value>>
const localActuals = ref<Map<string, Record<string, string>>>(new Map())

const checklistId = computed(() => route.params.id as string)

function toggleExpand(testCaseId: string) {
  const next = new Set(expandedRows.value)
  if (next.has(testCaseId)) {
    next.delete(testCaseId)
  } else {
    next.add(testCaseId)
  }
  expandedRows.value = next
}

function getLocalActual(testCaseId: string, fieldName: string): string | undefined {
  return localActuals.value.get(testCaseId)?.[fieldName]
}

function onActualInput(testCaseId: string, fieldName: string, value: string) {
  const current = localActuals.value.get(testCaseId) ?? {}
  localActuals.value.set(testCaseId, { ...current, [fieldName]: value })
}

async function saveActualValues(testCaseId: string) {
  const local = localActuals.value.get(testCaseId)
  if (!local) return
  const existing = itemsMap.value.get(testCaseId)?.actual_values ?? {}
  const merged = { ...existing, ...local }
  try {
    await patchChecklistCaseItem(checklistId.value, testCaseId, { actual_values: merged })
    const item = itemsMap.value.get(testCaseId)
    if (item) {
      itemsMap.value.set(testCaseId, { ...item, actual_values: merged })
    }
    localActuals.value.delete(testCaseId)
  } catch {
    // silent: keep local state so user can retry
  }
}

async function fetchChecklist() {
  loading.value = true
  errorMsg.value = ''
  const id = checklistId.value
  try {
    const [cl, exHistory] = await Promise.all([
      getChecklist(id),
      getChecklistExecutions(id),
    ])
    checklist.value = cl
    executions.value = exHistory.items

    // fetch detailed items (test_data + actual_values)
    const casesRes = await getChecklistCases(id)
    const map = new Map<string, ChecklistItemDetail>()
    for (const ci of casesRes.items) {
      map.set(ci.test_case_id, ci)
    }
    itemsMap.value = map
  } catch {
    checklist.value = null
  } finally {
    loading.value = false
  }
}

function openEditModal() {
  if (!checklist.value) return
  editName.value = checklist.value.name
  editCreatedBy.value = checklist.value.created_by
  editModalOpen.value = true
}

async function saveEdit() {
  if (!checklist.value) return
  errorMsg.value = ''
  try {
    const updated = await updateChecklist(checklist.value.id, editName.value, editCreatedBy.value)
    checklist.value = { ...checklist.value, ...updated }
    editModalOpen.value = false
  } catch {
    errorMsg.value = '編輯失敗'
  }
}

async function handleDelete() {
  if (!checklist.value) return
  const ok = await confirmAction({ title: `刪除清單「${checklist.value.name}」？`, message: '此操作不可還原。', confirmLabel: '刪除', danger: true })
  if (!ok) return
  errorMsg.value = ''
  try {
    await deleteChecklist(checklist.value.id)
    router.push('/checklists')
  } catch (err: any) {
    const code = err?.response?.status
    if (code === 409) {
      errorMsg.value = '有執行中的測試，無法刪除此清單'
    } else {
      errorMsg.value = '刪除失敗'
    }
  }
}

async function handleExecute() {
  if (!checklist.value) return
  if (checklist.value.items.length === 0) {
    alert('測試清單為空，請先新增案例')
    return
  }
  errorMsg.value = ''
  try {
    const { execution_id } = await executeChecklist(checklist.value.id, {
      parallel_mode: false,
      max_workers: 1,
    })
    router.push(`/executions/${execution_id}`)
  } catch {
    errorMsg.value = '執行失敗，請稍後再試'
  }
}

onMounted(fetchChecklist)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 24px; }
h1 { margin-bottom: 4px; }
.subtitle { color: var(--ink-muted); }
.actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }

.section { margin-bottom: 32px; }
.section h2 { margin-bottom: 12px; }

dl { display: grid; grid-template-columns: 100px 1fr; gap: 6px 16px; }
dt { font-weight: 600; color: var(--ink-muted); }

.col-expand { width: 36px; }
.mono { font-family: var(--font-mono); font-size: var(--fs-12); }

.expand-btn {
  background: none;
  border: none;
  min-height: 0;
  font-size: var(--fs-12);
  color: var(--ink-muted);
  padding: 2px 4px;
  border-radius: 3px;
}
.expand-btn:hover:not(:disabled) { background: var(--brand-soft); color: var(--ink); }

.expanded-row > td.expanded-cell {
  padding: 0;
  background: var(--brand-soft);
}

.test-data-area { padding: 12px 16px 16px 48px; }

.no-test-data { color: var(--ink-muted); font-size: var(--fs-12); padding: 8px 0; }

.test-data-table { width: 100%; border-collapse: collapse; font-size: var(--fs-12); }
.test-data-table th {
  font-weight: 600;
  color: var(--brand-ink-muted);
  padding: 6px 10px;
  text-align: left;
  border-bottom: 1px solid var(--brand-line);
}
.test-data-table td { padding: 4px 8px; border-bottom: 1px solid var(--brand-line); }
.td-readonly { color: var(--ink); }

.actual-input { width: 100%; padding: 4px 8px; font-size: var(--fs-12); }

.clickable { cursor: pointer; }
.clickable:hover { background: var(--brand-soft); }

.empty { color: var(--ink-muted); padding: 16px 0; }
.error-banner { background: var(--fail-bg); color: var(--fail); padding: 10px 16px; border-radius: var(--radius); margin-top: 16px; }
.loading-page, .not-found { padding: 60px; text-align: center; color: var(--ink-muted); }

.modal-overlay { position: fixed; inset: 0; background: rgba(14, 42, 68, 0.35); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: var(--paper); border-radius: var(--radius-lg); padding: 24px; min-width: 360px; }
.modal h3 { font-size: var(--fs-20); font-weight: 600; margin-bottom: 16px; }
.modal label { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; color: var(--ink-muted); }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 20px; }

@media (max-width: 767px) {
  .page-header { flex-direction: column; }
  .actions { justify-content: flex-start; }
  .case-table, .history-table { display: block; overflow-x: auto; }
}
</style>
