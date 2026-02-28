<template>
  <div class="inspect-task-list-premium">
    <!-- 搜索和筛选 -->
    <div class="search-filters-premium">
      <div class="search-wrapper">
        <input 
          v-model="searchQuery"
          @input="handleSearch"
          placeholder="搜索任务ID、航线名称..."
          class="search-input"
        />
      </div>
      
      <!-- 自定义下拉框 - 状态筛选 -->
      <div class="custom-select-wrapper" v-click-outside="() => closeDropdown('status')">
        <div class="custom-select-trigger" @click="toggleDropdown('status')" :class="{ 'is-open': activeDropdown === 'status' }">
          <span>{{ getStatusLabel(statusFilter) || '全部状态' }}</span>
          <span class="arrow-icon">▼</span>
        </div>
        <div v-show="activeDropdown === 'status'" class="custom-select-options">
          <div class="option-item" :class="{ 'is-selected': statusFilter === '' }" @click="selectStatus('')">全部状态</div>
          <div class="option-item" :class="{ 'is-selected': statusFilter === 'pending' }" @click="selectStatus('pending')">待检测</div>
          <div class="option-item" :class="{ 'is-selected': statusFilter === 'processing' }" @click="selectStatus('processing')">检测中</div>
          <div class="option-item" :class="{ 'is-selected': statusFilter === 'done' }" @click="selectStatus('done')">已完成</div>
          <div class="option-item" :class="{ 'is-selected': statusFilter === 'failed' }" @click="selectStatus('failed')">失败</div>
        </div>
      </div>
      
      <!-- 自定义下拉框 - 检测类型筛选 (Level 1) -->
      <div class="custom-select-wrapper" v-click-outside="() => closeDropdown('category')">
        <div class="custom-select-trigger" @click="toggleDropdown('category')" :class="{ 'is-open': activeDropdown === 'category' }">
          <span>{{ getCategoryLabel(categoryFilter) || '全部类型' }}</span>
          <span class="arrow-icon">▼</span>
        </div>
        <div v-show="activeDropdown === 'category'" class="custom-select-options">
          <div class="option-item" :class="{ 'is-selected': categoryFilter === '' }" @click="selectCategory('')">全部类型</div>
          <div class="option-item" :class="{ 'is-selected': categoryFilter === 'rail' }" @click="selectCategory('rail')">铁路检测</div>
          <div class="option-item" :class="{ 'is-selected': categoryFilter === 'contactline' }" @click="selectCategory('contactline')">接触网检测</div>
          <div class="option-item" :class="{ 'is-selected': categoryFilter === 'bridge' }" @click="selectCategory('bridge')">桥梁检测</div>
          <div class="option-item" :class="{ 'is-selected': categoryFilter === 'protected_area' }" @click="selectCategory('protected_area')">保护区检测</div>
        </div>
      </div>

      <!-- 自定义下拉框 - 航线筛选 (Level 2) -->
      <div class="custom-select-wrapper wayline-select" v-click-outside="() => closeDropdown('wayline')">
        <div class="custom-select-trigger" @click="toggleDropdown('wayline')" :class="{ 'is-open': activeDropdown === 'wayline' }">
          <span>{{ getWaylineLabel(waylineFilter) || '全部航线' }}</span>
          <span class="arrow-icon">▼</span>
        </div>
        <div v-show="activeDropdown === 'wayline'" class="custom-select-options">
          <div class="option-item" :class="{ 'is-selected': waylineFilter === '' }" @click="selectWayline('')">全部航线</div>
          <div 
            v-for="wayline in filteredWaylines" 
            :key="wayline.id" 
            class="option-item"
            :class="{ 'is-selected': waylineFilter === wayline.id }"
            @click="selectWayline(wayline.id)"
          >
            {{ wayline.name }}
          </div>
        </div>
      </div>

      <button @click="resetFilters" class="action-btn view-btn clear-all-btn">
        重复筛选
      </button>
    </div>
    
    <!-- 任务表格 -->
    <div class="table-container">
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>加载中...</p>
      </div>
      
      <table v-else class="task-table">
        <thead>
          <tr>
            <th width="24%">巡检任务名</th>
            <th v-if="isSubTaskMode" width="10%">执行设备</th>
            <th v-if="isSubTaskMode" width="14%">航线名称</th>
            <th v-if="isSubTaskMode" width="8%">检测类型</th>
            <th width="14%">创建时间</th>
            <th width="8%">状态</th>
            <th width="8%">已清理</th>
            <th width="20%">操作</th> <!-- 增加操作列宽度 -->
          </tr>
        </thead>
        <tbody>
          <tr v-if="filteredTasks.length === 0">
            <td :colspan="isSubTaskMode ? 8 : 6" class="empty-row">暂无任务数据</td>
          </tr>
          <tr v-for="task in filteredTasks" :key="task.id" class="task-row">
            <td>
              <!-- 🔥 修复：父任务显示external_task_id，子任务显示dji_task_name -->
              <span class="task-name" :title="isSubTaskMode ? (task.dji_task_name || task.external_task_id) : task.external_task_id">
                {{ isSubTaskMode ? (task.dji_task_name || task.external_task_id || '--') : (task.external_task_id || '--') }}
              </span>
            </td>
            <td v-if="isSubTaskMode">
              <span class="device-badge" :class="{'has-sn': task.device_sn}">
                {{ task.device_sn || '--' }}
              </span>
            </td>
            <td v-if="isSubTaskMode">{{ task.wayline_details?.name || '--' }}</td>
            <td v-if="isSubTaskMode">
              <span class="category-badge">
                {{ task.detect_category_name || getCategoryName(task.detect_category) || '未设置' }}
              </span>
            </td>
            <td>
              <span class="datetime-text">{{ formatDate(task.created_at) }}</span>
            </td>
            <td>
              <span class="status-badge" :class="`status-${task.detect_status}`">
                {{ getStatusText(task.detect_status) }}
              </span>
            </td>
            <td>
              <span class="clean-badge" :class="task.is_cleaned ? 'cleaned' : 'not-cleaned'">
                {{ task.is_cleaned ? '已清理' : '未清理' }}
              </span>
            </td>
            <td>
              <div class="action-buttons">
                <button
                  v-if="isSubTaskMode && task.detect_status === 'done'"
                  @click="playbackSubTask(task)"
                  class="action-btn playback-btn"
                  :disabled="task.is_cleaned"
                >
                  回放
                </button>
                <button @click="viewTaskDetail(task)" class="action-btn view-btn" :disabled="task.is_cleaned">
                  {{ isSubTaskMode ? '查看' : '统计' }}
                </button>
                <button v-if="!isSubTaskMode" @click="viewSubTasks(task)" class="action-btn subtask-btn" :disabled="task.is_cleaned">
                  任务列表
                </button>
                <button
                  v-if="isSubTaskMode && (task.detect_status === 'scanning' || task.detect_status === 'processing')"
                  @click="forceDeleteTask(task)"
                  class="action-btn force-delete-btn"
                  title="强制结束并删除任务及其所有相关数据"
                  :disabled="task.is_cleaned"
                >
                  强制删除
                </button>
                <button v-if="isSubTaskMode" @click="deleteTask(task.id)" class="action-btn delete-btn" :disabled="task.is_cleaned">
                  删除
                </button>
                <button
                  v-if="!isSubTaskMode && !task.is_cleaned && isAdminUser"
                  @click="openCleanupDialog(task)"
                  class="action-btn cleanup-btn"
                  :disabled="cleanupLoading || cleanupDownloadLoading"
                >
                  清理
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- 分页器 -->
    <div class="pagination-premium" v-if="totalTasks > 0">
      <div class="pagination-info">
        显示 {{ Math.min((currentPage - 1) * pageSize + 1, totalTasks) }} - {{ Math.min(currentPage * pageSize, totalTasks) }} 条，共 {{ totalTasks }} 条
      </div>
      <div class="pagination-controls">
        <button @click="handlePageChange(currentPage - 1)" :disabled="currentPage === 1" class="pagination-btn">
          ‹
        </button>
        <input
          type="number"
          :value="currentPage"
          @change="handlePageChange(Number($event.target.value))"
          class="page-input"
          min="1"
          :max="Math.ceil(totalTasks / pageSize)"
        />
        <span class="pagination-separator">/</span>
        <span class="total-pages">{{ Math.ceil(totalTasks / pageSize) || 1 }}</span>
        <button @click="handlePageChange(currentPage + 1)" :disabled="currentPage >= Math.ceil(totalTasks / pageSize)" class="pagination-btn">
          ›
        </button>
      </div>
    </div>
    
    <!-- 父任务详情对话框 -->
    <Teleport to="body">
      <div v-if="showDetailDialog" class="modal-overlay" @click.self="showDetailDialog = false">
        <div class="modal-premium detail-modal" :class="isCurrentParentTask ? 'detail-modal--parent' : 'detail-modal--child'">
          <div class="modal-header">
            <h3 class="modal-title">{{ isCurrentParentTask ? '统计详情' : '子任务详情' }}</h3>
            <button @click="showDetailDialog = false" class="modal-close">×</button>
          </div>
          <div class="modal-body">
            <div class="detail-grid">
              <div class="detail-item">
                <span class="detail-label">任务ID</span>
                <span class="detail-value">{{ currentTask?.id }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">巡检任务名</span>
                <span class="detail-value">{{ currentTask?.dji_task_name || currentTask?.external_task_id || '--' }}</span>
              </div>
              <div v-if="!isCurrentParentTask" class="detail-item">
                <span class="detail-label">检测类型</span>
                <span class="detail-value">
                  {{ currentTask?.detect_category_name || getCategoryName(currentTask?.detect_category) || '--' }}
                </span>
              </div>
              <div v-if="!isCurrentParentTask" class="detail-item">
                <span class="detail-label">航线</span>
                <span class="detail-value">
                  {{ currentTask?.wayline_details?.name || getWaylineLabel(currentTask?.wayline) || '--' }}
                </span>
              </div>
              <div class="detail-item">
                <span class="detail-label">创建时间</span>
                <span class="detail-value">{{ formatDate(currentTask?.created_at) }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">检测状态</span>
                <span class="status-badge" :class="`status-${currentTask?.detect_status}`">
                  {{ getStatusText(currentTask?.detect_status) }}
                </span>
              </div>
              <div class="detail-item">
                <span class="detail-label">媒体清理状态</span>
                <span class="clean-badge" :class="currentTask?.is_cleaned ? 'cleaned' : 'not-cleaned'">
                  {{ currentTask?.is_cleaned ? '已清理' : '未清理' }}
                </span>
              </div>
              <div class="detail-item">
                <span class="detail-label">图片总数</span>
                <span class="detail-value">{{ currentTaskTotalImages }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">异常数</span>
                <span class="detail-value">{{ currentTaskAlarmCount }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">异常率</span>
                <span class="detail-value">{{ calculateAnomalyRate(currentTaskAlarmCount, currentTaskTotalImages) }}</span>
              </div>
            </div>

            <div v-if="isCurrentParentTask" class="parent-chart-section">
              <div v-if="parentDonutSeries.length" class="parent-chart-wrap">
                <DonutRing
                  style="--donut-size: 120px"
                  :series="parentDonutSeries"
                  total-label="图片总数"
                  :total-value="parentDonutTotalImages"
                  :clickable="true"
                  @segment-click="handleParentSegmentClick"
                />
                <div class="parent-chart-legend">
                  <div v-for="item in parentDonutSeries" :key="item.id" class="legend-item">
                    <span class="legend-dot" :style="{ background: item.color }"></span>
                    <span class="legend-name">{{ item.name }}</span>
                    <span class="legend-value">{{ item.total_images }}</span>
                    <span class="legend-percent">{{ getPercent(item.total_images, parentDonutTotalImages) }}</span>
                  </div>
                </div>
              </div>
              <div v-else class="empty-row">暂无子任务统计</div>

              <div v-if="selectedParentSlice" class="parent-chart-selected">
                <span class="selected-name">{{ selectedParentSlice.name }}</span>
                <span class="selected-rate">{{ calculateAnomalyRate(selectedParentSlice.alarm_count, selectedParentSlice.total_images) }}</span>
                <span class="selected-meta">({{ selectedParentSlice.alarm_count || 0 }}/{{ selectedParentSlice.total_images || 0 }})</span>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button @click="showDetailDialog = false" class="modal-btn secondary-btn">关闭</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 子任务对话框 -->
    <Teleport to="body">
      <div v-if="showSubTaskDialog" class="modal-overlay" @click.self="showSubTaskDialog = false">
        <div class="modal-premium wide-modal">
          <div class="modal-header">
            <h3 class="modal-title">任务列表 - {{ currentTask?.external_task_id || currentTask?.id }}巡检任务</h3>
            <button @click="showSubTaskDialog = false" class="modal-close">×</button>
          </div>
          <div class="modal-body subtask-body">
            <div v-if="!subTasks.length" class="empty-row">暂无子任务</div>
            <table v-else class="task-table subtask-table">
              <thead>
                <tr>
                  <th width="80">ID</th>
                  <th width="200">任务名</th>
                  <th width="140">执行设备</th> <!-- 🔥 新增 -->
                  <th width="250">航线名称</th>
                  <th width="120">检测类型</th>
                  <th width="80">总数</th> <!-- 🔥 新增 -->
                  <th width="80">异常数</th> <!-- 🔥 新增 -->
                  <th width="80">异常率</th> <!-- 🔥 新增 -->
                  <th width="170">开始时间</th>
                  <th width="170">完成时间</th>
                  <th width="100">状态</th>
                  <th width="120">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in subTasks" :key="item.id" class="task-row">
                  <td><span class="id-badge">{{ item.id }}</span></td>
                  <td>{{ item.external_task_id || '--' }}</td>
                  <td><span class="device-badge">{{ item.device_sn || '--' }}</span></td> <!-- 🔥 新增 -->
                  <td>{{ item.wayline_details?.name || getWaylineLabel(item.wayline) || '--' }}</td>
                  <td>
                    <span class="category-badge">
                      {{ item.detect_category_name || getCategoryName(item.detect_category) || '未设置' }}
                    </span>
                  </td>
                  <td>{{ item.total_images || 0 }}</td>
                  <td>
                    <span class="alarm-count-text" :class="{'has-alarm': item.alarm_count > 0}">
                      {{ item.alarm_count || 0 }}
                    </span>
                  </td>
                  <td>{{ calculateAnomalyRate(item.alarm_count, item.total_images) }}</td>
                  <td><span class="datetime-text">{{ formatDate(item.started_at) }}</span></td>
                  <td><span class="datetime-text">{{ formatDate(item.finished_at) }}</span></td>
                  <td>
                    <span class="status-badge" :class="`status-${item.detect_status}`">
                      {{ getStatusText(item.detect_status) }}
                    </span>
                  </td>
                  <td>
                    <button 
                      v-if="item.detect_status === 'done'"
                      @click="playbackSubTask(item)" 
                      class="action-btn playback-btn"
                    >
                      回放
                    </button>
                    <span v-else class="text-muted">未完成</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="modal-footer">
            <button @click="showSubTaskDialog = false" class="modal-btn secondary-btn">关闭</button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showCleanupDialog" class="modal-overlay" @click.self="closeCleanupDialog">
        <div class="modal-premium cleanup-modal">
          <div class="modal-header">
            <h3 class="modal-title">清理确认 - {{ cleanupPreview?.parent?.display_name || cleanupPreview?.parent?.external_task_id || cleanupParentTask?.external_task_id || cleanupParentTask?.id }}</h3>
            <button @click="closeCleanupDialog" class="modal-close">×</button>
          </div>
          <div class="modal-body cleanup-body">
            <div v-if="cleanupLoading" class="loading-state">
              <div class="loading-spinner"></div>
              <p>加载中...</p>
            </div>
            <div v-else>
              <div class="cleanup-tip">
                请确认已转存 {{ cleanupPreview?.sub_task_count || 0 }} 个任务的 MinIO 媒体文件
              </div>
              <div class="cleanup-prefixes">
                <div v-if="!(cleanupPreview?.minio_prefixes || []).length" class="empty-row">暂无可清理的 MinIO 目录</div>
                <div v-else class="prefix-list">
                  <div v-for="(p, idx) in cleanupPreview.minio_prefixes" :key="`${p.bucket}-${p.prefix}-${idx}`" class="prefix-item">
                    <span class="prefix-bucket">{{ p.bucket }}</span>
                    <span class="prefix-path">{{ p.prefix }}</span>
                  </div>
                </div>
              </div>
              <div class="cleanup-confirm-row">
                <span class="cleanup-confirm-label">请输入已转存</span>
                <input v-model="cleanupConfirmText" class="cleanup-confirm-input" placeholder="已转存" />
              </div>
            </div>
            <div v-if="cleanupDownloadLoading" class="cleanup-download-overlay">
              <div class="cleanup-download-overlay-card">
                <div class="loading-spinner"></div>
                <p class="cleanup-download-title">正在生成并下载备份...</p>
                <p class="cleanup-download-sub">请不要关闭弹窗或刷新页面</p>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button @click="downloadCleanupZip" class="modal-btn download-btn" :disabled="cleanupLoading || cleanupDownloadLoading || !(cleanupPreview?.minio_prefixes || []).length">
              {{ cleanupDownloadLoading ? '下载中...' : '下载备份' }}
            </button>
            <button @click="closeCleanupDialog" class="modal-btn secondary-btn" :disabled="cleanupLoading || cleanupDownloadLoading">取消</button>
            <button @click="confirmCleanup" class="modal-btn primary-btn" :disabled="cleanupLoading || cleanupDownloadLoading || cleanupConfirmText !== '已转存'">确认清理</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script>
import inspectTaskApi from '../api/inspectTaskApi'
import waylineApi from '../api/waylineApi'
import { ElMessage } from 'element-plus'
import DonutRing from './dashboard/DonutRing.vue'

export default {
  name: 'InspectTaskList',
  components: {
    DonutRing
  },
  data() {
    return {
      tasks: [],
      waylines: [],
      categories: [], // 检测类型列表
      filteredTasks: [],
      loading: false,
      searchQuery: '',
      statusFilter: '',
      waylineFilter: '',
      categoryFilter: '', // 🔥 新增：检测类型筛选
      currentPage: 1,
      pageSize: 10,
      totalTasks: 0,
      showDetailDialog: false,
      currentTask: null,
      showSubTaskDialog: false,
      subTasks: [],
      showCleanupDialog: false,
      cleanupPreview: null,
      cleanupParentTask: null,
      cleanupConfirmText: '',
      cleanupLoading: false,
      cleanupDownloadLoading: false,
      activeDropdown: '',
      parentDonutSeries: [],
      parentDonutTotalImages: 0,
      selectedParentSlice: null
    }
  },
  directives: {
    'click-outside': {
      mounted(el, binding) {
        el.clickOutsideEvent = function(event) {
          if (!(el === event.target || el.contains(event.target))) {
            binding.value(event)
          }
        }
        document.body.addEventListener('click', el.clickOutsideEvent)
      },
      unmounted(el) {
        document.body.removeEventListener('click', el.clickOutsideEvent)
      }
    }
  },
  async mounted() {
    await this.loadWaylines()
    await this.loadTasks()
  },
  computed: {
    isSubTaskMode() {
      return Boolean(this.categoryFilter || this.waylineFilter)
    },
    isAdminUser() {
      return Boolean(this.$store?.getters?.isAdmin)
    },
    isCurrentParentTask() {
      return this.isParentTask(this.currentTask)
    },
    currentTaskTotalImages() {
      const n = Number(this.currentTask?.total_images)
      if (Number.isFinite(n)) return n
      if (this.isCurrentParentTask && this.parentDonutSeries.length) return this.parentDonutTotalImages
      return 0
    },
    currentTaskAlarmCount() {
      const n = Number(this.currentTask?.alarm_count)
      if (Number.isFinite(n)) return n
      if (this.isCurrentParentTask && this.parentDonutSeries.length) {
        return this.parentDonutSeries.reduce((sum, item) => sum + Number(item.alarm_count || 0), 0)
      }
      return 0
    },
    filteredWaylines() {
      if (!this.categoryFilter) {
        return this.waylines
      }
      
      const filter = this.categoryFilter.toLowerCase()
      const variantsMap = {
        'rail': ['rail', 'track'],
        'contactline': ['contactline', 'catenary', 'overhead', 'insulator', 'pole'],
        'bridge': ['bridge'],
        'protected_area': ['protected_area', 'protection_zone', 'protection_area']
      }
      
      const targetVariants = variantsMap[filter] || [filter]
      
      return this.waylines.filter(wayline => {
        const type = (wayline.detect_type || '').toLowerCase()
        return targetVariants.some(v => type.includes(v))
      })
    }
  },
  methods: {
    resetFilters() {
      this.searchQuery = ''
      this.statusFilter = ''
      this.categoryFilter = ''
      this.waylineFilter = ''
      this.activeDropdown = ''
      this.currentPage = 1
      this.loadTasks()
    },
    async openCleanupDialog(task) {
      this.cleanupParentTask = task
      this.cleanupPreview = null
      this.cleanupConfirmText = ''
      this.cleanupLoading = true
      this.cleanupDownloadLoading = false
      this.showCleanupDialog = true
      try {
        const res = await inspectTaskApi.getCleanupPreview(task.id)
        this.cleanupPreview = res
      } catch (e) {
        const msg = e?.response?.data?.detail || '获取清理预览失败'
        ElMessage.error(msg)
        this.showCleanupDialog = false
      } finally {
        this.cleanupLoading = false
      }
    },
    closeCleanupDialog() {
      if (this.cleanupLoading || this.cleanupDownloadLoading) return
      this.showCleanupDialog = false
      this.cleanupPreview = null
      this.cleanupParentTask = null
      this.cleanupConfirmText = ''
      this.cleanupLoading = false
      this.cleanupDownloadLoading = false
    },
    async confirmCleanup() {
      if (!this.cleanupParentTask) return
      if (this.cleanupConfirmText !== '已转存') return
      if (this.cleanupLoading || this.cleanupDownloadLoading) return
      this.cleanupLoading = true
      try {
        await inspectTaskApi.confirmCleanup(this.cleanupParentTask.id, { confirm_text: this.cleanupConfirmText })
        ElMessage.success('清理完成')
        this.showCleanupDialog = false
        this.cleanupPreview = null
        this.cleanupParentTask = null
        this.cleanupConfirmText = ''
        await this.loadTasks()
      } catch (e) {
        const msg = e?.response?.data?.detail || '清理失败'
        ElMessage.error(msg)
      } finally {
        this.cleanupLoading = false
      }
    },
    async downloadCleanupZip() {
      if (!this.cleanupParentTask) return
      if (this.cleanupLoading || this.cleanupDownloadLoading) return
      if (!((this.cleanupPreview?.minio_prefixes || []).length)) return
      this.cleanupDownloadLoading = true
      try {
        const blob = await inspectTaskApi.downloadCleanupZip(this.cleanupParentTask.id)
        const raw = (this.cleanupPreview?.parent?.external_task_id || this.cleanupParentTask?.external_task_id || this.cleanupParentTask?.id || 'task').toString()
        const label = raw.replaceAll('/', '_').replaceAll('\\', '_').replace(/\s+/g, '_')
        const filename = `${label}-minio-images.zip`
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(url)
      } catch (e) {
        ElMessage.error('下载失败')
      } finally {
        this.cleanupDownloadLoading = false
      }
    },
    isParentTask(task) {
      if (!task) return false
      if (typeof task.is_parent_task === 'boolean') return task.is_parent_task
      return !task.parent_task
    },
    getPercent(part, total) {
      if (!total || total <= 0) return '0%'
      const pct = (Number(part || 0) / total) * 100
      return pct.toFixed(2) + '%'
    },
    buildParentDonutSeries(subTasks) {
      const palette = ['#00d4ff', '#3b82f6', '#10b981', '#f59e0b', '#a855f7', '#ef4444', '#22c55e', '#eab308']
      const normalized = (subTasks || [])
        .map((t, idx) => {
          const total_images = Number(t.total_images || 0)
          const alarm_count = Number(t.alarm_count || 0)
          return {
            id: t.id ?? idx,
            name: t.display_name || t.dji_task_name || t.external_task_id || `任务-${t.id ?? idx}`,
            value: total_images,
            color: palette[idx % palette.length],
            total_images,
            alarm_count
          }
        })
        .filter(item => item.total_images > 0)

      this.parentDonutSeries = normalized
      this.parentDonutTotalImages = normalized.reduce((sum, item) => sum + Number(item.total_images || 0), 0)
    },
    async ensureParentDonut(task) {
      this.parentDonutSeries = []
      this.parentDonutTotalImages = 0
      this.selectedParentSlice = null

      const list = Array.isArray(task?.sub_tasks_list) ? task.sub_tasks_list : null
      if (list && list.length) {
        this.buildParentDonutSeries(list)
        return
      }
      try {
        const res = await inspectTaskApi.getSubTasks(task.id)
        const subTasks = Array.isArray(res) ? res : (res?.results || [])
        this.buildParentDonutSeries(subTasks)
      } catch (e) {
        this.parentDonutSeries = []
        this.parentDonutTotalImages = 0
      }
    },
    handleParentSegmentClick(item) {
      this.selectedParentSlice = item
      ElMessage.info(`${item.name} 异常率 ${this.calculateAnomalyRate(item.alarm_count, item.total_images)}`)
    },
    handleCategoryChange() {
      this.waylineFilter = '' // Reset wayline filter
      this.currentPage = 1
      this.loadTasks()
    },
    // 下拉框控制方法
    toggleDropdown(type) {
      if (this.activeDropdown === type) {
        this.activeDropdown = ''
      } else {
        this.activeDropdown = type
      }
    },
    closeDropdown(type) {
      if (this.activeDropdown === type) {
        this.activeDropdown = ''
      }
    },
    // 选项选择方法
    selectStatus(status) {
      this.statusFilter = status
      this.activeDropdown = ''
      this.currentPage = 1
      this.loadTasks()
    },
    selectCategory(category) {
      this.categoryFilter = category
      this.activeDropdown = ''
      this.currentPage = 1
      this.handleCategoryChange()
    },
    selectWayline(id) {
      this.waylineFilter = id
      this.activeDropdown = ''
      this.currentPage = 1
      this.loadTasks()
    },
    // 获取显示标签
    getStatusLabel(status) {
      if (!status) return ''
      return this.getStatusText(status)
    },
    getCategoryLabel(category) {
      if (!category) return ''
      return this.getCategoryName(category)
    },
    getWaylineLabel(id) {
      if (!id) return ''
      const wayline = this.waylines.find(w => w.id === id)
      return wayline ? wayline.name : id
    },
    async loadWaylines() {
      try {
        let allWaylines = []
        let page = 1
        let hasNext = true
        
        while (hasNext) {
          const response = await waylineApi.getWaylines({ page, page_size: 100 })
          console.log(`📋 [航线列表] 第${page}页数据:`, response)
          
          let results = []
          if (Array.isArray(response)) {
            results = response
            hasNext = false // 如果直接返回数组，说明没有分页
          } else {
            results = response?.results || []
            if (!response.next) {
              hasNext = false
            } else {
              page++
            }
          }
          
          allWaylines = allWaylines.concat(results)
        }
        
        this.waylines = allWaylines
        console.log(`📋 [航线列表] 共加载了 ${this.waylines.length} 条航线`)
      } catch (error) {
        console.error('❌ [航线列表] 加载失败:', error)
        ElMessage.error('加载航线列表失败')
      }
    },
    
    async loadTasks() {
      this.loading = true
      try {
        const params = {
          page: this.currentPage,
          page_size: this.pageSize
        }

        // 🔥 子任务模式：选了检测类型或航线 -> 查子任务；否则查父任务
        if (this.isSubTaskMode) {
          // 先获取检测类型的 ID
          if (this.categoryFilter) {
            const alarmApi = await import('../api/alarmApi')
            const categoryRes = await alarmApi.default.getAlarmCategories({ page_size: 100 })
            const categories = Array.isArray(categoryRes) ? categoryRes : (categoryRes?.results || [])
            const normalizeCode = (code) => {
              const v = (code || '').toString().toLowerCase().trim()
              if (v === 'rail' || v === 'track') return 'rail'
              if (v === 'contactline' || v === 'catenary' || v === 'overhead' || v === 'insulator' || v === 'pole') return 'contactline'
              if (v === 'bridge') return 'bridge'
              if (v === 'protected_area' || v === 'protection_zone' || v === 'protection_area') return 'protected_area'
              return v
            }
            const targetCategory = categories.find(c => normalizeCode(c.code) === this.categoryFilter)

            if (targetCategory) {
              params.detect_category = targetCategory.id
            }
          }
          params.parent_task__isnull = 'false'
        } else {
          // 没选类型，只显示父任务
          params.parent_task__isnull = 'true'
        }

        if (this.statusFilter) {
          params.detect_status = this.statusFilter
        }

        if (this.waylineFilter) {
          params.wayline = this.waylineFilter
        }

        if (this.searchQuery) {
          params.search = this.searchQuery
        }

        const response = await inspectTaskApi.getInspectTasks(params)

        const results = response?.results || []
        this.tasks = this.isSubTaskMode ? results.filter(t => t?.parent_task != null) : results
        this.totalTasks = response?.count || 0
        this.filteredTasks = this.tasks

        // 🔥 新增：如果当前页超出范围，自动调整到最后一页
        const maxPage = Math.ceil(this.totalTasks / this.pageSize) || 1
        if (this.currentPage > maxPage && maxPage > 0) {
          this.currentPage = maxPage
          // 重新加载正确的页码
          await this.loadTasks()
        }
      } catch (error) {
        console.error('加载巡检任务失败:', error)

        // 🔥 新增：如果是404或页码无效错误，自动调整到第一页
        if (error.response?.status === 404 || error.response?.data?.detail === 'Invalid page.') {
          console.warn('页码无效，重置到第一页')
          this.currentPage = 1
          await this.loadTasks()
          return
        }

        ElMessage.error('加载巡检任务失败')
      } finally {
        this.loading = false
      }
    },
    
    handleSearch() {
      this.currentPage = 1
      this.loadTasks()
    },
    
    handlePageChange(page) {
      // 验证页码有效性
      if (!page || page < 1 || isNaN(page)) {
        page = 1
      }

      // 计算最大页码
      const maxPage = Math.ceil(this.totalTasks / this.pageSize) || 1

      // 如果页码超出范围,调整到最后一页
      if (page > maxPage) {
        page = maxPage
        this.currentPage = page
      } else {
        this.currentPage = page
      }

      // 加载任务
      this.loadTasks()
    },
    
    async viewTaskDetail(task) {
      this.currentTask = task
      this.showDetailDialog = true
      if (this.isParentTask(task)) {
        await this.ensureParentDonut(task)
      } else {
        this.parentDonutSeries = []
        this.parentDonutTotalImages = 0
        this.selectedParentSlice = null
      }
    },

    async viewSubTasks(task) {
      try {
        const res = await inspectTaskApi.getSubTasks(task.id)
        const list = Array.isArray(res) ? res : (res?.results || [])
        this.subTasks = list
        this.currentTask = task
        this.showSubTaskDialog = true
      } catch (error) {
        console.error('加载子任务失败:', error)
        ElMessage.error('加载子任务失败')
      }
    },
    
    async deleteTask(taskId) {
      if (!confirm('确定要删除这个巡检任务吗？')) {
        return
      }

      try {
        await inspectTaskApi.deleteInspectTask(taskId)
        ElMessage.success('删除成功')
        await this.loadTasks()
      } catch (error) {
        console.error('删除任务失败:', error)
        ElMessage.error('删除任务失败')
      }
    },

    async forceDeleteTask(task) {
      const taskInfo = task.external_task_id || task.id
      const confirmMsg = `⚠️ 警告：强制删除将彻底删除任务及其所有相关数据！\n\n` +
        `任务: ${taskInfo}\n` +
        `包括:\n` +
        `- 所有图片记录 (InspectImage)\n` +
        `- 所有告警记录 (Alarm)\n` +
        `- 任务本身 (InspectTask)\n\n` +
        `此操作不可恢复！确定要继续吗？`

      if (!confirm(confirmMsg)) {
        return
      }

      // 二次确认
      if (!confirm('最后确认：真的要强制删除这个任务吗？所有相关数据将被永久删除！')) {
        return
      }

      try {
        ElMessage.info({
          message: '正在强制删除任务...',
          duration: 2000
        })

        const response = await inspectTaskApi.forceDeleteTask(task.id)

        ElMessage.success({
          message: `强制删除成功！已删除 ${response.deleted_images || 0} 张图片和相关告警`,
          duration: 3000
        })

        // 重新加载任务列表
        await this.loadTasks()
      } catch (error) {
        console.error('强制删除任务失败:', error)
        const errorMsg = error.response?.data?.detail || error.message || '强制删除任务失败'
        ElMessage.error({
          message: errorMsg,
          duration: 5000
        })
      }
    },
    
    calculateAnomalyRate(alarmCount, totalImages) {
      if (!totalImages || totalImages <= 0) return '0%'
      const rate = ((alarmCount || 0) / totalImages) * 100
      return rate.toFixed(2) + '%'
    },
    playbackSubTask(subTask) {
      // 跳转到轮播检测页，并传递任务信息
      this.$router.push({
        name: 'CarouselDetection',
        query: {
          playback: subTask.external_task_id || subTask.id
        }
      })
      ElMessage.success(`开始回放任务: ${subTask.external_task_id || subTask.id}`)
    },
    
    getWaylineName(task) {
      return task?.wayline_details?.name || '--'
    },
    
    // 🔥 新增：获取检测类型名称
    getCategoryName(categoryValue) {
      if (!categoryValue) return ''
      if (typeof categoryValue !== 'string') return ''
      const categoryMap = {
        'rail': '铁路检测',
        'contactline': '接触网检测',
        'bridge': '桥梁检测',
        'protected_area': '保护区检测',
        'catenary': '接触网检测',
        'overhead': '接触网检测',
        'insulator': '接触网检测',
        'pole': '接触网检测',
        'protection_zone': '保护区检测'
      }
      return categoryMap[categoryValue] || ''
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
    
    formatDate(dateString) {
      if (!dateString) return '--'
      const date = new Date(dateString)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }
  }
}
</script>

<style scoped>
/* 主容器 */
.inspect-task-list-premium {
  padding: 28px 36px;
  animation: cardSlideIn 0.5s ease-out;
  height: 100%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
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

/* 搜索和筛选区域 */
.search-filters-premium {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.search-wrapper {
  position: relative;
  flex: 1 1 360px;
  min-width: 260px;
}

/* 移除旧的 search-icon 样式 */

.search-input {
  width: 100%;
  padding: 12px 16px; /* 调整 padding，移除左侧图标的空隙 */
  background: rgba(10, 14, 39, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 10px; /* 统一圆角 */
  color: #e2e8f0;
  font-size: 14px;
  transition: all 0.3s ease;
}

.search-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* 自定义下拉框样式 - 复用 AlarmList.vue */
.custom-select-wrapper {
  position: relative;
  min-width: 160px; /* 默认宽度 */
}

/* 航线筛选特殊宽度 */
.custom-select-wrapper.wayline-select {
  min-width: 320px;
}

.custom-select-trigger {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(10, 14, 39, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.3); /* 使用蓝色系边框 */
  border-radius: 10px;
  color: #e2e8f0;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  user-select: none;
}

.custom-select-trigger:hover,
.custom-select-trigger.is-open {
  border-color: #3b82f6;
  box-shadow: 0 0 15px rgba(59, 130, 246, 0.15);
  background: rgba(10, 14, 39, 0.8);
}

.custom-select-trigger span:first-child {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-right: 8px;
}

.arrow-icon {
  font-size: 10px;
  color: #64748b;
  transition: transform 0.3s ease;
  margin-left: 8px;
}

.custom-select-trigger.is-open .arrow-icon {
  transform: rotate(180deg);
  color: #3b82f6;
}

.custom-select-options {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  z-index: 100;
  max-height: 240px;
  overflow-y: auto;
  animation: dropdownFadeIn 0.2s ease-out;
}

@keyframes dropdownFadeIn {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

.option-item {
  padding: 10px 16px;
  color: #cbd5e1;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.option-item:last-child {
  border-bottom: none;
}

.option-item:hover {
  background: rgba(59, 130, 246, 0.1);
  color: #fff;
}

.option-item.is-selected {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
  font-weight: 500;
}

/* 滚动条美化 */
.custom-select-options::-webkit-scrollbar {
  width: 6px;
}

.custom-select-options::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
}

.custom-select-options::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.3);
  border-radius: 3px;
}

.custom-select-options::-webkit-scrollbar-thumb:hover {
  background: rgba(59, 130, 246, 0.5);
}

/* 表格容器 */
.table-container {
  /* overflow-x: auto;  移除横向滚动 */
  overflow-y: auto;
  margin-bottom: 20px;
  flex: 1;
  min-height: 0;
  scrollbar-gutter: stable; /* 预留滚动条空间防止闪烁 */
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #94a3b8;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(59, 130, 246, 0.2);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 表格样式 */
.task-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 8px;
}

.task-table thead tr {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(37, 99, 235, 0.15) 100%);
}

.task-table th {
  padding: 14px 12px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: #3b82f6;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.task-table th:first-child {
  border-radius: 8px 0 0 8px;
}

.task-table th:last-child {
  border-radius: 0 8px 8px 0;
}

.task-row {
  background: rgba(10, 14, 39, 0.4);
  transition: all 0.3s ease;
}

.task-row:hover {
  background: rgba(10, 14, 39, 0.6);
  transform: translateX(2px);
}

.task-table td {
  padding: 14px 12px;
  color: #cbd5e1;
  font-size: 13px;
  border-top: 1px solid rgba(59, 130, 246, 0.1);
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
}

.task-table td:first-child {
  border-left: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 8px 0 0 8px;
}

.task-table td:last-child {
  border-right: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 0 8px 8px 0;
}

.empty-row {
  text-align: center;
  padding: 40px 20px !important;
  color: #64748b;
}

/* 徽章样式 */
.id-badge {
  display: inline-block;
  padding: 4px 10px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border-radius: 6px;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  font-family: 'Courier New', monospace;
}

/* 🔥 新增：任务名称样式 */
.task-name {
  display: inline-block;
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #e2e8f0;
  font-weight: 500;
  cursor: help;
}

.status-badge {
  display: inline-block;
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
}

.status-pending {
  background: rgba(234, 179, 8, 0.2);
  color: #fbbf24;
  border: 1px solid rgba(234, 179, 8, 0.3);
}

.status-processing {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
  animation: statusPulse 2s ease-in-out infinite;
}

.status-done {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.status-failed {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

@keyframes statusPulse {
  0%, 100% {
    box-shadow: 0 0 5px rgba(59, 130, 246, 0.5);
  }
  50% {
    box-shadow: 0 0 15px rgba(59, 130, 246, 0.8);
  }
}

.category-badge {
  display: inline-block;
  padding: 5px 12px;
  background: rgba(139, 92, 246, 0.2);
  color: #a78bfa;
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.clean-badge {
  display: inline-block;
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.clean-badge.cleaned {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.clean-badge.not-cleaned {
  background: rgba(100, 116, 139, 0.2);
  color: #94a3b8;
  border: 1px solid rgba(100, 116, 139, 0.3);
}

.datetime-text {
  font-family: 'Courier New', monospace;
  color: #94a3b8;
  font-size: 12px;
}

.alarm-count-text {
  font-weight: 600;
  color: #e2e8f0;
}

.alarm-count-text.has-alarm {
  color: #ef4444;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.action-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.view-btn {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #fff;
}

.view-btn:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
  transform: translateY(-1px);
}

.sync-btn {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  color: #fff;
}

.sync-btn:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
  transform: translateY(-1px);
}

.detect-btn {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #fff;
}

.detect-btn:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
  transform: translateY(-1px);
}

.delete-btn {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: #fff;
}

.delete-btn:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
  transform: translateY(-1px);
}

.force-delete-btn {
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  color: #fff;
  font-weight: 600;
  animation: pulse-orange 2s ease-in-out infinite;
}

.force-delete-btn:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(249, 115, 22, 0.5);
  transform: translateY(-1px);
}

@keyframes pulse-orange {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(249, 115, 22, 0.7);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(249, 115, 22, 0);
  }
}

.playback-btn {
  background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%);
  color: #fff;
}

.playback-btn:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(20, 184, 166, 0.4);
  transform: translateY(-1px);
}

.subtask-btn {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: #fff;
}

.subtask-btn:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
  transform: translateY(-1px);
}

.cleanup-btn {
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
  color: #fff;
}

.cleanup-btn:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(6, 182, 212, 0.4);
  transform: translateY(-1px);
}

.text-muted {
  color: #64748b;
  font-size: 12px;
}

.device-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  color: #94a3b8; /* Default muted color for '--' */
  background: rgba(148, 163, 184, 0.1);
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.device-badge.has-sn {
  color: #c084fc;
  border-color: rgba(192, 132, 252, 0.3);
  background: rgba(192, 132, 252, 0.1);
}

/* 分页器 */
.pagination-premium {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
}

.pagination-info {
  color: #94a3b8;
  font-size: 13px;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  color: #3b82f6;
  cursor: pointer;
  font-size: 18px;
  transition: all 0.3s ease;
}

.pagination-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.3);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.pagination-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.page-input {
  width: 50px;
  padding: 6px 8px;
  background: rgba(10, 14, 39, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  color: #e2e8f0;
  text-align: center;
  font-size: 13px;
}

.page-input:focus {
  outline: none;
  border-color: #3b82f6;
}

.pagination-separator {
  color: #64748b;
  font-size: 14px;
}

.clear-all-btn {
  margin-left: auto;
  padding: 8px 16px;
  font-weight: 600;
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.4);
  color: #3b82f6;
}

.clear-all-btn:hover {
  background: rgba(59, 130, 246, 0.3);
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.2);
}

.total-pages {
  color: #94a3b8;
  font-size: 13px;
  min-width: 30px;
  text-align: center;
}

/* 模态框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
  padding: 24px;
  z-index: 99999;
  animation: fadeIn 0.3s ease;
}

@media (max-width: 720px) {
  .modal-overlay {
    padding: 16px;
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-premium {
  background: rgba(26, 31, 58, 0.95);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  max-width: 800px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideUp 0.3s ease;
}

.detail-modal {
  max-width: 700px;
  max-height: none;
  overflow-y: visible;
}

.detail-modal--child {
  max-width: 560px;
  width: min(92vw, 520px);
}

.detail-modal--parent {
  max-width: 640px;
  width: min(92vw, 640px);
}

.wide-modal {
  max-width: 1200px;
}

.cleanup-modal {
  width: min(92vw, 900px);
  max-width: 900px;
}

.cleanup-body {
  padding: 18px 20px;
  max-height: 65vh;
  overflow: auto;
  scrollbar-gutter: stable both-edges;
  position: relative;
}

.cleanup-download-overlay {
  position: absolute;
  inset: 0;
  background: rgba(2, 6, 23, 0.55);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

.cleanup-download-overlay-card {
  width: min(520px, 92%);
  padding: 18px 16px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.92);
  border: 1px solid rgba(59, 130, 246, 0.25);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
  text-align: center;
  color: #cbd5e1;
}

.cleanup-download-title {
  margin: 0 0 6px;
  font-weight: 700;
  color: #e2e8f0;
}

.cleanup-download-sub {
  margin: 0;
  font-size: 12px;
  color: #94a3b8;
}

.cleanup-tip {
  color: #cbd5e1;
  font-size: 14px;
  margin-bottom: 12px;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
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
  padding: 24px 28px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
}

.detail-modal .modal-header {
  padding: 18px 20px;
}

.modal-title {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
}

.modal-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 28px;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.modal-close:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.modal-body {
  padding: 28px;
}

.detail-modal .modal-body {
  padding: 18px 20px;
}

.subtask-body {
  padding: 0;
  max-height: 60vh;
  overflow-y: auto;
  overflow-x: auto;
}

.subtask-table {
  margin: 0;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

@media (max-width: 720px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}

.parent-chart-section {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(59, 130, 246, 0.15);
}

.parent-chart-wrap {
  display: flex;
  gap: 18px;
  align-items: center;
}

.parent-chart-legend {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.legend-item {
  display: grid;
  grid-template-columns: 10px 1fr 64px 76px;
  gap: 8px;
  align-items: center;
  padding: 6px 10px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.35);
  border: 1px solid rgba(59, 130, 246, 0.12);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.legend-name {
  color: #e2e8f0;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.legend-value {
  color: #94a3b8;
  font-size: 12px;
  text-align: right;
}

.legend-percent {
  color: #3b82f6;
  font-size: 12px;
  font-weight: 700;
  text-align: right;
}

.parent-chart-selected {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(59, 130, 246, 0.12);
  border: 1px solid rgba(59, 130, 246, 0.25);
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}

.selected-name {
  color: #e2e8f0;
  font-weight: 700;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selected-rate {
  color: #3b82f6;
  font-weight: 800;
  font-size: 13px;
  flex-shrink: 0;
}

.selected-meta {
  color: #94a3b8;
  font-size: 12px;
  flex-shrink: 0;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-item.full-width {
  grid-column: 1 / -1;
}

.detail-label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  font-size: 14px;
  color: #e2e8f0;
}

.prefix-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.prefix-item {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 10px;
  background: rgba(10, 14, 39, 0.35);
}

.prefix-bucket {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  color: #93c5fd;
  background: rgba(59, 130, 246, 0.12);
  border: 1px solid rgba(59, 130, 246, 0.2);
  flex: 0 0 auto;
}

.prefix-path {
  font-family: 'Courier New', monospace;
  color: #e2e8f0;
  font-size: 12px;
  word-break: break-all;
}

.cleanup-confirm-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}

.cleanup-confirm-label {
  color: #94a3b8;
  font-size: 13px;
  flex: 0 0 auto;
}

.cleanup-confirm-input {
  flex: 1 1 auto;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(10, 14, 39, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #e2e8f0;
  font-size: 14px;
  outline: none;
}

.cleanup-confirm-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 28px;
  border-top: 1px solid rgba(59, 130, 246, 0.2);
}

.modal-btn {
  padding: 10px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.secondary-btn {
  background: rgba(100, 116, 139, 0.2);
  color: #94a3b8;
  border: 1px solid rgba(100, 116, 139, 0.3);
}

.secondary-btn:hover {
  background: rgba(100, 116, 139, 0.3);
}

.primary-btn {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #fff;
  border: 1px solid rgba(59, 130, 246, 0.35);
}

.primary-btn:hover:not(:disabled) {
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.35);
  transform: translateY(-1px);
}

.download-btn {
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
  color: #fff;
  border: 1px solid rgba(6, 182, 212, 0.35);
}

.download-btn:hover:not(:disabled) {
  box-shadow: 0 8px 24px rgba(6, 182, 212, 0.3);
  transform: translateY(-1px);
}

/* 滚动条样式 */
.modal-premium::-webkit-scrollbar,
.subtask-body::-webkit-scrollbar {
  width: 6px;
}

.modal-premium::-webkit-scrollbar-track,
.subtask-body::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
}

.modal-premium::-webkit-scrollbar-thumb,
.subtask-body::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.3);
  border-radius: 3px;
}

.modal-premium::-webkit-scrollbar-thumb:hover,
.subtask-body::-webkit-scrollbar-thumb:hover {
  background: rgba(59, 130, 246, 0.5);
}
</style>
