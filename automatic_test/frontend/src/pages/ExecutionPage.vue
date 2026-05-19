<template>
  <div class="execution-page">
    <div v-if="!executionId" class="no-execution">
      <p>無執行中的任務</p>
      <button @click="$router.push('/checklists')">返回清單</button>
    </div>

    <template v-else>
      <div class="page-header">
        <h1>執行中</h1>
        <button class="btn-secondary" @click="$router.push('/checklists')">返回清單</button>
      </div>

      <ExecutionProgress
        :execution-id="executionId"
        @completed="handleCompleted"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useExecutionStore } from '../stores/executionStore'
import ExecutionProgress from '../components/ExecutionProgress/index.vue'

const route = useRoute()
const router = useRouter()
const store = useExecutionStore()

const executionId = computed(() => (route.query.execution_id as string) || null)

function handleCompleted() {
  if (executionId.value) {
    router.push(`/results/${executionId.value}`)
  }
}
</script>
