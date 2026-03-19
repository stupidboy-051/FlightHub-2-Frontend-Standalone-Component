<template>
  <div class="dashboard-premium">
    <!-- 页面头部 -->
    <div class="dashboard-header">
      <div class="header-icon">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
          <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
          <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
          <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="2"/>
        </svg>
      </div>
      <div class="header-text">
        <h1 class="page-title">无人机巡检主控台</h1>
        <p class="page-subtitle">实时监控与任务管理</p>
      </div>

      <div class="mode-switch">
        <button
          class="mode-tab"
          :class="{ active: currentMode === 'monitor' }"
          @click="setMode('monitor')"
        >
          无人机数字孪生控制台
        </button>
        <button
          class="mode-tab"
          :class="{ active: currentMode === 'analysis' }"
          @click="setMode('analysis')"
        >
          航线报警点展示台
        </button>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="dashboard-content">
      <!-- 左侧面板 - 机场列表 -->
      <div class="side-panel left-panel">
        <div class="panel-group" v-show="currentMode === 'monitor'">
          <div class="panel-section dock-panel">
            <div class="panel-header">
              <h3 class="panel-title">机场列表</h3>
              <button class="panel-action" @click="loadDockList" :disabled="dockLoading">
                {{ dockLoading ? '加载中...' : '刷新' }}
              </button>
            </div>
            <div class="panel-body dock-panel-body">
              <div v-if="dockLoading && docks.length === 0" class="panel-placeholder">正在加载机场...</div>
              <div v-else-if="dockLoadError" class="panel-placeholder error">{{ dockLoadError }}</div>
              <div v-else-if="docks.length === 0" class="panel-placeholder">暂无机场数据</div>
              <ul v-else class="dock-list">
                <li
                    v-for="dock in docks"
                    :key="dock.id || dock.dock_sn"
                    class="dock-item"
                    :class="{ active: isDockSelected(dock) }"
                    @click="handleDockSelected(dock)"
                >
                  <div class="dock-item-header">
                    <div class="dock-item-name">
                      <span class="status-dot" :class="{ online: dock.is_online }"></span>
                      <span class="dock-name">{{ getDockDisplayName(dock) }}</span>
                    </div>
                    <span class="dock-status" :class="{ online: dock.is_online }">
                      {{ dock.is_online ? '在线' : '离线' }}
                    </span>
                  </div>
                  <div class="dock-item-meta">
                    <span class="dock-sn">SN {{ dock.dock_sn || '--' }}</span>
                    <span v-if="dock.drone_sn" class="drone-sn">无人机 {{ dock.drone_sn }}</span>
                    <span class="drone-state" :class="{ working: isDroneWorking(dock) }">
                      {{ getDroneStateLabel(dock) }}
                    </span>
                  </div>
                </li>
              </ul>

              <div class="dock-latest">
                <div class="dock-latest-header">
                  <span class="dock-latest-title">{{ isDroneWorking(selectedDock) ? '飞行统计' : '最新位置' }}</span>
                  <div class="dock-latest-tags" v-if="selectedDock">
                    <span v-if="selectedDock?.drone_sn" class="dock-latest-sn">{{ selectedDock.drone_sn }}</span>
                    <span class="dock-latest-state" :class="{ working: isDroneWorking(selectedDock) }">
                      {{ getDroneStateLabel(selectedDock) }}
                    </span>
                  </div>
                </div>
                <div v-if="!selectedDock" class="panel-placeholder small">请选择机场</div>
                <div v-else-if="!selectedDock.drone_sn" class="panel-placeholder small">该机场未绑定无人机</div>
                <div v-else-if="isDroneWorking(selectedDock)" class="position-list">
                  <div class="position-item">
                    <div class="position-row">
                      <span class="position-label">飞行时长</span>
                      <span class="position-value">{{ formatFlightDuration() }}</span>
                    </div>
                    <div class="position-row">
                      <span class="position-label">飞行里程</span>
                      <span class="position-value">{{ formatFlightDistance() }}</span>
                    </div>
                  </div>
                </div>
                <div v-else-if="positionLoading && latestPositions.length === 0" class="panel-placeholder small">读取中...</div>
                <div v-else-if="latestPositions.length === 0" class="panel-placeholder small">暂无位置数据</div>
                <div v-else class="position-list">
                  <div
                      v-for="(pos, index) in latestPositions"
                      :key="pos.id || pos.timestamp || index"
                      class="position-item"
                  >
                    <div class="position-row">
                      <span class="position-label">时间</span>
                      <span class="position-value">{{ formatPositionTime(pos.timestamp || pos.created_at) }}</span>
                    </div>
                    <div class="position-row">
                      <span class="position-label">飞行时长</span>
                      <span class="position-value">{{ formatFlightDuration() }}</span>
                    </div>
                    <div class="position-row">
                      <span class="position-label">飞行里程</span>
                      <span class="position-value">{{ formatFlightDistance() }}</span>
                    </div>
                    <div class="position-row">
                      <span class="position-label">高度</span>
                      <span class="position-value">{{ formatPositionAltitude(pos) }}</span>
                    </div>
                    <div v-if="pos.battery_percent !== null && pos.battery_percent !== undefined" class="position-row">
                      <span class="position-label">电量</span>
                      <span class="position-value">{{ pos.battery_percent }}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="panel-section alarm-panel">
            <div class="panel-body alarm-panel-body">
              <AlarmPanel
                  v-if="monitorAlarmPanelVisible"
                  :alarms="getFilteredAlarms()"
                  :loading="loadingAlarms"
                  @refresh="handleAlarmRefresh"
                  @view-detail="handleViewAlarmDetail"
                  @process-alarm="handleProcessAlarm"
                  @locate-alarm="handleLocateAlarm"
              />
              <div v-else class="dji-placeholder">
                <p>{{ monitorAlarmPlaceholder }}</p>
              </div>
            </div>
          </div>
        </div>
        <div class="panel-group analysis-panel-group" v-show="currentMode === 'analysis'">
          <div class="panel-section analysis-filter-panel">
            <div class="panel-header">
              <h3 class="panel-title">检测类型</h3>
            </div>
            <div class="panel-body analysis-filter-body">
              <div class="detect-type-grid">
                <button
                  v-for="type in detectTypes"
                  :key="type.code"
                  class="detect-type-item"
                  :class="{ active: selectedDetectType?.code === type.code }"
                  @click="handleDetectTypeSelect(type)"
                >
                  <span class="detect-type-name">{{ type.name }}</span>
                  <span class="detect-type-code">{{ type.code }}</span>
                </button>
              </div>
            </div>
          </div>
          <div class="panel-section analysis-wayline-panel">
            <div class="panel-header">
              <h3 class="panel-title">航线列表</h3>
              <button
                class="panel-action"
                :disabled="analysisWaylineLoading || !selectedDetectType"
                @click="loadAnalysisWaylines"
              >
                {{ analysisWaylineLoading ? '加载中...' : '刷新' }}
              </button>
            </div>
            <div class="panel-body analysis-wayline-body">
              <div v-if="!selectedDetectType" class="panel-placeholder">请选择检测类型</div>
              <div v-else-if="analysisWaylineLoading && analysisWaylines.length === 0" class="panel-placeholder">正在加载航线...</div>
              <div v-else-if="analysisWaylineError" class="panel-placeholder error">{{ analysisWaylineError }}</div>
              <div v-else-if="analysisWaylines.length === 0" class="panel-placeholder">暂无航线数据</div>
              <ul v-else class="analysis-wayline-list">
                <li
                  v-for="wayline in analysisWaylines"
                  :key="wayline.id || wayline.wayline_id"
                  class="analysis-wayline-item"
                  :class="{ active: isAnalysisWaylineSelected(wayline) }"
                  @click="handleAnalysisWaylineSelected(wayline)"
                >
                  <div class="analysis-wayline-title">{{ wayline.name || wayline.wayline_name || '未命名航线' }}</div>
                  <div class="analysis-wayline-meta">
                    <span class="analysis-wayline-id">ID {{ wayline.wayline_id || wayline.id || '--' }}</span>
                    <span class="analysis-wayline-type">{{ getDetectTypeLabel(wayline.detect_type) }}</span>
                  </div>
                </li>
              </ul>
            </div>
          </div>
          <div class="panel-section analysis-alarm-panel">
            <div class="panel-body alarm-panel-body">
              <AlarmPanel
                v-if="selectedWayline"
                :alarms="getFilteredAlarms()"
                :loading="loadingAlarms"
                @refresh="handleAlarmRefresh"
                @view-detail="handleViewAlarmDetail"
                @process-alarm="handleProcessAlarm"
                @locate-alarm="handleLocateAlarm"
              />
              <div v-else class="dji-placeholder">
                <p>请先选择航线查看告警信息</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 中间区域 - 3D视图和直播 -->
      <div class="main-view">
        <div class="viewer-grid" :class="{ 'analysis-mode': currentMode === 'analysis' }">
        <!-- Cesium 3D视图 -->
        <div class="cesium-section">
          <div class="cesium-controls">
            <button class="control-btn" @click="focusOnModel">定位模型</button>
            <button class="control-btn" @click="focusOnWayline">定位航线</button>
            <button
              class="control-btn"
              :class="{ 'is-active': cameraMode === 'bird' }"
              @click="setCameraMode('bird')"
            >
              鸟瞰视角
            </button>
            <button
              class="control-btn"
              :class="{ 'is-active': cameraMode === 'third' }"
              @click="setCameraMode('third')"
            >
              第三人称
            </button>
            <button class="control-btn" @click="resetCameraView">重置视角</button>
            <button class="control-btn" @click="toggleGlobe">{{ globeVisible ? '隐藏地球' : '显示地球' }}</button>
          </div>
          <div class="protected-alarm-toast" :class="{ show: protectedAlarmToastVisible }">
            {{ protectedAlarmToastMessage }}
          </div>
          <!-- 直接使用ref作为Cesium容器 -->
          <div ref="cesiumContainer" class="cesium-container">
            <!-- 加载指示器 -->
            <div v-if="loading" class="loading-overlay">
              <div class="loading-content">
                <div class="loading-spinner"></div>
                <span>正在加载3D模型...</span>
              </div>
            </div>

            <!-- 错误信息 -->
            <div v-else-if="error" class="error-overlay">
              <div class="error-content">
                <div class="error-icon">⚠️</div>
                <p>{{ error }}</p>
              </div>
            </div>
            <div v-if="showCreateTaskButton" class="create-task-overlay">
              <button class="create-task-button" @click="openCreateTaskDialog">创建任务</button>
            </div>
          </div>
        </div>
        <!-- 实时监控面板（直播流播放器） -->
        <div class="panel-section live-monitor-section" v-show="currentMode === 'monitor'">
          <div class="monitor-header">
            <span class="monitor-title">实时直播</span>
            <div class="monitor-actions">
              <div class="stream-toggle">
                <button
                  class="stream-btn"
                  :class="{ active: liveStreamType === 'airport' }"
                  :disabled="!airportPushUrl"
                  @click="setLiveStreamType('airport')"
                >
                  机场直播
                </button>
                <button
                  class="stream-btn"
                  :class="{ active: liveStreamType === 'drone' }"
                  :disabled="!dronePushUrl"
                  @click="setLiveStreamType('drone')"
                >
                  无人机直播
                </button>
              </div>
              <div class="monitor-commands">
                <button
                  class="command-btn warning"
                  :disabled="!selectedDockSn || commandLoading.returnHome"
                  @click="handleReturnHome"
                >
                  {{ commandLoading.returnHome ? '返航中...' : '返航' }}
                </button>
                <button
                  class="command-btn default"
                  :disabled="!selectedDockSn || commandLoading.cancelReturn"
                  @click="handleCancelReturn"
                >
                  {{ commandLoading.cancelReturn ? '取消中...' : '取消返航' }}
                </button>
                <button
                  class="command-btn info"
                  :disabled="!selectedDockSn || commandLoading.pause"
                  @click="handlePause"
                >
                  {{ commandLoading.pause ? '暂停中...' : '暂停' }}
                </button>
                <button
                  class="command-btn success"
                  :disabled="!selectedDockSn || commandLoading.resume"
                  @click="handleResume"
                >
                  {{ commandLoading.resume ? '恢复中...' : '恢复' }}
                </button>
              </div>
            </div>
          </div>
          <div class="live-player-wrapper">
            <LiveStreamPlayer
                :key="`${liveStreamType}-${currentLiveStreamId}-${currentLiveStreamUrl}`"
                :stream-id="currentLiveStreamId"
                :stream-name="currentLiveStreamName"
                :stream-url-override="currentLiveStreamUrl"
                :zlm-server="zlmServerUrl"
                :auto-play="true"
            />
          </div>
        </div>
        </div>
      </div>

    </div>

    <CreateFlightTaskDialog
      v-model="showCreateTaskDialog"
      :sn="selectedDockSn"
      :dock-name="selectedDockName"
    />

    <ImagePreviewModal v-model="showAlarmImagePreview" :url="previewAlarmImageUrl" title="图片预览" />

    <!-- 告警详情弹窗 -->
    <div v-if="showAlarmDetail" class="modal-overlay" @click.self="showAlarmDetail = false">
      <div class="modal-premium">
        <div class="modal-header">
          <h3 class="modal-title">告警详情</h3>
          <button @click="showAlarmDetail = false" class="modal-close">×</button>
        </div>
        <div class="modal-body">
          <div v-if="currentAlarm" class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">告警ID</span>
              <span class="detail-value">{{ currentAlarm.id }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">告警类型</span>
              <span class="detail-value">{{ currentAlarm.category_details?.name || '未分类' }}</span>
            </div>
            <div class="detail-item full-width">
              <span class="detail-label">告警描述</span>
              <span class="detail-value">{{ currentAlarm.content }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">告警时间</span>
              <span class="detail-value">{{ formatAlarmTime(currentAlarm.created_at) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">告警位置</span>
              <span class="detail-value">坐标({{ currentAlarm.latitude }}, {{ currentAlarm.longitude }})</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">航线信息</span>
              <span class="detail-value">{{ currentAlarm.wayline?.name || currentAlarm.wayline_details?.name || '未知航线' }}</span>
            </div>
            <div v-if="currentAlarm.image_signed_url || currentAlarm.image_url" class="detail-item full-width">
              <span class="detail-label">告警图片</span>
              <div
                class="alarm-image"
                role="button"
                tabindex="0"
                @click="openAlarmImagePreview(currentAlarm.image_signed_url || currentAlarm.image_url)"
                @keydown.enter.prevent="openAlarmImagePreview(currentAlarm.image_signed_url || currentAlarm.image_url)"
                @keydown.space.prevent="openAlarmImagePreview(currentAlarm.image_signed_url || currentAlarm.image_url)"
              >
                <img
                  :src="currentAlarm.image_signed_url || currentAlarm.image_url"
                  alt="告警图片"
                  @error="handleImageError"
                />
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showAlarmDetail = false" class="modal-btn secondary-btn">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AlarmPanel from '../components/AlarmPanel.vue'
import LiveStreamPlayer from '../components/LiveStreamPlayer.vue'
import CreateFlightTaskDialog from '../components/CreateFlightTaskDialog.vue'
import ImagePreviewModal from '../components/ImagePreviewModal.vue'
import alarmApi from '../api/alarmApi.js'
import waylineApi from '../api/waylineApi.js'
import componentConfigApi from '../api/componentConfigApi.js'
import dockStatusApi from '../api/dockStatusApi.js'
import dronePositionApi from '../api/dronePositionApi.js'
import flightTaskInfoApi from '../api/flightTaskInfoApi.js'
import flightTaskApi from '../api/flightTaskApi.js'
import { ElMessage, ElMessageBox } from 'element-plus'

const CESIUM_TARGET_FRAME_RATE = 30
const CESIUM_MAX_RENDER_TIME_CHANGE = 1 / CESIUM_TARGET_FRAME_RATE
const DRONE_POSITION_PAGE_SIZE = 2
const DRONE_SAMPLE_RETENTION_SECONDS = 20
const DRONE_SAMPLE_PRUNE_INTERVAL_MS = 2000
const DRONE_TELEMETRY_ACTIVE_WINDOW_MS = 15000

let chaseScratchRotationMatrix = null
let chaseScratchTransform = null
let chaseScratchOffset = null
let chaseScratchDynamicOffset = null
let chaseScratchForwardOffset = null
let chaseScratchCameraPosition = null
let chaseScratchDirection = null
let chaseScratchUp = null
let chaseScratchForwardTarget = null
let chaseScratchPosition = null
let chaseScratchOrientation = null
let droneTrackingRenderTime = null
let droneTrackingPruneBefore = null
let droneTrackingTrimInterval = null
let droneTrackingHeadingPitchRoll = null
let droneTrackingOrientationSample = null
let droneTrackingHeadingTransform = null
let droneTrackingHeadingInverseTransform = null
let droneTrackingHeadingLocalPoint = null

function ensureChaseCameraScratch(Cesium) {
  if (!chaseScratchRotationMatrix) chaseScratchRotationMatrix = new Cesium.Matrix3()
  if (!chaseScratchTransform) chaseScratchTransform = new Cesium.Matrix4()
  if (!chaseScratchOffset) chaseScratchOffset = new Cesium.Cartesian3()
  if (!chaseScratchDynamicOffset) chaseScratchDynamicOffset = new Cesium.Cartesian3()
  if (!chaseScratchForwardOffset) chaseScratchForwardOffset = new Cesium.Cartesian3()
  if (!chaseScratchCameraPosition) chaseScratchCameraPosition = new Cesium.Cartesian3()
  if (!chaseScratchDirection) chaseScratchDirection = new Cesium.Cartesian3()
  if (!chaseScratchUp) chaseScratchUp = new Cesium.Cartesian3()
  if (!chaseScratchForwardTarget) chaseScratchForwardTarget = new Cesium.Cartesian3()
  if (!chaseScratchPosition) chaseScratchPosition = new Cesium.Cartesian3()
  if (!chaseScratchOrientation) chaseScratchOrientation = new Cesium.Quaternion()
}

function ensureDroneTrackingScratch(Cesium) {
  if (!droneTrackingRenderTime) droneTrackingRenderTime = new Cesium.JulianDate()
  if (!droneTrackingPruneBefore) droneTrackingPruneBefore = new Cesium.JulianDate()
  if (!droneTrackingTrimInterval) droneTrackingTrimInterval = new Cesium.TimeInterval()
  if (!droneTrackingHeadingPitchRoll) droneTrackingHeadingPitchRoll = new Cesium.HeadingPitchRoll()
  if (!droneTrackingOrientationSample) droneTrackingOrientationSample = new Cesium.Quaternion()
  if (!droneTrackingHeadingTransform) droneTrackingHeadingTransform = new Cesium.Matrix4()
  if (!droneTrackingHeadingInverseTransform) droneTrackingHeadingInverseTransform = new Cesium.Matrix4()
  if (!droneTrackingHeadingLocalPoint) droneTrackingHeadingLocalPoint = new Cesium.Cartesian3()
}

export default {
  name: 'DjiDashboard',
  components: {
    AlarmPanel,
    LiveStreamPlayer,
    CreateFlightTaskDialog,
    ImagePreviewModal
  },
  data() {
    return {
      detectTypes: [
        { name: '轨道', code: 'rail', icon: '🛤️', keywords: 'rail, 铁路, 轨道' },
        { name: '接触网', code: 'contactline', icon: '⚡', keywords: 'contactline, 接触网, catenary, overhead' },
        { name: '桥梁', code: 'bridge', icon: '🌉', keywords: 'bridge, 桥梁' },
        { name: '保护区', code: 'protected_area', icon: '🛡️', keywords: 'protected_area, 保护区' }
      ],
      currentMode: 'monitor',
      selectedDetectType: null,
      analysisWaylines: [],
      analysisWaylineLoading: false,
      analysisWaylineError: '',
      loading: false,
      error: '',
      globeVisible: true,
      cameraMode: '',
      imageryProviderType: 'aerial',
      fh2Loaded: false,
      selectedWayline: null,
      alarms: [],
      loadingAlarms: false,
      currentTaskInfo: null,
      isProtectedAreaTask: false,
      currentTaskUuid: '',
      protectedAlarmPollTimer: null,
      protectedAlarmFetchInFlight: false,
      protectedAlarmInitialized: false,
      protectedAlarmToastMessage: '',
      protectedAlarmToastVisible: false,
      protectedAlarmToastTimer: null,
      showAlarmDetail: false,
      currentAlarm: null,
      showAlarmImagePreview: false,
      previewAlarmImageUrl: '',
      fh2CheckTimer: null,
      componentConfig: null,
      zlmServerUrl: 'http://192.168.10.10',
      droneTranscodedUrl: 'http://192.168.10.10/live/drone_fixed.live.mp4',
      liveStreamType: 'airport',
      showCreateTaskDialog: false,
      commandLoading: {
        returnHome: false,
        cancelReturn: false,
        pause: false,
        resume: false
      },
      actionDetails: [],
      waylinePointSource: '',
      docks: [],
      dockLoading: false,
      dockLoadError: '',
      dockPollTimer: null,
      dockPollInFlight: false,
      dockPollQueued: false,
      selectedDock: null,
      latestPositions: [],
      latestTelemetryTimestampsByDevice: {},
      latestTelemetryPositionsByDevice: {},
      positionLoading: false,
      positionPollTimer: null,
      positionPollingDeviceSn: '',
      lastDroneTimestamp: null,
      lastDroneHeading: null,
      lastDronePosition: null,
      flightStartTimestamp: null,
      flightDurationMs: 0,
      flightDistanceKm: 0,
      flightLastPosition: null,
      flightLastUpdateTimestamp: null,
      flightStatsTaskUuid: '',
      flightStatsSaving: false,
      flightStatsSavedTaskUuid: '',
      flightStatsByDock: {},
      flightStatsPollTimer: null,
      flightStatsPollInFlight: false,
      flightStatsPollQueued: false,
      currentWaylineUuid: '',
      lastTaskInfoAttempt: 0,
      lastTaskInfoSn: '',
      taskInfoFetchInFlight: false,
      waylineFetchInFlight: false,
      chaseCameraListener: null
    }
  },
  computed: {
    selectedDockSn() {
      return this.selectedDock?.dock_sn || ''
    },
    selectedDockName() {
      return this.selectedDock?.display_name || this.selectedDock?.dock_name || this.selectedDock?.dock_sn || ''
    },
    showCreateTaskButton() {
      if (this.currentMode !== 'monitor') return false
      if (this.loading || this.error) return false
      if (!this.selectedDock || !this.selectedDockSn) return false
      return this.selectedDock.drone_in_dock === 1 || this.selectedDock.drone_in_dock === '1'
    },
    airportPushUrl() {
      return this.selectedDock?.airport_push || ''
    },
    dronePushUrl() {
      return this.selectedDock?.drone_push || ''
    },
    currentLiveStreamUrl() {
      return this.liveStreamType === 'drone' ? this.droneTranscodedUrl : this.airportPushUrl
    },
    currentLiveStreamName() {
      return this.liveStreamType === 'drone' ? '无人机直播' : '机场直播'
    },
    currentLiveStreamId() {
      if (this.liveStreamType === 'drone') {
        return this.selectedDock?.drone_sn || this.selectedDock?.dock_sn || ''
      }
      return this.selectedDock?.dock_sn || ''
    },
    monitorAlarmPanelVisible() {
      return this.currentMode === 'monitor' && this.isProtectedAreaTask && Boolean(this.currentTaskUuid)
    },
    monitorAlarmPlaceholder() {
      if (!this.selectedDock) return '请选择机场'
      if (!this.currentTaskInfo) return '暂无任务信息'
      if (!this.isProtectedAreaTask) return '当前任务非保护区，不显示告警信息'
      if (!this.currentTaskUuid) return '暂无任务信息'
      return '暂无告警信息'
    }
  },
  watch: {
    selectedDock: {
      handler(newDock, oldDock) {
        if (!newDock || !oldDock) return
        const newKey = newDock.dock_sn || newDock.id
        const oldKey = oldDock.dock_sn || oldDock.id
        if (!newKey || newKey !== oldKey) return
        const wasInDock = oldDock.drone_in_dock === 1 || oldDock.drone_in_dock === '1'
        const nowWorking = newDock.drone_in_dock === 0 || newDock.drone_in_dock === '0'
        if (wasInDock && nowWorking) {
          this.resetFlightStats(newDock)
          this.autoStartThirdPersonForTaskDock(newDock)
          if (this.currentMode === 'monitor') {
            const dockSn = newDock.dock_sn
            if (!dockSn) return
            this.lastTaskInfoSn = dockSn
            this.lastTaskInfoAttempt = Date.now()
            void this.syncWaylineFromTaskInfo(dockSn)
          }
        }
        const wasWorking = oldDock.drone_in_dock === 0 || oldDock.drone_in_dock === '0'
        const nowInDock = newDock.drone_in_dock === 1 || newDock.drone_in_dock === '1'
        if (wasWorking && nowInDock) {
          const finalize = this.finalizeFlightStats(newDock)
          if (finalize && typeof finalize.then === 'function') {
            finalize.then(success => {
              if (success) this.resetFlightStats(newDock)
            })
          }
        }
      }
    },
    currentTaskUuid(newVal, oldVal) {
      if (!newVal || newVal === oldVal) return
      const dock = this.selectedDock
      if (this.flightStatsTaskUuid && this.flightStatsTaskUuid !== newVal) {
        this.resetFlightStats(dock)
      }
      const key = this.getFlightStatsKey(dock)
      if (!key) return
      const snapshot = this.flightStatsByDock[key] || this.buildFlightStatsSnapshot()
      snapshot.flightStatsTaskUuid = newVal
      this.flightStatsByDock[key] = snapshot
      if (this.isDockSelected(dock)) {
        this.applyFlightStatsSnapshot(snapshot)
      }
    }
  },
  created() {
    this.cesiumLib = null
    this.viewer = null
    this.tilesets = []
    this.waylineEntity = null
    this.waylinePointEntities = []
    this.droneEntity = null
    this.dronePositionProperty = null
    this.droneOrientationProperty = null
    this.lastDroneCartesian = null
    this.invertedTriangleImage = null
    this.alertTriangleIconCache = {}
    this.alarmEntities = []
    this.alarmEntityMap = new Map()
    this.protectedAlarmIdSet = new Set()
    this.actionDetailEntities = []
    this.pickHandler = null
    this.lastDroneSamplePruneTimestamp = null
    this.latestPositionsCacheKey = ''
  },
  async mounted() {
    this.checkFh2Availability()
    this.initSelectedWaylineFromRoute()
    this.loadDockList()
    this.startDockPolling()
    this.startFlightStatsPolling()

    await this.$nextTick()
    await this.loadComponentConfig()
    await this.initCesium()
  },
  beforeUnmount() {
    if (this.fh2CheckTimer) {
      clearTimeout(this.fh2CheckTimer)
      this.fh2CheckTimer = null
    }
    if (this.viewer && this.chaseCameraListener) {
      this.viewer.scene.preUpdate.removeEventListener(this.chaseCameraListener)
    }
    if (this.viewer) {
      this.viewer.destroy()
      this.viewer = null
    }
    if (this.pickHandler) {
      this.pickHandler.destroy()
      this.pickHandler = null
    }
    if (this.dockPollTimer) {
      clearInterval(this.dockPollTimer)
      this.dockPollTimer = null
    }
    if (this.flightStatsPollTimer) {
      clearInterval(this.flightStatsPollTimer)
      this.flightStatsPollTimer = null
    }
    if (this.positionPollTimer) {
      clearInterval(this.positionPollTimer)
      this.positionPollTimer = null
    }
    if (this.protectedAlarmPollTimer) {
      clearInterval(this.protectedAlarmPollTimer)
      this.protectedAlarmPollTimer = null
    }
    if (this.protectedAlarmToastTimer) {
      clearTimeout(this.protectedAlarmToastTimer)
      this.protectedAlarmToastTimer = null
    }
  },
  methods: {
    openAlarmImagePreview(url) {
      if (!url) return
      this.previewAlarmImageUrl = url
      this.showAlarmImagePreview = true
    },
    checkFh2Availability() {
      if (typeof window !== 'undefined' && window.FH2) {
        this.fh2Loaded = true
        this.fh2CheckTimer = null
        return
      }
      this.fh2Loaded = false
      this.fh2CheckTimer = setTimeout(() => {
        this.checkFh2Availability()
      }, 1000)
    },
    getAppBaseUrl() {
      const baseUrl = process.env.BASE_URL || '/'
      if (!baseUrl) return '/'
      return baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`
    },
    resolveAssetPath(relativePath = '') {
      const normalizedPath = String(relativePath || '').replace(/^\/+/, '')
      return `${this.getAppBaseUrl()}${normalizedPath}`
    },
    getSiteModelUrls() {
      return [
        'models/site_model/part1_terrain/tileset.json',
        'models/site_model/part2_poles/tileset.json',
        'models/site_model/part3_lines/tileset.json'
      ].map(path => this.resolveAssetPath(path))
    },
    waitForNextFrame() {
      return new Promise(resolve => {
        if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
          window.requestAnimationFrame(() => resolve())
          return
        }
        setTimeout(resolve, 16)
      })
    },
    setFallbackCameraView(Cesium) {
      if (!this.viewer) return
      this.viewer.camera.setView({
        destination: Cesium.Cartesian3.fromDegrees(116.39, 39.90, 4000),
        orientation: {
          heading: 0,
          pitch: Cesium.Math.toRadians(-90),
          roll: 0
        }
      })
    },
async loadSiteModelTilesets(Cesium) {
      if (!this.viewer) return []

      const modelUrls = this.getSiteModelUrls()
      const loadPromises = modelUrls.map(async url => {
        try {
          return await Cesium.Cesium3DTileset.fromUrl(url, {
            // ---------------- 性能优化参数开始 ----------------
            
            // 1. 调大屏幕空间误差 (SSE)
            // 默认值是 16。调大这个值（如 32 或 48），Cesium 会更倾向于渲染低层级（较模糊）的瓦片，从而大幅减少 Draw Calls 和渲染压力。
            // 如果你觉得 32 还是卡，可以改为 48 或 64；如果觉得太模糊，可以改回 24。
            maximumScreenSpaceError: 32, 
            
            // 2. 提高最大内存使用量 (单位 MB)
            // 默认值是 512。因为你现在有 3 个模型，内存很容易爆满导致频繁触发垃圾回收（掉帧）。
            // 提高到 1024 或 2048，可以允许显存缓存更多瓦片，减少重复加载的卡顿。
            maximumMemoryUsage: 1024,    
            
            // 3. 开启动态屏幕空间误差
            // 开启后，当相机快速移动或者视距较远时，会自动降低模型精度，防止拖拽视角时卡死。
            dynamicScreenSpaceError: true, 
            dynamicScreenSpaceErrorDensity: 0.00278,
            dynamicScreenSpaceErrorFactor: 4.0,
            dynamicScreenSpaceErrorHeightFalloff: 0.25,
            
            // 4. 原有的优化参数保持不变
            skipLevelOfDetail: true,
            cullWithChildrenBounds: true
            
            // ---------------- 性能优化参数结束 ----------------
          })
        } catch (error) {
          throw new Error(`模型加载失败: ${url}，${error.message}`)
        }
      })

      const tilesets = await Promise.all(loadPromises)
      if (!this.viewer) return tilesets

      tilesets.forEach(tileset => this.viewer.scene.primitives.add(tileset))

      const mainTileset = tilesets[0]
      if (!mainTileset) {
        this.tilesets = tilesets
        return tilesets
      }

      await mainTileset.readyPromise
      if (!mainTileset.boundingSphere) {
        this.tilesets = tilesets
        return tilesets
      }

      const heightOffset = -40.2
      const boundingSphere = mainTileset.boundingSphere
      const cartographic = Cesium.Cartographic.fromCartesian(boundingSphere.center)
      const surface = Cesium.Cartesian3.fromRadians(cartographic.longitude, cartographic.latitude, 0.0)
      const offset = Cesium.Cartesian3.fromRadians(cartographic.longitude, cartographic.latitude, heightOffset)
      const translation = Cesium.Cartesian3.subtract(offset, surface, new Cesium.Cartesian3())
      const modelMatrix = Cesium.Matrix4.fromTranslation(translation)

      tilesets.forEach(tileset => {
        tileset.modelMatrix = modelMatrix
      })

      this.tilesets = tilesets
      this.viewer.scene.requestRender()
      await this.waitForNextFrame()
      return tilesets
    },
    async initCesium() {
      if (this.viewer) return

      this.loading = true
      this.error = ''
      try {
        const Cesium = await import('cesium')
        this.cesiumLib = Cesium
        const tokenFromConfig = this.componentConfig?.cesium_ion_token || this.componentConfig?.cesiumIonToken
        Cesium.Ion.defaultAccessToken =
          tokenFromConfig || process.env.VUE_APP_CESIUM_ION_TOKEN || Cesium.Ion.defaultAccessToken || ''

        const container = this.$refs.cesiumContainer
        if (!container) throw new Error('找不到 Cesium 容器')

        this.viewer = new Cesium.Viewer(container, {
          sceneMode: Cesium.SceneMode.SCENE3D,
          scene3DOnly: true,
          animation: false,
          baseLayerPicker: false,
          fullscreenButton: false,
          vrButton: false,
          geocoder: false,
          homeButton: false,
          infoBox: false,
          sceneModePicker: false,
          selectionIndicator: false,
          timeline: false,
          navigationHelpButton: false,
          creditContainer: document.createElement('div'),
          orderIndependentTranslucency: false,
          requestRenderMode: true,
          maximumRenderTimeChange: CESIUM_MAX_RENDER_TIME_CHANGE,
          targetFrameRate: CESIUM_TARGET_FRAME_RATE,
          msaaSamples: 1,
          useBrowserRecommendedResolution: true
        })

        this.viewer.scene.globe.depthTestAgainstTerrain = false
        this.viewer.scene.screenSpaceCameraController.enableCollisionDetection = false
        this.viewer.scene.globe.show = this.globeVisible
        this.viewer.targetFrameRate = CESIUM_TARGET_FRAME_RATE

        await this.setupImageryLayers(Cesium)
        this.tuneCameraControls(this.viewer.scene.screenSpaceCameraController)
        this.setupPickHandler(Cesium)
        this.viewer.resize()

        try {
          await this.loadSiteModelTilesets(Cesium)
          const focused = await this.focusOnModel()
          if (!focused) {
            this.setFallbackCameraView(Cesium)
          }
        } catch (tilesetError) {
          console.error('加载3D Tiles模型失败:', tilesetError)
          this.setFallbackCameraView(Cesium)
        }
      } catch (err) {
        this.error = '初始化Cesium失败: ' + err.message
        console.error('Cesium initialization error:', err)
      } finally {
        this.loading = false
      }
    },

    async applyWaylineSelection(wayline) {
      if (!wayline?.id) return
      if (this.selectedWayline?.id === wayline.id) return
      console.log('[Dashboard] 航线更新:', wayline?.name, wayline?.id)
      this.selectedWayline = wayline

      // 1. 先加载告警
      if (this.currentMode === 'analysis') {
        this.fetchAlarmsByWayline(wayline.id)
      } else if (!this.isProtectedAreaTask) {
        this.clearAlarmData()
      }

      // 2. 获取动作详情 (用于蓝点/航线兜底)
      let validPoints = []
      try {
        const res = await waylineApi.getWaylineActionDetails(wayline.id)
        if (!this.selectedWayline || String(this.selectedWayline.id) !== String(wayline.id)) {
          return
        }
        this.actionDetails = Array.isArray(res?.action_details) ? res.action_details : []
        validPoints = this.actionDetails

        this.plotActionDetailMarkers(this.actionDetails)
        console.log('[Debug] 成功获取动作详情点，数量:', validPoints.length)
      } catch (e) {
        console.warn('[Debug] 获取动作详情失败', e)
      }

      // 3. 使用当前航线绘制
      await this.ensureWaylineWithPoints(wayline, validPoints)
    },

// 核心数据解析：增加去重逻辑，防止 NaN
// 修改函数签名，增加 fallbackData 参数
    async ensureWaylineWithPoints(wayline, fallbackData = []) {
      if (!this.selectedWayline || String(this.selectedWayline.id) !== String(wayline?.id)) {
        return
      }
      console.log('----------------------------------------------------');
      console.log('[Debug] 开始构建航线，WaylineID:', wayline?.id);

      let finalWayline = { ...wayline };
      let sourceList = [];
      let pointSource = '';

      // 1. 真实航点：仅使用 WaylineFingerprint.action_details
      if (fallbackData.length > 0) {
        console.log('[Debug] 来源: WaylineFingerprint.action_details (数量: ' + fallbackData.length + ')');
        sourceList = fallbackData;
        pointSource = 'actionDetails';
      }

      // 2. 如果还是空的，那就彻底没戏了
      if (sourceList.length === 0) {
        console.error('[Error] 未拿到 WaylineFingerprint.action_details 数据。');
        alert(`航线 ID ${wayline.id} 没有真实航点数据，无法绘制。`);
        return;
      }

      // 4. 解析数据 (打印第一条数据，帮你确认字段名)
      console.log('[Debug] 准备解析的第一条数据样本:', JSON.stringify(sourceList[0]));

      const mappedPoints = [];
      sourceList.forEach((p, i) => {
        const payload = this.getWaylinePointPayload(p);

        if (Number.isFinite(payload.longitude) && Number.isFinite(payload.latitude)) {
          mappedPoints.push(payload);
        } else {
          if (i === 0) console.warn('[Debug] 第一条数据解析失败，字段不匹配:', p);
        }
      });

      console.log(`[Debug] 解析完成，有效坐标点: ${mappedPoints.length} 个`);

      const mergeThresholdMeters = 0.5;
      const uniquePoints = this.mergeCloseWaypoints(mappedPoints, mergeThresholdMeters);
      if (uniquePoints.length !== mappedPoints.length) {
        console.log(`[Debug] 航点去重: ${mappedPoints.length} -> ${uniquePoints.length}`);
      }

      if (uniquePoints.length > 1) {
        finalWayline.waypoints = uniquePoints;
        this.waylinePointSource = pointSource || 'actionDetails';
        // 确保 Vue 响应式更新
        this.selectedWayline = finalWayline;

        // 延迟执行绘制，确保 DOM/Viewer 稳定
        setTimeout(() => {
          this.drawWaylineOnMap(finalWayline);
        }, 200);
      } else {
        alert('解析后有效点数不足 2 个，无法连线');
      }
    },
    drawWaylineOnMap(wayline) {
      if (!this.viewer || !wayline?.waypoints?.length) return;
      const Cesium = this.cesiumLib || window.Cesium;

      // 清理旧实体
      if (this.waylineEntity) {
        this.viewer.entities.remove(this.waylineEntity);
        this.waylineEntity = null;
      }
      if (this.waylinePointEntities.length) {
        this.waylinePointEntities.forEach(entity => this.viewer.entities.remove(entity));
        this.waylinePointEntities = [];
      }

      // 1. 提取坐标
      const positions = wayline.waypoints.map(p =>
          Cesium.Cartesian3.fromDegrees(p.longitude, p.latitude, p.altitude)
      );

      // 2. 绘制航线（轻微辉光 + 清晰主线）
      this.waylineEntity = this.viewer.entities.add({
        name: wayline.name || '航线',
        polyline: {
          positions: positions,
          width: 10,
          material: new Cesium.PolylineGlowMaterialProperty({
            glowPower: 0.15,
            color: Cesium.Color.CYAN.withAlpha(0.85)
          }),
          clampToGround: false,
          arcType: Cesium.ArcType.NONE,
          // 被地形遮挡时也保留可见性
          depthFailMaterial: new Cesium.PolylineGlowMaterialProperty({
            glowPower: 0.1,
            color: Cesium.Color.CYAN.withAlpha(0.45)
          })
        }
      });

      // 3. 绘制航点（保持原样，这部分你已经能看到了）
      if (this.waylinePointSource !== 'actionDetails') {
        positions.forEach((pos) => {
          const pointEntity = this.viewer.entities.add({
            position: pos,
            point: {
              pixelSize: 8,
              color: Cesium.Color.RED,
              outlineColor: Cesium.Color.WHITE,
              outlineWidth: 2,
              disableDepthTestDistance: Number.POSITIVE_INFINITY // 确保点永远在最上层
            }
          });
          this.waylinePointEntities.push(pointEntity);
        });
      }

      // 4. 视角飞向整个航线范围
      if (this.currentMode === 'analysis') {
        this.focusOnWayline();
      } else {
        const sphere = Cesium.BoundingSphere.fromPoints(positions);
        this.viewer.camera.flyToBoundingSphere(sphere, {
          duration: 1.0,
          offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-30), sphere.radius * 2.5)
        });
      }
    },

    // 安全的计算朝向函数，处理重合点
    calculateHeading(p1, p2) {
      const Cesium = this.cesiumLib || window.Cesium;
      ensureDroneTrackingScratch(Cesium)
      // 如果点太近，直接返回 0，防止数学错误
      if (Cesium.Cartesian3.distance(p1, p2) < 1.0) {
        return 0;
      }

      // 建立局部坐标系 ENU (East-North-Up)
      const transform = Cesium.Transforms.eastNorthUpToFixedFrame(p1, undefined, droneTrackingHeadingTransform);
      const invTransform = Cesium.Matrix4.inverse(transform, droneTrackingHeadingInverseTransform);

      // 将 p2 转到 p1 的局部坐标系
      const p2Local = Cesium.Matrix4.multiplyByPoint(invTransform, p2, droneTrackingHeadingLocalPoint);

      // 计算角度: atan2(y, x) 是相对东方向的逆时针角度
      // Cesium Heading 是相对北方向的顺时针角度
      // 数学转换:
      // East(X) -> 0 rad (Math) -> 90 deg (Cesium)
      // North(Y) -> 90 deg (Math) -> 0 deg (Cesium)
      // 简易公式: angle = atan2(x, y) (注意 x,y 顺序与标准 atan2 相反) 即可得到顺时针相对Y轴的角度吗？
      // Cesium 标准做法：
      let angle = Math.atan2(p2Local.y, p2Local.x);
      // angle 是与X轴(东)的夹角。
      // 我们需要 Heading (与北的夹角)。
      // Heading = 90度 - angle (弧度制: PI/2 - angle)
      let heading = Cesium.Math.PI_OVER_TWO - angle;

      return heading;
    },
    enableChaseCamera(entity, distance = 80, height = 30) {
      const Cesium = this.cesiumLib || window.Cesium;
      if (!Cesium || !this.viewer) return;
      ensureChaseCameraScratch(Cesium)

      // 1. 清理旧的监听器，防止重复绑定导致相机乱晃
      if (this.chaseCameraListener) {
        this.viewer.scene.preUpdate.removeEventListener(this.chaseCameraListener);
        this.chaseCameraListener = null;
      }

      // 2. 定义每帧刷新逻辑
      this.chaseCameraListener = () => {
        // 只有无人机存在且在显示时才跟随
        if (!this.viewer || !entity || !entity.show) return;

        const time = this.viewer.clock?.currentTime;
        if (!time) return;

        // 获取当前时刻的位置和朝向
        const position = entity.position?.getValue(time, chaseScratchPosition);
        const orientation = entity.orientation?.getValue(time, chaseScratchOrientation);

        if (position) {
          // A. 计算模型变换矩阵 (Model Matrix)
          // 这个矩阵代表了无人机当前的坐标系：原点在无人机中心，轴向跟随无人机旋转
          const transform = orientation
            ? Cesium.Matrix4.fromRotationTranslation(
              Cesium.Matrix3.fromQuaternion(orientation, chaseScratchRotationMatrix),
              position,
              chaseScratchTransform
            )
            : Cesium.Transforms.eastNorthUpToFixedFrame(position, undefined, chaseScratchTransform);

          // B. 定义相机在【局部坐标系】中的位置
          // 假设：X轴是正前方，Y轴是右侧，Z轴是上方
          // 我们要放在：后方 (-X) 且 上方 (+Z)
          // 注意：不同模型的坐标系可能不同。如果发现相机在侧面，请调整这里的 x/y 值
          // 💡 魔法抵消：为了不让相机跟着歪，这里要反向补偿！
          // 如果下面模型补偿了 -45 度，这里就填正的 45。如果不准，可以试试 135 或 -135。
          const cameraFixAngle = Cesium.Math.toRadians(-20);

          const offsetX = -distance * Math.cos(cameraFixAngle);
          const offsetY = -distance * Math.sin(cameraFixAngle);
          const offset = Cesium.Cartesian3.fromElements(offsetX, offsetY, height, chaseScratchOffset);

          // C. 将局部偏移量转换为世界坐标
          const cameraPosition = Cesium.Matrix4.multiplyByPoint(
            transform,
            offset,
            chaseScratchCameraPosition
          );

          // D. 设置相机
          // destination: 相机位置 (世界坐标)
          // orientation: 让相机看向无人机中心 (direction)
          const direction = Cesium.Cartesian3.subtract(
            position,
            cameraPosition,
            chaseScratchDirection
          );
          Cesium.Cartesian3.normalize(direction, direction);

          // 设置相机，保持 Up 轴大致向上 (避免翻滚)
          this.viewer.camera.setView({
            destination: cameraPosition,
            orientation: {
              direction,
              up: Cesium.Cartesian3.normalize(position, chaseScratchUp) // 使用地心向量作为Up，保持地球水平
            }
          });
        }
      };

      // 3. 绑定到场景更新事件 (每一帧渲染前执行)
      this.viewer.scene.preUpdate.addEventListener(this.chaseCameraListener);
    },
    // --- 辅助方法 ---
    enableDynamicChaseCamera(entity, offsetProperty) {
      const Cesium = this.cesiumLib || window.Cesium;
      if (!Cesium || !this.viewer) return;
      ensureChaseCameraScratch(Cesium)

      if (this.chaseCameraListener) {
        this.viewer.scene.preUpdate.removeEventListener(this.chaseCameraListener);
        this.chaseCameraListener = null;
      }

      this.chaseCameraListener = () => {
        if (!this.viewer || !entity || !entity.show) return;

        const time = this.viewer.clock?.currentTime;
        if (!time) return;

        // 1. 获取当前时刻的各项属性
        const position = entity.position?.getValue(time, chaseScratchPosition);
        const orientation = entity.orientation?.getValue(time, chaseScratchOrientation);
        // 【关键】获取当前时刻应该有的相机偏移量 (是远是近，由时间轴决定)
        const currentOffset = offsetProperty?.getValue(time, chaseScratchDynamicOffset);

        if (position && orientation && currentOffset) {
          const transform = Cesium.Matrix4.fromRotationTranslation(
            Cesium.Matrix3.fromQuaternion(orientation, chaseScratchRotationMatrix),
            position,
            chaseScratchTransform
          );

          // 2. 应用动态偏移量
          const cameraPosition = Cesium.Matrix4.multiplyByPoint(
            transform,
            currentOffset,
            chaseScratchCameraPosition
          );

          // 3. 计算朝向 (相机始终盯着无人机中心)
          // 如果是特写模式(Zoomed)，相机其实是在无人机前方，回头看无人机可能会穿模
          // 所以这里做一个微调：
          // 如果 currentOffset.x > 0 (在机头前方)，我们就让相机看向前方无限远，模拟第一人称
          // 如果 currentOffset.x < 0 (在机尾后方)，我们就看向无人机
          let direction;

          if (currentOffset.x > 0) {
            // 模拟第一人称：方向就是无人机的正前方
            // 简单做法：取 transform 的 X 轴方向
            const forwardOffset = Cesium.Cartesian3.fromElements(100, 0, 0, chaseScratchForwardOffset)
            const forwardTarget = Cesium.Matrix4.multiplyByPoint(
              transform,
              forwardOffset,
              chaseScratchForwardTarget
            );
            direction = Cesium.Cartesian3.subtract(forwardTarget, cameraPosition, chaseScratchDirection);
          } else {
            // 模拟第三人称：看向无人机
            direction = Cesium.Cartesian3.subtract(position, cameraPosition, chaseScratchDirection);
          }

          Cesium.Cartesian3.normalize(direction, direction);

          this.viewer.camera.setView({
            destination: cameraPosition,
            orientation: {
              direction,
              up: Cesium.Cartesian3.normalize(position, chaseScratchUp)
            }
          });
        }
      };

      this.viewer.scene.preUpdate.addEventListener(this.chaseCameraListener);
    },
    setCameraMode(mode) {
      if (!mode) return;
      this.cameraMode = mode;
      this.applyCameraMode(true);
    },
    autoStartThirdPersonForTaskDock(dock) {
      if (!dock || !this.isDroneWorking(dock)) return
      if (this.cameraMode === 'third') return
      this.setCameraMode('third')
    },
    applyCameraMode(force = false) {
      if (!this.viewer) return;
      const Cesium = this.cesiumLib || window.Cesium;
      if (!Cesium) return;

      if (this.cameraMode === 'third') {
        if ((force || !this.chaseCameraListener) && this.droneEntity) {
          this.enableChaseCamera(this.droneEntity, 80, 30);
        }
        return;
      }

      if (this.chaseCameraListener) {
        this.viewer.scene.preUpdate.removeEventListener(this.chaseCameraListener);
        this.chaseCameraListener = null;
      }
      this.viewer.trackedEntity = undefined;

      if (this.droneEntity?.position) {
        const time = this.viewer?.clock?.currentTime || Cesium.JulianDate.now();
        const position = this.droneEntity.position.getValue(time);
        if (position) {
          this.updateBirdCameraFromCartesian(position);
        }
      }
    },
    updateBirdCameraFromCartesian(cartesian, heightOffset = 200) {
      if (!this.viewer || !cartesian) return;
      const Cesium = this.cesiumLib || window.Cesium;
      if (!Cesium) return;
      const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
      if (!cartographic) return;
      const lon = Cesium.Math.toDegrees(cartographic.longitude);
      const lat = Cesium.Math.toDegrees(cartographic.latitude);
      const alt = cartographic.height;
      const safeHeight = Number.isFinite(alt) ? Math.max(alt + heightOffset, 200) : 300;
      this.viewer.camera.setView({
        destination: Cesium.Cartesian3.fromDegrees(lon, lat, safeHeight),
        orientation: {
          heading: 0,
          pitch: Cesium.Math.toRadians(-90),
          roll: 0
        }
      });
    },
    updateBirdCameraFromCoords(longitude, latitude, altitude, heightOffset = 200) {
      if (!this.viewer) return;
      const Cesium = this.cesiumLib || window.Cesium;
      if (!Cesium) return;
      if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return;
      const safeHeight = Number.isFinite(altitude) ? Math.max(altitude + heightOffset, 200) : 300;
      this.viewer.camera.setView({
        destination: Cesium.Cartesian3.fromDegrees(longitude, latitude, safeHeight),
        orientation: {
          heading: 0,
          pitch: Cesium.Math.toRadians(-90),
          roll: 0
        }
      });
    },
    async focusOnModel() {
      if (!this.viewer || !this.tilesets || this.tilesets.length === 0) return false

      const Cesium = this.cesiumLib || window.Cesium
      if (!Cesium) return false

      const mainTileset = this.tilesets[0]
      if (!mainTileset) return false

      try {
        if (mainTileset.readyPromise) {
          await mainTileset.readyPromise
        }
      } catch (err) {
        console.warn('等待模型就绪失败', err)
        return false
      }

      if (!mainTileset.boundingSphere) return false

      const range = Math.max(mainTileset.boundingSphere.radius * 2.5, 500)

      try {
        this.viewer.scene.requestRender()
        await this.waitForNextFrame()
        await this.viewer.flyTo(mainTileset, {
          duration: 1.2,
          offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-30), range)
        })
        return true
      } catch (err) {
        console.warn('飞到模型失败', err)
        return false
      }
    },

    focusOnWayline() {
      if (!this.viewer || !this.waylineEntity?.polyline?.positions) return;
      const Cesium = this.cesiumLib || window.Cesium;
      if (!Cesium) return;
      const time = this.viewer.clock?.currentTime || Cesium.JulianDate.now();
      const positions = this.waylineEntity.polyline.positions.getValue(time);
      if (!positions || positions.length === 0) return;
      const sphere = Cesium.BoundingSphere.fromPoints(positions);
      this.viewer.camera.flyToBoundingSphere(sphere, {
        duration: 1.2,
        offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-30), sphere.radius * 2.5)
      });
    },

    resetCameraView() {
      if (this.viewer) {
        const Cesium = this.cesiumLib || window.Cesium;
        if (!Cesium) return;

        if (this.chaseCameraListener) {
          this.viewer.scene.preUpdate.removeEventListener(this.chaseCameraListener);
          this.chaseCameraListener = null;
        }
        this.viewer.trackedEntity = undefined;

        if (this.waylineEntity?.polyline?.positions) {
          const positions = this.waylineEntity.polyline.positions.getValue(new Cesium.JulianDate());
          if (positions?.[0]) {
            this.viewer.camera.flyTo({
              destination: positions[0],
              orientation: {
                heading: Cesium.Math.toRadians(0),
                pitch: Cesium.Math.toRadians(-45),
                roll: 0.0
              },
              duration: 1.2
            });
            return;
          }
        }
      }
    },

    toggleGlobe() {
      this.globeVisible = !this.globeVisible;
      if (this.viewer) {
        this.viewer.scene.globe.show = this.globeVisible;
      }
    },
    setMode(mode) {
      if (!mode || this.currentMode === mode) return;
      this.clearDigitalTwinAndAlarms();
      this.currentMode = mode;
      if (this.viewer) {
        this.viewer.trackedEntity = undefined;
      }
      if (mode === 'analysis') {
        return;
      }
      this.applyCameraMode(true);
    },
    setDroneVisibility(visible) {
      if (this.droneEntity) {
        this.droneEntity.show = Boolean(visible);
      }
    },
    setActionDetailVisibility(visible) {
      if (!this.actionDetailEntities.length) return;
      const show = Boolean(visible);
      this.actionDetailEntities.forEach(entity => {
        entity.show = show;
      });
    },
    handleDetectTypeSelect(type) {
      if (!type) return;
      if (this.selectedDetectType?.code === type.code) return;
      this.selectedDetectType = type;
      this.analysisWaylines = [];
      this.analysisWaylineError = '';
      this.loadAnalysisWaylines();
    },
    async loadAnalysisWaylines() {
      if (!this.selectedDetectType?.code || this.analysisWaylineLoading) return;
      const detectTypeCode = this.selectedDetectType.code;
      this.analysisWaylineLoading = true;
      this.analysisWaylineError = '';
      try {
        let page = 1;
        let hasNext = true;
        const allWaylines = [];
        const seen = new Set();

        while (hasNext) {
          const response = await waylineApi.getWaylines({
            detect_type: detectTypeCode,
            page
          });
          const list = Array.isArray(response) ? response : (response.results || response.data || []);
          if (!Array.isArray(list)) break;

          list.forEach(item => {
            const key = item?.id ? `id:${item.id}` : `wayline:${item?.wayline_id || item?.name || ''}`;
            if (!key || seen.has(key)) return;
            seen.add(key);
            allWaylines.push(item);
          });

          if (Array.isArray(response) || !response?.next) {
            hasNext = false;
          } else {
            page += 1;
          }
        }

        if (this.selectedDetectType?.code !== detectTypeCode) return;
        this.analysisWaylines = allWaylines;
        console.log('[Dashboard] 航线列表加载完成:', detectTypeCode, this.analysisWaylines.length);
      } catch (error) {
        console.error('获取航线列表失败:', error);
        this.analysisWaylines = [];
        this.analysisWaylineError = '航线列表加载失败';
      } finally {
        this.analysisWaylineLoading = false;
      }
    },
    async handleAnalysisWaylineSelected(wayline) {
      if (!wayline) return;
      let target = wayline;
      if (!target.id && target.wayline_id) {
        try {
          const response = await waylineApi.getWaylines({ wayline_id: target.wayline_id });
          const list = Array.isArray(response) ? response : (response.results || response.data || []);
          if (list.length) {
            target = list[0];
          }
        } catch (error) {
          console.warn('获取航线详情失败:', error);
        }
      }
      await this.applyWaylineSelection(target);
    },
    isAnalysisWaylineSelected(wayline) {
      if (!this.selectedWayline || !wayline) return false;
      const selectedId = this.selectedWayline?.id ? String(this.selectedWayline.id) : '';
      const selectedWaylineId = this.selectedWayline?.wayline_id ? String(this.selectedWayline.wayline_id) : '';
      const candidateId = wayline?.id ? String(wayline.id) : '';
      const candidateWaylineId = wayline?.wayline_id ? String(wayline.wayline_id) : '';
      return Boolean(
        (selectedId && candidateId && selectedId === candidateId) ||
        (selectedWaylineId && candidateWaylineId && selectedWaylineId === candidateWaylineId)
      );
    },
    getDetectTypeLabel(code) {
      if (!code) return '--';
      const normalized = String(code).toLowerCase();
      const match = this.detectTypes.find(item => item.code === normalized);
      return match ? match.name : code;
    },

    handleViewAlarmDetail(alarm) {
      this.currentAlarm = alarm;
      this.showAlarmDetail = true;
    },

    handleImageError(event) {
      // 图片加载失败时显示占位图
      event.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect fill="%23ddd" width="400" height="300"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3E图片加载失败%3C/text%3E%3C/svg%3E';
    },

    async handleProcessAlarm(alarmId) {
      try {
        await alarmApi.patchAlarm(alarmId, { status: 'COMPLETED' });
        this.alarms = this.alarms.filter(alarm => alarm.id !== alarmId);
      } catch (error) {
        console.error('更新告警状态失败:', error);
      }
    },

    formatAlarmTime(timestamp) {
      if (!timestamp) return '--';
      const date = new Date(timestamp);
      return date.toLocaleString('zh-CN');
    },

    startDockPolling() {
      this.stopDockPolling()
      this.dockPollTimer = setInterval(() => {
        this.loadDockList(true)
      }, 1000)
    },

    stopDockPolling() {
      if (this.dockPollTimer) {
        clearInterval(this.dockPollTimer)
        this.dockPollTimer = null
      }
    },
    startFlightStatsPolling() {
      this.stopFlightStatsPolling()
      this.flightStatsPollTimer = setInterval(() => {
        this.fetchLatestPositionsForAllDocks()
      }, 1000)
    },
    stopFlightStatsPolling() {
      if (this.flightStatsPollTimer) {
        clearInterval(this.flightStatsPollTimer)
        this.flightStatsPollTimer = null
      }
    },
    async fetchLatestPositionsForAllDocks() {
      if (this.flightStatsPollInFlight) {
        this.flightStatsPollQueued = true
        return
      }
      this.flightStatsPollInFlight = true
      try {
        const response = await dronePositionApi.getLatestByDevice()
        const list = Array.isArray(response) ? response : (response.results || response.data || [])
        if (!Array.isArray(list) || list.length === 0) return
        list.forEach(item => {
          this.recordTelemetryHeartbeat(item)
        })
        const byDevice = new Map()
        list.forEach(item => {
          const deviceSn = this.normalizeDeviceSn(item?.device_sn || item?.drone_sn || item?.sn)
          if (deviceSn) {
            byDevice.set(deviceSn, item)
          }
        })
        const selectedDock = this.selectedDock
        const selectedDroneSn = this.normalizeDeviceSn(selectedDock?.drone_sn)
        const selectedPosition = selectedDroneSn ? byDevice.get(selectedDroneSn) : null
        if (
          this.shouldShowSelectedDrone(selectedDock) &&
          selectedDroneSn &&
          selectedPosition
        ) {
          this.updateLatestPositionsPanel([selectedPosition])
          this.updateDigitalTwinFromPositions([selectedPosition])
        }
        const selectedKey = this.getFlightStatsKey(this.selectedDock)
        this.docks.forEach(dock => {
          const dockDroneSn = this.normalizeDeviceSn(dock?.drone_sn)
          if (!dockDroneSn) return
          if (!this.isDroneWorking(dock)) return
          if (this.getFlightStatsKey(dock) === selectedKey) return
          const position = byDevice.get(dockDroneSn)
          if (position) {
            this.updateFlightStatsForDockFromPosition(position, dock)
          }
        })
      } catch (error) {
        console.error('批量获取无人机位置失败:', error)
      } finally {
        this.flightStatsPollInFlight = false
        if (this.flightStatsPollQueued) {
          this.flightStatsPollQueued = false
          this.fetchLatestPositionsForAllDocks()
        }
      }
    },

    async loadDockList(silent = false) {
      if (silent && this.dockLoading) return
      if (this.dockPollInFlight) {
        if (silent) {
          this.dockPollQueued = true
        }
        return
      }
      this.dockPollInFlight = true
      if (!silent) {
        this.dockLoading = true
        this.dockLoadError = ''
      }
      try {
        const response = await dockStatusApi.getAllDocks()
        const list = Array.isArray(response) ? response : (response.results || [])

        // 按 dock_sn 排序，防止列表跳动
        if (list && Array.isArray(list)) {
          list.sort((a, b) => {
            const snA = a.dock_sn || ''
            const snB = b.dock_sn || ''
            return snA.localeCompare(snB)
          })
        }

        const previousList = Array.isArray(this.docks) ? this.docks : []
        const previousMap = new Map()
        previousList.forEach(dock => {
          const key = this.getFlightStatsKey(dock)
          if (key) previousMap.set(key, dock)
        })

        this.docks = list
        this.dockLoadError = ''
        if (this.selectedDock) {
          const match = list.find(dock => {
            if (this.selectedDock.id && dock.id) {
              return this.selectedDock.id === dock.id
            }
            return this.selectedDock.dock_sn && dock.dock_sn && this.selectedDock.dock_sn === dock.dock_sn
          })
          if (match) {
            this.selectedDock = match
            this.syncLiveStreamType()
            if (!(match.drone_in_dock === 1 || match.drone_in_dock === '1')) {
              this.showCreateTaskDialog = false
            }
          }
        } else if (this.currentMode === 'monitor') {
          const preferredDock = list.find(dock => dock?.drone_sn && this.isDroneWorking(dock)) || list.find(dock => dock?.drone_sn)
          if (preferredDock) {
            this.selectedDock = preferredDock
            this.loadFlightStatsForDock(preferredDock)
            this.syncLiveStreamType()
            this.autoStartThirdPersonForTaskDock(preferredDock)
            if (!(preferredDock.drone_in_dock === 1 || preferredDock.drone_in_dock === '1')) {
              this.showCreateTaskDialog = false
            }
            const dockSn = preferredDock?.dock_sn
            if (dockSn) {
              this.lastTaskInfoSn = dockSn
              this.lastTaskInfoAttempt = Date.now()
              void this.syncWaylineFromTaskInfo(dockSn)
            }
          }
        }
        if (list && list.length) {
          const selectedKey = this.getFlightStatsKey(this.selectedDock)
          list.forEach(dock => {
            const key = this.getFlightStatsKey(dock)
            if (!key || key === selectedKey) return
            const previous = previousMap.get(key)
            if (!previous) return
            const wasInDock = previous.drone_in_dock === 1 || previous.drone_in_dock === '1'
            const nowWorking = dock.drone_in_dock === 0 || dock.drone_in_dock === '0'
            if (wasInDock && nowWorking) {
              this.resetFlightStats(dock)
              return
            }
            const wasWorking = previous.drone_in_dock === 0 || previous.drone_in_dock === '0'
            const nowInDock = dock.drone_in_dock === 1 || dock.drone_in_dock === '1'
            if (wasWorking && nowInDock) {
              const finalize = this.finalizeFlightStats(dock)
              if (finalize && typeof finalize.then === 'function') {
                finalize.then(success => {
                  if (success) this.resetFlightStats(dock)
                })
              }
            }
          })
        }
        if (this.selectedDock) {
          this.startPositionPolling()
          this.syncSelectedDockDronePresentation()
        }
      } catch (error) {
        console.error('获取机场列表失败:', error)
        if (!silent) {
          this.dockLoadError = '机场列表加载失败'
        }
      } finally {
        if (!silent) {
          this.dockLoading = false
        }
        this.dockPollInFlight = false
        if (this.dockPollQueued) {
          this.dockPollQueued = false
          this.loadDockList(true)
        }
      }
    },

    handleDockSelected(dock) {
      if (!dock) return
      const previousDock = this.selectedDock
      const previousSn = previousDock?.drone_sn
      const previousDockSn = previousDock?.dock_sn
      this.saveFlightStatsForDock(previousDock)
      this.selectedDock = dock
      this.loadFlightStatsForDock(dock)
      this.latestPositions = []
      this.latestPositionsCacheKey = ''
      this.positionLoading = false
      if (!previousDockSn || previousDockSn !== dock?.dock_sn) {
        this.resetProtectedTaskContext()
      }
      if (!(dock.drone_in_dock === 1 || dock.drone_in_dock === '1')) {
        this.showCreateTaskDialog = false
      }
      if (previousSn && dock?.drone_sn && previousSn !== dock.drone_sn) {
        this.resetDroneTrackingState()
      }
      this.syncLiveStreamType()
      this.startPositionPolling()
      this.syncSelectedDockDronePresentation()
      this.autoStartThirdPersonForTaskDock(dock)
      const dockSn = dock?.dock_sn
      if (dockSn) {
        this.lastTaskInfoSn = dockSn
        this.lastTaskInfoAttempt = Date.now()
        void this.syncWaylineFromTaskInfo(dockSn)
      }
    },
    syncLiveStreamType() {
      const hasAirport = Boolean(this.airportPushUrl)
      const hasDrone = Boolean(this.dronePushUrl)
      if (this.liveStreamType === 'airport' && hasAirport) return
      if (this.liveStreamType === 'drone' && hasDrone) return
      if (hasAirport) {
        this.liveStreamType = 'airport'
        return
      }
      if (hasDrone) {
        this.liveStreamType = 'drone'
        return
      }
      this.liveStreamType = 'airport'
    },
    setLiveStreamType(type) {
      if (type === 'airport' && this.airportPushUrl) {
        this.liveStreamType = 'airport'
        return
      }
      if (type === 'drone' && this.dronePushUrl) {
        this.liveStreamType = 'drone'
      }
    },
    openCreateTaskDialog() {
      if (!this.selectedDockSn) return
      this.showCreateTaskDialog = true
    },
    async handleReturnHome() {
      const deviceSn = this.selectedDockSn
      if (!deviceSn) {
        ElMessage.warning('请先选择机场')
        return
      }
      try {
        await ElMessageBox.confirm('确认执行返航操作？', '提示', {
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          type: 'warning'
        })
      } catch (error) {
        return
      }
      this.commandLoading.returnHome = true
      try {
        const res = await flightTaskApi.returnHome(deviceSn)
        if (res.code === 0) {
          ElMessage.success('返航指令已发送')
        } else {
          ElMessage.error(res.msg || '返航指令发送失败')
        }
      } catch (error) {
        ElMessage.error('返航指令发送失败：' + (error.message || '未知错误'))
      } finally {
        this.commandLoading.returnHome = false
      }
    },
    async handleCancelReturn() {
      const deviceSn = this.selectedDockSn
      if (!deviceSn) {
        ElMessage.warning('请先选择机场')
        return
      }
      try {
        await ElMessageBox.confirm('确认取消返航？', '提示', {
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          type: 'warning'
        })
      } catch (error) {
        return
      }
      this.commandLoading.cancelReturn = true
      try {
        const res = await flightTaskApi.cancelReturn(deviceSn)
        if (res.code === 0) {
          ElMessage.success('已取消返航')
        } else {
          ElMessage.error(res.msg || '取消返航失败')
        }
      } catch (error) {
        ElMessage.error('取消返航失败：' + (error.message || '未知错误'))
      } finally {
        this.commandLoading.cancelReturn = false
      }
    },
    async handlePause() {
      const deviceSn = this.selectedDockSn
      if (!deviceSn) {
        ElMessage.warning('请先选择机场')
        return
      }
      try {
        await ElMessageBox.confirm('确认暂停当前任务？', '提示', {
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          type: 'info'
        })
      } catch (error) {
        return
      }
      this.commandLoading.pause = true
      try {
        const res = await flightTaskApi.pauseTask(deviceSn)
        if (res.code === 0) {
          ElMessage.success('任务已暂停')
        } else {
          ElMessage.error(res.msg || '暂停任务失败')
        }
      } catch (error) {
        ElMessage.error('暂停任务失败：' + (error.message || '未知错误'))
      } finally {
        this.commandLoading.pause = false
      }
    },
    async handleResume() {
      const deviceSn = this.selectedDockSn
      if (!deviceSn) {
        ElMessage.warning('请先选择机场')
        return
      }
      try {
        await ElMessageBox.confirm('确认恢复任务？', '提示', {
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          type: 'success'
        })
      } catch (error) {
        return
      }
      this.commandLoading.resume = true
      try {
        const res = await flightTaskApi.resumeTask(deviceSn)
        if (res.code === 0) {
          ElMessage.success('任务已恢复')
        } else {
          ElMessage.error(res.msg || '恢复任务失败')
        }
      } catch (error) {
        ElMessage.error('恢复任务失败：' + (error.message || '未知错误'))
      } finally {
        this.commandLoading.resume = false
      }
    },

    startPositionPolling() {
      const deviceSn = this.normalizeDeviceSn(this.selectedDock?.drone_sn)
      const shouldPoll = deviceSn && this.shouldShowSelectedDrone(this.selectedDock)
      if (!shouldPoll) {
        this.stopPositionPolling()
        if (this.currentMode !== 'analysis') {
          this.clearDigitalTwinAndAlarms()
        }
        return
      }
      if (this.positionPollingDeviceSn && this.positionPollingDeviceSn !== deviceSn) {
        this.resetDroneTrackingState()
      }
      if (this.positionPollTimer && this.positionPollingDeviceSn === deviceSn) {
        return
      }
      this.stopPositionPolling()
      this.positionPollingDeviceSn = deviceSn
      this.fetchLatestPositions()
      this.positionPollTimer = setInterval(() => {
        this.fetchLatestPositions()
      }, 500)
    },

    stopPositionPolling() {
      if (this.positionPollTimer) {
        clearInterval(this.positionPollTimer)
        this.positionPollTimer = null
      }
      this.positionPollingDeviceSn = ''
    },

    async fetchLatestPositions() {
      const deviceSn = this.normalizeDeviceSn(this.selectedDock?.drone_sn)
      if (!deviceSn || this.positionLoading || !this.shouldShowSelectedDrone(this.selectedDock)) return
      this.positionLoading = true
      try {
        const response = await dronePositionApi.getPositions({
          device_sn: deviceSn,
          ordering: '-timestamp',
          page_size: DRONE_POSITION_PAGE_SIZE,
          limit: DRONE_POSITION_PAGE_SIZE
        })
        if (this.normalizeDeviceSn(this.selectedDock?.drone_sn) !== deviceSn) return
        const list = Array.isArray(response)
          ? response.slice(0, DRONE_POSITION_PAGE_SIZE)
          : ((response.results || []).slice(0, DRONE_POSITION_PAGE_SIZE))
        list.forEach(item => {
          this.recordTelemetryHeartbeat(item)
        })
        this.updateLatestPositionsPanel(list)
        this.updateDigitalTwinFromPositions(list)
      } catch (error) {
        console.error('获取无人机位置失败:', error)
      } finally {
        this.positionLoading = false
      }
    },
    updateLatestPositionsPanel(positions) {
      const nextPositions = Array.isArray(positions) ? positions.slice(0, DRONE_POSITION_PAGE_SIZE) : []
      const nextCacheKey = nextPositions
        .map(item => `${item?.id ?? ''}:${this.getPositionTimestamp(item)}`)
        .join('|')

      if (this.latestPositionsCacheKey === nextCacheKey && this.latestPositions.length === nextPositions.length) {
        return
      }

      this.latestPositionsCacheKey = nextCacheKey
      this.latestPositions = nextPositions
    },
    recordTelemetryHeartbeat(position) {
      const deviceSn = this.normalizeDeviceSn(position?.device_sn || position?.drone_sn || position?.sn)
      const timestamp = this.getPositionTimestamp(position)
      if (!deviceSn || !Number.isFinite(timestamp)) return
      this.latestTelemetryTimestampsByDevice = {
        ...this.latestTelemetryTimestampsByDevice,
        [deviceSn]: timestamp
      }
      this.latestTelemetryPositionsByDevice = {
        ...this.latestTelemetryPositionsByDevice,
        [deviceSn]: position
      }
    },
    hasRecentTelemetry(deviceSn, maxAgeMs = DRONE_TELEMETRY_ACTIVE_WINDOW_MS) {
      const normalizedSn = this.normalizeDeviceSn(deviceSn)
      if (!normalizedSn) return false
      const timestamp = this.latestTelemetryTimestampsByDevice?.[normalizedSn]
      if (!Number.isFinite(timestamp)) return false
      return Math.abs(Date.now() - timestamp) <= maxAgeMs
    },
    getLatestTelemetryPositionForDock(dock = this.selectedDock) {
      const deviceSn = this.normalizeDeviceSn(dock?.drone_sn)
      if (!deviceSn) return null
      return this.latestTelemetryPositionsByDevice?.[deviceSn] || null
    },
    shouldShowSelectedDrone(dock = this.selectedDock) {
      if (this.currentMode !== 'monitor') return false
      if (!dock) return false
      if (!this.normalizeDeviceSn(dock?.drone_sn)) return false
      return this.isDroneWorking(dock)
    },
    syncSelectedDockDronePresentation(preferredPosition = null) {
      if (!this.shouldShowSelectedDrone()) {
        this.setDroneVisibility(false)
        return false
      }
      const fallbackPosition = this.getLatestTelemetryPositionForDock(this.selectedDock)
      const latestPanelPosition = Array.isArray(this.latestPositions) ? this.latestPositions[0] : null
      const position = preferredPosition || fallbackPosition || latestPanelPosition
      if (position) {
        this.updateDroneEntityFromPosition(position)
        this.setDroneVisibility(true)
        return true
      }
      if (this.droneEntity) {
        this.setDroneVisibility(true)
        return true
      }
      return false
    },

    getDockDisplayName(dock) {
      return dock?.display_name || dock?.dock_name || dock?.dock_sn || '未知机场'
    },

    updateDigitalTwinFromPositions(positions) {
      if (this.currentMode === 'analysis') {
        this.setDroneVisibility(false)
        return
      }
      const latestPosition = Array.isArray(positions) ? positions[0] : null
      this.syncSelectedDockDronePresentation(latestPosition)
      const dockSn = this.selectedDock?.dock_sn
      if (!dockSn) return
      const now = Date.now()
      if (dockSn === this.lastTaskInfoSn && now - this.lastTaskInfoAttempt < 3000) {
        return
      }
      if (this.taskInfoFetchInFlight) return
      this.lastTaskInfoSn = dockSn
      this.lastTaskInfoAttempt = now
      void this.syncWaylineFromTaskInfo(dockSn)
    },
    pruneDroneTrackingSamples(sampleTime, timestamp) {
      const Cesium = this.cesiumLib || window.Cesium
      if (!Cesium || !this.dronePositionProperty || !this.droneOrientationProperty) return
      if (
        Number.isFinite(this.lastDroneSamplePruneTimestamp) &&
        timestamp - this.lastDroneSamplePruneTimestamp < DRONE_SAMPLE_PRUNE_INTERVAL_MS
      ) {
        return
      }

      ensureDroneTrackingScratch(Cesium)

      const pruneBefore = Cesium.JulianDate.addSeconds(
        sampleTime,
        -DRONE_SAMPLE_RETENTION_SECONDS,
        droneTrackingPruneBefore
      )

      droneTrackingTrimInterval.start = Cesium.Iso8601.MINIMUM_VALUE
      droneTrackingTrimInterval.stop = pruneBefore
      droneTrackingTrimInterval.isStartIncluded = true
      droneTrackingTrimInterval.isStopIncluded = false

      this.dronePositionProperty.removeSamples(droneTrackingTrimInterval)
      this.droneOrientationProperty.removeSamples(droneTrackingTrimInterval)
      this.lastDroneSamplePruneTimestamp = timestamp
    },
    updateDroneEntityFromPosition(position) {
      try {
        if (!position) return
        if (!this.viewer) return
        const Cesium = this.cesiumLib || window.Cesium
        if (!Cesium) return
        ensureDroneTrackingScratch(Cesium)

        const timestamp = this.getPositionTimestamp(position)
        if (!Number.isFinite(timestamp)) return
        if (Number.isFinite(this.lastDroneTimestamp) && timestamp <= this.lastDroneTimestamp) {
          return
        }

        const payload = this.extractPositionData(position)
        const longitude = payload.longitude
        const latitude = payload.latitude
        if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return
        const altitude = Number.isFinite(payload.altitude) ? payload.altitude : 0
        const cartesian = Cesium.Cartesian3.fromDegrees(longitude, latitude, altitude)
        const sampleTime = Cesium.JulianDate.fromDate(new Date(timestamp))

        if (!this.dronePositionProperty) {
          this.dronePositionProperty = new Cesium.SampledPositionProperty()
          this.dronePositionProperty.setInterpolationOptions({
            interpolationDegree: 1,
            interpolationAlgorithm: Cesium.LinearApproximation
          })
          this.dronePositionProperty.forwardExtrapolationType = Cesium.ExtrapolationType.HOLD
          this.dronePositionProperty.backwardExtrapolationType = Cesium.ExtrapolationType.HOLD
        }

        if (!this.droneOrientationProperty) {
          this.droneOrientationProperty = new Cesium.SampledProperty(Cesium.Quaternion)
          this.droneOrientationProperty.setInterpolationOptions({
            interpolationDegree: 1,
            interpolationAlgorithm: Cesium.LinearApproximation
          })
          this.droneOrientationProperty.forwardExtrapolationType = Cesium.ExtrapolationType.HOLD
          this.droneOrientationProperty.backwardExtrapolationType = Cesium.ExtrapolationType.HOLD
        }

        this.dronePositionProperty.addSample(sampleTime, cartesian)
        this.pruneDroneTrackingSamples(sampleTime, timestamp)

        if (!this.droneEntity) {
          const modelUri = this.resolveAssetPath('models/fly2.glb')
          this.droneEntity = this.viewer.entities.add({
            name: '无人机',
            show: true,
            position: this.dronePositionProperty,
            model: {
              uri: modelUri,
              minimumPixelSize: 128,
              maximumScale: 2000,
              scale: 0.3,
              runAnimations: true
            }
          })
        } else {
          if (this.droneEntity.position !== this.dronePositionProperty) {
            this.droneEntity.position = this.dronePositionProperty
          }
          if (this.droneEntity.point) {
            this.droneEntity.point = undefined
          }
          if (this.droneEntity.show !== true) {
            this.droneEntity.show = true
          }
        }

        this.updateFlightStatsFromPosition(payload)

        const resolvedHeading = this.resolveDroneHeading(payload.heading, cartesian)
        const heading = Number.isFinite(resolvedHeading) ? resolvedHeading : 0
        const pitch = Number.isFinite(payload.pitch) ? payload.pitch : 0
        const roll = Number.isFinite(payload.roll) ? payload.roll : 0

        const modelHeadingOffset = Cesium.Math.toRadians(20)

        droneTrackingHeadingPitchRoll.heading = heading + modelHeadingOffset
        droneTrackingHeadingPitchRoll.pitch = pitch
        droneTrackingHeadingPitchRoll.roll = roll
        const orientation = Cesium.Transforms.headingPitchRollQuaternion(
          cartesian,
          droneTrackingHeadingPitchRoll,
          undefined,
          undefined,
          droneTrackingOrientationSample
        )
        this.droneOrientationProperty.addSample(sampleTime, orientation)

        if (this.droneEntity.orientation !== this.droneOrientationProperty) {
          this.droneEntity.orientation = this.droneOrientationProperty
        }

        this.lastDroneTimestamp = timestamp
        this.lastDronePosition = { longitude, latitude, altitude }
        this.lastDroneCartesian = cartesian

        const clock = this.viewer.clock
        if (clock) {
          const renderTime = Cesium.JulianDate.addSeconds(sampleTime, -3, droneTrackingRenderTime)
          const driftSeconds = Math.abs(Cesium.JulianDate.secondsDifference(clock.currentTime, renderTime))
          if (driftSeconds >= 0.5) {
            clock.currentTime = renderTime
          }
          if (!clock.shouldAnimate) {
            clock.shouldAnimate = true
          }
        }

        this.viewer.scene.requestRender()

        if (this.cameraMode === 'bird') {
          this.updateBirdCameraFromCoords(longitude, latitude, altitude)
        } else if (this.cameraMode === 'third' && !this.chaseCameraListener) {
          this.enableChaseCamera(this.droneEntity, 80, 30)
        }
      } catch (error) {
        console.error('更新无人机实体失败:', error)
      }
    },
    getFlightStatsKey(dock = this.selectedDock) {
      if (!dock) return ''
      const key = dock.dock_sn || dock.id || ''
      return String(key || '')
    },
    getEmptyFlightStats() {
      return {
        flightStartTimestamp: null,
        flightDurationMs: 0,
        flightDistanceKm: 0,
        flightLastPosition: null,
        flightLastUpdateTimestamp: null,
        flightStatsTaskUuid: '',
        flightStatsSaving: false,
        flightStatsSavedTaskUuid: ''
      }
    },
    buildFlightStatsSnapshot() {
      return {
        flightStartTimestamp: this.flightStartTimestamp,
        flightDurationMs: this.flightDurationMs,
        flightDistanceKm: this.flightDistanceKm,
        flightLastPosition: this.flightLastPosition,
        flightLastUpdateTimestamp: this.flightLastUpdateTimestamp,
        flightStatsTaskUuid: this.flightStatsTaskUuid,
        flightStatsSaving: this.flightStatsSaving,
        flightStatsSavedTaskUuid: this.flightStatsSavedTaskUuid
      }
    },
    applyFlightStatsSnapshot(snapshot) {
      const safe = snapshot || this.getEmptyFlightStats()
      this.flightStartTimestamp = safe.flightStartTimestamp ?? null
      this.flightDurationMs = Number.isFinite(safe.flightDurationMs) ? safe.flightDurationMs : 0
      this.flightDistanceKm = Number.isFinite(safe.flightDistanceKm) ? safe.flightDistanceKm : 0
      this.flightLastPosition = safe.flightLastPosition || null
      this.flightLastUpdateTimestamp = safe.flightLastUpdateTimestamp ?? null
      this.flightStatsTaskUuid = safe.flightStatsTaskUuid || ''
      this.flightStatsSaving = Boolean(safe.flightStatsSaving)
      this.flightStatsSavedTaskUuid = safe.flightStatsSavedTaskUuid || ''
    },
    saveFlightStatsForDock(dock = this.selectedDock, snapshot = null) {
      const key = this.getFlightStatsKey(dock)
      if (!key) return
      const data = snapshot ? { ...snapshot } : { ...this.buildFlightStatsSnapshot() }
      this.flightStatsByDock[key] = data
    },
    loadFlightStatsForDock(dock = this.selectedDock) {
      const key = this.getFlightStatsKey(dock)
      if (!key) {
        this.applyFlightStatsSnapshot(this.getEmptyFlightStats())
        return
      }
      const snapshot = this.flightStatsByDock[key]
      if (snapshot) {
        this.applyFlightStatsSnapshot(snapshot)
      } else {
        this.applyFlightStatsSnapshot(this.getEmptyFlightStats())
      }
    },
    updateFlightStatsForDockFromPosition(position, dock = this.selectedDock) {
      if (!position) return
      const payload = this.extractPositionData(position)
      this.updateFlightStatsForDock(payload, dock)
    },
    updateFlightStatsForDock(payload, dock = this.selectedDock) {
      if (!dock || !this.isDroneWorking(dock)) return
      if (!payload) return
      const longitude = payload.longitude
      const latitude = payload.latitude
      if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return
      const altitude = Number.isFinite(payload.altitude) ? payload.altitude : 0

      const key = this.getFlightStatsKey(dock)
      if (!key) return
      const snapshot = this.flightStatsByDock[key]
        ? { ...this.flightStatsByDock[key] }
        : this.getEmptyFlightStats()

      const now = Date.now()
      if (!snapshot.flightStartTimestamp) {
        snapshot.flightStartTimestamp = now
        snapshot.flightDurationMs = 0
        snapshot.flightDistanceKm = 0
        snapshot.flightLastPosition = { longitude, latitude, altitude }
        snapshot.flightLastUpdateTimestamp = now
        if (!snapshot.flightStatsTaskUuid && this.isDockSelected(dock) && this.currentTaskUuid) {
          snapshot.flightStatsTaskUuid = this.currentTaskUuid
        }
        this.saveFlightStatsForDock(dock, snapshot)
        if (this.isDockSelected(dock)) {
          this.applyFlightStatsSnapshot(snapshot)
        }
        return
      }

      if (snapshot.flightLastPosition) {
        const distance = this.getWaypointDistanceMeters(snapshot.flightLastPosition, { longitude, latitude, altitude })
        if (Number.isFinite(distance) && distance >= 0) {
          snapshot.flightDistanceKm += distance / 1000
        }
      }

      snapshot.flightLastPosition = { longitude, latitude, altitude }
      snapshot.flightLastUpdateTimestamp = now
      snapshot.flightDurationMs = Math.max(0, now - snapshot.flightStartTimestamp)
      if (!snapshot.flightStatsTaskUuid && this.isDockSelected(dock) && this.currentTaskUuid) {
        snapshot.flightStatsTaskUuid = this.currentTaskUuid
      }
      this.saveFlightStatsForDock(dock, snapshot)
      if (this.isDockSelected(dock)) {
        this.applyFlightStatsSnapshot(snapshot)
      }
    },
    updateFlightStatsFromPosition(payload) {
      this.updateFlightStatsForDock(payload, this.selectedDock)
    },
    async finalizeFlightStats(dock = this.selectedDock) {
      const key = this.getFlightStatsKey(dock)
      if (!key) return false
      let snapshot = this.flightStatsByDock[key]
      if (!snapshot && this.isDockSelected(dock)) {
        snapshot = this.buildFlightStatsSnapshot()
        this.flightStatsByDock[key] = { ...snapshot }
      }
      if (!snapshot) return true
      let taskUuid = snapshot.flightStatsTaskUuid
      if (!taskUuid && this.isDockSelected(dock) && this.currentTaskUuid) {
        taskUuid = this.currentTaskUuid
      }
      if (!taskUuid) {
        taskUuid = await this.resolveTaskUuidForDock(dock)
        if (taskUuid) {
          snapshot.flightStatsTaskUuid = taskUuid
          this.flightStatsByDock[key] = snapshot
        }
      }
      if (snapshot.flightStatsSaving) return false
      if (!snapshot.flightStartTimestamp) return true

      const endTime = snapshot.flightLastUpdateTimestamp || Date.now()
      const durationMs = Math.max(0, endTime - snapshot.flightStartTimestamp)
      snapshot.flightDurationMs = durationMs
      snapshot.flightStatsSaving = false
      if (taskUuid) {
        snapshot.flightStatsSavedTaskUuid = taskUuid
      }
      this.flightStatsByDock[key] = snapshot
      if (this.isDockSelected(dock)) {
        this.applyFlightStatsSnapshot(snapshot)
      }
      return true
    },
    resetFlightStats(dock = this.selectedDock) {
      const cleared = this.getEmptyFlightStats()
      const key = this.getFlightStatsKey(dock)
      if (key) {
        this.flightStatsByDock[key] = { ...cleared }
      }
      if (!dock || this.isDockSelected(dock)) {
        this.applyFlightStatsSnapshot(cleared)
      }
    },
extractPositionData(position) {
      const rawData = this.parseRawData(position?.raw_data)
      const rawDataPayload = rawData?.data ? this.parseRawData(rawData.data) : null
      const directPayload = position?.data ? this.parseRawData(position.data) : null
      const raw =
        rawData?.position ||
        rawData?.location ||
        rawDataPayload?.position ||
        rawDataPayload?.location ||
        directPayload?.position ||
        directPayload?.location ||
        rawDataPayload ||
        directPayload ||
        rawData ||
        {}
        
      const toRadians = (value) => (Number.isFinite(value) ? value * (Math.PI / 180) : NaN)
      
      const longitude = this.toNumber(
        position?.longitude ?? position?.lon ?? position?.lng ?? raw.longitude ?? raw.lon ?? raw.lng
      )
      const latitude = this.toNumber(
        position?.latitude ?? position?.lat ?? raw.latitude ?? raw.lat
      )
      
      // 获取无人机的真实绝对高程 (RTK高度)
      const realAltitude = this.toNumber(
        position?.altitude ??
        position?.height ??
        position?.relative_height ??
        position?.ellipsoid_height ??
        raw.altitude ??
        raw.height ??
        raw.relative_height ??
        raw.ellipsoid_height
      )

      // 定义当地真实海拔偏移量
      const terrainElevationOffset = 40.2;
      
      // 扣除海拔高度，使无人机模型下沉贴合底图
      const renderAltitude = Number.isFinite(realAltitude) 
                             ? (realAltitude - terrainElevationOffset) 
                             : NaN;

      const attitudeHead = this.toNumber(
        position?.attitude_head ??
        position?.attitude_heading ??
        position?.attitude_yaw ??
        raw.attitude_head ??
        raw.attitude_heading ??
        raw.attitude_yaw
      )
      
      const heading = Number.isFinite(attitudeHead)
        ? toRadians(attitudeHead)
        : this.toNumber(
          position?.heading ??
          position?.yaw ??
          position?.aircraft_heading ??
          raw.heading ??
          raw.yaw ??
          raw.aircraft_heading
        )
        
      const pitchRaw = this.toNumber(
        position?.attitude_pitch ?? position?.pitch ?? raw.attitude_pitch ?? raw.pitch
      )
      const rollRaw = this.toNumber(
        position?.attitude_roll ?? position?.roll ?? raw.attitude_roll ?? raw.roll
      )
      
      const pitch = Number.isFinite(pitchRaw) ? toRadians(pitchRaw) : NaN
      const roll = Number.isFinite(rollRaw) ? toRadians(rollRaw) : NaN
      
      return { 
        longitude, 
        latitude, 
        altitude: renderAltitude, // 输出给 Cesium 的是扣除海拔后的渲染高度
        heading, 
        pitch, 
        roll 
      }
    },
    parseRawData(raw) {
      if (!raw) return null
      if (typeof raw === 'object') return raw
      if (typeof raw !== 'string') return null
      try {
        return JSON.parse(raw)
      } catch (e) {
        return null
      }
    },
    getPositionTimestamp(position) {
      const rawData = this.parseRawData(position?.raw_data)
      const rawDataPayload = rawData?.data ? this.parseRawData(rawData.data) : null
      const directPayload = position?.data ? this.parseRawData(position.data) : null
      const candidates = [
        position?.timestamp,
        position?.created_at,
        position?.updated_at,
        position?.time,
        position?.ts,
        rawData?.timestamp,
        rawData?.time,
        rawData?.ts,
        rawDataPayload?.timestamp,
        rawDataPayload?.time,
        rawDataPayload?.ts,
        directPayload?.timestamp,
        directPayload?.time,
        directPayload?.ts
      ]
      for (const candidate of candidates) {
        const normalized = this.normalizeTimestamp(candidate)
        if (Number.isFinite(normalized)) {
          return normalized
        }
      }
      return NaN
    },
    normalizeTimestamp(value) {
      if (value === null || value === undefined) return NaN
      if (value instanceof Date) {
        const time = value.getTime()
        return Number.isFinite(time) ? time : NaN
      }
      if (typeof value === 'number') {
        if (value > 1e12) return value
        if (value > 1e9) return value * 1000
        return value
      }
      if (typeof value === 'string') {
        const trimmed = value.trim()
        if (!trimmed) return NaN
        const parsed = Date.parse(trimmed)
        if (!Number.isNaN(parsed)) return parsed
        const asNumber = Number(trimmed)
        if (Number.isFinite(asNumber)) return this.normalizeTimestamp(asNumber)
      }
      return NaN
    },
    normalizeDeviceSn(value) {
      const normalized = String(value || '').trim()
      return normalized || ''
    },
    resolveDroneHeading(rawHeading, cartesian) {
      const Cesium = this.cesiumLib || window.Cesium
      if (!Cesium || !cartesian) return NaN
      let heading = this.toNumber(rawHeading)
      if (Number.isFinite(heading)) {
        if (Math.abs(heading) > Math.PI * 2) {
          heading = Cesium.Math.toRadians(heading)
        }
        this.lastDroneHeading = heading
        return heading
      }
      if (this.lastDroneCartesian) {
        const computed = this.calculateHeading(this.lastDroneCartesian, cartesian)
        if (Number.isFinite(computed)) {
          this.lastDroneHeading = computed
          return computed
        }
      }
      return this.lastDroneHeading ?? NaN
    },

    async syncWaylineFromTaskInfo(dockSn) {
      const normalizedSn = String(dockSn || '').trim()
      if (!normalizedSn) return
      if (this.taskInfoFetchInFlight) return
      this.taskInfoFetchInFlight = true
      try {
        const response = await flightTaskInfoApi.getLatestBySn(normalizedSn)
        let taskInfo = response
        if (Array.isArray(response)) {
          taskInfo = response[0]
        } else if (response?.results) {
          taskInfo = response.results[0]
        } else if (response?.data && typeof response.data === 'object' && !Array.isArray(response.data)) {
          taskInfo = response.data
        }
        if (this.selectedDock?.dock_sn && this.selectedDock.dock_sn !== normalizedSn) {
          return
        }
        if (!taskInfo || Object.keys(taskInfo).length === 0) {
          this.currentTaskInfo = null
          this.resetProtectedTaskContext()
          return
        }
        this.currentTaskInfo = taskInfo
        this.syncFlightStatsFromTaskInfo(taskInfo, this.selectedDock)
        const params = this.parseTaskParams(taskInfo.params)
        this.updateProtectedTaskContext(taskInfo, params)
        if (this.isTaskFinished(taskInfo, params)) {
          const finalize = this.finalizeFlightStats(this.selectedDock)
          if (finalize && typeof finalize.then === 'function') {
            finalize.then(success => {
              if (success) this.resetFlightStats(this.selectedDock)
            })
          }
        }
        const waylineUuid = params?.wayline_uuid || params?.wayline_id || taskInfo.wayline_id
        const normalizedUuid = String(waylineUuid || '').trim()
        if (!normalizedUuid) return
        if (normalizedUuid === this.currentWaylineUuid) return
        this.currentWaylineUuid = normalizedUuid
        await this.syncWaylineFromUuid(normalizedUuid)
      } catch (error) {
        console.error('获取任务信息失败:', error)
      } finally {
        this.taskInfoFetchInFlight = false
      }
    },

    async syncWaylineFromUuid(waylineUuid) {
      const normalizedUuid = String(waylineUuid || '').trim()
      if (!normalizedUuid) return
      if (this.waylineFetchInFlight) return
      this.waylineFetchInFlight = true
      try {
        let response = await waylineApi.getWaylines({ wayline_id: normalizedUuid })
        let list = Array.isArray(response) ? response : (response.results || response.data || [])
        if (!list.length) {
          response = await waylineApi.getWaylines({ wayline_id__icontains: normalizedUuid })
          list = Array.isArray(response) ? response : (response.results || response.data || [])
        }
        let match = list.find(item => String(item?.wayline_id) === normalizedUuid) || list[0]
        if (!match && /^\d+$/.test(normalizedUuid)) {
          const detail = await waylineApi.getWaylineDetail(normalizedUuid)
          if (detail?.id) {
            match = detail
          }
        }
        if (!match) {
          console.warn('[Dashboard] 未找到匹配航线:', normalizedUuid)
          return
        }
        await this.applyWaylineSelection(match)
      } catch (error) {
        console.error('获取航线信息失败:', error)
      } finally {
        this.waylineFetchInFlight = false
      }
    },

    parseTaskParams(params) {
      if (!params) return null
      if (typeof params === 'object') return params
      if (typeof params !== 'string') return null
      try {
        return JSON.parse(params)
      } catch (e) {
        return null
      }
    },
    getTaskUuidFromTaskInfo(taskInfo, params) {
      const candidates = [
        params?.task_uuid,
        params?.taskUuid,
        params?.task_id,
        params?.taskId,
        taskInfo?.task_uuid,
        taskInfo?.taskUuid
      ]
      for (const candidate of candidates) {
        const value = String(candidate || '').trim()
        if (value) return value
      }
      return ''
    },
    syncFlightStatsFromTaskInfo(taskInfo, dock = this.selectedDock) {
      if (!dock || !taskInfo) return
      const key = this.getFlightStatsKey(dock)
      if (!key) return

      const durationSeconds = this.toNumber(taskInfo?.flight_duration ?? taskInfo?.flightDuration)
      const distanceKm = this.toNumber(taskInfo?.flight_distance ?? taskInfo?.flightDistance)
      const hasDuration = Number.isFinite(durationSeconds) && durationSeconds >= 0
      const hasDistance = Number.isFinite(distanceKm) && distanceKm >= 0
      if (!hasDuration && !hasDistance) return

      const params = this.parseTaskParams(taskInfo?.params)
      const taskUuid = this.getTaskUuidFromTaskInfo(taskInfo, params)
      const isActive = taskInfo?.flight_active === true || taskInfo?.flight_active === 1 || taskInfo?.flight_active === '1'

      if (!isActive && hasDuration && hasDistance && durationSeconds === 0 && distanceKm === 0) {
        const cleared = this.getEmptyFlightStats()
        if (taskUuid) {
          cleared.flightStatsTaskUuid = taskUuid
          cleared.flightStatsSavedTaskUuid = taskUuid
        }
        this.flightStatsByDock[key] = { ...cleared }
        if (this.isDockSelected(dock)) {
          this.applyFlightStatsSnapshot(cleared)
        }
        return
      }

      const snapshot = this.flightStatsByDock[key]
        ? { ...this.flightStatsByDock[key] }
        : this.getEmptyFlightStats()
      const now = Date.now()

      if (hasDuration) {
        const durationMs = Math.max(0, Math.floor(durationSeconds * 1000))
        snapshot.flightDurationMs = durationMs
        if (durationMs > 0 || isActive || (hasDistance && distanceKm > 0)) {
          snapshot.flightStartTimestamp = now - durationMs
          snapshot.flightLastUpdateTimestamp = now
        }
      }
      if (hasDistance) {
        snapshot.flightDistanceKm = Math.max(0, distanceKm)
      }
      if (taskUuid) {
        snapshot.flightStatsTaskUuid = taskUuid
        if (!isActive) {
          snapshot.flightStatsSavedTaskUuid = taskUuid
        }
      }

      this.flightStatsByDock[key] = snapshot
      if (this.isDockSelected(dock)) {
        this.applyFlightStatsSnapshot(snapshot)
      }
    },
    async resolveTaskUuidForDock(dock) {
      const dockSn = dock?.dock_sn
      if (!dockSn) return ''
      try {
        const response = await flightTaskInfoApi.getLatestBySn(dockSn)
        let taskInfo = response
        if (Array.isArray(response)) {
          taskInfo = response[0]
        } else if (response?.results) {
          taskInfo = response.results[0]
        } else if (response?.data && typeof response.data === 'object' && !Array.isArray(response.data)) {
          taskInfo = response.data
        }
        if (!taskInfo || Object.keys(taskInfo).length === 0) return ''
        const params = this.parseTaskParams(taskInfo.params)
        return this.getTaskUuidFromTaskInfo(taskInfo, params)
      } catch (error) {
        console.error('获取任务UUID失败:', error)
        return ''
      }
    },
    isTaskFinished(taskInfo, params) {
      const rawStatus =
        taskInfo?.status ??
        taskInfo?.task_status ??
        params?.status ??
        params?.task_status ??
        params?.taskStatus
      const status = String(rawStatus || '').trim().toLowerCase()
      if (status) {
        const finishedStates = new Set([
          'finished',
          'complete',
          'completed',
          'success',
          'succeeded',
          'done',
          'ended',
          'stopped',
          'canceled',
          'cancelled',
          'failed'
        ])
        if (finishedStates.has(status)) return true
      }
      const endTime =
        taskInfo?.end_time ??
        taskInfo?.finished_at ??
        taskInfo?.completed_at ??
        params?.end_time ??
        params?.finished_at ??
        params?.completed_at
      return Boolean(endTime)
    },
    extractTaskIdFromImageUrl(url) {
      if (!url) return ''
      const value = String(url)
      const markers = ['/media/', 'media/']
      let marker = ''
      let index = -1
      for (const candidate of markers) {
        index = value.indexOf(candidate)
        if (index !== -1) {
          marker = candidate
          break
        }
      }
      if (index === -1) return ''
      const tail = value.slice(index + marker.length)
      const endIndex = tail.search(/[/?#]/)
      return endIndex === -1 ? tail : tail.slice(0, endIndex)
    },
    normalizeAlarmList(list) {
      if (!Array.isArray(list)) return []
      return list.map(alarm => ({
        ...alarm,
        image_url: alarm?.image_signed_url || alarm?.image_url
      }))
    },
    filterAlarmsByTaskId(list, taskId) {
      if (!taskId || !Array.isArray(list)) return []
      return list.filter(alarm => {
        const alarmTaskId = this.extractTaskIdFromImageUrl(alarm?.image_url || alarm?.image_signed_url)
        return alarmTaskId === taskId
      })
    },
    resetProtectedAlarmTracking() {
      this.protectedAlarmInitialized = false
      this.protectedAlarmIdSet = new Set()
    },
    hideProtectedAlarmToast() {
      this.protectedAlarmToastVisible = false
      if (this.protectedAlarmToastTimer) {
        clearTimeout(this.protectedAlarmToastTimer)
        this.protectedAlarmToastTimer = null
      }
    },
    showProtectedAlarmToast(message) {
      this.protectedAlarmToastMessage = message
      this.protectedAlarmToastVisible = true
      if (this.protectedAlarmToastTimer) {
        clearTimeout(this.protectedAlarmToastTimer)
      }
      this.protectedAlarmToastTimer = setTimeout(() => {
        this.protectedAlarmToastVisible = false
        this.protectedAlarmToastTimer = null
      }, 2500)
    },
    stopProtectedAlarmPolling() {
      if (this.protectedAlarmPollTimer) {
        clearInterval(this.protectedAlarmPollTimer)
        this.protectedAlarmPollTimer = null
      }
    },
    startProtectedAlarmPolling(taskUuid) {
      if (!taskUuid || this.currentMode !== 'monitor') return
      this.stopProtectedAlarmPolling()
      this.protectedAlarmPollTimer = setInterval(() => {
        this.fetchProtectedTaskAlarms({ silent: true })
      }, 1000)
      this.fetchProtectedTaskAlarms()
    },
    async fetchProtectedTaskAlarms(options = {}) {
      const { silent = false } = options
      if (this.currentMode !== 'monitor' || !this.isProtectedAreaTask) return
      const taskUuid = this.currentTaskUuid
      if (!taskUuid || this.protectedAlarmFetchInFlight) return
      this.protectedAlarmFetchInFlight = true
      if (!silent) {
        this.loadingAlarms = true
      }
      try {
        const response = await alarmApi.getAlarms({
          task_uuid: taskUuid,
          ordering: '-created_at'
        })
        if (this.currentMode !== 'monitor' || !this.isProtectedAreaTask || this.currentTaskUuid !== taskUuid) {
          return
        }
        let list = Array.isArray(response) ? response : (response.results || [])
        list = this.filterAlarmsByTaskId(list, taskUuid)
        const normalized = this.normalizeAlarmList(list)
        const nextIds = new Set(
          normalized.map(item => item?.id).filter(id => id !== null && id !== undefined)
        )
        const prevIds = this.protectedAlarmIdSet || new Set()
        const hasNew = this.protectedAlarmInitialized && Array.from(nextIds).some(id => !prevIds.has(id))
        this.protectedAlarmInitialized = true
        this.protectedAlarmIdSet = nextIds
        this.alarms = normalized
        this.plotAlarmMarkers(normalized)
        if (hasNew) {
          this.showProtectedAlarmToast('检测到保护区新增一条报警')
        }
      } catch (error) {
        console.error('获取保护区告警失败:', error)
        if (!silent) {
          this.alarms = []
          this.clearAlarmMarkers()
        }
      } finally {
        if (!silent) {
          this.loadingAlarms = false
        }
        this.protectedAlarmFetchInFlight = false
      }
    },
    updateProtectedTaskContext(taskInfo, params) {
      if (this.currentMode !== 'monitor') return
      const rawProtected = taskInfo?.is_protected_area
      const isProtected = rawProtected === true || rawProtected === 1 || rawProtected === '1'
      const taskUuid = this.getTaskUuidFromTaskInfo(taskInfo, params)
      const previousTaskUuid = this.currentTaskUuid
      this.isProtectedAreaTask = isProtected
      this.currentTaskUuid = taskUuid

      if (!isProtected || !taskUuid) {
        this.stopProtectedAlarmPolling()
        this.resetProtectedAlarmTracking()
        this.clearAlarmData()
        return
      }

      if (previousTaskUuid !== taskUuid) {
        this.resetProtectedAlarmTracking()
        this.clearAlarmData()
        this.startProtectedAlarmPolling(taskUuid)
        return
      }

      if (!this.protectedAlarmPollTimer) {
        this.startProtectedAlarmPolling(taskUuid)
      }
    },

    resetProtectedTaskContext(clearAlarms = true) {
      this.isProtectedAreaTask = false
      this.currentTaskUuid = ''
      this.currentTaskInfo = null
      this.stopProtectedAlarmPolling()
      this.resetProtectedAlarmTracking()
      this.hideProtectedAlarmToast()
      if (clearAlarms) {
        this.clearAlarmData()
      }
    },

    isDroneWorking(dock) {
      if (dock?.drone_in_dock === 0 || dock?.drone_in_dock === '0') return true
      return this.hasRecentTelemetry(dock?.drone_sn)
    },

    getDroneStateLabel(dock) {
      if (this.isDroneWorking(dock)) return '任务中'
      if (dock?.drone_in_dock === 1 || dock?.drone_in_dock === '1') return '机舱内'
      return '状态未知'
    },

    isDockSelected(dock) {
      if (!dock || !this.selectedDock) return false
      if (this.selectedDock.id && dock.id) {
        return this.selectedDock.id === dock.id
      }
      return this.selectedDock.dock_sn && dock.dock_sn && this.selectedDock.dock_sn === dock.dock_sn
    },

    formatPositionTime(timestamp) {
      return this.formatAlarmTime(timestamp)
    },

    formatFlightDuration(durationMs = this.flightDurationMs) {
      if (!this.flightStartTimestamp) return '--'
      const safeMs = Number.isFinite(durationMs) ? durationMs : 0
      const totalSeconds = Math.max(0, Math.floor(safeMs / 1000))
      const hours = Math.floor(totalSeconds / 3600)
      const minutes = Math.floor((totalSeconds % 3600) / 60)
      const seconds = totalSeconds % 60
      return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
    },

    formatFlightDistance(distanceKm = this.flightDistanceKm) {
      if (!this.flightStartTimestamp) return '--'
      const safeKm = Number.isFinite(distanceKm) ? distanceKm : 0
      return `${safeKm.toFixed(3)} km`
    },

    formatPositionCoords(position) {
      const lat = this.toNumber(position?.latitude)
      const lon = this.toNumber(position?.longitude)
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return '--'
      return `${lat.toFixed(6)}, ${lon.toFixed(6)}`
    },

    formatPositionAltitude(position) {
      const altitude = this.toNumber(position?.altitude)
      if (Number.isFinite(altitude)) {
        return `${altitude.toFixed(1)} m`
      }
      const relative = this.toNumber(position?.relative_height)
      return Number.isFinite(relative) ? `${relative.toFixed(1)} m` : '--'
    },

    async loadComponentConfig() {
      try {
        this.componentConfig = await componentConfigApi.getConfig();
      } catch (err) {
        console.warn('获取组件配置失败，将使用默认配置', err);
      }
    },
    // async setupImageryLayers(Cesium) {
    //   if (!this.viewer) return
    //   const layers = this.viewer.imageryLayers
    //   layers.removeAll()
    //   const localTilesUrl = 'http://192.168.10.10:5000/tiles/{z}/{x}/{y}'
    //   const extent = Cesium.Rectangle.fromDegrees(122.0, 41.0, 124.0, 43.0)
    //   try {
    //     const layer = new Cesium.UrlTemplateImageryProvider({
    //       url: localTilesUrl,
    //       tilingScheme: new Cesium.WebMercatorTilingScheme(),
    //       rectangle: extent,
    //       minimumLevel: 0,
    //       maximumLevel: 19
    //     })
    //     layers.addImageryProvider(layer)
    //   } catch (e) {
    //     console.warn('地图加载失败', e)
    //   }
    // },
    async setupImageryLayers(Cesium) {
      if (!this.viewer) return;
      const layers = this.viewer.imageryLayers;
      layers.removeAll();

      try {
        // 方案 B：使用 ArcGIS 全球卫星底图 (无需申请 Key，稳定且快)
        const arcgisProvider = await Cesium.ArcGisMapServerImageryProvider.fromUrl(
            'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer'
        );
        layers.addImageryProvider(arcgisProvider);

        // 叠加一层透明的混合路网（可选，为了看地名）
        const roads = await Cesium.ArcGisMapServerImageryProvider.fromUrl(
          'https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Hybrid_Reference/MapServer'
        );
        layers.addImageryProvider(roads);

      } catch (e) {
        console.warn('地图加载失败', e);
      }
    },
    tuneCameraControls(controller) {
      if (!controller) return;
      const applyNumber = (key, value) => {
        if (typeof controller[key] === 'number') {
          controller[key] = value;
        }
      };
      applyNumber('inertiaSpin', 0.1);
      applyNumber('inertiaTranslate', 0.12);
      applyNumber('inertiaZoom', 0.3);
      applyNumber('minimumZoomRate', 0.1);
      applyNumber('maximumZoomRate', 80000);
      applyNumber('zoomFactor', 2.0);
      applyNumber('rotateFactor', 0.15);
      applyNumber('tiltFactor', 0.15);
      applyNumber('lookFactor', 0.2);
      applyNumber('translateFactor', 0.2);
      applyNumber('_zoomFactor', 2.0);
      applyNumber('_rotateFactor', 0.15);
      applyNumber('_tiltFactor', 0.15);
      applyNumber('_lookFactor', 0.2);
      applyNumber('_translateFactor', 0.2);
      applyNumber('minimumRotateRate', 0.005);
      applyNumber('maximumRotateRate', 0.2);
      applyNumber('minimumTiltRate', 0.05);
      applyNumber('maximumTiltRate', 0.2);
      applyNumber('rotateRateRangeAdjustment', 0.2);
      applyNumber('_rotateRateRangeAdjustment', 0.2);
      applyNumber('tiltRateRangeAdjustment', 0.2);
      applyNumber('_tiltRateRangeAdjustment', 0.2);
    },

    async fetchAlarmsByWayline(waylineId) {
      if (this.currentMode === 'monitor') return
      if (!waylineId) {
        this.alarms = [];
        this.clearAlarmMarkers();
        return;
      }
      this.loadingAlarms = true;
      try {
        const response = await alarmApi.getAlarms({ wayline: waylineId });
        if (!this.selectedWayline || String(this.selectedWayline.id) !== String(waylineId)) {
          return;
        }
        this.alarms = Array.isArray(response) ? response : (response.results || []);
        this.plotAlarmMarkers(this.alarms);
      } catch (error) {
        console.error('获取告警信息失败:', error);
        this.alarms = [];
        this.clearAlarmMarkers();
      } finally {
        this.loadingAlarms = false;
      }
    },

    getFilteredAlarms() {
      return this.alarms;
    },

    handleAlarmRefresh() {
      if (this.currentMode === 'monitor') {
        if (this.isProtectedAreaTask && this.currentTaskUuid) {
          this.fetchProtectedTaskAlarms()
        }
        return
      }
      if (this.selectedWayline) {
        this.fetchAlarmsByWayline(this.selectedWayline.id);
      }
      if (this.alarms.length) {
        this.plotAlarmMarkers(this.alarms);
      }
    },

    async initSelectedWaylineFromRoute() {
      try {
        const id = this.$route?.query?.wayline_id;
        if (!id) return;
        const detail = await alarmApi.getWaylineDetail(id);
        if (detail && detail.id) {
          this.selectedWayline = detail;
          this.fetchAlarmsByWayline(detail.id);
          this.ensureWaylineWithPoints(detail);
          this.fetchActionDetails(detail.id);
        }
      } catch (e) {
        console.warn('根据路由初始化航线失败', e);
      }
    },
    async fetchActionDetails(waylineId) {
      try {
        const res = await waylineApi.getWaylineActionDetails(waylineId);
        if (!this.selectedWayline || String(this.selectedWayline.id) !== String(waylineId)) {
          return;
        }
        this.actionDetails = Array.isArray(res?.action_details) ? res.action_details : [];
        this.plotActionDetailMarkers(this.actionDetails);
      } catch (e) {
        console.warn('获取航线动作详情失败', e);
        this.actionDetails = [];
        this.clearActionDetailMarkers();
      }
    },
    plotActionDetailMarkers(details) {
      if (!this.viewer) return;
      const Cesium = this.cesiumLib || window.Cesium;
      if (!Cesium) return;
      this.clearActionDetailMarkers();
      const rawPoints = [];
      details.forEach(d => {
        const payload = this.getWaylinePointPayload(d);
        if (!Number.isFinite(payload.latitude) || !Number.isFinite(payload.longitude)) return;
        rawPoints.push({
          longitude: payload.longitude,
          latitude: payload.latitude,
          altitude: payload.altitude
        });
      });

      const mergeThresholdMeters = 0.5;
      const points = this.mergeCloseWaypoints(rawPoints, mergeThresholdMeters);
      const triangleImage = this.getInvertedTriangleImage();
      const entities = [];
      points.forEach(point => {
        const top = Cesium.Cartesian3.fromDegrees(point.longitude, point.latitude, point.altitude);
        const bottom = Cesium.Cartesian3.fromDegrees(point.longitude, point.latitude, 0);
        const line = this.viewer.entities.add({
          polyline: {
            positions: [top, bottom],
            width: 1.5,
            material: Cesium.Color.WHITE.withAlpha(0.85),
            depthFailMaterial: Cesium.Color.WHITE.withAlpha(0.35),
            clampToGround: false
          }
        });
        entities.push(line);

        const labelHeight = Math.max(point.altitude * 0.5, 1);
        const label = this.viewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(point.longitude, point.latitude, labelHeight),
          label: {
            text: Number.isFinite(point.altitude) ? `${point.altitude.toFixed(1)} m` : '--',
            font: '12px sans-serif',
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            horizontalOrigin: Cesium.HorizontalOrigin.LEFT,
            pixelOffset: new Cesium.Cartesian2(6, -6),
            disableDepthTestDistance: Number.POSITIVE_INFINITY
          }
        });
        entities.push(label);

        const marker = this.viewer.entities.add({
          position: top,
          billboard: triangleImage ? {
            image: triangleImage,
            width: 18,
            height: 14,
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            disableDepthTestDistance: Number.POSITIVE_INFINITY
          } : undefined,
          point: triangleImage ? undefined : {
            pixelSize: 7,
            color: Cesium.Color.CYAN.withAlpha(0.95),
            outlineColor: Cesium.Color.WHITE,
            outlineWidth: 1,
            disableDepthTestDistance: Number.POSITIVE_INFINITY
          }
        });
        entities.push(marker);
      });
      this.actionDetailEntities = entities;
    },
    clearActionDetailMarkers() {
      if (this.viewer && this.actionDetailEntities.length) {
        this.actionDetailEntities.forEach(e => this.viewer.entities.remove(e));
      }
      this.actionDetailEntities = [];
    },
    getInvertedTriangleImage() {
      if (this.invertedTriangleImage) return this.invertedTriangleImage;
      if (typeof document === 'undefined') return null;
      const canvas = document.createElement('canvas');
      canvas.width = 24;
      canvas.height = 18;
      const ctx = canvas.getContext('2d');
      if (!ctx) return null;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.beginPath();
      ctx.moveTo(canvas.width / 2, canvas.height - 2);
      ctx.lineTo(2, 2);
      ctx.lineTo(canvas.width - 2, 2);
      ctx.closePath();
      ctx.fillStyle = 'rgba(34, 211, 238, 0.95)';
      ctx.fill();
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.95)';
      ctx.lineWidth = 2;
      ctx.stroke();
      this.invertedTriangleImage = canvas;
      return canvas;
    },
    getAlertTriangleIcon(size = 28) {
      if (!size || typeof document === 'undefined') return null;
      if (!this.alertTriangleIconCache) {
        this.alertTriangleIconCache = {};
      }
      const key = String(size);
      if (this.alertTriangleIconCache[key]) return this.alertTriangleIconCache[key];
      const canvas = document.createElement('canvas');
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext('2d');
      if (!ctx) return null;
      const padding = Math.max(2, Math.round(size * 0.08));
      const topY = padding;
      const leftX = padding;
      const rightX = size - padding;
      const bottomY = size - padding;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.beginPath();
      ctx.moveTo(size / 2, topY);
      ctx.lineTo(rightX, bottomY);
      ctx.lineTo(leftX, bottomY);
      ctx.closePath();
      ctx.fillStyle = '#ef4444';
      ctx.fill();
      ctx.lineJoin = 'round';
      ctx.lineWidth = Math.max(2, Math.round(size * 0.1));
      ctx.strokeStyle = '#0b0b0b';
      ctx.stroke();
      ctx.fillStyle = '#ffffff';
      ctx.font = `bold ${Math.round(size * 0.55)}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('!', size / 2, size * 0.6);
      this.alertTriangleIconCache[key] = canvas;
      return canvas;
    },
    getActionDetailAltitude(detail) {
      const candidates = [
        detail?.height,
        detail?.altitude,
        detail?.ellipsoid_height,
        detail?.z
      ];
      for (const candidate of candidates) {
        const value = this.toNumber(candidate);
        if (Number.isFinite(value)) {
          return value;
        }
      }
      return NaN;
    },
    getWaylinePointPayload(point) {
      const longitude = this.toNumber(point?.lon ?? point?.longitude ?? point?.long ?? point?.x);
      const latitude = this.toNumber(point?.lat ?? point?.latitude ?? point?.y);
      // 设定机场的物理安装高度（相对于地面的高度）
      // 获取航点的相对高度（如 15 米）
      const relativeAltitude = this.getActionDetailAltitude(point);
      // TODO: 目前写死为 20 米，后续可根据实际业务从配置或接口获取
      const dockInstallHeight = 0;
      const renderAltitude = Number.isFinite(relativeAltitude) 
                               ? (relativeAltitude + dockInstallHeight) 
                               : dockInstallHeight;
      return {
        longitude,
        latitude,
        altitude: renderAltitude,
        heading: Number(point?.aircraft_heading || point?.heading || 0),
        gimbalPitch: Number(point?.gimbal_pitch || 0)
      };
    },
    mergeCloseWaypoints(points, thresholdMeters = 0.5) {
      if (!Array.isArray(points) || points.length === 0) return [];
      const merged = [];
      points.forEach(point => {
        if (!merged.length) {
          merged.push(point);
          return;
        }
        const last = merged[merged.length - 1];
        const distance = this.getWaypointDistanceMeters(last, point);
        if (Number.isFinite(distance) && distance <= thresholdMeters) {
          return;
        }
        merged.push(point);
      });
      return merged;
    },
    getWaypointDistanceMeters(pointA, pointB) {
      const lon1 = this.toNumber(pointA?.longitude);
      const lat1 = this.toNumber(pointA?.latitude);
      const lon2 = this.toNumber(pointB?.longitude);
      const lat2 = this.toNumber(pointB?.latitude);
      if (!Number.isFinite(lon1) || !Number.isFinite(lat1) || !Number.isFinite(lon2) || !Number.isFinite(lat2)) {
        return NaN;
      }
      const alt1 = this.toNumber(pointA?.altitude);
      const alt2 = this.toNumber(pointB?.altitude);
      const Cesium = this.cesiumLib || window.Cesium;
      if (Cesium?.Cartesian3) {
        const a = Cesium.Cartesian3.fromDegrees(lon1, lat1, Number.isFinite(alt1) ? alt1 : 0);
        const b = Cesium.Cartesian3.fromDegrees(lon2, lat2, Number.isFinite(alt2) ? alt2 : 0);
        return Cesium.Cartesian3.distance(a, b);
      }
      const rad = Math.PI / 180;
      const phi1 = lat1 * rad;
      const phi2 = lat2 * rad;
      const dPhi = (lat2 - lat1) * rad;
      const dLambda = (lon2 - lon1) * rad;
      const sinDphi = Math.sin(dPhi / 2);
      const sinDlambda = Math.sin(dLambda / 2);
      const aVal = sinDphi * sinDphi + Math.cos(phi1) * Math.cos(phi2) * sinDlambda * sinDlambda;
      const c = 2 * Math.atan2(Math.sqrt(aVal), Math.sqrt(1 - aVal));
      const horizontal = 6371000 * c;
      if (Number.isFinite(alt1) && Number.isFinite(alt2)) {
        const dz = alt2 - alt1;
        return Math.sqrt(horizontal * horizontal + dz * dz);
      }
      return horizontal;
    },

    handleLocateAlarm(alarm) {
      const { latitude, longitude, altitude } = this.getAlarmPosition(alarm);
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || !this.viewer) return;
      const Cesium = this.cesiumLib || window.Cesium;
      if (!Cesium) return;
      const baseHeight = Number.isFinite(altitude) ? altitude : 0;
      const range = Math.max(baseHeight + 220, 260);
      const target = Cesium.Cartesian3.fromDegrees(longitude, latitude, baseHeight);
      const sphere = new Cesium.BoundingSphere(target, 20);
      this.viewer.camera.flyToBoundingSphere(sphere, {
        duration: 1.2,
        offset: new Cesium.HeadingPitchRange(
          Cesium.Math.toRadians(0),
          Cesium.Math.toRadians(-35),
          range
        )
      });
    },
    plotAlarmMarkers(alarms) {
      if (!this.viewer) return;
      const Cesium = this.cesiumLib || window.Cesium;
      if (!Cesium) return;
      if (this.currentMode === 'monitor' && !this.isProtectedAreaTask) {
        this.clearAlarmMarkers()
        return
      }
      this.clearAlarmMarkers();
      const entities = [];
      const triangleSize = 32;
      const triangleImage = this.getAlertTriangleIcon(triangleSize);
      alarms.forEach(alarm => {
        const { latitude, longitude, altitude } = this.getAlarmPosition(alarm);
        if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return;
        const position = Cesium.Cartesian3.fromDegrees(
          longitude,
          latitude,
          Number.isFinite(altitude) ? altitude : 0
        );
        const entity = this.viewer.entities.add({
          position,
          alarmData: alarm,
          properties: new Cesium.PropertyBag({
            alarmData: alarm
          }),
          billboard: triangleImage ? {
            image: triangleImage,
            width: triangleSize,
            height: triangleSize,
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            disableDepthTestDistance: Number.POSITIVE_INFINITY
          } : undefined,
          point: triangleImage ? undefined : {
            pixelSize: 10,
            color: Cesium.Color.RED.withAlpha(0.95),
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
            disableDepthTestDistance: Number.POSITIVE_INFINITY
          }
        });
        entity.alarmData = alarm;
        entities.push(entity);
        if (this.alarmEntityMap) {
          this.alarmEntityMap.set(entity, alarm);
        }
      });
      this.alarmEntities = entities;
      if (this.isPickDebugEnabled()) {
        console.log('[AlarmMarkers] plotted', {
          count: entities.length,
          alarmCount: Array.isArray(alarms) ? alarms.length : 0,
          mode: this.currentMode
        });
      }
    },

    clearAlarmMarkers() {
      if (this.viewer && this.alarmEntities.length) {
        this.alarmEntities.forEach(e => this.viewer.entities.remove(e));
      }
      this.alarmEntities = [];
      if (this.alarmEntityMap) {
        this.alarmEntityMap.clear();
      }
    },
    resetDroneTrackingState() {
      this.lastDroneTimestamp = null;
      this.lastDroneHeading = null;
      this.lastDronePosition = null;
      this.lastDroneCartesian = null;
      this.dronePositionProperty = null;
      this.droneOrientationProperty = null;
      this.lastDroneSamplePruneTimestamp = null;
      if (this.viewer?.clock) {
        this.viewer.clock.shouldAnimate = false;
      }
      if (this.viewer?.scene) {
        this.viewer.scene.requestRender();
      }
    },

    clearDigitalTwin() {
      if (this.viewer && this.waylineEntity) {
        this.viewer.entities.remove(this.waylineEntity);
        this.waylineEntity = null;
      }
      if (this.viewer && this.waylinePointEntities.length) {
        this.waylinePointEntities.forEach(entity => this.viewer.entities.remove(entity));
        this.waylinePointEntities = [];
      }
      if (this.viewer && this.droneEntity) {
        this.viewer.entities.remove(this.droneEntity);
        this.droneEntity = null;
      }
      if (this.viewer && this.chaseCameraListener) {
        this.viewer.scene.preUpdate.removeEventListener(this.chaseCameraListener);
        this.chaseCameraListener = null;
      }
      this.clearActionDetailMarkers();
      this.actionDetails = [];
      this.selectedWayline = null;
      this.currentWaylineUuid = '';
      this.waylinePointSource = '';
      this.resetDroneTrackingState();
    },

    clearAlarmData() {
      this.alarms = [];
      this.clearAlarmMarkers();
      this.showAlarmDetail = false;
      this.currentAlarm = null;
      this.loadingAlarms = false;
    },

    clearDigitalTwinAndAlarms() {
      this.clearDigitalTwin();
      this.clearAlarmData();
      this.resetProtectedTaskContext(false);
    },

    setupPickHandler(Cesium) {
      if (!this.viewer || this.pickHandler) return;
      this.pickHandler = new Cesium.ScreenSpaceEventHandler(this.viewer.scene.canvas);
      this.pickHandler.setInputAction(click => {
        if (this.isPickDebugEnabled()) {
          console.log('[AlarmPick] click position', click?.position);
        }
        const pickPosition = this.normalizePickPosition(click?.position, Cesium);
        if (this.isPickDebugEnabled()) {
          console.log('[AlarmPick] normalized position', pickPosition);
        }
        const picks = this.viewer.scene.drillPick
          ? this.viewer.scene.drillPick(pickPosition)
          : [this.viewer.scene.pick(pickPosition)];
        if (this.isPickDebugEnabled()) {
          const summary = Array.isArray(picks) ? picks.map(picked => {
            const entity = picked?.id || picked?.primitive?.id || picked?.primitive;
            return {
              type: picked?.constructor?.name,
              entityType: entity?.constructor?.name,
              hasAlarmData: Boolean(
                entity?.alarmData
                || entity?.properties?.alarmData?.getValue?.(Cesium.JulianDate.now())
                || entity?.properties?.alarmData
              )
            };
          }) : [];
          console.log('[AlarmPick] pick summary', summary);
        }
        if (!Array.isArray(picks) || !picks.length) return;
        for (const picked of picks) {
          if (!Cesium.defined(picked)) continue;
          const entity = picked.id || picked.primitive?.id || picked.primitive;
          if (!entity) continue;
          let alarmData = entity.alarmData
            || entity?.properties?.alarmData?.getValue?.(Cesium.JulianDate.now())
            || entity?.properties?.alarmData;
          if (!alarmData && this.alarmEntityMap) {
            const mapped = this.alarmEntityMap.get(entity);
            if (mapped) {
              alarmData = mapped;
            }
          }
          if (alarmData) {
            if (this.isPickDebugEnabled()) {
              console.log('[AlarmPick] open from picked entity');
            }
            this.handleViewAlarmDetail(alarmData);
            break;
          }
        }
        if (!this.showAlarmDetail) {
          const fallbackAlarm = this.findClosestAlarmByScreenPosition(pickPosition);
          if (fallbackAlarm) {
            if (this.isPickDebugEnabled()) {
              console.log('[AlarmPick] open from fallback');
            }
            this.handleViewAlarmDetail(fallbackAlarm);
          }
        }
      }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
    },

    isPickDebugEnabled() {
      return typeof window !== 'undefined' && window.__DJI_DASHBOARD_PICK_DEBUG === true;
    },

    normalizePickPosition(position, Cesium) {
      if (!position || !this.viewer || !Cesium?.Cartesian2) return position;
      const canvas = this.viewer.scene?.canvas;
      if (!canvas || typeof canvas.getBoundingClientRect !== 'function') return position;
      const rect = canvas.getBoundingClientRect();
      if (!rect || !rect.width || !rect.height) return position;
      const scaleX = canvas.clientWidth / rect.width;
      const scaleY = canvas.clientHeight / rect.height;
      if (!Number.isFinite(scaleX) || !Number.isFinite(scaleY)) return position;
      if (scaleX === 1 && scaleY === 1) return position;
      if (this.isPickDebugEnabled()) {
        console.log('[AlarmPick] pick scale', { scaleX, scaleY, rect });
      }
      return new Cesium.Cartesian2(position.x * scaleX, position.y * scaleY);
    },

    findClosestAlarmByScreenPosition(position, thresholdPx = 18) {
      if (!this.viewer || !position) return null;
      const hasEntities = Array.isArray(this.alarmEntities) && this.alarmEntities.length > 0;
      const hasAlarms = Array.isArray(this.alarms) && this.alarms.length > 0;
      if (!hasEntities && !hasAlarms) return null;
      const thresholdOverride = typeof window !== 'undefined'
        ? Number(window.__DJI_DASHBOARD_PICK_THRESHOLD)
        : NaN;
      const effectiveThreshold = Number.isFinite(thresholdOverride)
        ? thresholdOverride
        : thresholdPx;
      const Cesium = this.cesiumLib || window.Cesium;
      const transforms = Cesium?.SceneTransforms;
      const canWgs84ToWindow = typeof transforms?.wgs84ToWindowCoordinates === 'function';
      const canWorldToWindow = typeof transforms?.worldToWindowCoordinates === 'function';
      const canDrawingBuffer = typeof transforms?.wgs84ToDrawingBufferCoordinates === 'function';
      const canCartesianToCanvas = typeof this.viewer?.scene?.cartesianToCanvasCoordinates === 'function';
      if (!canWgs84ToWindow && !canWorldToWindow && !canDrawingBuffer && !canCartesianToCanvas) return null;
      const toWindow = (cartesian) => {
        if (!cartesian) return null;
        if (canWorldToWindow) {
          return transforms.worldToWindowCoordinates(this.viewer.scene, cartesian);
        }
        if (canCartesianToCanvas) {
          return this.viewer.scene.cartesianToCanvasCoordinates(cartesian);
        }
        if (canWgs84ToWindow) {
          return transforms.wgs84ToWindowCoordinates(this.viewer.scene, cartesian);
        }
        if (canDrawingBuffer) {
          const bufferPos = transforms.wgs84ToDrawingBufferCoordinates(this.viewer.scene, cartesian);
          if (bufferPos) {
            const canvas = this.viewer.scene.canvas;
            const scaleX = canvas.clientWidth / canvas.width;
            const scaleY = canvas.clientHeight / canvas.height;
            return { x: bufferPos.x * scaleX, y: bufferPos.y * scaleY };
          }
        }
        return null;
      };
      let closest = null;
      let minDistance = Number.POSITIVE_INFINITY;
      if (hasEntities) {
        for (const entity of this.alarmEntities) {
          const cartesian = entity?.position?.getValue
            ? entity.position.getValue(Cesium.JulianDate.now())
            : entity?.position;
          const windowPos = toWindow(cartesian);
          if (!windowPos) continue;
          const dx = windowPos.x - position.x;
          const dy = windowPos.y - position.y;
          const dist = Math.hypot(dx, dy);
          if (dist < minDistance) {
            minDistance = dist;
            closest = entity?.alarmData
              || entity?.properties?.alarmData?.getValue?.(Cesium.JulianDate.now())
              || entity?.properties?.alarmData
              || (this.alarmEntityMap ? this.alarmEntityMap.get(entity) : null)
              || null;
          }
        }
      } else if (hasAlarms) {
        for (const alarm of this.alarms) {
          const { latitude, longitude, altitude } = this.getAlarmPosition(alarm);
          if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) continue;
          const cartesian = Cesium.Cartesian3.fromDegrees(
            longitude,
            latitude,
            Number.isFinite(altitude) ? altitude : 0
          );
          const windowPos = toWindow(cartesian);
          if (!windowPos) continue;
          const dx = windowPos.x - position.x;
          const dy = windowPos.y - position.y;
          const dist = Math.hypot(dx, dy);
          if (dist < minDistance) {
            minDistance = dist;
            closest = alarm;
          }
        }
      }
      if (this.isPickDebugEnabled()) {
        console.log('[AlarmPick] fallback distance', {
          minDistance,
          threshold: effectiveThreshold,
          usedEntities: hasEntities,
          usedAlarms: hasAlarms
        });
      }
      return minDistance <= effectiveThreshold ? closest : null;
    },

    toNumber(val) {
      const num = Number(val);
      return Number.isFinite(num) ? num : NaN;
    },

    getAlarmAltitude(alarm) {
      const candidates = [alarm?.high, alarm?.altitude, alarm?.alt];
      for (const candidate of candidates) {
        const value = this.toNumber(candidate);
        if (Number.isFinite(value)) {
          return value;
        }
      }
      return NaN;
    },
getAlarmPosition(alarm) {
      const latitudeCandidates = [
        alarm?.latitude, alarm?.lat, alarm?.y,
        alarm?.location?.latitude, alarm?.location?.lat,
        alarm?.position?.latitude, alarm?.position?.lat
      ];
      const longitudeCandidates = [
        alarm?.longitude, alarm?.lon, alarm?.lng, alarm?.long, alarm?.x,
        alarm?.location?.longitude, alarm?.location?.lon, alarm?.location?.lng,
        alarm?.position?.longitude, alarm?.position?.lon, alarm?.position?.lng
      ];
      
      let latitude = NaN;
      let longitude = NaN;
      
      for (const candidate of latitudeCandidates) {
        const value = this.toNumber(candidate);
        if (Number.isFinite(value)) {
          latitude = value;
          break;
        }
      }
      for (const candidate of longitudeCandidates) {
        const value = this.toNumber(candidate);
        if (Number.isFinite(value)) {
          longitude = value;
          break;
        }
      }

      // 获取告警点的真实绝对高程（包含当地海拔）
      const realAltitude = this.getAlarmAltitude(alarm);
      
      // 定义当地真实海拔偏移量
      const terrainElevationOffset = 40.2;
      
      // 扣除海拔高度，使告警点下沉贴合底图
      const renderAltitude = Number.isFinite(realAltitude) 
                             ? (realAltitude - terrainElevationOffset) 
                             : NaN;

      return {
        latitude,
        longitude,
        altitude: renderAltitude
      };
    },
  }
}
</script>

<style scoped>
.dashboard-premium {
  /* 使用绝对定位钉死在屏幕边缘，避免vh在部分浏览器计算误差导致溢出滚动 */
  position: absolute; 
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px;
  box-sizing: border-box;
  background: radial-gradient(circle at 20% 20%, rgba(0, 212, 255, 0.08), transparent 25%),
  radial-gradient(circle at 80% 0, rgba(0, 153, 255, 0.06), transparent 30%),
  #0b1024;
  color: #e2e8f0;
  overflow: hidden; /* 强制外层不滚动 */
}

/* 页面头部 */
.dashboard-header {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  padding: 24px 32px;
  background: rgba(26, 31, 58, 0.6);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  border: 1px solid rgba(0, 212, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  flex-shrink: 0; /* 保护头部在空间不足时不被挤压 */
}

.detect-type-summary {
  padding: 16px 20px;
  background: rgba(26, 31, 58, 0.6);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  border: 1px solid rgba(0, 212, 255, 0.16);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  flex-shrink: 0;
}

.detect-type-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.detect-type-title {
  font-size: 14px;
  font-weight: 700;
  color: #e2e8f0;
}

.detect-type-subtitle {
  font-size: 12px;
  color: #94a3b8;
}

.detect-type-table-wrap {
  overflow: auto;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.detect-type-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 520px;
  background: rgba(11, 16, 36, 0.35);
}

.detect-type-table th,
.detect-type-table td {
  padding: 10px 12px;
  font-size: 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  color: #cbd5e1;
}

.detect-type-table th {
  text-align: left;
  font-weight: 700;
  color: #e2e8f0;
  background: rgba(26, 31, 58, 0.45);
}

.type-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e2e8f0;
  white-space: nowrap;
}

.type-icon {
  width: 18px;
  display: inline-flex;
  justify-content: center;
}

.code-cell {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  color: #93c5fd;
  white-space: nowrap;
}

.keywords-cell {
  color: #94a3b8;
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

.mode-switch {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px;
  border-radius: 999px;
  background: rgba(10, 14, 39, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.2);
}

.mode-tab {
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: rgba(15, 23, 42, 0.7);
  color: #cbd5e1;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.mode-tab:hover {
  border-color: rgba(0, 212, 255, 0.5);
  color: #e2e8f0;
}

.mode-tab.active {
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.35), rgba(0, 153, 255, 0.45));
  border-color: rgba(0, 212, 255, 0.7);
  color: #ffffff;
  box-shadow: 0 8px 18px rgba(0, 212, 255, 0.25);
}

/* 主内容区 */
.dashboard-content {
  flex: 1;
  display: flex;
  flex-direction: row; /* 从grid修改为flex，更易控高度 */
  gap: 24px;
  min-height: 0; /* flex容器嵌套核心：防止子元素溢出 */
  overflow: hidden;
}

/* 左侧面板 */
.side-panel {
  width: 320px;
  flex-shrink: 0; /* 防止面板被挤压 */
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 0;
  overflow: hidden;
}

.panel-group {
  display: flex;
  flex-direction: column;
  gap: 20px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.panel-section {
  background: rgba(26, 31, 58, 0.6);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  border: 1px solid rgba(0, 212, 255, 0.2);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-header {
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.15) 0%, rgba(0, 153, 255, 0.15) 100%);
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.panel-title {
  font-size: 16px;
  font-weight: 700;
  color: #00d4ff;
  margin: 0;
}

.wayline-badge {
  padding: 4px 12px;
  background: rgba(0, 212, 255, 0.2);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 12px;
  color: #00d4ff;
  font-size: 12px;
  font-weight: 600;
}

.panel-body {
  flex: 1;
  overflow: hidden;
  min-height: 0;
}
.compact-panel {
  padding: 0;
}
.left-panel {
  min-height: 0;
}

.dock-panel {
  flex: 1.15 1 0;
  min-height: 0;
}

.dock-panel-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.panel-action {
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(0, 212, 255, 0.3);
  background: rgba(0, 212, 255, 0.12);
  color: #00d4ff;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.panel-action:hover:not(:disabled) {
  background: rgba(0, 212, 255, 0.2);
  border-color: rgba(0, 212, 255, 0.5);
}

.panel-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.panel-placeholder {
  padding: 12px;
  border-radius: 10px;
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
  background: rgba(10, 14, 39, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.15);
}

.panel-placeholder.small {
  padding: 8px;
  font-size: 11px;
}

.panel-placeholder.error {
  color: #fca5a5;
  border-color: rgba(248, 113, 113, 0.35);
}

.dock-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.dock-item {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(11, 16, 36, 0.6);
  cursor: pointer;
  transition: all 0.2s ease;
}

.dock-item:hover {
  border-color: rgba(0, 212, 255, 0.45);
  background: rgba(15, 23, 42, 0.7);
}

.dock-item.active {
  border-color: rgba(0, 212, 255, 0.7);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.2);
}

.dock-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.dock-item-name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #64748b;
}

.status-dot.online {
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.6);
}

.dock-name {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dock-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgba(249, 115, 22, 0.4);
  color: #f97316;
  background: rgba(249, 115, 22, 0.1);
  flex-shrink: 0;
}

.dock-status.online {
  border-color: rgba(34, 197, 94, 0.4);
  color: #22c55e;
  background: rgba(34, 197, 94, 0.12);
}

.dock-item-meta {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 11px;
  color: #94a3b8;
}

.dock-sn,
.drone-sn {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.drone-state {
  font-size: 11px;
  color: #cbd5e1;
}

.drone-state.working {
  color: #22c55e;
}

.dock-latest {
  padding-top: 10px;
  border-top: 1px solid rgba(148, 163, 184, 0.15);
  flex-shrink: 0;
}

.dock-latest-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  gap: 8px;
}

.dock-latest-tags {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dock-latest-title {
  font-size: 12px;
  color: #94a3b8;
}

.dock-latest-sn {
  font-size: 11px;
  color: #38bdf8;
  font-family: monospace;
}

.dock-latest-state {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  color: #94a3b8;
}

.dock-latest-state.working {
  border-color: rgba(34, 197, 94, 0.5);
  color: #22c55e;
  background: rgba(34, 197, 94, 0.08);
}

.position-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.position-item {
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid rgba(0, 212, 255, 0.2);
  background: rgba(15, 23, 42, 0.65);
}

.position-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 11px;
  color: #cbd5e1;
}

.position-label {
  color: #94a3b8;
}

.alarm-panel {
  flex: 1 1 0;
  min-height: 0;
}

.analysis-panel-group {
  min-height: 0;
}

.analysis-filter-panel {
  flex: 0 0 auto;
}

.analysis-filter-body {
  padding: 12px;
}

.detect-type-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.detect-type-item {
  padding: 12px 10px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(11, 16, 36, 0.6);
  color: #cbd5e1;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-align: left;
}

.detect-type-item:hover {
  border-color: rgba(0, 212, 255, 0.5);
  background: rgba(15, 23, 42, 0.75);
}

.detect-type-item.active {
  border-color: rgba(0, 212, 255, 0.8);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.2);
  color: #e2e8f0;
}

.detect-type-name {
  font-size: 13px;
  font-weight: 600;
}

.detect-type-code {
  font-size: 11px;
  color: #94a3b8;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.analysis-wayline-panel {
  flex: 1 1 0;
  min-height: 0;
}

.analysis-wayline-body {
  padding: 12px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.analysis-wayline-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.analysis-wayline-item {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(11, 16, 36, 0.6);
  cursor: pointer;
  transition: all 0.2s ease;
}

.analysis-wayline-item:hover {
  border-color: rgba(0, 212, 255, 0.45);
  background: rgba(15, 23, 42, 0.7);
}

.analysis-wayline-item.active {
  border-color: rgba(0, 212, 255, 0.7);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.2);
}

.analysis-wayline-title {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 6px;
}

.analysis-wayline-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 11px;
  color: #94a3b8;
}

.analysis-wayline-id {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.analysis-wayline-type {
  color: #7dd3fc;
}

.analysis-alarm-panel {
  flex: 1 1 0;
  min-height: 0;
}

.alarm-panel-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
}

.alarm-panel-body > * {
  flex: 1 1 auto;
  min-height: 0;
}

.monitor-body {
  padding: 40px 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 150px;
}

.placeholder-text {
  color: #64748b;
  font-size: 14px;
  text-align: center;
  margin: 0;
}

.dji-placeholder {
  padding: 40px 20px;
  text-align: center;
  color: #94a3b8;
  background: rgba(10, 14, 39, 0.6);
  border-radius: 12px;
}

/* 中间主视图 */
.main-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 0;
  overflow: hidden;
}

/* 视频和3D网格 */
.viewer-grid {
  display: flex;
  flex-direction: row;
  gap: 20px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.viewer-grid > * {
  flex: 1;
  min-height: 0;
}

.viewer-grid.analysis-mode .live-monitor-section {
  display: none; /* 分析模式隐藏直播，让3D视图自然撑满全宽 */
}

.cesium-section {
  flex: 1;
  min-height: 0;
  background: rgba(26, 31, 58, 0.6);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  border: 1px solid rgba(0, 212, 255, 0.2);
  overflow: hidden;
  position: relative;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.cesium-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.create-task-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 4;
  pointer-events: none;
  background: rgba(6, 10, 24, 0.25);
}

.create-task-button {
  pointer-events: auto;
  padding: 18px 40px;
  font-size: 18px;
  font-weight: 600;
  border-radius: 16px;
  border: 1px solid rgba(56, 189, 248, 0.6);
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.9), rgba(37, 99, 235, 0.9));
  color: #ffffff;
  cursor: pointer;
  box-shadow: 0 12px 30px rgba(0, 212, 255, 0.25);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.create-task-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 32px rgba(0, 212, 255, 0.3);
}

.cesium-controls {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  z-index: 5;
}

.protected-alarm-toast {
  position: absolute;
  top: 12px;
  left: 12px;
  max-width: 320px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid rgba(239, 68, 68, 0.55);
  background: linear-gradient(135deg, rgba(127, 29, 29, 0.9), rgba(220, 38, 38, 0.9));
  color: #fee2e2;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 12px 30px rgba(239, 68, 68, 0.35);
  opacity: 0;
  transform: translateY(-12px);
  transition: opacity 0.3s ease, transform 0.3s ease;
  pointer-events: none;
  z-index: 6;
}

.protected-alarm-toast.show {
  opacity: 1;
  transform: translateY(0);
}

.control-btn {
  padding: 8px 12px;
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 10px;
  background: rgba(26, 31, 58, 0.8);
  color: #e0f2fe;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.control-btn:hover {
  background: rgba(0, 212, 255, 0.15);
  border-color: rgba(0, 212, 255, 0.5);
}
.control-btn.is-active {
  background: rgba(0, 212, 255, 0.3);
  border-color: rgba(0, 212, 255, 0.7);
  color: #ffffff;
  box-shadow: 0 0 12px rgba(0, 212, 255, 0.25);
}

/* 加载和错误覆盖层 */
.loading-overlay,
.error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(10, 14, 39, 0.9);
  backdrop-filter: blur(10px);
  z-index: 10;
}

.loading-content,
.error-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: #e2e8f0;
  font-size: 16px;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(0, 212, 255, 0.2);
  border-top-color: #00d4ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-icon {
  font-size: 48px;
}

/* 模态框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(10, 14, 39, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.modal-premium {
  background: rgba(26, 31, 58, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(0, 212, 255, 0.3);
  box-shadow: 0 16px 64px rgba(0, 0, 0, 0.5);
  width: 100%;
  max-width: 700px;
  animation: modalSlideIn 0.3s ease;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(0, 153, 255, 0.1) 100%);
}

.modal-title {
  font-size: 18px;
  font-weight: 700;
  color: #00d4ff;
  margin: 0;
}

.modal-close {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  font-size: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.modal-close:hover {
  background: rgba(239, 68, 68, 0.3);
  transform: rotate(90deg);
}

.modal-body {
  padding: 24px;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.full-width {
  grid-column: 1 / -1;
}

.detail-label {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  color: #e2e8f0;
  font-size: 14px;
}

.alarm-image {
  margin-top: 8px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(0, 212, 255, 0.2);
  cursor: zoom-in;
  transition: all 0.2s ease;
}

.alarm-image:hover {
  border-color: rgba(0, 212, 255, 0.35);
  box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.08);
}

.alarm-image:focus-visible {
  outline: 2px solid rgba(0, 212, 255, 0.6);
  outline-offset: 2px;
}

.alarm-image img {
  width: 100%;
  height: auto;
  display: block;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
}

.modal-btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
}

.secondary-btn {
  background: rgba(100, 116, 139, 0.3);
  color: #e2e8f0;
  border: 1px solid rgba(100, 116, 139, 0.5);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.secondary-btn:hover {
  background: rgba(100, 116, 139, 0.4);
  transform: translateY(-1px);
}

/* 直播监控区域样式 */
.live-monitor-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.live-monitor-section .panel-body {
  padding: 0;
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(0, 212, 255, 0.05);
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
}

.monitor-title {
  font-size: 14px;
  font-weight: 600;
  color: #00d4ff;
}

.monitor-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.monitor-commands {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.command-btn {
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  color: #e2e8f0;
  background: rgba(15, 23, 42, 0.7);
}

.command-btn.warning {
  border-color: rgba(245, 158, 11, 0.6);
  color: #fbbf24;
}

.command-btn.default {
  border-color: rgba(148, 163, 184, 0.5);
  color: #e2e8f0;
}

.command-btn.info {
  border-color: rgba(56, 189, 248, 0.6);
  color: #7dd3fc;
}

.command-btn.success {
  border-color: rgba(34, 197, 94, 0.6);
  color: #86efac;
}

.command-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.stream-toggle {
  display: flex;
  gap: 8px;
}

.stream-btn {
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid rgba(0, 212, 255, 0.3);
  background: rgba(11, 16, 36, 0.8);
  color: #e2e8f0;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.stream-btn.active {
  background: rgba(0, 212, 255, 0.2);
  border-color: rgba(0, 212, 255, 0.6);
  color: #00d4ff;
}

.stream-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.live-player-wrapper {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 12px;
  display: flex;
  flex-direction: column;
}

/* 屏幕变小时，平分布局，绝对防止内容溢出 */
@media (max-width: 1180px) {
  .dashboard-content {
    flex-direction: column; /* 小屏上下堆叠 */
  }

  .mode-switch {
    width: 100%;
    margin-left: 0;
    justify-content: flex-start;
  }

  .panel-group {
    display: flex;
    flex-direction: column;
    gap: 20px;
    flex: 1; 
    min-height: 0;
    overflow: hidden;
  }

  .side-panel {
    width: 100%;
    flex: 1; 
    order: 2;
    min-height: 0;
    overflow: hidden;
  }

  .main-view {
    width: 100%;
    flex: 1; 
    order: 1;
    min-height: 0;
  }

  .viewer-grid {
    flex-direction: column;
    min-height: 0;
  }

  .alarm-panel-body {
    max-height: none;
    min-height: 0;
  }
}
</style>

<style>
/* 强制覆盖Cesium默认样式，确保充满容器 */
.cesium-viewer,
.cesium-viewer-cesiumWidgetContainer,
.cesium-widget,
.cesium-widget canvas {
  width: 100% !important;
  height: 100% !important;
  position: absolute !important;
  top: 0 !important;
  left: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}

/* 确保全局绝对无滚动条（严格控制外层） */
body, html, #app {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden !important; /* 切断浏览器默认滚动 */
  box-sizing: border-box;
}
</style>
