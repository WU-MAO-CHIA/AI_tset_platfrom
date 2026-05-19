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
}

export interface ChecklistDetail extends Checklist {
  items: ChecklistItem[]
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
