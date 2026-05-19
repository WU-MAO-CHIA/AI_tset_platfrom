<template>
  <div class="page">
    <h1>建立測試案例</h1>
    <TestCaseForm @saved="onSaved" @trial-run="onTrialRun" />
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import TestCaseForm from '../components/TestCaseForm/index.vue'
import { useCaseStore } from '../stores/caseStore'

const router = useRouter()
const store = useCaseStore()

function onSaved(id: string) {
  router.push(`/cases/${id}`)
}

function onTrialRun(executionId: string) {
  router.push(`/executions/${executionId}`)
}
</script>

<style scoped>
.page { max-width: 800px; margin: 0 auto; padding: 24px; }
h1 { margin-bottom: 24px; font-size: 22px; }
</style>
