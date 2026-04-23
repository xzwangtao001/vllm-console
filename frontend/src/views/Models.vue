<template>
  <default-layout>
    <div class="models-page">
      <!-- 工具栏 -->
      <el-card class="toolbar-card" shadow="hover">
        <el-space wrap>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索模型名称或仓库"
            style="width: 240px"
            clearable
            @clear="handleSearch"
          />
          
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 150px" @change="handleSearch">
            <el-option label="新建" value="new" />
            <el-option label="待下载" value="ready_to_download" />
            <el-option label="下载中" value="downloading" />
            <el-option label="已下载" value="downloaded" />
            <el-option label="错误" value="error" />
          </el-select>
          
          <el-select v-model="filterSourceType" placeholder="来源筛选" clearable style="width: 150px" @change="handleSearch">
            <el-option label="HuggingFace" value="huggingface" />
            <el-option label="ModelScope" value="modelscope" />
            <el-option label="本地" value="local" />
          </el-select>
          
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button type="success" @click="showAddDialog = true">添加模型</el-button>
        </el-space>
      </el-card>
      
      <!-- 模型列表 -->
      <el-card shadow="hover">
        <el-table :data="modelList" stripe v-loading="loading">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="名称" min-width="150" />
          <el-table-column prop="source_type" label="来源" width="120">
            <template #default="{ row }">
              <el-tag :type="getSourceTypeTag(row.source_type)">
                {{ getSourceTypeLabel(row.source_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="source_repo" label="仓库" min-width="200" />
          <el-table-column prop="local_path" label="本地路径" min-width="200" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="140">
            <template #default="{ row }">
              <el-tag :type="getStatusTag(row.status)">
                {{ getStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="大小" width="100">
            <template #default="{ row }">
              {{ formatSize(row.local_size_bytes) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="handleAnalyze(row)">分析</el-button>
              <el-button 
                size="small" 
                type="primary"
                :disabled="row.status !== 'ready_to_download' && row.status !== 'error'"
                @click="handleDownload(row)"
              >
                下载
              </el-button>
              <el-button 
                size="small" 
                type="success"
                :disabled="row.status !== 'downloaded'"
                @click="handleCreateInstance(row)"
              >
                创建实例
              </el-button>
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
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @current-change="fetchModels"
            @size-change="fetchModels"
          />
        </div>
      </el-card>
      
      <!-- 添加模型对话框 -->
      <el-dialog
        v-model="showAddDialog"
        title="添加模型"
        width="600px"
      >
        <el-form :model="addForm" label-width="120px" :rules="addRules" ref="addFormRef">
          <el-form-item label="模型名称" prop="name">
            <el-input v-model="addForm.name" placeholder="Qwen3-8B" />
          </el-form-item>
          
          <el-form-item label="来源类型" prop="source_type">
            <el-select v-model="addForm.source_type" style="width: 100%" @change="onSourceTypeChange">
              <el-option label="HuggingFace" value="huggingface" />
              <el-option label="ModelScope" value="modelscope" />
              <el-option label="本地" value="local" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="仓库 ID" prop="source_repo">
            <el-input v-model="addForm.source_repo" :placeholder="repoPlaceholder" />
          </el-form-item>
          
          <el-form-item label="分支/版本">
            <el-input v-model="addForm.source_revision" placeholder="main" />
          </el-form-item>
          
          <el-form-item label="本地路径" prop="local_path">
            <el-input v-model="addForm.local_path" placeholder="/data/models/xxx" />
          </el-form-item>
          
          <el-form-item label="备注">
            <el-input v-model="addForm.remark" type="textarea" :rows="2" />
          </el-form-item>
        </el-form>
        
        <template #footer>
          <el-button @click="showAddDialog = false">取消</el-button>
          <el-button type="primary" :loading="adding" @click="handleAddSubmit">确定</el-button>
        </template>
      </el-dialog>
    </div>
  </default-layout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { get, post, del } from '@/api/request'
import { useRouter } from 'vue-router'

const router = useRouter()

const loading = ref(false)
const adding = ref(false)
const showAddDialog = ref(false)
const addFormRef = ref<FormInstance>()

const searchKeyword = ref('')
const filterStatus = ref('')
const filterSourceType = ref('')

const modelList = ref<any[]>([])
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

const addForm = reactive({
  name: '',
  source_type: 'huggingface',
  source_repo: '',
  source_revision: 'main',
  local_path: '',
  remark: '',
})

const addRules: FormRules = {
  name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  source_type: [{ required: true, message: '请选择来源类型', trigger: 'change' }],
  source_repo: [{ required: true, message: '请输入仓库 ID', trigger: 'blur' }],
  local_path: [{ required: true, message: '请输入本地路径', trigger: 'blur' }],
}

const repoPlaceholder = computed(() => {
  if (addForm.source_type === 'huggingface') {
    return '例如：Qwen/Qwen3-8B'
  } else if (addForm.source_type === 'modelscope') {
    return '例如：qwen/Qwen3-8B'
  }
  return '本地路径'
})

// 获取模型列表
async function fetchModels() {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.page_size,
    }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterSourceType.value) params.source_type = filterSourceType.value
    if (searchKeyword.value) params.keyword = searchKeyword.value
    
    const res: any = await get('/models', params)
    modelList.value = res.data.items
    pagination.total = res.data.total
  } catch (error) {
    ElMessage.error('获取模型列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索
function handleSearch() {
  pagination.page = 1
  fetchModels()
}

// 来源类型变化
function onSourceTypeChange() {
  addForm.source_repo = ''
}

// 添加模型
async function handleAddSubmit() {
  if (!addFormRef.value) return
  
  await addFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    adding.value = true
    try {
      await post('/models', addForm)
      ElMessage.success('模型添加成功')
      showAddDialog.value = false
      fetchModels()
      // 重置表单
      Object.assign(addForm, {
        name: '',
        source_type: 'huggingface',
        source_repo: '',
        source_revision: 'main',
        local_path: '',
        remark: '',
      })
    } catch (error) {
      ElMessage.error('添加失败')
    } finally {
      adding.value = false
    }
  })
}

// 分析模型
async function handleAnalyze(row: any) {
  try {
    const res: any = await post(`/models/${row.id}/analyze`)
    ElMessage.success(`分析任务已创建 (ID: ${res.data.task_id})`)
    setTimeout(fetchModels, 2000)
  } catch (error) {
    ElMessage.error('分析失败')
  }
}

// 下载模型
async function handleDownload(row: any) {
  try {
    const res: any = await post(`/models/${row.id}/download`, { force: false })
    ElMessage.success(`下载任务已创建 (ID: ${res.data.task_id})`)
    setTimeout(fetchModels, 2000)
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

// 创建实例
function handleCreateInstance(row: any) {
  router.push(`/instances?model_id=${row.id}`)
}

// 删除模型
async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定要删除模型 "${row.name}" 吗？`, '警告', {
      type: 'warning',
    })
    
    await del(`/models/${row.id}`)
    ElMessage.success('删除成功')
    fetchModels()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 工具函数
function getSourceTypeLabel(type: string) {
  const map: Record<string, string> = {
    huggingface: 'HuggingFace',
    modelscope: 'ModelScope',
    local: '本地',
  }
  return map[type] || type
}

function getSourceTypeTag(type: string) {
  const map: Record<string, any> = {
    huggingface: 'primary',
    modelscope: 'success',
    local: 'info',
  }
  return map[type] || 'info'
}

function getStatusLabel(status: string) {
  const map: Record<string, string> = {
    new: '新建',
    analyzing: '分析中',
    ready_to_download: '待下载',
    downloading: '下载中',
    downloaded: '已下载',
    invalid: '无效',
    error: '错误',
  }
  return map[status] || status
}

function getStatusTag(status: string) {
  const map: Record<string, any> = {
    new: 'info',
    ready_to_download: 'warning',
    downloading: 'primary',
    downloaded: 'success',
    error: 'danger',
  }
  return map[status] || 'info'
}

function formatSize(bytes: number) {
  if (!bytes) return '-'
  const gb = bytes / 1024 / 1024 / 1024
  if (gb > 1) return `${gb.toFixed(2)} GB`
  const mb = bytes / 1024 / 1024
  return `${mb.toFixed(2)} MB`
}

import { computed } from 'vue'

onMounted(() => {
  fetchModels()
})
</script>

<style scoped>
.models-page {
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
