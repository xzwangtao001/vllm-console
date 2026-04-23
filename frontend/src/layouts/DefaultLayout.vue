<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <h2>vLLM Console</h2>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#1e3a5f"
        text-color="#c5a065"
        active-text-color="#fff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        
        <el-menu-item index="/engine">
          <el-icon><Cpu /></el-icon>
          <span>引擎管理</span>
        </el-menu-item>
        
        <el-menu-item index="/models">
          <el-icon><Folder /></el-icon>
          <span>模型管理</span>
        </el-menu-item>
        
        <el-menu-item index="/downloads">
          <el-icon><Download /></el-icon>
          <span>下载任务</span>
        </el-menu-item>
        
        <el-menu-item index="/instances">
          <el-icon><Server /></el-icon>
          <span>实例管理</span>
        </el-menu-item>
        
        <el-menu-item index="/logs">
          <el-icon><Document /></el-icon>
          <span>日志中心</span>
        </el-menu-item>
        
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <!-- 主内容区 -->
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-left">
          <h3>{{ title }}</h3>
        </div>
        <div class="header-right">
          <el-button :icon="Refresh" circle @click="handleRefresh" />
          <el-tag size="small" effect="plain">v0.1.0</el-tag>
        </div>
      </el-header>
      
      <!-- 内容区 -->
      <el-main class="main-content">
        <slot />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Refresh, DataAnalysis, Cpu, Folder, Download, Server, Document, Setting } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const title = computed(() => {
  return (route.meta?.title as string) || 'vLLM Console'
})

const activeMenu = computed(() => {
  return route.path
})

const handleRefresh = () => {
  router.go(0)
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: #1e3a5f;
  color: #c5a065;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #162a47;
  border-bottom: 1px solid #2c5282;
}

.logo h2 {
  color: #c5a065;
  font-size: 18px;
  font-weight: 600;
}

.el-menu {
  border-right: none;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left h3 {
  color: #303133;
  font-size: 18px;
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.main-content {
  background-color: #f5f7fa;
  padding: 20px;
}
</style>
