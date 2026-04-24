<template>
  <default-layout>
    <div class="engine-page">
      <el-card class="status-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>环境状态</span>
            <el-tag :type="statusType">{{ engineStatus?.status || '未检测' }}</el-tag>
          </div>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Python 路径">{{ engineStatus?.python_path || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Python 版本"><el-tag size="small">{{ engineStatus?.python_version || '-' }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="虚拟环境">{{ engineStatus?.venv_path || '-' }}</el-descriptions-item>
          <el-descriptions-item label="pip 版本">{{ engineStatus?.pip_version || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card class="gpu-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>GPU 信息</span>
            <el-tag :type="gpuTypeTag">{{ gpuTypeLabel }}</el-tag>
          </div>
        </template>
        <div v-if="engineStatus?.gpu_type === 'none'" class="no-gpu">
          <el-empty description="未检测到 GPU" :image-size="80" />
        </div>
        <div v-else>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="GPU 类型">{{ engineStatus?.gpu_type === 'nvidia' ? 'NVIDIA CUDA' : 'AMD ROCm' }}</el-descriptions-item>
            <el-descriptions-item label="版本">{{ engineStatus?.gpu_type === 'nvidia' ? (engineStatus?.cuda_version || '-') : (engineStatus?.rocm_version || '-') }}</el-descriptions-item>
          </el-descriptions>
          <div v-if="engineStatus?.gpu_info?.length > 0" class="gpu-list">
            <h4>GPU 列表</h4>
            <el-table :data="engineStatus.gpu_info" stripe style="margin-top: 12px">
              <el-table-column prop="index" label="#" width="60" />
              <el-table-column prop="name" label="名称" />
              <el-table-column label="显存 (MB)">
                <template #default="{ row }">{{ row.memory_used_mb }} / {{ row.memory_total_mb }}</template>
              </el-table-column>
              <el-table-column prop="utilization_gpu" label="使用率">
                <template #default="{ row }"><el-progress :percentage="row.utilization_gpu" :stroke-width="8" /></template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </el-card>

      <el-card class="vllm-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>vLLM 引擎</span>
            <el-tag :type="vllmStatusTag">{{ vllmStatusLabel }}</el-tag>
          </div>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="vLLM 版本">{{ engineStatus?.vllm_version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Torch 版本">{{ engineStatus?.torch_version || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card class="action-card" shadow="hover">
        <template #header><div class="card-header"><span>操作</span></div></template>
        <el-space wrap>
          <el-button type="primary" :icon="Refresh" :loading="checking" @click="handleCheckEngine">重新检测环境</el-button>
        </el-space>
      </el-card>
    </div>
  </default-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { useEngineStore } from '@/stores/engine'

const engineStore = useEngineStore()
const engineStatus = ref<any>(null)
const checking = ref(false)

const statusType = computed(() => {
  const map: Record<string, any> = { ready: 'success', partial: 'warning', not_installed: 'info', error: 'danger' }
  return map[engineStatus.value?.status] || 'info'
})
const gpuTypeLabel = computed(() => {
  const map: Record<string, string> = { nvidia: 'NVIDIA', amd: 'AMD', none: '无 GPU', unknown: '未知' }
  return map[engineStatus.value?.gpu_type] || '未知'
})
const gpuTypeTag = computed(() => {
  const map: Record<string, any> = { nvidia: 'success', amd: 'danger', none: 'info', unknown: 'info' }
  return map[engineStatus.value?.gpu_type] || 'info'
})
const vllmStatusLabel = computed(() => engineStatus.value?.vllm_version ? `已安装 (${engineStatus.value.vllm_version})` : '未安装')
const vllmStatusTag = computed(() => engineStatus.value?.vllm_version ? 'success' : 'danger')

async function fetchStatus() {
  try { engineStatus.value = await engineStore.fetchEngineStatus() } catch { ElMessage.error('获取状态失败') }
}

async function handleCheckEngine() {
  checking.value = true
  try {
    const result = await engineStore.triggerCheck()
    ElMessage.success(`检测任务已创建 (ID: ${result.task_id})`)
    setTimeout(fetchStatus, 2000)
  } catch { ElMessage.error('检测失败') } finally { checking.value = false }
}

onMounted(() => { fetchStatus() })
</script>

<style scoped>
.engine-page { max-width: 1200px; margin: 0 auto; }
.status-card, .gpu-card, .vllm-card, .action-card { margin-bottom: 20px; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.no-gpu { padding: 20px; }
.gpu-list { margin-top: 16px; }
.gpu-list h4 { margin-bottom: 12px; color: #303133; font-size: 14px; }
</style>
