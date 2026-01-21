import axios from 'axios'

const api = axios.create({
  baseURL: process.env.VUE_APP_API_BASE_URL || '/api/v1',
  timeout: 30000, // Download might take longer
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
  error => Promise.reject(error)
)

export default {
  async exportInspectImages(params) {
    try {
      const response = await api.get('/inspect-images/export/', {
        params,
        responseType: 'blob'
      })
      return response
    } catch (error) {
      console.error('导出巡检图片失败:', error)
      throw error
    }
  }
}
