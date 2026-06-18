export interface ImageItem {
  id: string
  file: File
  previewUrl: string
}

export interface FileUploadResponse {
  file_id: number
  original_name: string
  size_bytes: number
  mime_type: string
}

export interface TaskOutputFile {
  file_id: number
  download_url: string
  filename: string
}

export interface TaskInputFile {
  file_id: number
  original_name: string
}

export interface TaskResponse {
  task_id: number
  task_name: string
  status: 'pending' | 'running' | 'succeeded' | 'failed' | 'expired'
  tool_type: string
  progress: number
  error_code: string | null
  error_message: string | null
  warnings: string[]
  result_info: Record<string, unknown>
  output_files: TaskOutputFile[]
  input_files: TaskInputFile[]
  created_at: string | null
  started_at: string | null
  finished_at: string | null
}

export interface TaskListResponse {
  items: TaskResponse[]
  total: number
}

export type ToolType =
  | 'pdf_to_png'
  | 'images_to_pdf'
  | 'split_pdf'
  | 'remove_pdf_pages'
  | 'watermark_pdf'
  | 'pdf_to_word'
  | 'protect_pdf'
