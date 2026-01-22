<template>
  <div class="home-dashboard">
    <div class="dashboard-grid">
      <aside class="side-panel">
        <DashboardCard
          title="机场信息"
          icon="🏭"
          :more-to="routes.dock"
          :loading="loading.dock"
          :error="errors.dock"
          :is-empty="!dockSummary"
          empty-text="暂无机场信息"
        >
          <div class="dock-container">
            <div v-for="(item, index) in docks" :key="index" class="dock-card">
              <div class="dock-title">
                <span class="status-dot" :class="{ online: item.is_online }"></span>
                <span class="name-text">{{ getDockDisplayName(item) }}</span>
              </div>
              <div class="info-list">
                <div class="info-row">
                  <span class="label">🌡️ 环境温度</span>
                  <span class="value">{{ formatTemperature(item.environment_temperature) }}</span>
                </div>
                <div class="info-row">
                  <span class="label">💨 当前风速</span>
                  <span class="value">{{ formatWindSpeed(item.wind_speed) }}</span>
                </div>
                <div class="info-row">
                  <span class="label">🚁 无人机状态</span>
                  <span class="value" :class="{ 'highlight': isDroneWorking(item) }">
                    {{ getDroneInDockText(item.drone_in_dock) }}
                  </span>
                </div>
                <div class="info-row">
                  <span class="label">🔋 剩余电量</span>
                  <span class="value">{{ formatBatteryPercent(item.drone_battery_percent) }}</span>
                </div>
              </div>
            </div>
          </div>
        </DashboardCard>

        <DashboardCard
          title="告警管理"
          icon="🚨"
          :more-to="routes.alarm"
          :loading="loading.alarms"
          :error="errors.alarms"
          :is-empty="recentAlarms.length === 0"
          empty-text="暂无告警"
        >
           <div class="table-container">
            <div class="table-header">
              <span class="th-box">类型</span>
              <span class="th-box">描述</span>
              <span class="th-box">时间</span>
            </div>
            <div class="table-content">
              <div v-for="(item, index) in recentAlarms" :key="index" class="table-row">
                <span class="col">{{ item.category_name }}</span>
                <span class="col">{{ item.content }}</span>
                <span class="col">{{ formatDateTime(item.created_at) }}</span>
              </div>
            </div>
          </div>
        </DashboardCard>

        <DashboardCard
          title="告警统计"
          icon="📊"
          :more-to="routes.alarmStats"
          :loading="loading.alarmStats"
          :error="errors.alarmStats"
          :is-empty="!alertDetectTypeStats || alertDetectTypeStats.total === 0"
          empty-text="暂无统计"
        >
          <div class="stats-wrap">
            <div class="stats-total">
              <span class="stats-label">近12个月告警</span>
              <span class="stats-value">{{ (alertDetectTypeStats && alertDetectTypeStats.total) || 0 }}</span>
            </div>
            <div v-if="alertDetectTypeStats && alertDetectTypeStats.total > 0" class="donut-mini-content">
              <DonutRing
                :series="alertDetectTypeStats.series"
                total-label="总异常"
                :total-value="alertDetectTypeStats.total"
              />
              <div class="donut-mini-legend">
                <div v-for="item in alertDetectTypeStats.series" :key="item.id" class="legend-item">
                  <span class="legend-dot" :style="{ background: item.color }"></span>
                  <div class="legend-text">
                    <span class="legend-name" :title="item.name">{{ item.name }}</span>
                    <span class="legend-value">{{ donutPercent(item.value) }}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </DashboardCard>
      </aside>

      <section class="center-stage">
        <div class="map-card-wrapper">
          
          <div id="cesiumContainer" ref="cesiumContainer" class="cesium-full-screen"></div>
          
          <button class="start-btn-inline" @click="goStart">
            <span class="start-btn-text">启动检测</span>
            <span class="start-btn-sub">进入智能主控台</span>
          </button>
        </div>

        <div class="bottom-media">
          <div class="dashboard-card">
            <div class="card-header">
              <div class="header-main">
                <span class="card-icon" aria-hidden="true">🛡️</span>
                <h3 class="card-title">系统安全</h3>
              </div>
            </div>
            <div class="card-body">
              <div class="corner top-left"></div>
              <div class="corner top-right"></div>
              <div class="corner bottom-left"></div>
              <div class="corner bottom-right"></div>
              <div class="hero-content">
                <div class="hero-header">
                  <div>
                    <p class="hero-label">安全运行天数</p>
                    <div class="hero-number">
                      {{ safetyStats.safetyDays }}
                      <span class="hero-unit">天</span>
                    </div>
                  </div>
                  <span class="hero-tag">本年度</span>
                </div>
                <div class="hero-summary">
                  <div v-for="s in safetyStatuses" :key="s.label" class="summary-chip">
                    <span class="chip-dot" :style="{ background: s.color }"></span>
                    <span class="chip-label">{{ s.label }}</span>
                    <span class="chip-value">{{ s.value }}</span>
                  </div>
                </div>
                <div class="hero-foot">
                  <span class="foot-label">最近告警时间</span>
                  <span class="foot-value">{{ safetyLastUpdated }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="dashboard-card">
            <div class="card-header">
              <div class="header-main">
                <span class="card-icon" aria-hidden="true">🎞️</span>
                <h3 class="card-title">航迹回放</h3>
              </div>
            </div>
            <div class="card-body">
              <div class="corner top-left"></div>
              <div class="corner top-right"></div>
              <div class="corner bottom-left"></div>
              <div class="corner bottom-right"></div>
              <div class="playback-content">
                <div class="playback-ui">
                  <button class="btn-play-large" aria-label="播放" />
                </div>
                <div class="time-stamp-v2">{{ nowStamp }}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <aside class="side-panel">
        <DashboardCard
          title="AI检测"
          icon="🧠"
          :more-to="routes.ai"
          :loading="loading.ai"
          :error="errors.ai"
          :is-empty="aiSlides.length === 0"
          empty-text="暂无图片"
        >
          <div class="ai-card" @mouseenter="stopAiAuto" @mouseleave="startAiAuto">
            <div v-if="currentAiSlide" class="ai-slide">
              <div class="ai-image">
                <img :src="currentAiSlide.imageUrl" alt="AI检测图片" @error="handleAiImgError" />
              </div>
              <div class="ai-meta">
                <div class="ai-title">{{ currentAiSlide.title }}</div>
                <div class="ai-sub">{{ formatDateTime(currentAiSlide.createdAt) }}</div>
              </div>
            </div>
            <div v-else class="ai-empty">暂无可展示图片</div>
            <div v-if="aiSlides.length > 1" class="ai-controls">
              <button class="ai-btn ghost" @click="prevAi">上一张</button>
              <div class="ai-count">{{ aiIndex + 1 }}/{{ aiSlides.length }}</div>
              <button class="ai-btn ghost" @click="nextAi">下一张</button>
            </div>
          </div>
        </DashboardCard>

        <DashboardCard
          title="巡检任务"
          icon="📋"
          :more-to="routes.tasks"
          :loading="loading.tasks"
          :error="errors.tasks"
          :is-empty="recentTasks.length === 0"
          empty-text="暂无任务"
        >
          <div class="table-container">
            <div class="table-header">
              <span class="th-box">巡检类型</span>
              <span class="th-box">巡检状态</span>
              <span class="th-box">巡检时间</span>
            </div>
            <div class="table-content">
              <div v-for="t in recentTasks" :key="t.id" class="table-row">
                <span class="col">{{ t.detect_category_name || "--" }}</span>
                <span class="col">
                  <span class="pill">{{ getStatusText(t.detect_status) }}</span>
                </span>
                <span class="col">{{ formatDateTime(t.created_at) }}</span>
              </div>
            </div>
          </div>
        </DashboardCard>

        <DashboardCard
          title="人员管理"
          icon="👥"
          :more-to="routes.users"
          :loading="loading.users"
          :error="errors.users"
          :is-empty="personnel.users.length === 0"
          empty-text="暂无人员信息"
        >
           <div class="personnel">
            <div class="table-container">
              <div class="table-header">
                <span class="th-box">用户名</span>
                <span class="th-box">姓名</span>
                <span class="th-box">角色</span>
              </div>
              <div class="table-content">
                <div v-for="u in personnel.users" :key="u.id || u.username" class="table-row">
                  <span class="col">{{ u.username }}</span>
                  <span class="col">{{ u.name }}</span>
                  <span class="col">{{ u.role }}</span>
                </div>
              </div>
            </div>
          </div>
        </DashboardCard>
      </aside>
    </div>
  </div>
</template>

<script>
import DashboardCard from '@/components/dashboard/DashboardCard.vue'
import DonutRing from '@/components/dashboard/DonutRing.vue'
import homeDashboardApi from '@/api/homeDashboardApi'
import dockStatusApi from "@/api/dockStatusApi";

// 🔥 1. 引入 Cesium
import * as Cesium from 'cesium';

export default {
  name: 'MainView',
  components: {
    DashboardCard,
    DonutRing
  },
  data() {
    return {
      routes: {
        dock: '/dock-monitor',
        alarm: '/alarm-management',
        alarmStats: '/alarm-stats',
        ai: '/carousel-detection',
        tasks: '/inspect-task-management',
        users: '/user-management'
      },
      loading: {
        dock: true,
        alarms: true,
        alarmStats: true,
        ai: true,
        tasks: true,
        users: true,
        safety: true
      },
      errors: {
        dock: '',
        alarms: '',
        alarmStats: '',
        ai: '',
        tasks: '',
        users: '',
        safety: ''
      },
      dockSummary: null,
      docks: [],
      recentAlarms: [],
      alertWaylineStats: null,
      alertDetectTypeStats: null,
      aiSlides: [],
      aiIndex: 0,
      aiTimer: null,
      recentTasks: [],
      personnel: { isAdmin: false, total: 0, users: [] },
      safetyStats: { safetyDays: 0, todayAlarms: 0, monthAlarms: 0, yearAlarms: 0, latestAlarmAt: null },
      nowStampTimer: null,
      nowStamp: '',
      
      // 🔥 Cesium 实例
      cesiumViewer: null,
      dockEntities: [],
      dockPickHandler: null,
      selectedDockEntity: null,
      dockPinBuilder: null,
      dockMarkerCache: { online: null, offline: null }
    }
  },
  computed: {
    safetyStatuses() {
      return [
        { label: '今日异常', value: this.safetyStats.todayAlarms, color: '#38bdf8' },
        { label: '近30天异常', value: this.safetyStats.monthAlarms, color: '#a855f7' },
        { label: '本年异常', value: this.safetyStats.yearAlarms, color: '#22c55e' }
      ]
    },
    safetyLastUpdated() {
      if (!this.safetyStats.latestAlarmAt) return '--'
      return this.formatDateTime(this.safetyStats.latestAlarmAt)
    },
    currentAiSlide() {
      return this.aiSlides[this.aiIndex] || null
    }
  },
  mounted() {
    this.updateNowStamp()
    this.nowStampTimer = setInterval(() => {
      this.updateNowStamp()
      this.loadDock()
    }, 1000 * 10)
    this.loadAll()
    
    // 🔥 2. 初始化地图 (确保 DOM 已渲染)
    this.$nextTick(() => {
      this.initCesiumMap();
    });
  },
  beforeUnmount() {
    this.stopAiAuto()
    if (this.nowStampTimer) {
      clearInterval(this.nowStampTimer)
      this.nowStampTimer = null
    }
    if (this.dockPickHandler) {
      this.dockPickHandler.destroy()
      this.dockPickHandler = null
    }
    this.clearDockMarkers()
    // 🔥 3. 销毁地图，防止内存泄漏
    if (this.cesiumViewer && !this.cesiumViewer.isDestroyed()) {
      this.cesiumViewer.destroy();
      this.cesiumViewer = null;
    }
  },
  methods: {
    // 🔥 4. 核心地图初始化方法
initCesiumMap() {
  console.log('>>> [调试] 开始初始化地图...');
  
  const container = this.$refs.cesiumContainer;
  if (!container) {
    console.error('>>> [错误] 找不到 DOM 容器 cesiumContainer');
    return;
  }

  // 1. 获取正确的 IP
  const hostname = window.location.hostname;
  // 2. 拼接地址 (请确认你的 style 名字是不是 basic-preview)
  const tileUrl = `http://${hostname}:7777/services/shenyang3/tiles/{z}/{x}/{y}.png`;
  
  console.log('>>> [调试] 地图服务地址:', tileUrl);

  try {
    this.cesiumViewer = new Cesium.Viewer(container, {
      animation: false,
      baseLayerPicker: false,
      fullscreenButton: false,
      geocoder: false,
      homeButton: false,
      infoBox: false,
      sceneModePicker: false,
      selectionIndicator: false,
      timeline: false,
      navigationHelpButton: false,
      sceneMode: Cesium.SceneMode.SCENE3D,
      imageryProvider: false, // 先关掉默认的，后面再加
      contextOptions: {
        webgl: {
          alpha: true
        }
      }
    });

      this.tuneCameraControls(this.cesiumViewer.scene.screenSpaceCameraController);
      this.setupDockPickHandler();
    
    console.log('>>> [调试] Viewer 创建成功');
    
    // 强制显示地球
    this.cesiumViewer.scene.globe.show = true;
    this.cesiumViewer.scene.globe.baseColor = Cesium.Color.BLUE; // 给个蓝色底，证明 Cesium 活着

    // 加载图层
    const layer = new Cesium.UrlTemplateImageryProvider({
      url: tileUrl,
      maximumLevel: 18
    });

    // 监听错误
    layer.errorEvent.addEventListener((event) => {
      console.error('>>> [错误] 图层加载失败:', event);
    });

    this.cesiumViewer.imageryLayers.addImageryProvider(layer);
    console.log('>>> [调试] 图层已添加');

    // 飞过去
    const target = this.tileToLonLat(13, 6899, 3050);
    const viewConfig = { height: 15000, latOffset: 0.01 };
      this.cesiumViewer.camera.setView({
          destination: Cesium.Cartesian3.fromDegrees(
            target.lon,
            target.lat + viewConfig.latOffset,
            viewConfig.height
          ),
          orientation: {
            heading: 0,
            pitch: Cesium.Math.toRadians(-90),
            roll: 0
          }
      });
      this.renderDockMarkers();
      
    } catch (e) {
    console.error('>>> [错误] Cesium 初始化崩溃:', e);
  }
},
    // --- 其他原有方法 ---
      tuneCameraControls(controller) {
        if (!controller) return
        if (typeof controller.zoomFactor === 'number') {
          controller.zoomFactor = 0.4
        }
        if (typeof controller._zoomFactor === 'number') {
          controller._zoomFactor = 0.4
        }
        if (typeof controller.minimumZoomRate === 'number') {
          controller.minimumZoomRate = 0.05
        }
      },
      setupDockPickHandler() {
        if (!this.cesiumViewer || this.dockPickHandler) return
        this.dockPickHandler = new Cesium.ScreenSpaceEventHandler(this.cesiumViewer.scene.canvas)
        this.dockPickHandler.setInputAction(click => {
          const picked = this.cesiumViewer.scene.pick(click.position)
          if (Cesium.defined(picked) && picked.id && picked.id.dockData) {
            this.selectDockEntity(picked.id)
            return
          }
          this.clearDockSelection()
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
      },
      clearDockSelection() {
        if (this.selectedDockEntity && this.selectedDockEntity.label) {
          this.selectedDockEntity.label.show = false
        }
        this.selectedDockEntity = null
      },
      selectDockEntity(entity) {
        if (!entity || !entity.label) {
          this.clearDockSelection()
          return
        }
        if (this.selectedDockEntity && this.selectedDockEntity !== entity && this.selectedDockEntity.label) {
          this.selectedDockEntity.label.show = false
        }
        this.selectedDockEntity = entity
        this.selectedDockEntity.label.show = true
      },
      clearDockMarkers() {
        if (!this.cesiumViewer || !this.dockEntities.length) {
          this.dockEntities = []
          this.clearDockSelection()
          return
        }
        this.dockEntities.forEach(entity => {
          this.cesiumViewer.entities.remove(entity)
        })
        this.dockEntities = []
        this.clearDockSelection()
      },
      buildDockLabelText(dock) {
        const name = this.getDockDisplayName(dock)
        const status = dock?.is_online ? '在线' : '离线'
        const envTemp = this.formatTemperature(dock?.environment_temperature)
        const wind = this.formatWindSpeed(dock?.wind_speed)
        const droneState = this.getDroneInDockText(dock?.drone_in_dock)
        const battery = this.formatBatteryPercent(dock?.drone_battery_percent)
        const dockSn = dock?.dock_sn || '--'
        const droneSn = dock?.drone_sn || '--'
        return [
          name,
          `SN: ${dockSn}`,
          `状态: ${status}`,
          `环境温度: ${envTemp}`,
          `风速: ${wind}`,
          `无人机SN: ${droneSn}`,
          `电量: ${battery}`,
          `无人机状态: ${droneState}`
        ].join('\n')
      },
      getDockMarkerImage(isOnline) {
        const cacheKey = isOnline ? 'online' : 'offline'
        if (!this.dockMarkerCache) {
          this.dockMarkerCache = { online: null, offline: null }
        }
        if (this.dockMarkerCache[cacheKey]) return this.dockMarkerCache[cacheKey]

        const palette = isOnline
          ? { primary: '#16a34a', accent: '#86efac' }
          : { primary: '#ea580c', accent: '#fdba74' }
        const markerCanvas = this.createDockMarkerCanvas(palette.primary, palette.accent)
        this.dockMarkerCache[cacheKey] = markerCanvas
        return markerCanvas
      },
      createDockMarkerCanvas(primaryColor, accentColor) {
        const size = 78
        const canvas = document.createElement('canvas')
        canvas.width = size
        canvas.height = size
        const ctx = canvas.getContext('2d')
        if (!ctx) return canvas

        const center = size / 2
        const ringRadius = 16
        const glowRadius = 30
        const innerRadius = 12
        const primary = Cesium.Color.fromCssColorString(primaryColor)
        const accent = Cesium.Color.fromCssColorString(accentColor)

        const glow = ctx.createRadialGradient(center, center, 6, center, center, glowRadius)
        glow.addColorStop(0, primary.withAlpha(0.35).toCssColorString())
        glow.addColorStop(1, primary.withAlpha(0).toCssColorString())
        ctx.fillStyle = glow
        ctx.beginPath()
        ctx.arc(center, center, glowRadius, 0, Math.PI * 2)
        ctx.fill()

        const baseY = center + ringRadius - 1
        const tipY = center + ringRadius + 14
        ctx.beginPath()
        ctx.moveTo(center - 8, baseY)
        ctx.lineTo(center + 8, baseY)
        ctx.lineTo(center, tipY)
        ctx.closePath()
        ctx.fillStyle = primary.withAlpha(0.9).toCssColorString()
        ctx.fill()
        ctx.strokeStyle = accent.withAlpha(0.9).toCssColorString()
        ctx.lineWidth = 2
        ctx.stroke()

        ctx.save()
        ctx.shadowColor = primary.withAlpha(0.5).toCssColorString()
        ctx.shadowBlur = 12
        ctx.beginPath()
        ctx.arc(center, center, ringRadius, 0, Math.PI * 2)
        ctx.fillStyle = primary.withAlpha(0.92).toCssColorString()
        ctx.fill()
        ctx.restore()

        ctx.beginPath()
        ctx.lineWidth = 3
        ctx.strokeStyle = accent.withAlpha(0.95).toCssColorString()
        ctx.arc(center, center, ringRadius + 2, 0, Math.PI * 2)
        ctx.stroke()

        ctx.beginPath()
        ctx.fillStyle = '#0b1024'
        ctx.arc(center, center, innerRadius, 0, Math.PI * 2)
        ctx.fill()
        ctx.lineWidth = 1
        ctx.strokeStyle = accent.withAlpha(0.55).toCssColorString()
        ctx.stroke()

        const runwayWidth = 8
        const runwayHeight = 16
        const runwayX = center - runwayWidth / 2
        const runwayY = center - runwayHeight / 2 - 1
        ctx.fillStyle = primary.withAlpha(0.85).toCssColorString()
        ctx.fillRect(runwayX, runwayY, runwayWidth, runwayHeight)
        ctx.strokeStyle = accent.withAlpha(0.8).toCssColorString()
        ctx.lineWidth = 1
        ctx.strokeRect(runwayX, runwayY, runwayWidth, runwayHeight)

        ctx.fillStyle = '#f8fafc'
        const lineWidth = 2
        const lineHeight = 3
        for (let i = 0; i < 3; i += 1) {
          const lineY = runwayY + 2 + i * 5
          ctx.fillRect(center - lineWidth / 2, lineY, lineWidth, lineHeight)
        }

        const terminalWidth = 16
        const terminalHeight = 6
        const terminalX = center - terminalWidth / 2
        const terminalY = center + 6
        ctx.fillStyle = accent.withAlpha(0.9).toCssColorString()
        ctx.fillRect(terminalX, terminalY, terminalWidth, terminalHeight)

        ctx.fillStyle = '#0b1024'
        for (let i = 0; i < 3; i += 1) {
          ctx.fillRect(terminalX + 2 + i * 5, terminalY + 2, 2, 2)
        }

        const towerWidth = 4
        const towerHeight = 7
        const towerX = center - 14
        const towerY = center + 3
        ctx.fillStyle = accent.withAlpha(0.9).toCssColorString()
        ctx.fillRect(towerX, towerY, towerWidth, towerHeight)
        ctx.fillStyle = accent.withAlpha(0.7).toCssColorString()
        ctx.fillRect(towerX - 1, towerY - 3, towerWidth + 2, 3)

        ctx.strokeStyle = accent.withAlpha(0.8).toCssColorString()
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.arc(towerX + towerWidth / 2, towerY - 3, 4, Math.PI, Math.PI * 1.5)
        ctx.stroke()

        return canvas
      },
      renderDockMarkers() {
        if (!this.cesiumViewer) return
        this.clearDockMarkers()
        if (!Array.isArray(this.docks) || this.docks.length === 0) return

        const entities = []

        this.docks.forEach(dock => {
          const lat = Number(dock?.latitude)
          const lon = Number(dock?.longitude)
          if (!Number.isFinite(lat) || !Number.isFinite(lon)) return

          const isOnline = Boolean(dock?.is_online)
          const markerImage = this.getDockMarkerImage(isOnline)
          const labelAccent = Cesium.Color.fromCssColorString(isOnline ? '#86efac' : '#fdba74')

          const entity = this.cesiumViewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees(lon, lat, 0),
            billboard: {
              image: markerImage,
              verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
              heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
              scale: 1,
              disableDepthTestDistance: Number.POSITIVE_INFINITY
            },
            label: {
              text: this.buildDockLabelText(dock),
              font: '12px "Segoe UI", sans-serif',
              fillColor: Cesium.Color.WHITE,
              showBackground: true,
              backgroundColor: Cesium.Color.fromCssColorString('#0b1225').withAlpha(0.9),
              outlineColor: labelAccent.withAlpha(0.85),
              outlineWidth: 2,
              pixelOffset: new Cesium.Cartesian2(0, -70),
              verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
              horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
              disableDepthTestDistance: Number.POSITIVE_INFINITY,
              show: false
            }
          })
          entity.dockData = dock
          entities.push(entity)
        })

        this.dockEntities = entities
      },
      async loadAll() {
      await Promise.all([
        this.loadDock(),
        this.loadRecentAlarms(),
        this.loadAlertStats(),
        this.loadAiSlides(),
        this.loadTasks(),
        this.loadUsers(),
        this.loadSafety()
      ])
      this.startAiAuto()
    },
    async loadDock() {
      this.loading.dock = true
      this.errors.dock = ''
      try {
        this.dockSummary = await homeDashboardApi.getDockSummary()
        const docksData = await dockStatusApi.getAllDocks()

        // 按 dock_sn 排序，防止列表跳动
        if (docksData && Array.isArray(docksData)) {
          docksData.sort((a, b) => {
            const snA = a.dock_sn || ''
            const snB = b.dock_sn || ''
            return snA.localeCompare(snB)
          })
        }

          this.docks = docksData || []
          this.renderDockMarkers()
      } catch (e) {
        this.dockSummary = null
        this.errors.dock = this.getErrMsg(e, '加载机场信息失败')
      } finally {
        this.loading.dock = false
      }
    },
    async loadRecentAlarms() {
      this.loading.alarms = true
      this.errors.alarms = ''
      try {
        const list = await homeDashboardApi.getRecentAlarms(5)
        this.recentAlarms = list.map(item => ({
          ...item,
          category_name: item.category_details?.name || item.category_name || '未分类'
        }))
      } catch (e) {
        this.recentAlarms = []
        this.errors.alarms = this.getErrMsg(e, '加载告警列表失败')
      } finally {
        this.loading.alarms = false
      }
    },
    async loadAlertStats() {
      this.loading.alarmStats = true
      this.errors.alarmStats = ''
      try {
        this.alertWaylineStats = await homeDashboardApi.getAlertWaylineStats({ months: 12, topN: 6 })
        console.log(this.alertWaylineStats)
        this.alertDetectTypeStats = await homeDashboardApi.getDetectTypeStats()
        console.log(this.alertDetectTypeStats)
      } catch (e) {
        this.alertWaylineStats = null
        this.errors.alarmStats = this.getErrMsg(e, '加载告警统计失败')
      } finally {
        this.loading.alarmStats = false
      }
    },
    async loadAiSlides() {
      this.loading.ai = true
      this.errors.ai = ''
      try {
        this.aiSlides = await homeDashboardApi.getAiDetectionSlides(6)
        this.aiIndex = 0
      } catch (e) {
        this.aiSlides = []
        this.aiIndex = 0
        this.errors.ai = this.getErrMsg(e, '加载AI检测图片失败')
      } finally {
        this.loading.ai = false
      }
    },
    async loadTasks() {
      this.loading.tasks = true
      this.errors.tasks = ''
      try {
        this.recentTasks = await homeDashboardApi.getRecentInspectTasks(5)
      } catch (e) {
        this.recentTasks = []
        this.errors.tasks = this.getErrMsg(e, '加载巡检任务失败')
      } finally {
        this.loading.tasks = false
      }
    },
    async loadUsers() {
      this.loading.users = true
      this.errors.users = ''
      try {
        this.personnel = await homeDashboardApi.getPersonnelSummary(5)
      } catch (e) {
        this.personnel = { isAdmin: false, total: 0, users: [] }
        this.errors.users = this.getErrMsg(e, '加载人员信息失败')
      } finally {
        this.loading.users = false
      }
    },
    async loadSafety() {
      this.loading.safety = true
      this.errors.safety = ''
      try {
        this.safetyStats = await homeDashboardApi.getSafetyStats()
      } catch (e) {
        this.safetyStats = { safetyDays: 0, todayAlarms: 0, monthAlarms: 0, yearAlarms: 0, latestAlarmAt: null }
        this.errors.safety = this.getErrMsg(e, '加载安全统计失败')
      } finally {
        this.loading.safety = false
      }
    },
    formatTemperature(temp) {
      return temp !== null && temp !== undefined ? `${temp}℃` : '--'
    },
    getDockDisplayName(dock) {
      return dock?.display_name || dock?.dock_name || dock?.dock_sn || '--'
    },
    formatBatteryPercent(value) {
      if (value === null || value === undefined || value === '') return '--'
      const numeric = Number(value)
      return Number.isFinite(numeric) ? `${numeric}%` : '--'
    },
    tileToLonLat(z, x, y) {
      const n = Math.pow(2, z)
      const lon = ((x + 0.5) / n) * 360 - 180
      const latRad = Math.atan(Math.sinh(Math.PI * (1 - (2 * (y + 0.5)) / n)))
      const lat = (latRad * 180) / Math.PI
      return { lon, lat }
    },
    formatWindSpeed(speed) {
      return speed !== null && speed !== undefined ? `${speed} m/s` : '--'
    },
    getStatusText(status) {
      const statusMap = {
        'pending': '待检测',
        'processing': '检测中',
        'done': '已完成',
        'failed': '失败'
      }
      return statusMap[status] || status
    },
    isDroneWorking(dock) {
      return dock?.drone_in_dock === 0 || dock?.drone_in_dock === '0'
    },
    getDroneInDockText(state) {
      const stateMap = {
        0: '不在舱内',
        1: '在舱内',
        null: '--'
      }
      return stateMap[state] || '未知'
    },
    goStart() {
      this.$router.push('/')
    },
    updateNowStamp() {
      this.nowStamp = this.formatDateTime(new Date())
    },
    startAiAuto() {
      if (this.aiTimer || this.aiSlides.length <= 1) return
      this.aiTimer = setInterval(() => {
        this.nextAi()
      }, 4500)
    },
    stopAiAuto() {
      if (this.aiTimer) {
        clearInterval(this.aiTimer)
        this.aiTimer = null
      }
    },
    nextAi() {
      if (!this.aiSlides.length) return
      this.aiIndex = (this.aiIndex + 1) % this.aiSlides.length
    },
    prevAi() {
      if (!this.aiSlides.length) return
      this.aiIndex = (this.aiIndex - 1 + this.aiSlides.length) % this.aiSlides.length
    },
    donutPercent(value) {
      const total = Number(this.alertWaylineStats?.total || 0)
      if (!total) return 0
      return Math.round((Number(value || 0) / total) * 100)
    },
    handleAiImgError(event) {
      try {
        event.target.style.display = 'none'
      } catch (e) {
        // ignore
      }
    },
    getErrMsg(err, fallback) {
      const msg = err?.response?.data?.detail || err?.message
      return msg ? String(msg) : fallback
    },
    formatDateTime(dateLike) {
      const dt = dateLike instanceof Date ? dateLike : new Date(dateLike)
      if (Number.isNaN(dt.getTime())) return '--'
      const pad = n => String(n).padStart(2, '0')
      return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())} ${pad(dt.getHours())}:${pad(dt.getMinutes())}`
    }
  }
}
</script>

<style scoped>
/* 保持原有的大部分样式，只修改地图相关部分 */

.home-dashboard {
  width: 100%;
  height: calc(100vh - 110px);
  display: flex;
  flex-direction: column;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) 3fr minmax(280px, 1fr);
  gap: 18px;
  flex: 1;
  min-height: 0;
  width: 100%;
  table-layout: fixed;
}

.side-panel {
  display: grid;
  grid-template-rows: repeat(3, 1fr);
  gap: 18px;
  min-height: 0;
  min-width: 0;
  width: 100%;
  overflow: hidden;
}

.side-panel :deep(.dashboard-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.side-panel :deep(.card-body) {
  flex: 1;
  overflow-y: auto;
}

.center-stage {
  display: grid;
  grid-template-rows: repeat(3, 1fr);
  gap: 18px;
  min-height: 0;
  height: 100%;
}

/* 🔥 地图区域样式修正 */
.map-card-wrapper {
  grid-row: span 2;
  position: relative;
  border-radius: 18px;
  overflow: hidden;
  min-height: 0;
  background: #0b1024; /* 兜底深色背景 */
}

/* Cesium 容器全屏铺满 */
.cesium-full-screen {
  width: 100%;
  height: 100%;
  display: block;
  position: absolute;
  top: 0;
  left: 0;
}

/* 强制覆盖 Cesium 样式，防止溢出 */
:deep(.cesium-viewer),
:deep(.cesium-viewer-cesiumWidgetContainer),
:deep(.cesium-widget),
:deep(.cesium-widget canvas) {
  width: 100% !important;
  height: 100% !important;
  position: absolute !important;
  top: 0 !important;
  left: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}

.start-btn-inline {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  width: 420px;
  z-index: 10; /* 确保在地图上方 */
  padding: 16px 24px;
  border-radius: 12px;
  border: 1px solid rgba(0, 212, 255, 0.4);
  background: linear-gradient(135deg, rgba(10, 30, 60, 0.9), rgba(20, 50, 100, 0.85));
  backdrop-filter: blur(12px);
  color: #e0f2fe;
  cursor: pointer;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), 0 0 40px rgba(0, 212, 255, 0.2);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
}

.start-btn-inline:hover {
  border-color: #0ea5e9;
  background: rgba(14, 165, 233, 0.2);
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.6), 0 0 60px rgba(0, 212, 255, 0.35);
  transform: translateX(-50%) translateY(-2px);
}

.start-btn-text {
  font-size: 20px;
  font-weight: 900;
  letter-spacing: 4px;
  text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
}

.start-btn-sub {
  font-size: 13px;
  color: #7dd3fc;
  opacity: 0.8;
}

.dashboard-card {
  background: rgba(10, 35, 65, 0.7);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 191, 255, 0.3);
  box-shadow: 0 0 20px rgba(0, 140, 255, 0.2) inset;
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: visible;
  height: 100%;
  transition: all 0.3s ease;
}

.dashboard-card:hover {
  border-color: rgba(0, 191, 255, 0.5);
  box-shadow: 0 0 25px rgba(0, 140, 255, 0.3) inset;
}

.corner {
  position: absolute;
  width: 10px;
  height: 10px;
  border: 2px solid #00bfff;
  z-index: 2;
}
.top-left { top: -1px; left: -1px; border-right: none; border-bottom: none; }
.top-right { top: -1px; right: -1px; border-left: none; border-bottom: none; }
.bottom-left { bottom: -1px; left: -1px; border-right: none; border-top: none; }
.bottom-right { bottom: -1px; right: -1px; border-left: none; border-top: none; }

.card-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 16px;
  background: linear-gradient(to bottom, rgba(0, 110, 255, 0.25), transparent);
  border-bottom: 1px solid rgba(0, 191, 255, 0.15);
  min-height: 48px;
}

.header-main {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 60%;
}

.card-body {
  flex: 1;
  padding: 10px;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.bottom-media {
  grid-row: span 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
.glass-card {
  background: rgba(30, 41, 59, 0.45);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
}
.hero-card {
  position: relative;
  background: linear-gradient(135deg, rgba(12, 74, 110, 0.85), rgba(30, 64, 175, 0.85));
}
.hero-overlay {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 80% 20%, rgba(56, 189, 248, 0.35), transparent 45%),
    radial-gradient(circle at 20% 80%, rgba(94, 234, 212, 0.25), transparent 40%);
  filter: blur(10px);
  opacity: 0.8;
}
.hero-content {
  position: relative;
  padding: 18px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  z-index: 1;
}
.hero-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.hero-label {
  margin: 0;
  color: #cbd5e1;
  font-size: 13px;
  letter-spacing: 1px;
}
.hero-number {
  font-size: 44px;
  font-weight: 900;
  color: #e0f2fe;
  text-shadow: 0 0 16px rgba(14, 165, 233, 0.7);
}
.hero-unit {
  font-size: 14px;
  color: #bae6fd;
  margin-left: 6px;
}
.hero-tag {
  padding: 8px 12px;
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.4);
  border-radius: 999px;
  color: #e0f2fe;
  font-size: 12px;
}
.hero-summary {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.summary-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  background: rgba(15, 23, 42, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  color: #cbd5e1;
}
.chip-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}
.chip-label {
  font-size: 12px;
}
.chip-value {
  font-size: 14px;
  font-weight: 800;
  color: #e2e8f0;
}
.hero-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding-top: 4px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.foot-label {
  color: #cbd5e1;
  font-size: 12px;
  opacity: 0.9;
}
.foot-value {
  color: #e0f2fe;
  font-size: 12px;
  font-weight: 700;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}
.card-header-lite {
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.card-header-lite h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 800;
  color: #e0f2fe;
}
.playback-card {
  background: rgba(15, 23, 42, 0.8);
  display: flex;
  flex-direction: column;
}
.playback-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 12px;
}
.playback-ui {
  display: flex;
  align-items: center;
  gap: 25px;
}
.btn-play-large {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: rgba(56, 189, 248, 0.1);
  border: 2px solid #38bdf8;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 0 15px rgba(56, 189, 248, 0.2);
}
.btn-play-large:hover {
  background: #38bdf8;
  box-shadow: 0 0 25px rgba(56, 189, 248, 0.5);
  transform: scale(1.08);
}
.time-stamp-v2 {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  color: #94a3b8;
  font-size: 12px;
}
.pill {
  display: inline-block;
  padding: 2px 12px;
  font-size: 12px;
  font-weight: 500;
  color: #a5f3fc;
  background: linear-gradient(180deg, rgba(34, 211, 238, 0.15) 0%, rgba(34, 211, 238, 0.05) 100%);
  border: 1px solid rgba(34, 211, 238, 0.4);
  border-radius: 4px;
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.1);
  min-width: 70px;
  text-align: center;
  white-space: nowrap;
}
.stats-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.stats-total {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.stats-label {
  color: #94a3b8;
  font-size: 12px;
}
.stats-value {
  color: #e0f2fe;
  font-weight: 900;
  font-size: 22px;
}
.donut-mini-content {
  display: flex;
  gap: 12px;
  align-items: center;
}
.donut-mini-legend {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
  width: 100%;
  align-items: start;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(15, 23, 42, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 8px 10px;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  flex-shrink: 0;
}
.legend-text {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  color: #cbd5e1;
  font-size: 12px;
}
.legend-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 700;
}
.legend-value {
  color: #e0f2fe;
  font-weight: 900;
  flex-shrink: 0;
}
.ai-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}
.ai-slide {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ai-image {
  width: 100%;
  height: 150px;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
}
.ai-image img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.ai-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ai-title {
  color: #e2e8f0;
  font-weight: 800;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ai-sub {
  color: #94a3b8;
  font-size: 12px;
}
.ai-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.ai-btn {
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(255, 255, 255, 0.04);
  color: #e2e8f0;
  cursor: pointer;
  transition: all 0.2s ease;
}
.ai-btn.ghost {
  background: rgba(0, 212, 255, 0.08);
  border-color: rgba(0, 212, 255, 0.20);
}
.ai-btn:hover {
  color: #7dd3fc;
  border-color: rgba(0, 212, 255, 0.45);
}
.ai-count {
  color: #e0f2fe;
  font-size: 12px;
  font-weight: 800;
}
.ai-empty {
  padding: 18px 10px;
  text-align: center;
  color: #94a3b8;
  font-size: 12px;
  border: 1px dashed rgba(0, 212, 255, 0.18);
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.25);
}
.table-container {
  color: #fff;
  overflow: hidden;
}
.table-header {
  display: flex;
  gap: 12px;
  margin-bottom: 15px;
  color: #ffffff;
  font-size: 14px;
}
.th-box {
  flex: 1;
  background: linear-gradient(
      to bottom,
      rgba(0, 162, 255, 0.3) 0%,
      rgba(0, 80, 180, 0.1) 100%
  );
  border: 1px solid rgba(0, 191, 255, 0.6);
  box-shadow: inset 0 0 8px rgba(0, 191, 255, 0.3);
  color: #aaddff;
  text-align: center;
  padding: 5px 0;
  font-size: 12px;
  font-weight: bold;
}
.table-row {
  display: flex;
  gap: 12px;
  margin-bottom: 10px;
  font-size: 16px;
  transition: all 0.3s;
  align-items: center;
}
.table-row:hover {
  background: rgba(0, 191, 255, 0.1);
}
.col {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
}
.table-header, .table-row {
  display: flex;
  gap: 12px;
  width: 100%;
  table-layout: fixed;
}
.th-box, .col {
  flex: 1;
  width: 0;
  min-width: 0;
  text-align: center;
}
.dock-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.dock-card {
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid rgba(0, 191, 255, 0.15);
  border-radius: 8px;
  padding: 12px;
}
.dock-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-weight: bold;
  color: #e0f2fe;
  font-size: 14px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #64748b;
}
.status-dot.online {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.6);
}
.info-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 16px;
  padding-top: 4px;
}
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-width: 0;
}
.info-row .label {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
  margin-right: 4px;
}
.info-row .value {
  font-size: 13px;
  color: #f1f5f9;
  font-family: 'Inter', sans-serif;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.highlight {
  color: #fbbf24 !important;
}

@media (max-width: 1280px) {
  .dashboard-grid {
    grid-template-columns: 1fr 3fr 1fr;
  }
}
@media (max-width: 1120px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
  .bottom-media {
    grid-template-columns: 1fr;
    height: auto;
  }
}
</style>
