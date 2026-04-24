import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

// 创建 axios 实例
const service = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// 请求拦截器
service.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
)

// 响应拦截器
service.interceptors.response.use(
  (response) => {
    const apiData: ApiResponse = response.data
    if (apiData.code !== 0) {
      ElMessage.error(apiData.message || '请求失败')
      if (apiData.code === 401) {
        router.push('/login')
      }
    }
    return response
  },
  (error) => {
    const message = error.response?.data?.message || error.message || '网络异常'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// 便捷方法 — 返回 ApiResponse<T>，与 axios response.data 兼容
export const get = <T = any>(url: string, params?: any): Promise<ApiResponse<T>> => 
  service.get<ApiResponse<T>>(url, { params }).then(r => r.data)
export const post = <T = any>(url: string, data?: any): Promise<ApiResponse<T>> => 
  service.post<ApiResponse<T>>(url, data).then(r => r.data)
export const put = <T = any>(url: string, data?: any): Promise<ApiResponse<T>> => 
  service.put<ApiResponse<T>>(url, data).then(r => r.data)
export const del = <T = any>(url: string, params?: any): Promise<ApiResponse<T>> => 
  service.delete<ApiResponse<T>>(url, { params }).then(r => r.data)

export default service
