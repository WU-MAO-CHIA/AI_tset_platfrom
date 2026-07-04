import apiClient from './apiClient'

export interface ChecklistItem {
  id: string
  test_case_id: string
  position: number
  test_case?: { case_number: string | null; name: string | null; system_category: string | null } | null
}

export interface ChecklistExecutionRecord {
  id: string
  status: string
  passed_count: number
  failed_count: number
  total_count: number
  started_at: string | null
  finished_at: string | null
}

export interface Checklist {
  id: string
  name: string
  created_by: string
  description?: string
  case_count?: number
  last_run_at?: string | null
  status?: string | null
  created_at?: string
}

export interface ChecklistDetail extends Checklist {
  items: ChecklistItem[]
  order?: number
}

export interface ChecklistListResponse {
  items: Checklist[]
  total: number
  page: number
  page_size: number
}

export async function createChecklist(payload: {
  name: string
  created_by: string
  case_ids: string[]
  description?: string
}): Promise<Checklist> {
  const res = await apiClient.post<Checklist>('/checklists', payload)
  return res.data
}

export async function listChecklists(page = 1, pageSize = 20, keyword?: string, sort_by?: string, order?: string): Promise<ChecklistListResponse> {
  const res = await apiClient.get<ChecklistListResponse>('/checklists', {
    params: { page, page_size: pageSize, ...(keyword ? { keyword } : {}), ...(sort_by ? { sort_by } : {}), ...(order ? { order } : {}) },
  })
  return res.data
}

export async function getChecklist(id: string): Promise<ChecklistDetail> {
  const res = await apiClient.get<ChecklistDetail>(`/checklists/${id}`)
  return res.data
}

export async function updateChecklistItems(id: string, caseIds: string[]): Promise<ChecklistDetail> {
  const res = await apiClient.put<ChecklistDetail>(`/checklists/${id}/items`, { case_ids: caseIds })
  return res.data
}

export interface TestDataItem {
  id: string
  field_name: string
  rf_variable: string | null
  field_value: string | null
  description: string | null
  row_index: number | null
}

export interface ChecklistCaseItem {
  item_id: string
  test_case_id: string
  position: number
  notes: string | null
  case_number: string | null
  name: string | null
}

export interface ChecklistItemDetail extends ChecklistCaseItem {
  test_data: TestDataItem[]
  actual_values: Record<string, string>
}

export async function updateChecklist(id: string, name: string, created_by: string): Promise<Checklist> {
  const res = await apiClient.put<Checklist>(`/checklists/${id}`, { name, created_by })
  return res.data
}

export async function deleteChecklist(id: string): Promise<void> {
  await apiClient.delete(`/checklists/${id}`)
}

export async function getChecklistCases(checklistId: string): Promise<{ items: ChecklistItemDetail[]; total: number }> {
  const res = await apiClient.get(`/checklists/${checklistId}/cases`)
  return res.data
}

export async function addCaseToChecklist(
  checklistId: string,
  caseId: string,
  position?: number,
): Promise<{ item_id: string; position: number }> {
  const res = await apiClient.post(`/checklists/${checklistId}/cases`, { case_id: caseId, position: position ?? null })
  return res.data
}

export async function removeCaseFromChecklist(checklistId: string, caseId: string): Promise<void> {
  await apiClient.delete(`/checklists/${checklistId}/cases/${caseId}`)
}

export async function patchChecklistCaseItem(
  checklistId: string,
  caseId: string,
  payload: { notes?: string; position?: number; actual_values?: Record<string, string> },
): Promise<ChecklistItemDetail> {
  const res = await apiClient.patch(`/checklists/${checklistId}/cases/${caseId}`, payload)
  return res.data
}

export async function reorderChecklistCases(checklistId: string, caseIds: string[]): Promise<void> {
  await apiClient.put(`/checklists/${checklistId}/cases/reorder`, { case_ids: caseIds })
}

export async function getChecklistExecutions(checklistId: string): Promise<{ items: ChecklistExecutionRecord[]; total: number }> {
  const res = await apiClient.get(`/checklists/${checklistId}/executions`)
  return res.data
}
