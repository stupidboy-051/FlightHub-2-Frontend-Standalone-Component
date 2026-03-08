import axios from 'axios'

const api = axios.create({
  baseURL: process.env.VUE_APP_API_BASE_URL || '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Token ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API request error:', error)
    return Promise.reject(error)
  }
)

export default {
  async getAlarms(params = {}) {
    const response = await api.get('/alarms/', { params })
    return response
  },

  async getWaylines(params = {}) {
    const response = await api.get('/waylines/', { params })
    return response
  },

  async getWaylineDetail(id) {
    const response = await api.get(`/waylines/${id}/`)
    return response
  },

  async getAlarmDetail(alarmId) {
    const response = await api.get(`/alarms/${alarmId}/`)
    return response
  },

  async createAlarm(alarmData) {
    const response = await api.post('/alarms/', alarmData)
    return response
  },

  async updateAlarm(alarmId, alarmData) {
    const response = await api.put(`/alarms/${alarmId}/`, alarmData)
    return response
  },

  async patchAlarm(alarmId, alarmData) {
    const response = await api.patch(`/alarms/${alarmId}/`, alarmData)
    return response
  },

  async deleteAlarm(alarmId) {
    const response = await api.delete(`/alarms/${alarmId}/`)
    return response
  },

  async getAlarmCategories() {
    const response = await api.get('/alarm-categories/')
    return response
  },

  async getAlarmDashboardStats(params = {}) {
    const response = await api.get('/alarm-dashboard-stats/summary/', { params })
    return response
  },

  async getAlarmDashboardCache(params = {}) {
    const response = await api.get('/alarm-dashboard-cache/summary/', { params })
    return response
  }
}
