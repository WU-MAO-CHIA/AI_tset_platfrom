import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { CaseResultItem } from '../services/executionApi'

type ExecutionStatus =
  | 'idle'
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'error'
  | 'interrupted'
  | 'cancelled'

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
  // 排隊中時前面還有幾筆（execution_queued 事件），未排隊時為 null
  const queueAhead = ref<number | null>(null)

  function startExecution(id: string) {
    executionId.value = id
    executionStatus.value = 'running'
    queueAhead.value = null
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
      // 串流開頭帶的是記錄當下狀態，排隊中的執行先顯示 pending
      executionStatus.value = event.status === 'pending' ? 'pending' : 'running'
    } else if (type === 'execution_queued') {
      executionStatus.value = 'pending'
      queueAhead.value = (event.ahead as number) ?? 0
    } else if (type === 'pabot_started') {
      executionStatus.value = 'running'
      queueAhead.value = null
    } else if (type === 'case_started') {
      executionStatus.value = 'running'
      queueAhead.value = null
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
      // 已中斷／已取消的舊執行重新連線時，SSE 也以 execution_completed 結束
      executionStatus.value =
        event.status === 'interrupted' || event.status === 'cancelled' ? event.status : 'completed'
      passedCases.value = (event.passed as number) || 0
      failedCases.value = (event.failed as number) || 0
      totalCases.value = (event.total as number) || totalCases.value
      completedCases.value = totalCases.value
      runningCases.value = []
    } else if (type === 'execution_interrupted') {
      executionStatus.value = 'interrupted'
      errorMessage.value = (event.message as string) || '執行因服務重啟而中斷'
      runningCases.value = []
    } else if (type === 'execution_cancelled') {
      executionStatus.value = 'cancelled'
      errorMessage.value = (event.message as string) || '已取消排隊'
      queueAhead.value = null
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
    queueAhead.value = null
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
    queueAhead,
    startExecution,
    handleSSEEvent,
    setCaseResults,
    reset,
  }
})
