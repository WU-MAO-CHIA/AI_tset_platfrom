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
    <table v-else class="schedule-table">
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
            <RouterLink v-else-if="s.last_execution_id" :to="`/results/${s.last_execution_id}`">
              {{ statusLabel(s.last_execution_status) }}
            </RouterLink>
            <span v-else>-</span>
          </td>
          <td>
            <span :class="['badge', s.enabled ? 'on' : 'off']">{{ s.enabled ? '啟用' : '停用' }}</span>
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
.tz-note { font-size: 12px; color: #6b7280; }
.schedule-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.schedule-table th, .schedule-table td { padding: 10px 12px; border-bottom: 1px solid #e5e7eb; text-align: left; }
.schedule-table th { background: #f9fafb; font-weight: 600; color: #374151; }
.schedule-table a { color: #4f46e5; text-decoration: none; }
.schedule-table a:hover { text-decoration: underline; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.badge.on { background: #dcfce7; color: #166534; }
.badge.off { background: #f3f4f6; color: #6b7280; }
.skip { color: #b45309; font-size: 13px; }
.row-actions { white-space: nowrap; }
.btn-link { background: none; border: none; color: #4f46e5; cursor: pointer; font-size: 13px; padding: 2px 6px; }
.btn-link.danger { color: #dc2626; }
.empty { color: #9ca3af; font-size: 14px; padding: 16px 0; }
.error-banner { background: #fee2e2; color: #991b1b; padding: 10px 16px; border-radius: 6px; margin-top: 12px; }
.btn-primary { background: #4f46e5; color: white; padding: 6px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
@media (max-width: 767px) {
  .schedule-table { display: block; overflow-x: auto; }
}
</style>
