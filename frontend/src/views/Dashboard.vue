<template>
  <default-layout>
    <div class="dashboard">
      <!-- 状态卡片区 -->
      <el-row :gutter="20" class="status-cards">
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="card-content">
              <div class="card-icon" :class="engineStatus?.status">
                <el-icon :size="32"><Cpu /></el-icon>
              </div>
              <div class="card-info">
                <div class="card-label">环境状态</div>
                <div class="card-value">{{ engineStatus?.status || '未知' }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="card-content">
              <div class="card-icon gpu">
                <el-icon :size="32"><Monitor /></el-icon>
              </div>
              <div class="card-info">
                <div class="card-label">GPU 类型</div>
                <div class="card-value">{{ engineStatus?.gpu_type || '未知' }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="card-content">
              <div class="card-icon model">
                <el-icon :size="32"><Folder /></el-icon>
              </div>
              <div class="card-info">
                <div class="card-label">模型总数</div>
                <div class="card-value">{{ stats.modelCount || 0 }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card shadow="hover">
            <div class="card-content">
              <div class="card-icon instance">
                <el-icon :size="32"><Monitor /></el-icon>
              </div>
              <div class="card-info">
                <div class="card-label">运行中实例</div>
                <div class="card-value">{{ stats.runningInstances || 0 }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <!-- 操作区 -->
      <el-card class="action-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>快速操作</span>
          </div>
        </template>
        
        <el-button type="primary" :loading="checking" @click="handleCheckEngine">
          重新检测环境
        </el-button>
        
        <el-button @click="goToEngine">前往引擎管理</el-button>
        <el-button @click="goToModels">前往模型管理</el-button>
        <el-button @click="goToInstances">前往实例管理</el-button>
      </el-card>
      
      <!-- 详细信息 -->
      <el-card class="detail-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>环境详情</span>
          </div>
        </template>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Python 路径">{{ engineStatus?.python_path || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Python 版本">{{ engineStatus?.python_version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="vLLM 版本">{{ engineStatus?.vllm_version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Torch 版本">{{ engineStatus?.torch_version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="CUDA 版本">{{ engineStatus?.cuda_version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="ROCm 版本">{{ engineStatus?.rocm_version || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>
  </default-layout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Cpu, Monitor, Folder } from '@element-plus/icons-vue'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { useEngineStore } from '@/stores/engine'

const router = useRouter()
const engineStore = useEngineStore()

const engineStatus = ref<any>(null)
const checking = ref(false)
const stats = ref({
  modelCount: 0,
  runningInstances: 0,
})

// 获取引擎状态
async function fetchStatus() {
  try {
    const status = await engineStore.fetchEngineStatus()
    engineStatus.value = status
  } catch (error) {
    console.error('Failed to fetch status:', error)
  }
}

// 重新检测环境
async function handleCheckEngine() {
  checking.value = true
  try {
    const result = await engineStore.triggerCheck()
    ElMessage.success(`检测任务已创建 (ID: ${result.task_id})`)
    // 等待一下再刷新状态
    setTimeout(fetchStatus, 2000)
  } catch (error) {
    ElMessage.error('检测失败')
  } finally {
    checking.value = false
  }
}

// 导航
function goToEngine() {
  router.push('/engine')
}

function goToModels() {
  router.push('/models')
}

function goToInstances() {
  router.push('/instances')
}

onMounted(() => {
  fetchStatus()
})
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
}

.status-cards {
  margin-bottom: 20px;
}

.card-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.card-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f0f2f5;
  color: #409eff;
}

.card-icon.ready {
  background-color: #f0f9ff;
  color: #67c23a;
}

.card-icon.partial {
  background-color: #fdf6ec;
  color: #e6a23c;
}

.card-icon.not_installed {
  background-color: #f5f7fa;
  color: #909399;
}

.card-icon.gpu {
  background-color: #f0f9ff;
  color: #409eff;
}

.card-icon.model {
  background-color: #f0f9ff;
  color: #67c23a;
}

.card-icon.instance {
  background-color: #f0f9ff;
  color: #e6a23c;
}

.card-info {
  flex: 1;
}

.card-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 4px;
}

.card-value {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.action-card,
.detail-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
