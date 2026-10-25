<template>
  <div class="modal-overlay" @click.self="$emit('cancel')">
    <form class="modal" data-testid="schedule-form" @submit.prevent="submit">
      <h3>{{ schedule ? '編輯排程' : '新增排程' }}</h3>

      <label>名稱
        <input v-model="form.name" class="modal-input" data-testid="schedule-name" maxlength="100" />
      </label>

      <label>頻率
        <select v-model="form.frequency" class="modal-input" data-testid="schedule-frequency">
          <option value="daily">每天</option>
          <option value="weekly">每週</option>
          <option value="interval">每隔一段時間</option>
        </select>
      </label>

      <div v-if="form.frequency === 'weekly'" class="weekday-row" data-testid="schedule-weekdays">
        <label v-for="(label, idx) in WEEKDAY_LABELS" :key="idx" class="weekday">
          <input type="checkbox" :value="idx" v-model="form.weekdays" />週{{ label }}
        </label>
      </div>

      <label v-if="form.frequency !== 'interval'">時間（{{ timezone }}）
        <input v-model="form.time_of_day" type="time" class="modal-input" data-testid="schedule-time" />
      </label>

      <label v-else>間隔（分鐘，至少 15）
        <input v-model.number="form.interval_minutes" type="number" min="15" step="5" class="modal-input" data-testid="schedule-interval" />
      </label>

      <label class="inline">
        <input type="checkbox" v-model="form.parallel_mode" />平行執行
      </label>
      <label v-if="form.parallel_mode">平行數
        <input v-model.number="form.max_workers" type="number" min="1" class="modal-input" />
      </label>

      <label v-if="hasKind('linux')">網頁案例的執行環境
        <RunnerEnvironmentSelect
          v-model="form.linux_environment_id"
          :environments="environments"
          kind="linux"
          default-label="依各案例設定"
          data-testid="schedule-linux-env"
        />
      </label>
      <label v-if="hasKind('windows')">桌面案例的執行環境
        <RunnerEnvironmentSelect
          v-model="form.windows_environment_id"
          :environments="environments"
          kind="windows"
          default-label="依各案例設定"
          data-testid="schedule-windows-env"
        />
      </label>

      <label class="inline">
        <input type="checkbox" v-model="form.enabled" />啟用
      </label>

      <div v-if="error" class="form-error" data-testid="schedule-form-error">{{ error }}</div>

      <div class="modal-actions">
        <button type="button" class="btn-secondary" @click="$emit('cancel')">取消</button>
        <button type="submit" class="btn-primary" :disabled="saving">儲存</button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import RunnerEnvironmentSelect from '../RunnerEnvironmentSelect/index.vue'
import { listEnvironments, type EnvironmentKind, type RunnerEnvironment } from '../../services/runnerEnvironmentApi'
import type { Schedule, ScheduleInput } from '../../services/scheduleApi'
import { WEEKDAY_LABELS } from '../../utils/scheduleFormat'

const props = withDefaults(defineProps<{
  schedule?: Schedule | null
  timezone?: string
  saving?: boolean
}>(), { schedule: null, timezone: 'Asia/Taipei', saving: false })

const emit = defineEmits<{
  (e: 'submit', payload: ScheduleInput): void
  (e: 'cancel'): void
}>()

const form = reactive({
  name: props.schedule?.name ?? '',
  enabled: props.schedule?.enabled ?? true,
  frequency: props.schedule?.frequency ?? 'daily',
  time_of_day: props.schedule?.time_of_day ?? '02:00',
  weekdays: [...(props.schedule?.weekdays ?? [0])],
  interval_minutes: props.schedule?.interval_minutes ?? 60,
  parallel_mode: props.schedule?.parallel_mode ?? false,
  max_workers: props.schedule?.max_workers ?? 1,
  linux_environment_id: props.schedule?.linux_environment_id ?? null,
  windows_environment_id: props.schedule?.windows_environment_id ?? null,
})
const error = ref('')

// 執行環境（spec 005）：只有一個環境可選時（例如只有預設容器）不顯示
const environments = ref<RunnerEnvironment[]>([])
function hasKind(kind: EnvironmentKind): boolean {
  return environments.value.filter((e) => e.enabled && e.kind === kind).length > (kind === 'linux' ? 1 : 0)
}

onMounted(async () => {
  try {
    environments.value = await listEnvironments()
  } catch {
    // 讀不到時排程照各案例的預設環境執行
  }
})

function submit() {
  error.value = ''
  if (!form.name.trim()) {
    error.value = '請輸入名稱'
    return
  }
  if (form.frequency !== 'interval' && !/^\d{2}:\d{2}$/.test(form.time_of_day)) {
    error.value = '請選擇時間'
    return
  }
  if (form.frequency === 'weekly' && form.weekdays.length === 0) {
    error.value = '請至少選擇一天'
    return
  }
  if (form.frequency === 'interval' && !(Number.isInteger(form.interval_minutes) && form.interval_minutes >= 15)) {
    error.value = '間隔至少 15 分鐘'
    return
  }
  emit('submit', {
    name: form.name.trim(),
    enabled: form.enabled,
    frequency: form.frequency,
    time_of_day: form.frequency === 'interval' ? null : form.time_of_day,
    weekdays: form.frequency === 'weekly' ? [...form.weekdays].sort((a, b) => a - b) : null,
    interval_minutes: form.frequency === 'interval' ? form.interval_minutes : null,
    parallel_mode: form.parallel_mode,
    max_workers: form.parallel_mode ? form.max_workers : 1,
    linux_environment_id: form.linux_environment_id,
    windows_environment_id: form.windows_environment_id,
  })
}

</script>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(14, 42, 68, 0.35); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: var(--paper); border-radius: var(--radius-lg); padding: 24px; min-width: 360px; max-width: 92vw; }
.modal h3 { font-size: var(--fs-20); font-weight: 600; margin-bottom: 16px; }
.modal label { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; color: var(--ink-muted); }
.modal label.inline { flex-direction: row; align-items: center; gap: 6px; color: var(--ink); }
.modal label.weekday { flex-direction: row; align-items: center; gap: 4px; margin-bottom: 0; color: var(--ink); }
.weekday-row { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-bottom: 12px; }
.modal-input { width: 100%; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 20px; }
.form-error { background: var(--fail-bg); color: var(--fail); padding: 8px 12px; border-radius: var(--radius); font-size: var(--fs-12); }
</style>
