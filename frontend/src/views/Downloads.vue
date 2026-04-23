<template>
  <default-layout>
    <div class="downloads-page">
      <!-- 筛选栏 -->
      <el-card class="filter-card" shadow="hover">
        <el-space wrap>
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 150px" @change="fetchTasks">
            <el-option label="等待中" value="pending" />
            <el-option label="运行中" value="running" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
            <el-option label="已取消" value="canceled" />
          </el-select>
          
          <el-select v-model="filterTaskType" placeholder="任务类型" clearable style="width: 150px" @change="fetchTasks">
            <el-option label="模型分析" value="model_analyze" />
            <el-option label="模型下载" value="model_download" />
            <el-option label="环境检测" value="engine_check" />
            <el-option label="环境安装" value="engine_install" />
            <el-option label="实例启动" value="instance_start" />
            <el-option label="实例停止" value="instance_stop" />
          </el-select>
          
          <el-button type="primary" @click="fetchTasks">刷新</el-button>
          <el-switch v-model="autoRefresh" active-text="自动刷新" @change="toggleAutoRefresh" />
        </el-space>
      </el-card>
      
      <!-- 任务列表 -->
      <el-card shadow="hover">
        <el-table :data="taskList" stripe v-loading="loading">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="task_type" label="类型" width="150">
            <template #default="{ row }">
              <el-tag :type="getTaskTypeTag(row.task_type)">
                {{ getTaskTypeLabel(row.task_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="target_type" label="目标类型" width="100" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="getStatusTag(row.status)">
                {{ getStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="进度" width="150">
            <template #default="{ row }">
              <el-progress 
                :percentage="row.progress" 
                :status="row.status === 'failed' ? 'exception' : row.status === 'success' ? 'success' : undefined"
              />
            </template>
          </el-table-column>
          <el-table-column prop="message" label="消息" min-width="200" show-overflow-tooltip />
          <el-table-column prop="started_at" label="开始时间" width="180" />
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="viewLog(row)">日志</el-button>
              <el-button 
                size="small" 
                type="warning"
                :disabled="row.status !== 'failed'"
                @click="handleRetry(row)"
              >
                重试
              </el-button>
              <el-button 
                size="small" 
                type="danger"
                :disabled="row.status !== 'running' && row.status !== 'pending'"
                @click="handleCancel(row)"
              >
                取消
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <!-- 分页 -->
        <div class="pagination">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.page_size"
            :total="pagination.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="fetchTasks"
            @size-change="fetchTasks"
          />
        </div>
      </el-card>
      
      <!-- 日志对话框 -->
      <el-dialog v-model="showLogDialog" title="任务日志" width="800px">
        <div class="log-viewer">
          <pre>{{ currentLog }}</pre>
        </div>
        <template #footer>
          <el-button @click="showLogDialog = false">关闭</el-button>
        </template>
      </el-dialog>
    </div>
  </default-layout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { get, post } from '@/api/request'

const loading = ref(false)
const autoRefresh = ref(false)
const showLogDialog = ref(false)
const currentLog = ref('')

const filterStatus = ref('')
const filterTaskType = ref('')

const taskList = ref<any[]>([])
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

let refreshTimer: any = null

// 获取任务列表
async function fetchTasks() {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.page_size,
    }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterTaskType.value) params.task_type = filterTaskType.value
    
    const res: any = await get('/tasks', params)
    taskList.value = res.data.items
    pagination.total = res.data.total
  } catch (error) {
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

// 切换自动刷新
function toggleAutoRefresh() {
  if (autoRefresh.value) {
    refreshTimer = setInterval(fetchTasks, 5000)
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }
}

// 查看日志
async function viewLog(row: any) {
  try {
    if (row.log_path) {
      // 如果有日志路径，读取日志内容
      currentLog.value = `日志路径：${row.log_path}\n\n（日志内容待实现）`
    } else {
      currentLog.value = `任务消息：${row.message}\n\n（暂无日志文件）`
    }
    showLogDialog.value = true
  } catch (error) {
    ElMessage.error('获取日志失败')
  }
}

// 重试任务
async function handleRetry(row: any) {
  try {
    await ElMessageBox.confirm('确定要重试此任务吗？', '提示', {
      type: 'warning',
    })
    
    const res: any = await post(`/tasks/${row.id}/retry`)
    ElMessage.success(`重试任务已创建 (ID: ${res.data.task_id})`)
    fetchTasks()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('重试失败')
    }
  }
}

// 取消任务
async function handleCancel(row: any) {
  try {
    await ElMessageBox.confirm('确定要取消此任务吗？', '警告', {
      type: 'warning',
    })
    
    await post(`/tasks/${row.id}/cancel`)
    ElMessage.success('任务已取消')
    fetchTasks()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('取消失败')
    }
  }
}

// 工具函数
function getTaskTypeLabel(type: string) {
  const map: Record<string, string> = {
    engine_check: '环境检测',
    engine_install: '环境安装',
    engine_upgrade: '环境升级',
    model_analyze: '模型分析',
    model_download: '模型下载',
    instance_start: '实例启动',
    instance_stop: '实例停止',
    instance_restart: '实例重启',
  }
  return map[type] || type
}

function getTaskTypeTag(type: string) {
  const map: Record<string, any> = {
    engine_check: 'info',
    engine_install: 'warning',
    model_analyze: 'primary',
    model_download: 'success',
    instance_start: 'warning',
    instance_stop: 'danger',
  }
  return map[type] || 'info'
}

function getStatusLabel(status: string) {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    success: '成功',
    failed: '失败',
    canceled: '已取消',
  }
  return map[status] || status
}

function getStatusTag(status: string) {
  const map: Record<string, any> = {
    pending: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger',
    canceled: 'info',
  }
  return map[status] || 'info'
}

onMounted(() => {
  fetchTasks()
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.downloads-page {
  max-width: 1400px;
  margin: 0 auto;
}

.filter-card {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.log-viewer {
  max-height: 500px;
  overflow-y: auto;
  background-color: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 4px;
}

.log-viewer pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
