<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1>資料庫連線</h1>
        <p class="muted">測試案例可透過這些連線查詢或驗證資料</p>
      </div>
    </div>

    <section class="section">
      <h2>連線清單</h2>
      <p v-if="connections.length === 0" class="empty-state">還沒有任何連線，從下方「新增連線」開始。</p>
      <table v-else class="data-table">
        <thead>
          <tr><th>名稱</th><th>狀態</th><th class="col-actions"></th></tr>
        </thead>
        <tbody>
          <tr v-for="conn in connections" :key="conn.id" :class="{ selected: conn.id === selectedConnId }">
            <td class="conn-name">{{ conn.name }}</td>
            <td>
              <span v-if="conn.last_test_success === true" class="badge badge-pass">連線正常</span>
              <span v-else-if="conn.last_test_success === false" class="badge badge-fail">連線失敗</span>
              <span v-else class="badge">未測試</span>
            </td>
            <td class="col-actions">
              <button class="btn-secondary" @click="handleTest(conn.id)">測試連線</button>
              <button class="btn-secondary" @click="selectConnection(conn.id)">查詢</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="selectedConnId" class="section">
      <h2>執行查詢 <span class="muted">{{ selectedConnName }}</span></h2>
      <textarea v-model="querySQL" placeholder="SELECT * FROM table_name LIMIT 10" rows="4" class="sql-input" />
      <div class="form-actions">
        <button class="btn-primary" :disabled="!querySQL" @click="handleQuery">執行查詢</button>
        <span v-if="queryError" class="error-text">{{ queryError }}</span>
      </div>

      <div v-if="queryResult" class="query-result">
        <table class="data-table">
          <thead>
            <tr>
              <th v-for="col in queryResult.columns" :key="col">{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in queryResult.rows" :key="idx">
              <td v-for="col in queryResult.columns" :key="col">{{ row[col] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <h2>新增連線</h2>
      <form class="create-form" @submit.prevent="handleCreate">
        <label class="field">
          <span>連線名稱</span>
          <input v-model="form.name" placeholder="例如：會員資料庫" />
        </label>
        <label class="field">
          <span>連線字串</span>
          <input v-model="form.connectionString" placeholder="sqlite:///./data/mydb.db" />
        </label>
        <div class="form-actions">
          <button type="submit" class="btn-primary" :disabled="!form.name || !form.connectionString">新增連線</button>
          <span v-if="createError" class="error-text">{{ createError }}</span>
        </div>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import apiClient from '../services/apiClient'
import { useAuthStore } from '../stores/authStore'

const authStore = useAuthStore()

interface Connection {
  id: string
  name: string
  last_test_success: boolean | null
}

const connections = ref<Connection[]>([])
const form = ref({ name: '', connectionString: '' })
const createError = ref('')
const selectedConnId = ref<string | null>(null)
const querySQL = ref('')
const queryResult = ref<{ columns: string[]; rows: Record<string, unknown>[] } | null>(null)
const queryError = ref('')
const selectedConnName = computed(() => connections.value.find((c) => c.id === selectedConnId.value)?.name ?? '')

async function fetchConnections() {
  const res = await apiClient.get<{ items: Connection[] }>('/db-connections')
  connections.value = res.data.items
}

async function handleCreate() {
  createError.value = ''
  try {
    await apiClient.post('/db-connections', {
      name: form.value.name,
      connection_string: form.value.connectionString,
      created_by: authStore.username ?? '',
    })
    form.value = { name: '', connectionString: '' }
    await fetchConnections()
  } catch {
    createError.value = '建立失敗，請確認資料'
  }
}

async function handleTest(connId: string) {
  await apiClient.post(`/db-connections/${connId}/test`)
  await fetchConnections()
}

function selectConnection(connId: string) {
  selectedConnId.value = connId
  queryResult.value = null
  queryError.value = ''
}

async function handleQuery() {
  if (!selectedConnId.value) return
  queryError.value = ''
  queryResult.value = null
  try {
    const res = await apiClient.post<{ columns: string[]; rows: Record<string, unknown>[] }>(
      `/db-connections/${selectedConnId.value}/query`,
      { sql: querySQL.value }
    )
    queryResult.value = res.data
  } catch (err: unknown) {
    queryError.value = '查詢失敗'
  }
}

onMounted(fetchConnections)
</script>

<style scoped>
.page-header { margin-bottom: 32px; }
.page-header .muted { margin-top: 4px; }

.section { margin-bottom: 40px; }
.section h2 { display: flex; align-items: baseline; gap: 8px; margin-bottom: 12px; }
.section h2 .muted { font-weight: 400; font-size: var(--fs-14); }

.conn-name { font-weight: 600; }
.col-actions { text-align: right; white-space: nowrap; }
.col-actions button + button { margin-left: 8px; }
tr.selected td { background: var(--brand-soft); }

.sql-input { width: 100%; font-family: var(--font-mono); resize: vertical; }

.create-form { display: grid; gap: 16px; max-width: 560px; }
.field { display: grid; gap: 6px; }
.field span { font-size: var(--fs-12); color: var(--ink-muted); }

.form-actions { display: flex; align-items: center; gap: 12px; margin-top: 12px; }
.create-form .form-actions { margin-top: 0; }

.query-result { margin-top: 16px; overflow-x: auto; }
</style>
