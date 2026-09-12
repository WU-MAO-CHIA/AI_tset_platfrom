<template>
  <div class="page">
    <h1>建立測試案例</h1>

    <!-- Tab 導覽 -->
    <div class="tabs">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'basic' }"
        @click="activeTab = 'basic'"
      >
        基本資訊
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'steps' }"
        @click="activeTab = 'steps'"
      >
        測試步驟
      </button>
    </div>

    <!-- Tab 1：基本資訊 -->
    <div v-show="activeTab === 'basic'" class="tab-content">
      <TestCaseForm
        ref="formRef"
        :main-steps="mainSteps"
        :selected-model="selectedModel"
        @update:main-steps="mainSteps = $event"
        @rf-buffered="uploadedRfCode = $event"
        @saved="onSaved"
        @trial-run="onTrialRun"
      />
    </div>

    <!-- Tab 2：測試步驟（左：AI Chat，右：RF 預覽） -->
    <div v-show="activeTab === 'steps'" class="tab-content">
      <div class="split-layout">
        <section class="left-col">
          <AIChatPanel
            :selected-model="selectedModel"
            :rf-code-context="uploadedRfCode"
            @rf-updated="rfCode = $event"
          />
        </section>
        <section class="right-col">
          <RFCodePreview
            :main-steps="mainSteps"
            :selected-model="selectedModel"
            :rf-code-override="rfCode"
            :chat-mode="true"
          />
        </section>
      </div>
      <div class="tab2-save-bar">
        <span v-if="saveRfError" class="error">{{ saveRfError }}</span>
        <button class="btn-save-tab2" :disabled="savingRf" @click="saveFromTab2">
          {{ savingRf ? '儲存中...' : '儲存案例' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '../services/apiClient'
import { caseApi } from '../services/caseApi'
import TestCaseForm from '../components/TestCaseForm/index.vue'
import AIChatPanel from '../components/AIChatPanel/index.vue'
import RFCodePreview from '../components/RFCodePreview/index.vue'

const router = useRouter()
const activeTab = ref<'basic' | 'steps'>('basic')
const mainSteps = ref('')
// 模型集中於 /admin 管理：建立案例頁採用全域預設模型（FR-012 / FR-027），不提供選擇器
const selectedModel = ref('')
const rfCode = ref('')
const uploadedRfCode = ref<string | null>(null)
const savedCaseId = ref('')
const savingRf = ref(false)
const saveRfError = ref('')
const formRef = ref<InstanceType<typeof TestCaseForm> | null>(null)

onMounted(async () => {
  try {
    const { data } = await apiClient.get('/llm-models')
    selectedModel.value = data.default
  } catch {
    selectedModel.value = 'claude-sonnet-4-6'
  }
})

function saveFromTab2() {
  const submitBtn = formRef.value?.$el?.querySelector('button[type="submit"]') as HTMLButtonElement | null
  submitBtn?.click()
}

async function onSaved(id: string) {
  savedCaseId.value = id
  // 案例已建立：把 RF 程式碼持久化後再導頁，否則 AI 生成碼會被無聲丟棄。
  // 優先順序：Tab1 明確上傳的檔案 > Tab2 AI 生成的碼。
  const pendingUpload = formRef.value?.takePendingRfCode?.() ?? null
  const codeToSave = pendingUpload || rfCode.value || ''
  if (!codeToSave.trim()) {
    router.push(`/cases/${id}`)
    return
  }
  savingRf.value = true
  saveRfError.value = ''
  try {
    await caseApi.saveRobotScript(id, codeToSave)
    router.push(`/cases/${id}`)
  } catch (e: any) {
    // 留在原頁讓使用者重試（程式碼仍保留在畫面上，不會遺失）
    saveRfError.value = `RF 程式碼儲存失敗：${e?.message || '未知錯誤'}，請重試`
  } finally {
    savingRf.value = false
  }
}

function onTrialRun(executionId: string) {
  router.push(`/executions/${executionId}`)
}
</script>

<style scoped>
.page { padding: 24px; }
h1 { margin-bottom: 16px; font-size: 22px; }

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  border-bottom: 2px solid #e5e7eb;
}

.tab-btn {
  padding: 10px 20px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  color: #6b7280;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.15s;
}

.tab-btn.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
  font-weight: 600;
}

.tab-content { min-height: 400px; }

.split-layout {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 24px;
  align-items: start;
  height: calc(100vh - 200px);
}

.left-col, .right-col {
  display: flex;
  flex-direction: column;
  height: 100%;
}


@media (max-width: 767px) {
  .split-layout {
    grid-template-columns: 1fr;
    height: auto;
  }
}

.tab2-save-bar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  padding: 12px 0 0;
}

.tab2-save-bar .error { color: red; font-size: 13px; }

.btn-save-tab2 {
  padding: 8px 20px;
  background: #4f46e5;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
}

.btn-save-tab2:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
