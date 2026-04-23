<template>
  <default-layout>
    <div class="engine-page">
      <!-- 环境状态卡片 -->
      <el-card class="status-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>环境状态</span>
            <el-tag :type="statusType">{{ engineStatus?.status || '未检测' }}</el-tag>
          </div>
        </template>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Python 路径">
            {{ engineStatus?.python_path || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="Python 版本">
            <el-tag size="small">{{ engineStatus?.python_version || '-' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="虚拟环境">
            {{ engineStatus?.venv_path || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="pip 版本">
            {{ engineStatus?.pip_version || '-' }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
      
      <!-- GPU 信息卡片 -->
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
            <el-descriptions-item label="GPU 类型">
              {{ engineStatus?.gpu_type === 'nvidia' ? 'NVIDIA CUDA' : 'AMD ROCm' }}
            </el-descriptions-item>
            <el-descriptions-item label="版本">
              {{ engineStatus?.gpu_type === 'nvidia' 
                ? (engineStatus?.cuda_version || '-') 
                : (engineStatus?.rocm_version || '-') }}
            </el-descriptions-item>
            <el-descriptions-item label="检测工具">
              {{ engineStatus?.gpu_type === 'nvidia' 
                ? (engineStatus?.nvidia_smi_available ? 'nvidia-smi 可用' : 'nvidia-smi 不可用')
                : (engineStatus?.rocm_smi_available ? 'rocm-smi 可用' : 'rocm-smi 不可用') }}
            </el-descriptions-item>
          </el-descriptions>
          
          <!-- GPU 列表 -->
          <div v-if="engineStatus?.gpu_info?.length > 0" class="gpu-list">
            <h4>GPU 列表</h4>
            <el-table :data="engineStatus.gpu_info" stripe style="margin-top: 12px">
              <el-table-column prop="index" label="#" width="60" />
              <el-table-column prop="name" label="名称" />
              <el-table-column label="显存 (MB)">
                <template #default="{ row }">
                  {{ row.memory_used_mb }} / {{ row.memory_total_mb }}
                </template>
              </el-table-column>
              <el-table-column prop="utilization_gpu" label="使用率">
                <template #default="{ row }">
                  <el-progress :percentage="row.utilization_gpu" :stroke-width="8" />
                </template>
              </el-table-column>
              <el-table-column prop="temperature" label="温度">
                <template #default="{ row }">
                  {{ row.temperature }}°C
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </el-card>
      
      <!-- vLLM 信息卡片 -->
      <el-card class="vllm-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>vLLM 引擎</span>
            <el-tag :type="vllmStatusTag">{{ vllmStatusLabel }}</el-tag>
          </div>
        </template>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="vLLM 版本">
            {{ engineStatus?.vllm_version || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="Torch 版本">
            {{ engineStatus?.torch_version || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="Transformers 版本">
            {{ engineStatus?.transformers_version || '-' }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
      
      <!-- 操作区 -->
      <el-card class="action-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>操作</span>
          </div>
        </template>
        
        <el-space wrap>
          <el-button 
            type="primary" 
            :icon="Refresh" 
            :loading="checking"
            @click="handleCheckEngine"
          >
            重新检测环境
          </el-button>
          
          <el-button 
            :disabled="!canInstall"
            :loading="installing"
            @click="showInstallDialog = true"
          >
            安装 vLLM
          </el-button>
          
          <el-button 
            :disabled="!engineStatus?.vllm_version"
            :loading="upgrading"
            @click="handleUpgrade"
          >
            升级 vLLM
          </el-button>
          
          <el-button @click="viewLogs">查看日志</el-button>
        </el-space>
      </el-card>
      
      <!-- 安装对话框 -->
      <el-dialog
        v-model="showInstallDialog"
        title="安装 vLLM"
        width="500px"
      >
        <el-form :model="installForm" label-width="120px">
          <el-form-item label="Python 路径">
            <el-input 
              v-model="installForm.python_path" 
              placeholder="/usr/bin/python3"
            />
          </el-form-item>
          <el-form-item label="虚拟环境路径">
            <el-input 
              v-model="installForm.venv_path" 
              placeholder="/home/user/.venv"
            />
          </el-form-item>
          <el-form-item label="安装参数">
            <el-input 
              v-model="installForm.install_args" 
              placeholder="--extra-index-url ..."
            />
          </el-form-item>
        </el-form>
        
        <template #footer>
          <el-button @click="showInstallDialog = false">取消</el-button>
          <el-button type="primary" :loading="installing" @click="handleInstall">
            开始安装
          </el-button>
        </template>
      </el-dialog>
    </div>
  </default-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { useEngineStore } from '@/stores/engine'
import { installEngine, upgradeEngine } from '@/api/engine'

const engineStore = useEngineStore()

const engineStatus = ref<any>(null)
const checking = ref(false)
const installing = ref(false)
const upgrading = ref(false)
const showInstallDialog = ref(false)

const installForm = ref({
  python_path: '',
  venv_path: '',
  install_args: '',
})

// 状态标签类型
const statusType = computed(() => {
  const map: Record<string, any> = {
    ready: 'success',
    partial: 'warning',
    not_installed: 'info',
    error: 'danger',
  }
  return map[engineStatus.value?.status] || 'info'
})

// GPU 类型标签
const gpuTypeLabel = computed(() => {
  const map: Record<string, string> = {
    nvidia: 'NVIDIA',
    amd: 'AMD',
    none: '无 GPU',
    unknown: '未知',
  }
  return map[engineStatus.value?.gpu_type] || '未知'
})

const gpuTypeTag = computed(() => {
  const map: Record<string, any> = {
    nvidia: 'success',
    amd: 'danger',
    none: 'info',
    unknown: 'info',
  }
  return map[engineStatus.value?.gpu_type] || 'info'
})

// vLLM 状态
const vllmStatusLabel = computed(() => {
  if (engineStatus.value?.vllm_version) {
    return `已安装 (${engineStatus.value.vllm_version})`
  }
  return '未安装'
})

const vllmStatusTag = computed(() => {
  return engineStatus.value?.vllm_version ? 'success' : 'info'
})

// 是否可以安装
const canInstall = computed(() => {
  return !engineStatus.value?.vllm_version
})

// 获取状态
async function fetchStatus() {
  try {
    engineStatus.value = await engineStore.fetchEngineStatus()
  } catch (error) {
    ElMessage.error('获取状态失败')
  }
}

// 重新检测
async function handleCheckEngine() {
  checking.value = true
  try {
    const result = await engineStore.triggerCheck()
    ElMessage.success(`检测任务已创建 (ID: ${result.task_id})`)
    setTimeout(fetchStatus, 2000)
  } catch (error) {
    ElMessage.error('检测失败')
  } finally {
    checking.value = false
  }
}

// 安装 vLLM
async function handleInstall() {
  installing.value = true
  try {
    const result = await installEngine(installForm.value)
    ElMessage.success(`安装任务已创建 (ID: ${result.data.task_id})`)
    showInstallDialog.value = false
    setTimeout(fetchStatus, 3000)
  } catch (error) {
    ElMessage.error('安装失败')
  } finally {
    installing.value = false
  }
}

// 升级 vLLM
async function handleUpgrade() {
  try {
    await ElMessageBox.confirm('确定要升级 vLLM 吗？', '提示', {
      type: 'warning',
    })
    
    upgrading.value = true
    const result = await upgradeEngine()
    ElMessage.success(`升级任务已创建 (ID: ${result.data.task_id})`)
    setTimeout(fetchStatus, 3000)
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('升级失败')
    }
  } finally {
    upgrading.value = false
  }
}

// 查看日志
function viewLogs() {
  // TODO: 跳转到日志页面
  ElMessage.info('日志功能开发中')
}

onMounted(() => {
  fetchStatus()
})
</script>

<style scoped>
.engine-page {
  max-width: 1200px;
  margin: 0 auto;
}

.status-card,
.gpu-card,
.vllm-card,
.action-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.no-gpu {
  padding: 20px;
}

.gpu-list {
  margin-top: 16px;
}

.gpu-list h4 {
  margin-bottom: 12px;
  color: #303133;
  font-size: 14px;
}
</style>
