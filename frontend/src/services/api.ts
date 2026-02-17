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
import type { VocabItem } from '@/types/vocab'

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

// ============ API 配置（SQLite 加密存储） ============

export const saveApiConfig = async (config: {
  provider: string;
  api_keys: string[];
  model?: string;
  rotation_enabled?: boolean;
}): Promise<ApiConfigResponse> => {
  const response = await fetchAPI<ApiConfigResponse>('/api/settings/api-config', {
    method: 'POST',
    body: JSON.stringify(config),
  })

  if (!response.success) {
    handleError(new Error(response.error || '保存API配置失败'), 'saveApiConfig')
    throw new Error(response.error || '保存API配置失败')
  }

  return response.data!
}

export const getApiConfig = async (provider: string): Promise<ApiConfigResponse> => {
  const response = await fetchAPI<ApiConfigResponse>(`/api/settings/api-config/${provider}`, {
    method: 'GET',
  })

  if (!response.success) {
    handleError(new Error(response.error || '获取API配置失败'), 'getApiConfig')
    throw new Error(response.error || '获取API配置失败')
  }

  return response.data!
}

export const getTavilyConfig = async (): Promise<TavilyConfigResponse> => {
  const response = await fetchAPI<TavilyConfigResponse>('/api/settings/tavily-config', {
    method: 'GET',
  })

  if (!response.success) {
    handleError(new Error(response.error || '获取Tavily配置失败'), 'getTavilyConfig')
    throw new Error(response.error || '获取Tavily配置失败')
  }

  return response.data!
}

export const updateTavilyConfig = async (config: {
  api_key: string;
  enabled: boolean;
}): Promise<TavilyConfigResponse> => {
  const response = await fetchAPI<TavilyConfigResponse>('/api/settings/tavily-config', {
    method: 'PUT',
    body: JSON.stringify(config),
  })

  if (!response.success) {
    handleError(new Error(response.error || '更新Tavily配置失败'), 'updateTavilyConfig')
    throw new Error(response.error || '更新Tavily配置失败')
  }

  return response.data!
}

// ============ Provider 列表（从 LLM_MODEL_MAP 动态获取） ============

export interface ProviderOption {
  value: string;
  label: string;
}

export const getProviderOptions = async (): Promise<ProviderOption[]> => {
  const response = await fetchAPI<{ success: boolean; providers: ProviderOption[] }>(
    '/api/settings/providers',
    { method: 'GET' }
  )

  if (!response.success) {
    handleError(new Error(response.error || '获取 Provider 列表失败'), 'getProviderOptions')
    throw new Error(response.error || '获取 Provider 列表失败')
  }

  return response.data?.providers || []
}

// ============ 用户练习保存接口 ============

export const saveUserPractice = async (
  taskId: string,
  practice: Array<{ index: number; inputs: string[] }>
) => {
  const response = await fetchAPI(`/api/v1/tasks/${taskId}/user-practice`, {
    method: 'PUT',
    body: JSON.stringify({ practice }),
  })

  if (!response.success) {
    handleError(new Error(response.error || '保存练习失败'), 'saveUserPractice')
    throw new Error(response.error || '保存练习失败')
  }

  return response.data
}

export const getUserPractice = async (
  taskId: string
): Promise<Array<{ index: number; inputs: string[] }> | null> => {
  const response = await fetchAPI<{ practice: Array<{ index: number; inputs: string[] }> }>(
    `/api/v1/tasks/${taskId}/user-practice`,
    {
      method: 'GET',
    }
  )

  if (!response.success) {
    handleError(new Error(response.error || '获取练习失败'), 'getUserPractice')
    throw new Error(response.error || '获取练习失败')
  }

  return response.data?.practice || null
}

// ============ 生词本 API ============

export const syncVocabToServer = async (words: VocabItem[]): Promise<void> => {
  const res = await fetch('/api/vocab/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ words })
  })
  if (!res.ok) throw new Error('Sync failed')
}

export const getVocabFromServer = async (): Promise<VocabItem[]> => {
  const res = await fetch('/api/vocab')
  if (!res.ok) throw new Error('Failed to fetch vocab')
  const data = await res.json()
  return data.words
}

export const deleteVocabFromServer = async (id: string): Promise<void> => {
  const res = await fetch(`/api/vocab/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Delete failed')
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
  saveUserPractice,
  getUserPractice,
  getProviderOptions,
  saveApiConfig,
  getApiConfig,
  getTavilyConfig,
  updateTavilyConfig,
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
