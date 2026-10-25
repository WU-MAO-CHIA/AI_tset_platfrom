<template>
  <ElConfigProvider :locale="zhTw">
    <div class="page dashboard">
      <div class="page-header">
        <div>
          <h1>監控儀表板</h1>
          <span class="subtitle">執行佇列與排程的即時狀態，每 {{ REFRESH_SEC }} 秒自動更新</span>
        </div>
        <div class="header-actions">
          <span v-if="data" class="muted">更新於 {{ formatScheduleTime(data.generated_at, data.timezone) }}</span>
          <ElButton :loading="loading" data-testid="btn-refresh" @click="load">重新整理</ElButton>
        </div>
      </div>

      <div v-if="errorMsg" class="error-text" data-testid="dashboard-error">{{ errorMsg }}</div>

      <div class="stats">
        <div class="stat stat-running">
          <ElStatistic title="執行中" :value="data?.counts.running ?? 0" data-testid="stat-running">
            <template #suffix>/ {{ data?.max_concurrent ?? '-' }}</template>
          </ElStatistic>
        </div>
        <div class="stat stat-queued">
          <ElStatistic title="排隊中（尚未執行）" :value="data?.counts.pending ?? 0" data-testid="stat-pending" />
        </div>
        <div class="stat">
          <ElStatistic title="啟用中的排程" :value="data?.counts.schedules_enabled ?? 0" data-testid="stat-schedules">
            <template #suffix>/ {{ data?.counts.schedules_total ?? '-' }}</template>
          </ElStatistic>
        </div>
      </div>

      <section>
        <h2>執行中</h2>
        <ElTable :data="data?.running ?? []" empty-text="目前沒有執行中的項目" data-testid="table-running">
          <ElTableColumn label="項目" min-width="200">
            <template #default="{ row }">
              <RouterLink :to="`/executions/${row.id}`">{{ targetLabel(row) }}</RouterLink>
            </template>
          </ElTableColumn>
          <ElTableColumn label="來源" min-width="140">
            <template #default="{ row }">{{ triggerLabel(row) }}</template>
          </ElTableColumn>
          <ElTableColumn label="開始時間" min-width="150">
            <template #default="{ row }">{{ time(row.started_at) }}</template>
          </ElTableColumn>
          <ElTableColumn label="進度" min-width="220">
            <template #default="{ row }">
              <div class="progress">
                <ElProgress :percentage="percent(row)" :color="'var(--running)'" :show-text="false" />
                <span class="muted">{{ row.passed_count + row.failed_count }} / {{ row.total_count || '-' }}</span>
              </div>
            </template>
          </ElTableColumn>
          <ElTableColumn label="狀態" width="110">
            <template #default="{ row }"><StatusBadge :status="row.status" /></template>
          </ElTableColumn>
        </ElTable>
      </section>

      <section>
        <h2>排隊中</h2>
        <ElTable :data="data?.pending ?? []" empty-text="佇列是空的" data-testid="table-pending">
          <ElTableColumn label="順位" type="index" width="70" />
          <ElTableColumn label="項目" min-width="200">
            <template #default="{ row }">
              <RouterLink :to="`/executions/${row.id}`">{{ targetLabel(row) }}</RouterLink>
            </template>
          </ElTableColumn>
          <ElTableColumn label="來源" min-width="140">
            <template #default="{ row }">{{ triggerLabel(row) }}</template>
          </ElTableColumn>
          <ElTableColumn label="排入時間" min-width="150">
            <template #default="{ row }">{{ time(row.queued_at) }}</template>
          </ElTableColumn>
          <ElTableColumn label="狀態" width="110">
            <template #default="{ row }"><StatusBadge :status="row.status" /></template>
          </ElTableColumn>
        </ElTable>
      </section>

      <section>
        <h2>啟用中的排程</h2>
        <ElTable :data="data?.schedules ?? []" empty-text="沒有啟用中的排程" data-testid="table-schedules">
          <ElTableColumn label="名稱" prop="name" min-width="140" />
          <ElTableColumn label="清單" min-width="160">
            <template #default="{ row }">
              <RouterLink :to="`/checklists/${row.checklist_id}`">{{ row.checklist_name ?? row.checklist_id }}</RouterLink>
            </template>
          </ElTableColumn>
          <ElTableColumn label="頻率" min-width="140">
            <template #default="{ row }">{{ frequencyLabel(row) }}</template>
          </ElTableColumn>
          <ElTableColumn label="下次執行" min-width="150">
            <template #default="{ row }">{{ formatScheduleTime(row.next_run_at, row.timezone) }}</template>
          </ElTableColumn>
          <ElTableColumn label="上次結果" width="130">
            <template #default="{ row }">
              <span v-if="row.last_skip_reason" class="muted" :title="row.last_skip_reason">已略過</span>
              <RouterLink v-else-if="row.last_execution_id" :to="`/results/${row.last_execution_id}`">
                <StatusBadge :status="row.last_execution_status" />
              </RouterLink>
              <span v-else>-</span>
            </template>
          </ElTableColumn>
        </ElTable>
      </section>
    </div>
  </ElConfigProvider>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useIntervalFn } from '@vueuse/core'
import { ElButton, ElConfigProvider, ElProgress, ElStatistic, ElTable, ElTableColumn } from 'element-plus'
// 只載入用到元件的樣式，避免整包 element-plus CSS
import 'element-plus/es/components/button/style/css'
import 'element-plus/es/components/progress/style/css'
import 'element-plus/es/components/statistic/style/css'
import 'element-plus/es/components/table/style/css'
import 'element-plus/es/components/table-column/style/css'
import zhTw from 'element-plus/es/locale/lang/zh-tw'
import StatusBadge from '../components/StatusBadge/index.vue'
import { getDashboard, type Dashboard, type DashboardExecution } from '../services/dashboardApi'
import type { Schedule } from '../services/scheduleApi'
import { describeFrequency, formatScheduleTime, triggerLabel } from '../utils/scheduleFormat'

const REFRESH_SEC = 5

const data = ref<Dashboard | null>(null)
const loading = ref(false)
const errorMsg = ref('')

async function load() {
  loading.value = true
  try {
    data.value = await getDashboard()
    errorMsg.value = ''
  } catch {
    errorMsg.value = '無法載入儀表板資料'
  } finally {
    loading.value = false
  }
}

useIntervalFn(load, REFRESH_SEC * 1000, { immediateCallback: true })

function frequencyLabel(r: unknown): string {
  return describeFrequency(r as Schedule)
}

function time(iso: string | null): string {
  return formatScheduleTime(iso, data.value?.timezone ?? 'Asia/Taipei')
}

// ElTable 的 slot row 型別是寬鬆的 DefaultRow，這裡統一轉回 API 型別
function targetLabel(r: unknown): string {
  const row = r as DashboardExecution
  const name = row.target_name ?? row.checklist_id ?? row.source_case_id ?? row.id
  return row.execution_type === 'trial_run' ? `試跑：${name}` : name
}

function percent(r: unknown): number {
  const row = r as DashboardExecution
  if (!row.total_count) return 0
  return Math.min(100, Math.round(((row.passed_count + row.failed_count) / row.total_count) * 100))
}
</script>

<style scoped>
/* Element Plus 主色改為平台淺藍 */
.dashboard {
  --el-color-primary: var(--brand-strong);
  --el-color-primary-light-3: var(--brand);
  --el-color-primary-light-9: var(--brand-soft);
  --el-text-color-primary: var(--ink);
  --el-border-color-lighter: var(--line);
  --el-table-header-bg-color: var(--table-head);
}
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
h1 { margin-bottom: 4px; }
.subtitle { color: var(--ink-muted); }
.header-actions { display: flex; align-items: center; gap: 12px; }

.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 32px; }
.stat { padding: 16px 20px; background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius-lg); }
.stat-running { border-left: 4px solid var(--running); }
.stat-queued { border-left: 4px solid var(--queued); }

section { margin-bottom: 32px; }
section h2 { margin-bottom: 12px; }
section :deep(.el-table) { border: 1px solid var(--line); border-radius: var(--radius-lg); }

.progress { display: flex; align-items: center; gap: 10px; }
.progress :deep(.el-progress) { flex: 1; }

@media (max-width: 767px) {
  .stats { grid-template-columns: 1fr; gap: 10px; }
}
</style>
