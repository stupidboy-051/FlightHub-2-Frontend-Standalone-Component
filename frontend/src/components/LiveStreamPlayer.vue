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
import mpegts from 'mpegts.js' // 🔥 引入 mpegts

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
      isMuted: true, // 🔥 建议默认静音，避免 Chrome 自动播放拦截
      loading: false,
      hasError: false,
      errorMessage: '',
      isMonitoring: false,
      monitorLoading: false,
      monitorCheckTimer: null,
      isStreamOnline: null,  // null=未检查, true=在线, false=离线
      checkingStream: false,
      lastTimeUpdate: 0,
      stuckWatchdogTimer: null,
      stuckCount: 0,
      _reloadTimer: null,
      _isUnmounted: false,
      flvPlayer: null // 🔥 新增 mpegts 播放器实例
    }
  },
  computed: {
    // 🔥 代理地址并转换为 FLV 格式
    streamUrl() {
      const normalizeToFlv = (url) => {
        if (!url) return url
        // 保留 mp4 直连播放，不再强制转换为 flv
        if (url.endsWith('.mp4')) {
          return url
        }
        return url
      }

      // 如果传入了 Override URL，进行智能处理
      if (this.streamUrlOverride) {
        const url = this.streamUrlOverride

        // 智能转换 RTMP 地址为 HTTP-FLV
        if (url.startsWith('rtmp://')) {
          console.warn('检测到 RTMP 地址，尝试转换为 HTTP-FLV 播放地址:', url)
          try {
            const urlObj = new URL(url)
            const pathParts = urlObj.pathname.split('/').filter(p => p)
            if (pathParts.length >= 2) {
              const app = pathParts[0]
              const stream = pathParts[1]

              const isDev = process.env.NODE_ENV === 'development'
              if (isDev) {
                return normalizeToFlv(`/zlm/${app}/${stream}.live.flv`)
              } else {
                return normalizeToFlv(`${this.zlmServer}/${app}/${stream}.live.flv`)
              }
            }
          } catch (e) {
            console.error('RTMP 地址解析失败:', e)
          }
        }
        return normalizeToFlv(url)
      }

      if (!this.streamId) return ''

      const isDev = process.env.NODE_ENV === 'development'
      if (isDev) {
        return normalizeToFlv(`/zlm/live/${this.streamId}.live.flv`)
      } else {
        return normalizeToFlv(`${this.zlmServer}/live/${this.streamId}.live.flv`)
      }
    }
  },
  mounted() {
    this.initPlayer()
    this.syncMonitorStatusFromServer()

    this.monitorCheckTimer = setInterval(() => {
      this.checkMonitorStatus()
    }, 5000)

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

    // ========== 🔥 mpegts 播放器核心方法 ==========
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

      console.log('正在初始化 HTTP-FLV 播放:', this.streamUrl)
      this.loading = true
      this.hasError = false
      this.errorMessage = ''

  // 在你的 initPlayer 方法中找到这段：
    // 优先支持 MP4 直连播放（不走 mpegts）
    const isMp4 = typeof this.streamUrl === 'string' && this.streamUrl.includes('.mp4')
    if (isMp4) {
      const videoEl = this.$refs.videoElement
      try {
        videoEl.muted = this.isMuted
        videoEl.src = this.streamUrl
        if (this.autoPlay) {
          videoEl.play().then(() => {
            this.isPlaying = true
            this.loading = false
          }).catch(err => {
            console.warn('MP4 自动播放被阻止:', err)
            this.isPlaying = false
            this.loading = false
          })
        } else {
          this.loading = false
        }
      } catch (e) {
        this.hasError = true
        this.errorMessage = 'MP4 播放初始化失败'
        this.loading = false
      }
      return
    }

    if (mpegts.getFeatureList().mseLivePlayback) {
      this.flvPlayer = mpegts.createPlayer({
        type: 'flv',
        isLive: true,
        url: this.streamUrl,
        // 🛑 修改这里：不要用 !this.isMuted，直接写死 false
        // 强制 mpegts 在解包时丢弃所有音频轨，防止干扰视频解码
        hasAudio: false,
        hasVideo: true   // 明确告诉它我们要视频
      }, {
        enableWorker: true,
        enableStashBuffer: false,
        stashInitialSize: 128,
        liveBufferLatencyChasing: true,
        liveBufferLatencyMaxLatency: 2.0,
        liveBufferLatencyMinLatency: 0.5,
        // 🔥 新增这个配置：对不规范的 H.264 更加宽容
        fixAudioTimestampGap: false
      })

        this.flvPlayer.attachMediaElement(video)
        this.flvPlayer.load()

        // 监听底层错误
        this.flvPlayer.on(mpegts.Events.ERROR, (errorType, errorDetail) => {
          console.error(`❌ mpegts解码错误: type=${errorType}, detail=${errorDetail}`)
          if (!this.hasError) {
            this.hasError = true
            this.errorMessage = `解码异常: ${errorDetail}`
            this.loading = false
            this.isPlaying = false
          }
        })

        if (this.autoPlay) {
          this.flvPlayer.play().then(() => {
            this.isPlaying = true
          }).catch(err => {
            console.warn('自动播放被阻止，可能需要用户交互:', err)
            this.isPlaying = false
            this.loading = false
          })
        }
      } else {
        this.hasError = true
        this.errorMessage = '当前浏览器不支持 MSE 硬件加速，无法播放'
        this.loading = false
      }
    },

    destroyPlayer() {
      if (this.flvPlayer) {
        try {
          this.flvPlayer.pause()
          this.flvPlayer.unload()
          this.flvPlayer.detachMediaElement()
          this.flvPlayer.destroy()
        } catch (e) {
          console.warn('销毁播放器异常:', e)
        }
        this.flvPlayer = null
      }

      const video = this.$refs.videoElement
      if (video) {
        try { video.pause() } catch (e) { console.warn(e) }
        video.removeAttribute('src')
        video.load()
      }
      this.isPlaying = false
    },

    togglePlay() {
      if (this.isPlaying) {
        if (this.flvPlayer) {
          this.flvPlayer.pause()
        } else if (this.$refs.videoElement) {
          try { this.$refs.videoElement.pause() } catch (e) { console.warn(e) }
        }
        this.isPlaying = false
      } else {
        this.loading = true
        if (this.flvPlayer) {
          this.flvPlayer.play().then(() => {
            this.loading = false
            this.isPlaying = true
          }).catch(err => {
            console.error('播放失败:', err)
            this.loading = false
          })
        } else {
           // 原生视频播放
           const video = this.$refs.videoElement
           if (video) {
             video.play().then(() => {
               this.loading = false
               this.isPlaying = true
             }).catch(err => {
               console.error('原生播放失败:', err)
               this.loading = false
               this.isPlaying = false
             })
           } else {
             this.loading = false
           }
        }
      }
    },

    toggleMute() {
      this.isMuted = !this.isMuted
      if (this.$refs.videoElement) {
        this.$refs.videoElement.muted = this.isMuted
      }
    },

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
      }, 500)
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
    onError() {
      // 原生播放错误处理（mpegts 错误由其事件接管）
      if (!this.flvPlayer) {
        this.hasError = true
        this.errorMessage = '视频播放错误'
        this.loading = false
        this.isPlaying = false
      }
    },
    onWaiting() {
      console.log('缓冲中...')
    },
    onTimeUpdate() {
      this.lastTimeUpdate = Date.now()
    },

    // 卡死检测看门狗
    startStuckWatchdog() {
      this.stopStuckWatchdog()
      this.lastTimeUpdate = Date.now()

      this.stuckWatchdogTimer = setInterval(() => {
        if (!this.isPlaying || this.loading || this.hasError) return

        const now = Date.now()
        if (now - this.lastTimeUpdate > 4000) {
          this.stuckCount++
          console.warn(`⚠️ 画面疑似卡死 (${this.stuckCount}次)，上次更新: ${(now - this.lastTimeUpdate)/1000}s 前`)

          if (this.stuckCount >= 1) {
             console.log('🔄 触发防卡死重连机制...')
             this.reload()
             this.stuckCount = 0
             this.lastTimeUpdate = Date.now()
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

    // ========== 监听控制与其他业务方法 ==========
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

        this.isMonitoring = true
        this.setStoredMonitorStatus(true)

        this.$emit('monitor-started', response)
      } catch (err) {
        console.error('❌ 启动监听失败:', err)
        const errorMsg = err.response?.data?.message || err.message || '启动失败'
        alert(`启动保护区检测失败: ${errorMsg}`)
      } finally {
        this.monitorLoading = false
      }
    },

    async stopMonitor() {
      this.monitorLoading = true
      try {
        const response = await liveMonitorApi.stopMonitor(this.streamId)
        console.log('✅ 监听已停止:', response)

        this.isMonitoring = false
        this.clearStoredMonitorStatus()

        this.$emit('monitor-stopped', response)
      } catch (err) {
        console.error('❌ 停止监听失败:', err)
        const errorMsg = err.response?.data?.message || err.message || '停止失败'
        alert(`停止保护区检测失败: ${errorMsg}`)
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

        if (serverIsRunning !== this.isMonitoring) {
          console.log(`状态不一致! 本地: ${this.isMonitoring}, 服务器: ${serverIsRunning}, 以服务器为准`)
          this.isMonitoring = serverIsRunning
          if (serverIsRunning) {
            this.setStoredMonitorStatus(true)
          } else {
            this.clearStoredMonitorStatus()
          }
        }
      } catch (err) {
        console.warn('检查监听状态失败:', err)
      }
    },

    async syncMonitorStatusFromServer() {
      try {
        const status = await liveMonitorApi.getStatus(this.streamId)
        const serverIsRunning = status.is_running || false

        console.log(`从服务器同步监听状态: ${serverIsRunning}`)
        this.isMonitoring = serverIsRunning

        if (serverIsRunning) {
          this.setStoredMonitorStatus(true)
        } else {
          this.clearStoredMonitorStatus()
        }
      } catch (err) {
        console.warn('从服务器同步状态失败,使用本地缓存:', err)
      }
    },

    async checkBackendMonitorStatusOnce() {
      try {
        const status = await liveMonitorApi.getStatus(this.streamId)
        const serverIsRunning = status.is_running || false

        console.log(`🔍 [初始检查] 后端监听状态: ${serverIsRunning}`)

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
        console.warn('⚠️ 检查后端状态失败，使用默认状态（未检测）:', err)
        this.isMonitoring = false
      }
    },

    async checkStreamOnline() {
      if (!this.streamId) return

      this.checkingStream = true
      try {
        const apiUrl = `${this.zlmServer}/index/api/isMediaOnline`
        const params = new URLSearchParams({
          secret: '123456',
          vhost: '__defaultVhost__',
          app: 'live',
          stream: this.streamId
        })

        console.log('🔍 检查流状态:', `${apiUrl}?${params}`)
        const response = await fetch(`${apiUrl}?${params}`)
        const result = await response.json()

        if (result.code === 0) {
          const isOnline = result.data === 1 || result.data === true || result.data === '1'
          this.isStreamOnline = isOnline
          console.log(`✅ 流 ${this.streamId} 在线状态: ${this.isStreamOnline}`)
        } else {
          console.warn(`⚠️ ZLM API 返回错误: code=${result.code}, msg=${result.msg}`)
          if (this.isPlaying) {
            this.isStreamOnline = true
          } else {
            this.isStreamOnline = false
          }
        }
      } catch (err) {
        console.error('❌ 检查流状态失败:', err)
        if (this.isPlaying) {
          this.isStreamOnline = true
        } else {
          this.isStreamOnline = false
        }
      } finally {
        this.checkingStream = false
      }
    },

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
/* 样式部分保持不变 */
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
  font-size: 16px;
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

.monitor-control-btn {
  height: 32px;
  padding: 0 12px;
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 8px;
  background: rgba(26, 31, 58, 0.8);
  color: #10b981;
  font-size: 14px;
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
  font-size: 16px;
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
  font-size: 15px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.reload-btn:hover {
  background: rgba(0, 212, 255, 0.25);
  border-color: rgba(0, 212, 255, 0.5);
}

.player-footer {
  padding: 10px 16px;
  background: rgba(10, 14, 39, 0.8);
  border-top: 1px solid rgba(0, 212, 255, 0.15);
}

.stream-info {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 14px;
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
  font-size: 16px;
  margin: 0;
}
</style>
