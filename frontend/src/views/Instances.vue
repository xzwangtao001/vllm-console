<template>
  <default-layout>
    <div class="instances-page">
      <!-- 工具栏 -->
      <el-card class="toolbar-card" shadow="hover">
        <el-space wrap>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索实例名称"
            style="width: 200px"
            clearable
          />
          
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 150px">
            <el-option label="已创建" value="created" />
            <el-option label="启动中" value="starting" />
            <el-option label="运行中" value="running" />
            <el-option label="停止中" value="stopping" />
            <el-option label="已停止" value="stopped" />
            <el-option label="错误" value="error" />
          </el-select>
          
          <el-button type="primary" @click="fetchInstances">搜索</el-button>
          <el-button type="success" @click="showCreateDialog = true">创建实例</el-button>
        </el-space>
      </el-card>
      
      <!-- 实例列表 -->
      <el-card shadow="hover">
        <el-table :data="instanceList" stripe v-loading="loading">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="名称" min-width="150" />
          <el-table-column prop="model_name" label="模型" min-width="150" />
          <el-table-column prop="host" label="地址" width="140" />
          <el-table-column prop="port" label="端口" width="80" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="getStatusTag(row.status)">
                {{ getStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="health_status" label="健康状态" width="120">
            <template #default="{ row }">
              <el-tag :type="getHealthTag(row.health_status)">
                {{ row.health_status || '-' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="pid" label="PID" width="80" />
          <el-table-column label="操作" width="320" fixed="right">
            <template #default="{ row }">
              <el-button 
                size="small" 
                type="success"
                :disabled="row.status !== 'created' && row.status !== 'stopped'"
                @click="handleStart(row)"
              >
                启动
              </el-button>
              <el-button 
                size="small" 
                type="warning"
                :disabled="row.status !== 'running'"
                @click="handleStop(row)"
              >
                停止
              </el-button>
              <el-button 
                size="small" 
                :disabled="row.status !== 'running'"
                @click="handleRestart(row)"
              >
                重启
              </el-button>
              <el-button size="small" @click="handleViewLogs(row)">日志</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <!-- 分页 -->
        <div class="pagination">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.page_size"
            :total="pagination.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="fetchInstances"
            @size-change="fetchInstances"
          />
        </div>
      </el-card>
      
      <!-- 创建实例对话框 -->
      <el-dialog
        v-model="showCreateDialog"
        title="创建实例"
        width="700px"
      >
        <el-form :model="createForm" label-width="180px" :rules="createRules" ref="createFormRef">
          <el-form-item label="实例名称" prop="name">
            <el-input v-model="createForm.name" placeholder="qwen3-8b-api" />
          </el-form-item>
          
          <el-form-item label="选择模型" prop="model_id">
            <el-select v-model="createForm.model_id" style="width: 100%" @change="onModelChange">
              <el-option
                v-for="model in downloadedModels"
                :key="model.id"
                :label="model.name"
                :value="model.id"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="监听地址">
            <el-input v-model="createForm.host" placeholder="0.0.0.0" />
          </el-form-item>
          
          <el-form-item label="端口" prop="port">
            <el-input-number v-model="createForm.port" :min="1" :max="65535" style="width: 100%" />
          </el-form-item>
          
          <el-form-item label="服务模型名称">
            <el-input v-model="createForm.served_model_name" placeholder="qwen3-8b" />
          </el-form-item>
          
          <el-divider content-position="left">高级参数</el-divider>
          
          <el-form-item label="精度类型">
            <el-select v-model="createForm.dtype" style="width: 100%">
              <el-option label="auto" value="auto" />
              <el-option label="float16" value="float16" />
              <el-option label="bfloat16" value="bfloat16" />
              <el-option label="float32" value="float32" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="张量并行数">
            <el-input-number v-model="createForm.tensor_parallel_size" :min="1" :max="8" style="width: 100%" />
          </el-form-item>
          
          <el-form-item label="GPU 显存利用率">
            <el-slider v-model="createForm.gpu_memory_utilization" :step="0.1" :max="1" />
          </el-form-item>
          
          <el-form-item label="最大上下文长度">
            <el-input-number v-model="createForm.max_model_len" :min="1024" :step="1024" style="width: 100%" />
          </el-form-item>
          
          <el-form-item label="信任远程代码">
            <el-switch v-model="createForm.trust_remote_code" />
          </el-form-item>
        </el-form>
        
        <template #footer>
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" :loading="creating" @click="handleCreateSubmit">创建</el-button>
        </template>
      </el-dialog>
    </div>
  </default-layout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { get, post, del } from '@/api/request'

const loading = ref(false)
const creating = ref(false)
const showCreateDialog = ref(false)
const createFormRef = ref<FormInstance>()

const searchKeyword = ref('')
const filterStatus = ref('')

const instanceList = ref<any[]>([])
const downloadedModels = ref<any[]>([])
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

const createForm = reactive({
  name: '',
  model_id: null as number | null,
  host: '0.0.0.0',
  port: 8000,
  served_model_name: '',
  dtype: 'auto',
  tensor_parallel_size: 1,
  gpu_memory_utilization: 0.9,
  max_model_len: 8192,
  trust_remote_code: false,
})

const createRules: FormRules = {
  name: [{ required: true, message: '请输入实例名称', trigger: 'blur' }],
  model_id: [{ required: true, message: '请选择模型', trigger: 'change' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
}

// 获取实例列表
async function fetchInstances() {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.page_size,
    }
    if (filterStatus.value) params.status = filterStatus.value
    if (searchKeyword.value) params.keyword = searchKeyword.value
    
    const res: any = await get('/instances', params)
    instanceList.value = res.data.items
    pagination.total = res.data.total
  } catch (error) {
    ElMessage.error('获取实例列表失败')
  } finally {
    loading.value = false
  }
}

// 获取已下载的模型
async function fetchDownloadedModels() {
  try {
    const res: any = await get('/models', { status: 'downloaded', page_size: 100 })
    downloadedModels.value = res.data.items
  } catch (error) {
    console.error('Failed to fetch models:', error)
  }
}

// 模型变化
function onModelChange(modelId: number) {
  const model = downloadedModels.value.find(m => m.id === modelId)
  if (model && !createForm.served_model_name) {
    createForm.served_model_name = model.name.toLowerCase().replace(/[^a-z0-9]/g, '-')
  }
}

// 创建实例
async function handleCreateSubmit() {
  if (!createFormRef.value) return
  
  await createFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    creating.value = true
    try {
      await post('/instances', createForm)
      ElMessage.success('实例创建成功')
      showCreateDialog.value = false
      fetchInstances()
      // 重置表单
      Object.assign(createForm, {
        name: '',
        model_id: null,
        host: '0.0.0.0',
        port: 8000,
        served_model_name: '',
        dtype: 'auto',
        tensor_parallel_size: 1,
        gpu_memory_utilization: 0.9,
        max_model_len: 8192,
        trust_remote_code: false,
      })
    } catch (error) {
      ElMessage.error('创建失败')
    } finally {
      creating.value = false
    }
  })
}

// 启动实例
async function handleStart(row: any) {
  try {
    const res: any = await post(`/instances/${row.id}/start`)
    ElMessage.success(`启动任务已创建 (ID: ${res.data.task_id})`)
    setTimeout(fetchInstances, 2000)
  } catch (error) {
    ElMessage.error('启动失败')
  }
}

// 停止实例
async function handleStop(row: any) {
  try {
    await ElMessageBox.confirm(`确定要停止实例 "${row.name}" 吗？`, '警告', {
      type: 'warning',
    })
    
    const res: any = await post(`/instances/${row.id}/stop`)
    ElMessage.success(`停止任务已创建 (ID: ${res.data.task_id})`)
    setTimeout(fetchInstances, 2000)
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('停止失败')
    }
  }
}

// 重启实例
async function handleRestart(row: any) {
  try {
    await ElMessageBox.confirm(`确定要重启实例 "${row.name}" 吗？`, '警告', {
      type: 'warning',
    })
    
    const res: any = await post(`/instances/${row.id}/restart`)
    ElMessage.success(`重启任务已创建 (ID: ${res.data.task_id})`)
    setTimeout(fetchInstances, 2000)
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('重启失败')
    }
  }
}

// 查看日志
function handleViewLogs(row: any) {
  ElMessage.info(`查看实例 ${row.name} 的日志 (功能开发中)`)
}

// 删除实例
async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定要删除实例 "${row.name}" 吗？`, '警告', {
      type: 'warning',
    })
    
    await del(`/instances/${row.id}`)
    ElMessage.success('删除成功')
    fetchInstances()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 工具函数
function getStatusLabel(status: string) {
  const map: Record<string, string> = {
    created: '已创建',
    starting: '启动中',
    running: '运行中',
    stopping: '停止中',
    stopped: '已停止',
    error: '错误',
  }
  return map[status] || status
}

function getStatusTag(status: string) {
  const map: Record<string, any> = {
    created: 'info',
    starting: 'warning',
    running: 'success',
    stopping: 'warning',
    stopped: 'info',
    error: 'danger',
  }
  return map[status] || 'info'
}

function getHealthTag(health: string) {
  const map: Record<string, any> = {
    healthy: 'success',
    unhealthy: 'danger',
    unknown: 'info',
  }
  return map[health] || 'info'
}

onMounted(() => {
  fetchInstances()
  fetchDownloadedModels()
})
</script>

<style scoped>
.instances-page {
  max-width: 1400px;
  margin: 0 auto;
}

.toolbar-card {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
