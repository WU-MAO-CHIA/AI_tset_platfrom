import apiClient from './apiClient'
import type { AxiosResponse } from 'axios'

export interface TestCaseSummary {
  id: string
  case_number: string
  name: string
  system_category: string | null
  tags: string[]
  version: number
  created_by: string
  updated_at: string | null
}

export interface TestCaseDetail extends TestCaseSummary {
  description: string | null
  precondition_steps: string | null
  main_steps: string
  modified_by: string | null
  created_at: string | null
}

export interface CreateCaseRequest {
  case_number: string
  name: string
  main_steps: string
  description?: string
  precondition_steps?: string
  system_category?: string
  tags?: string[]
  created_by: string
}

export interface UpdateCaseRequest {
  name?: string
  main_steps?: string
  description?: string
  precondition_steps?: string
  system_category?: string
  tags?: string[]
  created_by: string
}

export interface AttachmentRecord {
  id: string
  attachment_type: string
  filename: string | null
  url: string | null
  file_path: string | null
  file_size_bytes: number | null
  mime_type: string | null
}

export interface CaseListResponse {
  items: TestCaseSummary[]
  total: number
  page: number
  page_size: number
}

export interface AICompleteRequest {
  partial_steps: string
  llm_model?: string
  description?: string
}

export interface AICompleteResponse {
  completed_steps: string
  model_used: string
}

export interface PreviewRFRequest {
  main_steps: string
  llm_model?: string
}

export interface PreviewRFResponse {
  rf_code: string
}

export interface ChatResponse {
  assistant_message: string
  rf_code: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface ChatHistoryResponse {
  messages: ChatMessage[]
}

export const caseApi = {
  createCase(data: CreateCaseRequest) {
    return apiClient.post<{ id: string; case_number: string; version: number; created_at: string }>('/cases', data)
  },

  listCases(params?: { system_category?: string; keyword?: string; page?: number; page_size?: number; sort_by?: string; order?: string }) {
    return apiClient.get<CaseListResponse>('/cases', { params })
  },

  getCase(id: string) {
    return apiClient.get<TestCaseDetail>(`/cases/${id}`)
  },

  updateCase(id: string, data: UpdateCaseRequest) {
    return apiClient.put<TestCaseDetail>(`/cases/${id}`, data)
  },

  deleteCase(id: string, deletedBy: string) {
    return apiClient.delete(`/cases/${id}`, { data: { deleted_by: deletedBy } })
  },

  aiComplete(id: string, data: AICompleteRequest) {
    return apiClient.post<AICompleteResponse>(`/cases/${id}/ai-complete`, data)
  },

  aiCompletePreview(data: AICompleteRequest) {
    return apiClient.post<AICompleteResponse>('/cases/ai-complete', data)
  },

  previewRfCode(data: PreviewRFRequest) {
    return apiClient.post<PreviewRFResponse>('/cases/preview-rf', data)
  },

  uploadAttachment(id: string, file: File) {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post(`/cases/${id}/attachments`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  uploadAttachmentUrl(id: string, url: string) {
    return apiClient.post(`/cases/${id}/attachments`, null, { params: { url } })
  },

  listAttachments(id: string) {
    return apiClient.get<{ items: AttachmentRecord[] }>(`/cases/${id}/attachments`)
  },

  deleteAttachment(id: string, attachmentId: string) {
    return apiClient.delete(`/cases/${id}/attachments/${attachmentId}`)
  },

  trialRun(id: string) {
    return apiClient.post<{ execution_id: string; stream_url: string }>(`/cases/${id}/trial-run`)
  },

  getExecutionHistory(id: string, params?: { page?: number; page_size?: number }) {
    return apiClient.get(`/cases/${id}/execution-history`, { params })
  },

  importTestData(id: string, file: File) {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post(`/cases/${id}/import-test-data`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  confirmImportTestData(id: string, importToken: string) {
    return apiClient.post(`/cases/${id}/import-test-data/confirm`, { import_token: importToken })
  },

  chatWithAI(caseId: string, message: string, model: string) {
    return apiClient.post<ChatResponse>(`/cases/${caseId}/chat`, { message, llm_model: model })
  },

  getChatHistory(caseId: string) {
    return apiClient.get<ChatHistoryResponse>(`/cases/${caseId}/chat-history`)
  },

  saveRobotScript(caseId: string, rfCode: string) {
    return apiClient.put<{ case_number: string; file_path: string }>(`/cases/${caseId}/robot-script`, { rf_code: rfCode })
  },

  getRobotScript(caseId: string) {
    return apiClient.get<{ rf_code: string; case_number: string }>(`/cases/${caseId}/robot-script`)
  },

  listCategories() {
    return apiClient.get<{ items: string[] }>('/cases/categories')
  },
}
