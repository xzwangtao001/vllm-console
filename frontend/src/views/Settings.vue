<template>
  <default-layout>
    <div class="settings-page">
      <el-card shadow="hover">
        <template #header>
          <div class="card-header">
            <span>系统设置</span>
            <el-button type="primary" :loading="saving" @click="handleSave">保存设置</el-button>
          </div>
        </template>
        
        <el-form :model="settings" label-width="180px" ref="settingsFormRef">
          <!-- 目录设置 -->
          <el-divider content-position="left">目录设置</el-divider>
          
          <el-form-item label="默认模型目录">
            <el-input v-model="settings.default_model_dir" placeholder="/data/models" />
            <div class="form-tip">模型文件存储路径</div>
          </el-form-item>
          
          <el-form-item label="默认日志目录">
            <el-input v-model="settings.default_log_dir" placeholder="/data/logs" />
            <div class="form-tip">日志文件存储路径</div>
          </el-form-item>
          
          <!-- 模型源认证 -->
          <el-divider content-position="left">模型源认证</el-divider>
          
          <el-form-item label="HuggingFace Token">
            <el-input 
              v-model="settings.huggingface_token" 
              type="password" 
              show-password
              placeholder="hf_xxx"
            />
            <div class="form-tip">用于访问私有模型</div>
          </el-form-item>
          
          <el-form-item label="ModelScope Token">
            <el-input 
              v-model="settings.modelscope_token" 
              type="password" 
              show-password
              placeholder="xxx"
            />
            <div class="form-tip">用于访问 ModelScope 模型</div>
          </el-form-item>
          
          <!-- 网络设置 -->
          <el-divider content-position="left">网络设置</el-divider>
          
          <el-form-item label="HTTP 代理">
            <el-input v-model="settings.http_proxy" placeholder="http://proxy.example.com:8080" />
          </el-form-item>
          
          <el-form-item label="HTTPS 代理">
            <el-input v-model="settings.https_proxy" placeholder="https://proxy.example.com:8080" />
          </el-form-item>
          
          <!-- 实例默认参数 -->
          <el-divider content-position="left">实例默认参数</el-divider>
          
          <el-form-item label="默认监听地址">
            <el-input v-model="settings.default_host" placeholder="0.0.0.0" />
          </el-form-item>
          
          <el-form-item label="默认起始端口">
            <el-input-number v-model="settings.default_port_start" :min="1" :max="65535" style="width: 100%" />
          </el-form-item>
          
          <el-form-item label="默认精度">
            <el-select v-model="settings.default_instance_template.dtype" style="width: 100%">
              <el-option label="auto" value="auto" />
              <el-option label="float16" value="float16" />
              <el-option label="bfloat16" value="bfloat16" />
              <el-option label="float32" value="float32" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="默认张量并行数">
            <el-input-number v-model="settings.default_instance_template.tensor_parallel_size" :min="1" :max="8" style="width: 100%" />
          </el-form-item>
          
          <el-form-item label="默认 GPU 显存利用率">
            <el-slider v-model="settings.default_instance_template.gpu_memory_utilization" :step="0.1" :max="1" />
            <div class="form-tip">当前值：{{ settings.default_instance_template.gpu_memory_utilization }}</div>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </default-layout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import { get, put } from '@/api/request'

const saving = ref(false)
const settingsFormRef = ref()

const settings = reactive({
  default_model_dir: '',
  default_log_dir: '',
  huggingface_token: '',
  modelscope_token: '',
  http_proxy: '',
  https_proxy: '',
  default_host: '0.0.0.0',
  default_port_start: 8000,
  default_instance_template: {
    dtype: 'auto',
    tensor_parallel_size: 1,
    gpu_memory_utilization: 0.9,
  },
})

// 获取设置
async function fetchSettings() {
  try {
    const res: any = await get('/settings')
    Object.assign(settings, res.data)
  } catch (error) {
    ElMessage.error('获取设置失败')
  }
}

// 保存设置
async function handleSave() {
  saving.value = true
  try {
    await put('/settings', settings)
    ElMessage.success('设置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchSettings()
})
</script>

<style scoped>
.settings-page {
  max-width: 900px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.el-divider {
  margin: 24px 0 16px;
}
</style>
