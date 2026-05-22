<template>
  <div class="page">
    <h1>建立測試案例</h1>
    <div class="split-layout">
      <!-- 左欄：基本欄位（編號、名稱、描述、前置步驟、系統別、附件等） -->
      <section class="left-col">
        <TestCaseForm
          :main-steps="mainSteps"
          @saved="onSaved"
          @trial-run="onTrialRun"
        />
      </section>
      <!-- 右欄：主要步驟撰寫 + AI 補齊 + RF 程式碼預覽 -->
      <section class="right-col">
        <StepsEditor
          v-model:main-steps="mainSteps"
          v-model:selected-model="selectedModel"
        />
        <div class="rf-divider" />
        <RFCodePreview
          :main-steps="mainSteps"
          :selected-model="selectedModel"
        />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import TestCaseForm from '../components/TestCaseForm/index.vue'
import StepsEditor from '../components/StepsEditor/index.vue'
import RFCodePreview from '../components/RFCodePreview/index.vue'

const router = useRouter()
const mainSteps = ref('')
const selectedModel = ref('claude-3-5-sonnet-20241022')

function onSaved(id: string) {
  router.push(`/cases/${id}`)
}

function onTrialRun(executionId: string) {
  router.push(`/executions/${executionId}`)
}
</script>

<style scoped>
.page { padding: 24px; }
h1 { margin-bottom: 20px; font-size: 22px; }

.split-layout {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 28px;
  align-items: start;
}

.left-col, .right-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rf-divider {
  border-top: 1px solid #e5e7eb;
  margin: 4px 0;
}

/* 行動裝置：單欄 */
@media (max-width: 767px) {
  .split-layout {
    grid-template-columns: 1fr;
  }
}
</style>
