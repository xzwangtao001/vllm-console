import { get, post } from './request'

export interface EngineStatus {
  python_path: string | null
  python_version: string | null
  pip_version: string | null
  venv_path: string | null
  gpu_type: 'nvidia' | 'amd' | 'none' | 'unknown'
  cuda_version: string | null
  rocm_version: string | null
  gpu_info: Array<{
    index: number
    name: string
    memory_total_mb: number
    memory_used_mb: number
    utilization_gpu: number
    temperature: number
  }>
  nvidia_smi_available: boolean
  rocm_smi_available: boolean
  torch_version: string | null
  transformers_version: string | null
  vllm_version: string | null
  status: 'ready' | 'partial' | 'not_installed' | 'error'
  message: string | null
  last_checked_at: string | null
}

export interface TaskInfo {
  id: number
  task_type: string
  status: string
  progress: number
  message: string | null
  log_path: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export function getEngineStatus() {
  return get<EngineStatus>('/engine/status')
}

export function checkEngine() {
  return post<{ task_id: number; task_type: string; status: string }>('/engine/check')
}

export function installEngine(data: { python_path?: string; venv_path?: string; install_args?: string }) {
  return post('/engine/install', data)
}

export function upgradeEngine() {
  return post('/engine/upgrade')
}

export function getEngineLogs(page = 1, page_size = 20) {
  return get('/engine/logs', { page, page_size })
}

export function getTask(taskId: number) {
  return get<TaskInfo>(`/tasks/${taskId}`)
}

export function getTasks(params?: { page?: number; page_size?: number; status?: string; task_type?: string }) {
  return get('/tasks', params)
}

export function cancelTask(taskId: number) {
  return post(`/tasks/${taskId}/cancel`)
}
