<template>
  <div class="app-container">
    <header class="dashboard-header">
      <div class="header-decoration-line"></div>
      
      <div class="header-left">
        <el-icon class="icon-margin" :size="22"><Location /></el-icon>
        <span class="org-text">{{ dashboardData.dashboard_info.organization }}</span>
      </div>

      <div class="header-center">
        <h1 class="main-title">{{ dashboardData.dashboard_info.title }}</h1>
      </div>

      <div class="header-right">
        <span class="time-text">{{ currentTime }}</span>
        <el-tag type="success" effect="dark" size="large" class="status-tag rounded-full px-4">系统正常</el-tag>
      </div>
    </header>

    <main class="main-content">
      
      <aside class="side-panel">
        
        <div class="tech-card flex-col flex-grow-4">
          <div class="panel-title">
            {{ dashboardData.layout_structure.left_panel.section_1.title }}
          </div>
          <div class="panel-body">
            <el-table :data="dashboardData.layout_structure.left_panel.section_1.data_samples" stripe style="width: 100%; height: 100%">
              <el-table-column prop="task" label="任务名称" min-width="110" align="center" header-align="center" show-overflow-tooltip></el-table-column>
              <el-table-column prop="route" label="航线名称" align="center" header-align="center" show-overflow-tooltip></el-table-column>
            </el-table>
          </div>
        </div>

        <div class="tech-card flex-col flex-grow-3">
          <div class="panel-title">
            {{ dashboardData.layout_structure.left_panel.section_2.title }}
          </div>
          <div class="panel-body params-wrapper">
            
            <div class="param-box">
               <div class="param-icon-bg">
                 <el-icon><Clock /></el-icon>
               </div>
               <div class="digital-text-group">
                 <div class="digital-value">00:45:12</div>
                 <div class="param-label">飞行时长</div>
               </div>
            </div>

            <div class="param-box">
              <el-progress 
                type="dashboard" 
                :percentage="35" 
                :width="90" 
                :stroke-width="8"
                color="#00ffff"
                :format="() => ''" 
              >
                <template #default>
                   <div class="gauge-content">
                     <span class="gauge-num">35</span>
                     <span class="gauge-unit">km/h</span>
                   </div>
                </template>
              </el-progress>
              <div class="param-label -mt-2">实时速度</div>
            </div>

            <div class="param-box">
              <el-progress 
                type="circle" 
                :percentage="78" 
                :width="80" 
                :stroke-width="8" 
                color="#4ade80" 
              />
              <div class="param-label mt-2">任务进度</div>
            </div>

          </div>
        </div>

        <div class="tech-card flex-col flex-grow-2">
          <div class="panel-title">
            {{ dashboardData.layout_structure.left_panel.section_3.title }}
            <div class="absolute-tag">
                <el-tag type="danger" effect="dark" size="small" class="rounded-tag">实时检测中</el-tag>
            </div>
          </div>
          <div class="panel-body risk-content">
             <el-empty description="当前无风险报警" :image-size="70" style="padding:0"></el-empty>
          </div>
        </div>

      </aside>

      <section class="center-panel">
        
        <div class="tech-card map-container">
          
          <div class="map-bg">
            <div class="map-grid"></div>
            <div class="map-pulse-circle"></div>
            <div class="map-ping-dot"></div>
            <div class="map-placeholder-text">
              <span>SHENYANG GIS MAP</span>
            </div>
          </div>

          <div class="map-overlay-center">
             <div class="stat-box">
                <div class="stat-num text-white">10</div>
                <div class="stat-desc">无人机总数</div>
             </div>
             <div class="stat-box">
                <div class="stat-num text-green">4</div>
                <div class="stat-desc">正在执行</div>
             </div>
             <div class="stat-box">
                <div class="stat-num text-yellow">6</div>
                <div class="stat-desc">待机中</div>
             </div>
          </div>

          <div class="map-overlay-bottom">
             <el-button type="primary" size="large" color="rgba(0, 255, 255, 0.3)" class="tech-btn text-lg rounded-btn">
                <el-icon class="mr-2" :size="22"><VideoPlay /></el-icon> 开始全域巡查
             </el-button>
          </div>
        </div>

        <div class="tech-card sub-view-container">
          <div class="panel-title tight-header">
            {{ dashboardData.layout_structure.center_panel.sub_view.title }}
          </div>
          <div class="camera-grid">
             <div class="camera-box">
               <div class="camera-placeholder">Camera 01</div>
               <div class="camera-status rec rounded-tag">● REC</div>
             </div>
             <div class="camera-box">
               <div class="camera-placeholder">Camera 02</div>
               <div class="camera-status live rounded-tag">● LIVE</div>
             </div>
          </div>
        </div>

      </section>

      <aside class="side-panel">
        
        <div class="tech-card flex-col flex-grow-3">
          <div class="panel-title">
            {{ dashboardData.layout_structure.right_panel.section_1.title }}
          </div>
          <div class="panel-body">
            <el-table :data="dashboardData.layout_structure.right_panel.section_1.data_samples" stripe style="width: 100%; height: 100%">
              <el-table-column prop="name" label="记录名称" min-width="120" align="center" header-align="center" show-overflow-tooltip></el-table-column>
              <el-table-column prop="date" label="时间" align="center" header-align="center"></el-table-column>
            </el-table>
          </div>
        </div>

        <div class="tech-card flex-col flex-grow-3">
          <div class="panel-title">
            {{ dashboardData.layout_structure.right_panel.section_2.title }}
          </div>
          <div class="panel-body">
             <el-table :data="dashboardData.layout_structure.right_panel.section_2.data_samples" stripe style="width: 100%; height: 100%">
                <el-table-column prop="name" label="设备名称" min-width="120" align="center" header-align="center" show-overflow-tooltip></el-table-column>
                <el-table-column label="状态" width="100" align="center" header-align="center">
                    <template #default>
                         <el-tag size="small" type="info" effect="dark" class="rounded-tag">空闲</el-tag>
                    </template>
                </el-table-column>
             </el-table>
          </div>
        </div>

        <div class="tech-card flex-col flex-grow-2">
          <div class="panel-title">
             {{ dashboardData.layout_structure.right_panel.section_3.title }}
          </div>
          <div class="panel-body center-content text-sub">
            暂无处置信息
          </div>
        </div>

        <div class="tech-card flex-col flex-grow-3">
          <div class="panel-title">
            {{ dashboardData.layout_structure.right_panel.section_4.title }}
          </div>
          <div class="panel-body video-box">
             <el-icon :size="48" class="play-icon"><VideoPlay /></el-icon>
             <span class="video-label">点击回放</span>
          </div>
        </div>

      </aside>

    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
// 如果图标没有全局注册，请取消下面的注释进行引入
// import { Location, VideoPlay, Clock } from '@element-plus/icons-vue'

const dashboardData = ref({
  "dashboard_info": {
    "title": "地铁无人机智慧巡查监控平台",
    "organization": "沈阳轨道交通 (Shenyang Rail Transit)"
  },
  "layout_structure": {
    "left_panel": {
      "section_1": {
        "title": "巡查任务",
        "data_samples": [
          {"task": "青年大街巡查", "route": "枢纽航线A"},
          {"task": "沈阳站巡查", "route": "重点区域B"},
          {"task": "奥体中心巡查", "route": "巡查航线C"},
          {"task": "中街商业区", "route": "沿线航线D"},
           {"task": "太原街巡查", "route": "沿线航线E"}
        ]
      },
      "section_2": { "title": "飞行参数" },
      "section_3": { "title": "风险识别", "current_status": "暂无" }
    },
    "center_panel": {
      "sub_view": { "title": "机库监控" }
    },
    "right_panel": {
      "section_1": {
        "title": "巡查记录",
        "data_samples": [
          {"name": "青年大街点位", "date": "10:00"},
          {"name": "沈阳站广场", "date": "10:15"},
          {"name": "奥体中心站", "date": "10:30"},
          {"name": "中街商业区", "date": "11:00"},
          {"name": "长青街沿线", "date": "11:20"}
        ]
      },
      "section_2": {
        "title": "设备统计",
        "data_samples": [
          {"id": "1", "name": "青年大街枢纽机场"},
          {"id": "2", "name": "沈阳站广场机场"},
          {"id": "3", "name": "奥体中心机场"},
          {"id": "4", "name": "浑南车辆段机库"},
          {"id": "5", "name": "滂江街节点机场"}
        ]
      },
      "section_3": { "title": "处置情况" },
      "section_4": { "title": "历史视频" }
    }
  }
});

const currentTime = ref('');
let timer = null;

const updateTime = () => {
  const now = new Date();
  currentTime.value = now.toLocaleString('zh-CN', { hour12: false });
};

onMounted(() => {
  updateTime();
  timer = setInterval(updateTime, 1000);
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<style scoped>
/* --- 全局变量与容器 --- */
:root {
  --bg-dark: #050b14;
  --bg-card: rgba(13, 25, 48, 0.85); 
  --border-color: rgba(0, 255, 255, 0.3);
  --accent-cyan: #00ffff;
  --text-main: #e0f2fe;
  --text-sub: #94a3b8;
}

.app-container {
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  background-color: #020617;
  color: #e0f2fe;
  font-size: 16px; 
  font-family: 'PingFang SC', sans-serif;
  overflow: hidden;
  box-sizing: border-box;
  padding: 10px;
  background-image: radial-gradient(circle at 50% 50%, #0f172a 0%, #020617 100%);
}

/* --- Header --- */
.dashboard-header {
  height: 70px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  position: relative;
  background: rgba(10, 20, 40, 0.6);
  border-bottom: 2px solid rgba(0,255,255,0.2);
  box-shadow: 0 0 15px rgba(0, 255, 255, 0.2);
  border-radius: 12px;
  margin-bottom: 12px;
}

.header-decoration-line {
  position: absolute;
  bottom: 0; left: 0; width: 100%; height: 2px;
  background: linear-gradient(90deg, transparent, #00ffff, transparent);
  box-shadow: 0 0 10px #00ffff;
}

.header-left, .header-right { width: 350px; display: flex; align-items: center; }
.header-right { justify-content: flex-end; }
.icon-margin { margin-right: 10px; color: #00ffff; }
.org-text { font-size: 18px; color: #00ffff; font-weight: 500; }

.main-title {
  font-size: 28px;
  font-weight: bold;
  letter-spacing: 3px;
  background: linear-gradient(to bottom, #fff, #00ffff);
  -webkit-background-clip: text;
  color: transparent;
  text-shadow: 0 0 15px rgba(0,255,255,0.6);
  margin: 0;
}
.time-text { font-family: monospace; font-size: 22px; margin-right: 20px; color: #00ffff; }
.status-tag { font-size: 14px; border: 2px solid #00ffff; color: #00ffff; background: rgba(0, 255, 255, 0.1); }
.rounded-full { border-radius: 9999px; }

/* --- 主布局 (Grid + Flex) --- */
.main-content {
  flex: 1;
  display: grid;
  grid-template-columns: 22% 56% 22%; 
  gap: 12px;
  overflow: hidden;
  padding-bottom: 4px;
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  overflow: hidden;
}

.center-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

/* --- 卡片通用样式 --- */
.tech-card {
  background: rgba(13, 25, 48, 0.6);
  border: 2px solid rgba(0, 255, 255, 0.25);
  box-shadow: inset 0 0 25px rgba(0, 100, 255, 0.1), 0 0 15px rgba(0, 255, 255, 0.15);
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 14px;
  border-radius: 16px;
  backdrop-filter: blur(4px);
}

/* Flex 权重类 */
.flex-col { display: flex; flex-direction: column; }
.flex-grow-1 { flex: 1; min-height: 0; }
.flex-grow-2 { flex: 2; min-height: 0; }
.flex-grow-3 { flex: 3; min-height: 0; }
.flex-grow-4 { flex: 4; min-height: 0; }

/* --- 面板标题 (居中 + 渐变) --- */
.panel-title {
  font-size: 18px;
  font-weight: 600;
  color: #00ffff;
  
  /* 居中核心 */
  justify-content: center; 
  text-align: center;
  position: relative;

  margin-bottom: 12px;
  height: 28px;
  line-height: 28px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  
  /* 渐变背景 */
  background: linear-gradient(90deg, transparent, rgba(0,255,255,0.15), transparent);
  border-bottom: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 8px 8px 0 0;
}
.absolute-tag {
  position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
}
.rounded-tag { border-radius: 9999px; transform: scale(0.9); }

/* 内容区域 */
.panel-body {
  flex: 1;
  overflow: hidden;
  position: relative;
}
.scrollable-y { overflow-y: auto; }
.center-content { display: flex; align-items: center; justify-content: center; }
.text-sub { color: #64748b; font-size: 14px; }

/* --- 飞行参数美化 (Dashboard Style) --- */
.params-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 4px;
  height: 100%;
}
.param-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0, 255, 255, 0.03);
  border: 1px solid rgba(0, 255, 255, 0.1);
  border-radius: 8px;
  height: 90%;
  margin: 0 4px;
  position: relative;
  box-shadow: inset 0 0 10px rgba(0, 255, 255, 0.02);
}
.param-label {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 5px;
  letter-spacing: 1px;
}
.-mt-2 { margin-top: -10px; }

/* 模块1：数字时钟 */
.param-icon-bg {
  color: #00ffff; font-size: 20px; margin-bottom: 4px; opacity: 0.8;
}
.digital-text-group { text-align: center; }
.digital-value {
  font-family: 'Courier New', Courier, monospace;
  font-size: 22px; font-weight: bold; color: #e0f2fe;
  text-shadow: 0 0 8px rgba(0, 255, 255, 0.6);
  letter-spacing: 1px;
}
/* 模块2：仪表盘 */
.gauge-content {
  display: flex; flex-direction: column; align-items: center; line-height: 1; margin-top: -5px;
}
.gauge-num {
  font-size: 24px; font-weight: bold; color: #00ffff;
  text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
}
.gauge-unit { font-size: 12px; color: #64748b; transform: scale(0.9); }
/* 覆盖进度条样式 */
:deep(.el-progress-circle__track) { stroke: rgba(255, 255, 255, 0.1) !important; }
:deep(.el-progress__text) { color: #e0f2fe !important; font-size: 16px !important; font-weight: bold; }

/* --- 风险识别 --- */
.risk-content {
  display: flex; align-items: center; justify-content: center;
}

/* --- 历史视频占位 --- */
.video-box {
  background: rgba(0,0,0,0.3);
  border: 2px dashed rgba(0, 255, 255, 0.3);
  display: flex; flex-direction: column; justify-content: center; align-items: center;
  color: #00ffff;
  cursor: pointer;
  border-radius: 12px;
}
.video-box:hover { background: rgba(0,255,255,0.08); }
.video-label { font-size: 14px; margin-top: 8px; }

/* --- 中间地图区域 --- */
.map-container {
  flex: 1;
  min-height: 0;
  position: relative;
  background: #000;
  padding: 0;
  border-radius: 16px;
  overflow: hidden;
  border: 2px solid rgba(0, 255, 255, 0.25);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.2);
}
.map-bg {
  position: absolute; inset: 0;
  background: radial-gradient(circle at center, #1e293b 0%, #020617 100%);
}
.map-grid {
  width: 100%; height: 100%;
  background-image: linear-gradient(rgba(0,255,255,0.1) 1px, transparent 1px),
  linear-gradient(90deg, rgba(0,255,255,0.1) 1px, transparent 1px);
  background-size: 50px 50px;
  opacity: 0.4;
}
.map-placeholder-text {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 50px;
  font-weight: bold; color: rgba(255,255,255,0.08);
  pointer-events: none;
}
/* 地图悬浮统计 */
.map-overlay-center {
  position: absolute; top: 30px; left: 50%;
  transform: translateX(-50%);
  display: flex; gap: 30px;
}
.stat-box {
  background: rgba(0,0,0,0.7);
  border: 2px solid rgba(0,255,255,0.4);
  padding: 10px 24px;
  border-radius: 12px;
  text-align: center;
  min-width: 90px;
  box-shadow: 0 0 15px rgba(0, 255, 255, 0.2);
}
.stat-num { font-size: 32px; font-weight: bold; line-height: 1.2; }
.stat-desc { font-size: 14px; color: #cbd5e1; }
.text-white { color: #fff; } .text-green { color: #4ade80; } .text-yellow { color: #facc15; }

.map-overlay-bottom {
  position: absolute; bottom: 30px; left: 50%;
  transform: translateX(-50%);
}
.tech-btn {
  border: 2px solid #00ffff; color: #00ffff;
  background: rgba(0,20,40,0.8);
  font-size: 16px; font-weight: bold;
  box-shadow: 0 0 15px rgba(0, 255, 255, 0.4);
}
.rounded-btn { border-radius: 9999px; padding-left: 3rem; padding-right: 3rem; }

/* --- 底部机库监控 --- */
.sub-view-container {
  height: 25%;
  min-height: 180px;
  flex-shrink: 0;
  padding: 0;
}
.tight-header { padding: 10px 14px; margin: 0; background: rgba(0,0,0,0.3); border-radius: 14px 14px 0 0; }
.camera-grid {
  flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 8px;
}
.camera-box {
  position: relative; background: #000; border: 2px solid rgba(0, 255, 255, 0.3);
  display: flex; align-items: center; justify-content: center;
  border-radius: 12px;
  overflow: hidden;
}
.camera-placeholder {
  color: #334155; font-size: 32px; font-weight: bold;
}
.camera-status {
  position: absolute; top: 8px; left: 8px;
  font-size: 12px; padding: 3px 8px;
  background: rgba(0,0,0,0.8); border: 1px solid;
}
.rec { color: #ef4444; border-color: #ef4444; } .live { color: #22c55e; border-color: #22c55e; }

/* --- 覆盖 Element Plus 表格样式 --- */
:deep(.el-table) {
  background-color: transparent !important;
  color: #e0f2fe !important;
  font-size: 15px !important;
  --el-table-tr-bg-color: transparent !important;
  --el-table-header-bg-color: rgba(0, 255, 255, 0.08) !important;
  --el-table-row-hover-bg-color: rgba(0, 255, 255, 0.12) !important;
  --el-table-border-color: rgba(0, 255, 255, 0.15) !important;
}
:deep(.el-table th.el-table__cell) {
  color: #00ffff; 
  font-weight: 600; 
  font-size: 16px !important;
  border-bottom: 1px solid rgba(0,255,255,0.25) !important;
}
:deep(.el-table td.el-table__cell) {
  padding: 8px 0;
  border-bottom: 1px solid rgba(0,255,255,0.08) !important;
}
:deep(.el-table__inner-wrapper::before) { display: none; }
</style>