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
import { reactive, ref } from 'vue'
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
})
const error = ref('')

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
