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
        <button class="btn-primary" @click="showCreateUser = true">新增帳號</button>
      </div>

      <table class="data-table responsive-table">
        <thead>
          <tr>
            <th>帳號</th><th>角色</th><th>狀態</th><th>建立時間</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td class="cell-title">{{ u.username }}</td>
            <td data-label="角色">
              <select :value="u.role" @change="onRoleChange(u, ($event.target as HTMLSelectElement).value)">
                <option>admin</option>
                <option>editor</option>
                <option>viewer</option>
              </select>
            </td>
            <td data-label="狀態">
              <button class="btn-secondary btn-sm" @click="toggleActive(u)">
                {{ u.is_active ? '停用' : '啟用' }}
              </button>
            </td>
            <td data-label="建立時間">{{ formatDate(u.created_at) }}</td>
            <td class="actions cell-actions">
              <button class="btn-secondary btn-sm" @click="openResetPw(u)">重設密碼</button>
              <button class="btn-danger btn-sm" @click="onDeleteUser(u)">刪除</button>
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
            <button class="btn-primary" @click="submitCreateUser">建立</button>
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
            <button class="btn-primary" @click="submitResetPw">確認</button>
          </div>
        </div>
      </div>
    </section>

    <!-- 系統別管理 -->
    <section v-if="activeTab === 'categories'" class="tab-content">
      <div class="section-toolbar">
        <h2>系統別管理</h2>
        <button class="btn-primary" @click="showCreateCat = true">新增系統別</button>
      </div>

      <table class="data-table responsive-table">
        <thead><tr><th>名稱</th><th>建立時間</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="c in categories" :key="c.id">
            <td class="cell-title">
              <span v-if="editingCatId !== c.id">{{ c.name }}</span>
              <input v-else v-model="editingCatName" @keyup.enter="submitRename(c)" />
            </td>
            <td data-label="建立時間">{{ formatDate(c.created_at) }}</td>
            <td class="actions cell-actions">
              <button v-if="editingCatId !== c.id" class="btn-secondary btn-sm" @click="startRename(c)">重新命名</button>
              <button v-else class="btn-secondary btn-sm" @click="submitRename(c)">儲存</button>
              <button class="btn-danger btn-sm" @click="onDeleteCat(c)">刪除</button>
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
            <button class="btn-primary" @click="submitCreateCat">建立</button>
          </div>
        </div>
      </div>
    </section>

    <!-- LLM 設定（金鑰唯讀 + 啟用模型可切換） -->
    <section v-if="activeTab === 'llm'" class="tab-content">
      <h2>LLM 設定</h2>
      <p class="hint">金鑰與連線由部署的 <code>.env</code> 配置（唯讀）；「目前使用模型」可於此切換並即時生效。</p>
      <div class="llm-row">
        <div class="llm-card">
          <h3>Anthropic (Claude)</h3>
          <p>狀態：{{ llmStatus?.anthropic_key_set ? '✅ 已設定' : '❌ 未設定' }}</p>
          <p v-if="llmStatus?.anthropic_key_set" class="masked-key">{{ llmStatus?.anthropic_key_masked }}</p>
        </div>

        <div class="llm-card">
          <h3>OpenAI (GPT)</h3>
          <p>狀態：{{ llmStatus?.openai_key_set ? '✅ 已設定' : '❌ 未設定' }}</p>
          <p v-if="llmStatus?.openai_key_set" class="masked-key">{{ llmStatus?.openai_key_masked }}</p>
        </div>

        <div class="llm-card">
          <h3>本地 Ollama</h3>
          <p>狀態：{{ llmStatus?.ollama_configured ? '✅ 已設定' : '❌ 未設定' }}</p>
          <p v-if="llmStatus?.ollama_configured" class="masked-key">{{ llmStatus?.ollama_base_url }}</p>
        </div>
      </div>

      <div class="llm-default-model">
        <h3>目前使用模型</h3>
        <p class="hint">套用於所有 AI 補齊／預覽／對話；切換後立即生效，無需重啟。</p>
        <select
          data-testid="active-model-select"
          :value="activeModel"
          @change="onActiveModelChange(($event.target as HTMLSelectElement).value)"
        >
          <optgroup v-for="group in groupedModels" :key="group.provider" :label="group.label">
            <option v-for="m in group.models" :key="m.id" :value="m.id">{{ m.name }}</option>
          </optgroup>
        </select>
        <p v-if="activeModelSaved" class="success-msg">✅ 已切換為 {{ activeModel }}</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as adminApi from '../services/adminApi'
import type { UserRecord, SystemCategory, LlmModel } from '../services/adminApi'
import { confirmAction } from '../composables/useConfirm'
import { formatDate } from '../utils/format'

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
  const ok = await confirmAction({
    title: `刪除帳號「${u.username}」？`,
    message: '刪除後這個帳號將無法登入，且無法復原。',
    confirmLabel: '刪除',
    danger: true,
  })
  if (!ok) return
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
    const ok = await confirmAction({
      title: `刪除系統別「${c.name}」？`,
      message: `有 ${res.affected_case_count} 個案例使用這個系統別，刪除後這些案例的系統別會被清空。`,
      confirmLabel: '刪除',
      danger: true,
    })
    if (!ok) {
      await loadCategories()
      return
    }
  }
  await loadCategories()
}

// ─── LLM 設定（金鑰唯讀 + 啟用模型可切換）───
const llmStatus = ref<adminApi.LlmKeyStatus | null>(null)
const availableModels = ref<LlmModel[]>([])
const activeModel = ref('')
const activeModelSaved = ref(false)

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: 'Anthropic (Claude)',
  openai: 'OpenAI (GPT)',
  ollama: '本地 Ollama',
}

// 僅列可用模型（requires_setup=false），依 provider 分組
const groupedModels = computed(() => {
  const groups: { provider: string; label: string; models: LlmModel[] }[] = []
  for (const m of availableModels.value) {
    if (m.requires_setup) continue
    let g = groups.find((x) => x.provider === m.provider)
    if (!g) {
      g = { provider: m.provider, label: PROVIDER_LABELS[m.provider] || m.provider, models: [] }
      groups.push(g)
    }
    g.models.push(m)
  }
  return groups
})

async function loadLlmStatus() {
  llmStatus.value = await adminApi.getLlmKeyStatus()
}

async function loadLlmModels() {
  const res = await adminApi.getLlmModels()
  availableModels.value = res.models
}

async function loadActiveModel() {
  const res = await adminApi.getActiveModel()
  activeModel.value = res.model
}

async function onActiveModelChange(model: string) {
  await adminApi.setActiveModel(model)
  activeModel.value = model
  activeModelSaved.value = true
  setTimeout(() => (activeModelSaved.value = false), 2500)
}

onMounted(async () => {
  await Promise.all([
    loadUsers(),
    loadCategories(),
    loadLlmStatus(),
    loadLlmModels(),
    loadActiveModel(),
  ])
})
</script>

<style scoped>
.admin-page {
  padding: 32px 24px;
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
  white-space: nowrap;
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
  color: var(--brand-strong);
  border-bottom-color: var(--brand-strong);
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




.actions {
  display: flex;
  gap: 6px;
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
  margin: 0;
  font-size: 0.875rem;
  color: #6b7280;
}

.hint {
  margin: 0 0 16px;
  font-size: 0.8rem;
  color: #6b7280;
}

.hint code {
  background: #f3f4f6;
  padding: 1px 5px;
  border-radius: 3px;
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

.llm-default-model select {
  width: 100%;
  max-width: 360px;
  padding: 7px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
}

@media (max-width: 767px) {
  .admin-page { padding: 20px 16px; }
  .tab-btn { padding: 8px 12px; margin-bottom: 0; }
  .tabs { overflow-x: auto; }
}
</style>
