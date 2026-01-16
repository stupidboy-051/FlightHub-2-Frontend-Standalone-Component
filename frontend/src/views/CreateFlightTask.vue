<template>
  <div class="create-flight-task-premium">
    <!-- 页面头部 -->
    <div class="page-header-premium">
      <div class="header-content">
        <div class="header-left">
          <div class="header-icon">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="header-text">
            <h1 class="page-title">创建飞行任务</h1>
            <p class="page-subtitle">配置并下发一键起飞任务</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 表单卡片 -->
    <div class="form-card-premium">
      <el-form
        ref="taskForm"
        :model="form"
        :rules="rules"
        label-width="140px"
        class="task-form-premium"
        status-icon
      >
        <!-- 任务名称 -->
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入任务名称"></el-input>
        </el-form-item>

        <!-- 设备SN -->
        <el-form-item label="执行设备" prop="sn">
          <!-- 快速选择最近使用的设备 -->
          <el-input v-model="form.sn" placeholder="请输入或选择设备SN" class="full-width">
            <template #append>
              <el-dropdown @command="selectRecentDevice" :disabled="loadingRecentDevices">
                <el-button :loading="loadingRecentDevices">
                  最近使用
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item v-if="recentDevices.length === 0" disabled>
                      暂无历史记录
                    </el-dropdown-item>
                    <el-dropdown-item
                      v-for="device in recentDevices"
                      :key="device.sn"
                      :command="device.sn"
                      :label="device.sn"
                    >
                      <div style="display: flex; justify-content: space-between; align-items: center; min-width: 300px;">
                        <div>
                          <div style="font-weight: bold;">{{ device.sn }}</div>
                          <div style="font-size: 12px; color: #909399;">{{ device.name }}</div>
                        </div>
                        <el-text size="small" type="info">{{ formatTime(device.last_used) }}</el-text>
                      </div>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
          </el-input>

          <!-- 设备列表下拉选择 -->
          <el-select
            v-model="form.sn"
            placeholder="或从列表选择"
            class="full-width"
            :loading="loadingDevices"
            filterable
            style="margin-top: 8px;"
          >
            <el-option
              v-for="device in devices"
              :key="device.gateway.sn"
              :label="`${device.gateway.callsign || '未命名设备'} (${device.gateway.sn})`"
              :value="device.gateway.sn"
            >
              <span style="float: left">{{ device.gateway.callsign || '未命名设备' }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">{{ device.gateway.sn }}</span>
            </el-option>
          </el-select>
        </el-form-item>

        <!-- 航线选择 -->
        <el-form-item label="选择航线" prop="wayline_uuid">
          <el-select v-model="form.wayline_uuid" placeholder="请选择航线" class="full-width" :loading="loadingWaylines">
            <el-option
              v-for="wayline in waylines"
              :key="wayline.id"
              :label="wayline.name"
              :value="wayline.wayline_id || wayline.id" 
            >
              <!-- assuming wayline object has name and id/wayline_id -->
            </el-option>
          </el-select>
        </el-form-item>

        <!-- 任务类型 -->
        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="form.task_type" placeholder="请选择任务类型" class="full-width">
            <el-option label="立即任务 (Immediate)" value="immediate"></el-option>
            <el-option label="单次定时 (Timed)" value="timed"></el-option>
            <el-option label="重复任务 (Recurring)" value="recurring"></el-option>
            <el-option label="连续任务 (Continuous)" value="continuous"></el-option>
          </el-select>
        </el-form-item>

        <!-- 是否为保护区任务 -->
        <el-form-item label="保护区监测" prop="is_protected_area" class="item-aligned">
          <el-switch
            v-model="form.is_protected_area"
            active-text="是"
            inactive-text="否"
            inline-prompt
          />
          <span style="margin-left: 10px; color: #909399; font-size: 12px;">开启后将启用保护区实时监测算法</span>
        </el-form-item>

        <!-- 返航高度 -->
        <el-form-item label="返航高度" prop="rth_altitude">
          <el-input v-model="form.rth_altitude" placeholder="请输入返航高度 (20-500米)" class="full-width"></el-input>
        </el-form-item>

        <!-- 返航模式 -->
        <el-form-item label="返航模式" prop="rth_mode">
          <el-radio-group v-model="form.rth_mode">
            <el-radio label="optimal">最优路径 (Optimal)</el-radio>
            <el-radio label="preset">预设高度 (Preset)</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 航线精度类型 -->
        <el-form-item label="航线精度" prop="wayline_precision_type">
          <el-radio-group v-model="form.wayline_precision_type">
            <el-radio label="rtk">RTK</el-radio>
            <el-radio label="gps">GPS</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 断点续飞 -->
        <el-form-item label="断点续飞" prop="resumable_status">
          <el-radio-group v-model="form.resumable_status">
            <el-radio label="auto">自动 (Auto)</el-radio>
            <el-radio label="manual">手动 (Manual)</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 失控行为 (隐藏或高级选项) -->
        <el-form-item label="失控行为" prop="out_of_control_action_in_flight" v-if="false">
          <el-input v-model="form.out_of_control_action_in_flight"></el-input>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="submitForm" :loading="submitting">创建任务</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>

        <!-- 任务控制按钮组 -->
        <el-divider content-position="left">
          <span class="divider-label">任务控制</span>
        </el-divider>

        <el-form-item label="设备控制">
          <div class="control-section-premium">
            <div class="control-buttons-premium">
              <el-button
                type="warning"
                @click="handleReturnHome"
                :disabled="!form.sn"
                :loading="commandLoading.returnHome"
                class="control-btn-premium warning-btn"
              >
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <polyline points="9 22 9 12 15 12 15 22" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                返航
              </el-button>
              <el-button
                @click="handleCancelReturn"
                :disabled="!form.sn"
                :loading="commandLoading.cancelReturn"
                class="control-btn-premium default-btn"
              >
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                  <line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                取消返航
              </el-button>
              <el-button
                type="info"
                @click="handlePause"
                :disabled="!form.sn"
                :loading="commandLoading.pause"
                class="control-btn-premium info-btn"
              >
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                  <rect x="6" y="4" width="4" height="16" stroke="currentColor" stroke-width="2"/>
                  <rect x="14" y="4" width="4" height="16" stroke="currentColor" stroke-width="2"/>
                </svg>
                暂停
              </el-button>
              <el-button
                type="success"
                @click="handleResume"
                :disabled="!form.sn"
                :loading="commandLoading.resume"
                class="control-btn-premium success-btn"
              >
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none">
                  <polygon points="5 3 19 12 5 21 5 3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                恢复
              </el-button>
            </div>
            <div class="control-tip">
              <el-text size="small" type="info">
                请先选择设备，然后点击相应的控制按钮
              </el-text>
            </div>
          </div>
        </el-form-item>
      </el-form>
    </div>

    <!-- 起飞确认弹窗 -->
    <el-dialog
      title="确认起飞"
      v-model="confirmDialogVisible"
      width="400px"
      :before-close="handleDialogClose"
      center
    >
      <div class="confirm-content">
        <p class="confirm-icon">🚀</p>
        <p class="confirm-text">任务已准备就绪</p>
        <p class="confirm-subtext">请确认是否立即下发并执行起飞任务？</p>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleDialogClose">取消</el-button>
          <el-button 
            type="danger" 
            @click="executeTask" 
            :disabled="countdown > 0"
            :loading="submitting"
          >
            {{ countdown > 0 ? `确认起飞 (${countdown}s)` : '确认起飞' }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import flightTaskApi from '../api/flightTaskApi'
import waylineApi from '../api/waylineApi'
import { ElMessage } from 'element-plus'

export default {
  name: 'CreateFlightTask',
  data() {
    return {
      loadingDevices: false,
      loadingWaylines: false,
      loadingRecentDevices: false,
      submitting: false,
      confirmDialogVisible: false,
      countdown: 5,
      timer: null,
      devices: [],
      recentDevices: [],
      waylines: [],
      commandLoading: {
        returnHome: false,
        cancelReturn: false,
        pause: false,
        resume: false
      },
      form: {
        name: '',
        sn: '',
        wayline_uuid: '',
        time_zone: 'Asia/Chongqing', // Default parameter
        rth_altitude: 100, // Default sensible value
        rth_mode: 'optimal',
        wayline_precision_type: 'rtk',
        resumable_status: 'manual',
        task_type: 'immediate',
        out_of_control_action_in_flight: 'return_home',
        is_protected_area: false
      },
      rules: {
        name: [
          { required: true, message: '请输入任务名称', trigger: 'blur' },
          { min: 3, max: 50, message: '长度在 3 到 50 个字符', trigger: 'blur' }
        ],
        sn: [
          { required: true, message: '请选择执行设备', trigger: 'change' }
        ],
        wayline_uuid: [
          { required: true, message: '请选择航线', trigger: 'change' }
        ],
        task_type: [
          { required: true, message: '请选择任务类型', trigger: 'change' }
        ],
        rth_altitude: [
          { required: true, message: '请输入返航高度', trigger: 'blur' },
          {
            validator: (rule, value, callback) => {
              if (!value) {
                callback(new Error('请输入返航高度'))
              } else if (isNaN(value) || value < 20 || value > 500) {
                callback(new Error('返航高度必须在 20-500 之间'))
              } else {
                callback()
              }
            },
            trigger: 'blur'
          }
        ]
      }
    }
  },
  mounted() {
    this.fetchDevices()
    this.fetchWaylines()
    this.fetchRecentDevices()
  },
  beforeUnmount() {
    if (this.timer) clearInterval(this.timer)
  },
  methods: {
    async fetchDevices() {
      this.loadingDevices = true
      try {
        const list = await flightTaskApi.getDevices()
        this.devices = list || []
      } catch (error) {
        ElMessage.error('获取设备列表失败')
      } finally {
        this.loadingDevices = false
      }
    },
    async fetchWaylines() {
      this.loadingWaylines = true
      try {
        // Assuming getWaylines returns a list or a paginated object
        const res = await waylineApi.getWaylines({ page_size: 100 })
        // Adapt based on actual API response structure.
        // Based on waylineApi.js: return response (which is response.data)
        // Usually Django DRF returns { results: [], count: ... } or just []
        if (Array.isArray(res)) {
          this.waylines = res
        } else if (res && res.results) {
          this.waylines = res.results
        } else {
          this.waylines = []
        }
      } catch (error) {
        ElMessage.error('获取航线列表失败')
      } finally {
        this.loadingWaylines = false
      }
    },
    async fetchRecentDevices() {
      this.loadingRecentDevices = true
      try {
        const res = await flightTaskApi.getRecentDevices()
        this.recentDevices = res || []
      } catch (error) {
        console.error('获取最近设备失败:', error)
        this.recentDevices = []
      } finally {
        this.loadingRecentDevices = false
      }
    },
    selectRecentDevice(sn) {
      this.form.sn = sn
      ElMessage.success(`已选择设备: ${sn}`)
    },
    formatTime(timeStr) {
      if (!timeStr) return ''
      const date = new Date(timeStr)
      const now = new Date()
      const diff = now - date
      const minutes = Math.floor(diff / 60000)
      const hours = Math.floor(diff / 3600000)
      const days = Math.floor(diff / 86400000)

      if (minutes < 1) return '刚刚'
      if (minutes < 60) return `${minutes}分钟前`
      if (hours < 24) return `${hours}小时前`
      if (days < 7) return `${days}天前`
      return date.toLocaleDateString('zh-CN')
    },
    submitForm() {
      this.$refs.taskForm.validate((valid) => {
        if (valid) {
          this.startCountdown()
        } else {
          return false
        }
      })
    },
    startCountdown() {
      this.confirmDialogVisible = true
      this.countdown = 5
      if (this.timer) clearInterval(this.timer)
      this.timer = setInterval(() => {
        this.countdown--
        if (this.countdown <= 0) {
          clearInterval(this.timer)
          this.timer = null
        }
      }, 1000)
    },
    handleDialogClose() {
      if (this.timer) {
        clearInterval(this.timer)
        this.timer = null
      }
      this.confirmDialogVisible = false
    },
    async executeTask() {
      this.submitting = true
      try {
        const payload = {
          ...this.form,
          // 🔥 确保返航高度是数字类型
          rth_altitude: Number(this.form.rth_altitude)
        }
        const res = await flightTaskApi.createFlightTask(payload)
        if (res.code === 0) {
          ElMessage.success('任务创建成功！')
          this.handleDialogClose()
          this.resetForm()
        } else {
          ElMessage.error(res.message || '任务创建失败')
        }
      } catch (error) {
        ElMessage.error('请求失败：' + (error.message || '未知错误'))
      } finally {
        this.submitting = false
      }
    },
    resetForm() {
      this.$refs.taskForm.resetFields()
      // Reset defaults that might not be covered by resetFields if prop is missing in initial form?
      // resetFields resets to initial value defined in data().
    },

    // 返航
    async handleReturnHome() {
      if (!this.form.sn) {
        ElMessage.warning('请先选择设备')
        return
      }

      this.$confirm('确认执行返航操作？', '提示', {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        this.commandLoading.returnHome = true
        try {
          const res = await flightTaskApi.returnHome(this.form.sn)
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
      }).catch(() => {})
    },

    // 取消返航
    async handleCancelReturn() {
      if (!this.form.sn) {
        ElMessage.warning('请先选择设备')
        return
      }

      this.$confirm('确认取消返航？', '提示', {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        this.commandLoading.cancelReturn = true
        try {
          const res = await flightTaskApi.cancelReturn(this.form.sn)
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
      }).catch(() => {})
    },

    // 暂停任务
    async handlePause() {
      if (!this.form.sn) {
        ElMessage.warning('请先选择设备')
        return
      }

      this.$confirm('确认暂停当前任务？', '提示', {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'info'
      }).then(async () => {
        this.commandLoading.pause = true
        try {
          const res = await flightTaskApi.pauseTask(this.form.sn)
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
      }).catch(() => {})
    },

    // 恢复任务
    async handleResume() {
      if (!this.form.sn) {
        ElMessage.warning('请先选择设备')
        return
      }

      this.$confirm('确认恢复任务？', '提示', {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'success'
      }).then(async () => {
        this.commandLoading.resume = true
        try {
          const res = await flightTaskApi.resumeTask(this.form.sn)
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
      }).catch(() => {})
    }
  }
}
</script>

<style scoped>
/* ========== 主容器 ========== */
.create-flight-task-premium {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0;
  min-height: 100%;
}

/* ========== 页面头部 ========== */
.page-header-premium {
  margin-bottom: 32px;
}

.header-content {
  padding: 28px 36px;
  background: rgba(26, 31, 58, 0.6);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  border: 1px solid rgba(59, 130, 246, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2), 0 0 40px rgba(59, 130, 246, 0.1);
  animation: headerSlideIn 0.5s ease-out;
}

@keyframes headerSlideIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
  animation: iconPulse 3s ease-in-out infinite;
}

@keyframes iconPulse {
  0%, 100% {
    box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
  }
  50% {
    box-shadow: 0 4px 24px rgba(59, 130, 246, 0.6);
  }
}

.header-icon svg {
  width: 28px;
  height: 28px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 8px 0;
  letter-spacing: 0.5px;
}

.page-subtitle {
  color: #94a3b8;
  font-size: 14px;
  margin: 0;
  font-weight: 400;
}

/* ========== 表单卡片 ========== */
.form-card-premium {
  background: rgba(10, 15, 35, 0.75);
  backdrop-filter: blur(20px) saturate(180%);
  border-radius: 16px;
  padding: 40px;
  border: 1px solid rgba(59, 130, 246, 0.3);
  box-shadow:
    0 20px 60px rgba(0, 0, 0, 0.5),
    0 0 40px rgba(59, 130, 246, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  animation: cardSlideIn 0.5s ease-out;
}

@keyframes cardSlideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.task-form-premium {
  max-width: 800px;
  margin: 0 auto;
}

/* ========== 表单项样式 ========== */
.task-form-premium :deep(.el-form-item__label) {
  color: #cbd5e1;
  font-weight: 500;
}

/* 修复对齐问题：为特定的非必填项模拟星号占位，并缩小字体防止突出 */
.task-form-premium :deep(.item-aligned .el-form-item__label) {
  font-size: 12px; /* 缩小字体到12px */
  letter-spacing: -1px; /* 更紧凑的字间距 */
  white-space: nowrap;
}

.task-form-premium :deep(.item-aligned .el-form-item__label)::before {
  content: '*';
  color: transparent;
  margin-right: 4px;
}

/* 统一所有输入框样式 */
.task-form-premium :deep(.el-input__wrapper) {
  background: transparent !important;
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
  box-shadow: none;
  transition: all 0.3s ease;
}

.task-form-premium :deep(.el-input__wrapper:hover) {
  border-color: rgba(255, 255, 255, 0.3) !important;
}

.task-form-premium :deep(.el-input__wrapper.is-focus) {
  border-color: rgba(255, 255, 255, 0.4) !important;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.1) !important;
}

.task-form-premium :deep(.el-input__inner) {
  color: #ffffff !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

.task-form-premium :deep(.el-input__inner)::placeholder {
  color: rgba(255, 255, 255, 0.5) !important;
}

.task-form-premium :deep(.el-input-number) {
  width: 100%;
}

.task-form-premium :deep(.el-input-number .el-input__wrapper) {
  height: 32px;
  background: transparent !important;
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
  box-shadow: none;
}

.task-form-premium :deep(.el-input-number .el-input__wrapper:hover) {
  border-color: rgba(255, 255, 255, 0.3) !important;
}

.task-form-premium :deep(.el-input-number .el-input__wrapper.is-focus) {
  border-color: rgba(255, 255, 255, 0.4) !important;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.1) !important;
}

.task-form-premium :deep(.el-input-number .el-input__inner) {
  background: transparent !important;
  color: #ffffff !important;
  border: none !important;
  box-shadow: none !important;
}

.task-form-premium :deep(.el-select) {
  width: 100%;
}

.task-form-premium :deep(.el-select .el-input__wrapper) {
  background: transparent !important;
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
}

.task-form-premium :deep(.el-select-dropdown) {
  background: rgba(10, 15, 35, 0.95);
  border: 1px solid rgba(59, 130, 246, 0.3);
  backdrop-filter: blur(10px);
}

.task-form-premium :deep(.el-select-dropdown__item) {
  color: #cbd5e1;
}

.task-form-premium :deep(.el-select-dropdown__item:hover) {
  background: rgba(59, 130, 246, 0.1);
}

.task-form-premium :deep(.el-select-dropdown__item.selected) {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
}

.task-form-premium :deep(.el-radio-group) {
  display: flex;
  gap: 24px;
}

.task-form-premium :deep(.el-radio__label) {
  color: #cbd5e1;
}

.task-form-premium :deep(.el-radio__input.is-checked .el-radio__inner) {
  background: #3b82f6;
  border-color: #3b82f6;
}

/* ========== 按钮样式 ========== */
/* 确保按钮不受透明背景影响 */
.task-form-premium :deep(.el-button) {
  background: initial !important;
}

.task-form-premium :deep(.el-button--primary) {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
  border: none;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
  transition: all 0.3s ease;
}

.task-form-premium :deep(.el-button--primary:hover) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5);
}

.task-form-premium :deep(.el-button--primary:active) {
  transform: translateY(0);
}

.task-form-premium :deep(.el-button--default) {
  background: rgba(59, 130, 246, 0.1) !important;
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #60a5fa;
  transition: all 0.3s ease;
}

.task-form-premium :deep(.el-button--default:hover) {
  background: rgba(59, 130, 246, 0.2) !important;
  border-color: rgba(59, 130, 246, 0.5);
}

/* ========== 分割线 ========== */
.task-form-premium :deep(.el-divider) {
  border-top-color: rgba(59, 130, 246, 0.2);
}

.task-form-premium :deep(.el-divider__text) {
  background: transparent;
  color: #94a3b8;
  font-weight: 500;
}

.divider-label {
  color: #94a3b8;
  font-size: 14px;
  font-weight: 500;
}

/* ========== 控制按钮区域 ========== */
.control-section-premium {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  padding: 24px;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.control-buttons-premium {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.control-btn-premium {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  font-size: 15px;
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.control-btn-premium::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s ease;
}

.control-btn-premium:hover::before {
  left: 100%;
}

.control-btn-premium:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
}

.control-btn-premium:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon {
  width: 18px;
  height: 18px;
}

.warning-btn {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  border: none;
  color: #fff;
  box-shadow: 0 4px 16px rgba(245, 158, 11, 0.4);
}

.warning-btn:hover:not(:disabled) {
  box-shadow: 0 6px 20px rgba(245, 158, 11, 0.5);
}

.default-btn {
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #60a5fa;
}

.default-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.5);
}

.info-btn {
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
  border: none;
  color: #fff;
  box-shadow: 0 4px 16px rgba(6, 182, 212, 0.4);
}

.info-btn:hover:not(:disabled) {
  box-shadow: 0 6px 20px rgba(6, 182, 212, 0.5);
}

.success-btn {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border: none;
  color: #fff;
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.4);
}

.success-btn:hover:not(:disabled) {
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.5);
}

.control-tip {
  padding-top: 8px;
  border-top: 1px solid rgba(59, 130, 246, 0.1);
}

/* ========== 确认弹窗 ========== */
.confirm-content {
  text-align: center;
  padding: 20px 0;
}

.confirm-icon {
  font-size: 48px;
  margin: 0 0 16px;
}

.confirm-text {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
  margin: 0 0 8px;
}

.confirm-subtext {
  color: #909399;
  font-size: 14px;
  margin: 0;
}

.full-width {
  width: 100%;
}

/* ========== 响应式 ========== */
@media (max-width: 768px) {
  .header-content {
    padding: 20px 24px;
  }

  .header-left {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .page-title {
    font-size: 24px;
  }

  .form-card-premium {
    padding: 24px;
  }

  .task-form-premium {
    max-width: 100%;
  }

  .task-form-premium :deep(.el-form-item__label) {
    width: 100% !important;
    text-align: left;
    margin-bottom: 8px;
  }

  .task-form-premium :deep(.el-form-item) {
    display: block;
  }

  .task-form-premium :deep(.el-radio-group) {
    flex-direction: column;
    gap: 12px;
  }

  .control-buttons-premium {
    flex-direction: column;
  }

  .control-btn-premium {
    width: 100%;
    justify-content: center;
  }
}
</style>
<style>
/* 覆盖 Element Plus 的 CSS 变量 - 设置为透明 */
:root {
  --el-fill-color-blank: transparent !important;
  --el-bg-color: transparent !important;
}

/* ========== 全局 Element UI 下拉菜单深色主题 ========== */
/* el-select 下拉选项 */
.el-select-dropdown {
  background: rgba(10, 15, 35, 0.98) !important;
  border: 1px solid rgba(59, 130, 246, 0.3) !important;
  backdrop-filter: blur(20px);
}

.el-select-dropdown__item {
  color: #cbd5e1 !important;
}

.el-select-dropdown__item:hover {
  background: rgba(59, 130, 246, 0.15) !important;
}

.el-select-dropdown__item.selected {
  color: #60a5fa !important;
  background: rgba(59, 130, 246, 0.2) !important;
}

/* el-dropdown 下拉菜单 */
.el-dropdown-menu {
  background: rgba(10, 15, 35, 0.98) !important;
  border: 1px solid rgba(59, 130, 246, 0.3) !important;
  backdrop-filter: blur(20px);
}

.el-dropdown-menu__item {
  color: #cbd5e1 !important;
}

.el-dropdown-menu__item:hover {
  background: rgba(59, 130, 246, 0.15) !important;
}

.el-dropdown-menu__item:focus {
  background: rgba(59, 130, 246, 0.15) !important;
  color: #60a5fa !important;
}

/* el-option 组件 */
.el-option {
  color: #cbd5e1 !important;
}

.el-option:hover {
  background: rgba(59, 130, 246, 0.15) !important;
}

.el-option.selected {
  color: #60a5fa !important;
}

/* 滚动条样式 */
.el-select-dropdown .el-scrollbar__wrap {
  background: transparent !important;
}

.el-select-dropdown__wrap {
  background: transparent !important;
}

/* ========== 全局 Element UI 输入框深色主题 ========== */
/* el-form-item 表单项容器 */
.el-form-item__content,
.el-form-item__content .el-input,
.el-form-item__content .el-select,
.el-form-item__content .el-textarea {
  background: transparent !important;
}

/* 只修改颜色，不影响功能 */
.el-input__wrapper {
  background: transparent !important;
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
}

/* 只针对 input-number */
.el-input-number .el-input__wrapper {
  background: transparent !important;
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
}

.el-input-number {
  width: auto;
}

.el-input__wrapper:hover,
.el-input-number .el-input__wrapper:hover {
  border-color: rgba(255, 255, 255, 0.3) !important;
}

.el-input__wrapper.is-focus,
.el-input-number .el-input__wrapper.is-focus {
  border-color: rgba(255, 255, 255, 0.4) !important;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.1) !important;
}

/* el-input 内部输入框 */
input.el-input__inner,
.el-input__inner,
.el-input-number .el-input__inner {
  color: #ffffff !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

input.el-input__inner::placeholder,
.el-input__inner::placeholder {
  color: rgba(255, 255, 255, 0.5) !important;
}

/* el-input-group 附加元素 */
.el-input-group__append,
.el-input-group__prepend {
  background-color: var(--el-fill-color-light, transparent) !important;
  border: 1px solid var(--el-border-color, rgba(255, 255, 255, 0.2)) !important;
  color: var(--el-text-color-regular, #ffffff) !important;
}

.el-input-group__append .el-button,
.el-input-group__prepend .el-button {
  background: transparent !important;
  color: inherit !important;
}

/* textarea 多行输入 */
textarea.el-textarea__inner,
.el-textarea__inner {
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
  color: #ffffff !important;
}

textarea.el-textarea__inner::placeholder,
.el-textarea__inner::placeholder {
  color: rgba(255, 255, 255, 0.5) !important;
}

textarea.el-textarea__inner:focus,
.el-textarea__inner:focus {
  border-color: rgba(255, 255, 255, 0.4) !important;
}

/* 确保所有表单元素完全透明背景 */
.el-input__inner,
.el-textarea__inner,
.el-input-number__inner {
  background: transparent !important;
}

/* 选择器下拉项文字颜色 */
.el-select-dropdown__item,
.el-option {
  color: #ffffff !important;
}

.el-select-dropdown__item:hover,
.el-option:hover {
  background: rgba(255, 255, 255, 0.1) !important;
}

.el-select-dropdown__item.selected,
.el-option.selected {
  color: #60a5fa !important;
}
</style>

