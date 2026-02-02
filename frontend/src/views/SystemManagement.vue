<template>
  <div class="system-management-page">
    <!-- 页面头部 -->
    <div class="page-header-premium">
      <div class="header-content">
        <div class="header-left">
          <div class="header-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
            </svg>
          </div>
          <div class="header-text">
            <h1 class="page-title">系统管理</h1>
            <p class="page-subtitle">监控机场状态与人员权限管理</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 主体内容：分栏布局 -->
    <div class="content-grid">
      <!-- 左侧：机场监控 -->
      <div class="grid-col left-col">
        <div class="panel-header">
          <h2 class="panel-title">
            <span class="icon">🏭</span>
            机场监控
          </h2>
        </div>
        <div class="panel-body">
          <DockStatusPanel />
        </div>
      </div>

      <!-- 右侧：人员管理 -->
      <div class="grid-col right-col">
        <div class="panel-header">
          <h2 class="panel-title">
            <span class="icon">👥</span>
            人员管理
          </h2>
        </div>
        <div class="panel-body">
          <UserList />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import DockStatusPanel from '@/components/DockStatusPanel.vue'
import UserList from '@/components/UserList.vue'

export default {
  name: 'SystemManagement',
  components: {
    DockStatusPanel,
    UserList
  },
  mounted() {
    document.title = '系统管理 - FlightHub'
  }
}
</script>

<style scoped>
.system-management-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 头部样式 */
.page-header-premium {
  margin-bottom: 24px;
}

.header-content {
  padding: 24px 32px;
  background: rgba(26, 31, 58, 0.6);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  border: 1px solid rgba(0, 212, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 4px 16px rgba(0, 212, 255, 0.4);
}

.header-icon svg {
  width: 28px;
  height: 28px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 4px 0;
}

.page-subtitle {
  color: #94a3b8;
  font-size: 14px;
  margin: 0;
}

/* 分栏布局 */
.content-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr; /* 左侧占60%，右侧占40% */
  gap: 24px;
  flex: 1;
  min-height: 0; /* 防止溢出 */
}

.grid-col {
  background: rgba(26, 31, 58, 0.4);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  border: 1px solid rgba(0, 212, 255, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.panel-header {
  padding: 16px 24px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.15);
  background: rgba(0, 212, 255, 0.05);
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: #00d4ff;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-body {
  flex: 1;
  overflow-y: auto; /* 允许垂直滚动，防止内容被截断 */
  position: relative;
  padding: 4px; /* 增加一点内边距，避免滚动条紧贴内容 */
}

/* 隐藏滚动条但保留功能 (可选，视需求而定，这里先保留默认滚动条以便用户感知) */
.panel-body::-webkit-scrollbar {
  width: 6px;
}
.panel-body::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.02);
}
.panel-body::-webkit-scrollbar-thumb {
  background: rgba(56, 189, 248, 0.2);
  border-radius: 3px;
}

/* 响应式 */
@media (max-width: 1200px) {
  .content-grid {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto;
    overflow-y: auto;
  }
  
  .grid-col {
    min-height: 500px;
  }
}
</style>