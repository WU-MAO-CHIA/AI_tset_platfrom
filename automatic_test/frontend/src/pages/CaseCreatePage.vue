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
        :main-steps="mainSteps"
        :selected-model="selectedModel"
        @update:main-steps="mainSteps = $event"
        @saved="onSaved"
        @trial-run="onTrialRun"
      />
    </div>

    <!-- Tab 2：測試步驟（左：AI Chat，右：RF 預覽） -->
    <div v-show="activeTab === 'steps'" class="tab-content split-layout">
      <section class="left-col">
        <AIChatPanel
          :selected-model="selectedModel"
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
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import TestCaseForm from '../components/TestCaseForm/index.vue'
import AIChatPanel from '../components/AIChatPanel/index.vue'
import RFCodePreview from '../components/RFCodePreview/index.vue'

const router = useRouter()
const activeTab = ref<'basic' | 'steps'>('basic')
const mainSteps = ref('')
const selectedModel = ref('claude-sonnet-4-6')
const rfCode = ref('')

function onSaved(id: string) {
  router.push(`/cases/${id}`)
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
</style>
