<template>
  <div class="live-stream-player">
    <div class="player-header">
      <div class="header-left">
        <span class="stream-label">{{ streamName || '保护区直播' }}</span>
        <span v-if="isPlaying" class="live-badge">
          <span class="live-dot"></span>
          LIVE
        </span>
        <span v-if="isMonitoring" class="monitor-badge">
          <span class="monitor-dot"></span>
          检测中
        </span>
      </div>
      <div class="header-right">
        <button
          @click="toggleMonitor"
          class="monitor-control-btn"
          :class="{ 'active': isMonitoring, 'loading': monitorLoading }"
          :disabled="monitorLoading"
          :title="isMonitoring ? '停止保护区检测' : '开始保护区检测'"
        >
          <svg v-if="!monitorLoading" viewBox="0 0 24 24" fill="currentColor">
            <path v-if="!isMonitoring" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            <path v-else d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm5 11H7v-2h10v2z"/>
          </svg>
          <div v-else class="mini-spinner"></div>
          <span>{{ isMonitoring ? '停止检测' : '开始检测' }}</span>
        </button>

        <button @click="togglePlay" class="control-icon-btn" :title="isPlaying ? '暂停' : '播放'">
          <svg v-if="!isPlaying" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor">
            <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
          </svg>
        </button>
        <button @click="toggleMute" class="control-icon-btn" :title="isMuted ? '取消静音' : '静音'">
          <svg v-if="!isMuted" viewBox="0 0 24 24" fill="currentColor">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor">
            <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>
          </svg>
        </button>
        <button @click="reload" class="control-icon-btn" title="重新加载">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
          </svg>
        </button>
      </div>
    </div>

    <div ref="playerContainer" class="player-container" :class="{ 'loading': loading, 'error': hasError }">
      <video
        ref="videoElement"
        class="video-element"
        :muted="isMuted"
        autoplay
        playsinline
        @loadstart="onLoadStart"
        @canplay="onCanPlay"
        @playing="onPlaying"
        @waiting="onWaiting"
        @error="onError"
        @timeupdate="onTimeUpdate"
      ></video>

      <div v-if="loading" class="overlay loading-overlay">
        <div class="loading-spinner"></div>
        <p>正在连接直播流...</p>
      </div>

      <div v-if="hasError" class="overlay error-overlay">
        <div class="error-icon">⚠️</div>
        <p class="error-message">{{ errorMessage }}</p>
        <button @click="reload" class="reload-btn">重新加载</button>
      </div>

      <div v-if="!streamUrl && !loading && !hasError" class="overlay placeholder-overlay">
        <div class="placeholder-icon">📹</div>
        <p>等待直播流推送...</p>
      </div>
    </div>

    <div class="player-footer">
      <div class="stream-info">
        <span class="info-item">
          <span class="info-label">流地址:</span>
          <span class="info-value">{{ streamUrl || '未配置' }}</span>
        </span>
        <span class="info-item">
          <span class="info-label">在线状态:</span>
          <span v-if="checkingStream" class="info-value">
            <span class="mini-spinner-inline"></span>
            检查中...
          </span>
          <span v-else-if="isStreamOnline === true" class="info-value status-online">● 在线</span>
          <span v-else-if="isStreamOnline === false" class="info-value status-offline">● 离线</span>
          <span v-else class="info-value status-unknown">○ 未知</span>
        </span>
        <span v-if="isPlaying" class="info-item">
          <span class="info-label">播放:</span>
          <span class="info-value status-active">正在播放</span>
        </span>
      </div>
    </div>
  </div>
</template>

<script>
import liveMonitorApi from '../api/liveMonitorApi'

export default {
  name: 'LiveStreamPlayer',
  props: {
    // 流ID (例如: drone03, protection_zone_01)
    streamId: {
      type: String,
      default: 'drone03'
    },
    streamUrlOverride: {
      type: String,
      default: ''
    },
    // 流名称显示
    streamName: {
      type: String,
      default: ''
    },
    // 是否自动播放
    autoPlay: {
      type: Boolean,
      default: true
    },
    // ZLM服务器地址
    zlmServer: {
      type: String,
      default: 'http://192.168.10.10'
    }
  },
  data() {
    return {
      isPlaying: false,
      isMuted: false,
      loading: false,
      hasError: false,
      errorMessage: '',
      // 🔥 修复：初始状态为 false，不从 localStorage 恢复
      // 按钮状态完全由用户操作控制
      isMonitoring: false,
      monitorLoading: false,
      monitorCheckTimer: null,
      // 🔥 新增：流状态检查
      isStreamOnline: null,  // null=未检查, true=在线, false=离线
      checkingStream: false,
      // 🔥 新增：卡死检测
      lastTimeUpdate: 0,
      stuckWatchdogTimer: null,
      stuckCount: 0,
      _reloadTimer: null,
      _isUnmounted: false,
      _lastChaseAt: 0
    }
  },
  computed: {
    // 🔥 使用代理路径访问 ZLM，避免跨域问题
    streamUrl() {
      const normalizeToMp4 = (url) => {
        if (!url) return url
        if (url.endsWith('.live.flv')) {
          return url.replace('.live.flv', '.live.mp4')
        }
        return url
      }

      // 如果传入了 Override URL，进行智能处理
      if (this.streamUrlOverride) {
        const url = this.streamUrlOverride
        
        // 🔥 智能转换 RTMP 地址为 HTTP-MP4
        if (url.startsWith('rtmp://')) {
          console.warn('检测到 RTMP 地址，尝试转换为 HTTP-MP4 播放地址:', url)
          try {
            // 解析 rtmp://host:port/app/streamId
            const urlObj = new URL(url)
            const pathParts = urlObj.pathname.split('/').filter(p => p)
            // 通常 pathParts 是 ['live', 'dock01']
            if (pathParts.length >= 2) {
              const app = pathParts[0]
              const stream = pathParts[1]
              
              // 重新构建为 HTTP-MP4
              const isDev = process.env.NODE_ENV === 'development'
              if (isDev) {
                return normalizeToMp4(`/zlm/${app}/${stream}.live.mp4`)
              } else {
                return normalizeToMp4(`${this.zlmServer}/${app}/${stream}.live.mp4`)
              }
            }
          } catch (e) {
            console.error('RTMP 地址解析失败:', e)
          }
        }
        
        // 如果不是 RTMP 或解析失败，原样返回
        return normalizeToMp4(url)
      }

      if (!this.streamId) return ''

      // 🔥 开发环境使用代理，生产环境直接访问
      // 开发环境: /zlm/live/dock01.live.mp4 -> http://192.168.10.10/live/dock01.live.mp4
      // 生产环境: 直接使用 zlmServer 地址
      const isDev = process.env.NODE_ENV === 'development'
      if (isDev) {
        return normalizeToMp4(`/zlm/live/${this.streamId}.live.mp4`)
      } else {
        return normalizeToMp4(`${this.zlmServer}/live/${this.streamId}.live.mp4`)
      }
    }
  },
  mounted() {
    // 直接初始化原生播放器，不需要等待 flv.js
    this.initPlayer()

    // 🔥 优先从服务器获取真实状态,然后同步到本地
    this.syncMonitorStatusFromServer()

    // 定时检查监听状态
    this.monitorCheckTimer = setInterval(() => {
      this.checkMonitorStatus()
    }, 5000)

    // 🔥 启动卡死检测看门狗 (每2秒检查一次)
    this.startStuckWatchdog()
  },
  beforeUnmount() {
    this._isUnmounted = true
    if (this._reloadTimer) {
      clearTimeout(this._reloadTimer)
      this._reloadTimer = null
    }
    this.destroyPlayer()
    this.stopStuckWatchdog()
    if (this.monitorCheckTimer) {
      clearInterval(this.monitorCheckTimer)
    }
  },
  methods: {
    chaseToLive() {
      const video = this.$refs.videoElement
      if (!video) return
      if (!video.buffered || video.buffered.length === 0) return

      const now = Date.now()
      if (now - (this._lastChaseAt || 0) < 1000) return

      const end = video.buffered.end(video.buffered.length - 1)
      const lag = end - video.currentTime
      if (!Number.isFinite(lag) || lag <= 1.5) return

      const target = Math.max(0, end - 0.3)
      if (Number.isFinite(target) && target > 0) {
        try { video.currentTime = target } catch (e) { void e }
        this._lastChaseAt = now
      }
    },

    // ========== 监听状态持久化方法 ==========
    getStorageKey() {
      return `monitor_status_${this.streamId}`
    },

    getStoredMonitorStatus() {
      try {
        const key = this.getStorageKey()
        const stored = localStorage.getItem(key)
        if (stored) {
          const data = JSON.parse(stored)
          // 检查是否过期(超过1小时则认为已失效)
          const now = Date.now()
          if (data.timestamp && (now - data.timestamp) < 3600000) {
            console.log(`从本地恢复监听状态: ${data.isMonitoring}`)
            return data.isMonitoring
          }
        }
      } catch (err) {
        console.warn('读取本地监听状态失败:', err)
      }
      return false
    },

    setStoredMonitorStatus(status) {
      try {
        const key = this.getStorageKey()
        const data = {
          isMonitoring: status,
          timestamp: Date.now(),
          streamId: this.streamId
        }
        localStorage.setItem(key, JSON.stringify(data))
        console.log(`保存监听状态: ${status}`)
      } catch (err) {
        console.warn('保存监听状态失败:', err)
      }
    },

    clearStoredMonitorStatus() {
      try {
        const key = this.getStorageKey()
        localStorage.removeItem(key)
        console.log('清除本地监听状态')
      } catch (err) {
        console.warn('清除监听状态失败:', err)
      }
    },

    // 动态加载 flv.js (已废弃，保留空函数防止报错)
    loadFlvJs() {
      console.log('FMP4 模式：无需加载 flv.js')
    },

    // 🔥【关键修改】原生 MP4 初始化逻辑
    initPlayer() {
      const video = this.$refs.videoElement

      if (this._isUnmounted) return
      if (!video) return
      if (!this.streamUrl) {
        console.warn('流地址为空')
        this.loading = false
        return
      }

      this.destroyPlayer()

      console.log('正在初始化 HTTP-MP4 播放:', this.streamUrl)

      this.loading = true
      this.hasError = false
      this.errorMessage = ''

      video.src = this.streamUrl
      video.load()

      if (!this.autoPlay) {
        this.loading = false
        this.isPlaying = false
        return
      }

      const playRet = video.play()
      if (playRet && typeof playRet.then === 'function') {
        playRet.catch(err => {
          console.warn('自动播放被阻止，可能需要用户交互:', err)
          this.isPlaying = false
          this.loading = false
        })
      }
    },

    // 销毁播放器
    destroyPlayer() {
      const video = this.$refs.videoElement

      if (video) {
        try { video.pause() } catch (e) { console.warn(e) }
        video.removeAttribute('src')
        video.load()
      }

      this.isPlaying = false
    },

    // 切换播放/暂停
    togglePlay() {
      const video = this.$refs.videoElement

      if (!video) return

      if (this.isPlaying) {
        video.pause()
        this.isPlaying = false
      } else {
        this.loading = true
        const ret = video.play()
        if (ret && typeof ret.then === 'function') {
          ret.then(() => {
            this.loading = false
          }).catch(err => {
            console.error('播放失败:', err)
            this.loading = false
          })
        } else {
          this.loading = false
        }
      }
    },

    // 切换静音
    toggleMute() {
      this.isMuted = !this.isMuted
      if (this.$refs.videoElement) {
        this.$refs.videoElement.muted = this.isMuted
      }
    },

    // 重新加载
    reload() {
      if (this._isUnmounted) return
      if (this._reloadTimer) return
      this.hasError = false
      this.errorMessage = ''
      this.loading = true
      this.destroyPlayer()
      this._reloadTimer = setTimeout(() => {
        this._reloadTimer = null
        this.initPlayer()
      }, 300)
    },

    // 视频事件处理
    onLoadStart() {
      this.loading = true
      console.log('开始加载流...')
    },

    onCanPlay() {
      this.loading = false
      console.log('流加载完成，可以播放')
    },

    onPlaying() {
      this.loading = false
      this.isPlaying = true
      this.hasError = false
      console.log('正在播放')
    },

    onError(e) {
      console.error('❌ 视频元素错误:', e)

      const video = this.$refs.videoElement
      if (video && video.error) {
        const errorCode = video.error.code
        const errorMsg = video.error.message

        console.error('错误代码:', errorCode)
        console.error('错误信息:', errorMsg)

        // 🔥 详细的错误诊断
        let errorDetail = ''
        switch (errorCode) {
          case 1: // MEDIA_ERR_ABORTED
            errorDetail = '用户中止'
            break
          case 2: // MEDIA_ERR_NETWORK
            errorDetail = '网络错误 - 请检查流是否正在推流'
            break
          case 3: // MEDIA_ERR_DECODE
            errorDetail = '视频解码错误 - 可能是编码格式不支持（H.265等）'
            break
          case 4: // MEDIA_ERR_SRC_NOT_SUPPORTED
            errorDetail = '视频格式不支持 - 请检查推流编码格式'
            break
          default:
            errorDetail = `未知错误 (${errorCode})`
        }

        console.error('错误详情:', errorDetail)

        // 忽略手动切换 src 时的 abort 错误
        if (errorCode === 20) {
          return
        }

        if (!this.hasError) {
          this.hasError = true
          this.errorMessage = `播放失败: ${errorDetail}`
        }
      }

      this.loading = false
      this.isPlaying = false
    },

    onWaiting() {
      console.log('缓冲中...')
      this.chaseToLive()
    },

    // 🔥 新增：FMP4 追帧逻辑，降低延迟
    onTimeUpdate() {
      const video = this.$refs.videoElement
      if (!video) return

      // 更新最后活动时间，用于看门狗检测
      this.lastTimeUpdate = Date.now()
      this.chaseToLive()
    },

    // 🔥 新增：卡死检测看门狗
    startStuckWatchdog() {
      this.stopStuckWatchdog()
      this.lastTimeUpdate = Date.now()
      
      this.stuckWatchdogTimer = setInterval(() => {
        // 如果没有在播放或正在加载，不检测
        if (!this.isPlaying || this.loading || this.hasError) return

        const now = Date.now()
        // 如果超过 4秒 没有 timeupdate 事件，认为画面卡死
        if (now - this.lastTimeUpdate > 4000) {
          this.stuckCount++
          console.warn(`⚠️ 画面疑似卡死 (${this.stuckCount}次)，上次更新: ${(now - this.lastTimeUpdate)/1000}s 前`)
          
          // 如果连续卡死检测触发，尝试重载
          if (this.stuckCount >= 1) {
             console.log('🔄 触发防卡死重连机制...')
             this.reload()
             this.stuckCount = 0
             this.lastTimeUpdate = Date.now() // 重置计时
          }
        } else {
          this.stuckCount = 0
        }
      }, 2000)
    },

    stopStuckWatchdog() {
      if (this.stuckWatchdogTimer) {
        clearInterval(this.stuckWatchdogTimer)
        this.stuckWatchdogTimer = null
      }
    },

    // ======================================================================
    // 监听控制方法 (保持不变)
    // ======================================================================

    async toggleMonitor() {
      if (this.monitorLoading) return

      if (this.isMonitoring) {
        await this.stopMonitor()
      } else {
        await this.startMonitor()
      }
    },

    async startMonitor() {
      this.monitorLoading = true
      try {
        const response = await liveMonitorApi.startMonitor(this.streamId, 3.0)
        console.log('✅ 监听已启动:', response)

        // 🔥 修复：直接设置状态为 true，不依赖服务器同步
        this.isMonitoring = true
        this.setStoredMonitorStatus(true)

        this.$emit('monitor-started', response)
      } catch (err) {
        console.error('❌ 启动监听失败:', err)
        const errorMsg = err.response?.data?.message || err.message || '启动失败'
        alert(`启动保护区检测失败: ${errorMsg}`)
        // 失败时保持当前状态不变
      } finally {
        this.monitorLoading = false
      }
    },

    async stopMonitor() {
      this.monitorLoading = true
      try {
        const response = await liveMonitorApi.stopMonitor(this.streamId)
        console.log('✅ 监听已停止:', response)

        // 🔥 修复：直接设置状态为 false，不依赖服务器同步
        this.isMonitoring = false
        this.clearStoredMonitorStatus()

        this.$emit('monitor-stopped', response)
      } catch (err) {
        console.error('❌ 停止监听失败:', err)
        const errorMsg = err.response?.data?.message || err.message || '停止失败'
        alert(`停止保护区检测失败: ${errorMsg}`)
        // 即使失败也设置为 false（用户意图是停止）
        this.isMonitoring = false
        this.clearStoredMonitorStatus()
      } finally {
        this.monitorLoading = false
      }
    },

    async checkMonitorStatus() {
      try {
        const status = await liveMonitorApi.getStatus(this.streamId)
        const serverIsRunning = status.is_running || false

        // 🔥 如果服务器状态与本地不一致,以服务器为准
        if (serverIsRunning !== this.isMonitoring) {
          console.log(`状态不一致! 本地: ${this.isMonitoring}, 服务器: ${serverIsRunning}, 以服务器为准`)
          this.isMonitoring = serverIsRunning
          // 同步到本地存储
          if (serverIsRunning) {
            this.setStoredMonitorStatus(true)
          } else {
            this.clearStoredMonitorStatus()
          }
        }
      } catch (err) {
        // 静默失败，不影响用户使用
        console.warn('检查监听状态失败:', err)
      }
    },

    // 🔥 新增: 从服务器同步状态到本地
    async syncMonitorStatusFromServer() {
      try {
        const status = await liveMonitorApi.getStatus(this.streamId)
        const serverIsRunning = status.is_running || false

        console.log(`从服务器同步监听状态: ${serverIsRunning}`)

        // 🔥 以服务器状态为准,覆盖本地状态
        this.isMonitoring = serverIsRunning

        // 同步到本地存储
        if (serverIsRunning) {
          this.setStoredMonitorStatus(true)
        } else {
          this.clearStoredMonitorStatus()
        }
      } catch (err) {
        // 如果服务器查询失败,使用本地缓存的状态
        console.warn('从服务器同步状态失败,使用本地缓存:', err)
        // 此时 isMonitoring 已经在 data() 中从 localStorage 恢复了
      }
    },

    // ========== 🔥 新增：流状态检查方法 ==========

    /**
     * 页面加载时检查一次后端状态
     * 之后不再自动改变，完全由用户操作控制
     */
    async checkBackendMonitorStatusOnce() {
      try {
        const status = await liveMonitorApi.getStatus(this.streamId)
        const serverIsRunning = status.is_running || false

        console.log(`🔍 [初始检查] 后端监听状态: ${serverIsRunning}`)

        // 🔥 只在页面加载时同步一次真实状态
        // 之后完全由用户操作控制，不再自动改变
        if (serverIsRunning) {
          this.isMonitoring = true
          this.setStoredMonitorStatus(true)
          console.log('✅ 后端正在运行，前端状态设为：正在检测')
        } else {
          this.isMonitoring = false
          this.clearStoredMonitorStatus()
          console.log('✅ 后端未运行，前端状态设为：未检测')
        }
      } catch (err) {
        // 检查失败时保持默认状态（false）
        console.warn('⚠️ 检查后端状态失败，使用默认状态（未检测）:', err)
        this.isMonitoring = false
      }
    },

    /**
     * 检查当前流是否在线
     * 通过 ZLM API 查询流列表
     */
    async checkStreamOnline() {
      if (!this.streamId) return

      this.checkingStream = true
      try {
        // 调用 ZLM API 检查流是否在线
        const apiUrl = `${this.zlmServer}/index/api/isMediaOnline`
        const params = new URLSearchParams({
          secret: '123456',
          vhost: '__defaultVhost__',
          app: 'live',
          stream: this.streamId
        })

        console.log('🔍 检查流状态:', `${apiUrl}?${params}`)

        const response = await fetch(`${apiUrl}?${params}`)

        console.log('📡 API 响应状态:', response.status)

        const result = await response.json()
        console.log('📄 API 响应数据:', result)

        if (result.code === 0) {
          // 🔥 ZLM 返回的数据可能是数字或布尔值
          const isOnline = result.data === 1 || result.data === true || result.data === '1'
          this.isStreamOnline = isOnline
          console.log(`✅ 流 ${this.streamId} 在线状态: ${this.isStreamOnline}`)
        } else {
          console.warn(`⚠️ ZLM API 返回错误: code=${result.code}, msg=${result.msg}`)
          // 🔥 如果 API 失败，但视频能播放，我们认为是在线的
          if (this.isPlaying) {
            this.isStreamOnline = true
            console.log('✅ API 检查失败，但视频正在播放，标记为在线')
          } else {
            this.isStreamOnline = false
          }
        }
      } catch (err) {
        console.error('❌ 检查流状态失败:', err)
        // 🔥 如果网络错误，但视频能播放，我们认为是在线的
        if (this.isPlaying) {
          this.isStreamOnline = true
          console.log('✅ 网络错误，但视频正在播放，标记为在线')
        } else {
          this.isStreamOnline = false
        }
      } finally {
        this.checkingStream = false
      }
    },

    /**
     * 获取所有在线流列表
     * 返回格式: [{ app: 'live', stream: 'dock01' }, ...]
     */
    async getOnlineStreams() {
      try {
        const apiUrl = `${this.zlmServer}/index/api/getMediaList`
        const params = new URLSearchParams({
          secret: '123456',
          app: 'live'
        })

        const response = await fetch(`${apiUrl}?${params}`)
        const result = await response.json()

        if (result.code === 0) {
          const streams = result.data || []
          console.log(`📹 当前在线流数量: ${streams.length}`)
          console.log('📋 在线流列表:', streams.map(s => `${s.app}/${s.stream}`).join(', '))
          return streams
        } else {
          console.warn(`⚠️ 获取流列表失败: ${result.msg}`)
          return []
        }
      } catch (err) {
        console.error('❌ 获取在线流列表失败:', err)
        return []
      }
    }
  }
}
</script>

<style scoped>
.live-stream-player {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(10, 14, 39, 0.6);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(0, 212, 255, 0.2);
}

/* 播放器头部 */
.player-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(0, 153, 255, 0.1) 100%);
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stream-label {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.live-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.4);
  border-radius: 12px;
  color: #ef4444;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.live-dot {
  width: 6px;
  height: 6px;
  background: #ef4444;
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

.monitor-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(16, 185, 129, 0.2);
  border: 1px solid rgba(16, 185, 129, 0.4);
  border-radius: 12px;
  color: #10b981;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.monitor-dot {
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}

.header-right {
  display: flex;
  gap: 8px;
}

.control-icon-btn {
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 8px;
  background: rgba(26, 31, 58, 0.8);
  color: #00d4ff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.control-icon-btn svg {
  width: 18px;
  height: 18px;
}

.control-icon-btn:hover {
  background: rgba(0, 212, 255, 0.15);
  border-color: rgba(0, 212, 255, 0.5);
  transform: translateY(-1px);
}

/* 监听控制按钮 */
.monitor-control-btn {
  height: 32px;
  padding: 0 12px;
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 8px;
  background: rgba(26, 31, 58, 0.8);
  color: #10b981;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
}

.monitor-control-btn svg {
  width: 16px;
  height: 16px;
}

.monitor-control-btn:hover:not(:disabled) {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.5);
  transform: translateY(-1px);
}

.monitor-control-btn.active {
  background: rgba(16, 185, 129, 0.2);
  border-color: rgba(16, 185, 129, 0.5);
  color: #10b981;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.3);
}

.monitor-control-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.mini-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(16, 185, 129, 0.2);
  border-top-color: #10b981;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

/* 播放器容器 */
.player-container {
  flex: 1;
  position: relative;
  background: #000;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-element {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

/* 覆盖层 */
.overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: rgba(10, 14, 39, 0.95);
  backdrop-filter: blur(10px);
  color: #e2e8f0;
  z-index: 10;
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
  to { transform: rotate(360deg); }
}

.error-icon,
.placeholder-icon {
  font-size: 48px;
}

.error-message {
  font-size: 14px;
  color: #ef4444;
  text-align: center;
  margin: 0;
  max-width: 300px;
}

.reload-btn {
  padding: 8px 16px;
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 8px;
  background: rgba(0, 212, 255, 0.15);
  color: #00d4ff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.reload-btn:hover {
  background: rgba(0, 212, 255, 0.25);
  border-color: rgba(0, 212, 255, 0.5);
}

/* 播放器底部 */
.player-footer {
  padding: 10px 16px;
  background: rgba(10, 14, 39, 0.8);
  border-top: 1px solid rgba(0, 212, 255, 0.15);
}

.stream-info {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
}

.info-item {
  display: flex;
  gap: 6px;
}

.info-label {
  color: #94a3b8;
}

.info-value {
  color: #e2e8f0;
  font-family: 'Courier New', monospace;
}

.status-active {
  color: #10b981;
  font-weight: 600;
}

.status-online {
  color: #10b981;
  font-weight: 600;
}

.status-offline {
  color: #ef4444;
  font-weight: 600;
}

.status-unknown {
  color: #94a3b8;
}

.mini-spinner-inline {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(0, 212, 255, 0.2);
  border-top-color: #00d4ff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin-right: 4px;
  vertical-align: middle;
}

.placeholder-overlay p {
  color: #64748b;
  font-size: 14px;
  margin: 0;
}
</style>
