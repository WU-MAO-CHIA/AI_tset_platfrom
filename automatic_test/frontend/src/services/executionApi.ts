import apiClient from './apiClient'

export interface ExecutionRecord {
  id: string
  status: string
  checklist_id: string | null
  source_case_id: string | null
  parallel_mode: boolean
  max_workers: number
  passed_count: number
  failed_count: number
  total_count: number
}

export interface CaseResultItem {
  id: string
  test_case_id: string
  case_number: string
  case_name: string
  status: string
  elapsed_ms: number | null
  failure_message: string | null
  media: Array<{ media_type: string; file_path: string | null; step_index: number | null }>
}

export async function executeChecklist(
  checklistId: string,
  options: { parallel_mode: boolean; max_workers: number }
): Promise<{ execution_id: string; stream_url: string }> {
  const res = await apiClient.post(`/checklists/${checklistId}/execute`, options)
  return res.data
}

export async function getExecution(executionId: string): Promise<ExecutionRecord> {
  const res = await apiClient.get<ExecutionRecord>(`/executions/${executionId}`)
  return res.data
}

export async function getExecutionResults(
  executionId: string
): Promise<{ items: CaseResultItem[]; total: number }> {
  const res = await apiClient.get(`/executions/${executionId}/results`)
  return res.data
}

export function streamExecution(executionId: string, onEvent: (data: unknown) => void): EventSource {
  const evtSource = new EventSource(`/api/v1/executions/${executionId}/stream`)
  evtSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      onEvent(data)
      if (data.event === 'execution_completed' || data.event === 'execution_error') {
        evtSource.close()
      }
    } catch {
      // ignore parse errors
    }
  }
  return evtSource
}

export async function exportReport(executionId: string): Promise<void> {
  const res = await apiClient.get(`/executions/${executionId}/export`, {
    responseType: 'blob',
  })
  const url = URL.createObjectURL(new Blob([res.data], { type: 'text/html' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `report-${executionId}.html`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
