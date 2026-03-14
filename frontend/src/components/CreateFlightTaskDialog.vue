<template>
  <div class="create-task-dialog-root">
    <el-dialog
      v-model="dialogVisible"
      class="create-task-dialog"
      width="640px"
      modal-class="create-task-modal"
      :close-on-click-modal="false"
      :before-close="handleDialogClose"
    >
      <template #header>
        <div class="dialog-header">
          <div>
            <h3 class="dialog-title">创建飞行任务</h3>
            <p class="dialog-subtitle">配置并下发一键起飞任务</p>
          </div>
          <div v-if="dockName || sn" class="dialog-sn">
            <span v-if="dockName">{{ dockName }}</span>
            <span v-if="sn">SN {{ sn }}</span>
          </div>
        </div>
      </template>

      <el-form
        ref="taskForm"
        :model="form"
        :rules="rules"
        label-width="120px"
        class="task-form-dialog"
        status-icon
      >
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入任务名称"></el-input>
        </el-form-item>

        <el-form-item label="航线类型">
          <el-select
            v-model="selectedWaylineType"
            class="full-width"
            placeholder="全部类型"
            @change="handleWaylineTypeChange"
          >
            <el-option label="全部" value="all"></el-option>
            <el-option label="铁路" value="rail"></el-option>
            <el-option label="接触网" value="contactline"></el-option>
            <el-option label="桥梁" value="bridge"></el-option>
            <el-option label="保护区" value="protected_area"></el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="选择航线" prop="wayline_uuid">
          <el-select
            v-model="form.wayline_uuid"
            placeholder="请选择航线"
            class="full-width"
            :loading="loadingWaylines"
            filterable
            :filter-method="handleWaylineFilter"
          >
            <el-option
              v-for="wayline in filteredWaylines"
              :key="wayline.id"
              :label="wayline.name || '未命名航线'"
              :value="wayline.wayline_id || wayline.id"
            >
              <span style="float: left">{{ wayline.name || '未命名航线' }}</span>
              <span style="float: right; color: #8492a6; font-size: 12px">
                {{ wayline.wayline_id || wayline.id }}
              </span>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="form.task_type" placeholder="请选择任务类型" class="full-width">
            <el-option label="立即任务 (Immediate)" value="immediate"></el-option>
            <el-option label="单次定时 (Timed)" value="timed"></el-option>
            <el-option label="重复任务 (Recurring)" value="recurring"></el-option>
            <el-option label="连续任务 (Continuous)" value="continuous"></el-option>
          </el-select>
        </el-form-item>

        <!-- 是否为保护区任务 -->
        <el-form-item label="保护区监测" prop="is_protected_area" class="item-aligned" v-if="false">
          <el-switch
            v-model="form.is_protected_area"
            active-text="是"
            inactive-text="否"
            inline-prompt
          />
        </el-form-item>

        <el-form-item label="返航高度" prop="rth_altitude">
          <el-input
            v-model.number="form.rth_altitude"
            placeholder="请输入 20-500 之间的整数"
            class="full-width"
          >
            <template #suffix>
              <span style="color: #94a3b8; margin-right: 5px;">米</span>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="返航模式" prop="rth_mode">
          <el-radio-group v-model="form.rth_mode">
            <el-radio value="optimal">最优路径 (Optimal)</el-radio>
            <el-radio value="preset">预设高度 (Preset)</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="航线精度" prop="wayline_precision_type">
          <el-radio-group v-model="form.wayline_precision_type">
            <el-radio value="rtk">RTK</el-radio>
            <el-radio value="gps">GPS</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="断点续飞" prop="resumable_status">
          <el-radio-group v-model="form.resumable_status">
            <el-radio value="auto">自动 (Auto)</el-radio>
            <el-radio value="manual">手动 (Manual)</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleDialogClose">取消</el-button>
          <el-button type="primary" @click="submitForm" :loading="submitting" :disabled="!sn">
            创建任务
          </el-button>
        </span>
      </template>
    </el-dialog>

    <el-dialog
      title="确认起飞"
      v-model="confirmDialogVisible"
      width="400px"
      class="create-task-dialog create-task-confirm-dialog"
      modal-class="create-task-modal"
      :before-close="handleConfirmClose"
      center
    >
      <div class="confirm-content">
        <p class="confirm-icon">🚀</p>
        <p class="confirm-text">任务已准备就绪</p>
        <p class="confirm-subtext">请确认是否立即下发并执行起飞任务？</p>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleConfirmClose">取消</el-button>
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
  name: 'CreateFlightTaskDialog',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    sn: {
      type: String,
      default: ''
    },
    dockName: {
      type: String,
      default: ''
    }
  },
  emits: ['update:modelValue', 'created'],
  data() {
    return {
      loadingWaylines: false,
      submitting: false,
      confirmDialogVisible: false,
      countdown: 5,
      timer: null,
      waylines: [],
      waylineKeyword: '',
      selectedWaylineType: 'all',
      form: {
        is_protected_area: false,
        name: '',
        sn: '',
        wayline_uuid: '',
        time_zone: 'Asia/Chongqing',
        rth_altitude: 70,
        rth_mode: 'preset',
        wayline_precision_type: 'rtk',
        resumable_status: 'manual',
        task_type: 'immediate',
        out_of_control_action_in_flight: 'return_home'
      },
      rules: {
        name: [
          { required: true, message: '请输入任务名称', trigger: 'blur' },
          { min: 3, max: 50, message: '长度在 3 到 50 个字符', trigger: 'blur' }
        ],
        wayline_uuid: [
          { required: true, message: '请选择航线', trigger: 'change' }
        ],
        task_type: [
          { required: true, message: '请选择任务类型', trigger: 'change' }
        ],
        rth_altitude: [
          { required: true, message: '请输入返航高度', trigger: 'blur' },
          { type: 'number', message: '返航高度必须为数字', trigger: 'blur' },
          { type: 'number', min: 20, max: 500, message: '高度需在 20 到 500 米之间', trigger: 'blur' }
        ]
      }
    }
  },
  computed: {
    dialogVisible: {
      get() {
        return this.modelValue
      },
      set(value) {
        this.$emit('update:modelValue', value)
      }
    },
    filteredWaylines() {
      const q = (this.waylineKeyword || '').trim().toLowerCase()
      if (!q) return this.waylines
      return (this.waylines || []).filter(w => {
        const name = (w?.name || '').toString().toLowerCase()
        const waylineId = (w?.wayline_id || '').toString().toLowerCase()
        const id = (w?.id ?? '').toString().toLowerCase()
        const detectType = (w?.detect_type || '').toString().toLowerCase()
        return (
          name.includes(q) ||
          waylineId.includes(q) ||
          id.includes(q) ||
          detectType.includes(q)
        )
      })
    }
  },
  watch: {
    modelValue(value) {
      if (value) {
        this.syncSn()
        this.fetchWaylines()
      } else {
        this.handleConfirmClose()
      }
    },
    sn: {
      immediate: true,
      handler() {
        this.syncSn()
      }
    }
  },
  beforeUnmount() {
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
  },
  methods: {
    syncSn() {
      this.form.sn = this.sn || ''
    },
    async fetchWaylines() {
      this.loadingWaylines = true
      this.waylineKeyword = ''
      try {
        const params = {}
        if (this.selectedWaylineType && this.selectedWaylineType !== 'all') {
          params.detect_type = this.selectedWaylineType
        }
        const res = await waylineApi.getWaylinesSelectAll(params)
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
    handleWaylineTypeChange() {
      this.form.wayline_uuid = ''
      this.waylineKeyword = ''
      this.fetchWaylines()
    },
    handleWaylineFilter(query) {
      this.waylineKeyword = query
    },
    submitForm() {
      if (!this.form.sn) {
        ElMessage.warning('请先选择机场')
        return
      }
      this.$refs.taskForm.validate((valid) => {
        if (valid) {
          this.startCountdown()
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
      this.handleConfirmClose()
      this.resetForm()
      this.dialogVisible = false
    },
    handleConfirmClose() {
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
          sn: this.form.sn
        }
        const res = await flightTaskApi.createFlightTask(payload)
        if (res.code === 0) {
          ElMessage.success('任务创建成功！')
          this.$emit('created', res)
          this.handleDialogClose()
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
      if (this.$refs.taskForm) {
        this.$refs.taskForm.resetFields()
      }
      this.form.name = ''
      this.form.wayline_uuid = ''
      this.form.rth_altitude = 100
      this.form.rth_mode = 'preset'
      this.form.wayline_precision_type = 'rtk'
      this.form.resumable_status = 'manual'
      this.form.task_type = 'immediate'
      this.form.out_of_control_action_in_flight = 'return_home'
      this.form.is_protected_area = false
      this.syncSn()
    }
  }
}
</script>

<style scoped>
:global(.create-task-modal) {
  background: rgba(10, 14, 39, 0.8) !important;
  backdrop-filter: blur(4px);
}

:deep(.create-task-dialog) {
  background: rgba(26, 31, 58, 0.95) !important;
  backdrop-filter: blur(20px);
  border-radius: 16px !important;
  border: 1px solid rgba(0, 212, 255, 0.3) !important;
  box-shadow: 0 16px 64px rgba(0, 0, 0, 0.5) !important;
  overflow: hidden;
  animation: modalSlideIn 0.3s ease;
}

:deep(.create-task-dialog .el-dialog__header) {
  padding: 20px 24px !important;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2) !important;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(0, 153, 255, 0.1) 100%) !important;
}

:deep(.create-task-dialog .el-dialog__title) {
  color: #00d4ff !important;
  font-weight: 700 !important;
  font-size: 18px;
}

:deep(.create-task-dialog .el-dialog__body) {
  padding: 24px !important;
  background: transparent !important;
  color: #e2e8f0 !important;
}

:deep(.create-task-dialog .el-dialog__footer) {
  padding: 16px 24px !important;
  border-top: 1px solid rgba(0, 212, 255, 0.1) !important;
  background: transparent !important;
}

:deep(.create-task-dialog .el-dialog__headerbtn) {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(239, 68, 68, 0.2);
  transition: all 0.3s ease;
}

:deep(.create-task-dialog .el-dialog__headerbtn:hover) {
  background: rgba(239, 68, 68, 0.3);
  transform: rotate(90deg);
}

:deep(.create-task-dialog .el-dialog__close) {
  color: #ef4444;
  font-size: 20px;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.dialog-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #00d4ff;
}

.dialog-subtitle {
  margin: 6px 0 0;
  font-size: 12px;
  color: #94a3b8;
}

.dialog-sn {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: #00d4ff;
  background: rgba(0, 212, 255, 0.12);
  padding: 6px 10px;
  border-radius: 10px;
  border: 1px solid rgba(0, 212, 255, 0.3);
  white-space: nowrap;
}

.task-form-dialog :deep(.el-form-item) {
  margin-bottom: 18px;
}

.task-form-dialog :deep(.el-form-item__label) {
  color: #94a3b8;
  font-weight: 500;
}

/* 修复对齐问题：为特定的非必填项模拟星号占位，并缩小字体防止突出 */
.task-form-dialog :deep(.item-aligned .el-form-item__label) {
  font-size: 13px; /* 稍微缩小字体 */
  letter-spacing: -0.5px; /* 紧凑字间距 */
}

.task-form-dialog :deep(.item-aligned .el-form-item__label)::before {
  content: '*';
  color: transparent;
  margin-right: 4px;
}

.task-form-dialog :deep(.el-input__wrapper),
.task-form-dialog :deep(.el-select__wrapper) {
  background-color: rgba(26, 31, 58, 0.95) !important;
  border: 1px solid rgba(0, 212, 255, 0.35) !important;
  box-shadow: none !important;
  outline: none !important;
  border-radius: 8px;
  padding: 1px 11px;
  height: 40px;
  transition: all 0.2s ease;
}

.task-form-dialog :deep(.el-input__wrapper:hover),
.task-form-dialog :deep(.el-select__wrapper:hover) {
  border-color: rgba(125, 211, 252, 0.85) !important;
  box-shadow: none !important;
}

.task-form-dialog :deep(.el-input__wrapper.is-focus),
.task-form-dialog :deep(.el-select__wrapper.is-focused) {
  border-color: rgba(125, 211, 252, 0.95) !important;
  box-shadow: none !important;
}

.task-form-dialog :deep(.el-input__inner) {
  color: #e0f2fe;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
}

.task-form-dialog :deep(.el-textarea__inner) {
  background-color: transparent !important;
  color: #e0f2fe;
}

.task-form-dialog :deep(.el-input__inner::placeholder) {
  color: #94a3b8;
}

.task-form-dialog :deep(.el-select__input) {
  color: #e0f2fe;
  background-color: transparent !important;
}

.task-form-dialog :deep(.el-input__suffix-inner .el-input__icon),
.task-form-dialog :deep(.el-select__caret) {
  color: #7dd3fc;
}

.task-form-dialog :deep(.el-radio-group) {
  gap: 18px;
}

.task-form-dialog :deep(.el-radio__label) {
  color: #cbd5e1;
}

.task-form-dialog :deep(.el-radio__input.is-checked + .el-radio__label) {
  color: #00d4ff;
}

:deep(.create-task-dialog .el-button) {
  border-radius: 8px !important;
  font-weight: 600;
  padding: 10px 20px;
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

.confirm-content {
  text-align: center;
  padding: 12px 0;
}

.confirm-icon {
  font-size: 36px;
  margin: 0 0 8px;
  filter: drop-shadow(0 0 12px rgba(0, 212, 255, 0.35));
}

.confirm-text {
  margin: 0;
  font-size: 16px;
  color: #ffffff;
}

.confirm-subtext {
  margin: 8px 0 0;
  font-size: 13px;
  color: #9fb0c8;
}
</style>
