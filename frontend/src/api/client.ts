import type { FileUploadResponse, TaskListResponse, TaskResponse, ToolType } from '../types'

const BASE = '/api'

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = body?.detail ?? `HTTP ${res.status}`
    const message = typeof detail === 'string' ? detail : detail?.error_message ?? detail
    throw new Error(message)
  }
  return res.json()
}

export async function uploadFile(file: File): Promise<FileUploadResponse> {
  const form = new FormData()
  form.set('file', file)
  const res = await fetch(`${BASE}/files`, { method: 'POST', body: form })
  return handleResponse<FileUploadResponse>(res)
}

export async function createTask(
  toolType: ToolType,
  inputFileIds: number[],
  params: Record<string, unknown> = {},
): Promise<TaskResponse> {
  const res = await fetch(`${BASE}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tool_type: toolType, input_file_ids: inputFileIds, params }),
  })
  return handleResponse<TaskResponse>(res)
}

export async function getTask(taskId: number): Promise<TaskResponse> {
  const res = await fetch(`${BASE}/tasks/${taskId}`)
  return handleResponse<TaskResponse>(res)
}

export interface ListTasksParams {
  limit?: number
  offset?: number
  task_name?: string
  file_name?: string
  status?: string
  date_from?: string
  date_to?: string
}

export async function listTasks(params: ListTasksParams = {}): Promise<TaskListResponse> {
  const query = new URLSearchParams()
  if (params.limit != null) query.set('limit', String(params.limit))
  if (params.offset != null) query.set('offset', String(params.offset))
  if (params.task_name) query.set('task_name', params.task_name)
  if (params.file_name) query.set('file_name', params.file_name)
  if (params.status) query.set('status', params.status)
  if (params.date_from) query.set('date_from', params.date_from)
  if (params.date_to) query.set('date_to', params.date_to)
  const res = await fetch(`${BASE}/tasks?${query}`)
  return handleResponse<TaskListResponse>(res)
}

export function getDownloadUrl(fileId: number): string {
  return `${BASE}/files/${fileId}/download`
}

export async function clearTasks(): Promise<void> {
  const res = await fetch(`${BASE}/tasks`, { method: 'DELETE' })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `HTTP ${res.status}`)
  }
}

export async function getSettings(): Promise<{ domain_url: string; password_length: number; qr_code_visible: boolean }> {
  const res = await fetch(`${BASE}/settings`)
  return handleResponse<{ domain_url: string; password_length: number; qr_code_visible: boolean }>(res)
}

export async function updateSettings(data: { domain_url: string; password_length: number; qr_code_visible: boolean }): Promise<{ domain_url: string; password_length: number; qr_code_visible: boolean }> {
  const res = await fetch(`${BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return handleResponse<{ domain_url: string; password_length: number; qr_code_visible: boolean }>(res)
}
