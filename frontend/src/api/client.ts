import type { FileUploadResponse, TaskResponse, ToolType } from '../types'

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

export async function listTasks(limit = 50, offset = 0): Promise<TaskResponse[]> {
  const res = await fetch(`${BASE}/tasks?limit=${limit}&offset=${offset}`)
  return handleResponse<TaskResponse[]>(res)
}

export function getDownloadUrl(fileId: number): string {
  return `${BASE}/files/${fileId}/download`
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
