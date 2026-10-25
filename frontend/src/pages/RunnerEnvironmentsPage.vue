<template>
  <ElConfigProvider :locale="zhTw">
    <div class="page runner-envs">
      <div class="page-header">
        <div>
          <h1>執行環境</h1>
          <span class="subtitle">測試要送到哪一台 runner 執行。Linux 容器跑網頁測試，Windows 跑桌面應用程式測試。</span>
        </div>
        <div class="header-actions">
          <ElButton :loading="loading" data-testid="btn-refresh" @click="load">重新整理</ElButton>
          <ElButton type="primary" data-testid="btn-add" @click="openCreate">新增環境</ElButton>
        </div>
      </div>

      <div v-if="errorMsg" class="error-text" data-testid="env-error">{{ errorMsg }}</div>

      <ElTable :data="environments" empty-text="尚未登記執行環境" data-testid="env-table">
        <ElTableColumn label="名稱" min-width="160">
          <template #default="{ row }">
            {{ row.name }}
            <ElTag v-if="row.is_builtin" size="small" type="info" class="builtin-tag">內建</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="類型" min-width="150">
          <template #default="{ row }">{{ KIND_LABEL[row.kind as EnvironmentKind] }}</template>
        </ElTableColumn>
        <ElTableColumn label="位址" min-width="200">
          <template #default="{ row }">
            <span v-if="row.is_builtin" class="muted">docker compose 內建</span>
            <code v-else>{{ row.url }}</code>
          </template>
        </ElTableColumn>
        <ElTableColumn label="狀態" width="130">
          <template #default="{ row }">
            <span v-if="!row.enabled" class="status status-disabled">已停用</span>
            <span v-else class="status" :class="`status-${row.status}`" :data-testid="`status-${row.id}`">
              {{ STATUS_LABEL[row.status as EnvironmentStatus] }}
            </span>
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="230">
          <template #default="{ row }">
            <ElButton link :data-testid="`btn-check-${row.id}`" @click="onCheck(row)">重新檢查</ElButton>
            <template v-if="!row.is_builtin">
              <ElButton link :data-testid="`btn-edit-${row.id}`" @click="openEdit(row)">編輯</ElButton>
              <ElButton link type="danger" :data-testid="`btn-delete-${row.id}`" @click="onDelete(row)">刪除</ElButton>
            </template>
          </template>
        </ElTableColumn>
      </ElTable>

      <ElDialog v-model="dialogOpen" :title="editingId ? '編輯執行環境' : '新增執行環境'" width="480px">
        <ElForm label-position="top" @submit.prevent>
          <ElFormItem label="名稱" required>
            <ElInput v-model="form.name" maxlength="100" placeholder="例如：Windows 測試機 A" data-testid="input-name" />
          </ElFormItem>
          <ElFormItem label="類型" required>
            <ElRadioGroup v-model="form.kind" :disabled="!!editingId" data-testid="input-kind">
              <ElRadio value="linux">{{ KIND_LABEL.linux }}</ElRadio>
              <ElRadio value="windows">{{ KIND_LABEL.windows }}</ElRadio>
            </ElRadioGroup>
            <div v-if="editingId" class="hint">類型建立後不能修改。</div>
          </ElFormItem>
          <ElFormItem label="位址" required>
            <ElInput v-model="form.url" placeholder="http://10.0.0.5:9000" data-testid="input-url" />
          </ElFormItem>
          <ElFormItem label="Token" :required="!editingId">
            <ElInput
              v-model="form.token"
              type="password"
              show-password
              autocomplete="new-password"
              :placeholder="editingId ? '留空表示不變' : 'runner 的 RUNNER_TOKEN'"
              data-testid="input-token"
            />
          </ElFormItem>
          <ElFormItem label="啟用">
            <ElSwitch v-model="form.enabled" data-testid="input-enabled" />
          </ElFormItem>
        </ElForm>
        <div v-if="formError" class="error-text" data-testid="form-error">{{ formError }}</div>
        <template #footer>
          <ElButton @click="dialogOpen = false">取消</ElButton>
          <ElButton type="primary" :loading="saving" data-testid="btn-save" @click="onSave">儲存</ElButton>
        </template>
      </ElDialog>
    </div>
  </ElConfigProvider>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  ElButton, ElConfigProvider, ElDialog, ElForm, ElFormItem, ElInput, ElRadio, ElRadioGroup, ElSwitch,
  ElTable, ElTableColumn, ElTag,
} from 'element-plus'
import 'element-plus/es/components/button/style/css'
import 'element-plus/es/components/dialog/style/css'
import 'element-plus/es/components/form/style/css'
import 'element-plus/es/components/form-item/style/css'
import 'element-plus/es/components/input/style/css'
import 'element-plus/es/components/radio/style/css'
import 'element-plus/es/components/radio-group/style/css'
import 'element-plus/es/components/switch/style/css'
import 'element-plus/es/components/table/style/css'
import 'element-plus/es/components/table-column/style/css'
import 'element-plus/es/components/tag/style/css'
import zhTw from 'element-plus/es/locale/lang/zh-tw'
import { confirmAction } from '../composables/useConfirm'
import {
  KIND_LABEL, STATUS_LABEL, checkEnvironment, createEnvironment, deleteEnvironment, listEnvironments,
  updateEnvironment, type EnvironmentKind, type EnvironmentStatus, type RunnerEnvironment,
} from '../services/runnerEnvironmentApi'

const environments = ref<RunnerEnvironment[]>([])
const loading = ref(false)
const errorMsg = ref('')

const dialogOpen = ref(false)
const editingId = ref<string | null>(null)
const saving = ref(false)
const formError = ref('')
const form = reactive({ name: '', kind: 'linux' as EnvironmentKind, url: '', token: '', enabled: true })

async function load() {
  loading.value = true
  try {
    environments.value = await listEnvironments()
    errorMsg.value = ''
  } catch (e: any) {
    errorMsg.value = `無法載入執行環境：${e.message}`
  } finally {
    loading.value = false
  }
}

onMounted(load)

function openCreate() {
  editingId.value = null
  Object.assign(form, { name: '', kind: 'linux', url: '', token: '', enabled: true })
  formError.value = ''
  dialogOpen.value = true
}

function openEdit(r: unknown) {
  const row = r as RunnerEnvironment
  editingId.value = row.id
  Object.assign(form, { name: row.name, kind: row.kind, url: row.url ?? '', token: '', enabled: row.enabled })
  formError.value = ''
  dialogOpen.value = true
}

function replace(updated: RunnerEnvironment) {
  const idx = environments.value.findIndex((e) => e.id === updated.id)
  if (idx >= 0) environments.value[idx] = updated
  else environments.value.push(updated)
}

async function onSave() {
  if (!form.name.trim() || !form.url.trim() || (!editingId.value && !form.token)) {
    formError.value = '請填寫名稱、位址與 token'
    return
  }
  saving.value = true
  formError.value = ''
  try {
    if (editingId.value) {
      const { kind: _kind, ...changes } = form
      replace(await updateEnvironment(editingId.value, changes))
    } else {
      replace(await createEnvironment({ ...form }))
    }
    dialogOpen.value = false
  } catch (e: any) {
    formError.value = e.message
  } finally {
    saving.value = false
  }
}

async function onCheck(r: unknown) {
  const row = r as RunnerEnvironment
  try {
    replace(await checkEnvironment(row.id))
  } catch (e: any) {
    errorMsg.value = e.message
  }
}

async function onDelete(r: unknown) {
  const row = r as RunnerEnvironment
  const fallback = row.kind === 'linux'
    ? '使用這個環境的案例會改回「預設容器」。'
    : '使用這個環境的案例需要重新選擇執行環境。'
  const ok = await confirmAction({ title: `刪除「${row.name}」？`, message: fallback, confirmLabel: '刪除', danger: true })
  if (!ok) return
  try {
    await deleteEnvironment(row.id)
    environments.value = environments.value.filter((e) => e.id !== row.id)
  } catch (e: any) {
    errorMsg.value = e.message
  }
}
</script>

<style scoped>
/* Element Plus 主色改為平台淺藍（與監控儀表板相同） */
.runner-envs {
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
.runner-envs :deep(.el-table) { border: 1px solid var(--line); border-radius: var(--radius-lg); }
.builtin-tag { margin-left: 6px; }
.muted { color: var(--ink-faint); }
.hint { color: var(--ink-faint); font-size: var(--fs-12); }
code { font-family: var(--font-mono); font-size: var(--fs-12); }
.status { font-weight: 600; }
.status-online, .status-local { color: var(--pass); }
.status-busy { color: var(--running); }
.status-offline, .status-unauthorized { color: var(--fail); }
.status-unknown, .status-disabled { color: var(--ink-faint); }
.error-text { color: var(--fail); margin-bottom: 12px; }
</style>
