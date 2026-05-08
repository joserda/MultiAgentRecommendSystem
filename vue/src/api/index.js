import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// ==================== 推荐相关 ====================

// 获取推荐
export const getRecommend = async (data) => {
  const response = await api.post('/recommend', data)
  return response.data
}

// 获取A/B实验状态
export const getExperiments = async () => {
  const response = await api.get('/experiments')
  return response.data
}

// 获取系统指标
export const getMetrics = async () => {
  const response = await api.get('/metrics')
  return response.data
}

// 健康检查
export const healthCheck = async () => {
  const response = await axios.get('/health')
  return response.data
}

// ==================== 向量存储相关 ====================

// 连接向量数据库
export const connectVectorStore = async () => {
  const response = await api.post('/vector/connect')
  return response.data
}

// 写入商品向量
export const upsertProducts = async () => {
  const response = await api.post('/vector/products')
  return response.data
}

// 获取向量存储状态
export const getVectorStats = async () => {
  const response = await api.get('/vector/stats')
  return response.data
}

export default api
