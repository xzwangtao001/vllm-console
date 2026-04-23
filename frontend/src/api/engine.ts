import { get, post } from './request'

// 引擎状态响应类型
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

// 获取引擎状态
export function getEngineStatus() {
  return get<EngineStatus>('/engine/status')
}

// 触发环境检测
export function checkEngine() {
  return post<{ task_id: number; task_type: string; status: string }>('/engine/check')
}

// 安装 vLLM
export function installEngine(data: { python_path?: string; venv_path?: string; install_args?: string }) {
  return post('/engine/install', data)
}

// 升级 vLLM
export function upgradeEngine() {
  return post('/engine/upgrade')
}

// 获取引擎日志列表
export function getEngineLogs(page = 1, page_size = 20) {
  return get('/engine/logs', { page, page_size })
}
