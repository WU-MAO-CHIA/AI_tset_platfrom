<template>
  <div class="admin-page">
    <div class="page-header">
      <h1>管理後台</h1>
    </div>

    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab-btn', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >{{ tab.label }}</button>
    </div>

    <!-- 帳號管理 -->
    <section v-if="activeTab === 'users'" class="tab-content">
      <div class="section-toolbar">
        <h2>帳號管理</h2>
        <button class="primary" @click="showCreateUser = true">+ 新增帳號</button>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>帳號</th><th>角色</th><th>狀態</th><th>建立時間</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.username }}</td>
            <td>
              <select :value="u.role" @change="onRoleChange(u, ($event.target as HTMLSelectElement).value)">
                <option>admin</option>
                <option>editor</option>
                <option>viewer</option>
              </select>
            </td>
            <td>
              <button class="small-btn" @click="toggleActive(u)">
                {{ u.is_active ? '停用' : '啟用' }}
              </button>
            </td>
            <td>{{ u.created_at.slice(0, 10) }}</td>
            <td class="actions">
              <button class="small-btn" @click="openResetPw(u)">重設密碼</button>
              <button class="small-btn danger" @click="onDeleteUser(u)">刪除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 新增帳號 modal -->
      <div v-if="showCreateUser" class="modal-overlay" @click.self="showCreateUser = false">
        <div class="modal">
          <h3>新增帳號</h3>
          <div class="field"><label>帳號</label><input v-model="newUser.username" /></div>
          <div class="field"><label>密碼</label><input v-model="newUser.password" type="password" /></div>
          <div class="field">
            <label>角色</label>
            <select v-model="newUser.role">
              <option>admin</option><option>editor</option><option>viewer</option>
            </select>
          </div>
          <p v-if="userError" class="error-msg">{{ userError }}</p>
          <div class="modal-actions">
            <button @click="showCreateUser = false">取消</button>
            <button class="primary" @click="submitCreateUser">建立</button>
          </div>
        </div>
      </div>

      <!-- 重設密碼 modal -->
      <div v-if="resetPwTarget" class="modal-overlay" @click.self="resetPwTarget = null">
        <div class="modal">
          <h3>重設密碼 — {{ resetPwTarget.username }}</h3>
          <div class="field"><label>新密碼</label><input v-model="newPassword" type="password" /></div>
          <p v-if="userError" class="error-msg">{{ userError }}</p>
          <div class="modal-actions">
            <button @click="resetPwTarget = null">取消</button>
            <button class="primary" @click="submitResetPw">確認</button>
          </div>
        </div>
      </div>
    </section>

    <!-- 系統別管理 -->
    <section v-if="activeTab === 'categories'" class="tab-content">
      <div class="section-toolbar">
        <h2>系統別管理</h2>
        <button class="primary" @click="showCreateCat = true">+ 新增系統別</button>
      </div>

      <table class="data-table">
        <thead><tr><th>名稱</th><th>建立時間</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="c in categories" :key="c.id">
            <td>
              <span v-if="editingCatId !== c.id">{{ c.name }}</span>
              <input v-else v-model="editingCatName" @keyup.enter="submitRename(c)" />
            </td>
            <td>{{ c.created_at.slice(0, 10) }}</td>
            <td class="actions">
              <button v-if="editingCatId !== c.id" class="small-btn" @click="startRename(c)">重新命名</button>
              <button v-else class="small-btn" @click="submitRename(c)">儲存</button>
              <button class="small-btn danger" @click="onDeleteCat(c)">刪除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="showCreateCat" class="modal-overlay" @click.self="showCreateCat = false">
        <div class="modal">
          <h3>新增系統別</h3>
          <div class="field"><label>名稱</label><input v-model="newCatName" /></div>
          <p v-if="catError" class="error-msg">{{ catError }}</p>
          <div class="modal-actions">
            <button @click="showCreateCat = false">取消</button>
            <button class="primary" @click="submitCreateCat">建立</button>
          </div>
        </div>
      </div>
    </section>

    <!-- LLM API Keys -->
    <section v-if="activeTab === 'llm'" class="tab-content">
      <h2>LLM API Keys</h2>
      <div class="llm-row">
        <div class="llm-card">
          <h3>Anthropic (Claude)</h3>
          <p>狀態：{{ llmStatus?.anthropic_key_set ? '✅ 已設定' : '❌ 未設定' }}</p>
          <p v-if="llmStatus?.anthropic_key_set" class="masked-key">目前：{{ llmStatus?.anthropic_key_masked }}</p>
          <div class="field">
            <label>覆寫 API Key</label>
            <input v-model="anthropicKey" type="password" placeholder="sk-ant-..." />
          </div>
          <button class="primary" :disabled="!anthropicKey" @click="submitLlmKey('anthropic', anthropicKey)">儲存</button>
        </div>

        <div class="llm-card">
          <h3>OpenAI (GPT)</h3>
          <p>狀態：{{ llmStatus?.openai_key_set ? '✅ 已設定' : '❌ 未設定' }}</p>
          <p v-if="llmStatus?.openai_key_set" class="masked-key">目前：{{ llmStatus?.openai_key_masked }}</p>
          <div class="field">
            <label>覆寫 API Key</label>
            <input v-model="openaiKey" type="password" placeholder="sk-..." />
          </div>
          <button class="primary" :disabled="!openaiKey" @click="submitLlmKey('openai', openaiKey)">儲存</button>
        </div>
      </div>

      <div class="llm-default-model">
        <h3>全域預設模型</h3>
        <p class="hint">所有 AI 補齊／RF 代碼生成將使用此模型；僅列出已設定 API Key 的可用模型。</p>
        <select
          data-testid="default-model-select"
          :value="defaultModel"
          @change="onDefaultModelChange(($event.target as HTMLSelectElement).value)"
        >
          <option v-for="m in availableModels" :key="m.id" :value="m.id">
            {{ m.name }}（{{ m.provider }}）
          </option>
        </select>
      </div>

      <p v-if="llmMsg" class="success-msg">{{ llmMsg }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as adminApi from '../services/adminApi'
import type { UserRecord, SystemCategory, LlmModel } from '../services/adminApi'

const tabs = [
  { key: 'users', label: '帳號管理' },
  { key: 'categories', label: '系統別管理' },
  { key: 'llm', label: 'LLM API Keys' },
]
const activeTab = ref('users')

// ─── 帳號管理 ───
const users = ref<UserRecord[]>([])
const showCreateUser = ref(false)
const newUser = ref({ username: '', password: '', role: 'viewer' })
const userError = ref('')
const resetPwTarget = ref<UserRecord | null>(null)
const newPassword = ref('')

async function loadUsers() {
  users.value = await adminApi.listUsers()
}

async function submitCreateUser() {
  userError.value = ''
  try {
    await adminApi.createUser(newUser.value)
    showCreateUser.value = false
    newUser.value = { username: '', password: '', role: 'viewer' }
    await loadUsers()
  } catch (e: any) {
    userError.value = e.message || '建立失敗'
  }
}

async function onRoleChange(u: UserRecord, role: string) {
  await adminApi.updateUser(u.id, { role })
  await loadUsers()
}

async function toggleActive(u: UserRecord) {
  await adminApi.updateUser(u.id, { is_active: !u.is_active })
  await loadUsers()
}

function openResetPw(u: UserRecord) {
  resetPwTarget.value = u
  newPassword.value = ''
  userError.value = ''
}

async function submitResetPw() {
  userError.value = ''
  try {
    await adminApi.updateUser(resetPwTarget.value!.id, { new_password: newPassword.value })
    resetPwTarget.value = null
  } catch (e: any) {
    userError.value = e.message || '更新失敗'
  }
}

async function onDeleteUser(u: UserRecord) {
  if (!confirm(`確定要刪除帳號「${u.username}」？`)) return
  await adminApi.deleteUser(u.id)
  await loadUsers()
}

// ─── 系統別管理 ───
const categories = ref<SystemCategory[]>([])
const showCreateCat = ref(false)
const newCatName = ref('')
const catError = ref('')
const editingCatId = ref<string | null>(null)
const editingCatName = ref('')

async function loadCategories() {
  categories.value = await adminApi.listSystemCategories()
}

async function submitCreateCat() {
  catError.value = ''
  try {
    await adminApi.createSystemCategory(newCatName.value)
    showCreateCat.value = false
    newCatName.value = ''
    await loadCategories()
  } catch (e: any) {
    catError.value = e.message || '建立失敗'
  }
}

function startRename(c: SystemCategory) {
  editingCatId.value = c.id
  editingCatName.value = c.name
}

async function submitRename(c: SystemCategory) {
  await adminApi.renameSystemCategory(c.id, editingCatName.value)
  editingCatId.value = null
  await loadCategories()
}

async function onDeleteCat(c: SystemCategory) {
  const res = await adminApi.deleteSystemCategory(c.id)
  if (res.affected_case_count > 0) {
    if (!confirm(`刪除「${c.name}」將影響 ${res.affected_case_count} 個案例的系統別欄位，確定繼續？`)) {
      await loadCategories()
      return
    }
  }
  await loadCategories()
}

// ─── LLM Key 管理 ───
const llmStatus = ref<adminApi.LlmKeyStatus | null>(null)
const anthropicKey = ref('')
const openaiKey = ref('')
const llmMsg = ref('')
const defaultModel = ref('')
const availableModels = ref<LlmModel[]>([])

async function loadLlmStatus() {
  llmStatus.value = await adminApi.getLlmKeyStatus()
}

async function loadLlmModels() {
  const [list, def] = await Promise.all([adminApi.getLlmModels(), adminApi.getDefaultModel()])
  availableModels.value = list.models.filter((m) => !m.requires_setup)
  defaultModel.value = def.model
}

async function onDefaultModelChange(model: string) {
  defaultModel.value = model
  await adminApi.setDefaultModel(model)
  llmMsg.value = `全域預設模型已更新為 ${model}`
  setTimeout(() => { llmMsg.value = '' }, 3000)
}

async function submitLlmKey(provider: string, key: string) {
  await adminApi.setLlmKey(provider, key)
  llmMsg.value = `${provider} API Key 已更新`
  if (provider === 'anthropic') anthropicKey.value = ''
  else openaiKey.value = ''
  await loadLlmStatus()
  setTimeout(() => { llmMsg.value = '' }, 3000)
}

onMounted(async () => {
  await Promise.all([loadUsers(), loadCategories(), loadLlmStatus(), loadLlmModels()])
})
</script>

<style scoped>
.admin-page {
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 20px;
}

.tabs {
  display: flex;
  gap: 4px;
  border-bottom: 2px solid #e5e7eb;
  margin-bottom: 24px;
}

.tab-btn {
  padding: 8px 20px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 0.9rem;
  color: #6b7280;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}

.tab-btn.active {
  color: #4f46e5;
  border-bottom-color: #4f46e5;
  font-weight: 500;
}

.tab-content { }

.section-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-toolbar h2 {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.data-table th, .data-table td {
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  text-align: left;
}

.data-table th {
  background: #f9fafb;
  font-weight: 600;
}

.actions {
  display: flex;
  gap: 6px;
}

.small-btn {
  padding: 3px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #f9fafb;
  cursor: pointer;
  font-size: 0.8rem;
}

.small-btn.danger {
  border-color: #fca5a5;
  color: #dc2626;
  background: #fff;
}

.primary {
  background: #4f46e5;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 6px 14px;
  cursor: pointer;
  font-size: 0.875rem;
}

.primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.modal {
  background: white;
  border-radius: 8px;
  padding: 28px;
  width: 380px;
}

.modal h3 {
  margin: 0 0 20px;
  font-size: 1rem;
  font-weight: 600;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

.field {
  margin-bottom: 14px;
}

.field label {
  display: block;
  font-size: 0.85rem;
  margin-bottom: 4px;
  color: #374151;
}

.field input, .field select {
  width: 100%;
  padding: 7px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
  box-sizing: border-box;
}

.error-msg {
  color: #dc2626;
  font-size: 0.85rem;
}

.success-msg {
  color: #059669;
  font-size: 0.875rem;
  margin-top: 12px;
}

.llm-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.llm-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
}

.llm-card h3 {
  margin: 0 0 8px;
  font-size: 0.95rem;
  font-weight: 600;
}

.llm-card p {
  margin: 0 0 12px;
  font-size: 0.875rem;
  color: #374151;
}

.masked-key {
  font-family: monospace;
  color: #6b7280;
  font-size: 0.8rem;
}

.llm-default-model {
  margin-top: 24px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
}

.llm-default-model h3 {
  margin: 0 0 8px;
  font-size: 0.95rem;
  font-weight: 600;
}

.llm-default-model .hint {
  margin: 0 0 12px;
  font-size: 0.8rem;
  color: #6b7280;
}

.llm-default-model select {
  width: 100%;
  max-width: 360px;
  padding: 7px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
}
</style>
