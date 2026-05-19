<template>
  <div class="db-connection-page">
    <h1>資料庫連線管理</h1>

    <section class="create-form">
      <h2>新增連線</h2>
      <div class="form-row">
        <label>連線名稱</label>
        <input v-model="form.name" placeholder="My SQLite DB" />
      </div>
      <div class="form-row">
        <label>連線字串</label>
        <input v-model="form.connectionString" placeholder="sqlite:///./data/mydb.db" />
      </div>
      <div class="form-row">
        <label>建立者</label>
        <input v-model="form.createdBy" placeholder="tester" />
      </div>
      <button class="btn-primary" :disabled="!form.name || !form.connectionString" @click="handleCreate">
        新增
      </button>
      <span v-if="createError" class="error">{{ createError }}</span>
    </section>

    <section class="connection-list">
      <h2>連線清單</h2>
      <div v-if="connections.length === 0" class="empty-state">尚無連線設定</div>
      <div v-for="conn in connections" :key="conn.id" class="connection-card">
        <div class="conn-name">{{ conn.name }}</div>
        <div class="conn-status">
          <span v-if="conn.last_test_success === true" class="status-ok">✓ 連線正常</span>
          <span v-else-if="conn.last_test_success === false" class="status-fail">✗ 連線失敗</span>
          <span v-else class="status-unknown">未測試</span>
        </div>
        <div class="conn-actions">
          <button class="btn-secondary" @click="handleTest(conn.id)">測試連線</button>
          <button class="btn-primary" @click="selectConnection(conn.id)">查詢</button>
        </div>
      </div>
    </section>

    <section v-if="selectedConnId" class="query-section">
      <h2>執行查詢</h2>
      <textarea v-model="querySQL" placeholder="SELECT * FROM table_name LIMIT 10" rows="4" />
      <button class="btn-primary" :disabled="!querySQL" @click="handleQuery">執行</button>

      <div v-if="queryResult" class="query-result">
        <table>
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
      <div v-if="queryError" class="error">{{ queryError }}</div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import apiClient from '../services/apiClient'

interface Connection {
  id: string
  name: string
  last_test_success: boolean | null
}

const connections = ref<Connection[]>([])
const form = ref({ name: '', connectionString: '', createdBy: '' })
const createError = ref('')
const selectedConnId = ref<string | null>(null)
const querySQL = ref('')
const queryResult = ref<{ columns: string[]; rows: Record<string, unknown>[] } | null>(null)
const queryError = ref('')

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
      created_by: form.value.createdBy,
    })
    form.value = { name: '', connectionString: '', createdBy: '' }
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
