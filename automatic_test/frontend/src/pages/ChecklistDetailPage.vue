<template>
  <div class="page" v-if="checklist">
    <!-- 頁首：清單名稱 + 動作按鈕 -->
    <div class="page-header">
      <div>
        <h1>{{ checklist.name }}</h1>
        <span class="subtitle">測試清單</span>
      </div>
      <div class="actions">
        <button class="btn-secondary" @click="$router.push('/checklists')">← 返回</button>
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
        <dt>建立時間</dt><dd>{{ checklist.created_at ?? '-' }}</dd>
        <dt>案例數</dt><dd>{{ checklist.items.length }}</dd>
      </dl>
    </div>

    <!-- 案例列表區 -->
    <div class="section" data-testid="case-list">
      <h2>所含案例</h2>
      <div v-if="checklist.items.length === 0" class="empty">尚無案例</div>
      <table v-else class="case-table">
        <thead>
          <tr>
            <th>#</th>
            <th>案例編號</th>
            <th>名稱</th>
            <th>系統別</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, idx) in checklist.items" :key="item.id">
            <td>{{ idx + 1 }}</td>
            <td>{{ (item as any).test_case?.case_number ?? item.test_case_id }}</td>
            <td>{{ (item as any).test_case?.name ?? '-' }}</td>
            <td>{{ (item as any).test_case?.system_category ?? '-' }}</td>
            <td>
              <button class="btn-danger-sm" @click="handleRemoveCase(item.test_case_id)">移除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 執行歷史區 -->
    <div class="section" data-testid="execution-history">
      <h2>執行歷史</h2>
      <div v-if="executions.length === 0" class="empty">尚無執行紀錄</div>
      <table v-else class="history-table">
        <thead>
          <tr><th>執行 ID</th><th>狀態</th><th>開始時間</th><th>通過</th><th>失敗</th></tr>
        </thead>
        <tbody>
          <tr
            v-for="ex in executions"
            :key="ex.id"
            class="clickable"
            @click="$router.push(`/results/${ex.id}`)"
          >
            <td>{{ ex.id.slice(0, 8) }}...</td>
            <td>{{ ex.status }}</td>
            <td>{{ ex.started_at ?? '-' }}</td>
            <td>{{ ex.passed_count }}</td>
            <td>{{ ex.failed_count }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="errorMsg" class="error-banner">{{ errorMsg }}</div>
  </div>

  <div v-else-if="loading" class="loading-page">載入中...</div>

  <div v-else class="not-found">
    <p>找不到清單</p>
    <button @click="$router.push('/checklists')">返回清單</button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getChecklist, updateChecklistItems, type ChecklistDetail } from '../services/checklistApi'

const route = useRoute()
const router = useRouter()

const checklist = ref<ChecklistDetail | null>(null)
const executions = ref<any[]>([])
const loading = ref(false)
const errorMsg = ref('')

async function fetchChecklist() {
  loading.value = true
  errorMsg.value = ''
  try {
    checklist.value = await getChecklist(route.params.id as string)
  } catch {
    checklist.value = null
  } finally {
    loading.value = false
  }
}

async function handleRemoveCase(caseId: string) {
  if (!checklist.value) return
  const newIds = checklist.value.items
    .filter((item) => item.test_case_id !== caseId)
    .map((item) => item.test_case_id)
  try {
    checklist.value = await updateChecklistItems(checklist.value.id, newIds)
  } catch {
    errorMsg.value = '移除案例失敗'
  }
}

function handleExecute() {
  alert('執行功能將在後續版本實作')
}

onMounted(fetchChecklist)
</script>

<style scoped>
.page { max-width: 1200px; margin: 0 auto; padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
h1 { font-size: 22px; margin-bottom: 4px; }
.subtitle { font-size: 13px; color: #6b7280; }
.actions { display: flex; gap: 8px; }

.section { margin-bottom: 32px; }
.section h2 { font-size: 16px; font-weight: 600; margin-bottom: 12px; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }

dl { display: grid; grid-template-columns: 100px 1fr; gap: 6px 16px; font-size: 14px; }
dt { font-weight: 600; color: #6b7280; }

.case-table, .history-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.case-table th, .case-table td,
.history-table th, .history-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
}
.case-table th, .history-table th {
  background: #f9fafb;
  font-weight: 600;
  color: #374151;
}
.clickable { cursor: pointer; }
.clickable:hover { background: #f0f4ff; }

.empty { color: #9ca3af; font-size: 14px; padding: 16px 0; }
.error-banner { background: #fee2e2; color: #991b1b; padding: 10px 16px; border-radius: 6px; margin-top: 16px; }
.loading-page, .not-found { padding: 60px; text-align: center; color: #6b7280; }

.btn-primary { background: #4f46e5; color: white; padding: 8px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
.btn-secondary { background: #e5e7eb; color: #374151; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
.btn-danger-sm { background: #fee2e2; color: #dc2626; padding: 4px 10px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }
.btn-danger-sm:hover { background: #fecaca; }
</style>
