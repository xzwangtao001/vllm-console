import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getEngineStatus, checkEngine } from '@/api/engine'

export const useEngineStore = defineStore('engine', () => {
  // 状态
  const engineStatus = ref<any>(null)
  const loading = ref(false)
  const lastCheckedAt = ref<string | null>(null)

  // 获取引擎状态
  async function fetchEngineStatus() {
    loading.value = true
    try {
      const res = await getEngineStatus()
      engineStatus.value = res.data
      lastCheckedAt.value = res.data.last_checked_at
      return res.data
    } catch (error) {
      console.error('Failed to fetch engine status:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 触发环境检测
  async function triggerCheck() {
    try {
      const res = await checkEngine()
      return res.data
    } catch (error) {
      console.error('Failed to trigger engine check:', error)
      throw error
    }
  }

  return {
    engineStatus,
    loading,
    lastCheckedAt,
    fetchEngineStatus,
    triggerCheck,
  }
})
