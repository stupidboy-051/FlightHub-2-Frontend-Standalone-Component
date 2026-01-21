import axios from 'axios'

// 创建axios实例 (复用现有配置逻辑，实际项目中最好抽取为公共 utils/request.js)
const api = axios.create({
  baseURL: process.env.VUE_APP_API_BASE_URL || '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Token ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API请求错误:', error)
    return Promise.reject(error)
  }
)

// 存疑图片API服务
export default {
  // 上报存疑图片
  async reportSuspiciousImage(data) {
    try {
      const response = await api.post('/suspicious-images/', data)
      return response
    } catch (error) {
      console.error('上报存疑图片失败:', error)
      throw error
    }
  },

  // 获取统计数据
  async getStats() {
    try {
      const response = await api.get('/suspicious-images/stats/')
      return response
    } catch (error) {
      console.error('获取存疑统计失败:', error)
      throw error
    }
  },

  // 导出数据 (返回 blob)
  async exportCsv() {
    try {
      const response = await api.get('/suspicious-images/export/', {
        responseType: 'blob' // 关键：指定响应类型为 blob
      })
      // 注意：由于响应拦截器直接返回了 response.data，这里其实拿到的就是 blob
      // 如果拦截器逻辑不同，可能需要调整。
      // 根据 alarmApi.js 的拦截器：return response.data。
      // 对于 blob 类型，axios 的 response.data 就是 blob 对象。
      return response
    } catch (error) {
      console.error('导出存疑图片失败:', error)
      throw error
    }
  }
}
