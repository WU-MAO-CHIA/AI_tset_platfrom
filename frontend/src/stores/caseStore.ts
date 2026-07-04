import { defineStore } from 'pinia'
import { ref } from 'vue'
import { caseApi, type TestCaseDetail, type CreateCaseRequest, type UpdateCaseRequest } from '../services/caseApi'

export const useCaseStore = defineStore('case', () => {
  const currentCase = ref<TestCaseDetail | null>(null)
  const savingState = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const aiCompletionState = ref<'idle' | 'loading' | 'done' | 'error'>('idle')
  const errorMessage = ref<string | null>(null)

  async function loadCase(id: string) {
    const response = await caseApi.getCase(id)
    currentCase.value = response.data
  }

  async function createCase(data: CreateCaseRequest) {
    savingState.value = 'saving'
    errorMessage.value = null
    try {
      const response = await caseApi.createCase(data)
      savingState.value = 'saved'
      return response.data
    } catch (err: any) {
      savingState.value = 'error'
      errorMessage.value = err.message
      throw err
    }
  }

  async function updateCase(id: string, data: UpdateCaseRequest) {
    savingState.value = 'saving'
    errorMessage.value = null
    try {
      const response = await caseApi.updateCase(id, data)
      currentCase.value = response.data
      savingState.value = 'saved'
      return response.data
    } catch (err: any) {
      savingState.value = 'error'
      errorMessage.value = err.message
      throw err
    }
  }

  async function aiComplete(id: string, partialSteps: string, llmModel?: string, description?: string) {
    aiCompletionState.value = 'loading'
    errorMessage.value = null
    try {
      const response = await caseApi.aiComplete(id, { partial_steps: partialSteps, llm_model: llmModel, description })
      aiCompletionState.value = 'done'
      return response.data.completed_steps
    } catch (err: any) {
      aiCompletionState.value = 'error'
      errorMessage.value = err.message
      throw err
    }
  }

  function reset() {
    currentCase.value = null
    savingState.value = 'idle'
    aiCompletionState.value = 'idle'
    errorMessage.value = null
  }

  return {
    currentCase,
    savingState,
    aiCompletionState,
    errorMessage,
    loadCase,
    createCase,
    updateCase,
    aiComplete,
    reset,
  }
})
