<template>
  <default-layout>
    <div class="logs-page">
      <el-row :gutter="20">
        <!-- 左侧：日志对象列表 -->
        <el-col :span="8">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>日志对象</span>
                <el-button size="small" :icon="Refresh" circle @click="fetchLogSources" />
              </div>
            </template>
            
            <el-tabs v-model="activeTab">
              <el-tab-pane label="实例日志" name="instances">
                <el-input
                  v-model="instanceSearch"
                  placeholder="搜索实例"
                  size="small"
                  style="margin-bottom: 12px"
                  clearable
                />
                <el-scrollbar max-height="500px">
                  <div
                    v-for="item in filteredInstances"
                    :key="item.id"
                    class="log-item"
                    :class="{ active: selectedLog?.id === item.id && selectedLog?.type === 'instance' }"
                    @click="selectLog('instance', item)"
                  >
                    <div class="log-item-name">{{ item.name }}</div>
                    <div class="log-item-meta">
                      <el-tag size="small" :type="getStatusTag(item.status)">
                        {{ item.status }}
                      </el-tag>
                      <span class="log-item-port">:{{ item.port }}</span>
                    </div>
                  </div>
                </el-scrollbar>
              </el-tab-pane>
              
              <el-tab-pane label="任务日志" name="tasks">
                <el-input
                  v-model="taskSearch"
                  placeholder="搜索任务"
                  size="small"
                  style="margin-bottom: 12px"
                  clearable
                />
                <el-scrollbar max-height="500px">
                  <div
                    v-for="item in filteredTasks"
                    :key="item.id"
                    class="log-item"
                    :class="{ active: selectedLog?.id === item.id && selectedLog?.type === 'task' }"
                    @click="selectLog('task', item)"
                  >
                    <div class="log-item-name">{{ getTaskTypeName(item.task_type) }}</div>
                    <div class="log-item-meta">
                      <el-tag size="small" :type="getStatusTag(item.status)">
                        {{ item.status }}
                      </el-tag>
                      <span class="log-item-time">{{ formatTime(item.created_at) }}</span>
                    </div>
                  </div>
                </el-scrollbar>
              </el-tab-pane>
            </el-tabs>
          </el-card>
        </el-col>
        
        <!-- 右侧：日志查看器 -->
        <el-col :span="16">
          <el-card shadow="hover" class="log-viewer-card">
            <template #header>
              <div class="card-header">
                <span>{{ selectedLog ? selectedLog.name : '请选择日志' }}</span>
                <el-space>
                  <el-switch v-model="autoRefresh" active-text="自动刷新" @change="toggleAutoRefresh" />
                  <el-button size="small" :icon="Refresh" circle @click="fetchLog" :disabled="!selectedLog" />
                  <el-button size="small" @click="downloadLog" :disabled="!selectedLog">下载</el-button>
                </el-space>
              </div>
            </template>
            
            <div v-if="!selectedLog" class="empty-log">
              <el-empty description="请从左侧选择要查看的日志" />
            </div>
            
            <div v-else class="log-content">
              <el-scrollbar ref="logScrollRef" max-height="600px" @scroll="handleScroll">
                <pre v-loading="loadingLog">{{ logContent || '加载中...' }}</pre>
              </el-scrollbar>
              
              <div class="log-controls">
                <el-button size="small" @click="copyLog">复制</el-button>
                <el-button size="small" @click="scrollToBottom">滚动到底部</el-button>
                <span class="log-info">
                  行数：{{ logLines }} | 大小：{{ formatSize(logContent?.length || 0) }}
                </span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </default-layout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { get } from '@/api/request'

const loadingLog = ref(false)
const autoRefresh = ref(false)
const activeTab = ref('instances')
const instanceSearch = ref('')
const taskSearch = ref('')

const instances = ref<any[]>([])
const tasks = ref<any[]>([])
const selectedLog = ref<any>(null)
const logContent = ref('')
const logLines = ref(0)

const logScrollRef = ref()
let refreshTimer: any = null

// 过滤后的实例列表
const filteredInstances = computed(() => {
  if (!instanceSearch.value) return instances.value
  return instances.value.filter(i => 
    i.name.toLowerCase().includes(instanceSearch.value.toLowerCase())
  )
})

// 过滤后的任务列表
const filteredTasks = computed(() => {
  if (!taskSearch.value) return tasks.value
  return tasks.value.filter(t => 
    t.task_type.toLowerCase().includes(taskSearch.value.toLowerCase()) ||
    t.message?.toLowerCase().includes(taskSearch.value.toLowerCase())
  )
})

// 获取实例列表
async function fetchInstances() {
  try {
    const res: any = await get('/instances', { page_size: 100 })
    instances.value = res.data.items
  } catch (error) {
    console.error('Failed to fetch instances:', error)
  }
}

// 获取任务列表（用于日志）
async function fetchTasks() {
  try {
    const res: any = await get('/tasks', { page_size: 100 })
    tasks.value = res.data.items.filter(t => t.log_path)
  } catch (error) {
    console.error('Failed to fetch tasks:', error)
  }
}

// 刷新日志源列表
function fetchLogSources() {
  fetchInstances()
  fetchTasks()
}

// 选择日志
function selectLog(type: string, item: any) {
  selectedLog.value = { type, ...item }
  logContent.value = ''
  fetchLog()
}

// 获取日志内容
async function fetchLog() {
  if (!selectedLog.value) return
  
  loadingLog.value = true
  try {
    if (selectedLog.value.type === 'instance') {
      const res: any = await get(`/instances/${selectedLog.value.id}/logs`, {
        lines: 500,
        offset: 0,
      })
      logContent.value = res.data.content || '暂无日志内容'
      logLines.value = res.data.lines || 0
    } else {
      // 任务日志（待实现后端 API）
      logContent.value = `任务日志路径：${selectedLog.value.log_path}\n\n（日志内容待实现）`
      logLines.value = 0
    }
    
    // 滚动到底部
    setTimeout(scrollToBottom, 100)
  } catch (error) {
    logContent.value = '获取日志失败'
  } finally {
    loadingLog.value = false
  }
}

// 切换自动刷新
function toggleAutoRefresh() {
  if (autoRefresh.value) {
    refreshTimer = setInterval(fetchLog, 3000)
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }
}

// 滚动到底部
function scrollToBottom() {
  if (logScrollRef.value) {
    const container = logScrollRef.value.wrapRef
    if (container) {
      container.scrollTop = container.scrollHeight
    }
  }
}

// 处理滚动（自动加载更多）
function handleScroll(event: any) {
  // TODO: 实现滚动加载更多
}

// 复制日志
function copyLog() {
  navigator.clipboard.writeText(logContent.value)
  ElMessage.success('已复制到剪贴板')
}

// 下载日志
function downloadLog() {
  const blob = new Blob([logContent.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${selectedLog.value.name || 'log'}.txt`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('下载已开始')
}

// 工具函数
function getTaskTypeName(type: string) {
  const map: Record<string, string> = {
    engine_check: '环境检测',
    engine_install: '环境安装',
    model_analyze: '模型分析',
    model_download: '模型下载',
    instance_start: '实例启动',
    instance_stop: '实例停止',
  }
  return map[type] || type
}

function getStatusTag(status: string) {
  const map: Record<string, any> = {
    running: 'warning',
    success: 'success',
    failed: 'danger',
    stopped: 'info',
  }
  return map[status] || 'info'
}

function formatTime(time: string) {
  if (!time) return ''
  return new Date(time).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

onMounted(() => {
  fetchLogSources()
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.logs-page {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.log-item {
  padding: 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.log-item:hover {
  background-color: #f5f7fa;
}

.log-item.active {
  background-color: #ecf5ff;
  border-color: #409eff;
}

.log-item-name {
  font-weight: 500;
  color: #303133;
  margin-bottom: 6px;
}

.log-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.log-item-port {
  color: #909399;
}

.log-item-time {
  color: #909399;
}

.log-viewer-card {
  height: calc(100vh - 160px);
}

.empty-log {
  height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.log-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.log-content pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  background-color: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 4px;
  min-height: 400px;
}

.log-controls {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.log-info {
  margin-left: auto;
  font-size: 12px;
  color: #909399;
}
</style>
