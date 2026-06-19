import apiClient from './apiClient'

export interface ChecklistItem {
  id: string
  test_case_id: string
  position: number
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
  test_case?: { case_number: string; name: string; system_category: string | null }
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

export async function listChecklists(page = 1, pageSize = 20): Promise<ChecklistListResponse> {
  const res = await apiClient.get<ChecklistListResponse>('/checklists', {
    params: { page, page_size: pageSize },
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

export interface ChecklistCaseItem {
  item_id: string
  test_case_id: string
  position: number
  notes: string | null
  case_number: string | null
  name: string | null
}

export async function updateChecklist(id: string, name: string, created_by: string): Promise<Checklist> {
  const res = await apiClient.put<Checklist>(`/checklists/${id}`, { name, created_by })
  return res.data
}

export async function deleteChecklist(id: string): Promise<void> {
  await apiClient.delete(`/checklists/${id}`)
}

export async function getChecklistCases(checklistId: string): Promise<{ items: ChecklistCaseItem[]; total: number }> {
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
  payload: { notes?: string; position?: number },
): Promise<ChecklistCaseItem> {
  const res = await apiClient.patch(`/checklists/${checklistId}/cases/${caseId}`, payload)
  return res.data
}

export async function reorderChecklistCases(checklistId: string, caseIds: string[]): Promise<void> {
  await apiClient.put(`/checklists/${checklistId}/cases/reorder`, { case_ids: caseIds })
}
