import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { CaseResultItem, ExecutionRecord } from '../services/executionApi'

type ExecutionStatus = 'idle' | 'running' | 'completed' | 'failed' | 'error'

interface SSECaseProgress {
  case_result_id: string
  case_number: string
  case_name: string
  status?: string
  elapsed_ms?: number
  failure_message?: string | null
  position?: number
}

export const useExecutionStore = defineStore('execution', () => {
  const executionId = ref<string | null>(null)
  const executionStatus = ref<ExecutionStatus>('idle')
  const totalCases = ref(0)
  const completedCases = ref(0)
  const passedCases = ref(0)
  const failedCases = ref(0)
  const runningCases = ref<string[]>([])
  const caseResults = ref<CaseResultItem[]>([])
  const errorMessage = ref<string | null>(null)

  function startExecution(id: string) {
    executionId.value = id
    executionStatus.value = 'running'
    totalCases.value = 0
    completedCases.value = 0
    passedCases.value = 0
    failedCases.value = 0
    runningCases.value = []
    caseResults.value = []
    errorMessage.value = null
  }

  function handleSSEEvent(event: Record<string, unknown>) {
    const type = event.event as string

    if (type === 'execution_started') {
      totalCases.value = (event.total_cases as number) || 0
      executionStatus.value = 'running'
    } else if (type === 'case_started') {
      const caseNumber = event.case_number as string
      if (!runningCases.value.includes(caseNumber)) {
        runningCases.value.push(caseNumber)
      }
    } else if (type === 'case_completed') {
      const caseNumber = event.case_number as string
      runningCases.value = runningCases.value.filter((c) => c !== caseNumber)
      completedCases.value++
      if ((event.status as string) === 'passed') passedCases.value++
      else failedCases.value++
    } else if (type === 'progress_update') {
      completedCases.value = (event.completed as number) || 0
      passedCases.value = (event.passed as number) || 0
      failedCases.value = (event.failed as number) || 0
      runningCases.value = (event.running_cases as string[]) || []
    } else if (type === 'execution_completed') {
      executionStatus.value = 'completed'
      passedCases.value = (event.passed as number) || 0
      failedCases.value = (event.failed as number) || 0
      runningCases.value = []
    } else if (type === 'execution_error') {
      executionStatus.value = 'error'
      errorMessage.value = (event.message as string) || 'Execution failed'
    }
  }

  function setCaseResults(results: CaseResultItem[]) {
    caseResults.value = results
  }

  function reset() {
    executionId.value = null
    executionStatus.value = 'idle'
    totalCases.value = 0
    completedCases.value = 0
    passedCases.value = 0
    failedCases.value = 0
    runningCases.value = []
    caseResults.value = []
    errorMessage.value = null
  }

  return {
    executionId,
    executionStatus,
    totalCases,
    completedCases,
    passedCases,
    failedCases,
    runningCases,
    caseResults,
    errorMessage,
    startExecution,
    handleSSEEvent,
    setCaseResults,
    reset,
  }
})
