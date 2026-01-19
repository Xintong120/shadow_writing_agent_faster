import { fetchAPI } from './client'
import { handleError } from '@/utils/errorHandler'
import {
  flattenStats,
  generateColors,
  convertMapToHighlightMapping,
  flattenBatchResults,
  calculateLearningTime,
  calculateStreakDays,
  convertShadowResultsToLearningItems,
} from './transforms'
import type {
  SearchTEDResponse,
  StartBatchResponse,
  TaskStatusResponse,
  StatsResponse,
  FlatStats,
  GetLearningRecordsResponse,
  ApiKeyTestResponse,
} from '@/types/api'

// ============ TED 搜索相关 ============

export const searchTED = async (
  topic: string,
  userId: string
) => {
  const response = await fetchAPI<SearchTEDResponse>('/api/v1/search-ted', {
    method: 'POST',
    body: JSON.stringify({ topic, user_id: userId }),
  })

  if (!response.success) {
    handleError(new Error(response.error || '搜索TED失败'), 'searchTED')
    throw new Error(response.error || '搜索TED失败')
  }

  return response.data
}

// ============ 批量处理相关 ============

export const startBatchProcess = async (
  urls: string[],
  userId: string
) => {
  const response = await fetchAPI<StartBatchResponse>('/api/v1/process-batch', {
    method: 'POST',
    body: JSON.stringify({ urls, user_id: userId }),
  })

  if (!response.success) {
    handleError(new Error(response.error || '启动批量处理失败'), 'startBatchProcess')
    throw new Error(response.error || '启动批量处理失败')
  }

  return response.data
}

export const getTaskStatus = async (
  taskId: string
) => {
  const requestStartTime = Date.now()
  console.log(`[API] getTaskStatus 开始调用 - taskId: ${taskId} 时间: ${new Date(requestStartTime).toLocaleTimeString()}`)

  // 设置30秒超时
  const controller = new AbortController()
  const timeoutId = setTimeout(() => {
    controller.abort()
    console.log(`[API] getTaskStatus 超时 - taskId: ${taskId} 时间: ${new Date().toLocaleTimeString()}`)
  }, 30000)

  try {
    const response = await fetchAPI<TaskStatusResponse>(`/api/v1/task/${taskId}`, {
      method: 'GET',
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    const responseTime = Date.now()
    const duration = responseTime - requestStartTime
    console.log(`[API] getTaskStatus 收到响应 - 耗时: ${duration}ms 成功: ${response.success} 时间: ${new Date(responseTime).toLocaleTimeString()}`)

    if (!response.success) {
      console.error(`[API] getTaskStatus 失败 - 错误: ${response.error}`)
      handleError(new Error(response.error || '获取任务状态失败'), 'getTaskStatus')
      throw new Error(response.error || '获取任务状态失败')
    }

    console.log(`[API] getTaskStatus 成功 - 任务状态: ${response.data?.status} 进度: ${response.data?.current}/${response.data?.total}`)
    return response.data
  } catch (error) {
    clearTimeout(timeoutId)
    if (error.name === 'AbortError') {
      console.error(`[API] getTaskStatus 超时 - taskId: ${taskId}`)
      throw new Error('获取任务状态超时，请稍后重试')
    }
    throw error
  }
}

// ============ Memory 系统相关 ============

export const getLearningRecords = async (
  userId: string,
  filters?: {
    limit?: number
    offset?: number
    sort_by?: 'learned_at' | 'learning_time'
    order?: 'asc' | 'desc'
  }
): Promise<GetLearningRecordsResponse> => {
  const params = new URLSearchParams({
    ...(filters?.limit && { limit: String(filters.limit) }),
    ...(filters?.offset && { offset: String(filters.offset) }),
    ...(filters?.sort_by && { sort_by: filters.sort_by }),
    ...(filters?.order && { order: filters.order }),
  })

  const response = await fetchAPI<GetLearningRecordsResponse>(
    `/memory/learning-records/${userId}?${params}`,
    { method: 'GET' }
  )

  if (!response.success) {
    handleError(new Error(response.error || '获取学习记录失败'), 'getLearningRecords')
    throw new Error(response.error || '获取学习记录失败')
  }

  return response.data!
}

export const getStats = async (userId: string): Promise<FlatStats> => {
  const response = await fetchAPI<StatsResponse>(`/memory/stats/${userId}`, {
    method: 'GET',
  })

  if (!response.success) {
    handleError(new Error(response.error || '获取统计数据失败'), 'getStats')
    throw new Error(response.error || '获取统计数据失败')
  }

  // ✅ 扁平化统计数据用于前端显示
  return flattenStats(response.data!)
}

// ============ 健康检查 ============

export const healthCheck = async () => {
  const response = await fetchAPI<{ status: string }>('/api/v1/health', {
    method: 'GET',
  })

  if (!response.success) {
    handleError(new Error(response.error || '健康检查失败'), 'healthCheck')
    throw new Error(response.error || '健康检查失败')
  }

  return response.data
}

// ============ 设置相关 ============

export const testApiKey = async (provider: string, apiKey: string): Promise<ApiKeyTestResponse> => {
  const response = await fetchAPI<ApiKeyTestResponse>('/api/settings/test-api-key', {
    method: 'POST',
    body: JSON.stringify({ provider, api_key: apiKey }),
  })

  if (!response.success) {
    handleError(new Error(response.error || '测试API密钥失败'), 'testApiKey')
    throw new Error(response.error || '测试API密钥失败')
  }

  return response.data!
}

export const updateSettings = async (settings: any) => {
  const response = await fetchAPI('/api/settings/', {
    method: 'PUT',
    body: JSON.stringify(settings),
  })

  if (!response.success) {
    handleError(new Error(response.error || '更新设置失败'), 'updateSettings')
    throw new Error(response.error || '更新设置失败')
  }

  return response.data
}

export const getSettings = async () => {
  const response = await fetchAPI('/api/settings/', {
    method: 'GET',
  })

  if (!response.success) {
    handleError(new Error(response.error || '获取设置失败'), 'getSettings')
    throw new Error(response.error || '获取设置失败')
  }

  return response.data
}

export const getProviderModels = async (provider: string, apiKey?: string) => {
  const url = apiKey
    ? `/api/config/models/${provider}?api_key=${encodeURIComponent(apiKey)}`
    : `/api/config/models/${provider}`

  const response = await fetchAPI(url, {
    method: 'GET',
  })

  if (!response.success) {
    handleError(new Error(response.error || '获取模型列表失败'), 'getProviderModels')
    throw new Error(response.error || '获取模型列表失败')
  }

  return response.data
}

// ============ 导出所有API ============

export const api = {
  searchTED,
  startBatchProcess,
  getTaskStatus,
  getLearningRecords,
  getStats,
  healthCheck,
  testApiKey,
  getSettings,
  updateSettings,
  getProviderModels,
}

// 导出工具函数（用于 ResultsPage 扁平化数据和 LearningSessionPage 数据转换）
export {
  flattenBatchResults,
  convertMapToHighlightMapping,
  generateColors,
  calculateLearningTime,
  calculateStreakDays,
  flattenStats,
  convertShadowResultsToLearningItems,
}

export default api
