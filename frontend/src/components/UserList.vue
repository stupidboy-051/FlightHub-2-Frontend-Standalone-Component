<template>
  <div class="user-list-premium">
    <!-- 搜索筛选区 -->
    <div class="search-section-premium">
      <div class="search-wrapper">
        <div class="search-icon">🔍</div>
        <input 
          v-model="searchQuery"
          @input="handleSearch"
          placeholder="搜索账号或姓名..."
          class="search-input-premium"
        />
      </div>
      
      <!-- 功能按钮组 - 紧凑设计 -->
      <div class="action-buttons-group">
        <button @click="exportSuspiciousImages" class="icon-btn-premium warning-gradient" title="导出存疑记录">
          <span class="btn-icon">⬇</span>
        </button>
        <button @click="exportInspectionReport" class="icon-btn-premium success-gradient" title="导出检测报表">
          <span class="btn-icon">📊</span>
        </button>
        <button @click="handleManualDetect" class="icon-btn-premium purple-gradient" title="手动检测">
          <span class="btn-icon">🛠️</span>
        </button>
        <button @click="showAddUserDialog" class="add-user-btn-premium" title="添加用户">
          <span class="btn-icon">+</span>
          <span class="btn-text">添加</span>
        </button>
      </div>
    </div>

    <!-- 用户列表卡片 -->
    <div class="table-card-premium">
      <div class="table-wrapper-premium">
        <table class="premium-table">
          <thead>
            <tr>
              <!-- <th width="80">ID</th> -->
              <th width="140">账号</th>
              <th width="140">姓名</th>
              <th width="100">角色</th>
              <th width="140">创建时间</th>
              <th width="140">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in allUsers" :key="user.id" class="table-row">
              <!-- <td>
                <span class="id-badge">{{ user.id }}</span>
              </td> -->
              <td>
                <div class="username-cell">
                  <div class="user-avatar-small">{{ user.username.charAt(0).toUpperCase() }}</div>
                  <span>{{ user.username }}</span>
                </div>
              </td>
              <td>{{ user.name }}</td>
              <td>
                <span class="role-badge" :class="user.role === 'admin' ? 'role-admin' : 'role-user'">
                  {{ user.role === 'admin' ? '管理员' : '普通用户' }}
                </span>
              </td>
              <td>
                <span class="datetime-text">{{ formatDate(user.createdAt) }}</span>
              </td>
              <td>
                <div v-if="user.username !== 'admin'" class="action-buttons">
                  <button @click="showEditUserDialog(user)" class="action-btn edit-btn">
                    <span>编辑</span>
                  </button>
                  <button @click="confirmDeleteUser(user)" class="action-btn delete-btn">
                    <span>删除</span>
                  </button>
                </div>
                <div v-else class="system-admin-badge">
                  系统管理员
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页器 -->
      <div class="pagination-premium">
        <div class="pagination-info">
          显示 {{ Math.min((currentPage - 1) * pageSize + 1, totalUsers) }} - {{ Math.min(currentPage * pageSize, totalUsers) }} 条，共 {{ totalUsers }} 条
        </div>
        <div class="pagination-controls">
          <button @click="handlePageChange(currentPage - 1)" :disabled="currentPage === 1" class="pagination-btn">
            <span>‹</span>
          </button>
          <input 
            type="number" 
            :value="currentPage"
            @change="handlePageChange(Number($event.target.value))"
            class="page-input"
            min="1"
            :max="Math.ceil(totalUsers / pageSize)"
          />
          <span class="pagination-separator">/</span>
          <span class="total-pages">{{ Math.ceil(totalUsers / pageSize) || 1 }}</span>
          <button @click="handlePageChange(currentPage + 1)" :disabled="currentPage >= Math.ceil(totalUsers / pageSize)" class="pagination-btn">
            <span>›</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 添加/编辑用户对话框 -->
    <div v-if="dialogVisible" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-premium">
        <div class="modal-header">
          <h2 class="modal-title">{{ dialogTitle }}</h2>
          <button @click="closeDialog" class="modal-close">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">账号</label>
            <input 
              v-model="formData.username"
              :disabled="editingUserId !== null"
              placeholder="请输入账号"
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label class="form-label">姓名</label>
            <input 
              v-model="formData.name"
              placeholder="请输入姓名"
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label class="form-label">密码{{ editingUserId !== null ? '（不修改请留空）' : '' }}</label>
            <input 
              v-model="formData.password"
              type="password"
              placeholder="请输入密码"
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label class="form-label">角色</label>
            <select v-model="formData.role" class="form-select">
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="closeDialog" class="modal-btn secondary-btn">取消</button>
          <button @click="submitForm" :disabled="isSubmitting" class="modal-btn primary-btn">
            {{ isSubmitting ? '提交中...' : '确定' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 手动检测弹窗 -->
    <div v-if="manualDetectVisible" class="modal-overlay" @click.self="manualDetectVisible = false">
      <div class="modal-premium">
        <div class="modal-header">
          <h2 class="modal-title">手动检测</h2>
          <button @click="manualDetectVisible = false" class="modal-close">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">MinIO 文件夹路径</label>
            <input 
              v-model="manualDetectForm.folderPath"
              placeholder="例如: 20231001_rail_test/media/flight_uuid/"
              class="form-input"
            />
            <p class="form-hint">请输入 MinIO 中包含图片的完整文件夹路径</p>
          </div>
          <div class="form-group">
            <label class="form-label">检测类型 (可选)</label>
            <select v-model="manualDetectForm.detectType" class="form-select">
              <option value="unknown">自动识别 (从文件夹名解析)</option>
              <option value="rail">轨道检测 (Rail)</option>
              <option value="contactline">接触网检测 (Contactline)</option>
              <option value="bridge">桥梁检测 (Bridge)</option>
              <option value="protected_area">保护区检测 (Protected Area)</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">任务名称 (可选)</label>
            <input 
              v-model="manualDetectForm.taskName"
              placeholder="默认自动生成"
              class="form-input"
            />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="manualDetectVisible = false" class="modal-btn secondary-btn">取消</button>
          <button @click="confirmManualDetect" class="modal-btn primary-btn" :disabled="!manualDetectForm.folderPath">
            确认启动
          </button>
        </div>
      </div>
    </div>

    <!-- 导出报表弹窗 -->
    <div v-if="exportReportVisible" class="modal-overlay" @click.self="exportReportVisible = false">
      <div class="modal-premium">
        <div class="modal-header">
          <h2 class="modal-title">导出检测报表</h2>
          <button @click="exportReportVisible = false" class="modal-close">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">开始日期</label>
            <input 
              v-model="exportForm.startDate"
              type="date"
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label class="form-label">结束日期</label>
            <input 
              v-model="exportForm.endDate"
              type="date"
              class="form-input"
            />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="exportReportVisible = false" class="modal-btn secondary-btn">取消</button>
          <button @click="confirmExportReport" class="modal-btn primary-btn">
            导出 Excel
          </button>
        </div>
      </div>
    </div>

    <!-- 删除确认对话框 -->
    <div v-if="deleteDialogVisible" class="modal-overlay" @click.self="deleteDialogVisible = false">
      <div class="modal-premium delete-modal">
        <div class="modal-header">
          <h2 class="modal-title">确认删除</h2>
          <button @click="deleteDialogVisible = false" class="modal-close">×</button>
        </div>
        <div class="modal-body">
          <div class="delete-warning">
            <div class="warning-icon">⚠️</div>
            <p>确定要删除用户 <strong>{{ selectedUserName }}</strong> 吗？</p>
            <p class="warning-text">此操作不可撤销，请谨慎操作！</p>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="deleteDialogVisible = false" class="modal-btn secondary-btn">取消</button>
          <button @click="deleteUser" :disabled="isDeleting" class="modal-btn danger-btn">
            {{ isDeleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useStore } from 'vuex'
import { ElMessage } from 'element-plus'
import suspiciousImageApi from '../api/suspiciousImageApi'
import inspectTaskApi from '../api/inspectTaskApi'
import inspectImageApi from '../api/inspectImageApi'

export default {
  name: 'UserList',
  setup() {
    const store = useStore()
    const userFormRef = ref(null)
    
    onMounted(() => {
      loadUsers()
      loadSuspiciousStats()
    })
    
    // 响应式数据
    const suspiciousStats = ref({
      total: 0,
      pending: 0,
      confirmed: 0,
      ignored: 0
    })
    const searchQuery = ref('')
    const dialogVisible = ref(false)
    const deleteDialogVisible = ref(false)
    const manualDetectVisible = ref(false)
    const exportReportVisible = ref(false)
    const editingUserId = ref(null)
    const selectedUserName = ref('')
    const selectedUserId = ref(null)
    const isSubmitting = ref(false)
    const isDeleting = ref(false)
    
    const formData = ref({
      username: '',
      name: '',
      password: '',
      role: 'user'
    })

    const manualDetectForm = ref({
      folderPath: '',
      detectType: 'unknown',
      taskName: ''
    })

    const exportForm = ref({
      startDate: new Date(new Date().setDate(new Date().getDate() - 30)).toISOString().split('T')[0],
      endDate: new Date().toISOString().split('T')[0]
    })
    
    // 计算属性
    const allUsers = computed(() => store.getters.allUsers)
    const currentPage = computed(() => store.state.currentPage)
    const pageSize = computed(() => store.state.pageSize)
    const totalUsers = computed(() => store.state.totalUsers)
    
    const dialogTitle = computed(() => {
      return editingUserId.value ? '编辑用户' : '添加用户'
    })
    
    // 加载用户列表
    const loadUsers = async () => {
      try {
        await store.dispatch('fetchUsers', {
          page: currentPage.value,
          page_size: pageSize.value,
          search: searchQuery.value
        })
      } catch (error) {
        console.error('加载用户失败:', error)
        ElMessage.error('加载用户列表失败')
      }
    }
    
    // 分页事件处理
    const handlePageChange = (page) => {
      if (page < 1 || page > Math.ceil(totalUsers.value / pageSize.value)) return
      store.commit('SET_PAGINATION_INFO', { currentPage: page })
      loadUsers()
    }
    
    // 搜索功能 - 使用防抖
    let searchTimeout = null
    const handleSearch = () => {
      if (searchTimeout) clearTimeout(searchTimeout)
      searchTimeout = setTimeout(() => {
        // 搜索时重置到第一页
        store.commit('SET_PAGINATION_INFO', { currentPage: 1 })
        loadUsers()
      }, 300)
    }
    
    // 方法
    const formatDate = (dateString) => {
      const date = new Date(dateString)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    }
    
    const showAddUserDialog = () => {
      resetForm()
      editingUserId.value = null
      dialogVisible.value = true
    }
    
    const showEditUserDialog = (user) => {
      editingUserId.value = user.id
      formData.value = {
        username: user.username,
        name: user.name,
        password: '',
        role: user.role
      }
      dialogVisible.value = true
    }
    
    const confirmDeleteUser = (user) => {
      selectedUserId.value = user.id
      selectedUserName.value = user.name
      deleteDialogVisible.value = true
    }
    
    const closeDialog = () => {
      dialogVisible.value = false
      resetForm()
    }
    
    const resetForm = () => {
      formData.value = {
        username: '',
        name: '',
        password: '',
        role: 'user'
      }
      editingUserId.value = null
    }
    
    const submitForm = async () => {
      try {
        // 简单验证
        if (!formData.value.username || !formData.value.name) {
          ElMessage.error('请填写完整信息')
          return
        }
        
        if (editingUserId.value === null && !formData.value.password) {
          ElMessage.error('请输入密码')
          return
        }
        
        isSubmitting.value = true
        
        if (editingUserId.value) {
          // 编辑用户
          const form = { ...formData.value }
          if (!form.password) {
            delete form.password
          }
          
          await store.dispatch('updateUser', { id: editingUserId.value, ...form })
          ElMessage.success('用户编辑成功')
          await loadUsers()
        } else {
          // 添加用户
          const existingUser = allUsers.value.find(
            user => user.username === formData.value.username
          )
          
          if (existingUser) {
            ElMessage.error('账号已存在，请选择其他账号')
            return
          }
          
          await store.dispatch('addUser', formData.value)
          ElMessage.success('用户添加成功')
          await loadUsers()
        }
        
        dialogVisible.value = false
        resetForm()
      } catch (error) {
        console.error('操作失败:', error)
        ElMessage.error(error.message || '操作失败，请重试')
      } finally {
        isSubmitting.value = false
      }
    }
    
    const deleteUser = async () => {
      try {
        isDeleting.value = true
        
        const user = allUsers.value.find(u => u.id === selectedUserId.value)
        if (user && user.username === 'admin') {
          ElMessage.error('不能删除系统管理员用户')
          return
        }
        
        await store.dispatch('deleteUser', selectedUserId.value)
        ElMessage.success('用户删除成功')
        deleteDialogVisible.value = false
        await loadUsers()
      } catch (error) {
        console.error('删除失败:', error)
        ElMessage.error(error.message || '删除失败，请重试')
      } finally {
        isDeleting.value = false
      }
    }

    // 存疑图片相关
    const loadSuspiciousStats = async () => {
      try {
        const res = await suspiciousImageApi.getStats()
        suspiciousStats.value = res
      } catch (error) {
        console.error('加载存疑统计失败:', error)
      }
    }

    const exportSuspiciousImages = async () => {
      try {
        const response = await suspiciousImageApi.exportCsv()
        // 创建下载链接
        const url = window.URL.createObjectURL(new Blob([response]))
        const link = document.createElement('a')
        link.href = url
        const now = new Date()
        const timestamp = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
        link.setAttribute('download', `suspicious_images_${timestamp}.csv`)
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      } catch (error) {
        console.error('导出失败:', error)
        ElMessage.error('导出失败')
      }
    }

    const exportInspectionReport = () => {
      exportReportVisible.value = true
    }

    const confirmExportReport = async () => {
      try {
        const response = await inspectImageApi.exportInspectImages({
          start_date: exportForm.value.startDate,
          end_date: exportForm.value.endDate
        })
        const url = window.URL.createObjectURL(new Blob([response]))
        const link = document.createElement('a')
        link.href = url
        const now = new Date()
        const timestamp = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
        link.setAttribute('download', `inspection_report_${timestamp}.xlsx`)
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        ElMessage.success('报表导出成功')
        exportReportVisible.value = false
      } catch (error) {
        console.error('导出报表失败:', error)
        ElMessage.error('导出报表失败')
      }
    }

    const handleManualDetect = () => {
      manualDetectVisible.value = true
    }

    const confirmManualDetect = async () => {
      try {
        await inspectTaskApi.startManualTask({
          source: 'web_manual',
          folder_path: manualDetectForm.value.folderPath,
          detect_type: manualDetectForm.value.detectType,
          task_name: manualDetectForm.value.taskName
        })
        ElMessage.success('手动检测指令已发送')
        manualDetectVisible.value = false
      } catch (error) {
        console.error('手动检测失败:', error)
        ElMessage.error('发送失败，请检查后端服务')
      }
    }

    return {
      searchQuery,
      dialogVisible,
      deleteDialogVisible,
      manualDetectVisible,
      exportReportVisible,
      selectedUserName,
      selectedUserId,
      isSubmitting,
      isDeleting,
      formData,
      manualDetectForm,
      exportForm,
      allUsers,
      currentPage,
      pageSize,
      totalUsers,
      dialogTitle,
      editingUserId,
      userFormRef,
      suspiciousStats,
      formatDate,
      showAddUserDialog,
      showEditUserDialog,
      confirmDeleteUser,
      closeDialog,
      submitForm,
      deleteUser,
      handlePageChange,
      handleSearch,
      loadSuspiciousStats,
      exportSuspiciousImages,
      exportInspectionReport,
      confirmExportReport,
      handleManualDetect,
      confirmManualDetect
    }
  }
}
</script>

<style scoped>
/* 复用原 UserManagement.vue 的样式，但移除最外层容器的 max-width 限制以适应分栏 */
.user-list-premium {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 按钮组样式 */
.action-buttons-group {
  display: flex;
  gap: 8px;
}

.icon-btn-premium {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  color: #fff;
}

.icon-btn-premium:hover {
  transform: translateY(-2px);
  filter: brightness(1.1);
}

.warning-gradient {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

.success-gradient {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.purple-gradient {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
}

.add-user-btn-premium {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  height: 36px;
  background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(0, 212, 255, 0.3);
}

.add-user-btn-premium:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 212, 255, 0.5);
}

.btn-icon {
  font-size: 16px;
  font-weight: bold;
}

.btn-text {
  white-space: nowrap;
}

/* 搜索区域 */
.search-section-premium {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}

.search-wrapper {
  flex: 1;
  min-width: 200px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(26, 31, 58, 0.6);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  border: 1px solid rgba(0, 212, 255, 0.2);
  transition: all 0.3s ease;
}

.search-wrapper:focus-within {
  border-color: #00d4ff;
  box-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
}

.search-icon {
  font-size: 16px;
  opacity: 0.7;
}

.search-input-premium {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: #e2e8f0;
  font-size: 14px;
}

.search-input-premium::placeholder {
  color: #64748b;
}

/* 表格卡片 */
.table-card-premium {
  background: rgba(26, 31, 58, 0.6);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  border: 1px solid rgba(0, 212, 255, 0.2);
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.table-wrapper-premium {
  flex: 1;
  overflow-y: auto;
  overflow-x: auto;
}

.premium-table {
  width: 100%;
  border-collapse: collapse;
}

.premium-table thead tr {
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.15) 0%, rgba(0, 153, 255, 0.15) 100%);
}

.premium-table th {
  padding: 12px 16px;
  text-align: left;
  color: #00d4ff;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 2px solid rgba(0, 212, 255, 0.3);
}

.premium-table tbody tr {
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
  transition: all 0.3s ease;
}

.premium-table tbody tr:hover {
  background: rgba(0, 212, 255, 0.05);
}

.premium-table td {
  padding: 12px 16px;
  color: #e2e8f0;
  font-size: 13px;
}

.id-badge {
  display: inline-block;
  padding: 2px 8px;
  background: rgba(0, 212, 255, 0.15);
  border-radius: 4px;
  color: #00d4ff;
  font-weight: 600;
  font-size: 12px;
}

.username-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-avatar-small {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 600;
  font-size: 12px;
}

.role-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.role-admin {
  background: linear-gradient(135deg, #a855f7 0%, #ec4899 100%);
  color: #fff;
  box-shadow: 0 2px 8px rgba(168, 85, 247, 0.3);
}

.role-user {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.datetime-text {
  color: #94a3b8;
  font-size: 12px;
}

.action-buttons {
  display: flex;
  gap: 6px;
}

.action-btn {
  padding: 4px 10px;
  border-radius: 4px;
  border: none;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.edit-btn {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.edit-btn:hover {
  background: rgba(59, 130, 246, 0.3);
  transform: translateY(-1px);
}

.delete-btn {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 0.3);
  transform: translateY(-1px);
}

.system-admin-badge {
  color: #94a3b8;
  font-size: 12px;
  font-style: italic;
}

/* 分页器 */
.pagination-premium {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
}

.pagination-info {
  color: #94a3b8;
  font-size: 12px;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid rgba(0, 212, 255, 0.3);
  background: rgba(0, 212, 255, 0.1);
  color: #00d4ff;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pagination-btn:hover:not(:disabled) {
  background: rgba(0, 212, 255, 0.2);
  transform: translateY(-1px);
}

.pagination-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.page-input {
  width: 40px;
  height: 28px;
  text-align: center;
  background: rgba(26, 31, 58, 0.8);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 12px;
  outline: none;
}

.page-input:focus {
  border-color: #00d4ff;
}

.pagination-separator {
  color: #64748b;
  font-size: 12px;
}

.total-pages {
  color: #94a3b8;
  font-size: 12px;
}

/* 模态框样式复用... */
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
  border-radius: 20px;
  border: 1px solid rgba(0, 212, 255, 0.3);
  box-shadow: 0 16px 64px rgba(0, 0, 0, 0.5), 0 0 40px rgba(0, 212, 255, 0.2);
  width: 100%;
  max-width: 540px;
  overflow: hidden;
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
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  font-size: 20px;
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

.form-group {
  margin-bottom: 16px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 6px;
}

.form-input,
.form-select {
  width: 100%;
  padding: 10px 14px;
  background: rgba(10, 14, 39, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 14px;
  outline: none;
  transition: all 0.3s ease;
}

.form-input:focus,
.form-select:focus {
  border-color: #00d4ff;
  box-shadow: 0 0 20px rgba(0, 212, 255, 0.2);
}

.form-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
}

.modal-btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
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
  background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
  color: #fff;
  box-shadow: 0 4px 16px rgba(0, 212, 255, 0.3);
}

.primary-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 212, 255, 0.5);
}

.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.danger-btn {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: #fff;
  box-shadow: 0 4px 16px rgba(239, 68, 68, 0.3);
}

.danger-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(239, 68, 68, 0.5);
}

/* 删除警告 */
.delete-warning {
  text-align: center;
  padding: 16px 0;
}

.warning-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.delete-warning p {
  color: #e2e8f0;
  font-size: 15px;
  margin: 6px 0;
}

.delete-warning strong {
  color: #00d4ff;
}

.warning-text {
  color: #f59e0b !important;
  font-size: 13px !important;
  margin-top: 8px !important;
}
</style>