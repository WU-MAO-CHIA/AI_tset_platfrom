<template>
  <div class="schedule-list">
    <div class="list-header">
      <span class="tz-note">時間以 {{ timezone }} 顯示</span>
      <button
        v-if="checklistId && authStore.isEditor"
        class="btn-primary"
        data-testid="btn-add-schedule"
        @click="openCreate"
      >
        新增排程
      </button>
    </div>

    <div v-if="loading" class="empty">載入中...</div>
    <div v-else-if="schedules.length === 0" class="empty" data-testid="schedule-empty">尚無排程</div>
    <table v-else class="data-table schedule-table">
      <thead>
        <tr>
          <th>名稱</th>
          <th v-if="!checklistId">清單</th>
          <th>頻率</th>
          <th>下次執行</th>
          <th>上次觸發</th>
          <th>上次結果</th>
          <th>狀態</th>
          <th v-if="authStore.isEditor"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="s in schedules" :key="s.id" :data-testid="`schedule-row-${s.id}`">
          <td>{{ s.name }}</td>
          <td v-if="!checklistId">
            <RouterLink :to="`/checklists/${s.checklist_id}`">{{ s.checklist_name ?? s.checklist_id }}</RouterLink>
          </td>
          <td>{{ describeFrequency(s) }}</td>
          <td>{{ s.enabled ? formatScheduleTime(s.next_run_at, s.timezone) : '-' }}</td>
          <td>{{ formatScheduleTime(s.last_triggered_at, s.timezone) }}</td>
          <td>
            <span v-if="s.last_skip_reason" class="skip" :title="s.last_skip_reason">略過：{{ s.last_skip_reason }}</span>
            <RouterLink v-else-if="s.last_execution_id" :to="`/results/${s.last_execution_id}`" class="result-link">
              <span :class="['badge', statusBadge(s.last_execution_status)]">{{ statusLabel(s.last_execution_status) }}</span>
            </RouterLink>
            <span v-else>-</span>
          </td>
          <td>
            <span :class="['toggle-state', s.enabled ? 'on' : 'off']">{{ s.enabled ? '啟用' : '停用' }}</span>
          </td>
          <td v-if="authStore.isEditor" class="row-actions">
            <button class="btn-link" data-testid="btn-toggle-schedule" @click="toggle(s)">{{ s.enabled ? '停用' : '啟用' }}</button>
            <button class="btn-link" data-testid="btn-edit-schedule" @click="openEdit(s)">編輯</button>
            <button class="btn-link danger" data-testid="btn-delete-schedule" @click="remove(s)">刪除</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="errorMsg" class="error-banner">{{ errorMsg }}</div>

    <ScheduleForm
      v-if="formOpen"
      :schedule="editing"
      :timezone="timezone"
      :saving="saving"
      @submit="save"
      @cancel="formOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import ScheduleForm from '../ScheduleForm/index.vue'
import {
  createSchedule,
  deleteSchedule,
  listChecklistSchedules,
  listSchedules,
  updateSchedule,
  type Schedule,
  type ScheduleInput,
} from '../../services/scheduleApi'
import { describeFrequency, formatScheduleTime } from '../../utils/scheduleFormat'
import { useAuthStore } from '../../stores/authStore'

// 傳入 checklistId 時只顯示該清單的排程並可新增；否則顯示全部排程
const props = defineProps<{ checklistId?: string }>()

const authStore = useAuthStore()
const schedules = ref<Schedule[]>([])
const loading = ref(false)
const errorMsg = ref('')
const formOpen = ref(false)
const editing = ref<Schedule | null>(null)
const saving = ref(false)

const timezone = computed(() => schedules.value[0]?.timezone ?? 'Asia/Taipei')

const STATUS_LABELS: Record<string, string> = {
  pending: '排隊中',
  running: '執行中',
  completed: '完成',
  failed: '失敗',
  error: '錯誤',
  interrupted: '已中斷',
  cancelled: '已取消',
}

// 狀態色只用在測試結果：通過綠、失敗紅、執行中紫、排隊黃，其餘中性
const STATUS_BADGES: Record<string, string> = {
  completed: 'badge-pass',
  failed: 'badge-fail',
  error: 'badge-fail',
  running: 'badge-running',
  pending: 'badge-queued',
}

function statusBadge(status: string | null): string {
  return (status && STATUS_BADGES[status]) || ''
}

function statusLabel(status: string | null): string {
  if (!status) return '-'
  return STATUS_LABELS[status] ?? status
}

function apiError(err: any, fallback: string): string {
  return err?.response?.data?.message ?? fallback
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = props.checklistId ? await listChecklistSchedules(props.checklistId) : await listSchedules()
    schedules.value = res.items
  } catch {
    errorMsg.value = '載入排程失敗'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  formOpen.value = true
}

function openEdit(s: Schedule) {
  editing.value = s
  formOpen.value = true
}

function replace(updated: Schedule) {
  schedules.value = schedules.value.map((s) => (s.id === updated.id ? updated : s))
}

async function save(payload: ScheduleInput) {
  saving.value = true
  errorMsg.value = ''
  try {
    if (editing.value) {
      replace(await updateSchedule(editing.value.id, payload))
    } else if (props.checklistId) {
      schedules.value = [...schedules.value, await createSchedule(props.checklistId, payload)]
    }
    formOpen.value = false
  } catch (err) {
    errorMsg.value = apiError(err, '儲存排程失敗')
  } finally {
    saving.value = false
  }
}

async function toggle(s: Schedule) {
  errorMsg.value = ''
  try {
    replace(await updateSchedule(s.id, { enabled: !s.enabled }))
  } catch (err) {
    errorMsg.value = apiError(err, '更新排程失敗')
  }
}

async function remove(s: Schedule) {
  if (!confirm(`確定要刪除排程「${s.name}」？`)) return
  errorMsg.value = ''
  try {
    await deleteSchedule(s.id)
    schedules.value = schedules.value.filter((x) => x.id !== s.id)
  } catch (err) {
    errorMsg.value = apiError(err, '刪除排程失敗')
  }
}

onMounted(load)
</script>

<style scoped>
.list-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.tz-note { font-size: var(--fs-12); color: var(--ink-muted); }
.schedule-table a { text-decoration: none; }
.schedule-table a:hover { text-decoration: underline; }
.result-link:hover { text-decoration: none; }
.toggle-state { font-size: var(--fs-12); font-weight: 600; }
.toggle-state.on { color: var(--brand-strong); }
.toggle-state.off { color: var(--ink-faint); }
.skip { color: var(--queued); font-size: var(--fs-12); }
.row-actions { white-space: nowrap; text-align: right; }
.btn-link { background: none; border: none; min-height: 0; color: var(--brand-strong); font-size: var(--fs-12); padding: 2px 6px; }
.btn-link:hover:not(:disabled) { background: var(--brand-soft); }
.btn-link.danger { color: var(--fail); }
.btn-link.danger:hover:not(:disabled) { background: var(--fail-bg); }
.empty { color: var(--ink-muted); padding: 16px 0; }
.error-banner { background: var(--fail-bg); color: var(--fail); padding: 10px 16px; border-radius: var(--radius); margin-top: 12px; }
@media (max-width: 767px) {
  .schedule-table { display: block; overflow-x: auto; }
}
</style>
