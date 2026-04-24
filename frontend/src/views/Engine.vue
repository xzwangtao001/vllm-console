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
          <div class="card-header"><span>vLLM 引擎</span><el-tag :type="vllmStatusTag">{{ vllmStatusLabel }}</el-tag></div>
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
          <el-button :disabled="!canInstall" :loading="installing" @click="showInstallDialog = true">安装 vLLM</el-button>
          <el-button :disabled="!engineStatus?.vllm_version" :loading="upgrading" @click="handleUpgrade">升级 vLLM</el-button>
          <el-button @click="showLogs = true">查看日志</el-button>
        </el-space>
      </el-card>

      <el-dialog v-model="showInstallDialog" title="安装 vLLM" width="500px">
        <el-form :model="installForm" label-width="120px">
          <el-form-item label="Python 路径"><el-input v-model="installForm.python_path" placeholder="留空自动检测" /></el-form-item>
          <el-form-item label="虚拟环境路径"><el-input v-model="installForm.venv_path" placeholder="留空自动检测" /></el-form-item>
          <el-form-item label="安装参数"><el-input v-model="installForm.install_args" placeholder="-i https://mirrors.aliyun.com/pypi/simple/" /></el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showInstallDialog = false">取消</el-button>
          <el-button type="primary" :loading="installing" @click="handleInstall">开始安装</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="showInstallProgress" title="安装进度" width="600px" :close-on-click-modal="false" :close-on-press-escape="false">
        <div class="install-progress">
          <el-progress :percentage="installProgress" :status="installStatus" :stroke-width="20" />
          <div class="progress-message">{{ installMessage }}</div>
          <div v-if="installLogs.length > 0" class="log-container">
            <pre class="log-content">{{ installLogs.join('\n') }}</pre>
          </div>
        </div>
        <template #footer>
          <el-button v-if="installFinished" type="primary" @click="onInstallComplete">完成</el-button>
          <el-button v-else @click="handleCancelInstall">取消</el-button>
        </template>
      </el-dialog>

      <el-dialog v-model="showLogs" title="安装日志" width="800px">
        <div v-if="logs.length === 0" class="empty-logs">暂无日志记录</div>
        <el-table v-else :data="logs" stripe>
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="task_type" label="类型" width="120" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }"><el-tag :type="row.status === 'success' ? 'success' : row.status === 'running' ? 'warning' : 'danger'" size="small">{{ row.status }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="message" label="信息" show-overflow-tooltip />
          <el-table-column prop="created_at" label="时间" width="180" />
        </el-table>
      </el-dialog>
    </div>
  </default-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { useEngineStore } from '@/stores/engine'
import { installEngine, upgradeEngine, getTask, getEngineLogs, cancelTask } from '@/api/engine'

const engineStore = useEngineStore()
const engineStatus = ref<any>(null)
const checking = ref(false)
const installing = ref(false)
const upgrading = ref(false)
const showInstallDialog = ref(false)
const showInstallProgress = ref(false)
const showLogs = ref(false)
const logs = ref<any[]>([])

const installForm = ref({ python_path: '', venv_path: '', install_args: '' })
const installProgress = ref(0)
const installMessage = ref('')
const installLogs = ref<string[]>([])
const installStatus = ref<'success' | 'exception' | ''>('')
const installFinished = ref(false)
const currentTaskId = ref(0)
let pollTimer: any = null

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
const vllmStatusTag = computed(() => engineStatus.value?.vllm_version ? 'success' : 'info')
const canInstall = computed(() => !engineStatus.value?.vllm_version)

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

async function handleInstall() {
  installing.value = true
  try {
    const result = await installEngine(installForm.value)
    currentTaskId.value = result.data.task_id
    showInstallDialog.value = false
    showInstallProgress.value = true
    installProgress.value = 0
    installMessage.value = '任务已创建，等待开始...'
    installLogs.value = []
    installStatus.value = ''
    installFinished.value = false
    startPolling()
  } catch { ElMessage.error('安装失败') } finally { installing.value = false }
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    try {
      const task = await getTask(currentTaskId.value)
      const t = task.data
      installProgress.value = t.progress || 0
      installMessage.value = t.message || ''
      if (t.message) { installLogs.value.push(t.message); if (installLogs.value.length > 50) installLogs.value.shift() }
      if (t.status === 'success') { installStatus.value = 'success'; installFinished.value = true; clearInterval(pollTimer); fetchStatus() }
      else if (t.status === 'failed') { installStatus.value = 'exception'; installMessage.value = t.message || '安装失败'; installFinished.value = true; clearInterval(pollTimer) }
      else if (t.status === 'canceled') { installStatus.value = 'exception'; installMessage.value = '安装已取消'; installFinished.value = true; clearInterval(pollTimer) }
    } catch { /* ignore */ }
  }, 2000)
}

function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }

async function handleCancelInstall() {
  try {
    await cancelTask(currentTaskId.value)
    ElMessage.info('安装已取消')
    installMessage.value = '已取消'
    installFinished.value = true
    stopPolling()
  } catch { ElMessage.error('取消失败') }
}

function onInstallComplete() { showInstallProgress.value = false; stopPolling() }

async function handleUpgrade() {
  try {
    await ElMessageBox.confirm('确定要升级 vLLM 吗？', '提示', { type: 'warning' })
    upgrading.value = true
    const result = await upgradeEngine()
    ElMessage.success(`升级任务已创建 (ID: ${result.data.task_id})`)
    setTimeout(fetchStatus, 3000)
  } catch (error: any) { if (error !== 'cancel') ElMessage.error('升级失败') } finally { upgrading.value = false }
}

onMounted(() => { fetchStatus() })
onUnmounted(() => { stopPolling() })
</script>

<style scoped>
.engine-page { max-width: 1200px; margin: 0 auto; }
.status-card, .gpu-card, .vllm-card, .action-card { margin-bottom: 20px; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.no-gpu { padding: 20px; }
.gpu-list { margin-top: 16px; }
.gpu-list h4 { margin-bottom: 12px; color: #303133; font-size: 14px; }
.install-progress { padding: 20px 0; }
.progress-message { margin-top: 12px; font-size: 14px; color: #606266; min-height: 20px; }
.log-container { margin-top: 16px; max-height: 300px; overflow-y: auto; background: #f5f7fa; border-radius: 4px; padding: 12px; }
.log-content { margin: 0; font-family: monospace; font-size: 12px; line-height: 1.5; white-space: pre-wrap; word-break: break-all; color: #606266; }
.empty-logs { text-align: center; padding: 40px; color: #909399; }
</style>
